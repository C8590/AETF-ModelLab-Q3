# Majority Baseline Review for LeftLab V1.4-D Replay

## Review Scope

审查分支：

```text
modellab-v1-4-f-majority-baseline
```

审查 commit hash：

```text
84955f53a02d79bc7cc8592197daf68a7882a1cc
```

审查目标：复审 Track B majority baseline remediation，确认该分支仅为
LeftLab V1.4-D true-left candidate history replay 建立 majority baseline，
不训练模型、不运行 torchrun、不调用 GPU、不修改 LeftLab、不修改 Protocol、
不接入主项目、不声明 `formal_v011_ready=true`。

## Git Status

审查前同步结果：

```text
On branch modellab-v1-4-f-majority-baseline
Your branch is up to date with 'origin/modellab-v1-4-f-majority-baseline'.

nothing to commit, working tree clean
```

HEAD 已确认等于：

```text
84955f53a02d79bc7cc8592197daf68a7882a1cc
```

远端：

```text
origin https://github.com/C8590/AETF-ModelLab-Q3.git
```

## Change Summary

`main...modellab-v1-4-f-majority-baseline` 的改动范围：

```text
.gitignore
docs/majority_baseline_leftlab_v1_4_d.md
scripts/build_majority_baseline.py
```

统计：

```text
3 files changed, 534 insertions(+)
```

审查结论：改动范围符合 Track B 要求，仅新增/修改 ignore 规则、baseline 文档、
只读 baseline 脚本。

未发现以下内容被提交：

```text
runtime_inbox/
READY zip
outputs/baseline/
outputs/replay/
runtime payload
model weights
training outputs
```

未发现 LeftLab 或 Protocol 文件被修改。

## Baseline Script Review

脚本：

```text
scripts/build_majority_baseline.py
```

审查结论：通过。

确认事项：

```text
只读 runtime_inbox/leftlab_v1_4_d_ready_handoff/
只读 outputs/replay/leftlab_v1_4_d/
输出到 ignored outputs/baseline/leftlab_v1_4_d/
不修改 handoff payload
不导入 torch
不调用 GPU / cuda
不运行 torchrun
不训练模型
可重复运行
不生成交易建议
不自动接入主项目
```

脚本输出包括：

```text
outputs/baseline/leftlab_v1_4_d/majority_baseline_report.json
outputs/baseline/leftlab_v1_4_d/majority_baseline_report.csv
outputs/baseline/leftlab_v1_4_d/majority_baseline_summary.md
```

这些文件是 runtime 输出，已由 `.gitignore` 排除，不应提交。

## Baseline Document Review

文档：

```text
docs/majority_baseline_leftlab_v1_4_d.md
```

审查结论：通过。

文档准确记录了：

```text
本阶段目标
输入 handoff / replay 来源
decision majority baseline
label_status majority baseline
risk bucket majority baseline
neutral baseline
majority_baseline_available = partial
directional_baseline_available = false
outcome_based_baseline_available = false
formal_v011_ready_support = false
不能支持 formal_v011_ready=true 的原因
剩余 stopline reasons
不训练、不 GPU、不交易建议声明
```

文档没有把 pending label 当作 realized outcome，没有把 risk bucket 当作真实收益方向，
没有把 majority baseline 写成模型胜率，也没有声明 `formal_v011_ready=true`。

## Baseline Result Review

生成的 `majority_baseline_report.json` 可读，结论如下：

```text
candidate_count = 20
```

decision majority baseline：

```text
majority_decision = unknown
majority_decision_count = 20
majority_decision_rate = 1.0
distribution = unknown: 20
```

label_status majority baseline：

```text
majority_label_status = pending
majority_label_status_count = 20
majority_label_status_rate = 1.0
distribution = pending: 20
```

risk bucket majority baseline：

```text
majority_risk_bucket = 风险偏高
majority_risk_bucket_count = 11
majority_risk_bucket_rate = 0.55
distribution = 样本不足: 9, 风险偏高: 11
```

availability / readiness：

```text
majority_baseline_available = partial
directional_baseline_available = false
outcome_based_baseline_available = false
formal_v011_ready_support = false
formal_v011_ready = false
stopline_triggered = true
```

审查结论：formal_v011_ready 仍为 false 合理；stopline 仍应保持 triggered。

## Remaining Stopline Reasons

Track B 已完成 majority baseline remediation，但仍保留以下 stopline reasons：

```text
reconstructed_artifacts_missing
realized_outcome_fields_missing
```

## Boundary Review

未发现：

```text
训练模型
torchrun
GPU / cuda 调用
runtime payload 提交
READY zip 提交
outputs/baseline 或 outputs/replay runtime 输出提交
LeftLab 修改
Protocol 修改
交易建议
formal_v011_ready 通过声明
自动接入主项目
```

## Verification

运行：

```text
$env:PYTHONPATH='.;src'; pytest
```

结果：

```text
collected 0 items
no tests ran
```

结论：无测试可运行；不记录为测试通过。

运行：

```text
python -m py_compile scripts/build_majority_baseline.py
```

结果：通过。

运行：

```text
python scripts/build_majority_baseline.py
```

结果：通过，生成 runtime-only baseline JSON/CSV/MD，并确认 JSON 可读。

## Review Recommendation

建议合并 `modellab-v1-4-f-majority-baseline` 到 `main`。

Track B 已完成 majority baseline remediation。

`formal_v011_ready` 仍为 false。

stopline 仍触发。

下一步建议进入 Track A：reconstructed artifacts。
