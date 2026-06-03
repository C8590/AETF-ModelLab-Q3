# Kronos V0.7 Finetune Evaluation Report

- 运行时间: 2026-06-03 16:13:33
- 输入 replay cases 路径: data/samples/replay/v05_left_candidates_history.csv
- 输入 replay metrics 路径: outputs/kronos_v05_replay_metrics.csv
- 输出 readiness JSON 路径: outputs/kronos_v07_finetune_readiness.json
- 输出 dataset profile CSV 路径: outputs/kronos_v07_dataset_profile.csv
- symbol_count: 2
- replay_case_count: 4
- direction_accuracy: 0.0
- mean_abs_return_error: 0.0616469458914649
- full_finetune_ready: False
- tokenizer_finetune_ready: False
- predictor_dry_run_ready: True
- decision: NOT_READY_FOR_FULL_FINETUNE
- recommended_next_step: Proceed only to V0.8 predictor-only dry-run design with tiny local settings.
- pytest 结果: PASS (48 passed in 2.43s)
- 是否可以进入 V0.8 predictor-only 微调 dry-run 设计: 是

## Reasons

- real symbol count 2 is below threshold 20.
- replay case count 4 is below threshold 200.
- direction accuracy is below the experiment threshold 0.52.
- mean absolute return error is above the experiment threshold 0.03.
- 8GB GPU memory is not recommended for full fine-tuning.
- full fine-tuning is disabled by hardware policy.

## Warnings

- Current input is synthetic/demo data and cannot be treated as a real ETF training set.
- V0.7 is evaluation only; it does not execute model training.
- tokenizer fine-tuning requires substantial real long-horizon ETF data.

## 评估结论

- 当前只做微调评估，不执行训练。
- 当前样本是 synthetic/demo data。
- 当前 V0.5 case_count=4，direction_accuracy=0.0，不支持任何交易结论。
- 当前不建议正式微调。
- 不可作为交易依据。
- V0.7 未运行 torchrun，未下载 Kronos-large，未生成 checkpoint。

## 安全边界

- 非交易建议。
- 不下单。
- 不回写主项目。
- 不访问主项目数据库。
