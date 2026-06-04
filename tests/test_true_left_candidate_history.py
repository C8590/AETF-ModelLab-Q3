import importlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.aggregate_true_left_candidate_snapshots import (
    FORBIDDEN_FIELD_PARTS,
    REQUIRED_COLUMNS,
    run,
)


def write_config(tmp_path: Path, snapshot_dir: Path) -> Path:
    config = {
        "mode": "true_left_candidate_history_aggregation",
        "inputs": {"snapshot_dir": str(snapshot_dir)},
        "outputs": {
            "aggregated_history_path": str(tmp_path / "left_candidates_history.csv"),
            "aggregation_report_path": str(tmp_path / "report.md"),
            "aggregation_manifest_path": str(tmp_path / "manifest.json"),
        },
        "thresholds": {
            "min_candidate_dates_for_formal_v011": 100,
            "min_replay_cases_for_formal_v011": 200,
        },
        "safety": {
            "allow_reconstructed_as_true_history": False,
            "allow_writeback_to_left_project": False,
            "allow_trading_advice": False,
            "allow_order_execution": False,
        },
    }
    path = tmp_path / "true_left_candidate_history.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def make_snapshot(path: Path, as_of_date: str, symbol: str, rank: int) -> None:
    pd.DataFrame(
        {
            "as_of_date": [as_of_date],
            "symbol": [symbol],
            "display_name": ["ETF"],
            "candidate_rank": [rank],
            "left_score": [0.8],
            "notes": ["true_left_snapshot_export"],
        }
    ).to_csv(path, index=False)


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_FIELD_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)


def test_empty_snapshot_dir_does_not_generate_fake_history(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    config_path = write_config(tmp_path, snapshot_dir)

    result = run(config_path)

    assert result["aggregation_status"] == "SNAPSHOT_DIR_EMPTY"
    assert result["snapshot_count"] == 0
    assert result["row_count"] == 0
    assert result["candidate_date_count"] == 0
    assert not (tmp_path / "left_candidates_history.csv").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "manifest.json").exists()


def test_missing_required_columns_raises(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    pd.DataFrame({"as_of_date": ["2024-01-01"]}).to_csv(snapshot_dir / "2024-01-01_left_candidates.csv", index=False)
    config_path = write_config(tmp_path, snapshot_dir)

    with pytest.raises(ValueError, match="missing required columns"):
        run(config_path)

    assert not (tmp_path / "left_candidates_history.csv").exists()


def test_multiple_snapshots_aggregate_correctly(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    make_snapshot(snapshot_dir / "2024-01-01_left_candidates.csv", "2024-01-01", "510300", 1)
    make_snapshot(snapshot_dir / "2024-01-02_left_candidates.csv", "2024-01-02", "159915", 1)
    config_path = write_config(tmp_path, snapshot_dir)

    result = run(config_path)
    output = pd.read_csv(tmp_path / "left_candidates_history.csv")

    assert result["aggregation_status"] == "TRUE_HISTORY_AGGREGATED"
    assert result["snapshot_count"] == 2
    assert result["row_count"] == 2
    assert result["candidate_date_count"] == 2
    assert output["symbol"].astype(str).tolist() == ["510300", "159915"]


def test_output_columns_are_exact_contract_columns(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    make_snapshot(snapshot_dir / "2024-01-01_left_candidates.csv", "2024-01-01", "510300", 1)
    config_path = write_config(tmp_path, snapshot_dir)

    run(config_path)
    output = pd.read_csv(tmp_path / "left_candidates_history.csv")

    assert list(output.columns) == REQUIRED_COLUMNS


def test_notes_must_not_contain_reconstructed_marker(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    frame = pd.DataFrame(
        {
            "as_of_date": ["2024-01-01"],
            "symbol": ["510300"],
            "display_name": ["ETF"],
            "candidate_rank": [1],
            "left_score": [0.8],
            "notes": ["reconstructed_candidate_history_not_real_left_snapshot"],
        }
    )
    frame.to_csv(snapshot_dir / "2024-01-01_left_candidates.csv", index=False)
    config_path = write_config(tmp_path, snapshot_dir)

    with pytest.raises(ValueError, match="forbidden reconstructed note text"):
        run(config_path)


def test_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.aggregate_true_left_candidate_snapshots")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def test_output_keys_do_not_contain_forbidden_terms(tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    config_path = write_config(tmp_path, snapshot_dir)

    result = run(config_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert_no_forbidden_keys(result)
    assert_no_forbidden_keys(manifest)
