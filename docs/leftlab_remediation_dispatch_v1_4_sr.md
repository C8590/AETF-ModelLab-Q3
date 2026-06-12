# LeftLab Remediation Dispatch V1.4-SR

dispatch_status = V1_4_SR_LEFTLAB_REMEDIATION_DISPATCHED

model_lab_registered_state = V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED

formal_v011_ready = false

training_allowed = false

torchrun_allowed = false

gpu_allowed = false

main_project_integration_allowed = false

## Dispatch Purpose

ModelLab received the LeftLab true-left candidate history handoff and completed
basic intake validation:

```text
leftlab_handoff_received = true
manifest_verified = true
checksum_verified = true
candidate_count = 8960
schema_valid = true
```

Replay did not start. `formal_v011_ready` remains `false`.

LeftLab is requested to provide a revised true-left handoff package that
resolves or explicitly documents the current blockers:

```text
source_tag_missing
realized_outcome_horizon_info_missing
realized_outcome_horizon_not_matured
full_pool_not_complete
partial_pool_warning_active
```

## Required Revised Package

LeftLab should submit a revised true-left handoff package with:

```text
revised manifest
revised checksum
revised transfer receipt
export timestamp
schema version
true-left candidate history data file
source commit
source tag
realized outcome horizon information
full pool completeness evidence
warning/blocker disposition
```

The revised package must not use reconstructed, synthetic, inferred,
forward-filled, substitute ETF, substitute index, or substitute symbol history
as true-left history.

## Source Evidence Requirement

The revised manifest/provenance must record:

```text
source_commit = <exact LeftLab commit>
source_tag = <exact LeftLab tag>
export_timestamp = <UTC timestamp>
source_runtime_type = true_left_runtime_export
not_reconstructed = true
not_synthetic = true
not_inferred_history = true
```

LeftLab should explicitly state whether the export came from the real
left-side runtime/export path and identify the source branch/tag used for the
export.

## Realized Outcome Horizon Requirement

The revised package must include a realized outcome horizon section with:

```text
outcome_window_definition
label_cutoff_date
last_candidate_timestamp
outcome_maturity_date
unresolved_or_immature_outcome_count
matured_sample_count
immature_sample_count
replay_allowed = true/false
future_leakage_guard
```

LeftLab should explain why the revised data can or cannot be replayed by
ModelLab. If any horizon remains immature, the package must keep
`replay_allowed=false` or provide a separate mature subset with complete
evidence and clear exclusion rules.

Future leakage protection must explain how labels/outcomes are cut off after
candidate generation and how no future information is used in candidate
features, ranking, or candidate identity.

## Full Pool Completeness Requirement

The revised package must include full-pool evidence:

```text
expected_candidate_pool_range
actual_exported_candidate_count
missing_candidate_count
exclusion_rules
duplicate_candidate_id_count
timestamp_coverage
full_pool_complete = true/false
partial_pool = true/false
partial_pool_warning = true/false
```

If the pool is not complete, LeftLab must explicitly set `partial_pool=true`
and must not request ModelLab replay or readiness release.

Exclusion rules must identify every intentional exclusion class and show that
no missing candidate was silently dropped, filled, inferred, or replaced.

## Warning Cleanup Requirement

LeftLab should resolve or explain:

```text
partial_pool_warning_active
full_pool_not_complete
realized_outcome_horizon_not_matured
```

If the realized outcome horizon is not mature, LeftLab should wait for
maturity or provide a mature subset proof. Any mature subset must include its
own manifest, checksum, receipt, schema version, horizon definition, sample
counts, and explicit statement that it is not reconstructed/synthetic/inferred.

## New Manifest / Checksum / Receipt Requirement

The revised handoff must include:

```text
MANIFEST.json or manifest.json
CHECKSUMS.sha256 or checksum_manifest.json
TRANSFER_RECEIPT.json
candidate history data file
README.md
schema/version metadata
source commit and tag
export timestamp
```

Checksums must cover all payload files. The transfer receipt must identify the
target as ModelLab and mark whether the package is replay-ready or
review-required.

## ModelLab Gate Reminder

ModelLab will keep:

```text
replay_completed = false
decision_matrix_recomputed = false
formal_v011_ready = false
training_allowed = false
torchrun_allowed = false
gpu_allowed = false
main_project_integration_allowed = false
```

until a revised package satisfies the stopline gates.
