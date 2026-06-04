# Kronos V0.10 Real Data Quality Report

- V0.10 运行时间: 2026-06-04 13:45:52
- 输入 raw_kline_dir: data/real/raw/kline
- 输入 raw_candidates_dir: data/real/raw/candidates
- symbol_count: 48
- qualified_symbol_count: 20
- candidate_date_count: 0
- replay_case_count: 0
- data_status: CANDIDATE_HISTORY_MISSING
- is_ready_for_expanded_replay: False
- dataset profile 路径: outputs/real_data/kronos_v10_real_dataset_profile.csv
- dataset manifest 路径: outputs/real_data/kronos_v10_real_dataset_manifest.json
- expanded replay cases 路径: data/real/replay/kronos_v10_expanded_replay_cases.csv
- readiness JSON 路径: outputs/real_data/kronos_v10_replay_readiness.json
- pytest 结果: PASS (100 passed in 2.66s)
- 是否可以进入 V0.11 真实数据 zero-shot 回放评估: 否

## 主要数据质量错误

- Real candidate history CSV is missing.
- replay_case_count 0 is below min_replay_cases 200.

## 主要数据质量警告

- 无主要警告。

## 候选池模板

- 已生成模板: data/real/raw/candidates/left_candidates_history_TEMPLATE.csv
- TEMPLATE 不是真实数据，不能当作真实候选池历史通过。

## V0.10 Scope

- V0.10 不训练模型。
- V0.10 不运行 torchrun。
- V0.10 不调用 GPU 推理。
- V0.10 不接主项目。
- V0.10 不产生交易建议。
- 如果真实数据不足，则不能进入 V0.11。
- 如果数据只是 SAMPLE/demo，则不能当作真实数据通过。

## 输出路径

- normalized K 线目录: data/real/normalized/kline
- normalized candidate history 路径: data/real/normalized/left_candidates_history.csv
