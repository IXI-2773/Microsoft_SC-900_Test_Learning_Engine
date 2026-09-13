# SC-900 Reviewed Bank Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the structurally accepted SC-900 candidate bank from 100 to exactly 200 approved questions while preserving provenance, review custody, semantic-family isolation, deterministic rebuilds, and the Gate-2 no-runtime boundary.

**Architecture:** Phase 3 extends the Phase-2 evidence pipeline rather than replacing it. A Phase-3 validator freezes terminal structural invariants first; source inventory, authored batches, content-bound review receipts, semantic-family audit, deterministic cumulative rebuild, and a design-time TRAIN/PROBE partition manifest are then added behind those invariants. Runtime application code and the launch bank remain untouched.

**Tech Stack:** Python 3.11, `unittest`, existing ingestion/importer models, existing SC-900 taxonomy/config, JSON/JSONL evidence artifacts, GitHub Actions verification.

**Spec:** `docs/research/SC900-BANK-PHASE3-001/00-HANDOFF.md`

## Global Constraints

- Phase-3 base is the activation-verified `main` SHA recorded in `docs/research/SC900-BANK-PHASE3-001/01-ACTIVATION-RECEIPT.md`.
- Exactly 100 new Phase-3 approved questions and exactly 200 cumulative approved/compiled questions at terminal acceptance.
- Cumulative domain allocation must be exactly `24 / 56 / 76 / 44`.
- Cumulative objective allocation must be exactly: `12,12,12,16,12,16,24,16,12,24,8,8,16,12` in taxonomy objective order.
- All 58 blueprint leaves remain represented; report concentration without forcing artificial equality.
- Import is not approval: every new item enters pending before explicit review promotion.
- Every new approved item has exact official-source provenance joined to the source inventory and a content-bound SHA-256 review receipt.
- Semantic-family membership is conservative; uncertainty fails closed and no family may span TRAIN/PROBE within one partition epoch.
- The design-time TRAIN/PROBE manifest has no runtime consumer in Phase 3.
- Default launch bank/config, Smart Practice, RRC-1 runtime, learner state/history, and protected recovery refs remain unchanged.
- `CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE` and `IMPLEMENTATION_AUTHORIZED = NO` unless a later separate Gate-2 reopening package changes authority.

---

### Task 1: Phase-3 Structural Validator Contract

**Files:**
- Create: `tests/test_sc900_phase3.py`
- Create: `tools/validate_sc900_phase3.py`

**Interfaces:**
- Consumes: `ingestion.models.load_taxonomy`, Phase-2 question-quality/review helpers, cumulative questions, cumulative review receipts, explicit Phase-3 question IDs.
- Produces: `validate_phase3_set(questions, taxonomy, review_receipts, phase3_question_ids) -> dict[str, Any]` with terminal status and structural metrics.

- [ ] **Step 1: Write failing tests** that require module existence, 200/100 counts, exact domain/objective allocations, 58-leaf coverage, zero pending/withheld terminal state, duplicate-ID rejection, and exact Phase-3 ID cardinality/uniqueness.
- [ ] **Step 2: Run `python -m unittest tests.test_sc900_phase3 -v` and verify RED** because `tools.validate_sc900_phase3` does not yet exist.
- [ ] **Step 3: Implement the minimal Phase-3 validator** by reusing stable Phase-2 validation primitives rather than duplicating manifest semantics.
- [ ] **Step 4: Run `python -m unittest tests.test_sc900_phase3 tests.test_sc900_phase2_deep_review tests.test_sc900_phase2_receipt_portability -v` and verify GREEN.**
- [ ] **Step 5: Commit only the new validator/tests.**

### Task 2: Phase-3 Source and Review-Custody Skeleton

**Files:**
- Create: `content/sc900/phase3/README.md`
- Create: `content/sc900/phase3/source_inventory.json`
- Extend test coverage in: `tests/test_sc900_phase3.py`
- Extend validator: `tools/validate_sc900_phase3.py`

**Interfaces:**
- Consumes: current Microsoft study-guide authority, exact question source URLs, Phase-3 review receipts.
- Produces: exact source-inventory join errors and content-bound review-custody errors.

- [ ] **Step 1: Add failing tests** for missing source inventory join, stale/missing retrieval metadata, missing review receipt, bad review disposition/checks, and review-content hash mismatch.
- [ ] **Step 2: Run focused tests and verify RED.**
- [ ] **Step 3: Implement source/custody validation using Phase-2 canonical review hash semantics or a versioned stronger equivalent.**
- [ ] **Step 4: Seed the Phase-3 source inventory with the refreshed official Microsoft authority used for authoring.**
- [ ] **Step 5: Run focused tests and verify GREEN; commit.**

### Task 3: Author 100 New Questions in Reviewed Batches

**Files:**
- Create: `content/sc900/phase3/batches/batch-01.jsonl` through `batch-10.jsonl`
- Create: `content/sc900/phase3/reviews/batch-01-review.json` through `batch-10-review.json`
- Extend: `content/sc900/phase3/source_inventory.json`

**Interfaces:**
- Consumes: frozen Phase-3 allocation, current Microsoft official sources, validator/source-custody rules.
- Produces: 100 unique `sc900_p3_*` authored items and 100 explicit reviewed dispositions.

- [ ] **Step 1: Freeze a 100-item authoring allocation matching the exact +12/+28/+38/+22 domain increment and objective targets.**
- [ ] **Step 2: Author each batch from current official source material without assessment scraping or practice-exam reuse.**
- [ ] **Step 3: Run question-quality validation before review; reject or repair malformed items.**
- [ ] **Step 4: Perform a separate adversarial review pass after authoring; bind each receipt to canonical reviewed-content SHA-256.**
- [ ] **Step 5: Check displayed answer-position balance/streaks before cumulative build; rebalance only by choice-order changes that preserve choice IDs/text and semantic answer keys.**
- [ ] **Step 6: Run the Phase-3 authored-set validator and commit only accepted batches/reviews/source inventory.**

### Task 4: Cumulative 200-Item Semantic-Family Audit

**Files:**
- Create: `content/sc900/phase3/semantic_family_audit.json`
- Create/extend tests in: `tests/test_sc900_phase3.py`
- Create helper/build logic in: `tools/build_sc900_phase3.py`

**Interfaces:**
- Consumes: all 200 cumulative approved items plus predecessor semantic-family evidence.
- Produces: one conservative family decision per cumulative question and auditable merge/split overrides.

- [ ] **Step 1: Add failing tests** requiring audit coverage of all 200 IDs and fail-closed handling of missing/duplicate/unresolved family decisions.
- [ ] **Step 2: Re-audit same-leaf, shared-answer/rationale, scenario-equivalent, source-sibling, and cross-leaf transfer edges across all 200 items.**
- [ ] **Step 3: Apply family overrides only through explicit auditable decisions; never optimize for family count.**
- [ ] **Step 4: Run semantic-audit tests and commit.**

### Task 5: Deterministic Phase-3 Builder and Evidence Receipt

**Files:**
- Create: `tools/build_sc900_phase3.py`
- Create: `content/sc900/phase3/store/*.json`
- Create: `content/sc900/phase3/compiled/sc900_phase3_reviewed_bank.json`
- Create: `content/sc900/phase3/phase3_build_receipt.json`
- Create: `content/sc900/phase3/phase3_acceptance_report.json`

**Interfaces:**
- Consumes: accepted Phase-2 predecessor store, ten Phase-3 batches, ten review receipts, source inventory, semantic-family audit.
- Produces: deterministic 200-item store/compiled candidate, canonical POSIX-path input hashes, custody transition proof, acceptance report.

- [ ] **Step 1: Add tests that require 100 Phase-3 imports to be pending before approval.**
- [ ] **Step 2: Implement deterministic rebuild from predecessor primary evidence plus Phase-3 primary inputs.**
- [ ] **Step 3: Apply explicit review decisions and prove terminal 200 approved / 0 pending / 0 withheld.**
- [ ] **Step 4: Compile 200 and validate bank quality, allocation, provenance, review custody, semantic audit, default-bank immutability, and Gate-2 authority.**
- [ ] **Step 5: Write a canonical build receipt using POSIX repository paths and SHA-256 hashes; immediately verify a clean rebuild reproduces committed outputs.**
- [ ] **Step 6: Commit generated evidence only after reproducibility passes.**

### Task 6: Design-Time TRAIN/PROBE Partition Manifest

**Files:**
- Create: `content/sc900/phase3/train_probe_manifest.json`
- Reuse/freeze schema semantics from: `content/sc900/phase2/train_probe_manifest.schema.json`
- Extend tests/validator as needed.

**Interfaces:**
- Consumes: 200-item resolved semantic-family audit, approved state, probe suitability, blueprint balance.
- Produces: one versioned partition epoch with TRAIN/PROBE/UNASSIGNED roles and assignment receipts; no runtime consumer.

- [ ] **Step 1: Add failing tests for family split, nonapproved roles, unresolved family roles, stale/missing epoch, malformed receipts, and allocation-report completeness.**
- [ ] **Step 2: Define a justified partition allocation from family structure and measurement balance rather than an arbitrary quota.**
- [ ] **Step 3: Generate/freeze the design-time manifest and assignment receipts.**
- [ ] **Step 4: Validate schema/Python parity and semantic-family isolation; commit.**

### Task 7: Gate-2 Design-Assurance Carry-Forward

**Files:**
- Create Phase-3 research receipts under `docs/research/SC900-BANK-PHASE3-001/` for leakage reconciliation, RRC-1 fairness/starvation, prior decay, allocation/confound controls, noetic dispositions, and terminal disposition.

**Interfaces:**
- Consumes: Phase-2 design contracts plus Phase-3 200-item evidence.
- Produces: implementation-ready design evidence for a later separate Gate-2 reopening review.

- [ ] **Step 1: Reconcile every known question-material path against the Phase-2 all-path leakage inventory and record additions/changes.**
- [ ] **Step 2: Preserve measurable RRC-1 fairness/starvation definitions; do not invent empirical thresholds without authority.**
- [ ] **Step 3: Freeze prior-decay test obligations and arm-allocation/selection-confound controls.**
- [ ] **Step 4: Reassess N02/N06/N07/N08 using only new evidence actually produced in Phase 3.**
- [ ] **Step 5: Write terminal Phase-3 disposition only after final verification.**

### Task 8: Final Verification and Gate-2 Reopening Handoff

**Files:**
- Finalize: `docs/research/SC900-BANK-PHASE3-001/*`
- Prepare only after acceptance: `docs/research/SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001/00-HANDOFF.md`

**Interfaces:**
- Consumes: final Phase-3 branch and all evidence.
- Produces: independently reviewable Phase-3 closure; no automatic Gate-2 state change.

- [ ] **Step 1: Run focused Phase-3/Phase-2/ingestion/bank tests.**
- [ ] **Step 2: Run `python -m unittest discover -s tests -v`.**
- [ ] **Step 3: Run bank lint, installation verification, ruff, black check, and mypy.**
- [ ] **Step 4: Verify the launch/default bank and runtime application files are unchanged.**
- [ ] **Step 5: Verify protected recovery refs/tag unchanged.**
- [ ] **Step 6: Deep-review final diff for hidden evidence/contract gaps before opening/merging a Phase-3 PR.**
- [ ] **Step 7: If structurally accepted, preserve `GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE` and `IMPLEMENTATION_AUTHORIZED = NO`; prepare the separate Gate-2 reopening handoff for a later adversarial decision.**
