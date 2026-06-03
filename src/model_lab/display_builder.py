from __future__ import annotations

import json
import math
from dataclasses import asdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from .display_schema import (
    DisplaySafetyBanner,
    ReplayMetricSummary,
    ShadowDisplayCard,
    ShadowDisplayPayload,
)


FORBIDDEN_JSON_KEY_PARTS = (
    "buy",
    "sell",
    "position",
    "target_price",
    "stop_loss",
    "order",
    "trade",
    "signal",
    "recommendation",
)

SMALL_SAMPLE_WARNING = "样本过小，仅验证工程链路，不代表真实市场预测能力。"


def load_shadow_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"shadow predictions file not found: {path}")
    return pd.read_csv(path)


def load_replay_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"replay metrics file not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        return {}
    return {key: _clean_scalar(value) for key, value in df.iloc[0].to_dict().items()}


def classify_prediction_direction(pred_return_last: float | None, flat_threshold: float = 0.001) -> str:
    value = _to_float_or_none(pred_return_last)
    if value is None:
        return "UNKNOWN"
    if abs(value) <= flat_threshold:
        return "FLAT"
    return "UP" if value > 0 else "DOWN"


def classify_observation_level(
    pred_range_pct: float | None,
    pred_close_volatility: float | None,
    model_status: str,
) -> str:
    status = (model_status or "").upper()
    if status == "FAIL":
        return "MODEL_FAILED"
    if status != "PASS":
        return "UNKNOWN"

    range_value = _to_float_or_none(pred_range_pct)
    volatility_value = _to_float_or_none(pred_close_volatility)
    if range_value is None and volatility_value is None:
        return "UNKNOWN"
    if volatility_value is not None and volatility_value >= 0.05:
        return "HIGH_VOLATILITY"
    if range_value is not None and range_value >= 0.05:
        return "WIDE_RANGE"
    return "NORMAL"


def build_display_payload(
    shadow_predictions_df: pd.DataFrame,
    replay_metrics: dict[str, Any],
    *,
    schema_version: str = "v0.6",
    flat_threshold: float = 0.001,
    small_sample_threshold: int = 30,
    data_sources: dict[str, str] | None = None,
) -> ShadowDisplayPayload:
    cards = [
        _row_to_display_card(row, flat_threshold=flat_threshold)
        for _, row in shadow_predictions_df.iterrows()
    ]
    pass_count = sum(1 for card in cards if card.model_status == "PASS")
    fail_count = sum(1 for card in cards if card.model_status == "FAIL")
    case_count = _to_int(replay_metrics.get("case_count"), default=0)

    sample_warning = SMALL_SAMPLE_WARNING if case_count < small_sample_threshold else ""
    replay_summary = ReplayMetricSummary(
        case_count=case_count,
        success_count=_to_int(replay_metrics.get("success_count"), default=0),
        fail_count=_to_int(replay_metrics.get("fail_count"), default=0),
        direction_accuracy=_to_float_or_none(replay_metrics.get("direction_accuracy")),
        mean_abs_return_error=_to_float_or_none(replay_metrics.get("mean_abs_return_error")),
        median_abs_return_error=_to_float_or_none(replay_metrics.get("median_abs_return_error")),
        rmse_return_error=_to_float_or_none(replay_metrics.get("rmse_return_error")),
        sample_warning=sample_warning,
    )

    summary = {
        "card_count": len(cards),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "mode": "shadow_display_only",
        "data_sources": data_sources or {},
    }
    return ShadowDisplayPayload(
        schema_version=schema_version,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        safety=DisplaySafetyBanner(),
        summary=summary,
        replay_metrics=replay_summary,
        cards=cards,
    )


def write_display_json(payload: ShadowDisplayPayload, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload_dict = payload_to_safe_dict(payload)
    _validate_json_keys(payload_dict)
    output_path.write_text(
        json.dumps(payload_dict, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def render_dashboard_html(payload: ShadowDisplayPayload, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = payload_to_safe_dict(payload)
    metrics = data["replay_metrics"]
    summary = data["summary"]
    cards = data["cards"]
    sources = summary.get("data_sources", {})

    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(card['symbol']))}</td>"
        f"<td>{escape(str(card['display_name']))}</td>"
        f"<td>{escape(str(card['as_of_date']))}</td>"
        f"<td>{escape(str(card['candidate_rank']))}</td>"
        f"<td>{_fmt(card['left_score'])}</td>"
        f"<td>{escape(str(card['model_status']))}</td>"
        f"<td>{escape(str(card['prediction_direction_label']))}</td>"
        f"<td>{_fmt_pct(card['pred_return_last'])}</td>"
        f"<td>{_fmt_pct(card['pred_range_pct'])}</td>"
        f"<td>{_fmt(card['pred_close_volatility'])}</td>"
        f"<td>{escape(str(card['observation_level']))}</td>"
        f"<td>{escape(str(card['notes']))}</td>"
        "</tr>"
        for card in cards
    )
    source_rows = "\n".join(
        f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>"
        for key, value in sources.items()
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AETF ModelLab - Kronos Shadow Display V0.6</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1b1f23;
      --muted: #5f6b7a;
      --line: #d8dee6;
      --paper: #ffffff;
      --band: #f5f7fa;
      --accent: #0f766e;
      --warn: #8a4b00;
      --warn-bg: #fff7e6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font: 14px/1.55 "Segoe UI", Arial, sans-serif;
    }}
    header {{
      padding: 24px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--band);
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 700; }}
    h2 {{ margin: 28px 0 12px; font-size: 17px; }}
    main {{ padding: 0 32px 32px; }}
    .muted {{ color: var(--muted); }}
    .banner {{
      margin-top: 16px;
      padding: 12px 14px;
      border: 1px solid #f0cf87;
      background: var(--warn-bg);
      color: var(--warn);
      border-radius: 6px;
      font-weight: 600;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fff;
    }}
    .metric strong {{ display: block; font-size: 18px; margin-top: 4px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      background: #fff;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{ background: var(--band); font-weight: 700; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    .note {{ max-width: 900px; color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>AETF ModelLab - Kronos Shadow Display V0.6</h1>
    <div class="muted">Generated at {escape(payload.generated_at)} · mode: shadow_display_only</div>
    <div class="banner">只读 AI 影子观察 · 非交易建议 · 不下单 · 不回写主项目 · 当前 synthetic/demo 样本不代表真实市场预测能力</div>
  </header>
  <main>
    <section>
      <h2>Replay Metrics</h2>
      <div class="summary-grid">
        <div class="metric">case_count<strong>{metrics['case_count']}</strong></div>
        <div class="metric">success_count<strong>{metrics['success_count']}</strong></div>
        <div class="metric">fail_count<strong>{metrics['fail_count']}</strong></div>
        <div class="metric">direction_accuracy<strong>{_fmt(metrics['direction_accuracy'])}</strong></div>
        <div class="metric">mean_abs_return_error<strong>{_fmt(metrics['mean_abs_return_error'])}</strong></div>
        <div class="metric">rmse_return_error<strong>{_fmt(metrics['rmse_return_error'])}</strong></div>
      </div>
      <p class="note">{escape(metrics.get('sample_warning') or 'No sample warning.')}</p>
    </section>
    <section>
      <h2>Shadow Cards</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th><th>Display Name</th><th>As Of</th><th>Rank</th><th>Left Score</th>
            <th>Model Status</th><th>Direction Label</th><th>Pred Return Last</th>
            <th>Pred Range</th><th>Pred Volatility</th><th>Observation Level</th><th>Notes</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Data Sources</h2>
      <table>
        <thead><tr><th>Source</th><th>Path</th></tr></thead>
        <tbody>{source_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Safety</h2>
      <p class="note">AI shadow observations only. Not trading advice. This static page is read-only and does not connect to the left-side project.</p>
    </section>
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def payload_to_safe_dict(payload: ShadowDisplayPayload) -> dict[str, Any]:
    return {
        "schema_version": payload.schema_version,
        "generated_at": payload.generated_at,
        "safety": {
            "mode": payload.safety.mode,
            "is_trading_advice": payload.safety.is_trading_advice,
            "execution_allowed": payload.safety.allow_order_execution,
            "writeback_to_left_project_allowed": payload.safety.allow_writeback_to_left_project,
            "disclaimer": payload.safety.disclaimer,
        },
        "summary": _clean_for_json(payload.summary),
        "replay_metrics": _clean_for_json(asdict(payload.replay_metrics)),
        "cards": [_clean_for_json(asdict(card)) for card in payload.cards],
    }


def _row_to_display_card(row: pd.Series, *, flat_threshold: float) -> ShadowDisplayCard:
    status = str(row.get("model_status", "UNKNOWN") or "UNKNOWN").upper()
    pred_return_last = _to_float_or_none(row.get("pred_return_last"))
    pred_range_pct = _prediction_range(row)
    pred_close_volatility = _to_float_or_none(row.get("pred_path_std", row.get("pred_close_volatility")))
    notes = ""
    error_message = _clean_scalar(row.get("error_message"))
    if status == "FAIL" and error_message:
        notes = str(error_message)
    return ShadowDisplayCard(
        symbol=str(row.get("symbol", row.get("code", ""))),
        display_name=str(row.get("display_name", row.get("name", ""))),
        as_of_date=str(row.get("as_of_date", "")),
        candidate_rank=_to_int(row.get("candidate_rank"), default=0),
        left_score=_to_float_or_none(row.get("left_score")),
        model_status=status,
        prediction_direction_label=classify_prediction_direction(pred_return_last, flat_threshold),
        pred_return_last=pred_return_last,
        pred_range_pct=pred_range_pct,
        pred_close_volatility=pred_close_volatility,
        observation_level=classify_observation_level(pred_range_pct, pred_close_volatility, status),
        notes=notes,
    )


def _prediction_range(row: pd.Series) -> float | None:
    explicit = _to_float_or_none(row.get("pred_range_pct"))
    if explicit is not None:
        return explicit
    pred_min = _to_float_or_none(row.get("pred_return_min"))
    pred_max = _to_float_or_none(row.get("pred_return_max"))
    if pred_min is None or pred_max is None:
        return None
    return float(pred_max - pred_min)


def _clean_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_json(item) for item in value]
    return _clean_scalar(value)


def _clean_scalar(value: Any) -> Any:
    if value is pd.NA:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return value
    return value


def _to_float_or_none(value: Any) -> float | None:
    value = _clean_scalar(value)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _to_int(value: Any, *, default: int) -> int:
    numeric = _to_float_or_none(value)
    return default if numeric is None else int(numeric)


def _fmt(value: Any) -> str:
    numeric = _to_float_or_none(value)
    if numeric is None:
        return "-"
    return f"{numeric:.6g}"


def _fmt_pct(value: Any) -> str:
    numeric = _to_float_or_none(value)
    if numeric is None:
        return "-"
    return f"{numeric:.2%}"


def _validate_json_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"display JSON key contains forbidden term: {key}")
            _validate_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_keys(item)
