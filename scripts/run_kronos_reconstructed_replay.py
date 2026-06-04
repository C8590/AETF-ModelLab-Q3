#!/usr/bin/env python3
"""Run V0.11-R reconstructed zero-shot Kronos replay."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
TRUE_LEFT_HISTORY_PATH = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.kronos_adapter import KronosAdapter, KronosAdapterConfig  # noqa: E402
from model_lab.reconstructed_replay_summary import (  # noqa: E402
    CANDIDATE_HISTORY_TYPE,
    build_reconstructed_replay_summary,
    validate_reconstructed_replay_inputs,
    write_json,
)
from model_lab.replay_pipeline import KronosHistoricalReplayPipeline, ReplayPipelineConfig  # noqa: E402


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(config_path: str | Path) -> dict[str, Any]:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("mode") != "reconstructed_zero_shot_replay":
        raise ValueError("mode must be reconstructed_zero_shot_replay.")
    evaluation = config.get("evaluation", {})
    if evaluation.get("candidate_history_type") != CANDIDATE_HISTORY_TYPE:
        raise ValueError("evaluation.candidate_history_type must be reconstructed_not_true_left_snapshot.")
    if bool(evaluation.get("allow_formal_v011_claim")):
        raise ValueError("evaluation.allow_formal_v011_claim must be false.")
    if not bool(evaluation.get("allow_reconstructed_branch_claim")):
        raise ValueError("evaluation.allow_reconstructed_branch_claim must be true.")
    if not bool(evaluation.get("require_no_lookahead_bias")):
        raise ValueError("evaluation.require_no_lookahead_bias must be true.")
    safety = config.get("safety", {})
    for key in [
        "allow_training",
        "allow_torchrun",
        "allow_tokenizer_finetune",
        "allow_full_finetune",
        "allow_trading_advice",
        "allow_order_execution",
        "allow_writeback_to_left_project",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false.")


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
        replay_cases_path=Path(config["inputs"]["replay_cases_path"]),
        output_predictions_path=Path(config["outputs"]["predictions_path"]),
        output_metrics_path=Path(config["outputs"]["metrics_path"]),
        report_path=Path(config["outputs"]["report_path"]),
        lookback=int(inference_cfg.get("lookback", 120)),
        pred_len=int(inference_cfg.get("pred_len", 24)),
        sample_count=int(inference_cfg.get("sample_count", 1)),
        max_cases=int(inference_cfg.get("max_cases", 200)),
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
    output = (result.stdout + "\n" + result.stderr).strip()
    summary = output.splitlines()[-1] if output else ""
    return ("PASS" if result.returncode == 0 else "FAIL", summary)


def write_design_doc(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Kronos V0.11-R Reconstructed Replay Design",
        "",
        "## 目标",
        "",
        "V0.11-R 使用 reconstructed candidate history 生成的 replay cases，对未微调的 Kronos-small 做 zero-shot 历史回放评估。",
        "",
        "## 分支边界",
        "",
        "这是 reconstructed 分支，不是正式 V0.11。reconstructed candidate history 来源于真实 ETF K 线的过去窗口特征排序，不是真实左侧历史候选池快照。",
        "",
        "## Zero-Shot",
        "",
        "Zero-shot 表示直接使用已有 Kronos-small 和 tokenizer，不训练、不微调、不生成 checkpoint。",
        "",
        "## 输入",
        "",
        "Replay case 输入来自 data/real/replay/kronos_v10_reconstructed_replay_cases.csv，每个 case 指向 data/real/normalized/kline 下的标准化 K 线。",
        "",
        "## 无未来函数",
        "",
        "回放切片以 as_of_date 为边界，Kronos 输入窗口只包含 as_of_date 及以前的 lookback 行，actual future 只用于评估 pred_len 行。",
        "",
        "## KronosAdapter",
        "",
        "KronosAdapter 负责加载 Kronos-small、Tokenizer-base，并在 GPU 上执行 zero-shot predict。KronosHistoricalReplayPipeline 负责逐 case 切片、调用 adapter、比较预测与真实 future。",
        "",
        "## 指标",
        "",
        "核心指标包括 direction_accuracy、mean_abs_return_error、median_abs_return_error、rmse_return_error。分组指标按 symbol 和 candidate_rank 汇总，用于观察 reconstructed 分支的样本结构差异。",
        "",
        "## 局限",
        "",
        "本结果不能代表真实左侧项目历史候选池表现，不能作为正式 V0.11 结论，也不可作为交易依据。",
        "",
        "## 与正式 V0.11",
        "",
        "未来正式 V0.11 需要真实 left_candidates_history.csv，并基于真实左侧历史候选池回放。",
        "",
        "## 安全边界",
        "",
        "本阶段不训练、不微调、不运行 torchrun、不下单、不访问交易接口、不回写主项目、不修改左侧项目。",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_report(
    path: Path,
    *,
    config: dict[str, Any],
    summary: dict[str, Any],
    pytest_status: str,
    pytest_summary: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    group_metrics = summary.get("group_metrics", {})
    by_symbol = group_metrics.get("by_symbol", [])[:10]
    by_rank = group_metrics.get("by_candidate_rank", [])[:10]
    lines = [
        "# Kronos V0.11-R Reconstructed Replay Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 replay cases 路径: {config['inputs']['replay_cases_path']}",
        f"- 输入 readiness 路径: {config['inputs']['reconstructed_readiness_path']}",
        f"- 输出 predictions 路径: {config['outputs']['predictions_path']}",
        f"- 输出 metrics 路径: {config['outputs']['metrics_path']}",
        f"- 输出 summary JSON 路径: {config['outputs']['summary_json_path']}",
        f"- candidate_history_type: {summary['candidate_history_type']}",
        f"- evaluated_case_count: {summary['evaluated_case_count']}",
        f"- success_count: {summary['success_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- direction_accuracy: {summary['direction_accuracy']}",
        f"- mean_abs_return_error: {summary['mean_abs_return_error']}",
        f"- median_abs_return_error: {summary['median_abs_return_error']}",
        f"- rmse_return_error: {summary['rmse_return_error']}",
        f"- 是否 zero-shot: {summary['zero_shot']}",
        f"- 是否未训练: {summary['no_training']}",
        f"- 是否未运行 torchrun: {summary['no_torchrun']}",
        f"- 是否未生成 checkpoint: {summary['no_checkpoint']}",
        f"- 是否可以进入正式 V0.11: {summary['formal_v011_ready']}",
        f"- 是否可以进入 V0.12-R reconstructed 分支展示或扩展评估: {summary['reconstructed_v011_ready']}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "",
        "## by_symbol 摘要",
        "",
    ]
    lines.extend(_format_group_rows(by_symbol, "symbol"))
    lines.extend(["", "## by_candidate_rank 摘要", ""])
    lines.extend(_format_group_rows(by_rank, "candidate_rank"))
    lines.extend(
        [
            "",
            "## Critical Scope",
            "",
            "- reconstructed candidate history 不是真实左侧历史候选池。",
            "- 本次结果不能代表真实左侧项目历史候选池表现。",
            "- 本次不是正式 V0.11。",
            "- 本次未训练、未微调。",
            "- 不可作为交易依据。",
            "- 未接入主项目，未修改左侧项目，未访问交易接口。",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _format_group_rows(rows: list[dict[str, Any]], label: str) -> list[str]:
    if not rows:
        return ["- 无。"]
    lines = [
        f"| {label} | success_count | direction_accuracy | mean_abs_return_error | rmse_return_error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get(label)} | {row.get('success_count')} | {row.get('direction_accuracy')} | {row.get('mean_abs_return_error')} | {row.get('rmse_return_error')} |"
        )
    return lines


def run(config_path: str | Path = ROOT / "configs" / "kronos_replay_reconstructed.yaml") -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    replay_cases_path = resolve_project_path(config["inputs"]["replay_cases_path"])
    readiness_path = resolve_project_path(config["inputs"]["reconstructed_readiness_path"])
    validate_reconstructed_replay_inputs(replay_cases_path, readiness_path)
    if TRUE_LEFT_HISTORY_PATH.exists():
        raise FileExistsError("Refusing V0.11-R run because true left_candidates_history.csv exists unexpectedly.")

    adapter = build_adapter(config)
    pipeline = KronosHistoricalReplayPipeline(adapter, build_pipeline_config(config))
    predictions_df, metrics = pipeline.run()
    summary = build_reconstructed_replay_summary(predictions_df, metrics, config)
    pytest_status, pytest_summary = run_pytest_quiet()
    summary["pytest_status"] = pytest_status
    summary["pytest_summary"] = pytest_summary
    write_json(summary, resolve_project_path(config["outputs"]["summary_json_path"]))
    write_design_doc(resolve_project_path(config["outputs"]["design_doc_path"]))
    write_report(resolve_project_path(config["outputs"]["report_path"]), config=config, summary=summary, pytest_status=pytest_status, pytest_summary=pytest_summary)
    return predictions_df, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V0.11-R reconstructed zero-shot replay.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "kronos_replay_reconstructed.yaml"))
    args = parser.parse_args(argv)
    _, summary = run(args.config)
    for key in [
        "mode",
        "candidate_history_type",
        "evaluated_case_count",
        "success_count",
        "fail_count",
        "direction_accuracy",
        "mean_abs_return_error",
        "median_abs_return_error",
        "rmse_return_error",
        "formal_v011_ready",
        "reconstructed_v011_ready",
        "no_training",
        "zero_shot",
    ]:
        print(f"{key}={summary.get(key)}")
    return 0 if summary["reconstructed_v011_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
