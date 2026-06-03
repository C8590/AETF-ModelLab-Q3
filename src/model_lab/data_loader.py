from __future__ import annotations

from pathlib import Path

import pandas as pd

from .validation import (
    ETF_DAILY_K_REQUIRED,
    LEFT_CANDIDATES_MIN_REQUIRED,
    normalize_trade_date,
    require_columns,
)

CANDIDATE_SNAPSHOT_REQUIRED = [
    "candidate_rank",
    "trade_date",
    "code",
    "name",
    "close",
    "kline_csv_path",
]

KLINE_REQUIRED = [
    "timestamps",
    "open",
    "high",
    "low",
    "close",
]


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


def read_candidate_snapshot(path: str | Path, *, max_candidates: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, CANDIDATE_SNAPSHOT_REQUIRED, "candidate snapshot")
    out = normalize_trade_date(df, "trade_date")
    out["candidate_rank"] = pd.to_numeric(out["candidate_rank"], errors="raise")
    out["close"] = pd.to_numeric(out["close"], errors="raise")
    out["code"] = out["code"].astype(str)
    if (out["candidate_rank"] <= 0).any():
        raise ValueError("candidate snapshot candidate_rank must be positive.")
    if (out["close"] <= 0).any():
        raise ValueError("candidate snapshot close must be positive.")
    out = out.sort_values("candidate_rank", kind="stable").reset_index(drop=True)
    if max_candidates is not None:
        if max_candidates <= 0:
            raise ValueError("max_candidates must be positive when provided.")
        out = out.head(max_candidates).reset_index(drop=True)
    return out


def read_kline_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, KLINE_REQUIRED, "kline CSV")
    out = df.copy()
    out["timestamps"] = pd.to_datetime(out["timestamps"])
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    for col in numeric_columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="raise")
    if out[KLINE_REQUIRED].isnull().values.any():
        raise ValueError("kline CSV contains NaN values in required columns.")
    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("kline CSV OHLC values must be positive.")
    out = out.sort_values("timestamps", kind="stable").reset_index(drop=True)
    return out


def get_history_until(etf_daily_k: pd.DataFrame, code: str, as_of_date: str, lookback: int) -> pd.DataFrame:
    df = etf_daily_k[(etf_daily_k["code"].astype(str) == str(code)) & (pd.to_datetime(etf_daily_k["trade_date"]) <= pd.to_datetime(as_of_date))]
    df = df.sort_values("trade_date").tail(lookback).reset_index(drop=True)
    return df
