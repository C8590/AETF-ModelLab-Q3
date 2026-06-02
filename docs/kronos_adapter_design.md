# Kronos Adapter 设计说明

## V0.3 目标

V0.3 将 V0.2 中已经跑通的 Kronos-small 单样本推理封装为项目内可复用的 `KronosAdapter`。目标是让模型加载、输入校验、预测调用和元数据记录有统一边界，后续脚本不再直接散落 Kronos 官方类的底层调用。

## 为什么需要 Adapter

V0.2 脚本证明了本机环境可以加载 `NeoQuasar/Kronos-small` 和 `NeoQuasar/Kronos-Tokenizer-base` 并完成 GPU 推理，但脚本级实现不利于测试、复用和扩展。Adapter 将外部仓库路径、Hugging Face 缓存、设备、上下文窗口和采样参数集中到配置对象中，减少后续 V0.4 影子预测阶段的重复代码。

## Adapter 负责什么

- 自动定位 `external/Kronos`。
- 将 `external/Kronos` 加入 `sys.path`。
- 延迟加载 `KronosTokenizer`、`Kronos`、`KronosPredictor`。
- 使用配置中的模型、tokenizer、device、max_context 和 hf cache。
- 校验输入 DataFrame 的 OHLC 必须字段。
- 在 `volume`、`amount` 缺失时填 0，并写入 metadata。
- 支持 `timestamp_col="timestamps"`。
- 支持外部传入 `x_timestamp` 和 `y_timestamp`。
- 调用官方 `KronosPredictor.predict`。
- 返回 `KronosPredictionResult`，包含预测 DataFrame 和 metadata。

## Adapter 不负责什么

- 不读取 AETF-LeftLab / A-ETF-L。
- 不接入主项目数据源。
- 不产生买卖、加减仓、目标价或止损价。
- 不做下单或自动交易。
- 不微调模型。
- 不下载 Kronos-large。
- 不运行 webui。

## 输入 DataFrame schema

必须字段：

- `open`
- `high`
- `low`
- `close`

默认时间戳字段：

- `timestamps`

可选字段：

- `volume`
- `amount`

若 `volume` 或 `amount` 缺失，Adapter 会补 0，并在 metadata 的 `filled_optional_columns` 中记录字段名。若未外部传入 `x_timestamp` / `y_timestamp`，DataFrame 必须包含 `timestamps`，且行数至少满足 `lookback + pred_len`。

## 输出 KronosPredictionResult schema

`KronosPredictionResult` 包含：

- `pred_df`：Kronos 预测输出。默认包含 `timestamps`, `open`, `high`, `low`, `close`, `volume`, `amount`。
- `metadata`：本次加载与推理的上下文记录。

## metadata 字段说明

- `model_name`：模型名称。
- `tokenizer_name`：tokenizer 名称。
- `device`：推理设备。
- `cuda_available`：CUDA 是否可用。
- `gpu_name`：GPU 名称。
- `max_context`：Kronos 上下文长度。
- `lookback`：历史输入长度。
- `pred_len`：预测步数。
- `input_columns`：原始输入字段。
- `output_columns`：预测输出字段。
- `filled_optional_columns`：被 Adapter 补 0 的可选字段。
- `started_at`：推理开始时间。
- `finished_at`：推理结束时间。
- `elapsed_seconds`：推理耗时。
- `success`：是否成功完成推理。

## 与 V0.2 脚本的区别

V0.2 脚本直接加载 Kronos 官方类并调用 predictor。V0.3 后，`scripts/run_kronos_sample.py` 只负责样本读取、调用 Adapter、写出 CSV 和报告；模型加载与推理由 `KronosAdapter` 统一管理。

## 与未来 V0.4 影子预测的关系

V0.4 可以把候选池样本转换为 Adapter 输入 schema，再调用 `KronosAdapter.predict` 获取预测结果和 metadata。V0.4 仍需要单独设计影子特征、风险解释和报告，不应把 Kronos 输出直接当成交易信号。

## 安全边界

V0.3 Adapter 只产生预测结果和元数据，不产生交易信号，不下单，不接主项目，不自动交易，不微调模型。
