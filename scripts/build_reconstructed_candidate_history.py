#!/usr/bin/env python3
"""Build a research-only reconstructed candidate history from real kline CSVs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REAL_CANDIDATE_PATH = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history.csv"
RECONSTRUCTED_PATH = ROOT / "data" / "real" / "raw" / "candidates" / "left_candidates_history_RECONSTRUCTED.csv"
RECONSTRUCTED_NOTE = "reconstructed_candidate_history_not_real_left_snapshot"

OUTPUT_COLUMNS = [
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "notes",
]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_kline(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamps", "symbol", "display_name", "close"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")
    out = df.copy()
    out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise")
    out["close"] = pd.to_numeric(out["close"], errors="raise")
    return out.sort_values("timestamps", kind="stable").reset_index(drop=True)


def build_reconstructed_history(
    raw_kline_dir: Path,
    output_path: Path,
    *,
    lookback_days: int = 60,
    top_n: int = 20,
    max_dates: int = 120,
    force: bool = False,
) -> dict[str, Any]:
    if REAL_CANDIDATE_PATH.exists():
        raise FileExistsError(
            "Refusing to build reconstructed history because real left_candidates_history.csv already exists."
        )
    if output_path.name == "left_candidates_history.csv":
        raise ValueError("Reconstructed output cannot overwrite left_candidates_history.csv.")
    if output_path.exists() and not force:
        raise FileExistsError(f"{output_path} already exists. Pass --force to replace the reconstructed file.")

    frames = []
    for path in sorted(raw_kline_dir.glob("*.csv")):
        kline = load_kline(path)
        if len(kline) <= lookback_days:
            continue
        kline["left_score"] = kline["close"].pct_change(lookback_days)
        frames.append(kline[["timestamps", "symbol", "display_name", "left_score"]].dropna())
    if not frames:
        raise ValueError("No eligible kline CSVs are available for reconstructed history.")

    combined = pd.concat(frames, ignore_index=True)
    selected_dates = sorted(combined["timestamps"].drop_duplicates())[-max_dates:]
    rows: list[dict[str, Any]] = []
    for as_of_date in selected_dates:
        daily = combined.loc[combined["timestamps"] == as_of_date].copy()
        daily = daily.sort_values(["left_score", "symbol"], ascending=[False, True], kind="stable").head(top_n)
        for rank, (_, item) in enumerate(daily.iterrows(), start=1):
            rows.append(
                {
                    "as_of_date": as_of_date.strftime("%Y-%m-%d"),
                    "symbol": str(item["symbol"]),
                    "display_name": str(item["display_name"]),
                    "candidate_rank": rank,
                    "left_score": float(item["left_score"]),
                    "notes": RECONSTRUCTED_NOTE,
                }
            )

    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "candidate_history_status": "RECONSTRUCTED_NOT_REAL_LEFT_SNAPSHOT",
        "output_path": output_path.as_posix(),
        "row_count": int(len(output)),
        "candidate_date_count": int(output["as_of_date"].nunique()) if not output.empty else 0,
        "symbol_count": int(output["symbol"].nunique()) if not output.empty else 0,
        "notes": RECONSTRUCTED_NOTE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build research-only reconstructed candidate history. This is not the real left-side history "
            "and cannot be used as true V0.11 left-side replay history."
        )
    )
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument("--output", default=str(RECONSTRUCTED_PATH))
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--max-dates", type=int, default=120)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    print("WARNING: this is not a real left-side historical candidate snapshot.")
    print("WARNING: it is only for research workflow testing and does not satisfy true V0.11 left history replay.")
    result = build_reconstructed_history(
        resolve_project_path(args.raw_kline_dir),
        resolve_project_path(args.output),
        lookback_days=max(1, args.lookback_days),
        top_n=max(1, args.top_n),
        max_dates=max(1, args.max_dates),
        force=bool(args.force),
    )
    print(f"candidate_history_status={result['candidate_history_status']}")
    print(f"output_path={result['output_path']}")
    print(f"candidate_date_count={result['candidate_date_count']}")
    print(f"row_count={result['row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
