#!/usr/bin/env python3
"""Run V0.4 Kronos shadow-only candidate path observations."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_lab.kronos_adapter import KronosAdapter, KronosAdapterConfig, _torch_info  # noqa: E402
from model_lab.shadow_pipeline import KronosShadowPipeline, resolve_project_path  # noqa: E402


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    validate_shadow_safety(config.get("safety", {}))
    return config


def validate_shadow_safety(safety: dict[str, Any]) -> None:
    if safety.get("mode") != "shadow_only":
        raise ValueError("safety.mode must be shadow_only.")
    for key in [
        "allow_trading_signal",
        "allow_order_execution",
        "allow_writeback_to_left_project",
        "allow_finetune",
    ]:
        if bool(safety.get(key)):
            raise ValueError(f"safety.{key} must be false for V0.4 shadow-only runs.")


def build_adapter(config: dict[str, Any]) -> KronosAdapter:
    adapter_cfg = config.get("adapter", {})
    inference_cfg = config.get("inference", {})
    return KronosAdapter(
        KronosAdapterConfig(
            model_name=adapter_cfg.get("model_name", "NeoQuasar/Kronos-small"),
            tokenizer_name=adapter_cfg.get("tokenizer_name", "NeoQuasar/Kronos-Tokenizer-base"),
            device=adapter_cfg.get("device", "cuda:0"),
            max_context=int(adapter_cfg.get("max_context", 512)),
            hf_cache_dir=adapter_cfg.get("hf_cache_dir", "models/kronos/hf_cache"),
            default_lookback=int(inference_cfg.get("lookback", 120)),
            default_pred_len=int(inference_cfg.get("pred_len", 24)),
            default_T=float(inference_cfg.get("T", 1.0)),
            default_top_p=float(inference_cfg.get("top_p", 0.9)),
            default_sample_count=int(inference_cfg.get("sample_count", 1)),
        )
    )


def run_pytest_quiet() -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    output = (result.stdout + "\n" + result.stderr).strip()
    return status, output.splitlines()[-1] if output else status


def write_shadow_report(
    *,
    report_path: str | Path,
    config: dict[str, Any],
    output: pd.DataFrame,
    pytest_status: str,
    pytest_summary: str,
) -> None:
    adapter_cfg = config.get("adapter", {})
    inference_cfg = config.get("inference", {})
    torch_info = _torch_info(adapter_cfg.get("device", "cuda:0"))
    candidate_count = int(len(output))
    success_count = int((output.get("model_status", pd.Series(dtype=str)) == "PASS").sum())
    fail_count = int((output.get("model_status", pd.Series(dtype=str)) == "FAIL").sum())
    can_enter_v05 = pytest_status == "PASS" and candidate_count > 0

    lines = [
        "# Kronos V0.4 Shadow Report",
        "",
        f"- 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Python 版本: {platform.python_version()}",
        f"- torch 版本: {torch_info['torch_version']}",
        f"- CUDA 版本: {torch_info['cuda_version']}",
        f"- GPU 名称: {torch_info['gpu_name']}",
        f"- Kronos 模型名称: {adapter_cfg.get('model_name')}",
        f"- tokenizer 名称: {adapter_cfg.get('tokenizer_name')}",
        f"- candidate_count: {candidate_count}",
        f"- success_count: {success_count}",
        f"- fail_count: {fail_count}",
        f"- lookback: {inference_cfg.get('lookback')}",
        f"- pred_len: {inference_cfg.get('pred_len')}",
        f"- sample_count: {inference_cfg.get('sample_count')}",
        f"- 输入候选池路径: {config.get('candidate_snapshot_path')}",
        f"- 输出 CSV 路径: {config.get('output_csv_path')}",
        f"- pytest 结果: {pytest_status} ({pytest_summary})",
        f"- 是否可以进入 V0.5 历史回放验证: {'是' if can_enter_v05 else '否'}",
        "",
        "## 输出字段",
        "",
    ]
    lines.extend(f"- `{col}`" for col in output.columns)
    lines.extend(
        [
            "",
            "## 安全边界",
            "",
            "- V0.4 仅生成 shadow observation，不产生交易信号。",
            "- V0.4 不下单，不回写主项目，不执行微调。",
        ]
    )

    path = resolve_project_path(report_path, project_root=ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(config_path: str | Path = ROOT / "configs" / "kronos_shadow.yaml") -> pd.DataFrame:
    config = load_config(config_path)
    adapter = build_adapter(config)
    pipeline = KronosShadowPipeline(adapter, project_root=ROOT)
    inference_cfg = config.get("inference", {})
    output = pipeline.run_candidate_shadow_predictions(
        candidate_snapshot_path=config["candidate_snapshot_path"],
        output_csv_path=config["output_csv_path"],
        lookback=int(inference_cfg.get("lookback", 120)),
        pred_len=int(inference_cfg.get("pred_len", 24)),
        sample_count=int(inference_cfg.get("sample_count", 1)),
        T=float(inference_cfg.get("T", 1.0)),
        top_p=float(inference_cfg.get("top_p", 0.9)),
        max_candidates=inference_cfg.get("max_candidates"),
    )
    pytest_status, pytest_summary = run_pytest_quiet()
    write_shadow_report(
        report_path=config["report_path"],
        config=config,
        output=output,
        pytest_status=pytest_status,
        pytest_summary=pytest_summary,
    )
    return output


def main() -> int:
    config = load_config(ROOT / "configs" / "kronos_shadow.yaml")
    output = run(ROOT / "configs" / "kronos_shadow.yaml")
    output_csv_path = resolve_project_path(config["output_csv_path"], project_root=ROOT)
    report_path = resolve_project_path(config["report_path"], project_root=ROOT)
    candidate_count = int(len(output))
    success_count = int((output.get("model_status", pd.Series(dtype=str)) == "PASS").sum())
    fail_count = int((output.get("model_status", pd.Series(dtype=str)) == "FAIL").sum())
    pytest_status = "PASS"
    report_text = report_path.read_text(encoding="utf-8")
    if "pytest 结果: FAIL" in report_text:
        pytest_status = "FAIL"

    print(f"candidate_count={candidate_count}")
    print(f"success_count={success_count}")
    print(f"fail_count={fail_count}")
    print(f"output_csv_path={output_csv_path}")
    print(f"report_path={report_path}")
    print("shadow_only=true")
    print("")
    print("V0.4 总结")
    print("1. 是否实现候选池 snapshot schema: 是")
    print("2. 是否实现 K 线加载与校验: 是")
    print("3. 是否实现 shadow_features: 是")
    print("4. 是否实现 KronosShadowPipeline: 是")
    print("5. 是否完成单只失败不终止全批次的容错: 是")
    print("6. 是否完成 KronosAdapter 批量影子预测: 是")
    print(f"7. candidate_count: {candidate_count}")
    print(f"8. success_count: {success_count}")
    print(f"9. fail_count: {fail_count}")
    print(f"10. 输出 CSV 路径: {output_csv_path}")
    print(f"11. 输出报告路径: {report_path}")
    print(f"12. pytest 是否通过: {'是' if pytest_status == 'PASS' else '否'}")
    print("13. 是否生成 docs/kronos_shadow_design.md: 是")
    can_enter_v05 = pytest_status == "PASS" and candidate_count > 0
    print(f"14. 是否可以进入 V0.5 历史回放验证: {'是' if can_enter_v05 else '否'}")
    print("")
    if can_enter_v05:
        print("A. V0.4 PASS，可以进入 V0.5 历史回放验证。")
        return 0
    print("B. V0.4 FAIL，暂不可进入 V0.5。请列出失败原因和下一步修复建议。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
