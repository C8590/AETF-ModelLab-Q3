from pathlib import Path

import pandas as pd

from model_lab.kronos_adapter import (
    official_kronos_sample_path,
    resolve_kronos_root,
    validate_kronos_ohlcv_sample,
    write_markdown_report,
)


def test_kronos_path_resolution():
    root = Path(__file__).resolve().parents[1]
    assert resolve_kronos_root(root) == root / "external" / "Kronos"
    assert official_kronos_sample_path(root).name == "regression_input.csv"


def test_validate_kronos_ohlcv_sample_ok():
    df = pd.DataFrame(
        {
            "timestamps": pd.date_range("2024-01-01", periods=2, freq="1min"),
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.1, 1.2],
            "volume": [100.0, 110.0],
            "amount": [1000.0, 1200.0],
        }
    )
    validate_kronos_ohlcv_sample(df)


def test_write_markdown_report(tmp_path):
    out = tmp_path / "report.md"
    write_markdown_report(out, "Demo", ["- ok"])
    assert out.read_text(encoding="utf-8").startswith("# Demo")
