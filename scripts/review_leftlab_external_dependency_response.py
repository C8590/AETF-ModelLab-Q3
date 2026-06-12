"""Review the LeftLab V1.4-S external dependency response package.

This script is read-only with respect to the runtime exchange directory. It
writes review artifacts only under ignored outputs. It does not train, import
torch, call GPU APIs, run torchrun, start formal_v011, modify LeftLab, modify
Protocol, or generate trading advice.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESPONSE_DIR = Path(
    r"E:\aetf_runtime_exchange\left_to_model\historical_true_left_external_dependency_response_v1_4_s"
)
OUTPUT_DIR = Path("outputs/leftlab_external_dependency_response_review")

EXPECTED_FILES = [
    "LEFTLAB_DEPENDENCY_RESPONSE.md",
    "560000_COVERAGE_REVIEW.md",
    "560000_COVERAGE_STATUS.json",
    "513360_PRICE_MISSING_REVIEW.md",
    "513360_PRICE_SOURCE_STATUS.json",
    "SUPPLEMENTAL_HANDOFF_MANIFEST.json",
    "SUPPLEMENTAL_CHECKSUMS.sha256",
    "TRANSFER_RECEIPT.json",
    "README.md",
    "NO_LEGAL_SUPPLEMENTAL_DATA_AVAILABLE.md",
]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except Exception as exc:  # pragma: no cover - surfaced in review output
        return None, f"{type(exc).__name__}: {exc}"


def parse_checksum_file(path: Path) -> tuple[list[dict[str, Any]], bool]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries, False
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            entries.append(
                {
                    "file": "",
                    "expected_sha256": "",
                    "actual_sha256": "",
                    "exists": False,
                    "matched": False,
                    "parse_error": raw_line,
                }
            )
            continue
        expected_hash, filename = parts
        filename = filename.strip().lstrip("*")
        file_path = RESPONSE_DIR / filename
        exists = file_path.exists()
        actual_hash = sha256_path(file_path) if exists else ""
        entries.append(
            {
                "file": filename,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "exists": exists,
                "matched": exists and actual_hash.lower() == expected_hash.lower(),
            }
        )
    return entries, bool(entries) and all(entry["matched"] for entry in entries)


def bool_false(data: dict[str, Any], key: str) -> bool:
    return data.get(key) is False


def write_outputs(result: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "leftlab_external_dependency_response_review.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary_lines = [
        "# LeftLab External Dependency Response Review",
        "",
        f"- receive_review_status: {result['receive_review_status']}",
        f"- response_dir_exists: {str(result['response_dir_exists']).lower()}",
        f"- response_checksum_verified: {str(result['response_checksum_verified']).lower()}",
        f"- dispatch_received: {str(result['dispatch_received']).lower()}",
        f"- dispatch_checksum_verified: {str(result['dispatch_checksum_verified']).lower()}",
        f"- 560000_status: {result['560000_status']}",
        f"- 560000_latest_date: {result['560000_latest_date']}",
        f"- 560000_forward_fill_used: {str(result['560000_forward_fill_used']).lower()}",
        f"- 560000_synthetic_data_used: {str(result['560000_synthetic_data_used']).lower()}",
        f"- 513360_2025_02_06_close_status: {result['513360_2025_02_06_close_status']}",
        f"- 513360_close_price: {result['513360_close_price']}",
        f"- 513360_forward_fill_used: {str(result['513360_forward_fill_used']).lower()}",
        f"- 513360_synthetic_price_used: {str(result['513360_synthetic_price_used']).lower()}",
        f"- supplemental_handoff_created: {str(result['supplemental_handoff_created']).lower()}",
        f"- full_pool_complete: {str(result['full_pool_complete']).lower()}",
        f"- partial_pool_warning: {str(result['partial_pool_warning']).lower()}",
        f"- formal_v011_ready: {str(result['formal_v011_ready']).lower()}",
        f"- training_allowed: {str(result['training_allowed']).lower()}",
        f"- torchrun_allowed: {str(result['torchrun_allowed']).lower()}",
        f"- gpu_allowed: {str(result['gpu_allowed']).lower()}",
        f"- main_project_integration_allowed: {str(result['main_project_integration_allowed']).lower()}",
        f"- no_supplemental_price_found: {str(result['no_supplemental_price_found']).lower()}",
        f"- no_synthetic_forwardfill_or_substitute_used: {str(result['no_synthetic_forwardfill_or_substitute_used']).lower()}",
        f"- wait_state_should_continue: {str(result['wait_state_should_continue']).lower()}",
        f"- readiness_gate_status: {result['readiness_gate_status']}",
        "",
        "No training, torchrun, GPU, formal_v011, trading advice, LeftLab modification,",
        "Protocol modification, price fabrication, forward-fill, or substitute symbol use",
        "was performed by this review.",
    ]
    (OUTPUT_DIR / "leftlab_external_dependency_response_review.md").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    response_dir_exists = RESPONSE_DIR.exists()
    present_files = sorted(path.name for path in RESPONSE_DIR.iterdir()) if response_dir_exists else []
    expected_file_presence = {name: (RESPONSE_DIR / name).exists() for name in EXPECTED_FILES}

    transfer_receipt, transfer_receipt_error = read_json(RESPONSE_DIR / "TRANSFER_RECEIPT.json")
    manifest, manifest_error = read_json(RESPONSE_DIR / "SUPPLEMENTAL_HANDOFF_MANIFEST.json")
    coverage_560000, coverage_560000_error = read_json(RESPONSE_DIR / "560000_COVERAGE_STATUS.json")
    price_513360, price_513360_error = read_json(RESPONSE_DIR / "513360_PRICE_SOURCE_STATUS.json")

    transfer_receipt = transfer_receipt if isinstance(transfer_receipt, dict) else {}
    manifest = manifest if isinstance(manifest, dict) else {}
    coverage_560000 = coverage_560000 if isinstance(coverage_560000, dict) else {}
    price_513360 = price_513360 if isinstance(price_513360, dict) else {}

    checksum_details, response_checksum_verified = parse_checksum_file(
        RESPONSE_DIR / "SUPPLEMENTAL_CHECKSUMS.sha256"
    )

    supplement_policy = manifest.get("supplement_policy", {})
    if not isinstance(supplement_policy, dict):
        supplement_policy = {}

    supplemental_files = manifest.get("supplemental_files", [])
    no_supplemental_files = isinstance(supplemental_files, list) and len(supplemental_files) == 0

    status_560000 = coverage_560000.get("status")
    latest_date_560000 = manifest.get("560000_latest_date")
    if latest_date_560000 is None:
        coverage = coverage_560000.get("coverage", {})
        latest_date_560000 = coverage.get("date_max") if isinstance(coverage, dict) else None

    status_513360 = price_513360.get("status")
    close_513360 = price_513360.get("close_price")

    no_supplemental_price_found = (
        no_supplemental_files
        and manifest.get("no_legal_supplemental_data_available") is True
        and status_560000 == "UNAVAILABLE_CONFIRMED"
        and status_513360 == "UNAVAILABLE_CONFIRMED"
        and close_513360 is None
    )

    no_synthetic_forwardfill_or_substitute_used = (
        manifest.get("560000_forward_fill_used") is False
        and manifest.get("560000_synthetic_data_used") is False
        and manifest.get("513360_forward_fill_used") is False
        and manifest.get("513360_synthetic_price_used") is False
        and supplement_policy.get("not_synthetic") is True
        and supplement_policy.get("no_forward_fill") is True
        and supplement_policy.get("no_back_fill") is True
        and supplement_policy.get("no_substitute_symbol") is True
    )

    required_json_parsed = all(
        error is None
        for error in [
            transfer_receipt_error,
            manifest_error,
            coverage_560000_error,
            price_513360_error,
        ]
    )
    required_files_present = all(expected_file_presence.values())

    field_checks = {
        "transfer_receipt_parseable": transfer_receipt_error is None,
        "manifest_parseable": manifest_error is None,
        "560000_status_unavailable_confirmed": status_560000 == "UNAVAILABLE_CONFIRMED",
        "560000_latest_date_2026_04_30": latest_date_560000 == "2026-04-30",
        "560000_forward_fill_false": manifest.get("560000_forward_fill_used") is False,
        "560000_synthetic_data_false": manifest.get("560000_synthetic_data_used") is False,
        "513360_status_unavailable_confirmed": status_513360 == "UNAVAILABLE_CONFIRMED",
        "513360_close_price_null": close_513360 is None,
        "513360_forward_fill_false": manifest.get("513360_forward_fill_used") is False,
        "513360_synthetic_price_false": manifest.get("513360_synthetic_price_used") is False,
        "supplemental_handoff_created_false": manifest.get("supplemental_handoff_created") is False,
        "full_pool_complete_false": manifest.get("full_pool_complete") is False,
        "partial_pool_warning_true": manifest.get("partial_pool_warning") is True,
        "formal_v011_ready_false": manifest.get("formal_v011_ready") is False,
        "training_allowed_false": manifest.get("training_allowed") is False,
        "torchrun_allowed_false": manifest.get("torchrun_allowed") is False,
        "gpu_allowed_false": manifest.get("gpu_allowed") is False,
        "main_project_integration_allowed_false": manifest.get("main_project_integration_allowed") is False,
        "no_supplemental_price_found": no_supplemental_price_found,
        "no_synthetic_forwardfill_or_substitute_used": no_synthetic_forwardfill_or_substitute_used,
    }

    accepted = (
        response_dir_exists
        and required_files_present
        and required_json_parsed
        and response_checksum_verified
        and all(field_checks.values())
    )

    result: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(RESPONSE_DIR),
        "response_dir_exists": response_dir_exists,
        "present_files": present_files,
        "expected_file_presence": expected_file_presence,
        "json_parse_errors": {
            "TRANSFER_RECEIPT.json": transfer_receipt_error,
            "SUPPLEMENTAL_HANDOFF_MANIFEST.json": manifest_error,
            "560000_COVERAGE_STATUS.json": coverage_560000_error,
            "513360_PRICE_SOURCE_STATUS.json": price_513360_error,
        },
        "response_checksum_verified": response_checksum_verified,
        "checksum_details": checksum_details,
        "dispatch_received": transfer_receipt.get("dispatch_received"),
        "dispatch_checksum_verified": transfer_receipt.get("dispatch_checksum_verified"),
        "560000_status": status_560000,
        "560000_latest_date": latest_date_560000,
        "560000_forward_fill_used": manifest.get("560000_forward_fill_used"),
        "560000_synthetic_data_used": manifest.get("560000_synthetic_data_used"),
        "513360_2025_02_06_close_status": status_513360,
        "513360_close_price": close_513360,
        "513360_forward_fill_used": manifest.get("513360_forward_fill_used"),
        "513360_synthetic_price_used": manifest.get("513360_synthetic_price_used"),
        "supplemental_handoff_created": manifest.get("supplemental_handoff_created"),
        "full_pool_complete": manifest.get("full_pool_complete"),
        "partial_pool_warning": manifest.get("partial_pool_warning"),
        "formal_v011_ready": manifest.get("formal_v011_ready"),
        "training_allowed": manifest.get("training_allowed"),
        "torchrun_allowed": manifest.get("torchrun_allowed"),
        "gpu_allowed": manifest.get("gpu_allowed"),
        "main_project_integration_allowed": manifest.get("main_project_integration_allowed"),
        "no_supplemental_price_found": no_supplemental_price_found,
        "no_synthetic_forwardfill_or_substitute_used": no_synthetic_forwardfill_or_substitute_used,
        "field_checks": field_checks,
        "wait_state_should_continue": True,
        "protocol_registration_recommended": True,
        "readiness_gate_status": (
            "LEFTLAB_EXTERNAL_DEPENDENCY_RESPONSE_ACCEPTED_WAIT_STATE_CONTINUES"
            if accepted
            else "LEFTLAB_EXTERNAL_DEPENDENCY_RESPONSE_RECEIVED_REVIEW_REQUIRED"
        ),
        "receive_review_status": (
            "LEFTLAB_EXTERNAL_DEPENDENCY_RESPONSE_ACCEPTED_WAIT_STATE_CONTINUES"
            if accepted
            else "LEFTLAB_EXTERNAL_DEPENDENCY_RESPONSE_RECEIVED_REVIEW_REQUIRED"
        ),
        "prohibited_actions_confirmed": {
            "trained_model": False,
            "torchrun": False,
            "gpu": False,
            "formal_v011_started": False,
            "trading_advice_generated": False,
            "leftlab_modified": False,
            "protocol_modified": False,
            "price_fabricated": False,
            "forward_fill_used_by_modellab": False,
            "substitute_etf_index_symbol_used": False,
            "runtime_exchange_submitted": False,
        },
    }
    write_outputs(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
