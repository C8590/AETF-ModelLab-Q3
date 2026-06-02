from __future__ import annotations

from pathlib import Path

import pandas as pd

from .validation import (
    ETF_DAILY_K_REQUIRED,
    LEFT_CANDIDATES_MIN_REQUIRED,
    normalize_trade_date,
    require_columns,
)


def read_csv_if_exists(path: str | Path, *, required: bool = False) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"CSV not found: {p}")
        return pd.DataFrame()
    return pd.read_csv(p)


def read_etf_daily_k(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, ETF_DAILY_K_REQUIRED, "ETF daily K")
    df = normalize_trade_date(df, "trade_date")
    df = df.sort_values(["code", "trade_date"]).reset_index(drop=True)
    return df


def read_left_candidates(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, LEFT_CANDIDATES_MIN_REQUIRED, "left candidates")
    df = normalize_trade_date(df, "trade_date")
    return df


def get_history_until(etf_daily_k: pd.DataFrame, code: str, as_of_date: str, lookback: int) -> pd.DataFrame:
    df = etf_daily_k[(etf_daily_k["code"].astype(str) == str(code)) & (pd.to_datetime(etf_daily_k["trade_date"]) <= pd.to_datetime(as_of_date))]
    df = df.sort_values("trade_date").tail(lookback).reset_index(drop=True)
    return df
