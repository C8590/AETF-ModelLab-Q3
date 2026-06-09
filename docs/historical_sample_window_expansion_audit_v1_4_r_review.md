# Historical Sample Window Expansion Audit V1.4-R Review

track = R

reviewed_branch = modellab-v1-4-r-historical-sample-window-expansion-audit

reviewed_commit = 50fde7a169a097ce0daa7924e809d8ab9c0f45bf

base_commit = 0f6fbaaa5bc401513583e2f30234bcddecfc5ec4

base_tag = modellab-v1.4-q-horizon-maturity-rerun-gate-final

review_status = R_REVIEWED_HISTORICAL_TRUE_LEFT_NOT_FOUND_STOPLINE_CONTINUES

formal_v011_ready = false

stopline_triggered = true

## Review Scope

This review-only pass checks whether the R audit supports moving the sample
window earlier or expanding the historical sample range as a direct stopline
release path.

The review adds no runtime input, does not enter realized outcome intake, does
not start `formal_v011`, does not train, does not run `torchrun`, does not call
GPU APIs, does not integrate with the main project, and does not provide
trading advice.

## Reviewed Evidence

The reviewed R audit identifies the formal true-left handoff and source
candidate file as a single current candidate set:

```text
true_left_candidate_history_type = true_left_candidate_history
true_left_candidate_count = 20
true_left_candidate_date_range = 2026-06-05 to 2026-06-05
```

The review confirms that no earlier true-left candidates were found with all
required candidate identity and date fields:

```text
historical_true_left_candidate_review_status = NOT_FOUND
historical_candidate_count = 0
eligible_candidate_count = 0
```

Required missing historical true-left structure:

```text
candidate_id + symbol + signal_date = not found before 2026-06-05
```

## left_signal_cases.csv Review

The R audit found a historical `left_signal_cases.csv` pool:

```text
rows = 20086
date_range = 2025-06-05 to 2026-06-05
rows_before_2026_06_05 = 20045
rows_with_candidate_id = 0
rows_with_candidate_id_symbol_signal_date = 0
```

Review status:

```text
left_signal_cases_review_status = HISTORICAL_DIAGNOSTIC_CASES_FOUND_NOT_TRUE_LEFT_HANDOFF
```

`left_signal_cases.csv` contains historical feature/label sample rows. It is
not a true-left candidate handoff, has no `candidate_id`, and cannot be directly
promoted into candidate history without creating new candidate provenance.

Therefore it cannot be used directly as:

```text
realized outcome input = no
exact alignment input = no
formal_v011 basis = no
```

It may remain a diagnostic or future schema-uplift candidate only.

## Horizon Review

The R audit reports zero eligible historical true-left candidates:

```text
historical_horizon_review_status = NO_ELIGIBLE_TRUE_LEFT_HISTORICAL_HORIZONS
mature_5d_count = 0
mature_10d_count = 0
mature_20d_count = 0
```

Although the diagnostic `left_signal_cases.csv` pool may contain rows with
mature horizons, those rows are not true-left candidates. They do not remove the
formal horizon blocker.

## Exact Alignment Review

The reconstructed side has a historical window, but the R audit found no exact
candidate-level alignment against historical true-left candidates:

```text
historical_exact_alignment_review_status = EXACT_ALIGNMENT_NOT_AVAILABLE
candidate_id_overlap_count = 0
symbol_date_overlap_count = 0
candidate_rank_overlap_status = WEAK_KEY_REJECTED
```

Reconstructed historical windows cannot automatically compensate for the
missing true-left handoff. `candidate_rank` is not accepted as an exact key.
An exact alignment path still requires a true-left historical candidate source
with `candidate_id + symbol + signal_date` and provenance mapping.

## Price Field Review

The R audit used:

```text
price_field_used = close
price_field_review_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

`close` is not reviewed `adjusted_close`, and this review does not promote it
as adjusted price evidence.

## Runtime And Safety Review

Runtime tracked check:

```text
runtime_tracked_check = empty
```

No runtime paths are approved for commit in this review:

```text
runtime_external_outcome_dry_run = not committed
runtime_intake = not committed
runtime_inbox = not committed
outputs = not committed
```

Safety state:

```text
formal_v011_ready = false
stopline_triggered = true
no_training = true
no_torchrun = true
no_gpu = true
main_project_integration = false
not_trading_advice = true
```

## Review Status

Post-review statuses:

```text
historical_true_left_candidate_review_status = NOT_FOUND
left_signal_cases_review_status = HISTORICAL_DIAGNOSTIC_CASES_FOUND_NOT_TRUE_LEFT_HANDOFF
historical_horizon_review_status = NO_ELIGIBLE_TRUE_LEFT_HISTORICAL_HORIZONS
historical_exact_alignment_review_status = EXACT_ALIGNMENT_NOT_AVAILABLE
price_field_review_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
runtime_tracked_check = empty
```

Remaining stopline reasons:

```text
- historical_true_left_candidates_not_available
- realized_outcome_horizon_not_matured_for_current_true_left
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

## Review Conclusion

R review confirms that the current formal true-left handoff/source candidate
contains only the 20 candidates dated 2026-06-05.

No true-left candidates earlier than 2026-06-05 were found with
`candidate_id + symbol + signal_date`.

`left_signal_cases.csv` contains historical samples and some horizons may be
mature, but those rows do not contain `candidate_id` and are not a true-left
candidate handoff.

Therefore `left_signal_cases.csv` can only serve as a later diagnostic or
schema-uplift candidate. It cannot directly serve as realized outcome input,
exact alignment input, or `formal_v011` evidence.

The reconstructed-side historical window cannot automatically fill the
true-left handoff gap. `formal_v011_ready` remains false, and the stopline
continues.
