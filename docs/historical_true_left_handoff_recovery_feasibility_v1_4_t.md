# Historical True-Left Handoff Recovery Feasibility V1.4-T

track = T

track_name = historical true-left handoff source recovery / replay feasibility

base_commit = 86af14e5a9a069d9c60a520e3dc47d00d310dff1

base_tag = modellab-v1.4-r-historical-sample-window-expansion-audit-final

formal_v011_ready = false

stopline_triggered = true

## Scope

This audit checks whether the stopline reason
`historical_true_left_candidates_not_available` can be reduced by locating an
original historical true-left handoff or a replayable canonical source.

The audit is read-only except for this document. It does not enter intake, does
not start `formal_v011`, does not train, does not run `torchrun`, does not call
GPU APIs, does not modify quarantine, does not copy quarantine artifacts into
runtime, does not integrate with the main project, and does not provide trading
advice.

## Search Coverage

Reviewed in the formal ModelLab workspace:

```text
E:\AETF-ModelLab-Q3
```

Read-only quarantine inspection:

```text
E:\AETF-ModelLab-Q3-quarantine
```

Search terms included:

```text
handoff
true_left
candidate_history
candidate_id
generation_run_id
run_id
manifest
provenance
checksum
left_signal_cases
signal_cases
candidate_rank
signal_date
as_of_date
etf_code
ticker
symbol
runtime output
exporter
v1.3
v1.4
preflight
```

## Current True-Left Handoff

The current V1.4-D handoff exists in ignored runtime:

```text
runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff/
```

It contains:

```text
candidate_history.jsonl
manifest.json
artifact_index.json
checksums.sha256
candidate_schema.md
feature_snapshot_refs.json
label_snapshot_refs.json
similar_case_refs.json
probability_bucket_snapshot.json
frontend_explanation_snapshot.json
```

Observed current handoff state:

```text
current_handoff_candidate_count = 20
current_handoff_candidate_id_count = 20
current_handoff_date_range = 2026-06-05 to 2026-06-05
current_handoff_manifest_available = true
current_handoff_checksum_available = true
current_handoff_artifact_index_available = true
current_handoff_type = true_left_candidate_history
```

The current handoff is valid for the current 2026-06-05 candidate set, but it
does not provide historical true-left candidates earlier than 2026-06-05.

## Historical Original Handoff Search

No original historical true-left handoff was found that satisfies the minimum
conditions:

```text
historical candidate rows = not found
historical candidate_id = not found
historical symbol / ticker / etf_code = not found
historical signal_date / as_of_date = not found
historical source artifact path = not found
historical row-level provenance = not found
historical manifest or checksum = not found
left-side generation proof = not found
```

The R audit had already established that the formal true-left handoff/source
candidate set contains only 20 candidates dated 2026-06-05. This T audit found
no additional earlier original handoff in the formal workspace or read-only
quarantine inspection.

## Canonical Replay Feasibility

Quarantine contains a future-oriented aggregation configuration and script:

```text
configs/true_left_candidate_history.yaml
scripts/aggregate_true_left_candidate_snapshots.py
```

The aggregation contract expects files in:

```text
data/real/raw/candidates/snapshots/*_left_candidates.csv
```

The recorded aggregation manifest says:

```text
aggregation_status = SNAPSHOT_DIR_EMPTY
snapshot_count = 0
row_count = 0
candidate_date_count = 0
history_file_created = false
can_enter_formal_v011 = false
```

The real data manifest also recorded:

```text
candidate_history_present = false
```

The discovery report recorded:

```text
discovery_status = LEFT_CANDIDATE_HISTORY_NOT_FOUND
scanned_file_count = 2164
candidate_source_count = 2
candidate row_count = 0
candidate_date_count = 0
reviewed_sources = none
```

There is a candidate_id rule in the current V1.4-D handoff schema:

```text
candidate_id = stable sha256 prefix derived from signal_date, etf_code,
source_run_id, candidate_rank, and artifact_ref
```

However, the required historical canonical inputs are missing. Without earlier
candidate source rows, source run ids, row-level artifact refs, and snapshot
manifests, this rule cannot be used to recover historical true-left candidates.

Therefore the historical source is not replayable from canonical source in this
audit.

## left_signal_cases.csv Review

The current handoff manifest records `left_signal_cases.csv` as a feature
snapshot source for the current V1.4-D handoff. The R audit recorded:

```text
left_signal_cases.csv rows = 20086
date_range = 2025-06-05 to 2026-06-05
rows_before_2026_06_05 = 20045
rows_with_candidate_id = 0
rows_with_candidate_id_symbol_signal_date = 0
```

This means `left_signal_cases.csv` may be useful as a diagnostic dataset or as
future schema-uplift evidence, but it is not a true-left candidate handoff.

It cannot be directly used as:

```text
true-left handoff = no
formal_v011 input = no
exact alignment input = no
realized outcome input = no
```

No `candidate_id` was generated or assigned to `left_signal_cases.csv` rows in
this audit.

## Status

```text
historical_true_left_handoff_status = ONLY_DIAGNOSTIC_CASES_FOUND_NOT_HANDOFF
candidate_id_recovery_status = NOT_AVAILABLE
provenance_recovery_status = PARTIAL_REVIEW_REQUIRED
left_signal_cases_status = DIAGNOSTIC_ONLY_NOT_TRUE_LEFT_HANDOFF
```

Count summary:

```text
historical_source_candidate_count = 0
candidate_id_available_count = 0
symbol_date_available_count = 0
manifest_available_count = 0
checksum_available_count = 0
provenance_available_count = 0
replayable_candidate_count = 0
diagnostic_case_count = 20086
```

Current non-historical handoff evidence, retained only for context:

```text
current_true_left_candidate_count = 20
current_candidate_id_available_count = 20
current_symbol_signal_date_binding_count = 20
current_manifest_available_count = 1
current_checksum_available_count = 1
```

## Answered Questions

```text
1. earlier original true-left candidate handoff exists = no
2. historical left-side candidate generation runtime output exists = no reviewed handoff source found
3. replayable canonical input snapshot exists = no
4. candidate_id generation rule exists = current handoff schema only; not enough for missing history
5. generation_run_id / manifest / checksum / provenance exists = current handoff only, not historical
6. candidate_id + symbol + signal_date can be generated for historical candidates = no
7. candidates proven not outcome/reconstructed backfill = no historical candidates found to prove
8. left_signal_cases.csv can be upgraded to handoff = no
9. left_signal_cases.csv can be diagnostic dataset = yes
```

## Next Step

Because only diagnostic cases were found:

```text
next_step = LEFT_SIGNAL_CASES_DIAGNOSTIC_SCHEMA_UPLIFT_FEASIBILITY
formal_v011_ready = false
stopline_triggered = true
```

Remaining stopline reasons:

```text
- historical_true_left_candidates_not_available
- realized_outcome_horizon_not_matured_for_current_true_left
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

## Boundary Statement

This audit did not fabricate historical true-left candidates, did not add
`candidate_id` to `left_signal_cases.csv`, did not promote diagnostic cases to
true-left handoff, did not infer candidates from outcomes or reconstructed
artifacts, did not create manifest/checksum/provenance, did not submit runtime
artifacts, did not start `formal_v011`, did not train, did not run `torchrun`,
did not call GPU APIs, did not integrate with the main project, and did not
provide trading advice.
