# Kronos Predictor Smoke Design

## V0.9 目标

V0.9 执行一个严格受控的 predictor-only 1-step smoke training。它只验证 Kronos-small predictor 的加载、loss 计算、backward、optimizer step、CUDA 显存观测和 checkpoint 隔离，不做正式训练，不追求模型效果，不提交 checkpoint。

## Predictor-Only 1-Step Smoke 定义

1-step smoke 只运行一个 synthetic/demo batch，执行一次 forward、一次 loss、一次 backward 和一次 optimizer step。它不是微调实验，也不产生可用模型。

## 与正式训练的区别

正式训练需要真实 ETF 长周期数据、训练/验证/测试切分、多步优化、验证集评估、checkpoint 选择和外部复现实验。V0.9 只验证训练链路能跑通，不评价模型效果。

## 不微调 Tokenizer

Tokenizer 微调会改变 K 线量化边界，需要大量真实多标的数据支持。V0.7 已明确 tokenizer_finetune_ready=False，V0.9 继续禁止 tokenizer 微调。

## 不 Full Finetune

当前 V0.5 只有 4 个 replay case，direction_accuracy=0.0，V0.7 full_finetune_ready=False。V0.9 只允许 predictor-only 单步 smoke，不允许 full finetune。

## 为什么 max_steps=1

max_steps=1 把本阶段限制在链路验证：只确认 loss、backward、optimizer step 和显存观测正常。超过 1 step 就进入训练行为，不属于 smoke。

## 为什么 batch_size=1

batch_size=1 是 8GB GPU 上的最小安全批量，也避免 synthetic/demo data 被误解为训练集。它只用于检查代码路径和 CUDA 资源。

## 官方 Predictor 训练入口研究摘要

- Qlib predictor 入口是 `external/Kronos/finetune/train_predictor.py`。
- Qlib tokenizer 入口是 `external/Kronos/finetune/train_tokenizer.py`。
- Qlib predictor 依赖 `QlibDataset`，需要由 Qlib 预处理生成 pickle 数据。
- Qlib predictor 使用 `Config()` 读取 `external/Kronos/finetune/config.py`，该配置默认 epochs=30、batch_size=50、save_path=`./outputs/models`。
- Qlib predictor 必须通过 `torchrun` 启动；脚本检查 `WORLD_SIZE`。
- Qlib predictor 没有安全的 `max_steps=1` 早停参数，且会验证并保存 best checkpoint。
- CSV predictor 入口是 `external/Kronos/finetune_csv/finetune_base_model.py`。
- CSV sequential 入口是 `external/Kronos/finetune_csv/train_sequential.py`，可通过 `--skip-tokenizer` 只跑 predictor。
- CSV 路径读取 CSV OHLCV 数据，但同样没有硬性 `max_steps=1` 保护，并会保存 best model。
- 因此 V0.9 不直接执行官方训练入口，而使用项目内受控 wrapper 复用官方 Kronos 模型、tokenizer、forward 和 loss API。

## Smoke Gate 规则

gate 要求 V0.7 predictor_dry_run_ready=True、full_finetune_ready=False、tokenizer_finetune_ready=False，V0.8 manifest predictor_only=True，且 V0.9 config 保持 predictor_only=True、tokenizer_finetune=False、full_finetune=False、nproc_per_node=1、max_steps=1、batch_size=1、save_checkpoint=False。若配置要求显式执行，则没有 `--execute-smoke` 时只做 preflight。

## Checkpoint 隔离规则

V0.9 创建 `outputs/ignored_checkpoints/kronos_v09_predictor_smoke`，但受控 wrapper 不保存 checkpoint。该目录由 `.gitignore` 忽略，任何 checkpoint 或权重文件都不得提交。

## 官方入口 BLOCKED 原因

官方 Qlib 入口必须 torchrun，硬编码 `Config()`，没有 max_steps=1 参数，并会在验证后保存 best checkpoint。CSV 入口也没有单步硬停和不保存 checkpoint 的强制保护。因此官方入口不安全直接执行，V0.9 使用项目内 wrapper。

## 与 V0.8 Dry-Run Plan 的关系

V0.8 只生成 dry-run manifest 和 command plan，不执行训练。V0.9 读取 V0.8 manifest 作为进入单步 smoke 的前置证明，并继续保持 predictor-only、非正式训练和 checkpoint 隔离。

## 与 V0.10 的关系

若 V0.9 PASS，V0.10 应转向真实 ETF 长周期数据准备与 replay 扩容，而不是扩大训练步数。只有数据规模、数据质量和回放验证达标后，才考虑后续训练实验。

## 安全边界

V0.9 非交易建议，不下单，不回写主项目，不访问主项目数据库，不生成买卖结论，不把 synthetic/demo data 结果作为交易依据。
