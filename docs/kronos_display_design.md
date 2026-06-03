# Kronos V0.6 Shadow Display Design

## V0.6 目标

V0.6 提供一个离线、安全、只读的 AI 影子判断展示层。它只读取 V0.4 当前候选池影子预测结果与 V0.5 历史回放指标，生成结构化 display JSON 和单文件静态 HTML dashboard。

## 为什么需要展示层

V0.4/V0.5 已经产生模型观察结果与历史回放统计，但这些产物偏工程数据表，不适合直接给人检查。展示层负责把离线结果整理成可读结构，帮助确认工程链路、字段含义、安全边界和样本限制。

## 展示层读取哪些输入

- `outputs/kronos_v04_shadow_predictions.csv`
- `outputs/kronos_v05_replay_predictions.csv`
- `outputs/kronos_v05_replay_metrics.csv`

V0.6 不读取主项目文件，不访问主项目数据库，不回写任何外部系统。

## display JSON schema

顶层结构包含：

- `schema_version`: schema 版本。
- `generated_at`: 生成时间。
- `safety`: 只读影子展示安全声明。
- `summary`: 展示摘要、card 数量、PASS/FAIL 数量、数据来源。
- `replay_metrics`: V0.5 历史回放指标摘要。
- `cards`: V0.4 当前候选池展示卡片列表。

JSON 字段名不使用 buy、sell、position、target_price、stop_loss、order、trade、signal、recommendation 等交易建议语义。

## HTML dashboard 结构

HTML dashboard 是单文件静态页面，不依赖 CDN，不启动服务。页面包含：

- 顶部安全提示：只读 AI 影子观察、非交易建议、不下单、不回写主项目。
- Replay metrics 区域。
- Shadow cards 表格。
- 数据来源表格。
- 安全边界说明。

## ShadowDisplayCard 字段说明

- `symbol`: ETF 代码。
- `display_name`: 展示名称。
- `as_of_date`: 影子观察日期。
- `candidate_rank`: 候选池排序。
- `left_score`: 左侧候选分数，若输入没有该字段则为空。
- `model_status`: 模型产物状态。
- `prediction_direction_label`: 预测路径方向标签，只能是 UP、DOWN、FLAT、UNKNOWN，不是交易信号。
- `pred_return_last`: 预测路径末端收益率。
- `pred_range_pct`: 预测路径范围百分比。
- `pred_close_volatility`: 预测收盘路径波动观察值。
- `observation_level`: 展示层观察标签，不是风险评级。
- `notes`: 展示备注或失败原因。

## ReplayMetricSummary 字段说明

- `case_count`: 历史回放样本数量。
- `success_count`: 成功生成回放结果的样本数量。
- `fail_count`: 失败样本数量。
- `direction_accuracy`: 预测方向与实际方向一致率。
- `mean_abs_return_error`: 平均绝对收益误差。
- `median_abs_return_error`: 中位绝对收益误差。
- `rmse_return_error`: 收益误差 RMSE。
- `sample_warning`: 小样本警告。

## 为什么 direction_accuracy=0.0 不能解读为真实预测能力

V0.5 当前样本是 synthetic/demo data，且 case_count 很小。`direction_accuracy=0.0` 只能说明这 4 个工程验收样本中的方向标签没有匹配，不能外推为模型在真实市场中的预测能力，也不能支持任何交易结论。

## 为什么 case_count=4 样本过小

4 个样本只能覆盖基本数据流、指标计算和报告生成，不足以形成稳定统计估计。展示层会保留小样本警告，强调当前结果仅验证工程链路。

## 与 V0.4 影子预测的关系

V0.6 读取 V0.4 的 `outputs/kronos_v04_shadow_predictions.csv`，把每个候选池结果转换为 `ShadowDisplayCard`。V0.6 不重新推理，不调用 KronosAdapter。

## 与 V0.5 历史回放的关系

V0.6 读取 V0.5 的 `outputs/kronos_v05_replay_metrics.csv`，在 dashboard 中展示回放指标，并明确这些指标来自 demo 样本，只用于工程验收。

## 与 V0.7 微调评估的关系

V0.6 完成后，可以为 V0.7 ETF 本地微调评估提供展示与验收壳层。但 V0.6 本身不微调模型，不下载 Kronos-large，不评估真实市场收益。

## 安全边界：非交易建议、不下单、不回写主项目

V0.6 是只读 AI 影子观察展示层。它不产生交易建议，不下单，不回写主项目，不访问主项目数据库，不启动长期服务，不做自动交易。
