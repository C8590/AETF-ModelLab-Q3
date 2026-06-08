"""Audit reconstructed artifact candidates without importing them.

The script scans the clean ModelLab workspace and the quarantine workspace in
read-only mode, then writes an audit index under outputs/. It does not train,
run torchrun, call GPU APIs, modify payloads, or promote quarantine files into
formal artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLEAN_ROOT = Path("E:/AETF-ModelLab-Q3")
QUARANTINE_ROOT = Path("E:/AETF-ModelLab-Q3-quarantine")
OUTPUT_DIR = CLEAN_ROOT / "outputs/reconstructed_artifacts"
OUTPUT_INDEX = OUTPUT_DIR / "reconstructed_artifact_index.json"

SEARCH_DIRS = {
    "docs",
    "outputs",
    "artifacts",
    "runtime",
    "closeout",
    "reports",
    "decision_matrix",
    "data",
    "examples",
    "configs",
}

KEYWORDS = [
    "reconstructed",
    "reconstructed_v1",
    "decision_matrix",
    "closeout",
    "artifact_index",
    "candidate_history",
    "direction_accuracy",
    "majority_direction_accuracy",
    "PAUSED_BY_STOPLINE",
    "PAUSE_RECONSTRUCTED_BRANCH",
]

CONTENT_EXTENSIONS = {
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}

MAX_CONTENT_BYTES = 2_000_000


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def tracked_files(root: Path) -> set[str]:
    if not (root / ".git").exists():
        return set()
    output = run_git(["ls-files"], root)
    return {line.replace("\\", "/") for line in output.splitlines() if line.strip()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for child in root.iterdir():
        if child.name in {".git", ".pytest_cache", "__pycache__"}:
            continue
        if child.is_file():
            files.append(child)
            continue
        if child.name not in SEARCH_DIRS and root == CLEAN_ROOT:
            continue
        if child.name not in SEARCH_DIRS and root == QUARANTINE_ROOT:
            continue
        for path in child.rglob("*"):
            if root == CLEAN_ROOT and OUTPUT_DIR in path.parents:
                continue
            if path.is_file() and ".git" not in path.parts:
                files.append(path)
    return files


def read_text_sample(path: Path, size: int) -> str:
    if path.suffix.lower() not in CONTENT_EXTENSIONS or size > MAX_CONTENT_BYTES:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def keyword_hits(rel_path: str, text: str) -> dict[str, bool]:
    haystack = f"{rel_path}\n{text}".lower()
    return {keyword: keyword.lower() in haystack for keyword in KEYWORDS}


def summarize_content(text: str) -> str:
    if not text:
        return "Content not scanned because the file is binary, too large, or outside text extensions."
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(keyword.lower() in lower for keyword in KEYWORDS):
            selected.append(line[:240])
        if len(selected) >= 3:
            break
    if selected:
        return " | ".join(selected)
    return "Text scanned; no keyword-bearing summary line found."


def audit_workspace(root: Path, name: str) -> list[dict[str, Any]]:
    tracked = tracked_files(root)
    candidates: list[dict[str, Any]] = []
    for path in workspace_files(root):
        try:
            stat = path.stat()
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        text = read_text_sample(path, stat.st_size)
        hits = keyword_hits(rel, text)
        strong_reconstructed_signal = (
            "reconstructed" in rel.lower()
            or "reconstructed_not_true_left_snapshot" in text
            or "reconstructed_v1" in text.lower()
            or "paused_by_stopline" in text.lower()
            or "pause_reconstructed_branch" in text.lower()
            or "reconstructed branch" in text.lower()
        )
        is_reconstructed_related = (
            strong_reconstructed_signal
            or hits["reconstructed_v1"]
            or hits["PAUSED_BY_STOPLINE"]
            or hits["PAUSE_RECONSTRUCTED_BRANCH"]
        )
        is_artifact_like = any(
            marker in rel.lower()
            for marker in ("decision_matrix", "closeout", "artifact_index", "candidate_history")
        )
        if not (is_reconstructed_related or (name == "clean" and is_artifact_like and any(hits.values()))):
            continue

        has_candidate_history = hits["candidate_history"] or "candidate_history" in rel.lower()
        has_decision_matrix = hits["decision_matrix"] or "decision_matrix" in rel.lower()
        has_closeout = hits["closeout"] or "closeout" in rel.lower()
        has_artifact_index = hits["artifact_index"] or "artifact_index" in rel.lower()
        has_metrics = any(
            token in f"{rel}\n{text}".lower()
            for token in ("metrics", "accuracy", "direction_accuracy", "majority_direction_accuracy")
        )
        has_direction_accuracy = hits["direction_accuracy"]
        has_majority_direction_accuracy = hits["majority_direction_accuracy"]

        source_trusted = name == "clean" and rel in tracked
        usable_for_formal = False
        if name == "quarantine":
            trust_note = "quarantine candidate only; requires controlled import, provenance, checksum, and review"
        elif source_trusted:
            trust_note = "clean tracked file; trusted as repository documentation/source, not automatically a runtime artifact"
        else:
            trust_note = "clean untracked/runtime candidate; requires review before formal use"

        candidates.append(
            {
                "path": str(path),
                "relative_path": rel,
                "workspace": name,
                "file_type": path.suffix.lower() or "<none>",
                "tracked": rel in tracked,
                "size_bytes": stat.st_size,
                "modified_time_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "sha256": sha256(path),
                "content_summary": summarize_content(text),
                "contains_candidate_history": has_candidate_history,
                "contains_decision_matrix": has_decision_matrix,
                "contains_closeout": has_closeout,
                "contains_artifact_index": has_artifact_index,
                "contains_metrics": has_metrics,
                "contains_direction_accuracy": has_direction_accuracy,
                "contains_majority_direction_accuracy": has_majority_direction_accuracy,
                "source_trusted": source_trusted,
                "trust_note": trust_note,
                "usable_for_formal_v011_replay": usable_for_formal,
                "keyword_hits": {key: value for key, value in hits.items() if value},
            }
        )
    return sorted(candidates, key=lambda item: (item["workspace"], item["relative_path"]))


def summarize(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [item for item in candidates if item["workspace"] == "clean"]
    quarantine = [item for item in candidates if item["workspace"] == "quarantine"]
    artifact_roots = ("outputs/", "artifacts/", "runtime/", "closeout/", "reports/", "decision_matrix/", "data/")
    clean_runtime_artifacts = [
        item
        for item in clean
        if item["relative_path"].startswith(artifact_roots)
        and not item["relative_path"].startswith("outputs/replay/leftlab_v1_4_d/")
        and "reconstructed_artifacts_missing" not in item["content_summary"]
        and (
            "reconstructed" in item["relative_path"].lower()
            or "reconstructed_v1" in item["content_summary"].lower()
            or "reconstructed_not_true_left_snapshot" in item["content_summary"]
            or "paused_by_stopline" in item["content_summary"].lower()
            or "pause_reconstructed_branch" in item["content_summary"].lower()
        )
        and (
            item["contains_candidate_history"]
            or item["contains_decision_matrix"]
            or item["contains_closeout"]
            or item["contains_artifact_index"]
        )
    ]
    clean_documentation_candidates = [
        item
        for item in clean
        if item["relative_path"].startswith(("docs/", "scripts/", "configs/"))
    ]
    quarantine_runtime_candidates = [
        item
        for item in quarantine
        if item["contains_candidate_history"]
        or item["contains_decision_matrix"]
        or item["contains_closeout"]
        or item["contains_artifact_index"]
    ]
    return {
        "clean_candidate_count": len(clean),
        "clean_documentation_candidate_count": len(clean_documentation_candidates),
        "clean_runtime_artifact_candidate_count": len(clean_runtime_artifacts),
        "quarantine_candidate_count": len(quarantine),
        "quarantine_runtime_artifact_candidate_count": len(quarantine_runtime_candidates),
        "artifact_candidate_count": len(candidates),
        "clean_reconstructed_artifacts_found": bool(clean_runtime_artifacts),
        "quarantine_candidate_artifacts_found": bool(quarantine_runtime_candidates),
        "has_candidate_history": any(item["contains_candidate_history"] for item in candidates),
        "has_decision_matrix": any(item["contains_decision_matrix"] for item in candidates),
        "has_closeout": any(item["contains_closeout"] for item in candidates),
        "has_artifact_index": any(item["contains_artifact_index"] for item in candidates),
        "clean_has_candidate_history": any(item["contains_candidate_history"] for item in clean_runtime_artifacts),
        "clean_has_decision_matrix": any(item["contains_decision_matrix"] for item in clean_runtime_artifacts),
        "clean_has_closeout": any(item["contains_closeout"] for item in clean_runtime_artifacts),
        "clean_has_artifact_index": any(item["contains_artifact_index"] for item in clean_runtime_artifacts),
        "quarantine_has_candidate_history": any(item["contains_candidate_history"] for item in quarantine),
        "quarantine_has_decision_matrix": any(item["contains_decision_matrix"] for item in quarantine),
        "quarantine_has_closeout": any(item["contains_closeout"] for item in quarantine),
        "quarantine_has_artifact_index": any(item["contains_artifact_index"] for item in quarantine),
        "reconstructed_artifacts_status": (
            "CANDIDATE_FOUND_IN_QUARANTINE_REVIEW_REQUIRED"
            if quarantine_runtime_candidates and not clean_runtime_artifacts
            else "MISSING_CONFIRMED"
            if not clean_runtime_artifacts
            else "CLEAN_CANDIDATE_FOUND_RECHECK_REQUIRED"
        ),
        "formal_v011_ready": False,
        "stopline_triggered": True,
        "remaining_stopline_reasons": [
            "reconstructed_artifacts_missing",
            "realized_outcome_fields_missing",
        ],
        "no_training": True,
        "torchrun": False,
        "gpu": False,
        "quarantine_modified": False,
        "runtime_payload_modified": False,
        "not_trading_advice": True,
    }


def main() -> None:
    candidates = audit_workspace(CLEAN_ROOT, "clean")
    if QUARANTINE_ROOT.exists():
        candidates.extend(audit_workspace(QUARANTINE_ROOT, "quarantine"))

    report = {
        "audit_name": "leftlab_v1_4_g_reconstructed_artifacts_audit",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "clean_root": str(CLEAN_ROOT),
        "quarantine_root": str(QUARANTINE_ROOT),
        "quarantine_read_only": True,
        "searched_dirs": sorted(SEARCH_DIRS),
        "keywords": KEYWORDS,
        "summary": summarize(candidates),
        "candidates": candidates,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_INDEX.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = OUTPUT_DIR / "reconstructed_artifact_candidates.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "workspace",
                "relative_path",
                "tracked",
                "size_bytes",
                "sha256",
                "contains_candidate_history",
                "contains_decision_matrix",
                "contains_closeout",
                "contains_artifact_index",
                "contains_metrics",
                "source_trusted",
                "usable_for_formal_v011_replay",
                "trust_note",
            ],
        )
        writer.writeheader()
        for item in candidates:
            writer.writerow({field: item[field] for field in writer.fieldnames})

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
