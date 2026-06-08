# ModelLab Repo Lineage Audit

## Clean Clone Follow-Up

Controller accepted the quarantine recommendation.

- quarantined legacy worktree: `E:\AETF-ModelLab-Q3`
- clean clone path: `E:\AETF-ModelLab-Q3-clean`
- clean clone remote: `https://github.com/C8590/AETF-ModelLab-Q3.git`
- clean clone `main`: `93d2b57e340aea6ac5f1ebab46075264c34ed118`
- clean clone `origin/main`: `93d2b57e340aea6ac5f1ebab46075264c34ed118`
- clean clone merge-base: `93d2b57e340aea6ac5f1ebab46075264c34ed118`
- clean clone status after clone/pull: clean before staging receive docs

The clean clone has normal lineage against `origin/main`. Replay remains blocked until a separate replay branch is opened from this clean clone and the controller explicitly authorizes replay.

## Scope

This audit records the repository lineage issue found before starting LeftLab V1.4-D replay.

No replay was started. `formal_v011` was not started. No model was trained, `torchrun` was not run, GPU was not called, and no LeftLab or Protocol workspace was modified.

## Local Repository

- local workspace: `E:\AETF-ModelLab-Q3`
- current branch during audit: `plan-leftlab-v1-4-d-replay`
- remote: `origin https://github.com/C8590/AETF-ModelLab-Q3.git`
- `git fetch origin`: success

## Branch Heads

| Ref | HEAD |
| --- | --- |
| local `main` | `9247e656c93349409bcc87b6d2206fdfb938a3c8` |
| `origin/main` | `93d2b57e340aea6ac5f1ebab46075264c34ed118` |
| local `receive-leftlab-v1-4-d-handoff` | `41b5f370a8f57eae0a697b45f628f349cd967842` |
| local `plan-leftlab-v1-4-d-replay` | `02174a834a258a21428fd76aa704b06a957e5ebe` |
| `origin/receive-leftlab-v1-4-d-handoff` | `41b5f370a8f57eae0a697b45f628f349cd967842` |
| `origin/plan-leftlab-v1-4-d-replay` | `02174a834a258a21428fd76aa704b06a957e5ebe` |

The pushed receive and plan branches are recoverable from the remote:

- `git show --stat origin/receive-leftlab-v1-4-d-handoff`: success
- `git show --stat origin/plan-leftlab-v1-4-d-replay`: success

## Merge-Base Results

| Check | Result |
| --- | --- |
| `git merge-base main origin/main` | failed, exit `1`, no merge base |
| `git merge-base receive-leftlab-v1-4-d-handoff origin/main` | failed, exit `1`, no merge base |
| `git merge-base plan-leftlab-v1-4-d-replay origin/main` | failed, exit `1`, no merge base |

Additional ancestry checks:

- `origin/main` is not an ancestor of `plan-leftlab-v1-4-d-replay`.
- local `main` is an ancestor of `plan-leftlab-v1-4-d-replay`.
- `origin/main` is not an ancestor of `receive-leftlab-v1-4-d-handoff`.
- local `main` is an ancestor of `receive-leftlab-v1-4-d-handoff`.

Root commit comparison:

| Ref | Root commit |
| --- | --- |
| local `main` root | `3b326055d940bc91cdf7998cc3f9e2aa5f1237f8` |
| `origin/main` root | `ee8e0285f6e91f6f32e861cbe01a16aa1473bfbf` |

Commit counts:

- local `main`: `27`
- `origin/main`: `4`

This confirms that local `main` and `origin/main` are unrelated histories. The earlier `git pull origin main` failure is expected and should not be bypassed with `--allow-unrelated-histories` for replay work.

## Unrelated Histories Behavior

Observed pull failure:

```text
fatal: refusing to merge unrelated histories
```

The receive and plan branches were pushed successfully, but they are based on the local legacy `main`, not on `origin/main`. They should be treated as recoverable documentation branches, not as clean replay bases.

## Current Uncommitted And Untracked Files

Current working tree has pre-existing uncommitted/untracked files that were not cleaned or modified by this audit:

```text
 M docs/kronos_v10_real_data_quality_report.md
 M docs/pytorch_cuda_env_check.md
 M outputs/real_data/kronos_v10_real_dataset_manifest.json
?? AETF-ModelLab_V0.1.git.bundle
?? AETF-ModelLab_V0.1_scaffold.zip
?? AETF-ModelLab_完整开发计划.md
?? data/real/normalized/
?? data/real/raw/kline/
?? runtime_inbox/
```

Tracked file watch list:

- `docs/kronos_v10_real_data_quality_report.md`: modified
- `docs/pytorch_cuda_env_check.md`: modified
- `outputs/real_data/kronos_v10_real_dataset_manifest.json`: modified

Untracked file/directory watch list:

- `AETF-ModelLab_V0.1.git.bundle`: present
- `AETF-ModelLab_V0.1_scaffold.zip`: present
- `AETF-ModelLab_完整开发计划.md`: present
- `data/real/normalized/`: present
- `data/real/raw/kline/`: present
- `runtime_inbox/`: present

No runtime inbox payload or READY zip should be committed from this workspace.

## Governance Conclusion

Do not continue replay from `E:\AETF-ModelLab-Q3`.

Reasons:

- local `main` and `origin/main` have unrelated histories;
- receive and plan branches are based on local legacy `main`, not remote `main`;
- the current worktree contains multiple unrelated modified/untracked files;
- runtime inbox payload exists locally and must remain uncommitted;
- replay should start from a clean, auditable branch lineage rooted at the remote repository.

Recommended action:

- mark `E:\AETF-ModelLab-Q3` as a quarantine / legacy worktree;
- do not delete or clean its existing files;
- use it only as a reference for already validated receive/plan facts until migrated;
- create a clean clone from the remote repository before replay.

Recommended clean clone path:

```text
E:\AETF-ModelLab-Q3-clean
```

Recommended clean-clone setup:

```powershell
Set-Location E:\
git clone https://github.com/C8590/AETF-ModelLab-Q3.git AETF-ModelLab-Q3-clean
Set-Location E:\AETF-ModelLab-Q3-clean
git fetch origin receive-leftlab-v1-4-d-handoff
git fetch origin plan-leftlab-v1-4-d-replay
```

Before replay, create a new replay branch from clean `origin/main` or a controller-approved clean base. If the receive/plan documents need to be available on that branch, cherry-pick or re-apply the documentation commits only after confirming they do not bring legacy history into the replay base.

## Replay Gate

Replay is not allowed from the current quarantined workspace.

Replay may be considered only after:

- a clean clone exists;
- the replay branch is based on clean remote lineage;
- the READY payload is staged into a runtime-only ignored inbox in the clean clone;
- receive/validate facts are rechecked or imported as documentation without merging unrelated histories;
- no runtime payload or READY zip is committed.
