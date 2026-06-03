# Kronos V0.7 Finetune Readiness

## V0.7 目标

V0.7 只做 ETF 本地微调可行性评估，包括官方 Kronos 微调结构研究、当前 demo 数据画像、门禁判断、资源风险分析和 V0.8 dry-run 进入条件。V0.7 不执行训练，不运行 `torchrun`，不下载 Kronos-large，不生成 checkpoint。

## 官方 Kronos 微调流程概览

官方 README 描述的 Qlib 路线分为四步：

1. 配置路径和超参数，核心配置在 `external/Kronos/finetune/config.py`。
2. 使用 `finetune/qlib_data_preprocess.py` 从 Qlib 数据生成 `train_data.pkl`、`val_data.pkl`、`test_data.pkl`。
3. 使用 `torchrun --standalone --nproc_per_node=NUM_GPUS finetune/train_tokenizer.py` 微调 tokenizer。
4. 使用 `torchrun --standalone --nproc_per_node=NUM_GPUS finetune/train_predictor.py` 微调 predictor，然后用 `finetune/qlib_test.py` 做示例回测。

`external/Kronos/finetune_csv/` 还提供 CSV 路线，要求 CSV 至少包含 `timestamps/open/high/low/close/volume/amount`，可以用 `train_sequential.py` 顺序执行 tokenizer 和 predictor 训练，也可以分别运行 `finetune_tokenizer.py` 与 `finetune_base_model.py`。

## Qlib 依赖说明

官方 Qlib 路线依赖 `pyqlib` 和本地 Qlib 数据目录。`qlib_data_preprocess.py` 会初始化 Qlib provider，并按 `instrument`、时间范围和字段配置加载市场数据。本项目当前 V0.7 不安装或调用 Qlib，也不访问主项目数据库。

## tokenizer 微调和 predictor 微调区别

tokenizer 微调调整 K 线连续特征到离散 token 的量化表示，输出默认路径类似 `./outputs/models/finetune_tokenizer_demo/checkpoints/best_model`。predictor 微调在 tokenizer 之后训练 Kronos 主预测模型，输出默认路径类似 `./outputs/models/finetune_predictor_demo/checkpoints/best_model`。CSV 路线的默认 checkpoint 路径为 `{base_save_path}/{exp_name}/tokenizer/best_model/` 与 `{base_save_path}/{exp_name}/basemodel/best_model/`。

## 默认数据格式和切分方式

Qlib 路线默认使用日频 A 股示例，字段包括 `open/high/low/close/vol/amt`，训练窗口由 `lookback_window=90` 和 `predict_window=10` 控制。默认时间切分为：

- train: `2011-01-01` 到 `2022-12-31`
- val: `2022-09-01` 到 `2024-06-30`
- test: `2024-04-01` 到 `2025-06-05`

CSV 路线默认使用比例切分，示例配置为 `train_ratio=0.9`、`val_ratio=0.1`、`test_ratio=0.0`，`lookback_window=512`、`predict_window=48`。

## 为什么当前阶段不执行正式微调

当前本项目只有 synthetic/demo replay 样本，V0.5 `case_count=4`，无法代表真实 ETF 长周期训练集。正式微调会生成 checkpoint、可能长时间占用 GPU，并且官方脚本默认按多 GPU DDP/`torchrun` 设计，不适合 V0.7 直接执行。

## 当前 ETF 数据准备缺口

当前缺少至少 20 个真实 ETF 标的、每标的至少 1000 根真实历史 bar、至少 200 个 replay case，以及 24 个月训练、6 个月验证、6 个月测试的明确时间切分。当前 replay cases 只覆盖 2 个 symbol 和 4 个 case。

## 当前 V0.5 replay 样本过小的问题

V0.5 只有 4 个 synthetic/demo case，只能验证工程链路。任何聚合指标都没有统计稳定性，不能用来判断真实市场泛化能力。

## direction_accuracy=0.0 的含义

`direction_accuracy=0.0` 表示当前 4 个 demo replay case 的预测方向与实际方向没有匹配。这个结果必须如实保留，但不能外推为真实市场预测能力，也不能支持任何交易结论。

## 4060 Ti 8GB 的资源边界

本机 RTX 4060 Ti 约 8GB 显存。官方默认 batch size 较大，Qlib 路线还依赖 DDP、多进程和较长训练轮数。8GB 显存更适合未来小规模 predictor-only dry-run：batch size 1、梯度累积、混合精度、极少样本、短步数，并且只用于验证训练脚本连通性。

## 不适合当前阶段直接执行的流程

- tokenizer 微调：需要充足真实 ETF 长周期数据。
- full fine-tune：当前数据量、指标和显存都不满足门禁。
- Qlib 回测示例：包含策略评估和外部数据依赖，不属于 V0.7。
- `torchrun` 长时间训练：会越过本阶段“评估 only”的边界。
- Kronos-large 下载或训练：本阶段明确禁止。

## 建议未来只做 predictor-only dry-run

V0.8 可以设计 predictor-only dry-run，但应限制为小 batch、短步数、只读数据输入、不保存正式 checkpoint、不做任何交易解释。dry-run 的目标是验证本地训练入口和资源边界，而不是追求预测效果。

## 安全边界：非交易建议、不下单、不回写主项目

V0.7 不产生交易建议，不下单，不回写主项目，不访问主项目数据库，不做自动交易。所有结论仅用于 AETF-ModelLab 的工程验收和后续实验设计。
