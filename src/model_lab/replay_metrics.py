from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def split_kline_for_replay(
    kline_df: pd.DataFrame,
    as_of_date: str,
    lookback: int,
    pred_len: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if lookback <= 0:
        raise ValueError("lookback must be positive.")
    if pred_len <= 0:
        raise ValueError("pred_len must be positive.")
    if "timestamps" not in kline_df.columns:
        raise ValueError("kline_df missing columns: ['timestamps']")

    working = kline_df.copy()
    working["timestamps"] = pd.to_datetime(working["timestamps"])
    working = working.sort_values("timestamps", kind="stable").reset_index(drop=True)
    cutoff = pd.to_datetime(as_of_date)

    history = working[working["timestamps"] <= cutoff].copy()
    future = working[working["timestamps"] > cutoff].copy()

    if len(history) < lookback:
        raise ValueError(f"historical rows before as_of_date are fewer than lookback: {len(history)} < {lookback}")
    if len(future) < pred_len:
        raise ValueError(f"future rows after as_of_date are fewer than pred_len: {len(future)} < {pred_len}")

    input_df = history.tail(lookback).reset_index(drop=True)
    actual_future_df = future.head(pred_len).reset_index(drop=True)
    if input_df["timestamps"].max() > cutoff:
        raise ValueError("lookahead detected: input window contains data after as_of_date.")
    if actual_future_df["timestamps"].min() <= cutoff:
        raise ValueError("replay split error: actual future window contains data on or before as_of_date.")
    return input_df, actual_future_df


def summarize_actual_future_path(actual_df: pd.DataFrame, last_close: float) -> dict[str, float | int]:
    if last_close <= 0:
        raise ValueError("last_close must be positive.")
    if actual_df.empty:
        raise ValueError("actual_df must not be empty.")
    if "close" not in actual_df.columns:
        raise ValueError("actual_df missing columns: ['close']")

    closes = pd.to_numeric(actual_df["close"], errors="coerce").dropna().reset_index(drop=True)
    if closes.empty:
        raise ValueError("actual_df close values are empty after numeric conversion.")
    returns = closes / float(last_close) - 1.0

    return {
        "actual_path_len": int(len(closes)),
        "actual_close_first": float(closes.iloc[0]),
        "actual_close_last": float(closes.iloc[-1]),
        "actual_close_min": float(closes.min()),
        "actual_close_max": float(closes.max()),
        "actual_return_first": float(returns.iloc[0]),
        "actual_return_last": float(returns.iloc[-1]),
        "actual_return_min": float(returns.min()),
        "actual_return_max": float(returns.max()),
        "actual_range_pct": float((closes.max() - closes.min()) / float(last_close)),
        "actual_close_volatility": float(closes.std(ddof=0)) if len(closes) > 1 else 0.0,
    }


def direction_label(value: Any, *, threshold: float = 1e-12) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric) or abs(float(numeric)) <= threshold:
        return "FLAT"
    return "UP" if float(numeric) > 0 else "DOWN"


def compare_prediction_to_actual(prediction_summary: dict[str, Any], actual_summary: dict[str, Any]) -> dict[str, Any]:
    pred_return_last = float(prediction_summary.get("pred_return_last", np.nan))
    actual_return_last = float(actual_summary.get("actual_return_last", np.nan))
    return_error = pred_return_last - actual_return_last
    pred_direction = direction_label(pred_return_last)
    actual_direction = direction_label(actual_return_last)
    return {
        "pred_return_last": pred_return_last,
        "actual_return_last": actual_return_last,
        "return_error": float(return_error),
        "abs_return_error": float(abs(return_error)),
        "squared_return_error": float(return_error * return_error),
        "pred_direction": pred_direction,
        "actual_direction": actual_direction,
        "direction_match": bool(pred_direction == actual_direction),
    }


def aggregate_replay_metrics(replay_df: pd.DataFrame) -> dict[str, Any]:
    case_count = int(len(replay_df))
    status = replay_df.get("model_status", pd.Series(dtype=str)).astype(str)
    success_mask = status == "PASS"
    fail_mask = status == "FAIL"
    success_count = int(success_mask.sum())
    fail_count = int(fail_mask.sum())
    successful = replay_df[success_mask].copy()

    direction_match = successful.get("direction_match", pd.Series(dtype=bool))
    direction_match_count = int(sum(True for value in direction_match if value is True))
    direction_accuracy = (
        float(direction_match_count / success_count)
        if success_count > 0
        else float("nan")
    )

    abs_errors = pd.to_numeric(successful.get("abs_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
    squared_errors = pd.to_numeric(successful.get("squared_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
    pred_returns = pd.to_numeric(successful.get("pred_return_last", pd.Series(dtype=float)), errors="coerce").dropna()
    actual_returns = pd.to_numeric(successful.get("actual_return_last", pd.Series(dtype=float)), errors="coerce").dropna()

    return {
        "case_count": case_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "direction_match_count": direction_match_count,
        "direction_accuracy": direction_accuracy,
        "mean_abs_return_error": float(abs_errors.mean()) if not abs_errors.empty else float("nan"),
        "median_abs_return_error": float(abs_errors.median()) if not abs_errors.empty else float("nan"),
        "rmse_return_error": float(math.sqrt(squared_errors.mean())) if not squared_errors.empty else float("nan"),
        "mean_pred_return_last": float(pred_returns.mean()) if not pred_returns.empty else float("nan"),
        "mean_actual_return_last": float(actual_returns.mean()) if not actual_returns.empty else float("nan"),
    }
