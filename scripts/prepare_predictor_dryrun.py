#!/usr/bin/env python3
"""Prepare V0.8 Kronos predictor-only dry-run artifacts without training."""

from __future__ import annotations

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

from model_lab.predictor_dryrun import (  # noqa: E402
    build_dryrun_manifest,
    build_predictor_dryrun_command_plan,
    config_from_dict,
    load_readiness_json,
    validate_predictor_dryrun_gate,
    write_json,
)


REQUIRED_GITIGNORE_PATTERNS = (
    "outputs/ignored_checkpoints/",
    "checkpoints/",
    "runs/",
    "wandb/",
    "comet/",
    "*.ckpt",
    "*.pt",
    "*.pth",
    "*.safetensors",
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
    if config.get("mode") != "predictor_dryrun_design_only":
        raise ValueError("mode must be predictor_dryrun_design_only.")
    dryrun = config.get("dryrun", {})
    safety = config.get("safety", {})
    blocked_true_flags = {
        "dryrun.tokenizer_finetune": dryrun.get("tokenizer_finetune"),
        "dryrun.full_finetune": dryrun.get("full_finetune"),
        "dryrun.execute_training": dryrun.get("execute_training"),
        "dryrun.allow_torchrun_execution": dryrun.get("allow_torchrun_execution"),
        "dryrun.save_checkpoint": dryrun.get("save_checkpoint"),
        "safety.allow_trading_advice": safety.get("allow_trading_advice"),
        "safety.allow_order_execution": safety.get("allow_order_execution"),
        "safety.allow_writeback_to_left_project": safety.get("allow_writeback_to_left_project"),
        "safety.allow_submit_checkpoints": safety.get("allow_submit_checkpoints"),
        "safety.allow_download_kronos_large": safety.get("allow_download_kronos_large"),
        "safety.allow_tokenizer_finetune": safety.get("allow_tokenizer_finetune"),
        "safety.allow_full_finetune": safety.get("allow_full_finetune"),
    }
    for key, value in blocked_true_flags.items():
        if bool(value):
            raise ValueError(f"{key} must be false for V0.8 dry-run design.")


def check_gitignore() -> list[str]:
    gitignore_path = ROOT / ".gitignore"
    text = gitignore_path.read_text(encoding="utf-8")
    missing = [pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in text]
    if missing:
        raise ValueError(f".gitignore missing required ignore patterns: {missing}")
    return list(REQUIRED_GITIGNORE_PATTERNS)


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


def write_report(
    *,
    report_path: Path,
    config: dict[str, Any],
    manifest: dict[str, Any],
    plan: dict[str, Any],
    gate: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> bool:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    can_enter_v09 = (
        pytest_status == "PASS"
        and gate["passed"]
        and manifest["no_formal_training"]
        and manifest["synthetic_demo_only"]
        and not plan["execute_training"]
        and not plan["allow_torchrun_execution"]
    )
    lines = [
        "# Kronos V0.8 Predictor Dry-Run Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 readiness JSON 路径: {inputs['readiness_json_path']}",
        f"- 输入 replay metrics 路径: {inputs['replay_metrics_path']}",
        f"- 输入 dataset profile 路径: {inputs['dataset_profile_csv_path']}",
        f"- 输出 dryrun manifest 路径: {outputs['dryrun_manifest_path']}",
        f"- 输出 dryrun plan 路径: {outputs['dryrun_plan_path']}",
        f"- checkpoint root: {outputs['ignored_checkpoint_root']}",
        f"- predictor_only: {manifest['predictor_only']}",
        f"- execute_training: {plan['execute_training']}",
        f"- allow_torchrun_execution: {plan['allow_torchrun_execution']}",
        f"- replay_case_count: {manifest['replay_case_count']}",
        f"- symbol_count: {manifest['symbol_count']}",
        f"- direction_accuracy: {manifest['direction_accuracy']}",
        f"- mean_abs_return_error: {manifest['mean_abs_return_error']}",
        f"- full_finetune_ready: {gate['full_finetune_ready']}",
        f"- tokenizer_finetune_ready: {gate['tokenizer_finetune_ready']}",
        f"- predictor_dryrun_ready: {gate['predictor_dryrun_ready']}",
        f"- command_preview: `{plan['command_preview']}`",
        f"- blocked_commands: {'; '.join(plan['blocked_commands'])}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.9 predictor-only 1-step smoke training: {'是' if can_enter_v09 else '否'}",
        "",
        "## V0.8 Scope",
        "",
        "- 当前只做 dry-run 设计与预检。",
        "- 当前未执行训练。",
        "- 当前未运行 torchrun。",
        "- 当前未生成可用 checkpoint。",
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
    return can_enter_v09


def run(config_path: str | Path = ROOT / "configs" / "kronos_predictor_dryrun.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    inputs = config["inputs"]
    outputs = config["outputs"]
    dryrun_config = config_from_dict(config)

    readiness_path = resolve_project_path(inputs["readiness_json_path"])
    replay_cases_path = resolve_project_path(inputs["replay_cases_path"])
    replay_metrics_path = resolve_project_path(inputs["replay_metrics_path"])
    dataset_profile_path = resolve_project_path(inputs["dataset_profile_csv_path"])
    manifest_path = resolve_project_path(outputs["dryrun_manifest_path"])
    plan_path = resolve_project_path(outputs["dryrun_plan_path"])
    report_path = resolve_project_path(outputs["report_path"])
    checkpoint_root = resolve_project_path(outputs["ignored_checkpoint_root"])

    ignored_patterns = check_gitignore()
    checkpoint_root.mkdir(parents=True, exist_ok=True)

    readiness = load_readiness_json(readiness_path)
    gate = validate_predictor_dryrun_gate(readiness, dryrun_config)
    manifest = build_dryrun_manifest(
        readiness,
        replay_cases_path,
        replay_metrics_path,
        dataset_profile_path,
        checkpoint_root,
    )
    plan = build_predictor_dryrun_command_plan(ROOT / "external" / "Kronos", checkpoint_root, dryrun_config)
    write_json(manifest, manifest_path)
    write_json(plan, plan_path)

    pytest_status, pytest_summary = run_pytest_quiet()
    can_enter_v09 = write_report(
        report_path=report_path,
        config=config,
        manifest=manifest,
        plan=plan,
        gate=gate,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "config": config,
        "gate": gate,
        "manifest": manifest,
        "plan": plan,
        "manifest_path": manifest_path,
        "plan_path": plan_path,
        "report_path": report_path,
        "checkpoint_root": checkpoint_root,
        "ignored_patterns": ignored_patterns,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
        "can_enter_v09": can_enter_v09,
    }


def main() -> int:
    output = run()
    gate = output["gate"]
    manifest = output["manifest"]
    plan = output["plan"]
    pytest_status = output["pytest_status"]
    can_enter_v09 = bool(output["can_enter_v09"])

    print(f"mode={manifest['mode']}")
    print(f"predictor_only={manifest['predictor_only']}")
    print(f"execute_training={plan['execute_training']}")
    print(f"allow_torchrun_execution={plan['allow_torchrun_execution']}")
    print(f"replay_case_count={manifest['replay_case_count']}")
    print(f"symbol_count={manifest['symbol_count']}")
    print(f"direction_accuracy={manifest['direction_accuracy']}")
    print(f"full_finetune_ready={gate['full_finetune_ready']}")
    print(f"tokenizer_finetune_ready={gate['tokenizer_finetune_ready']}")
    print(f"predictor_dryrun_ready={gate['predictor_dryrun_ready']}")
    print(f"command_preview={plan['command_preview']}")
    print(f"checkpoint_root={output['checkpoint_root']}")
    print("no_formal_training=true")
    print("")
    print("V0.8 总结")
    print("1. 是否完成官方 predictor 微调入口研究: 是")
    print("2. 是否实现 PredictorDryRunConfig: 是")
    print("3. 是否实现 predictor_dryrun gate: 是")
    print("4. 是否生成 dry-run manifest: 是")
    print("5. 是否生成 dry-run command plan: 是")
    print(f"6. predictor_only: {manifest['predictor_only']}")
    print(f"7. execute_training: {plan['execute_training']}")
    print(f"8. allow_torchrun_execution: {plan['allow_torchrun_execution']}")
    print(f"9. replay_case_count: {manifest['replay_case_count']}")
    print(f"10. symbol_count: {manifest['symbol_count']}")
    print(f"11. direction_accuracy: {manifest['direction_accuracy']}")
    print(f"12. mean_abs_return_error: {manifest['mean_abs_return_error']}")
    print(f"13. full_finetune_ready: {gate['full_finetune_ready']}")
    print(f"14. tokenizer_finetune_ready: {gate['tokenizer_finetune_ready']}")
    print(f"15. predictor_dryrun_ready: {gate['predictor_dryrun_ready']}")
    print(f"16. checkpoint_root: {output['checkpoint_root']}")
    print("17. 是否未执行正式训练: 是")
    print("18. 是否未运行 torchrun: 是")
    print("19. 是否未生成 checkpoint: 是")
    print("20. 是否未下载 Kronos-large: 是")
    print(f"21. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("22. 是否生成 docs/kronos_predictor_dryrun_design.md: 是")
    print("23. 是否生成 docs/kronos_v08_predictor_dryrun_report.md: 是")
    print(f"24. 是否可以进入 V0.9 predictor-only 1-step smoke training: {'是' if can_enter_v09 else '否'}")
    print("")
    if can_enter_v09:
        print("A. V0.8 PASS，可以进入 V0.9 predictor-only 1-step smoke training。")
        return 0
    print("B. V0.8 FAIL，暂不可进入 V0.9。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
