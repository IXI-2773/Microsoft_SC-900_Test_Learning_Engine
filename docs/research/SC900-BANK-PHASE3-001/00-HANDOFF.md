# SC900-BANK-PHASE3-001 — Handoff

HANDOFF_STATUS = `PREPARED_NOT_ACTIVE`
PREDECESSOR = `SC900-BANK-PHASE2-001`
PREDECESSOR_TERMINAL = `PHASE_2_STRUCTURALLY_ACCEPTED`
PREDECESSOR_TESTED_EVIDENCE_HEAD = `414b9be4d7cc8d7fd97f6beaa52e353c16bb16e2`
PREDECESSOR_CURRENT_PR = `#9`
BLUEPRINT = `SC-900 skills measured as of 2026-07-28`

## Activation rule

This handoff prepares Phase 3 but does not start it.

`SC900-BANK-PHASE3-001` MUST NOT become active until all of the following are true:

1. PR #9 has completed the final corrected adversarial review;
2. PR #9 has been merged without changing the accepted evidence semantics;
3. the Phase-2 work branch has been cleaned up according to repository policy;
4. the post-merge `main` SHA has been freshly verified;
5. both protected recovery refs are freshly verified unchanged;
6. the current Microsoft SC-900 study guide/scope authority is rechecked before new content authoring begins.

The Phase-3 implementation branch must be created from that freshly verified post-merge `main`, not from the current Phase-2 work branch and not from a stale hard-coded base SHA.

## Authority state carried forward

The Phase-2 terminal authority remains controlling at handoff time:

```text
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

Phase 3 is a reviewed-bank and design-assurance package. It does not authorize RRC-1 activation, runtime TRAIN/PROBE exclusion guards, experimental measurement execution, Smart Practice behavior changes, learner-model changes, or protected learner-history mutations.

A later Gate-2 reopening package must make any change to Gate-2 disposition. Reaching 200 reviewed questions alone does not pass Gate 2.

## Phase-3 primary goal

Expand the cumulative independently reviewed SC-900 candidate bank from 100 to exactly 200 approved questions while preserving the corrected Phase-2 evidence-custody, semantic-family, source-provenance, and fail-closed design contracts.

Phase-3 increment:

```text
NEW_APPROVED_QUESTIONS = 100
CUMULATIVE_APPROVED_QUESTIONS = 200
```

The default launch bank remains unchanged unless a separate explicitly authorized work package changes that authority.

## Frozen cumulative allocation target

Phase 2 closed at:

```text
security_compliance_identity = 12
microsoft_entra = 28
microsoft_security_solutions = 38
microsoft_compliance_solutions = 22
TOTAL = 100
```

Phase 3 adds the same blueprint-preserving increment:

```text
security_compliance_identity = +12
microsoft_entra = +28
microsoft_security_solutions = +38
microsoft_compliance_solutions = +22
TOTAL = +100
```

Successful cumulative target:

```text
security_compliance_identity = 24
microsoft_entra = 56
microsoft_security_solutions = 76
microsoft_compliance_solutions = 44
TOTAL = 200
```

Cumulative objective targets:

| Objective | Target at 200 |
| --- | ---: |
| security_compliance_concepts | 12 |
| identity_concepts | 12 |
| entra_identity_types_and_function | 12 |
| entra_authentication | 16 |
| entra_access_management | 12 |
| entra_identity_protection_governance | 16 |
| azure_infrastructure_security | 24 |
| azure_security_management | 16 |
| microsoft_sentinel | 12 |
| defender_xdr | 24 |
| service_trust_privacy | 8 |
| purview_compliance_management | 8 |
| purview_information_protection_lifecycle | 16 |
| purview_insider_risk_ediscovery_audit | 12 |

All 58 blueprint leaves must remain represented. Phase 3 must report leaf-level counts and concentration, but must not force artificial per-leaf equality that would distort the frozen domain/objective allocation.

## Content and provenance requirements

Each new Phase-3 question must preserve or strengthen the Phase-2 quality contract:

- immutable question ID;
- valid domain, objective, and blueprint leaf mapping;
- current Microsoft official-source provenance;
- exact source URL joined to the Phase-3 source inventory;
- source retrieval date and authority classification;
- one correct answer and plausible distractors;
- explanation/rationale that is supported by the cited source;
- explicit semantic-family candidate metadata;
- explicit source-family metadata;
- future probe-suitability disposition;
- no practice-assessment scraping or unauthorized assessment-content reuse;
- no unsupported product claims or stale terminology;
- no malformed distractors, giveaway wording, answer-position artifacts, or obvious clue leakage.

Source authority must be revalidated at Phase-3 start. If Microsoft changes the SC-900 blueprint after `2026-07-28`, Phase 3 must stop and reconcile the taxonomy/allocation authority before authoring against the changed scope.

## Review-custody requirements

Phase 3 inherits the corrected Phase-2 evidence chain as a hard minimum.

Required sequence:

```text
AUTHORED -> IMPORTED_PENDING -> EXPLICIT_REVIEW -> APPROVED_OR_WITHHELD -> COMPILED_IF_APPROVED
```

Import MUST NOT equal approval.

For all 100 new questions:

- importer acceptance must first produce pending state;
- each final approval/withhold decision must have an explicit review receipt;
- review receipts must bind to the exact canonical reviewed question content using the Phase-2 SHA-256 custody rule or a strictly stronger versioned rule;
- content mutation after review must invalidate the old receipt unless the mutation is explicitly outside the hashed custody surface and independently justified;
- cumulative store reconstruction must be deterministic from predecessor accepted evidence plus Phase-3 authored batches and review decisions;
- a committed build receipt must hash the relevant inputs and outputs and prove the 100-question pending-before-approval transition.

No generated store or compiled bank may be treated as primary evidence by itself.

## Semantic-family requirements

Phase 3 inherits the corrected Phase-2 conservative family ontology.

The starting cumulative audit contains 100 items and 57 semantic families. That count is evidence, not a quota.

Phase 3 MUST NOT optimize for a larger family count. Different wording, changed nouns, or changed scenarios do not prove independence.

The cumulative 200-item audit must consider at least:

- same blueprint proposition;
- same decision rule;
- paraphrase/near-duplicate relationships;
- scenario variants;
- concept-equivalent variants;
- shared correct-answer cues;
- shared rationale leakage;
- distinctive option-structure leakage;
- source-derived siblings;
- explicit cross-leaf transfer relationships;
- uncertain/disputed membership.

Uncertain family membership fails closed:

```text
family_state = needs_review | disputed | unknown
experimental_role = UNASSIGNED
PROBE = forbidden
```

Any family split or merge requires an auditable override receipt. The cumulative audit must re-evaluate prior Phase-1/Phase-2 family assignments when new Phase-3 items create transfer edges; prior assignments are not immutable if new evidence shows they were too permissive.

## TRAIN/PROBE partition-design milestone

Phase 3 should freeze a concrete design-time TRAIN/PROBE partition manifest over the reviewed candidate bank, but it must not wire that manifest into runtime selection.

The manifest must preserve the Phase-2 schema invariants and corrected validator parity, including:

- immutable question IDs;
- semantic-family IDs;
- source-family IDs;
- `TRAIN`, `PROBE`, or `UNASSIGNED` roles;
- partition epoch;
- promotion status;
- future probe suitability;
- family state;
- blueprint version;
- assignment rationale;
- assignment receipt.

Hard rules remain:

1. one semantic family may not span TRAIN and PROBE within one epoch;
2. TRAIN and PROBE both require approved content and resolved family state;
3. PROBE additionally requires probe suitability = eligible;
4. missing/malformed membership fails closed;
5. unknown/disputed family state cannot enter an experimental role;
6. partition-epoch changes create new auditable manifests rather than mutating historical assignments.

Phase 3 must not invent a TRAIN/PROBE ratio merely to fill a quota. The proposed arm allocation must be justified against measurement power, family structure, domain/objective balance, and contamination risk before it is frozen.

## All-path leakage contract carried forward

The future verification matrix from Phase 2 remains active and must be reconciled against the repository again during Phase 3.

At minimum the inventory must still account for:

- Smart Practice initial selection;
- prewarm/cache;
- normal practice builder;
- full-bank practice/restore;
- due and weak paths;
- twins/related-item injection;
- delayed recall/follow-up;
- memory ramp;
- wrong-answer memory;
- confusion-pair drills;
- streak rescue;
- misconception repair and its child injectors;
- boss rounds;
- stealth checkpoints;
- explicit future measurement runner;
- answer/explanation rendering;
- progress/history writes;
- analytics dashboards and exports;
- import/compiler/rebuild;
- restore/import/migration;
- developer/debug helpers;
- test fixtures;
- any new material path discovered before Phase-3 closure.

For every path, Phase 3 must preserve or improve the documented future guard location, allowed role, metadata custody rule, fail-closed behavior, and executable Gate-3 verification obligation.

Phase 3 still does not implement those runtime guards under the current authority state.

## RRC-1 fairness/starvation work carried forward

Phase 2 defined measurable service-risk quantities but intentionally did not invent thresholds.

Phase 3 must preserve reporting definitions for:

- maximum service delay by REPAIR / REVIEW / COVERAGE;
- overdue-service rate;
- starvation rate;
- REPAIR and REVIEW queue-age distributions;
- coverage debt by domain/objective;
- domain/objective service balance by arm and class.

Numeric pass/fail thresholds remain `UNRESOLVED_PARAMETER` unless Phase 3 obtains either:

1. prospective SC-900 service traces suitable for calibration; or
2. an independently justified policy/experimental requirement fixed before outcome inspection.

If neither basis exists, Phase 3 must carry the unresolved threshold blocker forward rather than manufacturing a number.

## Historical-prior decay work carried forward

The Phase-2 authority stages remain controlling unless a separately reviewed design changes them:

```text
SEED: fewer than 10 clean SC-900 held-out probe outcomes
ADVISORY: 10-29 clean SC-900 held-out probe outcomes
RETIRED: at least 30 clean 7-day probe outcomes, all four domains represented, at least 4 observations/domain
```

Phase 3 must preserve the future test obligations for clean-count filtering, exact stage boundaries, all-domain retirement, monotonicity, irreversible retirement, direct-evidence precedence, no side-channel resurrection, unobserved-outcome semantics, and duplicate custody.

Because runtime implementation is not authorized, Phase 3 may refine test vectors/specification and evidence requirements but must not claim runtime prior-decay enforcement exists.

## Allocation and confound controls

Before any later experimental execution, Phase 3 must freeze a design that makes the following observable and auditable:

- TRAIN versus PROBE family allocation;
- domain and objective composition by arm;
- question difficulty/quality differences by arm where measurable;
- source-family concentration by arm;
- semantic-family size/concentration by arm;
- selection-quality differences;
- time/order effects;
- repeated-exposure effects;
- one-learner/N-of-1 limitations;
- missing-observation handling;
- contaminated-observation exclusion.

The design must prevent an apparent scheduler effect from being silently explained by easier questions, stronger source coverage, different domain mix, repeated-family exposure, or unequal measurement opportunity.

Thresholds or allocation rules used as outcome gates must be frozen before inspecting the outcomes they judge.

## Noetic findings carried forward

Phase 3 begins with:

- N02 — `UNRESOLVED`: independent prospective SC-900 learner evidence does not yet exist;
- N06 — `UNRESOLVED`: no prospective SC-900 outcome series exists for anomaly mining;
- N07 — `DESIGN_ADVANCED_PENDING_RUNTIME_AND_LARGER_BANK_PROOF`;
- N08 — `UNRESOLVED`: bank sufficiency, runtime guards, RRC-1 thresholds, allocation controls, and prior portability remain load-bearing assumptions.

Bank growth may reduce the bank-sufficiency portion of N08 and strengthen N07 family evidence. It cannot truthfully close N02 or N06 without prospective observations.

Phase 3 must resolve, evidence-reclassify, or explicitly carry forward every material finding. Silence is not closure.

## Required Phase-3 artifacts

At minimum the active Phase-3 package should produce:

- package index/map;
- refreshed source/blueprint authority receipt;
- authored-question manifests/batches;
- cryptographically bound review receipts;
- cumulative source inventory;
- cumulative 200-item semantic-family audit and override receipts;
- cumulative deterministic store/build receipt;
- compiled non-default 200-question candidate bank;
- structural/quality acceptance report;
- coverage/concentration report at domain, objective, leaf, family, and source-family levels;
- design-time TRAIN/PROBE partition manifest plus assignment receipts;
- updated all-path leakage-verification matrix;
- RRC-1 fairness/starvation disposition;
- historical-prior decay/test-vector disposition;
- allocation/confound-control design receipt;
- updated noetic dispositions;
- terminal Phase-3 disposition.

Follow existing repository conventions where they are sound. Do not create duplicate evidence files merely to satisfy this list if an existing canonical artifact can be extended without weakening auditability.

## Verification requirements

Before `PHASE_3_STRUCTURALLY_ACCEPTED` may be claimed, verification must prove at least:

1. exactly 200 cumulative approved questions;
2. exactly 100 new Phase-3 approved IDs;
3. 0 pending and 0 withheld items counted as approved/compiled;
4. exact cumulative domain allocation 24 / 56 / 76 / 44;
5. exact cumulative objective targets listed above;
6. all 58 blueprint leaves represented and concentration reported;
7. every new question has valid current-source provenance joined to the inventory;
8. every new approval has valid content-bound review custody;
9. import-before-approval pending custody is complete;
10. cumulative semantic audit covers all 200 items with no unresolved item falsely treated as an independent family;
11. deterministic rebuild from predecessor accepted evidence plus Phase-3 primary inputs reproduces the committed store/compiled bank;
12. answer-position and other structural quality checks pass;
13. default launch bank/config remain unchanged;
14. no runtime RRC-1 or TRAIN/PROBE implementation has slipped into this bank/design package;
15. relevant focused tests pass;
16. full repository regression discovery passes;
17. bank lint, installation verification, and repository quality gates pass;
18. protected recovery refs remain unchanged;
19. final diff contains only authorized Phase-3 bank/design/test/tooling changes;
20. terminal disposition accurately preserves unresolved Gate-2/noetic blockers rather than inferring closure from bank size.

The verification run must execute against the final evidence state or an exact content-identical state, with any documentation-only post-verification commits clearly distinguished from the tested evidence head.

## Stop conditions

Stop and record the blocker instead of forcing acceptance if any of the following occurs:

- fewer than 200 legitimately approved cumulative questions can be produced;
- source authority materially changed and taxonomy reconciliation is incomplete;
- provenance is missing or cannot be joined exactly;
- review custody does not bind to the reviewed content;
- semantic duplication/transfer uncertainty is being hidden by family IDs;
- deterministic rebuild fails;
- domain/objective allocation drifts without explicit reviewed justification;
- pending/withheld content enters approval/compile counts;
- default launch-bank/runtime behavior changes without authority;
- protected recovery history would be mutated;
- a material noetic/Gate-2 finding is contradicted by new evidence and the package has not been revised to reflect it;
- Phase-3 evidence reveals that the approximately-200 target is still structurally inadequate for a serious Gate-2 reopening.

## Successful Phase-3 terminal target

If and only if the structural/evidence requirements are met, the Phase-3 package may close as:

```text
PHASE_3_STRUCTURALLY_ACCEPTED
APPROVED_QUESTIONS = 200
COMPILED_QUESTIONS = 200
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
```

That Gate-2 line is the default handoff authority. Phase 3 must not silently change it.

After Phase-3 structural acceptance, the next action is a separate adversarial Gate-2 reopening package, tentatively:

`SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001`

That package—not Phase 3 by itself—must determine whether the larger bank plus frozen design contracts are sufficient to change the Gate-2 terminal disposition or authorize any later implementation.

## Execution handoff

When activated, use one bounded Phase-3 work branch from freshly verified post-PR-#9 `main`, for example:

`implementation/sc900-reviewed-bank-phase3`

Do not recreate stale alias branches.

The executor must begin by re-reading:

- `docs/research/SC900-BANK-PHASE2-001/06-phase2-disposition.md`;
- `content/sc900/phase2/phase2_acceptance_report.json`;
- `content/sc900/phase2/phase2_build_receipt.json`;
- `content/sc900/phase2/semantic_family_audit.json`;
- `docs/research/SC900-BANK-PHASE2-001/02-semantic-family-and-train-probe-contract.md`;
- `docs/research/SC900-BANK-PHASE2-001/03-future-leakage-verification-matrix.md`;
- `docs/research/SC900-BANK-PHASE2-001/04-rrc1-fairness-and-prior-decay.md`;
- `docs/research/SC900-BANK-PHASE2-001/05-noetic-dispositions.md`;
- `config/certifications/sc900-2026.json`.

Then refresh external Microsoft scope/source authority before authoring new Phase-3 content.

This handoff carries authority and requirements only. It does not itself activate Phase 3, authorize runtime implementation, merge PR #9, or alter protected recovery state.
