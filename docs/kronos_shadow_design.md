# Kronos V0.4 Shadow Prediction Design

## V0.4 目标

V0.4 的目标是把 V0.3 KronosAdapter 放进一个独立的影子预测流程：读取候选池快照，按候选排名加载每只标的的 K 线，调用 `KronosAdapter.predict`，并把预测路径汇总为 shadow observation CSV。

V0.4 只验证数据接口、推理调用、结果汇总和失败容错，不接主项目，不产生交易信号。

## 什么是影子预测

影子预测是指模型在主交易系统旁边独立运行，只记录模型看到候选标的后的预测路径摘要。它不改变候选池，不改变风控状态，也不向任何执行层输出建议。

## 为什么不直接接交易系统

Kronos 路径预测需要先验证输入 schema、模型稳定性、异常处理和历史样本表现。直接接入交易系统会把未验证模型输出混入决策链，增加误触发、误解释和回写污染风险。

## 候选池 Snapshot Schema

`data/samples/v04_left_candidates_snapshot.csv` 至少包含：

| 字段 | 说明 |
|---|---|
| `candidate_rank` | 候选排序，数值越小优先级越高 |
| `trade_date` | 候选快照日期 |
| `code` | ETF 代码 |
| `name` | ETF 名称 |
| `close` | 快照收盘价，必须大于 0 |
| `kline_csv_path` | 该标的 K 线 CSV 路径，可为项目相对路径 |

读取后按 `candidate_rank` 稳定排序，并支持 `max_candidates` 截断，避免一次运行过多标的。

## K 线 Schema

K 线 CSV 至少包含：

| 字段 | 说明 |
|---|---|
| `timestamps` | 时间戳，可解析为 pandas datetime |
| `open` | 开盘价，必须大于 0 |
| `high` | 最高价，必须大于 0 |
| `low` | 最低价，必须大于 0 |
| `close` | 收盘价，必须大于 0 |
| `volume` | 可选成交量 |
| `amount` | 可选成交额 |

读取后按 `timestamps` 升序排序。Pipeline 使用最近 `lookback` 条 K 线，并为 `pred_len` 生成未来工作日时间戳。

## ShadowPipeline 结构

`KronosShadowPipeline` 位于 `src/model_lab/shadow_pipeline.py`。

流程：

1. 调用 `read_candidate_snapshot` 读取候选池。
2. 按 `candidate_rank` 排序，并应用 `max_candidates`。
3. 对每只候选标的调用 `read_kline_csv`。
4. 调用 `KronosAdapter.predict`。
5. 调用 `summarize_prediction_path` 汇总预测路径。
6. 调用 `build_shadow_observation_row` 生成 shadow observation 行。
7. 保存 `outputs/kronos_v04_shadow_predictions.csv`。
8. 返回 `DataFrame`。

## Shadow Observation 输出字段

输出字段只描述模型路径观察，不包含 `buy`、`sell`、`order`、`trade` 等交易语义字段。

核心字段包括：

| 字段 | 说明 |
|---|---|
| `as_of_date` | 候选快照日期 |
| `candidate_rank` | 候选排序 |
| `code` | ETF 代码 |
| `name` | ETF 名称 |
| `last_close` | 快照收盘价 |
| `risk_level` | 候选风险等级，若无则为空 |
| `model_status` | `PASS` 或 `FAIL` |
| `error_message` | 单标的失败原因 |
| `model_name` | Kronos 模型名称 |
| `tokenizer_name` | tokenizer 名称 |
| `device` | 推理设备 |
| `lookback` | 输入窗口长度 |
| `pred_len` | 预测长度 |
| `sample_count` | 采样次数 |
| `run_time` | 推理完成时间 |
| `path_len` | 预测路径长度 |
| `pred_close_1` | 第 1 步预测收盘 |
| `pred_close_3` | 第 3 步预测收盘 |
| `pred_close_5` | 第 5 步预测收盘 |
| `pred_close_last` | 最后一步预测收盘 |
| `pred_return_1` | 第 1 步相对 `last_close` 的变化 |
| `pred_return_3` | 第 3 步相对 `last_close` 的变化 |
| `pred_return_5` | 第 5 步相对 `last_close` 的变化 |
| `pred_return_last` | 最后一步相对 `last_close` 的变化 |
| `pred_low_min` | 预测路径最低价 |
| `pred_high_max` | 预测路径最高价 |
| `pred_drawdown_min` | 预测路径最低价相对 `last_close` 的变化 |
| `pred_upside_max` | 预测路径最高价相对 `last_close` 的变化 |
| `pred_path_std` | 预测收盘路径标准差 |

## 失败容错机制

Pipeline 在单只标的粒度捕获异常。任一标的 K 线缺失、schema 不合法、模型加载失败或推理失败，都只会使该标的输出：

```text
model_status=FAIL
error_message=<异常信息>
```

其他候选标的继续运行，全批次不因单只失败中断。

## 与 V0.3 Adapter 的关系

V0.3 的 `KronosAdapter` 是模型边界，负责输入准备、加载外部 Kronos、调用 predictor 并返回预测路径。V0.4 不修改主项目，而是在 Adapter 外面增加 `KronosShadowPipeline`，把单次预测扩展为候选池批处理和 observation 输出。

## 与 V0.5 历史回放的关系

V0.4 产出的 shadow observation schema 将作为 V0.5 历史回放验证的基础。V0.5 可以复用同一套候选池读取、K 线读取、路径汇总和失败容错机制，只把单日 snapshot 扩展为多日期历史样本。

## 安全边界

V0.4 固定为 shadow-only：

- 不产生交易信号。
- 不输出买入、卖出、下单或执行建议。
- 不下单。
- 不回写主项目。
- 不修改主项目候选池、风控、持仓或交易状态。
- 不执行模型微调。
