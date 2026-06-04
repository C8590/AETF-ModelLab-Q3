# LeftLab Candidate Snapshot Export Patch Plan

## Scope

这是给 `AETF-LeftLab` 的未来补丁计划。当前 V0.16-L 阶段只在 `AETF-ModelLab` 内定义契约、汇总脚本、配置和测试，不修改 `AETF-LeftLab`。

## Future Patch Proposal

用户明确授权后，建议在左侧项目完成每日候选池生成后调用一个 exporter。该 exporter 只把当日候选池写成 CSV，不改变候选池生成逻辑，不调整排序，不补写历史，不读取 ModelLab。

推荐输出路径：

`E:\AETF-LeftLab\exports\candidate_snapshots\YYYY-MM-DD_left_candidates.csv`

推荐字段：

| Field | Description |
| --- | --- |
| `as_of_date` | 候选池生成日期。 |
| `symbol` | ETF 代码。 |
| `display_name` | ETF 名称。 |
| `candidate_rank` | 左侧系统当日排序。 |
| `left_score` | 左侧系统当日分数。 |
| `notes` | 来源说明，建议为 `true_left_snapshot_export`。 |

## Safety Requirements

- exporter 只写 CSV。
- exporter 不改变候选池逻辑。
- exporter 不接交易接口。
- exporter 不下单。
- exporter 不产生交易建议。
- exporter 不回写 ModelLab。
- 左侧项目补丁必须在用户授权后单独执行。
