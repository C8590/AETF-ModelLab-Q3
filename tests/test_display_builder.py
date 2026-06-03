import importlib
import json

import pandas as pd
import pytest

from model_lab.display_builder import (
    FORBIDDEN_JSON_KEY_PARTS,
    build_display_payload,
    classify_observation_level,
    classify_prediction_direction,
    payload_to_safe_dict,
    render_dashboard_html,
    write_display_json,
)


def test_classify_prediction_direction():
    assert classify_prediction_direction(0.02) == "UP"
    assert classify_prediction_direction(-0.02) == "DOWN"
    assert classify_prediction_direction(0.0005) == "FLAT"
    assert classify_prediction_direction(None) == "UNKNOWN"


def test_classify_observation_level():
    assert classify_observation_level(0.02, 0.01, "PASS") == "NORMAL"
    assert classify_observation_level(0.02, 0.08, "PASS") == "HIGH_VOLATILITY"
    assert classify_observation_level(0.08, 0.01, "PASS") == "WIDE_RANGE"
    assert classify_observation_level(0.02, 0.01, "FAIL") == "MODEL_FAILED"
    assert classify_observation_level(None, None, "PENDING") == "UNKNOWN"


def test_build_display_payload_from_minimal_inputs_preserves_metrics():
    shadow_df = pd.DataFrame(
        [
            {
                "as_of_date": "2026-06-03",
                "candidate_rank": 1,
                "code": "510300",
                "name": "沪深300ETF",
                "model_status": "PASS",
                "pred_return_last": -0.02,
                "pred_return_min": -0.03,
                "pred_return_max": 0.01,
                "pred_path_std": 0.02,
            }
        ]
    )
    metrics = {
        "case_count": 4,
        "success_count": 4,
        "fail_count": 0,
        "direction_accuracy": 0.0,
        "mean_abs_return_error": 0.06164694589146491,
        "median_abs_return_error": 0.062378,
        "rmse_return_error": 0.065148,
    }

    payload = build_display_payload(shadow_df, metrics)

    assert payload.summary["card_count"] == 1
    assert payload.summary["pass_count"] == 1
    assert payload.summary["fail_count"] == 0
    assert payload.replay_metrics.case_count == 4
    assert payload.replay_metrics.sample_warning
    assert payload.replay_metrics.direction_accuracy == 0.0
    assert payload.cards[0].symbol == "510300"
    assert payload.cards[0].prediction_direction_label == "DOWN"


def test_write_display_json_top_level_and_key_safety(tmp_path):
    shadow_df = pd.DataFrame(
        [
            {
                "as_of_date": "2026-06-03",
                "candidate_rank": 1,
                "code": "510300",
                "name": "沪深300ETF",
                "model_status": "PASS",
                "pred_return_last": 0.0,
                "pred_return_min": -0.01,
                "pred_return_max": 0.01,
                "pred_path_std": 0.01,
            }
        ]
    )
    payload = build_display_payload(shadow_df, {"case_count": 1, "direction_accuracy": 0.0})
    output_path = tmp_path / "display.json"

    write_display_json(payload, output_path)
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert set(data) == {
        "schema_version",
        "generated_at",
        "safety",
        "summary",
        "replay_metrics",
        "cards",
    }
    assert data["safety"]["execution_allowed"] is False
    assert data["safety"]["is_trading_advice"] is False
    assert_no_forbidden_keys(data)


def test_render_dashboard_html_generates_static_file(tmp_path):
    shadow_df = pd.DataFrame(
        [
            {
                "as_of_date": "2026-06-03",
                "candidate_rank": 1,
                "code": "510300",
                "name": "沪深300ETF",
                "model_status": "PASS",
                "pred_return_last": 0.002,
                "pred_return_min": -0.01,
                "pred_return_max": 0.02,
                "pred_path_std": 0.01,
            }
        ]
    )
    payload = build_display_payload(shadow_df, {"case_count": 4, "direction_accuracy": 0.0})
    output_path = tmp_path / "dashboard.html"

    render_dashboard_html(payload, output_path)

    html = output_path.read_text(encoding="utf-8")
    assert "AETF ModelLab - Kronos Shadow Display V0.6" in html
    assert "非交易建议" in html or "Not trading advice" in html
    assert "cdn" not in html.lower()


def test_payload_to_safe_dict_omits_forbidden_safety_key():
    payload = build_display_payload(
        pd.DataFrame(
            [
                {
                    "as_of_date": "2026-06-03",
                    "candidate_rank": 1,
                    "code": "510300",
                    "name": "沪深300ETF",
                    "model_status": "FAIL",
                    "error_message": "demo error",
                }
            ]
        ),
        {"case_count": 0},
    )

    data = payload_to_safe_dict(payload)

    assert "allow_order_execution" not in data["safety"]
    assert_no_forbidden_keys(data)


def test_build_shadow_dashboard_import_has_no_side_effects():
    module = importlib.import_module("scripts.build_shadow_dashboard")

    assert hasattr(module, "run")
    assert hasattr(module, "main")


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
