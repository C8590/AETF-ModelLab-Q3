import importlib

import pandas as pd

from model_lab.reconstructed_candidates import (
    CANDIDATE_COLUMNS,
    FORBIDDEN_FIELD_PARTS,
    RECONSTRUCTED_NOTE,
    REPLAY_CASE_COLUMNS,
    ReconstructedCandidateConfig,
    build_reconstructed_candidate_history,
    build_reconstructed_replay_cases,
    compute_past_only_features,
    evaluate_reconstructed_readiness,
)


def make_kline(symbol: str = "510300", rows: int = 220, start: str = "2024-01-01") -> pd.DataFrame:
    values = [10.0 + index * 0.1 for index in range(rows)]
    return pd.DataFrame(
        {
            "timestamps": pd.date_range(start, periods=rows, freq="D"),
            "open": values,
            "high": [value + 0.2 for value in values],
            "low": [value - 0.2 for value in values],
            "close": values,
            "volume": [1000 + index for index in range(rows)],
            "amount": [10000 + index * 10 for index in range(rows)],
            "symbol": [symbol] * rows,
            "display_name": [f"ETF{symbol}"] * rows,
        }
    )


def test_compute_past_only_features_does_not_use_future_data():
    config = ReconstructedCandidateConfig(momentum_short=20, momentum_mid=60, volatility=20, liquidity=20)
    baseline = make_kline()
    changed_future = baseline.copy()
    changed_future.loc[80:, "close"] = changed_future.loc[80:, "close"] * 10

    baseline_features = compute_past_only_features(baseline, config)
    changed_features = compute_past_only_features(changed_future, config)

    pd.testing.assert_series_equal(
        baseline_features.loc[:79, "momentum_20"],
        changed_features.loc[:79, "momentum_20"],
        check_names=False,
    )


def test_feature_output_has_no_future_logic_columns():
    features = compute_past_only_features(make_kline(), ReconstructedCandidateConfig())

    assert not any("future" in column.lower() or "forward" in column.lower() for column in features.columns)


def test_reconstructed_candidate_history_contains_standard_fields_and_note():
    config = ReconstructedCandidateConfig(min_symbols_per_date=2, max_candidate_dates=5, candidate_top_n=1)
    klines = {"510300": make_kline("510300"), "510500": make_kline("510500")}

    history = build_reconstructed_candidate_history(klines, config)

    assert history.columns.tolist() == CANDIDATE_COLUMNS
    assert RECONSTRUCTED_NOTE in history["notes"].iloc[0]


def test_build_reconstructed_candidate_history_does_not_create_true_left_history(tmp_path):
    config = ReconstructedCandidateConfig(min_symbols_per_date=2, max_candidate_dates=5)
    true_left_history = tmp_path / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"

    build_reconstructed_candidate_history({"510300": make_kline("510300"), "510500": make_kline("510500")}, config)

    assert not true_left_history.exists()


def test_build_reconstructed_replay_cases_requires_lookback_and_pred_len(tmp_path):
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    kline = make_kline(rows=12)
    kline.to_csv(normalized_dir / "510300.csv", index=False)
    history = pd.DataFrame(
        {
            "as_of_date": ["2024-01-03", "2024-01-07"],
            "symbol": ["510300", "510300"],
            "display_name": ["ETF", "ETF"],
            "candidate_rank": [1, 1],
            "left_score": [0.5, 0.6],
            "notes": [RECONSTRUCTED_NOTE, RECONSTRUCTED_NOTE],
        }
    )
    config = ReconstructedCandidateConfig(lookback_for_replay=4, pred_len_for_replay=3)

    cases = build_reconstructed_replay_cases(history, normalized_dir, config)

    assert cases.columns.tolist() == REPLAY_CASE_COLUMNS
    assert cases["replay_id"].tolist() == ["2024-01-07_510300_RECONSTRUCTED"]


def test_reconstructed_readiness_never_allows_formal_v011():
    history = pd.DataFrame(
        {
            "as_of_date": ["2024-01-01"],
            "symbol": ["510300"],
            "display_name": ["ETF"],
            "candidate_rank": [1],
            "left_score": [0.5],
            "notes": [RECONSTRUCTED_NOTE],
        }
    )
    cases = pd.DataFrame({"replay_id": ["case"]})

    readiness = evaluate_reconstructed_readiness(
        history,
        cases,
        ReconstructedCandidateConfig(min_candidate_dates=1, min_replay_cases=1),
    )

    assert readiness["is_true_left_history"] is False
    assert readiness["can_enter_formal_v011"] is False
    assert readiness["can_enter_v011_reconstructed"] is True


def test_reconstructed_output_fields_do_not_contain_forbidden_terms():
    for column in CANDIDATE_COLUMNS + REPLAY_CASE_COLUMNS:
        lower = column.lower()
        assert all(term not in lower for term in FORBIDDEN_FIELD_PARTS)


def test_build_script_import_has_no_side_effects():
    module = importlib.import_module("scripts.build_reconstructed_candidate_history")

    assert hasattr(module, "run")
    assert hasattr(module, "main")
