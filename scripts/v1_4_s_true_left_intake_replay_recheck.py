"""V1.4-S true-left intake, replay, and formal_v011 readiness recheck.

The script reads the LeftLab handoff package, validates intake gates, and
emits an ignored closeout report. It stops before replay when a stopline gate is
hit. It does not train, run torchrun, import torch, use GPU APIs, start
formal_v011, modify LeftLab, modify Protocol, infer missing history, forward
fill prices, or generate trading advice.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path
from typing import Any


EXCHANGE_ROOT = Path(r"E:\aetf_runtime_exchange\left_to_model")
HANDOFF_DIR_NAME = "historical_true_left_candidate_handoff_v1_4_full_export"
HANDOFF_DIR = EXCHANGE_ROOT / HANDOFF_DIR_NAME
ZIP_NAME = "historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.zip"
ZIP_PATH = HANDOFF_DIR / ZIP_NAME
ZIP_SHA256_PATH = HANDOFF_DIR / "historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.sha256"
TRANSFER_RECEIPT_PATH = HANDOFF_DIR / "TRANSFER_RECEIPT.json"
OUTPUT_DIR = Path("outputs/v1_4_s_true_left_intake_replay_recheck")

REQUIRED_ZIP_MEMBERS = {
    "candidate_history.csv",
    "manifest.json",
    "checksum_manifest.json",
    "provenance.json",
    "README.md",
}
REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "symbol",
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
DEFAULT_HORIZONS = [5, 10, 20]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def normalize_date(value: object) -> str:
    text = str(value or "").strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]
    return text


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and not result.stdout.strip()


def expected_zip_hash() -> str:
    if not ZIP_SHA256_PATH.exists():
        return ""
    text = ZIP_SHA256_PATH.read_text(encoding="utf-8-sig").strip()
    return text.split()[0] if text else ""


def load_zip_payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, str], str, list[str]]:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        members = archive.namelist()
        manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
        provenance = json.loads(archive.read("provenance.json").decode("utf-8-sig"))
        checksums = json.loads(archive.read("checksum_manifest.json").decode("utf-8-sig"))
        readme = archive.read("README.md").decode("utf-8-sig")
    return manifest, provenance, checksums, readme, members


def verify_inner_checksums(checksums: dict[str, str]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        members = set(archive.namelist())
        for member, expected in sorted(checksums.items()):
            exists = member in members
            actual = sha256_bytes(archive.read(member)) if exists else ""
            details.append(
                {
                    "file": member,
                    "exists": exists,
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                    "matched": exists and actual.lower() == str(expected).lower(),
                }
            )
    return {"details": details, "verified": bool(details) and all(item["matched"] for item in details)}


def load_candidate_rows() -> tuple[list[dict[str, str]], list[str]]:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        with archive.open("candidate_history.csv") as raw:
            wrapper = TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(wrapper)
            rows = [dict(row) for row in reader]
            fields = list(reader.fieldnames or [])
    return rows, fields


def validate_candidate_rows(rows: list[dict[str, str]], fields: list[str]) -> dict[str, Any]:
    missing_fields = sorted(REQUIRED_CANDIDATE_FIELDS - set(fields))
    ids = [str(row.get("candidate_id") or "").strip() for row in rows]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if key and count > 1)
    missing_required_rows = 0
    future_leakage_rows = 0
    timestamp_anomaly_rows = 0
    recompute_mismatches = 0
    signal_dates: list[str] = []
    max_generation_date = ""

    for row in rows:
        if any(not str(row.get(field) or "").strip() for field in REQUIRED_CANDIDATE_FIELDS):
            missing_required_rows += 1
        signal_date = normalize_date(row.get("signal_date"))
        data_until = normalize_date(row.get("data_available_until"))
        feature_end = normalize_date(row.get("feature_data_end_date"))
        generation_date = normalize_date(row.get("generation_time"))
        if signal_date:
            signal_dates.append(signal_date)
        if generation_date > max_generation_date:
            max_generation_date = generation_date
        if data_until and signal_date and data_until > signal_date:
            future_leakage_rows += 1
        if feature_end and signal_date and feature_end > signal_date:
            future_leakage_rows += 1
        if generation_date and signal_date and generation_date < signal_date:
            timestamp_anomaly_rows += 1
        expected_id = (
            f"leftlab:{row.get('generation_run_id', '')}:{signal_date}:"
            f"{row.get('symbol', '')}:{row.get('candidate_rank', '')}"
        )
        if all([row.get("generation_run_id"), signal_date, row.get("symbol"), row.get("candidate_rank")]):
            if row.get("candidate_id") != expected_id:
                recompute_mismatches += 1

    unique_signal_dates = sorted(set(signal_dates))
    return {
        "candidate_count": len(rows),
        "fields": fields,
        "missing_schema_fields": missing_fields,
        "duplicate_candidate_id_count": len(duplicate_ids),
        "duplicate_candidate_id_sample": duplicate_ids[:10],
        "missing_required_rows": missing_required_rows,
        "future_leakage_rows": future_leakage_rows,
        "timestamp_anomaly_rows": timestamp_anomaly_rows,
        "candidate_id_recompute_mismatches": recompute_mismatches,
        "unique_signal_dates": len(unique_signal_dates),
        "signal_date_min": unique_signal_dates[0] if unique_signal_dates else None,
        "signal_date_max": unique_signal_dates[-1] if unique_signal_dates else None,
        "max_generation_date": max_generation_date,
        "schema_valid": (
            len(rows) > 0
            and not missing_fields
            and missing_required_rows == 0
            and not duplicate_ids
            and future_leakage_rows == 0
            and timestamp_anomaly_rows == 0
            and recompute_mismatches == 0
        ),
    }


def get_horizons(manifest: dict[str, Any], provenance: dict[str, Any]) -> tuple[list[int], str]:
    for source_name, source in (("manifest", manifest), ("provenance", provenance)):
        for key in ("realized_outcome_horizons", "realized_outcome_horizon", "horizons", "dry_run_horizons_trading_days"):
            value = source.get(key)
            if isinstance(value, list) and value:
                parsed = [int(item) for item in value]
                return parsed, f"{source_name}.{key}"
    return DEFAULT_HORIZONS, "default_missing_from_handoff"


def parse_price_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    rows.sort(key=lambda row: normalize_date(row.get("date")))
    return rows


def horizon_maturity(rows: list[dict[str, str]], manifest: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    horizons, horizon_source = get_horizons(manifest, provenance)
    workspace = provenance.get("workspace") or r"E:\AETF-LeftLab"
    cache_root = Path(str(workspace)) / "data" / "cache"
    latest_signal = max((normalize_date(row.get("signal_date")) for row in rows), default="")
    latest_rows = [row for row in rows if normalize_date(row.get("signal_date")) == latest_signal]
    samples: list[dict[str, Any]] = []
    all_matured = True

    for row in latest_rows[:20]:
        symbol = str(row.get("symbol") or "").strip()
        price_path = cache_root / f"{symbol}.csv"
        dates: list[str] = []
        if price_path.exists():
            dates = [normalize_date(item.get("date")) for item in parse_price_rows(price_path)]
        on_or_after = [date for date in dates if date >= latest_signal]
        matured_by_horizon = {str(horizon): len(on_or_after) > horizon for horizon in horizons}
        if not all(matured_by_horizon.values()):
            all_matured = False
        samples.append(
            {
                "symbol": symbol,
                "signal_date": latest_signal,
                "price_file_exists": price_path.exists(),
                "latest_price_date": max(dates) if dates else None,
                "trading_rows_on_or_after_signal": len(on_or_after),
                "matured_by_horizon": matured_by_horizon,
            }
        )

    return {
        "horizons": horizons,
        "horizon_source": horizon_source,
        "horizon_info_present_in_handoff": horizon_source != "default_missing_from_handoff",
        "latest_signal_date": latest_signal,
        "sampled_latest_signal_candidates": len(samples),
        "latest_signal_horizon_maturity_samples": samples,
        "realized_outcome_horizon_matured": bool(samples) and all_matured,
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "v1_4_s_true_left_intake_replay_recheck.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# V1.4-S True-Left Intake Replay Recheck",
        "",
        f"- next_state: {result['next_state']}",
        f"- leftlab_handoff_received: {str(result['leftlab_handoff_received']).lower()}",
        f"- manifest_verified: {str(result['manifest_verified']).lower()}",
        f"- checksum_verified: {str(result['checksum_verified']).lower()}",
        f"- candidate_count: {result['candidate_count']}",
        f"- schema_valid: {str(result['schema_valid']).lower()}",
        f"- realized_outcome_horizon_matured: {str(result['realized_outcome_horizon_matured']).lower()}",
        f"- replay_completed: {str(result['replay_completed']).lower()}",
        f"- decision_matrix_recomputed: {str(result['decision_matrix_recomputed']).lower()}",
        f"- formal_v011_ready: {str(result['formal_v011_ready']).lower()}",
        f"- main_project_integration_allowed: {str(result['main_project_integration_allowed']).lower()}",
        f"- remaining_blocker_count: {result['remaining_blocker_count']}",
        f"- remaining_blockers: {', '.join(result['remaining_blockers'])}",
        "",
        "No training, torchrun, GPU, formal_v011, main-project integration,",
        "trading advice, LeftLab modification, Protocol modification, inference,",
        "synthetic history, or forward-fill was performed.",
    ]
    (OUTPUT_DIR / "v1_4_s_true_left_intake_replay_recheck.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    blockers: list[str] = []
    git_status_clean = git_clean()
    if not git_status_clean:
        blockers.append("git_status_not_clean")

    leftlab_handoff_received = HANDOFF_DIR.exists() and ZIP_PATH.exists()
    if not leftlab_handoff_received:
        blockers.append("leftlab_handoff_package_not_located")

    receipt_exists = TRANSFER_RECEIPT_PATH.exists()
    checksum_file_exists = ZIP_SHA256_PATH.exists()
    if not receipt_exists:
        blockers.append("transfer_receipt_missing")
    if not checksum_file_exists:
        blockers.append("checksum_file_missing")

    receipt: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    checksums: dict[str, str] = {}
    readme = ""
    members: list[str] = []
    rows: list[dict[str, str]] = []
    fields: list[str] = []
    candidate_validation: dict[str, Any] = {"candidate_count": 0, "schema_valid": False}
    inner_checksum = {"details": [], "verified": False}
    zip_sha256_actual = ""
    zip_sha256_expected = expected_zip_hash()
    zip_sha256_match = False

    try:
        if leftlab_handoff_received:
            zip_sha256_actual = sha256_path(ZIP_PATH)
            zip_sha256_match = bool(zip_sha256_expected) and zip_sha256_actual == zip_sha256_expected
            manifest, provenance, checksums, readme, members = load_zip_payload()
            rows, fields = load_candidate_rows()
            candidate_validation = validate_candidate_rows(rows, fields)
            inner_checksum = verify_inner_checksums(checksums)
        if receipt_exists:
            receipt = read_json(TRANSFER_RECEIPT_PATH)
    except Exception as exc:
        blockers.append(f"handoff_parse_error:{type(exc).__name__}")

    manifest_verified = (
        REQUIRED_ZIP_MEMBERS.issubset(set(members))
        and manifest.get("status") == "REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED"
        and manifest.get("dry_run") is False
        and manifest.get("export_mode") == "runtime_full_export"
        and manifest.get("candidate_count", 0) == candidate_validation.get("candidate_count")
    )
    if not manifest_verified:
        blockers.append("manifest_not_verified")

    checksum_verified = zip_sha256_match and inner_checksum["verified"]
    if not checksum_verified:
        blockers.append("checksum_not_verified")

    candidate_count = int(candidate_validation.get("candidate_count") or 0)
    if candidate_count <= 0:
        blockers.append("candidate_count_zero")

    schema_valid = bool(candidate_validation.get("schema_valid"))
    if not schema_valid:
        blockers.append("schema_not_valid_for_replay")

    artifact_policy = provenance.get("artifact_policy", {}) if isinstance(provenance.get("artifact_policy"), dict) else {}
    data_is_true_left_runtime = (
        manifest.get("runtime_full_export_generated") is True
        and manifest.get("not_reconstructed") is True
        and artifact_policy.get("used_reconstructed") is False
        and "reconstructed" not in str(manifest.get("source_branch", "")).lower()
    )
    if not data_is_true_left_runtime:
        blockers.append("data_not_confirmed_true_left_runtime_export")

    source_commit = manifest.get("leftlab_code_commit") or provenance.get("code_commit")
    source_tag = manifest.get("source_tag") or provenance.get("code_tag")
    export_timestamp = manifest.get("generation_time") or provenance.get("created_at")
    if not source_commit:
        blockers.append("source_commit_missing")
    if not source_tag:
        blockers.append("source_tag_missing")
    if not export_timestamp:
        blockers.append("export_timestamp_missing")

    maturity = horizon_maturity(rows, manifest, provenance) if rows else {
        "realized_outcome_horizon_matured": False,
        "horizon_info_present_in_handoff": False,
    }
    if not maturity.get("horizon_info_present_in_handoff"):
        blockers.append("realized_outcome_horizon_info_missing")
    if not maturity.get("realized_outcome_horizon_matured"):
        blockers.append("realized_outcome_horizon_not_matured")

    if manifest.get("full_pool_complete") is not True:
        blockers.append("full_pool_not_complete")
    if manifest.get("partial_pool_warning") is True:
        blockers.append("partial_pool_warning_active")

    stopline_triggered = bool(blockers)
    replay_completed = False
    decision_matrix_recomputed = False
    formal_v011_ready = False
    main_project_integration_allowed = False
    next_state = (
        "V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED"
        if stopline_triggered
        else "V1_4_S_TRUE_LEFT_REPLAY_READY_REVIEW_REQUIRED"
    )

    result = {
        "created_at": utc_now(),
        "handoff_dir": str(HANDOFF_DIR),
        "zip_path": str(ZIP_PATH),
        "git_status_clean": git_status_clean,
        "leftlab_handoff_received": leftlab_handoff_received,
        "transfer_receipt_exists": receipt_exists,
        "receipt_status": receipt.get("handoff_status") or receipt.get("status"),
        "manifest_verified": manifest_verified,
        "checksum_file_exists": checksum_file_exists,
        "zip_sha256_expected": zip_sha256_expected,
        "zip_sha256_actual": zip_sha256_actual,
        "zip_sha256_match": zip_sha256_match,
        "inner_checksum_verified": inner_checksum["verified"],
        "checksum_verified": checksum_verified,
        "zip_members": members,
        "candidate_count": candidate_count,
        "schema_valid": schema_valid,
        "candidate_validation": candidate_validation,
        "data_is_true_left_runtime_export": data_is_true_left_runtime,
        "data_from_reconstructed_branch": not data_is_true_left_runtime,
        "source_commit": source_commit,
        "source_tag": source_tag,
        "export_timestamp": export_timestamp,
        "manifest_status": manifest.get("status"),
        "replay_status_in_handoff": manifest.get("replay_status"),
        "full_pool_complete": manifest.get("full_pool_complete"),
        "partial_pool_warning": manifest.get("partial_pool_warning"),
        "gap_policy": manifest.get("gap_policy"),
        "readme_confirms_no_reconstructed_candidates": "no reconstructed candidates" in readme.lower(),
        "realized_outcome_horizon_matured": maturity.get("realized_outcome_horizon_matured"),
        "horizon_maturity": maturity,
        "replay_completed": replay_completed,
        "decision_matrix_recomputed": decision_matrix_recomputed,
        "formal_v011_ready": formal_v011_ready,
        "training_allowed": False,
        "torchrun_allowed": False,
        "gpu_allowed": False,
        "main_project_integration_allowed": main_project_integration_allowed,
        "remaining_blocker_count": len(blockers),
        "remaining_blockers": blockers,
        "next_state": next_state,
        "prohibited_actions_confirmed": {
            "trained_model": False,
            "torchrun": False,
            "gpu": False,
            "formal_v011_started": False,
            "main_project_integration": False,
            "trading_advice_generated": False,
            "leftlab_modified": False,
            "protocol_modified": False,
            "reconstructed_or_synthetic_history_used": False,
            "missing_fields_silently_dropped_filled_or_inferred": False,
            "forward_fill_used": False,
            "substitute_etf_index_symbol_used": False,
        },
    }
    write_outputs(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if stopline_triggered else 0


if __name__ == "__main__":
    raise SystemExit(main())
