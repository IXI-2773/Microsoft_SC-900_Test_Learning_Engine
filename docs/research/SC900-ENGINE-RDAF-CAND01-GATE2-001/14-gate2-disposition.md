# Gate 2 Disposition

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
BASE_MAIN_SHA = `ae584fc2453c12cced98a7987702d8f37a2fc097`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`  
CANDIDATE = `CAND-01R2 - Historical Learner Prior + Held-Out Policy Verification`  
CHAMPION = `Current Smart Practice, unchanged`  
CHALLENGER = `RRC-1 - REPAIR / REVIEW / COVERAGE`  
PRIMARY_ENDPOINT = `7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items`

## Terminal Result

`GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`

## What Survived

- RRC-1 is a meaningful design candidate in principle.
- REPAIR-first precedence can remove due/weak double-membership at the class-assignment level.
- The held-out delayed primary endpoint is appropriate.
- The historical prior is properly constrained as a cold-start strategy hypothesis.
- The SEED / ADVISORY / RETIRED rule is conceptually fail-closed.

## What Blocks Gate 2

- The current bank has only eight placeholder questions and cannot support serious held-out champion/challenger evidence.
- No implementation-ready all-path TRAIN / PROBE exclusion contract and verification matrix has yet been frozen.
- Follow-up, repair, boss, stealth checkpoint, due, weak, Smart Practice, full-bank restore, render, history, analytics, and export paths are all potential leakage paths.
- Exact-item withholding does not guarantee meaningful transfer withholding.
- RRC-1 starvation and overdue-review fairness remain unresolved.
- Selection quality, blueprint balance, time trend, and one-learner confounds cannot be resolved without a real reviewed bank and allocation plan.
- Material noetic items remain `UNRESOLVED`.

## Implementation Authorization

`IMPLEMENTATION_AUTHORIZED = NO`

No runtime work is authorized by this package.

## Gate 2 / Gate 3 Boundary

Gate 2 must complete the all-path leakage inventory, define the implementation-ready TRAIN / PROBE exclusion contract, specify required guard semantics and fail-closed behavior, and specify the future verification/test matrix. Gate 3 or later implementation work must actually implement those guards and prove every runtime path enforces them.

## Next Gate Requirements

Gate 2 may be reopened only after:

1. a sufficiently large reviewed SC-900 bank exists;
2. a TRAIN / PROBE manifest design includes semantic-family controls;
3. implementation-ready leakage guard semantics and fail-closed behavior are specified for every inventory path in `05-probe-leakage-audit.md`;
4. a future verification/test matrix covers every selector, injector, restore, prewarm, render, history, analytics, and export path;
5. RRC-1 service fairness and starvation metrics are specified;
6. prior decay enforcement tests are specified;
7. unresolved material noetic findings are resolved or reclassified as non-material with basis.
