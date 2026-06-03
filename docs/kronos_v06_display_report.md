# Kronos V0.6 Shadow Display Report

- 运行时间: 2026-06-03 16:00:40
- 输入 shadow predictions 路径: outputs/kronos_v04_shadow_predictions.csv
- 输入 replay metrics 路径: outputs/kronos_v05_replay_metrics.csv
- 输出 JSON 路径: outputs/kronos_v06_shadow_display.json
- 输出 HTML 路径: outputs/kronos_v06_shadow_dashboard.html
- card_count: 2
- pass_count: 2
- fail_count: 0
- case_count: 4
- direction_accuracy: 0.0
- mean_abs_return_error: 0.0616469458914649
- 是否生成 safety banner: 是
- 是否明确非交易建议: 是
- 是否不调用 GPU 推理: 是
- pytest 结果: PASS (38 passed in 2.46s)
- 是否可以进入 V0.7 ETF 本地微调评估: 是

## 工程验收说明

- 当前展示只用于工程验收。
- 当前样本是 synthetic / demo data。
- V0.5 direction_accuracy=0.0，不能支持任何交易结论。
- 当前展示不可作为交易依据。
- V0.6 只读取 V0.4/V0.5 已生成的离线文件，不调用 KronosAdapter，不运行 GPU 推理。

## 安全边界

- 非交易建议。
- 不下单。
- 不回写主项目。
- 不访问主项目数据库。
- 不下载或微调模型。
