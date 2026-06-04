# Kronos V0.13-R Reconstructed Dashboard Design

## 目标

V0.13-R 目标是基于 V0.12-R 的全量 reconstructed zero-shot 回放结果，生成 reconstructed 分支专用展示 JSON、诊断 JSON、单文件静态 HTML dashboard 和验收报告。

本阶段是 V0.13-R，不是正式 V0.13，也不是正式 V0.11。它只展示 reconstructed 分支的离线诊断结果，不训练、不微调、不调用 GPU、不运行 torchrun、不接入主项目。

## 分支定位

V0.12-R 的 `candidate_history_type` 是 `reconstructed_not_true_left_snapshot`。这意味着输入候选历史是 reconstructed candidate history，不是真实左侧历史候选池，也不能代表 AETF-LeftLab / A-ETF-L 的真实历史候选表现。

因此 V0.13-R dashboard 必须把 reconstructed branch only、Not formal V0.11、Not true left history、Not trading advice、No order execution、No writeback to left project、No training 放在顶部安全提示中。

## 为什么不能进入正式 V0.11

V0.11-R 的 200-case baseline direction_accuracy 为 0.555；V0.12-R full expansion 的 direction_accuracy 为 0.40939597315436244，delta 为 -0.1456040268456376。全量扩展没有确认 200-case baseline 的稳定性，且方向准确率低于 0.5。

因此 reconstructed 分支可以进入 V0.14-R 的误差诊断或停止线讨论，但不能进入正式 V0.11。

## 输入文件

- `outputs/kronos_v12r_reconstructed_full_summary.json`
- `outputs/kronos_v12r_reconstructed_full_metrics.csv`
- `outputs/kronos_v12r_group_by_symbol.csv`
- `outputs/kronos_v12r_group_by_candidate_rank.csv`
- `outputs/kronos_v12r_group_by_month.csv`
- `outputs/kronos_v12r_reconstructed_full_predictions.csv`
- `docs/kronos_v12r_reconstructed_expansion_report.md`

## Dashboard JSON Schema

顶层字段：

- `schema_version`
- `generated_at`
- `title`
- `safety_banner`
- `headline_metrics`
- `baseline_comparison`
- `group_by_symbol`
- `group_by_candidate_rank`
- `group_by_month`
- `diagnostics`
- `data_sources`

JSON 字段名不使用买卖、下单、交易、信号或建议相关的禁用词。相关安全含义通过 `not_trading_advice`、`execution_allowed=false` 和 banner 文本表达。

## HTML 结构

HTML dashboard 是单文件静态页面，不依赖 CDN，不需要启动服务。页面结构：

- 顶部标题和安全提示。
- Headline Diagnostics。
- V0.11-R baseline vs V0.12-R full expansion。
- Diagnostics 文本说明。
- by_symbol 表格。
- by_candidate_rank 表格。
- by_month 表格。
- Data Sources 表格。

## Diagnostics 规则

- `direction_accuracy < 0.5` 输出 `UNDER_50_PERCENT_DIRECTION_ACCURACY`。
- `direction_accuracy_delta_vs_v11r < -0.05` 输出 `V11R_BASELINE_NOT_STABLE`。
- `fail_count == 0` 输出 `ENGINEERING_PIPELINE_STABLE`。
- delta 低于阈值时输出 `FULL_EXPANSION_DID_NOT_CONFIRM_V11R_200_CASE_BASELINE_STABILITY`。

## 安全边界

本阶段不可作为交易依据，不输出买入、卖出、加仓、减仓、目标价、止损价、仓位、下单等交易建议。不训练、不微调、不调用 GPU、不运行 torchrun、不调用 KronosAdapter、不回写主项目、不连接 AETF-LeftLab / A-ETF-L。
