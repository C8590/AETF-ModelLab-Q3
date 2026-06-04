import importlib
import json

import pandas as pd
import pytest

from model_lab.reconstructed_replay_summary import (
    FORBIDDEN_KEY_PARTS,
    build_reconstructed_replay_summary,
    compute_group_metrics,
    validate_reconstructed_replay_inputs,
)


def write_readiness(path, **overrides):
    data = {
        "candidate_history_type": "reconstructed_not_true_left_snapshot",
        "can_enter_formal_v011": False,
        "can_enter_v011_reconstructed": True,
        "replay_case_count": 200,
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_cases(path, rows: int = 200):
    pd.DataFrame(
        {
            "replay_id": [f"case_{index}" for index in range(rows)],
            "as_of_date": ["2024-01-01"] * rows,
            "symbol": ["510300"] * rows,
            "display_name": ["ETF"] * rows,
            "candidate_rank": [1] * rows,
            "left_score": [0.5] * rows,
            "kline_path": ["data/real/normalized/kline/510300.csv"] * rows,
            "notes": ["reconstructed"] * rows,
        }
    ).to_csv(path, index=False)


def test_validate_reconstructed_replay_inputs_rejects_formal_v011_true(tmp_path):
    cases = tmp_path / "cases.csv"
    readiness = tmp_path / "readiness.json"
    write_cases(cases)
    write_readiness(readiness, can_enter_formal_v011=True)

    with pytest.raises(ValueError, match="formal V0.11"):
        validate_reconstructed_replay_inputs(cases, readiness)


def test_validate_reconstructed_replay_inputs_rejects_wrong_history_type(tmp_path):
    cases = tmp_path / "cases.csv"
    readiness = tmp_path / "readiness.json"
    write_cases(cases)
    write_readiness(readiness, candidate_history_type="true_left_snapshot")

    with pytest.raises(ValueError, match="candidate_history_type"):
        validate_reconstructed_replay_inputs(cases, readiness)


def test_validate_reconstructed_replay_inputs_rejects_small_replay_count(tmp_path):
    cases = tmp_path / "cases.csv"
    readiness = tmp_path / "readiness.json"
    write_cases(cases, rows=199)
    write_readiness(readiness, replay_case_count=199)

    with pytest.raises(ValueError, match="at least 200"):
        validate_reconstructed_replay_inputs(cases, readiness)


def test_build_reconstructed_replay_summary_never_allows_formal_v011():
    predictions = make_predictions()
    metrics = {
        "case_count": 2,
        "success_count": 2,
        "fail_count": 0,
        "direction_accuracy": 0.5,
        "mean_abs_return_error": 0.1,
        "median_abs_return_error": 0.1,
        "rmse_return_error": 0.2,
    }

    summary = build_reconstructed_replay_summary(predictions, metrics, {"inference": {"max_cases": 2}})

    assert summary["formal_v011_ready"] is False
    assert summary["zero_shot"] is True


def test_compute_group_metrics_groups_by_symbol():
    group_metrics = compute_group_metrics(make_predictions())

    assert {row["symbol"] for row in group_metrics["by_symbol"]} == {"510300", "510500"}


def test_compute_group_metrics_groups_by_candidate_rank():
    group_metrics = compute_group_metrics(make_predictions())

    assert {row["candidate_rank"] for row in group_metrics["by_candidate_rank"]} == {"1", "2"}


def test_summary_keys_do_not_contain_forbidden_terms():
    summary = build_reconstructed_replay_summary(
        make_predictions(),
        {
            "case_count": 2,
            "success_count": 2,
            "fail_count": 0,
            "direction_accuracy": 1.0,
            "mean_abs_return_error": 0.1,
            "median_abs_return_error": 0.1,
            "rmse_return_error": 0.1,
        },
        {"inference": {"max_cases": 2}},
    )

    assert_no_forbidden_keys(json.loads(json.dumps(summary)))


def test_run_kronos_reconstructed_replay_import_has_no_side_effects():
    module = importlib.import_module("scripts.run_kronos_reconstructed_replay")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def make_predictions():
    return pd.DataFrame(
        {
            "replay_id": ["a", "b"],
            "symbol": ["510300", "510500"],
            "candidate_rank": [1, 2],
            "model_status": ["PASS", "PASS"],
            "direction_match": [True, False],
            "abs_return_error": [0.1, 0.2],
            "squared_return_error": [0.01, 0.04],
        }
    )


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
