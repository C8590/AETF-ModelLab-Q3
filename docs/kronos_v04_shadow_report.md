# Kronos V0.4 Shadow Report

- 运行时间: 2026-06-03 14:30:56
- Python 版本: 3.12.0
- torch 版本: 2.12.0+cu126
- CUDA 版本: 12.6
- GPU 名称: NVIDIA GeForce RTX 4060 Ti
- Kronos 模型名称: NeoQuasar/Kronos-small
- tokenizer 名称: NeoQuasar/Kronos-Tokenizer-base
- candidate_count: 2
- success_count: 2
- fail_count: 0
- lookback: 120
- pred_len: 24
- sample_count: 1
- 输入候选池路径: data/samples/v04_left_candidates_snapshot.csv
- 输出 CSV 路径: outputs/kronos_v04_shadow_predictions.csv
- pytest 结果: PASS (21 passed in 2.09s)
- 是否可以进入 V0.5 历史回放验证: 是

## 输出字段

- `as_of_date`
- `candidate_rank`
- `code`
- `name`
- `last_close`
- `risk_level`
- `model_status`
- `error_message`
- `model_name`
- `tokenizer_name`
- `device`
- `lookback`
- `pred_len`
- `sample_count`
- `run_time`
- `path_len`
- `pred_close_1`
- `pred_close_3`
- `pred_close_5`
- `pred_close_last`
- `pred_close_mean`
- `pred_return_1`
- `pred_return_3`
- `pred_return_5`
- `pred_return_last`
- `pred_return_min`
- `pred_return_max`
- `pred_low_min`
- `pred_high_max`
- `pred_drawdown_min`
- `pred_upside_max`
- `pred_path_std`

## 安全边界

- V0.4 仅生成 shadow observation，不产生交易信号。
- V0.4 不下单，不回写主项目，不执行微调。
