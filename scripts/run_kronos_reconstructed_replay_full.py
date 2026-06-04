#!/usr/bin/env python3
"""Run V0.12-R full or resumed reconstructed zero-shot replay expansion."""

from __future__ import annotations

import argparse
import json
import shutil
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
from model_lab.reconstructed_replay_expansion import (  # noqa: E402
    CANDIDATE_HISTORY_TYPE,
    append_predictions,
    build_expanded_summary,
    compute_expanded_group_metrics,
    load_completed_replay_ids,
    load_reconstructed_replay_cases,
    select_cases_for_expansion,
    write_json,
)
from model_lab.replay_metrics import aggregate_replay_metrics  # noqa: E402
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
    if config.get("mode") != "reconstructed_zero_shot_replay_full_expansion":
        raise ValueError("mode must be reconstructed_zero_shot_replay_full_expansion.")
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


def validate_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any] | None]:
    replay_cases = load_reconstructed_replay_cases(resolve_project_path(config["inputs"]["replay_cases_path"]))
    readiness_path = resolve_project_path(config["inputs"]["reconstructed_readiness_path"])
    readiness = json.loads(readiness_path.read_text(encoding="utf-8-sig"))
    if readiness.get("candidate_history_type") != CANDIDATE_HISTORY_TYPE:
        raise ValueError("readiness candidate_history_type must be reconstructed_not_true_left_snapshot.")
    if bool(readiness.get("can_enter_formal_v011")):
        raise ValueError("readiness must not allow formal V0.11.")
    if not bool(readiness.get("can_enter_v011_reconstructed")):
        raise ValueError("readiness must allow reconstructed branch.")
    prior_path = resolve_project_path(config["inputs"]["prior_v11r_summary_path"])
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.exists() else None
    return replay_cases, prior


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
        "# Kronos V0.12-R Reconstructed Expansion Design",
        "",
        "## 目标",
        "",
        "V0.12-R 将 V0.11-R 的 200 case reconstructed zero-shot 回放扩展到全量或接近全量，以观察指标稳定性。",
        "",
        "## 分支边界",
        "",
        "本阶段是 reconstructed 分支，不是正式 V0.12，也不是正式 V0.11。输入 replay cases 来源于 reconstructed candidate history，而不是真实左侧历史候选池。",
        "",
        "## 输入来源",
        "",
        "Replay cases 来自 data/real/replay/kronos_v10_reconstructed_replay_cases.csv，K 线来自 data/real/normalized/kline。",
        "",
        "## Resume",
        "",
        "脚本从 outputs/kronos_v12r_reconstructed_full_predictions.csv 读取已完成 replay_id，后续运行只执行未完成 case。",
        "",
        "## 分批策略",
        "",
        "默认每批 100 cases。每批通过 KronosHistoricalReplayPipeline 执行并追加去重到全量 predictions。",
        "",
        "## 分组指标",
        "",
        "group_by_symbol 用于观察不同 ETF 的误差与方向命中；group_by_rank 用于观察 reconstructed 排名位置差异；group_by_month 用于观察时间段稳定性。",
        "",
        "## V0.11-R Baseline",
        "",
        "summary 会记录 V0.11-R 200-case baseline direction_accuracy，并计算扩展后 direction_accuracy_delta_vs_v11r。",
        "",
        "## 局限",
        "",
        "结果不能代表真实左侧历史候选池表现，不能作为正式 V0.11/V0.12 结论，也不可作为交易依据。",
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
    lines = [
        "# Kronos V0.12-R Reconstructed Expansion Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 replay cases 路径: {config['inputs']['replay_cases_path']}",
        f"- 输出 predictions 路径: {config['outputs']['predictions_path']}",
        f"- 输出 metrics 路径: {config['outputs']['metrics_path']}",
        f"- 输出 summary JSON 路径: {config['outputs']['summary_json_path']}",
        f"- candidate_history_type: {summary['candidate_history_type']}",
        f"- total_available_cases: {summary['total_available_cases']}",
        f"- evaluated_case_count: {summary['evaluated_case_count']}",
        f"- success_count: {summary['success_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- direction_accuracy: {summary['direction_accuracy']}",
        f"- mean_abs_return_error: {summary['mean_abs_return_error']}",
        f"- median_abs_return_error: {summary['median_abs_return_error']}",
        f"- rmse_return_error: {summary['rmse_return_error']}",
        f"- V0.11-R baseline direction_accuracy: {summary['v11r_baseline_direction_accuracy']}",
        f"- direction_accuracy_delta_vs_v11r: {summary['direction_accuracy_delta_vs_v11r']}",
        f"- 是否 zero-shot: {summary['zero_shot']}",
        f"- 是否未训练: {summary['no_training']}",
        f"- 是否未运行 torchrun: {summary['no_torchrun']}",
        f"- 是否未生成 checkpoint: {summary['no_checkpoint']}",
        f"- 是否可以进入正式 V0.11: {summary['formal_v011_ready']}",
        f"- 是否可以进入 V0.13-R reconstructed 展示层: {summary['reconstructed_v012r_ready']}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "",
        "## by_symbol 摘要",
        "",
    ]
    lines.extend(_format_group_rows(group_metrics.get("by_symbol", [])[:12], "symbol"))
    lines.extend(["", "## by_candidate_rank 摘要", ""])
    lines.extend(_format_group_rows(group_metrics.get("by_candidate_rank", [])[:12], "candidate_rank"))
    lines.extend(["", "## by_month 摘要", ""])
    lines.extend(_format_group_rows(group_metrics.get("by_month", [])[:12], "month"))
    lines.extend(
        [
            "",
            "## Critical Scope",
            "",
            "- reconstructed candidate history 不是真实左侧历史候选池。",
            "- 本次结果不能代表真实左侧项目历史候选池表现。",
            "- 本次不是正式 V0.12。",
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
        f"| {label} | case_count | success_count | fail_count | direction_accuracy | mean_abs_return_error | rmse_return_error |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get(label)} | {row.get('case_count')} | {row.get('success_count')} | {row.get('fail_count')} | {row.get('direction_accuracy')} | {row.get('mean_abs_return_error')} | {row.get('rmse_return_error')} |"
        )
    return lines


def _write_group_csvs(summary: dict[str, Any], config: dict[str, Any]) -> None:
    outputs = config["outputs"]
    groups = summary["group_metrics"]
    mapping = [
        ("by_symbol", outputs["group_by_symbol_path"]),
        ("by_candidate_rank", outputs["group_by_rank_path"]),
        ("by_month", outputs["group_by_month_path"]),
    ]
    for key, path in mapping:
        out_path = resolve_project_path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(groups.get(key, [])).to_csv(out_path, index=False, encoding="utf-8-sig")


def _write_progress(config: dict[str, Any], payload: dict[str, Any]) -> None:
    progress_path = resolve_project_path(config["outputs"]["progress_path"])
    write_json(payload, progress_path)


def run(config_path: str | Path = ROOT / "configs" / "kronos_replay_reconstructed_full.yaml") -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    if TRUE_LEFT_HISTORY_PATH.exists():
        raise FileExistsError("Refusing V0.12-R run because true left_candidates_history.csv exists unexpectedly.")
    replay_cases, prior_summary = validate_inputs(config)
    outputs = config["outputs"]
    inference = config.get("inference", {})
    predictions_path = resolve_project_path(outputs["predictions_path"])
    metrics_path = resolve_project_path(outputs["metrics_path"])
    batch_size = max(1, int(inference.get("batch_size_cases", 100)))
    max_cases = inference.get("max_cases")
    max_cases_value = None if max_cases is None else int(max_cases)
    completed = load_completed_replay_ids(predictions_path) if bool(inference.get("resume", True)) else set()
    selected = select_cases_for_expansion(replay_cases, completed, max_cases_value)
    newly_evaluated = 0
    adapter = build_adapter(config)
    temp_dir = ROOT / "outputs" / "_tmp_v12r_replay"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for batch_index, start in enumerate(range(0, len(selected), batch_size), start=1):
        batch = selected.iloc[start : start + batch_size].copy().reset_index(drop=True)
        if batch.empty:
            continue
        temp_cases = temp_dir / f"cases_batch_{batch_index:04d}.csv"
        temp_predictions = temp_dir / f"predictions_batch_{batch_index:04d}.csv"
        temp_metrics = temp_dir / f"metrics_batch_{batch_index:04d}.csv"
        batch.to_csv(temp_cases, index=False, encoding="utf-8-sig")
        pipeline = KronosHistoricalReplayPipeline(
            adapter,
            ReplayPipelineConfig(
                replay_cases_path=temp_cases,
                output_predictions_path=temp_predictions,
                output_metrics_path=temp_metrics,
                report_path=resolve_project_path(outputs["report_path"]),
                lookback=int(inference.get("lookback", 120)),
                pred_len=int(inference.get("pred_len", 24)),
                sample_count=int(inference.get("sample_count", 1)),
                max_cases=None,
                T=float(inference.get("T", 1.0)),
                top_p=float(inference.get("top_p", 0.9)),
                project_root=ROOT,
            ),
        )
        batch_predictions, _ = pipeline.run()
        append_predictions(predictions_path, batch_predictions)
        newly_evaluated += int(len(batch_predictions))
        current_predictions = pd.read_csv(predictions_path)
        _write_progress(
            config,
            {
                "mode": config["mode"],
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "total_available_cases": int(len(replay_cases)),
                "completed_case_count": int(len(current_predictions)),
                "newly_evaluated_case_count": newly_evaluated,
                "last_batch_index": batch_index,
                "zero_shot": True,
                "no_training": True,
                "no_torchrun": True,
            },
        )

    predictions = pd.read_csv(predictions_path) if predictions_path.exists() else pd.DataFrame()
    metrics = aggregate_replay_metrics(predictions)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False, encoding="utf-8-sig")
    runtime_config = dict(config)
    runtime_config["runtime"] = {
        "total_available_cases": int(len(replay_cases)),
        "newly_evaluated_case_count": newly_evaluated,
    }
    summary = build_expanded_summary(predictions, metrics, prior_summary, runtime_config)
    summary["newly_evaluated_case_count"] = newly_evaluated
    pytest_status, pytest_summary = run_pytest_quiet()
    summary["pytest_status"] = pytest_status
    summary["pytest_summary"] = pytest_summary
    write_json(summary, resolve_project_path(outputs["summary_json_path"]))
    _write_group_csvs(summary, config)
    write_design_doc(resolve_project_path(outputs["design_doc_path"]))
    write_report(resolve_project_path(outputs["report_path"]), config=config, summary=summary, pytest_status=pytest_status, pytest_summary=pytest_summary)
    shutil.rmtree(temp_dir, ignore_errors=True)
    _write_progress(
        config,
        {
            "mode": config["mode"],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "total_available_cases": int(len(replay_cases)),
            "completed_case_count": int(len(predictions)),
            "newly_evaluated_case_count": newly_evaluated,
            "reconstructed_v012r_ready": summary["reconstructed_v012r_ready"],
            "zero_shot": True,
            "no_training": True,
            "no_torchrun": True,
        },
    )
    return predictions, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V0.12-R reconstructed full replay expansion.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "kronos_replay_reconstructed_full.yaml"))
    args = parser.parse_args(argv)
    _, summary = run(args.config)
    for key in [
        "mode",
        "candidate_history_type",
        "total_available_cases",
        "evaluated_case_count",
        "newly_evaluated_case_count",
        "success_count",
        "fail_count",
        "direction_accuracy",
        "mean_abs_return_error",
        "median_abs_return_error",
        "rmse_return_error",
        "v11r_baseline_direction_accuracy",
        "direction_accuracy_delta_vs_v11r",
        "formal_v011_ready",
        "zero_shot",
        "no_training",
    ]:
        print(f"{key}={summary.get(key)}")
    return 0 if int(summary.get("evaluated_case_count", 0)) >= 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
