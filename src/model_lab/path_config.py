from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelLabPaths:
    root: Path
    config_path: Path
    left_candidates: Path
    watchlist: Path
    positions: Path
    etf_daily_k: Path
    risk_warning: Path
    sector_map: Path
    daily_forecast: Path
    shadow_features: Path
    shadow_report: Path


def _resolve(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def load_paths(config_path: str | Path | None = None) -> ModelLabPaths:
    root = Path(__file__).resolve().parents[2]
    cfg_path = Path(config_path) if config_path else root / "configs" / "model_lab.yaml"
    cfg = load_yaml(cfg_path)
    io = cfg.get("io", {})
    return ModelLabPaths(
        root=root,
        config_path=cfg_path,
        left_candidates=_resolve(root, io.get("left_candidates", "data/input/left_candidates.csv")),
        watchlist=_resolve(root, io.get("watchlist", "data/input/watchlist.csv")),
        positions=_resolve(root, io.get("positions", "data/input/positions.csv")),
        etf_daily_k=_resolve(root, io.get("etf_daily_k", "data/input/etf_daily_k.csv")),
        risk_warning=_resolve(root, io.get("risk_warning", "data/input/risk_warning.csv")),
        sector_map=_resolve(root, io.get("sector_map", "data/input/sector_map.csv")),
        daily_forecast=_resolve(root, io.get("daily_forecast", "outputs/kronos_daily_forecast.csv")),
        shadow_features=_resolve(root, io.get("shadow_features", "outputs/kronos_shadow_features.csv")),
        shadow_report=_resolve(root, io.get("shadow_report", "outputs/kronos_shadow_report.md")),
    )
