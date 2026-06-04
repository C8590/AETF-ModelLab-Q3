# Kronos V0.11-R Reconstructed Replay Design

## 目标

V0.11-R 使用 reconstructed candidate history 生成的 replay cases，对未微调的 Kronos-small 做 zero-shot 历史回放评估。

## 分支边界

这是 reconstructed 分支，不是正式 V0.11。reconstructed candidate history 来源于真实 ETF K 线的过去窗口特征排序，不是真实左侧历史候选池快照。

## Zero-Shot

Zero-shot 表示直接使用已有 Kronos-small 和 tokenizer，不训练、不微调、不生成 checkpoint。

## 输入

Replay case 输入来自 data/real/replay/kronos_v10_reconstructed_replay_cases.csv，每个 case 指向 data/real/normalized/kline 下的标准化 K 线。

## 无未来函数

回放切片以 as_of_date 为边界，Kronos 输入窗口只包含 as_of_date 及以前的 lookback 行，actual future 只用于评估 pred_len 行。

## KronosAdapter

KronosAdapter 负责加载 Kronos-small、Tokenizer-base，并在 GPU 上执行 zero-shot predict。KronosHistoricalReplayPipeline 负责逐 case 切片、调用 adapter、比较预测与真实 future。

## 指标

核心指标包括 direction_accuracy、mean_abs_return_error、median_abs_return_error、rmse_return_error。分组指标按 symbol 和 candidate_rank 汇总，用于观察 reconstructed 分支的样本结构差异。

## 局限

本结果不能代表真实左侧项目历史候选池表现，不能作为正式 V0.11 结论，也不可作为交易依据。

## 与正式 V0.11

未来正式 V0.11 需要真实 left_candidates_history.csv，并基于真实左侧历史候选池回放。

## 安全边界

本阶段不训练、不微调、不运行 torchrun、不下单、不访问交易接口、不回写主项目、不修改左侧项目。
