# Kronos 研究记录

## 1. 研究范围

本阶段只研究 Kronos 本地推理，不接入左侧主项目，不做 fine-tune。

## 2. 仓库

```text
https://github.com/shiyu-coder/Kronos
```

## 3. 重点记录

| 项目 | 记录 |
|---|---|
| 安装方式 | 待 V0.2 填写 |
| 入口类 | `Kronos`, `KronosTokenizer`, `KronosPredictor` |
| 推荐模型 | `Kronos-small` |
| tokenizer | `NeoQuasar/Kronos-Tokenizer-base` |
| 输入必需字段 | `open`, `high`, `low`, `close` |
| 输入可选字段 | `volume`, `amount` |
| 时间字段 | `timestamps` / `trade_date` 转换 |
| 输出字段 | `open`, `high`, `low`, `close`, `volume`, `amount` |
| 第一阶段 fine-tune | 不允许 |

## 4. 样本推理参数

```yaml
lookback: 240
pred_len: 10
sample_count: 3
T: 1.0
top_p: 0.9
device: cuda
```

## 5. 待验证问题

- 4060 Ti 8GB / 16GB 下 `sample_count` 和 `batch_size` 的稳定上限。
- ETF 日 K 是否需要前复权/后复权统一。
- 缺失成交额 `amount` 时是否填 0 或回退。
- 预测路径对极端波动 ETF 是否稳定。
- 与左侧 invalid_price / recent_low 的冲突处理。
