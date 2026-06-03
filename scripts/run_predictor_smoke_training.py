#!/usr/bin/env python3
"""Run V0.9 Kronos predictor-only one-step smoke training."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.predictor_smoke import (  # noqa: E402
    build_smoke_training_plan,
    config_from_dict,
    inspect_official_predictor_training_entry,
    load_json,
    run_predictor_1step_smoke,
    validate_predictor_smoke_gate,
    write_json,
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_config_safety(config)
    return config


def validate_config_safety(config: dict[str, Any]) -> None:
    if config.get("mode") != "predictor_only_1step_smoke":
        raise ValueError("mode must be predictor_only_1step_smoke.")
    smoke = config.get("smoke", {})
    safety = config.get("safety", {})
    if not bool(smoke.get("execute_smoke_training", False)):
        raise ValueError("smoke.execute_smoke_training must be true for V0.9 config.")
    blocked_true_flags = {
        "smoke.tokenizer_finetune": smoke.get("tokenizer_finetune"),
        "smoke.full_finetune": smoke.get("full_finetune"),
        "smoke.save_checkpoint": smoke.get("save_checkpoint"),
        "safety.allow_trading_advice": safety.get("allow_trading_advice"),
        "safety.allow_order_execution": safety.get("allow_order_execution"),
        "safety.allow_writeback_to_left_project": safety.get("allow_writeback_to_left_project"),
        "safety.allow_submit_checkpoints": safety.get("allow_submit_checkpoints"),
        "safety.allow_download_kronos_large": safety.get("allow_download_kronos_large"),
        "safety.allow_tokenizer_finetune": safety.get("allow_tokenizer_finetune"),
        "safety.allow_full_finetune": safety.get("allow_full_finetune"),
        "safety.allow_long_training": safety.get("allow_long_training"),
    }
    for key, value in blocked_true_flags.items():
        if bool(value):
            raise ValueError(f"{key} must be false for V0.9 smoke.")


def run_pytest_quiet() -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    summary = output.splitlines()[-1] if output else ""
    return ("PASS" if result.returncode == 0 else "FAIL", summary)


def write_log(log_path: Path, lines: list[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_report(
    *,
    report_path: Path,
    config: dict[str, Any],
    gate: dict[str, Any],
    inspection: dict[str, Any],
    plan: dict[str, Any],
    smoke_result: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> bool:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    can_enter_v10 = pytest_status == "PASS" and gate["gate_status"] == "PASS" and smoke_result["status"] == "PASS"
    lines = [
        "# Kronos V0.9 Predictor Smoke Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- readiness JSON 路径: {inputs['readiness_json_path']}",
        f"- dryrun manifest 路径: {inputs['dryrun_manifest_path']}",
        f"- ignored checkpoint root: {outputs['ignored_checkpoint_root']}",
        f"- gate_status: {gate['gate_status']}",
        f"- smoke_status: {smoke_result['status']}",
        f"- predictor_only: {gate['predictor_only']}",
        f"- tokenizer_finetune: {gate['tokenizer_finetune']}",
        f"- full_finetune: {gate['full_finetune']}",
        f"- max_steps: {gate['max_steps']}",
        f"- batch_size: {gate['batch_size']}",
        f"- nproc_per_node: {gate['nproc_per_node']}",
        f"- torch 版本: {smoke_result.get('torch_version')}",
        f"- CUDA 是否可用: {smoke_result.get('cuda_available')}",
        f"- GPU 名称: {smoke_result.get('gpu_name')}",
        f"- max_memory_allocated_mb: {smoke_result.get('max_memory_allocated_mb')}",
        f"- loss_before: {smoke_result.get('loss_before')}",
        f"- loss_after: {smoke_result.get('loss_after')}",
        f"- optimizer_step_executed: {smoke_result.get('optimizer_step_executed')}",
        f"- checkpoint_files_created: {smoke_result.get('checkpoint_files_created')}",
        "- 是否未执行正式训练: 是",
        "- 是否未运行长时间 torchrun: 是",
        "- 是否未提交 checkpoint: 是",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.10 真实 ETF 长周期数据准备与回放扩容: {'是' if can_enter_v10 else '否'}",
        "",
        "## Official Entry Inspection",
        "",
        f"- predictor 入口: {inspection['qlib_predictor_entry']}",
        f"- CSV predictor 入口: {inspection['csv_predictor_entry']}",
        f"- 是否安全直接执行官方入口: {inspection['safe_to_execute_official_directly']}",
        f"- 阻塞原因: {inspection['blocked_reason']}",
        f"- command_preview: `{plan['command_preview']}`",
        "",
        "## V0.9 Scope",
        "",
        "- 当前只是 1-step smoke training。",
        "- 当前不是正式微调。",
        "- 当前未生成可用模型。",
        "- 当前样本是 synthetic/demo data。",
        "- 当前 V0.5 case_count=4，direction_accuracy=0.0，不支持任何交易结论。",
        "- 不可作为交易依据。",
        "",
        "## Safety Boundary",
        "",
        "- 非交易建议。",
        "- 不下单。",
        "- 不回写主项目。",
        "- 不访问主项目数据库。",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return can_enter_v10


def build_not_executed_result(checkpoint_root: Path) -> dict[str, Any]:
    return {
        "status": "PRECHECK_ONLY",
        "started_at": None,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": 0.0,
        "torch_version": None,
        "cuda_available": None,
        "gpu_name": "N/A",
        "max_memory_allocated_mb": None,
        "loss_before": None,
        "loss_after": None,
        "optimizer_step_executed": False,
        "checkpoint_files_created": 0,
        "checkpoint_root": checkpoint_root.as_posix(),
        "error_message": "Preflight only; pass --execute-smoke to run exactly one training step.",
    }


def run(
    *,
    config_path: str | Path = ROOT / "configs" / "kronos_predictor_smoke.yaml",
    execute_smoke: bool = False,
) -> dict[str, Any]:
    config = load_config(config_path)
    inputs = config["inputs"]
    outputs = config["outputs"]
    smoke_config = config_from_dict(config)
    readiness = load_json(resolve_project_path(inputs["readiness_json_path"]))
    dryrun_manifest = load_json(resolve_project_path(inputs["dryrun_manifest_path"]))
    checkpoint_root = resolve_project_path(outputs["ignored_checkpoint_root"])
    result_path = resolve_project_path(outputs["smoke_result_path"])
    log_path = resolve_project_path(outputs["smoke_log_path"])
    report_path = resolve_project_path(outputs["report_path"])
    kronos_root = ROOT / "external" / "Kronos"
    checkpoint_root.mkdir(parents=True, exist_ok=True)

    gate = validate_predictor_smoke_gate(readiness, dryrun_manifest, smoke_config, explicit_execute=execute_smoke)
    inspection = inspect_official_predictor_training_entry(kronos_root)
    plan = build_smoke_training_plan(kronos_root, checkpoint_root, smoke_config)
    if gate["gate_status"] == "PASS" and execute_smoke:
        smoke_result = run_predictor_1step_smoke(ROOT, kronos_root, smoke_config, checkpoint_root)
    else:
        smoke_result = build_not_executed_result(checkpoint_root)

    pytest_status, pytest_summary = run_pytest_quiet()
    payload = {
        "mode": config["mode"],
        "gate": gate,
        "inspection": inspection,
        "plan": plan,
        "smoke_result": smoke_result,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
        "no_formal_training": True,
        "no_long_torchrun": True,
        "no_tokenizer_finetune": True,
        "no_full_finetune": True,
        "no_kronos_large_download": True,
    }
    write_json(payload, result_path)
    log_lines = [
        f"mode={config['mode']}",
        f"gate_status={gate['gate_status']}",
        f"smoke_status={smoke_result['status']}",
        f"predictor_only={gate['predictor_only']}",
        f"tokenizer_finetune={gate['tokenizer_finetune']}",
        f"full_finetune={gate['full_finetune']}",
        f"max_steps={gate['max_steps']}",
        f"batch_size={gate['batch_size']}",
        f"nproc_per_node={gate['nproc_per_node']}",
        f"loss_before={smoke_result.get('loss_before')}",
        f"loss_after={smoke_result.get('loss_after')}",
        f"optimizer_step_executed={smoke_result.get('optimizer_step_executed')}",
        f"max_memory_allocated_mb={smoke_result.get('max_memory_allocated_mb')}",
        f"checkpoint_files_created={smoke_result.get('checkpoint_files_created')}",
        f"checkpoint_root={checkpoint_root}",
        "no_formal_training=true",
        f"pytest_status={pytest_status}",
    ]
    write_log(log_path, log_lines)
    can_enter_v10 = write_report(
        report_path=report_path,
        config=config,
        gate=gate,
        inspection=inspection,
        plan=plan,
        smoke_result=smoke_result,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "config": config,
        "gate": gate,
        "inspection": inspection,
        "plan": plan,
        "smoke_result": smoke_result,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
        "can_enter_v10": can_enter_v10,
        "result_path": result_path,
        "log_path": log_path,
        "report_path": report_path,
        "checkpoint_root": checkpoint_root,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V0.9 predictor-only one-step smoke training.")
    parser.add_argument("--execute-smoke", action="store_true", help="Execute exactly one smoke training step.")
    args = parser.parse_args(argv)
    output = run(execute_smoke=args.execute_smoke)
    gate = output["gate"]
    smoke_result = output["smoke_result"]
    pytest_status = output["pytest_status"]
    can_enter_v10 = bool(output["can_enter_v10"])

    print(f"mode={output['config']['mode']}")
    print(f"gate_status={gate['gate_status']}")
    print(f"smoke_status={smoke_result['status']}")
    print(f"predictor_only={gate['predictor_only']}")
    print(f"tokenizer_finetune={gate['tokenizer_finetune']}")
    print(f"full_finetune={gate['full_finetune']}")
    print(f"max_steps={gate['max_steps']}")
    print(f"batch_size={gate['batch_size']}")
    print(f"nproc_per_node={gate['nproc_per_node']}")
    print(f"loss_before={smoke_result.get('loss_before')}")
    print(f"loss_after={smoke_result.get('loss_after')}")
    print(f"optimizer_step_executed={smoke_result.get('optimizer_step_executed')}")
    print(f"max_memory_allocated_mb={smoke_result.get('max_memory_allocated_mb')}")
    print(f"checkpoint_files_created={smoke_result.get('checkpoint_files_created')}")
    print(f"checkpoint_root={output['checkpoint_root']}")
    print("no_formal_training=true")
    print("")
    print("V0.9 总结")
    print("1. 是否完成官方 predictor 训练入口研究: 是")
    print("2. 是否实现 PredictorSmokeConfig: 是")
    print("3. 是否实现 predictor smoke gate: 是")
    print("4. 是否生成 smoke training plan: 是")
    print(f"5. 是否执行 1-step smoke training: {'是' if smoke_result['status'] == 'PASS' else '否'}")
    print(f"6. gate_status: {gate['gate_status']}")
    print(f"7. smoke_status: {smoke_result['status']}")
    print(f"8. predictor_only: {gate['predictor_only']}")
    print(f"9. tokenizer_finetune: {gate['tokenizer_finetune']}")
    print(f"10. full_finetune: {gate['full_finetune']}")
    print(f"11. max_steps: {gate['max_steps']}")
    print(f"12. batch_size: {gate['batch_size']}")
    print(f"13. nproc_per_node: {gate['nproc_per_node']}")
    print(f"14. loss_before: {smoke_result.get('loss_before')}")
    print(f"15. loss_after: {smoke_result.get('loss_after')}")
    print(f"16. optimizer_step_executed: {smoke_result.get('optimizer_step_executed')}")
    print(f"17. max_memory_allocated_mb: {smoke_result.get('max_memory_allocated_mb')}")
    print(f"18. checkpoint_files_created: {smoke_result.get('checkpoint_files_created')}")
    print(f"19. checkpoint_root: {output['checkpoint_root']}")
    print("20. 是否未执行正式训练: 是")
    print("21. 是否未运行长时间 torchrun: 是")
    print("22. 是否未提交 checkpoint: 是")
    print("23. 是否未下载 Kronos-large: 是")
    print(f"24. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("25. 是否生成 docs/kronos_predictor_smoke_design.md: 是")
    print("26. 是否生成 docs/kronos_v09_predictor_smoke_report.md: 是")
    print(f"27. 是否可以进入 V0.10 真实 ETF 长周期数据准备与回放扩容: {'是' if can_enter_v10 else '否'}")
    print("")
    if not args.execute_smoke:
        print("Preflight only: 未传入 --execute-smoke，因此未执行 1-step smoke training。")
        return 0
    if can_enter_v10:
        print("A. V0.9 PASS，可以进入 V0.10 真实 ETF 长周期数据准备与回放扩容。")
        return 0
    if smoke_result["status"] == "BLOCKED":
        print("B. V0.9 BLOCKED，暂不可进入 V0.10。官方训练入口或环境不允许安全执行 1-step smoke，请列出阻塞原因和下一步修复建议。")
        return 2
    print("C. V0.9 FAIL，暂不可进入 V0.10。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
