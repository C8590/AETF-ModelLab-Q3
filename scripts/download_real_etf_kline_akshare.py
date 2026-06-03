#!/usr/bin/env python3
"""Download real A-share ETF daily kline data from AkShare for V0.10.2-A."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

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

AKSHARE_COLUMN_MAP = {
    "日期": "timestamps",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "amount",
}


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_universe(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    if not isinstance(config.get("etfs"), list) or not config["etfs"]:
        raise ValueError("configs/real_etf_universe.yaml must contain a non-empty etfs list.")
    download = config.get("download", {})
    if download.get("adjust") != "qfq" or download.get("price_adjustment") != "qfq":
        raise ValueError("V0.10.2-A requires uniform qfq adjustment.")
    if download.get("source_name") != "akshare.fund_etf_hist_em":
        raise ValueError("V0.10.2-A downloader is scoped to akshare.fund_etf_hist_em.")
    return config


def normalize_akshare_frame(raw_df: pd.DataFrame, etf: dict[str, Any], download: dict[str, Any]) -> pd.DataFrame:
    missing_source_columns = [column for column in AKSHARE_COLUMN_MAP if column not in raw_df.columns]
    if missing_source_columns:
        raise ValueError(f"AkShare result missing expected columns: {missing_source_columns}")
    if raw_df.empty:
        raise ValueError("AkShare returned zero rows.")

    out = raw_df.rename(columns=AKSHARE_COLUMN_MAP).copy()
    out = out[list(AKSHARE_COLUMN_MAP.values())]
    out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        out[column] = pd.to_numeric(out[column], errors="raise")

    symbol = str(etf["symbol"]).strip()
    display_name = str(etf.get("display_name", "")).strip()
    market = str(etf.get("market", "")).strip()
    out["symbol"] = symbol
    out["display_name"] = display_name
    out["market"] = market
    out["frequency"] = str(download["frequency"]).strip()
    out["price_adjustment"] = str(download["price_adjustment"]).strip()
    out["source_name"] = str(download["source_name"]).strip()
    out["source_note"] = (
        f"downloaded_at={datetime.now().isoformat(timespec='seconds')}; "
        f"start_date={download['start_date']}; end_date={download['end_date']}; "
        f"period={download['period']}; adjust={download['adjust']}"
    )
    out = out[KLINE_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)
    return out


def load_existing_standardized_kline(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existing standardized raw CSV found at {path}.")
    existing = pd.read_csv(path)
    missing_columns = [column for column in KLINE_COLUMNS if column not in existing.columns]
    if missing_columns:
        raise ValueError(f"Existing standardized raw CSV missing columns: {missing_columns}")
    if existing.empty:
        raise ValueError("Existing standardized raw CSV has zero rows.")
    existing["timestamps"] = pd.to_datetime(existing["timestamps"], errors="raise").dt.strftime("%Y-%m-%d")
    return existing[KLINE_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(report_path: Path, manifest: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    rows = manifest["etfs"]
    success_rows = [row for row in rows if row["status"] == "PASS"]
    failed_rows = [row for row in rows if row["status"] != "PASS"]
    lines = [
        "# Kronos V0.10.2-A AkShare ETF Kline Download Report",
        "",
        f"- 运行时间: {manifest['generated_at']}",
        f"- 数据源: {manifest['source_name']}",
        f"- 下载区间: {manifest['start_date']} 至 {manifest['end_date']}",
        f"- 周期: {manifest['period']}",
        f"- 复权: {manifest['price_adjustment']}",
        f"- ETF 配置数量: {manifest['requested_count']}",
        f"- 成功数量: {manifest['success_count']}",
        f"- 失败数量: {manifest['failed_count']}",
        f"- raw kline 输出目录: {manifest['raw_kline_dir']}",
        f"- manifest 路径: {manifest['manifest_path']}",
        "",
        "## 每只 ETF 下载结果",
        "",
        "| symbol | display_name | market | status | acquisition | bar_count | start_date | end_date | raw_path | failure_reason |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        report_row = dict(row)
        if report_row["status"] == "PASS":
            report_row["failure_reason"] = "-"
        lines.append(
            "| {symbol} | {display_name} | {market} | {status} | {acquisition} | {bar_count} | {start_date} | {end_date} | {raw_path} | {failure_reason} |".format(
                **report_row
            )
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- 本阶段只下载并标准化真实 A 股 ETF 日线 K 线。",
            "- 未处理或伪造 left_candidates_history.csv。",
            "- 未训练模型。",
            "- 未运行 torchrun。",
            "- 未调用 GPU 推理。",
            "- 未接入或回写主项目。",
            "- 未生成交易建议。",
        ]
    )
    if failed_rows:
        lines.extend(["", "## 失败原因", ""])
        lines.extend(f"- {row['symbol']}: {row['failure_reason']}" for row in failed_rows)
    if success_rows:
        min_bar_count = min(int(row["bar_count"]) for row in success_rows)
        lines.extend(["", "## 下载概览", "", f"- 成功 ETF 最小 bar_count: {min_bar_count}"])
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def download(
    config_path: Path,
    raw_kline_dir: Path,
    manifest_path: Path,
    report_path: Path,
    retries: int,
    retry_sleep_seconds: float,
) -> dict[str, Any]:
    config = load_universe(config_path)
    download_config = config["download"]
    raw_kline_dir.mkdir(parents=True, exist_ok=True)

    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("akshare is not installed in the current Python environment.") from exc

    rows: list[dict[str, Any]] = []
    for etf in config["etfs"]:
        symbol = str(etf["symbol"]).strip()
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
            "failure_reason": "",
            "acquisition": "",
        }
        for attempt in range(1, retries + 2):
            try:
                raw_df = ak.fund_etf_hist_em(
                    symbol=symbol,
                    period=download_config["period"],
                    start_date=download_config["start_date"],
                    end_date=download_config["end_date"],
                    adjust=download_config["adjust"],
                )
                normalized = normalize_akshare_frame(raw_df, etf, download_config)
                normalized.to_csv(raw_path, index=False, encoding="utf-8-sig")
                row.update(
                    {
                        "status": "PASS",
                        "acquisition": "downloaded",
                        "bar_count": int(len(normalized)),
                        "start_date": str(normalized["timestamps"].iloc[0]),
                        "end_date": str(normalized["timestamps"].iloc[-1]),
                        "raw_path": raw_path.as_posix(),
                    }
                )
                print(f"PASS {symbol} rows={row['bar_count']} path={raw_path}")
                break
            except Exception as exc:  # noqa: BLE001 - keep batch running and record per-symbol reason.
                row["failure_reason"] = str(exc).replace("\n", " ").strip()
                if attempt <= retries:
                    print(
                        f"RETRY {symbol} attempt={attempt}/{retries} reason={row['failure_reason']}",
                        file=sys.stderr,
                    )
                    time.sleep(retry_sleep_seconds)
                else:
                    print(f"FAIL {symbol} reason={row['failure_reason']}", file=sys.stderr)
        rows.append(row)
        if row["status"] != "PASS" and raw_path.exists():
            try:
                existing = load_existing_standardized_kline(raw_path)
                row.update(
                    {
                        "status": "PASS",
                        "acquisition": "existing_standardized_raw_csv",
                        "bar_count": int(len(existing)),
                        "start_date": str(existing["timestamps"].iloc[0]),
                        "end_date": str(existing["timestamps"].iloc[-1]),
                        "raw_path": raw_path.as_posix(),
                        "failure_reason": f"Remote download failed on this run; reused existing standardized raw CSV. Last remote reason: {row['failure_reason']}",
                    }
                )
                print(f"PASS_EXISTING {symbol} rows={row['bar_count']} path={raw_path}")
            except Exception as exc:  # noqa: BLE001 - report existing-file validation failure too.
                row["failure_reason"] = f"{row['failure_reason']} | existing raw CSV unusable: {exc}"

    success_count = sum(1 for row in rows if row["status"] == "PASS")
    failed_count = len(rows) - success_count
    manifest = {
        "mode": "real_etf_kline_download",
        "version": "V0.10.2-A",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_path.as_posix(),
        "source_name": download_config["source_name"],
        "akshare_version": getattr(ak, "__version__", ""),
        "start_date": download_config["start_date"],
        "end_date": download_config["end_date"],
        "period": download_config["period"],
        "frequency": download_config["frequency"],
        "price_adjustment": download_config["price_adjustment"],
        "raw_kline_dir": raw_kline_dir.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "report_path": report_path.as_posix(),
        "requested_count": len(rows),
        "success_count": success_count,
        "failed_count": failed_count,
        "retries": retries,
        "retry_sleep_seconds": retry_sleep_seconds,
        "etfs": rows,
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
    parser = argparse.ArgumentParser(description="Download V0.10.2-A real ETF kline data from AkShare.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "real_etf_universe.yaml"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "outputs" / "real_data" / "kronos_v10_akshare_download_manifest.json"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "docs" / "kronos_v10_akshare_download_report.md"),
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-sleep-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)

    manifest = download(
        resolve_project_path(args.config),
        resolve_project_path(args.raw_kline_dir),
        resolve_project_path(args.manifest),
        resolve_project_path(args.report),
        max(0, args.retries),
        max(0.0, args.retry_sleep_seconds),
    )
    print(
        "download_summary "
        f"requested_count={manifest['requested_count']} "
        f"success_count={manifest['success_count']} "
        f"failed_count={manifest['failed_count']}"
    )
    return 0 if manifest["success_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
