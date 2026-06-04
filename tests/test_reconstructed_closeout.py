import importlib

from model_lab.reconstructed_closeout import (
    FORBIDDEN_JSON_KEY_PARTS,
    build_artifact_index,
    build_next_step_decision_matrix,
    build_reconstructed_closeout,
    load_json_if_exists,
)


def test_load_json_if_exists_returns_missing_status(tmp_path):
    result = load_json_if_exists(tmp_path / "missing.json")

    assert result["exists"] is False
    assert result["data"] == {}


def test_build_artifact_index_marks_exists_true_and_false(tmp_path):
    existing = tmp_path / "outputs" / "kronos_v14r_reconstructed_stopline.json"
    existing.parent.mkdir(parents=True)
    existing.write_text("{}", encoding="utf-8")

    index = build_artifact_index(tmp_path, [existing, tmp_path / "missing.md"])

    assert index["artifact_count"] == 2
    assert index["missing_artifact_count"] == 1
    assert index["artifacts"][0]["exists"] is True
    assert index["artifacts"][1]["exists"] is False


def test_build_reconstructed_closeout_pauses_branch_and_blocks_formal_v011(tmp_path):
    artifact_index = build_artifact_index(tmp_path, [])
    closeout = build_reconstructed_closeout(_inputs(), artifact_index, _config())

    assert closeout["final_branch_status"] == "PAUSED_BY_STOPLINE"
    assert closeout["formal_v011_ready"] is False
    assert closeout["reconstructed_branch_continue"] is False
    assert_no_forbidden_keys(closeout)


def test_build_next_step_decision_matrix_contains_three_paths():
    closeout = build_reconstructed_closeout(_inputs(), {"artifact_count": 0}, _config())
    matrix = build_next_step_decision_matrix(closeout)

    paths = {item["path"]: item for item in matrix["paths"]}
    assert set(paths) == {
        "OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY",
        "REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2",
        "DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1",
    }
    assert paths["DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1"]["status"] == "BLOCKED"
    assert_no_forbidden_keys(matrix)


def test_build_reconstructed_closeout_import_has_no_side_effects():
    module = importlib.import_module("scripts.build_reconstructed_closeout")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def _inputs():
    return {
        "v12r_summary": {
            "exists": True,
            "data": {
                "candidate_history_type": "reconstructed_not_true_left_snapshot",
                "evaluated_case_count": 1341,
                "direction_accuracy": 0.4094,
                "mean_abs_return_error": 0.157,
                "rmse_return_error": 0.195,
                "direction_accuracy_delta_vs_v11r": -0.145,
            },
        },
        "v14r_stopline": {
            "exists": True,
            "data": {
                "decision": "PAUSE_RECONSTRUCTED_BRANCH",
                "decision_level": "STOPLINE",
                "candidate_history_type": "reconstructed_not_true_left_snapshot",
                "evaluated_case_count": 1341,
                "direction_accuracy": 0.4094,
                "majority_direction_accuracy": 0.6018,
                "wilson_interval": {"lower": 0.383, "upper": 0.436},
                "mean_abs_return_error": 0.157,
                "rmse_return_error": 0.195,
                "direction_accuracy_delta_vs_v11r": -0.145,
                "blockers": ["DIRECTION_ACCURACY_UNDER_50_PERCENT"],
            },
        },
    }


def _config():
    return {
        "closeout": {
            "branch_name": "reconstructed_v1",
            "candidate_history_type": "reconstructed_not_true_left_snapshot",
            "final_branch_status": "PAUSED_BY_STOPLINE",
            "final_decision": "PAUSE_RECONSTRUCTED_BRANCH",
        },
        "next_steps": {
            "preferred_path": "OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY",
            "fallback_path": "REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2",
            "blocked_path": "DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1",
        },
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
