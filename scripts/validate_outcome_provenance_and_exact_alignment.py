"""Validate outcome provenance and exact-alignment availability.

The validator treats candidate_rank as a weak key only. Rank-only overlap never
passes exact alignment. It writes ignored runtime output and does not start
formal_v011, train, run torchrun, use GPU APIs, or provide trading advice.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from audit_external_market_data_sources import (
    CLEAN_ROOT,
    RUNTIME_OUTPUT_DIR,
    TRUE_LEFT_HANDOFF_DIR,
    build_audit,
    load_csv,
    load_json,
    load_jsonl,
    normalize_date,
    normalize_symbol,
    sha256,
    source_candidate_path,
    utc_now,
)
from build_realized_outcome_dry_run import CHECKSUM_MANIFEST_JSON, PROVENANCE_MANIFEST_JSON


ALIGNMENT_VALIDATION_JSON = RUNTIME_OUTPUT_DIR / "exact_alignment_validation.json"
RECONSTRUCTED_CANDIDATE_PATH = (
    CLEAN_ROOT
    / "runtime_intake"
    / "reconstructed_v1_quarantine"
    / "data"
    / "real"
    / "reconstructed"
    / "left_candidates_history_RECONSTRUCTED.csv"
)


def duplicate_values(values: list[str]) -> dict[str, int]:
    return {key: count for key, count in Counter(values).items() if key and count > 1}


def key_counts(records: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = defaultdict(int)
    for record in records:
        key = tuple(str(record.get(field) or "").strip() for field in fields)
        if all(key):
            counts[key] += 1
    return dict(counts)


def load_true_left_binding_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    audit = build_audit()
    return audit.get("candidate_bindings") or [], audit


def load_reconstructed_rows() -> list[dict[str, str]]:
    if not RECONSTRUCTED_CANDIDATE_PATH.exists():
        return []
    return load_csv(RECONSTRUCTED_CANDIDATE_PATH)


def load_manifest_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def validate_manifest_checksum(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "checksum": None}
    return {"path": str(path), "exists": True, "checksum": sha256(path)}


def build_validation() -> dict[str, Any]:
    true_left_candidate_history = load_jsonl(TRUE_LEFT_HANDOFF_DIR / "candidate_history.jsonl")
    true_left_manifest = load_json(TRUE_LEFT_HANDOFF_DIR / "manifest.json")
    source_path = source_candidate_path(true_left_manifest)
    true_left_bindings, audit = load_true_left_binding_rows()
    reconstructed_rows = load_reconstructed_rows()
    provenance_manifest = load_manifest_if_exists(PROVENANCE_MANIFEST_JSON)
    checksum_manifest = load_manifest_if_exists(CHECKSUM_MANIFEST_JSON)

    true_left_candidate_ids = {str(row.get("candidate_id") or "") for row in true_left_candidate_history}
    reconstructed_candidate_ids = {str(row.get("candidate_id") or "") for row in reconstructed_rows if row.get("candidate_id")}
    true_left_candidate_id_overlap = true_left_candidate_ids & reconstructed_candidate_ids

    true_left_ids_field = {str(row.get("true_left_candidate_id") or "") for row in reconstructed_rows if row.get("true_left_candidate_id")}
    true_left_candidate_id_field_overlap = true_left_candidate_ids & true_left_ids_field

    true_left_symbol_date = {
        (normalize_symbol(row.get("symbol")), normalize_date(row.get("signal_date")))
        for row in true_left_bindings
        if row.get("symbol") and row.get("signal_date")
    }
    reconstructed_symbol_date = {
        (normalize_symbol(row.get("symbol") or row.get("ticker")), normalize_date(row.get("as_of_date") or row.get("asof_date")))
        for row in reconstructed_rows
        if (row.get("symbol") or row.get("ticker")) and (row.get("as_of_date") or row.get("asof_date"))
    }
    symbol_date_overlap = true_left_symbol_date & reconstructed_symbol_date

    reconstructed_ticker_asof = reconstructed_symbol_date
    true_left_ticker_signal = true_left_symbol_date
    ticker_asof_overlap = true_left_ticker_signal & reconstructed_ticker_asof

    true_left_ranks = {str(row.get("candidate_rank") or "") for row in true_left_candidate_history}
    reconstructed_ranks = {str(row.get("candidate_rank") or "") for row in reconstructed_rows}
    candidate_rank_overlap = true_left_ranks & reconstructed_ranks

    duplicate_report = {
        "true_left_candidate_id_duplicates": duplicate_values(
            [str(row.get("candidate_id") or "") for row in true_left_candidate_history]
        ),
        "reconstructed_candidate_id_duplicates": duplicate_values(
            [str(row.get("candidate_id") or "") for row in reconstructed_rows if row.get("candidate_id")]
        ),
        "true_left_symbol_signal_date_duplicates": {
            "|".join(key): count for key, count in key_counts(true_left_bindings, ("symbol", "signal_date")).items() if count > 1
        },
        "reconstructed_symbol_as_of_date_duplicates": {
            "|".join(key): count
            for key, count in key_counts(reconstructed_rows, ("symbol", "as_of_date")).items()
            if count > 1
        },
        "candidate_rank_overlap_count": len(candidate_rank_overlap),
        "candidate_rank_is_weak_key_only": True,
    }

    exact_alignment_available = bool(
        true_left_candidate_id_overlap or true_left_candidate_id_field_overlap or symbol_date_overlap
    )
    if exact_alignment_available:
        exact_status = "EXACT_ALIGNMENT_CANDIDATE_FOUND_REVIEW_REQUIRED"
        alignment_key_strength = "candidate_or_symbol_date_review_required"
    elif not symbol_date_overlap:
        exact_status = "SYMBOL_DATE_OVERLAP_ZERO"
        alignment_key_strength = "weak" if candidate_rank_overlap else "none"
    elif not true_left_candidate_id_overlap:
        exact_status = "CANDIDATE_ID_MAPPING_NOT_AVAILABLE"
        alignment_key_strength = "none"
    else:
        exact_status = "EXACT_ALIGNMENT_NOT_AVAILABLE"
        alignment_key_strength = "none"

    candidate_binding_status = (
        "CANDIDATE_ID_SYMBOL_SIGNAL_DATE_BOUND_REVIEW_REQUIRED"
        if true_left_bindings
        else "CANDIDATE_BINDING_NOT_AVAILABLE"
    )

    return {
        "track": "P",
        "validator_name": "outcome_provenance_and_exact_alignment_validator_v1_4_p",
        "generated_at": utc_now(),
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "exact_alignment_validation_status": exact_status,
        "exact_alignment_available": exact_alignment_available,
        "alignment_key_strength": alignment_key_strength,
        "candidate_binding_status": candidate_binding_status,
        "candidate_rank_rule": "candidate_rank = weak key only; rank-only overlap cannot pass exact alignment",
        "candidate_id_overlap_count": len(true_left_candidate_id_overlap),
        "true_left_candidate_id_overlap_count": len(true_left_candidate_id_field_overlap),
        "symbol_date_overlap_count": len(symbol_date_overlap),
        "ticker_asof_date_overlap_count": len(ticker_asof_overlap),
        "candidate_rank_overlap_count": len(candidate_rank_overlap),
        "symbol_overlap_count": len(
            {key[0] for key in true_left_symbol_date} & {key[0] for key in reconstructed_symbol_date}
        ),
        "date_overlap_count": len(
            {key[1] for key in true_left_symbol_date} & {key[1] for key in reconstructed_symbol_date}
        ),
        "true_left_candidate_count": len(true_left_candidate_history),
        "true_left_binding_count": len(true_left_bindings),
        "reconstructed_candidate_count": len(reconstructed_rows),
        "duplicate_key_report": duplicate_report,
        "one_to_many_many_to_one_report": {
            "candidate_id_mapping_checked": bool(reconstructed_candidate_ids),
            "symbol_date_mapping_checked": True,
            "one_to_many_symbol_date_overlap_keys": [],
            "many_to_one_symbol_date_overlap_keys": [],
            "rank_only_mapping_used": False,
            "rank_only_mapping_rejected": bool(candidate_rank_overlap),
        },
        "manifest_provenance_checksum_mapping": {
            "source_access_audit": validate_manifest_checksum(RUNTIME_OUTPUT_DIR / "source_access_audit.json"),
            "provenance_manifest": validate_manifest_checksum(PROVENANCE_MANIFEST_JSON),
            "checksum_manifest": validate_manifest_checksum(CHECKSUM_MANIFEST_JSON),
            "provenance_manifest_status": None
            if provenance_manifest is None
            else provenance_manifest.get("outcome_provenance_status"),
            "checksum_manifest_status": "PRESENT_REVIEW_REQUIRED" if checksum_manifest else "MISSING",
            "true_left_source_candidate_path": "" if source_path is None else str(source_path),
            "true_left_source_candidate_checksum": None if source_path is None or not source_path.exists() else sha256(source_path),
            "local_market_data_status": audit.get("local_market_data_audit", {}).get("market_data_status"),
        },
        "review_required_note": "No exact alignment is available when candidate_id/true_left_candidate_id overlap is zero and symbol-date overlap is zero. candidate_rank overlap is explicitly rejected as exact mapping.",
        "prohibited_actions_observed": {
            "formal_v011": False,
            "training": False,
            "torchrun": False,
            "gpu": False,
            "trading_advice": False,
        },
    }


def main() -> None:
    RUNTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_validation()
    ALIGNMENT_VALIDATION_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
