# SC900-ENGINE-RDAF-CAND01-GATE3-001 — Handoff

```text
WORK_ID = SC900-ENGINE-RDAF-CAND01-GATE3-001
CANDIDATE = CAND_01R3
PACKAGE = CAND-01R3 — GATE 3 BOUNDED RUNTIME IMPLEMENTATION
SOURCE_RESEARCH_BRANCH = research/sc900-cand01-gate2-reopen-001
GATE_2_REOPENING_HEAD = a9d66c093fa821a1db0b4f4cae348052f0357e25
PHASE_3_TERMINAL_HEAD = 06182c9dec6ddb7ef2090c5818228bb924aae20e
IMPLEMENTATION_BRANCH = implementation/sc900-cand01r3-gate3
IMPLEMENTATION_SCOPE = BOUNDED_GATE3_CAND01R3_ONLY
IMPLEMENTATION_AUTHORIZED = YES
```

## Authority inherited, not reopened

```text
CAND01R2_DISPOSITION = GATE_2_BLOCKED_DESIGN_REVISION_REQUIRED
CAND01R3_DISPOSITION = GATE_2_EARNED
CAND01_GATE2_STATUS = GATE_2_EARNED
HISTORICAL_SY0701_PRIOR_RUNTIME_AUTHORITY = PROHIBITED
DEPLOYMENT_AUTHORIZED = NO
DEFAULT_BANK_ACTIVATION_AUTHORIZED = NO
LEARNING_EFFECTIVENESS_PROVEN = NO
```

Gate 3 implements and verifies the CAND-01R3 runtime. It does not reopen Gate 2, merge PR #10, merge PR #11, activate the 200-question candidate bank as the launch bank, or claim learning effectiveness.

## Design

CAND-01R3 is prior-neutral held-out policy verification:

- Champion: current Smart Practice, TRAIN-only eligible universe
- Challenger: RRC-1 (REPAIR / REVIEW / COVERAGE)
- Both policies train only on the frozen TRAIN set
- PROBE is held out for clean measurement
- Historical SY0-701 learner information has zero runtime policy authority

Enforcement is scoped. The normal engine remains behaviorally unchanged when the CAND-01R3 context is inactive.

## Frozen Phase-3 inputs

```text
APPROVED_QUESTIONS = 200
COMPILED_QUESTIONS = 200
SEMANTIC_FAMILIES = 27
TRAIN_QUESTIONS = 171
PROBE_QUESTIONS = 29
UNASSIGNED_QUESTIONS = 0
TRAIN_FAMILIES = 20
PROBE_FAMILIES = 7
UNASSIGNED_FAMILIES = 0
TRAIN_PROBE_FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
EFFECTIVE_INDEPENDENT_PROBE_UNITS = 7
```

Hash bindings:

| Artifact | SHA-256 |
| --- | --- |
| Task-4 semantic audit | `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701` |
| Task-5 reviewed store | `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c` |
| Task-5 compiled candidate bank | `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b` |
| Task-6 TRAIN/PROBE manifest | `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90` |
| Default launch bank | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

Gate 3 must not mutate those artifacts. If an implementation defect appears to require mutation, stop and treat it as an upstream evidence defect.

## What this package must prove

1. Fail-closed partition eligibility for TRAINING and MEASUREMENT.
2. Explicit CAND-01R3 runtime context; inactive context leaves the default engine unchanged.
3. Early TRAIN filtering of derived Smart Practice / worker / cache state.
4. Late revalidation on selection, injection, render, restore, and export surfaces.
5. RRC-1 prior-neutral class assignment and round-robin service.
6. Clean PROBE measurement custody, contamination monotonicity, and UNOBSERVED missingness.
7. Task-7 P01–P48 all-path reconciliation.

## What this package must not claim

```text
RRC-1 improves learning = NOT CLAIMED
Smart Practice is worse = NOT CLAIMED
candidate bank predicts exam success = NOT CLAIMED
7-day endpoint measured = NOT CLAIMED
historical prior is useful = NOT CLAIMED
deployment authorized = NO
candidate bank is the default launch bank = NO
```

## Protected refs (must remain unchanged)

```text
recovery/publish-exact-history/sc900-v8-20260910 = b567d4b74a2f99e50022dd0dafd81ffa75dff0a2
recovery/publish-sc900-v8-exact-history = bbc3bd900b73bde89151dc51706ad62fc69e8196
tag sc900-v8.0.0-baseline object = 9c80be5b20e652dc2eb86621dfdf7c32baa06528
```
