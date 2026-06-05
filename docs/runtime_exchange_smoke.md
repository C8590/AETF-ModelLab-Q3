# Runtime Exchange Smoke Test

Date: 2026-06-05

## Scope

This document explains the AETF-ModelLab-Q3 side of the Phase 2 runtime exchange smoke test.

This is not model production deployment.

It only reads a validated `production_snapshot` bundle and generates a safe `model_advisory` READ_ONLY bundle for Protocol validation.

## Boundary

This smoke test does not:

```text
train models
run experiments
connect to production systems
generate formal execution plans
generate formal actions
change AETF-LeftLab-Q3 final action
modify AETF-LeftLab-Q3
write production outputs
```

## Script

```text
scripts/generate_readonly_advisory.py
```

The script generates:

```text
manifest.json
payload/advisory.json
```

with:

```text
bundle_type = model_advisory
source_repo = AETF-ModelLab-Q3
target_repo = AETF-LeftLab-Q3
advisory_mode = READ_ONLY
final_action_change_allowed = false
contains_live_action = false
contains_secret = false
based_on_production_bundle declared
```

## Example Command

Recommended local runtime exchange directory:

```text
E:\aetf_runtime_exchange
```

After AETF-LeftLab-Q3 exports a validated snapshot, run from AETF-ModelLab-Q3:

```powershell
py -3 scripts\generate_readonly_advisory.py `
  --production-bundle E:\aetf_runtime_exchange\left_to_model\smoke_snapshot `
  --output E:\aetf_runtime_exchange\model_to_left\smoke_advisory `
  --allow-overwrite
```

Then validate from AETF-Protocol-Q3:

```powershell
py -3 tools\validate_bundle.py `
  E:\aetf_runtime_exchange\model_to_left\smoke_advisory `
  --type model_advisory
```

Expected validator result:

```text
{"status": "ok", "bundle_type": "model_advisory"}
```

## Next Step

The validated advisory may only enter human promotion gate review.

AETF-LeftLab-Q3 must not automatically load the advisory into formal signals or final action.
