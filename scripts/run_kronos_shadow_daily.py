#!/usr/bin/env python3
"""V0.4 placeholder: generate daily Kronos shadow features.

Expected after V0.3:
1. Read left candidates from data/input/left_candidates.csv.
2. Read forecast from outputs/kronos_daily_forecast.csv.
3. Write outputs/kronos_shadow_features.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_lab.data_loader import read_csv_if_exists  # noqa: E402
from model_lab.shadow_features import build_shadow_features  # noqa: E402


def main() -> int:
    candidates_path = ROOT / "data" / "input" / "left_candidates.csv"
    forecast_path = ROOT / "outputs" / "kronos_daily_forecast.csv"
    output_path = ROOT / "outputs" / "kronos_shadow_features.csv"

    candidates = read_csv_if_exists(candidates_path)
    forecast = read_csv_if_exists(forecast_path)
    shadow = build_shadow_features(candidates, forecast)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shadow.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
