# SC-900 Answer-Length Leakage Repair — Tranche 4 Design Contract

**Date:** 2026-09-18  
**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE4-CLOSURE-DESIGN`  
**Design base:** T3 implementation HEAD `400b7846189e6b12b599a4dcdd1da7ae2b321408`  
**Status:** DESIGN ONLY

This contract authorizes a future T4 implementation package only after a separate exact-head implementation prompt. It does not authorize content edits, a T4 candidate bank, registry activation, default-bank change, EXE rebuild, Package C, T5 implementation, or merge.

Parent authorities:

- `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md` (statistical target and quality override unchanged)
- `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md` (Package A)
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/27-PACKAGE-B-TRANCHE4-DESIGN.md`

## Frozen residual

```text
T3_CANDIDATE = sc900_bank_v8_length_rebalanced_t3.json
T3_CANDIDATE_SHA256 = d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b
T3_CANDIDATE_FINGERPRINT = 83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2
PRODUCTION_BANK = sc900_bank_v8_final.json
PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
STRICT_LONGEST_ON_T3_CANDIDATE = 256 / 449
UNIQUE_LONGEST_ON_T3_CANDIDATE = 256 / 425
DOMAIN_MAXIMUM = microsoft_security_solutions 98 / 163 = 60.12%
T3_EXTERNAL_REVIEW_STATE = IMPLEMENTED_UNMERGED
```

Package B completion target is unchanged:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
QUALITY_OVERRIDE = factual/pedagogical integrity wins
```

Unique-longest is the stricter global metric. A strict-longest count of 179 / 449 would still leave 179 / 425 ≈ 42.12% unique-longest if the unique denominator does not shrink. Dynamic unique closure needs about 87, 95, or 108 crossings depending on tie share. Do not engineer ties.

## Architecture

```text
SELECTED = CHAINED_T4
T4_SOURCE = sc900_bank_v8_length_rebalanced_t3.json
T4_TARGET = future T4 candidate filename, distinct from final/t1/t2/t3
T4_MANIFEST = t3 -> t4
PRODUCTION_DEFAULT = sc900_bank_v8_final.json
REGISTRY = {}
```

T4 live-state tests bind progress/session fixtures to the T3 candidate as source. They do not activate T1, T2, T3, or T4. Package C activation topology is out of scope.

Ordinary tranche implementation is not `final → T4`. Package A remains sequential. No implicit multi-hop live migration.

## Repair strategy

Primary tactic: `SEMANTIC_CONTRAST_FIRST`.

- T1 `CORRECT_ONLY` second-pass: prefer `DISTRACTOR_JOB_CONTRAST` when unused real product-job contrast remains.
- Fresh sentence-like items in the 21–40 gap band: prefer two-sided equivalent rebalancing when the correct choice is verbose and a distractor is underdeveloped.
- Do not default to T1 correct-only tightening.
- Do not globally mandate distractor growth from combined T2/T3 distractor-only 8 / 10 (`LOW_SAMPLE_SIZE = YES`).
- T1, T2, and T3 SKIP IDs stay excluded, including `sc900_mlc_q109` and the other six T3 reopened-then-skipped IDs.
- T3 non-crossing `EDIT`s are not a T4 second-pass class.
- Third or later edits are presumptively SKIP.

Permitted change surface remains version-1 wording-only A–D choices. All other question fields stay unchanged.

Record both max-distractor metric delta and per-option length deltas. Trigger extra semantic inspection for unusually large growth; do not impose a hard character cap.

## Queue

Primary bound: **64** IDs listed in `27-PACKAGE-B-TRANCHE4-DESIGN.md` and `26-PACKAGE-B-TRANCHE4-QUEUE.json`.

Composition: 10 T1 unused-distractor second-pass residuals + 54 never-reviewed TIER_A/B items. Domain quotas: security 24, compliance 15, entra 17, SCI 8. Multi-edit count: 0.

The list is a design candidate queue, not an approved `EDIT` set. Semantic review during implementation may `SKIP` any item. A smaller executed tranche is allowed if equivalence cannot be established.

T4 is not a Package B closure tranche. Expected reviewed crossing range is a scenario analysis: conservative 13–19, baseline 20–26, optimistic 26–32.

## Implementation boundary

Future implementation work ID:

```text
SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE4-001
```

Authorized implementation branch, when separately authorized:

```text
implementation/sc900-content-revision-equivalence-migration-B-tranche4-001
```

Exact implementation base SHA must be a commit that still contains the frozen T3 candidate identity. Do not start from this design branch. T3 merge is a predecessor gate, not an implied authorization.

T4 must stop for external review before merge. T4 must not start T5, Package C, registry activation, default-bank change, or EXE rebuild.

```text
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T4 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
T5_LIKELY_REQUIRED = YES
T6_PLAUSIBLY_REQUIRED = YES
PRODUCTION_ACTIVATION_READINESS = NOT_READY
T4_IMPLEMENTATION_AUTHORIZED = NO
T5_IMPLEMENTATION_AUTHORIZED = NO
PACKAGE_C_AUTHORIZED = NO
```
