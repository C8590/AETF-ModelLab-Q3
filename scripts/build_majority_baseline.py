"""Build a read-only majority baseline for LeftLab V1.4-D replay output.

This script reads existing handoff/replay runtime artifacts and writes baseline
reports under outputs/. It does not train models, import torch, call GPU APIs, or
modify payload files.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPLAY_DIR = Path("outputs/replay/leftlab_v1_4_d")
HANDOFF_DIR = Path("runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff")
OUTPUT_DIR = Path("outputs/baseline/leftlab_v1_4_d")

REPLAY_SUMMARY = REPLAY_DIR / "replay_summary.json"
DECISION_MATRIX = REPLAY_DIR / "decision_matrix_true_left.json"
FORMAL_RECHECK = REPLAY_DIR / "formal_v011_recheck.json"
CANDIDATE_HISTORY = HANDOFF_DIR / "candidate_history.jsonl"

OUTCOME_FIELDS = {
    "realized_direction",
    "future_return",
    "direction_accuracy",
    "majority_direction_accuracy",
    "formal_v011_outcome",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def require_inputs() -> None:
    missing = [
        str(path)
        for path in (REPLAY_SUMMARY, DECISION_MATRIX, FORMAL_RECHECK, CANDIDATE_HISTORY)
        if not path.exists()
    ]
    if missing:
        joined = "\n  - ".join(missing)
        raise FileNotFoundError(
            "Required replay/handoff runtime files are missing:\n"
            f"  - {joined}\n"
            "Restore them under ignored runtime/output directories before rebuilding the baseline."
        )


def majority(values: list[str], total: int) -> dict[str, Any]:
    counts = Counter(value if value not in ("", None) else "missing" for value in values)
    if not counts:
        return {
            "value": None,
            "count": 0,
            "rate": 0.0,
            "distribution": {},
        }
    value, count = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0]
    return {
        "value": value,
        "count": count,
        "rate": count / total if total else 0.0,
        "distribution": dict(sorted(counts.items(), key=lambda item: str(item[0]))),
    }


def has_realized_outcome(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        for field in OUTCOME_FIELDS:
            value = row.get(field)
            if value not in (None, "", "missing", "pending", "unknown"):
                return True
    return False


def build_report() -> dict[str, Any]:
    require_inputs()
    replay_summary = read_json(REPLAY_SUMMARY)
    decision_matrix = read_json(DECISION_MATRIX)
    formal_recheck = read_json(FORMAL_RECHECK)
    candidate_history = read_jsonl(CANDIDATE_HISTORY)

    rows = replay_summary.get("replay_table") or decision_matrix.get("rows") or []
    if not rows:
        raise ValueError("Replay summary and decision matrix do not contain baseline rows.")

    candidate_count = len(candidate_history)
    if candidate_count != len(rows):
        raise ValueError(
            "Candidate history and replay row counts differ: "
            f"{candidate_count} != {len(rows)}"
        )

    decision_majority = majority([row.get("decision", "missing") for row in rows], candidate_count)
    label_status_majority = majority(
        [row.get("label_status", row.get("label", "missing")) for row in rows],
        candidate_count,
    )
    risk_bucket_majority = majority(
        [row.get("risk_bucket") or row.get("risk_level") or "missing" for row in rows],
        candidate_count,
    )

    realized_outcome_available = has_realized_outcome(rows)
    directional_values = {decision_majority["value"], label_status_majority["value"]}
    directional_baseline_available = bool(
        realized_outcome_available
        and not directional_values.intersection({"unknown", "pending", "missing", None})
    )

    report = {
        "baseline_name": "leftlab_v1_4_d_majority_baseline",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_sources": {
            "handoff_candidate_history": str(CANDIDATE_HISTORY),
            "replay_summary": str(REPLAY_SUMMARY),
            "decision_matrix": str(DECISION_MATRIX),
            "formal_v011_recheck": str(FORMAL_RECHECK),
        },
        "candidate_count": candidate_count,
        "majority_baseline_available": "partial",
        "decision_majority": {
            "field": "decision",
            "majority_decision": decision_majority["value"],
            "majority_decision_count": decision_majority["count"],
            "majority_decision_rate": decision_majority["rate"],
            "distribution": decision_majority["distribution"],
        },
        "label_status_majority": {
            "field": "label_status",
            "majority_label_status": label_status_majority["value"],
            "majority_label_status_count": label_status_majority["count"],
            "majority_label_status_rate": label_status_majority["rate"],
            "distribution": label_status_majority["distribution"],
        },
        "risk_bucket_majority": {
            "field": "risk_bucket_or_risk_level",
            "majority_risk_bucket": risk_bucket_majority["value"],
            "majority_risk_bucket_count": risk_bucket_majority["count"],
            "majority_risk_bucket_rate": risk_bucket_majority["rate"],
            "distribution": risk_bucket_majority["distribution"],
            "not_realized_return_direction": True,
        },
        "neutral_baseline": {
            "name": "neutral_no_edge_baseline",
            "available": True,
            "prediction": "no_directional_edge",
            "rationale": (
                "All decisions are unknown, all labels are pending, and realized outcome "
                "fields are missing; the reproducible baseline is neutral rather than directional."
            ),
        },
        "directional_baseline_available": directional_baseline_available,
        "outcome_based_baseline_available": realized_outcome_available,
        "formal_v011_ready_support": False,
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "stopline_reasons_remaining": [
            "reconstructed_artifacts_missing",
            "realized_outcome_fields_missing",
        ],
        "stopline_reason_remediated": "majority_baseline_unavailable",
        "source_formal_recheck": {
            "formal_v011_ready": formal_recheck.get("formal_v011_ready"),
            "stopline_triggered": formal_recheck.get("stopline_triggered"),
            "reasons": formal_recheck.get("reasons", []),
        },
        "recheck_input": {
            "majority_baseline_available": "partial",
            "directional_baseline_available": False,
            "outcome_based_baseline_available": False,
            "formal_v011_ready_support": False,
            "do_not_treat_pending_as_realized_outcome": True,
            "do_not_treat_risk_bucket_as_return_direction": True,
            "do_not_report_as_model_win_rate": True,
        },
        "not_trading_advice": True,
        "no_training": True,
        "no_gpu": True,
        "torchrun": False,
        "trained_model": False,
        "runtime_payload_modified": False,
    }
    return report


def write_csv(report: dict[str, Any], path: Path) -> None:
    rows = [
        {
            "baseline": "decision_majority",
            "field": "decision",
            "majority_value": report["decision_majority"]["majority_decision"],
            "majority_count": report["decision_majority"]["majority_decision_count"],
            "majority_rate": report["decision_majority"]["majority_decision_rate"],
            "distribution_json": json.dumps(report["decision_majority"]["distribution"], ensure_ascii=False),
        },
        {
            "baseline": "label_status_majority",
            "field": "label_status",
            "majority_value": report["label_status_majority"]["majority_label_status"],
            "majority_count": report["label_status_majority"]["majority_label_status_count"],
            "majority_rate": report["label_status_majority"]["majority_label_status_rate"],
            "distribution_json": json.dumps(report["label_status_majority"]["distribution"], ensure_ascii=False),
        },
        {
            "baseline": "risk_bucket_majority",
            "field": "risk_bucket_or_risk_level",
            "majority_value": report["risk_bucket_majority"]["majority_risk_bucket"],
            "majority_count": report["risk_bucket_majority"]["majority_risk_bucket_count"],
            "majority_rate": report["risk_bucket_majority"]["majority_risk_bucket_rate"],
            "distribution_json": json.dumps(report["risk_bucket_majority"]["distribution"], ensure_ascii=False),
        },
        {
            "baseline": "neutral_no_edge",
            "field": "directional_edge",
            "majority_value": report["neutral_baseline"]["prediction"],
            "majority_count": "",
            "majority_rate": "",
            "distribution_json": "",
        },
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "baseline",
                "field",
                "majority_value",
                "majority_count",
                "majority_rate",
                "distribution_json",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# LeftLab V1.4-D Majority Baseline Summary",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"- candidate_count: {report['candidate_count']}",
        (
            "- decision majority baseline: "
            f"{report['decision_majority']['majority_decision']} "
            f"({report['decision_majority']['majority_decision_count']}/"
            f"{report['candidate_count']}, "
            f"{report['decision_majority']['majority_decision_rate']:.2%})"
        ),
        (
            "- label_status majority baseline: "
            f"{report['label_status_majority']['majority_label_status']} "
            f"({report['label_status_majority']['majority_label_status_count']}/"
            f"{report['candidate_count']}, "
            f"{report['label_status_majority']['majority_label_status_rate']:.2%})"
        ),
        (
            "- risk bucket majority baseline: "
            f"{report['risk_bucket_majority']['majority_risk_bucket']} "
            f"({report['risk_bucket_majority']['majority_risk_bucket_count']}/"
            f"{report['candidate_count']}, "
            f"{report['risk_bucket_majority']['majority_risk_bucket_rate']:.2%})"
        ),
        "- neutral baseline: no_directional_edge",
        f"- directional_baseline_available: {str(report['directional_baseline_available']).lower()}",
        f"- outcome_based_baseline_available: {str(report['outcome_based_baseline_available']).lower()}",
        f"- formal_v011_ready_support: {str(report['formal_v011_ready_support']).lower()}",
        f"- formal_v011_ready: {str(report['formal_v011_ready']).lower()}",
        f"- stopline_triggered: {str(report['stopline_triggered']).lower()}",
        "",
        "This is not trading advice. No training, torchrun, or GPU path is used.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "majority_baseline_report.json"
    csv_path = OUTPUT_DIR / "majority_baseline_report.csv"
    summary_path = OUTPUT_DIR / "majority_baseline_summary.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(report, csv_path)
    write_summary(report, summary_path)

    print(json.dumps({
        "report": str(json_path),
        "candidate_count": report["candidate_count"],
        "decision_majority": report["decision_majority"],
        "label_status_majority": report["label_status_majority"],
        "risk_bucket_majority": report["risk_bucket_majority"],
        "formal_v011_ready_support": report["formal_v011_ready_support"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
