# SC-900 Reviewed Bank — Phase 2

Work package: `SC900-BANK-PHASE2-001`

Phase 2 extends the accepted reviewed candidate bank from 50 to **100 approved questions** while leaving the launch bank and runtime learning policy unchanged.

## Authority

- Blueprint authority: Microsoft SC-900 study guide, skills measured as of **July 28, 2026**.
- Factual authority: official Microsoft Learn and Microsoft product documentation.
- Questions must be newly authored from those sources.
- Practice Assessment items, Learn module-assessment/knowledge-check questions, recalled live-exam items, exam dumps, and unlicensed commercial-bank content are excluded.

The current blueprint remains:

| Domain | Weight | Cumulative target |
| --- | ---: | ---: |
| Security, compliance, and identity concepts | 10–15% | 12 |
| Microsoft Entra | 25–30% | 28 |
| Microsoft security solutions | 35–40% | 38 |
| Microsoft compliance solutions | 20–25% | 22 |

Phase 2 adds exactly 50 newly reviewed questions in the same incremental distribution as Phase 1: `6 / 14 / 19 / 11`.

## Review invariant

`IMPORT != APPROVAL`

Import places a question into the canonical review store in pending state. A question counts toward the cumulative 100 only after an explicit independent `approved` decision with all required review checks recorded.

Pending, withheld, quarantined, malformed, or unresolved duplicate records do not count toward the Phase-2 target.

## Semantic-family invariant

`EXACT_ITEM_WITHHELD != CLEAN_PROBE`

Every candidate retains `semantic_family_id` and `source_family_id`. A semantic family groups items when exposure to one could materially simplify another because of a shared core proposition, scenario/template, narrow cue association, answer structure, source wording, or rationale.

Different wording does not prove independence. Unknown or disputed family membership fails closed to `needs_review`/`UNASSIGNED` for future partition design.

A semantic family may not be split across future TRAIN and PROBE roles.

## TRAIN/PROBE boundary

`train_probe_manifest.schema.json` is a **design-only** Phase-2 artifact. No runtime selector, scheduler, repair path, renderer, history path, analytics path, restore path, importer, or exporter is authorized to consume it in Phase 2.

Gate 2 specifies the implementation-ready contract and future verification matrix. Gate 3 or later must implement and prove runtime enforcement.

## Candidate-bank isolation

The runtime default remains:

`sc900_bank_v8_baseline.json`

The Phase-2 compiled candidate bank is written only to:

`content/sc900/phase2/compiled/sc900_phase2_reviewed_bank.json`

Phase 2 does not implement RRC-1, TRAIN/PROBE runtime guards, historical-prior decay, Smart Practice changes, readiness changes, or learner-history changes.

## Terminal target

Successful structural acceptance requires:

```text
PHASE_2_STRUCTURALLY_ACCEPTED
APPROVED_QUESTIONS = 100
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
```

Reaching 100 reviewed questions does not itself reopen Gate 2. The serious reopening target remains approximately 200 reviewed questions unless later evidence changes that requirement.
