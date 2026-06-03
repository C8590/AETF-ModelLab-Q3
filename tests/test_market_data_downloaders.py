import importlib
import json
import os

import pandas as pd

from scripts import download_real_etf_kline_baostock as baostock_downloader
from scripts import download_real_etf_kline_tushare as tushare_downloader


def test_baostock_sh_symbol_conversion():
    assert baostock_downloader.baostock_code("510300", "SH") == "sh.510300"


def test_baostock_sz_symbol_conversion():
    assert baostock_downloader.baostock_code("159915", "SZ") == "sz.159915"


def test_existing_qualified_csv_is_skipped(tmp_path):
    path = tmp_path / "510300.csv"
    frame = pd.DataFrame(
        {
            "timestamps": pd.date_range("2020-01-01", periods=3, freq="D").strftime("%Y-%m-%d"),
            "open": [1.0, 1.1, 1.2],
            "high": [1.1, 1.2, 1.3],
            "low": [0.9, 1.0, 1.1],
            "close": [1.0, 1.1, 1.2],
            "volume": [100, 100, 100],
            "amount": [1000, 1000, 1000],
            "symbol": ["510300"] * 3,
            "display_name": ["ETF"] * 3,
            "market": ["SH"] * 3,
            "frequency": ["daily"] * 3,
            "price_adjustment": ["qfq"] * 3,
            "source_name": ["unit_test"] * 3,
            "source_note": ["existing"] * 3,
        }
    )
    frame.to_csv(path, index=False)

    assert baostock_downloader.should_skip_existing(path, min_bars=3) is True


def test_tushare_token_missing_returns_status_without_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    manifest = tushare_downloader.download(
        tmp_path / "config.yaml",
        tmp_path / "raw",
        tmp_path / "manifest.json",
        tmp_path / "report.md",
        min_bars=1000,
    )

    assert manifest["status"] == tushare_downloader.TUSHARE_TOKEN_MISSING
    assert manifest["enabled"] is False


def test_tushare_manifest_does_not_contain_token(tmp_path, monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "SECRET_TOKEN_VALUE")
    manifest = {"status": "PASS", "token_echo": "SECRET_TOKEN_VALUE"}
    output_path = tmp_path / "manifest.json"

    tushare_downloader.write_json(manifest, output_path)

    assert "SECRET_TOKEN_VALUE" not in output_path.read_text(encoding="utf-8")


def test_downloader_script_imports_have_no_download_side_effects():
    modules = [
        "scripts.diagnose_market_data_network",
        "scripts.download_real_etf_kline_baostock",
        "scripts.download_real_etf_kline_tushare",
        "scripts.download_real_etf_kline_all_sources",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert hasattr(module, "main")


def test_standard_output_columns_do_not_contain_forbidden_terms():
    forbidden = ("buy", "sell", "order", "trade", "signal", "recommendation")

    for column in baostock_downloader.KLINE_COLUMNS:
        lower = column.lower()
        assert all(term not in lower for term in forbidden)


def test_tushare_token_missing_manifest_fields_do_not_contain_forbidden_terms(tmp_path, monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    manifest = tushare_downloader.download(
        tmp_path / "config.yaml",
        tmp_path / "raw",
        tmp_path / "manifest.json",
        tmp_path / "report.md",
        min_bars=1000,
    )
    forbidden = ("buy", "sell", "order", "trade", "signal", "recommendation")

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert all(term not in str(key).lower() for term in forbidden)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(json.loads(json.dumps(manifest)))


def test_tushare_token_env_restored_by_monkeypatch(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", os.environ.get("TUSHARE_TOKEN", ""))
