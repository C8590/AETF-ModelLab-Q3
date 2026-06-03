#!/usr/bin/env python3
"""Prepare V0.10 real ETF dataset intake artifacts."""

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
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.real_data_prep import (  # noqa: E402
    CANDIDATE_REQUIRED_COLUMNS,
    KLINE_REQUIRED_COLUMNS,
    RealDataPrepConfig,
    build_expanded_replay_cases,
    config_from_dict,
    discover_raw_kline_files,
    evaluate_real_data_readiness,
    load_candidate_history,
    normalize_kline_df,
    normalized_kline_path,
    profile_kline_df,
    validate_raw_kline_schema,
    write_json,
)


PROFILE_COLUMNS = [
    "symbol",
    "display_name",
    "start_date",
    "end_date",
    "bar_count",
    "missing_rate",
    "duplicate_timestamp_count",
    "price_adjustment",
    "frequency",
    "source_name",
    "status",
    "errors",
]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_config_safety(config)
    return config


def validate_config_safety(config: dict[str, Any]) -> None:
    if config.get("mode") != "real_etf_data_preparation":
        raise ValueError("mode must be real_etf_data_preparation.")
    safety = config.get("safety", {})
    blocked_true_flags = {
        "safety.allow_training": safety.get("allow_training"),
        "safety.allow_torchrun": safety.get("allow_torchrun"),
        "safety.allow_trading_advice": safety.get("allow_trading_advice"),
        "safety.allow_order_execution": safety.get("allow_order_execution"),
        "safety.allow_writeback_to_left_project": safety.get("allow_writeback_to_left_project"),
    }
    for key, value in blocked_true_flags.items():
        if bool(value):
            raise ValueError(f"{key} must be false for V0.10.")


def ensure_directories(config: dict[str, Any]) -> None:
    inputs = config["inputs"]
    outputs = config["outputs"]
    for key in ["raw_kline_dir", "raw_candidates_dir"]:
        resolve_project_path(inputs[key]).mkdir(parents=True, exist_ok=True)
    for key in ["normalized_kline_dir"]:
        resolve_project_path(outputs[key]).mkdir(parents=True, exist_ok=True)
    for path in [
        ROOT / "data" / "real" / "normalized",
        ROOT / "data" / "real" / "quality",
        ROOT / "data" / "real" / "replay",
        ROOT / "outputs" / "real_data",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def create_candidate_template(raw_candidates_dir: Path) -> Path:
    template_path = raw_candidates_dir / "left_candidates_history_TEMPLATE.csv"
    if not template_path.exists():
        pd.DataFrame(columns=CANDIDATE_REQUIRED_COLUMNS).to_csv(
            template_path,
            index=False,
            encoding="utf-8-sig",
        )
    return template_path


def process_kline_files(raw_kline_dir: Path, normalized_kline_dir: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    profiles: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    for raw_path in discover_raw_kline_files(raw_kline_dir):
        raw_df = pd.read_csv(raw_path)
        errors = validate_raw_kline_schema(raw_df, raw_path)
        if errors:
            profile = profile_kline_df(raw_df, raw_path)
            profiles.append(profile)
            file_rows.append(
                {
                    "raw_path": raw_path.as_posix(),
                    "normalized_path": "",
                    "status": "FAIL",
                    "errors": errors,
                }
            )
            continue
        normalized = normalize_kline_df(raw_df, raw_path)
        symbol = str(normalized["symbol"].iloc[0])
        normalized_path = normalized_kline_path(normalized_kline_dir, symbol)
        normalized.to_csv(normalized_path, index=False, encoding="utf-8-sig")
        profile = profile_kline_df(normalized, normalized_path)
        profiles.append(profile)
        file_rows.append(
            {
                "raw_path": raw_path.as_posix(),
                "normalized_path": normalized_path.as_posix(),
                "status": profile["status"],
                "errors": profile["errors"],
            }
        )

    profile_df = pd.DataFrame(profiles, columns=PROFILE_COLUMNS)
    return profile_df, file_rows


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
    readiness: dict[str, Any],
    manifest_path: Path,
    profile_path: Path,
    replay_cases_path: Path,
    readiness_path: Path,
    pytest_status: str,
    pytest_summary: str,
    candidate_template_path: Path | None,
) -> bool:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = config["inputs"]
    outputs = config["outputs"]
    can_enter_v11 = pytest_status == "PASS" and bool(readiness["is_ready_for_expanded_replay"])
    reasons = readiness.get("reasons", [])
    warnings = readiness.get("warnings", [])
    lines = [
        "# Kronos V0.10 Real Data Quality Report",
        "",
        f"- V0.10 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入 raw_kline_dir: {inputs['raw_kline_dir']}",
        f"- 输入 raw_candidates_dir: {inputs['raw_candidates_dir']}",
        f"- symbol_count: {readiness['symbol_count']}",
        f"- qualified_symbol_count: {readiness['qualified_symbol_count']}",
        f"- candidate_date_count: {readiness['candidate_date_count']}",
        f"- replay_case_count: {readiness['replay_case_count']}",
        f"- data_status: {readiness['data_status']}",
        f"- is_ready_for_expanded_replay: {readiness['is_ready_for_expanded_replay']}",
        f"- dataset profile 路径: {profile_path.relative_to(ROOT).as_posix()}",
        f"- dataset manifest 路径: {manifest_path.relative_to(ROOT).as_posix()}",
        f"- expanded replay cases 路径: {replay_cases_path.relative_to(ROOT).as_posix()}",
        f"- readiness JSON 路径: {readiness_path.relative_to(ROOT).as_posix()}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.11 真实数据 zero-shot 回放评估: {'是' if can_enter_v11 else '否'}",
        "",
        "## 主要数据质量错误",
        "",
    ]
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- 无阻断错误。")
    lines.extend(["", "## 主要数据质量警告", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 无主要警告。")
    if candidate_template_path is not None:
        lines.extend(
            [
                "",
                "## 候选池模板",
                "",
                f"- 已生成模板: {candidate_template_path.relative_to(ROOT).as_posix()}",
                "- TEMPLATE 不是真实数据，不能当作真实候选池历史通过。",
            ]
        )
    lines.extend(
        [
            "",
            "## V0.10 Scope",
            "",
            "- V0.10 不训练模型。",
            "- V0.10 不运行 torchrun。",
            "- V0.10 不调用 GPU 推理。",
            "- V0.10 不接主项目。",
            "- V0.10 不产生交易建议。",
            "- 如果真实数据不足，则不能进入 V0.11。",
            "- 如果数据只是 SAMPLE/demo，则不能当作真实数据通过。",
            "",
            "## 输出路径",
            "",
            f"- normalized K 线目录: {outputs['normalized_kline_dir']}",
            f"- normalized candidate history 路径: {outputs['normalized_candidate_history_path']}",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return can_enter_v11


def run(config_path: str | Path = ROOT / "configs" / "real_data_prep.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    ensure_directories(config)
    prep_config: RealDataPrepConfig = config_from_dict(config)
    inputs = config["inputs"]
    outputs = config["outputs"]

    raw_kline_dir = resolve_project_path(inputs["raw_kline_dir"])
    raw_candidates_dir = resolve_project_path(inputs["raw_candidates_dir"])
    candidate_history_path = resolve_project_path(inputs["candidate_history_path"])
    normalized_kline_dir = resolve_project_path(outputs["normalized_kline_dir"])
    normalized_candidate_history_path = resolve_project_path(outputs["normalized_candidate_history_path"])
    profile_path = resolve_project_path(outputs["dataset_profile_path"])
    manifest_path = resolve_project_path(outputs["dataset_manifest_path"])
    replay_cases_path = resolve_project_path(outputs["expanded_replay_cases_path"])
    readiness_path = resolve_project_path(outputs["replay_readiness_path"])
    report_path = resolve_project_path(outputs["data_quality_report_path"])

    profile_df, file_rows = process_kline_files(raw_kline_dir, normalized_kline_dir)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_df.to_csv(profile_path, index=False, encoding="utf-8-sig")

    candidate_template_path: Path | None = None
    candidate_history_df: pd.DataFrame | None = None
    if candidate_history_path.exists():
        candidate_history_df = load_candidate_history(candidate_history_path)
        normalized_candidate_history_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_history_df.to_csv(normalized_candidate_history_path, index=False, encoding="utf-8-sig")
    else:
        candidate_template_path = create_candidate_template(raw_candidates_dir)

    replay_cases_df = build_expanded_replay_cases(
        candidate_history_df if candidate_history_df is not None else pd.DataFrame(columns=CANDIDATE_REQUIRED_COLUMNS),
        profile_df,
        normalized_kline_dir,
        prep_config,
    )
    replay_cases_path.parent.mkdir(parents=True, exist_ok=True)
    replay_cases_df.to_csv(replay_cases_path, index=False, encoding="utf-8-sig")

    readiness = evaluate_real_data_readiness(profile_df, replay_cases_df, candidate_history_df, prep_config)
    write_json(readiness, readiness_path)

    manifest = {
        "mode": config["mode"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_kline_dir": raw_kline_dir.as_posix(),
        "raw_candidates_dir": raw_candidates_dir.as_posix(),
        "raw_kline_file_count": len(discover_raw_kline_files(raw_kline_dir)),
        "normalized_kline_dir": normalized_kline_dir.as_posix(),
        "dataset_profile_path": profile_path.as_posix(),
        "expanded_replay_cases_path": replay_cases_path.as_posix(),
        "readiness_json_path": readiness_path.as_posix(),
        "candidate_history_present": candidate_history_df is not None,
        "candidate_template_path": candidate_template_path.as_posix() if candidate_template_path else "",
        "kline_files": file_rows,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
    }
    write_json(manifest, manifest_path)

    pytest_status, pytest_summary = run_pytest_quiet()
    can_enter_v11 = write_report(
        report_path=report_path,
        config=config,
        readiness=readiness,
        manifest_path=manifest_path,
        profile_path=profile_path,
        replay_cases_path=replay_cases_path,
        readiness_path=readiness_path,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
        candidate_template_path=candidate_template_path,
    )

    return {
        "config": config,
        "readiness": readiness,
        "pytest_status": pytest_status,
        "pytest_summary": pytest_summary,
        "can_enter_v11": can_enter_v11,
        "manifest_path": manifest_path,
        "profile_path": profile_path,
        "replay_cases_path": replay_cases_path,
        "readiness_path": readiness_path,
        "report_path": report_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare V0.10 real ETF dataset intake artifacts.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "configs" / "real_data_prep.yaml"),
        help="Path to real data preparation config.",
    )
    args = parser.parse_args(argv)
    output = run(args.config)
    readiness = output["readiness"]
    pytest_status = output["pytest_status"]
    can_enter_v11 = bool(output["can_enter_v11"])

    print(f"data_status={readiness['data_status']}")
    print(f"symbol_count={readiness['symbol_count']}")
    print(f"qualified_symbol_count={readiness['qualified_symbol_count']}")
    print(f"candidate_date_count={readiness['candidate_date_count']}")
    print(f"replay_case_count={readiness['replay_case_count']}")
    print(f"is_ready_for_expanded_replay={readiness['is_ready_for_expanded_replay']}")
    print(f"next_step={readiness['next_step']}")
    print("")
    print("V0.10 总结")
    print("1. 是否实现真实 ETF 数据契约: 是")
    print("2. 是否实现真实 K 线扫描: 是")
    print("3. 是否实现 K 线 schema 校验: 是")
    print("4. 是否实现 K 线标准化: 是")
    print("5. 是否实现数据画像: 是")
    print("6. 是否实现候选池历史导入校验: 是")
    print("7. 是否实现 expanded replay cases 构造: 是")
    print(f"8. data_status: {readiness['data_status']}")
    print(f"9. symbol_count: {readiness['symbol_count']}")
    print(f"10. qualified_symbol_count: {readiness['qualified_symbol_count']}")
    print(f"11. candidate_date_count: {readiness['candidate_date_count']}")
    print(f"12. replay_case_count: {readiness['replay_case_count']}")
    print(f"13. is_ready_for_expanded_replay: {readiness['is_ready_for_expanded_replay']}")
    print(f"14. dataset manifest 路径: {output['manifest_path']}")
    print(f"15. dataset profile 路径: {output['profile_path']}")
    print(f"16. expanded replay cases 路径: {output['replay_cases_path']}")
    print(f"17. readiness JSON 路径: {output['readiness_path']}")
    print("18. 是否未训练: 是")
    print("19. 是否未运行 torchrun: 是")
    print("20. 是否未调用 GPU 推理: 是")
    print("21. 是否未接主项目: 是")
    print(f"22. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("23. 是否生成 docs/real_etf_data_contract.md: 是")
    print("24. 是否生成 docs/kronos_v10_real_data_quality_report.md: 是")
    print(f"25. 是否可以进入 V0.11 真实数据 zero-shot 回放评估: {'是' if can_enter_v11 else '否'}")
    print("")
    if pytest_status != "PASS":
        print("C. V0.10 FAIL，暂不可进入 V0.11。请列出失败原因和下一步修复建议。")
        return 1
    if can_enter_v11:
        print("A. V0.10 DATA_READY PASS，可以进入 V0.11 真实数据 zero-shot 回放评估。")
        return 0
    print("B. V0.10 PIPELINE_READY BUT DATA_NOT_READY，暂不可进入 V0.11。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
