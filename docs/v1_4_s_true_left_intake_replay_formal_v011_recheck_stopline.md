# V1.4-S True-Left Intake Replay formal_v011 Recheck Stopline

task = V1.4-S True-Left Intake, Replay & formal_v011 Recheck

next_state = V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED

formal_v011_ready = false

training_allowed = false

torchrun_allowed = false

gpu_allowed = false

main_project_integration_allowed = false

## Scope

This ModelLab pass receives and validates the LeftLab true-left candidate
history handoff package, then applies the V1.4-S replay and readiness gate
preconditions.

Input package:

```text
E:\aetf_runtime_exchange\left_to_model\historical_true_left_candidate_handoff_v1_4_full_export
```

Package file:

```text
historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.zip
```

This pass is intake/review only. It does not train, run `torchrun`, use GPU,
start `formal_v011`, connect the main project, modify LeftLab, modify Protocol,
infer missing history, forward-fill, fabricate prices, or generate trading
advice.

## Intake Record

```text
leftlab_handoff_received = true
transfer_receipt_exists = true
manifest_verified = true
checksum_verified = true
candidate_count = 8960
schema_valid = true
data_is_true_left_runtime_export = true
data_from_reconstructed_branch = false
```

The package contains:

```text
candidate_history.csv
manifest.json
checksum_manifest.json
provenance.json
README.md
```

`TRANSFER_RECEIPT.json` is present outside the zip.

Checksum review:

```text
zip_sha256_expected = d4662f3a2279831eaf865ff7be7e341df7b86a9a6535a55b51bf8339d8e2ab5d
zip_sha256_actual = d4662f3a2279831eaf865ff7be7e341df7b86a9a6535a55b51bf8339d8e2ab5d
zip_sha256_match = true
inner_checksum_verified = true
```

Source evidence:

```text
source_commit = 459c8fd45145ba3dc93bb51e283520773412f92f
source_tag = null
export_timestamp = 2026-06-11T03:55:29Z
manifest_status = REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED
replay_status_in_handoff = REPLAYED
export_mode = runtime_full_export
dry_run = false
not_reconstructed = true
```

## Schema And Leakage Review

Candidate history validation:

```text
candidate_count = 8960
unique_signal_dates = 448
signal_date_min = 2024-08-01
signal_date_max = 2026-06-10
duplicate_candidate_id_count = 0
missing_schema_fields = []
missing_required_rows = 0
future_leakage_rows = 0
timestamp_anomaly_rows = 0
candidate_id_recompute_mismatches = 0
schema_valid = true
```

The required replay fields are present:

```text
candidate_id
symbol
signal_date
candidate_rank
generation_run_id
leftlab_code_commit
rule_version
input_data_snapshot_ref
as_of_boundary
data_available_until
source_artifact
source_row
```

No missing fields were silently dropped, filled, or inferred.

## Stopline Evidence

Replay and readiness gate recheck stop before replay because stopline
preconditions are not satisfied.

Remaining blockers:

```text
source_tag_missing
realized_outcome_horizon_info_missing
realized_outcome_horizon_not_matured
full_pool_not_complete
partial_pool_warning_active
```

The handoff manifest/provenance includes `source_commit` and export timestamp,
but does not provide a source tag field.

The handoff manifest/provenance does not include explicit realized outcome
horizon metadata. For evidence only, the recheck script used the existing
ModelLab review horizons of 5, 10, and 20 trading days; it did not use this
default to pass any gate.

Latest signal date:

```text
latest_signal_date = 2026-06-10
```

For the 20 sampled latest-signal candidates, local price cache rows on or after
`2026-06-10` equal `1`, so 5D, 10D, and 20D trading horizons are not matured.

Pool completeness remains blocked:

```text
full_pool_complete = false
partial_pool_warning = true
gap_policy = GAP_POLICY_WARNING_EXCLUDE_UNAVAILABLE_SYMBOL_DATES
```

## Replay And Decision Matrix

Because a stopline was triggered, ModelLab did not continue into replay.

```text
realized_outcome_horizon_matured = false
replay_completed = false
decision_matrix_recomputed = false
formal_v011_ready = false
main_project_integration_allowed = false
remaining_blocker_count = 5
```

No true-left vs reconstructed replay alignment was recomputed after the
stopline. No candidate rows were dropped or filled to force replay.

## Required Closeout Fields

```text
leftlab_handoff_received = true
manifest_verified = true
checksum_verified = true
candidate_count = 8960
schema_valid = true
realized_outcome_horizon_matured = false
replay_completed = false
decision_matrix_recomputed = false
formal_v011_ready = false
training_allowed = false
torchrun_allowed = false
gpu_allowed = false
main_project_integration_allowed = false
remaining_blocker_count = 5
remaining_blockers = source_tag_missing, realized_outcome_horizon_info_missing, realized_outcome_horizon_not_matured, full_pool_not_complete, partial_pool_warning_active
next_state = V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED
```

## Runtime Outputs

Ignored runtime evidence was generated under:

```text
outputs/v1_4_s_true_left_intake_replay_recheck/
```

Runtime outputs and runtime inbox contents are not submitted.

## Safety Confirmation

```text
trained_model = false
torchrun = false
gpu = false
formal_v011_started = false
main_project_integration = false
trading_advice_generated = false
leftlab_modified = false
protocol_modified = false
reconstructed_or_synthetic_history_used = false
missing_fields_silently_dropped_filled_or_inferred = false
forward_fill_used = false
substitute_etf_index_symbol_used = false
```
