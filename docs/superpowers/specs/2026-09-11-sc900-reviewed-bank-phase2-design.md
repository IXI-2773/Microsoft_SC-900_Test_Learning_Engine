# SC-900 Reviewed Bank Phase 2 Design

Status: APPROVED FOR EXECUTION by operator instruction in chat on 2026-09-11.

Base main: `98ea25ee3303567ca60730853a82b4643931c173`

Work package: `SC900-BANK-PHASE2-001`

Blueprint authority: Microsoft SC-900 skills measured as of **July 28, 2026**, as already frozen by Phase 1.

## 1. Purpose

Extend the accepted Phase-1 reviewed candidate bank from 50 to **100 approved SC-900 questions** without changing the default launch bank, Smart Practice policy, RRC-1 runtime logic, learner-history behavior, or any TRAIN/PROBE runtime guard.

Phase 2 reuses the existing provenance-aware ingestion, review, approval, semantic-family metadata, deterministic compilation, bank validation, and acceptance-report machinery. It also advances the blocked CAND-01R2 Gate-2 design work so a later Gate-2 reopening can judge a fully specified implementation-ready isolation contract.

The terminal target is:

`PHASE_2_STRUCTURALLY_ACCEPTED`

with:

- `APPROVED_QUESTIONS = 100`
- `CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`
- `IMPLEMENTATION_AUTHORIZED = NO`

Reaching 100 questions does not itself reopen or pass Gate 2. The serious reopening target remains approximately 200 reviewed questions unless later evidence justifies a different threshold.

## 2. Authority boundaries

The merged Gate-2 package remains authoritative. Gate 2 is a design/research assurance gate. It requires:

- a complete all-path leakage inventory;
- an implementation-ready TRAIN/PROBE exclusion contract;
- semantic-family partition controls;
- required guard semantics and fail-closed behavior;
- a future verification/test matrix;
- RRC-1 fairness/starvation definitions;
- prior-decay enforcement specification;
- resolution or explicit disposition of material noetic findings.

The absence of already-implemented runtime guards is not itself a Gate-2 failure. Gate 3 or later implementation work must actually implement those guards and prove every runtime path enforces them.

Phase 2 must not implement those runtime guards under false Gate-2 authority.

## 3. Bank growth target

Phase 1 accepted exactly 50 questions with domain allocation `6 / 14 / 19 / 11`. Phase 2 adds another 50 using the same increment, producing the cumulative 100-question distribution already anticipated by the Phase-1 design:

| Domain | Phase-1 count | Phase-2 increment | Cumulative 100 |
| --- | ---: | ---: | ---: |
| Security, compliance, and identity concepts | 6 | 6 | 12 |
| Microsoft Entra | 14 | 14 | 28 |
| Microsoft security solutions | 19 | 19 | 38 |
| Microsoft compliance solutions | 11 | 11 | 22 |
| **Total** | **50** | **50** | **100** |

Cumulative objective allocation is exactly double the accepted Phase-1 allocation:

- `security_compliance_concepts` — 6
- `identity_concepts` — 6
- `entra_identity_types_and_function` — 6
- `entra_authentication` — 8
- `entra_access_management` — 6
- `entra_identity_protection_governance` — 8
- `azure_infrastructure_security` — 12
- `azure_security_management` — 8
- `microsoft_sentinel` — 6
- `defender_xdr` — 12
- `service_trust_privacy` — 4
- `purview_compliance_management` — 4
- `purview_information_protection_lifecycle` — 8
- `purview_insider_risk_ediscovery_audit` — 6

A Microsoft blueprint change must trigger explicit source/taxonomy review rather than silent remapping.

## 4. Source and originality contract

Question factual authority remains:

1. the official Microsoft SC-900 study guide for scope and weighting;
2. official Microsoft Learn SC-900 learning paths/modules for teaching content;
3. official Microsoft product documentation where a Learn module is too high-level or ambiguous.

Every new question must be original. Do not copy or lightly paraphrase Microsoft Practice Assessment questions, module knowledge checks/assessments, recalled live-exam items, exam dumps, or unlicensed commercial-bank content.

Every approved item must retain official-source provenance, references, source retrieval date, objective/leaf mapping, source family, semantic family, stem style, probe suitability, and authoring-origin metadata under the existing canonical schema.

## 5. Review and acceptance contract

`IMPORT != APPROVAL` remains a hard invariant.

An item counts toward the cumulative 100 only when the canonical store records it as approved and an independent review receipt confirms all required checks.

Each new item must pass review for:

- current SC-900 scope;
- correct domain/objective/leaf mapping;
- factual support from official Microsoft sources;
- exactly one defensible correct answer for single-select questions;
- plausible but wrong distractors;
- supported explanation;
- original wording/scenario construction;
- duplicate and near-duplicate review;
- semantic-family review;
- future probe-suitability review;
- stale terminology/version-sensitivity review;
- absence of answer-clue leakage.

Pending, withheld, quarantined, malformed, or unresolved duplicate items do not count merely to meet the numeric target.

## 6. Semantic-family contract

Phase 2 strengthens semantic-family metadata into an implementation-ready design contract for future TRAIN/PROBE partitioning.

### 6.1 Identity layers

The design distinguishes:

- **exact-item identity** — the canonical question ID/fingerprint;
- **semantic-family identity** — items whose exposure could materially reveal another;
- **source-family identity** — sibling items derived from the same Microsoft source family;
- **scenario variants** — different surface stories testing the same proposition;
- **concept-equivalent variants** — distinct wording that still transfers the answer substantially;
- **shared-answer leakage** — repeated narrow cue-to-product mappings;
- **shared-rationale leakage** — one explanation reveals another held-out answer.

### 6.2 Conservative assignment

Items belong to the same semantic family when exposure to one could materially simplify another because of a shared core proposition, near-identical scenario/template, distinctive answer-option structure, source wording, narrow cue association, or explanation content.

Different wording alone never proves independence. When family membership is uncertain, the design fails closed: the item remains `needs_review` and cannot be assigned to a clean future PROBE partition until the uncertainty is resolved.

### 6.3 Review override

A reviewer may split or merge family assignments only with an explicit review receipt containing the affected item IDs, old/new family IDs, rationale, reviewer, and review date. The canonical manifest must make such overrides auditable.

## 7. TRAIN/PROBE manifest design

Phase 2 defines the future manifest but does not make runtime selectors consume it.

The design must specify fields for:

- immutable question ID;
- semantic family ID;
- source family ID;
- role: `TRAIN`, `PROBE`, or `UNASSIGNED`;
- partition epoch/version;
- review status prerequisite;
- probe-suitability prerequisite;
- assignment rationale/receipt;
- unknown-family/fail-closed state;
- source and blueprint version metadata.

Required invariants:

1. one semantic family cannot span TRAIN and PROBE;
2. an unknown or disputed family cannot enter PROBE;
3. pending/withheld questions cannot enter either experimental arm;
4. restore/import/rebuild operations must preserve immutable role/family metadata or fail closed;
5. exact-item withholding without family-level withholding cannot claim a clean probe.

## 8. Future leakage-guard verification matrix

Extend the existing all-path leakage inventory with a machine-readable or auditable matrix covering at minimum:

- normal selector;
- Smart Practice;
- due selection;
- weak selection;
- repair flow;
- follow-up flow;
- boss flow;
- stealth checkpoint flow;
- restore;
- full-bank restore;
- import/rebuild;
- prewarm/cache;
- render;
- history;
- analytics;
- export;
- developer/debug helpers;
- test fixtures;
- any newly discovered path capable of exposing question material or probe metadata.

For each path record:

- TRAIN material permitted?;
- PROBE material permitted?;
- probe metadata permitted?;
- intended future guard location;
- expected fail-closed behavior;
- future test obligation.

This is specification only in Phase 2.

## 9. RRC-1 fairness/starvation design

Define measurable service-risk metrics so Gate 2 can later judge whether RRC-1 starves review/coverage work. At minimum record definitions for:

- maximum service delay;
- overdue-service rate;
- starvation rate;
- repair queue age;
- review queue age;
- coverage debt;
- domain/objective service balance.

Do not fabricate authoritative thresholds. If the evidence does not justify a threshold, mark it as an unresolved parameter and state what observations would be required to calibrate it.

## 10. Historical-prior decay design

Specify future tests proving that the historical learner prior:

- influences cold start only as designed;
- decays as SC-900 learner evidence accumulates;
- cannot dominate indefinitely;
- transitions into learner-specific behavior;
- exposes a detectable failure when decay does not occur.

No learner-model runtime implementation is authorized in Phase 2.

## 11. Noetic/epistemic closure

Review the material unresolved noetic findings in `SC900-ENGINE-RDAF-CAND01-GATE2-001`. Each material item must be one of:

- resolved with evidence;
- reclassified non-material with explicit basis;
- still unresolved with a precise blocking statement.

Phase 2 must not hide unresolved findings merely to reach a milestone.

## 12. Candidate-bank layout

Follow Phase-1 conventions and keep Phase 2 auditable. The implementation should converge on:

- `content/sc900/phase2/README.md`
- `content/sc900/phase2/source_inventory.json`
- `content/sc900/phase2/batches/` — five new ten-question JSONL batches
- `content/sc900/phase2/reviews/` — item-level independent review receipts
- `content/sc900/phase2/store/` — canonical 100-question cumulative reviewed store or deterministic derived store as chosen by the implementation plan
- `content/sc900/phase2/compiled/sc900_phase2_reviewed_bank.json`
- `content/sc900/phase2/phase2_acceptance_report.json`
- `content/sc900/phase2/train_probe_manifest.schema.json` or equivalent design artifact
- `docs/research/SC900-BANK-PHASE2-001/` — source, coverage, semantic-family, leakage-matrix, fairness/prior/noetic, acceptance, and handoff receipts

Do not duplicate canonical data unnecessarily. Phase 2 may deterministically combine the accepted Phase-1 store with the new Phase-2 increment rather than copying mutable approval state by hand.

## 13. Candidate-bank isolation

The default launch bank remains `sc900_bank_v8_baseline.json` throughout Phase 2.

The Phase-2 bank is a non-default candidate artifact only. No partial batch may become the runtime default. No Smart Practice scheduler behavior, RRC-1 logic, TRAIN/PROBE runtime guard, readiness calculation, or protected learner-history path may change.

## 14. Phase-2 acceptance gate

Phase 2 is structurally complete only when fresh verification establishes:

1. exactly 100 approved cumulative questions;
2. exactly 50 newly approved Phase-2 questions;
3. cumulative domain allocation `12 / 28 / 38 / 22`;
4. cumulative objective allocation matches Section 3;
5. all approved items have valid official-source provenance and references;
6. every approved item has a reviewed blueprint leaf, semantic family, and probe-suitability classification;
7. no approved item is pending, withheld, quarantined, malformed, or an unresolved duplicate;
8. source-inventory validation passes;
9. candidate compilation is deterministic and idempotent;
10. generic bank validation passes without unresolved issues/warnings;
11. relevant ingestion/review/runtime regression tests remain green;
12. the default launch bank remains unchanged;
13. the protected baseline tag and recovery refs remain unchanged;
14. no runtime TRAIN/PROBE guard or RRC-1 implementation was introduced;
15. Gate-2 design-progress receipts accurately report unresolved blockers.

If fewer than 100 questions survive review, the correct terminal state is `PHASE_2_INCOMPLETE`; author/review replacements rather than lowering the gate.

## 15. Terminal research disposition

A successful Phase 2 records:

`PHASE_2_STRUCTURALLY_ACCEPTED`

but retains:

`CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`

`IMPLEMENTATION_AUTHORIZED = NO`

No automatic Gate-2 reopening or positive Gate-2 disposition occurs at 100 questions.

## 16. Phase-3 handoff

After acceptance, produce a bounded `SC900-BANK-PHASE3-001` handoff targeting approximately 200 reviewed questions. The handoff must identify remaining objective/family coverage gaps, unresolved leakage-contract items, fairness/starvation parameters, prior-decay test obligations, material noetic findings, and evidence still required before Gate-2 reopening.
