from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


CANDIDATE_HISTORY_TYPE = "reconstructed_not_true_left_snapshot"
FORBIDDEN_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


def validate_reconstructed_replay_inputs(
    replay_cases_path: Path,
    readiness_path: Path,
) -> dict[str, Any]:
    if not replay_cases_path.exists():
        raise FileNotFoundError(f"reconstructed replay cases not found: {replay_cases_path}")
    if not readiness_path.exists():
        raise FileNotFoundError(f"reconstructed readiness JSON not found: {readiness_path}")

    readiness = json.loads(readiness_path.read_text(encoding="utf-8-sig"))
    if readiness.get("candidate_history_type") != CANDIDATE_HISTORY_TYPE:
        raise ValueError("candidate_history_type must be reconstructed_not_true_left_snapshot.")
    if bool(readiness.get("can_enter_formal_v011")):
        raise ValueError("reconstructed replay input must not be allowed to enter formal V0.11.")
    if not bool(readiness.get("can_enter_v011_reconstructed")):
        raise ValueError("reconstructed readiness does not allow V0.11-R.")
    if int(readiness.get("replay_case_count", 0)) < 200:
        raise ValueError("reconstructed replay_case_count must be at least 200.")

    replay_cases = pd.read_csv(replay_cases_path)
    if len(replay_cases) < 200:
        raise ValueError("reconstructed replay cases CSV must contain at least 200 rows.")
    return {
        "candidate_history_type": readiness["candidate_history_type"],
        "replay_case_count": int(readiness["replay_case_count"]),
        "can_enter_formal_v011": False,
        "can_enter_v011_reconstructed": True,
        "replay_cases_path": replay_cases_path.as_posix(),
        "readiness_path": readiness_path.as_posix(),
    }


def build_reconstructed_replay_summary(
    predictions_df: pd.DataFrame,
    metrics: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    evaluated_case_count = int(metrics.get("case_count", len(predictions_df)) or 0)
    success_count = int(metrics.get("success_count", 0) or 0)
    fail_count = int(metrics.get("fail_count", 0) or 0)
    max_cases = int(config.get("inference", {}).get("max_cases", 200) or 200)
    reconstructed_ready = evaluated_case_count >= 200 and success_count >= min(max_cases, 200)
    group_metrics = compute_group_metrics(predictions_df)
    summary = {
        "mode": "reconstructed_zero_shot_replay",
        "candidate_history_type": CANDIDATE_HISTORY_TYPE,
        "evaluated_case_count": evaluated_case_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "direction_accuracy": _clean_metric(metrics.get("direction_accuracy")),
        "mean_abs_return_error": _clean_metric(metrics.get("mean_abs_return_error")),
        "median_abs_return_error": _clean_metric(metrics.get("median_abs_return_error")),
        "rmse_return_error": _clean_metric(metrics.get("rmse_return_error")),
        "formal_v011_ready": False,
        "reconstructed_v011_ready": bool(reconstructed_ready),
        "no_training": True,
        "no_torchrun": True,
        "zero_shot": True,
        "no_checkpoint": True,
        "no_left_project_connection": True,
        "warnings": [
            "Reconstructed candidate history is not true left-side historical candidate data.",
            "V0.11-R results cannot represent true left project historical candidate performance.",
            "This is not formal V0.11 and must not be used as a trading basis.",
        ],
        "next_step": (
            "Proceed to V0.12-R reconstructed branch display or extended evaluation."
            if reconstructed_ready
            else "Increase successful reconstructed zero-shot replay cases or resolve inference failures."
        ),
        "group_metrics": group_metrics,
    }
    assert_no_forbidden_keys(summary)
    return summary


def compute_group_metrics(predictions_df: pd.DataFrame) -> dict[str, Any]:
    pass_df = predictions_df[predictions_df.get("model_status", pd.Series(dtype=str)).astype(str) == "PASS"].copy()
    return {
        "by_symbol": _group_rows(pass_df, "symbol"),
        "by_candidate_rank": _group_rows(pass_df, "candidate_rank"),
        "fail_reasons": _fail_reasons(predictions_df),
    }


def write_json(data: dict[str, Any], output_path: Path) -> None:
    assert_no_forbidden_keys(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_no_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_KEY_PARTS:
                if forbidden in lower:
                    raise ValueError(f"output key contains forbidden term: {key}")
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)


def _group_rows(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if df.empty or column not in df.columns:
        return []
    rows: list[dict[str, Any]] = []
    for value, group in df.groupby(column, dropna=False):
        abs_errors = pd.to_numeric(group.get("abs_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
        squared_errors = pd.to_numeric(group.get("squared_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
        matches = group.get("direction_match", pd.Series(dtype=bool))
        match_count = int(sum(True for item in matches if item is True or str(item).lower() == "true"))
        success_count = int(len(group))
        rows.append(
            {
                column: str(value),
                "success_count": success_count,
                "direction_accuracy": float(match_count / success_count) if success_count else float("nan"),
                "mean_abs_return_error": float(abs_errors.mean()) if not abs_errors.empty else float("nan"),
                "rmse_return_error": float(math.sqrt(squared_errors.mean())) if not squared_errors.empty else float("nan"),
            }
        )
    return rows


def _fail_reasons(predictions_df: pd.DataFrame) -> list[dict[str, Any]]:
    if predictions_df.empty or "model_status" not in predictions_df.columns:
        return []
    failed = predictions_df[predictions_df["model_status"].astype(str) == "FAIL"].copy()
    if failed.empty:
        return []
    rows: list[dict[str, Any]] = []
    for reason, group in failed.groupby("error_message", dropna=False):
        rows.append({"error_message": str(reason), "count": int(len(group))})
    return rows


def _clean_metric(value: Any) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)
