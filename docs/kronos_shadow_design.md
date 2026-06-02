# Kronos AI 影子特征设计

## 1. 设计原则

Kronos 不直接输出买入信号，只输出 AI 影子判断。左侧主项目仍由原有规则控制。

## 2. 输入

```text
left_candidates.csv
watchlist.csv
positions.csv
ETF 日 K 数据
risk_warning.csv
sector_map.csv
```

## 3. 输出

```text
outputs/kronos_shadow_features.csv
```

## 4. 字段

| 字段 | 含义 |
|---|---|
| `trade_date` | 左侧候选日期 |
| `code` | ETF 代码 |
| `name` | ETF 名称 |
| `close` | 当前收盘价 |
| `kronos_pred_close_3d` | 预测第 3 日收盘 |
| `kronos_pred_close_5d` | 预测第 5 日收盘 |
| `kronos_pred_close_10d` | 预测第 10 日收盘 |
| `kronos_pred_return_3d` | 预测 3 日收益 |
| `kronos_pred_return_5d` | 预测 5 日收益 |
| `kronos_pred_return_10d` | 预测 10 日收益 |
| `kronos_pred_low_5d` | 预测未来 5 日最低价 |
| `kronos_pred_high_5d` | 预测未来 5 日最高价 |
| `kronos_max_pred_drawdown_5d` | 预测未来 5 日最大回撤 |
| `kronos_break_recent_low` | 是否跌破近期低点 |
| `kronos_break_invalid_price` | 是否跌破失效价 |
| `kronos_expected_upside` | 预期上行空间 |
| `kronos_expected_downside` | 预期下行空间 |
| `kronos_rr` | 上下行风险收益比 |
| `kronos_shadow_score` | AI 影子分 |
| `kronos_shadow_action` | AI 影子动作 |
| `kronos_explanation` | 中文解释 |
| `model_name` | 模型名称 |
| `run_time` | 推理时间 |

## 5. 动作规则草案

```text
R4 / P0：强制 WAIT 或 RISK_OF_BREAKDOWN，不允许 SUPPORT_PROBE。
预测跌破 invalid_price：RISK_OF_BREAKDOWN。
预测跌破 recent_low：RISK_OF_BREAKDOWN。
未来 5 日最大回撤 <= -3%：RISK_OF_BREAKDOWN 或 WAIT。
未来 5 日收益 > 1.5%，RR >= 1.5，且风险级别 R0/R1：SUPPORT_PROBE。
其他：WAIT。
```

## 6. 中文解释模板

```text
Kronos 预测未来5日低点不会跌破失效价，且收盘路径温和上修，支持小仓试探。
```

```text
Kronos 预测未来3-5日仍有破低风险，当前左侧信号应降级为观察。
```
