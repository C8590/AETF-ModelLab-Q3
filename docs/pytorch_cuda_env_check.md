# PyTorch / CUDA 环境检查报告

状态：未在目标机执行。

请在目标机运行：

```bash
python scripts/check_cuda.py
```

脚本会自动覆盖本文件，写入真实检查结果。

## 验收要求

| 检查项 | 目标 |
|---|---|
| Python | 3.10+ |
| PyTorch | CUDA 版 |
| GPU | NVIDIA 4060 Ti |
| `torch.cuda.is_available()` | True |
| Tensor 测试 | PASS |
| 是否进入 V0.2 | YES |
