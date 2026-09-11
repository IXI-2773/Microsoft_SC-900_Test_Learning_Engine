# SC-900 Reviewed Bank — Phase 1

This package builds the first serious reviewed SC-900 candidate bank while preserving the existing launch bank and learning-engine behavior.

## Authority and originality

- Blueprint authority: Microsoft SC-900 skills measured as of **July 28, 2026**.
- Factual sources: Microsoft Learn and official Microsoft product documentation.
- Questions must be newly authored from those sources.
- Do **not** copy or lightly paraphrase Microsoft Practice Assessment questions, Learn module-assessment questions, recalled live-exam items, exam dumps, or unlicensed commercial-bank items.
- `source_inventory.json` records the official source set used for scope and factual verification.

## Phase-1 target

Exactly **50 approved** questions are required.

Domain allocation:

| Domain | Count |
| --- | ---: |
| Security, compliance, and identity concepts | 6 |
| Microsoft Entra | 14 |
| Microsoft security solutions | 19 |
| Microsoft compliance solutions | 11 |

Objective allocation is frozen in the approved design and enforced by `tools/validate_sc900_phase1.py`.

## Review invariant

`IMPORT != APPROVAL`

Importing a question only places it into the canonical review store with `promotion_status = pending`. A question enters the compiled candidate bank only after an explicit independent `approved` decision.

Pending, withheld, quarantined, malformed, or unresolved duplicate records do not count toward the 50-question target.

## Semantic families

Every candidate carries `semantic_family_id`. Items belong to the same family when exposure to one could materially reveal another because they share a core proposition, near-identical scenario/template, distinctive answer-option structure, near-identical source wording, or an unusually narrow cue association.

Family labeling is conservative. Different wording does not prove independence. Exact duplicate detection is not a substitute for semantic-family review.

Phase 1 records future TRAIN/PROBE suitability but does **not** implement a TRAIN/PROBE runtime partition.

## Candidate-bank isolation

`sc900_bank_v8_baseline.json` remains the default launch bank throughout Phase 1.

The reviewed Phase-1 bank is compiled only to:

`content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json`

Promotion to the default runtime bank is a separate later decision.

## Workflow

Import a batch:

```bash
python tools/import_sc900_content.py content/sc900/phase1/batches/batch-01.jsonl \
  --store content/sc900/phase1/store
```

Record an independent review decision:

```bash
python tools/review_sc900_content.py decide approved <question-id> \
  --store content/sc900/phase1/store \
  --actor phase1-independent-review
```

Inspect counts and compile approved content:

```bash
python tools/review_sc900_content.py report \
  --store content/sc900/phase1/store \
  --compile content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json
```

Run the Phase-1 acceptance gate:

```bash
python tools/validate_sc900_phase1.py \
  --store content/sc900/phase1/store \
  --compiled content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json \
  --reviews content/sc900/phase1/reviews \
  --source-inventory content/sc900/phase1/source_inventory.json \
  --report content/sc900/phase1/phase1_acceptance_report.json
```

The validator exits successfully only when the complete Phase-1 structural gate is satisfied. Before that point the correct state is `PHASE_1_INCOMPLETE`.

## Gate-2 boundary

Completing this 50-question bank does not reverse the existing research disposition:

`GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`

Phase 1 validates the taxonomy, source provenance, authoring/review workflow, semantic-family labeling, and candidate compilation. The serious comparison target remains approximately 200 reviewed questions unless a later research receipt justifies otherwise.
