#!/usr/bin/env python3
"""Build V0.15-R reconstructed branch closeout artifacts."""

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

from model_lab.reconstructed_closeout import (  # noqa: E402
    build_artifact_index,
    build_next_step_decision_matrix,
    build_reconstructed_closeout,
    load_json_if_exists,
    write_json,
)


EXPECTED_REPORT_PATHS = [
    "docs/kronos_v10_reconstructed_candidate_history_report.md",
    "docs/kronos_v11r_reconstructed_replay_report.md",
    "docs/kronos_v12r_reconstructed_expansion_report.md",
    "docs/kronos_v13r_reconstructed_dashboard_report.md",
    "docs/kronos_v14r_reconstructed_stopline_report.md",
]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_config(config)
    return _resolve_paths_in_config(config)


def validate_config(config: dict[str, Any]) -> None:
    if config.get("mode") != "reconstructed_branch_closeout":
        raise ValueError("mode must be reconstructed_branch_closeout.")
    closeout = config.get("closeout", {})
    if closeout.get("candidate_history_type") != "reconstructed_not_true_left_snapshot":
        raise ValueError("closeout.candidate_history_type must be reconstructed_not_true_left_snapshot.")
    if bool(closeout.get("formal_v011_ready")):
        raise ValueError("closeout.formal_v011_ready must be false.")
    if bool(closeout.get("reconstructed_branch_continue")):
        raise ValueError("closeout.reconstructed_branch_continue must be false.")
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
            raise ValueError(f"safety.{key} must be false for V0.15-R.")


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
    closeout: dict[str, Any],
    decision_matrix: dict[str, Any],
    artifact_index: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_summary = [
        f"{item['path']}: {item['status']} - {item['reason']}"
        for item in decision_matrix.get("paths", [])
    ]
    lines = [
        "# Kronos V0.15-R Reconstructed Branch Closeout Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- branch_name: {closeout['branch_name']}",
        f"- candidate_history_type: {closeout['candidate_history_type']}",
        f"- final_branch_status: {closeout['final_branch_status']}",
        f"- final_decision: {closeout['final_decision']}",
        f"- evaluated_case_count: {closeout['evaluated_case_count']}",
        f"- direction_accuracy: {closeout['direction_accuracy']}",
        f"- majority_direction_accuracy: {closeout['majority_direction_accuracy']}",
        f"- Wilson interval: {closeout['wilson_interval']}",
        f"- mean_abs_return_error: {closeout['mean_abs_return_error']}",
        f"- rmse_return_error: {closeout['rmse_return_error']}",
        f"- blockers: {', '.join(closeout['blockers'])}",
        f"- lessons learned: {'; '.join(closeout['lessons_learned'])}",
        f"- recommended_next_step: {closeout['recommended_next_step']}",
        f"- next-step decision matrix: {' | '.join(matrix_summary)}",
        f"- artifact_count: {artifact_index['artifact_count']}",
        f"- missing_artifact_count: {artifact_index['missing_artifact_count']}",
        f"- formal_v011_ready: {str(closeout['formal_v011_ready']).lower()}",
        f"- reconstructed_branch_continue: {str(closeout['reconstructed_branch_continue']).lower()}",
        f"- no_training: {str(closeout['no_training']).lower()}",
        f"- no_torchrun: {str(closeout['no_torchrun']).lower()}",
        f"- no_gpu_inference: {str(closeout['no_gpu_inference']).lower()}",
        "- 是否可以进入正式 V0.11: false",
        "- 是否可以进入 V0.10.2-E2 或真实候选池导入: true",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "",
        "## Closeout Conclusion",
        "",
        "- reconstructed candidate history 不是真实左侧历史候选池。",
        "- reconstructed_v1 已被 stopline 暂停。",
        "- 当前结果不支持训练、交易或正式 V0.11。",
        "- 优先路径是获取真实 left_candidates_history.csv。",
        "- 备选路径是重新设计 reconstructed 规则，从 V0.10.2-E2 重新开始。",
        "- 不可作为交易依据。",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_reconstructed_closeout.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    inputs_cfg = config["inputs"]
    outputs_cfg = config["outputs"]
    loaded_inputs = {
        "reconstructed_readiness": load_json_if_exists(resolve_project_path(inputs_cfg["reconstructed_readiness_path"])),
        "v11r_summary": load_json_if_exists(resolve_project_path(inputs_cfg["v11r_summary_path"])),
        "v12r_summary": load_json_if_exists(resolve_project_path(inputs_cfg["v12r_summary_path"])),
        "v13r_diagnostics": load_json_if_exists(resolve_project_path(inputs_cfg["v13r_diagnostics_path"])),
        "v14r_stopline": load_json_if_exists(resolve_project_path(inputs_cfg["v14r_stopline_path"])),
        "v14r_error_diagnostics": load_json_if_exists(resolve_project_path(inputs_cfg["v14r_error_diagnostics_path"])),
    }
    prior_paths = [Path(value) for value in inputs_cfg.values()] + [
        Path(value) for value in EXPECTED_REPORT_PATHS
    ]
    prior_index = build_artifact_index(ROOT, prior_paths)
    closeout = build_reconstructed_closeout(loaded_inputs, prior_index, config)
    decision_matrix = build_next_step_decision_matrix(closeout)

    output_paths = {key: resolve_project_path(value) for key, value in outputs_cfg.items()}
    write_json(closeout, output_paths["closeout_json_path"])
    write_json(decision_matrix, output_paths["decision_matrix_path"])
    final_index = build_artifact_index(
        ROOT,
        prior_paths
        + [
            Path(outputs_cfg["closeout_json_path"]),
            Path(outputs_cfg["decision_matrix_path"]),
            Path(outputs_cfg["artifact_index_path"]),
            Path(outputs_cfg["report_path"]),
            Path(outputs_cfg["design_doc_path"]),
        ],
    )
    write_json(final_index, output_paths["artifact_index_path"])
    pytest_status, pytest_summary = run_pytest_quiet()
    build_report(
        report_path=output_paths["report_path"],
        closeout=closeout,
        decision_matrix=decision_matrix,
        artifact_index=final_index,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    final_index = build_artifact_index(
        ROOT,
        prior_paths
        + [
            Path(outputs_cfg["closeout_json_path"]),
            Path(outputs_cfg["decision_matrix_path"]),
            Path(outputs_cfg["artifact_index_path"]),
            Path(outputs_cfg["report_path"]),
            Path(outputs_cfg["design_doc_path"]),
        ],
    )
    write_json(final_index, output_paths["artifact_index_path"])
    build_report(
        report_path=output_paths["report_path"],
        closeout=closeout,
        decision_matrix=decision_matrix,
        artifact_index=final_index,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "config": config,
        "closeout": closeout,
        "decision_matrix": decision_matrix,
        "artifact_index": final_index,
        "output_paths": output_paths,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }


def main() -> int:
    result = run()
    closeout = result["closeout"]
    pytest_status = result["pytest_status"]
    print(f"branch_name={closeout['branch_name']}")
    print(f"candidate_history_type={closeout['candidate_history_type']}")
    print(f"final_branch_status={closeout['final_branch_status']}")
    print(f"final_decision={closeout['final_decision']}")
    print(f"direction_accuracy={closeout['direction_accuracy']}")
    print(f"majority_direction_accuracy={closeout['majority_direction_accuracy']}")
    print(f"formal_v011_ready={str(closeout['formal_v011_ready']).lower()}")
    print(f"reconstructed_branch_continue={str(closeout['reconstructed_branch_continue']).lower()}")
    print(f"recommended_next_step={closeout['recommended_next_step']}")
    print(f"no_training={str(closeout['no_training']).lower()}")
    print(f"no_torchrun={str(closeout['no_torchrun']).lower()}")
    print(f"no_gpu_inference={str(closeout['no_gpu_inference']).lower()}")
    print("no_left_project_connection=true")
    print(f"pytest={pytest_status} ({result['pytest_summary']})")
    print("")
    if pytest_status == "PASS" and closeout["final_branch_status"] == "PAUSED_BY_STOPLINE":
        print("A. V0.15-R CLOSEOUT PASS，reconstructed_v1 分支正式暂停；下一步优先获取真实 left_candidates_history.csv，或进入 V0.10.2-E2 重建设计；不能进入正式 V0.11。")
        return 0
    print("B. V0.15-R FAIL，请列出原因。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
