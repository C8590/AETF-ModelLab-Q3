#!/usr/bin/env python3
"""Build research-only reconstructed candidate history and replay cases."""

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
TRUE_LEFT_HISTORY_PATH = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"
REAL_CANDIDATE_PATH = TRUE_LEFT_HISTORY_PATH

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.reconstructed_candidates import (  # noqa: E402
    RECONSTRUCTED_NOTE,
    RECONSTRUCTED_TYPE,
    ReconstructedCandidateConfig,
    build_reconstructed_candidate_history,
    build_reconstructed_replay_cases,
    evaluate_reconstructed_readiness,
    load_normalized_klines,
    write_json,
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_safety(config)
    return config


def validate_safety(config: dict[str, Any]) -> None:
    if config.get("mode") != "reconstructed_candidate_history_only":
        raise ValueError("mode must be reconstructed_candidate_history_only.")
    safety = config.get("safety", {})
    if safety.get("candidate_history_type") != RECONSTRUCTED_TYPE:
        raise ValueError("safety.candidate_history_type must mark reconstructed history.")
    blocked_flags = {
        "allow_overwrite_true_left_history": safety.get("allow_overwrite_true_left_history"),
        "allow_training": safety.get("allow_training"),
        "allow_gpu_inference": safety.get("allow_gpu_inference"),
        "allow_trading_advice": safety.get("allow_trading_advice"),
        "allow_order_execution": safety.get("allow_order_execution"),
        "allow_writeback_to_left_project": safety.get("allow_writeback_to_left_project"),
    }
    for key, value in blocked_flags.items():
        if bool(value):
            raise ValueError(f"safety.{key} must be false.")
    if not bool(safety.get("prevent_lookahead_bias")):
        raise ValueError("safety.prevent_lookahead_bias must be true.")


def reconstruction_config_from_dict(config: dict[str, Any]) -> ReconstructedCandidateConfig:
    reconstruction = config["reconstruction"]
    windows = reconstruction.get("feature_windows", {})
    return ReconstructedCandidateConfig(
        candidate_top_n=int(reconstruction.get("candidate_top_n", 5)),
        min_symbols_per_date=int(reconstruction.get("min_symbols_per_date", 10)),
        min_candidate_dates=int(reconstruction.get("min_candidate_dates", 100)),
        min_replay_cases=int(reconstruction.get("min_replay_cases", 200)),
        lookback_for_replay=int(reconstruction.get("lookback_for_replay", 120)),
        pred_len_for_replay=int(reconstruction.get("pred_len_for_replay", 24)),
        momentum_short=int(windows.get("momentum_short", 20)),
        momentum_mid=int(windows.get("momentum_mid", 60)),
        volatility=int(windows.get("volatility", 20)),
        liquidity=int(windows.get("liquidity", 20)),
        max_candidate_dates=reconstruction.get("max_candidate_dates", 300),
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


def write_report(
    report_path: Path,
    *,
    config: dict[str, Any],
    readiness: dict[str, Any],
    reconstructed_path: Path,
    replay_cases_path: Path,
    pytest_status: str,
    pytest_summary: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    lines = [
        "# Kronos V0.10.2-E Reconstructed Candidate History Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 normalized_kline_dir: {inputs['normalized_kline_dir']}",
        f"- 输出 reconstructed candidate history 路径: {reconstructed_path.relative_to(ROOT).as_posix()}",
        f"- 输出 reconstructed replay cases 路径: {replay_cases_path.relative_to(ROOT).as_posix()}",
        f"- candidate_history_type: {readiness['candidate_history_type']}",
        f"- candidate_date_count: {readiness['candidate_date_count']}",
        f"- row_count: {readiness['row_count']}",
        f"- symbol_count: {readiness['symbol_count']}",
        f"- replay_case_count: {readiness['replay_case_count']}",
        f"- 是否防止未来函数: {readiness['prevent_lookahead_bias']}",
        f"- 是否未生成真实 left_candidates_history.csv: {not TRUE_LEFT_HISTORY_PATH.exists()}",
        f"- 是否可以进入正式 V0.11: {readiness['can_enter_formal_v011']}",
        f"- 是否可以进入 V0.11-R: {readiness['can_enter_v011_reconstructed']}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        "",
        "## Critical Scope",
        "",
        "- reconstructed candidate history 不是真实左侧历史候选池。",
        "- reconstructed candidate history 不能冒充 left_candidates_history.csv。",
        "- reconstructed candidate history 不能用于正式 V0.11。",
        "- reconstructed candidate history 只能用于 V0.11-R reconstructed zero-shot 研究分支。",
        "- reconstructed candidate history 不可作为交易依据。",
        "- 未训练模型。",
        "- 未运行 torchrun。",
        "- 未调用 GPU 推理。",
        "- 未接入主项目。",
        "- 未修改左侧项目。",
        "",
        "## Reasons",
        "",
    ]
    reasons = readiness.get("reasons", [])
    lines.extend(f"- {reason}" for reason in reasons) if reasons else lines.append("- 无阻断 reconstructed replay 的错误。")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in readiness.get("warnings", []))
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_reconstructed_history(
    raw_kline_dir: Path,
    output_path: Path,
    *,
    lookback_days: int = 60,
    top_n: int = 20,
    max_dates: int = 120,
    force: bool = False,
) -> dict[str, Any]:
    """Backward-compatible research-only builder used by older safety tests."""
    if REAL_CANDIDATE_PATH.exists():
        raise FileExistsError(
            "Refusing to build reconstructed history because real left_candidates_history.csv already exists."
        )
    if output_path.name == "left_candidates_history.csv":
        raise ValueError("Reconstructed output cannot overwrite left_candidates_history.csv.")
    if output_path.exists() and not force:
        raise FileExistsError(f"{output_path} already exists. Pass force=True to replace it.")

    config = ReconstructedCandidateConfig(
        candidate_top_n=max(1, top_n),
        min_symbols_per_date=1,
        min_candidate_dates=1,
        min_replay_cases=1,
        momentum_short=max(1, min(20, lookback_days)),
        momentum_mid=max(1, lookback_days),
        max_candidate_dates=max(1, max_dates),
    )
    klines = load_normalized_klines(raw_kline_dir)
    reconstructed = build_reconstructed_candidate_history(klines, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reconstructed.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "candidate_history_status": "RECONSTRUCTED_NOT_REAL_LEFT_SNAPSHOT",
        "output_path": output_path.as_posix(),
        "row_count": int(len(reconstructed)),
        "candidate_date_count": int(reconstructed["as_of_date"].nunique()) if not reconstructed.empty else 0,
        "symbol_count": int(reconstructed["symbol"].nunique()) if not reconstructed.empty else 0,
        "notes": RECONSTRUCTED_NOTE,
    }


def run(config_path: str | Path = ROOT / "configs" / "reconstructed_candidate_history.yaml") -> dict[str, Any]:
    config_file = resolve_project_path(config_path)
    config = load_config(config_file)
    rc = reconstruction_config_from_dict(config)
    normalized_dir = resolve_project_path(config["inputs"]["normalized_kline_dir"])
    reconstructed_path = resolve_project_path(config["outputs"]["reconstructed_candidate_history_path"])
    replay_cases_path = resolve_project_path(config["outputs"]["reconstructed_replay_cases_path"])
    manifest_path = resolve_project_path(config["outputs"]["manifest_path"])
    readiness_path = resolve_project_path(config["outputs"]["readiness_path"])
    report_path = resolve_project_path(config["outputs"]["report_path"])

    if reconstructed_path.resolve() == TRUE_LEFT_HISTORY_PATH.resolve():
        raise ValueError("Refusing to write reconstructed output to true left_candidates_history.csv.")

    klines = load_normalized_klines(normalized_dir)
    reconstructed = build_reconstructed_candidate_history(klines, rc)
    reconstructed_path.parent.mkdir(parents=True, exist_ok=True)
    reconstructed.to_csv(reconstructed_path, index=False, encoding="utf-8-sig")

    replay_cases = build_reconstructed_replay_cases(reconstructed, normalized_dir, rc)
    replay_cases_path.parent.mkdir(parents=True, exist_ok=True)
    replay_cases.to_csv(replay_cases_path, index=False, encoding="utf-8-sig")

    readiness = evaluate_reconstructed_readiness(reconstructed, replay_cases, rc)
    write_json(readiness, readiness_path)
    manifest = {
        "mode": config["mode"],
        "version": "V0.10.2-E",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_file.as_posix(),
        "normalized_kline_dir": normalized_dir.as_posix(),
        "normalized_symbol_count": len(klines),
        "reconstructed_candidate_history_path": reconstructed_path.as_posix(),
        "reconstructed_replay_cases_path": replay_cases_path.as_posix(),
        "readiness_path": readiness_path.as_posix(),
        "report_path": report_path.as_posix(),
        "candidate_history_type": RECONSTRUCTED_TYPE,
        "candidate_date_count": readiness["candidate_date_count"],
        "row_count": readiness["row_count"],
        "symbol_count": readiness["symbol_count"],
        "replay_case_count": readiness["replay_case_count"],
        "true_left_history_path": TRUE_LEFT_HISTORY_PATH.as_posix(),
        "true_left_history_created": FALSE_TRUE_LEFT_HISTORY_CREATED,
        "reconstructed_note": RECONSTRUCTED_NOTE,
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    write_json(manifest, manifest_path)

    pytest_status, pytest_summary = run_pytest_quiet()
    write_report(
        report_path,
        config=config,
        readiness=readiness,
        reconstructed_path=reconstructed_path,
        replay_cases_path=replay_cases_path,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    output = {
        "manifest": manifest,
        "readiness": readiness,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
    }
    return output


FALSE_TRUE_LEFT_HISTORY_CREATED = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build V0.10.2-E reconstructed candidate history branch artifacts.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "reconstructed_candidate_history.yaml"))
    args = parser.parse_args(argv)
    output = run(args.config)
    readiness = output["readiness"]
    print(f"candidate_history_type={readiness['candidate_history_type']}")
    print(f"candidate_date_count={readiness['candidate_date_count']}")
    print(f"row_count={readiness['row_count']}")
    print(f"symbol_count={readiness['symbol_count']}")
    print(f"replay_case_count={readiness['replay_case_count']}")
    print(f"is_ready_for_reconstructed_replay={readiness['is_ready_for_reconstructed_replay']}")
    print(f"can_enter_formal_v011={readiness['can_enter_formal_v011']}")
    print(f"can_enter_v011_reconstructed={readiness['can_enter_v011_reconstructed']}")
    print(f"pytest_status={output['pytest_status']} {output['pytest_summary']}")
    return 0 if readiness["is_ready_for_reconstructed_replay"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
