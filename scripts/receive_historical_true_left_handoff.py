"""Receive and validate the LeftLab historical true-left handoff runtime package.

The script reads the runtime exchange directory, copies the package into ignored
runtime_inbox, extracts it, and writes receive-review outputs under ignored
outputs. It does not train, import torch, call GPU APIs, start formal_v011,
modify LeftLab, or modify Protocol.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCHANGE_DIR = Path(
    r"E:\aetf_runtime_exchange\left_to_model\historical_true_left_candidate_handoff_v1_4_full_export"
)
INBOX_DIR = Path("runtime_inbox/historical_true_left_candidate_handoff_v1_4_full_export")
EXTRACT_DIR = INBOX_DIR / "extracted"
OUTPUT_DIR = Path("outputs/historical_true_left_handoff_receive_review")

ZIP_NAME = "historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.zip"
EXPECTED_ZIP_SHA256 = "d4662f3a2279831eaf865ff7be7e341df7b86a9a6535a55b51bf8339d8e2ab5d"
EXPECTED_STATUS = "REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED"
EXPECTED_POLICY = "GAP_POLICY_WARNING_EXCLUDE_UNAVAILABLE_SYMBOL_DATES"
EXPECTED_WARNING_SYMBOL = "560000"
EXPECTED_WARNING_NAME = "智能电车ETF浦银"

REQUIRED_ZIP_MEMBERS = {
    "manifest.json",
    "checksum_manifest.json",
    "provenance.json",
    "README.md",
}
REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "signal_date",
    "candidate_rank",
    "generation_run_id",
    "leftlab_code_commit",
    "rule_version",
    "input_data_snapshot_ref",
    "as_of_boundary",
    "data_available_until",
    "source_artifact",
    "source_row",
}
SYMBOL_FIELDS = ("symbol", "etf_code", "ticker")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def copy_exchange_files() -> dict[str, bool]:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    names = [
        ZIP_NAME,
        "historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.sha256",
        "historical_true_left_runtime_full_export_report.md",
        "review_historical_true_left_runtime_full_export.md",
        "TRANSFER_RECEIPT.json",
        "DELIVERY_TO_MODELLAB_REVIEW.md",
    ]
    copied: dict[str, bool] = {}
    for name in names:
        source = EXCHANGE_DIR / name
        copied[name] = source.exists()
        if source.exists():
            shutil.copy2(source, INBOX_DIR / name)
    return copied


def extract_zip(zip_path: Path) -> list[str]:
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(EXTRACT_DIR)
        return archive.namelist()


def has_warning_symbol(items: Any) -> bool:
    text = json.dumps(items, ensure_ascii=False)
    return EXPECTED_WARNING_SYMBOL in text and EXPECTED_WARNING_NAME in text


def has_excluded_560000_20260610(items: Any) -> bool:
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("symbol") == EXPECTED_WARNING_SYMBOL and item.get("signal_date") == "2026-06-10":
                return True
    return "560000" in json.dumps(items, ensure_ascii=False) and "2026-06-10" in json.dumps(items, ensure_ascii=False)


def validate_checksum_manifest(zip_path: Path, names: list[str], checksum_manifest: dict[str, str]) -> dict[str, Any]:
    required_payload = {"candidate_history.csv", "candidate_history.jsonl", "manifest.json", "provenance.json", "README.md"}
    present_payload = set(names)
    candidate_present = bool({"candidate_history.csv", "candidate_history.jsonl"} & present_payload)
    expected_covered = (required_payload - {"candidate_history.csv", "candidate_history.jsonl"}) | (
        {"candidate_history.csv"} if "candidate_history.csv" in present_payload else {"candidate_history.jsonl"}
    )

    mismatches: list[str] = []
    missing_listed_files: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        for member, expected_hash in checksum_manifest.items():
            if member not in names:
                missing_listed_files.append(member)
                continue
            actual_hash = sha256_bytes(archive.read(member))
            if actual_hash.lower() != str(expected_hash).lower():
                mismatches.append(member)
    missing_coverage = sorted(expected_covered - set(checksum_manifest))
    return {
        "candidate_history_present": candidate_present,
        "checksum_manifest_entries": len(checksum_manifest),
        "missing_listed_files": missing_listed_files,
        "hash_mismatches": mismatches,
        "missing_required_payload_coverage": missing_coverage,
        "covers_required_payload_files": not missing_coverage and candidate_present,
        "valid": not missing_listed_files and not mismatches and not missing_coverage and candidate_present,
    }


def load_candidate_rows() -> tuple[str, list[dict[str, str]]]:
    csv_path = EXTRACT_DIR / "candidate_history.csv"
    jsonl_path = EXTRACT_DIR / "candidate_history.jsonl"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return "candidate_history.csv", list(csv.DictReader(handle))
    if jsonl_path.exists():
        rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        return "candidate_history.jsonl", rows
    return "", []


def validate_candidates(rows: list[dict[str, str]]) -> dict[str, Any]:
    signal_dates = [row.get("signal_date", "") for row in rows]
    candidate_ids = [row.get("candidate_id", "") for row in rows]
    id_counts = Counter(candidate_ids)
    duplicate_ids = sorted(candidate_id for candidate_id, count in id_counts.items() if candidate_id and count > 1)

    missing_required = 0
    missing_symbol_identity = 0
    data_after_signal = 0
    recomputable = 0
    recompute_mismatches = 0
    rows_560000_20260610 = 0
    symbol_date_counter: Counter[str] = Counter()

    for row in rows:
        if any(not str(row.get(field, "")).strip() for field in REQUIRED_CANDIDATE_FIELDS):
            missing_required += 1
        symbol = next((str(row.get(field, "")).strip() for field in SYMBOL_FIELDS if str(row.get(field, "")).strip()), "")
        if not symbol:
            missing_symbol_identity += 1
        signal_date = row.get("signal_date", "")
        data_available_until = row.get("data_available_until", "")
        if data_available_until and signal_date and data_available_until > signal_date:
            data_after_signal += 1
        if symbol and signal_date:
            symbol_date_counter[f"{symbol}/{signal_date}"] += 1
        if symbol == EXPECTED_WARNING_SYMBOL and signal_date == "2026-06-10":
            rows_560000_20260610 += 1
        expected_id = f"leftlab:{row.get('generation_run_id', '')}:{signal_date}:{symbol}:{row.get('candidate_rank', '')}"
        if all([row.get("generation_run_id"), signal_date, symbol, row.get("candidate_rank")]):
            recomputable += 1
            if row.get("candidate_id") != expected_id:
                recompute_mismatches += 1

    unique_signal_dates = sorted(set(date for date in signal_dates if date))
    top_symbol_date_counts = [
        {"symbol_date": key, "count": value} for key, value in symbol_date_counter.most_common(10)
    ]
    return {
        "row_count": len(rows),
        "unique_signal_dates": len(unique_signal_dates),
        "signal_date_min": min(unique_signal_dates) if unique_signal_dates else None,
        "signal_date_max": max(unique_signal_dates) if unique_signal_dates else None,
        "candidate_id_present": all(bool(candidate_id) for candidate_id in candidate_ids),
        "candidate_id_recomputable_rows": recomputable,
        "candidate_id_recompute_mismatches": recompute_mismatches,
        "candidate_id_unique": len(duplicate_ids) == 0,
        "duplicate_candidate_id_count": len(duplicate_ids),
        "missing_required_fields_count": missing_required + missing_symbol_identity,
        "missing_required_field_rows": missing_required,
        "missing_symbol_identity_rows": missing_symbol_identity,
        "data_available_until_after_signal_date_count": data_after_signal,
        "rows_560000_20260610": rows_560000_20260610,
        "top_symbol_date_counts": top_symbol_date_counts,
        "valid": (
            len(rows) == 8960
            and len(unique_signal_dates) == 448
            and (min(unique_signal_dates) if unique_signal_dates else None) == "2024-08-01"
            and (max(unique_signal_dates) if unique_signal_dates else None) == "2026-06-10"
            and len(duplicate_ids) == 0
            and missing_required == 0
            and missing_symbol_identity == 0
            and data_after_signal == 0
            and recompute_mismatches == 0
            and rows_560000_20260610 == 0
        ),
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "receive_review_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (OUTPUT_DIR / "receive_review_result.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        flat_keys = [
            "receive_status",
            "zip_sha256_expected",
            "zip_sha256_actual",
            "zip_sha256_match",
            "candidate_count",
            "unique_signal_dates",
            "signal_date_min",
            "signal_date_max",
            "full_pool_complete",
            "partial_pool_warning",
            "gap_policy",
            "duplicate_candidate_id_count",
            "missing_required_fields_count",
            "manifest_valid",
            "checksum_valid",
            "provenance_valid",
            "readme_valid",
            "formal_v011_ready",
        ]
        for key in flat_keys:
            writer.writerow([key, result.get(key)])
    summary = [
        "# Historical True-Left Handoff Receive Review Summary",
        "",
        f"- receive_status: {result['receive_status']}",
        f"- zip_sha256_match: {str(result['zip_sha256_match']).lower()}",
        f"- candidate_count: {result['candidate_count']}",
        f"- unique_signal_dates: {result['unique_signal_dates']}",
        f"- signal_date_range: {result['signal_date_min']} to {result['signal_date_max']}",
        f"- full_pool_complete: {str(result['full_pool_complete']).lower()}",
        f"- partial_pool_warning: {str(result['partial_pool_warning']).lower()}",
        f"- gap_policy: {result['gap_policy']}",
        f"- warning_symbols: {', '.join(result['warning_symbols'])}",
        f"- excluded_symbol_dates_includes_560000_20260610: {str(result['excluded_560000_20260610']).lower()}",
        f"- duplicate_candidate_id_count: {result['duplicate_candidate_id_count']}",
        f"- missing_required_fields_count: {result['missing_required_fields_count']}",
        f"- manifest_valid: {str(result['manifest_valid']).lower()}",
        f"- checksum_valid: {str(result['checksum_valid']).lower()}",
        f"- provenance_valid: {str(result['provenance_valid']).lower()}",
        f"- readme_valid: {str(result['readme_valid']).lower()}",
        f"- formal_v011_ready: {str(result['formal_v011_ready']).lower()}",
        "",
        "No training, torchrun, GPU, QMT, trading advice, LeftLab modification, or Protocol modification was performed.",
    ]
    (OUTPUT_DIR / "receive_review_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main() -> int:
    copied_files = copy_exchange_files()
    receipt_path = INBOX_DIR / "TRANSFER_RECEIPT.json"
    receipt = read_json(receipt_path)
    receipt_valid = bool(receipt.get("review_required") is True and receipt.get("modellab_formal_v011_ready") is False)

    zip_path = INBOX_DIR / ZIP_NAME
    zip_exists = zip_path.exists()
    actual_zip_hash = sha256_path(zip_path) if zip_exists else ""
    zip_sha256_match = actual_zip_hash.lower() == EXPECTED_ZIP_SHA256

    zip_members = extract_zip(zip_path) if zip_exists else []
    required_members_present = REQUIRED_ZIP_MEMBERS.issubset(zip_members) and (
        "candidate_history.csv" in zip_members or "candidate_history.jsonl" in zip_members
    )

    manifest = read_json(EXTRACT_DIR / "manifest.json")
    checksum_manifest = read_json(EXTRACT_DIR / "checksum_manifest.json")
    provenance = read_json(EXTRACT_DIR / "provenance.json")
    readme_text = (EXTRACT_DIR / "README.md").read_text(encoding="utf-8-sig")
    candidate_file, candidate_rows = load_candidate_rows()

    checksum_validation = validate_checksum_manifest(zip_path, zip_members, checksum_manifest)
    candidate_validation = validate_candidates(candidate_rows)

    warning_symbols = manifest.get("warning_symbols", [])
    excluded_symbol_dates = manifest.get("excluded_symbol_dates", [])
    provenance_policy = provenance.get("artifact_policy", {})
    provenance_gap_policy = provenance.get("gap_policy", {})

    manifest_signal_dates = manifest.get("runtime_full_export_signal_dates", [])
    manifest_signal_min = min(manifest_signal_dates) if manifest_signal_dates else manifest.get("signal_date_min")
    manifest_signal_max = max(manifest_signal_dates) if manifest_signal_dates else manifest.get("signal_date_max")
    manifest_unique_signal_dates = len(set(manifest_signal_dates)) if manifest_signal_dates else manifest.get("unique_signal_dates")

    manifest_valid = (
        (manifest.get("handoff_status") or manifest.get("status")) == EXPECTED_STATUS
        and manifest.get("dry_run") is False
        and manifest.get("export_mode") == "runtime_full_export"
        and manifest.get("candidate_count") == 8960
        and manifest_unique_signal_dates == 448
        and manifest_signal_min == "2024-08-01"
        and manifest_signal_max == "2026-06-10"
        and manifest.get("full_pool_complete") is False
        and manifest.get("partial_pool_warning") is True
        and manifest.get("gap_policy") == EXPECTED_POLICY
        and has_warning_symbol(warning_symbols)
        and has_excluded_560000_20260610(excluded_symbol_dates)
    )
    provenance_valid = (
        manifest.get("replay_status") == "REPLAYED"
        and manifest.get("original_historical_handoff_exists") is False
        and provenance.get("command_contract", {}).get("dry_run") is False
        and provenance.get("command_contract", {}).get("export_mode") == "runtime_full_export"
        and provenance_policy.get("used_future_outcome") is False
        and provenance_policy.get("used_reconstructed") is False
        and provenance_policy.get("used_modellab") is False
        and provenance_policy.get("trained_model") is False
        and provenance_policy.get("used_torchrun") is False
        and provenance_policy.get("used_gpu") is False
        and provenance_gap_policy.get("gap_policy") == EXPECTED_POLICY
        and provenance_gap_policy.get("full_pool_complete") is False
        and provenance_gap_policy.get("partial_pool_warning") is True
    )
    readme_valid = (
        EXPECTED_STATUS in readme_text
        and "replay_status: REPLAYED" in readme_text
        and "formal_v011_ready" in readme_text
        and "full_pool_complete: false" in readme_text
        and "partial_pool_warning: true" in readme_text
        and EXPECTED_WARNING_SYMBOL in readme_text
    )
    receive_valid = all(
        [
            all(copied_files.values()),
            receipt_valid,
            zip_exists,
            zip_sha256_match,
            required_members_present,
            manifest_valid,
            checksum_validation["valid"],
            provenance_valid,
            candidate_validation["valid"],
            readme_valid,
        ]
    )

    result: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "exchange_dir": str(EXCHANGE_DIR),
        "runtime_inbox_dir": str(INBOX_DIR),
        "extract_dir": str(EXTRACT_DIR),
        "outputs_dir": str(OUTPUT_DIR),
        "copied_files": copied_files,
        "receipt_valid": receipt_valid,
        "zip_exists": zip_exists,
        "zip_filename": ZIP_NAME,
        "zip_sha256_expected": EXPECTED_ZIP_SHA256,
        "zip_sha256_actual": actual_zip_hash,
        "zip_sha256_match": zip_sha256_match,
        "zip_members": zip_members,
        "required_zip_members_present": required_members_present,
        "candidate_file": candidate_file,
        "manifest_valid": manifest_valid,
        "checksum_valid": checksum_validation["valid"],
        "checksum_validation": checksum_validation,
        "provenance_valid": provenance_valid,
        "readme_valid": readme_valid,
        "candidate_validation": candidate_validation,
        "receive_status": (
            "HISTORICAL_TRUE_LEFT_HANDOFF_SCHEMA_CHECK_PASSED_REVIEW_REQUIRED"
            if receive_valid
            else "HISTORICAL_TRUE_LEFT_HANDOFF_RECEIVED_REVIEW_REQUIRED"
        ),
        "candidate_count": candidate_validation["row_count"],
        "unique_signal_dates": candidate_validation["unique_signal_dates"],
        "signal_date_min": candidate_validation["signal_date_min"],
        "signal_date_max": candidate_validation["signal_date_max"],
        "full_pool_complete": manifest.get("full_pool_complete"),
        "partial_pool_warning": manifest.get("partial_pool_warning"),
        "gap_policy": manifest.get("gap_policy"),
        "warning_symbols": [
            f"{item.get('symbol')} {item.get('name')}" for item in warning_symbols if isinstance(item, dict)
        ],
        "excluded_symbol_dates": excluded_symbol_dates,
        "excluded_560000_20260610": has_excluded_560000_20260610(excluded_symbol_dates),
        "duplicate_candidate_id_count": candidate_validation["duplicate_candidate_id_count"],
        "missing_required_fields_count": candidate_validation["missing_required_fields_count"],
        "full_pool_complete_true_error": manifest.get("full_pool_complete") is True,
        "suggest_realized_outcome_calculation_review": receive_valid,
        "formal_v011_ready": False,
        "trained_model": False,
        "torchrun": False,
        "gpu": False,
        "modified_leftlab": False,
        "modified_protocol": False,
        "trading_advice": False,
    }
    write_outputs(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if receive_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
