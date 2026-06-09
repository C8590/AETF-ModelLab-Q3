# Reconstructed Alignment Precheck V1.4-J

## Stage Goal

Track A4 performs a structural reconstructed alignment precheck. The goal is
to verify whether the A3 selected reconstructed candidate set can be compared
against the LeftLab V1.4-D true-left candidate history at schema and key level.

This stage does not run alignment dry-run, does not start `formal_v011`, does
not train, does not run `torchrun`, does not call GPU APIs, does not produce
model win-rate claims, and does not provide trading advice.

## Input Sources

The precheck used the formal ModelLab workspace:

```text
E:\AETF-ModelLab-Q3
```

Runtime inputs were read from ignored paths only:

```text
runtime_intake/reconstructed_v1_quarantine/
outputs/reconstructed_artifacts/alignment_candidate_map.json
runtime_inbox/leftlab_v1_4_d_ready_handoff/
```

The runtime output was written to an ignored path:

```text
outputs/reconstructed_alignment_precheck/
```

No runtime input or output path is intended for commit.

## Reconstructed Artifact Set Source

A3 selected one reconstructed alignment precheck candidate set:

```text
reconstructed_candidate_set_count = 1
reconstructed_candidate_set_id = reconstructed_v1_quarantine_primary
```

The selected set came from:

```text
outputs/reconstructed_artifacts/alignment_candidate_map.json
```

Resolved ignored runtime files:

```text
reconstructed_candidate_history_path = E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\data\real\reconstructed\left_candidates_history_RECONSTRUCTED.csv
reconstructed_decision_matrix_path = E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\outputs\kronos_v15r_next_step_decision_matrix.json
reconstructed_closeout_path = E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\outputs\kronos_v15r_reconstructed_closeout.json
reconstructed_artifact_index_path = E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\outputs\kronos_v15r_reconstructed_artifact_index.json
```

Readability result:

```text
reconstructed_candidate_history_readable = true
reconstructed_decision_matrix_readable = true
reconstructed_closeout_readable = true
reconstructed_artifact_index_readable = true
reconstructed_candidate_count = 1500
```

The reconstructed closeout identifies this history as:

```text
reconstructed_candidate_history_type = reconstructed_not_true_left_snapshot
```

## True-Left Candidate History Source

The true-left handoff input was read from:

```text
true_left_candidate_history_path = E:\AETF-ModelLab-Q3\runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\candidate_history.jsonl
true_left_manifest_path = E:\AETF-ModelLab-Q3\runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\manifest.json
true_left_artifact_index_path = E:\AETF-ModelLab-Q3\runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\artifact_index.json
```

Readability result:

```text
true_left_candidate_history_readable = true
true_left_candidate_count = 20
true_left_candidate_count_is_20 = true
true_left_candidate_history_type = true_left_candidate_history
```

## Field Alignment Check

The reconstructed candidate history fields include:

```text
as_of_date
symbol
display_name
candidate_rank
left_score
notes
```

The true-left candidate history fields include:

```text
artifact_ref
candidate_id
candidate_rank
decision
decision_reason
decision_step
frontend_explanation_ref
input_feature_snapshot_ref
label_snapshot_ref
left_project_commit
probability_bucket
round
similar_case_ref
source_snapshot_id
timestamp
```

Common fields:

```text
common_fields = [candidate_rank]
common_field_count = 1
```

Schema conclusion:

```text
schema_alignable = true
```

The schema is alignable only at a structural precheck level. The common key is
weak because `candidate_rank` is not a stable identity key across all
reconstructed rows.

## Key Overlap Check

Alignment key candidates:

```text
alignment_key_candidates = [candidate_rank]
candidate_key_overlap_count = 5
candidate_key_overlap_values = [1, 2, 3, 4, 5]
```

Candidate-level alignment conclusion:

```text
candidate_level_alignment_possible = true
```

This means a limited candidate-level dry-run key can be constructed for review.
It does not mean reconstructed artifacts are true-left history, and it does not
mean realized outcomes are available.

## Date And Symbol Overlap Check

Date-level check:

```text
date_field_reconstructed = as_of_date
date_field_true_left = timestamp
date_overlap_count = 0
```

Symbol/code-level check:

```text
symbol_field_reconstructed = symbol
symbol_field_true_left = null
symbol_overlap_count = 0
```

There is no date-level or symbol/code-level overlap in this precheck. This is
why the next step should remain a reviewed alignment dry-run, not formal replay.

## Source Separation And Risk Controls

The precheck can distinguish:

```text
true_left_candidate_history
reconstructed_not_true_left_snapshot
```

Risk controls:

```text
can_distinguish_true_left_from_reconstructed = true
risk_mistake_true_left_as_reconstructed = low
risk_mistake_reconstructed_as_realized_outcome = controlled_by_stopline
```

The true-left manifest marks true-left history, while the reconstructed closeout
marks the reconstructed history as not true-left. This prevents promoting the
reconstructed snapshot as true-left evidence.

## Precheck Status

The structural precheck status is:

```text
alignment_precheck_status = RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED
precheck_status = RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED
```

Recommendation:

```text
recommend_review = true
recommend_alignment_dry_run = true
```

The recommended next stage is an alignment dry-run review. This stage did not
start that dry-run.

## Why This Is Still Not formal_v011

This stage only checks readability, schema compatibility, and key overlap. It
does not run formal replay, does not create formal replay outputs, does not use
realized outcome fields, and does not establish model readiness.

Formal readiness remains blocked:

```text
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_alignment_precheck_review_required",
  "realized_outcome_fields_missing"
]
```

## Boundary Statement

This stage did not train a model, did not run `torchrun`, did not call GPU APIs,
did not modify quarantine, did not modify LeftLab, did not modify Protocol, did
not submit runtime artifacts, did not generate model win-rate claims, and did
not provide trading advice.

```text
no_training = true
no_torchrun = true
no_gpu = true
not_trading_advice = true
```
