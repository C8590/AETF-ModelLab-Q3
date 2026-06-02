#!/usr/bin/env python3
"""Check PyTorch / CUDA availability and write a Markdown report.

This script is safe for V0.1: it does not read or write the left-side project,
it does not download model weights, and it does not run any trading logic.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def run_command(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    """Run a command and return stdout/stderr without raising."""
    if shutil.which(cmd[0]) is None:
        return {"ok": False, "stdout": "", "stderr": f"{cmd[0]} not found"}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "stdout": "", "stderr": repr(exc)}


def check_torch() -> dict[str, Any]:
    """Collect torch and CUDA information."""
    result: dict[str, Any] = {
        "torch_imported": False,
        "torch_error": None,
        "torch_version": None,
        "torch_cuda_version": None,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "tensor_test": "SKIPPED",
        "tensor_test_error": None,
        "can_enter_kronos_phase": False,
    }

    try:
        import torch  # type: ignore
    except Exception as exc:
        result["torch_error"] = repr(exc)
        return result

    result["torch_imported"] = True
    result["torch_version"] = getattr(torch, "__version__", None)
    result["torch_cuda_version"] = getattr(getattr(torch, "version", None), "cuda", None)

    try:
        result["cuda_available"] = bool(torch.cuda.is_available())
        result["device_count"] = int(torch.cuda.device_count()) if result["cuda_available"] else 0
    except Exception as exc:
        result["tensor_test_error"] = f"CUDA query failed: {exc!r}"
        return result

    if result["cuda_available"]:
        for idx in range(result["device_count"]):
            props = torch.cuda.get_device_properties(idx)
            result["devices"].append(
                {
                    "index": idx,
                    "name": torch.cuda.get_device_name(idx),
                    "capability": ".".join(str(x) for x in torch.cuda.get_device_capability(idx)),
                    "total_memory_gb": round(props.total_memory / (1024**3), 2),
                    "multi_processor_count": props.multi_processor_count,
                }
            )

        try:
            device = torch.device("cuda:0")
            a = torch.randn((1024, 1024), device=device)
            b = torch.randn((1024, 1024), device=device)
            c = a @ b
            torch.cuda.synchronize()
            checksum = float(c[0, 0].detach().cpu())
            result["tensor_test"] = "PASS"
            result["tensor_checksum"] = checksum
            result["can_enter_kronos_phase"] = True
        except Exception as exc:
            result["tensor_test"] = "FAIL"
            result["tensor_test_error"] = repr(exc)

    return result


def render_markdown(info: dict[str, Any]) -> str:
    """Render a human-readable Markdown report."""
    nvidia = info["nvidia_smi"]
    torch_info = info["torch"]
    devices = torch_info.get("devices", [])
    device_rows = "\n".join(
        f"| {d['index']} | {d['name']} | {d['capability']} | {d['total_memory_gb']} | {d['multi_processor_count']} |"
        for d in devices
    ) or "| - | 未识别 | - | - | - |"

    status = "YES" if torch_info.get("can_enter_kronos_phase") else "NO"
    cuda_available = torch_info.get("cuda_available")
    tensor_test = torch_info.get("tensor_test")

    return f"""# PyTorch / CUDA 环境检查报告

生成时间：{info['checked_at']}  
项目：AETF-ModelLab  
阶段：V0.1 PyTorch / CUDA 环境检查  

## 1. 结论

| 项目 | 结果 |
|---|---|
| Python 版本 | `{info['python_version']}` |
| 操作系统 | `{info['platform']}` |
| PyTorch 已安装 | `{torch_info.get('torch_imported')}` |
| PyTorch 版本 | `{torch_info.get('torch_version')}` |
| PyTorch CUDA 版本 | `{torch_info.get('torch_cuda_version')}` |
| CUDA 可用 | `{cuda_available}` |
| GPU 数量 | `{torch_info.get('device_count')}` |
| Tensor 测试 | `{tensor_test}` |
| 是否可以进入 Kronos 部署阶段 | `{status}` |

## 2. GPU 设备

| Index | 名称 | Compute Capability | 显存 GB | SM 数 |
|---:|---|---:|---:|---:|
{device_rows}

## 3. nvidia-smi

可执行：`{nvidia.get('ok')}`  
返回码：`{nvidia.get('returncode', '-')}`

```text
{nvidia.get('stdout') or nvidia.get('stderr') or '无输出'}
```

## 4. 错误信息

```text
Torch import error: {torch_info.get('torch_error')}
Tensor test error: {torch_info.get('tensor_test_error')}
```

## 5. 验收判断

```text
V0.1_PASS = {torch_info.get('can_enter_kronos_phase')}
NEXT_STEP = {'进入 V0.2 Kronos 本地样本推理' if torch_info.get('can_enter_kronos_phase') else '停止；先修复 Python / PyTorch / CUDA / NVIDIA 驱动环境'}
```

## 6. 边界确认

本检查脚本不读取、不修改左侧主项目，不下载模型权重，不执行交易逻辑。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PyTorch CUDA environment for AETF-ModelLab.")
    parser.add_argument(
        "--output",
        default="docs/pytorch_cuda_env_check.md",
        help="Markdown report path. Default: docs/pytorch_cuda_env_check.md",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit code when CUDA tensor test fails.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    info = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
        "nvidia_smi": run_command(["nvidia-smi"]),
        "torch": check_torch(),
    }

    output.write_text(render_markdown(info), encoding="utf-8")

    if args.json_output:
        json_output = Path(args.json_output)
        if not json_output.is_absolute():
            json_output = root / json_output
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote report: {output}")
    ok = bool(info["torch"].get("can_enter_kronos_phase"))
    print(f"V0.1_PASS={ok}")

    if args.strict and not ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
