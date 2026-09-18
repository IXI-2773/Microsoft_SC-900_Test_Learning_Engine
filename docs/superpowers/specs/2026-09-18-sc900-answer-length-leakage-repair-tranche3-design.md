# SC-900 Answer-Length Leakage Repair — Tranche 3 Design Contract

**Date:** 2026-09-18  
**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE3-DESIGN`  
**Design base:** T2 implementation HEAD `56739154999795434abe761e4032d465ec967f20`  
**Status:** DESIGN ONLY

This contract authorizes a future T3 implementation package only after a separate exact-head implementation prompt. It does not authorize content edits, a T3 candidate bank, registry activation, default-bank change, EXE rebuild, Package C, or merge.

Parent authorities:

- `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md` (statistical target and quality override unchanged)
- `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md` (Package A)
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/17-PACKAGE-B-TRANCHE3-DESIGN.md`

## Frozen residual

```text
T2_CANDIDATE = sc900_bank_v8_length_rebalanced_t2.json
T2_CANDIDATE_SHA256 = 9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800
T2_CANDIDATE_FINGERPRINT = 34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b
PRODUCTION_BANK = sc900_bank_v8_final.json
PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
STRICT_LONGEST_ON_T2_CANDIDATE = 270 / 449
UNIQUE_LONGEST_ON_T2_CANDIDATE = 270 / 428
DOMAIN_MAXIMUM = microsoft_compliance_solutions 64 / 102 = 62.75%
T2_EXTERNAL_REVIEW_STATE = IMPLEMENTED_UNMERGED
```

Package B completion target is unchanged:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
QUALITY_OVERRIDE = factual/pedagogical integrity wins
```

Unique-longest is the stricter global metric. A strict-longest count of 179 / 449 would still leave 179 / 428 ≈ 41.82% unique-longest if the unique denominator does not shrink.

## Architecture

```text
SELECTED = CHAINED_T3
T3_SOURCE = sc900_bank_v8_length_rebalanced_t2.json
T3_TARGET = sc900_bank_v8_length_rebalanced_t3.json
T3_MANIFEST = t2 -> t3
PRODUCTION_DEFAULT = sc900_bank_v8_final.json
REGISTRY = {}
```

T3 live-state tests bind progress/session fixtures to the T2 candidate as source. They do not activate T1, T2, or T3. Package C activation topology is out of scope.

## Repair strategy

Primary tactic: `MIXED_BY_CANDIDATE`.

- Second-pass near-crossing prior EDITs: prefer distractor-only when the correct choice is already tight.
- Fresh sentence-like items in the 21–50 gap band: prefer two-sided equivalent rebalancing.
- Do not default to T1 correct-only tightening.
- Do not globally mandate distractor growth from the small T2 distractor-only sample (4 / 6).
- T1 and T2 SKIP IDs stay excluded.

Permitted change surface remains version-1 wording-only A–D choices. All other question fields stay unchanged.

Record both max-distractor metric delta and per-option length deltas. Trigger extra semantic inspection for unusually large growth; do not impose a hard character cap.

## Queue

Primary bound: **36** IDs listed in `17-PACKAGE-B-TRANCHE3-DESIGN.md` and `19-PACKAGE-B-TRANCHE3-QUEUE.json`.

Composition: 10 prior-edit second-pass residuals + 26 never-reviewed yield-band items. Domain quotas: compliance 12, security 12, entra 8, SCI 4.

The list is a design candidate queue, not an approved `EDIT` set. Semantic review during implementation may `SKIP` any item. A smaller executed tranche is allowed if equivalence cannot be established.

## Implementation boundary

Future implementation work ID:

```text
SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE3-001
```

Authorized implementation branch, when separately authorized:

```text
implementation/sc900-content-revision-equivalence-migration-B-tranche3-001
```

Exact implementation base SHA must be a commit that still contains the frozen T2 candidate identity. Do not start from this design branch. T2 merge is a predecessor gate, not an implied authorization.

T3 must stop for external review before merge. T3 must not start T4, Package C, registry activation, default-bank change, or EXE rebuild.

```text
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T3 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
T4_LIKELY_REQUIRED = YES
PRODUCTION_ACTIVATION_READINESS = NOT_READY
```
