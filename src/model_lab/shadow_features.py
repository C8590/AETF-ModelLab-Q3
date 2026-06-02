from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .validation import KRONOS_FORECAST_REQUIRED


def _nth_value(values: pd.Series, n: int) -> float:
    if len(values) >= n:
        return float(values.iloc[n - 1])
    if len(values) > 0:
        return float(values.iloc[-1])
    return float("nan")


def _safe_div(a: float, b: float) -> float:
    if b == 0 or np.isnan(a) or np.isnan(b):
        return float("nan")
    return float(a / b)


def decide_action(row: pd.Series) -> tuple[str, str, float]:
    risk_level = str(row.get("risk_level", "") or "")
    break_invalid = bool(row.get("kronos_break_invalid_price", False))
    break_recent = bool(row.get("kronos_break_recent_low", False))
    max_dd = float(row.get("kronos_max_pred_drawdown_5d", np.nan))
    ret5 = float(row.get("kronos_pred_return_5d", np.nan))
    rr = float(row.get("kronos_rr", np.nan))

    if risk_level in {"R4", "P0"}:
        return (
            "WAIT",
            "风控等级为 R4/P0，Kronos 只能展示风险提示，不允许提高买入级别。",
            0.0,
        )

    if break_invalid:
        return (
            "RISK_OF_BREAKDOWN",
            "Kronos 预测未来5日低点可能跌破失效价，当前左侧信号应降级为观察。",
            10.0,
        )

    if break_recent:
        return (
            "RISK_OF_BREAKDOWN",
            "Kronos 预测未来5日低点可能跌破近期低点，存在继续破低风险。",
            20.0,
        )

    if not np.isnan(max_dd) and max_dd <= -0.03:
        return (
            "WAIT",
            "Kronos 预测未来5日最大回撤偏大，建议等待风险释放后再观察。",
            35.0,
        )

    if risk_level in {"R2", "R3"} and (not np.isnan(ret5) and ret5 > 0):
        return (
            "WAIT",
            "Kronos 路径略偏修复，但当前风险等级不允许提高到强买入，仅保留观察。",
            50.0,
        )

    if (not np.isnan(ret5) and ret5 >= 0.015) and (not np.isnan(rr) and rr >= 1.5):
        return (
            "SUPPORT_PROBE",
            "Kronos 预测未来5日低点未跌破关键风险价，且收盘路径温和上修，支持小仓试探。",
            75.0,
        )

    if not np.isnan(ret5):
        return (
            "WAIT",
            "Kronos 未给出足够强的修复优势，当前建议等待。",
            45.0,
        )

    return "NO_SIGNAL", "Kronos 预测结果缺失或不足，暂不形成有效影子判断。", 0.0


def build_shadow_features(candidates: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    """Build Kronos shadow features from left candidates and forecast rows.

    This function does not modify left project files. It only returns a DataFrame
    that can be written to outputs/kronos_shadow_features.csv.
    """
    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "trade_date", "code", "name", "close", "kronos_shadow_action", "kronos_explanation",
                "model_name", "run_time",
            ]
        )

    if forecast.empty:
        out = candidates.copy()
        out["kronos_shadow_action"] = "NO_SIGNAL"
        out["kronos_explanation"] = "未找到 Kronos 预测结果，暂不形成有效影子判断。"
        out["model_name"] = pd.NA
        out["run_time"] = pd.NA
        return out

    missing = [c for c in KRONOS_FORECAST_REQUIRED if c not in forecast.columns]
    if missing:
        raise ValueError(f"forecast missing columns: {missing}")

    f = forecast.copy()
    f["trade_date"] = pd.to_datetime(f["trade_date"]).dt.strftime("%Y-%m-%d")
    f["pred_date"] = pd.to_datetime(f["pred_date"])
    f = f.sort_values(["trade_date", "code", "pred_date"])

    rows: list[dict[str, Any]] = []
    for (trade_date, code), g in f.groupby(["trade_date", "code"], dropna=False):
        closes = pd.to_numeric(g["pred_close"], errors="coerce").dropna().reset_index(drop=True)
        lows = pd.to_numeric(g["pred_low"], errors="coerce").dropna().reset_index(drop=True)
        highs = pd.to_numeric(g["pred_high"], errors="coerce").dropna().reset_index(drop=True)
        rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                "kronos_pred_close_3d": _nth_value(closes, 3),
                "kronos_pred_close_5d": _nth_value(closes, 5),
                "kronos_pred_close_10d": _nth_value(closes, 10),
                "kronos_pred_low_5d": float(lows.head(5).min()) if len(lows) else np.nan,
                "kronos_pred_high_5d": float(highs.head(5).max()) if len(highs) else np.nan,
                "model_name": g.get("model_name", pd.Series([pd.NA])).iloc[0],
                "run_time": g.get("run_time", pd.Series([pd.NA])).iloc[0],
            }
        )
    agg = pd.DataFrame(rows)

    c = candidates.copy()
    c["trade_date"] = pd.to_datetime(c["trade_date"]).dt.strftime("%Y-%m-%d")
    merged = c.merge(agg, on=["trade_date", "code"], how="left")

    close = pd.to_numeric(merged["close"], errors="coerce")
    for horizon in [3, 5, 10]:
        col = f"kronos_pred_close_{horizon}d"
        merged[f"kronos_pred_return_{horizon}d"] = pd.to_numeric(merged[col], errors="coerce") / close - 1.0

    pred_low_5d = pd.to_numeric(merged["kronos_pred_low_5d"], errors="coerce")
    pred_high_5d = pd.to_numeric(merged["kronos_pred_high_5d"], errors="coerce")
    merged["kronos_max_pred_drawdown_5d"] = pred_low_5d / close - 1.0

    if "recent_low" in merged.columns:
        recent_low = pd.to_numeric(merged["recent_low"], errors="coerce")
        merged["kronos_break_recent_low"] = pred_low_5d < recent_low
    else:
        merged["kronos_break_recent_low"] = False

    if "invalid_price" in merged.columns:
        invalid_price = pd.to_numeric(merged["invalid_price"], errors="coerce")
        merged["kronos_break_invalid_price"] = pred_low_5d < invalid_price
    else:
        merged["kronos_break_invalid_price"] = False

    merged["kronos_expected_upside"] = pred_high_5d / close - 1.0
    merged["kronos_expected_downside"] = pred_low_5d / close - 1.0
    merged["kronos_rr"] = merged.apply(
        lambda r: _safe_div(float(r.get("kronos_expected_upside", np.nan)), abs(float(r.get("kronos_expected_downside", np.nan)))),
        axis=1,
    )

    decisions = merged.apply(decide_action, axis=1, result_type="expand")
    merged["kronos_shadow_action"] = decisions[0]
    merged["kronos_explanation"] = decisions[1]
    merged["kronos_shadow_score"] = decisions[2]

    preferred = [
        "trade_date", "code", "name", "close",
        "kronos_pred_close_3d", "kronos_pred_close_5d", "kronos_pred_close_10d",
        "kronos_pred_return_3d", "kronos_pred_return_5d", "kronos_pred_return_10d",
        "kronos_pred_low_5d", "kronos_pred_high_5d", "kronos_max_pred_drawdown_5d",
        "kronos_break_recent_low", "kronos_break_invalid_price",
        "kronos_expected_upside", "kronos_expected_downside", "kronos_rr",
        "kronos_shadow_score", "kronos_shadow_action", "kronos_explanation",
        "model_name", "run_time",
    ]
    for col in preferred:
        if col not in merged.columns:
            merged[col] = pd.NA
    other_cols = [c for c in merged.columns if c not in preferred]
    return merged[preferred + other_cols]
