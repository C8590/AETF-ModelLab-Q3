"""Read-only source discovery for realized outcomes and exact alignment inputs.

This audit scans filenames and text/structured file contents. It does not
generate outcomes, infer alignment from rank, train models, or write runtime
artifacts.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
QUARANTINE = WORKSPACE.parent / f"{WORKSPACE.name}-quarantine"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
}

TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

OUTCOME_FIELDS = {
    "realized_outcome",
    "realized_return",
    "realized_direction",
    "actual_return",
    "actual_return_last",
    "actual_direction",
    "future_return",
    "horizon_return",
    "outcome_label",
    "realized_label",
    "post_event_return",
    "forward_return",
    "formal_v011_outcome",
}

PLACEHOLDER_VALUES = {
    "",
    "pending",
    "unknown",
    "placeholder",
    "mock",
    "nan",
    "none",
    "null",
    "na",
    "n/a",
}

EXACT_KEY_FIELDS = {
    "candidate_id",
    "left_candidate_id",
    "true_left_candidate_id",
    "source_candidate_id",
    "candidate_uuid",
    "source_snapshot_id",
    "etf_code",
    "symbol",
    "ticker",
    "as_of_date",
    "signal_date",
    "event_date",
    "source_key",
}

RANK_FIELDS = {"candidate_rank", "rank"}


@dataclass
class StructuredHit:
    root: str
    path: str
    file_kind: str
    row_count: int | None
    outcome_fields: list[str] = field(default_factory=list)
    non_placeholder_outcomes: dict[str, int] = field(default_factory=dict)
    exact_fields: list[str] = field(default_factory=list)
    rank_only: bool = False
    notes: list[str] = field(default_factory=list)


def is_under_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not is_under_excluded(path)
    ]


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def safe_read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit)
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def normalize_field(name: Any) -> str:
    return str(name).strip()


def non_placeholder(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in PLACEHOLDER_VALUES


def collect_fields_from_obj(obj: Any, counter: Counter[str], max_items: int = 5000) -> None:
    seen = 0
    stack = [obj]
    while stack and seen < max_items:
        current = stack.pop()
        seen += 1
        if isinstance(current, dict):
            for key, value in current.items():
                counter[normalize_field(key)] += 1
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(current[:100])


def summarize_csv(root_name: str, root: Path, path: Path) -> StructuredHit | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = [normalize_field(field) for field in (reader.fieldnames or [])]
            rows = []
            for index, row in enumerate(reader):
                if index >= 5000:
                    break
                rows.append(row)
    except (OSError, UnicodeDecodeError, csv.Error):
        return None

    field_set = set(fields)
    outcome_fields = sorted(field_set & OUTCOME_FIELDS)
    exact_fields = sorted(field_set & EXACT_KEY_FIELDS)
    rank_fields = sorted(field_set & RANK_FIELDS)
    if not (outcome_fields or exact_fields or rank_fields):
        return None

    non_placeholder_counts = {
        field: sum(1 for row in rows if non_placeholder(row.get(field)))
        for field in outcome_fields
    }
    return StructuredHit(
        root=root_name,
        path=rel(root, path),
        file_kind="csv",
        row_count=len(rows),
        outcome_fields=outcome_fields,
        non_placeholder_outcomes=non_placeholder_counts,
        exact_fields=exact_fields,
        rank_only=bool(rank_fields) and not exact_fields,
    )


def load_jsonish(path: Path) -> Any:
    text = safe_read_text(path, limit=10_000_000)
    if not text.strip():
        return None
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in text.splitlines()[:5000]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return None
        return rows
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def summarize_jsonish(root_name: str, root: Path, path: Path) -> StructuredHit | None:
    obj = load_jsonish(path)
    if obj is None:
        return None

    counter: Counter[str] = Counter()
    collect_fields_from_obj(obj, counter)
    fields = set(counter)
    outcome_fields = sorted(fields & OUTCOME_FIELDS)
    exact_fields = sorted(fields & EXACT_KEY_FIELDS)
    rank_fields = sorted(fields & RANK_FIELDS)
    if not (outcome_fields or exact_fields or rank_fields):
        return None

    row_count: int | None = len(obj) if isinstance(obj, list) else None
    notes = []
    if path.name in {"label_snapshot_refs.json", "similar_case_refs.json", "probability_bucket_snapshot.json"}:
        notes.append("handoff candidate_id refs include symbol/date-like keys in nested summaries")
    if path.name == "weak_key_alignment_pairs.json":
        notes.append("known weak-key rank-based dry-run output")

    return StructuredHit(
        root=root_name,
        path=rel(root, path),
        file_kind=path.suffix.lower().lstrip("."),
        row_count=row_count,
        outcome_fields=outcome_fields,
        non_placeholder_outcomes={field: counter[field] for field in outcome_fields},
        exact_fields=exact_fields,
        rank_only=bool(rank_fields) and not exact_fields,
        notes=notes,
    )


def discover_structured(root_name: str, root: Path) -> list[StructuredHit]:
    hits: list[StructuredHit] = []
    for path in iter_files(root):
        suffix = path.suffix.lower()
        hit = None
        if suffix == ".csv":
            hit = summarize_csv(root_name, root, path)
        elif suffix in {".json", ".jsonl"}:
            hit = summarize_jsonish(root_name, root, path)
        if hit:
            hits.append(hit)
    return hits


def text_keyword_counts(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    keywords = sorted(OUTCOME_FIELDS | EXACT_KEY_FIELDS | RANK_FIELDS | {"manifest", "provenance", "checksum", "handoff"})
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = safe_read_text(path).lower()
        for keyword in keywords:
            if keyword.lower() in text:
                counts[keyword] += 1
    return counts


def load_label_ref_summary(path: Path) -> dict[str, Any]:
    obj = load_jsonish(path)
    if not isinstance(obj, dict):
        return {"available": False}
    records = [value for value in obj.values() if isinstance(value, dict)]
    matched = [record for record in records if record.get("matched") is True]
    with_symbol_date = []
    labels = Counter()
    for record in matched:
        summary = record.get("matched_record_summary")
        if not isinstance(summary, dict):
            continue
        labels[str(summary.get("label_status") or summary.get("label") or "").lower()] += 1
        symbol = summary.get("etf_code") or summary.get("symbol")
        date = summary.get("signal_date") or summary.get("as_of_date") or summary.get("event_date")
        if record.get("candidate_id") and symbol and date:
            with_symbol_date.append(record)
    return {
        "available": True,
        "record_count": len(records),
        "matched_count": len(matched),
        "candidate_id_symbol_date_count": len(with_symbol_date),
        "label_status_counts": dict(sorted(labels.items())),
        "source_files": sorted({str(record.get("source_file")) for record in with_symbol_date}),
    }


def load_reconstructed_symbol_dates(path: Path) -> set[tuple[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            pairs = set()
            for row in reader:
                symbol = str(row.get("symbol") or "").strip()
                date = str(row.get("as_of_date") or row.get("signal_date") or "").strip()
                if symbol and date:
                    pairs.add((symbol, date))
            return pairs
    except (OSError, UnicodeDecodeError, csv.Error):
        return set()


def label_ref_symbol_dates(path: Path) -> set[tuple[str, str]]:
    obj = load_jsonish(path)
    pairs = set()
    if not isinstance(obj, dict):
        return pairs
    for record in obj.values():
        if not isinstance(record, dict):
            continue
        summary = record.get("matched_record_summary")
        if not isinstance(summary, dict):
            continue
        symbol = str(summary.get("etf_code") or summary.get("symbol") or "").strip()
        date = str(summary.get("signal_date") or summary.get("as_of_date") or "").strip()
        if symbol and date:
            pairs.add((symbol, date))
    return pairs


def alignment_overlap_summary() -> dict[str, Any]:
    label_refs = WORKSPACE / "runtime_inbox" / "leftlab_v1_4_d_ready_handoff" / "true_left_candidate_history_handoff" / "label_snapshot_refs.json"
    reconstructed = WORKSPACE / "runtime_intake" / "reconstructed_v1_quarantine" / "data" / "real" / "reconstructed" / "left_candidates_history_RECONSTRUCTED.csv"
    if not reconstructed.exists():
        reconstructed = QUARANTINE / "data" / "real" / "reconstructed" / "left_candidates_history_RECONSTRUCTED.csv"

    left_pairs = label_ref_symbol_dates(label_refs)
    reconstructed_pairs = load_reconstructed_symbol_dates(reconstructed)
    return {
        "true_left_label_ref_symbol_date_count": len(left_pairs),
        "reconstructed_symbol_date_count": len(reconstructed_pairs),
        "symbol_date_overlap_count": len(left_pairs & reconstructed_pairs),
        "label_refs_path": str(label_refs),
        "reconstructed_path": str(reconstructed),
    }


def print_hit(hit: StructuredHit) -> None:
    parts = [
        f"- [{hit.root}] {hit.path}",
        f"kind={hit.file_kind}",
    ]
    if hit.row_count is not None:
        parts.append(f"rows_sampled={hit.row_count}")
    if hit.outcome_fields:
        parts.append(f"outcome_fields={','.join(hit.outcome_fields)}")
        parts.append(f"non_placeholder={hit.non_placeholder_outcomes}")
    if hit.exact_fields:
        parts.append(f"exact_fields={','.join(hit.exact_fields)}")
    if hit.rank_only:
        parts.append("rank_only=true")
    if hit.notes:
        parts.append(f"notes={'; '.join(hit.notes)}")
    print(" | ".join(parts))


def main() -> int:
    roots = [("workspace", WORKSPACE)]
    if QUARANTINE.exists():
        roots.append(("quarantine_readonly", QUARANTINE))

    print("source_discovery_audit=outcome_and_exact_alignment_v1_4_n")
    print(f"workspace={WORKSPACE}")
    print(f"quarantine_readonly={QUARANTINE if QUARANTINE.exists() else 'not_found'}")
    print("writes_runtime_outputs=false")
    print("trains_models=false")
    print("uses_gpu=false")
    print()

    all_hits: list[StructuredHit] = []
    for root_name, root in roots:
        counts = text_keyword_counts(root)
        print(f"[{root_name}] file_count={len(iter_files(root))}")
        print(f"[{root_name}] keyword_file_counts={dict(sorted(counts.items()))}")
        hits = discover_structured(root_name, root)
        all_hits.extend(hits)
        print(f"[{root_name}] structured_hit_count={len(hits)}")

    print()
    print("structured_hits_with_outcome_fields")
    for hit in all_hits:
        if hit.outcome_fields:
            print_hit(hit)

    print()
    print("structured_hits_with_exact_fields")
    for hit in all_hits:
        if hit.exact_fields or hit.rank_only:
            print_hit(hit)

    label_refs = WORKSPACE / "runtime_inbox" / "leftlab_v1_4_d_ready_handoff" / "true_left_candidate_history_handoff" / "label_snapshot_refs.json"
    print()
    print(f"true_left_label_ref_summary={load_label_ref_summary(label_refs)}")
    print(f"alignment_overlap_summary={alignment_overlap_summary()}")

    outcome_candidates = [
        hit for hit in all_hits if hit.outcome_fields and any(hit.non_placeholder_outcomes.values())
    ]
    exact_candidates = [
        hit for hit in all_hits if hit.exact_fields and not hit.rank_only
    ]
    print()
    print(f"candidate_outcome_source_count={len(outcome_candidates)}")
    print(f"candidate_exact_key_source_count={len(exact_candidates)}")
    print("audit_interpretation_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
