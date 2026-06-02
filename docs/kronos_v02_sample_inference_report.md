# Kronos V0.2 样本推理报告

- 生成时间: 2026-06-02 23:17:23
- 运行时间: 16.40s
- Python 版本: 3.12.0
- torch 版本: 2.12.0+cu126
- CUDA 版本: 12.6
- GPU 名称: NVIDIA GeForce RTX 4060 Ti
- 模型名称: NeoQuasar/Kronos-small
- tokenizer 名称: NeoQuasar/Kronos-Tokenizer-base
- lookback: 400
- pred_len: 120
- max_context: 512
- T: 1.0
- top_p: 0.9
- sample_count: 1
- 输入数据源: external/Kronos/tests/data/regression_input.csv (E:\AETF-ModelLab\external\Kronos\tests\data\regression_input.csv)
- 输入字段: open, high, low, close, volume, amount
- 输出字段: timestamps, open, high, low, close, volume, amount
- 是否使用 GPU: True
- 显存使用观察-运行前: {'available': True, 'allocated_mib': 0.0, 'reserved_mib': 0.0, 'max_allocated_mib': 0.0, 'name': 'NVIDIA GeForce RTX 4060 Ti'}
- 显存使用观察-运行后: {'available': True, 'allocated_mib': 120.95, 'reserved_mib': 152.0, 'max_allocated_mib': 136.27, 'name': 'NVIDIA GeForce RTX 4060 Ti'}
- 是否成功导入 Kronos 类: True
- 是否成功加载 Kronos-small: True
- 是否成功完成推理: True
- 输出 CSV 路径: E:\AETF-ModelLab\outputs\kronos_v02_sample_prediction.csv
- 失败原因: N/A

## pred_df.head()

```text
         timestamps      open      high       low     close      volume       amount
2024-06-28 14:05:00 10.822159 10.834056 10.811458 10.820602  523.151428  563867.9375
2024-06-28 14:10:00 10.817679 10.829527 10.798173 10.803773  447.788452  485101.1875
2024-06-28 14:15:00 10.822860 10.834818 10.793283 10.798425  546.139832  583950.0625
2024-06-28 14:20:00 10.800748 10.816830 10.793537 10.806897  355.710815  387684.3125
2024-06-28 14:25:00 10.805638 10.809422 10.787955 10.788035 1406.369507 1486529.0000
```
