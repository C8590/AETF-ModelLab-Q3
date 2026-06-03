from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .data_loader import read_candidate_snapshot, read_kline_csv
from .kronos_adapter import KronosPredictionResult
from .shadow_features import build_shadow_observation_row, summarize_prediction_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path, *, project_root: Path = PROJECT_ROOT) -> Path:
    value = Path(path)
    return value if value.is_absolute() else project_root / value


def future_business_timestamps(last_timestamp: Any, pred_len: int) -> pd.Series:
    if pred_len <= 0:
        raise ValueError("pred_len must be positive.")
    start = pd.to_datetime(last_timestamp) + pd.offsets.BDay(1)
    return pd.Series(pd.bdate_range(start=start, periods=pred_len), name="timestamps")


class KronosShadowPipeline:
    """Run shadow-only Kronos path observations for a candidate snapshot."""

    def __init__(self, adapter: Any, *, project_root: str | Path | None = None) -> None:
        self.adapter = adapter
        self.project_root = Path(project_root) if project_root is not None else PROJECT_ROOT

    def run_candidate_shadow_predictions(
        self,
        *,
        candidate_snapshot_path: str | Path,
        output_csv_path: str | Path | None = None,
        lookback: int,
        pred_len: int,
        sample_count: int,
        T: float,
        top_p: float,
        max_candidates: int | None = None,
    ) -> pd.DataFrame:
        snapshot_path = resolve_project_path(candidate_snapshot_path, project_root=self.project_root)
        candidates = read_candidate_snapshot(snapshot_path, max_candidates=max_candidates)

        rows: list[dict[str, Any]] = []
        for _, candidate in candidates.iterrows():
            try:
                kline_path = resolve_project_path(candidate["kline_csv_path"], project_root=self.project_root)
                kline = read_kline_csv(kline_path)
                if len(kline) < lookback:
                    raise ValueError(f"kline rows are fewer than lookback: {len(kline)} < {lookback}")

                y_timestamp = future_business_timestamps(kline["timestamps"].iloc[-1], pred_len)
                prediction = self.adapter.predict(
                    kline,
                    timestamp_col="timestamps",
                    x_timestamp=kline["timestamps"],
                    y_timestamp=y_timestamp,
                    lookback=lookback,
                    pred_len=pred_len,
                    T=T,
                    top_p=top_p,
                    sample_count=sample_count,
                    verbose=False,
                )
                pred_df, metadata = self._unpack_prediction(prediction)
                metadata = {
                    **self._adapter_metadata(),
                    **metadata,
                    "lookback": lookback,
                    "pred_len": pred_len,
                    "sample_count": sample_count,
                }
                summary = summarize_prediction_path(pred_df, last_close=float(candidate["close"]))
                rows.append(
                    build_shadow_observation_row(
                        candidate,
                        summary=summary,
                        model_status="PASS",
                        metadata=metadata,
                    )
                )
            except Exception as exc:
                metadata = {
                    **self._adapter_metadata(),
                    "lookback": lookback,
                    "pred_len": pred_len,
                    "sample_count": sample_count,
                }
                rows.append(
                    build_shadow_observation_row(
                        candidate,
                        model_status="FAIL",
                        error_message=str(exc),
                        metadata=metadata,
                    )
                )

        output = pd.DataFrame(rows)
        if output_csv_path is not None:
            out_path = resolve_project_path(output_csv_path, project_root=self.project_root)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            output.to_csv(out_path, index=False, encoding="utf-8-sig")
        return output

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
