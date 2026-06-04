import importlib
import json

import pandas as pd
import pytest

from model_lab.reconstructed_replay_expansion import (
    FORBIDDEN_KEY_PARTS,
    RECONSTRUCTED_NOTE,
    append_predictions,
    build_expanded_summary,
    compute_expanded_group_metrics,
    load_reconstructed_replay_cases,
    select_cases_for_expansion,
)


def make_cases(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "replay_id": [f"case_{index}" for index in range(rows)],
            "as_of_date": pd.date_range("2024-01-01", periods=rows, freq="D").strftime("%Y-%m-%d"),
            "symbol": ["510300", "510500", "159915"][:rows],
            "display_name": ["ETF"] * rows,
            "candidate_rank": [1, 2, 3][:rows],
            "left_score": [0.7, 0.6, 0.5][:rows],
            "kline_path": [f"data/real/normalized/kline/{symbol}.csv" for symbol in ["510300", "510500", "159915"][:rows]],
            "notes": [RECONSTRUCTED_NOTE] * rows,
        }
    )


def make_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "replay_id": ["case_0", "case_1", "case_2"],
            "as_of_date": ["2024-01-01", "2024-01-15", "2024-02-01"],
            "symbol": ["510300", "510300", "510500"],
            "candidate_rank": [1, 2, 1],
            "model_status": ["PASS", "PASS", "FAIL"],
            "direction_match": [True, False, ""],
            "abs_return_error": [0.1, 0.2, None],
            "squared_return_error": [0.01, 0.04, None],
            "error_message": ["", "", "unit failure"],
        }
    )


def test_load_reconstructed_replay_cases_requires_reconstructed_note(tmp_path):
    path = tmp_path / "cases.csv"
    df = make_cases()
    df.loc[0, "notes"] = "missing marker"
    df.to_csv(path, index=False)

    with pytest.raises(ValueError, match="reconstructed marker"):
        load_reconstructed_replay_cases(path)


def test_select_cases_for_expansion_excludes_completed_replay_ids():
    selected = select_cases_for_expansion(make_cases(), {"case_1"}, max_cases=10)

    assert selected["replay_id"].tolist() == ["case_0", "case_2"]


def test_select_cases_for_expansion_supports_max_cases_none():
    selected = select_cases_for_expansion(make_cases(), set(), max_cases=None)

    assert len(selected) == 3


def test_append_predictions_does_not_duplicate_replay_id(tmp_path):
    path = tmp_path / "predictions.csv"
    append_predictions(path, make_predictions().head(2))
    append_predictions(path, make_predictions().iloc[1:])

    saved = pd.read_csv(path)
    assert saved["replay_id"].tolist() == ["case_0", "case_1", "case_2"]


def test_compute_expanded_group_metrics_generates_by_symbol():
    metrics = compute_expanded_group_metrics(make_predictions())

    assert {row["symbol"] for row in metrics["by_symbol"]} == {"510300", "510500"}


def test_compute_expanded_group_metrics_generates_by_candidate_rank():
    metrics = compute_expanded_group_metrics(make_predictions())

    assert {row["candidate_rank"] for row in metrics["by_candidate_rank"]} == {"1", "2"}


def test_compute_expanded_group_metrics_generates_by_month():
    metrics = compute_expanded_group_metrics(make_predictions())

    assert {row["month"] for row in metrics["by_month"]} == {"2024-01", "2024-02"}


def test_build_expanded_summary_blocks_formal_v011_and_marks_zero_shot():
    summary = build_expanded_summary(
        make_predictions(),
        {
            "case_count": 3,
            "success_count": 2,
            "fail_count": 1,
            "direction_accuracy": 0.5,
            "mean_abs_return_error": 0.15,
            "median_abs_return_error": 0.15,
            "rmse_return_error": 0.18,
        },
        {"direction_accuracy": 0.55, "evaluated_case_count": 200},
        {"runtime": {"total_available_cases": 3}},
    )

    assert summary["formal_v011_ready"] is False
    assert summary["zero_shot"] is True


def test_expanded_summary_keys_do_not_contain_forbidden_terms():
    summary = build_expanded_summary(
        make_predictions(),
        {
            "case_count": 3,
            "success_count": 2,
            "fail_count": 1,
            "direction_accuracy": 0.5,
            "mean_abs_return_error": 0.15,
            "median_abs_return_error": 0.15,
            "rmse_return_error": 0.18,
        },
        None,
        {"runtime": {"total_available_cases": 3}},
    )

    assert_no_forbidden_keys(json.loads(json.dumps(summary)))


def test_run_kronos_reconstructed_replay_full_import_has_no_side_effects():
    module = importlib.import_module("scripts.run_kronos_reconstructed_replay_full")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_KEY_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)
