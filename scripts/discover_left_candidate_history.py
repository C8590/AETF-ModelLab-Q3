#!/usr/bin/env python3
"""Read-only discovery of left-side candidate history sources for V0.10.2-D."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

import sys

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model_lab.left_candidate_discovery import (  # noqa: E402
    LeftCandidateDiscoveryConfig,
    discover_left_project_paths,
    export_left_candidate_history,
    load_source_dataframe,
    normalize_candidate_history_df,
    scan_candidate_history_files,
    source_rank,
    validate_normalized_candidate_history,
    write_inventory_json,
)


DEFAULT_LEFT_ROOTS = [
    Path(r"E:\AETF-LeftLab"),
    Path(r"E:\A-ETF-L"),
    Path(r"E:\AETF-L"),
    Path(r"E:\AETF-Left"),
    Path(r"E:\AETF"),
]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def available_kline_symbols(raw_kline_dir: Path) -> set[str]:
    if not raw_kline_dir.exists():
        return set()
    return {path.stem for path in raw_kline_dir.glob("*.csv") if path.is_file()}


def select_export_source(
    inventory_rows: list[dict[str, Any]],
    available_symbols: set[str],
) -> tuple[dict[str, Any] | None, pd.DataFrame | None, list[dict[str, Any]]]:
    reviewed: list[dict[str, Any]] = []
    candidates = [row for row in inventory_rows if row.get("is_candidate_history_like") and row.get("extractable")]
    for source in sorted(candidates, key=source_rank):
        review = {
            "path": source.get("path", ""),
            "file_kind": source.get("file_kind", ""),
            "table_name": source.get("table_name", ""),
            "status": "REJECTED",
            "candidate_date_count": 0,
            "row_count": 0,
            "matched_symbol_count": 0,
            "validation_errors": [],
        }
        try:
            raw_df = load_source_dataframe(source)
            normalized = normalize_candidate_history_df(raw_df, Path(str(source["path"])))
            errors = validate_normalized_candidate_history(normalized, available_symbols)
            symbols = set(normalized["symbol"].astype(str).str.strip()) & available_symbols
            review.update(
                {
                    "candidate_date_count": int(pd.to_datetime(normalized["as_of_date"], errors="coerce").dt.strftime("%Y-%m-%d").nunique()),
                    "row_count": int(len(normalized)),
                    "matched_symbol_count": len(symbols),
                    "validation_errors": errors,
                }
            )
            if not errors:
                review["status"] = "SELECTED"
                reviewed.append(review)
                return source, normalized, reviewed
        except Exception as exc:  # noqa: BLE001 - continue to the next possible source.
            review["validation_errors"] = [str(exc).replace("\n", " ").replace("|", "/").strip()]
        reviewed.append(review)
    return None, None, reviewed


def write_report(report_path: Path, inventory: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    selected_source = inventory.get("selected_source") or {}
    lines = [
        "# Left Candidate History Discovery Report",
        "",
        f"- 运行时间: {inventory['generated_at']}",
        f"- discovery_status: {inventory['discovery_status']}",
        f"- 是否找到左侧项目目录: {inventory['left_project_found']}",
        f"- 左侧项目目录: {', '.join(inventory['left_project_roots']) if inventory['left_project_roots'] else '-'}",
        f"- 扫描文件数量: {inventory['scanned_file_count']}",
        f"- 候选历史源数量: {inventory['candidate_source_count']}",
        f"- 是否导出 left_candidates_history.csv: {inventory['exported']}",
        f"- 导出路径: {inventory['output_path'] if inventory['exported'] else '-'}",
        f"- 选中来源: {selected_source.get('path', '-') if selected_source else '-'}",
        f"- candidate_date_count: {inventory['candidate_date_count']}",
        f"- candidate row_count: {inventory['candidate_row_count']}",
        f"- matched_symbol_count: {inventory['matched_symbol_count']}",
        "",
        "## Candidate Sources",
        "",
    ]
    candidate_rows = [row for row in inventory["files"] if row.get("is_candidate_history_like")]
    if candidate_rows:
        lines.extend(
            [
                "| path | kind | rows | matched_fields | confidence |",
                "| --- | --- | ---: | --- | ---: |",
            ]
        )
        for row in candidate_rows[:50]:
            fields = ",".join(row.get("matched_standard_fields", []))
            table_name = row.get("table_name", "")
            path = f"{row['path']}#{table_name}" if table_name else row["path"]
            lines.append(
                f"| {path} | {row.get('file_kind', '')} | {row.get('row_count', 0)} | {fields} | {row.get('confidence_score', 0)} |"
            )
    else:
        lines.append("- 未发现可确认的真实历史候选池来源。")

    lines.extend(["", "## Reviewed Sources", ""])
    reviewed = inventory.get("reviewed_sources", [])
    if reviewed:
        for row in reviewed:
            reason = "; ".join(row.get("validation_errors", [])) or "-"
            table_name = row.get("table_name", "")
            label = f"{row['path']}#{table_name}" if table_name else row["path"]
            lines.append(f"- {row['status']}: {label}; rows={row['row_count']}; dates={row['candidate_date_count']}; matched_symbols={row['matched_symbol_count']}; reason={reason}")
    else:
        lines.append("- 无可复核来源。")

    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- 仅只读扫描左侧项目目录。",
            "- 未修改左侧项目。",
            "- 未运行左侧项目程序。",
            "- 未训练模型。",
            "- 未运行 torchrun。",
            "- 未调用 GPU 推理。",
            "- 未运行 KronosAdapter。",
            "- 未生成交易建议。",
            "- 未生成 reconstructed candidate history。",
        ]
    )
    if inventory["discovery_status"] in {"LEFT_PROJECT_NOT_FOUND", "LEFT_CANDIDATE_HISTORY_NOT_FOUND"}:
        lines.extend(
            [
                "",
                "## Next Steps",
                "",
                "- 用户提供真实 left_candidates_history.csv。",
                "- 或用户明确授权按左侧规则重建 reconstructed candidate history。",
                "- reconstructed 不等于真实历史快照，不能冒充真实历史候选池。",
            ]
        )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(
    inventory_path: str | Path = ROOT / "outputs" / "real_data" / "left_candidate_history_source_inventory.json",
    report_path: str | Path = ROOT / "docs" / "left_candidate_history_discovery_report.md",
    output_path: str | Path = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv",
    raw_kline_dir: str | Path = ROOT / "data" / "real" / "raw" / "kline",
    candidate_roots: list[Path] | None = None,
    config: LeftCandidateDiscoveryConfig | None = None,
) -> dict[str, Any]:
    config = config or LeftCandidateDiscoveryConfig()
    roots = candidate_roots if candidate_roots is not None else DEFAULT_LEFT_ROOTS
    left_roots = discover_left_project_paths(roots)
    output = resolve_project_path(output_path)
    available_symbols = available_kline_symbols(resolve_project_path(raw_kline_dir))

    files: list[dict[str, Any]] = []
    selected_source: dict[str, Any] | None = None
    normalized: pd.DataFrame | None = None
    reviewed_sources: list[dict[str, Any]] = []
    exported = False
    status = "LEFT_PROJECT_NOT_FOUND"
    candidate_date_count = 0
    candidate_row_count = 0
    matched_symbol_count = 0

    if left_roots:
        files = scan_candidate_history_files(left_roots, config)
        selected_source, normalized, reviewed_sources = select_export_source(files, available_symbols)
        if selected_source is not None and normalized is not None:
            export_left_candidate_history(normalized, output)
            exported = True
            status = "EXPORTED"
            candidate_date_count = int(pd.to_datetime(normalized["as_of_date"], errors="coerce").dt.strftime("%Y-%m-%d").nunique())
            candidate_row_count = int(len(normalized))
            matched_symbol_count = len(set(normalized["symbol"].astype(str).str.strip()) & available_symbols)
        else:
            status = "LEFT_CANDIDATE_HISTORY_NOT_FOUND"

    inventory = {
        "mode": "left_candidate_history_discovery",
        "version": "V0.10.2-D",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "discovery_status": status,
        "left_project_found": bool(left_roots),
        "left_project_roots": [path.as_posix() for path in left_roots],
        "scanned_file_count": len(files),
        "candidate_source_count": sum(1 for row in files if row.get("is_candidate_history_like")),
        "exported": exported,
        "output_path": output.as_posix(),
        "candidate_date_count": candidate_date_count,
        "candidate_row_count": candidate_row_count,
        "matched_symbol_count": matched_symbol_count,
        "selected_source": selected_source or {},
        "reviewed_sources": reviewed_sources,
        "files": files,
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_write": True,
        "no_broker_interface": True,
        "no_market_advice": True,
        "no_reconstructed_history": True,
    }
    write_inventory_json(inventory, resolve_project_path(inventory_path))
    write_report(resolve_project_path(report_path), inventory)
    print(f"discovery_status={status}")
    print(f"left_project_found={bool(left_roots)}")
    print(f"scanned_file_count={inventory['scanned_file_count']}")
    print(f"candidate_source_count={inventory['candidate_source_count']}")
    print(f"exported={exported}")
    print(f"candidate_date_count={candidate_date_count}")
    print(f"candidate_row_count={candidate_row_count}")
    print(f"matched_symbol_count={matched_symbol_count}")
    return inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover and export true left candidate history snapshots.")
    parser.add_argument("--inventory", default=str(ROOT / "outputs" / "real_data" / "left_candidate_history_source_inventory.json"))
    parser.add_argument("--report", default=str(ROOT / "docs" / "left_candidate_history_discovery_report.md"))
    parser.add_argument("--output", default=str(ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    args = parser.parse_args(argv)
    run(args.inventory, args.report, args.output, args.raw_kline_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
