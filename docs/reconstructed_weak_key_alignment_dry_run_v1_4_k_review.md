# Review: Reconstructed Weak-Key Alignment Dry-Run V1.4-K

## review_status

```text
A5_REVIEWED_WEAK_KEY_AMBIGUITY_CONFIRMED
```

## reviewed_branch

```text
modellab-v1-4-k-reconstructed-weak-key-alignment-dry-run
```

## reviewed_commit

```text
dcc6f35618e3b2f93cb209b495426e89ea89d8e3
```

## formal_v011_ready

```text
false
```

The reviewed A5 dry-run does not support `formal_v011_ready=true`.

## stopline_triggered

```text
true
```

## remaining_stopline_reasons

```text
reconstructed_weak_key_alignment_dry_run_review_required
realized_outcome_fields_missing
```

## changed_files_reviewed

The `main...HEAD` diff contains only:

```text
A docs/reconstructed_weak_key_alignment_dry_run_v1_4_k.md
A scripts/dry_run_reconstructed_weak_key_alignment.py
```

No LeftLab, Protocol, model weight, training output, READY zip, payload, or
runtime output file was part of the tracked diff.

## runtime_files_committed_check

Command:

```text
git ls-files runtime_intake runtime_inbox outputs/reconstructed_artifacts outputs/reconstructed_alignment_precheck outputs/reconstructed_alignment_dry_run
```

Result:

```text
empty
```

Conclusion: no `runtime_intake`, `runtime_inbox`, `outputs/reconstructed_artifacts`,
`outputs/reconstructed_alignment_precheck`, or `outputs/reconstructed_alignment_dry_run`
runtime files are tracked by Git.

## py_compile_result

Command:

```text
python -m py_compile scripts/dry_run_reconstructed_weak_key_alignment.py
```

Result:

```text
passed
```

## pytest_result

Command:

```text
pytest
```

Result:

```text
collected 0 items
```

Conclusion: no tests runnable. This is not recorded as test coverage passing.

## dry_run_result

The dry-run script was run with:

```text
python scripts/dry_run_reconstructed_weak_key_alignment.py
```

Result:

```text
alignment_mode = rank_based_weak_key
alignment_key = candidate_rank
alignment_key_strength = weak
true_left_candidate_count = 20
reconstructed_candidate_count = 1500
candidate_key_overlap_count = 5
aligned_pair_count = 1500
ambiguous_pair_count = 1500
date_overlap_count = 0
symbol_overlap_count = 0
exact_date_symbol_alignment = false
candidate_id_exact_alignment = false
dry_run_status = RECONSTRUCTED_WEAK_KEY_ALIGNMENT_DRY_RUN_COMPLETED_REVIEW_REQUIRED
formal_v011_ready_support = false
formal_v011_ready = false
stopline_triggered = true
remaining_stopline_reasons = [
  "reconstructed_weak_key_alignment_dry_run_review_required",
  "realized_outcome_fields_missing"
]
```

## weak_key_interpretation

`candidate_rank` is only a weak key. It is a positional field, not a stable
identity key.

`aligned_pair_count = 1500` must not be interpreted as 1500 valid exact pairs.
All generated pairs are weak-key dry-run pairs.

`ambiguous_pair_count = 1500` confirms every generated weak-key pair is
ambiguous. The ambiguity is expected because ranks 1 through 5 overlap, while
the reconstructed history contains many rows for each rank across dates and
symbols.

`date_overlap_count = 0` and `symbol_overlap_count = 0`; therefore there is no
date/symbol/candidate-id exact alignment. The reviewed result cannot support
formal replay, model training, outcome-based evaluation, main project
integration, or trading conclusions.

## forbidden_actions_check

Review found:

```text
formal_v011 started = no
model training = no
torchrun = no
GPU / cuda call = no
main project integration = no
trading advice = no
quarantine modified = no
quarantine artifact copied in this review = no
runtime_intake committed = no
runtime_inbox committed = no
outputs runtime committed = no
reconstructed artifacts fabricated = no
candidate_rank treated as exact alignment = no
1500 ambiguous pairs treated as valid exact samples = no
formal_v011_ready=true declared = no
outcome-based evaluation declared = no
main merge performed = no
final tag created = no
```

Keyword scanning over `docs` and `scripts` found only explanatory negative
statements and read-only runtime path constants for the A5 scope. No actual
training, `torchrun`, GPU, optimizer, backward, or fitting execution path was
found in the A5 script.

## final_recommendation

A5 已完成 review-only 复审。

A5 weak-key ambiguity 已确认。

`candidate_rank` 仅为 weak key。

1500 aligned pairs 全部 ambiguous。

date/symbol/candidate-id 精确对齐不存在。

`formal_v011_ready` 仍为 false。

`stopline_triggered` 仍为 true。

该链路仍不能支持训练、GPU、`formal_v011`、主项目接入或交易结论。

复审通过后，下一阶段也只能进入 reviewed weak-key ambiguity analysis；
不得直接进入 `formal_v011`、model training、outcome-based evaluation 或 main
project integration。
