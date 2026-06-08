# Reconstructed Artifacts Audit for LeftLab V1.4-G

## Stage Goal

Track A audits the remaining stopline reason:

```text
reconstructed_artifacts_missing
```

The goal is to determine whether reconstructed_v1 artifacts exist in the clean
ModelLab workspace, whether candidate artifacts exist in the quarantine
workspace, and what controlled steps are required before any artifact can be
used for formal replay/recheck.

This stage is audit-only. It does not train, does not run torchrun, does not call
GPU, does not modify LeftLab, does not modify Protocol, does not start
formal_v011, and does not fabricate reconstructed artifacts.

## Search Scope

Clean workspace:

```text
E:\AETF-ModelLab-Q3
```

Quarantine workspace, read-only:

```text
E:\AETF-ModelLab-Q3-quarantine
```

Searched path classes:

```text
docs/
outputs/
artifacts/
runtime/
closeout/
reports/
decision_matrix/
data/
examples/
configs/
```

Searched keywords:

```text
reconstructed
reconstructed_v1
decision_matrix
closeout
artifact_index
candidate_history
direction_accuracy
majority_direction_accuracy
PAUSED_BY_STOPLINE
PAUSE_RECONSTRUCTED_BRANCH
```

The reproducible audit script is:

```text
scripts/audit_reconstructed_artifacts.py
```

It writes runtime-only audit outputs to:

```text
outputs/reconstructed_artifacts/reconstructed_artifact_index.json
outputs/reconstructed_artifacts/reconstructed_artifact_candidates.csv
```

These outputs are ignored by Git and must not be committed.

## Clean Workspace Result

Clean workspace result:

```text
clean_reconstructed_artifacts_found = false
clean_candidate_count = 3
clean_documentation_candidate_count = 1
clean_runtime_artifact_candidate_count = 0
clean_has_candidate_history = false
clean_has_decision_matrix = false
clean_has_closeout = false
clean_has_artifact_index = false
```

The clean workspace contains Track B documentation and true-left replay runtime
outputs that mention `reconstructed_artifacts_missing`, including:

```text
outputs/replay/leftlab_v1_4_d/decision_matrix_true_left.json
outputs/replay/leftlab_v1_4_d/true_vs_reconstructed_alignment.json
```

Those files are not reconstructed_v1 artifacts. They document the missing
alignment/artifact condition and must not be treated as reconstructed artifacts.

Conclusion: clean clone still lacks usable reconstructed_v1 artifact material.

## Quarantine Read-Only Result

Quarantine result:

```text
quarantine_candidate_artifacts_found = true
quarantine_candidate_count = 38
quarantine_runtime_artifact_candidate_count = 28
artifact_candidate_count = 41
quarantine_has_candidate_history = true
quarantine_has_decision_matrix = true
quarantine_has_closeout = true
quarantine_has_artifact_index = true
```

The quarantine workspace is on a historical branch and is not clean:

```text
branch = plan-leftlab-v1-4-d-replay
tracked modifications present = true
untracked files present = true
```

Therefore quarantine files are candidates only. They are not accepted as clean
formal artifacts in this stage.

## Key Artifact Candidates

| Workspace | Relative path | Tracked in quarantine | Size bytes | SHA-256 | Contents | Formal use now |
|---|---:|---:|---:|---|---|---|
| quarantine | `data/real/reconstructed/left_candidates_history_RECONSTRUCTED.csv` | true | 150408 | `475d34a25fc10f94c560aec33dce0d6b12f1056a26904867598e162981112de6` | reconstructed candidate history, tagged `reconstructed_candidate_history_not_real_left_snapshot` | no |
| quarantine | `data/real/replay/kronos_v10_reconstructed_replay_cases.csv` | true | 250629 | `51fc9b9e37c596183bac0eaf5609708f475d9ca7f1ef0fc0997e7973b2ea3105` | reconstructed replay cases | no |
| quarantine | `outputs/kronos_v11r_reconstructed_replay_summary.json` | true | 6092 | `32f0d5bba6ac0576dbeb500f0d6b0e64b39613a79352aa7e5b82e77c118a5757` | V0.11-R reconstructed summary, direction_accuracy `0.555` | no |
| quarantine | `outputs/kronos_v12r_reconstructed_full_summary.json` | true | 14738 | `82f29625dc30bffc309d767cfb0a108cd2c897a8b82f7c0aa9f83e7e9cbd43fd` | V0.12-R full summary, direction_accuracy `0.40939597315436244` | no |
| quarantine | `outputs/kronos_v14r_reconstructed_stopline.json` | true | 5232 | `4946016d657e8097bc8f3fb54dc9a7053eccd23e0aa39b0a51843f9b79a564a3` | reconstructed stopline, candidate_history_type `reconstructed_not_true_left_snapshot` | no |
| quarantine | `outputs/kronos_v15r_reconstructed_closeout.json` | true | 2362 | `76cf307aaff01f11587af1fd15c0e80819db1fdb16e0e9a5af5f43a8504ba070` | closeout, branch_name `reconstructed_v1` | no |
| quarantine | `outputs/kronos_v15r_reconstructed_artifact_index.json` | true | 3849 | `af7a56cc8e1fad0422677226f2a28b8280c7b8bc0ad1a18676b8d8d8c137ba0c` | artifact index and closeout references | no |
| quarantine | `outputs/kronos_v15r_next_step_decision_matrix.json` | true | 1215 | `8fbdcaefac960ff43763f5f7bbcf7fc624ed7eb46ca7d9fbdd355398c5211efa` | next-step decision matrix, `PAUSED_BY_STOPLINE` | no |
| quarantine | `docs/kronos_v15r_reconstructed_closeout_report.md` | true | 2684 | `16fa332461e4ab2d8bbbd47964c90a07fdcaefa0cf752a998c99f276f4334172` | closeout report, candidate_history_type `reconstructed_not_true_left_snapshot` | no |

## Availability and Trust

Status:

```text
reconstructed_artifacts_status = CANDIDATE_FOUND_IN_QUARANTINE_REVIEW_REQUIRED
```

The clean workspace does not currently contain usable reconstructed_v1 artifacts.
The quarantine workspace contains plausible reconstructed candidate history,
decision matrix, closeout, artifact index, and metrics candidates, but the
quarantine workspace is explicitly not the development workspace and is not clean.

Trust conclusion:

```text
source_trusted_for_formal_v011_replay = false
```

The quarantine candidates may be used only to plan a controlled introduction.
They must not be copied directly into clean runtime or treated as formal replay
inputs in this stage.

## Controlled Introduction Plan

If total control approves introducing quarantine candidates in a later stage,
the next stage should:

```text
1. identify the exact reconstructed_v1 historical commit or bundle source;
2. verify branch provenance and expected closeout lineage;
3. verify SHA-256 checksums for each candidate file;
4. perform a read-only copy into ignored clean runtime staging;
5. preserve candidate_history_type = reconstructed_not_true_left_snapshot;
6. rebuild a clean artifact index from staged files;
7. run a separate replay/recheck;
8. request Mac / total-control review before changing stopline state.
```

Do not use true-left history to backfill or mutate reconstructed artifacts.
Do not relabel reconstructed artifacts as true-left artifacts.

## Remaining Gap

The clean clone still lacks formal, provenance-checked reconstructed_v1 artifact
material. The unresolved gap is not numerical computation; it is controlled
artifact recovery and provenance validation.

If the quarantine candidates are rejected or unavailable, next recovery options
are:

```text
restore from reconstructed_v1 historical branch
restore from closeout artifact index
restore from backup / bundle
regenerate reconstructed candidate history with reconstructed_not_true_left_snapshot label
```

Regeneration must never be presented as true-left history.

## formal_v011_ready Impact

This stage does not reclassify `formal_v011_ready`.

Current conclusion:

```text
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_artifacts_missing",
  "realized_outcome_fields_missing"
]
```

Even though quarantine candidates exist, the stopline cannot be cleared until a
controlled introduction and subsequent replay/recheck complete.

## Boundary Statement

This audit did not train a model, did not run torchrun, did not call GPU, did not
modify LeftLab, did not modify Protocol, did not modify quarantine, did not copy
quarantine artifacts into clean formal runtime, did not submit runtime payloads,
and did not provide trading advice.
