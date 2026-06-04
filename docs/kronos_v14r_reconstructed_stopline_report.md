# Kronos V0.14-R Reconstructed Stopline Report

- 运行时间: 2026-06-04 15:59:05
- 输入 predictions 路径: E:\AETF-ModelLab\outputs\kronos_v12r_reconstructed_full_predictions.csv
- 输入 summary 路径: E:\AETF-ModelLab\outputs\kronos_v12r_reconstructed_full_summary.json
- 输入 V0.13-R diagnostics 路径: E:\AETF-ModelLab\outputs\kronos_v13r_reconstructed_diagnostics.json
- 输出 stopline JSON 路径: E:\AETF-ModelLab\outputs\kronos_v14r_reconstructed_stopline.json
- 输出 error diagnostics JSON 路径: E:\AETF-ModelLab\outputs\kronos_v14r_reconstructed_error_diagnostics.json
- 输出 extreme errors CSV 路径: E:\AETF-ModelLab\outputs\kronos_v14r_extreme_errors.csv
- evaluated_case_count: 1341
- direction_accuracy: 0.40939597315436244
- majority_direction_accuracy: 0.6017897091722595
- Wilson interval: {'success_count': 549, 'total_count': 1341, 'point_estimate': 0.40939597315436244, 'lower': 0.38337259776730287, 'upper': 0.4359369774272778, 'z': 1.96}
- mean_abs_return_error: 0.15708397727969794
- median_abs_return_error: 0.1382922503969841
- rmse_return_error: 0.19508706514643384
- direction_accuracy_delta_vs_v11r: -0.1456040268456376
- decision: PAUSE_RECONSTRUCTED_BRANCH
- decision_level: STOPLINE
- blockers: DIRECTION_ACCURACY_UNDER_50_PERCENT, DIRECTION_ACCURACY_BELOW_CONTINUE_THRESHOLD, NO_CLEAR_MARGIN_VS_MAJORITY_DIRECTION_BASELINE, V11R_BASELINE_NOT_STABLE, MEAN_ABS_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD, RMSE_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD, STABLE_MONTH_GROUP_COUNT_BELOW_THRESHOLD, RECONSTRUCTED_HISTORY_IS_NOT_TRUE_LEFT_HISTORY
- next_step: Enter V0.15-R branch closeout or candidate pool reconstruction rule redesign; do not enter formal V0.11.
- formal_v011_ready: false
- reconstructed_branch_continue: false
- not_trading_advice: true
- no_training: true
- no_torchrun: true
- no_gpu_call: true
- no_left_project_connection: true
- pytest 结果: PASS (149 passed in 2.68s)
- 是否可以进入正式 V0.11: false
- 是否可以进入 V0.15-R 分支收尾或候选池重建规则再设计: true

## 停止线说明

- reconstructed candidate history 不是真实左侧历史候选池。
- V0.12-R 全量结果没有确认 V0.11-R 200-case baseline 的稳定性。
- 当前 direction_accuracy=0.4094，低于 50%，不支持继续推进 reconstructed 分支作为有效预测路线。
- 本次不是正式 V0.14。
- 本次未训练、未微调、未调用 GPU。
- 不可作为交易依据。
