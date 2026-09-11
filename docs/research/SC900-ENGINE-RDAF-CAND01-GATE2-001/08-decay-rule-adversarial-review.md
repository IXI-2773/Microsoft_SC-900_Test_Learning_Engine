# Decay Rule Adversarial Review

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Frozen Rule

Historical prior authority is:

- `SEED`: fewer than 10 clean SC-900 held-out probe outcomes;
- `ADVISORY`: 10 through 29 clean SC-900 held-out probe outcomes;
- `RETIRED`: at 30 clean 7-day probe outcomes, all four domains represented, and at least 4 observations per domain.

After `RETIRED`, the prior loses decision authority and must never regain it.

## Counting Semantics Needed

A future implementation must define and test the exact countable observation:

- SC-900, not SY0-701;
- held-out PROBE item;
- clean, not contaminated;
- first scored attempt on that exact item;
- 7-day observation for RETIRED counting;
- valid domain metadata;
- not duplicated by restore, backup, retry, redo, or export/import.

## Break Attempts

| Attack | Required fail-closed behavior |
| --- | --- |
| Contaminated probe appears correct | Exclude from clean count and primary endpoint. |
| Missed 7-day probe | Mark `UNOBSERVED`, not wrong and not correct. |
| 30 clean probes but one domain has fewer than 4 | Remain `ADVISORY`, not `RETIRED`; do not reset to `SEED`. |
| Restore imports old progress | Do not decrement authority or regain SEED. |
| User changes device or bank path | Preserve monotonic authority by stable evaluation identity. |
| Direct SC-900 evidence clearly contradicts prior during ADVISORY | Direct evidence wins. |
| Confidence or response time aligns with prior | Cannot override the stage rule. |

## Disposition

The rule is well stated in documents but unimplemented. It needs later tests for monotonicity, clean-count filtering, all-domain coverage, and irreversible retirement.

`DECAY_RULE = CONCEPTUALLY_ACCEPTABLE`  
`ENFORCEMENT = NOT_PROVEN`  
`GATE_EFFECT = MATERIAL_UNRESOLVED`