import importlib
import json

import pandas as pd
import pytest

from model_lab.predictor_dryrun import (
    FORBIDDEN_RESULT_KEY_PARTS,
    PredictorDryRunConfig,
    build_dryrun_manifest,
    build_predictor_dryrun_command_plan,
    validate_predictor_dryrun_gate,
    write_json,
)


def make_readiness(**updates):
    data = {
        "decision": "NOT_READY_FOR_FULL_FINETUNE",
        "is_ready_for_full_finetune": False,
        "is_ready_for_tokenizer_finetune": False,
        "is_ready_for_predictor_dry_run": True,
        "observed": {
            "symbol_count": 2,
            "replay_case_count": 4,
            "direction_accuracy": 0.0,
            "mean_abs_return_error": 0.06164694589146491,
        },
    }
    data.update(updates)
    return data


def test_predictor_dryrun_config_defaults_are_predictor_only_safe():
    config = PredictorDryRunConfig()

    assert config.predictor_only is True
    assert config.tokenizer_finetune is False
    assert config.full_finetune is False
    assert config.execute_training is False
    assert config.allow_torchrun_execution is False


def test_gate_rejects_when_predictor_dryrun_not_ready():
    readiness = make_readiness(is_ready_for_predictor_dry_run=False)

    with pytest.raises(ValueError, match="predictor dry-run"):
        validate_predictor_dryrun_gate(readiness, PredictorDryRunConfig())


def test_gate_rejects_when_execute_training_true():
    with pytest.raises(ValueError, match="execute_training"):
        validate_predictor_dryrun_gate(make_readiness(), PredictorDryRunConfig(execute_training=True))


def test_gate_rejects_when_tokenizer_finetune_true():
    with pytest.raises(ValueError, match="tokenizer_finetune"):
        validate_predictor_dryrun_gate(make_readiness(), PredictorDryRunConfig(tokenizer_finetune=True))


def test_gate_rejects_when_full_finetune_true():
    with pytest.raises(ValueError, match="full_finetune"):
        validate_predictor_dryrun_gate(make_readiness(), PredictorDryRunConfig(full_finetune=True))


def test_gate_rejects_when_max_steps_gt_one():
    with pytest.raises(ValueError, match="max_steps"):
        validate_predictor_dryrun_gate(make_readiness(), PredictorDryRunConfig(max_steps=2))


def test_build_dryrun_manifest_sets_no_formal_training(tmp_path):
    replay_cases_path = tmp_path / "cases.csv"
    replay_metrics_path = tmp_path / "metrics.csv"
    dataset_profile_path = tmp_path / "profile.csv"
    pd.DataFrame({"symbol": ["510300", "159915"], "case_count": [2, 2]}).to_csv(
        replay_cases_path, index=False
    )
    pd.DataFrame(
        {
            "case_count": [4],
            "direction_accuracy": [0.0],
            "mean_abs_return_error": [0.06164694589146491],
        }
    ).to_csv(replay_metrics_path, index=False)
    pd.DataFrame({"symbol": ["510300", "159915"], "case_count": [2, 2]}).to_csv(
        dataset_profile_path, index=False
    )

    manifest = build_dryrun_manifest(
        make_readiness(),
        replay_cases_path,
        replay_metrics_path,
        dataset_profile_path,
        tmp_path / "ignored_checkpoints",
    )

    assert manifest["no_formal_training"] is True
    assert manifest["replay_case_count"] == 4
    assert manifest["symbol_count"] == 2


def test_command_plan_preview_is_not_executable(tmp_path):
    plan = build_predictor_dryrun_command_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorDryRunConfig(),
    )

    assert "torchrun" in plan["command_preview"]
    assert plan["execute_training"] is False
    assert plan["allow_torchrun_execution"] is False


def test_command_plan_blocks_disallowed_training_modes(tmp_path):
    plan = build_predictor_dryrun_command_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorDryRunConfig(),
    )
    blocked = " ".join(plan["blocked_commands"])

    assert "tokenizer" in blocked
    assert "full finetune" in blocked
    assert "long torchrun" in blocked
    assert "Kronos-large" in blocked


def test_output_json_keys_do_not_contain_forbidden_terms(tmp_path):
    plan = build_predictor_dryrun_command_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorDryRunConfig(),
    )
    output_path = tmp_path / "plan.json"

    write_json(plan, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert_no_forbidden_keys(data)


def test_prepare_predictor_dryrun_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.prepare_predictor_dryrun")

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
