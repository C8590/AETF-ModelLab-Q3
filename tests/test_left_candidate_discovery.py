import importlib
import json

import pandas as pd

from model_lab.left_candidate_discovery import (
    FORBIDDEN_OUTPUT_FIELD_PARTS,
    LeftCandidateDiscoveryConfig,
    discover_left_project_paths,
    export_left_candidate_history,
    normalize_candidate_history_df,
    scan_candidate_history_files,
    validate_normalized_candidate_history,
)


def test_discover_left_project_paths_filters_missing_paths(tmp_path):
    existing = tmp_path / "AETF-LeftLab"
    missing = tmp_path / "missing"
    existing.mkdir()

    assert discover_left_project_paths([missing, existing]) == [existing]


def test_scan_candidate_history_files_detects_path_keywords(tmp_path):
    left_root = tmp_path / "left"
    source_dir = left_root / "daily_candidate_snapshot"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "rank_history.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "code": ["510300"],
            "name": ["ETF"],
            "rank": [1],
            "score": [0.8],
        }
    ).to_csv(source_path, index=False)

    inventory = scan_candidate_history_files([left_root], LeftCandidateDiscoveryConfig())

    assert len(inventory) == 1
    assert inventory[0]["is_candidate_history_like"] is True
    assert {"candidate", "snapshot", "rank", "history"}.issubset(set(inventory[0]["path_keyword_matches"]))


def test_normalize_candidate_history_df_maps_synonyms(tmp_path):
    source = tmp_path / "candidate_snapshot.csv"
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "code": ["510300.SH"],
            "name": ["沪深300ETF"],
            "rank": ["1"],
            "score": ["0.91"],
        }
    )

    normalized = normalize_candidate_history_df(df, source)

    assert normalized.columns.tolist() == list(LeftCandidateDiscoveryConfig().required_output_columns)
    assert normalized["as_of_date"].iloc[0] == "2024-01-01"
    assert normalized["symbol"].iloc[0] == "510300"
    assert normalized["candidate_rank"].iloc[0] == 1
    assert normalized["left_score"].iloc[0] == 0.91
    assert "candidate_history_type=true_left_snapshot" in normalized["notes"].iloc[0]


def test_validate_normalized_candidate_history_reports_bad_date_and_symbol():
    df = pd.DataFrame(
        {
            "as_of_date": ["bad-date"],
            "symbol": [""],
            "display_name": ["ETF"],
            "candidate_rank": ["x"],
            "left_score": [None],
            "notes": ["unit"],
        }
    )

    errors = validate_normalized_candidate_history(df, {"510300"})

    assert any("as_of_date" in error for error in errors)
    assert any("symbol" in error for error in errors)
    assert any("candidate_rank" in error for error in errors)


def test_export_left_candidate_history_writes_standard_fields(tmp_path):
    output_path = tmp_path / "left_candidates_history.csv"
    df = pd.DataFrame(
        {
            "as_of_date": ["2024-01-01"],
            "symbol": ["510300"],
            "display_name": ["ETF"],
            "candidate_rank": [1],
            "left_score": [0.8],
            "notes": ["source_path=test;candidate_history_type=true_left_snapshot"],
        }
    )

    export_left_candidate_history(df, output_path)
    exported = pd.read_csv(output_path)

    assert exported.columns.tolist() == list(LeftCandidateDiscoveryConfig().required_output_columns)


def test_discovery_script_import_has_no_scan_side_effects():
    module = importlib.import_module("scripts.discover_left_candidate_history")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def test_output_fields_do_not_contain_forbidden_terms():
    for column in LeftCandidateDiscoveryConfig().required_output_columns:
        lower = column.lower()
        assert all(term not in lower for term in FORBIDDEN_OUTPUT_FIELD_PARTS)


def test_inventory_keys_do_not_contain_forbidden_terms(tmp_path):
    left_root = tmp_path / "left"
    left_root.mkdir()
    (left_root / "candidate_snapshot.txt").write_text("candidate score rank snapshot", encoding="utf-8")

    inventory = scan_candidate_history_files([left_root], LeftCandidateDiscoveryConfig())

    assert_no_forbidden_keys(json.loads(json.dumps({"files": inventory})))


def test_discovery_run_does_not_write_left_project_path(tmp_path):
    module = importlib.import_module("scripts.discover_left_candidate_history")
    left_root = tmp_path / "AETF-LeftLab"
    left_root.mkdir()
    before = {path.as_posix() for path in left_root.rglob("*")}

    module.run(
        inventory_path=tmp_path / "inventory.json",
        report_path=tmp_path / "report.md",
        output_path=tmp_path / "left_candidates_history.csv",
        raw_kline_dir=tmp_path / "kline",
        candidate_roots=[left_root],
    )
    after = {path.as_posix() for path in left_root.rglob("*")}

    assert before == after


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_OUTPUT_FIELD_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)
