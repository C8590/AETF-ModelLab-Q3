# Left Candidate History Intake Plan

## 作用

`left_candidates_history.csv` 是 V0.11 真实数据 zero-shot 回放的左侧候选池时间轴。它描述每个 `as_of_date` 当天左侧策略实际给出的 ETF 候选集合、排序和左侧分数。Kronos 回放只能使用 `as_of_date` 当日及以前的 K 线作为输入，并用之后的行情作为未来窗口，因此候选池历史是防止未来函数和复现真实流程的核心输入。

## 为什么不能从 AkShare/Tushare 下载

AkShare 和 Tushare 可以提供公开市场行情、基金信息等数据，但 `left_candidates_history.csv` 不是公开市场字段。它来自 AETF 左侧项目自身的每日筛选结果，包含左侧策略在某一天实际看到、实际保留、实际排序的候选 ETF。公开数据源无法还原这份内部快照，也不能证明某只 ETF 当天确实进入过左侧候选池。

## 真实历史候选池的优先来源

优先级建议如下：

1. 左侧项目保存的每日候选池 CSV。
2. 左侧项目运行日志中的每日候选池快照。
3. 左侧项目数据库中的候选池历史表。
4. 左侧项目缓存中的候选池快照。

本仓库不直接读取主项目、不访问主项目数据库、不回写主项目。只有在用户明确提供路径并授权只读导出时，才可以新增只读导出脚本。

## reconstructed candidate history

如果没有真实历史候选池，只能生成 `reconstructed candidate history`。这类数据可以基于真实 K 线重建研究用候选集，用来测试数据管线形状和回放流程，但它不是左侧项目当时的真实候选池快照。

所有 reconstructed 输出必须明确标记：

```text
reconstructed_candidate_history_not_real_left_snapshot
```

它不可被称为真实历史候选池，也不能作为真实 V0.11 左侧历史回放通过条件。

## 标准字段

`left_candidates_history.csv` 必须包含以下字段：

```text
as_of_date
symbol
display_name
candidate_rank
left_score
notes
```

字段要求：

- `as_of_date`: 可被 pandas 解析的日期。
- `symbol`: 必须能在 `data/real/raw/kline/{symbol}.csv` 中找到对应真实 K 线。
- `display_name`: ETF 显示名。
- `candidate_rank`: 正整数，表示左侧候选池排序。
- `left_score`: 左侧项目给出的分数，可为空。
- `notes`: 来源说明或导出备注。

## V0.11 进入条件

进入 V0.11 需要同时满足：

- 真实 ETF K 线数量达到门槛，当前配置为 `qualified_symbol_count >= 20`。
- 存在真实 `data/real/raw/candidates/left_candidates_history.csv`。
- 候选池日期数量达到门槛，当前配置为 `candidate_date_count >= 100`。
- expanded replay cases 达到门槛，当前配置为 `replay_case_count >= 200`。
- `outputs/real_data/kronos_v10_replay_readiness.json` 中 `is_ready_for_expanded_replay` 为 `true`。

## 安全边界

- 不接入主项目，除非用户明确提供路径并授权只读导出。
- 不访问主项目数据库，除非用户明确授权。
- 不回写主项目。
- 不伪造真实左侧候选池历史。
- 不把 reconstructed 数据说成真实历史。
- 不训练模型。
- 不运行 torchrun。
- 不调用 GPU 推理。
- 不产生交易建议。
