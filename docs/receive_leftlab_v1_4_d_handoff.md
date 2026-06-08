# Receive LeftLab V1.4-D Handoff

## Scope

This document records the ModelLab receive/validate result for the LeftLab V1.4-D READY handoff package.

This receive step did not start replay, did not start `formal_v011`, did not train a model, did not run `torchrun`, and did not call GPU.

## Receive Context

- received_at: `2026-06-08T20:58:48+08:00`
- clean workspace: `E:\AETF-ModelLab-Q3-clean`
- legacy workspace status: `E:\AETF-ModelLab-Q3` is retained as quarantine / legacy worktree
- runtime exchange path: `E:\aetf_runtime_exchange\left_to_model\v1_4_d_ready_handoff\`
- zip filename: `true_left_candidate_history_handoff_v1_4_d_READY.zip`
- summary filename: `true_left_candidate_history_handoff_v1_4_d_READY_summary.md`
- checklist filename: `DELIVERY_TO_MAC_CHECKLIST.txt`
- transfer receipt filename: `TRANSFER_RECEIPT.json`
- ModelLab runtime unpack path: `E:\AETF-ModelLab-Q3-clean\runtime_inbox\leftlab_v1_4_d_ready_handoff\`

## External File Checks

All expected runtime exchange files were present:

- `true_left_candidate_history_handoff_v1_4_d_READY.zip`
- `true_left_candidate_history_handoff_v1_4_d_READY_summary.md`
- `DELIVERY_TO_MAC_CHECKLIST.txt`
- `TRANSFER_RECEIPT.json`

SHA-256 results:

- zip expected: `e2f7dbb69067f570baad611e301d73f8fa8ff2c87cbfbc740e4def766c6ac137`
- zip actual: `e2f7dbb69067f570baad611e301d73f8fa8ff2c87cbfbc740e4def766c6ac137`
- zip match: yes
- summary expected: `1eba54823cd136e56c1a4dd813666d8048477d6f153850dfb8a99eb38eea8e8d`
- summary actual: `1eba54823cd136e56c1a4dd813666d8048477d6f153850dfb8a99eb38eea8e8d`
- summary match: yes

`TRANSFER_RECEIPT.json` was present and consistent with the staged package:

- `transfer_status=STAGED_FOR_MODELLAB`
- `modellab_received=false` before this receive validation report
- `modellab_replay_completed=false`
- `formal_v011_ready=NOT_EVALUATED_BY_MODELLAB`
- `not_reconstructed=true`
- `not_trading_advice=true`

## Payload File List

The zip was unpacked into ModelLab runtime-only inbox. The following payload files were present:

- `true_left_candidate_history_handoff\manifest.json`
- `true_left_candidate_history_handoff\candidate_history.jsonl`
- `true_left_candidate_history_handoff\candidate_schema.md`
- `true_left_candidate_history_handoff\artifact_index.json`
- `true_left_candidate_history_handoff\checksums.sha256`
- `true_left_candidate_history_handoff\feature_snapshot_refs.json`
- `true_left_candidate_history_handoff\label_snapshot_refs.json`
- `true_left_candidate_history_handoff\similar_case_refs.json`
- `true_left_candidate_history_handoff\probability_bucket_snapshot.json`
- `true_left_candidate_history_handoff\frontend_explanation_snapshot.json`
- `true_left_candidate_history_handoff\left_v1_3_commit.txt`

The runtime inbox path is ignored by Git in the clean clone and the unpacked payload is not committed.

## Candidate History Validation

- `candidate_history.jsonl` line count: `20`
- required-field validation: pass
- missing required fields: `0`

Each candidate history record contains:

- `candidate_id`
- `timestamp`
- `round`
- `decision_step`
- `source_snapshot_id`
- `input_feature_snapshot_ref`
- `label_snapshot_ref`
- `similar_case_ref`
- `probability_bucket`
- `frontend_explanation_ref`
- `candidate_rank`
- `decision`
- `decision_reason`
- `left_project_commit`
- `artifact_ref`

## Manifest Validation

Manifest fields:

- `handoff_status=READY`
- `candidate_history_type=true_left_candidate_history`
- `candidate_count=20`
- `not_reconstructed=true`
- `not_trading_advice=true`
- `ready_for_modellab_replay=true`
- `ready_for_formal_v011_recheck=true`
- `missing_artifacts=[]`

Ref match summary:

- feature refs: `20/20`
- similarity refs: `20/20`
- frontend refs: `20/20`
- label refs: `20/20`
- probability refs: `20/20`

`ready_for_formal_v011_recheck=true` only means the package is eligible for ModelLab replay followed by formal readiness re-evaluation. It does not mean `formal_v011` has passed.

## Internal Checksum Validation

`checksums.sha256` was compatible with manual PowerShell validation. Each declared payload hash matched:

- `artifact_index.json`: pass
- `candidate_history.jsonl`: pass
- `candidate_schema.md`: pass
- `feature_snapshot_refs.json`: pass
- `frontend_explanation_snapshot.json`: pass
- `label_snapshot_refs.json`: pass
- `left_v1_3_commit.txt`: pass
- `manifest.json`: pass
- `probability_bucket_snapshot.json`: pass
- `similar_case_refs.json`: pass

Checksum failures: `0`

## Trading Instruction Word Scan

Search terms:

- `买入`
- `卖出`
- `加仓`
- `清仓`
- `满仓`
- `强烈买入`
- `必买`
- `必卖`

Result: no matches found.

## Receive Conclusion

ModelLab receive/validate passed again in the clean clone for the LeftLab V1.4-D READY handoff package.

The package is suitable to enter a separately authorized replay stage. This report does not start replay and does not determine `formal_v011_ready`.

Current formal status:

- `modellab_replay_completed=false`
- `formal_v011_ready=NOT_EVALUATED_BY_MODELLAB`
