#!/usr/bin/env python3
"""Download real A-share ETF daily kline data from BaoStock for V0.10.2-C."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIN_BARS = 1000

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

BAOSTOCK_FIELDS = "date,open,high,low,close,volume,amount"
BAOSTOCK_SOURCE_NAME = "baostock.query_history_k_data_plus"
BAOSTOCK_SOURCE_NOTE = "baostock_fallback_adjustment_unverified"


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def safe_error_message(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def load_universe(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    etfs = config.get("etfs")
    if not isinstance(etfs, list) or not etfs:
        raise ValueError("configs/real_etf_universe.yaml must contain a non-empty etfs list.")
    symbols = [str(etf.get("symbol", "")).strip() for etf in etfs]
    duplicates = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicates:
        raise ValueError(f"ETF universe contains duplicate symbols: {duplicates}")
    return config


def baostock_code(symbol: str, market: str) -> str:
    market_value = str(market).strip().upper()
    symbol_value = str(symbol).strip()
    if market_value == "SH":
        return f"sh.{symbol_value}"
    if market_value == "SZ":
        return f"sz.{symbol_value}"
    raise ValueError(f"Unsupported ETF market for BaoStock: {market}")


def yyyymmdd_to_iso(value: str) -> str:
    return datetime.strptime(str(value), "%Y%m%d").strftime("%Y-%m-%d")


def normalize_baostock_frame(raw_df: pd.DataFrame, etf: dict[str, Any], download: dict[str, Any]) -> pd.DataFrame:
    missing_source_columns = [column for column in BAOSTOCK_FIELDS.split(",") if column not in raw_df.columns]
    if missing_source_columns:
        raise ValueError(f"BaoStock result missing expected columns: {missing_source_columns}")
    if raw_df.empty:
        raise ValueError("BaoStock returned zero rows.")

    out = raw_df.rename(columns={"date": "timestamps"}).copy()
    out = out[["timestamps", "open", "high", "low", "close", "volume", "amount"]]
    out["timestamps"] = pd.to_datetime(out["timestamps"], errors="raise").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        out[column] = pd.to_numeric(out[column], errors="raise")

    out["symbol"] = str(etf["symbol"]).strip()
    out["display_name"] = str(etf.get("display_name", "")).strip()
    out["market"] = str(etf.get("market", "")).strip()
    out["frequency"] = str(download.get("frequency", "daily")).strip()
    out["price_adjustment"] = str(download.get("price_adjustment", "qfq")).strip()
    out["source_name"] = BAOSTOCK_SOURCE_NAME
    out["source_note"] = (
        f"{BAOSTOCK_SOURCE_NOTE}; downloaded_at={datetime.now().isoformat(timespec='seconds')}; "
        f"start_date={download['start_date']}; end_date={download['end_date']}; "
        "frequency=daily; requested_adjustflag=2"
    )
    return out[KLINE_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)


def load_standardized_kline(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No standardized raw CSV found at {path}.")
    existing = pd.read_csv(path)
    missing_columns = [column for column in KLINE_COLUMNS if column not in existing.columns]
    if missing_columns:
        raise ValueError(f"Standardized raw CSV missing columns: {missing_columns}")
    if existing.empty:
        raise ValueError("Standardized raw CSV has zero rows.")
    existing["timestamps"] = pd.to_datetime(existing["timestamps"], errors="raise").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        existing[column] = pd.to_numeric(existing[column], errors="raise")
    return existing[KLINE_COLUMNS].sort_values("timestamps", kind="stable").reset_index(drop=True)


def summarize_kline(path: Path) -> dict[str, Any]:
    df = load_standardized_kline(path)
    return {
        "bar_count": int(len(df)),
        "start_date": str(df["timestamps"].iloc[0]),
        "end_date": str(df["timestamps"].iloc[-1]),
        "raw_path": path.as_posix(),
    }


def scan_raw_kline_dir(raw_kline_dir: Path, min_bars: int) -> dict[str, int]:
    total_available = 0
    qualified = 0
    if not raw_kline_dir.exists():
        return {"total_available_raw_csv_count": 0, "qualified_raw_csv_count": 0}
    for path in sorted(raw_kline_dir.glob("*.csv")):
        try:
            summary = summarize_kline(path)
        except Exception:
            continue
        total_available += 1
        if int(summary["bar_count"]) >= min_bars:
            qualified += 1
    return {
        "total_available_raw_csv_count": total_available,
        "qualified_raw_csv_count": qualified,
    }


def try_existing(raw_path: Path, min_bars: int) -> dict[str, Any] | None:
    if not raw_path.exists():
        return None
    summary = summarize_kline(raw_path)
    if int(summary["bar_count"]) < min_bars:
        return None
    return summary


def should_skip_existing(raw_path: Path, min_bars: int) -> bool:
    try:
        return try_existing(raw_path, min_bars) is not None
    except Exception:
        return False


def base_symbol_row(etf: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(etf.get("symbol", "")).strip(),
        "display_name": str(etf.get("display_name", "")).strip(),
        "market": str(etf.get("market", "")).strip(),
        "status": "FAIL",
        "bar_count": 0,
        "start_date": "",
        "end_date": "",
        "raw_path": "",
        "attempts": 0,
        "acquisition": "",
        "error_message": "",
    }


def baostock_result_to_frame(result: Any) -> pd.DataFrame:
    rows: list[list[Any]] = []
    fields = list(getattr(result, "fields", BAOSTOCK_FIELDS.split(",")))
    while result.next():
        rows.append(result.get_row_data())
    return pd.DataFrame(rows, columns=fields)


def download_one(*, bs: Any, etf: dict[str, Any], download_config: dict[str, Any], raw_path: Path) -> pd.DataFrame:
    code = baostock_code(str(etf["symbol"]), str(etf.get("market", "")))
    result = bs.query_history_k_data_plus(
        code,
        BAOSTOCK_FIELDS,
        start_date=yyyymmdd_to_iso(str(download_config["start_date"])),
        end_date=yyyymmdd_to_iso(str(download_config["end_date"])),
        frequency="d",
        adjustflag="2",
    )
    if str(getattr(result, "error_code", "0")) != "0":
        raise RuntimeError(f"BaoStock query failed: {getattr(result, 'error_msg', '')}")
    raw_df = baostock_result_to_frame(result)
    normalized = normalize_baostock_frame(raw_df, etf, download_config)
    normalized.to_csv(raw_path, index=False, encoding="utf-8-sig")
    return normalized


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(report_path: Path, manifest: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    rows = manifest["etfs"]
    failed_rows = [row for row in rows if row["status"] == "FAIL"]
    lines = [
        "# Kronos V0.10.2-C BaoStock ETF Kline Download Report",
        "",
        f"- 运行时间: {manifest['generated_at']}",
        f"- 数据源: {manifest['source_name']}",
        f"- 下载区间: {manifest['start_date']} 至 {manifest['end_date']}",
        f"- 周期: daily",
        f"- 复权: {manifest['price_adjustment']}",
        f"- ETF universe 配置数量: {manifest['configured_count']}",
        f"- 已跳过已有合格 CSV 数量: {manifest['skipped_existing_count']}",
        f"- 本次下载成功数量: {manifest['success_count']}",
        f"- 失败数量: {manifest['fail_count']}",
        f"- raw kline CSV 总数: {manifest['total_available_raw_csv_count']}",
        f"- qualified raw CSV 数量: {manifest['qualified_raw_csv_count']}",
        f"- raw kline 输出目录: {manifest['raw_kline_dir']}",
        f"- manifest 路径: {manifest['manifest_path']}",
        "",
        "## 数据源混用风险",
        "",
        "- BaoStock fallback 已请求 adjustflag=2，但与 AkShare qfq 的复权口径未做逐项一致性校验。",
        f"- 写入 BaoStock CSV 的 source_note 均包含 `{BAOSTOCK_SOURCE_NOTE}`。",
        "",
        "## 每只 ETF 结果",
        "",
        "| symbol | display_name | market | status | acquisition | bar_count | attempts | start_date | end_date | error_message |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        report_row = dict(row)
        if report_row["status"] != "FAIL":
            report_row["error_message"] = "-"
        lines.append(
            "| {symbol} | {display_name} | {market} | {status} | {acquisition} | {bar_count} | {attempts} | {start_date} | {end_date} | {error_message} |".format(
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
        lines.extend(["", "## 仍失败 ETF", ""])
        lines.extend(f"- {row['symbol']}: {row['error_message']}" for row in failed_rows)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def download(
    config_path: Path,
    raw_kline_dir: Path,
    manifest_path: Path,
    report_path: Path,
    force: bool,
    min_bars: int,
    target_symbols: set[str] | None = None,
) -> dict[str, Any]:
    config = load_universe(config_path)
    download_config = config.get("download", {})
    raw_kline_dir.mkdir(parents=True, exist_ok=True)

    try:
        import baostock as bs
    except ImportError as exc:
        raise RuntimeError("baostock is not installed in the current Python environment.") from exc

    login_result = bs.login()
    if str(getattr(login_result, "error_code", "0")) != "0":
        raise RuntimeError(f"BaoStock login failed: {getattr(login_result, 'error_msg', '')}")

    rows: list[dict[str, Any]] = []
    try:
        for etf in config["etfs"]:
            symbol = str(etf["symbol"]).strip()
            if target_symbols is not None and symbol not in target_symbols:
                continue
            raw_path = raw_kline_dir / f"{symbol}.csv"
            row = base_symbol_row(etf)

            if not force:
                try:
                    existing_summary = try_existing(raw_path, min_bars)
                except Exception as exc:  # noqa: BLE001
                    existing_summary = None
                    row["error_message"] = f"existing CSV check failed: {safe_error_message(exc)}"
                if existing_summary is not None:
                    row.update(existing_summary)
                    row.update({"status": "SKIPPED_EXISTING", "acquisition": "existing_standardized_raw_csv"})
                    rows.append(row)
                    print(f"SKIP {symbol} rows={row['bar_count']} path={raw_path}")
                    continue

            try:
                row["attempts"] = 1
                normalized = download_one(bs=bs, etf=etf, download_config=download_config, raw_path=raw_path)
                row.update(
                    {
                        "status": "DOWNLOADED",
                        "acquisition": "downloaded",
                        "bar_count": int(len(normalized)),
                        "start_date": str(normalized["timestamps"].iloc[0]),
                        "end_date": str(normalized["timestamps"].iloc[-1]),
                        "raw_path": raw_path.as_posix(),
                        "error_message": "",
                    }
                )
                print(f"PASS {symbol} rows={row['bar_count']} path={raw_path}")
            except Exception as exc:  # noqa: BLE001 - keep batch running and record per-symbol reason.
                row["error_message"] = safe_error_message(exc)
                print(f"FAIL {symbol} reason={row['error_message']}", file=sys.stderr)
            rows.append(row)
    finally:
        bs.logout()

    dir_scan = scan_raw_kline_dir(raw_kline_dir, min_bars)
    skipped_existing_count = sum(1 for row in rows if row["status"] == "SKIPPED_EXISTING")
    success_count = sum(1 for row in rows if row["status"] == "DOWNLOADED")
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    manifest = {
        "mode": "real_etf_kline_download",
        "version": "V0.10.2-C",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_path": config_path.as_posix(),
        "source_name": BAOSTOCK_SOURCE_NAME,
        "start_date": str(download_config.get("start_date", "")),
        "end_date": str(download_config.get("end_date", "")),
        "frequency": str(download_config.get("frequency", "daily")),
        "price_adjustment": str(download_config.get("price_adjustment", "qfq")),
        "raw_kline_dir": raw_kline_dir.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "report_path": report_path.as_posix(),
        "configured_count": len(config["etfs"]),
        "requested_count": len(rows),
        "skipped_existing_count": skipped_existing_count,
        "success_count": success_count,
        "downloaded_success_count": success_count,
        "fail_count": fail_count,
        "failed_count": fail_count,
        "total_available_raw_csv_count": dir_scan["total_available_raw_csv_count"],
        "qualified_raw_csv_count": dir_scan["qualified_raw_csv_count"],
        "min_bars": min_bars,
        "force": force,
        "target_symbols": sorted(target_symbols) if target_symbols is not None else [],
        "etfs": rows,
        "data_source_mixing_warning": BAOSTOCK_SOURCE_NOTE,
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
    parser = argparse.ArgumentParser(description="Download V0.10.2-C real ETF kline data from BaoStock.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "real_etf_universe.yaml"))
    parser.add_argument("--raw-kline-dir", default=str(ROOT / "data" / "real" / "raw" / "kline"))
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "outputs" / "real_data" / "kronos_v10_baostock_download_manifest.json"),
    )
    parser.add_argument("--report", default=str(ROOT / "docs" / "kronos_v10_baostock_download_report.md"))
    parser.add_argument("--force", action="store_true", help="Redownload even when a qualified raw CSV exists.")
    parser.add_argument("--min-bars", type=int, default=DEFAULT_MIN_BARS)
    parser.add_argument("--symbols", nargs="*", default=None, help="Optional symbol allow-list.")
    args = parser.parse_args(argv)

    manifest = download(
        resolve_project_path(args.config),
        resolve_project_path(args.raw_kline_dir),
        resolve_project_path(args.manifest),
        resolve_project_path(args.report),
        bool(args.force),
        max(1, args.min_bars),
        set(args.symbols) if args.symbols else None,
    )
    print(
        "baostock_download_summary "
        f"requested_count={manifest['requested_count']} "
        f"success_count={manifest['success_count']} "
        f"fail_count={manifest['fail_count']} "
        f"qualified_raw_csv_count={manifest['qualified_raw_csv_count']}"
    )
    return 0 if manifest["qualified_raw_csv_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
