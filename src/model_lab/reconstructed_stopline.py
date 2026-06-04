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


def compute_direction_confusion(predictions_df: pd.DataFrame) -> dict[str, Any]:
    required = {"pred_direction", "actual_direction"}
    _require_columns(predictions_df, required)
    pairs = (
        predictions_df.assign(
            pred_direction=predictions_df["pred_direction"].fillna("UNKNOWN").astype(str),
            actual_direction=predictions_df["actual_direction"].fillna("UNKNOWN").astype(str),
        )
        .groupby(["actual_direction", "pred_direction"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    total = int(len(predictions_df))
    matched = _direction_match_series(predictions_df).sum()
    result = {
        "total_count": total,
        "matched_count": int(matched),
        "mismatched_count": int(total - matched),
        "direction_accuracy": _safe_ratio(matched, total),
        "matrix": _clean_for_json(pairs.to_dict(orient="records")),
    }
    _validate_json_keys(result)
    return result


def compute_majority_direction_baseline(predictions_df: pd.DataFrame) -> dict[str, Any]:
    _require_columns(predictions_df, {"actual_direction"})
    actual = predictions_df["actual_direction"].fillna("UNKNOWN").astype(str)
    counts = actual.value_counts(dropna=False)
    total = int(len(actual))
    if total == 0:
        raise ValueError("predictions_df must contain at least one row.")
    majority_direction = str(counts.index[0])
    majority_count = int(counts.iloc[0])
    result = {
        "majority_direction": majority_direction,
        "majority_count": majority_count,
        "total_count": total,
        "majority_direction_accuracy": _safe_ratio(majority_count, total),
        "class_counts": {str(key): int(value) for key, value in counts.items()},
    }
    _validate_json_keys(result)
    return result


def wilson_interval(success_count: int, total_count: int, z: float = 1.96) -> dict[str, float]:
    if total_count <= 0:
        raise ValueError("total_count must be greater than zero for Wilson interval.")
    if success_count < 0 or success_count > total_count:
        raise ValueError("success_count must be between 0 and total_count.")
    n = float(total_count)
    phat = success_count / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denominator
    margin = (
        z
        * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
        / denominator
    )
    return {
        "success_count": int(success_count),
        "total_count": int(total_count),
        "point_estimate": phat,
        "lower": max(0.0, center - margin),
        "upper": min(1.0, center + margin),
        "z": float(z),
    }


def compute_error_distribution(predictions_df: pd.DataFrame) -> dict[str, Any]:
    _require_columns(predictions_df, {"abs_return_error", "return_error", "squared_return_error"})
    abs_errors = pd.to_numeric(predictions_df["abs_return_error"], errors="coerce").dropna()
    signed_errors = pd.to_numeric(predictions_df["return_error"], errors="coerce").dropna()
    squared_errors = pd.to_numeric(predictions_df["squared_return_error"], errors="coerce").dropna()
    if abs_errors.empty:
        raise ValueError("abs_return_error must contain at least one numeric value.")
    result = {
        "count": int(abs_errors.count()),
        "mean_abs_return_error": float(abs_errors.mean()),
        "median_abs_return_error": float(abs_errors.median()),
        "p90_abs_return_error": float(abs_errors.quantile(0.90)),
        "p95_abs_return_error": float(abs_errors.quantile(0.95)),
        "max_abs_return_error": float(abs_errors.max()),
        "mean_signed_return_error": float(signed_errors.mean()) if not signed_errors.empty else None,
        "rmse_return_error": (
            float(math.sqrt(squared_errors.mean())) if not squared_errors.empty else None
        ),
    }
    _validate_json_keys(result)
    return result


def compute_extreme_errors(predictions_df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    _require_columns(predictions_df, {"abs_return_error"})
    df = predictions_df.copy()
    df["abs_return_error"] = pd.to_numeric(df["abs_return_error"], errors="coerce")
    df = df.sort_values("abs_return_error", ascending=False, na_position="last").head(top_n)
    preferred_columns = [
        "replay_id",
        "as_of_date",
        "symbol",
        "display_name",
        "candidate_rank",
        "pred_direction",
        "actual_direction",
        "direction_match",
        "pred_return_last",
        "actual_return_last",
        "return_error",
        "abs_return_error",
        "model_status",
    ]
    return df[[column for column in preferred_columns if column in df.columns]]


def diagnose_group_stability(
    group_df: pd.DataFrame,
    group_name: str,
    min_cases: int = 20,
) -> dict[str, Any]:
    _require_columns(group_df, {"case_count", "direction_accuracy"})
    df = group_df.copy()
    df["case_count"] = pd.to_numeric(df["case_count"], errors="coerce").fillna(0)
    df["direction_accuracy"] = pd.to_numeric(df["direction_accuracy"], errors="coerce")
    eligible = df[df["case_count"] >= min_cases]
    stable = eligible[eligible["direction_accuracy"] >= 0.5]
    weak = eligible[eligible["direction_accuracy"] < 0.5]
    result = {
        "group_name": group_name,
        "group_count": int(len(df)),
        "eligible_group_count": int(len(eligible)),
        "stable_group_count": int(len(stable)),
        "weak_group_count": int(len(weak)),
        "min_cases": int(min_cases),
        "weighted_direction_accuracy": _weighted_accuracy(eligible),
        "min_direction_accuracy": _optional_float(eligible["direction_accuracy"].min()),
        "max_direction_accuracy": _optional_float(eligible["direction_accuracy"].max()),
    }
    _validate_json_keys(result)
    return result


def build_group_error_table(group_df: pd.DataFrame, min_cases: int = 20) -> pd.DataFrame:
    df = group_df.copy()
    df["case_count"] = pd.to_numeric(df["case_count"], errors="coerce").fillna(0).astype(int)
    df["direction_accuracy"] = pd.to_numeric(df["direction_accuracy"], errors="coerce")
    df["mean_abs_return_error"] = pd.to_numeric(
        df.get("mean_abs_return_error"), errors="coerce"
    )
    df["rmse_return_error"] = pd.to_numeric(df.get("rmse_return_error"), errors="coerce")
    df["eligible_for_stability_check"] = df["case_count"] >= min_cases
    df["under_50_direction_accuracy"] = df["direction_accuracy"] < 0.5
    df["high_mean_abs_error"] = df["mean_abs_return_error"] > 0.10
    df["high_rmse_error"] = df["rmse_return_error"] > 0.15
    return df


def build_stopline_decision(
    summary: dict[str, Any],
    diagnostics: dict[str, Any],
    majority_baseline: dict[str, Any],
    interval: dict[str, Any],
    error_distribution: dict[str, Any],
    group_stability: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    thresholds = config.get("thresholds", {})
    direction_accuracy = _to_float(summary.get("direction_accuracy"), default=0.0)
    evaluated_case_count = _to_int(summary.get("evaluated_case_count"), default=0)
    mean_abs_error = _to_float(summary.get("mean_abs_return_error"), default=0.0)
    rmse_error = _to_float(summary.get("rmse_return_error"), default=0.0)
    delta = _to_float(summary.get("direction_accuracy_delta_vs_v11r"), default=0.0)
    majority_accuracy = _to_float(
        majority_baseline.get("majority_direction_accuracy"), default=0.0
    )
    blockers: list[str] = []

    if evaluated_case_count < int(thresholds.get("min_cases_for_stopline", 1000)):
        blockers.append("INSUFFICIENT_CASE_COUNT_FOR_STOPLINE")
    if direction_accuracy < 0.5:
        blockers.append("DIRECTION_ACCURACY_UNDER_50_PERCENT")
    if direction_accuracy < float(thresholds.get("min_direction_accuracy_to_continue", 0.52)):
        blockers.append("DIRECTION_ACCURACY_BELOW_CONTINUE_THRESHOLD")
    margin = direction_accuracy - majority_accuracy
    if margin < float(thresholds.get("min_direction_accuracy_margin_vs_majority_baseline", 0.02)):
        blockers.append("NO_CLEAR_MARGIN_VS_MAJORITY_DIRECTION_BASELINE")
    if delta < float(thresholds.get("max_negative_delta_vs_v11r_baseline", -0.05)):
        blockers.append("V11R_BASELINE_NOT_STABLE")
    if mean_abs_error > float(thresholds.get("max_mean_abs_return_error_to_continue", 0.10)):
        blockers.append("MEAN_ABS_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD")
    if rmse_error > float(thresholds.get("max_rmse_return_error_to_continue", 0.15)):
        blockers.append("RMSE_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD")
    symbol_stable = group_stability.get("by_symbol", {}).get("stable_group_count", 0)
    month_stable = group_stability.get("by_month", {}).get("stable_group_count", 0)
    if symbol_stable < int(thresholds.get("min_stable_symbol_group_count", 5)):
        blockers.append("STABLE_SYMBOL_GROUP_COUNT_BELOW_THRESHOLD")
    if month_stable < int(thresholds.get("min_stable_month_group_count", 6)):
        blockers.append("STABLE_MONTH_GROUP_COUNT_BELOW_THRESHOLD")
    blockers.append("RECONSTRUCTED_HISTORY_IS_NOT_TRUE_LEFT_HISTORY")

    pause = bool(blockers) and (
        direction_accuracy < 0.5
        or direction_accuracy < float(thresholds.get("min_direction_accuracy_to_continue", 0.52))
        or delta < float(thresholds.get("max_negative_delta_vs_v11r_baseline", -0.05))
    )
    decision = (
        "PAUSE_RECONSTRUCTED_BRANCH"
        if pause
        else "RECONSTRUCTED_BRANCH_REQUIRES_MORE_REVIEW"
    )
    result = {
        "schema_version": "v0.14-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "reconstructed_branch_error_diagnostics_stopline",
        "candidate_history_type": str(
            summary.get("candidate_history_type", "reconstructed_not_true_left_snapshot")
        ),
        "evaluated_case_count": evaluated_case_count,
        "direction_accuracy": direction_accuracy,
        "majority_direction_accuracy": majority_accuracy,
        "wilson_interval": interval,
        "mean_abs_return_error": mean_abs_error,
        "median_abs_return_error": _to_float_or_none(summary.get("median_abs_return_error")),
        "rmse_return_error": rmse_error,
        "direction_accuracy_delta_vs_v11r": delta,
        "group_stability": group_stability,
        "error_distribution": error_distribution,
        "v13r_diagnostics": diagnostics,
        "decision": decision,
        "decision_level": "STOPLINE" if pause else "REVIEW",
        "blockers": blockers,
        "next_step": (
            "Enter V0.15-R branch closeout or candidate pool reconstruction rule redesign; "
            "do not enter formal V0.11."
            if pause
            else "Continue only with reconstructed branch review; do not enter formal V0.11."
        ),
        "formal_v011_ready": False,
        "reconstructed_branch_continue": not pause,
        "reconstructed_branch_only": True,
        "zero_shot": True,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu_call": True,
        "no_checkpoint": True,
        "not_trading_advice": True,
        "execution_allowed": False,
        "left_project_writeback_allowed": False,
        "notes": [
            "Reconstructed candidate history is not true left-side historical candidate data.",
            "V0.12-R full expansion did not confirm V0.11-R 200-case baseline stability.",
            "Current direction accuracy is below 50 percent and does not support continuing this reconstructed route as an effective prediction path.",
        ],
    }
    result = _clean_for_json(result)
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _direction_match_series(predictions_df: pd.DataFrame) -> pd.Series:
    if "direction_match" in predictions_df.columns:
        values = predictions_df["direction_match"]
        if values.dtype == bool:
            return values
        return values.astype(str).str.lower().isin(["true", "1", "yes"])
    _require_columns(predictions_df, {"pred_direction", "actual_direction"})
    return predictions_df["pred_direction"].astype(str) == predictions_df["actual_direction"].astype(str)


def _weighted_accuracy(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    weights = pd.to_numeric(df["case_count"], errors="coerce").fillna(0)
    values = pd.to_numeric(df["direction_accuracy"], errors="coerce")
    total_weight = float(weights.sum())
    if total_weight <= 0:
        return None
    return float((values.fillna(0) * weights).sum() / total_weight)


def _require_columns(df: pd.DataFrame, required: set[str]) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


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


def _to_float(value: Any, *, default: float) -> float:
    numeric = _to_float_or_none(value)
    return default if numeric is None else numeric


def _to_int(value: Any, *, default: int) -> int:
    numeric = _to_float_or_none(value)
    return default if numeric is None else int(numeric)


def _optional_float(value: Any) -> float | None:
    return _to_float_or_none(value)


def _validate_json_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"stopline JSON key contains forbidden term: {key}")
            _validate_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_keys(item)
