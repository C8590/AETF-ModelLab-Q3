# Kronos Predictor-Only Dry-Run Design

## V0.8 目标

V0.8 只完成 predictor-only 微调 dry-run 设计与预检框架。它生成配置、manifest、command plan、门禁报告和测试，不执行正式训练，不运行 torchrun，不生成可用模型。

## Predictor-Only Dry-Run 定义

predictor-only dry-run 是一个训练前设计阶段：保留 tokenizer，规划只微调 predictor 的最小命令形态，并用 V0.7 readiness 与 V0.5 replay 结果做门禁。当前命令只作为 preview 字符串写入 plan，默认不可执行。

## 不做 Tokenizer 微调

Tokenizer 微调会改变连续 K 线到离散 token 的量化边界，需要大量真实、长期、多标的 ETF 数据验证。当前 V0.5 只有 4 个 replay case，V0.7 明确 tokenizer_finetune_ready=False，因此 V0.8 禁止 tokenizer 微调。

## 不做 Full Finetune

Full finetune 对数据规模、验证集、GPU 显存和 checkpoint 管理要求更高。当前 GPU 约 8GB，symbol_count=2，case_count=4，direction_accuracy=0.0，V0.7 明确 full_finetune_ready=False，因此不能进入 full finetune。

## 不默认执行 Torchrun

官方 Qlib 训练入口依赖 torchrun/DDP，CSV 路径也支持 DDP。V0.8 的目标是 dry-run 设计，不是训练实验；torchrun 只能被写入 command plan，不能被脚本执行。未来 V0.9 若进入 1-step smoke training，需要单独放开执行门禁。

## 官方 Kronos 微调入口研究摘要

- Qlib 路径 predictor 训练入口: `external/Kronos/finetune/train_predictor.py`。
- Qlib 路径 tokenizer 训练入口: `external/Kronos/finetune/train_tokenizer.py`。
- Qlib 路径需要 `pyqlib`，并通过 `finetune/qlib_data_preprocess.py` 生成 `train_data.pkl`、`val_data.pkl`、`test_data.pkl`。
- Qlib predictor/tokenizer 训练脚本要求由 `torchrun` 启动；缺少 `WORLD_SIZE` 会报错。
- CSV 路径存在: `external/Kronos/finetune_csv/train_sequential.py`、`finetune_base_model.py`、`finetune_tokenizer.py`。
- CSV 路径可用普通 `python` 单进程，也支持 `torchrun --standalone --nproc_per_node=... train_sequential.py --config ...`。
- Qlib 默认 checkpoint 位置来自 `finetune/config.py` 的 `save_path`，默认 `./outputs/models`，并派生 tokenizer/predictor checkpoints。
- CSV 默认 checkpoint 位置来自 `model_paths.base_path`、`exp_name`、`tokenizer_save_name`、`basemodel_save_name`，保存到 `{base_save_path}/tokenizer/best_model` 和 `{base_save_path}/basemodel/best_model`。
- 必须重写到 AETF-ModelLab ignored 目录的路径包括 `qlib_data_path`、`dataset_path`、`save_path`、`backtest_result_path`、`pretrained_tokenizer_path`、`pretrained_predictor_path`、CSV `data_path`、`base_path`、`base_save_path`、`finetuned_tokenizer`。
- V0.8 只能生成计划、不能执行的命令包括 tokenizer 训练、full/sequential finetune、Kronos-large 下载、长时间 torchrun 和任何 backtest 交易流程。

## Dry-Run 配置字段

`configs/kronos_predictor_dryrun.yaml` 将输入路径、输出路径、预训练模型名、最小 dry-run 参数、门槛和安全开关集中管理。关键开关为 `predictor_only=true`、`execute_training=false`、`allow_torchrun_execution=false`、`tokenizer_finetune=false`、`full_finetune=false`、`save_checkpoint=false`。

## Dry-Run Manifest 字段

manifest 记录 `mode`、`created_at`、V0.7 `readiness_decision`、V0.5 `replay_case_count`、`symbol_count`、`direction_accuracy`、`mean_abs_return_error`、`synthetic_demo_only`、`predictor_only`、`checkpoint_root`、`checkpoint_root_ignored_expected`、`no_formal_training`、`no_tokenizer_finetune`、`no_full_finetune`。

## Checkpoint 隔离和 Gitignore

V0.8 创建 `outputs/ignored_checkpoints/kronos_v08_predictor_dryrun` 作为未来实验隔离根目录，但不写入模型权重。.gitignore 必须覆盖 `outputs/ignored_checkpoints/`、`checkpoints/`、`runs/`、`wandb/`、`comet/`、`*.ckpt`、`*.pt`、`*.pth`、`*.safetensors`。

## 与 V0.7 Readiness 的关系

V0.8 gate 读取 `outputs/kronos_v07_finetune_readiness.json`。只有 `predictor_dry_run_ready=True`、`full_finetune_ready=False`、`tokenizer_finetune_ready=False` 且 dry-run 配置全部保持关闭训练执行时，才允许生成 V0.8 产物。

## 与 V0.9 的关系

若 V0.8 通过，V0.9 可以设计 predictor-only 1-step smoke training，但必须作为新的阶段显式放开执行权限。V0.9 仍应保持 batch_size=1、max_steps=1、checkpoint 隔离和不下载 Kronos-large。

## 安全边界

V0.8 非交易建议，不下单，不回写主项目，不访问主项目数据库，不生成买卖结论，不把 synthetic/demo data 结果作为交易依据。
