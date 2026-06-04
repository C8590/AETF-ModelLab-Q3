# Left Candidate History Discovery Report

- 运行时间: 2026-06-04T14:00:46
- discovery_status: LEFT_CANDIDATE_HISTORY_NOT_FOUND
- 是否找到左侧项目目录: True
- 左侧项目目录: E:/AETF-LeftLab
- 扫描文件数量: 2164
- 候选历史源数量: 2
- 是否导出 left_candidates_history.csv: False
- 导出路径: -
- 选中来源: -
- candidate_date_count: 0
- candidate row_count: 0
- matched_symbol_count: 0

## Candidate Sources

| path | kind | rows | matched_fields | confidence |
| --- | --- | ---: | --- | ---: |
| E:/AETF-LeftLab/.pytest_workspace_tmp/streamlit_user_view_stderr.log | log | 0 |  | 3 |
| E:/AETF-LeftLab/.pytest_workspace_tmp/streamlit_user_view_stdout.log | log | 0 |  | 3 |

## Reviewed Sources

- 无可复核来源。

## Scope

- 仅只读扫描左侧项目目录。
- 未修改左侧项目。
- 未运行左侧项目程序。
- 未训练模型。
- 未运行 torchrun。
- 未调用 GPU 推理。
- 未运行 KronosAdapter。
- 未生成交易建议。
- 未生成 reconstructed candidate history。

## Next Steps

- 用户提供真实 left_candidates_history.csv。
- 或用户明确授权按左侧规则重建 reconstructed candidate history。
- reconstructed 不等于真实历史快照，不能冒充真实历史候选池。
