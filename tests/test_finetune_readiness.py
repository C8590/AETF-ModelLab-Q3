import importlib
import json

import pandas as pd
import pytest

from model_lab.finetune_readiness import (
    FORBIDDEN_RESULT_KEY_PARTS,
    FinetuneReadinessConfig,
    evaluate_finetune_readiness,
    profile_replay_dataset,
    write_readiness_json,
)


def make_replay_cases() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "replay_id": "2025-07-03_510300",
                "as_of_date": "2025-07-03",
                "symbol": "510300",
                "display_name": "沪深300ETF",
                "candidate_rank": 1,
                "left_score": 82.5,
            },
            {
                "replay_id": "2025-09-11_510300",
                "as_of_date": "2025-09-11",
                "symbol": "510300",
                "display_name": "沪深300ETF",
                "candidate_rank": 2,
                "left_score": 84.0,
            },
            {
                "replay_id": "2025-08-14_159915",
                "as_of_date": "2025-08-14",
                "symbol": "159915",
                "display_name": "创业板ETF",
                "candidate_rank": 1,
                "left_score": 76.0,
            },
        ]
    )


def test_profile_replay_dataset_outputs_symbol_profile():
    profile = profile_replay_dataset(make_replay_cases())

    assert list(profile.columns) == [
        "symbol",
        "case_count",
        "min_as_of_date",
        "max_as_of_date",
        "rank_min",
        "rank_max",
        "left_score_mean",
    ]
    row = profile[profile["symbol"] == "510300"].iloc[0]
    assert row["case_count"] == 2
    assert row["min_as_of_date"] == "2025-07-03"
    assert row["max_as_of_date"] == "2025-09-11"
    assert row["left_score_mean"] == pytest.approx(83.25)


def test_profile_replay_dataset_empty_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        profile_replay_dataset(make_replay_cases().iloc[0:0])


def test_profile_replay_dataset_missing_required_columns_raises():
    with pytest.raises(ValueError, match="missing columns"):
        profile_replay_dataset(pd.DataFrame({"symbol": ["510300"]}))


def test_evaluate_readiness_blocks_full_finetune_on_small_case_count():
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 4, "direction_accuracy": 0.8, "mean_abs_return_error": 0.01},
        FinetuneReadinessConfig(min_replay_cases=200),
    )

    assert result["is_ready_for_full_finetune"] is False
    assert any("replay case count" in reason for reason in result["reasons"])


def test_evaluate_readiness_blocks_full_finetune_when_accuracy_zero():
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 300, "direction_accuracy": 0.0, "mean_abs_return_error": 0.01},
        FinetuneReadinessConfig(min_replay_cases=1),
    )

    assert result["is_ready_for_full_finetune"] is False
    assert result["observed"]["direction_accuracy"] == 0.0


def test_gpu_memory_8_blocks_full_finetune_even_when_policy_default():
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 300, "direction_accuracy": 0.8, "mean_abs_return_error": 0.01},
        FinetuneReadinessConfig(min_replay_cases=1, gpu_memory_gb=8),
    )

    assert result["is_ready_for_full_finetune"] is False
    assert any("8GB GPU memory" in reason for reason in result["reasons"])


def test_predictor_dry_run_is_ready_without_formal_training_permission():
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 4, "direction_accuracy": 0.0, "mean_abs_return_error": 0.061},
        FinetuneReadinessConfig(allow_predictor_dry_run=True),
    )

    assert result["is_ready_for_predictor_dry_run"] is True
    assert result["is_ready_for_full_finetune"] is False
    assert result["is_ready_for_tokenizer_finetune"] is False
    assert result["safety"]["training_executed"] is False


def test_readiness_result_keys_do_not_use_forbidden_terms():
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 4, "direction_accuracy": 0.0, "mean_abs_return_error": 0.061},
        FinetuneReadinessConfig(),
    )

    assert_no_forbidden_keys(result)


def test_write_readiness_json(tmp_path):
    profile = profile_replay_dataset(make_replay_cases())
    result = evaluate_finetune_readiness(
        profile,
        {"case_count": 4, "direction_accuracy": 0.0, "mean_abs_return_error": 0.061},
        FinetuneReadinessConfig(),
    )
    output_path = tmp_path / "readiness.json"

    write_readiness_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["mode"] == "finetune_evaluation_only"
    assert data["is_ready_for_full_finetune"] is False
    assert_no_forbidden_keys(data)


def test_evaluate_finetune_readiness_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.evaluate_finetune_readiness")

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
