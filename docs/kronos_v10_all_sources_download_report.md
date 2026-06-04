# Kronos V0.10.2-C All Sources ETF Kline Download Report

- 运行时间: 2026-06-04T13:45:35
- ETF universe 配置数量: 48
- 初始 qualified raw CSV 数量: 15
- 最终 raw kline CSV 总数: 48
- 最终 qualified raw CSV 数量: 20
- 目标 qualified raw CSV 数量: 20
- AkShare 成功数量: 5
- BaoStock 成功数量: 0
- Tushare 状态: SKIPPED_TOKEN_MISSING
- Tushare 成功数量: 0
- 仍失败 ETF 数量: 28

## 数据源混用风险

- BaoStock fallback CSV 的 source_note 会标记 `baostock_fallback_adjustment_unverified`。
- BaoStock 与 AkShare qfq 复权口径未做逐项一致性校验，后续分析应按 source_name/source_note 分层检查。

## 仍失败 ETF

- 510880
- 515180
- 515790
- 516160
- 515700
- 516950
- 512400
- 512170
- 512980
- 512200
- 515050
- 515880
- 516510
- 515230
- 159995
- 159845
- 159629
- 159919
- 159922
- 159967
- 159819
- 159869
- 159766
- 159865
- 159870
- 159611
- 159638
- 159755

## Scope

- 本阶段只下载并标准化真实 A 股 ETF 日线 K 线。
- 未处理或伪造 left_candidates_history.csv。
- 未训练模型。
- 未运行 torchrun。
- 未调用 GPU 推理。
- 未接入或回写主项目。
- 未生成交易建议。
