# Kronos V0.3 Adapter 冒烟报告

- 生成时间: 2026-06-02 23:28:38
- 运行时间: 7.01s
- Python 版本: 3.12.0
- torch 版本: 2.12.0+cu126
- CUDA 版本: 12.6
- GPU 名称: NVIDIA GeForce RTX 4060 Ti
- 模型名称: NeoQuasar/Kronos-small
- tokenizer 名称: NeoQuasar/Kronos-Tokenizer-base
- 是否通过 Adapter 加载: True
- 是否通过 Adapter 推理: True
- 输入字段: timestamps, open, high, low, close, volume, amount
- 输出字段: timestamps, open, high, low, close, volume, amount
- lookback: 120
- pred_len: 24
- 输出 CSV 路径: E:\AETF-ModelLab\outputs\kronos_v03_adapter_prediction.csv
- pytest 结果: 13 passed
- 是否可以进入 V0.4 影子预测设计: True
- 显存使用观察-运行前: {'available': True, 'allocated_mib': 0.0, 'reserved_mib': 0.0, 'max_allocated_mib': 0.0, 'name': 'NVIDIA GeForce RTX 4060 Ti'}
- 显存使用观察-运行后: {'available': True, 'allocated_mib': 118.56, 'reserved_mib': 140.0, 'max_allocated_mib': 122.84, 'name': 'NVIDIA GeForce RTX 4060 Ti'}
- 失败原因: N/A

## pred_df.head()

```text
         timestamps      open      high       low     close      volume      amount
2024-06-20 14:45:00 11.013877 11.033864 11.003569 11.023383  678.854858  682193.250
2024-06-20 14:50:00 11.012412 11.033617 10.998189 11.020667 1324.073975 1356993.750
2024-06-20 14:55:00 11.023520 11.027264 10.997292 11.005977 1517.928711 1564170.875
2024-06-20 15:00:00 11.019485 11.010990 11.011641 11.000117 1378.481445 1345983.875
2024-06-21 09:35:00 11.006049 11.010218 10.971944 10.983891 2328.377441 2390116.750
```
