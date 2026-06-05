# Protocol Alignment

Date: 2026-06-05

## Current Protocol Baseline

```text
protocol_repo = AETF-Protocol-Q3
protocol_version = v0.1.0-rc1
schema_version = aetf.protocol.bundle.v1
```

AETF-ModelLab-Q3 recognizes AETF-Protocol-Q3 as the third communication / contract / validation / gate repository for left-side three-repo communication.

## Repository Role

AETF-ModelLab-Q3 is the model and algorithm repository.

It only provides:

```text
research
diagnosis
model output
explanation
risk note
READ_ONLY advisory
```

AETF-ModelLab-Q3 does not own final action.

## Allowed Inbound Bundle

AETF-ModelLab-Q3 may use AETF-LeftLab-Q3 production snapshot only after AETF-Protocol-Q3 validation.

Direction:

```text
AETF-LeftLab-Q3
  -> production_snapshot bundle
  -> AETF-Protocol-Q3 validation
  -> AETF-ModelLab-Q3 read-only research input
```

The bundle is a snapshot, not production authority.

## Allowed Outbound Advisory

AETF-ModelLab-Q3 may send model advisory only through AETF-Protocol-Q3 validation.

Direction:

```text
AETF-ModelLab-Q3
  -> model_advisory bundle
  -> AETF-Protocol-Q3 validation
  -> human promotion gate
  -> AETF-LeftLab-Q3 separate implementation task only after approval
```

## Required Advisory Fields

```text
advisory_mode = READ_ONLY
final_action_change_allowed = false
contains_live_action = false
contains_secret = false
based_on_production_bundle declared
```

## Mandatory Rejection Rules

AETF-ModelLab-Q3 must not produce or forward any advisory containing:

```text
formal action
live action material
automatic execution instruction
secret or credential material
production connection material
final_action_change_allowed = true
advisory_mode != READ_ONLY
```

## Promotion Gate

AETF-ModelLab-Q3 output cannot directly enter AETF-LeftLab-Q3 production logic.

Any model result entering AETF-LeftLab-Q3 must follow:

```text
model research report
-> AETF-Protocol-Q3 validation
-> human confirmation
-> AETF-LeftLab-Q3 separate implementation task
-> AETF-LeftLab-Q3 tests
-> AETF-LeftLab-Q3 acceptance
-> small commit
```

## Current Integration Scope

This is docs-only protocol alignment.

This task does not:

```text
change model logic
train models
run experiments
refresh runtime data
connect production system
generate formal execution plan
generate formal action
call Protocol tool code
modify AETF-LeftLab-Q3
modify AETF-Protocol-Q3
write runtime exchange
```
