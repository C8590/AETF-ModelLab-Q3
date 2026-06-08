# Reconstructed Artifact Intake for LeftLab V1.4-H

## 本阶段目标

Track A2 执行受控引入 quarantine reconstructed candidates。

目标是只读读取 quarantine 中已经被 Track A 审计识别的 reconstructed
artifact candidates，计算 checksum，记录 provenance，并复制到正式工作区
ignored runtime intake 目录：

```text
runtime_intake/reconstructed_v1_quarantine/
```

本阶段不启动 `formal_v011`，不直接 replay，不训练模型，不运行 `torchrun`，
不调用 GPU，不修改 LeftLab，不修改 Protocol，不伪造 reconstructed artifacts，
不提交 copied artifacts。

## Quarantine 来源

只读来源：

```text
E:\AETF-ModelLab-Q3-quarantine
```

正式工作区：

```text
E:\AETF-ModelLab-Q3
```

旧 quarantine 工作区没有作为开发目录使用。本阶段仅从该目录读取候选文件并计算
checksum，不修改、不删除、不重命名 quarantine 文件。

Track A 审计记录的基线：

```text
artifact candidates = 41
quarantine candidate count = 38
quarantine runtime artifact candidates = 28
candidate_history = found
decision_matrix = found
closeout = found
artifact_index = found
```

Track A 审查报告合入 main 后，复跑审计时 clean documentation candidate 增加 1，
因此 total artifact candidates 可显示为 42；本阶段 intake 仅使用 quarantine 侧
38 个候选，不复制 clean 文档候选。

## 受控引入规则

执行脚本：

```text
scripts/intake_reconstructed_artifacts.py
```

脚本行为：

- 复用 `scripts/audit_reconstructed_artifacts.py` 的 quarantine 候选识别口径
- 只读扫描 `E:\AETF-ModelLab-Q3-quarantine`
- 将 quarantine 候选复制到 `runtime_intake/reconstructed_v1_quarantine/`
- 保留源相对路径，避免 misleading rename
- 复制前记录 `source_sha256`
- 复制后记录 `copied_sha256`
- 要求 `copied_sha256 == source_sha256`
- 生成 ignored runtime index/CSV
- 不把 intake artifact 标记为 formal replay ready
- 不提交 `runtime_intake/`

运行期输出：

```text
outputs/reconstructed_artifacts/intake_index.json
outputs/reconstructed_artifacts/intake_index.csv
```

这些输出位于 ignored `outputs/` 下，不提交。

## Intake 结果

```text
intake_candidate_count = 38
copied_artifact_count = 38
checksum_pass_count = 38
checksum_fail_count = 0
```

checksum 结论：全部 copied checksum 与 source checksum 一致。

## 角色分类

按候选标记统计：

```text
candidate_history_candidates_count = 27
decision_matrix_candidates_count = 3
closeout_candidates_count = 7
artifact_index_candidates_count = 3
```

按 primary role guess 统计：

```text
reconstructed_candidate_history_candidate = 27
reconstructed_closeout_candidate = 1
reconstructed_metrics_candidate = 5
unknown_reconstructed_candidate = 5
```

confidence 统计：

```text
high_confidence_count = 27
medium_confidence_count = 6
low_confidence_count = 5
```

高可信候选主要来自明确包含 reconstructed context 与 candidate_history marker 的文件。
decision_matrix、closeout、artifact_index 候选已发现，但仍需人工 provenance 审查后
才能进入后续 alignment / replay 判定。

## Intake Status

本阶段状态推进为：

```text
reconstructed_artifacts_status = QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED
```

该状态仅表示 quarantine candidates 已完成 ignored intake copy 和 checksum 验证。
它不表示 artifact 已可信，不表示可直接用于 formal replay，也不表示 stopline 解除。

## 是否足以进入下一阶段 reconstructed alignment

本阶段结果足以提交审查，以决定是否进入下一阶段 reconstructed alignment 准备。

但在总控审查前，仍不得自动启动 reconstructed alignment，不得接入主项目，不得用于
`formal_v011` replay。下一阶段至少还需要 provenance 审查、候选 lineage 核对、
artifact role 复核，以及 alignment 输入边界确认。

## 为什么仍不直接 formal_v011 replay

原因：

- quarantine 来源不是 clean 正式工作区
- quarantine 工作区历史状态仍需 provenance 审查
- copied artifacts 位于 ignored runtime intake 目录
- intake index 只是 checksum/provenance 记录，不是正式 artifact registry
- candidate_history 类型仍需保持 reconstructed/not true-left 语义
- `realized_outcome_fields_missing` 仍未解除
- reconstructed candidates 仍需要 review

因此本阶段不得推进为：

```text
READY_FOR_FORMAL_V011_REPLAY
```

## Readiness / Stopline

本阶段保持：

```text
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_artifacts_pending_review",
  "realized_outcome_fields_missing"
]
```

## Boundary Statement

本阶段未训练模型，未运行 `torchrun`，未调用 GPU，未修改 quarantine，未修改
LeftLab，未修改 Protocol，未提交 runtime copied artifacts，未提交 runtime payload，
未提交模型权重，未提交 READY zip，未伪造 reconstructed artifacts，未声明
`formal_v011_ready` 通过，未自动接入主项目。
