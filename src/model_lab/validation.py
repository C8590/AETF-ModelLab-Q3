from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


ETF_DAILY_K_REQUIRED = [
    "trade_date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
]

LEFT_CANDIDATES_MIN_REQUIRED = ["trade_date", "code", "close"]
KRONOS_FORECAST_REQUIRED = ["trade_date", "code", "pred_date", "pred_close", "pred_low", "pred_high"]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    missing_columns: list[str]
    message: str


def validate_columns(df: pd.DataFrame, required: Iterable[str], name: str = "dataframe") -> ValidationResult:
    required_list = list(required)
    missing = [col for col in required_list if col not in df.columns]
    if missing:
        return ValidationResult(False, missing, f"{name} missing columns: {missing}")
    return ValidationResult(True, [], f"{name} columns OK")


def require_columns(df: pd.DataFrame, required: Iterable[str], name: str = "dataframe") -> None:
    result = validate_columns(df, required, name)
    if not result.ok:
        raise ValueError(result.message)


def normalize_trade_date(df: pd.DataFrame, column: str = "trade_date") -> pd.DataFrame:
    if column not in df.columns:
        return df
    out = df.copy()
    out[column] = pd.to_datetime(out[column]).dt.strftime("%Y-%m-%d")
    return out


def assert_no_future_data(history: pd.DataFrame, as_of_date: str, date_col: str = "trade_date") -> None:
    """Raise if history includes rows after as_of_date."""
    if date_col not in history.columns or history.empty:
        return
    max_date = pd.to_datetime(history[date_col]).max()
    cutoff = pd.to_datetime(as_of_date)
    if max_date > cutoff:
        raise ValueError(f"Future data leakage: max {date_col}={max_date.date()} > as_of_date={cutoff.date()}")
