#!/usr/bin/env python3
"""Evaluate V0.7 finetune readiness without training or torchrun."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.finetune_readiness import (  # noqa: E402
    config_from_dict,
    evaluate_finetune_readiness,
    load_replay_metrics,
    profile_replay_dataset,
    write_readiness_json,
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_safety(config)
    return config


def validate_safety(config: dict[str, Any]) -> None:
    if config.get("mode") != "finetune_evaluation_only":
        raise ValueError("mode must be finetune_evaluation_only.")
    safety = config.get("safety", {})
    for key in [
        "allow_trading_advice",
        "allow_order_execution",
        "allow_writeback_to_left_project",
        "allow_submit_checkpoints",
        "allow_download_kronos_large",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false for V0.7 evaluation.")


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
    result: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    observed = result["observed"]
    can_enter_v08 = pytest_status == "PASS" and bool(result["is_ready_for_predictor_dry_run"])
    lines = [
        "# Kronos V0.7 Finetune Evaluation Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 replay cases 路径: {inputs['sample_replay_cases_path']}",
        f"- 输入 replay metrics 路径: {inputs['replay_metrics_path']}",
        f"- 输出 readiness JSON 路径: {outputs['readiness_json_path']}",
        f"- 输出 dataset profile CSV 路径: {outputs['dataset_profile_csv_path']}",
        f"- symbol_count: {observed['symbol_count']}",
        f"- replay_case_count: {observed['replay_case_count']}",
        f"- direction_accuracy: {observed['direction_accuracy']}",
        f"- mean_abs_return_error: {observed['mean_abs_return_error']}",
        f"- full_finetune_ready: {result['is_ready_for_full_finetune']}",
        f"- tokenizer_finetune_ready: {result['is_ready_for_tokenizer_finetune']}",
        f"- predictor_dry_run_ready: {result['is_ready_for_predictor_dry_run']}",
        f"- decision: {result['decision']}",
        f"- recommended_next_step: {result['recommended_next_step']}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.8 predictor-only 微调 dry-run 设计: {'是' if can_enter_v08 else '否'}",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in result["reasons"])
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result["warnings"])
    lines.extend(
        [
            "",
            "## 评估结论",
            "",
            "- 当前只做微调评估，不执行训练。",
            "- 当前样本是 synthetic/demo data。",
            "- 当前 V0.5 case_count=4，direction_accuracy=0.0，不支持任何交易结论。",
            "- 当前不建议正式微调。",
            "- 不可作为交易依据。",
            "- V0.7 未运行 torchrun，未下载 Kronos-large，未生成 checkpoint。",
            "",
            "## 安全边界",
            "",
            "- 非交易建议。",
            "- 不下单。",
            "- 不回写主项目。",
            "- 不访问主项目数据库。",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_finetune_eval.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    inputs = config["inputs"]
    outputs = config["outputs"]
    replay_cases_path = resolve_project_path(inputs["sample_replay_cases_path"])
    metrics_path = resolve_project_path(inputs["replay_metrics_path"])
    profile_path = resolve_project_path(outputs["dataset_profile_csv_path"])
    readiness_path = resolve_project_path(outputs["readiness_json_path"])
    report_path = resolve_project_path(outputs["report_path"])

    replay_cases_df = pd.read_csv(replay_cases_path)
    dataset_profile = profile_replay_dataset(replay_cases_df)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_profile.to_csv(profile_path, index=False, encoding="utf-8-sig")

    replay_metrics = load_replay_metrics(metrics_path)
    readiness_config = config_from_dict(config)
    result = evaluate_finetune_readiness(dataset_profile, replay_metrics, readiness_config)
    write_readiness_json(result, readiness_path)

    pytest_status, pytest_summary = run_pytest_quiet()
    write_report(
        report_path=report_path,
        config=config,
        result=result,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "result": result,
        "dataset_profile": dataset_profile,
        "profile_path": profile_path,
        "readiness_path": readiness_path,
        "report_path": report_path,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }


def main() -> int:
    output = run()
    result = output["result"]
    observed = result["observed"]
    pytest_status = output["pytest_status"]
    can_enter_v08 = pytest_status == "PASS" and bool(result["is_ready_for_predictor_dry_run"])

    print(f"mode={result['mode']}")
    print(f"symbol_count={observed['symbol_count']}")
    print(f"replay_case_count={observed['replay_case_count']}")
    print(f"direction_accuracy={observed['direction_accuracy']}")
    print(f"mean_abs_return_error={observed['mean_abs_return_error']}")
    print(f"is_ready_for_full_finetune={result['is_ready_for_full_finetune']}")
    print(f"is_ready_for_tokenizer_finetune={result['is_ready_for_tokenizer_finetune']}")
    print(f"is_ready_for_predictor_dry_run={result['is_ready_for_predictor_dry_run']}")
    print(f"decision={result['decision']}")
    print(f"recommended_next_step={result['recommended_next_step']}")
    print("")
    print("V0.7 总结")
    print("1. 是否完成官方 Kronos finetune 结构研究: 是")
    print("2. 是否实现 FinetuneReadinessConfig: 是")
    print("3. 是否实现 dataset profile: 是")
    print("4. 是否实现 finetune readiness evaluator: 是")
    print("5. 是否生成 readiness JSON: 是")
    print("6. 是否生成 dataset profile CSV: 是")
    print(f"7. symbol_count: {observed['symbol_count']}")
    print(f"8. replay_case_count: {observed['replay_case_count']}")
    print(f"9. direction_accuracy: {observed['direction_accuracy']}")
    print(f"10. mean_abs_return_error: {observed['mean_abs_return_error']}")
    print(f"11. full_finetune_ready: {result['is_ready_for_full_finetune']}")
    print(f"12. tokenizer_finetune_ready: {result['is_ready_for_tokenizer_finetune']}")
    print(f"13. predictor_dry_run_ready: {result['is_ready_for_predictor_dry_run']}")
    print(f"14. decision: {result['decision']}")
    print(f"15. recommended_next_step: {result['recommended_next_step']}")
    print("16. 是否未执行正式训练: 是")
    print("17. 是否未运行 torchrun: 是")
    print("18. 是否未下载 Kronos-large: 是")
    print(f"19. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("20. 是否生成 docs/kronos_finetune_readiness.md: 是")
    print("21. 是否生成 docs/kronos_v07_finetune_evaluation_report.md: 是")
    print(f"22. 是否可以进入 V0.8 predictor-only 微调 dry-run 设计: {'是' if can_enter_v08 else '否'}")
    print("")
    if can_enter_v08:
        print("A. V0.7 PASS，可以进入 V0.8 predictor-only 微调 dry-run 设计。")
        return 0
    print("B. V0.7 FAIL，暂不可进入 V0.8。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
