import importlib
import json

import pandas as pd
import pytest

from model_lab.real_data_prep import (
    FORBIDDEN_RESULT_KEY_PARTS,
    RealDataPrepConfig,
    build_expanded_replay_cases,
    discover_raw_kline_files,
    evaluate_real_data_readiness,
    normalize_kline_df,
    normalized_kline_path,
    profile_kline_df,
    validate_candidate_history,
    validate_raw_kline_schema,
    write_json,
)


def make_kline(rows: int = 8, symbol: str = "510300") -> pd.DataFrame:
    close = [10.0 + index * 0.1 for index in range(rows)]
    return pd.DataFrame(
        {
            "timestamps": pd.date_range("2024-01-01", periods=rows, freq="D"),
            "open": close,
            "high": [value + 0.2 for value in close],
            "low": [value - 0.2 for value in close],
            "close": close,
            "volume": [1000] * rows,
            "amount": [10000] * rows,
            "symbol": [symbol] * rows,
            "display_name": ["ETF"] * rows,
            "market": ["SH"] * rows,
            "frequency": ["daily"] * rows,
            "price_adjustment": ["qfq"] * rows,
            "source_name": ["local_export"] * rows,
            "source_note": ["unit test"] * rows,
        }
    )


def make_candidate_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "as_of_date": ["2024-01-04", "2024-01-07"],
            "symbol": ["510300", "510300"],
            "display_name": ["ETF", "ETF"],
            "candidate_rank": [1, 1],
            "left_score": [0.5, 0.6],
            "notes": ["first", "second"],
        }
    )


def test_discover_raw_kline_files_missing_dir_returns_empty(tmp_path):
    assert discover_raw_kline_files(tmp_path / "missing") == []


def test_validate_raw_kline_schema_reports_missing_columns(tmp_path):
    errors = validate_raw_kline_schema(pd.DataFrame({"timestamps": ["2024-01-01"]}), tmp_path / "bad.csv")

    assert errors


def test_normalize_kline_df_sorts_by_timestamps(tmp_path):
    df = make_kline().sample(frac=1, random_state=10).reset_index(drop=True)

    normalized = normalize_kline_df(df, tmp_path / "kline.csv")

    assert normalized["timestamps"].tolist() == sorted(normalized["timestamps"].tolist())


def test_normalize_kline_df_rejects_invalid_ohlc(tmp_path):
    df = make_kline()
    df.loc[0, "high"] = df.loc[0, "close"] - 0.1

    with pytest.raises(ValueError, match="high"):
        normalize_kline_df(df, tmp_path / "bad_ohlc.csv")


def test_profile_kline_df_outputs_core_fields(tmp_path):
    profile = profile_kline_df(make_kline(), tmp_path / "kline.csv")

    assert profile["symbol"] == "510300"
    assert profile["bar_count"] == 8
    assert profile["start_date"] == "2024-01-01"
    assert profile["end_date"] == "2024-01-08"


def test_validate_candidate_history_reports_missing_columns():
    errors = validate_candidate_history(pd.DataFrame({"as_of_date": ["2024-01-01"]}))

    assert errors


def test_build_expanded_replay_cases_requires_lookback_and_pred_len(tmp_path):
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    normalized = normalize_kline_df(make_kline(rows=8), tmp_path / "raw.csv")
    normalized.to_csv(normalized_kline_path(normalized_dir, "510300"), index=False)
    profile_df = pd.DataFrame([profile_kline_df(normalized, normalized_dir / "510300.csv")])

    cases = build_expanded_replay_cases(
        make_candidate_history(),
        profile_df,
        normalized_dir,
        RealDataPrepConfig(lookback=4, pred_len=2, max_cases=None),
    )

    assert cases["replay_id"].tolist() == ["2024-01-04_510300"]


def test_build_expanded_replay_cases_uses_normalized_dir_paths(tmp_path):
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    normalized = normalize_kline_df(make_kline(rows=8), tmp_path / "raw.csv")
    normalized.to_csv(normalized_kline_path(normalized_dir, "510300"), index=False)
    profile_df = pd.DataFrame([profile_kline_df(normalized, normalized_dir / "510300.csv")])

    cases = build_expanded_replay_cases(
        make_candidate_history().head(1),
        profile_df,
        normalized_dir,
        RealDataPrepConfig(lookback=4, pred_len=2),
    )

    assert str(normalized_dir.as_posix()) in cases["kline_path"].iloc[0]


def test_evaluate_real_data_readiness_without_kline_is_not_ready():
    readiness = evaluate_real_data_readiness(
        pd.DataFrame(),
        pd.DataFrame(),
        None,
        RealDataPrepConfig(),
    )

    assert readiness["data_status"] in {"KLINE_DATA_MISSING", "DATA_NOT_READY"}
    assert readiness["is_ready_for_expanded_replay"] is False


def test_evaluate_real_data_readiness_rejects_insufficient_cases():
    profile_df = pd.DataFrame(
        [
            {
                "symbol": "510300",
                "display_name": "ETF",
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "bar_count": 1001,
                "missing_rate": 0.0,
                "duplicate_timestamp_count": 0,
                "price_adjustment": "qfq",
                "frequency": "daily",
                "source_name": "local_export",
                "status": "PASS",
                "errors": "",
            }
        ]
    )

    readiness = evaluate_real_data_readiness(
        profile_df,
        pd.DataFrame({"replay_id": ["case_1"]}),
        make_candidate_history(),
        RealDataPrepConfig(min_symbols=1, min_replay_cases=2, min_candidate_dates=1),
    )

    assert readiness["is_ready_for_expanded_replay"] is False


def test_output_keys_do_not_contain_forbidden_terms(tmp_path):
    readiness = evaluate_real_data_readiness(pd.DataFrame(), pd.DataFrame(), None, RealDataPrepConfig())
    output_path = tmp_path / "readiness.json"

    write_json(readiness, output_path)

    assert_no_forbidden_keys(json.loads(output_path.read_text(encoding="utf-8")))


def test_prepare_real_etf_dataset_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.prepare_real_etf_dataset")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_RESULT_KEY_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)
