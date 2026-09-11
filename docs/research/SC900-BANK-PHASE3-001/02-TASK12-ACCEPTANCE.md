# SC900-BANK-PHASE3-001 — Task 1–2 Acceptance Receipt

TASK_1_STATUS = `ACCEPTED`
TASK_2_STATUS = `ACCEPTED`
TASK_3_STATUS = `AUTHORIZED_TO_PROCEED`
WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TESTED_EVIDENCE_HEAD = `8f194252dd18bc4aabbc7aa76da0a9da90fbcb61`

## Scope accepted

Task 1 establishes the Phase-3 structural validator contract before bulk content authoring. The published contract fails closed on:

- cumulative approved count other than 200;
- Phase-3 new-approved count other than exactly 100 unique IDs;
- duplicate approved IDs;
- pending or withheld cumulative content;
- cumulative domain allocation other than `24 / 56 / 76 / 44`;
- cumulative objective allocation drift from the frozen Phase-3 plan;
- cumulative blueprint coverage below all 58 leaves;
- missing, incomplete, or non-approved review authority.

Task 2 establishes the Phase-3 provenance/review-custody skeleton before Task-3 authoring. It requires:

- exact per-question source URL joins against the Phase-3 source inventory;
- source retrieval evidence no older than the active blueprint effective date;
- an explicit review receipt for every approved cumulative question;
- canonical `reviewed_content_sha256` binding for every new Phase-3 approval;
- truthful review-method custody as a separate adversarial review pass after authoring.

The initial Phase-3 source inventory is the accepted Phase-2 first-party Microsoft inventory refreshed on `2026-09-11`. Task 3 must extend it whenever a new question uses an official source URL not already represented with the correct objective/leaf scope.

## TDD evidence

RED was proved before the Phase-3 validator existed.

- RED test commit: `5e2658d399eff1e4cebb7e90b8aceee3ae3fbb6e`
- RED Actions run: `34623172362`
- expected failure: `tools.validate_sc900_phase3 must exist`
- disposition: `EXPECTED_RED_CONFIRMED`

The accepted published Task-1/2 evidence head is:

`8f194252dd18bc4aabbc7aa76da0a9da90fbcb61`

GREEN verification:

- Actions run: `34623675516`
- result: `SUCCESS`
- focused suite: **24/24 passed**
  - 13 Phase-3 structural/provenance/custody tests;
  - 10 Phase-2 deep-review regression tests;
  - 1 Phase-2 receipt-portability regression test.
- Python compile: PASS
- bounded publication scope: PASS

An earlier GREEN worker run `34623590364` had already passed compilation and all focused tests but failed its final scope-check command because the checkout was shallow and did not contain the comparison base. No code/test assertion failed in that run. The retry used full Git history and proved the same four-file scope successfully.

## Published Task-1/2 file scope

Relative to the pre-Task-1/2 Phase-3 head `a6784f92d0ffced42e92967930651226b5e27ff0`, the tested evidence changes exactly:

- `tests/test_sc900_phase3.py`
- `tools/validate_sc900_phase3.py`
- `content/sc900/phase3/README.md`
- `content/sc900/phase3/source_inventory.json`

No runtime application file, launch/default bank, Smart Practice path, learner-state/history path, or RRC-1 runtime file is part of this accepted scope.

## Main cleanup proof

The temporary verification workflows self-removed. Current `main` after the final retry cleanup is:

`f4fa20a4db31410fdbf63320a1c01ca77e4afa45`

Its tree remains exactly:

`aabd88b379fd118619460955e986b5f0579228a4`

which is the Phase-3 activation-base content tree. Temporary runner history therefore caused no persistent `main` content mutation.

## Protected authority recheck

Fresh verification after Task-1/2 publication preserved:

- `recovery/publish-exact-history/sc900-v8-20260910` = `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`
- `recovery/publish-sc900-v8-exact-history` = `bbc3bd900b73bde89151dc51706ad62fc69e8196`
- `sc900-v8.0.0-baseline` tag object = `9c80be5b20e652dc2eb86621dfdf7c32baa06528`

## Authority boundary

Task 1–2 acceptance does not change Gate-2 or runtime authority:

```text
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

Task 3 may now proceed with the 100-question authoring/review increment. This receipt does not authorize Phase-3 structural acceptance, runtime TRAIN/PROBE enforcement, RRC-1 implementation, or a Gate-2 pass.
