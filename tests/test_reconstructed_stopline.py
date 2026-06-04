import importlib

import pandas as pd
import pytest

from model_lab.reconstructed_stopline import (
    FORBIDDEN_JSON_KEY_PARTS,
    build_stopline_decision,
    compute_direction_confusion,
    compute_error_distribution,
    compute_majority_direction_baseline,
    wilson_interval,
)


def test_wilson_interval_zero_success_has_valid_bounds():
    interval = wilson_interval(0, 10)

    assert interval["point_estimate"] == 0.0
    assert 0.0 <= interval["lower"] <= interval["upper"] <= 1.0


def test_wilson_interval_zero_total_raises_clear_error():
    with pytest.raises(ValueError, match="total_count"):
        wilson_interval(0, 0)


def test_compute_majority_direction_baseline_finds_majority_class():
    baseline = compute_majority_direction_baseline(
        pd.DataFrame({"actual_direction": ["UP", "DOWN", "DOWN", "DOWN"]})
    )

    assert baseline["majority_direction"] == "DOWN"
    assert baseline["majority_direction_accuracy"] == 0.75


def test_compute_direction_confusion_outputs_counts():
    confusion = compute_direction_confusion(_predictions_df())

    assert confusion["total_count"] == 5
    assert confusion["matched_count"] == 2
    assert confusion["mismatched_count"] == 3
    assert len(confusion["matrix"]) >= 2


def test_compute_error_distribution_outputs_tail_quantiles():
    distribution = compute_error_distribution(_predictions_df())

    assert distribution["p90_abs_return_error"] >= distribution["median_abs_return_error"]
    assert distribution["p95_abs_return_error"] >= distribution["p90_abs_return_error"]


def test_build_stopline_decision_pauses_when_direction_accuracy_under_half():
    stopline = build_stopline_decision(
        _summary(direction_accuracy=0.4),
        {"mode": "reconstructed_branch_dashboard"},
        {"majority_direction_accuracy": 0.6},
        wilson_interval(2, 5),
        compute_error_distribution(_predictions_df()),
        {
            "by_symbol": {"stable_group_count": 1},
            "by_month": {"stable_group_count": 1},
        },
        _config(),
    )

    assert stopline["decision"] == "PAUSE_RECONSTRUCTED_BRANCH"
    assert stopline["formal_v011_ready"] is False
    assert stopline["reconstructed_branch_continue"] is False
    assert_no_forbidden_keys(stopline)


def test_build_reconstructed_stopline_import_has_no_side_effects():
    module = importlib.import_module("scripts.build_reconstructed_stopline")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def _predictions_df():
    return pd.DataFrame(
        {
            "pred_direction": ["UP", "UP", "DOWN", "DOWN", "UP"],
            "actual_direction": ["UP", "DOWN", "DOWN", "UP", "DOWN"],
            "direction_match": [True, False, True, False, False],
            "return_error": [0.01, -0.20, 0.05, 0.12, -0.30],
            "abs_return_error": [0.01, 0.20, 0.05, 0.12, 0.30],
            "squared_return_error": [0.0001, 0.04, 0.0025, 0.0144, 0.09],
        }
    )


def _summary(direction_accuracy=0.4):
    return {
        "candidate_history_type": "reconstructed_not_true_left_snapshot",
        "evaluated_case_count": 1341,
        "direction_accuracy": direction_accuracy,
        "mean_abs_return_error": 0.157,
        "median_abs_return_error": 0.138,
        "rmse_return_error": 0.195,
        "direction_accuracy_delta_vs_v11r": -0.145,
    }


def _config():
    return {
        "thresholds": {
            "min_cases_for_stopline": 1000,
            "min_direction_accuracy_to_continue": 0.52,
            "min_direction_accuracy_margin_vs_majority_baseline": 0.02,
            "max_mean_abs_return_error_to_continue": 0.10,
            "max_rmse_return_error_to_continue": 0.15,
            "max_negative_delta_vs_v11r_baseline": -0.05,
            "min_stable_symbol_group_count": 5,
            "min_stable_month_group_count": 6,
        }
    }


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)
