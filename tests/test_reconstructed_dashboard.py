import importlib
import json

import pandas as pd

from model_lab.reconstructed_dashboard import (
    FORBIDDEN_JSON_KEY_PARTS,
    build_dashboard_payload,
    build_reconstructed_diagnostics,
    load_v12r_outputs,
    render_reconstructed_dashboard_html,
    write_json,
)


def test_load_v12r_outputs_reads_minimal_mock_files(tmp_path):
    paths = _write_mock_inputs(tmp_path)
    config = {"inputs": {key: str(value) for key, value in paths.items()}}

    loaded = load_v12r_outputs(config)

    assert loaded["summary"]["candidate_history_type"] == "reconstructed_not_true_left_snapshot"
    assert len(loaded["group_by_symbol"]) == 1
    assert len(loaded["group_by_candidate_rank"]) == 1
    assert len(loaded["group_by_month"]) == 1


def test_build_reconstructed_diagnostics_flags_under_half_accuracy():
    diagnostics = build_reconstructed_diagnostics(_minimal_inputs(direction_accuracy=0.4094))

    assert "UNDER_50_PERCENT_DIRECTION_ACCURACY" in diagnostics["performance_interpretation"]


def test_build_reconstructed_diagnostics_flags_negative_delta():
    diagnostics = build_reconstructed_diagnostics(
        _minimal_inputs(direction_accuracy=0.49, delta=-0.10)
    )

    assert "V11R_BASELINE_NOT_STABLE" in diagnostics["performance_interpretation"]
    assert diagnostics["stability_warning"] == (
        "FULL_EXPANSION_DID_NOT_CONFIRM_V11R_200_CASE_BASELINE_STABILITY"
    )


def test_build_dashboard_payload_contains_safety_banner_and_branch_flags():
    inputs = _minimal_inputs()
    diagnostics = build_reconstructed_diagnostics(inputs)
    payload = build_dashboard_payload(inputs, diagnostics, _minimal_config())

    assert payload["safety_banner"]
    assert payload["diagnostics"]["formal_v011_ready"] is False
    assert payload["diagnostics"]["reconstructed_branch_only"] is True
    assert_no_forbidden_keys(payload)


def test_render_reconstructed_dashboard_html_generates_static_file(tmp_path):
    inputs = _minimal_inputs()
    diagnostics = build_reconstructed_diagnostics(inputs)
    payload = build_dashboard_payload(inputs, diagnostics, _minimal_config())
    output_path = tmp_path / "dashboard.html"

    render_reconstructed_dashboard_html(payload, output_path)

    html = output_path.read_text(encoding="utf-8")
    assert "AETF ModelLab - Kronos Reconstructed Branch Dashboard V0.13-R" in html
    assert "Not trading advice" in html or "非交易建议" in html
    assert "Full expansion did not confirm the 200-case baseline stability" in html
    assert "cdn" not in html.lower()


def test_write_json_rejects_forbidden_output_keys(tmp_path):
    output_path = tmp_path / "diagnostics.json"
    diagnostics = build_reconstructed_diagnostics(_minimal_inputs())

    write_json(diagnostics, output_path)
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["not_trading_advice"] is True
    assert_no_forbidden_keys(data)


def test_build_reconstructed_dashboard_import_has_no_side_effects():
    module = importlib.import_module("scripts.build_reconstructed_dashboard")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


def _write_mock_inputs(tmp_path):
    summary_path = tmp_path / "summary.json"
    metrics_path = tmp_path / "metrics.csv"
    predictions_path = tmp_path / "predictions.csv"
    by_symbol_path = tmp_path / "by_symbol.csv"
    by_rank_path = tmp_path / "by_rank.csv"
    by_month_path = tmp_path / "by_month.csv"
    summary_path.write_text(json.dumps(_summary()), encoding="utf-8")
    metrics = pd.DataFrame([_metric_row()])
    metrics.to_csv(metrics_path, index=False)
    pd.DataFrame(
        [
            {
                "replay_id": "mock",
                "as_of_date": "2026-01-02",
                "symbol": "510300",
                "direction_match": False,
                "model_status": "PASS",
            }
        ]
    ).to_csv(predictions_path, index=False)
    metrics.assign(symbol="510300").to_csv(by_symbol_path, index=False)
    metrics.assign(candidate_rank=1).to_csv(by_rank_path, index=False)
    metrics.assign(month="2026-01").to_csv(by_month_path, index=False)
    return {
        "summary_json_path": summary_path,
        "metrics_path": metrics_path,
        "predictions_path": predictions_path,
        "group_by_symbol_path": by_symbol_path,
        "group_by_rank_path": by_rank_path,
        "group_by_month_path": by_month_path,
    }


def _minimal_inputs(direction_accuracy=0.4094, delta=-0.1456):
    return {
        "summary": _summary(direction_accuracy=direction_accuracy, delta=delta),
        "metrics": pd.DataFrame([_metric_row(direction_accuracy=direction_accuracy)]),
        "predictions": pd.DataFrame([{"replay_id": "mock", "model_status": "PASS"}]),
        "group_by_symbol": pd.DataFrame([{"symbol": "510300", **_metric_row()}]),
        "group_by_candidate_rank": pd.DataFrame([{"candidate_rank": 1, **_metric_row()}]),
        "group_by_month": pd.DataFrame([{"month": "2026-01", **_metric_row()}]),
        "paths": {
            "summary_json": "summary.json",
            "metrics_csv": "metrics.csv",
            "predictions_csv": "predictions.csv",
            "by_symbol_csv": "by_symbol.csv",
            "by_rank_csv": "by_rank.csv",
            "by_month_csv": "by_month.csv",
        },
    }


def _minimal_config():
    return {
        "display": {
            "title": "AETF ModelLab - Kronos Reconstructed Branch Dashboard V0.13-R",
            "top_n_symbols": 20,
            "top_n_months": 24,
        }
    }


def _summary(direction_accuracy=0.4094, delta=-0.1456):
    return {
        "candidate_history_type": "reconstructed_not_true_left_snapshot",
        "evaluated_case_count": 1341,
        "success_count": 1341,
        "fail_count": 0,
        "direction_accuracy": direction_accuracy,
        "mean_abs_return_error": 0.157,
        "median_abs_return_error": 0.138,
        "rmse_return_error": 0.195,
        "v11r_baseline_direction_accuracy": 0.555,
        "direction_accuracy_delta_vs_v11r": delta,
        "zero_shot": True,
    }


def _metric_row(direction_accuracy=0.4094):
    return {
        "case_count": 1,
        "success_count": 1,
        "fail_count": 0,
        "direction_accuracy": direction_accuracy,
        "mean_abs_return_error": 0.157,
        "median_abs_return_error": 0.138,
        "rmse_return_error": 0.195,
    }


def assert_no_forbidden_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                assert forbidden not in lower, f"{key} contains {forbidden}"
            assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_keys(child)
