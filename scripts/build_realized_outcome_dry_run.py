"""Build a review-required realized outcome dry-run from traceable prices.

The script computes only when the required entry and horizon exit prices exist.
Missing horizon prices are reported explicitly. It does not fabricate outcomes,
promote reviewed fields, start formal_v011, train, run torchrun, use GPU APIs,
or provide trading advice.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from audit_external_market_data_sources import (
    DRY_RUN_HORIZONS,
    RUNTIME_OUTPUT_DIR,
    SOURCE_ACCESS_AUDIT_JSON,
    audit_symbol_cache,
    build_audit,
    local_cache_root,
    normalize_date,
    read_price_rows,
    sha256,
    utc_now,
)


REALIZED_OUTCOME_CSV = RUNTIME_OUTPUT_DIR / "realized_outcome_dry_run.csv"
PROVENANCE_MANIFEST_JSON = RUNTIME_OUTPUT_DIR / "provenance_manifest.json"
CHECKSUM_MANIFEST_JSON = RUNTIME_OUTPUT_DIR / "checksum_manifest.json"


def load_or_build_audit() -> dict[str, Any]:
    if SOURCE_ACCESS_AUDIT_JSON.exists():
        return json.loads(SOURCE_ACCESS_AUDIT_JSON.read_text(encoding="utf-8"))
    report = build_audit()
    RUNTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_ACCESS_AUDIT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        if not text:
            return None
        return float(text)
    except ValueError:
        return None


def direction_from_return(value: float) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def first_entry_index(rows: list[dict[str, str]], signal_date: str, price_field: str) -> int | None:
    for index, row in enumerate(rows):
        date = normalize_date(row.get("date"))
        price = parse_float(row.get(price_field))
        if date >= signal_date and price is not None:
            return index
    return None


def outcome_for_horizon(
    binding: dict[str, Any],
    rows: list[dict[str, str]],
    price_field: str,
    horizon_days: int,
) -> dict[str, Any]:
    signal_date = str(binding.get("signal_date") or "")
    entry_index = first_entry_index(rows, signal_date, price_field)
    base = {
        "candidate_id": binding.get("candidate_id"),
        "candidate_rank": binding.get("candidate_rank"),
        "symbol": binding.get("symbol"),
        "ticker": binding.get("ticker"),
        "display_name": binding.get("display_name"),
        "signal_date": signal_date,
        "horizon_trading_days": horizon_days,
        "horizon_status": "DRY_RUN_ASSUMED_NOT_FORMAL",
        "price_field_used": price_field,
        "price_adjustment_status": "UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED"
        if price_field == "close"
        else "ADJUSTED_CLOSE_AVAILABLE",
        "trading_day_rule": "entry is signal_date or first later row with a valid price; exit is N trading rows after entry in the same symbol price file",
        "missing_price_rule": "do not impute; leave realized_return and realized_direction empty when entry or horizon exit is unavailable",
        "entry_date": "",
        "entry_price": "",
        "exit_date": "",
        "exit_price": "",
        "realized_return": "",
        "realized_direction": "",
        "outcome_status": "",
    }
    if entry_index is None:
        base["outcome_status"] = "ENTRY_PRICE_MISSING"
        return base

    entry_row = rows[entry_index]
    entry_price = parse_float(entry_row.get(price_field))
    base["entry_date"] = normalize_date(entry_row.get("date"))
    base["entry_price"] = entry_price
    exit_index = entry_index + horizon_days
    if exit_index >= len(rows):
        base["outcome_status"] = "HORIZON_NOT_MATURE_OR_PRICE_MISSING"
        return base

    exit_row = rows[exit_index]
    exit_price = parse_float(exit_row.get(price_field))
    if entry_price is None or exit_price is None:
        base["outcome_status"] = "ENTRY_OR_EXIT_PRICE_INVALID"
        return base

    realized_return = exit_price / entry_price - 1
    base["exit_date"] = normalize_date(exit_row.get("date"))
    base["exit_price"] = exit_price
    base["realized_return"] = f"{realized_return:.12g}"
    base["realized_direction"] = direction_from_return(realized_return)
    base["outcome_status"] = "REALIZED_OUTCOME_DRY_RUN_COMPUTED_REVIEW_REQUIRED"
    return base


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "candidate_id",
        "candidate_rank",
        "symbol",
        "ticker",
        "display_name",
        "signal_date",
        "horizon_trading_days",
        "horizon_status",
        "price_field_used",
        "price_adjustment_status",
        "trading_day_rule",
        "missing_price_rule",
        "entry_date",
        "entry_price",
        "exit_date",
        "exit_price",
        "realized_return",
        "realized_direction",
        "outcome_status",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def build_outputs() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    audit = load_or_build_audit()
    bindings = audit.get("candidate_bindings") or []
    cache_root_text = audit.get("local_market_data_audit", {}).get("cache_root")
    cache_root = Path(cache_root_text) if cache_root_text else None

    outcome_rows: list[dict[str, Any]] = []
    source_price_files: dict[str, dict[str, Any]] = {}
    if cache_root and cache_root.exists():
        for binding in bindings:
            symbol = str(binding.get("symbol") or "")
            signal_date = str(binding.get("signal_date") or "")
            if not symbol or not signal_date:
                continue
            price_path = cache_root / f"{symbol}.csv"
            if not price_path.exists():
                for horizon in DRY_RUN_HORIZONS:
                    outcome_rows.append(
                        {
                            **binding,
                            "horizon_trading_days": horizon,
                            "horizon_status": "DRY_RUN_ASSUMED_NOT_FORMAL",
                            "outcome_status": "PRICE_SOURCE_MISSING",
                        }
                    )
                continue
            rows = read_price_rows(price_path)
            audit_for_symbol = audit_symbol_cache(symbol, {signal_date}, cache_root)
            price_field = audit_for_symbol.get("price_field_used") or "close"
            source_price_files[symbol] = {
                "path": str(price_path),
                "checksum": sha256(price_path),
                "price_field_used": price_field,
                "price_adjustment_status": audit_for_symbol.get("price_adjustment_status"),
                "source_values": audit_for_symbol.get("source_values"),
                "latest_date": audit_for_symbol.get("latest_date"),
            }
            for horizon in DRY_RUN_HORIZONS:
                outcome_rows.append(outcome_for_horizon(binding, rows, str(price_field), horizon))

    computed_count = sum(
        1 for row in outcome_rows if row.get("outcome_status") == "REALIZED_OUTCOME_DRY_RUN_COMPUTED_REVIEW_REQUIRED"
    )
    if computed_count == len(outcome_rows) and outcome_rows:
        dry_run_status = "COMPLETED_REVIEW_REQUIRED"
    elif outcome_rows:
        dry_run_status = "PARTIAL_REVIEW_REQUIRED"
    else:
        dry_run_status = "NOT_RUN_NO_VALID_SOURCE"

    provenance = {
        "track": "P",
        "manifest_name": "realized_outcome_dry_run_provenance_manifest_v1_4_p",
        "generated_at": utc_now(),
        "realized_outcome_dry_run_status": dry_run_status,
        "outcome_provenance_status": "GENERATED_REVIEW_REQUIRED" if outcome_rows else "INSUFFICIENT",
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "candidate_binding_status": "CANDIDATE_ID_SYMBOL_SIGNAL_DATE_BOUND_REVIEW_REQUIRED"
        if bindings
        else "CANDIDATE_BINDING_NOT_AVAILABLE",
        "horizon_status": "DRY_RUN_ASSUMED_NOT_FORMAL",
        "dry_run_horizons_trading_days": DRY_RUN_HORIZONS,
        "price_field_rule": "Use adjusted_close only when present; otherwise use close and label UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED.",
        "trading_day_rule": "entry is signal_date or first later valid trading row; exit is N trading rows after entry.",
        "missing_price_rule": "No imputation, no forward fill, no guessed outcomes.",
        "timezone_date_normalization_rule": audit.get("timezone_date_normalization_rule"),
        "candidate_source_audit": audit.get("candidate_source_audit"),
        "source_price_files": source_price_files,
        "runtime_outputs": {
            "source_access_audit": str(SOURCE_ACCESS_AUDIT_JSON),
            "realized_outcome_dry_run": str(REALIZED_OUTCOME_CSV),
            "provenance_manifest": str(PROVENANCE_MANIFEST_JSON),
            "checksum_manifest": str(CHECKSUM_MANIFEST_JSON),
        },
        "computed_outcome_count": computed_count,
        "output_row_count": len(outcome_rows),
        "review_required_note": "Dry-run output is not a reviewed formal outcome and must not release the stopline.",
    }
    checksums = {
        "track": "P",
        "manifest_name": "realized_outcome_dry_run_checksum_manifest_v1_4_p",
        "generated_at": utc_now(),
        "inputs": {
            "source_access_audit": sha256(SOURCE_ACCESS_AUDIT_JSON) if SOURCE_ACCESS_AUDIT_JSON.exists() else None,
            "candidate_source": audit.get("candidate_source_audit", {}).get("checksum"),
            "price_files": source_price_files,
        },
        "outputs": {},
        "formal_v011_ready": False,
        "stopline_triggered": True,
    }
    return outcome_rows, provenance, checksums


def main() -> None:
    RUNTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome_rows, provenance, checksums = build_outputs()
    write_csv(REALIZED_OUTCOME_CSV, outcome_rows)
    PROVENANCE_MANIFEST_JSON.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums["outputs"] = {
        "realized_outcome_dry_run": sha256(REALIZED_OUTCOME_CSV),
        "provenance_manifest": sha256(PROVENANCE_MANIFEST_JSON),
    }
    CHECKSUM_MANIFEST_JSON.write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums["outputs"]["checksum_manifest"] = "SELF_CHECKSUM_NOT_EMBEDDED_USE_VALIDATOR_COMPUTED_HASH"
    CHECKSUM_MANIFEST_JSON.write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
