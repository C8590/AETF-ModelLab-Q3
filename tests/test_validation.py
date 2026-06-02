import pandas as pd

from model_lab.validation import validate_columns, assert_no_future_data


def test_validate_columns_ok():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = validate_columns(df, ["a", "b"], "demo")
    assert result.ok


def test_validate_columns_missing():
    df = pd.DataFrame({"a": [1]})
    result = validate_columns(df, ["a", "b"], "demo")
    assert not result.ok
    assert result.missing_columns == ["b"]


def test_assert_no_future_data():
    df = pd.DataFrame({"trade_date": ["2026-01-01", "2026-01-02"]})
    assert_no_future_data(df, "2026-01-02")
