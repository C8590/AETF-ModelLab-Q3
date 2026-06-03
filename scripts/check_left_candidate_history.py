#!/usr/bin/env python3
"""Check real left candidate history intake without reading the left project."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_COLUMNS = [
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "notes",
]

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
                    raise ValueError(f"candidate history result field contains forbidden term: {key}")
            assert_no_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_fields(child)


def available_kline_symbols(raw_kline_dir: Path) -> set[str]:
    if not raw_kline_dir.exists():
        return set()
    return {path.stem for path in raw_kline_dir.glob("*.csv") if path.is_file()}


def check_candidate_history(candidate_path: Path, raw_kline_dir: Path) -> dict[str, Any]:
    if not candidate_path.exists():
        return {
            "candidate_history_status": "CANDIDATE_HISTORY_MISSING",
            "candidate_date_count": 0,
            "row_count": 0,
            "symbol_count": 0,
            "min_as_of_date": "",
            "max_as_of_date": "",
            "error_messages": [f"{candidate_path.as_posix()} does not exist."],
        }

    df = pd.read_csv(candidate_path)
    missing_columns = [column for column in CANDIDATE_COLUMNS if column not in df.columns]
    if missing_columns:
        return {
            "candidate_history_status": "SCHEMA_INVALID",
            "candidate_date_count": 0,
            "row_count": int(len(df)),
            "symbol_count": 0,
            "min_as_of_date": "",
            "max_as_of_date": "",
            "error_messages": [f"missing columns: {missing_columns}"],
        }

    errors: list[str] = []
    parsed_dates = pd.to_datetime(df["as_of_date"], errors="coerce")
    if parsed_dates.isna().any():
        errors.append("as_of_date contains unparsable values.")

    symbols = df["symbol"].astype(str).str.strip()
    if symbols.eq("").any():
        errors.append("symbol contains empty values.")
    kline_symbols = available_kline_symbols(raw_kline_dir)
    unmatched = sorted(set(symbols.dropna()) - kline_symbols)
    if unmatched:
        errors.append(f"symbols missing raw kline CSV: {unmatched}")

    ranks = pd.to_numeric(df["candidate_rank"], errors="coerce")
    if ranks.isna().any() or (ranks <= 0).any():
        errors.append("candidate_rank must be positive numeric values.")
    pd.to_numeric(df["left_score"], errors="coerce")

    valid_dates = parsed_dates.dropna()
    result = {
        "candidate_history_status": "PASS" if not errors else "CHECK_FAILED",
        "candidate_date_count": int(valid_dates.dt.strftime("%Y-%m-%d").nunique()),
        "row_count": int(len(df)),
        "symbol_count": int(symbols.nunique()),
        "min_as_of_date": "" if valid_dates.empty else valid_dates.min().strftime("%Y-%m-%d"),
        "max_as_of_date": "" if valid_dates.empty else valid_dates.max().strftime("%Y-%m-%d"),
        "error_messages": errors,
    }
    assert_no_forbidden_fields(result)
    return result


def write_report(report_path: Path, candidate_path: Path, raw_kline_dir: Path, result: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Left Candidate History Check Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- candidate_history_path: {candidate_path.as_posix()}",
        f"- raw_kline_dir: {raw_kline_dir.as_posix()}",
        f"- candidate_history_status: {result['candidate_history_status']}",
        f"- candidate_date_count: {result['candidate_date_count']}",
        f"- row_count: {result['row_count']}",
        f"- symbol_count: {result['symbol_count']}",
        f"- min_as_of_date: {result['min_as_of_date']}",
        f"- max_as_of_date: {result['max_as_of_date']}",
        "",
        "## Errors",
        "",
    ]
    errors = result.get("error_messages", [])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- 无阻断错误。")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- 未伪造候选池历史。",
            "- 未读取主项目。",
            "- 未访问主项目数据库。",
            "- 未回写主项目。",
            "- 未产生交易建议。",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(
    candidate_path: str | Path = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv",
    raw_kline_dir: str | Path = ROOT / "data" / "real" / "raw" / "kline",
    report_path: str | Path = ROOT / "docs" / "left_candidate_history_check_report.md",
) -> dict[str, Any]:
    candidate = resolve_project_path(candidate_path)
    kline_dir = resolve_project_path(raw_kline_dir)
    report = resolve_project_path(report_path)
    result = check_candidate_history(candidate, kline_dir)
    write_report(report, candidate, kline_dir, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check left candidate history CSV.")
    parser.add_argument("--candidate-path", default=str(ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument("--report", default=str(ROOT / "docs" / "left_candidate_history_check_report.md"))
    args = parser.parse_args(argv)
    result = run(args.candidate_path, args.raw_kline_dir, args.report)
    print(f"candidate_history_status={result['candidate_history_status']}")
    print(f"candidate_date_count={result['candidate_date_count']}")
    print(f"row_count={result['row_count']}")
    print(f"symbol_count={result['symbol_count']}")
    return 0 if result["candidate_history_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
