import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_reconstructed_candidate_history import build_reconstructed_history
from scripts.check_left_candidate_history import (
    FORBIDDEN_FIELD_PARTS,
    check_candidate_history,
    run,
)


def make_kline(path: Path, symbol: str = "510300", rows: int = 90) -> None:
    close = [10.0 + index * 0.1 for index in range(rows)]
    pd.DataFrame(
        {
            "timestamps": pd.date_range("2024-01-01", periods=rows, freq="D").strftime("%Y-%m-%d"),
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
            "source_name": ["unit_test"] * rows,
            "source_note": ["unit test"] * rows,
        }
    ).to_csv(path, index=False)


def make_candidate(path: Path, symbol: str = "510300", as_of_date: str = "2024-01-02") -> None:
    pd.DataFrame(
        {
            "as_of_date": [as_of_date],
            "symbol": [symbol],
            "display_name": ["ETF"],
            "candidate_rank": [1],
            "left_score": [0.5],
            "notes": ["real left snapshot export"],
        }
    ).to_csv(path, index=False)


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_FIELD_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)


def test_missing_left_candidate_history_returns_missing_status(tmp_path):
    result = run(
        candidate_path=tmp_path / "missing.csv",
        raw_kline_dir=tmp_path / "kline",
        report_path=tmp_path / "report.md",
    )

    assert result["candidate_history_status"] == "CANDIDATE_HISTORY_MISSING"
    assert (tmp_path / "report.md").exists()


def test_candidate_history_missing_columns_reports_schema_invalid(tmp_path):
    candidate = tmp_path / "left_candidates_history.csv"
    pd.DataFrame({"as_of_date": ["2024-01-01"]}).to_csv(candidate, index=False)

    result = check_candidate_history(candidate, tmp_path / "kline")

    assert result["candidate_history_status"] == "SCHEMA_INVALID"
    assert result["error_messages"]


def test_candidate_history_accepts_parseable_dates(tmp_path):
    kline_dir = tmp_path / "kline"
    kline_dir.mkdir()
    make_kline(kline_dir / "510300.csv")
    candidate = tmp_path / "left_candidates_history.csv"
    make_candidate(candidate, as_of_date="2024-01-02")

    result = check_candidate_history(candidate, kline_dir)

    assert result["candidate_history_status"] == "PASS"
    assert result["candidate_date_count"] == 1
    assert result["min_as_of_date"] == "2024-01-02"


def test_candidate_history_unparseable_dates_fail(tmp_path):
    kline_dir = tmp_path / "kline"
    kline_dir.mkdir()
    make_kline(kline_dir / "510300.csv")
    candidate = tmp_path / "left_candidates_history.csv"
    make_candidate(candidate, as_of_date="not-a-date")

    result = check_candidate_history(candidate, kline_dir)

    assert result["candidate_history_status"] == "CHECK_FAILED"
    assert "as_of_date" in result["error_messages"][0]


def test_candidate_history_symbol_must_match_kline_file(tmp_path):
    kline_dir = tmp_path / "kline"
    kline_dir.mkdir()
    make_kline(kline_dir / "510300.csv")
    candidate = tmp_path / "left_candidates_history.csv"
    make_candidate(candidate, symbol="159915")

    result = check_candidate_history(candidate, kline_dir)

    assert result["candidate_history_status"] == "CHECK_FAILED"
    assert "symbols missing raw kline CSV" in " ".join(result["error_messages"])


def test_check_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.check_left_candidate_history")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def test_reconstructed_script_refuses_to_overwrite_real_left_candidate_history(tmp_path, monkeypatch):
    raw_kline_dir = tmp_path / "kline"
    raw_kline_dir.mkdir()
    make_kline(raw_kline_dir / "510300.csv")
    real_candidate = tmp_path / "left_candidates_history.csv"
    real_candidate.write_text("real\n", encoding="utf-8")

    module = importlib.import_module("scripts.build_reconstructed_candidate_history")
    monkeypatch.setattr(module, "REAL_CANDIDATE_PATH", real_candidate)

    with pytest.raises(FileExistsError):
        module.build_reconstructed_history(raw_kline_dir, tmp_path / "left_candidates_history_RECONSTRUCTED.csv")


def test_reconstructed_script_refuses_left_candidate_history_output(tmp_path, monkeypatch):
    raw_kline_dir = tmp_path / "kline"
    raw_kline_dir.mkdir()
    make_kline(raw_kline_dir / "510300.csv")
    module = importlib.import_module("scripts.build_reconstructed_candidate_history")
    monkeypatch.setattr(module, "REAL_CANDIDATE_PATH", tmp_path / "missing_real.csv")

    with pytest.raises(ValueError):
        build_reconstructed_history(raw_kline_dir, tmp_path / "left_candidates_history.csv")


def test_candidate_history_result_keys_do_not_contain_forbidden_terms(tmp_path):
    result = run(
        candidate_path=tmp_path / "missing.csv",
        raw_kline_dir=tmp_path / "kline",
        report_path=tmp_path / "report.md",
    )

    assert_no_forbidden_keys(json.loads(json.dumps(result)))
