from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
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
class PredictorDryRunConfig:
    predictor_only: bool = True
    tokenizer_finetune: bool = False
    full_finetune: bool = False
    execute_training: bool = False
    allow_torchrun_execution: bool = False
    nproc_per_node: int = 1
    max_steps: int = 1
    epochs: int = 1
    batch_size: int = 1
    gradient_accumulation_steps: int = 1
    mixed_precision: bool = True
    save_checkpoint: bool = False
    synthetic_demo_only: bool = True


def load_readiness_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"readiness JSON not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("readiness JSON must contain an object.")
    return data


def validate_predictor_dryrun_gate(
    readiness: dict[str, Any],
    config: PredictorDryRunConfig,
) -> dict[str, Any]:
    predictor_ready = _read_bool(readiness, "predictor_dry_run_ready", "is_ready_for_predictor_dry_run")
    full_ready = _read_bool(readiness, "full_finetune_ready", "is_ready_for_full_finetune")
    tokenizer_ready = _read_bool(readiness, "tokenizer_finetune_ready", "is_ready_for_tokenizer_finetune")
    failures: list[str] = []

    if not predictor_ready:
        failures.append("readiness predictor dry-run flag must be true.")
    if full_ready:
        failures.append("full finetune readiness must remain false for V0.8.")
    if tokenizer_ready:
        failures.append("tokenizer finetune readiness must remain false for V0.8.")
    if not config.predictor_only:
        failures.append("config.predictor_only must be true.")
    if config.tokenizer_finetune:
        failures.append("config.tokenizer_finetune must be false.")
    if config.full_finetune:
        failures.append("config.full_finetune must be false.")
    if config.execute_training:
        failures.append("config.execute_training must be false.")
    if config.allow_torchrun_execution:
        failures.append("config.allow_torchrun_execution must be false.")
    if config.max_steps > 1:
        failures.append("config.max_steps must not exceed 1.")
    if config.batch_size > 1:
        failures.append("config.batch_size must not exceed 1.")

    gate = {
        "mode": "predictor_dryrun_gate",
        "passed": not failures,
        "predictor_dryrun_ready": predictor_ready,
        "full_finetune_ready": full_ready,
        "tokenizer_finetune_ready": tokenizer_ready,
        "predictor_only": config.predictor_only,
        "execute_training": config.execute_training,
        "allow_torchrun_execution": config.allow_torchrun_execution,
        "max_steps": config.max_steps,
        "batch_size": config.batch_size,
        "failures": failures,
    }
    _validate_result_keys(gate)
    if failures:
        raise ValueError("predictor dry-run gate failed: " + "; ".join(failures))
    return gate


def build_dryrun_manifest(
    readiness: dict[str, Any],
    replay_cases_path: Path,
    replay_metrics_path: Path,
    dataset_profile_path: Path,
    checkpoint_root: Path,
) -> dict[str, Any]:
    replay_cases_df = _read_csv(replay_cases_path)
    metrics = _read_first_csv_row(replay_metrics_path)
    dataset_profile_df = _read_csv(dataset_profile_path)
    observed = readiness.get("observed", {}) if isinstance(readiness.get("observed"), dict) else {}

    replay_case_count = _to_int(
        metrics.get("case_count"),
        default=_to_int(observed.get("replay_case_count"), default=int(len(replay_cases_df))),
    )
    symbol_count = _to_int(
        observed.get("symbol_count"),
        default=int(dataset_profile_df["symbol"].nunique()) if "symbol" in dataset_profile_df else 0,
    )
    manifest = {
        "mode": "predictor_dryrun_design_only",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "readiness_decision": readiness.get("decision"),
        "replay_case_count": replay_case_count,
        "symbol_count": symbol_count,
        "direction_accuracy": _to_float_or_none(metrics.get("direction_accuracy")),
        "mean_abs_return_error": _to_float_or_none(metrics.get("mean_abs_return_error")),
        "synthetic_demo_only": True,
        "predictor_only": True,
        "checkpoint_root": checkpoint_root.as_posix(),
        "checkpoint_root_ignored_expected": True,
        "no_formal_training": True,
        "no_tokenizer_finetune": True,
        "no_full_finetune": True,
    }
    _validate_result_keys(manifest)
    return manifest


def build_predictor_dryrun_command_plan(
    kronos_root: Path,
    checkpoint_root: Path,
    config: PredictorDryRunConfig,
) -> dict[str, Any]:
    script_path = kronos_root / "finetune" / "train_predictor.py"
    command_preview = (
        f"torchrun --standalone --nproc_per_node={config.nproc_per_node} "
        f"{script_path.as_posix()} "
        f"# dry-run preview only: max_steps={config.max_steps}, "
        f"batch_size={config.batch_size}, checkpoint_root={checkpoint_root.as_posix()}"
    )
    plan = {
        "executable": "torchrun",
        "command_preview": command_preview,
        "execute_training": config.execute_training,
        "allow_torchrun_execution": config.allow_torchrun_execution,
        "nproc_per_node": config.nproc_per_node,
        "max_steps": config.max_steps,
        "batch_size": config.batch_size,
        "warnings": [
            "Preview only; V0.8 must not execute torchrun.",
            "Official predictor training saves checkpoints, so output must remain under an ignored root.",
            "Synthetic/demo inputs are insufficient for formal model training.",
        ],
        "blocked_commands": [
            "tokenizer training via finetune/train_tokenizer.py or finetune_csv/finetune_tokenizer.py",
            "full finetune or sequential tokenizer plus predictor training",
            "Kronos-large download or substitution",
            "long torchrun execution beyond a future approved one-step smoke run",
        ],
    }
    _validate_result_keys(plan)
    return plan


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _validate_result_keys(data)
    output_path.write_text(
        json.dumps(_clean_for_json(data), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def config_from_dict(config: dict[str, Any]) -> PredictorDryRunConfig:
    dryrun = config.get("dryrun", {})
    return PredictorDryRunConfig(
        predictor_only=bool(dryrun.get("predictor_only", True)),
        tokenizer_finetune=bool(dryrun.get("tokenizer_finetune", False)),
        full_finetune=bool(dryrun.get("full_finetune", False)),
        execute_training=bool(dryrun.get("execute_training", False)),
        allow_torchrun_execution=bool(dryrun.get("allow_torchrun_execution", False)),
        nproc_per_node=int(dryrun.get("nproc_per_node", 1)),
        max_steps=int(dryrun.get("max_steps", 1)),
        epochs=int(dryrun.get("epochs", 1)),
        batch_size=int(dryrun.get("batch_size", 1)),
        gradient_accumulation_steps=int(dryrun.get("gradient_accumulation_steps", 1)),
        mixed_precision=bool(dryrun.get("mixed_precision", True)),
        save_checkpoint=bool(dryrun.get("save_checkpoint", False)),
        synthetic_demo_only=bool(dryrun.get("synthetic_demo_only", True)),
    )


def config_to_dict(config: PredictorDryRunConfig) -> dict[str, Any]:
    data = asdict(config)
    _validate_result_keys(data)
    return data


def _read_bool(data: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in data:
            return bool(data[key])
    return False


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return pd.read_csv(path)


def _read_first_csv_row(path: Path) -> dict[str, Any]:
    df = _read_csv(path)
    if df.empty:
        return {}
    return {key: _clean_scalar(value) for key, value in df.iloc[0].to_dict().items()}


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
                    raise ValueError(f"dry-run result key contains forbidden term: {key}")
            _validate_result_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_result_keys(item)
