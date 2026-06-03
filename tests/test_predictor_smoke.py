import importlib
import json

from model_lab.predictor_smoke import (
    FORBIDDEN_RESULT_KEY_PARTS,
    PredictorSmokeConfig,
    build_smoke_training_plan,
    validate_predictor_smoke_gate,
    write_json,
)


def make_readiness(**updates):
    data = {
        "decision": "NOT_READY_FOR_FULL_FINETUNE",
        "is_ready_for_full_finetune": False,
        "is_ready_for_tokenizer_finetune": False,
        "is_ready_for_predictor_dry_run": True,
    }
    data.update(updates)
    return data


def make_manifest(**updates):
    data = {
        "mode": "predictor_dryrun_design_only",
        "predictor_only": True,
        "synthetic_demo_only": True,
        "no_formal_training": True,
    }
    data.update(updates)
    return data


def test_predictor_smoke_config_defaults_are_one_step_safe():
    config = PredictorSmokeConfig()

    assert config.predictor_only is True
    assert config.tokenizer_finetune is False
    assert config.full_finetune is False
    assert config.max_steps == 1
    assert config.batch_size == 1
    assert config.nproc_per_node == 1


def test_gate_rejects_execution_without_explicit_flag():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(require_explicit_execute_flag=True),
        explicit_execute=False,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("explicit --execute-smoke" in reason for reason in gate["reasons"])


def test_gate_rejects_max_steps_gt_one():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(max_steps=2),
        explicit_execute=True,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("max_steps" in reason for reason in gate["reasons"])


def test_gate_rejects_batch_size_gt_one():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(batch_size=2),
        explicit_execute=True,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("batch_size" in reason for reason in gate["reasons"])


def test_gate_rejects_tokenizer_finetune():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(tokenizer_finetune=True),
        explicit_execute=True,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("tokenizer_finetune" in reason for reason in gate["reasons"])


def test_gate_rejects_full_finetune():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(full_finetune=True),
        explicit_execute=True,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("full_finetune" in reason for reason in gate["reasons"])


def test_gate_rejects_save_checkpoint():
    gate = validate_predictor_smoke_gate(
        make_readiness(),
        make_manifest(),
        PredictorSmokeConfig(save_checkpoint=True),
        explicit_execute=True,
    )

    assert gate["gate_status"] == "FAIL"
    assert any("save_checkpoint" in reason for reason in gate["reasons"])


def test_build_smoke_training_plan_generates_command_preview(tmp_path):
    plan = build_smoke_training_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorSmokeConfig(),
    )

    assert "--execute-smoke" in plan["command_preview"]
    assert plan["max_steps"] == 1
    assert plan["batch_size"] == 1


def test_blocked_commands_include_disallowed_modes(tmp_path):
    plan = build_smoke_training_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorSmokeConfig(),
    )
    blocked = " ".join(plan["blocked_commands"])

    assert "tokenizer" in blocked
    assert "full finetune" in blocked
    assert "long torchrun" in blocked
    assert "Kronos-large" in blocked


def test_result_json_keys_do_not_contain_forbidden_terms(tmp_path):
    plan = build_smoke_training_plan(
        tmp_path / "external" / "Kronos",
        tmp_path / "ignored_checkpoints",
        PredictorSmokeConfig(),
    )
    output_path = tmp_path / "plan.json"

    write_json(plan, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert_no_forbidden_keys(data)


def test_run_predictor_smoke_training_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.run_predictor_smoke_training")

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
