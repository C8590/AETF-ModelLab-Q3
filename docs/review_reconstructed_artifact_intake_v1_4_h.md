# Review: Reconstructed Artifact Intake V1.4-H

## 审查对象

审查分支：

```text
modellab-v1-4-h-reconstructed-artifact-intake
```

审查 commit hash：

```text
0f13f1deebf42cc7366ff3a8510155194b88e1b1
```

说明：该 hash 是被审查的开发侧 intake commit。复审开始时，远端分支
`modellab-v1-4-h-reconstructed-artifact-intake` 的 HEAD 已推进到已有复审提交：

```text
b60deb5ea256ae01b2898d28e0bb831b6cf75a86
```

因此本报告按开发侧 commit `0f13f1deebf42cc7366ff3a8510155194b88e1b1`
审查 intake 改动范围，并同时确认当前分支额外包含本复审报告文件。

远端：

```text
origin https://github.com/C8590/AETF-ModelLab-Q3.git
```

审查前 git status：

```text
## modellab-v1-4-h-reconstructed-artifact-intake...origin/modellab-v1-4-h-reconstructed-artifact-intake
```

开发侧 intake commit 已确认存在于当前分支历史：

```text
0f13f1deebf42cc7366ff3a8510155194b88e1b1
```

复审开始时分支 HEAD：

```text
b60deb5ea256ae01b2898d28e0bb831b6cf75a86
```

## 改动范围摘要

`main...0f13f1deebf42cc7366ff3a8510155194b88e1b1` 的开发侧改动范围为：

```text
.gitignore
docs/reconstructed_artifact_intake_v1_4_h.md
scripts/intake_reconstructed_artifacts.py
```

diff stat：

```text
3 files changed, 396 insertions(+)
```

当前分支相对 `main` 额外包含本复审报告：

```text
docs/review_reconstructed_artifact_intake_v1_4_h.md
```

确认事项：

- 仅新增/修改 `.gitignore`、intake 文档、intake 脚本。
- 未提交 `runtime_intake/`。
- 未提交 `outputs/reconstructed_artifacts` runtime 输出。
- 未提交 quarantine 文件。
- 未提交 READY zip、READY payload 或正式 replay outputs。
- 未提交模型权重或训练输出。
- 未修改 LeftLab。
- 未修改 Protocol。
- 未发现训练、`torchrun`、GPU 调用。
- 未声明 `formal_v011_ready` 通过。

## Intake 脚本结论

审查文件：

```text
scripts/intake_reconstructed_artifacts.py
```

结论：通过。

脚本行为与本阶段边界一致：

- 使用 `E:/AETF-ModelLab-Q3-quarantine` 作为 quarantine 只读来源。
- 不修改、不删除、不重命名 quarantine 文件。
- 复制目标为 `runtime_intake/reconstructed_v1_quarantine/`。
- 生成 `outputs/reconstructed_artifacts/intake_index.json`。
- 生成 `outputs/reconstructed_artifacts/intake_index.csv`。
- 记录 `source_sha256`。
- 记录 `copied_sha256`。
- 使用 `copied_sha256 == source_sha256` 判定 checksum pass/fail。
- 记录 source/destination path、source workspace、copy mode、modified time、size 等 provenance 字段。
- 记录 `artifact_role_guess`。
- 记录 `confidence` 和 `reason`。
- `usable_for_formal_v011_replay` 固定为 `false`。
- `formal_v011_ready` 固定为 `false`。
- `stopline_triggered` 固定为 `true`。
- 不训练模型。
- 不导入或调用 torch。
- 不运行 `torchrun`。
- 不调用 GPU。
- 不自动启动 replay。
- 不把 intake artifact 标记为 formal_v011 ready。

脚本依赖 `scripts/audit_reconstructed_artifacts.py` 的候选识别口径。该依赖仅扫描并读取 clean/quarantine 中的候选文件，计算 checksum，写 clean workspace 下 ignored `outputs/` 审计输出；未发现 quarantine 写操作。

## Intake 文档结论

审查文件：

```text
docs/reconstructed_artifact_intake_v1_4_h.md
```

结论：通过。

文档准确记录：

- 本阶段目标是 controlled intake，不是 formal replay。
- quarantine 来源为 `E:\AETF-ModelLab-Q3-quarantine`。
- 正式工作区为 `E:\AETF-ModelLab-Q3`。
- 受控引入规则为只读 quarantine、checksum、provenance、ignored runtime copy、role guess、intake index。
- copied artifact count 为 38。
- checksum pass/fail 为 38 / 0。
- candidate role marker 分类统计。
- high confidence count 为 27。
- `reconstructed_artifacts_status = QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED`。
- `formal_v011_ready = false`。
- `stopline_triggered = true`。
- remaining stopline reasons 包含 `reconstructed_artifacts_pending_review` 与 `realized_outcome_fields_missing`。
- 仍不能 formal_v011 replay 的原因。
- 未训练、不 GPU、不伪造声明、不自动接入主项目。

## Intake 结果复核

运行：

```text
python scripts/intake_reconstructed_artifacts.py
```

输出 summary：

```text
intake_candidate_count = 38
copied_artifact_count = 38
checksum_pass_count = 38
checksum_fail_count = 0
candidate_history_candidates_count = 27
decision_matrix_candidates_count = 3
closeout_candidates_count = 7
artifact_index_candidates_count = 3
high_confidence_count = 27
reconstructed_artifacts_status = QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_artifacts_pending_review",
  "realized_outcome_fields_missing"
]
```

结论：

- copied artifact count 结论：38，符合预期。
- checksum pass/fail 结论：38 / 0，符合预期。
- candidate_history candidates 结论：27，符合预期。
- decision_matrix candidates 结论：3，符合预期。
- closeout candidates 结论：7，符合预期。
- artifact_index candidates 结论：3，符合预期。
- high confidence count 结论：27，符合预期。
- `reconstructed_artifacts_status` 结论：推进到 `QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED` 合理。
- `formal_v011_ready` 结论：仍为 `false`，合理。
- `stopline_triggered` 结论：仍为 `true`，合理。
- remaining stopline reasons 结论：保留 `reconstructed_artifacts_pending_review` 合理，且至少包含 `realized_outcome_fields_missing`。

## 状态推进审查

从：

```text
CANDIDATE_FOUND_IN_QUARANTINE_REVIEW_REQUIRED
```

推进到：

```text
QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED
```

是合理的。该推进只表示 quarantine candidates 已完成 ignored intake copy、checksum 与 provenance index，不表示 reconstructed artifacts 已完成 provenance review，也不表示 formal replay readiness。

不得推进到：

```text
READY_FOR_FORMAL_V011_REPLAY
```

理由：

- reconstructed artifacts 仍需 provenance review。
- intake copy 位于 ignored runtime 目录，不是正式 artifact registry。
- `realized_outcome_fields_missing` 仍未解除。
- stopline 仍触发。
- 本阶段没有执行 alignment preparation 的正式验收。

## 边界复核

是否发现训练模型：否。

是否发现 `torchrun`：否。

是否发现 GPU 调用：否。

是否发现 quarantine 被修改：否。

是否发现 `runtime_intake` 被提交：否。

是否发现 `outputs/reconstructed_artifacts` 被提交：否。

是否发现 READY zip / payload 被提交：否。

是否发现模型权重或训练输出被提交：否。

是否修改 LeftLab：否。

是否修改 Protocol：否。

是否声明 `formal_v011_ready` 通过：否。

## Runtime 提交检查

运行：

```text
git ls-files runtime_intake outputs/reconstructed_artifacts
```

输出为空。结论：`runtime_intake` 与 `outputs/reconstructed_artifacts` 没有被 git 跟踪或提交。

生成物状态检查显示：

```text
!! outputs/
!! runtime_intake/
```

结论：运行期生成物被 ignore，不进入本次提交。

## 验证结果

运行：

```text
$env:PYTHONPATH='.;src'; pytest
```

结果：

```text
collected 0 items
no tests ran
```

结论：无测试可运行。

运行：

```text
python -m py_compile scripts/audit_reconstructed_artifacts.py
python -m py_compile scripts/intake_reconstructed_artifacts.py
```

结果：均通过。

运行：

```text
python scripts/intake_reconstructed_artifacts.py
```

结果：通过，输出 summary 与文档记录一致。

## 合并与下一阶段建议

建议合并 `modellab-v1-4-h-reconstructed-artifact-intake` 到 `main`。

Track A2 受控引入完成。

reconstructed artifacts 已从 quarantine 完成 checksum/provenance/read-only intake。

当前仍不可 `formal_v011` replay。

下一步建议做 reconstructed artifact provenance review / alignment preparation。
