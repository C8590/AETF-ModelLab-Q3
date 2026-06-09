# A5 Reviewed-But-Unmerged Status Register V1.4-L

## Registration Status

```text
status_register = A5_REVIEWED_BUT_UNMERGED
track = A5
track_name = reconstructed weak-key alignment dry-run
branch = modellab-v1-4-k-reconstructed-weak-key-alignment-dry-run
development_commit = dcc6f35618e3b2f93cb209b495426e89ea89d8e3
review_commit = 5a24b48a7c5e9632370a5907feca571f396cc4d1
closeout_commit = d94c4d335beec47910dde9120d27969401b87742
post_review_status = A5_POST_REVIEW_CLOSED_WITH_WEAK_KEY_AMBIGUITY
main_merge_status = A5_NOT_MERGED
final_tag_status = A5_FINAL_TAG_NOT_CREATED
```

This document registers A5 state only. It does not merge A5, does not
cherry-pick A5 commits, and does not create an A5 final tag.

## Mainline Context

```text
main_latest_known_commit = 6d1b17aeeaa0d017b1796d97fbefaabfd4f3248d
main_latest_known_tag = modellab-v1.4-j-reconstructed-alignment-precheck-final
formal_v011_ready = false
stopline_triggered = true
```

## A5 Technical Conclusion

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
candidate_id_exact_alignment = false
exact_date_symbol_alignment = false
formal_v011_ready = false
stopline_triggered = true
```

`candidate_rank` is only a weak key. It is not a stable identity key and must
not be treated as an exact candidate identifier.

The 1500 aligned pairs are all ambiguous. `aligned_pair_count = 1500` must not
be interpreted as 1500 valid exact pairs or as 1500 valid outcome samples.

Because `date_overlap_count = 0` and `symbol_overlap_count = 0`, date/symbol/
candidate-id exact alignment does not exist.

## Stopline Reasons

```text
remaining_stopline_reasons =
  - reconstructed_weak_key_ambiguity_confirmed
  - realized_outcome_fields_missing
```

A5 review and post-review closeout are complete, but the review confirmed
weak-key ambiguity. The reconstructed chain therefore remains stopped.

## Boundary Statement

A5 reviewed-but-unmerged status cannot support formal readiness, model learning
workloads, accelerator execution, main project integration, trading
conclusions, or realized-outcome evaluation.

```text
formal_v011
main project integration
trading conclusions
```

This V1.4-L registration branch does not merge A5, does not tag A5, does not
start `formal_v011`, does not run model learning workloads, does not run a
distributed model launcher, does not call accelerator APIs, does not modify
quarantine, and does not submit runtime artifacts.

Runtime paths remain non-committable:

```text
runtime_intake/
runtime_inbox/
outputs/
```

## Recommendation

Keep A5 reviewed but unmerged until human control decides whether a status-only
registration should enter `main`. The next technical step is not authorized by
this document. If authorized later, the only valid continuation is from the
confirmed weak-key ambiguity status, not from formal readiness.
