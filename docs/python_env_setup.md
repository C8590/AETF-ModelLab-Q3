# Python / PyTorch / CUDA 环境搭建说明

## 1. 目标

在独立 Python 环境中检查 NVIDIA 4060 Ti 是否可被 PyTorch 识别，并确认 GPU tensor 计算可以正常执行。

## 2. Windows 推荐流程

```powershell
cd /d E:\AETF-ModelLab
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

安装 CUDA 版 PyTorch。具体 CUDA 版本以 PyTorch 官网选择器为准；常用示例：

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

检查：

```powershell
python scripts/check_cuda.py
```

## 3. 检查项

- 操作系统。
- Python 版本。
- PyTorch 版本。
- `torch.version.cuda`。
- `torch.cuda.is_available()`。
- GPU 数量。
- GPU 名称。
- GPU compute capability。
- 显存大小。
- `nvidia-smi`。
- GPU tensor 矩阵乘法测试。

## 4. 通过标准

`docs/pytorch_cuda_env_check.md` 中必须显示：

```text
CUDA 可用：True
Tensor 测试：PASS
是否可以进入 Kronos 部署阶段：YES
```

## 5. 常见失败

### 5.1 安装了 CPU 版 PyTorch

表现：

```text
torch.cuda.is_available() = False
```

处理：卸载后安装 CUDA 版。

```powershell
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

### 5.2 NVIDIA 驱动不可用

表现：

```text
nvidia-smi 不存在或报错
```

处理：更新 NVIDIA 驱动后重启。

### 5.3 Python 版本太低

处理：安装 Python 3.10+，重新创建 `.venv`。
