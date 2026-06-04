# Kronos V0.11-R Reconstructed Replay Report

- 运行时间: 2026-06-04 15:00:48
- 输入 replay cases 路径: data/real/replay/kronos_v10_reconstructed_replay_cases.csv
- 输入 readiness 路径: outputs/real_data/kronos_v10_reconstructed_replay_readiness.json
- 输出 predictions 路径: outputs/kronos_v11r_reconstructed_replay_predictions.csv
- 输出 metrics 路径: outputs/kronos_v11r_reconstructed_replay_metrics.csv
- 输出 summary JSON 路径: outputs/kronos_v11r_reconstructed_replay_summary.json
- candidate_history_type: reconstructed_not_true_left_snapshot
- evaluated_case_count: 200
- success_count: 200
- fail_count: 0
- direction_accuracy: 0.555
- mean_abs_return_error: 0.06988062957852337
- median_abs_return_error: 0.05156520296983658
- rmse_return_error: 0.0913133653438696
- 是否 zero-shot: True
- 是否未训练: True
- 是否未运行 torchrun: True
- 是否未生成 checkpoint: True
- 是否可以进入正式 V0.11: False
- 是否可以进入 V0.12-R reconstructed 分支展示或扩展评估: True
- pytest 结果: PASS (125 passed in 2.44s)

## by_symbol 摘要

| symbol | success_count | direction_accuracy | mean_abs_return_error | rmse_return_error |
| --- | ---: | ---: | ---: | ---: |
| 159915 | 1 | 1.0 | 0.016702281481501213 | 0.016702281481501213 |
| 159928 | 20 | 0.8 | 0.022049051218522426 | 0.02848854087105811 |
| 159937 | 32 | 0.4375 | 0.17113637251229816 | 0.1753908812882061 |
| 159992 | 14 | 0.5 | 0.06136876075440824 | 0.07732145095307431 |
| 159996 | 5 | 1.0 | 0.022979051364044857 | 0.02599833889144411 |
| 510050 | 26 | 0.46153846153846156 | 0.03100632118418541 | 0.034626276262414976 |
| 510300 | 3 | 1.0 | 0.009222365999756565 | 0.012077191298358762 |
| 510500 | 2 | 0.5 | 0.05036997798233073 | 0.06635065640526241 |
| 512010 | 2 | 0.5 | 0.04849926773571289 | 0.049925504667035915 |
| 512100 | 11 | 0.7272727272727273 | 0.05032570950181737 | 0.05479197947978823 |

## by_candidate_rank 摘要

| candidate_rank | success_count | direction_accuracy | mean_abs_return_error | rmse_return_error |
| --- | ---: | ---: | ---: | ---: |
| 1 | 40 | 0.525 | 0.13107155212302463 | 0.14472707056859824 |
| 2 | 40 | 0.725 | 0.05197589802342924 | 0.0778056654709737 |
| 3 | 40 | 0.55 | 0.056282703734843065 | 0.07313141996401765 |
| 4 | 40 | 0.425 | 0.05840946013842766 | 0.07086925633730645 |
| 5 | 40 | 0.55 | 0.05166353387289224 | 0.065729375758557 |

## Critical Scope

- reconstructed candidate history 不是真实左侧历史候选池。
- 本次结果不能代表真实左侧项目历史候选池表现。
- 本次不是正式 V0.11。
- 本次未训练、未微调。
- 不可作为交易依据。
- 未接入主项目，未修改左侧项目，未访问交易接口。
