"""Review reconstructed artifact intake provenance and prepare alignment inputs.

This script reads the ignored A2 intake index and copied intake artifacts,
checks provenance/checksum/readability, performs lightweight structural scans,
and writes review outputs under outputs/. It does not modify quarantine, train,
run torchrun, call GPU APIs, start replay, start formal_v011, or promote intake
artifacts to formal readiness.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_reconstructed_artifacts import CLEAN_ROOT, OUTPUT_DIR, QUARANTINE_ROOT, sha256
from intake_reconstructed_artifacts import INTAKE_DIR, INTAKE_INDEX


PROVENANCE_REVIEW_JSON = OUTPUT_DIR / "provenance_review.json"
PROVENANCE_REVIEW_CSV = OUTPUT_DIR / "provenance_review.csv"
ALIGNMENT_MAP_JSON = OUTPUT_DIR / "alignment_candidate_map.json"
ALIGNMENT_MAP_CSV = OUTPUT_DIR / "alignment_candidate_map.csv"

TEXT_EXTENSIONS = {".csv", ".html", ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
MAX_TEXT_BYTES = 2_000_000

CANDIDATE_HISTORY_TOKENS = {
    "candidate",
    "code",
    "symbol",
    "date",
    "decision",
    "label_status",
    "risk_bucket",
}
DECISION_MATRIX_TOKENS = {"decision", "predicted", "actual", "direction", "confidence", "score"}
METRICS_TOKENS = {"direction_accuracy", "majority_direction_accuracy", "accuracy", "metrics"}
STOPLINE_TOKENS = {"paused_by_stopline", "pause_reconstructed_branch"}
INDEX_TOKENS = {"candidate_history", "decision_matrix", "metrics", "closeout"}


def load_intake_index() -> dict[str, Any]:
    if not INTAKE_INDEX.exists():
        raise FileNotFoundError(f"intake index not found: {INTAKE_INDEX}")
    return json.loads(INTAKE_INDEX.read_text(encoding="utf-8"))


def read_text_if_supported(path: Path, size: int) -> tuple[str, str | None]:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return "", "unsupported_text_extension"
    if size > MAX_TEXT_BYTES:
        return "", "file_too_large_for_text_scan"
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return "", str(exc)


def json_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(json_keys(child))
    elif isinstance(value, list):
        for child in value[:50]:
            keys.update(json_keys(child))
    return keys


def csv_header_and_rows(path: Path) -> tuple[list[str], int]:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        return [item.strip().lower() for item in header], rows
    except OSError:
        return [], 0


def collect_tokens(path: Path, text: str) -> tuple[set[str], int, str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        header, rows = csv_header_and_rows(path)
        return set(header), rows, "csv"
    if suffix == ".json":
        try:
            data = json.loads(text)
            return json_keys(data), 1, "json"
        except json.JSONDecodeError:
            return set(), 0, "json_invalid"
    if suffix == ".jsonl":
        keys: set[str] = set()
        rows = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            rows += 1
            try:
                keys.update(json_keys(json.loads(line)))
            except json.JSONDecodeError:
                continue
            if rows >= 50:
                break
        return keys, rows, "jsonl"
    words = {
        token.strip("`'\"[]{}():,").lower()
        for token in text.replace("-", "_").replace("/", "_").split()
        if token.strip()
    }
    return words, len([line for line in text.splitlines() if line.strip()]), suffix.lstrip(".") or "text"


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def review_record(record: dict[str, Any], known_paths: set[str], known_hashes: set[str]) -> dict[str, Any]:
    source_path = Path(record["source_path"])
    destination_path = Path(record["destination_path"])
    source_hash = record.get("source_sha256")
    copied_hash_from_index = record.get("copied_sha256")
    copied_hash_current = sha256(destination_path) if destination_path.exists() else None
    destination_size = destination_path.stat().st_size if destination_path.exists() else None
    source_size = record.get("size_bytes")
    text, read_error = read_text_if_supported(destination_path, destination_size or 0) if destination_path.exists() else ("", "missing_destination")
    detected_tokens, row_count, file_format = collect_tokens(destination_path, text) if text else (set(), 0, destination_path.suffix.lower().lstrip(".") or "unknown")
    lower_text = text.lower()
    lower_path = record["source_relative_path"].lower()
    haystack = f"{lower_path}\n{lower_text}"

    provenance_checks = {
        "source_path_from_quarantine": path_is_under(source_path, QUARANTINE_ROOT),
        "destination_path_in_runtime_intake": path_is_under(destination_path, INTAKE_DIR),
        "source_workspace_is_quarantine": record.get("source_workspace") == "quarantine",
        "copy_mode_is_read_only_intake": record.get("copy_mode") == "read_only_intake",
        "source_sha256_present": bool(source_hash),
        "copied_sha256_present": bool(copied_hash_from_index),
        "index_hashes_match": bool(source_hash and copied_hash_from_index and source_hash == copied_hash_from_index),
        "copied_sha256_matches_current_file": bool(copied_hash_from_index and copied_hash_current == copied_hash_from_index),
        "size_bytes_match_current_file": destination_size == source_size,
        "modified_time_present": bool(record.get("modified_time")),
        "artifact_role_guess_present": bool(record.get("artifact_role_guess")),
        "confidence_present": record.get("confidence") in {"high", "medium", "low"},
        "reason_present": bool(record.get("reason")),
        "intake_status_success": record.get("intake_status") == "copied_checksum_pass",
    }
    provenance_status = "pass" if all(provenance_checks.values()) else "fail"
    structural_readability = "readable" if destination_path.exists() and read_error is None and destination_size != 0 else "not_readable"

    candidate_history_fields_found = sorted(CANDIDATE_HISTORY_TOKENS & detected_tokens)
    decision_fields_found = sorted(DECISION_MATRIX_TOKENS & detected_tokens)
    metrics_fields_found = sorted(METRICS_TOKENS & detected_tokens)
    index_fields_found = sorted(INDEX_TOKENS & detected_tokens)
    has_reconstructed_snapshot_marker = (
        "reconstructed_not_true_left_snapshot" in haystack
        or "reconstructed_candidate_history_not_real_left_snapshot" in haystack
    )
    clearly_distinct_from_true_left = "reconstructed" in haystack and "true_left_snapshot" not in haystack
    has_stopline_marker = any(token in haystack for token in STOPLINE_TOKENS)
    has_reconstructed_closeout = "reconstructed_v1" in haystack or "reconstructed closeout" in haystack
    known_reference_hits = sum(1 for item in known_paths | known_hashes if item and item.lower() in haystack)

    return {
        "source_path": record["source_path"],
        "destination_path": record["destination_path"],
        "source_relative_path": record["source_relative_path"],
        "source_workspace": record.get("source_workspace"),
        "copy_mode": record.get("copy_mode"),
        "source_sha256": source_hash,
        "copied_sha256": copied_hash_from_index,
        "copied_sha256_current": copied_hash_current,
        "size_bytes": source_size,
        "destination_size_bytes": destination_size,
        "modified_time": record.get("modified_time"),
        "artifact_role_guess": record.get("artifact_role_guess"),
        "confidence": record.get("confidence"),
        "reason": record.get("reason"),
        "intake_status": record.get("intake_status"),
        "provenance_status": provenance_status,
        "failed_provenance_checks": sorted(key for key, value in provenance_checks.items() if not value),
        "file_format": file_format,
        "row_count": row_count,
        "structural_readability": structural_readability,
        "read_error": read_error,
        "contains_candidate_history": bool(record.get("contains_candidate_history")),
        "contains_decision_matrix": bool(record.get("contains_decision_matrix")),
        "contains_closeout": bool(record.get("contains_closeout")),
        "contains_artifact_index": bool(record.get("contains_artifact_index")),
        "contains_metrics": bool(record.get("contains_metrics")),
        "candidate_history_fields_found": candidate_history_fields_found,
        "candidate_history_field_count": len(candidate_history_fields_found),
        "has_reconstructed_snapshot_marker": has_reconstructed_snapshot_marker,
        "clearly_distinct_from_true_left": clearly_distinct_from_true_left,
        "decision_matrix_fields_found": decision_fields_found,
        "decision_matrix_field_count": len(decision_fields_found),
        "has_stopline_marker": has_stopline_marker,
        "has_reconstructed_closeout": has_reconstructed_closeout,
        "metrics_fields_found": metrics_fields_found,
        "artifact_index_fields_found": index_fields_found,
        "artifact_index_reference_hit_count": known_reference_hits,
        "obvious_empty_or_corrupt": structural_readability != "readable" or file_format == "json_invalid",
    }


def score_for_role(review: dict[str, Any], role: str) -> tuple[int, str]:
    path = review["source_relative_path"].lower()
    score = 0
    reasons: list[str] = []
    if review["provenance_status"] == "pass":
        score += 20
        reasons.append("provenance pass")
    if review["structural_readability"] == "readable":
        score += 20
        reasons.append("readable")
    if review["confidence"] == "high":
        score += 10
    elif review["confidence"] == "medium":
        score += 5

    if role == "candidate_history":
        if review["contains_candidate_history"]:
            score += 15
        if "candidate_history" in path or "left_candidates_history" in path:
            score += 25
            reasons.append("candidate history path")
        if review["file_format"] == "csv":
            score += 10
        if review["candidate_history_field_count"] >= 2:
            score += 10
        if review["has_reconstructed_snapshot_marker"]:
            score += 10
    elif role == "decision_matrix":
        if review["contains_decision_matrix"]:
            score += 15
        if "decision_matrix" in path:
            score += 25
            reasons.append("decision matrix path")
        if review["decision_matrix_field_count"] >= 1:
            score += 10
    elif role == "closeout":
        if review["contains_closeout"]:
            score += 15
        if "closeout" in path:
            score += 25
            reasons.append("closeout path")
        if review["has_reconstructed_closeout"] or review["has_stopline_marker"]:
            score += 10
    elif role == "artifact_index":
        if review["contains_artifact_index"]:
            score += 15
        if "artifact_index" in path:
            score += 25
            reasons.append("artifact index path")
        if review["artifact_index_reference_hit_count"] > 0:
            score += 10

    return score, "; ".join(reasons) or "weak role evidence"


def choose_best(reviews: list[dict[str, Any]], role: str) -> tuple[dict[str, Any] | None, int, str]:
    scored = [(score_for_role(item, role), item) for item in reviews]
    scored = [item for item in scored if item[0][0] > 0]
    if not scored:
        return None, 0, "no candidate"
    scored.sort(key=lambda item: (item[0][0], item[1]["source_relative_path"]), reverse=True)
    score_reason, review = scored[0]
    return review, score_reason[0], score_reason[1]


def build_alignment_map(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, tuple[dict[str, Any] | None, int, str]] = {
        role: choose_best(reviews, role)
        for role in ("candidate_history", "decision_matrix", "closeout", "artifact_index")
    }
    selected_reviews = [item[0] for item in selected.values() if item[0] is not None]
    all_core_pass = bool(selected_reviews) and all(
        item["provenance_status"] == "pass" and item["structural_readability"] == "readable"
        for item in selected_reviews
    )
    has_history = selected["candidate_history"][0] is not None
    has_supporting_context = selected["closeout"][0] is not None or selected["artifact_index"][0] is not None
    recommended = all_core_pass and has_history and has_supporting_context
    status = "alignment_precheck_candidate" if recommended else "alignment_prep_review_required"
    reason = (
        "selected intake artifacts are readable and checksum-verified; human provenance review is still required before running precheck"
        if recommended
        else "candidate set requires additional review before alignment precheck"
    )

    def field(role: str, key: str) -> Any:
        review = selected[role][0]
        return review[key] if review else None

    return [
        {
            "candidate_set_id": "reconstructed_v1_quarantine_primary",
            "candidate_history_artifact": field("candidate_history", "source_relative_path"),
            "decision_matrix_artifact": field("decision_matrix", "source_relative_path"),
            "closeout_artifact": field("closeout", "source_relative_path"),
            "artifact_index_artifact": field("artifact_index", "source_relative_path"),
            "source_sha256": field("candidate_history", "source_sha256"),
            "copied_sha256": field("candidate_history", "copied_sha256"),
            "provenance_status": "pass" if all_core_pass else "review_required",
            "role_confidence": field("candidate_history", "confidence"),
            "structural_readability": "readable" if all_core_pass else "review_required",
            "alignment_candidate_status": status,
            "reason": reason,
            "recommended_for_alignment_precheck": recommended,
            "candidate_history_score": selected["candidate_history"][1],
            "decision_matrix_score": selected["decision_matrix"][1],
            "closeout_score": selected["closeout"][1],
            "artifact_index_score": selected["artifact_index"][1],
            "candidate_history_reason": selected["candidate_history"][2],
            "decision_matrix_reason": selected["decision_matrix"][2],
            "closeout_reason": selected["closeout"][2],
            "artifact_index_reason": selected["artifact_index"][2],
        }
    ]


def build_summary(reviews: list[dict[str, Any]], alignment_map: list[dict[str, Any]]) -> dict[str, Any]:
    hash_counts = Counter(item["source_sha256"] for item in reviews if item["source_sha256"])
    duplicate_hashes = {hash_value: count for hash_value, count in hash_counts.items() if count > 1}
    checksum_pass_count = sum(
        1
        for item in reviews
        if item["source_sha256"] and item["source_sha256"] == item["copied_sha256"] == item["copied_sha256_current"]
    )
    checksum_fail_count = len(reviews) - checksum_pass_count
    recommended_count = sum(1 for item in alignment_map if item["recommended_for_alignment_precheck"])
    alignment_status = (
        "PROVENANCE_REVIEW_COMPLETED_ALIGNMENT_PRECHECK_READY"
        if recommended_count and checksum_fail_count == 0
        else "PROVENANCE_REVIEW_COMPLETED_ALIGNMENT_PREP_REQUIRED"
    )
    return {
        "intake_index_readable": True,
        "provenance_reviewed_count": len(reviews),
        "checksum_pass_count": checksum_pass_count,
        "checksum_fail_count": checksum_fail_count,
        "candidate_history_readable_count": sum(
            1 for item in reviews if item["contains_candidate_history"] and item["structural_readability"] == "readable"
        ),
        "decision_matrix_readable_count": sum(
            1 for item in reviews if item["contains_decision_matrix"] and item["structural_readability"] == "readable"
        ),
        "closeout_readable_count": sum(
            1 for item in reviews if item["contains_closeout"] and item["structural_readability"] == "readable"
        ),
        "artifact_index_readable_count": sum(
            1 for item in reviews if item["contains_artifact_index"] and item["structural_readability"] == "readable"
        ),
        "duplicate_hash_count": len(duplicate_hashes),
        "duplicate_hash_record_count": sum(duplicate_hashes.values()),
        "selected_alignment_candidate_set_count": len(alignment_map),
        "recommended_alignment_precheck_count": recommended_count,
        "reconstructed_artifacts_status": "QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED",
        "alignment_preparation_status": alignment_status,
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "remaining_stopline_reasons": [
            "reconstructed_alignment_not_run" if recommended_count else "reconstructed_artifacts_pending_review",
            "realized_outcome_fields_missing",
        ],
        "no_training": True,
        "torchrun": False,
        "gpu": False,
        "quarantine_modified": False,
        "runtime_intake_committed": False,
        "outputs_committed": False,
    }


def write_csv(path: Path, records: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field) for field in fieldnames})


def main() -> None:
    intake = load_intake_index()
    records = intake.get("records", [])
    known_paths = {item.get("source_relative_path", "") for item in records}
    known_hashes = {item.get("source_sha256", "") for item in records}
    reviews = [review_record(record, known_paths, known_hashes) for record in records]
    alignment_map = build_alignment_map(reviews)
    summary = build_summary(reviews, alignment_map)
    report = {
        "review_name": "leftlab_v1_4_i_reconstructed_provenance_alignment_prep",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "clean_root": str(CLEAN_ROOT),
        "runtime_intake_dir": str(INTAKE_DIR),
        "intake_index": str(INTAKE_INDEX),
        "quarantine_root_from_index_only": str(QUARANTINE_ROOT),
        "quarantine_modified": False,
        "alignment_not_run": True,
        "formal_v011_not_started": True,
        "summary": summary,
        "reviews": reviews,
        "alignment_candidate_map": alignment_map,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_REVIEW_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ALIGNMENT_MAP_JSON.write_text(json.dumps(alignment_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        PROVENANCE_REVIEW_CSV,
        reviews,
        [
            "source_relative_path",
            "source_sha256",
            "copied_sha256",
            "copied_sha256_current",
            "size_bytes",
            "destination_size_bytes",
            "provenance_status",
            "file_format",
            "row_count",
            "structural_readability",
            "contains_candidate_history",
            "contains_decision_matrix",
            "contains_closeout",
            "contains_artifact_index",
            "contains_metrics",
            "candidate_history_field_count",
            "decision_matrix_field_count",
            "has_reconstructed_snapshot_marker",
            "has_stopline_marker",
            "has_reconstructed_closeout",
            "artifact_index_reference_hit_count",
            "confidence",
            "artifact_role_guess",
            "obvious_empty_or_corrupt",
        ],
    )
    write_csv(
        ALIGNMENT_MAP_CSV,
        alignment_map,
        [
            "candidate_set_id",
            "candidate_history_artifact",
            "decision_matrix_artifact",
            "closeout_artifact",
            "artifact_index_artifact",
            "source_sha256",
            "copied_sha256",
            "provenance_status",
            "role_confidence",
            "structural_readability",
            "alignment_candidate_status",
            "reason",
            "recommended_for_alignment_precheck",
        ],
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
