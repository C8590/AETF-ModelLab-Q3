# External Outcome Dry-Run And Alignment Validator V1.4-P

track = P

track_name = external market data outcome dry-run and exact alignment validator

base_commit = 516d1cdbf32d63c7ea180cd98cc6ec6bbfc20695

base_tag = modellab-v1.4-o-register-n-reviewed-insufficient-sources-final

formal_v011_ready = false

stopline_triggered = true

## Scope

This P-track branch adds a review-required external/local market-data source
access audit, a realized outcome construction dry-run, and an exact-alignment
validator. It does not release the stopline, does not enter `formal_v011`, does
not train, does not run `torchrun`, does not use GPU APIs, does not integrate
with the main project, and does not provide trading advice.

## Runtime Outputs

The scripts write only ignored runtime outputs under:

```text
runtime_external_outcome_dry_run/
```

Expected files:

```text
runtime_external_outcome_dry_run/source_access_audit.json
runtime_external_outcome_dry_run/realized_outcome_dry_run.csv
runtime_external_outcome_dry_run/provenance_manifest.json
runtime_external_outcome_dry_run/checksum_manifest.json
runtime_external_outcome_dry_run/exact_alignment_validation.json
```

These runtime outputs are review artifacts only and must not be committed.

## Source Access Status

external_market_data_access_status = FOUND_ACCESSIBLE_REVIEW_REQUIRED

The audit prioritizes the existing true-left handoff and local LeftLab cache:

```text
true_left_handoff =
  runtime_inbox/leftlab_v1_4_d_ready_handoff/true_left_candidate_history_handoff

candidate_source =
  E:/AETF-LeftLab/output/left_side/paper/left_side_paper_candidates.csv

local_market_data_cache =
  E:/AETF-LeftLab/data/cache/<symbol>.csv
```

The local cache exposes `close`, not a reviewed `adjusted_close` field. When it
is used, the dry-run must mark:

```text
price_adjustment_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

## Candidate Binding

The true-left candidate handoff has `candidate_id` and `artifact_ref`. The
source candidate CSV provides `symbol` and `signal_date`. The P scripts bind
candidate rows by the explicit `artifact_ref#row=N` reference and record the
source path and checksum.

candidate_binding_status = CANDIDATE_ID_SYMBOL_SIGNAL_DATE_BOUND_REVIEW_REQUIRED

No missing symbol, date, price, return, direction, or candidate mapping may be
filled by guesswork.

## Dry-Run Rules

horizon_status = DRY_RUN_ASSUMED_NOT_FORMAL

dry_run_horizons = 5D, 10D, 20D trading days

Calculation rule:

```text
entry_price = signal_date or first later valid trading row
exit_price = N trading rows after entry within the same symbol price file
realized_return = exit_price / entry_price - 1
realized_direction = up if > 0, down if < 0, flat if == 0
```

Missing price rule:

```text
do not impute
do not forward fill
do not guess realized_return
do not guess realized_direction
```

realized_outcome_dry_run_status = PARTIAL_REVIEW_REQUIRED

outcome_provenance_status = GENERATED_REVIEW_REQUIRED

## Exact Alignment Validator

The validator checks:

```text
candidate_id exact overlap
true_left_candidate_id overlap
symbol + signal_date vs symbol + as_of_date overlap
ticker + asof_date overlap
manifest / provenance / checksum mapping
duplicate keys
one-to-many / many-to-one mapping
rank-only mapping misuse
```

Rules:

```text
candidate_rank = weak key only
rank-only overlap cannot pass exact alignment
symbol/date overlap = 0 means exact alignment is not available
```

exact_alignment_validation_status = SYMBOL_DATE_OVERLAP_ZERO

## Current Stopline Position

The current remaining stopline reasons remain:

```text
realized_outcome_fields_provenance_horizon_binding_insufficient
stronger_exact_alignment_input_not_available
```

Even if a dry-run computes some outcomes, it is only:

```text
COMPLETED_REVIEW_REQUIRED
```

It must not be treated as a formal reviewed outcome and must not set:

```text
formal_v011_ready = true
```

## Runtime Result Summary

This section is updated after running the scripts.

```text
external_market_data_access_status = FOUND_ACCESSIBLE_REVIEW_REQUIRED
realized_outcome_dry_run_status = PARTIAL_REVIEW_REQUIRED
outcome_provenance_status = GENERATED_REVIEW_REQUIRED
exact_alignment_validation_status = SYMBOL_DATE_OVERLAP_ZERO
candidate_binding_status = CANDIDATE_ID_SYMBOL_SIGNAL_DATE_BOUND_REVIEW_REQUIRED
symbol_date_overlap_count = 0
candidate_id_overlap_count = 0
formal_v011_ready = false
stopline_triggered = true
runtime_tracked_check = empty
```

Runtime observations:

```text
true_left_candidate_count = 20
true_left_binding_count = 20
candidate_source_checksum_matches_manifest = true
local_price_symbol_accessible_count = 20
dry_run_output_row_count = 60
computed_outcome_count = 0
candidate_rank_overlap_count = 5
alignment_key_strength = weak
rank_only_mapping_rejected = true
```

Conclusion:

The scripts found a traceable local market-data cache for all 20 true-left
candidates and generated source/provenance/checksum manifests. The price files
contain `close` rather than reviewed `adjusted_close`, so every use is marked
`UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED`.

No realized return or realized direction was computed because the candidate
`signal_date` is 2026-06-05 and the local price cache has only one trading row
on or after that date for each symbol. The 5D, 10D, and 20D horizons are
therefore not mature in the available data. The dry-run remains partial and
review-required.

Exact alignment is not available. The validator found zero candidate-id
overlap, zero true-left-candidate-id overlap, and zero symbol/date overlap
between true-left `symbol + signal_date` and reconstructed `symbol +
as_of_date`. `candidate_rank` overlap exists only as a weak key and is rejected
as an exact mapping.
