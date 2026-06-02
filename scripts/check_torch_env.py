#!/usr/bin/env python3
"""Compatibility wrapper for V0.1 environment check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    return subprocess.call([sys.executable, str(root / "scripts" / "check_cuda.py")])


if __name__ == "__main__":
    raise SystemExit(main())
