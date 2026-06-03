# Kronos V0.8 Predictor Dry-Run Report

- 运行时间: 2026-06-03 17:12:36
- 输入 readiness JSON 路径: outputs/kronos_v07_finetune_readiness.json
- 输入 replay metrics 路径: outputs/kronos_v05_replay_metrics.csv
- 输入 dataset profile 路径: outputs/kronos_v07_dataset_profile.csv
- 输出 dryrun manifest 路径: outputs/kronos_v08_predictor_dryrun_manifest.json
- 输出 dryrun plan 路径: outputs/kronos_v08_predictor_dryrun_plan.json
- checkpoint root: outputs/ignored_checkpoints/kronos_v08_predictor_dryrun
- predictor_only: True
- execute_training: False
- allow_torchrun_execution: False
- replay_case_count: 4
- symbol_count: 2
- direction_accuracy: 0.0
- mean_abs_return_error: 0.0616469458914649
- full_finetune_ready: False
- tokenizer_finetune_ready: False
- predictor_dryrun_ready: True
- command_preview: `torchrun --standalone --nproc_per_node=1 E:/AETF-ModelLab/external/Kronos/finetune/train_predictor.py # dry-run preview only: max_steps=1, batch_size=1, checkpoint_root=E:/AETF-ModelLab/outputs/ignored_checkpoints/kronos_v08_predictor_dryrun`
- blocked_commands: tokenizer training via finetune/train_tokenizer.py or finetune_csv/finetune_tokenizer.py; full finetune or sequential tokenizer plus predictor training; Kronos-large download or substitution; long torchrun execution beyond a future approved one-step smoke run
- pytest 结果: PASS (59 passed in 2.60s)
- 是否可以进入 V0.9 predictor-only 1-step smoke training: 是

## V0.8 Scope

- 当前只做 dry-run 设计与预检。
- 当前未执行训练。
- 当前未运行 torchrun。
- 当前未生成可用 checkpoint。
- 当前样本是 synthetic/demo data。
- 当前 V0.5 case_count=4，direction_accuracy=0.0，不支持任何交易结论。
- 不可作为交易依据。

## Safety Boundary

- 非交易建议。
- 不下单。
- 不回写主项目。
- 不访问主项目数据库。
