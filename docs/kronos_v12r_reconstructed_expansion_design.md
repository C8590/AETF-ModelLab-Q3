# Kronos V0.12-R Reconstructed Expansion Design

## 目标

V0.12-R 将 V0.11-R 的 200 case reconstructed zero-shot 回放扩展到全量或接近全量，以观察指标稳定性。

## 分支边界

本阶段是 reconstructed 分支，不是正式 V0.12，也不是正式 V0.11。输入 replay cases 来源于 reconstructed candidate history，而不是真实左侧历史候选池。

## 输入来源

Replay cases 来自 data/real/replay/kronos_v10_reconstructed_replay_cases.csv，K 线来自 data/real/normalized/kline。

## Resume

脚本从 outputs/kronos_v12r_reconstructed_full_predictions.csv 读取已完成 replay_id，后续运行只执行未完成 case。

## 分批策略

默认每批 100 cases。每批通过 KronosHistoricalReplayPipeline 执行并追加去重到全量 predictions。

## 分组指标

group_by_symbol 用于观察不同 ETF 的误差与方向命中；group_by_rank 用于观察 reconstructed 排名位置差异；group_by_month 用于观察时间段稳定性。

## V0.11-R Baseline

summary 会记录 V0.11-R 200-case baseline direction_accuracy，并计算扩展后 direction_accuracy_delta_vs_v11r。

## 局限

结果不能代表真实左侧历史候选池表现，不能作为正式 V0.11/V0.12 结论，也不可作为交易依据。

## 安全边界

本阶段不训练、不微调、不运行 torchrun、不下单、不访问交易接口、不回写主项目、不修改左侧项目。
