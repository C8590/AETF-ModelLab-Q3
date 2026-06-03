#!/usr/bin/env python3
"""Optional Tushare ETF daily kline fallback for V0.10.2-C."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIN_BARS = 1000
TUSHARE_TOKEN_MISSING = "TUSHARE_TOKEN_MISSING"
TUSHARE_SOURCE_NAME = "tushare.fund_daily"

KLINE_COLUMNS = [
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


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def ts_code(symbol: str, market: str) -> str:
    market_value = str(market).strip().upper()
    if market_value == "SH":
        return f"{str(symbol).strip()}.SH"
    if market_value == "SZ":
        return f"{str(symbol).strip()}.SZ"
    raise ValueError(f"Unsupported ETF market for Tushare: {market}")


def safe_error_message(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def load_universe(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    etfs = config.get("etfs")
    if not isinstance(etfs, list) or not etfs:
        raise ValueError("configs/real_etf_universe.yaml must contain a non-empty etfs list.")
    return config


def build_token_missing_manifest(config_path: Path, manifest_path: Path, report_path: Path) -> dict[str, Any]:
    manifest = {
        "mode": "real_etf_kline_download",
        "version": "V0.10.2-C",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_path.as_posix(),
        "source_name": TUSHARE_SOURCE_NAME,
        "status": TUSHARE_TOKEN_MISSING,
        "enabled": False,
        "success_count": 0,
        "fail_count": 0,
        "failed_count": 0,
        "etfs": [],
        "manifest_path": manifest_path.as_posix(),
        "report_path": report_path.as_posix(),
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    write_json(manifest, manifest_path)
    write_report(report_path, manifest)
    return manifest


def normalize_tushare_frame(raw_df: pd.DataFrame, etf: dict[str, Any], download: dict[str, Any]) -> pd.DataFrame:
    column_map = {
        "trade_date": "timestamps",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "vol": "volume",
        "amount": "amount",
    }
    missing = [column for column in column_map if column not in raw_df.columns]
    if missing:
        raise ValueError(f"Tushare result missing expected columns: {missing}")
    if raw_df.empty:
        raise ValueError("Tushare returned zero rows.")
    out = raw_df.rename(columns=column_map).copy()
    out = out[list(column_map.values())]
    out["timestamps"] = pd.to_datetime(out["timestamps"], format="%Y%m%d", errors="raise").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        out[column] = pd.to_numeric(out[column], errors="raise")
    out["symbol"] = str(etf["symbol"]).strip()
    out["display_name"] = str(etf.get("display_name", "")).strip()
    out["market"] = str(etf.get("market", "")).strip()
    out["frequency"] = str(download.get("frequency", "daily")).strip()
    out["price_adjustment"] = str(download.get("price_adjustment", "qfq")).strip()
    out["source_name"] = TUSHARE_SOURCE_NAME
    out["source_note"] = (
        f"tushare_optional_fallback; downloaded_at={datetime.now().isoformat(timespec='seconds')}; "
        f"start_date={download['start_date']}; end_date={download['end_date']}; token_redacted=true"
    )
    return out[KLINE_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        encoded = encoded.replace(token, "[REDACTED]")
    output_path.write_text(encoded + "\n", encoding="utf-8")


def write_report(report_path: Path, manifest: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Kronos V0.10.2-C Tushare ETF Kline Optional Fallback Report",
        "",
        f"- 运行时间: {manifest['generated_at']}",
        f"- 数据源: {manifest['source_name']}",
        f"- 状态: {manifest['status']}",
        f"- 是否启用: {manifest['enabled']}",
        f"- 成功数量: {manifest['success_count']}",
        f"- 失败数量: {manifest['fail_count']}",
        "",
        "## Scope",
        "",
        "- 仅在 TUSHARE_TOKEN 存在时启用。",
        "- 未把 token 写入日志或报告。",
        "- 未训练模型。",
        "- 未运行 torchrun。",
        "- 未调用 GPU 推理。",
        "- 未接入或回写主项目。",
        "- 未生成交易建议。",
    ]
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def download(
    config_path: Path,
    raw_kline_dir: Path,
    manifest_path: Path,
    report_path: Path,
    min_bars: int,
    target_symbols: set[str] | None = None,
) -> dict[str, Any]:
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        return build_token_missing_manifest(config_path, manifest_path, report_path)

    try:
        import tushare as ts
    except ImportError as exc:
        raise RuntimeError("tushare is not installed in the current Python environment.") from exc

    config = load_universe(config_path)
    download_config = config.get("download", {})
    raw_kline_dir.mkdir(parents=True, exist_ok=True)
    pro = ts.pro_api(token)

    rows: list[dict[str, Any]] = []
    for etf in config["etfs"]:
        symbol = str(etf["symbol"]).strip()
        if target_symbols is not None and symbol not in target_symbols:
            continue
        raw_path = raw_kline_dir / f"{symbol}.csv"
        row = {
            "symbol": symbol,
            "display_name": str(etf.get("display_name", "")).strip(),
            "market": str(etf.get("market", "")).strip(),
            "status": "FAIL",
            "bar_count": 0,
            "start_date": "",
            "end_date": "",
            "raw_path": "",
            "attempts": 1,
            "acquisition": "",
            "error_message": "",
        }
        try:
            existing = pd.read_csv(raw_path) if raw_path.exists() else pd.DataFrame()
            if len(existing) >= min_bars and set(KLINE_COLUMNS).issubset(existing.columns):
                row.update(
                    {
                        "status": "SKIPPED_EXISTING",
                        "bar_count": int(len(existing)),
                        "start_date": str(existing["timestamps"].iloc[0]),
                        "end_date": str(existing["timestamps"].iloc[-1]),
                        "raw_path": raw_path.as_posix(),
                        "acquisition": "existing_standardized_raw_csv",
                    }
                )
                rows.append(row)
                continue
            raw_df = pro.fund_daily(
                ts_code=ts_code(symbol, str(etf.get("market", ""))),
                start_date=str(download_config["start_date"]),
                end_date=str(download_config["end_date"]),
            )
            normalized = normalize_tushare_frame(raw_df, etf, download_config)
            normalized.to_csv(raw_path, index=False, encoding="utf-8-sig")
            row.update(
                {
                    "status": "DOWNLOADED",
                    "bar_count": int(len(normalized)),
                    "start_date": str(normalized["timestamps"].iloc[0]),
                    "end_date": str(normalized["timestamps"].iloc[-1]),
                    "raw_path": raw_path.as_posix(),
                    "acquisition": "downloaded",
                }
            )
        except Exception as exc:  # noqa: BLE001
            row["error_message"] = safe_error_message(exc)
        rows.append(row)

    success_count = sum(1 for row in rows if row["status"] == "DOWNLOADED")
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    manifest = {
        "mode": "real_etf_kline_download",
        "version": "V0.10.2-C",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_path.as_posix(),
        "source_name": TUSHARE_SOURCE_NAME,
        "status": "PASS",
        "enabled": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "failed_count": fail_count,
        "min_bars": min_bars,
        "target_symbols": sorted(target_symbols) if target_symbols is not None else [],
        "etfs": rows,
        "manifest_path": manifest_path.as_posix(),
        "report_path": report_path.as_posix(),
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    write_json(manifest, manifest_path)
    write_report(report_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optionally download V0.10.2-C ETF kline data from Tushare.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "real_etf_universe.yaml"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "outputs" / "real_data" / "kronos_v10_tushare_download_manifest.json"),
    )
    parser.add_argument("--report", default=str(ROOT / "docs" / "kronos_v10_tushare_download_report.md"))
    parser.add_argument("--min-bars", type=int, default=DEFAULT_MIN_BARS)
    parser.add_argument("--symbols", nargs="*", default=None, help="Optional symbol allow-list.")
    args = parser.parse_args(argv)

    manifest = download(
        resolve_project_path(args.config),
        resolve_project_path(args.raw_kline_dir),
        resolve_project_path(args.manifest),
        resolve_project_path(args.report),
        max(1, args.min_bars),
        set(args.symbols) if args.symbols else None,
    )
    print(
        "tushare_download_summary "
        f"status={manifest['status']} "
        f"enabled={manifest['enabled']} "
        f"success_count={manifest['success_count']} "
        f"fail_count={manifest['fail_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
