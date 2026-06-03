# Kronos V0.5 Historical Replay Design

## V0.5 目标

V0.5 的目标是建立历史回放验证框架：读取历史 replay cases 和完整历史 K 线，按 `as_of_date` 严格切分模型输入窗口与真实未来验证窗口，调用 V0.3 `KronosAdapter` 做预测，并把预测路径与真实未来走势对比，输出逐案例结果、聚合指标和回放报告。

V0.5 不接主项目，不生成交易建议，不回写任何外部系统。

## 什么是历史回放

历史回放是在已知历史数据中模拟某个过去日期的模型运行。每个 replay case 都把 `as_of_date` 当作当时的当前日期，模型只能看到该日期当天及以前的数据，随后用该日期之后的真实数据评估预测路径。

## 为什么历史回放不能有未来函数

未来函数会让模型输入包含预测发生日之后的数据，导致评估指标虚高且不可复现。V0.5 明确把输入窗口和验证窗口分开：

- 输入窗口：`timestamps <= as_of_date`
- 验证窗口：`timestamps > as_of_date`

任何历史不足或未来不足都会报错，不用补齐或跨窗口偷看数据。

## Replay Case Schema

`data/samples/replay/v05_left_candidates_history.csv` 至少包含：

| 字段 | 说明 |
|---|---|
| `replay_id` | 唯一回放案例 ID |
| `as_of_date` | 模拟预测发生日期 |
| `symbol` | ETF 代码或内部标识 |
| `display_name` | 展示名称 |
| `candidate_rank` | 当时左侧候选排序 |
| `left_score` | 当时左侧系统分数，仅作观察字段 |
| `kline_path` | 完整历史 K 线 CSV 路径 |
| `notes` | 备注 |

读取后按 `as_of_date` 和 `candidate_rank` 排序，并支持 `max_cases` 截断。

## K 线切片规则

历史 K 线 schema：

| 字段 | 说明 |
|---|---|
| `timestamps` | 时间戳 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 成交量 |
| `amount` | 成交额 |

`split_kline_for_replay` 会先按 `timestamps` 升序排序，再进行两段切分：

1. `input_df` 只取 `timestamps <= as_of_date` 的最后 `lookback` 行。
2. `actual_future_df` 只取 `timestamps > as_of_date` 的前 `pred_len` 行。
3. 若历史不足 `lookback` 或未来不足 `pred_len`，该 case 失败并记录错误。

## 输入窗口与验证窗口

输入窗口是 Kronos 的上下文窗口，默认 `lookback=120`。验证窗口是真实未来路径，默认 `pred_len=24`。Pipeline 会把验证窗口的时间戳作为 `y_timestamp` 传给 `KronosAdapter.predict`，但不会把验证窗口价格传入模型。

## KronosHistoricalReplayPipeline 结构

`KronosHistoricalReplayPipeline` 位于 `src/model_lab/replay_pipeline.py`。

流程：

1. 读取 replay cases。
2. 按 `as_of_date`、`candidate_rank` 排序，并应用 `max_cases`。
3. 加载每个 case 的完整 K 线。
4. 调用 `split_kline_for_replay` 切分输入与验证窗口。
5. 调用 `KronosAdapter.predict`。
6. 使用 `summarize_prediction_path` 汇总预测路径。
7. 使用 `summarize_actual_future_path` 汇总真实未来路径。
8. 使用 `compare_prediction_to_actual` 生成误差指标。
9. 对全批次调用 `aggregate_replay_metrics`。
10. 保存 predictions CSV、metrics CSV 和 markdown report。

## 逐案例输出字段

逐案例结果保存到 `outputs/kronos_v05_replay_predictions.csv`，核心字段包括：

| 字段 | 说明 |
|---|---|
| `replay_id` | 回放案例 ID |
| `as_of_date` | 模拟预测日期 |
| `symbol` | 标的代码 |
| `display_name` | 展示名称 |
| `candidate_rank` | 候选排序 |
| `left_score` | 左侧系统观察分 |
| `model_name` | Kronos 模型名称 |
| `tokenizer_name` | tokenizer 名称 |
| `device` | 推理设备 |
| `lookback` | 输入窗口长度 |
| `pred_len` | 预测长度 |
| `last_close` | 输入窗口最后收盘价 |
| `pred_close_last` | 预测最后一步收盘 |
| `actual_close_last` | 真实未来最后一步收盘 |
| `pred_return_last` | 预测最后一步收益 |
| `actual_return_last` | 真实未来最后一步收益 |
| `return_error` | 预测收益减真实收益 |
| `abs_return_error` | 绝对收益误差 |
| `pred_direction` | 预测方向评估标签：UP/DOWN/FLAT |
| `actual_direction` | 真实方向评估标签：UP/DOWN/FLAT |
| `direction_match` | 方向是否一致 |
| `model_status` | PASS 或 FAIL |
| `error_message` | case 失败原因 |

输出字段禁止包含 `buy`、`sell`、`position`、`target_price`、`stop_loss`、`order`、`trade`、`signal` 等交易语义。

## 聚合指标说明

聚合指标保存到 `outputs/kronos_v05_replay_metrics.csv`：

| 指标 | 说明 |
|---|---|
| `case_count` | 回放案例数 |
| `success_count` | 成功案例数 |
| `fail_count` | 失败案例数 |
| `direction_match_count` | 方向一致案例数 |
| `direction_accuracy` | 成功案例中的方向一致比例 |
| `mean_abs_return_error` | 平均绝对收益误差 |
| `median_abs_return_error` | 中位数绝对收益误差 |
| `rmse_return_error` | 收益误差 RMSE |
| `mean_pred_return_last` | 平均预测末端收益 |
| `mean_actual_return_last` | 平均真实末端收益 |

V0.5 样本数较少，指标仅用于工程冒烟验收，不能做稳定统计解释。

## 失败容错机制

Pipeline 在单个 replay case 粒度捕获异常。K 线缺失、schema 错误、历史不足、未来不足、模型加载失败或推理失败，都只会让该 case 输出：

```text
model_status=FAIL
error_message=<异常信息>
```

其他 case 继续运行，全批次不中断。

## 与 V0.4 影子预测的关系

V0.4 解决单日候选池的 shadow observation 输出。V0.5 复用 V0.4 的数据校验、路径汇总和批处理容错思路，但把单日 snapshot 扩展为多个历史 `as_of_date` case，并加入真实未来路径对比。

## 与 V0.6 展示层的关系

V0.6 可以基于 V0.5 的逐案例结果和聚合指标做 AI 影子判断展示。V0.5 只提供验证数据与报告，不定义展示交互，也不产生交易动作。

## 样本说明

当前 `data/samples/replay/` 下的数据是 synthetic/demo data，只用于工程验收：

- 当前结果只验证工程链路。
- 当前结果不代表真实市场预测能力。
- 当前结果不可作为交易依据。

## 安全边界

V0.5 固定为 historical-replay-only：

- 不产生交易信号。
- 不输出买入、卖出、加仓、减仓、目标价、止损价等建议。
- 不下单。
- 不访问主项目数据库。
- 不读取或修改主项目文件。
- 不回写主项目。
- 不微调模型。
- 不下载 Kronos-large。
- 不运行 webui。
