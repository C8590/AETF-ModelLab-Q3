# Review: Reconstructed Artifacts Audit for LeftLab V1.4-G

## 审查对象

- 审查分支：`modellab-v1-4-g-reconstructed-artifacts`
- 审查 commit hash：`774fb238a7db81707aa4f5a2ff2e57a0dbc2ff6f`
- 远端状态：分支已同步 `origin/modellab-v1-4-g-reconstructed-artifacts`
- 审查前 git status：clean

## 改动范围摘要

`main...modellab-v1-4-g-reconstructed-artifacts` 仅新增 2 个文件：

- `docs/reconstructed_artifacts_leftlab_v1_4_g.md`
- `scripts/audit_reconstructed_artifacts.py`

diff 统计：

```text
 docs/reconstructed_artifacts_leftlab_v1_4_g.md | 230 ++++++++++++++++
 scripts/audit_reconstructed_artifacts.py       | 350 +++++++++++++++++++++++++
 2 files changed, 580 insertions(+)
```

未发现提交 quarantine 文件、runtime outputs、READY zip、payload、模型权重或训练输出。未发现 LeftLab / Protocol 修改。

## 审计脚本结论

`scripts/audit_reconstructed_artifacts.py` 审查通过。

确认事项：

- 只读扫描 clean 工作区 `E:\AETF-ModelLab-Q3`
- 只读扫描 quarantine 工作区 `E:\AETF-ModelLab-Q3-quarantine`
- 不修改 quarantine
- 不复制 quarantine artifacts
- 不将 quarantine artifacts 登记为正式 artifacts
- 不伪造 reconstructed_v1 artifacts
- 仅输出 ignored runtime index/CSV：
  - `outputs/reconstructed_artifacts/reconstructed_artifact_index.json`
  - `outputs/reconstructed_artifacts/reconstructed_artifact_candidates.csv`
- 不训练模型
- 不运行 `torchrun`
- 不导入或调用 `torch`
- 不调用 GPU

脚本生成的 runtime 输出命中 `.gitignore` 的 `outputs/` 规则，未纳入提交。

## 审计文档结论

`docs/reconstructed_artifacts_leftlab_v1_4_g.md` 审查通过。

文档准确记录了：

- 本阶段为 audit-only
- 查找范围包含 clean 工作区和只读 quarantine 工作区
- clean 工作区未找到 usable reconstructed_v1 artifacts
- quarantine 中只读发现候选 artifacts
- artifact 候选数量
- candidate_history / decision_matrix / closeout / artifact_index 候选情况
- `reconstructed_artifacts_status`
- clean 工作区仍 missing 的原因
- quarantine artifacts 不能直接用于 formal replay 的原因
- 下一步受控引入要求
- `formal_v011_ready` 仍为 false
- `stopline_triggered` 仍为 true
- remaining stopline reasons
- 不训练、不 GPU、不伪造声明

未发现文档将 true-left replay files 误标为 reconstructed_v1 artifacts。未发现因 quarantine 候选存在而声明 stopline 已解除。

## Artifact 审查结论

- clean 工作区 reconstructed artifacts 结论：未找到正式可用 reconstructed_v1 artifacts
- quarantine 候选 artifacts 结论：只读发现候选 artifacts，但仅可作为下一阶段受控引入候选
- artifact 候选数量结论：总计 41
- clean runtime artifact candidate 数量：0
- quarantine runtime artifact candidate 数量：28
- clean candidate_history：无
- clean decision_matrix：无
- clean closeout：无
- clean artifact_index：无
- quarantine candidate_history：有候选
- quarantine decision_matrix：有候选
- quarantine closeout：有候选
- quarantine artifact_index：有候选

`reconstructed_artifacts_status` 结论：

```text
CANDIDATE_FOUND_IN_QUARANTINE_REVIEW_REQUIRED
```

quarantine 候选未被复制、未被登记为正式 artifact、未被标记为可直接用于 `formal_v011` replay。

## Readiness / Stopline

- `formal_v011_ready` 仍为 false
- `stopline_triggered` 仍为 true
- remaining stopline reasons：
  - `reconstructed_artifacts_missing`
  - `realized_outcome_fields_missing`

未发现声明 `formal_v011_ready=true`。未发现声明可以主项目接入。未发现将 quarantine artifacts 直接视作可信正式 artifacts。

## 禁区检查

- 是否发现训练模型：否
- 是否发现 `torchrun`：否
- 是否发现 GPU 调用：否
- 是否发现 quarantine 文件被提交：否
- 是否发现 runtime outputs 被提交：否
- 是否发现 READY zip 被提交：否
- 是否发现 payload 被提交：否
- 是否发现 LeftLab / Protocol 修改：否

## 验证结果

运行命令：

```text
$env:PYTHONPATH='.;src'; pytest
```

结果：`collected 0 items`，记录为无测试可运行；这不是测试通过。

运行命令：

```text
python -m py_compile scripts/audit_reconstructed_artifacts.py
```

结果：通过。

运行命令：

```text
python scripts/audit_reconstructed_artifacts.py
```

结果：通过，输出摘要与审计文档一致：

```text
clean_candidate_count = 3
clean_runtime_artifact_candidate_count = 0
quarantine_candidate_count = 38
quarantine_runtime_artifact_candidate_count = 28
artifact_candidate_count = 41
clean_reconstructed_artifacts_found = false
quarantine_candidate_artifacts_found = true
reconstructed_artifacts_status = CANDIDATE_FOUND_IN_QUARANTINE_REVIEW_REQUIRED
formal_v011_ready = false
stopline_triggered = true
```

## 合并建议

建议合并 `modellab-v1-4-g-reconstructed-artifacts` 到 `main`。

Track A 审计完成。

clean 工作区仍缺正式 reconstructed artifacts。

quarantine 中发现候选 artifacts，但不能直接作为正式 replay 输入。

下一步建议进入受控引入阶段，做 checksum / provenance / read-only copy / 审查。
