# SC-900 Reviewed Bank — Phase 3

Work package: `SC900-BANK-PHASE3-001`

Phase 3 expands the structurally accepted 100-question candidate bank toward exactly 200 cumulative approved questions. This directory is evidence/research scope only; it does not alter runtime selection, Smart Practice, learner history, RRC-1, or the launch/default bank.

## Task 1–2 contract

Before bulk Task-3 authoring, Phase 3 establishes:

- exactly 200 cumulative approved questions at Phase-3 structural closure;
- exactly 100 unique newly approved Phase-3 IDs;
- cumulative domain allocation `24 / 56 / 76 / 44`;
- cumulative objective allocation frozen in the Phase-3 handoff/implementation plan;
- all 58 blueprint leaves represented;
- zero pending or withheld records at structural closure;
- explicit review receipts for every approved question;
- exact content-bound SHA-256 custody for every new Phase-3 approval;
- exact per-question source URL joins against this Phase-3 source inventory;
- source retrieval evidence no older than the active blueprint effective date.

## Source rule

Only first-party Microsoft authority is admissible. Practice Assessment items, knowledge checks, exam dumps, recalled live items, and copied commercial practice banks are excluded.

`source_inventory.json` begins from the accepted Phase-2 Microsoft authority inventory refreshed on 2026-09-11. Task 3 must extend it whenever a new question cites an official URL that is not already represented with the correct objective/leaf scope.

## Review rule

Authoring and review are distinct passes. When the same model performs both stages, review custody must be described truthfully as a `separate adversarial review pass after authoring`, not as external human or third-party review.

For every new approved Phase-3 item, the review receipt must bind `reviewed_content_sha256` to the canonical reviewed question content using the existing Phase-2 custody semantics.

## Authority boundary

```text
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

Task 1–2 readiness is not Phase-3 structural acceptance. Tasks 3–8 remain required before any separate Gate-2 reopening review.
