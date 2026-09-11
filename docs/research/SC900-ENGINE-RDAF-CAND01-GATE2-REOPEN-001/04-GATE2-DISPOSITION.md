# Gate-2 Reopening Disposition

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001`  
PREDECESSOR = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
PHASE3_EVIDENCE = `SC900-BANK-PHASE3-001`

## Terminal disposition

```text
GATE2_REOPENING_ADJUDICATED = YES
CAND01R2_DISPOSITION = GATE_2_BLOCKED_DESIGN_REVISION_REQUIRED
CAND01R3_DISPOSITION = GATE_2_EARNED
CAND01_GATE2_STATUS = GATE_2_EARNED
AUTHORIZED_CANDIDATE = CAND-01R3_PRIOR_NEUTRAL_HELD_OUT_POLICY_VERIFICATION
IMPLEMENTATION_AUTHORIZED = YES
IMPLEMENTATION_SCOPE = BOUNDED_GATE3_CAND01R3_ONLY
HISTORICAL_SY0701_PRIOR_RUNTIME_AUTHORITY = PROHIBITED
RUNTIME_GUARDS_IMPLEMENTED = NO
RUNTIME_RRC1_IMPLEMENTED = NO
LEARNING_EFFECTIVENESS_PROVEN = NO
DEPLOYMENT_AUTHORIZED = NO
DEFAULT_BANK_ACTIVATION_AUTHORIZED = NO
PR10_MERGE_AUTHORIZED_BY_THIS_PACKAGE = NO
NOETIC_GATE = ALLOW_POSITIVE_GATE2_CLOSURE
```

## What earned Gate 2

Gate 2 is earned for the bounded CAND-01R3 design because the adversarial design requirements are now implementation-ready:

1. **Reviewed bank:** 200 approved / 200 compiled candidate questions with current Microsoft provenance and 58 blueprint leaves.
2. **Meaningful-transfer control:** 27 resolved semantic families, 158 merges, 20 explicit transfer edges, zero unresolved families.
3. **Concrete holdout:** 171 TRAIN / 29 PROBE / 7 independent PROBE families, with zero family splits and zero transfer-edge crossings.
4. **All-path exclusion contract:** Task-7 P01–P48 current-source inventory and one shared fail-closed eligibility boundary.
5. **Future verification matrix:** path-specific positive, negative, fail-closed, family, transfer, restore, cache, render, history, analytics/export obligations.
6. **RRC-1 design:** mutually exclusive REPAIR / REVIEW / COVERAGE classes with deterministic service semantics.
7. **Fairness/starvation observability:** service delay, overdue, starvation, queue age, coverage debt, class share, backlog, and domain/objective balance metrics are defined without fabricated thresholds.
8. **Measurement integrity:** clean held-out 7-day first-attempt endpoint, UNOBSERVED missingness, monotonic contamination, stable evaluation identity.
9. **Confound contract:** TRAIN/PROBE is explicitly separate from Smart Practice/RRC-1 arm allocation; exposure/time/order/source/family/dose imbalances must be recorded.
10. **Noetic reconciliation:** no material Gate-2 attack remains `UNRESOLVED` after CAND-01R3 removes the unproven cross-exam prior from load-bearing authority.

## Why CAND-01R2 did not earn Gate 2 as written

The historical SY0-701 prior remained `PLAUSIBLE_BUT_UNPROVEN`, while original Gate-2 authority explicitly required direct SC-900 evidence before that prior could support positive closure.

Rather than weaken the requirement or invent direct evidence, the reopening review made the smallest falsifiability-preserving design correction:

> the first SC-900 champion/challenger comparison is prior-neutral.

CAND-01R3 therefore tests the scheduler/held-out design without simultaneously testing cross-exam learner-profile portability.

The historical prior is preserved as research context only and requires a later separate reopening before any runtime authority can be granted.

## Noetic disposition

```text
N02 = RESOLVED_BY_SCOPE_EXCLUSION
N03 = ACTIVE_PRESERVED
N04 = ACTIVE_PRESERVED
N05 = ACTIVE_PRESERVED
N06 = ACTIVE_CONSTRAINT_SATISFIED_AT_DESIGN_LEVEL
N07 = RESOLVED_FOR_DESIGN
N08 = ACTIVE_CONSTRAINT_SATISFIED_AT_DESIGN_LEVEL
MATERIAL_UNRESOLVED_GATE2_ITEMS = 0
```

`ACTIVE` does not mean empirically proven. It means the attack remains a required constraint/falsification obligation rather than an unexamined design gap.

## Gate-2 / Gate-3 boundary

This disposition authorizes a **bounded Gate-3 implementation package**. It does not claim Gate-3 success.

Gate 3 must actually implement and prove the contracts frozen at Gate 2.

At minimum Gate 3 must:

### Partition enforcement

- load and verify the accepted partition authority;
- fail closed on missing/malformed/unknown/hash-mismatched authority;
- permit TRAIN only for training paths;
- permit PROBE only for clean measurement paths;
- keep UNASSIGNED/unknown/ineligible items out of both;
- enforce whole-family and transfer-edge isolation.

### All-path coverage

Implement the shared eligibility boundary before material exposure or derived-state construction across every Task-7 P01–P48 path, including selection, follow-ups, Smart Practice prewarm/cache, detached work, restore, render, history, analytics/export, compile/load, debug, and fixture-sensitive paths as applicable.

### RRC-1

Implement the prior-neutral challenger only:

- REPAIR first;
- REVIEW second;
- COVERAGE third;
- mutually exclusive snapshot assignment;
- deterministic within-class ordering;
- no confidence or response-time class authority;
- no SY0-701 historical-prior authority.

### Fairness and measurement instrumentation

Record sufficient events to compute the frozen Task-7 fairness/starvation metrics and the champion/challenger confound ledger.

Implement clean/contaminated/UNOBSERVED probe observation custody with stable evaluation identity.

### Verification

Gate-3 tests must cover every frozen negative/fail-closed path and prove runtime enforcement. Passing ordinary software tests alone is not evidence of learning effectiveness.

## Explicit prohibitions

Gate-2 earned does **not** authorize:

- declaring RRC-1 superior to Smart Practice;
- declaring Smart Practice superior to RRC-1;
- claiming SC-900 exam readiness from the candidate model;
- population/general efficacy claims from one learner;
- enabling the historical Security+ prior;
- activating the Phase-3 candidate bank as the default launch bank;
- merging PR #10 without explicit operator authorization;
- production/deployment claims before Gate-3 verification.

## Microsoft blueprint check

The reopening review rechecked Microsoft Learn on 2026-09-11. The current SC-900 study guide continues to use the July 28, 2026 skills-measured blueprint and four weight bands used by the Phase-3 allocation. No blueprint drift blocks Gate 2.

Authority: `https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900`

## Evidence identity

```text
PHASE3_FINAL_HEAD = 06182c9dec6ddb7ef2090c5818228bb924aae20e
PHASE3_TESTED_EVIDENCE_HEAD = 04e728cf4e6ddc0ec5b3e322f2602f6ce9056840
SEMANTIC_AUDIT_SHA256 = e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701
STORE_SHA256 = 2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c
COMPILED_CANDIDATE_SHA256 = 72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b
TRAIN_PROBE_MANIFEST_SHA256 = 67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90
DEFAULT_LAUNCH_BANK_SHA256 = 60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426
```

## Protected-state rule

The recovery refs and baseline tag remain protected and outside this package. This reopening package contains design/research documentation only.

## Next authorized work

```text
NEXT_LOGICAL_NODE = CAND01R3_GATE3_BOUNDED_IMPLEMENTATION
PR10 = OPEN_UNMERGED
MERGE = NOT_AUTHORIZED_BY_THIS_DISPOSITION
```

Gate-3 implementation must start from the accepted Phase-3 evidence and this prior-neutral Gate-2 disposition. If implementation requires weakening any frozen fail-closed, family-isolation, measurement, or prior-neutral rule, Gate 2 must be reopened rather than silently changing the contract.
