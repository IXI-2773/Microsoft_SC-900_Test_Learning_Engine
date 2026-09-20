# SC-900 Answer-Length Leakage Repair — Tranche 2 Design Contract

**Date:** 2026-09-18  
**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE2-DESIGN`  
**Design base:** `main` at `e535daef6ea62e174c453c6a8ad91c7331ceaf82`  
**Status:** DESIGN ONLY

This contract authorizes a future T2 implementation package only after a separate exact-head implementation prompt. It does not authorize content edits, a T2 candidate bank, registry activation, default-bank change, EXE rebuild, Package C, or merge.

Parent authorities:

- `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md` (design branch; statistical target and quality override unchanged)
- `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md` (Package A)
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/12-PACKAGE-B-TRANCHE2-DESIGN.md`

## Frozen residual

```text
T1_CANDIDATE = sc900_bank_v8_length_rebalanced_t1.json
T1_CANDIDATE_SHA256 = 45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8
PRODUCTION_BANK = sc900_bank_v8_final.json
PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
STRICT_LONGEST_ON_T1_CANDIDATE = 287 / 449
UNIQUE_LONGEST_ON_T1_CANDIDATE = 287 / 431
DOMAIN_MAXIMUM = microsoft_security_solutions 108 / 163 = 66.26%
```

Package B completion target is unchanged:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
QUALITY_OVERRIDE = factual/pedagogical integrity wins
```

## Architecture

```text
SELECTED = CHAINED_T2
T2_SOURCE = sc900_bank_v8_length_rebalanced_t1.json
T2_TARGET = sc900_bank_v8_length_rebalanced_t2.json
T2_MANIFEST = t1 -> t2
PRODUCTION_DEFAULT = sc900_bank_v8_final.json
REGISTRY = {}
```

T2 live-state tests bind progress/session fixtures to the T1 candidate as source. They do not activate T1 or T2. Package C activation topology is out of scope.

## Repair strategy

Prefer two-sided equivalent rebalancing. Do not repeat T1’s correct-only pattern as the default. T1 SKIP IDs are excluded. T1 EDIT residuals are excluded from the primary T2 queue.

Permitted change surface remains version-1 wording-only A–D choices. All other question fields stay unchanged.

## Queue

Primary bound: 50 unreviewed strict-longest IDs listed in `12-PACKAGE-B-TRANCHE2-DESIGN.md` and `13-PACKAGE-B-TRANCHE2-RESIDUAL-INVENTORY.json`. The list is a design candidate queue, not an approved EDIT set.

## Implementation boundary

Future implementation work ID:

```text
SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE2-001
```

Authorized implementation branch, when separately authorized:

```text
implementation/sc900-content-revision-equivalence-migration-B-tranche2-001
```

T2 must stop for external review before merge. T2 must not start T3, Package C, registry activation, default-bank change, or EXE rebuild.

```text
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T2 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
PRODUCTION_ACTIVATION_READINESS = NOT_READY
```
