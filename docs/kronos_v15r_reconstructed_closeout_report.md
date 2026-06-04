# Kronos V0.15-R Reconstructed Branch Closeout Report

- 运行时间: 2026-06-04 16:30:53
- branch_name: reconstructed_v1
- candidate_history_type: reconstructed_not_true_left_snapshot
- final_branch_status: PAUSED_BY_STOPLINE
- final_decision: PAUSE_RECONSTRUCTED_BRANCH
- evaluated_case_count: 1341
- direction_accuracy: 0.40939597315436244
- majority_direction_accuracy: 0.6017897091722595
- Wilson interval: {'success_count': 549, 'total_count': 1341, 'point_estimate': 0.40939597315436244, 'lower': 0.38337259776730287, 'upper': 0.4359369774272778, 'z': 1.96}
- mean_abs_return_error: 0.15708397727969794
- rmse_return_error: 0.19508706514643384
- blockers: DIRECTION_ACCURACY_UNDER_50_PERCENT, DIRECTION_ACCURACY_BELOW_CONTINUE_THRESHOLD, NO_CLEAR_MARGIN_VS_MAJORITY_DIRECTION_BASELINE, V11R_BASELINE_NOT_STABLE, MEAN_ABS_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD, RMSE_RETURN_ERROR_ABOVE_CONTINUE_THRESHOLD, STABLE_MONTH_GROUP_COUNT_BELOW_THRESHOLD, RECONSTRUCTED_HISTORY_IS_NOT_TRUE_LEFT_HISTORY
- lessons learned: Reconstructed candidate history is not true left-side historical candidate data.; V0.12-R full expansion did not confirm the V0.11-R 200-case baseline stability.; Direction accuracy stayed below 50 percent and below the majority-direction baseline.; Engineering pipeline can be stable while predictive evidence remains insufficient.; Formal V0.11 requires true left_candidates_history.csv rather than reconstructed_v1 inputs.
- recommended_next_step: OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY
- next-step decision matrix: OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY: RECOMMENDED - Formal V0.11 requires true left_candidates_history.csv. | REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2: OPTIONAL_RESEARCH - Current reconstructed_v1 is stopped; rules may be redesigned and re-evaluated from V0.10.2-E2. | DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1: BLOCKED - Direction accuracy is below 50 percent and below the majority-direction baseline.
- artifact_count: 16
- missing_artifact_count: 0
- formal_v011_ready: false
- reconstructed_branch_continue: false
- no_training: true
- no_torchrun: true
- no_gpu_inference: true
- 是否可以进入正式 V0.11: false
- 是否可以进入 V0.10.2-E2 或真实候选池导入: true
- pytest 结果: PASS (154 passed in 2.76s)

## Closeout Conclusion

- reconstructed candidate history 不是真实左侧历史候选池。
- reconstructed_v1 已被 stopline 暂停。
- 当前结果不支持训练、交易或正式 V0.11。
- 优先路径是获取真实 left_candidates_history.csv。
- 备选路径是重新设计 reconstructed 规则，从 V0.10.2-E2 重新开始。
- 不可作为交易依据。
