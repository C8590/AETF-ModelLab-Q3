# Kronos V0.13-R Reconstructed Dashboard Report

- 运行时间: 2026-06-04 15:41:00
- 输入 summary 路径: E:\AETF-ModelLab\outputs\kronos_v12r_reconstructed_full_summary.json
- 输入 metrics 路径: E:\AETF-ModelLab\outputs\kronos_v12r_reconstructed_full_metrics.csv
- 输入 by_symbol 路径: E:\AETF-ModelLab\outputs\kronos_v12r_group_by_symbol.csv
- 输入 by_rank 路径: E:\AETF-ModelLab\outputs\kronos_v12r_group_by_candidate_rank.csv
- 输入 by_month 路径: E:\AETF-ModelLab\outputs\kronos_v12r_group_by_month.csv
- 输出 dashboard JSON 路径: E:\AETF-ModelLab\outputs\kronos_v13r_reconstructed_dashboard.json
- 输出 dashboard HTML 路径: E:\AETF-ModelLab\outputs\kronos_v13r_reconstructed_dashboard.html
- 输出 diagnostics JSON 路径: E:\AETF-ModelLab\outputs\kronos_v13r_reconstructed_diagnostics.json
- candidate_history_type: reconstructed_not_true_left_snapshot
- evaluated_case_count: 1341
- direction_accuracy: 0.40939597315436244
- V0.11-R baseline direction_accuracy: 0.555
- direction_accuracy_delta_vs_v11r: -0.1456040268456376
- mean_abs_return_error: 0.15708397727969794
- median_abs_return_error: 0.1382922503969841
- rmse_return_error: 0.19508706514643384
- performance_interpretation: UNDER_50_PERCENT_DIRECTION_ACCURACY, V11R_BASELINE_NOT_STABLE, ENGINEERING_PIPELINE_STABLE
- stability_warning: FULL_EXPANSION_DID_NOT_CONFIRM_V11R_200_CASE_BASELINE_STABILITY
- 是否 formal_v011_ready: false
- 是否 reconstructed_branch_only: true
- 是否未训练: true
- 是否未运行 torchrun: true
- 是否未调用 GPU: true
- 是否可以进入正式 V0.11: false
- 是否可以进入 V0.14-R reconstructed 误差诊断或停止线: true
- pytest 结果: PASS (142 passed in 3.12s)

## 结论说明

- reconstructed candidate history 不是真实左侧历史候选池。
- V0.12-R 全量结果没有确认 V0.11-R 200-case baseline 的稳定性。
- 当前 direction_accuracy=0.4094，不支持交易结论。
- 本次不是正式 V0.13。
- 本次未训练、未微调、未调用 GPU。
- 不可作为交易依据。
- Dashboard safety banner: Reconstructed branch only | Not formal V0.11 | Not true left history | Not trading advice | No order execution | No writeback to left project | No training
