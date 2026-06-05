# AETF-ModelLab-Q3

AETF-ModelLab-Q3 is the model and algorithm research repository for the AETF left-side Q3 architecture.

It is not the production/control repository and does not own final action.

```text
AETF-LeftLab-Q3   = front-end and control / production-like side / final action source
AETF-ModelLab-Q3  = model and algorithm research / READ_ONLY advisory source
AETF-Protocol-Q3  = communication contract / schema / validation / safety gate
```

## Current Protocol Baseline

```text
protocol_repo = AETF-Protocol-Q3
protocol_version = v0.1.0-rc1
schema_version = aetf.protocol.bundle.v1
```

AETF-ModelLab-Q3 must output only READ_ONLY advisory bundles that pass AETF-Protocol-Q3 validation.

## Repository Role

AETF-ModelLab-Q3 is responsible for:

```text
research
diagnosis
model output
explanation
risk notes
READ_ONLY advisory
reproducible experiment notes
```

It must not:

```text
change AETF-LeftLab-Q3 final action
generate formal execution actions
bypass AETF-LeftLab-Q3 risk control
directly modify AETF-LeftLab-Q3
auto-submit production actions
carry secrets or production connection material
```

## Advisory Boundary

Any model output sent toward AETF-LeftLab-Q3 must be a `model_advisory` bundle with:

```text
advisory_mode = READ_ONLY
final_action_change_allowed = false
contains_live_action = false
contains_secret = false
based_on_production_bundle declared
```

## Flow

```text
AETF-LeftLab-Q3
  -> production_snapshot bundle
  -> AETF-Protocol-Q3 validation
  -> AETF-ModelLab-Q3 read-only research input

AETF-ModelLab-Q3
  -> model_advisory bundle
  -> AETF-Protocol-Q3 validation
  -> human promotion gate
  -> AETF-LeftLab-Q3 separate implementation task only after approval
```

## Promotion Gate

Model results do not enter production directly.

They must go through:

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

This repository is currently docs-only aligned with `AETF-Protocol-Q3 v0.1.0-rc1`.

This task does not:

```text
train models
run experiments
refresh runtime data
connect production systems
generate formal execution plan
generate formal action
call Protocol tool code
modify AETF-LeftLab-Q3
modify AETF-Protocol-Q3
write runtime exchange
```
