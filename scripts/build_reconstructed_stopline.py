#!/usr/bin/env python3
"""Build V0.14-R reconstructed branch stopline artifacts without model inference."""

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

from model_lab.reconstructed_stopline import (  # noqa: E402
    build_group_error_table,
    build_stopline_decision,
    compute_direction_confusion,
    compute_error_distribution,
    compute_extreme_errors,
    compute_majority_direction_baseline,
    diagnose_group_stability,
    load_json,
    wilson_interval,
    write_json,
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_config(config)
    return _resolve_paths_in_config(config)


def validate_config(config: dict[str, Any]) -> None:
    if config.get("mode") != "reconstructed_branch_error_diagnostics_stopline":
        raise ValueError("mode must be reconstructed_branch_error_diagnostics_stopline.")
    evaluation = config.get("evaluation", {})
    if evaluation.get("candidate_history_type") != "reconstructed_not_true_left_snapshot":
        raise ValueError("evaluation.candidate_history_type must be reconstructed_not_true_left_snapshot.")
    if bool(evaluation.get("allow_formal_v011_claim")):
        raise ValueError("evaluation.allow_formal_v011_claim must be false.")
    if not bool(evaluation.get("allow_reconstructed_branch_claim")):
        raise ValueError("evaluation.allow_reconstructed_branch_claim must be true.")
    safety = config.get("safety", {})
    for key in [
        "allow_training",
        "allow_torchrun",
        "allow_gpu_inference",
        "allow_trading_advice",
        "allow_order_execution",
        "allow_writeback_to_left_project",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false for V0.14-R.")


def _resolve_paths_in_config(config: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(config)
    resolved["inputs"] = {
        key: str(resolve_project_path(value))
        for key, value in config.get("inputs", {}).items()
    }
    resolved["outputs"] = {
        key: str(resolve_project_path(value))
        for key, value in config.get("outputs", {}).items()
    }
    return resolved


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


def build_report(
    *,
    report_path: Path,
    config: dict[str, Any],
    stopline: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    can_enter_v15r = stopline["decision"] == "PAUSE_RECONSTRUCTED_BRANCH" and pytest_status == "PASS"
    lines = [
        "# Kronos V0.14-R Reconstructed Stopline Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 predictions 路径: {inputs['predictions_path']}",
        f"- 输入 summary 路径: {inputs['summary_json_path']}",
        f"- 输入 V0.13-R diagnostics 路径: {inputs['diagnostics_json_path']}",
        f"- 输出 stopline JSON 路径: {outputs['stopline_json_path']}",
        f"- 输出 error diagnostics JSON 路径: {outputs['diagnostics_json_path']}",
        f"- 输出 extreme errors CSV 路径: {outputs['extreme_errors_path']}",
        f"- evaluated_case_count: {stopline['evaluated_case_count']}",
        f"- direction_accuracy: {stopline['direction_accuracy']}",
        f"- majority_direction_accuracy: {stopline['majority_direction_accuracy']}",
        f"- Wilson interval: {stopline['wilson_interval']}",
        f"- mean_abs_return_error: {stopline['mean_abs_return_error']}",
        f"- median_abs_return_error: {stopline['median_abs_return_error']}",
        f"- rmse_return_error: {stopline['rmse_return_error']}",
        f"- direction_accuracy_delta_vs_v11r: {stopline['direction_accuracy_delta_vs_v11r']}",
        f"- decision: {stopline['decision']}",
        f"- decision_level: {stopline['decision_level']}",
        f"- blockers: {', '.join(stopline['blockers'])}",
        f"- next_step: {stopline['next_step']}",
        f"- formal_v011_ready: {str(stopline['formal_v011_ready']).lower()}",
        f"- reconstructed_branch_continue: {str(stopline['reconstructed_branch_continue']).lower()}",
        f"- not_trading_advice: {str(stopline['not_trading_advice']).lower()}",
        f"- no_training: {str(stopline['no_training']).lower()}",
        f"- no_torchrun: {str(stopline['no_torchrun']).lower()}",
        f"- no_gpu_call: {str(stopline['no_gpu_call']).lower()}",
        "- no_left_project_connection: true",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "- 是否可以进入正式 V0.11: false",
        f"- 是否可以进入 V0.15-R 分支收尾或候选池重建规则再设计: {str(can_enter_v15r).lower()}",
        "",
        "## 停止线说明",
        "",
        "- reconstructed candidate history 不是真实左侧历史候选池。",
        "- V0.12-R 全量结果没有确认 V0.11-R 200-case baseline 的稳定性。",
        "- 当前 direction_accuracy=0.4094，低于 50%，不支持继续推进 reconstructed 分支作为有效预测路线。",
        "- 本次不是正式 V0.14。",
        "- 本次未训练、未微调、未调用 GPU。",
        "- 不可作为交易依据。",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_reconstructed_stopline.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    inputs_cfg = config["inputs"]
    outputs_cfg = config["outputs"]
    for key, value in inputs_cfg.items():
        path = resolve_project_path(value)
        if not path.exists():
            raise FileNotFoundError(f"missing V0.14-R input {key}: {path}")

    predictions = pd.read_csv(inputs_cfg["predictions_path"])
    group_by_symbol = pd.read_csv(inputs_cfg["group_by_symbol_path"])
    group_by_rank = pd.read_csv(inputs_cfg["group_by_rank_path"])
    group_by_month = pd.read_csv(inputs_cfg["group_by_month_path"])
    summary = load_json(resolve_project_path(inputs_cfg["summary_json_path"]))
    v13r_diagnostics = load_json(resolve_project_path(inputs_cfg["diagnostics_json_path"]))

    confusion = compute_direction_confusion(predictions)
    majority_baseline = compute_majority_direction_baseline(predictions)
    interval = wilson_interval(confusion["matched_count"], confusion["total_count"])
    error_distribution = compute_error_distribution(predictions)
    extreme_errors = compute_extreme_errors(predictions, top_n=50)

    error_by_symbol = build_group_error_table(group_by_symbol)
    error_by_rank = build_group_error_table(group_by_rank)
    error_by_month = build_group_error_table(group_by_month)
    group_stability = {
        "by_symbol": diagnose_group_stability(group_by_symbol, "symbol"),
        "by_rank": diagnose_group_stability(group_by_rank, "candidate_rank"),
        "by_month": diagnose_group_stability(group_by_month, "month"),
    }
    stopline = build_stopline_decision(
        summary,
        v13r_diagnostics,
        majority_baseline,
        interval,
        error_distribution,
        group_stability,
        config,
    )
    error_diagnostics = {
        "schema_version": "v0.14-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "reconstructed_branch_error_diagnostics",
        "candidate_history_type": stopline["candidate_history_type"],
        "direction_confusion": confusion,
        "majority_direction_baseline": majority_baseline,
        "wilson_interval": interval,
        "error_distribution": error_distribution,
        "group_stability": group_stability,
        "not_trading_advice": True,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu_call": True,
        "left_project_writeback_allowed": False,
    }

    output_paths = {key: resolve_project_path(value) for key, value in outputs_cfg.items()}
    for key, path in output_paths.items():
        if key.endswith("_path"):
            path.parent.mkdir(parents=True, exist_ok=True)
    write_json(stopline, output_paths["stopline_json_path"])
    write_json(error_diagnostics, output_paths["diagnostics_json_path"])
    error_by_symbol.to_csv(output_paths["error_by_symbol_path"], index=False)
    error_by_rank.to_csv(output_paths["error_by_rank_path"], index=False)
    error_by_month.to_csv(output_paths["error_by_month_path"], index=False)
    extreme_errors.to_csv(output_paths["extreme_errors_path"], index=False)
    pytest_status, pytest_summary = run_pytest_quiet()
    build_report(
        report_path=output_paths["report_path"],
        config=config,
        stopline=stopline,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "config": config,
        "stopline": stopline,
        "error_diagnostics": error_diagnostics,
        "output_paths": output_paths,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }


def main() -> int:
    result = run()
    stopline = result["stopline"]
    pytest_status = result["pytest_status"]
    stopline_pass = (
        pytest_status == "PASS"
        and stopline["decision"] in {"PAUSE_RECONSTRUCTED_BRANCH", "RECONSTRUCTED_BRANCH_NOT_SUPPORTED_BY_FULL_EXPANSION"}
    )
    print(f"evaluated_case_count={stopline['evaluated_case_count']}")
    print(f"direction_accuracy={stopline['direction_accuracy']}")
    print(f"majority_direction_accuracy={stopline['majority_direction_accuracy']}")
    print(f"wilson_interval={stopline['wilson_interval']}")
    print(f"mean_abs_return_error={stopline['mean_abs_return_error']}")
    print(f"median_abs_return_error={stopline['median_abs_return_error']}")
    print(f"rmse_return_error={stopline['rmse_return_error']}")
    print(f"direction_accuracy_delta_vs_v11r={stopline['direction_accuracy_delta_vs_v11r']}")
    print(f"group_stability_generated={bool(stopline['group_stability'])}")
    print(f"decision={stopline['decision']}")
    print(f"decision_level={stopline['decision_level']}")
    print(f"blockers={','.join(stopline['blockers'])}")
    print(f"next_step={stopline['next_step']}")
    print(f"formal_v011_ready={str(stopline['formal_v011_ready']).lower()}")
    print(f"reconstructed_branch_continue={str(stopline['reconstructed_branch_continue']).lower()}")
    print(f"not_trading_advice={str(stopline['not_trading_advice']).lower()}")
    print(f"no_training={str(stopline['no_training']).lower()}")
    print(f"no_torchrun={str(stopline['no_torchrun']).lower()}")
    print(f"no_gpu_call={str(stopline['no_gpu_call']).lower()}")
    print("no_left_project_connection=true")
    print(f"pytest={pytest_status} ({result['pytest_summary']})")
    print("")
    if stopline_pass:
        print("A. V0.14-R STOPLINE PASS，建议暂停当前 reconstructed 分支；可以进入 V0.15-R 分支收尾或候选池重建规则再设计；不能进入正式 V0.11。")
        return 0
    if pytest_status == "PASS":
        print("B. V0.14-R CONTINUE PASS，可以进入 V0.15-R reconstructed 分支扩展；但不能进入正式 V0.11。")
        return 0
    print("C. V0.14-R FAIL，请列出原因。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
