# Kronos V0.10.2-E Reconstructed Candidate History Report

- 运行时间: 2026-06-04 14:25:06
- 输入 normalized_kline_dir: data/real/normalized/kline
- 输出 reconstructed candidate history 路径: data/real/reconstructed/left_candidates_history_RECONSTRUCTED.csv
- 输出 reconstructed replay cases 路径: data/real/replay/kronos_v10_reconstructed_replay_cases.csv
- candidate_history_type: reconstructed_not_true_left_snapshot
- candidate_date_count: 300
- row_count: 1500
- symbol_count: 27
- replay_case_count: 1341
- 是否防止未来函数: True
- 是否未生成真实 left_candidates_history.csv: True
- 是否可以进入正式 V0.11: False
- 是否可以进入 V0.11-R: True
- pytest 结果: PASS (117 passed in 2.50s)

## Critical Scope

- reconstructed candidate history 不是真实左侧历史候选池。
- reconstructed candidate history 不能冒充 left_candidates_history.csv。
- reconstructed candidate history 不能用于正式 V0.11。
- reconstructed candidate history 只能用于 V0.11-R reconstructed zero-shot 研究分支。
- reconstructed candidate history 不可作为交易依据。
- 未训练模型。
- 未运行 torchrun。
- 未调用 GPU 推理。
- 未接入主项目。
- 未修改左侧项目。

## Reasons

- 无阻断 reconstructed replay 的错误。

## Warnings

- Reconstructed candidate history is not true left-side historical snapshot data.
- This output cannot be used for formal V0.11 true left history replay.
