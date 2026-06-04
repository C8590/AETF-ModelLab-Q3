# Kronos V0.15-R Reconstructed Branch Closeout Design

## 目标

V0.15-R 对 reconstructed_v1 分支做正式收尾，生成分支状态、artifact index、最终报告和下一步决策包。该阶段只读取 V0.10.2-E 到 V0.14-R 的已有输出，不运行模型，不评估新样本，不调用 GPU。

## 为什么做分支收尾

V0.14-R stopline 已经给出 `PAUSE_RECONSTRUCTED_BRANCH`。继续扩展 reconstructed_v1 不能解决候选池不是真实 left history 的根问题，也不能把低于 50% 的方向准确率解释成可继续推进的证据。因此需要用 V0.15-R 固化结论，避免误入正式 V0.11 或训练阶段。

## 分支阶段列表

- V0.10.2-E：构建 reconstructed candidate history readiness。
- V0.11-R：200-case reconstructed zero-shot replay baseline。
- V0.12-R：1341-case reconstructed full expansion。
- V0.13-R：reconstructed dashboard 与诊断报告。
- V0.14-R：误差诊断与 stopline。
- V0.15-R：分支收尾与下一步决策包。

## Stopline 摘要

V0.14-R 结果：evaluated_case_count=1341，direction_accuracy=0.40939597315436244，majority_direction_accuracy=0.6017897091722595，Wilson interval 为 0.38337259776730287 到 0.4359369774272778，decision=`PAUSE_RECONSTRUCTED_BRANCH`。

## 暂停原因

当前分支暂停，因为 direction_accuracy 低于 50%，低于多数类基线，且 V0.12-R 全量扩展没有确认 V0.11-R 200-case baseline 的稳定性。reconstructed candidate history 也不是真实左侧历史候选池。

## 为什么不能进入正式 V0.11

正式 V0.11 需要真实 `left_candidates_history.csv`。reconstructed_v1 的候选池来源是规则重构，不可代表真实左侧历史候选表现。

## 为什么不能进入训练

训练需要可靠的目标数据和可解释的候选池来源。当前 reconstructed_v1 的 stopline 已经暂停，继续训练只会放大不可靠输入，不符合本地验收边界。

## 下一步三路径

- `OBTAIN_TRUE_LEFT_CANDIDATE_HISTORY`: 推荐路径，等待或导入真实 left_candidates_history.csv 后回到正式路线。
- `REDESIGN_RECONSTRUCTED_CANDIDATE_RULES_FROM_V0102E2`: 可选研究路径，重新设计 reconstructed 规则并从 V0.10.2-E2 重新开始。
- `DO_NOT_TRAIN_OR_TRADE_ON_RECONSTRUCTED_V1`: 阻断路径，不能基于 reconstructed_v1 训练、交易或推进正式 V0.11。

## Artifact Index

artifact index 记录每个输入和输出工件的 path、exists、size_bytes、artifact_type、stage 和 note。缺失工件只记录，不通过模型、GPU 或主项目重生成。

## 安全边界

本阶段不训练、不微调、不运行 torchrun、不调用 GPU、不运行 KronosAdapter、不下单、不回写主项目、不接 AETF-LeftLab / A-ETF-L，不输出任何交易建议。V0.15-R 不是正式 V0.15，也不是正式 V0.11。
