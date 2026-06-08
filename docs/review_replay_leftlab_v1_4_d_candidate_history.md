# Review: Replay LeftLab V1.4-D Candidate History

## Review Verdict

Review status: **APPROVED**.

Recommendation:

- 建议合并 `replay-leftlab-v1-4-d-candidate-history` 到 `main`.
- ModelLab 已完成 true-left candidate history replay, based on the branch replay document.
- `formal_v011_ready=false`.
- 不建议进入训练或主项目接入.
- 建议下一步更新 Protocol 状态: `modellab_received=true`, `modellab_replay_completed=true`, `formal_v011_ready=false`.

## Branch And Commit

- Review branch: `replay-leftlab-v1-4-d-candidate-history`
- Reviewed commit hash: `ca6db30c2b7c1139b5a1efe943b1390c7894485c`
- Upstream: `origin/replay-leftlab-v1-4-d-candidate-history`
- Latest commit confirmed by `git log --oneline -5`: `ca6db30 docs: replay LeftLab candidate history`
- Expected commit match: yes
- Review checkout: `/Users/a1/Developer/AETF-ModelLab-Q3-clean`

## Git Status And Remote

`git status --short --branch` before this report:

```text
## replay-leftlab-v1-4-d-candidate-history...origin/replay-leftlab-v1-4-d-candidate-history
```

`git remote -v`:

```text
origin	https://github.com/C8590/AETF-ModelLab-Q3.git (fetch)
origin	https://github.com/C8590/AETF-ModelLab-Q3.git (push)
```

## Diff Scope

Reviewed diff:

```text
git diff main...replay-leftlab-v1-4-d-candidate-history
```

Diff summary:

```text
 .gitignore                                      |   5 +
 docs/replay_leftlab_v1_4_d_candidate_history.md | 138 ++++++++++
 scripts/replay_leftlab_candidate_history.py     | 325 ++++++++++++++++++++++++
 3 files changed, 468 insertions(+)
```

Changed files:

```text
A	.gitignore
A	docs/replay_leftlab_v1_4_d_candidate_history.md
A	scripts/replay_leftlab_candidate_history.py
```

Scope conclusions:

- Only `.gitignore`, replay documentation, and a read-only replay script were submitted: yes
- `runtime_inbox/` payload submitted: no
- READY zip submitted: no
- `outputs/replay/` runtime output submitted: no
- Model weights or training outputs submitted: no
- LeftLab modified: no
- Protocol modified: no
- Training-related code started or wired into the main project: no

`.gitignore` protects:

```text
runtime_inbox/
outputs/replay/
.pytest_cache/
__pycache__/
*.pyc
```

Tracked-file check found no `runtime_inbox`, no READY zip, no `outputs/replay`, and no model-weight files.

## Replay Script Review

Reviewed file:

```text
scripts/replay_leftlab_candidate_history.py
```

Conclusion: approved.

The script:

- Reads the handoff payload directory supplied through `--input`.
- Requires handoff files such as `manifest.json`, `candidate_history.jsonl`, `artifact_index.json`, and the ref snapshots.
- Does not import `torch`.
- Does not call GPU or CUDA APIs.
- Does not train, fit, or optimize a model.
- Does not modify the handoff payload.
- Writes replay audit artifacts only under the caller-provided `--output`, documented as `outputs/replay/leftlab_v1_4_d/`.
- Keeps formal readiness conservative when stopline reasons exist.
- Records boundary flags for no trained model, no `torchrun`, no GPU, no trading advice, and no auto-integration.

The script is an audit/replay utility, not a trading-advice generator and not an automatic main-project integration path.

## Replay Document Review

Reviewed file:

```text
docs/replay_leftlab_v1_4_d_candidate_history.md
```

Conclusion: approved.

The document accurately records:

- Input handoff path under `runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff`.
- Runtime outputs under `outputs/replay/leftlab_v1_4_d/`.
- `candidate_count=20`.
- Handoff status `READY`.
- Refs coverage `20/20` for feature, similar case, frontend explanation, label, and probability bucket snapshots.
- Replay completed.
- Decision matrix recomputed.
- `decision_distribution={"unknown": 20}`.
- `label_status_distribution={"pending": 20}`.
- `risk_bucket_counts={"样本不足": 9, "风险偏高": 11}`.
- Reconstructed artifacts missing.
- True-left vs reconstructed alignment incomplete.
- `formal_v011_ready=false`.
- `stopline_triggered=true`.
- Complete false reasons:
  - `reconstructed_alignment_incomplete`
  - `majority_baseline_unavailable`
  - `realized_outcome_fields_missing`
- No model training, no `torchrun`, no GPU, no `formal_v011` start.
- No runtime payload / READY zip submission.
- Not trading advice and not an automatic production gate.

## Candidate And Ref Conclusions

- `candidate_count`: 20, consistent between the replay document and the script's expected validation logic.
- Feature snapshot refs: `20/20`.
- Similar case refs: `20/20`.
- Frontend explanation snapshot refs: `20/20`.
- Label snapshot refs: `20/20`.
- Probability bucket snapshot refs: `20/20`.
- Decision matrix: recomputed for true-left candidate history, with all 20 decisions still `unknown`.
- Label status: all 20 remain `pending`.
- Risk buckets: 9 `样本不足`, 11 `风险偏高`.

## Formal Readiness Review

Conclusion: `formal_v011_ready=false` is reasonable and correctly conservative.

The branch does not automatically promote `formal_v011_ready=true` merely because the handoff manifest is `READY`.

The NOT_READY / stopline result is justified because:

- Reconstructed artifacts are missing, so true-left vs reconstructed alignment is incomplete.
- Majority baseline is unavailable.
- Realized outcome fields are missing.

Therefore `stopline_triggered=true` is appropriate, and the branch should not proceed into training or main-project integration.

## Validation

Allowed validation commands run on the Mac review node:

```text
PYTHONPATH='.:src' /Users/a1/Developer/AETF-LeftLab/.venv/bin/python -m pytest
/Users/a1/Developer/AETF-LeftLab/.venv/bin/python -m py_compile scripts/replay_leftlab_candidate_history.py
```

Results:

```text
pytest: collected 0 items; no tests ran
py_compile: passed
```

The repository checkout did not contain runnable tests, so this review records **no tests available to run**, not a passing test suite.

Commands intentionally not run:

- training
- `torchrun`
- GPU/CUDA calls
- `formal_v011`
- replay execution against runtime payload
- runtime payload copy or commit

## Forbidden Scope Check

Review found no evidence that this branch:

- Trained a model.
- Ran `torchrun`.
- Called GPU.
- Started `formal_v011`.
- Submitted `runtime_inbox/` payload.
- Submitted the READY zip.
- Submitted `outputs/replay/` runtime files.
- Modified LeftLab.
- Modified Protocol.
- Auto-integrated replay results into the main project.

## Final Recommendation

建议合并 `replay-leftlab-v1-4-d-candidate-history` 到 `main`.

ModelLab 已完成 true-left candidate history replay.

`formal_v011_ready=false`.

不建议进入训练或主项目接入.

建议下一步更新 Protocol 状态: `modellab_received=true`, `modellab_replay_completed=true`, `formal_v011_ready=false`.
