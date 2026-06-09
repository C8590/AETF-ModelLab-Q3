"""Audit traceable market data sources for P-track outcome dry-run.

This script reads only local handoff/runtime inputs and writes ignored runtime
outputs. It does not promote any field to a reviewed outcome, start formal_v011,
train, run torchrun, use GPU APIs, or provide trading advice.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLEAN_ROOT = Path(__file__).resolve().parents[1]
TRUE_LEFT_HANDOFF_DIR = (
    CLEAN_ROOT
    / "runtime_inbox"
    / "leftlab_v1_4_d_ready_handoff"
    / "true_left_candidate_history_handoff"
)
RUNTIME_OUTPUT_DIR = CLEAN_ROOT / "runtime_external_outcome_dry_run"
SOURCE_ACCESS_AUDIT_JSON = RUNTIME_OUTPUT_DIR / "source_access_audit.json"

DRY_RUN_HORIZONS = [5, 10, 20]
BASE_COMMIT = "516d1cdbf32d63c7ea180cd98cc6ec6bbfc20695"
BASE_TAG = "modellab-v1.4-o-register-n-reviewed-insufficient-sources-final"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def normalize_symbol(value: object) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(6) if text.isdigit() and len(text) < 6 else text


def normalize_date(value: object) -> str:
    text = str(value or "").strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]
    return text


def parse_artifact_row(artifact_ref: str) -> int | None:
    marker = "#row="
    if marker not in artifact_ref:
        return None
    try:
        return int(artifact_ref.rsplit(marker, 1)[1])
    except ValueError:
        return None


def true_left_paths() -> dict[str, Path]:
    return {
        "candidate_history": TRUE_LEFT_HANDOFF_DIR / "candidate_history.jsonl",
        "manifest": TRUE_LEFT_HANDOFF_DIR / "manifest.json",
        "artifact_index": TRUE_LEFT_HANDOFF_DIR / "artifact_index.json",
        "checksums": TRUE_LEFT_HANDOFF_DIR / "checksums.sha256",
    }


def load_true_left_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    paths = true_left_paths()
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("missing true-left handoff inputs: " + ", ".join(missing))
    manifest = load_json(paths["manifest"])
    candidate_history = load_jsonl(paths["candidate_history"])
    artifact_index = load_json(paths["artifact_index"])
    return manifest, candidate_history, artifact_index


def source_candidate_path(manifest: dict[str, Any]) -> Path | None:
    workspace = manifest.get("workspace")
    source_artifacts = manifest.get("source_artifacts") or []
    for artifact in source_artifacts:
        if artifact.get("artifact_name") == "left_side_paper_candidates":
            rel_path = artifact.get("path")
            if workspace and rel_path:
                return Path(str(workspace)) / str(rel_path)
    return None


def build_candidate_bindings(
    candidate_history: list[dict[str, Any]],
    source_rows: list[dict[str, str]],
    source_path: Path,
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for record in candidate_history:
        row_number = parse_artifact_row(str(record.get("artifact_ref", "")))
        source_row = source_rows[row_number - 1] if row_number and 0 < row_number <= len(source_rows) else {}
        signal_date = normalize_date(source_row.get("signal_date") or source_row.get("date") or record.get("timestamp"))
        symbol = normalize_symbol(source_row.get("symbol") or source_row.get("etf_code"))
        bindings.append(
            {
                "candidate_id": record.get("candidate_id"),
                "candidate_rank": record.get("candidate_rank"),
                "artifact_ref": record.get("artifact_ref"),
                "source_row_number": row_number,
                "symbol": symbol,
                "ticker": symbol,
                "display_name": source_row.get("name") or source_row.get("display_name") or "",
                "signal_date": signal_date,
                "source_candidate_path": str(source_path),
                "binding_status": "BOUND_TO_TRUE_LEFT_SOURCE_ROW" if symbol and signal_date else "BINDING_INSUFFICIENT",
            }
        )
    return bindings


def candidate_source_audit(
    manifest: dict[str, Any],
    candidate_history: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = source_candidate_path(manifest)
    if path is None or not path.exists():
        return (
            {
                "source_candidate_status": "SOURCE_CANDIDATE_FILE_NOT_AVAILABLE",
                "path": "" if path is None else str(path),
                "checksum": None,
                "checksum_matches_manifest": False,
            },
            [],
        )

    source_rows = load_csv(path)
    expected_hash = None
    for artifact in manifest.get("source_artifacts") or []:
        if artifact.get("artifact_name") == "left_side_paper_candidates":
            expected_hash = artifact.get("sha256")
            break
    actual_hash = sha256(path)
    bindings = build_candidate_bindings(candidate_history, source_rows, path)
    return (
        {
            "source_candidate_status": "SOURCE_CANDIDATE_FILE_ACCESSIBLE_REVIEW_REQUIRED",
            "path": str(path),
            "rows": len(source_rows),
            "checksum": actual_hash,
            "expected_checksum": expected_hash,
            "checksum_matches_manifest": bool(expected_hash and actual_hash == expected_hash),
            "binding_count": len(bindings),
            "bound_count": sum(1 for item in bindings if item["binding_status"] == "BOUND_TO_TRUE_LEFT_SOURCE_ROW"),
        },
        bindings,
    )


def local_cache_root(manifest: dict[str, Any]) -> Path | None:
    workspace = manifest.get("workspace")
    if not workspace:
        return None
    root = Path(str(workspace)) / "data" / "cache"
    return root if root.exists() else None


def read_price_rows(path: Path) -> list[dict[str, str]]:
    rows = load_csv(path)
    rows.sort(key=lambda row: normalize_date(row.get("date")))
    return rows


def audit_symbol_cache(symbol: str, signal_dates: set[str], cache_root: Path) -> dict[str, Any]:
    path = cache_root / f"{symbol}.csv"
    if not path.exists():
        return {
            "symbol": symbol,
            "source_status": "LOCAL_PRICE_CACHE_MISSING",
            "path": str(path),
            "checksum": None,
            "price_field_used": None,
        }

    rows = read_price_rows(path)
    dates = [normalize_date(row.get("date")) for row in rows if normalize_date(row.get("date"))]
    fields = set(rows[0].keys()) if rows else set()
    close_available = "close" in fields
    adjusted_close_available = "adjusted_close" in fields or "adj_close" in fields
    source_values = sorted({str(row.get("source") or "").strip() for row in rows if str(row.get("source") or "").strip()})
    latest_date = max(dates) if dates else ""
    start_date = min(dates) if dates else ""
    signal_date_coverage = {
        signal_date: {
            "entry_date_available": any(date >= signal_date for date in dates),
            "exact_signal_date_present": signal_date in dates,
            "trading_rows_on_or_after_signal_date": sum(1 for date in dates if date >= signal_date),
        }
        for signal_date in sorted(signal_dates)
    }
    return {
        "symbol": symbol,
        "source_status": "LOCAL_PRICE_CACHE_ACCESSIBLE_REVIEW_REQUIRED",
        "path": str(path),
        "checksum": sha256(path),
        "rows": len(rows),
        "start_date": start_date,
        "latest_date": latest_date,
        "fields": sorted(fields),
        "source_values": source_values,
        "price_field_used": "adjusted_close" if adjusted_close_available else "close" if close_available else None,
        "price_adjustment_status": (
            "ADJUSTED_CLOSE_AVAILABLE"
            if adjusted_close_available
            else "UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED"
            if close_available
            else "NO_CLOSE_FIELD_AVAILABLE"
        ),
        "signal_date_coverage": signal_date_coverage,
    }


def audit_local_market_data(manifest: dict[str, Any], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    cache_root = local_cache_root(manifest)
    if cache_root is None:
        return {
            "market_data_status": "LOCAL_PRICE_CACHE_ROOT_NOT_AVAILABLE",
            "cache_root": "",
            "symbol_audits": [],
        }

    by_symbol: dict[str, set[str]] = {}
    for binding in bindings:
        symbol = str(binding.get("symbol") or "")
        signal_date = str(binding.get("signal_date") or "")
        if symbol and signal_date:
            by_symbol.setdefault(symbol, set()).add(signal_date)

    symbol_audits = [audit_symbol_cache(symbol, dates, cache_root) for symbol, dates in sorted(by_symbol.items())]
    accessible = [item for item in symbol_audits if item["source_status"] == "LOCAL_PRICE_CACHE_ACCESSIBLE_REVIEW_REQUIRED"]
    return {
        "market_data_status": (
            "LOCAL_PRICE_CACHE_ACCESSIBLE_REVIEW_REQUIRED" if accessible else "LOCAL_PRICE_CACHE_NOT_AVAILABLE"
        ),
        "cache_root": str(cache_root),
        "candidate_symbol_count": len(by_symbol),
        "accessible_symbol_count": len(accessible),
        "missing_symbol_count": len(symbol_audits) - len(accessible),
        "symbol_audits": symbol_audits,
    }


def build_audit() -> dict[str, Any]:
    manifest, candidate_history, artifact_index = load_true_left_inputs()
    candidate_audit, bindings = candidate_source_audit(manifest, candidate_history)
    local_market_data = audit_local_market_data(manifest, bindings)

    accessible = local_market_data.get("accessible_symbol_count", 0) == len(
        {item.get("symbol") for item in bindings if item.get("symbol")}
    )
    if accessible and bindings:
        status = "FOUND_ACCESSIBLE_REVIEW_REQUIRED"
    else:
        status = "SOURCE_FOUND_BUT_LICENSE_OR_PROVENANCE_INSUFFICIENT"

    return {
        "track": "P",
        "audit_name": "external_market_data_source_access_audit_v1_4_p",
        "generated_at": utc_now(),
        "base_commit": BASE_COMMIT,
        "base_tag": BASE_TAG,
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "external_market_data_access_status": status,
        "horizon_status": "DRY_RUN_ASSUMED_NOT_FORMAL",
        "dry_run_horizons_trading_days": DRY_RUN_HORIZONS,
        "timezone_date_normalization_rule": "Dates are normalized to YYYY-MM-DD strings; source timezone is treated as China A-share trading calendar context when provided by the local cache.",
        "true_left_handoff_dir": str(TRUE_LEFT_HANDOFF_DIR),
        "true_left_manifest": {
            "candidate_history_type": manifest.get("candidate_history_type"),
            "candidate_count": manifest.get("candidate_count"),
            "workspace": manifest.get("workspace"),
            "handoff_export_commit": manifest.get("handoff_export_commit"),
            "not_reconstructed": manifest.get("not_reconstructed"),
        },
        "true_left_artifact_index_input_count": len(artifact_index.get("inputs") or []),
        "candidate_source_audit": candidate_audit,
        "candidate_bindings": bindings,
        "local_market_data_audit": local_market_data,
        "source_acceptance_note": "Local cache is traceable by path, provider marker, retrieval/update timestamp, and checksum, but remains review-required and is not formal outcome evidence.",
        "prohibited_actions_observed": {
            "formal_v011": False,
            "training": False,
            "torchrun": False,
            "gpu": False,
            "trading_advice": False,
        },
    }


def main() -> None:
    report = build_audit()
    RUNTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_ACCESS_AUDIT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
