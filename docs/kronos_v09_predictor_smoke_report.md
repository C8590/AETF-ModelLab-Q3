# Kronos V0.9 Predictor Smoke Report

- 运行时间: 2026-06-03 17:31:31
- readiness JSON 路径: outputs/kronos_v07_finetune_readiness.json
- dryrun manifest 路径: outputs/kronos_v08_predictor_dryrun_manifest.json
- ignored checkpoint root: outputs/ignored_checkpoints/kronos_v09_predictor_smoke
- gate_status: PASS
- smoke_status: PASS
- predictor_only: True
- tokenizer_finetune: False
- full_finetune: False
- max_steps: 1
- batch_size: 1
- nproc_per_node: 1
- torch 版本: 2.12.0+cu126
- CUDA 是否可用: True
- GPU 名称: NVIDIA GeForce RTX 4060 Ti
- max_memory_allocated_mb: 503.51
- loss_before: 2.325525999069214
- loss_after: 2.2955832481384277
- optimizer_step_executed: True
- checkpoint_files_created: 0
- 是否未执行正式训练: 是
- 是否未运行长时间 torchrun: 是
- 是否未提交 checkpoint: 是
- pytest 结果: PASS (70 passed in 2.22s)
- 是否可以进入 V0.10 真实 ETF 长周期数据准备与回放扩容: 是

## Official Entry Inspection

- predictor 入口: E:/AETF-ModelLab/external/Kronos/finetune/train_predictor.py
- CSV predictor 入口: E:/AETF-ModelLab/external/Kronos/finetune_csv/finetune_base_model.py
- 是否安全直接执行官方入口: False
- 阻塞原因: Official predictor entries do not expose a hard max_steps=1 guard and save best-model checkpoints after validation, so V0.9 uses a project-local one-step wrapper instead.
- command_preview: `python scripts/run_predictor_smoke_training.py --execute-smoke # controlled wrapper: nproc_per_node=1, max_steps=1, batch_size=1, save_checkpoint=False`

## V0.9 Scope

- 当前只是 1-step smoke training。
- 当前不是正式微调。
- 当前未生成可用模型。
- 当前样本是 synthetic/demo data。
- 当前 V0.5 case_count=4，direction_accuracy=0.0，不支持任何交易结论。
- 不可作为交易依据。

## Safety Boundary

- 非交易建议。
- 不下单。
- 不回写主项目。
- 不访问主项目数据库。
