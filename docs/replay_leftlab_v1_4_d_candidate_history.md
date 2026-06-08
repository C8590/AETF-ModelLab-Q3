# Replay LeftLab V1.4-D Candidate History

Date: 2026-06-08

## Scope

This document records the clean-clone ModelLab replay of the LeftLab V1.4-D READY handoff.

Input handoff:

```text
runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff
```

Runtime replay outputs:

```text
outputs/replay/leftlab_v1_4_d/replay_summary.json
outputs/replay/leftlab_v1_4_d/decision_matrix_true_left.json
outputs/replay/leftlab_v1_4_d/true_vs_reconstructed_alignment.json
outputs/replay/leftlab_v1_4_d/formal_v011_recheck.json
```

The runtime input and output directories are ignored and are not intended for Git commits.

## Command

```powershell
python scripts/replay_leftlab_candidate_history.py --input runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff --output outputs/replay/leftlab_v1_4_d
```

## Handoff Validation

```text
handoff_status = READY
candidate_count = 20
candidate_history.jsonl rows = 20
not_reconstructed = true
not_trading_advice = true
ready_for_modellab_replay = true
ready_for_formal_v011_recheck = true
```

`ready_for_formal_v011_recheck=true` means the handoff is eligible for replay-based recheck. It does not mean `formal_v011_ready` has already passed.

## Refs Coverage

```text
feature_snapshot_refs = 20/20
similar_case_refs = 20/20
frontend_explanation_snapshot = 20/20
label_snapshot_refs = 20/20
probability_bucket_snapshot = 20/20
```

All handoff refs matched the 20 replay candidates.

## Replay Result

```text
replay_completed = true
decision_distribution = {"unknown": 20}
label_status_distribution = {"pending": 20}
probability risk_level coverage = 20/20
probability bucket_key coverage = 20/20
```

The replay table was generated from the true-left candidate history and the handoff ref snapshots. The script did not reconstruct candidates and did not modify the handoff payload.

## Decision Matrix

The decision matrix was recomputed for the true-left candidate history.

```text
candidate_count = 20
decision_counts = {"unknown": 20}
label_status_counts = {"pending": 20}
risk_bucket_counts = {"样本不足": 9, "风险偏高": 11}
available_outcome_fields = ["label", "label_status"]
missing_outcome_fields = [
  "realized_direction",
  "future_return",
  "direction_accuracy",
  "majority_direction_accuracy",
  "formal_v011_outcome"
]
```

## True-Left vs Reconstructed

Clean clone reconstructed_v1 artifacts were not found.

```text
reconstructed_artifacts_found = false
alignment_status = reconstructed_artifacts_missing
true-left vs reconstructed alignment complete = false
```

No reconstructed_v1 values were fabricated. Difference alignment cannot be completed until the reconstructed artifacts or an approved substitute baseline are provided.

## formal_v011_ready Recheck

The replay produced a conservative NOT_READY decision.

```text
formal_v011_ready = false
decision = NOT_READY
stopline_triggered = true
```

Reasons:

```text
reconstructed_alignment_incomplete
majority_baseline_unavailable
realized_outcome_fields_missing
```

This means the LeftLab handoff is replayable, but this clean ModelLab replay does not have enough evidence to mark `formal_v011_ready=true`.

## Boundary Statement

This stage did not:

```text
train models
run torchrun
call GPU
start formal_v011
modify LeftLab
modify Protocol
submit runtime_inbox payload
submit READY zip
generate trading advice
auto-integrate replay results into the main project
```

The replay result is an audit and recheck artifact only. It is not a trading recommendation and is not an automatic production gate.
