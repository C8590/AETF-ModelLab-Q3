# Kronos V0.14-R Reconstructed Stopline Design

## 目标

V0.14-R 基于 V0.12-R / V0.13-R 已有离线结果，生成 reconstructed 分支误差诊断、统计稳定性分析和停止线判断。输出包括 stopline JSON、error diagnostics JSON、分组误差 CSV、极端误差 CSV、Markdown 报告和设计文档。

本阶段是 V0.14-R，不是正式 V0.14，也不是正式 V0.11。它不训练、不微调、不调用 GPU、不运行 torchrun、不运行 KronosAdapter、不接入主项目。

## 输入

- `outputs/kronos_v12r_reconstructed_full_predictions.csv`
- `outputs/kronos_v12r_reconstructed_full_metrics.csv`
- `outputs/kronos_v12r_group_by_symbol.csv`
- `outputs/kronos_v12r_group_by_candidate_rank.csv`
- `outputs/kronos_v12r_group_by_month.csv`
- `outputs/kronos_v12r_reconstructed_full_summary.json`
- `outputs/kronos_v13r_reconstructed_diagnostics.json`
- `outputs/kronos_v13r_reconstructed_dashboard.json`
- `docs/kronos_v13r_reconstructed_dashboard_report.md`

## 诊断方法

V0.14-R 计算以下诊断：

- direction confusion：按 `actual_direction` 和 `pred_direction` 汇总混淆统计。
- majority direction baseline：用真实方向多数类作为朴素基线。
- Wilson interval：对 direction match 成功率给出 95% Wilson 区间。
- error distribution：统计 absolute return error 的 mean、median、p90、p95、max 和 RMSE。
- extreme errors：抽取 absolute return error 最大的样本。
- group stability：按 symbol、candidate_rank、month 检查 eligible group、stable group 和 weighted direction accuracy。

## 停止线规则

触发停止线的主要条件：

- `direction_accuracy < 0.5`
- `direction_accuracy < min_direction_accuracy_to_continue`
- 相比 majority direction baseline 没有足够 margin
- `direction_accuracy_delta_vs_v11r < max_negative_delta_vs_v11r_baseline`
- `mean_abs_return_error` 或 `rmse_return_error` 超过继续阈值
- stable symbol 或 stable month 分组数量不足
- reconstructed candidate history 不是真实左侧历史候选池

当前 V0.12-R 全量结果 direction_accuracy 为 0.40939597315436244，低于 50%；相比 V0.11-R 200-case baseline 的 0.555 下降 -0.1456040268456376，未确认 baseline 稳定性。因此预期停止线结论为 `PAUSE_RECONSTRUCTED_BRANCH`。

## 输出

- `outputs/kronos_v14r_reconstructed_stopline.json`
- `outputs/kronos_v14r_reconstructed_error_diagnostics.json`
- `outputs/kronos_v14r_error_by_symbol.csv`
- `outputs/kronos_v14r_error_by_rank.csv`
- `outputs/kronos_v14r_error_by_month.csv`
- `outputs/kronos_v14r_extreme_errors.csv`
- `docs/kronos_v14r_reconstructed_stopline_report.md`

## 安全边界

reconstructed candidate history 不是真实左侧历史候选池，不能代表正式 V0.11，也不可作为交易依据。本阶段不输出买入、卖出、加仓、减仓、目标价、止损价、仓位、下单等交易建议。不训练、不微调、不调用 GPU、不运行 torchrun、不调用 KronosAdapter、不接 AETF-LeftLab / A-ETF-L、不回写主项目。
