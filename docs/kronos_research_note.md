# Kronos V0.2 研究记录

生成时间：2026-06-02

## Kronos 是什么

Kronos 是 shiyu-coder/Kronos 开源仓库提供的金融 K 线基础模型家族。README 将其定位为面向金融市场“K-line sequence”的 decoder-only foundation model，并使用专门 tokenizer 将连续多维 OHLCV 数据量化为离散 token，再由自回归 Transformer 生成未来序列。

本次 V0.2 使用官方源码快照：

- 仓库来源：https://github.com/shiyu-coder/Kronos
- 本地路径：`external/Kronos`
- 上游 master commit：`67b630e67f6a18c9e9be918d9b4337c960db1e9a`
- 备注：首次 `git clone` 到 GitHub 443 端口超时；重试时使用 `git -c http.version=HTTP/1.1 clone --depth 1` 成功，`external/Kronos` 当前为嵌套 git checkout。

## 它解决什么问题

Kronos 解决的是金融 K 线序列预测问题：给定历史 K 线数据和对应时间戳，输出未来若干时间步的 OHLCV/amount 预测路径。官方 `KronosPredictor` 封装了预处理、归一化、tokenizer 编码、自回归推理和反归一化。

这不是交易系统，也不是信号引擎。V0.2 仅验证模型能否在本项目环境中完成“单只样本输入 -> Kronos-small 推理 -> CSV/报告输出”的闭环。

## 输入字段要求

`KronosPredictor.predict` 的主要输入为：

- `df`：历史 K 线 DataFrame，必须包含 `open`, `high`, `low`, `close`。
- `volume` 和 `amount` 为可选字段。若缺少 `volume`，官方代码会将 `volume` 与 `amount` 置为 0；若有 `volume` 但缺少 `amount`，会用 `volume * price_cols.mean(axis=1)` 补齐。
- `x_timestamp`：历史样本时间戳序列，长度与 `df` 行数一致。
- `y_timestamp`：待预测未来时间戳序列，长度应等于 `pred_len`。

V0.2 样本脚本使用官方测试样本：

- `external/Kronos/tests/data/regression_input.csv`
- 字段：`timestamps`, `open`, `high`, `low`, `close`, `volume`, `amount`
- 默认取前 `lookback=400` 行作为上下文，随后 `pred_len=120` 个时间戳作为预测时间轴。

## 输出字段格式

官方 `predict` 返回一个 pandas DataFrame，字段为：

- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`

索引使用传入的 `y_timestamp`。V0.2 脚本为了 CSV 可读性，会额外插入一列 `timestamps`，最终输出：

- `timestamps`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`

输出文件：`outputs/kronos_v02_sample_prediction.csv`

## Kronos-mini / Kronos-small / Kronos-base 区别

根据 README 的 model zoo：

- `Kronos-mini`：使用 `NeoQuasar/Kronos-Tokenizer-2k`，context length 2048，参数约 4.1M。
- `Kronos-small`：使用 `NeoQuasar/Kronos-Tokenizer-base`，context length 512，参数约 24.7M。
- `Kronos-base`：使用 `NeoQuasar/Kronos-Tokenizer-base`，context length 512，参数约 102.3M。

README 还列出 `Kronos-large`，但其 open-source 状态为未开放；V0.2 明确禁止下载 Kronos-large。

## 为什么 V0.2 选择 Kronos-small

V0.2 的目标是验证推理闭环，不是追求最大模型容量。`Kronos-small` 相比 `mini` 更接近后续 adapter 可能使用的 base tokenizer 路线，同时比 `base` 小很多，更适合在 RTX 4060 Ti 8GB 显存上做快速样本验证。它也与官方 README 的入门预测示例一致：

- tokenizer：`NeoQuasar/Kronos-Tokenizer-base`
- model：`NeoQuasar/Kronos-small`
- max_context：512

## max_context=512 的含义

`max_context` 是模型在自回归推理时可处理的最大上下文 token 序列长度。官方 README 指出 `Kronos-small` 与 `Kronos-base` 的最大上下文为 512。官方 `auto_regressive_inference` 内部会保留最近 `max_context` 的 token 缓冲区；当历史序列超过该长度时，会截断/滚动窗口，只让模型看到最近的上下文。

V0.2 默认：

- `max_context=512`
- `lookback=400`

因此历史上下文没有超过 `Kronos-small` 的上下文上限。

## lookback 与 pred_len 的关系

`lookback` 是输入历史窗口长度，决定 `x_df` 与 `x_timestamp` 的行数。`pred_len` 是未来预测步数，决定 `y_timestamp` 长度和输出 DataFrame 行数。

二者不是同一个概念：

- `lookback` 越大，模型可用历史越多，但不能有效超过 `max_context`。
- `pred_len` 越大，自回归生成步数越多，推理时间和误差累积风险越高。
- 输入样本总行数至少要满足 `lookback + pred_len`，因为 V0.2 需要从同一官方样本中取未来时间戳作为 `y_timestamp`。

## Python 3.12 兼容性观察

当前环境：

- Python：3.12.0
- torch：2.12.0+cu126
- CUDA：12.6
- GPU：NVIDIA GeForce RTX 4060 Ti

执行 `python -m pip install -r external/Kronos/requirements.txt` 后：

- torch CUDA 环境保持可用，`torch.cuda.is_available()` 为 True。
- `einops==0.8.1`, `huggingface_hub==0.33.1`, `matplotlib==3.9.3`, `tqdm==4.67.1`, `safetensors==0.6.2` 安装成功。
- pandas 被 Kronos requirements 固定到 `2.2.2`，在 Python 3.12 下可安装并通过本项目测试。
- 未观察到 numpy/pandas 依赖冲突。

## 本项目后续如何封装 adapter

建议 V0.3 将 V0.2 脚本中的一次性逻辑沉淀到 `src/model_lab/kronos_adapter.py`：

- `KronosConfig` 管理 model/tokenizer/cache/device/lookback/pred_len/sampling 参数。
- `load()` 负责插入 `external/Kronos` import path，并加载 tokenizer/model/predictor。
- `prepare_input()` 只接收本项目后续明确定义的 adapter 输入，不直接读取主项目数据。
- `predict_single()` 负责生成 `x_df`, `x_timestamp`, `y_timestamp`，调用 `KronosPredictor.predict`。
- `map_prediction_output()` 将 Kronos 原始输出映射为本项目预测 schema。
- 单元测试继续避免依赖真实模型下载，模型加载和 GPU 推理放在手动验收脚本或集成测试中。

## 风险提示

Kronos 输出是概率式/采样式预测路径，不能直接等同于交易信号。任何后续策略或风控阶段都必须将预测结果视为研究特征或影子判断输入，不能直接用于下单、自动交易、仓位调整或收益承诺。V0.2 不接入 AETF-LeftLab / A-ETF-L，不写交易逻辑，不下单，不做自动交易，不微调模型。
