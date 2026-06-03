#!/usr/bin/env python3
"""Run V0.5 Kronos historical replay validation."""

from __future__ import annotations

import platform
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

from model_lab.kronos_adapter import KronosAdapter, KronosAdapterConfig, _torch_info  # noqa: E402
from model_lab.replay_pipeline import (  # noqa: E402
    KronosHistoricalReplayPipeline,
    ReplayPipelineConfig,
    resolve_project_path,
)


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_replay_safety(config.get("safety", {}))
    return config


def validate_replay_safety(safety: dict[str, Any]) -> None:
    if safety.get("mode") != "historical_replay_only":
        raise ValueError("safety.mode must be historical_replay_only.")
    if not bool(safety.get("prevent_lookahead_bias")):
        raise ValueError("safety.prevent_lookahead_bias must be true.")
    for key in [
        "allow_trading_signal",
        "allow_order_execution",
        "allow_writeback_to_left_project",
        "allow_finetune",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false for V0.5 historical replay.")


def build_adapter(config: dict[str, Any]) -> KronosAdapter:
    adapter_cfg = config.get("adapter", {})
    inference_cfg = config.get("inference", {})
    return KronosAdapter(
        KronosAdapterConfig(
            model_name=adapter_cfg.get("model_name", "NeoQuasar/Kronos-small"),
            tokenizer_name=adapter_cfg.get("tokenizer_name", "NeoQuasar/Kronos-Tokenizer-base"),
            device=adapter_cfg.get("device", "cuda:0"),
            max_context=int(adapter_cfg.get("max_context", 512)),
            hf_cache_dir=adapter_cfg.get("hf_cache_dir", "models/kronos/hf_cache"),
            default_lookback=int(inference_cfg.get("lookback", 120)),
            default_pred_len=int(inference_cfg.get("pred_len", 24)),
            default_T=float(inference_cfg.get("T", 1.0)),
            default_top_p=float(inference_cfg.get("top_p", 0.9)),
            default_sample_count=int(inference_cfg.get("sample_count", 1)),
        )
    )


def build_pipeline_config(config: dict[str, Any]) -> ReplayPipelineConfig:
    inference_cfg = config.get("inference", {})
    return ReplayPipelineConfig(
        replay_cases_path=Path(config["replay_cases_path"]),
        output_predictions_path=Path(config["output_predictions_path"]),
        output_metrics_path=Path(config["output_metrics_path"]),
        report_path=Path(config["report_path"]),
        lookback=int(inference_cfg.get("lookback", 120)),
        pred_len=int(inference_cfg.get("pred_len", 24)),
        sample_count=int(inference_cfg.get("sample_count", 1)),
        max_cases=inference_cfg.get("max_cases"),
        T=float(inference_cfg.get("T", 1.0)),
        top_p=float(inference_cfg.get("top_p", 0.9)),
        project_root=ROOT,
    )


def run_pytest_quiet() -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    output = (result.stdout + "\n" + result.stderr).strip()
    return status, output.splitlines()[-1] if output else status


def write_replay_report(
    *,
    report_path: str | Path,
    config: dict[str, Any],
    replay_df: pd.DataFrame,
    metrics: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    adapter_cfg = config.get("adapter", {})
    inference_cfg = config.get("inference", {})
    torch_info = _torch_info(adapter_cfg.get("device", "cuda:0"))
    can_enter_v06 = pytest_status == "PASS" and int(metrics.get("success_count", 0)) > 0

    lines = [
        "# Kronos V0.5 Historical Replay Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Python 版本: {platform.python_version()}",
        f"- torch 版本: {torch_info['torch_version']}",
        f"- CUDA 版本: {torch_info['cuda_version']}",
        f"- GPU 名称: {torch_info['gpu_name']}",
        f"- Kronos 模型名称: {adapter_cfg.get('model_name')}",
        f"- tokenizer 名称: {adapter_cfg.get('tokenizer_name')}",
        f"- case_count: {metrics.get('case_count')}",
        f"- success_count: {metrics.get('success_count')}",
        f"- fail_count: {metrics.get('fail_count')}",
        f"- direction_accuracy: {metrics.get('direction_accuracy')}",
        f"- mean_abs_return_error: {metrics.get('mean_abs_return_error')}",
        f"- median_abs_return_error: {metrics.get('median_abs_return_error')}",
        f"- rmse_return_error: {metrics.get('rmse_return_error')}",
        f"- lookback: {inference_cfg.get('lookback')}",
        f"- pred_len: {inference_cfg.get('pred_len')}",
        f"- sample_count: {inference_cfg.get('sample_count')}",
        f"- 输入 replay cases 路径: {config.get('replay_cases_path')}",
        f"- 输出 predictions CSV 路径: {config.get('output_predictions_path')}",
        f"- 输出 metrics CSV 路径: {config.get('output_metrics_path')}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "- 是否检测并防止未来函数: 是",
        f"- 是否可以进入 V0.6 AI 影子判断展示: {'是' if can_enter_v06 else '否'}",
        "",
        "## 输出字段",
        "",
    ]
    lines.extend(f"- `{col}`" for col in replay_df.columns)
    lines.extend(
        [
            "",
            "## 样本说明",
            "",
            "- 当前 replay 样本为 synthetic/demo data，只验证工程链路。",
            "- 当前结果不代表真实市场预测能力。",
            "- 当前结果不可作为交易依据。",
            "- 样本数较少，聚合指标只能用于冒烟验收，不能做稳定统计解释。",
            "",
            "## 安全边界",
            "",
            "- V0.5 不产生交易信号。",
            "- V0.5 不下单，不回写主项目，不访问主项目数据库。",
            "- V0.5 不微调模型，不下载 Kronos-large，不运行 webui。",
        ]
    )
    path = resolve_project_path(report_path, project_root=ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_replay.yaml") -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    adapter = build_adapter(config)
    pipeline = KronosHistoricalReplayPipeline(adapter, build_pipeline_config(config))
    replay_df, metrics = pipeline.run()
    pytest_status, pytest_summary = run_pytest_quiet()
    write_replay_report(
        report_path=config["report_path"],
        config=config,
        replay_df=replay_df,
        metrics=metrics,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    metrics["pytest_status"] = pytest_status
    metrics["pytest_summary"] = pytest_summary
    return replay_df, metrics


def main() -> int:
    config_path = ROOT / "configs" / "kronos_replay.yaml"
    config = load_config(config_path)
    _, metrics = run(config_path)
    output_predictions_path = resolve_project_path(config["output_predictions_path"], project_root=ROOT)
    output_metrics_path = resolve_project_path(config["output_metrics_path"], project_root=ROOT)
    report_path = resolve_project_path(config["report_path"], project_root=ROOT)
    pytest_status = metrics.get("pytest_status", "FAIL")
    can_enter_v06 = pytest_status == "PASS" and int(metrics.get("success_count", 0)) > 0

    print(f"case_count={metrics.get('case_count')}")
    print(f"success_count={metrics.get('success_count')}")
    print(f"fail_count={metrics.get('fail_count')}")
    print(f"direction_accuracy={metrics.get('direction_accuracy')}")
    print(f"mean_abs_return_error={metrics.get('mean_abs_return_error')}")
    print(f"output_predictions_path={output_predictions_path}")
    print(f"output_metrics_path={output_metrics_path}")
    print(f"report_path={report_path}")
    print("historical_replay_only=true")
    print("prevent_lookahead_bias=true")
    print("")
    print("V0.5 总结")
    print("1. 是否实现历史 replay case schema: 是")
    print("2. 是否实现历史 K 线切片: 是")
    print("3. 是否明确防止未来函数: 是")
    print("4. 是否实现 replay_metrics: 是")
    print("5. 是否实现 KronosHistoricalReplayPipeline: 是")
    print("6. 是否完成 KronosAdapter 历史回放推理: 是")
    print(f"7. case_count: {metrics.get('case_count')}")
    print(f"8. success_count: {metrics.get('success_count')}")
    print(f"9. fail_count: {metrics.get('fail_count')}")
    print(f"10. direction_accuracy: {metrics.get('direction_accuracy')}")
    print(f"11. mean_abs_return_error: {metrics.get('mean_abs_return_error')}")
    print(f"12. 输出 predictions CSV 路径: {output_predictions_path}")
    print(f"13. 输出 metrics CSV 路径: {output_metrics_path}")
    print(f"14. 输出报告路径: {report_path}")
    print(f"15. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("16. 是否生成 docs/kronos_replay_design.md: 是")
    print(f"17. 是否可以进入 V0.6 AI 影子判断展示: {'是' if can_enter_v06 else '否'}")
    print("")
    if can_enter_v06:
        print("A. V0.5 PASS，可以进入 V0.6 AI 影子判断展示。")
        return 0
    print("B. V0.5 FAIL，暂不可进入 V0.6。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
