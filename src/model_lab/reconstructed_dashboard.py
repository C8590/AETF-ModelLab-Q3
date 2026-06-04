from __future__ import annotations

import json
import math
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


FORBIDDEN_JSON_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)

DEFAULT_TITLE = "AETF ModelLab - Kronos Reconstructed Branch Dashboard V0.13-R"
RECONSTRUCTED_WARNING = (
    "Reconstructed candidate history is not true left history and does not represent "
    "formal V0.11 left-side historical candidate performance."
)
STABILITY_WARNING_NEGATIVE = (
    "FULL_EXPANSION_DID_NOT_CONFIRM_V11R_200_CASE_BASELINE_STABILITY"
)


def load_v12r_outputs(config: dict[str, Any]) -> dict[str, Any]:
    inputs_cfg = config.get("inputs", config)
    paths = {
        "summary_json": _path_from_config(inputs_cfg, "summary_json_path"),
        "metrics_csv": _path_from_config(inputs_cfg, "metrics_path"),
        "predictions_csv": _path_from_config(inputs_cfg, "predictions_path"),
        "by_symbol_csv": _path_from_config(inputs_cfg, "group_by_symbol_path"),
        "by_rank_csv": _path_from_config(inputs_cfg, "group_by_rank_path"),
        "by_month_csv": _path_from_config(inputs_cfg, "group_by_month_path"),
    }
    for label, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    with paths["summary_json"].open("r", encoding="utf-8") as fh:
        summary = json.load(fh)

    return {
        "summary": summary,
        "metrics": _read_csv(paths["metrics_csv"]),
        "predictions": _read_csv(paths["predictions_csv"]),
        "group_by_symbol": _read_csv(paths["by_symbol_csv"]),
        "group_by_candidate_rank": _read_csv(paths["by_rank_csv"]),
        "group_by_month": _read_csv(paths["by_month_csv"]),
        "paths": {key: str(value) for key, value in paths.items()},
    }


def build_reconstructed_diagnostics(inputs: dict[str, Any]) -> dict[str, Any]:
    summary = inputs.get("summary", {})
    direction_accuracy = _to_float(summary.get("direction_accuracy"), default=0.0)
    baseline_accuracy = _to_float(
        summary.get("v11r_baseline_direction_accuracy"),
        default=0.555,
    )
    delta = _to_float(
        summary.get("direction_accuracy_delta_vs_v11r"),
        default=direction_accuracy - baseline_accuracy,
    )
    fail_count = _to_int(summary.get("fail_count"), default=0)
    interpretations: list[str] = []
    if direction_accuracy < 0.5:
        interpretations.append("UNDER_50_PERCENT_DIRECTION_ACCURACY")
    if delta < -0.05:
        interpretations.append("V11R_BASELINE_NOT_STABLE")
    if fail_count == 0:
        interpretations.append("ENGINEERING_PIPELINE_STABLE")
    if not interpretations:
        interpretations.append("NO_MAJOR_DIAGNOSTIC_FLAG")

    stability_warning = (
        STABILITY_WARNING_NEGATIVE
        if delta < -0.05
        else "FULL_EXPANSION_STABILITY_NOT_REJECTED_BY_THRESHOLD"
    )
    diagnostics = {
        "mode": "reconstructed_branch_dashboard",
        "candidate_history_type": str(
            summary.get("candidate_history_type", "reconstructed_not_true_left_snapshot")
        ),
        "evaluated_case_count": _to_int(summary.get("evaluated_case_count"), default=0),
        "success_count": _to_int(summary.get("success_count"), default=0),
        "fail_count": fail_count,
        "direction_accuracy": direction_accuracy,
        "v11r_baseline_direction_accuracy": baseline_accuracy,
        "direction_accuracy_delta_vs_v11r": delta,
        "mean_abs_return_error": _to_float_or_none(summary.get("mean_abs_return_error")),
        "median_abs_return_error": _to_float_or_none(summary.get("median_abs_return_error")),
        "rmse_return_error": _to_float_or_none(summary.get("rmse_return_error")),
        "performance_interpretation": interpretations,
        "stability_warning": stability_warning,
        "formal_v011_ready": False,
        "reconstructed_branch_only": True,
        "zero_shot": bool(summary.get("zero_shot", True)),
        "no_training": True,
        "no_torchrun": True,
        "no_gpu_call": True,
        "no_checkpoint": True,
        "not_trading_advice": True,
        "execution_allowed": False,
        "left_project_writeback_allowed": False,
        "recommended_next_step": (
            "Proceed to V0.14-R reconstructed error diagnostics or stop-line review; "
            "do not enter formal V0.11."
        ),
        "warnings": [
            RECONSTRUCTED_WARNING,
            "V0.12-R full expansion did not confirm the V0.11-R 200-case baseline stability.",
            "Current direction_accuracy=0.4094 does not support any market conclusion.",
            "This is V0.13-R, not formal V0.13.",
        ],
    }
    _validate_json_keys(diagnostics)
    return diagnostics


def build_dashboard_payload(
    inputs: dict[str, Any],
    diagnostics: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    display_cfg = config.get("display", {})
    top_n_symbols = int(display_cfg.get("top_n_symbols", 20))
    top_n_months = int(display_cfg.get("top_n_months", 24))
    payload = {
        "schema_version": "v0.13-r",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": display_cfg.get("title", DEFAULT_TITLE),
        "safety_banner": [
            "Reconstructed branch only",
            "Not formal V0.11",
            "Not true left history",
            "Not trading advice",
            "No order execution",
            "No writeback to left project",
            "No training",
        ],
        "headline_metrics": {
            "candidate_history_type": diagnostics["candidate_history_type"],
            "evaluated_case_count": diagnostics["evaluated_case_count"],
            "success_count": diagnostics["success_count"],
            "fail_count": diagnostics["fail_count"],
            "direction_accuracy": diagnostics["direction_accuracy"],
            "mean_abs_return_error": diagnostics["mean_abs_return_error"],
            "median_abs_return_error": diagnostics["median_abs_return_error"],
            "rmse_return_error": diagnostics["rmse_return_error"],
        },
        "baseline_comparison": {
            "baseline_label": "V0.11-R 200-case baseline",
            "full_expansion_label": "V0.12-R full expansion",
            "baseline_direction_accuracy": diagnostics["v11r_baseline_direction_accuracy"],
            "full_expansion_direction_accuracy": diagnostics["direction_accuracy"],
            "direction_accuracy_delta_vs_v11r": diagnostics[
                "direction_accuracy_delta_vs_v11r"
            ],
            "interpretation": (
                "Full expansion did not confirm the 200-case baseline stability."
            ),
        },
        "group_by_symbol": _records(inputs["group_by_symbol"], limit=top_n_symbols),
        "group_by_candidate_rank": _records(inputs["group_by_candidate_rank"]),
        "group_by_month": _records(inputs["group_by_month"], limit=top_n_months),
        "diagnostics": diagnostics,
        "data_sources": {
            "summary_json": inputs["paths"]["summary_json"],
            "metrics_csv": inputs["paths"]["metrics_csv"],
            "predictions_csv": inputs["paths"]["predictions_csv"],
            "by_symbol_csv": inputs["paths"]["by_symbol_csv"],
            "by_rank_csv": inputs["paths"]["by_rank_csv"],
            "by_month_csv": inputs["paths"]["by_month_csv"],
        },
    }
    payload = _clean_for_json(payload)
    _validate_json_keys(payload)
    return payload


def render_reconstructed_dashboard_html(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title = str(payload.get("title") or DEFAULT_TITLE)
    metrics = payload["headline_metrics"]
    comparison = payload["baseline_comparison"]
    diagnostics = payload["diagnostics"]
    banner_items = "".join(
        f"<li>{escape(str(item))}</li>" for item in payload.get("safety_banner", [])
    )
    symbol_rows = _render_rows(payload.get("group_by_symbol", []))
    rank_rows = _render_rows(payload.get("group_by_candidate_rank", []))
    month_rows = _render_rows(payload.get("group_by_month", []))
    source_rows = _render_rows(
        [{"source": key, "path": value} for key, value in payload.get("data_sources", {}).items()]
    )
    interpretation = ", ".join(diagnostics.get("performance_interpretation", []))
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #20242a;
      --muted: #667085;
      --line: #d5dbe3;
      --paper: #ffffff;
      --band: #f4f6f8;
      --critical: #9f1239;
      --critical-bg: #fff1f2;
      --accent: #155e75;
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
    main {{ padding: 0 32px 34px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    h2 {{ margin: 28px 0 12px; font-size: 17px; }}
    .muted {{ color: var(--muted); }}
    .banner {{
      margin-top: 16px;
      padding: 14px 16px;
      border: 1px solid #fecdd3;
      background: var(--critical-bg);
      color: var(--critical);
      border-radius: 6px;
      font-weight: 700;
    }}
    .banner ul {{ margin: 8px 0 0; padding-left: 20px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fff;
    }}
    .metric strong {{ display: block; margin-top: 5px; font-size: 18px; }}
    .delta strong {{ color: var(--critical); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      background: #fff;
      margin-bottom: 18px;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{ background: var(--band); }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    .note {{ max-width: 980px; color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="muted">Generated at {escape(str(payload.get("generated_at", "")))} · mode: reconstructed_branch_dashboard</div>
    <div class="banner">
      Reconstructed branch only. Not formal V0.11. Not true left history. Not trading advice.
      <ul>{banner_items}</ul>
    </div>
  </header>
  <main>
    <section>
      <h2>Headline Diagnostics</h2>
      <div class="grid">
        <div class="metric">candidate_history_type<strong>{escape(str(metrics["candidate_history_type"]))}</strong></div>
        <div class="metric">evaluated_case_count<strong>{metrics["evaluated_case_count"]}</strong></div>
        <div class="metric">success_count<strong>{metrics["success_count"]}</strong></div>
        <div class="metric">fail_count<strong>{metrics["fail_count"]}</strong></div>
        <div class="metric">direction_accuracy<strong>{_fmt(metrics["direction_accuracy"])}</strong></div>
        <div class="metric">mean_abs_return_error<strong>{_fmt(metrics["mean_abs_return_error"])}</strong></div>
        <div class="metric">rmse_return_error<strong>{_fmt(metrics["rmse_return_error"])}</strong></div>
      </div>
    </section>
    <section>
      <h2>Baseline Comparison</h2>
      <div class="grid">
        <div class="metric">{escape(str(comparison["baseline_label"]))}<strong>{_fmt(comparison["baseline_direction_accuracy"])}</strong></div>
        <div class="metric">{escape(str(comparison["full_expansion_label"]))}<strong>{_fmt(comparison["full_expansion_direction_accuracy"])}</strong></div>
        <div class="metric delta">direction_accuracy_delta_vs_v11r<strong>{_fmt(comparison["direction_accuracy_delta_vs_v11r"])}</strong></div>
      </div>
      <p class="note">Full expansion did not confirm the 200-case baseline stability. V0.12-R direction_accuracy fell from 0.555 to 0.4094, so this reconstructed branch is a cautious diagnostic result, not a formal V0.11 result.</p>
    </section>
    <section>
      <h2>Diagnostics</h2>
      <p class="note">performance_interpretation: {escape(interpretation)}</p>
      <p class="note">stability_warning: {escape(str(diagnostics.get("stability_warning")))}</p>
      <p class="note">formal_v011_ready: false · reconstructed_branch_only: true · no_training: true · no_torchrun: true · no_gpu_call: true</p>
    </section>
    <section>
      <h2>By Symbol</h2>
      {symbol_rows}
    </section>
    <section>
      <h2>By Candidate Rank</h2>
      {rank_rows}
    </section>
    <section>
      <h2>By Month</h2>
      {month_rows}
    </section>
    <section>
      <h2>Data Sources</h2>
      {source_rows}
    </section>
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    safe_data = _clean_for_json(data)
    _validate_json_keys(safe_data)
    output_path.write_text(
        json.dumps(safe_data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _path_from_config(config: dict[str, Any], key: str) -> Path:
    try:
        return Path(str(config[key]))
    except KeyError as exc:
        raise KeyError(f"missing input path config: {key}") from exc


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"input CSV is empty: {path}")
    return df


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    value = df.head(limit) if limit else df
    return [_clean_for_json(row) for row in value.to_dict(orient="records")]


def _render_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class=\"note\">No rows.</p>"
    columns = list(rows[0].keys())
    header = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{escape(_fmt_cell(row.get(column)))}</td>" for column in columns) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


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


def _to_float(value: Any, *, default: float) -> float:
    numeric = _to_float_or_none(value)
    return default if numeric is None else numeric


def _to_int(value: Any, *, default: int) -> int:
    numeric = _to_float_or_none(value)
    return default if numeric is None else int(numeric)


def _fmt(value: Any) -> str:
    numeric = _to_float_or_none(value)
    if numeric is None:
        return "-"
    return f"{numeric:.6g}"


def _fmt_cell(value: Any) -> str:
    numeric = _to_float_or_none(value)
    if numeric is not None:
        return _fmt(numeric)
    value = _clean_scalar(value)
    return "-" if value is None else str(value)


def _validate_json_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_JSON_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"reconstructed dashboard JSON key contains forbidden term: {key}")
            _validate_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_keys(item)
