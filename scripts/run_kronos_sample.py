#!/usr/bin/env python3
"""V0.2 placeholder: run Kronos-small on one ETF sample after Kronos is installed.

This script intentionally does not download weights in V0.1.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_lab.kronos_adapter import KronosAdapter, KronosConfig  # noqa: E402


def main() -> int:
    print("V0.2 脚本骨架已就绪。")
    print("请先完成 V0.1 CUDA 验收，再拉取 external/Kronos 并下载 Kronos-small 权重。")
    print("正式实现入口：model_lab.kronos_adapter.KronosAdapter")
    _ = KronosAdapter(KronosConfig())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
