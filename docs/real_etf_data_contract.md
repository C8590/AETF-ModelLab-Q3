# Real ETF Data Contract

## V0.10 目标

V0.10 建立真实 ETF 长周期数据导入、校验、画像、标准化和 replay case 扩容框架。它不训练模型，不运行 torchrun，不调用 GPU 推理，不接入主项目，也不回写主项目。

## 真实 ETF K 线 CSV Schema

标准字段如下：

```text
timestamps
open
high
low
close
volume
amount
symbol
display_name
market
frequency
price_adjustment
source_name
source_note
```

## 候选池历史 CSV Schema

标准字段如下：

```text
as_of_date
symbol
display_name
candidate_rank
left_score
notes
```

候选池历史应来自未来由左侧项目导出的 CSV。本项目 V0.10 不直接读取左侧主项目。如果没有真实候选池历史，只生成导入模板，不能伪造为真实候选池。

## 字段类型说明

- `timestamps`: 可解析为 datetime 的交易日期或时间戳。
- `open`, `high`, `low`, `close`: 数值型，必须为正数。
- `volume`, `amount`: 数值型，必须大于或等于 0。
- `symbol`: 非空字符串，建议使用交易所通用 ETF 代码格式。
- `display_name`, `market`, `frequency`, `price_adjustment`, `source_name`, `source_note`: 字符串元数据。
- `candidate_rank`: 正整数。
- `left_score`: 可为空的数值字段。

## 时间字段规则

`timestamps` 与 `as_of_date` 必须能被 pandas 解析为 datetime。标准化输出按 `timestamps` 升序排列。replay case 的输入窗口只能使用 `as_of_date` 当日及以前的数据，未来窗口只能使用 `as_of_date` 之后的数据。

## 复权字段规则

`price_adjustment` 必须明确记录复权状态，例如 `none`、`qfq` 或 `hfq`。同一个 symbol 的标准化数据不允许混用复权状态。V0.10 不做复权计算，也不改变价格含义，只记录来源给定的复权状态。

## 成交量和成交额规则

`volume` 和 `amount` 必须为非负数。若数据源没有成交额，应由用户在原始 CSV 中显式填 0 或补充来源说明，V0.10 不推导成交额。

## Symbol 命名规则

`symbol` 必须非空，且应在 K 线和候选池历史中保持一致。建议使用稳定代码，例如 `510300`、`159915`，不要在不同文件混用别名。

## 数据源记录规则

`source_name` 记录数据来源名称，`source_note` 记录导出说明、导出时间或清洗备注。V0.10 不在线抓取数据。

## 缺失值处理规则

必需字段缺失会被记录为质量错误。V0.10 不自动填补 OHLC、成交量或成交额。数据画像会输出缺失率，超过阈值时不能进入扩容 replay。

## 重复时间戳处理规则

完全重复行可在标准化时去重。相同 symbol 内重复 `timestamps` 会被记录为质量错误，默认阈值为 0。

## 无未来函数要求

expanded replay case 必须满足：`as_of_date` 前含至少 `lookback` 行，`as_of_date` 后含至少 `pred_len` 行。输入窗口不得包含 `as_of_date` 之后的数据。

## 安全边界

V0.10 不接主项目、不访问主项目数据库、不回写主项目、不训练模型、不调用 GPU 推理、不运行 torchrun、不产生交易建议、不下单。任何真实数据质量报告都只用于工程验收和后续回放准备，不可作为交易依据。
