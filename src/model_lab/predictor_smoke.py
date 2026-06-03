from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
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
class PredictorSmokeConfig:
    predictor_only: bool = True
    tokenizer_finetune: bool = False
    full_finetune: bool = False
    execute_smoke_training: bool = True
    require_explicit_execute_flag: bool = True
    allow_torchrun_execution: bool = True
    nproc_per_node: int = 1
    max_steps: int = 1
    epochs: int = 1
    batch_size: int = 1
    gradient_accumulation_steps: int = 1
    mixed_precision: bool = True
    save_checkpoint: bool = False
    allow_checkpoint_files_in_ignored_dir: bool = True
    synthetic_demo_only: bool = True
    timeout_seconds: int = 300


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def validate_predictor_smoke_gate(
    readiness: dict[str, Any],
    dryrun_manifest: dict[str, Any],
    config: PredictorSmokeConfig,
    explicit_execute: bool,
) -> dict[str, Any]:
    predictor_ready = _read_bool(readiness, "predictor_dry_run_ready", "is_ready_for_predictor_dry_run")
    full_ready = _read_bool(readiness, "full_finetune_ready", "is_ready_for_full_finetune")
    tokenizer_ready = _read_bool(readiness, "tokenizer_finetune_ready", "is_ready_for_tokenizer_finetune")
    reasons: list[str] = []

    if not predictor_ready:
        reasons.append("readiness predictor dry-run flag must be true.")
    if full_ready:
        reasons.append("full finetune readiness must remain false for V0.9.")
    if tokenizer_ready:
        reasons.append("tokenizer finetune readiness must remain false for V0.9.")
    if dryrun_manifest.get("predictor_only") is not True:
        reasons.append("V0.8 dry-run manifest predictor_only must be true.")
    if not config.predictor_only:
        reasons.append("config.predictor_only must be true.")
    if config.tokenizer_finetune:
        reasons.append("config.tokenizer_finetune must be false.")
    if config.full_finetune:
        reasons.append("config.full_finetune must be false.")
    if not config.execute_smoke_training:
        reasons.append("config.execute_smoke_training must be true for the execute phase.")
    if config.require_explicit_execute_flag and not explicit_execute:
        reasons.append("explicit --execute-smoke flag is required before running the one-step smoke.")
    if config.nproc_per_node != 1:
        reasons.append("config.nproc_per_node must equal 1.")
    if config.max_steps != 1:
        reasons.append("config.max_steps must equal 1.")
    if config.batch_size != 1:
        reasons.append("config.batch_size must equal 1.")
    if config.save_checkpoint:
        reasons.append("config.save_checkpoint must be false.")
    if _contains_kronos_large(dryrun_manifest):
        reasons.append("Kronos-large is not allowed.")

    gate = {
        "mode": "predictor_only_1step_smoke_gate",
        "gate_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
        "predictor_dryrun_ready": predictor_ready,
        "full_finetune_ready": full_ready,
        "tokenizer_finetune_ready": tokenizer_ready,
        "dryrun_predictor_only": dryrun_manifest.get("predictor_only"),
        "predictor_only": config.predictor_only,
        "tokenizer_finetune": config.tokenizer_finetune,
        "full_finetune": config.full_finetune,
        "execute_smoke_training": config.execute_smoke_training,
        "explicit_execute": explicit_execute,
        "nproc_per_node": config.nproc_per_node,
        "max_steps": config.max_steps,
        "batch_size": config.batch_size,
        "save_checkpoint": config.save_checkpoint,
    }
    _validate_result_keys(gate)
    return gate


def inspect_official_predictor_training_entry(kronos_root: Path) -> dict[str, Any]:
    finetune_root = kronos_root / "finetune"
    csv_root = kronos_root / "finetune_csv"
    qlib_predictor = finetune_root / "train_predictor.py"
    qlib_tokenizer = finetune_root / "train_tokenizer.py"
    csv_predictor = csv_root / "finetune_base_model.py"
    csv_tokenizer = csv_root / "finetune_tokenizer.py"
    csv_sequential = csv_root / "train_sequential.py"
    config_py = finetune_root / "config.py"
    qlib_text = qlib_predictor.read_text(encoding="utf-8") if qlib_predictor.exists() else ""
    csv_text = csv_predictor.read_text(encoding="utf-8") if csv_predictor.exists() else ""

    inspection = {
        "mode": "official_predictor_entry_inspection",
        "kronos_root": kronos_root.as_posix(),
        "qlib_predictor_entry": qlib_predictor.as_posix(),
        "qlib_tokenizer_entry": qlib_tokenizer.as_posix(),
        "csv_predictor_entry": csv_predictor.as_posix(),
        "csv_tokenizer_entry": csv_tokenizer.as_posix(),
        "csv_sequential_entry": csv_sequential.as_posix(),
        "config_py_exists": config_py.exists(),
        "qlib_pickle_required": "QlibDataset" in qlib_text,
        "csv_training_entry_exists": csv_predictor.exists(),
        "qlib_requires_torchrun": "WORLD_SIZE" in qlib_text and "torchrun" in qlib_text,
        "qlib_hardcoded_config_py": "Config()" in qlib_text,
        "qlib_has_max_steps_guard": "max_steps" in qlib_text,
        "csv_has_max_steps_guard": "max_steps" in csv_text,
        "checkpoint_default_summary": (
            "Qlib saves under config.save_path/predictor_save_folder_name/checkpoints/best_model; "
            "CSV saves under base_save_path/basemodel/best_model."
        ),
        "safe_to_execute_official_directly": False,
        "blocked_reason": (
            "Official predictor entries do not expose a hard max_steps=1 guard and save best-model "
            "checkpoints after validation, so V0.9 uses a project-local one-step wrapper instead."
        ),
    }
    _validate_result_keys(inspection)
    return inspection


def build_smoke_training_plan(
    kronos_root: Path,
    checkpoint_root: Path,
    config: PredictorSmokeConfig,
) -> dict[str, Any]:
    command_preview = (
        "python scripts/run_predictor_smoke_training.py --execute-smoke "
        f"# controlled wrapper: nproc_per_node={config.nproc_per_node}, "
        f"max_steps={config.max_steps}, batch_size={config.batch_size}, save_checkpoint={config.save_checkpoint}"
    )
    plan = {
        "mode": "predictor_only_1step_smoke_plan",
        "executable": "python",
        "command_preview": command_preview,
        "official_predictor_entry": (kronos_root / "finetune" / "train_predictor.py").as_posix(),
        "controlled_wrapper": "scripts/run_predictor_smoke_training.py",
        "execute_smoke_training": config.execute_smoke_training,
        "allow_torchrun_execution": config.allow_torchrun_execution,
        "nproc_per_node": config.nproc_per_node,
        "max_steps": config.max_steps,
        "batch_size": config.batch_size,
        "save_checkpoint": config.save_checkpoint,
        "checkpoint_root": checkpoint_root.as_posix(),
        "checkpoint_root_ignored_expected": True,
        "warnings": [
            "Official entry is inspected but not directly launched because it cannot be safely bounded to one step.",
            "The controlled wrapper performs one forward, backward, and optimizer step only.",
            "No checkpoint is saved by the wrapper.",
        ],
        "blocked_commands": [
            "tokenizer training via finetune/train_tokenizer.py or finetune_csv/finetune_tokenizer.py",
            "full finetune or sequential tokenizer plus predictor training",
            "Kronos-large download or substitution",
            "long torchrun execution beyond the one-step smoke boundary",
        ],
    }
    _validate_result_keys(plan)
    return plan


def run_predictor_1step_smoke(
    project_root: Path,
    kronos_root: Path,
    config: PredictorSmokeConfig,
    checkpoint_root: Path,
) -> dict[str, Any]:
    started = datetime.now()
    started_perf = time.perf_counter()
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    checkpoint_files_before = _list_checkpoint_files(checkpoint_root)
    result: dict[str, Any] = {
        "status": "FAIL",
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": None,
        "elapsed_seconds": None,
        "torch_version": None,
        "cuda_available": False,
        "gpu_name": "N/A",
        "max_memory_allocated_mb": None,
        "loss_before": None,
        "loss_after": None,
        "optimizer_step_executed": False,
        "checkpoint_files_created": 0,
        "checkpoint_root": checkpoint_root.as_posix(),
        "error_message": "",
    }

    try:
        import torch

        result["torch_version"] = torch.__version__
        result["cuda_available"] = bool(torch.cuda.is_available())
        if not torch.cuda.is_available():
            result["status"] = "BLOCKED"
            result["error_message"] = "CUDA is not available; V0.9 smoke requires cuda:0."
            return _finish_smoke_result(result, started_perf, checkpoint_root, checkpoint_files_before)
        if config.max_steps != 1 or config.batch_size != 1 or config.nproc_per_node != 1:
            result["status"] = "BLOCKED"
            result["error_message"] = "Smoke config must remain exactly one process, one step, batch size one."
            return _finish_smoke_result(result, started_perf, checkpoint_root, checkpoint_files_before)

        device = torch.device("cuda:0")
        result["gpu_name"] = torch.cuda.get_device_name(device)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        torch.manual_seed(909)
        torch.cuda.manual_seed_all(909)

        os.environ.setdefault("HF_HOME", str(project_root / "models" / "kronos" / "hf_cache"))
        os.environ.setdefault("HF_HUB_CACHE", str(project_root / "models" / "kronos" / "hf_cache" / "hub"))
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        _ensure_kronos_import_path(kronos_root)

        from model import Kronos, KronosTokenizer  # type: ignore  # noqa: E402

        cache_dir = project_root / "models" / "kronos" / "hf_cache"
        tokenizer = _load_hf_model(KronosTokenizer, "NeoQuasar/Kronos-Tokenizer-base", cache_dir)
        model = _load_hf_model(Kronos, "NeoQuasar/Kronos-small", cache_dir)
        tokenizer.eval().to(device)
        model.train().to(device)

        batch_x, batch_x_stamp = _build_synthetic_batch(torch, device, seq_len=32)
        optimizer = torch.optim.AdamW(model.parameters(), lr=4e-5, betas=(0.9, 0.95), weight_decay=0.1)
        autocast_enabled = bool(config.mixed_precision and torch.cuda.is_available())
        amp_context = torch.amp.autocast(device_type="cuda", enabled=autocast_enabled)

        with torch.no_grad():
            token_seq_0, token_seq_1 = tokenizer.encode(batch_x, half=True)
        token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
        token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]

        optimizer.zero_grad(set_to_none=True)
        with amp_context:
            logits = model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
            loss, _, _ = model.head.compute_loss(logits[0], logits[1], token_out[0], token_out[1])
        result["loss_before"] = float(loss.detach().cpu().item())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
        optimizer.step()
        result["optimizer_step_executed"] = True

        model.eval()
        with torch.no_grad():
            with torch.amp.autocast(device_type="cuda", enabled=autocast_enabled):
                logits_after = model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
                loss_after, _, _ = model.head.compute_loss(
                    logits_after[0],
                    logits_after[1],
                    token_out[0],
                    token_out[1],
                )
        result["loss_after"] = float(loss_after.detach().cpu().item())
        result["max_memory_allocated_mb"] = round(torch.cuda.max_memory_allocated(device) / 1024 / 1024, 2)
        result["status"] = "PASS"

        del logits_after, logits, loss_after, loss, optimizer, model, tokenizer, batch_x, batch_x_stamp
        torch.cuda.empty_cache()
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_message"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    finally:
        return _finish_smoke_result(result, started_perf, checkpoint_root, checkpoint_files_before)


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _validate_result_keys(data)
    output_path.write_text(
        json.dumps(_clean_for_json(data), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def config_from_dict(config: dict[str, Any]) -> PredictorSmokeConfig:
    smoke = config.get("smoke", {})
    return PredictorSmokeConfig(
        predictor_only=bool(smoke.get("predictor_only", True)),
        tokenizer_finetune=bool(smoke.get("tokenizer_finetune", False)),
        full_finetune=bool(smoke.get("full_finetune", False)),
        execute_smoke_training=bool(smoke.get("execute_smoke_training", True)),
        require_explicit_execute_flag=bool(smoke.get("require_explicit_execute_flag", True)),
        allow_torchrun_execution=bool(smoke.get("allow_torchrun_execution", True)),
        nproc_per_node=int(smoke.get("nproc_per_node", 1)),
        max_steps=int(smoke.get("max_steps", 1)),
        epochs=int(smoke.get("epochs", 1)),
        batch_size=int(smoke.get("batch_size", 1)),
        gradient_accumulation_steps=int(smoke.get("gradient_accumulation_steps", 1)),
        mixed_precision=bool(smoke.get("mixed_precision", True)),
        save_checkpoint=bool(smoke.get("save_checkpoint", False)),
        allow_checkpoint_files_in_ignored_dir=bool(smoke.get("allow_checkpoint_files_in_ignored_dir", True)),
        synthetic_demo_only=bool(smoke.get("synthetic_demo_only", True)),
        timeout_seconds=int(smoke.get("timeout_seconds", 300)),
    )


def config_to_dict(config: PredictorSmokeConfig) -> dict[str, Any]:
    data = asdict(config)
    _validate_result_keys(data)
    return data


def _build_synthetic_batch(torch_module: Any, device: Any, *, seq_len: int) -> tuple[Any, Any]:
    t = torch_module.arange(seq_len, device=device, dtype=torch_module.float32)
    close = 10.0 + 0.01 * t + 0.02 * torch_module.sin(t / 3.0)
    open_ = close + 0.003 * torch_module.cos(t)
    high = torch_module.maximum(open_, close) + 0.01
    low = torch_module.minimum(open_, close) - 0.01
    volume = 1000.0 + 5.0 * t
    amount = volume * (open_ + high + low + close) / 4.0
    x = torch_module.stack([open_, high, low, close, volume, amount], dim=-1)
    x = (x - x.mean(dim=0)) / (x.std(dim=0) + 1e-5)
    x = torch_module.clamp(x, -5.0, 5.0).unsqueeze(0)
    stamp = torch_module.stack(
        [
            (t % 60),
            ((9 + t // 12) % 24),
            (t % 5),
            (1 + t % 28),
            torch_module.ones_like(t),
        ],
        dim=-1,
    ).unsqueeze(0)
    return x, stamp


def _load_hf_model(model_cls: Any, model_name: str, cache_dir: Path) -> Any:
    try:
        return model_cls.from_pretrained(model_name, cache_dir=cache_dir, local_files_only=True)
    except TypeError:
        return model_cls.from_pretrained(model_name, cache_dir=cache_dir)


def _ensure_kronos_import_path(kronos_root: Path) -> None:
    root_str = str(kronos_root.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _finish_smoke_result(
    result: dict[str, Any],
    started_perf: float,
    checkpoint_root: Path,
    checkpoint_files_before: set[Path],
) -> dict[str, Any]:
    result["finished_at"] = datetime.now().isoformat(timespec="seconds")
    result["elapsed_seconds"] = round(time.perf_counter() - started_perf, 2)
    checkpoint_files_after = _list_checkpoint_files(checkpoint_root)
    result["checkpoint_files_created"] = len(checkpoint_files_after - checkpoint_files_before)
    _validate_result_keys(result)
    return _clean_for_json(result)


def _list_checkpoint_files(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {path for path in root.rglob("*") if path.is_file()}


def _read_bool(data: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in data:
            return bool(data[key])
    return False


def _contains_kronos_large(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_kronos_large(key) or _contains_kronos_large(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_kronos_large(item) for item in value)
    return isinstance(value, str) and "kronos-large" in value.lower()


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


def _validate_result_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_RESULT_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"smoke result key contains forbidden term: {key}")
            _validate_result_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_result_keys(item)
