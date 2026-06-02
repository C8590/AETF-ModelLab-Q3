from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

import pandas as pd

from .validation import ETF_DAILY_K_REQUIRED, require_columns


KRONOS_SAMPLE_REQUIRED = ["timestamps", "open", "high", "low", "close"]
KRONOS_SAMPLE_OPTIONAL = ["volume", "amount"]


@dataclass
class KronosConfig:
    model_name: str = "Kronos-small"
    tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-base"
    predictor_name: str = "NeoQuasar/Kronos-small"
    max_context: int = 512
    lookback: int = 400
    pred_len: int = 120
    sample_count: int = 1
    temperature: float = 1.0
    top_p: float = 0.9
    device: str = "cuda:0"
    external_repo_path: Path = Path("external/Kronos")
    hf_cache_dir: Path = Path("models/kronos/hf_cache")


def resolve_kronos_root(project_root: Path | None = None) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
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
    if "volume" in df.columns and "amount" not in df.columns:
        return
    if "amount" in df.columns and "volume" not in df.columns:
        return
    optional_present = [col for col in KRONOS_SAMPLE_OPTIONAL if col in df.columns]
    if optional_present and df[optional_present].isnull().values.any():
        raise ValueError(f"{name} contains NaN values in optional volume/amount columns.")


def write_markdown_report(output_path: str | Path, title: str, lines: list[str]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {title}", "", *lines]
    path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")


class KronosAdapter:
    """Adapter boundary around Kronos.

    V0.1 only provides the contract. V0.2 implements actual loading after
    external/Kronos and model weights are installed locally.
    """

    def __init__(self, config: KronosConfig | None = None) -> None:
        self.config = config or KronosConfig()
        self._predictor: Any | None = None

    def is_ready(self) -> bool:
        repo = resolve_kronos_root() if not self.config.external_repo_path.is_absolute() else self.config.external_repo_path
        return repo.exists() and any(repo.iterdir())

    def load(self) -> None:
        """Load tokenizer/model/predictor from the external Kronos checkout."""
        if not self.is_ready():
            raise RuntimeError(
                "Kronos repo is not installed. Finish V0.1 first, then clone "
                "https://github.com/shiyu-coder/Kronos into external/Kronos in V0.2."
            )
        kronos_root = (
            self.config.external_repo_path
            if self.config.external_repo_path.is_absolute()
            else resolve_kronos_root()
        )
        ensure_kronos_import_path(kronos_root)
        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore  # noqa: E402

        cache_dir = Path(self.config.hf_cache_dir)
        if not cache_dir.is_absolute():
            cache_dir = Path(__file__).resolve().parents[2] / cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

        tokenizer = KronosTokenizer.from_pretrained(self.config.tokenizer_name, cache_dir=cache_dir)
        model = Kronos.from_pretrained(self.config.predictor_name, cache_dir=cache_dir)
        tokenizer.eval()
        model.eval()
        self._predictor = KronosPredictor(
            model,
            tokenizer,
            device=self.config.device,
            max_context=self.config.max_context,
        )

    def prepare_input(self, daily_k: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        require_columns(daily_k, ETF_DAILY_K_REQUIRED, "ETF daily K")
        df = daily_k.sort_values("trade_date").tail(self.config.lookback).copy()
        if len(df) < min(self.config.lookback, 30):
            raise ValueError(f"Not enough history rows for Kronos: {len(df)}")
        x_df = df[["open", "high", "low", "close", "volume", "amount"]].copy()
        x_timestamp = pd.to_datetime(df["trade_date"])
        return x_df, x_timestamp

    def predict_single(self, daily_k: pd.DataFrame, code: str, as_of_date: str) -> pd.DataFrame:
        """Predict a single ETF future path.

        Returns the standard forecast schema. V0.2 should replace the placeholder
        with actual KronosPredictor.predict output.
        """
        _x_df, _x_timestamp = self.prepare_input(daily_k)
        raise NotImplementedError("V0.2: call KronosPredictor.predict and map output schema.")

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
        out["lookback"] = self.config.lookback
        out["pred_len"] = self.config.pred_len
        out["sample_count"] = self.config.sample_count
        out["run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ordered = [
            "trade_date", "code", "pred_date", "pred_open", "pred_high", "pred_low", "pred_close",
            "pred_volume", "pred_amount", "model_name", "lookback", "pred_len", "sample_count", "run_time",
        ]
        for col in ordered:
            if col not in out.columns:
                out[col] = pd.NA
        return out[ordered]
