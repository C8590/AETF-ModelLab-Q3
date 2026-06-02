from pathlib import Path

import pandas as pd
import pytest

from model_lab.kronos_adapter import (
    KronosAdapter,
    KronosAdapterConfig,
    KronosPredictionResult,
    official_kronos_sample_path,
    resolve_kronos_root,
    validate_kronos_ohlcv_sample,
    write_markdown_report,
)


class FakePredictor:
    device = "cuda:0"

    def predict(self, df, x_timestamp, y_timestamp, pred_len, T, top_k, top_p, sample_count, verbose):
        assert len(df) == len(x_timestamp)
        assert len(y_timestamp) == pred_len
        return pd.DataFrame(
            {
                "open": [1.0] * pred_len,
                "high": [1.1] * pred_len,
                "low": [0.9] * pred_len,
                "close": [1.05] * pred_len,
                "volume": [0.0] * pred_len,
                "amount": [0.0] * pred_len,
            }
        )


def sample_df(rows: int = 8, include_optional: bool = True) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "timestamps": pd.date_range("2024-01-01", periods=rows, freq="1min"),
            "open": [1.0] * rows,
            "high": [1.2] * rows,
            "low": [0.9] * rows,
            "close": [1.1] * rows,
        }
    )
    if include_optional:
        df["volume"] = [100.0] * rows
        df["amount"] = [1000.0] * rows
    return df


def test_kronos_adapter_config_defaults():
    cfg = KronosAdapterConfig()
    assert cfg.model_name == "NeoQuasar/Kronos-small"
    assert cfg.tokenizer_name == "NeoQuasar/Kronos-Tokenizer-base"
    assert cfg.device == "cuda:0"
    assert cfg.max_context == 512
    assert cfg.default_lookback == 400
    assert cfg.default_pred_len == 120
    assert cfg.default_sample_count == 1


def test_kronos_path_resolution():
    root = Path(__file__).resolve().parents[1]
    assert resolve_kronos_root(root) == root / "external" / "Kronos"
    assert official_kronos_sample_path(root).name == "regression_input.csv"


def test_required_ohlc_missing_raises():
    adapter = KronosAdapter(KronosAdapterConfig(default_lookback=3, default_pred_len=2))
    df = sample_df().drop(columns=["close"])
    with pytest.raises(ValueError, match="missing columns"):
        adapter.prepare_prediction_input(df)


def test_missing_volume_amount_filled_with_zero():
    adapter = KronosAdapter(KronosAdapterConfig(default_lookback=3, default_pred_len=2))
    prepared = adapter.prepare_prediction_input(sample_df(include_optional=False))
    assert prepared.filled_optional_columns == ["volume", "amount"]
    assert prepared.x_df["volume"].eq(0.0).all()
    assert prepared.x_df["amount"].eq(0.0).all()


def test_timestamp_col_missing_raises():
    adapter = KronosAdapter(KronosAdapterConfig(default_lookback=3, default_pred_len=2))
    df = sample_df().drop(columns=["timestamps"])
    with pytest.raises(ValueError, match="timestamp"):
        adapter.prepare_prediction_input(df)


def test_lookback_plus_pred_len_overflow_raises():
    adapter = KronosAdapter(KronosAdapterConfig(default_lookback=7, default_pred_len=4))
    with pytest.raises(ValueError, match="lookback \\+ pred_len"):
        adapter.prepare_prediction_input(sample_df(rows=8))


def test_predict_metadata_has_no_trading_advice_fields():
    adapter = KronosAdapter(KronosAdapterConfig(default_lookback=3, default_pred_len=2))
    adapter._predictor = FakePredictor()
    result = adapter.predict(sample_df(), verbose=False)
    assert isinstance(result, KronosPredictionResult)
    assert result.metadata["success"] is True
    forbidden = {"trade_signal", "buy", "sell", "target_price", "stop_loss", "order"}
    assert forbidden.isdisjoint(result.metadata)


def test_run_kronos_sample_import_has_no_side_effects():
    import scripts.run_kronos_sample as sample_script

    assert callable(sample_script.main)


def test_validate_kronos_ohlcv_sample_ok():
    validate_kronos_ohlcv_sample(sample_df())


def test_write_markdown_report(tmp_path):
    out = tmp_path / "report.md"
    write_markdown_report(out, "Demo", ["- ok"])
    assert out.read_text(encoding="utf-8").startswith("# Demo")
