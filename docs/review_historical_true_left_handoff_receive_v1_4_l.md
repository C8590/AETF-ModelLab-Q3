# Historical True-Left Handoff Receive Review V1.4-L

review_branch = modellab-v1-4-l-receive-historical-true-left-handoff
receive_status = HISTORICAL_TRUE_LEFT_HANDOFF_SCHEMA_CHECK_PASSED_REVIEW_REQUIRED
formal_v011_ready = false

## Scope

This ModelLab receive review ingests the LeftLab historical true-left candidate
handoff runtime package from:

E:\aetf_runtime_exchange\left_to_model\historical_true_left_candidate_handoff_v1_4_full_export\

The package was copied into ignored runtime inbox:

runtime_inbox/historical_true_left_candidate_handoff_v1_4_full_export/

The review generated ignored runtime outputs under:

outputs/historical_true_left_handoff_receive_review/

No runtime inbox payload, extracted zip content, candidate history, manifest,
checksum manifest, provenance file, README runtime payload, or receive output is
tracked by git.

## Input Package

zip_filename =
historical_true_left_candidate_handoff_full_REVIEW_REQUIRED.zip

zip_sha256_expected =
d4662f3a2279831eaf865ff7be7e341df7b86a9a6535a55b51bf8339d8e2ab5d

zip_sha256_actual =
d4662f3a2279831eaf865ff7be7e341df7b86a9a6535a55b51bf8339d8e2ab5d

sha256_match = true

TRANSFER_RECEIPT.json was parsed successfully. It declares:

- delivery_name = historical_true_left_candidate_handoff_v1_4_full_export
- handoff_status = REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED
- source_project = AETF-LeftLab
- target_project = AETF-ModelLab-Q3
- modellab_formal_v011_ready = false
- review_required = true

## Zip Content Check

The zip contains the required root files:

- candidate_history.csv
- manifest.json
- checksum_manifest.json
- provenance.json
- README.md

zip_content_check = passed

## Manifest Validation

manifest_validation = passed

Validated fields:

- status = REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED
- dry_run = false
- export_mode = runtime_full_export
- candidate_count = 8960
- unique_signal_dates = 448
- signal_date_min = 2024-08-01
- signal_date_max = 2026-06-10
- full_pool_complete = false
- partial_pool_warning = true
- gap_policy = GAP_POLICY_WARNING_EXCLUDE_UNAVAILABLE_SYMBOL_DATES
- replay_status = REPLAYED
- original_historical_handoff_exists = false

The manifest does not declare `full_pool_complete=true`.

## 560000 Warning / Exclusion

warning_symbols includes:

- 560000 智能电车ETF浦银

excluded_symbol_dates includes:

- 560000 / 2026-06-10

The candidate history contains no row for:

- symbol = 560000
- signal_date = 2026-06-10

560000_warning_exclusion_validation = passed

## Checksum Validation

checksum_validation = passed

checksum_manifest.json includes hashes for delivered payload files:

- README.md
- candidate_history.csv
- manifest.json
- provenance.json

All listed hashes matched the corresponding zip member bytes. The checksum
manifest does not list itself, which is acceptable for this receive review
because the required handoff payload files are covered and verified.

## Provenance Validation

provenance_validation = passed

Validated provenance and cross-manifest evidence:

- replayed handoff = true
- original historical handoff = false
- used_future_outcome = false
- used_reconstructed = false
- used_modellab = false
- trained_model = false
- used_torchrun = false
- used_gpu = false
- command_contract.dry_run = false
- command_contract.export_mode = runtime_full_export
- gap_policy = GAP_POLICY_WARNING_EXCLUDE_UNAVAILABLE_SYMBOL_DATES
- full_pool_complete = false
- partial_pool_warning = true

This receive review does not use outcome data, reconstructed artifacts, or
ModelLab results as inputs.

## README Validation

README_validation = passed

README.md confirms:

- historical true-left candidate handoff runtime full export
- status = REPLAYED_HISTORICAL_TRUE_LEFT_CANDIDATE_HANDOFF_REVIEW_REQUIRED
- replay_status = REPLAYED
- dry_run = false
- candidate_count = 8960
- gap_policy = GAP_POLICY_WARNING_EXCLUDE_UNAVAILABLE_SYMBOL_DATES
- full_pool_complete = false
- partial_pool_warning = true
- ModelLab review is required before any formal_v011 decision
- no future outcome
- no ModelLab result
- no reconstructed candidates
- no training
- no torchrun/GPU/QMT

## Candidate History Validation

candidate_history_validation = passed

candidate_history_file = candidate_history.csv

Validated statistics:

- candidate_count = 8960
- unique_signal_dates = 448
- signal_date_min = 2024-08-01
- signal_date_max = 2026-06-10
- duplicate_candidate_id_count = 0
- missing_required_fields_count = 0
- data_available_until_after_signal_date_count = 0
- candidate_id_recomputable_rows = 8960
- candidate_id_recompute_mismatches = 0
- rows_560000_20260610 = 0

Required field validation covered:

- candidate_id
- symbol / etf_code / ticker identity, with symbol present
- candidate_rank
- generation_run_id
- leftlab_code_commit
- rule_version
- input_data_snapshot_ref
- as_of_boundary
- data_available_until
- source_artifact
- source_row

candidate_id was recomputed as:

leftlab:{generation_run_id}:{signal_date}:{symbol}:{candidate_rank}

All 8960 rows matched this rule.

## Basic Overlap Validation

basic_overlap_validation = passed

- symbol/date coverage statistics were computed.
- candidate_id uniqueness = true.
- duplicate candidate_id count = 0.
- missing required fields count = 0.
- 560000 exclusion is correctly marked.
- No erroneous `full_pool_complete=true` declaration was found.

## Runtime Outputs

Ignored receive-review outputs were generated:

- outputs/historical_true_left_handoff_receive_review/receive_review_result.json
- outputs/historical_true_left_handoff_receive_review/receive_review_result.csv
- outputs/historical_true_left_handoff_receive_review/receive_review_summary.md

These outputs are runtime artifacts and are not submitted.

## Verification

python -m py_compile scripts/receive_historical_true_left_handoff.py

Result: passed.

python scripts/receive_historical_true_left_handoff.py

Result: passed. It returned:

receive_status =
HISTORICAL_TRUE_LEFT_HANDOFF_SCHEMA_CHECK_PASSED_REVIEW_REQUIRED

$env:PYTHONPATH='.;src'; pytest

Result: collected 0 items. No tests were available to run; this is recorded as
"no tests to run", not as a test pass.

git ls-files runtime_inbox outputs

Result: empty for this runtime package and receive outputs.

## Next Step

Recommendation:

ModelLab may proceed to realized outcome calculation review, subject to the
existing review gates. This receive result does not authorize formal_v011, model
training, main-project integration, GPU work, torchrun, or trading advice.

## Safety Confirmations

- formal_v011_ready = false
- READY_FOR_TRAINING was not declared.
- READY_FOR_FORMAL_V011 was not declared.
- No formal_v011 stage was started.
- No model was trained.
- torchrun was not run.
- GPU was not used.
- QMT was not connected.
- No trading advice was generated.
- LeftLab was not modified.
- Protocol was not modified.
- runtime_inbox was not submitted.
- outputs runtime artifacts were not submitted.
