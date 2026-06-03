from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DisplaySafetyBanner:
    mode: str = "shadow_display_only"
    is_trading_advice: bool = False
    allow_order_execution: bool = False
    allow_writeback_to_left_project: bool = False
    disclaimer: str = "AI shadow observations only. Not trading advice."


@dataclass
class ShadowDisplayCard:
    symbol: str
    display_name: str
    as_of_date: str
    candidate_rank: int
    left_score: float | None
    model_status: str
    prediction_direction_label: str
    pred_return_last: float | None
    pred_range_pct: float | None
    pred_close_volatility: float | None
    observation_level: str
    notes: str = ""


@dataclass
class ReplayMetricSummary:
    case_count: int
    success_count: int
    fail_count: int
    direction_accuracy: float | None
    mean_abs_return_error: float | None
    median_abs_return_error: float | None = None
    rmse_return_error: float | None = None
    sample_warning: str = ""


@dataclass
class ShadowDisplayPayload:
    schema_version: str
    generated_at: str
    safety: DisplaySafetyBanner
    summary: dict[str, Any]
    replay_metrics: ReplayMetricSummary
    cards: list[ShadowDisplayCard] = field(default_factory=list)
