"""Run a rank-based weak-key reconstructed alignment dry-run.

This script reads ignored runtime inputs only and writes ignored dry-run outputs
under outputs/reconstructed_alignment_dry_run/. It does not train, run
torchrun, call GPU APIs, start formal_v011, produce model win-rate claims, or
provide trading advice.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLEAN_ROOT = Path(__file__).resolve().parents[1]
RECONSTRUCTED_INTAKE_DIR = CLEAN_ROOT / "runtime_intake" / "reconstructed_v1_quarantine"
RECONSTRUCTED_OUTPUT_DIR = CLEAN_ROOT / "outputs" / "reconstructed_artifacts"
ALIGNMENT_CANDIDATE_MAP = RECONSTRUCTED_OUTPUT_DIR / "alignment_candidate_map.json"
PRECHECK_REPORT = CLEAN_ROOT / "outputs" / "reconstructed_alignment_precheck" / "alignment_precheck_report.json"
TRUE_LEFT_HANDOFF_DIR = (
    CLEAN_ROOT
    / "runtime_inbox"
    / "leftlab_v1_4_d_ready_handoff"
    / "true_left_candidate_history_handoff"
)
TRUE_LEFT_HISTORY = TRUE_LEFT_HANDOFF_DIR / "candidate_history.jsonl"
TRUE_LEFT_MANIFEST = TRUE_LEFT_HANDOFF_DIR / "manifest.json"
DRY_RUN_OUTPUT_DIR = CLEAN_ROOT / "outputs" / "reconstructed_alignment_dry_run"
PAIRS_CSV = DRY_RUN_OUTPUT_DIR / "weak_key_alignment_pairs.csv"
PAIRS_JSON = DRY_RUN_OUTPUT_DIR / "weak_key_alignment_pairs.json"
SUMMARY_MD = DRY_RUN_OUTPUT_DIR / "weak_key_alignment_summary.md"
DECISION_JSON = DRY_RUN_OUTPUT_DIR / "weak_key_alignment_decision.json"

ALIGNMENT_MODE = "rank_based_weak_key"
ALIGNMENT_KEY = "candidate_rank"
ALIGNMENT_KEY_STRENGTH = "weak"
DRY_RUN_STATUS_COMPLETED = "RECONSTRUCTED_WEAK_KEY_ALIGNMENT_DRY_RUN_COMPLETED_REVIEW_REQUIRED"
DRY_RUN_STATUS_MISSING_INPUT = "RECONSTRUCTED_WEAK_KEY_ALIGNMENT_DRY_RUN_BLOCKED_MISSING_INPUT"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        records = [dict(row) for row in reader]
        return records, list(reader.fieldnames or [])


def ensure_inputs(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"{DRY_RUN_STATUS_MISSING_INPUT}: {', '.join(missing)}")


def selected_candidate_set(candidate_map: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [item for item in candidate_map if item.get("recommended_for_alignment_precheck") is True]
    candidate_sets = selected or candidate_map[:1]
    if len(candidate_sets) != 1:
        raise ValueError(f"expected one reconstructed candidate set, found {len(candidate_sets)}")
    return candidate_sets[0]


def reconstructed_history_path(candidate_set: dict[str, Any]) -> Path:
    relative_path = candidate_set.get("candidate_history_artifact")
    if not relative_path:
        raise FileNotFoundError(f"{DRY_RUN_STATUS_MISSING_INPUT}: missing candidate_history_artifact")
    return RECONSTRUCTED_INTAKE_DIR / Path(str(relative_path))


def rank_value(record: dict[str, Any]) -> str | None:
    value = record.get(ALIGNMENT_KEY)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def records_by_rank(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        rank = rank_value(record)
        if rank is not None:
            grouped.setdefault(rank, []).append(record)
    return grouped


def sort_rank_values(values: set[str]) -> list[str]:
    return sorted(values, key=lambda value: (len(value), value))


def with_reconstructed_row_ids(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row_index, record in enumerate(records, start=1):
        item: dict[str, Any] = dict(record)
        item["reconstructed_row_index"] = row_index
        enriched.append(item)
    return enriched


def with_true_left_row_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row_index, record in enumerate(records, start=1):
        item = dict(record)
        item["true_left_row_index"] = row_index
        enriched.append(item)
    return enriched


def build_pairs(
    true_left_by_rank: dict[str, list[dict[str, Any]]],
    reconstructed_by_rank: dict[str, list[dict[str, Any]]],
    overlap_values: list[str],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    pair_index = 1
    for rank in overlap_values:
        true_left_records = true_left_by_rank.get(rank, [])
        reconstructed_records = reconstructed_by_rank.get(rank, [])
        ambiguous = len(true_left_records) != 1 or len(reconstructed_records) != 1
        ambiguity_reason = (
            "rank maps one-to-one"
            if not ambiguous
            else f"candidate_rank {rank} maps true_left_count={len(true_left_records)} "
            f"to reconstructed_count={len(reconstructed_records)}"
        )
        for true_left in true_left_records:
            for reconstructed in reconstructed_records:
                pairs.append(
                    {
                        "pair_id": f"weak-rank-{rank}-{pair_index:04d}",
                        "alignment_mode": ALIGNMENT_MODE,
                        "alignment_key": ALIGNMENT_KEY,
                        "alignment_key_value": rank,
                        "alignment_key_strength": ALIGNMENT_KEY_STRENGTH,
                        "alignment_ambiguous": ambiguous,
                        "ambiguity_reason": ambiguity_reason,
                        "date_symbol_alignment": False,
                        "exact_date_symbol_alignment": False,
                        "candidate_id_exact_alignment": False,
                        "true_left_row_index": true_left.get("true_left_row_index"),
                        "true_left_candidate_id": true_left.get("candidate_id"),
                        "true_left_candidate_rank": true_left.get("candidate_rank"),
                        "true_left_timestamp": true_left.get("timestamp"),
                        "true_left_round": true_left.get("round"),
                        "true_left_decision": true_left.get("decision"),
                        "true_left_probability_bucket": true_left.get("probability_bucket"),
                        "reconstructed_row_index": reconstructed.get("reconstructed_row_index"),
                        "reconstructed_candidate_rank": reconstructed.get("candidate_rank"),
                        "reconstructed_as_of_date": reconstructed.get("as_of_date"),
                        "reconstructed_symbol": reconstructed.get("symbol"),
                        "reconstructed_display_name": reconstructed.get("display_name"),
                        "reconstructed_left_score": reconstructed.get("left_score"),
                        "formal_v011_ready_support": False,
                    }
                )
                pair_index += 1
    return pairs


def build_report() -> dict[str, Any]:
    ensure_inputs([ALIGNMENT_CANDIDATE_MAP, PRECHECK_REPORT, TRUE_LEFT_HISTORY, TRUE_LEFT_MANIFEST])
    candidate_map = load_json(ALIGNMENT_CANDIDATE_MAP)
    if not isinstance(candidate_map, list):
        raise ValueError("alignment_candidate_map.json must contain a list")
    candidate_set = selected_candidate_set(candidate_map)
    reconstructed_history = reconstructed_history_path(candidate_set)
    ensure_inputs([reconstructed_history])

    precheck = load_json(PRECHECK_REPORT)
    true_left_manifest = load_json(TRUE_LEFT_MANIFEST)
    true_left_records = with_true_left_row_ids(load_jsonl(TRUE_LEFT_HISTORY))
    reconstructed_records, reconstructed_fields = load_csv(reconstructed_history)
    enriched_reconstructed_records = with_reconstructed_row_ids(reconstructed_records)

    true_left_by_rank = records_by_rank(true_left_records)
    reconstructed_by_rank = records_by_rank(enriched_reconstructed_records)
    overlap_values = sort_rank_values(set(true_left_by_rank) & set(reconstructed_by_rank))
    pairs = build_pairs(true_left_by_rank, reconstructed_by_rank, overlap_values)
    ambiguous_pair_count = sum(1 for pair in pairs if pair["alignment_ambiguous"])
    ambiguous_rank_values = [
        rank
        for rank in overlap_values
        if len(true_left_by_rank.get(rank, [])) != 1 or len(reconstructed_by_rank.get(rank, [])) != 1
    ]

    date_overlap_count = int(precheck.get("date_overlap_count") or 0)
    symbol_overlap_count = int(precheck.get("symbol_overlap_count") or 0)
    candidate_key_overlap_count = len(overlap_values)
    remaining_stopline_reasons = [
        "reconstructed_weak_key_alignment_dry_run_review_required",
        "realized_outcome_fields_missing",
    ]

    summary = {
        "alignment_mode": ALIGNMENT_MODE,
        "alignment_key": ALIGNMENT_KEY,
        "alignment_key_strength": ALIGNMENT_KEY_STRENGTH,
        "alignment_key_values": overlap_values,
        "true_left_candidate_count": int(true_left_manifest.get("candidate_count") or len(true_left_records)),
        "reconstructed_candidate_count": len(enriched_reconstructed_records),
        "reconstructed_candidate_set_id": candidate_set.get("candidate_set_id"),
        "reconstructed_candidate_history_path": str(reconstructed_history),
        "true_left_candidate_history_path": str(TRUE_LEFT_HISTORY),
        "candidate_key_overlap_count": candidate_key_overlap_count,
        "aligned_pair_count": len(pairs),
        "ambiguous_pair_count": ambiguous_pair_count,
        "ambiguous_rank_count": len(ambiguous_rank_values),
        "ambiguous_rank_values": ambiguous_rank_values,
        "date_overlap_count": date_overlap_count,
        "symbol_overlap_count": symbol_overlap_count,
        "date_symbol_alignment": False,
        "exact_date_symbol_alignment": False,
        "candidate_id_exact_alignment": False,
        "schema_alignable": bool(precheck.get("schema_alignable")),
        "candidate_level_alignment_possible": bool(precheck.get("candidate_level_alignment_possible")),
        "dry_run_status": DRY_RUN_STATUS_COMPLETED,
        "formal_v011_ready_support": False,
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "remaining_stopline_reasons": remaining_stopline_reasons,
        "recommend_review": True,
        "recommend_next_stage_reviewed_alignment_analysis": True,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu": True,
        "not_trading_advice": True,
        "not_exact_date_symbol_alignment": True,
        "not_candidate_id_exact_alignment": True,
        "reconstructed_fields": reconstructed_fields,
        "source_precheck_status": precheck.get("alignment_precheck_status"),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pairs": pairs,
    }
    return summary


def write_pairs_csv(pairs: list[dict[str, Any]]) -> None:
    fieldnames = [
        "pair_id",
        "alignment_mode",
        "alignment_key",
        "alignment_key_value",
        "alignment_key_strength",
        "alignment_ambiguous",
        "ambiguity_reason",
        "date_symbol_alignment",
        "exact_date_symbol_alignment",
        "candidate_id_exact_alignment",
        "true_left_row_index",
        "true_left_candidate_id",
        "true_left_candidate_rank",
        "true_left_timestamp",
        "true_left_round",
        "true_left_decision",
        "true_left_probability_bucket",
        "reconstructed_row_index",
        "reconstructed_candidate_rank",
        "reconstructed_as_of_date",
        "reconstructed_symbol",
        "reconstructed_display_name",
        "reconstructed_left_score",
        "formal_v011_ready_support",
    ]
    with PAIRS_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pairs)


def write_summary_md(report: dict[str, Any]) -> None:
    lines = [
        "# Reconstructed Weak-Key Alignment Dry-Run Summary",
        "",
        f"alignment_mode = {report['alignment_mode']}",
        f"alignment_key = {report['alignment_key']}",
        f"alignment_key_strength = {report['alignment_key_strength']}",
        f"true_left_candidate_count = {report['true_left_candidate_count']}",
        f"reconstructed_candidate_count = {report['reconstructed_candidate_count']}",
        f"candidate_key_overlap_count = {report['candidate_key_overlap_count']}",
        f"aligned_pair_count = {report['aligned_pair_count']}",
        f"ambiguous_pair_count = {report['ambiguous_pair_count']}",
        f"date_overlap_count = {report['date_overlap_count']}",
        f"symbol_overlap_count = {report['symbol_overlap_count']}",
        f"exact_date_symbol_alignment = {str(report['exact_date_symbol_alignment']).lower()}",
        f"candidate_id_exact_alignment = {str(report['candidate_id_exact_alignment']).lower()}",
        f"dry_run_status = {report['dry_run_status']}",
        f"formal_v011_ready = {str(report['formal_v011_ready']).lower()}",
        f"stopline_triggered = {str(report['stopline_triggered']).lower()}",
        "remaining_stopline_reasons = " + ", ".join(report["remaining_stopline_reasons"]),
        "",
        "This dry-run uses candidate_rank only. It is rank-based weak-key alignment,",
        "not date/symbol/candidate-id exact alignment. It does not train, run",
        "torchrun, call GPU APIs, start formal_v011, produce model results, or",
        "provide trading advice.",
        "",
    ]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_decision_json(report: dict[str, Any]) -> None:
    decision_keys = [
        "alignment_mode",
        "alignment_key",
        "alignment_key_strength",
        "candidate_key_overlap_count",
        "aligned_pair_count",
        "ambiguous_pair_count",
        "date_overlap_count",
        "symbol_overlap_count",
        "exact_date_symbol_alignment",
        "candidate_id_exact_alignment",
        "dry_run_status",
        "formal_v011_ready_support",
        "formal_v011_ready",
        "stopline_triggered",
        "remaining_stopline_reasons",
        "recommend_review",
        "recommend_next_stage_reviewed_alignment_analysis",
        "no_training",
        "no_torchrun",
        "no_gpu",
        "not_trading_advice",
    ]
    decision = {key: report[key] for key in decision_keys}
    DECISION_JSON.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    DRY_RUN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PAIRS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_pairs_csv(report["pairs"])
    write_summary_md(report)
    write_decision_json(report)
    print(json.dumps({key: value for key, value in report.items() if key != "pairs"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
