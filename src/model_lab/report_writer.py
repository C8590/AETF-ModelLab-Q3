from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def write_shadow_report(shadow: pd.DataFrame, output_path: str | Path) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Kronos AI 影子判断日报",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    if shadow.empty:
        lines.append("无影子判断结果。")
    else:
        counts = shadow.get("kronos_shadow_action", pd.Series(dtype=str)).value_counts(dropna=False)
        lines.extend(["## 动作分布", ""])
        for action, count in counts.items():
            lines.append(f"- {action}: {count}")
        lines.extend(["", "## 明细", ""])
        for _, row in shadow.iterrows():
            lines.append(
                f"- {row.get('trade_date')} {row.get('code')} {row.get('name', '')}: "
                f"{row.get('kronos_shadow_action')}；{row.get('kronos_explanation')}"
            )
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
