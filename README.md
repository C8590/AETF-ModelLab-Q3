# AETF-ModelLab

AETF-ModelLab 是 AETF 左侧 ETF 策略的 **AI 影子预测实验室**。

本项目独立于左侧主项目 `AETF-LeftLab / A-ETF-L`，第一阶段只做 PyTorch / CUDA 环境检查；后续在本地接入 Kronos 金融 K 线基础模型，生成影子判断字段，供左侧项目展示和回放验证使用。

## 1. 项目边界

### 允许做

- 新建独立 Python 环境。
- 检查 PyTorch / CUDA / NVIDIA GPU 是否可用。
- 后续本地拉取 Kronos 仓库与模型权重。
- 读取 ETF 日 K 数据与左侧候选池文件。
- 生成 `kronos_daily_forecast.csv`、`kronos_shadow_features.csv`、回放报告。

### 禁止做

- 不修改左侧主项目买入规则、风控规则、持仓状态文件。
- 不自动下单，不直接接 QMT。
- 第一阶段不部署 Kronos、不下载大模型权重、不做 fine-tune。
- 不把模型权重、缓存、大型预测结果提交进 Git。
- 不污染左侧主项目 Python 环境。
- 不把策略数据上传到外部服务。

## 2. 推荐放置位置

Windows：

```text
E:\AETF-LeftLab      ← 左侧主项目
E:\AETF-ModelLab     ← 本项目
```

macOS：

```text
/Users/a1/Developer/A-ETF-L        ← 左侧主项目
/Users/a1/Developer/AETF-ModelLab  ← 本项目
```

## 3. 当前版本

```text
V0.1-scaffold
```

当前包已经包含：

- 项目目录结构。
- 独立环境安装说明。
- PyTorch / CUDA 检查脚本。
- Kronos 后续接入接口骨架。
- AI 影子特征字段设计。
- 历史回放开发计划。
- `.gitignore` 防止权重、缓存、日志、大型输出入库。

## 4. 第一阶段执行命令

### Windows / NVIDIA 4060 Ti

建议在 PowerShell 或 CMD 中执行：

```powershell
cd /d E:\AETF-ModelLab
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

PyTorch 请以官网当前选择器为准。NVIDIA 4060 Ti 场景通常选择 Windows + Pip + Python + CUDA 版本：

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
python scripts/check_cuda.py
```

脚本会生成：

```text
docs/pytorch_cuda_env_check.md
```

### macOS / CPU 或 MPS 检查

本项目目标机是 NVIDIA 4060 Ti。macOS 只能做代码开发或小样本 CPU/MPS 验证，不作为 V0.1 GPU 验收依据。

```bash
cd /Users/a1/Developer/AETF-ModelLab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install torch torchvision
pip install -r requirements.txt
python scripts/check_cuda.py
```

## 5. 项目目录

```text
AETF-ModelLab/
  README.md
  pyproject.toml
  requirements.txt
  .gitignore
  docs/
    development_plan.md
    python_env_setup.md
    pytorch_cuda_env_check.md
    kronos_research_note.md
    kronos_shadow_design.md
    kronos_backtest_report.md
  configs/
    model_lab.yaml
    kronos_shadow.yaml
  scripts/
    check_cuda.py
    check_torch_env.py
    run_kronos_sample.py
    run_kronos_shadow_daily.py
    run_kronos_historical_replay.py
  src/model_lab/
    path_config.py
    validation.py
    data_loader.py
    kronos_adapter.py
    shadow_features.py
    report_writer.py
  external/Kronos/
  models/kronos/
  data/input/
  data/cache/
  data/samples/
  outputs/
  logs/
  tests/
```

## 6. 版本路线

```text
V0.1  PyTorch / CUDA 环境检查
V0.2  Kronos 仓库研究与样本推理
V0.3  Kronos adapter 封装
V0.4  左侧候选池 AI 影子预测
V0.5  历史回放验证
V0.6  前端 AI 影子判断展示
V0.7  评估是否进行 ETF 本地微调
```

详见：[`docs/development_plan.md`](docs/development_plan.md)
