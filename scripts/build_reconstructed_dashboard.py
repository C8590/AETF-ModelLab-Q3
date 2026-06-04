#!/usr/bin/env python3
"""Build V0.13-R reconstructed branch dashboard artifacts without model inference."""

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

from model_lab.reconstructed_dashboard import (  # noqa: E402
    build_dashboard_payload,
    build_reconstructed_diagnostics,
    load_v12r_outputs,
    render_reconstructed_dashboard_html,
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
    if config.get("mode") != "reconstructed_branch_dashboard":
        raise ValueError("mode must be reconstructed_branch_dashboard.")
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
            raise ValueError(f"safety.{key} must be false for V0.13-R.")


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
    diagnostics: dict[str, Any],
    payload: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    can_enter_v14r = pytest_status == "PASS"
    lines = [
        "# Kronos V0.13-R Reconstructed Dashboard Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 summary 路径: {inputs['summary_json_path']}",
        f"- 输入 metrics 路径: {inputs['metrics_path']}",
        f"- 输入 by_symbol 路径: {inputs['group_by_symbol_path']}",
        f"- 输入 by_rank 路径: {inputs['group_by_rank_path']}",
        f"- 输入 by_month 路径: {inputs['group_by_month_path']}",
        f"- 输出 dashboard JSON 路径: {outputs['dashboard_json_path']}",
        f"- 输出 dashboard HTML 路径: {outputs['dashboard_html_path']}",
        f"- 输出 diagnostics JSON 路径: {outputs['diagnostic_json_path']}",
        f"- candidate_history_type: {diagnostics['candidate_history_type']}",
        f"- evaluated_case_count: {diagnostics['evaluated_case_count']}",
        f"- direction_accuracy: {diagnostics['direction_accuracy']}",
        f"- V0.11-R baseline direction_accuracy: {diagnostics['v11r_baseline_direction_accuracy']}",
        f"- direction_accuracy_delta_vs_v11r: {diagnostics['direction_accuracy_delta_vs_v11r']}",
        f"- mean_abs_return_error: {diagnostics['mean_abs_return_error']}",
        f"- median_abs_return_error: {diagnostics['median_abs_return_error']}",
        f"- rmse_return_error: {diagnostics['rmse_return_error']}",
        f"- performance_interpretation: {', '.join(diagnostics['performance_interpretation'])}",
        f"- stability_warning: {diagnostics['stability_warning']}",
        f"- 是否 formal_v011_ready: {str(diagnostics['formal_v011_ready']).lower()}",
        f"- 是否 reconstructed_branch_only: {str(diagnostics['reconstructed_branch_only']).lower()}",
        f"- 是否未训练: {str(diagnostics['no_training']).lower()}",
        f"- 是否未运行 torchrun: {str(diagnostics['no_torchrun']).lower()}",
        f"- 是否未调用 GPU: {str(diagnostics['no_gpu_call']).lower()}",
        "- 是否可以进入正式 V0.11: false",
        f"- 是否可以进入 V0.14-R reconstructed 误差诊断或停止线: {str(can_enter_v14r).lower()}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "",
        "## 结论说明",
        "",
        "- reconstructed candidate history 不是真实左侧历史候选池。",
        "- V0.12-R 全量结果没有确认 V0.11-R 200-case baseline 的稳定性。",
        "- 当前 direction_accuracy=0.4094，不支持交易结论。",
        "- 本次不是正式 V0.13。",
        "- 本次未训练、未微调、未调用 GPU。",
        "- 不可作为交易依据。",
        "- Dashboard safety banner: " + " | ".join(payload.get("safety_banner", [])),
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_reconstructed_dashboard.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    outputs = config["outputs"]
    inputs = load_v12r_outputs(config)
    diagnostics = build_reconstructed_diagnostics(inputs)
    payload = build_dashboard_payload(inputs, diagnostics, config)

    dashboard_json_path = resolve_project_path(outputs["dashboard_json_path"])
    dashboard_html_path = resolve_project_path(outputs["dashboard_html_path"])
    diagnostic_json_path = resolve_project_path(outputs["diagnostic_json_path"])
    report_path = resolve_project_path(outputs["report_path"])

    write_json(payload, dashboard_json_path)
    write_json(diagnostics, diagnostic_json_path)
    render_reconstructed_dashboard_html(payload, dashboard_html_path)
    pytest_status, pytest_summary = run_pytest_quiet()
    build_report(
        report_path=report_path,
        config=config,
        diagnostics=diagnostics,
        payload=payload,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "config": config,
        "diagnostics": diagnostics,
        "payload": payload,
        "dashboard_json_path": dashboard_json_path,
        "dashboard_html_path": dashboard_html_path,
        "diagnostic_json_path": diagnostic_json_path,
        "report_path": report_path,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }


def main() -> int:
    result = run()
    diagnostics = result["diagnostics"]
    pytest_status = result["pytest_status"]
    can_enter_v14r = pytest_status == "PASS"

    print(f"mode={diagnostics['mode']}")
    print(f"candidate_history_type={diagnostics['candidate_history_type']}")
    print(f"evaluated_case_count={diagnostics['evaluated_case_count']}")
    print(f"direction_accuracy={diagnostics['direction_accuracy']}")
    print(f"v11r_baseline_direction_accuracy={diagnostics['v11r_baseline_direction_accuracy']}")
    print(f"direction_accuracy_delta_vs_v11r={diagnostics['direction_accuracy_delta_vs_v11r']}")
    print(f"performance_interpretation={','.join(diagnostics['performance_interpretation'])}")
    print(f"stability_warning={diagnostics['stability_warning']}")
    print("formal_v011_ready=false")
    print("reconstructed_branch_only=true")
    print("not_trading_advice=true")
    print("no_training=true")
    print("no_torchrun=true")
    print("no_gpu_call=true")
    print(f"dashboard_json_path={result['dashboard_json_path']}")
    print(f"dashboard_html_path={result['dashboard_html_path']}")
    print(f"diagnostic_json_path={result['diagnostic_json_path']}")
    print(f"report_path={result['report_path']}")
    print(f"pytest={pytest_status} ({result['pytest_summary']})")
    print("")
    if can_enter_v14r:
        print("A. V0.13-R PASS，可以进入 V0.14-R reconstructed 误差诊断或停止线；但不能进入正式 V0.11。")
        return 0
    print("B. V0.13-R FAIL，请列出原因。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
