"""Run a structural precheck for reconstructed vs true-left alignment.

The precheck reads ignored runtime inputs only and writes ignored runtime
outputs under outputs/reconstructed_alignment_precheck/. It does not train,
run torchrun, call GPU APIs, start formal_v011, or promote any reconstructed
artifact to replay readiness.
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
TRUE_LEFT_INBOX_ROOT = CLEAN_ROOT / "runtime_inbox" / "leftlab_v1_4_d_ready_handoff"
TRUE_LEFT_HANDOFF_DIR = TRUE_LEFT_INBOX_ROOT / "true_left_candidate_history_handoff"
PRECHECK_OUTPUT_DIR = CLEAN_ROOT / "outputs" / "reconstructed_alignment_precheck"
PRECHECK_JSON = PRECHECK_OUTPUT_DIR / "alignment_precheck_report.json"
PRECHECK_CSV = PRECHECK_OUTPUT_DIR / "alignment_precheck_report.csv"
PRECHECK_SUMMARY = PRECHECK_OUTPUT_DIR / "alignment_precheck_summary.md"

DATE_FIELDS = ("trade_date", "date", "as_of_date", "timestamp", "round")
SYMBOL_FIELDS = ("code", "symbol", "ts_code")
CANDIDATE_KEY_FIELDS = ("candidate_id", "candidate_rank")


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


def normalize_fields(fields: list[str] | set[str]) -> set[str]:
    return {str(field).strip().lower() for field in fields if str(field).strip()}


def field_values(records: list[dict[str, Any]], field_names: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    for record in records:
        lowered = {str(key).lower(): value for key, value in record.items()}
        for field in field_names:
            value = lowered.get(field)
            if value is not None and str(value).strip():
                values.add(str(value).strip())
    return values


def first_present_field(fields: set[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in fields:
            return candidate
    return None


def resolve_reconstructed_path(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    return RECONSTRUCTED_INTAKE_DIR / Path(relative_path)


def load_alignment_candidate_map() -> list[dict[str, Any]]:
    if not ALIGNMENT_CANDIDATE_MAP.exists():
        raise FileNotFoundError(f"missing reconstructed alignment candidate map: {ALIGNMENT_CANDIDATE_MAP}")
    data = load_json(ALIGNMENT_CANDIDATE_MAP)
    if not isinstance(data, list):
        raise ValueError("alignment_candidate_map.json must contain a list")
    return data


def selected_candidate_sets(candidate_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [item for item in candidate_map if item.get("recommended_for_alignment_precheck") is True]
    return selected or candidate_map[:1]


def true_left_paths() -> dict[str, Path]:
    candidate_history = TRUE_LEFT_HANDOFF_DIR / "candidate_history.jsonl"
    manifest = TRUE_LEFT_HANDOFF_DIR / "manifest.json"
    artifact_index = TRUE_LEFT_HANDOFF_DIR / "artifact_index.json"
    missing = [path for path in (candidate_history, manifest, artifact_index) if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"missing true-left handoff inputs: {missing_text}")
    return {
        "candidate_history": candidate_history,
        "manifest": manifest,
        "artifact_index": artifact_index,
    }


def status_from_checks(
    reconstructed_inputs_readable: bool,
    true_left_readable: bool,
    schema_alignable: bool,
    alignment_key_candidates: list[str],
) -> str:
    if not reconstructed_inputs_readable:
        return "RECONSTRUCTED_ALIGNMENT_PRECHECK_BLOCKED_MISSING_RECONSTRUCTED_INPUT"
    if not true_left_readable:
        return "RECONSTRUCTED_ALIGNMENT_PRECHECK_BLOCKED_MISSING_TRUE_LEFT_INPUT"
    if not schema_alignable:
        return "RECONSTRUCTED_ALIGNMENT_PRECHECK_BLOCKED_SCHEMA_MISMATCH"
    if not alignment_key_candidates:
        return "RECONSTRUCTED_ALIGNMENT_PRECHECK_BLOCKED_NO_KEY_OVERLAP"
    return "RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED"


def build_report() -> dict[str, Any]:
    candidate_map = load_alignment_candidate_map()
    selected_sets = selected_candidate_sets(candidate_map)
    if len(selected_sets) != 1:
        raise ValueError(f"expected one selected reconstructed candidate set, found {len(selected_sets)}")
    selected = selected_sets[0]

    reconstructed_candidate_history_path = resolve_reconstructed_path(selected.get("candidate_history_artifact"))
    reconstructed_decision_matrix_path = resolve_reconstructed_path(selected.get("decision_matrix_artifact"))
    reconstructed_closeout_path = resolve_reconstructed_path(selected.get("closeout_artifact"))
    reconstructed_artifact_index_path = resolve_reconstructed_path(selected.get("artifact_index_artifact"))
    reconstructed_paths = [
        reconstructed_candidate_history_path,
        reconstructed_decision_matrix_path,
        reconstructed_closeout_path,
        reconstructed_artifact_index_path,
    ]
    reconstructed_inputs_readable = all(path is not None and path.exists() and path.is_file() for path in reconstructed_paths)
    if not reconstructed_inputs_readable:
        missing = [str(path) for path in reconstructed_paths if path is None or not path.exists()]
        raise FileNotFoundError(f"missing reconstructed inputs: {', '.join(missing)}")

    assert reconstructed_candidate_history_path is not None
    assert reconstructed_decision_matrix_path is not None
    assert reconstructed_closeout_path is not None
    assert reconstructed_artifact_index_path is not None

    reconstructed_records, reconstructed_fields = load_csv(reconstructed_candidate_history_path)
    load_json(reconstructed_decision_matrix_path)
    closeout = load_json(reconstructed_closeout_path)
    load_json(reconstructed_artifact_index_path)

    true_left = true_left_paths()
    true_left_records = load_jsonl(true_left["candidate_history"])
    manifest = load_json(true_left["manifest"])
    load_json(true_left["artifact_index"])

    reconstructed_field_set = normalize_fields(reconstructed_fields)
    true_left_field_set = normalize_fields(set().union(*(record.keys() for record in true_left_records)) if true_left_records else set())
    common_fields = sorted(reconstructed_field_set & true_left_field_set)

    candidate_key_field = first_present_field(reconstructed_field_set & true_left_field_set, CANDIDATE_KEY_FIELDS)
    date_field_reconstructed = first_present_field(reconstructed_field_set, DATE_FIELDS)
    date_field_true_left = first_present_field(true_left_field_set, DATE_FIELDS)
    symbol_field_reconstructed = first_present_field(reconstructed_field_set, SYMBOL_FIELDS)
    symbol_field_true_left = first_present_field(true_left_field_set, SYMBOL_FIELDS)

    candidate_key_overlap_values: set[str] = set()
    alignment_key_candidates: list[str] = []
    if candidate_key_field:
        reconstructed_values = field_values(reconstructed_records, (candidate_key_field,))
        true_left_values = field_values(true_left_records, (candidate_key_field,))
        candidate_key_overlap_values = reconstructed_values & true_left_values
        if candidate_key_overlap_values:
            alignment_key_candidates.append(candidate_key_field)

    reconstructed_dates = field_values(reconstructed_records, DATE_FIELDS)
    true_left_dates = field_values(true_left_records, DATE_FIELDS)
    reconstructed_symbols = field_values(reconstructed_records, SYMBOL_FIELDS)
    true_left_symbols = field_values(true_left_records, SYMBOL_FIELDS)

    schema_alignable = bool(common_fields)
    candidate_level_alignment_possible = bool(candidate_key_overlap_values)
    true_left_readable = bool(true_left_records) and manifest.get("candidate_history_type") == "true_left_candidate_history"
    true_left_candidate_count = int(manifest.get("candidate_count") or len(true_left_records))
    precheck_status = status_from_checks(
        reconstructed_inputs_readable=reconstructed_inputs_readable,
        true_left_readable=true_left_readable,
        schema_alignable=schema_alignable,
        alignment_key_candidates=alignment_key_candidates,
    )
    remaining_stopline_reasons = [
        "reconstructed_alignment_precheck_review_required",
        "realized_outcome_fields_missing",
    ]

    return {
        "precheck_name": "modellab_v1_4_j_reconstructed_alignment_precheck",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "clean_root": str(CLEAN_ROOT),
        "reconstructed_candidate_set_count": len(selected_sets),
        "reconstructed_candidate_set_id": selected.get("candidate_set_id"),
        "reconstructed_candidate_history_path": str(reconstructed_candidate_history_path),
        "reconstructed_decision_matrix_path": str(reconstructed_decision_matrix_path),
        "reconstructed_closeout_path": str(reconstructed_closeout_path),
        "reconstructed_artifact_index_path": str(reconstructed_artifact_index_path),
        "true_left_candidate_history_path": str(true_left["candidate_history"]),
        "true_left_manifest_path": str(true_left["manifest"]),
        "true_left_artifact_index_path": str(true_left["artifact_index"]),
        "true_left_candidate_history_readable": true_left_readable,
        "true_left_candidate_count": true_left_candidate_count,
        "true_left_candidate_count_expected": 20,
        "true_left_candidate_count_is_20": true_left_candidate_count == 20,
        "reconstructed_candidate_history_readable": True,
        "reconstructed_decision_matrix_readable": True,
        "reconstructed_closeout_readable": True,
        "reconstructed_artifact_index_readable": True,
        "reconstructed_candidate_count": len(reconstructed_records),
        "common_field_count": len(common_fields),
        "common_fields": common_fields,
        "candidate_key_field": candidate_key_field,
        "candidate_key_overlap_count": len(candidate_key_overlap_values),
        "candidate_key_overlap_values": sorted(candidate_key_overlap_values, key=lambda value: (len(value), value)),
        "date_field_reconstructed": date_field_reconstructed,
        "date_field_true_left": date_field_true_left,
        "date_overlap_count": len(reconstructed_dates & true_left_dates),
        "symbol_field_reconstructed": symbol_field_reconstructed,
        "symbol_field_true_left": symbol_field_true_left,
        "symbol_overlap_count": len(reconstructed_symbols & true_left_symbols),
        "alignment_key_candidates": alignment_key_candidates,
        "schema_alignable": schema_alignable,
        "candidate_level_alignment_possible": candidate_level_alignment_possible,
        "true_left_candidate_history_type": manifest.get("candidate_history_type"),
        "reconstructed_candidate_history_type": closeout.get("candidate_history_type"),
        "can_distinguish_true_left_from_reconstructed": (
            manifest.get("candidate_history_type") == "true_left_candidate_history"
            and closeout.get("candidate_history_type") == "reconstructed_not_true_left_snapshot"
        ),
        "risk_mistake_true_left_as_reconstructed": "low",
        "risk_mistake_reconstructed_as_realized_outcome": "controlled_by_stopline",
        "precheck_status": precheck_status,
        "alignment_precheck_status": precheck_status,
        "recommend_review": precheck_status == "RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED",
        "recommend_alignment_dry_run": precheck_status == "RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED",
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "remaining_stopline_reasons": remaining_stopline_reasons,
        "no_training": True,
        "no_torchrun": True,
        "no_gpu": True,
        "not_trading_advice": True,
    }


def write_report_csv(report: dict[str, Any]) -> None:
    fieldnames = [
        "reconstructed_candidate_set_id",
        "true_left_candidate_count",
        "reconstructed_candidate_count",
        "common_field_count",
        "common_fields",
        "candidate_key_overlap_count",
        "date_overlap_count",
        "symbol_overlap_count",
        "alignment_key_candidates",
        "schema_alignable",
        "candidate_level_alignment_possible",
        "precheck_status",
        "formal_v011_ready",
        "stopline_triggered",
        "remaining_stopline_reasons",
        "no_training",
        "no_torchrun",
        "no_gpu",
        "not_trading_advice",
    ]
    with PRECHECK_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                field: json.dumps(report[field], ensure_ascii=False) if isinstance(report.get(field), list) else report.get(field)
                for field in fieldnames
            }
        )


def write_summary(report: dict[str, Any]) -> None:
    lines = [
        "# Reconstructed Alignment Precheck Summary",
        "",
        f"precheck_status = {report['precheck_status']}",
        f"reconstructed_candidate_set_id = {report['reconstructed_candidate_set_id']}",
        f"true_left_candidate_count = {report['true_left_candidate_count']}",
        f"reconstructed_candidate_count = {report['reconstructed_candidate_count']}",
        f"common_fields = {', '.join(report['common_fields']) if report['common_fields'] else 'none'}",
        f"candidate_key_overlap_count = {report['candidate_key_overlap_count']}",
        f"date_overlap_count = {report['date_overlap_count']}",
        f"symbol_overlap_count = {report['symbol_overlap_count']}",
        f"schema_alignable = {str(report['schema_alignable']).lower()}",
        f"candidate_level_alignment_possible = {str(report['candidate_level_alignment_possible']).lower()}",
        f"formal_v011_ready = {str(report['formal_v011_ready']).lower()}",
        f"stopline_triggered = {str(report['stopline_triggered']).lower()}",
        "remaining_stopline_reasons = "
        + ", ".join(report["remaining_stopline_reasons"]),
        "",
        "This precheck does not train, run torchrun, call GPU APIs, start formal_v011,",
        "produce model win-rate claims, or provide trading advice.",
        "",
    ]
    PRECHECK_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report()
    PRECHECK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PRECHECK_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report_csv(report)
    write_summary(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
