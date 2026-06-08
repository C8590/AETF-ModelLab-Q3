# Plan LeftLab V1.4-D Handoff Replay

## Scope

This is a pre-replay planning audit for the LeftLab V1.4-D READY handoff package.

This stage does not start replay, does not start `formal_v011`, does not train a model, does not run `torchrun`, does not call GPU, does not modify LeftLab, and does not modify Protocol.

## Input Confirmation

Receive/validate source:

- receive report source: `receive-leftlab-v1-4-d-handoff:docs/receive_leftlab_v1_4_d_handoff.md`
- handoff zip path: `E:\aetf_runtime_exchange\left_to_model\v1_4_d_ready_handoff\true_left_candidate_history_handoff_v1_4_d_READY.zip`
- unpacked payload path: `E:\AETF-ModelLab-Q3\runtime_inbox\leftlab_v1_4_d_ready_handoff\true_left_candidate_history_handoff\`
- `candidate_history.jsonl` line count: `20`
- manifest `handoff_status`: `READY`
- manifest `candidate_history_type`: `true_left_candidate_history`
- manifest `ready_for_modellab_replay`: `true`
- manifest `ready_for_formal_v011_recheck`: `true`
- manifest `not_reconstructed`: `true`
- manifest `not_trading_advice`: `true`
- manifest `missing_artifacts`: `[]`
- `formal_v011_ready`: `NOT_EVALUATED_BY_MODELLAB`

Ref coverage already validated by receive/validate:

- feature refs: `20/20`
- similarity refs: `20/20`
- frontend refs: `20/20`
- label refs: `20/20`
- probability refs: `20/20`

`ready_for_formal_v011_recheck=true` means the handoff is eligible for a replay-based recheck. It does not mean `formal_v011` has passed.

## Replay Goals

The next replay stage should be limited to read-only research validation:

- align true-left candidate history against previous reconstructed history;
- replay the 20 true-left candidate records;
- recompute the decision matrix from true-left inputs;
- re-evaluate whether `formal_v011_ready` can be set after replay;
- determine whether the result can enter a later main-project integration assessment.

Replay must not produce trading advice, order instructions, strategy parameter changes, or direct LeftLab writeback.

## Field Mapping Plan

Each `candidate_history.jsonl` record should map to a ModelLab replay input row as follows:

| Handoff field | Replay input use |
| --- | --- |
| `candidate_id` | Stable case key for replay joins, logs, diagnostics, and output traceability. |
| `timestamp` | Candidate event time; maps to the replay as-of timestamp and temporal boundary. |
| `round` | Candidate generation round; used for grouping and replay batch metadata. |
| `decision_step` | Left-side decision stage; used to align replay diagnostics with decision flow. |
| `source_snapshot_id` | Source snapshot lineage key; used to join source artifact metadata. |
| `input_feature_snapshot_ref` | Pointer to feature snapshot payload used as replay model/input context. |
| `label_snapshot_ref` | Pointer to label/ground-truth snapshot for post-replay metric calculation. |
| `similar_case_ref` | Pointer to similar-case context for explainability and diagnostics. |
| `probability_bucket` | Bucket assignment used in decision matrix grouping and calibration checks. |
| `frontend_explanation_ref` | Pointer to frontend explanation snapshot for audit and explanation parity. |
| `candidate_rank` | Rank feature/grouping key for rank-stratified metrics. |
| `decision` | Left-side recorded decision used for replay outcome comparison. |
| `decision_reason` | Human-readable rationale used for discrepancy review; not an execution instruction. |
| `left_project_commit` | LeftLab source commit boundary for reproducibility. |
| `artifact_ref` | Artifact index pointer for payload-level traceability and checksum review. |

The replay stage should preserve all references as pointers. It should not reconstruct missing true-left history and should not overwrite the received handoff payload.

## Alignment With `reconstructed_v1`

The reconstructed branch is already documented as paused by stopline and not a substitute for true left-side history. The true-left replay should compare against it only as a diagnostic baseline.

Alignment dimensions:

- reconstructed candidate history vs true-left candidate history;
- `candidate_id` or compatible case key;
- ETF identifier from candidate/source refs where available;
- `timestamp` / as-of date;
- `candidate_rank`;
- `decision`;
- decision matrix group membership;
- direction accuracy;
- majority-direction baseline;
- missing-ref and missing-label rates.

Comparison outputs should separate:

- exact candidate overlap;
- true-left-only candidates;
- reconstructed-only candidates;
- rank movement or rank incompatibility;
- decision mismatch;
- direction outcome mismatch;
- probability bucket mismatch;
- explanation/similarity context mismatch.

The reconstructed metrics must remain labeled as reconstructed and must not be promoted to true-left evidence.

## `formal_v011_ready` Decision Plan

This planning stage does not decide `formal_v011_ready`.

The next replay stage may evaluate `formal_v011_ready` only after all of the following are checked:

- replay completed successfully without runtime integrity errors;
- decision matrix is complete for all eligible true-left candidates;
- true-left direction accuracy is computed from validated label refs;
- true-left accuracy is compared against the majority-direction baseline;
- data coverage is sufficient for the stated scope;
- missing feature, label, similarity, probability, and frontend refs remain at acceptable levels;
- no unexplained systematic bias appears by ETF, timestamp/date bucket, rank, decision, or probability bucket;
- no reconstructed data is substituted for true-left candidate history;
- no trading instruction or action field appears in replay outputs;
- any unresolved data-quality or statistical-stability issue is converted into a stopline rather than a readiness claim.

Potential outcomes:

- `formal_v011_ready=true`: only if replay, matrix, coverage, accuracy, baseline comparison, and bias review all support it.
- `formal_v011_ready=false`: if replay completes but evidence is insufficient or below the required baseline.
- `formal_v011_ready=STOPLINE_REQUIRED`: if replay reveals missing data, unstable metrics, unexplained bias, or scope violations.

## Forbidden Actions

This plan and the next replay stage must preserve these boundaries unless the controller explicitly authorizes a broader task:

- do not train models;
- do not run `torchrun`;
- do not call GPU;
- do not start `formal_v011`;
- do not output trading advice;
- do not submit orders or action instructions;
- do not modify LeftLab;
- do not modify Protocol;
- do not commit runtime inbox payloads or READY zip files.

## Next Step Recommendation

If this plan is approved, open a separate branch:

```text
replay-leftlab-v1-4-d-candidate-history
```

That stage may run the read-only candidate-history replay and formal readiness recheck. It should still avoid training, `torchrun`, and GPU unless the controller grants separate explicit authorization.
