# Majority Baseline for LeftLab V1.4-D Replay

## Stage Goal

Track B remediates the `majority_baseline_unavailable` stopline reason for the
LeftLab V1.4-D true candidate history replay. The goal is to define and build a
reproducible majority baseline input for later `formal_v011_ready` recheck,
without training a model, calling GPU, modifying LeftLab, modifying Protocol, or
treating the result as trading advice.

This document does not declare `formal_v011_ready=true`.

## Input Sources

The baseline uses the clean ModelLab runtime artifacts already unpacked under
ignored runtime paths:

```text
runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff/
outputs/replay/leftlab_v1_4_d/
```

Required replay/runtime files:

```text
runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff/candidate_history.jsonl
outputs/replay/leftlab_v1_4_d/replay_summary.json
outputs/replay/leftlab_v1_4_d/decision_matrix_true_left.json
outputs/replay/leftlab_v1_4_d/formal_v011_recheck.json
```

If these runtime artifacts are absent, they must be restored from the approved
runtime exchange ZIP into ignored runtime directories. Runtime payloads, READY
ZIPs, replay outputs, and baseline outputs must not be committed.

## Baseline Definitions

The majority baseline is a descriptive baseline over the replayed candidate
history. It is not a learned model, not a realized outcome analysis, and not a
trading recommendation.

The script `scripts/build_majority_baseline.py` writes runtime-only reports to:

```text
outputs/baseline/leftlab_v1_4_d/
```

Generated runtime reports:

```text
majority_baseline_report.json
majority_baseline_report.csv
majority_baseline_summary.md
```

## Decision Majority Baseline

Definition: count the `decision` field for the 20 replayed candidates and select
the highest-frequency value.

Observed distribution:

```text
unknown = 20
```

Result:

```text
majority_decision = unknown
majority_decision_count = 20
majority_decision_rate = 1.0
```

This confirms that the replayed candidate history has no explicit kept,
rejected, promoted, or demoted decision signal.

## Label Status Majority Baseline

Definition: count the `label_status` field and select the highest-frequency
value.

Observed distribution:

```text
pending = 20
```

Result:

```text
majority_label_status = pending
majority_label_status_count = 20
majority_label_status_rate = 1.0
```

`pending` is not a realized outcome and must not be used as a proxy for future
return, direction accuracy, or model win rate.

## Risk Bucket Majority Baseline

Definition: count `risk_bucket` when present, otherwise `risk_level`, and select
the highest-frequency value.

Observed distribution:

```text
样本不足 = 9
风险偏高 = 11
```

Result:

```text
majority_risk_bucket = 风险偏高
majority_risk_bucket_count = 11
majority_risk_bucket_rate = 0.55
```

Risk bucket / risk level is a descriptive replay field. It is not a realized
return direction, not a target label, and not evidence that a directional model
is ready.

## Neutral Baseline

The neutral baseline is:

```text
neutral_no_edge_baseline = no_directional_edge
```

It exists to make the no-edge condition explicit. With all decisions unknown,
all labels pending, and realized outcome fields missing, the safe baseline is
neutral rather than directional.

## Why Outcome-Based Baseline Is Unavailable

The replay decision matrix identifies realized outcome fields as missing:

```text
realized_direction
future_return
direction_accuracy
majority_direction_accuracy
formal_v011_outcome
```

Because those fields are unavailable, the baseline cannot compute realized
direction accuracy, realized return, future-return hit rate, or any model win
rate.

## Why This Does Not Support formal_v011_ready=true

The baseline can now be computed reproducibly, so the previous
`majority_baseline_unavailable` stopline reason is remediated for recheck input
purposes.

However:

```text
majority_baseline_available = partial
directional_baseline_available = false
outcome_based_baseline_available = false
formal_v011_ready_support = false
formal_v011_ready = false
stopline_triggered = true
```

The result does not support `formal_v011_ready=true` because it is not
directional and has no realized outcome basis.

## Relation to Stopline Reasons

Remediated for recheck input:

```text
majority_baseline_unavailable
```

Remaining blockers:

```text
reconstructed_artifacts_missing
realized_outcome_fields_missing
```

The baseline report should therefore be treated as a Track B remediation
artifact, not as formal readiness approval.

## Current Repair Result

Track B adds:

```text
docs/majority_baseline_leftlab_v1_4_d.md
scripts/build_majority_baseline.py
.gitignore
```

The script is read-only with respect to handoff/replay payloads and writes only
ignored runtime baseline outputs. It does not train, does not use torchrun, and
does not call GPU.

## Boundary Statement

This baseline is not trading advice. It does not modify LeftLab, Protocol, or
runtime payloads. It must not be auto-integrated into the main project or used
to declare `formal_v011_ready=true`.
