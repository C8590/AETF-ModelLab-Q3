#!/usr/bin/env python3
"""Diagnose ETF market data network access for V0.10.2-C."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROXY_ENV_NAMES = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def safe_error_message(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def check_proxy_env() -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in PROXY_ENV_NAMES}


def check_winhttp_proxy() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["netsh", "winhttp", "show", "proxy"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "returncode": None, "stdout": "", "stderr": safe_error_message(exc)}


def check_akshare() -> dict[str, Any]:
    try:
        import akshare as ak

        df = ak.fund_etf_hist_em(
            symbol="510300",
            period="daily",
            start_date="20240101",
            end_date="20240201",
            adjust="qfq",
        )
        return {
            "status": "PASS" if len(df) > 0 else "FAIL",
            "row_count": int(len(df)),
            "columns": list(map(str, df.columns)),
            "error_message": "" if len(df) > 0 else "AkShare returned zero rows.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "row_count": 0, "columns": [], "error_message": safe_error_message(exc)}


def check_baostock() -> dict[str, Any]:
    try:
        import baostock as bs

        login_result = bs.login()
        if str(getattr(login_result, "error_code", "0")) != "0":
            return {
                "status": "FAIL",
                "symbol": "",
                "row_count": 0,
                "error_message": f"login failed: {getattr(login_result, 'error_msg', '')}",
            }
        try:
            last_error = ""
            for symbol in ["sh.510300", "sz.159915"]:
                result = bs.query_history_k_data_plus(
                    symbol,
                    "date,open,high,low,close,volume,amount",
                    start_date="2024-01-01",
                    end_date="2024-02-01",
                    frequency="d",
                    adjustflag="2",
                )
                if str(getattr(result, "error_code", "0")) != "0":
                    last_error = str(getattr(result, "error_msg", ""))
                    continue
                row_count = 0
                while result.next():
                    result.get_row_data()
                    row_count += 1
                if row_count > 0:
                    return {"status": "PASS", "symbol": symbol, "row_count": row_count, "error_message": ""}
                last_error = "BaoStock returned zero rows."
            return {"status": "FAIL", "symbol": "", "row_count": 0, "error_message": last_error}
        finally:
            bs.logout()
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "symbol": "", "row_count": 0, "error_message": safe_error_message(exc)}


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(report_path: Path, diagnosis: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Kronos V0.10.2-C Market Data Network Diagnosis",
        "",
        f"- 运行时间: {diagnosis['generated_at']}",
        f"- Python 路径: {diagnosis['python_executable']}",
        f"- AkShare 最小测试: {diagnosis['akshare']['status']} (rows={diagnosis['akshare']['row_count']})",
        f"- BaoStock 最小测试: {diagnosis['baostock']['status']} (symbol={diagnosis['baostock']['symbol']}, rows={diagnosis['baostock']['row_count']})",
        f"- Windows winhttp proxy 状态: {diagnosis['winhttp_proxy']['status']}",
        "",
        "## Proxy Environment",
        "",
    ]
    lines.extend(f"- {name}: {'present' if present else 'missing'}" for name, present in diagnosis["proxy_env_present"].items())
    lines.extend(
        [
            "",
            "## winhttp proxy",
            "",
            "```text",
            diagnosis["winhttp_proxy"].get("stdout", "") or diagnosis["winhttp_proxy"].get("stderr", ""),
            "```",
            "",
            "## Errors",
            "",
        ]
    )
    errors = []
    if diagnosis["akshare"]["status"] != "PASS":
        errors.append(f"AkShare: {diagnosis['akshare']['error_message']}")
    if diagnosis["baostock"]["status"] != "PASS":
        errors.append(f"BaoStock: {diagnosis['baostock']['error_message']}")
    lines.extend(f"- {error}" for error in errors) if errors else lines.append("- 无阻断错误。")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- 未训练模型。",
            "- 未运行 torchrun。",
            "- 未调用 GPU 推理。",
            "- 未接入或回写主项目。",
            "- 未生成交易建议。",
        ]
    )
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(
    output_path: str | Path = ROOT / "outputs" / "real_data" / "kronos_v10_market_data_network_diagnosis.json",
    report_path: str | Path = ROOT / "docs" / "kronos_v10_market_data_network_diagnosis.md",
) -> dict[str, Any]:
    diagnosis = {
        "mode": "market_data_network_diagnosis",
        "version": "V0.10.2-C",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "python_executable": sys.executable,
        "proxy_env_present": check_proxy_env(),
        "winhttp_proxy": check_winhttp_proxy(),
        "akshare": check_akshare(),
        "baostock": check_baostock(),
        "no_model_training": True,
        "no_torchrun": True,
        "no_gpu_inference": True,
        "no_left_project_connection": True,
        "no_market_advice": True,
    }
    write_json(diagnosis, resolve_project_path(output_path))
    write_report(resolve_project_path(report_path), diagnosis)
    return diagnosis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose V0.10.2-C ETF market data network access.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "outputs" / "real_data" / "kronos_v10_market_data_network_diagnosis.json"),
    )
    parser.add_argument("--report", default=str(ROOT / "docs" / "kronos_v10_market_data_network_diagnosis.md"))
    args = parser.parse_args(argv)
    diagnosis = run(args.output, args.report)
    print(f"python_executable={diagnosis['python_executable']}")
    for name, present in diagnosis["proxy_env_present"].items():
        print(f"{name}={'present' if present else 'missing'}")
    print(f"winhttp_proxy_status={diagnosis['winhttp_proxy']['status']}")
    print(f"akshare_status={diagnosis['akshare']['status']} rows={diagnosis['akshare']['row_count']}")
    print(
        "baostock_status="
        f"{diagnosis['baostock']['status']} symbol={diagnosis['baostock']['symbol']} rows={diagnosis['baostock']['row_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
