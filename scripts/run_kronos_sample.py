#!/usr/bin/env python3
"""Run the V0.2 Kronos-small sample through the reusable V0.3 adapter."""

from __future__ import annotations

import os
import platform
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import numpy as np
import pandas as pd
try:
    import torch
except Exception:
    torch = None

from model_lab.kronos_adapter import (
    KronosAdapter,
    KronosAdapterConfig,
    official_kronos_sample_path,
    validate_kronos_ohlcv_sample,
    write_markdown_report,
)

MODEL_NAME = "NeoQuasar/Kronos-small"
TOKENIZER_NAME = "NeoQuasar/Kronos-Tokenizer-base"
LOOKBACK = 400
PRED_LEN = 120
MAX_CONTEXT = 512
TEMPERATURE = 1.0
TOP_P = 0.9
SAMPLE_COUNT = 1
DEVICE = "cuda:0"
HF_CACHE_DIR = PROJECT_ROOT / "models" / "kronos" / "hf_cache"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "kronos_v02_sample_prediction.csv"
REPORT_PATH = PROJECT_ROOT / "docs" / "kronos_v02_sample_inference_report.md"
SYNTHETIC_SAMPLE_PATH = PROJECT_ROOT / "data" / "samples" / "kronos_v02_synthetic_ohlcv.csv"


def set_seed(seed: int = 123) -> None:
    random.seed(seed)
    np.random.seed(seed)
    if torch is None:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def generate_synthetic_sample(path: Path, rows: int = 640) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(123)
    timestamps = pd.date_range("2024-01-01 09:30:00", periods=rows, freq="5min")
    close = 10 + np.cumsum(rng.normal(0, 0.015, rows))
    open_ = close + rng.normal(0, 0.01, rows)
    high = np.maximum(open_, close) + rng.uniform(0.005, 0.04, rows)
    low = np.minimum(open_, close) - rng.uniform(0.005, 0.04, rows)
    volume = rng.integers(100, 1500, rows).astype(float)
    amount = volume * (open_ + high + low + close) / 4 * 100
    pd.DataFrame(
        {
            "timestamps": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
        }
    ).to_csv(path, index=False)
    return path


def load_sample() -> tuple[pd.DataFrame, Path, str]:
    sample_path = official_kronos_sample_path(PROJECT_ROOT)
    source = "external/Kronos/tests/data/regression_input.csv"
    if not sample_path.exists():
        sample_path = generate_synthetic_sample(SYNTHETIC_SAMPLE_PATH)
        source = "data/samples/kronos_v02_synthetic_ohlcv.csv"
    df = pd.read_csv(sample_path, parse_dates=["timestamps"])
    validate_kronos_ohlcv_sample(df, source)
    return df, sample_path, source


def gpu_memory() -> dict[str, Any]:
    if torch is None:
        return {"available": False}
    if not torch.cuda.is_available():
        return {"available": False}
    device = torch.device(DEVICE)
    return {
        "available": True,
        "allocated_mib": round(torch.cuda.memory_allocated(device) / 1024 / 1024, 2),
        "reserved_mib": round(torch.cuda.memory_reserved(device) / 1024 / 1024, 2),
        "max_allocated_mib": round(torch.cuda.max_memory_allocated(device) / 1024 / 1024, 2),
        "name": torch.cuda.get_device_name(device),
    }


def report_lines(state: dict[str, Any]) -> list[str]:
    metadata = state.get("metadata", {})
    pred_head = state.get("pred_head", "")
    error = state.get("error", "")
    return [
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 运行时间: {metadata.get('elapsed_seconds', 'N/A')}s",
        f"- Python 版本: {platform.python_version()}",
        f"- torch 版本: {torch.__version__ if torch is not None else 'unavailable'}",
        f"- CUDA 版本: {torch.version.cuda if torch is not None else 'unavailable'}",
        f"- GPU 名称: {torch.cuda.get_device_name(0) if torch is not None and torch.cuda.is_available() else 'N/A'}",
        f"- 模型名称: {metadata.get('model_name', MODEL_NAME)}",
        f"- tokenizer 名称: {metadata.get('tokenizer_name', TOKENIZER_NAME)}",
        f"- lookback: {metadata.get('lookback', LOOKBACK)}",
        f"- pred_len: {metadata.get('pred_len', PRED_LEN)}",
        f"- max_context: {metadata.get('max_context', MAX_CONTEXT)}",
        f"- T: {TEMPERATURE}",
        f"- top_p: {TOP_P}",
        f"- sample_count: {SAMPLE_COUNT}",
        f"- 输入数据源: {state.get('sample_source', 'N/A')}",
        f"- 输入字段: {', '.join(metadata.get('input_columns', []))}",
        f"- 输出字段: {', '.join(metadata.get('output_columns', []))}",
        f"- 是否使用 GPU: {metadata.get('device') == DEVICE and metadata.get('cuda_available', False)}",
        f"- 显存使用观察-运行前: {state.get('gpu_memory_before', {})}",
        f"- 显存使用观察-运行后: {state.get('gpu_memory_after', {})}",
        f"- 是否通过 Adapter 加载: {state.get('adapter_loaded', False)}",
        f"- 是否通过 Adapter 推理: {state.get('success', False)}",
        f"- 输出 CSV 路径: {OUTPUT_CSV if state.get('success') else 'N/A'}",
        f"- 失败原因: {error if error else 'N/A'}",
        "",
        "## pred_df.head()",
        "",
        "```text",
        pred_head if pred_head else "N/A",
        "```",
    ]


def main() -> int:
    state: dict[str, Any] = {"success": False, "adapter_loaded": False}
    os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
    os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR / "hub"))
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    try:
        set_seed()
        if torch is None:
            raise RuntimeError("torch is not installed; V0.2 sample requires PyTorch with CUDA.")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available; V0.2 sample requires cuda:0.")
        state["gpu_memory_before"] = gpu_memory()
        df, sample_path, sample_source = load_sample()
        state["sample_source"] = f"{sample_source} ({sample_path})"

        adapter = KronosAdapter(
            KronosAdapterConfig(
                model_name=MODEL_NAME,
                tokenizer_name=TOKENIZER_NAME,
                device=DEVICE,
                max_context=MAX_CONTEXT,
                hf_cache_dir=HF_CACHE_DIR,
                default_lookback=LOOKBACK,
                default_pred_len=PRED_LEN,
                default_T=TEMPERATURE,
                default_top_p=TOP_P,
                default_sample_count=SAMPLE_COUNT,
            )
        )
        result = adapter.predict(
            df,
            lookback=LOOKBACK,
            pred_len=PRED_LEN,
            T=TEMPERATURE,
            top_p=TOP_P,
            sample_count=SAMPLE_COUNT,
            verbose=True,
        )
        state["adapter_loaded"] = adapter.is_loaded()
        result.pred_df.to_csv(OUTPUT_CSV, index=False)
        state["metadata"] = result.metadata
        state["pred_head"] = result.pred_df.head().to_string(index=False)
        state["gpu_memory_after"] = gpu_memory()
        state["success"] = True
    except Exception as exc:
        state["error"] = f"{type(exc).__name__}: {exc}"
        state["traceback"] = traceback.format_exc()
        state.setdefault("gpu_memory_after", gpu_memory())
    finally:
        write_markdown_report(REPORT_PATH, "Kronos V0.2 样本推理报告", report_lines(state))
        print(f"Wrote report: {REPORT_PATH}")
        if state.get("success"):
            print(f"Wrote prediction CSV: {OUTPUT_CSV}")
            print("V0.2_SAMPLE_INFERENCE_PASS=True")
            return 0
        print("V0.2_SAMPLE_INFERENCE_PASS=False")
        print(state.get("error", "Unknown error"))
        if state.get("traceback"):
            print(state["traceback"])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
