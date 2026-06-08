#!/usr/bin/env python3
"""Replay a LeftLab true-left candidate-history handoff without training.

This script is intentionally narrow:
- reads only a handoff payload directory;
- does not import torch or use GPU resources;
- does not train, fit, or optimize a model;
- writes replay audit artifacts under a caller-provided output directory.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REF_FILES = {
    "feature_snapshot_refs": "feature_snapshot_refs.json",
    "label_snapshot_refs": "label_snapshot_refs.json",
    "similar_case_refs": "similar_case_refs.json",
    "probability_bucket_snapshot": "probability_bucket_snapshot.json",
    "frontend_explanation_snapshot": "frontend_explanation_snapshot.json",
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"candidate_history line {line_no} is not a JSON object")
        records.append(record)
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"required handoff file not found: {path}")


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def ref_summary(refs: dict[str, dict[str, Any]], candidate_ids: set[str]) -> dict[str, Any]:
    present_ids = set(refs)
    matched_ids = {cid for cid, payload in refs.items() if payload.get("matched") is True}
    missing_ids = sorted(candidate_ids - present_ids)
    unmatched_ids = sorted(cid for cid in candidate_ids & present_ids if refs[cid].get("matched") is not True)
    return {
        "total_candidates": len(candidate_ids),
        "ref_records": len(refs),
        "matched_count": len(candidate_ids & matched_ids),
        "missing_count": len(missing_ids),
        "unmatched_count": len(unmatched_ids),
        "coverage": f"{len(candidate_ids & matched_ids)}/{len(candidate_ids)}",
        "all_matched": len(candidate_ids & matched_ids) == len(candidate_ids),
        "missing_ids": missing_ids,
        "unmatched_ids": unmatched_ids,
    }


def nested_summary(refs: dict[str, dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    payload = refs.get(candidate_id, {})
    summary = payload.get("matched_record_summary")
    return summary if isinstance(summary, dict) else {}


def replay_candidates(
    candidates: list[dict[str, Any]],
    refs: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    label_refs = refs["label_snapshot_refs"]
    similar_refs = refs["similar_case_refs"]
    probability_refs = refs["probability_bucket_snapshot"]
    feature_refs = refs["feature_snapshot_refs"]
    frontend_refs = refs["frontend_explanation_snapshot"]
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id", ""))
        label_summary = nested_summary(label_refs, candidate_id)
        probability_summary = nested_summary(probability_refs, candidate_id)
        feature_summary = nested_summary(feature_refs, candidate_id)
        similar_summary = nested_summary(similar_refs, candidate_id)
        frontend_summary = nested_summary(frontend_refs, candidate_id)
        rows.append(
            {
                "candidate_id": candidate_id,
                "etf_code": label_summary.get("etf_code") or feature_summary.get("etf_code") or probability_summary.get("etf_code"),
                "timestamp": candidate.get("timestamp") or candidate.get("round") or label_summary.get("signal_date"),
                "rank": candidate.get("candidate_rank"),
                "decision": candidate.get("decision", "unknown"),
                "decision_reason": candidate.get("decision_reason", ""),
                "label": label_summary.get("label"),
                "label_status": label_summary.get("label_status", "unknown"),
                "probability_bucket": candidate.get("probability_bucket", "unknown"),
                "risk_level": probability_summary.get("risk_level"),
                "bucket_key": probability_summary.get("bucket_key"),
                "sample_confidence": probability_summary.get("sample_confidence") or frontend_summary.get("sample_confidence"),
                "feature_ref_matched": feature_refs.get(candidate_id, {}).get("matched") is True,
                "label_ref_matched": label_refs.get(candidate_id, {}).get("matched") is True,
                "similar_ref_matched": similar_refs.get(candidate_id, {}).get("matched") is True,
                "probability_ref_matched": probability_refs.get(candidate_id, {}).get("matched") is True,
                "frontend_ref_matched": frontend_refs.get(candidate_id, {}).get("matched") is True,
                "similar_cases_count": frontend_summary.get("similar_cases_count"),
                "similar_source_key": similar_refs.get(candidate_id, {}).get("source_key"),
            }
        )
    return rows


def find_reconstructed_artifacts(input_dir: Path, explicit_path: str | None) -> dict[str, Any]:
    searched: list[str] = []
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    root = input_dir.resolve().parents[2] if len(input_dir.resolve().parents) >= 3 else input_dir.resolve().parent
    candidates.extend(
        [
            root / "reconstructed_v1",
            root / "reconstructed_v1_candidate_history.jsonl",
            root / "reconstructed_candidate_history.jsonl",
            Path.cwd() / "outputs" / "reconstructed_v1",
            Path.cwd() / "outputs" / "closeout",
        ]
    )
    for candidate in candidates:
        searched.append(str(candidate))
        if candidate.exists():
            return {
                "reconstructed_artifacts_found": True,
                "artifact_path": str(candidate),
                "searched_paths": searched,
            }
    return {
        "reconstructed_artifacts_found": False,
        "artifact_path": None,
        "searched_paths": searched,
    }


def build_outputs(input_dir: Path, output_dir: Path, reconstructed_path: str | None) -> dict[str, Path]:
    for filename in ["manifest.json", "candidate_history.jsonl", "candidate_schema.md", "artifact_index.json", *REF_FILES.values()]:
        require_file(input_dir / filename)

    manifest = load_json(input_dir / "manifest.json")
    artifact_index = load_json(input_dir / "artifact_index.json")
    candidates = load_jsonl(input_dir / "candidate_history.jsonl")
    refs = {name: load_json(input_dir / filename) for name, filename in REF_FILES.items()}
    candidate_ids = {str(candidate.get("candidate_id", "")) for candidate in candidates}
    candidate_ids.discard("")

    refs_coverage = {name: ref_summary(payload, candidate_ids) for name, payload in refs.items()}
    replay_table = replay_candidates(candidates, refs)

    decision_counts = Counter(str(row.get("decision") or "unknown") for row in replay_table)
    label_status_counts = Counter(str(row.get("label_status") or "unknown") for row in replay_table)
    risk_bucket_counts = Counter(str(row.get("risk_level") or "unknown") for row in replay_table)
    probability_records_with_risk = sum(1 for row in replay_table if row.get("risk_level"))
    probability_records_with_bucket_key = sum(1 for row in replay_table if row.get("bucket_key"))
    all_refs_matched = all(summary["all_matched"] for summary in refs_coverage.values())
    replay_completed = (
        manifest.get("handoff_status") == "READY"
        and manifest.get("not_reconstructed") is True
        and manifest.get("ready_for_modellab_replay") is True
        and len(candidates) == int(manifest.get("candidate_count", len(candidates)))
        and len(candidates) == 20
        and all_refs_matched
    )

    available_outcome_fields = sorted(
        field
        for field in ["label", "label_status"]
        if any(row.get(field) not in (None, "", "unknown") for row in replay_table)
    )
    missing_outcome_fields = [
        "realized_direction",
        "future_return",
        "direction_accuracy",
        "majority_direction_accuracy",
        "formal_v011_outcome",
    ]

    reconstructed = find_reconstructed_artifacts(input_dir, reconstructed_path)
    alignment = {
        **reconstructed,
        "true_candidate_count": len(candidates),
        "reconstructed_candidate_count": None,
        "matched_count": None,
        "missing_in_reconstructed": None,
        "extra_in_reconstructed": None,
        "rank_differences": None,
        "decision_differences": None,
        "label_probability_differences": None,
        "alignment_status": "not_evaluated",
    }
    if reconstructed["reconstructed_artifacts_found"]:
        alignment["alignment_status"] = "reconstructed_artifact_present_manual_alignment_required"
    else:
        alignment["alignment_status"] = "reconstructed_artifacts_missing"

    decision_matrix_complete = replay_completed and all_refs_matched
    reconstructed_alignment_complete = alignment["alignment_status"] == "complete"
    majority_baseline_available = False
    stopline_reasons = []
    if not replay_completed:
        stopline_reasons.append("replay_not_completed")
    if not decision_matrix_complete:
        stopline_reasons.append("decision_matrix_incomplete")
    if not reconstructed_alignment_complete:
        stopline_reasons.append("reconstructed_alignment_incomplete")
    if not majority_baseline_available:
        stopline_reasons.append("majority_baseline_unavailable")
    if missing_outcome_fields:
        stopline_reasons.append("realized_outcome_fields_missing")
    formal_v011_ready = not stopline_reasons

    generated_at = utc_now()
    replay_summary = {
        "generated_at": generated_at,
        "input_dir": str(input_dir),
        "candidate_count": len(candidates),
        "manifest_status": manifest.get("handoff_status"),
        "not_reconstructed": manifest.get("not_reconstructed"),
        "not_trading_advice": manifest.get("not_trading_advice"),
        "ready_for_modellab_replay": manifest.get("ready_for_modellab_replay"),
        "ready_for_formal_v011_recheck": manifest.get("ready_for_formal_v011_recheck"),
        "refs_coverage": refs_coverage,
        "decision_distribution": counter_dict(decision_counts),
        "label_status_distribution": counter_dict(label_status_counts),
        "probability_risk_coverage": {
            "risk_level": f"{probability_records_with_risk}/{len(candidates)}",
            "bucket_key": f"{probability_records_with_bucket_key}/{len(candidates)}",
        },
        "replay_completed": replay_completed,
        "replay_table": replay_table,
    }
    decision_matrix = {
        "generated_at": generated_at,
        "candidate_count": len(candidates),
        "decision_counts": counter_dict(decision_counts),
        "label_status_counts": counter_dict(label_status_counts),
        "risk_bucket_counts": counter_dict(risk_bucket_counts),
        "available_outcome_fields": available_outcome_fields,
        "missing_outcome_fields": missing_outcome_fields,
        "coverage": {
            "refs_all_matched": all_refs_matched,
            "probability_risk": f"{probability_records_with_risk}/{len(candidates)}",
            "probability_bucket_key": f"{probability_records_with_bucket_key}/{len(candidates)}",
        },
        "rows": replay_table,
    }
    formal_recheck = {
        "generated_at": generated_at,
        "formal_v011_ready": formal_v011_ready,
        "decision": "NOT_READY" if not formal_v011_ready else "READY",
        "reasons": stopline_reasons,
        "replay_completed": replay_completed,
        "decision_matrix_complete": decision_matrix_complete,
        "reconstructed_alignment_complete": reconstructed_alignment_complete,
        "majority_baseline_available": majority_baseline_available,
        "stopline_triggered": bool(stopline_reasons),
        "boundary": {
            "trained_model": False,
            "torchrun": False,
            "gpu": False,
            "trading_advice": False,
            "auto_integrated_to_main_project": False,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "replay_summary": output_dir / "replay_summary.json",
        "decision_matrix": output_dir / "decision_matrix_true_left.json",
        "alignment": output_dir / "true_vs_reconstructed_alignment.json",
        "formal_recheck": output_dir / "formal_v011_recheck.json",
    }
    write_json(paths["replay_summary"], replay_summary)
    write_json(paths["decision_matrix"], decision_matrix)
    write_json(paths["alignment"], alignment)
    write_json(paths["formal_recheck"], formal_recheck)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay LeftLab V1.4-D candidate history without training")
    parser.add_argument("--input", required=True, help="Handoff true_left_candidate_history_handoff directory")
    parser.add_argument("--output", required=True, help="Runtime output directory for replay artifacts")
    parser.add_argument("--reconstructed", default=None, help="Optional reconstructed_v1 artifact path")
    args = parser.parse_args()

    paths = build_outputs(Path(args.input), Path(args.output), args.reconstructed)
    print(
        json.dumps(
            {
                "status": "ok",
                "replay_executed": True,
                "outputs": {name: str(path) for name, path in paths.items()},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
