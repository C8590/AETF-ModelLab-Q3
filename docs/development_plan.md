# AETF-ModelLab 完整开发计划

版本：V0.1-scaffold  
日期：2026-06-02  
项目定位：AETF 左侧 ETF 策略的 AI 影子预测实验室。

---

## 1. 总目标

AETF-ModelLab 的目标不是自动交易，而是建立一个本地金融模型实验项目部，为左侧 ETF 项目提供“影子预测能力”。

第一阶段只回答：

1. 本机 4060 Ti 能不能稳定跑 PyTorch / CUDA 推理。
2. Kronos 能不能在本地完成 ETF 日 K 预测。
3. Kronos 的影子判断是否能降低破低率、提高左侧修复成功率。

只有历史回放证明有效后，才允许进入左侧主项目的展示层或辅助决策层。

---

## 2. 项目部组织

即使由一个人开发，也按以下角色分工推进，避免职责混乱。

| 角色 | 职责 | 关键产出 |
|---|---|---|
| 项目负责人 | 控制边界、版本节奏、验收标准 | 版本路线、验收结论 |
| 环境工程 | Python、PyTorch、CUDA、GPU 检查 | `docs/pytorch_cuda_env_check.md` |
| 数据工程 | ETF 日 K、候选池、风控文件读取与校验 | `src/model_lab/data_loader.py` |
| 模型工程 | Kronos 研究、部署、推理封装 | `src/model_lab/kronos_adapter.py` |
| 策略接口工程 | 将原始预测转成左侧可读字段 | `outputs/kronos_shadow_features.csv` |
| 回放工程 | 避免未来函数，统计破低率/修复率/收益/回撤 | `docs/kronos_backtest_report.md` |
| QA / 风控 | 检查不得修改左侧规则，不产生自动交易行为 | 风险清单、验收门禁 |

---

## 3. 总体架构

```text
左侧主项目生成候选池 left_candidates.csv
            ↓ 只读
AETF-ModelLab 读取候选池 + ETF 日 K + risk_warning
            ↓
Kronos 本地推理，生成未来 3/5/10 日预测路径
            ↓
转换成 AI 影子特征 kronos_shadow_features.csv
            ↓ 只读
左侧主项目读取标准文件并展示“AI影子判断”
```

硬边界：AETF-ModelLab 不写入左侧主项目，不修改买入规则、风控规则、持仓状态，不触发下单。

---

## 4. 版本路线与里程碑

| 版本 | 阶段 | 目标 | 核心任务 | 输出 | 验收 |
|---|---|---|---|---|---|
| V0.1 | PyTorch / CUDA 环境检查 | 确认 4060 Ti 可跑 GPU 推理 | 建目录、独立 venv、安装 PyTorch、运行 tensor 测试 | `docs/pytorch_cuda_env_check.md` | CUDA 可用、GPU 名称正确、tensor 测试通过 |
| V0.2 | Kronos 仓库研究与样本推理 | 本地跑通 Kronos-small 单只 ETF | 拉取 Kronos、记录 I/O、下载 small 权重、跑 1 只 ETF | `outputs/kronos_daily_forecast.csv` | 未来 10 日 OHLCV 预测可生成 |
| V0.3 | Adapter 封装 | 统一 Kronos 输入输出 | 封装 `KronosAdapter`，支持 CPU fallback、异常处理 | `src/model_lab/kronos_adapter.py` | 调用接口稳定，字段标准化 |
| V0.4 | AI 影子特征 | 把原始预测变成左侧可读字段 | 计算 3/5/10 日收益、破低、RR、动作、中文解释 | `outputs/kronos_shadow_features.csv` | 候选池批量生成、解释可读 |
| V0.5 | 历史回放验证 | 判断模型是否真的提升策略质量 | 日切回放、避免未来函数、统计破低率/修复率 | `docs/kronos_backtest_report.md` | 给出是否接入展示层结论 |
| V0.6 | 前端展示对接 | 只读展示 AI 影子判断 | 左侧项目读取输出 CSV，展示字段 | 前端展示说明 | 不影响交易规则 |
| V0.7 | 本地微调评估 | 决定是否 ETF 本地 fine-tune | 数据量、收益、风险、泛化评估 | 微调评估报告 | 只有回放显著有效才进入 |

---

## 5. V0.1 详细计划：环境检查

### 5.1 任务清单

1. 创建独立项目目录 `AETF-ModelLab`。
2. 创建独立 Python 3.10+ 虚拟环境。
3. 按目标机 CUDA 版本安装 PyTorch。
4. 执行 `scripts/check_cuda.py`。
5. 检查以下项目：
   - `torch.__version__`
   - `torch.version.cuda`
   - `torch.cuda.is_available()`
   - `torch.cuda.get_device_name(0)`
   - `torch.cuda.get_device_capability(0)`
   - 显存大小
   - `nvidia-smi` 输出
   - GPU tensor 矩阵乘法测试
6. 生成 `docs/pytorch_cuda_env_check.md`。
7. 若 CUDA 不可用，停止进入 V0.2。

### 5.2 执行命令

```powershell
cd /d E:\AETF-ModelLab
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
python scripts/check_cuda.py
```

### 5.3 V0.1 验收标准

- 能识别 NVIDIA 4060 Ti。
- `torch.cuda.is_available()` 返回 True。
- tensor 能放到 `cuda:0` 上计算。
- 报告显示显存大小与设备能力。
- 没有修改左侧主项目任何文件。

### 5.4 V0.1 阻断条件

- 未安装 CUDA 版 PyTorch。
- NVIDIA 驱动不可用。
- PyTorch 识别不到 GPU。
- 显存不足以运行最小推理样本。
- 目标机 Python 版本低于 3.10。

---

## 6. V0.2 详细计划：Kronos 本地样本推理

### 6.1 目标

只研究和部署 Kronos，不接入左侧主项目业务逻辑。

### 6.2 任务清单

1. 拉取 Kronos 到 `external/Kronos`。
2. 记录 Kronos 依赖项、入口类、输入输出格式。
3. 下载 `Kronos-small` 与 tokenizer 到 `models/kronos` 或本机 Hugging Face 缓存。
4. 准备单只 ETF 日 K 样本。
5. 以 `lookback=120/240`、`pred_len=10`、`sample_count=3` 跑样本。
6. 输出 `outputs/kronos_daily_forecast.csv`。
7. 记录显存占用、运行时间、失败原因。

### 6.3 推荐参数

```yaml
lookback: 240
pred_len: 10
sample_count: 3
max_context: 512
device: cuda
batch_size_4060ti_8gb: 16
batch_size_4060ti_16gb: 64
```

### 6.4 验收标准

- 能加载 `Kronos-small`。
- 能读取单只 ETF 日 K。
- 能输出未来 10 日预测 K 线。
- 显存不足时有明确报错或自动降 batch / sample_count。
- 不做 fine-tune。

---

## 7. V0.3 详细计划：Kronos Adapter

### 7.1 目标

封装一层本地适配器，让左侧项目未来只面对标准 CSV，不直接碰 Kronos 代码。

### 7.2 输入字段

```text
trade_date
code
open
high
low
close
volume
amount
```

内部转换为 Kronos 需要的：

```text
open
high
low
close
volume
amount
timestamps
```

### 7.3 输出字段

```text
trade_date
code
pred_date
pred_open
pred_high
pred_low
pred_close
pred_volume
pred_amount
model_name
lookback
pred_len
sample_count
run_time
```

### 7.4 工程要求

- 所有路径从 `configs/model_lab.yaml` 读取。
- Kronos import 失败时给出清晰错误。
- GPU OOM 时自动降低 batch 或 sample_count。
- CPU fallback 只用于小样本验证，不能作为正式回放速度依据。
- 输出文件覆盖前必须备份或写入 run_id。

---

## 8. V0.4 详细计划：AI 影子特征

### 8.1 目标

不要把 Kronos 原始预测直接给用户；要转成左侧项目能理解、可展示、可回放的影子字段。

### 8.2 输出字段

```text
trade_date
code
name
close
kronos_pred_close_3d
kronos_pred_close_5d
kronos_pred_close_10d
kronos_pred_return_3d
kronos_pred_return_5d
kronos_pred_return_10d
kronos_pred_low_5d
kronos_pred_high_5d
kronos_max_pred_drawdown_5d
kronos_break_recent_low
kronos_break_invalid_price
kronos_expected_upside
kronos_expected_downside
kronos_rr
kronos_shadow_score
kronos_shadow_action
kronos_explanation
model_name
run_time
```

### 8.3 动作枚举

| 动作 | 含义 |
|---|---|
| `SUPPORT_PROBE` | 支持小仓试探 |
| `WAIT` | 等待 |
| `RISK_OF_BREAKDOWN` | 有继续破低风险 |
| `CONFLICT` | 与规则信号冲突 |
| `NO_SIGNAL` | 无有效预测 |
| `ERROR` | 模型推理失败 |

### 8.4 风控优先级

`risk_warning` 高于 Kronos。

| 风险级别 | 规则 |
|---|---|
| R0/R1 | Kronos 可辅助提高或降低可信度 |
| R2 | Kronos 只能辅助，不能提高到强买入 |
| R3 | 禁止自动试探，Kronos 只能展示风险提示 |
| R4/P0 | 禁止左侧买入，Kronos 不允许提高任何买入级别 |

### 8.5 必须降级的情况

- 预测跌破 `invalid_price`。
- 预测跌破近期低点。
- 预测未来 5 日最大回撤过大。
- 预测路径持续下行。
- 模型结果缺失或异常。

---

## 9. V0.5 详细计划：历史回放验证

### 9.1 目标

验证 Kronos 是否真的提升左侧策略质量，而不是只生成好看的解释。

### 9.2 回放原则

必须避免未来函数。每个历史交易日只能使用当日及以前数据。

### 9.3 回放流程

```text
对每个历史交易日：
1. 截断到当日数据。
2. 读取或生成当日左侧候选。
3. Kronos 预测未来 3 / 5 / 10 日。
4. 生成 kronos_shadow_action。
5. 读取真实未来走势。
6. 判断是否破低、是否修复成功、收益和回撤。
7. 汇总统计。
```

### 9.4 重点统计

- `SUPPORT_PROBE` 的未来 5 日胜率。
- `SUPPORT_PROBE` 的未来 10 日胜率。
- `RISK_OF_BREAKDOWN` 的真实破低率。
- Kronos 与左侧规则冲突时谁更准。
- 是否降低 `bad_left_probe` 比例。
- 是否提高 `successful_repair` 比例。
- 不同板块下是否有效。
- 不同 `risk_level` 下是否失效。

### 9.5 输出

```text
outputs/kronos_historical_predictions.csv
outputs/kronos_shadow_backtest_samples.csv
outputs/kronos_error_cases.csv
docs/kronos_backtest_report.md
```

### 9.6 是否接入左侧展示层的判断门槛

建议至少满足：

- `SUPPORT_PROBE` 样本数足够，且未来 5/10 日收益与修复率优于基准。
- `RISK_OF_BREAKDOWN` 对破低风险有显著识别能力。
- 分板块、分风险级别结果没有明显灾难性失效区。
- 异常率、超时率、缺失率可控。
- 结论稳定，不依赖少数样本。

---

## 10. V0.6 详细计划：前端只读展示

### 10.1 接入原则

左侧主项目只读 `outputs/kronos_shadow_features.csv` 或同步后的标准文件。

### 10.2 前端展示建议

- AI 影子动作：`SUPPORT_PROBE / WAIT / RISK_OF_BREAKDOWN / CONFLICT`。
- 中文解释。
- 预测 3/5/10 日收益。
- 预测 5 日低点是否跌破失效价。
- 风控提示：当 `risk_level` 为 R3/R4/P0 时，必须展示风控优先。

### 10.3 禁止

- 禁止前端把 Kronos 结论直接映射为买入按钮。
- 禁止修改左侧策略状态。
- 禁止自动下单。

---

## 11. V0.7 详细计划：是否 fine-tune

第一阶段不做 fine-tune。只有满足以下条件才评估 ETF 本地微调：

- V0.5 回放证明 zero-shot 或 small/base 推理有效。
- ETF 日 K 数据规模、质量、连续性满足训练要求。
- 有足够算力与可重复训练流程。
- 微调后的提升能通过严格回放证明，不是过拟合。

---

## 12. 风险清单

| 风险 | 表现 | 处理 |
|---|---|---|
| CUDA 环境不一致 | `torch.cuda.is_available()` 为 False | 回到 V0.1，修驱动和 PyTorch 安装 |
| 4060 Ti 显存不足 | OOM | 降低 batch_size、sample_count、lookback，优先 small |
| 未来函数 | 回放结果虚高 | 日切截断，严格只用当日及以前数据 |
| 数据字段不一致 | 预测失败或解释错误 | `validation.py` 统一字段校验 |
| 模型过度自信 | 前端误导 | 只输出影子判断，不直接买入 |
| 左侧项目污染 | 环境或文件被改 | 左侧路径只读，禁止写入左侧目录 |
| 权重入库 | Git 仓库膨胀或泄漏 | `.gitignore` 排除 `models/` 权重 |
| 外部数据上传 | 策略数据泄漏 | 全流程本地运行 |

---

## 13. 质量门禁

进入下一阶段前必须满足：

```text
V0.1 → V0.2：CUDA 检查通过。
V0.2 → V0.3：Kronos-small 单 ETF 预测通过。
V0.3 → V0.4：Adapter 输出标准 forecast CSV。
V0.4 → V0.5：影子字段可批量生成且解释稳定。
V0.5 → V0.6：回放证明有实际增益。
V0.6 → V0.7：展示层稳定且不影响策略规则。
```

---

## 14. 第一条执行指令

```text
请在不修改左侧主项目的前提下，新建独立金融模型项目部 AETF-ModelLab。
第一阶段只做 PyTorch / CUDA 环境检查，不部署 Kronos，不下载大模型权重，不接入交易逻辑。

要求：
1. 创建项目目录。
2. 创建独立 Python 环境说明。
3. 新增 scripts/check_cuda.py。
4. 检查 PyTorch 是否能识别 4060 Ti。
5. 执行简单 GPU tensor 测试。
6. 输出 docs/pytorch_cuda_env_check.md。
7. 新增 .gitignore，排除模型权重、缓存、日志、大型输出。
8. 提交 Git。
9. 给出执行结果和下一阶段建议。

不得修改：
AETF-LeftLab
A-ETF-L
任何左侧策略代码
任何买入规则
任何风控规则
任何状态文件
```
