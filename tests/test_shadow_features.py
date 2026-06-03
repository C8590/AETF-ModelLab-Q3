import pandas as pd
import pytest

from model_lab.shadow_features import build_shadow_observation_row, summarize_prediction_path


def prediction_path() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamps": pd.date_range("2026-06-04", periods=5, freq="B"),
            "open": [10.0, 10.1, 10.2, 10.3, 10.4],
            "high": [10.2, 10.3, 10.4, 10.5, 10.6],
            "low": [9.9, 10.0, 10.1, 10.2, 10.3],
            "close": [10.1, 10.2, 10.3, 10.4, 10.5],
        }
    )


def test_summarize_prediction_path_outputs_required_fields():
    summary = summarize_prediction_path(prediction_path(), last_close=10.0)

    for field in [
        "path_len",
        "last_close",
        "pred_close_1",
        "pred_close_3",
        "pred_close_5",
        "pred_return_5",
        "pred_low_min",
        "pred_high_max",
        "pred_drawdown_min",
    ]:
        assert field in summary
    assert summary["path_len"] == 5
    assert summary["pred_return_5"] == pytest.approx(0.05)


def test_summarize_prediction_path_last_close_must_be_positive():
    with pytest.raises(ValueError, match="last_close must be positive"):
        summarize_prediction_path(prediction_path(), last_close=0)


def test_build_shadow_observation_row_has_no_trading_semantic_fields():
    row = build_shadow_observation_row(
        {
            "trade_date": "2026-06-03",
            "candidate_rank": 1,
            "code": "510300",
            "name": "沪深300ETF",
            "close": 4.0,
        },
        summary={"path_len": 5, "pred_return_last": 0.01},
        model_status="PASS",
        metadata={"model_name": "demo", "tokenizer_name": "tok"},
    )

    lowered = " ".join(row.keys()).lower()
    for forbidden in ["buy", "sell", "order", "trade"]:
        assert forbidden not in lowered
    assert row["as_of_date"] == "2026-06-03"
    assert row["model_status"] == "PASS"
