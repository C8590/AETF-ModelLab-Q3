"""Controlled intake of reconstructed artifact candidates from quarantine.

The script reads the quarantine workspace, copies audited quarantine candidates
into an ignored runtime intake directory, and writes checksum/provenance indexes
under outputs/. It does not train, run torchrun, call GPU APIs, modify
quarantine, promote artifacts, or mark formal_v011 ready.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_reconstructed_artifacts import (
    CLEAN_ROOT,
    OUTPUT_DIR,
    QUARANTINE_ROOT,
    audit_workspace,
    sha256,
    summarize,
)


INTAKE_DIR = CLEAN_ROOT / "runtime_intake/reconstructed_v1_quarantine"
INTAKE_INDEX = OUTPUT_DIR / "intake_index.json"
INTAKE_CSV = OUTPUT_DIR / "intake_index.csv"


def guess_artifact_role(candidate: dict[str, Any]) -> tuple[str, str, str]:
    rel = candidate["relative_path"].lower()
    summary = candidate.get("content_summary", "").lower()
    haystack = f"{rel}\n{summary}"

    if candidate.get("contains_candidate_history"):
        if "reconstructed" in haystack:
            return (
                "reconstructed_candidate_history_candidate",
                "high",
                "candidate_history marker appears with reconstructed context",
            )
        return (
            "reconstructed_candidate_history_candidate",
            "medium",
            "candidate_history marker appears without a direct reconstructed token",
        )
    if candidate.get("contains_artifact_index"):
        return (
            "reconstructed_artifact_index_candidate",
            "high" if "reconstructed" in haystack else "medium",
            "artifact_index marker identifies a reconstructed artifact index candidate",
        )
    if candidate.get("contains_closeout"):
        return (
            "reconstructed_closeout_candidate",
            "high" if "reconstructed" in haystack else "medium",
            "closeout marker identifies a reconstructed closeout candidate",
        )
    if candidate.get("contains_decision_matrix"):
        return (
            "reconstructed_decision_matrix_candidate",
            "high" if "reconstructed" in haystack or "paused_by_stopline" in haystack else "medium",
            "decision_matrix marker identifies a reconstructed decision matrix candidate",
        )
    if candidate.get("contains_metrics"):
        return (
            "reconstructed_metrics_candidate",
            "medium",
            "metrics or accuracy marker appears in reconstructed candidate context",
        )
    return (
        "unknown_reconstructed_candidate",
        "low",
        "reconstructed candidate signal exists, but role markers are not specific",
    )


def copy_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    source = Path(candidate["path"])
    destination = INTAKE_DIR / candidate["relative_path"]
    source_hash = candidate["sha256"]
    role, confidence, reason = guess_artifact_role(candidate)

    record = {
        "source_path": str(source),
        "destination_path": str(destination),
        "source_relative_path": candidate["relative_path"],
        "destination_relative_path": destination.relative_to(CLEAN_ROOT).as_posix(),
        "source_workspace": "quarantine",
        "copy_mode": "read_only_intake",
        "source_sha256": source_hash,
        "copied_sha256": None,
        "size_bytes": candidate["size_bytes"],
        "modified_time": candidate["modified_time_utc"],
        "artifact_role_guess": role,
        "confidence": confidence,
        "reason": reason,
        "intake_status": "failed",
        "contains_candidate_history": candidate["contains_candidate_history"],
        "contains_decision_matrix": candidate["contains_decision_matrix"],
        "contains_closeout": candidate["contains_closeout"],
        "contains_artifact_index": candidate["contains_artifact_index"],
        "contains_metrics": candidate["contains_metrics"],
        "usable_for_formal_v011_replay": False,
    }

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_hash = sha256(destination)
        record["copied_sha256"] = copied_hash
        record["intake_status"] = "copied_checksum_pass" if copied_hash == source_hash else "copied_checksum_failed"
    except OSError as exc:
        record["failure_reason"] = str(exc)

    return record


def build_summary(records: list[dict[str, Any]], audited_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    checksum_pass = [item for item in records if item["intake_status"] == "copied_checksum_pass"]
    checksum_fail = [item for item in records if item["intake_status"] != "copied_checksum_pass"]
    status = (
        "QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED"
        if records and not checksum_fail
        else "QUARANTINE_INTAKE_FAILED_REVIEW_REQUIRED"
    )
    return {
        "intake_candidate_count": len(audited_candidates),
        "copied_artifact_count": len(checksum_pass),
        "checksum_pass_count": len(checksum_pass),
        "checksum_fail_count": len(checksum_fail),
        "candidate_history_candidates_count": sum(
            1 for item in records if item["contains_candidate_history"]
        ),
        "decision_matrix_candidates_count": sum(
            1 for item in records if item["contains_decision_matrix"]
        ),
        "closeout_candidates_count": sum(1 for item in records if item["contains_closeout"]),
        "artifact_index_candidates_count": sum(
            1 for item in records if item["contains_artifact_index"]
        ),
        "high_confidence_count": sum(1 for item in records if item["confidence"] == "high"),
        "reconstructed_artifacts_status": status,
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "remaining_stopline_reasons": [
            "reconstructed_artifacts_pending_review",
            "realized_outcome_fields_missing",
        ],
        "no_training": True,
        "torchrun": False,
        "gpu": False,
        "quarantine_modified": False,
        "runtime_intake_committed": False,
        "runtime_payload_modified": False,
    }


def write_outputs(report: dict[str, Any], records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTAKE_INDEX.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with INTAKE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_workspace",
                "source_relative_path",
                "destination_relative_path",
                "copy_mode",
                "source_sha256",
                "copied_sha256",
                "size_bytes",
                "modified_time",
                "artifact_role_guess",
                "confidence",
                "reason",
                "intake_status",
                "usable_for_formal_v011_replay",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({field: record[field] for field in writer.fieldnames})


def main() -> None:
    if not QUARANTINE_ROOT.exists():
        raise FileNotFoundError(f"quarantine workspace not found: {QUARANTINE_ROOT}")

    quarantine_candidates = audit_workspace(QUARANTINE_ROOT, "quarantine")
    records = [copy_candidate(candidate) for candidate in quarantine_candidates]
    audit_summary = summarize(quarantine_candidates)
    summary = build_summary(records, quarantine_candidates)
    report = {
        "intake_name": "leftlab_v1_4_h_reconstructed_artifact_intake",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "clean_root": str(CLEAN_ROOT),
        "quarantine_root": str(QUARANTINE_ROOT),
        "intake_dir": str(INTAKE_DIR),
        "quarantine_read_only": True,
        "copy_mode": "read_only_intake",
        "audit_summary": audit_summary,
        "summary": summary,
        "records": records,
    }
    write_outputs(report, records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
