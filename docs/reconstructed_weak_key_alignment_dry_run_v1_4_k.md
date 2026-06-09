# Reconstructed Weak-Key Alignment Dry-Run V1.4-K

## Stage Goal

Track A5 runs a rank-based / weak-key reconstructed alignment dry-run. The goal
is to pair the LeftLab V1.4-D true-left candidate history with the selected
reconstructed candidate history using only the shared `candidate_rank` field.

This stage is only a dry-run for review. It does not start `formal_v011`, does
not run formal replay, does not train, does not run `torchrun`, does not call
GPU APIs, does not modify LeftLab or Protocol, does not generate model win-rate
claims, and does not provide trading advice.

## Input Sources

The dry-run used the formal ModelLab workspace:

```text
E:\AETF-ModelLab-Q3
```

Ignored runtime inputs:

```text
runtime_intake/reconstructed_v1_quarantine/
runtime_inbox/leftlab_v1_4_d_ready_handoff/
outputs/reconstructed_artifacts/alignment_candidate_map.json
outputs/reconstructed_alignment_precheck/alignment_precheck_report.json
```

Ignored runtime outputs:

```text
outputs/reconstructed_alignment_dry_run/weak_key_alignment_pairs.csv
outputs/reconstructed_alignment_dry_run/weak_key_alignment_pairs.json
outputs/reconstructed_alignment_dry_run/weak_key_alignment_summary.md
outputs/reconstructed_alignment_dry_run/weak_key_alignment_decision.json
```

No runtime input or output path is intended for commit.

## A4 Precheck Baseline

The A4 reconstructed alignment precheck established:

```text
common_fields = [candidate_rank]
common_field_count = 1
candidate_key_overlap_count = 5
date_overlap_count = 0
symbol_overlap_count = 0
schema_alignable = true
candidate_level_alignment_possible = true
alignment_precheck_status = RECONSTRUCTED_ALIGNMENT_PRECHECK_COMPLETED_REVIEW_REQUIRED
formal_v011_ready = false
stopline_triggered = true
```

The only shared candidate-level field is `candidate_rank`. There is no date
overlap and no symbol/code overlap.

## Why candidate_rank Only

The true-left candidate history contains `candidate_rank` and `candidate_id`,
but the reconstructed candidate history contains `candidate_rank` without a
matching true-left `candidate_id`.

The reconstructed history contains `as_of_date` and `symbol`, but the true-left
history has no shared symbol field and has no overlapping date values with the
reconstructed history.

Therefore this stage uses only:

```text
alignment_key = candidate_rank
alignment_key_strength = weak
```

## Why This Is Weak-Key Alignment

`candidate_rank` is a positional field, not a stable identity field. The same
rank can appear on multiple reconstructed dates and symbols. A rank match means
only that both records occupy the same rank number in their own source context.

It does not prove:

```text
date_symbol_alignment = false
exact_date_symbol_alignment = false
candidate_id_exact_alignment = false
```

This dry-run must not be described as date/symbol/candidate-id exact alignment.

## Dry-Run Result

The dry-run result is:

```text
alignment_mode = rank_based_weak_key
alignment_key = candidate_rank
alignment_key_strength = weak
true_left_candidate_count = 20
reconstructed_candidate_count = 1500
candidate_key_overlap_count = 5
alignment_key_values = [1, 2, 3, 4, 5]
aligned_pair_count = 1500
ambiguous_pair_count = 1500
ambiguous_rank_count = 5
ambiguous_rank_values = [1, 2, 3, 4, 5]
date_overlap_count = 0
symbol_overlap_count = 0
schema_alignable = true
candidate_level_alignment_possible = true
dry_run_status = RECONSTRUCTED_WEAK_KEY_ALIGNMENT_DRY_RUN_COMPLETED_REVIEW_REQUIRED
```

All 1500 produced pairs are ambiguous because each overlapping true-left rank
maps to multiple reconstructed rows across reconstructed dates/symbols. The
script marks `alignment_ambiguous = true` for those pairs and does not force a
unique exact match.

## Generated Runtime Artifacts

The ignored dry-run output directory contains:

```text
weak_key_alignment_pairs.csv
weak_key_alignment_pairs.json
weak_key_alignment_summary.md
weak_key_alignment_decision.json
```

The CSV/JSON pair files contain rank-based pair records with:

```text
alignment_mode = rank_based_weak_key
alignment_key = candidate_rank
alignment_key_strength = weak
alignment_ambiguous = true
date_symbol_alignment = false
exact_date_symbol_alignment = false
candidate_id_exact_alignment = false
formal_v011_ready_support = false
```

These files are runtime-only and ignored by Git.

## Review Recommendation

This branch recommends review of the weak-key dry-run output:

```text
recommend_review = true
recommend_next_stage_reviewed_alignment_analysis = true
```

The next stage, if authorized, should be reviewed alignment analysis of the
rank-based weak-key output. It must preserve the limitation that this is not
date/symbol/candidate-id exact alignment.

## Why This Is Still Not formal_v011

This stage only creates weak-key dry-run pairs. It does not provide realized
outcome fields, does not produce formal replay outputs, does not run a model,
and does not establish formal readiness.

Formal readiness remains blocked:

```text
formal_v011_ready_support = false
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_weak_key_alignment_dry_run_review_required",
  "realized_outcome_fields_missing"
]
```

## Boundary Statement

This stage did not modify quarantine, did not modify LeftLab, did not modify
Protocol, did not train a model, did not run `torchrun`, did not call GPU APIs,
did not start `formal_v011`, did not submit runtime artifacts, did not generate
model results, and did not provide trading advice.

```text
no_training = true
no_torchrun = true
no_gpu = true
not_trading_advice = true
```
