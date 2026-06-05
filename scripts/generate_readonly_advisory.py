#!/usr/bin/env python3
"""Generate a READ_ONLY model advisory bundle from a production snapshot manifest.

This script is intentionally small-scope:
- does not train models;
- does not run experiments;
- does not connect to production systems;
- does not generate formal actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

SCHEMA_VERSION = "aetf.protocol.bundle.v1"
PROTOCOL_VERSION = "v0.1.0-rc1"
SOURCE_REPO = "AETF-ModelLab-Q3"
TARGET_REPO = "AETF-LeftLab-Q3"
PRODUCTION_REPO = "AETF-LeftLab-Q3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_production_manifest(production_bundle: Path) -> dict:
    manifest_path = production_bundle / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"production bundle manifest not found: {manifest_path}")
    manifest = load_json(manifest_path)
    if manifest.get("bundle_type") != "production_snapshot":
        raise ValueError("input bundle must be a production_snapshot bundle")
    if manifest.get("source_repo") != PRODUCTION_REPO:
        raise ValueError("production snapshot source_repo must be AETF-LeftLab-Q3")
    if manifest.get("target_repo") != SOURCE_REPO:
        raise ValueError("production snapshot target_repo must be AETF-ModelLab-Q3")
    return manifest


def build_advisory_bundle(
    output: Path,
    production_bundle: Path,
    source_commit: str,
    data_date: str | None,
    allow_overwrite: bool,
) -> Path:
    production_manifest = read_production_manifest(production_bundle)
    effective_data_date = data_date or production_manifest["data_date"]
    if output.exists():
        if not allow_overwrite:
            raise FileExistsError(f"output already exists: {output}")
        shutil.rmtree(output)
    payload_path = output / "payload" / "advisory.json"
    advisory = {
        "advisory_id": f"modellab-q3-smoke-{effective_data_date}-{uuid4().hex[:8]}",
        "generated_by": SOURCE_REPO,
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "bundle_type": "model_advisory",
        "advisory_mode": "READ_ONLY",
        "data_date": effective_data_date,
        "summary": "Runtime exchange smoke advisory only. Human promotion gate is required.",
        "final_action_change_allowed": False,
        "contains_live_action": False,
        "contains_secret": False,
        "based_on_production_bundle": {
            "source_repo": production_manifest["source_repo"],
            "source_commit": production_manifest["source_commit"],
            "data_date": production_manifest["data_date"],
        },
        "recommendations": [
            {
                "type": "protocol_smoke",
                "message": "Protocol smoke advisory generated. No production action is requested.",
            }
        ],
        "risk_boundary": {
            "changes_final_action": False,
            "requires_human_promotion_gate": True,
        },
    }
    write_json(payload_path, advisory)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_type": "model_advisory",
        "source_repo": SOURCE_REPO,
        "target_repo": TARGET_REPO,
        "source_commit": source_commit,
        "generated_at": utc_now(),
        "data_date": effective_data_date,
        "contains_secret": False,
        "contains_live_action": False,
        "advisory_mode": "READ_ONLY",
        "final_action_change_allowed": False,
        "based_on_production_bundle": {
            "source_repo": production_manifest["source_repo"],
            "source_commit": production_manifest["source_commit"],
            "data_date": production_manifest["data_date"],
        },
        "files": [
            {
                "path": "payload/advisory.json",
                "sha256": sha256_file(payload_path),
                "role": "advisory_payload",
            }
        ],
    }
    write_json(output / "manifest.json", manifest)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AETF-ModelLab-Q3 READ_ONLY advisory smoke bundle")
    parser.add_argument("--production-bundle", required=True, help="Validated production snapshot bundle directory")
    parser.add_argument("--output", required=True, help="Output advisory bundle directory")
    parser.add_argument("--source-commit", default="2222222222222222222222222222222222222222")
    parser.add_argument("--data-date", default=None)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()
    output = build_advisory_bundle(
        output=Path(args.output),
        production_bundle=Path(args.production_bundle),
        source_commit=args.source_commit,
        data_date=args.data_date,
        allow_overwrite=args.allow_overwrite,
    )
    print(json.dumps({"status": "ok", "bundle_type": "model_advisory", "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
