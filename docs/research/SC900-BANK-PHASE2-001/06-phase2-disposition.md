# Phase 2 Disposition

WORK_ID = `SC900-BANK-PHASE2-001`
BASE_MAIN_SHA = `98ea25ee3303567ca60730853a82b4643931c173`
WORK_BRANCH = `implementation/sc900-reviewed-bank-phase2`
CORRECTED_EVIDENCE_HEAD = `414b9be4d7cc8d7fd97f6beaa52e353c16bb16e2`
BLUEPRINT = `SC-900 skills measured as of 2026-07-28`

## Terminal Result

`PHASE_2_STRUCTURALLY_ACCEPTED`

The terminal acceptance report is:

`content/sc900/phase2/phase2_acceptance_report.json`

The deterministic build/custody receipt is:

`content/sc900/phase2/phase2_build_receipt.json`

Acceptance summary:

- approved_count = 100;
- phase2_new_approved_count = 50;
- compiled_count = 100;
- pending_count = 0;
- withheld_count = 0;
- bank_validation_issues = [];
- quality_errors = [];
- source_inventory_errors = [];
- review_custody_errors = [];
- semantic_audit_errors = [];
- distinct_leaf_count = 58;
- semantic_family_count = 57;
- probe_suitability = 98 eligible / 2 train-only;
- cumulative domain allocation = 12 / 28 / 38 / 22.

The corrected compiled candidate SHA-256 is:

`f98dd302c6eed1d10a4d466aad5c83bfb70b6ad43d6341313cac2845ca6dfe23`

The default launch-bank SHA-256 remains:

`60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`

Phase 2 therefore accepts the cumulative 100-question reviewed candidate as a structurally valid, non-default research bank. It does not replace the launch bank.

## Reproducibility And Evidence Custody

The permanent Phase-2 builder reconstructs the candidate from the accepted Phase-1 store plus the five Phase-2 authored batches and five explicit review receipts.

The committed build receipt records:

- phase1_approved_base_count = 50;
- phase2_authored_count = 50;
- pending_before_approval_count = 50;
- approved_after_review_count = 100;
- withheld_after_review_count = 0;
- import_pending_ledger_complete = true;
- reviewed_phase2_items = 50;
- semantic_family_override_count = 12;
- build status = `REPRODUCIBLE`.

Each Phase-2 review receipt is bound to canonical reviewed question content using SHA-256. The semantic-family audit is separately hashed and is applied after content-review custody so family reassignment cannot silently rewrite the content that was reviewed.

The cumulative semantic-family audit reduced the earlier nominal count from 63 to 57 after conservative cross-phase reclassification. This correction includes same-leaf transfer and explicit cross-leaf transfer cases that had previously been assigned separate family IDs.

## Verification Evidence

Correction verification was executed by GitHub Actions run `34604050551` using the corrected worktree before publication of the final evidence commit.

Verified results:

- focused Phase-2 / quality / taxonomy / importer suite: 39/39 passed;
- full repository unittest discovery: 513/513 passed;
- `tools/lint_bank.py`: PASS;
- `tools/verify_installation.py`: PASS;
- repository quality checks (`ruff`, `black --check`, `mypy`): PASS;
- deterministic committed rebuild verification: `REPRODUCIBLE`.

The correction runner then removed transient correction helpers/workflows, committed the remaining verified Phase-2 state as:

`414b9be4d7cc8d7fd97f6beaa52e353c16bb16e2`

No separate GitHub check-run is attached directly to that commit SHA; the verification authority for this disposition is the successful one-shot run above plus the committed deterministic build receipt.

## Runtime Boundary

This package does not implement experimental runtime behavior.

It does not:

- activate RRC-1;
- change Smart Practice scheduling behavior;
- implement TRAIN/PROBE runtime exclusion guards;
- change learner-state semantics;
- replace the launch/default bank;
- mutate protected learner-history paths.

Phase 2 defines and hardens design-time contracts, schemas, validation, evidence custody, semantic-family isolation, and the future leakage-verification matrix. Runtime enforcement remains a later Gate-3-or-later implementation obligation.

## Gate-2 Boundary

`CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`

`IMPLEMENTATION_AUTHORIZED = NO`

Reaching 100 reviewed questions is a Phase-2 bank milestone, not evidence sufficient to pass or reopen Gate 2.

The corrected Phase-2 evidence materially advances the earlier N07 ontology challenge by providing a cumulative 100-item semantic-family audit, conservative family reassignment, fail-closed manifest semantics, and auditable family overrides. N07 is therefore best characterized as:

`N07 = DESIGN_ADVANCED_PENDING_RUNTIME_AND_LARGER_BANK_PROOF`

It is not positively closed because runtime exclusion enforcement has not been implemented or proven and the serious bank-sufficiency target has not yet been reached.

Material findings that remain unresolved include:

- N02 — no independent prospective SC-900 learner evidence yet;
- N06 — no prospective SC-900 outcome series for anomaly mining yet;
- N08 — bank sufficiency, runtime guards, RRC-1 service thresholds, allocation controls, and prior portability remain load-bearing assumptions.

Accordingly:

```text
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
```

## Next Milestone Boundary

The next reviewed-bank milestone is approximately 200 cumulative independently reviewed questions. That milestone should continue the same evidence-custody and semantic-family controls rather than relaxing them.

Before a serious Gate-2 reopening, the repository still requires at least:

- a sufficiently larger reviewed bank;
- a frozen TRAIN/PROBE partition manifest using the corrected semantic-family ontology;
- complete implementation-ready fail-closed semantics for every known question-material path;
- the corresponding future verification matrix;
- RRC-1 service fairness/starvation criteria;
- prior-decay enforcement tests;
- arm-allocation and selection-confound controls;
- resolution or evidence-based reclassification of remaining material noetic findings.

This disposition closes `SC900-BANK-PHASE2-001` only as a structurally accepted reviewed-bank/design package. It does not authorize runtime implementation and does not alter the existing Gate-2 terminal state.
