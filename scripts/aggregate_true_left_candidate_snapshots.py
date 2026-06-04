#!/usr/bin/env python3
"""Aggregate true left candidate snapshot CSV files inside ModelLab only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_COLUMNS = [
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "notes",
]

FORBIDDEN_NOTE_TEXT = "reconstructed_candidate_history_not_real_left_snapshot"

FORBIDDEN_FIELD_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def assert_no_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_FIELD_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"aggregation output field contains forbidden term: {key}")
            assert_no_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_fields(child)


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = resolve_project_path(config_path)
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    if config.get("mode") != "true_left_candidate_history_aggregation":
        raise ValueError("mode must be true_left_candidate_history_aggregation.")
    safety = config.get("safety", {})
    blocked_flags = {
        "allow_reconstructed_as_true_history": safety.get("allow_reconstructed_as_true_history"),
        "allow_writeback_to_left_project": safety.get("allow_writeback_to_left_project"),
        "allow_trading_advice": safety.get("allow_trading_advice"),
        "allow_order_execution": safety.get("allow_order_execution"),
    }
    enabled = [name for name, value in blocked_flags.items() if bool(value)]
    if enabled:
        raise ValueError(f"safety flags must be false: {enabled}")
    return config


def snapshot_files(snapshot_dir: Path) -> list[Path]:
    if not snapshot_dir.exists():
        return []
    return sorted(path for path in snapshot_dir.glob("*_left_candidates.csv") if path.is_file())


def validate_snapshot(frame: pd.DataFrame, path: Path) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.as_posix()} missing required columns: {missing}")
    note_values = frame["notes"].astype(str)
    if note_values.str.contains(FORBIDDEN_NOTE_TEXT, case=False, na=False).any():
        raise ValueError(f"{path.as_posix()} contains forbidden reconstructed note text.")


def aggregate_snapshots(snapshot_dir: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    files = snapshot_files(snapshot_dir)
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    for file_index, path in enumerate(files):
        frame = pd.read_csv(path)
        validate_snapshot(frame, path)
        normalized = frame[REQUIRED_COLUMNS].copy()
        normalized["_source_file"] = path.name
        normalized["_source_index"] = file_index
        normalized["_source_row"] = range(len(normalized))
        frames.append(normalized)

    if not frames:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), [], []

    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(
        subset=["as_of_date", "symbol", "candidate_rank"],
        keep="last",
    )
    duplicate_count = before - len(combined)
    if duplicate_count:
        warnings.append(
            "duplicate as_of_date + symbol + candidate_rank rows were found; kept the last snapshot file entry."
        )

    combined = combined.sort_values(["as_of_date", "candidate_rank", "symbol"], kind="stable")
    return combined[REQUIRED_COLUMNS].reset_index(drop=True), [path.name for path in files], warnings


def build_result(
    *,
    status: str,
    snapshot_dir: Path,
    snapshot_names: list[str],
    history_path: Path,
    report_path: Path,
    manifest_path: Path,
    frame: pd.DataFrame,
    warnings: list[str],
    history_file_created: bool,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    result = {
        "aggregation_status": status,
        "snapshot_dir": snapshot_dir.as_posix(),
        "snapshot_count": len(snapshot_names),
        "snapshot_files": snapshot_names,
        "aggregated_history_path": history_path.as_posix(),
        "aggregation_report_path": report_path.as_posix(),
        "aggregation_manifest_path": manifest_path.as_posix(),
        "row_count": int(len(frame)),
        "candidate_date_count": int(frame["as_of_date"].nunique()) if not frame.empty else 0,
        "symbol_count": int(frame["symbol"].nunique()) if not frame.empty else 0,
        "history_file_created": history_file_created,
        "warnings": warnings,
        "errors": errors or [],
        "can_enter_formal_v011": False,
    }
    assert_no_forbidden_fields(result)
    return result


def write_report(report_path: Path, result: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# True Left Candidate History Aggregation Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- aggregation_status: {result['aggregation_status']}",
        f"- snapshot_dir: {result['snapshot_dir']}",
        f"- snapshot_count: {result['snapshot_count']}",
        f"- row_count: {result['row_count']}",
        f"- candidate_date_count: {result['candidate_date_count']}",
        f"- symbol_count: {result['symbol_count']}",
        f"- history_file_created: {result['history_file_created']}",
        f"- can_enter_formal_v011: {result['can_enter_formal_v011']}",
        "",
        "## Snapshot Files",
        "",
    ]
    snapshot_files_value = result.get("snapshot_files", [])
    if snapshot_files_value:
        lines.extend(f"- {name}" for name in snapshot_files_value)
    else:
        lines.append("- 无。")
    lines.extend(["", "## Warnings", ""])
    warnings = result.get("warnings", [])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 无。")
    lines.extend(["", "## Errors", ""])
    errors = result.get("errors", [])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- 无。")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- 未训练模型。",
            "- 未运行 torchrun。",
            "- 未调用 GPU。",
            "- 未读取 E:\\AETF-LeftLab。",
            "- 未访问主项目数据库。",
            "- 未回写主项目。",
            "- 未伪造 left_candidates_history.csv。",
            "- 未把 reconstructed 数据冒充真实历史。",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_manifest(manifest_path: Path, result: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "true_left_candidate_history_aggregation",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "result": result,
        "scope": {
            "no_model_training": True,
            "no_torchrun": True,
            "no_gpu_use": True,
            "no_left_project_access": True,
            "csv_read_only": True,
        },
    }
    assert_no_forbidden_fields(payload)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "true_left_candidate_history.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    snapshot_dir = resolve_project_path(config["inputs"]["snapshot_dir"])
    history_path = resolve_project_path(config["outputs"]["aggregated_history_path"])
    report_path = resolve_project_path(config["outputs"]["aggregation_report_path"])
    manifest_path = resolve_project_path(config["outputs"]["aggregation_manifest_path"])

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    names = [path.name for path in snapshot_files(snapshot_dir)]
    if not names:
        frame = pd.DataFrame(columns=REQUIRED_COLUMNS)
        result = build_result(
            status="SNAPSHOT_DIR_EMPTY",
            snapshot_dir=snapshot_dir,
            snapshot_names=[],
            history_path=history_path,
            report_path=report_path,
            manifest_path=manifest_path,
            frame=frame,
            warnings=["snapshot directory has no *_left_candidates.csv files; no history file was generated."],
            history_file_created=False,
        )
        write_report(report_path, result)
        write_manifest(manifest_path, result)
        return result

    try:
        frame, names, warnings = aggregate_snapshots(snapshot_dir)
    except Exception as exc:
        frame = pd.DataFrame(columns=REQUIRED_COLUMNS)
        result = build_result(
            status="SNAPSHOT_AGGREGATION_FAILED",
            snapshot_dir=snapshot_dir,
            snapshot_names=names,
            history_path=history_path,
            report_path=report_path,
            manifest_path=manifest_path,
            frame=frame,
            warnings=[],
            history_file_created=False,
            errors=[str(exc)],
        )
        write_report(report_path, result)
        write_manifest(manifest_path, result)
        raise

    history_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(history_path, index=False, encoding="utf-8-sig")
    result = build_result(
        status="TRUE_HISTORY_AGGREGATED",
        snapshot_dir=snapshot_dir,
        snapshot_names=names,
        history_path=history_path,
        report_path=report_path,
        manifest_path=manifest_path,
        frame=frame,
        warnings=warnings,
        history_file_created=True,
    )
    assert_no_forbidden_fields(result)
    write_report(report_path, result)
    write_manifest(manifest_path, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate true left candidate snapshot CSV files.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "true_left_candidate_history.yaml"))
    args = parser.parse_args(argv)
    result = run(args.config)
    print(f"aggregation_status={result['aggregation_status']}")
    print(f"snapshot_count={result['snapshot_count']}")
    print(f"row_count={result['row_count']}")
    print(f"candidate_date_count={result['candidate_date_count']}")
    print(f"history_file_created={result['history_file_created']}")
    return 0 if result["aggregation_status"] in {"SNAPSHOT_DIR_EMPTY", "TRUE_HISTORY_AGGREGATED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
