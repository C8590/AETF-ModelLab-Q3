#!/usr/bin/env python3
"""Run the V0.2 Kronos-small single-sample inference."""

from __future__ import annotations

import os
import platform
import random
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
KRONOS_ROOT = PROJECT_ROOT / "external" / "Kronos"
HF_CACHE_DIR = PROJECT_ROOT / "models" / "kronos" / "hf_cache"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "kronos_v02_sample_prediction.csv"
REPORT_PATH = PROJECT_ROOT / "docs" / "kronos_v02_sample_inference_report.md"
SYNTHETIC_SAMPLE_PATH = PROJECT_ROOT / "data" / "samples" / "kronos_v02_synthetic_ohlcv.csv"

os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR / "hub"))
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(KRONOS_ROOT))

import numpy as np
import pandas as pd
import torch

from model_lab.kronos_adapter import (
    KronosConfig,
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
INPUT_FIELDS = ["open", "high", "low", "close", "volume", "amount"]


def set_seed(seed: int = 123) -> None:
    random.seed(seed)
    np.random.seed(seed)
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
    df = pd.DataFrame(
        {
            "timestamps": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "amount": amount,
        }
    )
    df.to_csv(path, index=False)
    return path


def load_sample() -> tuple[pd.DataFrame, Path, str]:
    sample_path = official_kronos_sample_path(PROJECT_ROOT)
    source = "external/Kronos/tests/data/regression_input.csv"
    if not sample_path.exists():
        sample_path = generate_synthetic_sample(SYNTHETIC_SAMPLE_PATH)
        source = "data/samples/kronos_v02_synthetic_ohlcv.csv"
    df = pd.read_csv(sample_path, parse_dates=["timestamps"])
    validate_kronos_ohlcv_sample(df, source)
    if len(df) < LOOKBACK + PRED_LEN:
        raise ValueError(f"Sample has {len(df)} rows, needs at least {LOOKBACK + PRED_LEN}.")
    return df, sample_path, source


def gpu_memory() -> dict[str, Any]:
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
    pred_head = state.get("pred_head", "")
    error = state.get("error", "")
    mem_before = state.get("gpu_memory_before", {})
    mem_after = state.get("gpu_memory_after", {})
    return [
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 运行时间: {state.get('elapsed_seconds', 'N/A')}",
        f"- Python 版本: {platform.python_version()}",
        f"- torch 版本: {torch.__version__}",
        f"- CUDA 版本: {torch.version.cuda}",
        f"- GPU 名称: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}",
        f"- 模型名称: {MODEL_NAME}",
        f"- tokenizer 名称: {TOKENIZER_NAME}",
        f"- lookback: {LOOKBACK}",
        f"- pred_len: {PRED_LEN}",
        f"- max_context: {MAX_CONTEXT}",
        f"- T: {TEMPERATURE}",
        f"- top_p: {TOP_P}",
        f"- sample_count: {SAMPLE_COUNT}",
        f"- 输入数据源: {state.get('sample_source', 'N/A')}",
        f"- 输入字段: {', '.join(INPUT_FIELDS)}",
        f"- 输出字段: {', '.join(state.get('output_fields', []))}",
        f"- 是否使用 GPU: {state.get('used_gpu', False)}",
        f"- 显存使用观察-运行前: {mem_before}",
        f"- 显存使用观察-运行后: {mem_after}",
        f"- 是否成功导入 Kronos 类: {state.get('import_ok', False)}",
        f"- 是否成功加载 Kronos-small: {state.get('model_loaded', False)}",
        f"- 是否成功完成推理: {state.get('success', False)}",
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
    start = time.perf_counter()
    state: dict[str, Any] = {
        "success": False,
        "import_ok": False,
        "model_loaded": False,
        "used_gpu": False,
        "output_fields": [],
    }
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    try:
        set_seed()
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available; V0.2 requires cuda:0.")
        state["gpu_memory_before"] = gpu_memory()

        from model import Kronos, KronosPredictor, KronosTokenizer

        state["import_ok"] = True
        tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_NAME, cache_dir=HF_CACHE_DIR)
        model = Kronos.from_pretrained(MODEL_NAME, cache_dir=HF_CACHE_DIR)
        tokenizer.eval()
        model.eval()
        state["model_loaded"] = True

        predictor = KronosPredictor(model, tokenizer, device=DEVICE, max_context=MAX_CONTEXT)
        config = KronosConfig()
        df, sample_path, sample_source = load_sample()
        state["sample_source"] = f"{sample_source} ({sample_path})"

        x_df = df.loc[: LOOKBACK - 1, INPUT_FIELDS].reset_index(drop=True)
        x_timestamp = df.loc[: LOOKBACK - 1, "timestamps"].reset_index(drop=True)
        y_timestamp = df.loc[LOOKBACK : LOOKBACK + PRED_LEN - 1, "timestamps"].reset_index(drop=True)

        with torch.no_grad():
            pred_df = predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=PRED_LEN,
                T=TEMPERATURE,
                top_p=TOP_P,
                sample_count=SAMPLE_COUNT,
                verbose=True,
            )
        pred_df = pred_df.copy()
        pred_df.insert(0, "timestamps", y_timestamp.to_numpy())
        pred_df.to_csv(OUTPUT_CSV, index=False)

        state["used_gpu"] = predictor.device == DEVICE
        state["output_fields"] = pred_df.columns.tolist()
        state["pred_head"] = pred_df.head().to_string(index=False)
        state["gpu_memory_after"] = gpu_memory()
        state["success"] = True
        _ = config
    except Exception as exc:
        state["error"] = f"{type(exc).__name__}: {exc}"
        state["traceback"] = traceback.format_exc()
        state.setdefault("gpu_memory_after", gpu_memory())
    finally:
        state["elapsed_seconds"] = f"{time.perf_counter() - start:.2f}s"
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
