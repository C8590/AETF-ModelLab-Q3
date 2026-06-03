from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .data_loader import read_kline_csv
from .kronos_adapter import KronosAdapter, KronosPredictionResult
from .replay_metrics import (
    aggregate_replay_metrics,
    compare_prediction_to_actual,
    split_kline_for_replay,
    summarize_actual_future_path,
)
from .shadow_features import summarize_prediction_path
from .validation import require_columns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPLAY_CASE_REQUIRED = [
    "replay_id",
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "kline_path",
    "notes",
]
FORBIDDEN_REPLAY_FIELD_TERMS = (
    "buy",
    "sell",
    "position",
    "target_price",
    "stop_loss",
    "order",
    "trade",
    "signal",
)


@dataclass
class ReplayPipelineConfig:
    replay_cases_path: Path
    output_predictions_path: Path
    output_metrics_path: Path
    report_path: Path
    lookback: int = 120
    pred_len: int = 24
    sample_count: int = 1
    max_cases: int | None = None
    T: float = 1.0
    top_p: float = 0.9
    project_root: Path = PROJECT_ROOT


def resolve_project_path(path: str | Path, *, project_root: Path = PROJECT_ROOT) -> Path:
    value = Path(path)
    return value if value.is_absolute() else project_root / value


def read_replay_cases(path: str | Path, *, max_cases: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, REPLAY_CASE_REQUIRED, "replay cases")
    out = df.copy()
    out["as_of_date"] = pd.to_datetime(out["as_of_date"]).dt.strftime("%Y-%m-%d")
    out["candidate_rank"] = pd.to_numeric(out["candidate_rank"], errors="raise")
    out["left_score"] = pd.to_numeric(out["left_score"], errors="coerce")
    out["symbol"] = out["symbol"].astype(str)
    if out["replay_id"].astype(str).duplicated().any():
        raise ValueError("replay cases replay_id must be unique.")
    if (out["candidate_rank"] <= 0).any():
        raise ValueError("replay cases candidate_rank must be positive.")
    out = out.sort_values(["as_of_date", "candidate_rank"], kind="stable").reset_index(drop=True)
    if max_cases is not None:
        if max_cases <= 0:
            raise ValueError("max_cases must be positive when provided.")
        out = out.head(max_cases).reset_index(drop=True)
    return out


class KronosHistoricalReplayPipeline:
    def __init__(self, adapter: KronosAdapter, config: ReplayPipelineConfig) -> None:
        self.adapter = adapter
        self.config = config

    def run(self) -> tuple[pd.DataFrame, dict[str, Any]]:
        cases_path = resolve_project_path(self.config.replay_cases_path, project_root=self.config.project_root)
        cases = read_replay_cases(cases_path, max_cases=self.config.max_cases)
        rows: list[dict[str, Any]] = []

        for _, replay_case in cases.iterrows():
            try:
                kline_path = resolve_project_path(replay_case["kline_path"], project_root=self.config.project_root)
                kline = read_kline_csv(kline_path)
                input_df, actual_future_df = split_kline_for_replay(
                    kline,
                    str(replay_case["as_of_date"]),
                    self.config.lookback,
                    self.config.pred_len,
                )
                last_close = float(input_df["close"].iloc[-1])
                prediction = self.adapter.predict(
                    input_df,
                    timestamp_col="timestamps",
                    x_timestamp=input_df["timestamps"],
                    y_timestamp=actual_future_df["timestamps"],
                    lookback=self.config.lookback,
                    pred_len=self.config.pred_len,
                    T=self.config.T,
                    top_p=self.config.top_p,
                    sample_count=self.config.sample_count,
                    verbose=False,
                )
                pred_df, metadata = self._unpack_prediction(prediction)
                prediction_summary = summarize_prediction_path(pred_df, last_close=last_close)
                actual_summary = summarize_actual_future_path(actual_future_df, last_close=last_close)
                comparison = compare_prediction_to_actual(prediction_summary, actual_summary)
                rows.append(
                    self._build_result_row(
                        replay_case,
                        model_status="PASS",
                        last_close=last_close,
                        metadata={**self._adapter_metadata(), **metadata},
                        prediction_summary=prediction_summary,
                        actual_summary=actual_summary,
                        comparison=comparison,
                    )
                )
            except Exception as exc:
                rows.append(
                    self._build_result_row(
                        replay_case,
                        model_status="FAIL",
                        error_message=str(exc),
                        metadata=self._adapter_metadata(),
                    )
                )

        replay_df = pd.DataFrame(rows)
        self._validate_result_fields(replay_df)
        metrics = aggregate_replay_metrics(replay_df)
        self._write_outputs(replay_df, metrics)
        return replay_df, metrics

    def _build_result_row(
        self,
        replay_case: pd.Series,
        *,
        model_status: str,
        error_message: str = "",
        last_close: float | None = None,
        metadata: dict[str, Any] | None = None,
        prediction_summary: dict[str, Any] | None = None,
        actual_summary: dict[str, Any] | None = None,
        comparison: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        prediction_summary = prediction_summary or {}
        actual_summary = actual_summary or {}
        comparison = comparison or {}
        row = {
            "replay_id": replay_case.get("replay_id"),
            "as_of_date": replay_case.get("as_of_date"),
            "symbol": replay_case.get("symbol"),
            "display_name": replay_case.get("display_name"),
            "candidate_rank": replay_case.get("candidate_rank"),
            "left_score": replay_case.get("left_score"),
            "model_name": metadata.get("model_name", pd.NA),
            "tokenizer_name": metadata.get("tokenizer_name", pd.NA),
            "device": metadata.get("device", pd.NA),
            "lookback": self.config.lookback,
            "pred_len": self.config.pred_len,
            "sample_count": self.config.sample_count,
            "last_close": last_close if last_close is not None else pd.NA,
            "pred_close_last": prediction_summary.get("pred_close_last", pd.NA),
            "actual_close_last": actual_summary.get("actual_close_last", pd.NA),
            "pred_return_last": comparison.get("pred_return_last", pd.NA),
            "actual_return_last": comparison.get("actual_return_last", pd.NA),
            "return_error": comparison.get("return_error", pd.NA),
            "abs_return_error": comparison.get("abs_return_error", pd.NA),
            "squared_return_error": comparison.get("squared_return_error", pd.NA),
            "pred_direction": comparison.get("pred_direction", pd.NA),
            "actual_direction": comparison.get("actual_direction", pd.NA),
            "direction_match": comparison.get("direction_match", pd.NA),
            "actual_close_min": actual_summary.get("actual_close_min", pd.NA),
            "actual_close_max": actual_summary.get("actual_close_max", pd.NA),
            "actual_range_pct": actual_summary.get("actual_range_pct", pd.NA),
            "model_status": model_status,
            "error_message": error_message,
        }
        return row

    def _adapter_metadata(self) -> dict[str, Any]:
        config = getattr(self.adapter, "config", None)
        if config is None:
            return {}
        return {
            "model_name": getattr(config, "model_name", pd.NA),
            "tokenizer_name": getattr(config, "tokenizer_name", pd.NA),
            "device": getattr(config, "device", pd.NA),
        }

    @staticmethod
    def _unpack_prediction(prediction: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
        if isinstance(prediction, KronosPredictionResult):
            return prediction.pred_df, prediction.metadata
        if isinstance(prediction, pd.DataFrame):
            return prediction, {}
        pred_df = getattr(prediction, "pred_df", None)
        if isinstance(pred_df, pd.DataFrame):
            metadata = getattr(prediction, "metadata", {})
            return pred_df, dict(metadata or {})
        raise ValueError("adapter.predict must return KronosPredictionResult or pandas DataFrame.")

    def _write_outputs(self, replay_df: pd.DataFrame, metrics: dict[str, Any]) -> None:
        predictions_path = resolve_project_path(
            self.config.output_predictions_path,
            project_root=self.config.project_root,
        )
        metrics_path = resolve_project_path(
            self.config.output_metrics_path,
            project_root=self.config.project_root,
        )
        predictions_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        replay_df.to_csv(predictions_path, index=False, encoding="utf-8-sig")
        pd.DataFrame([metrics]).to_csv(metrics_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def _validate_result_fields(replay_df: pd.DataFrame) -> None:
        forbidden = [
            col
            for col in replay_df.columns
            if any(term in col.lower() for term in FORBIDDEN_REPLAY_FIELD_TERMS)
        ]
        if forbidden:
            raise ValueError(f"replay result contains forbidden fields: {forbidden}")
