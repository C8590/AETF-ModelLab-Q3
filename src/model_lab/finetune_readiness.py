from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


FORBIDDEN_RESULT_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


@dataclass
class FinetuneReadinessConfig:
    min_real_symbols: int = 20
    min_real_bars_per_symbol: int = 1000
    min_replay_cases: int = 200
    min_direction_accuracy_for_experiment: float = 0.52
    max_mean_abs_return_error_for_experiment: float = 0.03
    min_train_months: int = 24
    min_validation_months: int = 6
    min_test_months: int = 6
    gpu_memory_gb: int = 8
    allow_full_finetune: bool = False
    allow_tokenizer_finetune: bool = False
    allow_predictor_dry_run: bool = True


def profile_replay_dataset(replay_cases_df: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "as_of_date", "candidate_rank", "left_score"}
    missing = sorted(required - set(replay_cases_df.columns))
    if missing:
        raise ValueError(f"replay_cases_df missing columns: {missing}")
    if replay_cases_df.empty:
        raise ValueError("replay_cases_df must not be empty.")

    working = replay_cases_df.copy()
    working["as_of_date"] = pd.to_datetime(working["as_of_date"], errors="coerce")
    working["candidate_rank"] = pd.to_numeric(working["candidate_rank"], errors="coerce")
    working["left_score"] = pd.to_numeric(working["left_score"], errors="coerce")
    grouped = (
        working.groupby("symbol", dropna=False)
        .agg(
            case_count=("symbol", "size"),
            min_as_of_date=("as_of_date", "min"),
            max_as_of_date=("as_of_date", "max"),
            rank_min=("candidate_rank", "min"),
            rank_max=("candidate_rank", "max"),
            left_score_mean=("left_score", "mean"),
        )
        .reset_index()
    )
    grouped["symbol"] = grouped["symbol"].astype(str)
    grouped["min_as_of_date"] = grouped["min_as_of_date"].dt.strftime("%Y-%m-%d")
    grouped["max_as_of_date"] = grouped["max_as_of_date"].dt.strftime("%Y-%m-%d")
    grouped["case_count"] = grouped["case_count"].astype(int)
    return grouped[
        [
            "symbol",
            "case_count",
            "min_as_of_date",
            "max_as_of_date",
            "rank_min",
            "rank_max",
            "left_score_mean",
        ]
    ]


def load_replay_metrics(metrics_path: Path) -> dict[str, Any]:
    if not metrics_path.exists():
        raise FileNotFoundError(f"replay metrics file not found: {metrics_path}")
    df = pd.read_csv(metrics_path)
    if df.empty:
        return {}
    return {key: _clean_scalar(value) for key, value in df.iloc[0].to_dict().items()}


def evaluate_finetune_readiness(
    dataset_profile_df: pd.DataFrame,
    replay_metrics: dict[str, Any],
    config: FinetuneReadinessConfig,
) -> dict[str, Any]:
    if dataset_profile_df.empty:
        raise ValueError("dataset_profile_df must not be empty.")

    symbol_count = int(dataset_profile_df["symbol"].nunique())
    replay_case_count = _to_int(replay_metrics.get("case_count"), default=int(dataset_profile_df["case_count"].sum()))
    direction_accuracy = _to_float_or_none(replay_metrics.get("direction_accuracy"))
    mean_abs_return_error = _to_float_or_none(replay_metrics.get("mean_abs_return_error"))

    reasons: list[str] = []
    warnings: list[str] = [
        "Current input is synthetic/demo data and cannot be treated as a real ETF training set.",
        "V0.7 is evaluation only; it does not execute model training.",
    ]

    if symbol_count < config.min_real_symbols:
        reasons.append(f"real symbol count {symbol_count} is below threshold {config.min_real_symbols}.")
    if replay_case_count < config.min_replay_cases:
        reasons.append(f"replay case count {replay_case_count} is below threshold {config.min_replay_cases}.")
    if direction_accuracy is None or direction_accuracy < config.min_direction_accuracy_for_experiment:
        reasons.append(
            "direction accuracy is below the experiment threshold "
            f"{config.min_direction_accuracy_for_experiment}."
        )
    if (
        mean_abs_return_error is None
        or mean_abs_return_error > config.max_mean_abs_return_error_for_experiment
    ):
        reasons.append(
            "mean absolute return error is above the experiment threshold "
            f"{config.max_mean_abs_return_error_for_experiment}."
        )
    if config.gpu_memory_gb <= 8:
        reasons.append("8GB GPU memory is not recommended for full fine-tuning.")
    if not config.allow_full_finetune:
        reasons.append("full fine-tuning is disabled by hardware policy.")
    if not config.allow_tokenizer_finetune:
        warnings.append("tokenizer fine-tuning requires substantial real long-horizon ETF data.")

    full_ready = False
    tokenizer_ready = False
    predictor_dry_ready = bool(config.allow_predictor_dry_run)
    decision = "NOT_READY_FOR_FULL_FINETUNE"
    recommended_next_step = "Proceed only to V0.8 predictor-only dry-run design with tiny local settings."
    if not predictor_dry_ready:
        decision = "NOT_READY_FOR_ANY_FINETUNE_EXPERIMENT"
        recommended_next_step = "Collect real ETF history and expand replay validation before any dry-run design."

    result = {
        "mode": "finetune_evaluation_only",
        "is_ready_for_full_finetune": full_ready,
        "is_ready_for_tokenizer_finetune": tokenizer_ready,
        "is_ready_for_predictor_dry_run": predictor_dry_ready,
        "decision": decision,
        "reasons": reasons,
        "warnings": warnings,
        "observed": {
            "symbol_count": symbol_count,
            "replay_case_count": replay_case_count,
            "direction_accuracy": direction_accuracy,
            "mean_abs_return_error": mean_abs_return_error,
            "max_symbol_case_count": int(dataset_profile_df["case_count"].max()),
            "min_symbol_case_count": int(dataset_profile_df["case_count"].min()),
            "gpu_memory_gb": int(config.gpu_memory_gb),
            "data_kind": "synthetic_demo",
        },
        "thresholds": {
            "min_real_symbols": config.min_real_symbols,
            "min_real_bars_per_symbol": config.min_real_bars_per_symbol,
            "min_replay_cases": config.min_replay_cases,
            "min_direction_accuracy_for_experiment": config.min_direction_accuracy_for_experiment,
            "max_mean_abs_return_error_for_experiment": config.max_mean_abs_return_error_for_experiment,
            "min_train_months": config.min_train_months,
            "min_validation_months": config.min_validation_months,
            "min_test_months": config.min_test_months,
        },
        "recommended_next_step": recommended_next_step,
        "safety": {
            "training_executed": False,
            "torchrun_executed": False,
            "model_download_executed": False,
            "execution_allowed": False,
            "writeback_to_left_project_allowed": False,
            "is_market_advice": False,
        },
    }
    _validate_result_keys(result)
    return result


def write_readiness_json(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _validate_result_keys(result)
    cleaned = _clean_for_json(result)
    output_path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def config_from_dict(config: dict[str, Any]) -> FinetuneReadinessConfig:
    thresholds = config.get("thresholds", {})
    hardware = config.get("hardware", {})
    return FinetuneReadinessConfig(
        min_real_symbols=int(thresholds.get("min_real_symbols", 20)),
        min_real_bars_per_symbol=int(thresholds.get("min_real_bars_per_symbol", 1000)),
        min_replay_cases=int(thresholds.get("min_replay_cases", 200)),
        min_direction_accuracy_for_experiment=float(
            thresholds.get("min_direction_accuracy_for_experiment", 0.52)
        ),
        max_mean_abs_return_error_for_experiment=float(
            thresholds.get("max_mean_abs_return_error_for_experiment", 0.03)
        ),
        min_train_months=int(thresholds.get("min_train_months", 24)),
        min_validation_months=int(thresholds.get("min_validation_months", 6)),
        min_test_months=int(thresholds.get("min_test_months", 6)),
        gpu_memory_gb=int(hardware.get("gpu_memory_gb", 8)),
        allow_full_finetune=bool(hardware.get("allow_full_finetune", False)),
        allow_tokenizer_finetune=bool(hardware.get("allow_tokenizer_finetune", False)),
        allow_predictor_dry_run=bool(hardware.get("allow_predictor_dry_run", True)),
    )


def config_to_dict(config: FinetuneReadinessConfig) -> dict[str, Any]:
    return asdict(config)


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


def _validate_result_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_RESULT_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"readiness result key contains forbidden term: {key}")
            _validate_result_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_result_keys(item)
