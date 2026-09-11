# SC900-BANK-PHASE2-001 — Index

BASE_MAIN_SHA = `98ea25ee3303567ca60730853a82b4643931c173`
WORK_BRANCH = `implementation/sc900-reviewed-bank-phase2`
BLUEPRINT = `SC-900 skills measured as of 2026-07-28`

## Authority state

- Phase 1: `PHASE_1_STRUCTURALLY_ACCEPTED`
- Phase-2 target: 50 new / 100 cumulative independently reviewed questions
- CAND-01R2 Gate 2: `GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`
- `IMPLEMENTATION_AUTHORIZED = NO`

Gate 2 is a design/research assurance gate. Phase 2 advances implementation-ready TRAIN/PROBE semantics and the future verification matrix but does not implement runtime exclusion guards. Gate 3 or later must implement and prove runtime enforcement.

## Package map

- `01-source-and-coverage-receipt.md` — current Microsoft authority, blueprint, and cumulative allocation.
- `02-semantic-family-and-train-probe-contract.md` — family ontology, manifest semantics, and fail-closed rules.
- `03-future-leakage-verification-matrix.md` — every known question-material path and future guard/test obligation.
- `04-rrc1-fairness-and-prior-decay.md` — measurable service-risk definitions and future prior-decay tests.
- `05-noetic-dispositions.md` — Phase-2 effect on material N02–N08 findings.
- `06-phase2-disposition.md` — written only after final bank/test evidence exists.

## Successful terminal target

```text
PHASE_2_STRUCTURALLY_ACCEPTED
APPROVED_QUESTIONS = 100
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
```

Reaching 100 reviewed questions does not itself reopen Gate 2. The serious reopening target remains approximately 200 reviewed questions unless later evidence justifies a different threshold.
