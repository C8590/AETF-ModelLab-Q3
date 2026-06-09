# Horizon Maturity Rerun Gate V1.4-Q

track = Q

track_name = horizon maturity rerun gate

base_commit = 33bf91787d69ccd5817017f4201d70f5f72afdc1

base_tag = modellab-v1.4-p1-runtime-ignore-hygiene-final

formal_v011_ready = false

stopline_triggered = true

## Scope

This Q-track rerun starts from `main` after the P1 runtime ignore hygiene merge
and uses the P external outcome dry-run tooling already merged into `main`.

Allowed actions performed:

```text
read traceable local market data cache
run external market data source audit
run realized outcome dry-run
run provenance / checksum / exact alignment validator
generate ignored runtime audit outputs
register this Q status document
```

No runtime output is committed. This rerun does not enter intake, does not
start `formal_v011`, does not train, does not run `torchrun`, does not use GPU
APIs, does not integrate with the main project, and does not produce trading
conclusions.

## Commands Run

Syntax checks:

```text
python -m py_compile scripts/audit_external_market_data_sources.py
python -m py_compile scripts/build_realized_outcome_dry_run.py
python -m py_compile scripts/validate_outcome_provenance_and_exact_alignment.py
```

P tooling rerun:

```text
python scripts/audit_external_market_data_sources.py
python scripts/build_realized_outcome_dry_run.py
python scripts/validate_outcome_provenance_and_exact_alignment.py
```

## Runtime Outputs

The rerun generated ignored runtime review artifacts under:

```text
runtime_external_outcome_dry_run/
```

Observed files:

```text
runtime_external_outcome_dry_run/source_access_audit.json
runtime_external_outcome_dry_run/realized_outcome_dry_run.csv
runtime_external_outcome_dry_run/provenance_manifest.json
runtime_external_outcome_dry_run/checksum_manifest.json
runtime_external_outcome_dry_run/exact_alignment_validation.json
```

Runtime tracked check:

```text
git ls-files runtime_external_outcome_dry_run runtime_intake runtime_inbox outputs
```

Result:

```text
empty
```

## Q Status Summary

```text
market_data_access_status = ACCESSIBLE_LOCAL_CACHE_REVIEWED
horizon_maturity_status = ALL_HORIZONS_NOT_MATURED
realized_outcome_rerun_status = NO_OUTCOME_COMPUTED_HORIZON_NOT_MATURED
computed_outcome_count = 0
expected_candidate_count = 20
requested_horizons = 5D, 10D, 20D
```

Price field status:

```text
price_field_used = close
price_adjustment_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

Exact alignment status:

```text
candidate_id_overlap_count = 0
symbol_date_overlap_count = 0
candidate_rank_overlap_count = 5
candidate_rank_overlap_status = WEAK_KEY_REJECTED
exact_alignment_status = SYMBOL_DATE_OVERLAP_ZERO
```

Safety state:

```text
formal_v011_ready = false
stopline_triggered = true
```

## Source Access Result

The source audit found the true-left candidate source and local LeftLab market
data cache accessible for all 20 candidates.

Reviewed source properties:

```text
candidate_source_path = E:/AETF-LeftLab/output/left_side/paper/left_side_paper_candidates.csv
candidate_source_checksum = 429dc4742e095ea493bc612f41aecc2a99fb3e720f10aa99e301687e08947198
candidate_source_checksum_matches_manifest = true
local_market_data_cache = E:/AETF-LeftLab/data/cache/<symbol>.csv
local_price_symbol_accessible_count = 20
source_provider_marker = akshare.fund_etf_hist_sina
```

The cache remains review-required outcome evidence. The rerun did not refresh
external market data because the existing traceable local cache was accessible.

## Horizon Maturity Result

The rerun used trading rows from the local cache, not calendar-day inference.
For each reviewed candidate, the signal date was:

```text
signal_date = 2026-06-05
trading_rows_on_or_after_signal_date = 1
```

The dry-run produced 60 candidate-horizon rows:

```text
5D rows = 20
10D rows = 20
20D rows = 20
```

All 60 rows reported:

```text
outcome_status = HORIZON_NOT_MATURE_OR_PRICE_MISSING
```

No row had `exit_date`, `exit_price`, `realized_return`, or
`realized_direction` populated. Therefore:

```text
horizon_maturity_status = ALL_HORIZONS_NOT_MATURED
realized_outcome_rerun_status = NO_OUTCOME_COMPUTED_HORIZON_NOT_MATURED
computed_outcome_count = 0
```

## Price Field Result

The local cache exposes `close` and does not expose a reviewed
`adjusted_close` field. The rerun therefore records:

```text
price_field_used = close
price_adjustment_status = UNADJUSTED_CLOSE_USED_REVIEW_REQUIRED
```

`close` is not promoted to reviewed adjusted close.

## Exact Alignment Result

The exact alignment validator reported:

```text
candidate_id_overlap_count = 0
true_left_candidate_id_overlap_count = 0
symbol_date_overlap_count = 0
ticker_asof_date_overlap_count = 0
candidate_rank_overlap_count = 5
alignment_key_strength = weak
exact_alignment_available = false
rank_only_mapping_rejected = true
exact_alignment_status = SYMBOL_DATE_OVERLAP_ZERO
```

`candidate_rank` overlap is explicitly rejected as a weak key and is not used
as exact alignment.

## Remaining Stopline Reasons

```text
- realized_outcome_horizon_not_matured
- price_adjustment_review_required
- stronger_exact_alignment_input_not_available
```

## Conclusion

The Q rerun confirms that the local market data cache is accessible and
traceable, but the available trading rows after the 2026-06-05 signal date are
not sufficient for 5D, 10D, or 20D realized outcome computation. No
`exit_price`, `realized_return`, or `realized_direction` was computed or
fabricated.

The rerun still uses `close`, not reviewed `adjusted_close`, so price
adjustment review remains required. Exact alignment remains unavailable because
candidate-id overlap and symbol/date overlap are both zero; rank-only overlap
is rejected. The stopline remains active, and this state cannot support
`formal_v011`, intake, training, GPU use, main project integration, or trading
conclusions.
