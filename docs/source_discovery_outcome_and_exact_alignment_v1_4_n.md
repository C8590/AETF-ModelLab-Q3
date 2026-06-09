# Source Discovery: Realized Outcome Fields and Exact Alignment Input V1.4-N

track = N

track_name = realized outcome fields and exact alignment input source discovery

base_commit = 27ce495eff8dedd6c18f6618ed3ca1305f461150

base_tag = modellab-v1.4-m-reconstructed-chain-stopline-closeout-final

formal_v011_ready = false

stopline_triggered = true

closeout_status = RECONSTRUCTED_CHAIN_CLOSED_AT_WEAK_KEY_AMBIGUITY_STOPLINE

source_discovery_status = CANDIDATE_SOURCES_FOUND_REVIEW_REQUIRED

realized_outcome_fields_status = CANDIDATE_FOUND_BUT_PROVENANCE_INSUFFICIENT

exact_alignment_input_status = CANDIDATE_FOUND_BUT_WEAK_OR_INSUFFICIENT

## Scope

This N-track audit only performs source discovery / feasibility review for:

1. realized outcome fields
2. stronger exact alignment input

This branch does not start `formal_v011`, does not train, does not run
`torchrun`, does not use GPU, and does not connect any source into the main
project runtime.

Allowed read scopes used:

- formal workspace: `E:\AETF-ModelLab-Q3`
- quarantine workspace: `E:\AETF-ModelLab-Q3-quarantine` as read-only

Quarantine handling:

- read-only inspection only
- no quarantine file modification
- no quarantine artifact copied into formal runtime
- no quarantine file moved or deleted

## Audit Script

Added script:

```text
scripts/audit_source_discovery_outcome_and_exact_alignment.py
```

The script is read-only. It scans filenames and text/structured contents
(`.csv`, `.json`, `.jsonl`, `.md`, `.py`, `.txt`, `.yaml`, `.yml`) for suspected
outcome fields and exact-key fields. It prints an audit summary to stdout only.
It does not write runtime outputs.

Verification command:

```text
python -m py_compile scripts/audit_source_discovery_outcome_and_exact_alignment.py
python scripts/audit_source_discovery_outcome_and_exact_alignment.py
```

Observed script summary:

```text
workspace_file_count = 94
quarantine_readonly_file_count = 414
workspace_structured_hit_count = 18
quarantine_structured_hit_count = 128
candidate_outcome_source_count = 8
candidate_exact_key_source_count = 141
true_left_label_ref_record_count = 20
true_left_label_ref_matched_count = 20
true_left_candidate_id_symbol_date_count = 20
true_left_label_status_counts = {"pending": 20}
reconstructed_symbol_date_count = 1500
symbol_date_overlap_count = 0
```

## Realized Outcome Field Discovery

Candidate-like outcome fields were found, but they are not sufficient to mark
realized outcome fields as available for formal replay.

Primary candidate sources:

```text
E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\outputs\kronos_v11r_reconstructed_replay_predictions.csv
fields = actual_direction, actual_return_last
non_placeholder_rows_sampled = 200
candidate binding fields = as_of_date, symbol

E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\outputs\kronos_v12r_reconstructed_full_predictions.csv
fields = actual_direction, actual_return_last
non_placeholder_rows_sampled = 1341
candidate binding fields = as_of_date, symbol
```

Read-only quarantine mirrors / related candidates:

```text
E:\AETF-ModelLab-Q3-quarantine\outputs\kronos_v11r_reconstructed_replay_predictions.csv
E:\AETF-ModelLab-Q3-quarantine\outputs\kronos_v12r_reconstructed_full_predictions.csv
E:\AETF-ModelLab-Q3-quarantine\outputs\kronos_v14r_extreme_errors.csv
E:\AETF-ModelLab-Q3-quarantine\outputs\kronos_v14r_reconstructed_error_diagnostics.json
```

Interpretation:

- These fields are not placeholder values in the scanned files.
- They are bound to reconstructed `as_of_date + symbol` rows.
- They appear in ignored runtime intake / quarantine reconstructed replay
  outputs, not in tracked formal main artifacts.
- They are reconstructed replay outputs, not a reviewed true-left realized
  outcome source for the handoff candidate set.
- They do not by themselves provide `candidate_id`-level outcome binding for
  the true-left 20-candidate handoff.
- The current branch does not review or certify their generation window,
  horizon, or provenance well enough to use them as formal outcome labels.

Rejected as true realized outcome sources:

```text
runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\label_snapshot_refs.json
```

Reason: the handoff label refs are candidate-bound, but all discovered label
statuses are `pending`; `pending` is not a realized outcome.

Decision:

```text
realized_outcome_fields_status = CANDIDATE_FOUND_BUT_PROVENANCE_INSUFFICIENT
```

The stopline reason `realized_outcome_fields_missing` is not fully cleared by
this source discovery.

## Stronger Exact Alignment Input Discovery

Candidate-like exact alignment inputs were found, but they are not sufficient to
establish exact true-left vs reconstructed alignment.

Primary true-left exact-key candidate:

```text
E:\AETF-ModelLab-Q3\runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\label_snapshot_refs.json
records = 20
matched = 20
fields = candidate_id, etf_code, signal_date, source_key
source_file = output/left_signal_cases.csv
label_status_counts = {"pending": 20}
```

Related handoff exact-key candidates:

```text
feature_snapshot_refs.json
probability_bucket_snapshot.json
similar_case_refs.json
candidate_history.jsonl
```

These artifacts provide stronger-than-rank candidate identity and, for several
ref files, symbol/date-like source keys (`etf_code + signal_date`) for the
true-left handoff candidates.

Reconstructed candidate source:

```text
E:\AETF-ModelLab-Q3\runtime_intake\reconstructed_v1_quarantine\data\real\reconstructed\left_candidates_history_RECONSTRUCTED.csv
rows = 1500
fields = as_of_date, symbol, candidate_rank
```

Overlap check:

```text
true_left_label_ref_symbol_date_count = 20
reconstructed_symbol_date_count = 1500
symbol_date_overlap_count = 0
```

Rejected as strong exact alignment:

```text
outputs\reconstructed_alignment_dry_run\weak_key_alignment_pairs.csv
outputs\reconstructed_alignment_dry_run\weak_key_alignment_pairs.json
```

Reason: these dry-run files are rank-based / weak-key outputs. They include
`true_left_candidate_id` as an annotation, but the pairing itself remains
rank-based and explicitly reports:

```text
exact_date_symbol_alignment = false
candidate_id_exact_alignment = false
symbol_overlap_count = 0
```

Decision:

```text
exact_alignment_input_status = CANDIDATE_FOUND_BUT_WEAK_OR_INSUFFICIENT
```

The handoff ref files are useful source candidates for a later reviewed intake
branch, but this audit did not find an already sufficient exact mapping from
true-left candidates to reconstructed candidates.

## Runtime Tracked Check

Command:

```text
git ls-files runtime_intake runtime_inbox outputs/reconstructed_artifacts outputs/reconstructed_alignment_precheck outputs/reconstructed_alignment_dry_run
```

Observed result:

```text
empty
```

Runtime directories remain untracked and are not committed by this branch.

## Status

```text
source_discovery_status = CANDIDATE_SOURCES_FOUND_REVIEW_REQUIRED
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons =
  - realized_outcome_fields_review_required_or_missing_for_true_left
  - stronger_exact_alignment_input_insufficient_for_true_left_vs_reconstructed
```

## Conclusion

This N-track audit found candidate sources, but did not find enough reviewed
source input to start `formal_v011`.

Realized outcome fields:

- reconstructed replay files contain non-placeholder `actual_return_last` and
  `actual_direction`
- those fields require provenance / horizon / generation-window review
- they are not certified as true-left candidate realized outcomes

Exact alignment:

- true-left handoff refs provide `candidate_id -> etf_code + signal_date`
  candidate-level source keys
- reconstructed candidate rows provide `symbol + as_of_date`
- overlap between these two key spaces is zero in this audit
- rank-only dry-run output remains weak and cannot be used as exact alignment

Therefore the closeout posture remains:

```text
formal_v011_ready = false
stopline_triggered = true
```

If these candidate sources are pursued, the next step must be a separate
reviewed intake branch. This branch must not directly enable `formal_v011`, run
training, run GPU, or connect the candidates into the main project.
