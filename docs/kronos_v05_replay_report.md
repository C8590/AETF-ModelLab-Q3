# Kronos V0.5 Historical Replay Report

- 运行时间: 2026-06-03 14:46:49
- Python 版本: 3.12.0
- torch 版本: 2.12.0+cu126
- CUDA 版本: 12.6
- GPU 名称: NVIDIA GeForce RTX 4060 Ti
- Kronos 模型名称: NeoQuasar/Kronos-small
- tokenizer 名称: NeoQuasar/Kronos-Tokenizer-base
- case_count: 4
- success_count: 4
- fail_count: 0
- direction_accuracy: 0.0
- mean_abs_return_error: 0.06164694589146491
- median_abs_return_error: 0.06237783528769314
- rmse_return_error: 0.06514821987783886
- lookback: 120
- pred_len: 24
- sample_count: 1
- 输入 replay cases 路径: data/samples/replay/v05_left_candidates_history.csv
- 输出 predictions CSV 路径: outputs/kronos_v05_replay_predictions.csv
- 输出 metrics CSV 路径: outputs/kronos_v05_replay_metrics.csv
- pytest 结果: PASS (30 passed in 2.21s)
- 是否检测并防止未来函数: 是
- 是否可以进入 V0.6 AI 影子判断展示: 是

## 输出字段

- `replay_id`
- `as_of_date`
- `symbol`
- `display_name`
- `candidate_rank`
- `left_score`
- `model_name`
- `tokenizer_name`
- `device`
- `lookback`
- `pred_len`
- `sample_count`
- `last_close`
- `pred_close_last`
- `actual_close_last`
- `pred_return_last`
- `actual_return_last`
- `return_error`
- `abs_return_error`
- `squared_return_error`
- `pred_direction`
- `actual_direction`
- `direction_match`
- `actual_close_min`
- `actual_close_max`
- `actual_range_pct`
- `model_status`
- `error_message`

## 样本说明

- 当前 replay 样本为 synthetic/demo data，只验证工程链路。
- 当前结果不代表真实市场预测能力。
- 当前结果不可作为交易依据。
- 样本数较少，聚合指标只能用于冒烟验收，不能做稳定统计解释。

## 安全边界

- V0.5 不产生交易信号。
- V0.5 不下单，不回写主项目，不访问主项目数据库。
- V0.5 不微调模型，不下载 Kronos-large，不运行 webui。
