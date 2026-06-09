# Historical Sample Window Expansion Audit V1.4-R

track = R

track_name = historical sample window expansion feasibility audit

base_commit = 0f6fbaaa5bc401513583e2f30234bcddecfc5ec4

base_tag = modellab-v1.4-q-horizon-maturity-rerun-gate-final

formal_v011_ready = false

stopline_triggered = true

## Scope

This R-track audit checks whether moving the sample window earlier can reduce
the Q stopline. It only reads existing ModelLab runtime inputs, LeftLab output
artifacts, local market data cache files, and already-intaken reconstructed
review artifacts. It does not create candidates, backfill candidate provenance,
enter intake, start `formal_v011`, train, run `torchrun`, use GPU APIs,
integrate with the main project, or produce trading conclusions.

Current stopline reasons:

```text
- realized_outcome_horizon_not_matured
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

## Status Summary

```text
historical_true_left_candidate_status = NOT_FOUND
historical_market_data_coverage_status = INSUFFICIENT
historical_horizon_maturity_status = NO_MATURE_HORIZONS_FOUND
historical_exact_alignment_status = EXACT_ALIGNMENT_NOT_AVAILABLE
```

Required counts:

```text
historical_candidate_count = 0
eligible_candidate_count = 0
mature_5d_count = 0
mature_10d_count = 0
mature_20d_count = 0
price_field_used = close
candidate_id_overlap_count = 0
symbol_date_overlap_count = 0
rank_only_overlap_count = 0
```

Safety state:

```text
formal_v011_ready = false
stopline_triggered = true
historical_sample_expansion_status = NOT_AVAILABLE
```

## Sources Reviewed

True-left handoff:

```text
path = runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff/
candidate_history = candidate_history.jsonl
manifest = manifest.json
candidate_history_type = true_left_candidate_history
candidate_count = 20
```

True-left source candidate file:

```text
path = E:/AETF-LeftLab/output/left_side/paper/left_side_paper_candidates.csv
rows = 20
date_range = 2026-06-05 to 2026-06-05
sha256 = 429dc4742e095ea493bc612f41aecc2a99fb3e720f10aa99e301687e08947198
```

Historical feature/label sample pool:

```text
path = E:/AETF-LeftLab/output/left_signal_cases.csv
rows = 20086
date_range = 2025-06-05 to 2026-06-05
rows_before_2026_06_05 = 20045
rows_with_candidate_id = 0
rows_with_candidate_id_symbol_signal_date = 0
sha256 = f4be4f1cc87fe728f5276d28328fcd105d25148627b3ab8a3c16f5445fe479ce
```

Reconstructed review artifact:

```text
path = runtime_intake/reconstructed_v1_quarantine/data/real/reconstructed/left_candidates_history_RECONSTRUCTED.csv
rows = 1500
date_range = 2025-03-10 to 2026-06-03
```

## Historical True-Left Candidate Finding

The reviewed true-left candidate handoff and its source candidate CSV contain
only 20 candidates with:

```text
signal_date = 2026-06-05
candidate_id present = true
symbol present = true
artifact_ref present = true
```

No true-left candidates earlier than 2026-06-05 were found in the reviewed
candidate handoff or source candidate file:

```text
historical_true_left_candidate_status = NOT_FOUND
historical_candidate_count = 0
eligible_candidate_count = 0
```

The historical `left_signal_cases.csv` file contains many earlier feature and
label rows, but it is not a true-left candidate handoff and it has no
`candidate_id`. It cannot be promoted to true-left candidate history without
creating new candidate provenance, which this audit does not do.

## Market Data And Horizon Coverage

For the formal historical true-left candidate set:

```text
historical_candidate_count = 0
eligible_candidate_count = 0
mature_5d_count = 0
mature_10d_count = 0
mature_20d_count = 0
historical_market_data_coverage_status = INSUFFICIENT
historical_horizon_maturity_status = NO_MATURE_HORIZONS_FOUND
```

Diagnostic-only check on non-candidate historical sample rows:

```text
historical_non_candidate_rows_before_2026_06_05 = 20045
historical_non_candidate_eligible_by_local_cache = 20045
historical_non_candidate_mature_5d_count = 19785
historical_non_candidate_mature_10d_count = 19450
historical_non_candidate_mature_20d_count = 18687
```

This diagnostic shows that moving earlier in time would likely reduce the
outcome maturity blocker if equivalent true-left candidate provenance existed.
However, these rows are feature/label samples, not true-left candidates, so the
formal R candidate/horizon counts remain zero.

The local market data cache uses:

```text
price_field_used = close
price_adjustment_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

No reviewed `adjusted_close` field was identified for this audit, and `close`
is not promoted to reviewed adjusted close.

## Reconstructed Window And Alignment

The reconstructed side has a historical window:

```text
reconstructed_candidate_count = 1500
reconstructed_date_range = 2025-03-10 to 2026-06-03
reconstructed_symbol_date_count = 1500
```

Diagnostic-only overlap with the non-candidate historical sample pool:

```text
historical_non_candidate_symbol_date_count = 20045
historical_non_candidate_symbol_date_overlap_with_reconstructed = 230
```

This overlap is not exact alignment because the historical sample pool is not a
true-left candidate source and has no candidate_id.

Historical true-left candidate alignment counts:

```text
candidate_id_overlap_count = 0
true_left_candidate_id_field_overlap_count = 0
symbol_date_overlap_count = 0
rank_only_overlap_count = 0
historical_exact_alignment_status = EXACT_ALIGNMENT_NOT_AVAILABLE
```

Current 2026-06-05 true-left reference check remains:

```text
current_candidate_id_overlap_count = 0
current_symbol_date_overlap_count = 0
current_rank_only_overlap_count = 5
candidate_rank_overlap_status = WEAK_KEY_REJECTED
```

Expanding the sample window cannot be treated as exact alignment unless a
historical true-left candidate source with `candidate_id + symbol +
signal_date` and manifest/provenance mapping is provided. Rank-only overlap
remains a weak key and is rejected.

## Answers To Audit Questions

```text
1. earlier true-left candidates exist = no
2. candidate_id + symbol + signal_date for earlier candidates = no
3. market cache covers earlier non-candidate sample horizons = yes, diagnostic only
4. price field = close
5. mature candidate/horizon count for historical true-left candidates = 0 / 0 / 0
6. reconstructed side has overlapping historical window = yes, but not exact candidate provenance
7. candidate_id overlap greater than zero = no
8. symbol/date overlap greater than zero for historical true-left candidates = no
9. manifest/provenance/handoff mapping for historical true-left candidates = no
10. expanded sample still only weak/no exact alignment = yes
```

## Remaining Stopline Reasons

```text
- realized_outcome_horizon_not_matured
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

The realized outcome blocker may be reducible only if a real historical
true-left candidate handoff is supplied. The current reviewed artifacts do not
provide one. The price adjustment blocker and stronger exact alignment blocker
remain.

## Conclusion

Moving the sample window earlier does not currently solve the stopline because
no earlier true-left candidates with candidate provenance were found. The
available historical rows are feature/label samples without `candidate_id`, not
candidate history. They show that earlier market data could support many
mature 5D/10D/20D horizons in a diagnostic sense, but they cannot be used as
formal candidate outcomes or exact alignment inputs.

The reconstructed side has an overlapping historical window, but without
historical true-left candidate ids or symbol/date candidate provenance, exact
alignment remains unavailable. `formal_v011_ready` remains false and
`stopline_triggered` remains true.
