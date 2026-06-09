# Reconstructed Artifact Provenance Review and Alignment Prep for LeftLab V1.4-I

## 本阶段目标

Track A3 执行 reconstructed artifact provenance review / alignment preparation。

目标是复核 A2 intake artifacts 的 provenance、checksum、readability 和结构特征，
并准备 reconstructed alignment 的候选输入清单。本阶段只做准备，不启动
reconstructed alignment，不启动 `formal_v011`，不训练模型，不运行 `torchrun`，
不调用 GPU，不修改 LeftLab，不修改 Protocol，不提交 runtime intake 或 outputs。

## 输入来源

正式工作区：

```text
E:\AETF-ModelLab-Q3
```

A2 ignored runtime intake：

```text
runtime_intake/reconstructed_v1_quarantine/
```

A2 intake index：

```text
outputs/reconstructed_artifacts/intake_index.json
```

旧 quarantine 来源仅作为 A2 index 中的 provenance 字段存在：

```text
E:\AETF-ModelLab-Q3-quarantine
```

本阶段没有使用 quarantine 作为开发目录，没有修改 quarantine，也没有复制新的
quarantine artifact 到正式 tracked 目录。

## Provenance 审查规则

执行脚本：

```text
scripts/review_reconstructed_artifact_provenance.py
```

脚本只读 `intake_index.json` 和 `runtime_intake/`，检查每条 intake record：

- `source_path` 是否来自 `E:\AETF-ModelLab-Q3-quarantine`
- `destination_path` 是否位于 `runtime_intake/reconstructed_v1_quarantine/`
- `source_workspace == quarantine`
- `copy_mode == read_only_intake`
- `source_sha256` 存在
- `copied_sha256` 存在
- `source_sha256 == copied_sha256`
- copied file 当前 SHA-256 与 index 中 `copied_sha256` 一致
- copied file 当前 size 与 index 中 `size_bytes` 一致
- `modified_time` 存在
- `artifact_role_guess` 存在
- `confidence` 存在
- `reason` 存在
- `intake_status == copied_checksum_pass`

运行期输出：

```text
outputs/reconstructed_artifacts/provenance_review.json
outputs/reconstructed_artifacts/provenance_review.csv
outputs/reconstructed_artifacts/alignment_candidate_map.json
outputs/reconstructed_artifacts/alignment_candidate_map.csv
```

这些输出位于 ignored `outputs/` 下，不提交。

## Checksum 复核结果

```text
intake_index_readable = true
provenance_reviewed_count = 38
checksum_pass_count = 38
checksum_fail_count = 0
duplicate_hash_count = 0
duplicate_hash_record_count = 0
```

结论：A2 intake index 可读；38 条 intake records 均完成 provenance/checksum 复核；
source/copy/index/current copied file hash 一致；未发现重复 SHA-256；未发现 checksum
失败。

## Candidate History 结构审查结果

```text
candidate_history_readable_count = 27
```

检查项包括文件格式、行数、字段 token、reconstructed snapshot marker、true-left
区分标记、空文件/损坏文件，以及高可信候选。

结构扫描发现 candidate_history 候选可读；其中最适合作为下一阶段 precheck 候选的
artifact 是：

```text
data/real/reconstructed/left_candidates_history_RECONSTRUCTED.csv
```

该候选：

- provenance pass
- checksum pass
- copied file readable
- role confidence high
- path 明确指向 reconstructed candidate history
- source/copy SHA-256：

```text
475d34a25fc10f94c560aec33dce0d6b12f1056a26904867598e162981112de6
```

本阶段没有把 reconstructed candidate history 改写为 true-left history。

## Decision Matrix 结构审查结果

```text
decision_matrix_readable_count = 3
```

检查项包括文件格式、decision/predicted/actual/direction/confidence/score 等可识别
字段，以及是否可与 candidate history 形成候选对应关系。

本阶段选出的 alignment precheck 候选 decision matrix artifact：

```text
outputs/kronos_v15r_next_step_decision_matrix.json
```

该候选 provenance pass、checksum pass、copied file readable，并且路径明确指向
decision matrix。它仍只是 precheck 候选，不是 formal replay 输入。

## Closeout 结构审查结果

```text
closeout_readable_count = 7
```

检查项包括是否记录 reconstructed closeout、是否包含 stopline 语义、是否包含
direction accuracy / majority direction accuracy 相关证据，以及是否支持 provenance
解释。

本阶段选出的 alignment precheck 候选 closeout artifact：

```text
outputs/kronos_v15r_reconstructed_closeout.json
```

该候选 provenance pass、checksum pass、copied file readable，并且路径明确指向
reconstructed closeout。

## Artifact Index 结构审查结果

```text
artifact_index_readable_count = 3
```

检查项包括是否能索引 candidate_history、decision_matrix、metrics、closeout，以及
是否能与 intake index 中的文件名、hash 或路径对应。

本阶段选出的 alignment precheck 候选 artifact index：

```text
outputs/kronos_v15r_reconstructed_artifact_index.json
```

该候选 provenance pass、checksum pass、copied file readable，并且路径明确指向
reconstructed artifact index。

## Alignment Candidate Map 摘要

生成 1 个候选输入清单：

```text
candidate_set_id = reconstructed_v1_quarantine_primary
candidate_history_artifact = data/real/reconstructed/left_candidates_history_RECONSTRUCTED.csv
decision_matrix_artifact = outputs/kronos_v15r_next_step_decision_matrix.json
closeout_artifact = outputs/kronos_v15r_reconstructed_closeout.json
artifact_index_artifact = outputs/kronos_v15r_reconstructed_artifact_index.json
provenance_status = pass
role_confidence = high
structural_readability = readable
alignment_candidate_status = alignment_precheck_candidate
recommended_for_alignment_precheck = true
```

状态：

```text
alignment_preparation_status = PROVENANCE_REVIEW_COMPLETED_ALIGNMENT_PRECHECK_READY
selected_alignment_candidate_set_count = 1
recommended_alignment_precheck_count = 1
```

这表示证据足以建议进入下一阶段 alignment precheck。它不表示 alignment 已运行，
不表示 replay 已完成，也不表示可以进入 `formal_v011`。

## 为什么本阶段仍不可 formal_v011 replay

原因：

- 本阶段只做 provenance review / alignment preparation
- reconstructed alignment 未运行
- selected candidate set 仍需总控审查
- copied artifacts 仍位于 ignored runtime intake
- outputs/reconstructed_artifacts 仍是 runtime review 输出，不是正式 registry
- `realized_outcome_fields_missing` 仍未解除
- 不得将 intake artifacts 直接标记为 formal replay ready

本阶段没有输出任何 formal replay ready 状态。

## Readiness / Stopline

本阶段保持：

```text
reconstructed_artifacts_status = QUARANTINE_INTAKE_COMPLETED_REVIEW_REQUIRED
alignment_preparation_status = PROVENANCE_REVIEW_COMPLETED_ALIGNMENT_PRECHECK_READY
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_alignment_not_run",
  "realized_outcome_fields_missing"
]
```

## Boundary Statement

本阶段未启动 reconstructed alignment，未启动 `formal_v011`，未训练模型，未运行
`torchrun`，未调用 GPU，未修改 quarantine，未修改 LeftLab，未修改 Protocol，未提交
runtime_intake，未提交 outputs/reconstructed_artifacts runtime，未提交 READY zip，未提交
payload，未提交模型权重，未提交训练输出，未伪造 reconstructed artifacts，未声明
`formal_v011_ready` 通过，未自动接入主项目。
