from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


FORBIDDEN_JSON_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path), "data": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {"exists": True, "path": str(path), "data": data}


def build_artifact_index(project_root: Path, expected_paths: list[Path]) -> dict[str, Any]:
    artifacts = []
    for path in expected_paths:
        absolute_path = path if path.is_absolute() else project_root / path
        relative_path = _relative_path(absolute_path, project_root)
        exists = absolute_path.exists()
        artifacts.append(
            {
                "path": relative_path,
                "exists": exists,
                "size_bytes": absolute_path.stat().st_size if exists else 0,
                "artifact_type": _artifact_type(absolute_path),
                "stage": _stage_from_path(relative_path),
                "note": "available" if exists else "missing artifact recorded; not regenerated",
            }
        )
    result = {
        "schema_version": "v0.15-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "reconstructed_branch_artifact_index",
        "artifact_count": len(artifacts),
        "missing_artifact_count": sum(1 for item in artifacts if not item["exists"]),
        "artifacts": artifacts,
    }
    _validate_json_keys(result)
    return result


def build_reconstructed_closeout(
    inputs: dict[str, Any],
    artifact_index: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    closeout_cfg = config.get("closeout", {})
    stopline = inputs.get("v14r_stopline", {}).get("data", {})
    v12r_summary = inputs.get("v12r_summary", {}).get("data", {})
    source = stopline or v12r_summary
    blockers = list(stopline.get("blockers", []))
    lessons = [
        "Reconstructed candidate history is not true left-side historical candidate data.",
        "V0.12-R full expansion did not confirm the V0.11-R 200-case baseline stability.",
        "Direction accuracy stayed below 50 percent and below the majority-direction baseline.",
        "Engineering pipeline can be stable while predictive evidence remains insufficient.",
        "Formal V0.11 requires true left_candidates_history.csv rather than reconstructed_v1 inputs.",
    ]
    closeout = {
        "schema_version": "v0.15-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "reconstructed_branch_closeout",
        "branch_name": closeout_cfg.get("branch_name", "reconstructed_v1"),
        "candidate_history_type": closeout_cfg.get(
            "candidate_history_type",
            source.get("candidate_history_type", "reconstructed_not_true_left_snapshot"),
        ),
        "final_branch_status": closeout_cfg.get("final_branch_status", "PAUSED_BY_STOPLINE"),
        "final_decision": closeout_cfg.get(
            "final_decision",
            stopline.get("decision", "PAUSE_RECONSTRUCTED_BRANCH"),
        ),
        "decision_level": stopline.get("decision_level", "STOPLINE"),
        "evaluated_case_count": _to_int(source.get("evaluated_case_count"), default=0),
        "direction_accuracy": _to_float_or_none(source.get("direction_accuracy")),
        "majority_direction_accuracy": _to_float_or_none(
            stopline.get("majority_direction_accuracy")
        ),
        "wilson_interval": stopline.get("wilson_interval", {}),
        "mean_abs_return_error": _to_float_or_none(source.get("mean_abs_return_error")),
        "rmse_return_error": _to_float_or_none(source.get("rmse_return_error")),
        "direction_accuracy_delta_vs_v11r": _to_float_or_none(
            source.get("direction_accuracy_delta_vs_v11r")
        ),
        "blockers": blockers,
        "lessons_learned": lessons,
        "artifact_index_summary": {
            "artifact_count": artifact_index.get("artifact_count", 0),
            "missing_artifact_count": artifact_index.get("missing_artifact_count", 0),
        },
        "formal_v011_ready": False,
        "reconstructed_branch_continue": False,
        "not_true_left_history": True,
        "not_trading_advice": True,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_kronos_adapter_call": True,
        "left_project_connection": False,
        "recommended_next_step": config.get("next_steps", {}).get(
            "preferred_path",
            "OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY",
        ),
        "fallback_next_step": config.get("next_steps", {}).get(
            "fallback_path",
            "REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2",
        ),
        "blocked_path": config.get("next_steps", {}).get(
            "blocked_path",
            "DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1",
        ),
    }
    closeout = _clean_for_json(closeout)
    _validate_json_keys(closeout)
    return closeout


def build_next_step_decision_matrix(closeout: dict[str, Any]) -> dict[str, Any]:
    paths = [
        {
            "path": "OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY",
            "status": "RECOMMENDED",
            "reason": "Formal V0.11 requires true left_candidates_history.csv.",
            "entry_condition": "A verified true left-side historical candidate file is available.",
        },
        {
            "path": "REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2",
            "status": "OPTIONAL_RESEARCH",
            "reason": "Current reconstructed_v1 is stopped; rules may be redesigned and re-evaluated from V0.10.2-E2.",
            "entry_condition": "Research scope is explicitly limited to reconstructed branch redesign.",
        },
        {
            "path": "DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1",
            "status": "BLOCKED",
            "reason": "Direction accuracy is below 50 percent and below the majority-direction baseline.",
            "entry_condition": "No entry; this path is blocked by the V0.14-R stopline.",
        },
    ]
    result = {
        "schema_version": "v0.15-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "reconstructed_branch_next_step_decision_matrix",
        "branch_name": closeout.get("branch_name"),
        "final_branch_status": closeout.get("final_branch_status"),
        "formal_v011_ready": False,
        "reconstructed_branch_continue": False,
        "paths": paths,
    }
    _validate_json_keys(result)
    return result


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    safe_data = _clean_for_json(data)
    _validate_json_keys(safe_data)
    output_path.write_text(
        json.dumps(safe_data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def _artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    if suffix == ".md":
        return "markdown_report"
    if suffix in {".html", ".htm"}:
        return "html"
    return "other"


def _stage_from_path(path: str) -> str:
    lower = path.lower()
    for marker, stage in [
        ("v10", "V0.10.2-E"),
        ("v11r", "V0.11-R"),
        ("v12r", "V0.12-R"),
        ("v13r", "V0.13-R"),
        ("v14r", "V0.14-R"),
        ("v15r", "V0.15-R"),
    ]:
        if marker in lower:
            return stage
    return "UNKNOWN"


def _clean_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_json(item) for item in value]
    return _clean_scalar(value)


def _clean_scalar(value: Any) -> Any:
    if value is pd.NA:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return value
    return value


def _to_float_or_none(value: Any) -> float | None:
    value = _clean_scalar(value)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _to_int(value: Any, *, default: int) -> int:
    numeric = _to_float_or_none(value)
    return default if numeric is None else int(numeric)


def _validate_json_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"closeout JSON key contains forbidden term: {key}")
            _validate_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_keys(item)
