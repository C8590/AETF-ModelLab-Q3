from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


CANDIDATE_HISTORY_TYPE = "reconstructed_not_true_left_snapshot"
RECONSTRUCTED_NOTE = "reconstructed_candidate_history_not_real_left_snapshot"
REPLAY_CASE_COLUMNS = [
    "replay_id",
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "kline_path",
    "notes",
]
FORBIDDEN_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


def load_reconstructed_replay_cases(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"reconstructed replay cases not found: {path}")
    df = pd.read_csv(path)
    missing = [column for column in REPLAY_CASE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"reconstructed replay cases missing columns: {missing}")
    out = df.copy()
    out["replay_id"] = out["replay_id"].fillna("").astype(str).str.strip()
    if out["replay_id"].eq("").any():
        raise ValueError("replay_id must be non-empty.")
    if out["replay_id"].duplicated().any():
        raise ValueError("replay_id must be unique.")
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="raise").dt.strftime("%Y-%m-%d")
    out["symbol"] = out["symbol"].fillna("").astype(str).str.strip()
    if out["symbol"].eq("").any():
        raise ValueError("symbol must be non-empty.")
    out["candidate_rank"] = pd.to_numeric(out["candidate_rank"], errors="raise").astype(int)
    if (out["candidate_rank"] <= 0).any():
        raise ValueError("candidate_rank must be positive.")
    out["kline_path"] = out["kline_path"].fillna("").astype(str).str.strip()
    if out["kline_path"].eq("").any():
        raise ValueError("kline_path must be non-empty.")
    notes = out["notes"].fillna("").astype(str)
    if not notes.str.contains(RECONSTRUCTED_NOTE, regex=False).all():
        raise ValueError("all replay cases notes must contain reconstructed marker.")
    return out[REPLAY_CASE_COLUMNS].sort_values(["as_of_date", "candidate_rank"], kind="stable").reset_index(drop=True)


def select_cases_for_expansion(
    replay_cases_df: pd.DataFrame,
    completed_replay_ids: set[str],
    max_cases: int | None,
) -> pd.DataFrame:
    selected = replay_cases_df.loc[~replay_cases_df["replay_id"].astype(str).isin(completed_replay_ids)].copy()
    selected = selected.sort_values(["as_of_date", "candidate_rank"], kind="stable").reset_index(drop=True)
    if max_cases is not None:
        if max_cases <= 0:
            raise ValueError("max_cases must be positive when provided.")
        selected = selected.head(max_cases).reset_index(drop=True)
    return selected


def load_completed_replay_ids(predictions_path: Path) -> set[str]:
    if not predictions_path.exists():
        return set()
    df = pd.read_csv(predictions_path, usecols=["replay_id"])
    return set(df["replay_id"].dropna().astype(str))


def append_predictions(existing_path: Path, new_df: pd.DataFrame) -> None:
    if new_df.empty:
        return
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df.copy()
    combined = combined.drop_duplicates(subset=["replay_id"], keep="first")
    combined = combined.sort_values(["as_of_date", "candidate_rank"], kind="stable").reset_index(drop=True)
    combined.to_csv(existing_path, index=False, encoding="utf-8-sig")


def compute_expanded_group_metrics(predictions_df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    working = predictions_df.copy()
    if "as_of_date" in working.columns:
        working["month"] = pd.to_datetime(working["as_of_date"], errors="coerce").dt.strftime("%Y-%m")
    else:
        working["month"] = ""
    return {
        "by_symbol": _group_rows(working, "symbol"),
        "by_candidate_rank": _group_rows(working, "candidate_rank"),
        "by_month": _group_rows(working, "month"),
        "fail_reasons": _fail_reasons(working),
    }


def build_expanded_summary(
    predictions_df: pd.DataFrame,
    metrics: dict[str, Any],
    prior_summary: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    total_available_cases = int(config.get("runtime", {}).get("total_available_cases", len(predictions_df)) or 0)
    evaluated_case_count = int(metrics.get("case_count", len(predictions_df)) or 0)
    success_count = int(metrics.get("success_count", 0) or 0)
    fail_count = int(metrics.get("fail_count", 0) or 0)
    baseline_accuracy = None
    baseline_case_count = None
    if prior_summary:
        baseline_accuracy = _clean_metric(prior_summary.get("direction_accuracy"))
        baseline_case_count = int(prior_summary.get("evaluated_case_count", 0) or 0)
    direction_accuracy = _clean_metric(metrics.get("direction_accuracy"))
    delta = (
        float(direction_accuracy - baseline_accuracy)
        if direction_accuracy is not None and baseline_accuracy is not None
        else None
    )
    ready = evaluated_case_count >= 1000 and success_count > 0
    summary = {
        "mode": "reconstructed_zero_shot_replay_full_expansion",
        "candidate_history_type": CANDIDATE_HISTORY_TYPE,
        "total_available_cases": total_available_cases,
        "evaluated_case_count": evaluated_case_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "direction_accuracy": direction_accuracy,
        "mean_abs_return_error": _clean_metric(metrics.get("mean_abs_return_error")),
        "median_abs_return_error": _clean_metric(metrics.get("median_abs_return_error")),
        "rmse_return_error": _clean_metric(metrics.get("rmse_return_error")),
        "v11r_baseline_direction_accuracy": baseline_accuracy,
        "v11r_baseline_case_count": baseline_case_count,
        "direction_accuracy_delta_vs_v11r": delta,
        "formal_v011_ready": False,
        "reconstructed_v012r_ready": bool(ready),
        "zero_shot": True,
        "no_training": True,
        "no_torchrun": True,
        "no_checkpoint": True,
        "no_left_project_connection": True,
        "warnings": [
            "Reconstructed candidate history is not true left-side historical candidate data.",
            "V0.12-R results cannot represent true left project historical candidate performance.",
            "This is not formal V0.12 or formal V0.11 and must not be used as a trading basis.",
        ],
        "next_step": (
            "Proceed to V0.13-R reconstructed display layer."
            if ready
            else "Continue expansion until evaluated_case_count reaches at least 1000."
        ),
        "group_metrics": compute_expanded_group_metrics(predictions_df),
    }
    assert_no_forbidden_keys(summary)
    return summary


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
        status = group.get("model_status", pd.Series(dtype=str)).astype(str)
        success_mask = status == "PASS"
        success = group[success_mask].copy()
        success_count = int(success_mask.sum())
        fail_count = int((status == "FAIL").sum())
        match_values = success.get("direction_match", pd.Series(dtype=bool))
        match_count = int(sum(True for item in match_values if item is True or str(item).lower() == "true"))
        abs_errors = pd.to_numeric(success.get("abs_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
        squared_errors = pd.to_numeric(success.get("squared_return_error", pd.Series(dtype=float)), errors="coerce").dropna()
        rows.append(
            {
                column: str(value),
                "case_count": int(len(group)),
                "success_count": success_count,
                "fail_count": fail_count,
                "direction_accuracy": float(match_count / success_count) if success_count else None,
                "mean_abs_return_error": float(abs_errors.mean()) if not abs_errors.empty else None,
                "median_abs_return_error": float(abs_errors.median()) if not abs_errors.empty else None,
                "rmse_return_error": float(math.sqrt(squared_errors.mean())) if not squared_errors.empty else None,
            }
        )
    return rows


def _fail_reasons(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty or "model_status" not in df.columns:
        return []
    failed = df[df["model_status"].astype(str) == "FAIL"].copy()
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
