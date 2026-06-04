from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


FORBIDDEN_OUTPUT_FIELD_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)

PATH_KEYWORDS = (
    "candidate",
    "candidates",
    "left",
    "rank",
    "score",
    "pool",
    "snapshot",
    "selection",
    "selected",
    "watchlist",
    "etf",
    "history",
    "daily",
)

FIELD_SYNONYMS = {
    "as_of_date": ("as_of_date", "date", "trade_date", "trading_date", "snapshot_date", "run_date"),
    "symbol": ("symbol", "code", "etf_code", "fund_code", "ts_code"),
    "display_name": ("display_name", "name", "etf_name", "fund_name"),
    "candidate_rank": ("candidate_rank", "rank", "score_rank", "left_rank", "sort_rank"),
    "left_score": ("left_score", "score", "total_score", "final_score", "rank_score"),
    "notes": ("notes", "note", "source", "remark"),
}


@dataclass(frozen=True)
class LeftCandidateDiscoveryConfig:
    max_file_size_mb: int = 100
    allowed_suffixes: tuple[str, ...] = (
        ".csv",
        ".json",
        ".jsonl",
        ".parquet",
        ".db",
        ".sqlite",
        ".log",
        ".txt",
    )
    required_output_columns: tuple[str, ...] = (
        "as_of_date",
        "symbol",
        "display_name",
        "candidate_rank",
        "left_score",
        "notes",
    )


def discover_left_project_paths(candidate_roots: list[Path]) -> list[Path]:
    return [path for path in candidate_roots if path.exists() and path.is_dir()]


def scan_candidate_history_files(left_roots: list[Path], config: LeftCandidateDiscoveryConfig) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    max_size = int(config.max_file_size_mb) * 1024 * 1024
    suffixes = {suffix.lower() for suffix in config.allowed_suffixes}

    for root in left_roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in suffixes:
                continue
            try:
                size = path.stat().st_size
            except OSError as exc:
                inventory.append(_base_inventory_row(path, status="SKIPPED", error_message=_safe_error(exc)))
                continue
            if size > max_size:
                row = _base_inventory_row(path, status="SKIPPED", size_bytes=size)
                row["error_message"] = f"file size exceeds max_file_size_mb={config.max_file_size_mb}"
                inventory.append(row)
                continue

            inspected = inspect_tabular_file(path)
            inspected["size_bytes"] = size
            inventory.extend(_expand_inspection_rows(inspected))
    return inventory


def inspect_tabular_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    base = _base_inventory_row(path, status="INSPECTED", size_bytes=_file_size(path))
    try:
        if suffix == ".csv":
            df = pd.read_csv(path, nrows=5000)
            return _with_frame_metadata(base, df, "csv")
        if suffix == ".json":
            df = pd.read_json(path)
            return _with_frame_metadata(base, df, "json")
        if suffix == ".jsonl":
            df = pd.read_json(path, lines=True)
            return _with_frame_metadata(base, df, "jsonl")
        if suffix == ".parquet":
            df = pd.read_parquet(path)
            return _with_frame_metadata(base, df, "parquet")
        if suffix in {".db", ".sqlite"}:
            base["file_kind"] = "sqlite"
            base["tables"] = _inspect_sqlite_tables(path)
            base["source_count"] = len(base["tables"])
            return base
        if suffix in {".log", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")[:1_000_000]
            matches = _keyword_matches(text)
            base.update(
                {
                    "file_kind": suffix.lstrip("."),
                    "row_count": 0,
                    "column_names": [],
                    "matched_standard_fields": [],
                    "matched_field_count": 0,
                    "text_keyword_matches": matches,
                    "is_candidate_history_like": bool(matches and base["path_keyword_matches"]),
                    "extractable": False,
                    "confidence_score": len(matches) + len(base["path_keyword_matches"]),
                }
            )
            return base
    except Exception as exc:  # noqa: BLE001 - discovery must keep scanning.
        base["status"] = "ERROR"
        base["error_message"] = _safe_error(exc)
        return base

    base["status"] = "SKIPPED"
    base["error_message"] = f"unsupported suffix: {suffix}"
    return base


def normalize_candidate_history_df(df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    column_map = _build_column_map(df.columns)
    missing = [column for column in LeftCandidateDiscoveryConfig().required_output_columns[:-1] if column not in column_map]
    if missing:
        raise ValueError(f"candidate history is missing required source fields: {missing}")

    out = pd.DataFrame()
    out["as_of_date"] = pd.to_datetime(df[column_map["as_of_date"]], errors="coerce").dt.strftime("%Y-%m-%d")
    out["symbol"] = df[column_map["symbol"]].map(_normalize_symbol)
    if "display_name" in column_map:
        out["display_name"] = df[column_map["display_name"]].fillna("").astype(str).str.strip()
    else:
        out["display_name"] = ""
    out["candidate_rank"] = pd.to_numeric(df[column_map["candidate_rank"]], errors="coerce")
    out["left_score"] = pd.to_numeric(df[column_map["left_score"]], errors="coerce")
    if "notes" in column_map:
        base_notes = df[column_map["notes"]].fillna("").astype(str).str.strip()
    else:
        base_notes = pd.Series([""] * len(out), index=out.index)

    source_note = f"source_path={_display_path(source_path)};candidate_history_type=true_left_snapshot"
    out["notes"] = base_notes.map(lambda value: f"{value};{source_note}" if value else source_note)
    return out[list(LeftCandidateDiscoveryConfig().required_output_columns)].drop_duplicates().reset_index(drop=True)


def validate_normalized_candidate_history(df: pd.DataFrame, available_symbols: set[str]) -> list[str]:
    errors: list[str] = []
    required = list(LeftCandidateDiscoveryConfig().required_output_columns)
    missing = [column for column in required if column not in df.columns]
    if missing:
        return [f"missing normalized columns: {missing}"]

    for column in df.columns:
        lower = str(column).lower()
        for forbidden in FORBIDDEN_OUTPUT_FIELD_PARTS:
            if forbidden in lower:
                errors.append(f"normalized output field contains forbidden term: {column}")

    dates = pd.to_datetime(df["as_of_date"], errors="coerce")
    if dates.isna().any():
        errors.append("as_of_date contains unparsable values.")
    symbols = df["symbol"].fillna("").astype(str).str.strip()
    if symbols.eq("").any():
        errors.append("symbol contains empty values.")
    ranks = pd.to_numeric(df["candidate_rank"], errors="coerce")
    if ranks.isna().any():
        errors.append("candidate_rank contains non-numeric values.")
    pd.to_numeric(df["left_score"], errors="coerce")
    matched_symbols = set(symbols) & set(available_symbols)
    if not matched_symbols:
        errors.append("no candidate symbols match available raw kline symbols.")
    return errors


def export_left_candidate_history(df: pd.DataFrame, output_path: Path) -> None:
    for column in df.columns:
        lower = str(column).lower()
        if any(forbidden in lower for forbidden in FORBIDDEN_OUTPUT_FIELD_PARTS):
            raise ValueError(f"refusing to export forbidden output field: {column}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df[list(LeftCandidateDiscoveryConfig().required_output_columns)].to_csv(output_path, index=False, encoding="utf-8-sig")


def load_source_dataframe(source: dict[str, Any]) -> pd.DataFrame:
    path = Path(source["path"])
    kind = source.get("file_kind", path.suffix.lower().lstrip("."))
    if kind == "csv":
        return pd.read_csv(path)
    if kind == "json":
        return pd.read_json(path)
    if kind == "jsonl":
        return pd.read_json(path, lines=True)
    if kind == "parquet":
        return pd.read_parquet(path)
    if kind == "sqlite":
        table_name = str(source.get("table_name", "")).replace('"', '""')
        if not table_name:
            raise ValueError("sqlite source is missing table_name.")
        with _connect_sqlite_readonly(path) as conn:
            return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    raise ValueError(f"source is not extractable as candidate history: {kind}")


def source_rank(source: dict[str, Any]) -> tuple[int, int, int]:
    kind = str(source.get("file_kind", "")).lower()
    path_text = str(source.get("path", "")).lower()
    priority = 5
    if kind == "csv" and any(word in path_text for word in ("daily", "snapshot", "history", "candidate")):
        priority = 0
    elif kind == "csv":
        priority = 1
    elif kind == "sqlite":
        priority = 2
    elif kind in {"json", "jsonl"}:
        priority = 3
    elif kind in {"log", "txt"}:
        priority = 4
    confidence = int(source.get("confidence_score", 0) or 0)
    rows = int(source.get("row_count", 0) or 0)
    return (priority, -confidence, -rows)


def _base_inventory_row(path: Path, status: str, size_bytes: int = 0, error_message: str = "") -> dict[str, Any]:
    matches = _keyword_matches(path.as_posix().lower())
    return {
        "path": path.as_posix(),
        "suffix": path.suffix.lower(),
        "status": status,
        "size_bytes": int(size_bytes),
        "path_keyword_matches": matches,
        "file_kind": path.suffix.lower().lstrip("."),
        "row_count": 0,
        "column_names": [],
        "matched_standard_fields": [],
        "matched_field_count": 0,
        "is_candidate_history_like": False,
        "extractable": False,
        "confidence_score": len(matches),
        "error_message": error_message,
    }


def _with_frame_metadata(base: dict[str, Any], df: pd.DataFrame, file_kind: str) -> dict[str, Any]:
    matched_fields = _matched_standard_fields(df.columns)
    base.update(
        {
            "file_kind": file_kind,
            "row_count": int(len(df)),
            "column_names": [str(column) for column in df.columns],
            "matched_standard_fields": matched_fields,
            "matched_field_count": len(matched_fields),
            "is_candidate_history_like": _is_candidate_like(base["path_keyword_matches"], matched_fields, len(df)),
            "extractable": file_kind not in {"log", "txt"},
            "confidence_score": len(base["path_keyword_matches"]) + len(matched_fields) * 3 + min(int(len(df) > 0), 1),
        }
    )
    return base


def _inspect_sqlite_tables(path: Path) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    with _connect_sqlite_readonly(path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        for (table_name,) in rows:
            escaped = str(table_name).replace('"', '""')
            columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{escaped}")').fetchall()]
            try:
                row_count = int(conn.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0])
            except Exception:
                row_count = 0
            matched_fields = _matched_standard_fields(columns)
            path_matches = _keyword_matches(f"{path.as_posix().lower()} {str(table_name).lower()}")
            tables.append(
                {
                    "path": path.as_posix(),
                    "suffix": path.suffix.lower(),
                    "status": "INSPECTED",
                    "size_bytes": _file_size(path),
                    "path_keyword_matches": path_matches,
                    "file_kind": "sqlite",
                    "table_name": str(table_name),
                    "row_count": row_count,
                    "column_names": [str(column) for column in columns],
                    "matched_standard_fields": matched_fields,
                    "matched_field_count": len(matched_fields),
                    "is_candidate_history_like": _is_candidate_like(path_matches, matched_fields, row_count),
                    "extractable": True,
                    "confidence_score": len(path_matches) + len(matched_fields) * 3 + min(int(row_count > 0), 1),
                    "error_message": "",
                }
            )
    return tables


def _expand_inspection_rows(inspected: dict[str, Any]) -> list[dict[str, Any]]:
    if inspected.get("file_kind") == "sqlite" and "tables" in inspected:
        tables = inspected.get("tables") or []
        if tables:
            return list(tables)
        inspected = dict(inspected)
        inspected.pop("tables", None)
        return [inspected]
    return [inspected]


def _connect_sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri_path = path.resolve().as_posix()
    return sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)


def _build_column_map(columns: Any) -> dict[str, str]:
    normalized = {_normalize_column_name(column): str(column) for column in columns}
    column_map: dict[str, str] = {}
    for standard, synonyms in FIELD_SYNONYMS.items():
        for synonym in synonyms:
            matched = normalized.get(_normalize_column_name(synonym))
            if matched is not None:
                column_map[standard] = matched
                break
    return column_map


def _matched_standard_fields(columns: Any) -> list[str]:
    column_map = _build_column_map(columns)
    return [column for column in LeftCandidateDiscoveryConfig().required_output_columns if column in column_map]


def _is_candidate_like(path_matches: list[str], matched_fields: list[str], row_count: int) -> bool:
    required = {"as_of_date", "symbol", "candidate_rank", "left_score"}
    return row_count > 0 and required.issubset(set(matched_fields)) and bool(path_matches)


def _normalize_column_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _normalize_symbol(value: Any) -> str:
    text = str(value).strip()
    match = re.search(r"(\d{6})", text)
    return match.group(1) if match else text


def _keyword_matches(value: str) -> list[str]:
    lowered = value.lower()
    return [keyword for keyword in PATH_KEYWORDS if keyword in lowered]


def _display_path(path: Path) -> str:
    try:
        return path.as_posix()
    except Exception:
        return str(path)


def _file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except OSError:
        return 0


def _safe_error(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def write_inventory_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
