from pathlib import Path

import pandas as pd
import pytest

from model_lab.replay_metrics import (
    aggregate_replay_metrics,
    compare_prediction_to_actual,
    split_kline_for_replay,
    summarize_actual_future_path,
)


def make_kline(rows: int = 12) -> pd.DataFrame:
    closes = [10.0 + i * 0.1 for i in range(rows)]
    return pd.DataFrame(
        {
            "timestamps": pd.date_range("2026-01-01", periods=rows, freq="B"),
            "open": closes,
            "high": [v + 0.2 for v in closes],
            "low": [v - 0.2 for v in closes],
            "close": closes,
            "volume": [1000] * rows,
            "amount": [10000] * rows,
        }
    )


def test_split_kline_for_replay_prevents_lookahead():
    kline = make_kline()
    as_of_date = kline["timestamps"].iloc[5].strftime("%Y-%m-%d")

    input_df, actual_future_df = split_kline_for_replay(kline, as_of_date, lookback=4, pred_len=3)

    assert input_df["timestamps"].max() <= pd.Timestamp(as_of_date)
    assert actual_future_df["timestamps"].min() > pd.Timestamp(as_of_date)
    assert len(input_df) == 4
    assert len(actual_future_df) == 3


def test_split_kline_for_replay_history_short_raises():
    kline = make_kline()
    as_of_date = kline["timestamps"].iloc[2].strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="fewer than lookback"):
        split_kline_for_replay(kline, as_of_date, lookback=4, pred_len=3)


def test_split_kline_for_replay_future_short_raises():
    kline = make_kline()
    as_of_date = kline["timestamps"].iloc[-2].strftime("%Y-%m-%d")

    with pytest.raises(ValueError, match="fewer than pred_len"):
        split_kline_for_replay(kline, as_of_date, lookback=4, pred_len=3)


def test_summarize_actual_future_path_outputs_required_fields():
    actual = make_kline(5)

    summary = summarize_actual_future_path(actual, last_close=10.0)

    for field in [
        "actual_close_first",
        "actual_close_last",
        "actual_close_min",
        "actual_close_max",
        "actual_return_first",
        "actual_return_last",
        "actual_return_min",
        "actual_return_max",
        "actual_range_pct",
        "actual_close_volatility",
    ]:
        assert field in summary
    assert summary["actual_return_last"] == pytest.approx(0.04)


def test_compare_prediction_to_actual_outputs_error_and_direction_match():
    comparison = compare_prediction_to_actual(
        {"pred_return_last": 0.03},
        {"actual_return_last": 0.01},
    )

    assert comparison["return_error"] == pytest.approx(0.02)
    assert comparison["abs_return_error"] == pytest.approx(0.02)
    assert comparison["pred_direction"] == "UP"
    assert comparison["actual_direction"] == "UP"
    assert comparison["direction_match"] is True


def test_aggregate_replay_metrics_counts_and_errors():
    replay_df = pd.DataFrame(
        {
            "model_status": ["PASS", "PASS", "FAIL"],
            "direction_match": [True, False, pd.NA],
            "abs_return_error": [0.02, 0.04, pd.NA],
            "squared_return_error": [0.0004, 0.0016, pd.NA],
            "pred_return_last": [0.03, -0.01, pd.NA],
            "actual_return_last": [0.01, 0.02, pd.NA],
        }
    )

    metrics = aggregate_replay_metrics(replay_df)

    assert metrics["case_count"] == 3
    assert metrics["success_count"] == 2
    assert metrics["fail_count"] == 1
    assert metrics["direction_match_count"] == 1
    assert metrics["direction_accuracy"] == pytest.approx(0.5)
    assert metrics["mean_abs_return_error"] == pytest.approx(0.03)
