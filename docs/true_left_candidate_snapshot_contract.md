# True Left Candidate Snapshot Contract

## Purpose

正式 V0.11 必须依赖真实 `left_candidates_history.csv`，因为 V0.11 的 replay case 需要还原左侧系统在每个历史日期实际给出的候选池。只有真实候选池快照才能表达当日左侧排序、左侧分数、人工或系统来源说明，以及当时可见的信息边界。

`reconstructed_v1` 分支已经正式暂停，结论为 `PAUSED_BY_STOPLINE`。该分支通过 K 线和研究规则重建候选池，只能用于研究诊断，不能证明左侧系统当日真的产出过这些候选。因此 reconstructed 数据不能替代真实左侧历史，不能冒充正式 `left_candidates_history.csv`，也不能作为正式 V0.11 的输入。

## Daily Snapshot Schema

左侧项目未来每日候选池快照 CSV 必须包含且只推荐使用以下标准字段：

| Field | Description |
| --- | --- |
| `as_of_date` | 候选池生成日期，格式建议为 `YYYY-MM-DD`。 |
| `symbol` | ETF 代码。 |
| `display_name` | ETF 名称。 |
| `candidate_rank` | 左侧系统当日排序，正整数，数值越小表示排名越靠前。 |
| `left_score` | 左侧系统当日分数。 |
| `notes` | 来源说明，例如 `true_left_snapshot_export`。 |

## Recommended LeftLab Export

- 推荐左侧输出目录：`E:\AETF-LeftLab\exports\candidate_snapshots\`
- 推荐每日快照命名：`YYYY-MM-DD_left_candidates.csv`
- 示例文件名：`2026-06-04_left_candidates.csv`

左侧项目只负责导出 CSV 文件，不改变候选池逻辑，不回写 ModelLab，不接交易接口，不下单，不产生交易建议。

## ModelLab Intake

- ModelLab 本地快照目录：`E:\AETF-ModelLab\data\real\raw\candidates\snapshots\`
- ModelLab 汇总目标文件：`E:\AETF-ModelLab\data\real\raw\candidates\left_candidates_history.csv`
- ModelLab 只读取 CSV 快照，不读取 `E:\AETF-LeftLab`，不访问主项目数据库，不回写主项目。
- 如果快照目录为空，ModelLab 必须返回 `SNAPSHOT_DIR_EMPTY`，并且不得生成假的 `left_candidates_history.csv`。

## Safety Boundary

- 左侧只导出 CSV。
- ModelLab 只读取 CSV。
- 不回写主项目。
- 不接交易。
- 不下单。
- 不产生交易建议。
- 不把 reconstructed 数据冒充真实历史。
- 不提交 raw K 线大文件、`.venv`、`models/kronos`、`external/Kronos`、checkpoint 或权重文件。
