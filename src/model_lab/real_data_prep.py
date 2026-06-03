from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


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
    "market",
    "frequency",
    "price_adjustment",
    "source_name",
    "source_note",
]

CANDIDATE_REQUIRED_COLUMNS = [
    "as_of_date",
    "symbol",
    "display_name",
    "candidate_rank",
    "left_score",
    "notes",
]

FORBIDDEN_RESULT_KEY_PARTS = (
    "buy",
    "sell",
    "order",
    "trade",
    "signal",
    "recommendation",
)


@dataclass
class RealDataPrepConfig:
    min_symbols: int = 20
    min_bars_per_symbol: int = 1000
    min_replay_cases: int = 200
    min_history_days: int = 1000
    min_candidate_dates: int = 100
    max_missing_rate: float = 0.01
    max_duplicate_timestamp_count: int = 0
    lookback: int = 120
    pred_len: int = 24
    max_cases: int | None = 500


def discover_raw_kline_files(raw_kline_dir: Path) -> list[Path]:
    if not raw_kline_dir.exists():
        return []
    return sorted(path for path in raw_kline_dir.glob("*.csv") if path.is_file())


def validate_raw_kline_schema(df: pd.DataFrame, path: Path) -> list[str]:
    errors: list[str] = []
    missing = [column for column in KLINE_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        errors.append(f"{path}: missing columns: {missing}")
        return errors

    timestamps = pd.to_datetime(df["timestamps"], errors="coerce")
    if timestamps.isna().any():
        errors.append(f"{path}: timestamps contains unparsable values.")

    for column in ["open", "high", "low", "close", "volume", "amount"]:
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.isna().any():
            errors.append(f"{path}: {column} contains non-numeric or missing values.")
        if column in ["open", "high", "low", "close"] and (numeric <= 0).any():
            errors.append(f"{path}: {column} must be positive.")
        if column in ["volume", "amount"] and (numeric < 0).any():
            errors.append(f"{path}: {column} must be non-negative.")

    open_ = pd.to_numeric(df["open"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")
    if (high < pd.concat([open_, close], axis=1).max(axis=1)).any():
        errors.append(f"{path}: high must be greater than or equal to max(open, close).")
    if (low > pd.concat([open_, close], axis=1).min(axis=1)).any():
        errors.append(f"{path}: low must be less than or equal to min(open, close).")

    if df["symbol"].astype(str).str.strip().eq("").any():
        errors.append(f"{path}: symbol must be non-empty.")

    price_adjustments = df["price_adjustment"].dropna().astype(str).str.strip().str.lower().unique()
    if len(price_adjustments) != 1:
        errors.append(f"{path}: price_adjustment must be present and uniform within one file.")

    return errors


def normalize_kline_df(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    errors = validate_raw_kline_schema(df, path)
    if errors:
        raise ValueError("; ".join(errors))

    out = df.copy().drop_duplicates().reset_index(drop=True)
    out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise")
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        out[column] = pd.to_numeric(out[column], errors="raise")
    for column in [
        "symbol",
        "display_name",
        "market",
        "frequency",
        "price_adjustment",
        "source_name",
        "source_note",
    ]:
        out[column] = out[column].fillna("").astype(str).str.strip()
    out = out[KLINE_REQUIRED_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)
    out["timestamps"] = out["timestamps"].dt.strftime("%Y-%m-%d")
    return out


def profile_kline_df(df: pd.DataFrame, path: Path) -> dict[str, Any]:
    errors: list[str] = []
    working = df.copy()
    if "timestamps" in working.columns:
        working["timestamps"] = pd.to_datetime(working["timestamps"], errors="coerce")
    schema_errors = validate_raw_kline_schema(working, path)
    errors.extend(schema_errors)

    symbol = _first_value(working, "symbol")
    display_name = _first_value(working, "display_name")
    timestamps = working.get("timestamps", pd.Series(dtype="datetime64[ns]"))
    duplicate_count = int(timestamps.duplicated().sum()) if len(timestamps) else 0
    if len(working) and all(column in working.columns for column in KLINE_REQUIRED_COLUMNS):
        missing_rate = float(
            working[KLINE_REQUIRED_COLUMNS].isna().sum().sum() / (len(working) * len(KLINE_REQUIRED_COLUMNS))
        )
    else:
        missing_rate = 1.0
    if duplicate_count > 0:
        errors.append(f"{path}: duplicate timestamps: {duplicate_count}")

    profile = {
        "symbol": symbol,
        "display_name": display_name,
        "start_date": _date_or_empty(timestamps.min()) if len(timestamps) else "",
        "end_date": _date_or_empty(timestamps.max()) if len(timestamps) else "",
        "bar_count": int(len(working)),
        "missing_rate": missing_rate,
        "duplicate_timestamp_count": duplicate_count,
        "price_adjustment": _first_value(working, "price_adjustment"),
        "frequency": _first_value(working, "frequency"),
        "source_name": _first_value(working, "source_name"),
        "status": "PASS" if not errors else "FAIL",
        "errors": " | ".join(errors),
    }
    _validate_result_keys(profile)
    return profile


def load_candidate_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=CANDIDATE_REQUIRED_COLUMNS)
    df = pd.read_csv(path)
    errors = validate_candidate_history(df)
    if errors:
        raise ValueError("; ".join(errors))
    out = df.copy()
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="raise").dt.strftime("%Y-%m-%d")
    out["symbol"] = out["symbol"].astype(str).str.strip()
    out["display_name"] = out["display_name"].fillna("").astype(str).str.strip()
    out["candidate_rank"] = pd.to_numeric(out["candidate_rank"], errors="raise").astype(int)
    out["left_score"] = pd.to_numeric(out["left_score"], errors="coerce")
    out["notes"] = out["notes"].fillna("").astype(str)
    return out.sort_values(["as_of_date", "candidate_rank"], kind="stable").reset_index(drop=True)


def validate_candidate_history(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    missing = [column for column in CANDIDATE_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        return [f"candidate history missing columns: {missing}"]
    dates = pd.to_datetime(df["as_of_date"], errors="coerce")
    if dates.isna().any():
        errors.append("candidate history as_of_date contains unparsable values.")
    if df["symbol"].astype(str).str.strip().eq("").any():
        errors.append("candidate history symbol must be non-empty.")
    ranks = pd.to_numeric(df["candidate_rank"], errors="coerce")
    if ranks.isna().any() or (ranks <= 0).any():
        errors.append("candidate history candidate_rank must be positive numeric values.")
    pd.to_numeric(df["left_score"], errors="coerce")
    return errors


def build_expanded_replay_cases(
    candidate_history_df: pd.DataFrame,
    kline_profile_df: pd.DataFrame,
    normalized_kline_dir: Path,
    config: RealDataPrepConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if candidate_history_df.empty or kline_profile_df.empty:
        return _empty_replay_cases()

    valid_symbols = set(
        kline_profile_df.loc[kline_profile_df["status"].astype(str) == "PASS", "symbol"].astype(str)
    )
    kline_cache: dict[str, pd.DataFrame] = {}
    for _, candidate in candidate_history_df.iterrows():
        symbol = str(candidate["symbol"]).strip()
        if symbol not in valid_symbols:
            continue
        kline_path = normalized_kline_dir / f"{_safe_file_stem(symbol)}.csv"
        if not kline_path.exists():
            continue
        if symbol not in kline_cache:
            kline = pd.read_csv(kline_path)
            kline["timestamps"] = pd.to_datetime(kline["timestamps"])
            kline_cache[symbol] = kline.sort_values("timestamps", kind="stable").reset_index(drop=True)
        kline = kline_cache[symbol]
        as_of = pd.to_datetime(candidate["as_of_date"])
        history_count = int((kline["timestamps"] <= as_of).sum())
        future_count = int((kline["timestamps"] > as_of).sum())
        if history_count < config.lookback or future_count < config.pred_len:
            continue
        replay_id = f"{as_of.strftime('%Y-%m-%d')}_{symbol}"
        rows.append(
            {
                "replay_id": replay_id,
                "as_of_date": as_of.strftime("%Y-%m-%d"),
                "symbol": symbol,
                "display_name": candidate.get("display_name", ""),
                "candidate_rank": int(candidate["candidate_rank"]),
                "left_score": candidate.get("left_score", pd.NA),
                "kline_path": kline_path.as_posix(),
                "notes": candidate.get("notes", ""),
            }
        )
        if config.max_cases is not None and len(rows) >= config.max_cases:
            break
    return pd.DataFrame(rows, columns=_empty_replay_cases().columns)


def evaluate_real_data_readiness(
    kline_profile_df: pd.DataFrame,
    replay_cases_df: pd.DataFrame,
    candidate_history_df: pd.DataFrame | None,
    config: RealDataPrepConfig,
) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    symbol_count = int(kline_profile_df["symbol"].dropna().astype(str).nunique()) if not kline_profile_df.empty else 0
    if kline_profile_df.empty or symbol_count == 0:
        data_status = "KLINE_DATA_MISSING"
        reasons.append("No real ETF kline CSV files were found.")
    elif candidate_history_df is None or candidate_history_df.empty:
        data_status = "CANDIDATE_HISTORY_MISSING"
        reasons.append("Real candidate history CSV is missing.")
    else:
        data_status = "DATA_READY"
    if candidate_history_df is None or candidate_history_df.empty:
        candidate_reason = "Real candidate history CSV is missing."
        if candidate_reason not in reasons:
            reasons.append(candidate_reason)

    qualified_mask = _qualified_profile_mask(kline_profile_df, config)
    qualified_symbol_count = int(kline_profile_df.loc[qualified_mask, "symbol"].astype(str).nunique()) if not kline_profile_df.empty else 0
    candidate_date_count = (
        int(pd.to_datetime(candidate_history_df["as_of_date"]).dt.strftime("%Y-%m-%d").nunique())
        if candidate_history_df is not None and not candidate_history_df.empty
        else 0
    )
    replay_case_count = int(len(replay_cases_df))
    max_missing_rate_observed = (
        float(pd.to_numeric(kline_profile_df["missing_rate"], errors="coerce").max())
        if not kline_profile_df.empty
        else None
    )

    if symbol_count and symbol_count < config.min_symbols:
        reasons.append(f"symbol_count {symbol_count} is below min_symbols {config.min_symbols}.")
    if qualified_symbol_count < config.min_symbols:
        reasons.append(
            f"qualified_symbol_count {qualified_symbol_count} is below min_symbols {config.min_symbols}."
        )
    if candidate_history_df is not None and not candidate_history_df.empty and candidate_date_count < config.min_candidate_dates:
        reasons.append(
            f"candidate_date_count {candidate_date_count} is below min_candidate_dates {config.min_candidate_dates}."
        )
    if replay_case_count < config.min_replay_cases:
        reasons.append(f"replay_case_count {replay_case_count} is below min_replay_cases {config.min_replay_cases}.")
    if not kline_profile_df.empty and (kline_profile_df["status"].astype(str) == "FAIL").any():
        data_status = "QUALITY_CHECK_FAILED"
        reasons.append("At least one kline file failed quality checks.")

    is_ready = data_status == "DATA_READY" and not reasons
    if not is_ready and data_status == "DATA_READY":
        data_status = "DATA_NOT_READY"
    if max_missing_rate_observed is not None and max_missing_rate_observed > config.max_missing_rate:
        warnings.append(
            f"max_missing_rate_observed {max_missing_rate_observed:.6f} exceeds {config.max_missing_rate}."
        )

    next_step = (
        "Proceed to V0.11 real-data zero-shot replay evaluation."
        if is_ready
        else "Import sufficient real ETF kline CSVs and real candidate history CSV, then rerun V0.10."
    )
    readiness = {
        "mode": "real_etf_data_preparation",
        "data_status": data_status,
        "symbol_count": symbol_count,
        "qualified_symbol_count": qualified_symbol_count,
        "candidate_date_count": candidate_date_count,
        "replay_case_count": replay_case_count,
        "min_bars_per_symbol": config.min_bars_per_symbol,
        "max_missing_rate_observed": max_missing_rate_observed,
        "is_ready_for_expanded_replay": is_ready,
        "reasons": reasons,
        "warnings": warnings,
        "next_step": next_step,
    }
    _validate_result_keys(readiness)
    return readiness


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _validate_result_keys(data)
    output_path.write_text(
        json.dumps(_clean_for_json(data), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def config_from_dict(config: dict[str, Any]) -> RealDataPrepConfig:
    thresholds = config.get("thresholds", {})
    replay = config.get("replay", {})
    max_cases = replay.get("max_cases", 500)
    return RealDataPrepConfig(
        min_symbols=int(thresholds.get("min_symbols", 20)),
        min_bars_per_symbol=int(thresholds.get("min_bars_per_symbol", 1000)),
        min_replay_cases=int(thresholds.get("min_replay_cases", 200)),
        min_history_days=int(thresholds.get("min_history_days", 1000)),
        min_candidate_dates=int(thresholds.get("min_candidate_dates", 100)),
        max_missing_rate=float(thresholds.get("max_missing_rate", 0.01)),
        max_duplicate_timestamp_count=int(thresholds.get("max_duplicate_timestamp_count", 0)),
        lookback=int(replay.get("lookback", 120)),
        pred_len=int(replay.get("pred_len", 24)),
        max_cases=None if max_cases is None else int(max_cases),
    )


def normalized_kline_path(normalized_kline_dir: Path, symbol: str) -> Path:
    return normalized_kline_dir / f"{_safe_file_stem(symbol)}.csv"


def _qualified_profile_mask(kline_profile_df: pd.DataFrame, config: RealDataPrepConfig) -> pd.Series:
    if kline_profile_df.empty:
        return pd.Series(dtype=bool)
    return (
        (kline_profile_df["status"].astype(str) == "PASS")
        & (pd.to_numeric(kline_profile_df["bar_count"], errors="coerce") >= config.min_bars_per_symbol)
        & (pd.to_numeric(kline_profile_df["missing_rate"], errors="coerce") <= config.max_missing_rate)
        & (
            pd.to_numeric(kline_profile_df["duplicate_timestamp_count"], errors="coerce")
            <= config.max_duplicate_timestamp_count
        )
    )


def _empty_replay_cases() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "replay_id",
            "as_of_date",
            "symbol",
            "display_name",
            "candidate_rank",
            "left_score",
            "kline_path",
            "notes",
        ]
    )


def _safe_file_stem(symbol: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in str(symbol).strip())


def _first_value(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns or df.empty:
        return ""
    values = df[column].dropna().astype(str).str.strip()
    return "" if values.empty else values.iloc[0]


def _date_or_empty(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def _clean_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_json(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if value is pd.NA:
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


def _validate_result_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            for forbidden in FORBIDDEN_RESULT_KEY_PARTS:
                if forbidden in lower_key:
                    raise ValueError(f"real data result key contains forbidden term: {key}")
            _validate_result_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_result_keys(item)
