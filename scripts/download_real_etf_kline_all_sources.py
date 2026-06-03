#!/usr/bin/env python3
"""Download real ETF kline data with AkShare, BaoStock, and optional Tushare fallbacks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIN_BARS = 1000
DEFAULT_TARGET_QUALIFIED = 20

SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.download_real_etf_kline_akshare import normalize_akshare_frame  # noqa: E402
from scripts.download_real_etf_kline_baostock import (  # noqa: E402
    BAOSTOCK_SOURCE_NOTE,
    download as download_baostock,
    safe_error_message,
    scan_raw_kline_dir,
    summarize_kline,
)
from scripts.download_real_etf_kline_tushare import download as download_tushare  # noqa: E402


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_universe(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    etfs = config.get("etfs")
    if not isinstance(etfs, list) or not etfs:
        raise ValueError("configs/real_etf_universe.yaml must contain a non-empty etfs list.")
    return config


def symbol_status(raw_kline_dir: Path, universe: list[dict[str, Any]], min_bars: int) -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for etf in universe:
        symbol = str(etf["symbol"]).strip()
        path = raw_kline_dir / f"{symbol}.csv"
        row = {"symbol": symbol, "raw_path": path.as_posix(), "exists": path.exists(), "qualified": False, "bar_count": 0}
        if path.exists():
            try:
                summary = summarize_kline(path)
                row.update(summary)
                row["qualified"] = int(summary["bar_count"]) >= min_bars
            except Exception as exc:  # noqa: BLE001
                row["error_message"] = safe_error_message(exc)
        status[symbol] = row
    return status


def missing_or_unqualified_symbols(raw_kline_dir: Path, universe: list[dict[str, Any]], min_bars: int) -> list[str]:
    status = symbol_status(raw_kline_dir, universe, min_bars)
    return [str(etf["symbol"]).strip() for etf in universe if not status[str(etf["symbol"]).strip()]["qualified"]]


def qualified_count(raw_kline_dir: Path, min_bars: int) -> int:
    return int(scan_raw_kline_dir(raw_kline_dir, min_bars)["qualified_raw_csv_count"])


def attempt_akshare(
    *,
    config: dict[str, Any],
    raw_kline_dir: Path,
    target_symbols: list[str],
    min_bars: int,
    target_qualified_count: int,
    retries: int,
    retry_sleep_seconds: float,
) -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except ImportError:
        return [
            {
                "symbol": symbol,
                "source_name": "akshare.fund_etf_hist_em",
                "status": "FAIL",
                "bar_count": 0,
                "error_message": "akshare is not installed in the current Python environment.",
            }
            for symbol in target_symbols
        ]

    download_config = config["download"]
    etf_by_symbol = {str(etf["symbol"]).strip(): etf for etf in config["etfs"]}
    rows: list[dict[str, Any]] = []
    for symbol in target_symbols:
        if qualified_count(raw_kline_dir, min_bars) >= target_qualified_count:
            break
        etf = etf_by_symbol[symbol]
        raw_path = raw_kline_dir / f"{symbol}.csv"
        row = {
            "symbol": symbol,
            "source_name": download_config["source_name"],
            "status": "FAIL",
            "bar_count": 0,
            "raw_path": raw_path.as_posix(),
            "attempts": 0,
            "error_message": "",
        }
        last_error = ""
        for attempt in range(1, retries + 2):
            row["attempts"] = attempt
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
                        "status": "DOWNLOADED",
                        "bar_count": int(len(normalized)),
                        "start_date": str(normalized["timestamps"].iloc[0]),
                        "end_date": str(normalized["timestamps"].iloc[-1]),
                        "error_message": "",
                    }
                )
                print(f"AKSHARE PASS {symbol} rows={row['bar_count']} path={raw_path}")
                break
            except Exception as exc:  # noqa: BLE001
                last_error = safe_error_message(exc)
                if attempt <= retries:
                    print(f"AKSHARE RETRY {symbol} attempt={attempt}/{retries} reason={last_error}", file=sys.stderr)
                    time.sleep(retry_sleep_seconds)
                else:
                    row["error_message"] = last_error
                    print(f"AKSHARE FAIL {symbol} reason={last_error}", file=sys.stderr)
        rows.append(row)
    return rows


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        encoded = encoded.replace(token, "[REDACTED]")
    output_path.write_text(encoded + "\n", encoding="utf-8")


def write_report(report_path: Path, manifest: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    failed_symbols = manifest["failed_symbols"]
    lines = [
        "# Kronos V0.10.2-C All Sources ETF Kline Download Report",
        "",
        f"- 运行时间: {manifest['generated_at']}",
        f"- ETF universe 配置数量: {manifest['configured_count']}",
        f"- 初始 qualified raw CSV 数量: {manifest['initial_qualified_raw_csv_count']}",
        f"- 最终 raw kline CSV 总数: {manifest['total_available_raw_csv_count']}",
        f"- 最终 qualified raw CSV 数量: {manifest['qualified_raw_csv_count']}",
        f"- 目标 qualified raw CSV 数量: {manifest['target_qualified_raw_csv_count']}",
        f"- AkShare 成功数量: {manifest['akshare_success_count']}",
        f"- BaoStock 成功数量: {manifest['baostock_success_count']}",
        f"- Tushare 状态: {manifest['tushare_status']}",
        f"- Tushare 成功数量: {manifest['tushare_success_count']}",
        f"- 仍失败 ETF 数量: {len(failed_symbols)}",
        "",
        "## 数据源混用风险",
        "",
        f"- BaoStock fallback CSV 的 source_note 会标记 `{BAOSTOCK_SOURCE_NOTE}`。",
        "- BaoStock 与 AkShare qfq 复权口径未做逐项一致性校验，后续分析应按 source_name/source_note 分层检查。",
        "",
        "## 仍失败 ETF",
        "",
    ]
    lines.extend(f"- {symbol}" for symbol in failed_symbols) if failed_symbols else lines.append("- 无。")
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
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(
    config_path: str | Path = ROOT / "configs" / "real_etf_universe.yaml",
    raw_kline_dir: str | Path = ROOT / "data" / "real" / "raw" / "kline",
    manifest_path: str | Path = ROOT / "outputs" / "real_data" / "kronos_v10_all_sources_download_manifest.json",
    report_path: str | Path = ROOT / "docs" / "kronos_v10_all_sources_download_report.md",
    min_bars: int = DEFAULT_MIN_BARS,
    target_qualified_count: int = DEFAULT_TARGET_QUALIFIED,
    retries: int = 2,
    retry_sleep_seconds: float = 1.0,
) -> dict[str, Any]:
    config_file = resolve_project_path(config_path)
    raw_dir = resolve_project_path(raw_kline_dir)
    manifest_file = resolve_project_path(manifest_path)
    report_file = resolve_project_path(report_path)
    config = load_universe(config_file)
    raw_dir.mkdir(parents=True, exist_ok=True)

    initial_scan = scan_raw_kline_dir(raw_dir, min_bars)
    akshare_rows: list[dict[str, Any]] = []
    baostock_manifest: dict[str, Any] | None = None
    tushare_manifest: dict[str, Any] | None = None
    tushare_status = "SKIPPED_TOKEN_MISSING"

    if int(initial_scan["qualified_raw_csv_count"]) < target_qualified_count:
        targets = missing_or_unqualified_symbols(raw_dir, config["etfs"], min_bars)
        akshare_rows = attempt_akshare(
            config=config,
            raw_kline_dir=raw_dir,
            target_symbols=targets,
            min_bars=min_bars,
            target_qualified_count=target_qualified_count,
            retries=max(0, retries),
            retry_sleep_seconds=max(0.0, retry_sleep_seconds),
        )

    if qualified_count(raw_dir, min_bars) < target_qualified_count:
        targets = missing_or_unqualified_symbols(raw_dir, config["etfs"], min_bars)
        baostock_manifest = download_baostock(
            config_file,
            raw_dir,
            ROOT / "outputs" / "real_data" / "kronos_v10_baostock_download_manifest.json",
            ROOT / "docs" / "kronos_v10_baostock_download_report.md",
            False,
            min_bars,
            set(targets),
        )

    if qualified_count(raw_dir, min_bars) < target_qualified_count:
        if os.environ.get("TUSHARE_TOKEN", "").strip():
            targets = missing_or_unqualified_symbols(raw_dir, config["etfs"], min_bars)
            tushare_manifest = download_tushare(
                config_file,
                raw_dir,
                ROOT / "outputs" / "real_data" / "kronos_v10_tushare_download_manifest.json",
                ROOT / "docs" / "kronos_v10_tushare_download_report.md",
                min_bars,
                set(targets),
            )
            tushare_status = str(tushare_manifest.get("status", "UNKNOWN"))
        else:
            tushare_status = "SKIPPED_TOKEN_MISSING"

    final_scan = scan_raw_kline_dir(raw_dir, min_bars)
    final_missing = missing_or_unqualified_symbols(raw_dir, config["etfs"], min_bars)
    akshare_success_count = sum(1 for row in akshare_rows if row["status"] == "DOWNLOADED")
    baostock_success_count = int(baostock_manifest.get("success_count", 0)) if baostock_manifest else 0
    tushare_success_count = int(tushare_manifest.get("success_count", 0)) if tushare_manifest else 0
    manifest = {
        "mode": "real_etf_kline_all_sources_download",
        "version": "V0.10.2-C",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_file.as_posix(),
        "raw_kline_dir": raw_dir.as_posix(),
        "configured_count": len(config["etfs"]),
        "initial_total_available_raw_csv_count": initial_scan["total_available_raw_csv_count"],
        "initial_qualified_raw_csv_count": initial_scan["qualified_raw_csv_count"],
        "total_available_raw_csv_count": final_scan["total_available_raw_csv_count"],
        "qualified_raw_csv_count": final_scan["qualified_raw_csv_count"],
        "target_qualified_raw_csv_count": target_qualified_count,
        "min_bars": min_bars,
        "akshare_success_count": akshare_success_count,
        "baostock_success_count": baostock_success_count,
        "tushare_status": tushare_status,
        "tushare_enabled": bool(os.environ.get("TUSHARE_TOKEN", "").strip()),
        "tushare_success_count": tushare_success_count,
        "failed_symbols": final_missing,
        "akshare_attempts": akshare_rows,
        "baostock_manifest_path": str(ROOT / "outputs" / "real_data" / "kronos_v10_baostock_download_manifest.json")
        if baostock_manifest
        else "",
        "tushare_manifest_path": str(ROOT / "outputs" / "real_data" / "kronos_v10_tushare_download_manifest.json")
        if tushare_manifest
        else "",
        "manifest_path": manifest_file.as_posix(),
        "report_path": report_file.as_posix(),
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    write_json(manifest, manifest_file)
    write_report(report_file, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download V0.10.2-C ETF kline data from all allowed sources.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "real_etf_universe.yaml"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "outputs" / "real_data" / "kronos_v10_all_sources_download_manifest.json"),
    )
    parser.add_argument("--report", default=str(ROOT / "docs" / "kronos_v10_all_sources_download_report.md"))
    parser.add_argument("--min-bars", type=int, default=DEFAULT_MIN_BARS)
    parser.add_argument("--target-qualified-count", type=int, default=DEFAULT_TARGET_QUALIFIED)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)
    manifest = run(
        args.config,
        args.raw_kline_dir,
        args.manifest,
        args.report,
        max(1, args.min_bars),
        max(1, args.target_qualified_count),
        max(0, args.retries),
        max(0.0, args.retry_sleep_seconds),
    )
    print(
        "all_sources_download_summary "
        f"initial_qualified={manifest['initial_qualified_raw_csv_count']} "
        f"qualified_raw_csv_count={manifest['qualified_raw_csv_count']} "
        f"akshare_success_count={manifest['akshare_success_count']} "
        f"baostock_success_count={manifest['baostock_success_count']} "
        f"tushare_status={manifest['tushare_status']} "
        f"tushare_success_count={manifest['tushare_success_count']} "
        f"failed_count={len(manifest['failed_symbols'])}"
    )
    return 0 if int(manifest["qualified_raw_csv_count"]) >= int(manifest["target_qualified_raw_csv_count"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
