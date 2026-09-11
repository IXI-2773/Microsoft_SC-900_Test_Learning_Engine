# CAND-01R3 — Prior-Neutral Initial SC-900 Comparison

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001`  
STATUS = `BOUNDED_GATE2_DESIGN_CORRECTION`

## Purpose

Remove the unproven SY0-701 historical learner prior from all load-bearing authority in the first SC-900 champion/challenger comparison, without changing the accepted RRC-1, TRAIN/PROBE, measurement, or Phase-3 bank design.

This is a design correction only. No runtime implementation occurs in this package.

## Candidate identity

```text
CANDIDATE = CAND-01R3 - Prior-Neutral Held-Out Policy Verification
CHAMPION = Current Smart Practice, unchanged except future common TRAIN-only eligibility boundary
CHALLENGER = RRC-1 - REPAIR / REVIEW / COVERAGE
PRIMARY_ENDPOINT = 7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items
```

## Removed authority

For the initial authorized SC-900 implementation/experiment, historical SY0-701 learner evidence has zero control authority.

It MUST NOT determine:

- RRC-1 class membership;
- RRC-1 tie-breaking;
- Smart Practice selection;
- session size;
- arm allocation;
- domain/objective emphasis;
- TRAIN/PROBE membership;
- item difficulty;
- readiness/mastery;
- confidence weighting;
- response-time weighting;
- prior probability of SC-900 correctness;
- pass/readiness estimates;
- retirement or promotion decisions.

The implementation default is therefore SC-900-prior-neutral.

## What may remain

Historical Security+ material may remain only as:

- non-runtime research context;
- a documented future hypothesis about exam-independent learner-strategy tendencies;
- an offline comparison target after direct clean SC-900 evidence exists.

It may not influence learner-facing or scheduler behavior in the initial CAND-01R3 implementation.

No private learner outcome or prior is required to run CAND-01R3.

## RRC-1 remains unchanged

For each TRAIN-eligible SC-900 question at a service snapshot:

1. `REPAIR` — current SC-900 `is_active_weak(...)`;
2. `REVIEW` — not REPAIR and current SC-900 `is_review_due(...)`;
3. `COVERAGE` — not REPAIR/REVIEW and serves SC-900 blueprint coverage.

Service order remains:

`REPAIR -> REVIEW -> COVERAGE -> ...`

with empty-class skip and the already frozen deterministic within-class ordering.

No weighted utility is introduced.

## Held-out measurement remains unchanged

Task-6 authority remains:

```text
TRAIN = 171 questions / 20 semantic families
PROBE = 29 questions / 7 independent semantic families
UNASSIGNED = 0
FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
```

Both champion and challenger train only on TRAIN.

PROBE is common measurement holdout, not an experimental arm.

## Prior-decay documents after this correction

The existing SEED / ADVISORY / RETIRED design remains valuable as a **future optional historical-prior lane**, but it is no longer a prerequisite for the initial CAND-01R3 implementation.

Its status becomes:

```text
HISTORICAL_PRIOR_RUNTIME_AUTHORITY = DISABLED_FOR_CAND01R3_INITIAL_COMPARISON
SEED_ADVISORY_RETIRED_CONTRACT = PRESERVED_FOR_FUTURE_OPTIONAL_RESEARCH
DIRECT_SC900_EVIDENCE_REQUIRED_BEFORE_REENABLING = YES
```

If a later package proposes to re-enable any historical prior, it must:

1. reopen N02 portability explicitly;
2. use direct clean SC-900 evidence;
3. implement and test the frozen decay/monotonicity contract;
4. prove that the prior adds value without contaminating the champion/challenger comparison;
5. receive separate authorization.

## Gate-3 implementation obligations

CAND-01R3 implementation must still implement and test:

- shared fail-closed partition eligibility;
- all-path TRAIN/PROBE isolation across the Task-7 P01–P48 inventory;
- role-safe cache/prewarm/derived state;
- restore/import enforcement;
- protected PROBE render/history/analytics/export custody;
- RRC-1 mutually exclusive class assignment;
- RRC-1 fairness/starvation instrumentation;
- experiment allocation/confound logging;
- clean/contaminated/UNOBSERVED probe outcome identity.

This design correction does not claim any of those are already implemented.

## Why this is preferable to inventing prior portability

The first SC-900 comparison is intended to test scheduling policy, not to simultaneously test whether Security+ learner-profile traits transfer to SC-900.

Keeping the historical prior active would introduce a second causal hypothesis into the first comparison and make a poor RRC-1 result ambiguous:

- scheduler failure;
- cross-exam prior failure;
- or interaction between both.

Removing prior authority makes the initial comparison simpler, cleaner, and more falsifiable.

## Disposition

```text
CAND01R3_DESIGN = FROZEN
CROSS_EXAM_PRIOR_IS_LOAD_BEARING = NO
INITIAL_SC900_COMPARISON_PRIOR_NEUTRAL = YES
HISTORICAL_PRIOR_REENABLE_REQUIRES_SEPARATE_REVIEW = YES
RUNTIME_IMPLEMENTED_HERE = NO
```
