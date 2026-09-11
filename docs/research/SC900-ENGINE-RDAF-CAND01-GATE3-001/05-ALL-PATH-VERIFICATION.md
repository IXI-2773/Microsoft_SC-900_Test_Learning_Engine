# 05 — All-path verification

```text
RECEIPT = SC900-ENGINE-RDAF-CAND01-GATE3-001 / 05-ALL-PATH-VERIFICATION
STATUS = VERIFIED
TASK7_PATHS = P01-P48
MISSING_PATHS = 0
```

Canonical matrix: `cand01r3_paths.PATH_MATRIX`

Enforcement rule: filter early and revalidate late. Guarding only final render is insufficient.

## Runtime choke points

- Early TRAIN filter: session builder pool, Smart Practice signal/worker/cache, due/weak pools, follow-up index, injection candidate scans
- Late revalidation: session start, follow-up insert, jump, render, restore, analytics/export sanitize

## Disposition summary

| Status | Paths |
| --- | --- |
| ENFORCED | P01–P36, P41, P44, P45, P47, P48 |
| DESIGN_TIME_NOT_RUNTIME | P37, P43 |
| ADMIN_AUTHORING_CONTAMINATION_RECORDED | P38, P39, P40, P46 |
| FIXTURE_FAIL_CLOSED | P42 |

Design-time and admin-authoring paths are not learner training selectors. They remain accounted for: unknown/unassigned items fail closed inside an active experiment, and PROBE debug/authoring exposure is treated as contamination rather than a training eligibility bypass.

The automated matrix test fails if any Task-7 path id is missing.
