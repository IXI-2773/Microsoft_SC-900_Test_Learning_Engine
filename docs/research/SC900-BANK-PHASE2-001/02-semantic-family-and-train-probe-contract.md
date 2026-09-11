# Semantic-Family and TRAIN/PROBE Design Contract

WORK_ID = `SC900-BANK-PHASE2-001`
STATUS = `DESIGN_ONLY_NO_RUNTIME_CONSUMER`

## Purpose

Exact-item withholding is insufficient for a clean held-out probe. Phase 2 therefore freezes a family-level ontology and a manifest contract that later Gate-3 implementation can enforce.

This document specifies semantics only. It does not authorize runtime selection changes.

## Identity layers

### Exact-item identity

The immutable canonical `question_id` identifies one authored question record. Different IDs do not imply independent learning content.

### Semantic-family identity

`semantic_family_id` groups items when exposure to one could materially simplify another. Family membership is conservative and may arise from any of the following:

- the same core proposition or distinction;
- a near-identical scenario/template with changed nouns or numbers;
- a product-to-capability mapping whose answer becomes obvious after sibling exposure;
- a distinctive answer-option structure or cue;
- near-identical official-source wording;
- an explanation/rationale that reveals the sibling answer;
- scenario variants that test the same decision rule;
- concept-equivalent variants that differ linguistically but not educationally.

### Source-family identity

`source_family_id` groups items derived from the same official source family. Source siblings are not automatically one semantic family, but source proximity is a required leakage-review signal.

## Family assignment rule

Different wording never proves independence.

When reviewers are uncertain whether two items belong to the same semantic family, the uncertainty fails closed:

```text
family_state = needs_review | disputed | unknown
future role = UNASSIGNED
PROBE = forbidden
```

A later reviewer may split or merge family assignments only through an auditable receipt containing:

- affected question IDs;
- prior family IDs;
- resulting family IDs;
- override type (`family_merge` or `family_split`);
- rationale;
- reviewer;
- reviewed timestamp.

## TRAIN/PROBE manifest

Schema:

`content/sc900/phase2/train_probe_manifest.schema.json`

Minimum item fields:

- immutable `question_id`;
- `semantic_family_id`;
- `source_family_id`;
- role: `TRAIN`, `PROBE`, or `UNASSIGNED`;
- `partition_epoch` at manifest level;
- `promotion_status`;
- `future_probe_suitability`;
- `family_state`;
- blueprint version;
- assignment rationale;
- assignment receipt.

## Hard invariants

1. A semantic family MUST NOT span TRAIN and PROBE within an epoch.
2. PROBE requires `promotion_status = approved`.
3. PROBE requires `future_probe_suitability = eligible`.
4. PROBE requires `family_state = resolved`.
5. Pending or withheld content cannot enter an experimental role.
6. Unknown/disputed family membership cannot be silently treated as independent.
7. Exact-item withholding without semantic-family withholding cannot support a `CLEAN HELD-OUT` claim.
8. Restore/import/rebuild operations must preserve immutable family/role metadata or fail closed in later implementation.
9. A partition-epoch change requires a new auditable manifest; it must not silently mutate the historical assignment used to judge earlier observations.

## Exposure boundary

A future TRAIN path may expose TRAIN material according to the experiment policy. A future PROBE path may expose PROBE material only during the defined measurement event and must prevent the normal training system from exposing the same family before that event.

The exclusion boundary applies to content and derived answer-revealing metadata, not merely to question IDs. Stems, choices, correct answers, explanations, semantic-family hints, and sufficiently revealing analytics/export fields are all within the custody model.

## Phase-2 implementation boundary

No runtime selector, Smart Practice path, repair/follow-up path, game injection path, restore path, cache, render path, history writer, analytics/export path, or importer/compiler is changed to consume this contract in Phase 2.

Gate 2 freezes the contract. Gate 3 or later must implement one shared fail-closed eligibility boundary and prove every runtime path respects it.
