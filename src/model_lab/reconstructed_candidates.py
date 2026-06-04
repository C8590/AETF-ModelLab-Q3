from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


RECONSTRUCTED_NOTE = "reconstructed_candidate_history_not_real_left_snapshot"
RECONSTRUCTED_TYPE = "reconstructed_not_true_left_snapshot"

KLINE_REQUIRED_COLUMNS = [
    "timestamps",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "symbol",
    "display_name",
]

CANDIDATE_COLUMNS = [
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "notes",
]

REPLAY_CASE_COLUMNS = [
    "replay_id",
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "kline_path",
    "notes",
]

FORBIDDEN_FIELD_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


@dataclass(frozen=True)
class ReconstructedCandidateConfig:
    candidate_top_n: int = 5
    min_symbols_per_date: int = 10
    min_candidate_dates: int = 100
    min_replay_cases: int = 200
    lookback_for_replay: int = 120
    pred_len_for_replay: int = 24
    momentum_short: int = 20
    momentum_mid: int = 60
    volatility: int = 20
    liquidity: int = 20
    max_candidate_dates: int | None = 300


def load_normalized_klines(normalized_kline_dir: Path) -> dict[str, pd.DataFrame]:
    if not normalized_kline_dir.exists():
        raise FileNotFoundError(f"normalized kline dir does not exist: {normalized_kline_dir}")

    klines: dict[str, pd.DataFrame] = {}
    for path in sorted(normalized_kline_dir.glob("*.csv")):
        df = pd.read_csv(path)
        missing = [column for column in KLINE_REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            raise ValueError(f"{path} missing required normalized kline columns: {missing}")
        out = df.copy()
        out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise")
        for column in ["open", "high", "low", "close", "volume", "amount"]:
            out[column] = pd.to_numeric(out[column], errors="raise")
        out["symbol"] = out["symbol"].fillna("").astype(str).str.strip()
        out["display_name"] = out["display_name"].fillna("").astype(str).str.strip()
        out = out.sort_values("timestamps", kind="stable").reset_index(drop=True)
        symbol = str(out["symbol"].iloc[0]).strip()
        if not symbol:
            raise ValueError(f"{path} contains an empty symbol.")
        klines[symbol] = out
    return klines


def compute_past_only_features(kline_df: pd.DataFrame, config: ReconstructedCandidateConfig) -> pd.DataFrame:
    out = kline_df.copy().sort_values("timestamps", kind="stable").reset_index(drop=True)
    out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise")
    out["close"] = pd.to_numeric(out["close"], errors="raise")
    out["amount"] = pd.to_numeric(out["amount"], errors="raise")
    out["momentum_20"] = out["close"] / out["close"].shift(config.momentum_short) - 1.0
    out["momentum_60"] = out["close"] / out["close"].shift(config.momentum_mid) - 1.0
    out["volatility_20"] = out["close"].pct_change().rolling(config.volatility).std()
    out["liquidity_20"] = out["amount"].rolling(config.liquidity).mean()
    return out


def build_reconstructed_candidate_history(
    klines: dict[str, pd.DataFrame],
    config: ReconstructedCandidateConfig,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for symbol, kline in sorted(klines.items()):
        featured = compute_past_only_features(kline, config)
        display_name = str(featured["display_name"].dropna().astype(str).iloc[0]) if not featured.empty else ""
        frame = featured[
            [
                "timestamps",
                "symbol",
                "display_name",
                "momentum_20",
                "momentum_60",
                "volatility_20",
                "liquidity_20",
            ]
        ].copy()
        frame["symbol"] = symbol
        frame["display_name"] = frame["display_name"].fillna(display_name).astype(str)
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS)

    combined = pd.concat(frames, ignore_index=True).dropna(
        subset=["momentum_20", "momentum_60", "volatility_20", "liquidity_20"]
    )
    if combined.empty:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS)

    all_dates = sorted(combined["timestamps"].drop_duplicates())
    if config.max_candidate_dates is not None:
        all_dates = all_dates[-max(1, int(config.max_candidate_dates)) :]

    rows: list[dict[str, Any]] = []
    for as_of_date in all_dates:
        daily = combined.loc[combined["timestamps"] == as_of_date].copy()
        if len(daily) < config.min_symbols_per_date:
            continue

        daily["left_score"] = (
            daily["momentum_20"].rank(pct=True, method="average") * 0.4
            + daily["momentum_60"].rank(pct=True, method="average") * 0.3
            + daily["liquidity_20"].rank(pct=True, method="average") * 0.2
            - daily["volatility_20"].rank(pct=True, method="average") * 0.1
        )
        daily = daily.sort_values(["left_score", "symbol"], ascending=[False, True], kind="stable").head(
            config.candidate_top_n
        )
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

    return pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)


def build_reconstructed_replay_cases(
    reconstructed_df: pd.DataFrame,
    normalized_kline_dir: Path,
    config: ReconstructedCandidateConfig,
) -> pd.DataFrame:
    kline_cache = load_normalized_klines(normalized_kline_dir)
    rows: list[dict[str, Any]] = []
    for item in reconstructed_df.itertuples(index=False):
        symbol = str(item.symbol)
        kline = kline_cache.get(symbol)
        if kline is None:
            continue
        dates = pd.to_datetime(kline["timestamps"], errors="raise").reset_index(drop=True)
        as_of_date = pd.to_datetime(item.as_of_date, errors="raise")
        matches = dates[dates == as_of_date]
        if matches.empty:
            continue
        position = int(matches.index[-1])
        if position < config.lookback_for_replay:
            continue
        if len(kline) - position - 1 < config.pred_len_for_replay:
            continue
        rows.append(
            {
                "replay_id": f"{as_of_date.strftime('%Y-%m-%d')}_{symbol}_RECONSTRUCTED",
                "as_of_date": as_of_date.strftime("%Y-%m-%d"),
                "symbol": symbol,
                "display_name": str(item.display_name),
                "candidate_rank": int(item.candidate_rank),
                "left_score": float(item.left_score),
                "kline_path": (normalized_kline_dir / f"{symbol}.csv").as_posix(),
                "notes": RECONSTRUCTED_NOTE,
            }
        )
    return pd.DataFrame(rows, columns=REPLAY_CASE_COLUMNS)


def evaluate_reconstructed_readiness(
    reconstructed_df: pd.DataFrame,
    replay_cases_df: pd.DataFrame,
    config: ReconstructedCandidateConfig,
) -> dict[str, Any]:
    candidate_date_count = int(reconstructed_df["as_of_date"].nunique()) if not reconstructed_df.empty else 0
    row_count = int(len(reconstructed_df))
    symbol_count = int(reconstructed_df["symbol"].nunique()) if not reconstructed_df.empty else 0
    replay_case_count = int(len(replay_cases_df))
    reasons: list[str] = []
    warnings: list[str] = [
        "Reconstructed candidate history is not true left-side historical snapshot data.",
        "This output cannot be used for formal V0.11 true left history replay.",
    ]
    if candidate_date_count < config.min_candidate_dates:
        reasons.append(
            f"candidate_date_count {candidate_date_count} is below min_candidate_dates {config.min_candidate_dates}."
        )
    if replay_case_count < config.min_replay_cases:
        reasons.append(f"replay_case_count {replay_case_count} is below min_replay_cases {config.min_replay_cases}.")

    ready = not reasons
    readiness = {
        "mode": "reconstructed_candidate_history_only",
        "candidate_history_type": RECONSTRUCTED_TYPE,
        "candidate_date_count": candidate_date_count,
        "row_count": row_count,
        "symbol_count": symbol_count,
        "replay_case_count": replay_case_count,
        "is_ready_for_reconstructed_replay": ready,
        "is_true_left_history": False,
        "can_enter_formal_v011": False,
        "can_enter_v011_reconstructed": ready,
        "prevent_lookahead_bias": True,
        "reasons": reasons,
        "warnings": warnings,
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    assert_no_forbidden_fields(readiness)
    return readiness


def assert_no_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            for forbidden in FORBIDDEN_FIELD_PARTS:
                if forbidden in lower:
                    raise ValueError(f"output field contains forbidden term: {key}")
            assert_no_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_fields(child)


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
