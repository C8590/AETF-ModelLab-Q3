# PyTorch / CUDA 环境检查报告

生成时间：2026-06-02 22:59:14  
项目：AETF-ModelLab  
阶段：V0.1 PyTorch / CUDA 环境检查  

## 1. 结论

| 项目 | 结果 |
|---|---|
| Python 版本 | `3.12.0 (tags/v3.12.0:0fb18b0, Oct  2 2023, 13:03:39) [MSC v.1935 64 bit (AMD64)]` |
| 操作系统 | `Windows-11-10.0.22631-SP0` |
| PyTorch 已安装 | `True` |
| PyTorch 版本 | `2.12.0+cu126` |
| PyTorch CUDA 版本 | `12.6` |
| CUDA 可用 | `True` |
| GPU 数量 | `1` |
| Tensor 测试 | `PASS` |
| 是否可以进入 Kronos 部署阶段 | `YES` |

## 2. GPU 设备

| Index | 名称 | Compute Capability | 显存 GB | SM 数 |
|---:|---|---:|---:|---:|
| 0 | NVIDIA GeForce RTX 4060 Ti | 8.9 | 8.0 | 34 |

## 3. nvidia-smi

可执行：`True`  
返回码：`0`

```text
Tue Jun  2 22:59:14 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 610.47                 KMD Version: 610.47        CUDA UMD Version: 13.3     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 4060 Ti   WDDM  |   00000000:01:00.0 Off |                  N/A |
|  0%   40C    P8              9W /  160W |    1000MiB /   8188MiB |     28%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A            2008    C+G   ..._cw5n1h2txyewy\SearchHost.exe      N/A      |
|    0   N/A  N/A            2396    C+G   ...y\StartMenuExperienceHost.exe      N/A      |
|    0   N/A  N/A            6612    C+G   ...8bbwe\PhoneExperienceHost.exe      N/A      |
|    0   N/A  N/A            7300    C+G   ....0.3967.96\msedgewebview2.exe      N/A      |
|    0   N/A  N/A            7304    C+G   C:\Windows\explorer.exe               N/A      |
|    0   N/A  N/A            7996    C+G   ...5n1h2txyewy\TextInputHost.exe      N/A      |
|    0   N/A  N/A           10680    C+G   ...ntrolPanel\SystemSettings.exe      N/A      |
|    0   N/A  N/A           12940    C+G   ...crosoft OneDrive\OneDrive.exe      N/A      |
|    0   N/A  N/A           13176    C+G   ...ogram Files\ToDesk\ToDesk.exe      N/A      |
|    0   N/A  N/A           15860    C+G   ...__2p2nqsd0c76g0\app\Codex.exe      N/A      |
|    0   N/A  N/A           17044    C+G   ...8wekyb3d8bbwe\M365Copilot.exe      N/A      |
|    0   N/A  N/A           17880    C+G   ...App_cw5n1h2txyewy\LockApp.exe      N/A      |
|    0   N/A  N/A           18152    C+G   ...IA app\CEF\NVIDIA Overlay.exe      N/A      |
|    0   N/A  N/A           19420    C+G   ...IA app\CEF\NVIDIA Overlay.exe      N/A      |
|    0   N/A  N/A           20868    C+G   ....0.3967.96\msedgewebview2.exe      N/A      |
|    0   N/A  N/A           23668    C+G   ...em_tray\lghub_system_tray.exe      N/A      |
|    0   N/A  N/A           25692    C+G   ...t\Edge\Application\msedge.exe      N/A      |
|    0   N/A  N/A           26188    C+G   ...2p2nqsd0c76g0\app\ChatGPT.exe      N/A      |
|    0   N/A  N/A           28088    C+G   ....0.3967.96\msedgewebview2.exe      N/A      |
|    0   N/A  N/A           28412    C+G   ...yb3d8bbwe\Notepad\Notepad.exe      N/A      |
|    0   N/A  N/A           31464    C+G   ...xyewy\ShellExperienceHost.exe      N/A      |
+-----------------------------------------------------------------------------------------+
```

## 4. 错误信息

```text
Torch import error: None
Tensor test error: None
```

## 5. 验收判断

```text
V0.1_PASS = True
NEXT_STEP = 进入 V0.2 Kronos 本地样本推理
```

## 6. 边界确认

本检查脚本不读取、不修改左侧主项目，不下载模型权重，不执行交易逻辑。
