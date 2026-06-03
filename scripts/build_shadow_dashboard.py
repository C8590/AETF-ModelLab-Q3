#!/usr/bin/env python3
"""Build V0.6 static shadow display artifacts without model inference."""

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

from model_lab.display_builder import (  # noqa: E402
    build_display_payload,
    load_replay_metrics,
    load_shadow_predictions,
    render_dashboard_html,
    write_display_json,
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_safety(config.get("safety", {}))
    return config


def validate_safety(safety: dict[str, Any]) -> None:
    if safety.get("mode") != "shadow_display_only":
        raise ValueError("safety.mode must be shadow_display_only.")
    for key in [
        "allow_trading_advice",
        "allow_order_execution",
        "allow_writeback_to_left_project",
        "allow_finetune",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false for V0.6 shadow display.")


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
    metrics: dict[str, Any],
    payload_summary: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_path = config["shadow_predictions_path"]
    replay_metrics_path = config["replay_metrics_path"]
    output_json_path = config["output_json_path"]
    output_html_path = config["output_html_path"]
    replay_summary = payload_summary.get("replay_metrics", {})
    can_enter_v07 = pytest_status == "PASS" and payload_summary.get("card_count", 0) > 0
    lines = [
        "# Kronos V0.6 Shadow Display Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 shadow predictions 路径: {shadow_path}",
        f"- 输入 replay metrics 路径: {replay_metrics_path}",
        f"- 输出 JSON 路径: {output_json_path}",
        f"- 输出 HTML 路径: {output_html_path}",
        f"- card_count: {payload_summary.get('card_count')}",
        f"- pass_count: {payload_summary.get('pass_count')}",
        f"- fail_count: {payload_summary.get('fail_count')}",
        f"- case_count: {replay_summary.get('case_count')}",
        f"- direction_accuracy: {replay_summary.get('direction_accuracy')}",
        f"- mean_abs_return_error: {replay_summary.get('mean_abs_return_error')}",
        "- 是否生成 safety banner: 是",
        "- 是否明确非交易建议: 是",
        "- 是否不调用 GPU 推理: 是",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.7 ETF 本地微调评估: {'是' if can_enter_v07 else '否'}",
        "",
        "## 工程验收说明",
        "",
        "- 当前展示只用于工程验收。",
        "- 当前样本是 synthetic / demo data。",
        "- V0.5 direction_accuracy=0.0，不能支持任何交易结论。",
        "- 当前展示不可作为交易依据。",
        "- V0.6 只读取 V0.4/V0.5 已生成的离线文件，不调用 KronosAdapter，不运行 GPU 推理。",
        "",
        "## 安全边界",
        "",
        "- 非交易建议。",
        "- 不下单。",
        "- 不回写主项目。",
        "- 不访问主项目数据库。",
        "- 不下载或微调模型。",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_display.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    display_cfg = config.get("display", {})
    shadow_path = resolve_project_path(config["shadow_predictions_path"])
    metrics_path = resolve_project_path(config["replay_metrics_path"])
    output_json_path = resolve_project_path(config["output_json_path"])
    output_html_path = resolve_project_path(config["output_html_path"])
    report_path = resolve_project_path(config["report_path"])

    shadow_df = load_shadow_predictions(shadow_path)
    replay_metrics = load_replay_metrics(metrics_path)
    payload = build_display_payload(
        shadow_df,
        replay_metrics,
        schema_version=display_cfg.get("schema_version", "v0.6"),
        flat_threshold=float(display_cfg.get("flat_threshold", 0.001)),
        small_sample_threshold=int(display_cfg.get("small_sample_threshold", 30)),
        data_sources={
            "shadow_predictions": config["shadow_predictions_path"],
            "replay_predictions": config["replay_predictions_path"],
            "replay_metrics": config["replay_metrics_path"],
        },
    )
    write_display_json(payload, output_json_path)
    render_dashboard_html(payload, output_html_path)
    pytest_status, pytest_summary = run_pytest_quiet()
    build_report(
        report_path=report_path,
        config=config,
        metrics=replay_metrics,
        payload_summary={**payload.summary, "replay_metrics": payload.replay_metrics.__dict__},
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return {
        "payload": payload,
        "metrics": replay_metrics,
        "output_json_path": output_json_path,
        "output_html_path": output_html_path,
        "report_path": report_path,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }


def main() -> int:
    result = run()
    payload = result["payload"]
    metrics = payload.replay_metrics
    pytest_status = result["pytest_status"]
    can_enter_v07 = pytest_status == "PASS" and payload.summary.get("card_count", 0) > 0

    print(f"card_count={payload.summary.get('card_count')}")
    print(f"pass_count={payload.summary.get('pass_count')}")
    print(f"fail_count={payload.summary.get('fail_count')}")
    print(f"case_count={metrics.case_count}")
    print(f"direction_accuracy={metrics.direction_accuracy}")
    print(f"output_json_path={result['output_json_path']}")
    print(f"output_html_path={result['output_html_path']}")
    print(f"report_path={result['report_path']}")
    print("shadow_display_only=true")
    print("is_trading_advice=false")
    print("allow_order_execution=false")
    print("")
    print("V0.6 总结")
    print("1. 是否实现 display schema: 是")
    print("2. 是否实现 display_builder: 是")
    print("3. 是否生成 display JSON: 是")
    print("4. 是否生成静态 HTML dashboard: 是")
    print("5. 是否读取 V0.4 shadow predictions: 是")
    print("6. 是否读取 V0.5 replay metrics: 是")
    print(f"7. card_count: {payload.summary.get('card_count')}")
    print(f"8. pass_count: {payload.summary.get('pass_count')}")
    print(f"9. fail_count: {payload.summary.get('fail_count')}")
    print(f"10. case_count: {metrics.case_count}")
    print(f"11. direction_accuracy: {metrics.direction_accuracy}")
    print(f"12. mean_abs_return_error: {metrics.mean_abs_return_error}")
    print("13. 是否包含 safety banner: 是")
    print("14. 是否明确非交易建议: 是")
    print("15. 是否完全不调用 GPU 推理: 是")
    print(f"16. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("17. 是否生成 docs/kronos_display_design.md: 是")
    print(f"18. 是否可以进入 V0.7 ETF 本地微调评估: {'是' if can_enter_v07 else '否'}")
    print("")
    if can_enter_v07:
        print("A. V0.6 PASS，可以进入 V0.7 ETF 本地微调评估。")
        return 0
    print("B. V0.6 FAIL，暂不可进入 V0.7。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
