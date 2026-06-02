from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .validation import ETF_DAILY_K_REQUIRED, require_columns


@dataclass
class KronosConfig:
    model_name: str = "Kronos-small"
    tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-base"
    predictor_name: str = "NeoQuasar/Kronos-small"
    max_context: int = 512
    lookback: int = 240
    pred_len: int = 10
    sample_count: int = 3
    temperature: float = 1.0
    top_p: float = 0.9
    device: str = "cuda"
    external_repo_path: Path = Path("external/Kronos")


class KronosAdapter:
    """Adapter boundary around Kronos.

    V0.1 only provides the contract. V0.2 implements actual loading after
    external/Kronos and model weights are installed locally.
    """

    def __init__(self, config: KronosConfig | None = None) -> None:
        self.config = config or KronosConfig()
        self._predictor: Any | None = None

    def is_ready(self) -> bool:
        repo = Path(self.config.external_repo_path)
        return repo.exists() and any(repo.iterdir())

    def load(self) -> None:
        """Load tokenizer/model/predictor.

        Actual implementation belongs to V0.2 after Kronos dependencies are installed.
        """
        if not self.is_ready():
            raise RuntimeError(
                "Kronos repo is not installed. Finish V0.1 first, then clone "
                "https://github.com/shiyu-coder/Kronos into external/Kronos in V0.2."
            )
        raise NotImplementedError("V0.2: implement Kronos tokenizer/model loading here.")

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
