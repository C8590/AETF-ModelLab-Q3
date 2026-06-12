# Protocol Registration V1.4-SR True-Left Intake Stopline

registration_status = V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED

next_state = V1_4_SR_LEFTLAB_REMEDIATION_DISPATCHED

formal_v011_ready = false

training_allowed = false

torchrun_allowed = false

gpu_allowed = false

main_project_integration_allowed = false

## Registration Scope

This document registers the V1.4-S true-left intake stopline state for
Protocol/status tracking. It records that ModelLab received and validated the
LeftLab true-left candidate history handoff at the basic intake layer, but did
not start replay because readiness preconditions remain blocked.

No replay, training, `torchrun`, GPU use, `formal_v011`, main-project
integration, trading advice, LeftLab modification, Protocol code modification,
history reconstruction, synthetic history, inferred history, price
fabrication, or forward-fill was performed.

## Registered State

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
```

Remaining blockers:

```text
source_tag_missing
realized_outcome_horizon_info_missing
realized_outcome_horizon_not_matured
full_pool_not_complete
partial_pool_warning_active
```

## Evidence

Registered stopline evidence comes from the V1.4-S stopline closeout:

```text
docs/v1_4_s_true_left_intake_replay_formal_v011_recheck_stopline.md
scripts/v1_4_s_true_left_intake_replay_recheck.py
```

Key intake facts:

```text
handoff_dir = E:\aetf_runtime_exchange\left_to_model\historical_true_left_candidate_handoff_v1_4_full_export
zip_sha256_match = true
inner_checksum_verified = true
candidate_count = 8960
duplicate_candidate_id_count = 0
missing_schema_fields = []
future_leakage_rows = 0
candidate_id_recompute_mismatches = 0
data_is_true_left_runtime_export = true
data_from_reconstructed_branch = false
source_commit = 459c8fd45145ba3dc93bb51e283520773412f92f
source_tag = null
export_timestamp = 2026-06-11T03:55:29Z
```

Replay blockers:

```text
source_tag_missing = true
realized_outcome_horizon_info_missing = true
realized_outcome_horizon_not_matured = true
full_pool_complete = false
partial_pool_warning = true
```

The latest signal date in the received handoff is `2026-06-10`. The V1.4-S
recheck sampled latest-signal candidates and found only one local price row on
or after that signal date, so the 5D, 10D, and 20D trading horizons were not
matured.

## Protocol Decision

Protocol/status registration is:

```text
V1_4_S_TRUE_LEFT_INTAKE_STOPLINE_REVIEW_REQUIRED
```

The operational next state is:

```text
V1_4_SR_LEFTLAB_REMEDIATION_DISPATCHED
```

This registration does not authorize `formal_v011`, model training, GPU work,
`torchrun`, main-project integration, replay continuation, or trading
conclusions.
