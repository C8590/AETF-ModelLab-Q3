from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .validation import require_columns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_COLUMNS = ["open", "high", "low", "close"]
OPTIONAL_COLUMNS = ["volume", "amount"]
KRONOS_OUTPUT_COLUMNS = ["open", "high", "low", "close", "volume", "amount"]
KRONOS_SAMPLE_REQUIRED = ["timestamps", *PRICE_COLUMNS]
KRONOS_SAMPLE_OPTIONAL = OPTIONAL_COLUMNS.copy()


@dataclass
class KronosAdapterConfig:
    model_name: str = "NeoQuasar/Kronos-small"
    tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-base"
    device: str = "cuda:0"
    max_context: int = 512
    hf_cache_dir: Path | None = None
    kronos_root: Path | None = None
    default_lookback: int = 400
    default_pred_len: int = 120
    default_T: float = 1.0
    default_top_p: float = 0.9
    default_sample_count: int = 1


@dataclass
class KronosPredictionResult:
    pred_df: pd.DataFrame
    metadata: dict[str, Any]


@dataclass
class KronosPreparedInput:
    x_df: pd.DataFrame
    x_timestamp: pd.Series
    y_timestamp: pd.Series
    lookback: int
    pred_len: int
    filled_optional_columns: list[str]
    input_columns: list[str]


# Backward-compatible V0.2 name. V0.3 code should prefer KronosAdapterConfig.
KronosConfig = KronosAdapterConfig


def resolve_project_path(path: str | Path | None, default: str | Path) -> Path:
    value = Path(path) if path is not None else Path(default)
    return value if value.is_absolute() else PROJECT_ROOT / value


def resolve_kronos_root(project_root: Path | None = None) -> Path:
    root = project_root or PROJECT_ROOT
    return (root / "external" / "Kronos").resolve()


def ensure_kronos_import_path(kronos_root: Path) -> None:
    root_str = str(kronos_root.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def official_kronos_sample_path(project_root: Path | None = None) -> Path:
    return resolve_kronos_root(project_root) / "tests" / "data" / "regression_input.csv"


def validate_kronos_ohlcv_sample(df: pd.DataFrame, name: str = "Kronos sample") -> None:
    require_columns(df, KRONOS_SAMPLE_REQUIRED, name)
    if df[KRONOS_SAMPLE_REQUIRED].isnull().values.any():
        raise ValueError(f"{name} contains NaN values in required Kronos columns.")
    optional_present = [col for col in OPTIONAL_COLUMNS if col in df.columns]
    if optional_present and df[optional_present].isnull().values.any():
        raise ValueError(f"{name} contains NaN values in optional volume/amount columns.")


def write_markdown_report(output_path: str | Path, title: str, lines: list[str]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {title}", "", *lines]
    path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")


def _as_series(values: Iterable[Any] | pd.Series, name: str) -> pd.Series:
    series = values if isinstance(values, pd.Series) else pd.Series(list(values))
    if series.empty:
        raise ValueError(f"{name} must not be empty.")
    return pd.to_datetime(series).reset_index(drop=True)


def _torch_info(device: str) -> dict[str, Any]:
    try:
        import torch
    except Exception:
        return {
            "cuda_available": False,
            "gpu_name": "N/A",
            "torch_version": "unavailable",
            "cuda_version": "unavailable",
        }

    cuda_available = bool(torch.cuda.is_available())
    gpu_name = "N/A"
    if cuda_available:
        try:
            gpu_name = torch.cuda.get_device_name(torch.device(device))
        except Exception:
            gpu_name = torch.cuda.get_device_name(0)
    return {
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
    }


class KronosAdapter:
    """Reusable boundary around the external Kronos predictor."""

    def __init__(self, config: KronosAdapterConfig | None = None) -> None:
        self.config = config or KronosAdapterConfig()
        self.kronos_root = resolve_project_path(self.config.kronos_root, "external/Kronos")
        self.hf_cache_dir = resolve_project_path(self.config.hf_cache_dir, "models/kronos/hf_cache")
        self._predictor: Any | None = None
        self._model: Any | None = None
        self._tokenizer: Any | None = None

    def is_ready(self) -> bool:
        return self.kronos_root.exists() and (self.kronos_root / "model").exists()

    def is_loaded(self) -> bool:
        return self._predictor is not None

    def load(self) -> None:
        if self.is_loaded():
            return
        if not self.is_ready():
            raise RuntimeError(f"Kronos repo is not ready: {self.kronos_root}")

        self.hf_cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.hf_cache_dir))
        os.environ.setdefault("HF_HUB_CACHE", str(self.hf_cache_dir / "hub"))
        ensure_kronos_import_path(self.kronos_root)

        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore  # noqa: E402

        tokenizer = KronosTokenizer.from_pretrained(self.config.tokenizer_name, cache_dir=self.hf_cache_dir)
        model = Kronos.from_pretrained(self.config.model_name, cache_dir=self.hf_cache_dir)
        tokenizer.eval()
        model.eval()

        self._tokenizer = tokenizer
        self._model = model
        self._predictor = KronosPredictor(
            model,
            tokenizer,
            device=self.config.device,
            max_context=self.config.max_context,
        )

    def prepare_prediction_input(
        self,
        df: pd.DataFrame,
        *,
        timestamp_col: str = "timestamps",
        x_timestamp: Iterable[Any] | pd.Series | None = None,
        y_timestamp: Iterable[Any] | pd.Series | None = None,
        lookback: int | None = None,
        pred_len: int | None = None,
    ) -> KronosPreparedInput:
        if not isinstance(df, pd.DataFrame):
            raise ValueError("df must be a pandas DataFrame.")

        effective_lookback = lookback or self.config.default_lookback
        effective_pred_len = pred_len or self.config.default_pred_len
        if effective_lookback <= 0:
            raise ValueError("lookback must be positive.")
        if effective_pred_len <= 0:
            raise ValueError("pred_len must be positive.")

        require_columns(df, PRICE_COLUMNS, "Kronos input")
        working = df.copy()
        input_columns = working.columns.tolist()
        filled_optional_columns: list[str] = []
        for col in OPTIONAL_COLUMNS:
            if col not in working.columns:
                working[col] = 0.0
                filled_optional_columns.append(col)

        feature_columns = PRICE_COLUMNS + OPTIONAL_COLUMNS
        if working[feature_columns].isnull().values.any():
            raise ValueError("Kronos input contains NaN values in OHLCV/amount columns.")

        if x_timestamp is None:
            if timestamp_col not in working.columns:
                raise ValueError(f"Kronos input missing timestamp column: {timestamp_col}")
            if y_timestamp is None and len(working) < effective_lookback + effective_pred_len:
                raise ValueError(
                    "Not enough rows for Kronos prediction: "
                    f"{len(working)} < lookback + pred_len ({effective_lookback + effective_pred_len})."
                )
            if len(working) < effective_lookback:
                raise ValueError(
                    f"Not enough rows for Kronos lookback: {len(working)} < {effective_lookback}."
                )
            history = working.iloc[:effective_lookback].copy()
            x_ts = pd.to_datetime(history[timestamp_col]).reset_index(drop=True)
        else:
            x_ts_all = _as_series(x_timestamp, "x_timestamp")
            if len(working) < effective_lookback:
                raise ValueError(
                    f"Not enough rows for Kronos lookback: {len(working)} < {effective_lookback}."
                )
            history = working.tail(effective_lookback).copy()
            if len(x_ts_all) == len(working):
                x_ts = x_ts_all.tail(effective_lookback).reset_index(drop=True)
            elif len(x_ts_all) == effective_lookback:
                x_ts = x_ts_all.reset_index(drop=True)
            else:
                raise ValueError(
                    "x_timestamp length must equal df length or lookback: "
                    f"{len(x_ts_all)} not in {{{len(working)}, {effective_lookback}}}."
                )

        if y_timestamp is None:
            if timestamp_col not in working.columns:
                raise ValueError(f"Kronos input missing timestamp column: {timestamp_col}")
            if len(working) < effective_lookback + effective_pred_len:
                raise ValueError(
                    "Not enough rows for Kronos prediction: "
                    f"{len(working)} < lookback + pred_len ({effective_lookback + effective_pred_len})."
                )
            y_ts = pd.to_datetime(
                working[timestamp_col].iloc[effective_lookback : effective_lookback + effective_pred_len]
            ).reset_index(drop=True)
        else:
            y_ts = _as_series(y_timestamp, "y_timestamp")
            if len(y_ts) != effective_pred_len:
                raise ValueError(
                    f"y_timestamp length must equal pred_len: {len(y_ts)} != {effective_pred_len}."
                )

        x_df = history[feature_columns].reset_index(drop=True)
        return KronosPreparedInput(
            x_df=x_df,
            x_timestamp=x_ts,
            y_timestamp=y_ts,
            lookback=effective_lookback,
            pred_len=effective_pred_len,
            filled_optional_columns=filled_optional_columns,
            input_columns=input_columns,
        )

    def predict(
        self,
        df: pd.DataFrame,
        *,
        timestamp_col: str = "timestamps",
        x_timestamp: Iterable[Any] | pd.Series | None = None,
        y_timestamp: Iterable[Any] | pd.Series | None = None,
        lookback: int | None = None,
        pred_len: int | None = None,
        T: float | None = None,
        top_p: float | None = None,
        sample_count: int | None = None,
        top_k: int = 0,
        verbose: bool = True,
        include_timestamps: bool = True,
    ) -> KronosPredictionResult:
        started_at = datetime.now()
        started_monotonic = time.perf_counter()
        prepared = self.prepare_prediction_input(
            df,
            timestamp_col=timestamp_col,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            lookback=lookback,
            pred_len=pred_len,
        )
        if not self.is_loaded():
            self.load()
        if self._predictor is None:
            raise RuntimeError("Kronos predictor did not load.")

        import torch

        with torch.no_grad():
            pred_df = self._predictor.predict(
                df=prepared.x_df,
                x_timestamp=prepared.x_timestamp,
                y_timestamp=prepared.y_timestamp,
                pred_len=prepared.pred_len,
                T=T if T is not None else self.config.default_T,
                top_k=top_k,
                top_p=top_p if top_p is not None else self.config.default_top_p,
                sample_count=sample_count if sample_count is not None else self.config.default_sample_count,
                verbose=verbose,
            )

        pred_df = pred_df.copy()
        if include_timestamps and timestamp_col not in pred_df.columns:
            pred_df.insert(0, timestamp_col, prepared.y_timestamp.to_numpy())

        finished_at = datetime.now()
        torch_info = _torch_info(self.config.device)
        metadata = {
            "model_name": self.config.model_name,
            "tokenizer_name": self.config.tokenizer_name,
            "device": self.config.device,
            "cuda_available": torch_info["cuda_available"],
            "gpu_name": torch_info["gpu_name"],
            "max_context": self.config.max_context,
            "lookback": prepared.lookback,
            "pred_len": prepared.pred_len,
            "input_columns": prepared.input_columns,
            "output_columns": pred_df.columns.tolist(),
            "filled_optional_columns": prepared.filled_optional_columns,
            "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(time.perf_counter() - started_monotonic, 2),
            "success": True,
        }
        return KronosPredictionResult(pred_df=pred_df, metadata=metadata)

    def map_prediction_output(self, pred_df: pd.DataFrame, code: str, as_of_date: str) -> pd.DataFrame:
        out = pred_df.copy()
        rename = {
            "open": "pred_open",
            "high": "pred_high",
            "low": "pred_low",
            "close": "pred_close",
            "volume": "pred_volume",
            "amount": "pred_amount",
            "timestamps": "pred_date",
        }
        out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
        out["trade_date"] = as_of_date
        out["code"] = code
        out["model_name"] = self.config.model_name
        out["lookback"] = self.config.default_lookback
        out["pred_len"] = self.config.default_pred_len
        out["sample_count"] = self.config.default_sample_count
        out["run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ordered = [
            "trade_date", "code", "pred_date", "pred_open", "pred_high", "pred_low", "pred_close",
            "pred_volume", "pred_amount", "model_name", "lookback", "pred_len", "sample_count", "run_time",
        ]
        for col in ordered:
            if col not in out.columns:
                out[col] = pd.NA
        return out[ordered]
