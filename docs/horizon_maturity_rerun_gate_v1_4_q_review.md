# Horizon Maturity Rerun Gate V1.4-Q Review

track = Q

reviewed_branch = modellab-v1-4-q-horizon-maturity-rerun-gate

reviewed_commit = 83e188c9a7e6061e1d8323f606f19c6d1506a36a

base_commit = 33bf91787d69ccd5817017f4201d70f5f72afdc1

base_tag = modellab-v1.4-p1-runtime-ignore-hygiene-final

review_status = Q_REVIEWED_HORIZONS_NOT_MATURED_STOPLINE_CONTINUES

formal_v011_ready = false

stopline_triggered = true

## Review Scope

This is a review-only pass over the Q horizon maturity rerun gate branch. The
review checked the Q document, reran the already-merged P tooling on the Q
branch, and verified ignored runtime outputs. It does not merge `main`, does
not create a tag, does not enter intake, does not start `formal_v011`, does not
train, does not run `torchrun`, does not use GPU APIs, does not integrate with
the main project, and does not provide trading conclusions.

Reviewed Q branch diff:

```text
docs/horizon_maturity_rerun_gate_v1_4_q.md
```

The reviewed branch uses the P scripts already present on `main` at the P1
runtime ignore hygiene base.

## Review Status

```text
market_data_review_status = ACCESSIBLE_LOCAL_CACHE_REVIEWED
horizon_maturity_review_status = ALL_HORIZONS_NOT_MATURED
computed_outcome_review_status = NO_OUTCOME_COMPUTED_NO_FABRICATION
price_field_review_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
exact_alignment_review_status = SYMBOL_DATE_AND_CANDIDATE_ID_OVERLAP_ZERO
candidate_rank_review_status = WEAK_KEY_REJECTED
runtime_tracked_check = empty
```

## Review Commands

Branch and diff checks:

```text
git fetch --all --tags
git checkout modellab-v1-4-q-horizon-maturity-rerun-gate
git status --short
git rev-parse HEAD
git diff --name-status main...HEAD
git log --oneline main..HEAD
```

Observed:

```text
HEAD = 83e188c9a7e6061e1d8323f606f19c6d1506a36a
git status = clean
diff = A docs/horizon_maturity_rerun_gate_v1_4_q.md
main..HEAD = 83e188c docs: run horizon maturity rerun gate
```

P tool syntax checks:

```text
python -m py_compile scripts/audit_external_market_data_sources.py
python -m py_compile scripts/build_realized_outcome_dry_run.py
python -m py_compile scripts/validate_outcome_provenance_and_exact_alignment.py
```

P tool rerun:

```text
python scripts/audit_external_market_data_sources.py
python scripts/build_realized_outcome_dry_run.py
python scripts/validate_outcome_provenance_and_exact_alignment.py
```

## Market Data Review

The source audit found traceable local cache access for all 20 reviewed
candidates.

Reviewed properties:

```text
candidate_source_path = E:/AETF-LeftLab/output/left_side/paper/left_side_paper_candidates.csv
candidate_source_checksum = 429dc4742e095ea493bc612f41aecc2a99fb3e720f10aa99e301687e08947198
candidate_source_checksum_matches_manifest = true
local_market_data_cache = E:/AETF-LeftLab/data/cache/<symbol>.csv
local_price_symbol_accessible_count = 20
source_provider_marker = akshare.fund_etf_hist_sina
```

The cache is traceable by path, source marker, and checksum, but remains
review-required evidence rather than formal reviewed outcome evidence.

## Horizon Maturity Review

The rerun uses trading rows from the local price cache. It does not use
calendar-day substitution.

Reviewed runtime facts:

```text
signal_date = 2026-06-05
requested_horizons = 5D, 10D, 20D trading days
trading_rows_on_or_after_signal_date = 1 for each reviewed symbol
dry_run_output_row_count = 60
computed_outcome_count = 0
```

Runtime outcome status:

```text
HORIZON_NOT_MATURE_OR_PRICE_MISSING = 60 rows
```

No runtime row populated:

```text
exit_date
exit_price
realized_return
realized_direction
```

The zero computed outcome count is therefore the correct safe result from
immature trading-day horizons. It is not a script failure and not a reason to
fabricate future prices or directions.

## Price Field Review

Reviewed price field state:

```text
price_field_used = close
price_adjustment_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

The local cache does not provide reviewed `adjusted_close`. `close` is not
promoted to reviewed adjusted close.

## Exact Alignment Review

The exact alignment validator reported:

```text
exact_alignment_validation_status = SYMBOL_DATE_OVERLAP_ZERO
exact_alignment_available = false
candidate_id_overlap_count = 0
true_left_candidate_id_overlap_count = 0
symbol_date_overlap_count = 0
candidate_rank_overlap_count = 5
alignment_key_strength = weak
rank_only_mapping_rejected = true
```

`candidate_rank` remains a weak key only. It is explicitly rejected as exact
alignment and is not used to release the alignment stopline.

## Runtime Hygiene Review

Runtime outputs may exist locally under:

```text
runtime_external_outcome_dry_run/
```

Tracked runtime check:

```text
git ls-files runtime_external_outcome_dry_run runtime_intake runtime_inbox outputs
```

Result:

```text
empty
```

No runtime outputs are committed by this review.

## Safety Review

The review confirmed:

```text
formal_v011_ready = false
stopline_triggered = true
training_ready = not declared true
gpu_required = not declared true
main_project_integration_ready = not declared true
```

The Q result does not support intake, `formal_v011`, model training, GPU use,
main project integration, or trading conclusions.

## Remaining Stopline Reasons

```text
- realized_outcome_horizon_not_matured
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

## Review Conclusion

Q is reviewed as correct and safe. The 5D, 10D, and 20D horizons are not
matured in the available trading-row cache. `computed_outcome_count = 0` is the
proper no-fabrication result. No `exit_price`, `realized_return`, or
`realized_direction` was generated.

The reviewed price field remains `close`, not reviewed `adjusted_close`.
Candidate-id overlap and symbol/date overlap remain zero, and `candidate_rank`
is rejected as a weak key. The stopline continues.
