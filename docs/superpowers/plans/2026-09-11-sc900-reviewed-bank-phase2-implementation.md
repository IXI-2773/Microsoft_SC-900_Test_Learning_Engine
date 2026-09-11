# SC-900 Reviewed Bank Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the accepted 50-question SC-900 reviewed candidate bank to 100 approved questions and freeze the next layer of Gate-2 TRAIN/PROBE design contracts without changing runtime policy.

**Architecture:** Reuse the accepted Phase-1 ingestion/review/compiler path and treat Phase 1 as immutable input evidence. Phase 2 adds five new reviewed ten-question batches, validates the cumulative 100-question set against doubled blueprint allocations, compiles a separate non-default candidate bank, and records design-only semantic-family/TRAIN-PROBE/leakage/fairness/prior/noetic contracts. Repository-native CI/Actions may generate and verify derived artifacts, but the final tree must not retain a temporary worker.

**Tech Stack:** Python 3.11, standard-library `json`/`unittest`, existing `ingestion` package and review/compiler tools, JSON/JSONL artifacts, GitHub Actions for repository-native execution where needed, official Microsoft Learn/product documentation.

**Spec:** `docs/superpowers/specs/2026-09-11-sc900-reviewed-bank-phase2-design.md`

## Global Constraints

- Base `main`: `98ea25ee3303567ca60730853a82b4643931c173`.
- Work branch: `implementation/sc900-reviewed-bank-phase2`.
- Work package: `SC900-BANK-PHASE2-001`.
- Blueprint authority remains the July 28, 2026 SC-900 taxonomy already frozen by Phase 1.
- Phase-2 cumulative target: exactly **100 approved questions**, exactly **50 new Phase-2 approvals**.
- Cumulative domain allocation: exactly `12 / 28 / 38 / 22`.
- Cumulative objective allocation: `6/6`, `6/8/6/8`, `12/8/6/12`, `4/4/8/6` in taxonomy order.
- Preserve `IMPORT != APPROVAL` and existing `promotion_status` / review-decision authority.
- Questions must be original from official Microsoft factual sources; no Practice Assessment, module-assessment/knowledge-check, recalled live-exam, dump, or unlicensed commercial-bank content.
- Every approved item must retain official provenance, blueprint leaf, source family, semantic family, stem style, future probe suitability, authoring origin, explanation, and references.
- Same-semantic-family items may never be split across future TRAIN and PROBE; uncertain family membership fails closed to `needs_review`/`UNASSIGNED` in design artifacts.
- Default launch bank `sc900_bank_v8_baseline.json` must not change.
- Do not implement RRC-1, TRAIN/PROBE runtime guards, learner-prior runtime decay, Smart Practice redesign, or learner-history mutation.
- Gate-2 terminal state remains `GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`; `IMPLEMENTATION_AUTHORIZED = NO`.
- Recovery refs and baseline tag are immutable.
- No completion claim without fresh tests, generated acceptance evidence, final diff inspection, and protected-ref verification.

---

## File Structure

- `tools/validate_sc900_phase2.py` — cumulative 100-question structural/quality acceptance validator; reuses Phase-1 source/question validation.
- `tests/test_sc900_phase2.py` — TDD coverage for cumulative counts, new-item counts, manifest fail-closed invariants, and design-matrix shape.
- `content/sc900/phase2/README.md` — Phase-2 authoring/review and design-contract rules.
- `content/sc900/phase2/source_inventory.json` — official-source inventory used by the additional 50 items; must still cover all current objectives/leaves relied upon by Phase 2.
- `content/sc900/phase2/batches/batch-01.jsonl` ... `batch-05.jsonl` — 50 original new question records.
- `content/sc900/phase2/reviews/batch-01-review.json` ... `batch-05-review.json` — independent review receipts for the 50 new items.
- `content/sc900/phase2/store/questions.json` — cumulative canonical 100-question store generated deterministically from accepted Phase 1 plus Phase-2 imports/decisions.
- `content/sc900/phase2/store/review_decisions.json` — cumulative explicit decision ledger or deterministic equivalent produced through the existing review tool.
- `content/sc900/phase2/compiled/sc900_phase2_reviewed_bank.json` — non-default compiled 100-question candidate bank.
- `content/sc900/phase2/phase2_acceptance_report.json` — machine-readable terminal report.
- `content/sc900/phase2/train_probe_manifest.schema.json` — design-only manifest schema; no runtime consumer.
- `docs/research/SC900-BANK-PHASE2-001/00-INDEX.md` — package map/status.
- `docs/research/SC900-BANK-PHASE2-001/01-source-and-coverage-receipt.md` — source and blueprint coverage.
- `docs/research/SC900-BANK-PHASE2-001/02-semantic-family-and-train-probe-contract.md` — implementation-ready family/partition semantics.
- `docs/research/SC900-BANK-PHASE2-001/03-future-leakage-verification-matrix.md` — all-path future guard/test obligations.
- `docs/research/SC900-BANK-PHASE2-001/04-rrc1-fairness-and-prior-decay.md` — fairness/starvation metrics and prior-decay future tests.
- `docs/research/SC900-BANK-PHASE2-001/05-noetic-dispositions.md` — material noetic closure/status.
- `docs/research/SC900-BANK-PHASE2-001/06-phase2-disposition.md` — terminal Phase-2 disposition and Phase-3 handoff.

Derived store/compiled/report artifacts must be generated by the repository tooling rather than hand-edited after generation.

---

### Task 1: Add the cumulative Phase-2 acceptance and TRAIN/PROBE design validator

**Files:**
- Create: `tools/validate_sc900_phase2.py`
- Create: `tests/test_sc900_phase2.py`
- Create: `content/sc900/phase2/train_probe_manifest.schema.json`

**Interfaces:**
- Consumes: Phase-1/Phase-2 canonical question rows, taxonomy, Phase-2 review receipts, source inventory, compiled candidate bank, design-only manifest/matrix artifacts.
- Produces: `validate_phase2_set(...) -> dict[str, Any]` and CLI acceptance report with terminal status `PHASE_2_STRUCTURALLY_ACCEPTED` or `PHASE_2_INCOMPLETE`.
- Reuses: `phase1_review_status`, `validate_phase1_question`, `validate_source_inventory`, and generic `validate_bank` rather than duplicating factual/source validation logic.

- [ ] **Step 1: Write failing cumulative-count tests**

Create synthetic approved rows by reusing the Phase-1 test helpers and duplicating the allocation with new IDs/families. Assert:

```python
result = validate_phase2_set(questions, taxonomy, reviews, phase2_ids)
self.assertEqual("PHASE_2_STRUCTURALLY_ACCEPTED", result["status"])
self.assertEqual(100, result["approved_count"])
self.assertEqual(50, result["phase2_new_approved_count"])
self.assertEqual(EXPECTED_PHASE2_DOMAIN_COUNTS, result["domain_counts"])
self.assertEqual(EXPECTED_PHASE2_OBJECTIVE_COUNTS, result["objective_counts"])
self.assertEqual([], result["quality_errors"])
```

Also prove 99 approved, 49 new approvals, duplicate IDs, missing review receipts, wrong domain allocation, and wrong objective allocation produce `PHASE_2_INCOMPLETE` with explicit reason codes.

- [ ] **Step 2: Write failing semantic-family/manifest tests**

Define manifest validation helpers in `tools/validate_sc900_phase2.py` and tests proving:

- one `semantic_family_id` cannot contain both `TRAIN` and `PROBE`;
- `PROBE` requires `promotion_status == approved` and `future_probe_suitability == eligible`;
- missing/disputed family fails closed to `UNASSIGNED`/error;
- duplicate immutable question IDs fail;
- unknown role fails;
- manifest schema/version and partition epoch are required.

These tests validate design artifacts only; they must not hook runtime selectors.

- [ ] **Step 3: Run tests and prove RED**

```bash
python -m unittest tests.test_sc900_phase2 -v
```

Expected: FAIL because the Phase-2 validator/module does not yet exist.

- [ ] **Step 4: Implement the minimal validator**

Use constants:

```python
EXPECTED_PHASE2_DOMAIN_COUNTS = {
    "security_compliance_identity": 12,
    "microsoft_entra": 28,
    "microsoft_security_solutions": 38,
    "microsoft_compliance_solutions": 22,
}
EXPECTED_PHASE2_OBJECTIVE_COUNTS = {
    "security_compliance_concepts": 6,
    "identity_concepts": 6,
    "entra_identity_types_and_function": 6,
    "entra_authentication": 8,
    "entra_access_management": 6,
    "entra_identity_protection_governance": 8,
    "azure_infrastructure_security": 12,
    "azure_security_management": 8,
    "microsoft_sentinel": 6,
    "defender_xdr": 12,
    "service_trust_privacy": 4,
    "purview_compliance_management": 4,
    "purview_information_protection_lifecycle": 8,
    "purview_insider_risk_ediscovery_audit": 6,
}
```

`validate_phase2_set` must require exactly 100 approved rows and exactly 50 approved IDs from the Phase-2 increment. It should call the existing Phase-1 quality validator for every approved row because the metadata/source contract remains valid.

- [ ] **Step 5: Add design-only JSON Schema**

`train_probe_manifest.schema.json` must describe immutable item/family/source-family IDs, role enum `TRAIN|PROBE|UNASSIGNED`, partition epoch, review status, probe suitability, assignment rationale/receipt, blueprint version, and fail-closed family state. Add an explicit `$comment` that no Phase-2 runtime path consumes this schema.

- [ ] **Step 6: Run focused tests GREEN**

```bash
python -m unittest tests.test_sc900_phase2 tests.test_sc900_bank_quality tests.test_sc900_taxonomy -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add tools/validate_sc900_phase2.py tests/test_sc900_phase2.py content/sc900/phase2/train_probe_manifest.schema.json
git commit -m "feat: add SC-900 Phase 2 acceptance contract"
```

---

### Task 2: Freeze Phase-2 source, semantic-family, and Gate-2 design receipts

**Files:**
- Create: `content/sc900/phase2/README.md`
- Create: `content/sc900/phase2/source_inventory.json`
- Create: `docs/research/SC900-BANK-PHASE2-001/00-INDEX.md`
- Create: `docs/research/SC900-BANK-PHASE2-001/01-source-and-coverage-receipt.md`
- Create: `docs/research/SC900-BANK-PHASE2-001/02-semantic-family-and-train-probe-contract.md`
- Create: `docs/research/SC900-BANK-PHASE2-001/03-future-leakage-verification-matrix.md`
- Create: `docs/research/SC900-BANK-PHASE2-001/04-rrc1-fairness-and-prior-decay.md`
- Create: `docs/research/SC900-BANK-PHASE2-001/05-noetic-dispositions.md`

**Interfaces:**
- Consumes: current taxonomy, Phase-1 source inventory, Gate-2 leakage audit/noetic findings, official Microsoft source verification.
- Produces: frozen Phase-2 authoring rules and implementation-ready design semantics only.

- [ ] **Step 1: Reverify official Microsoft authority**

Confirm the current SC-900 study guide/learning-path authority and source URLs. Do not use assessment/knowledge-check pages as content sources.

- [ ] **Step 2: Build the Phase-2 source inventory**

Reuse still-current Phase-1 sources where valid, update retrieval date, and add official product documentation only where needed for the second 50 questions. Ensure all 14 objectives and every leaf relied on by the authored set are covered.

- [ ] **Step 3: Freeze semantic-family and manifest semantics**

Document exact-item identity, semantic/source-family identity, scenario/concept-equivalent variants, shared-answer/shared-rationale leakage, uncertain-family fail-closed rules, and auditable family merge/split override receipts.

- [ ] **Step 4: Freeze future all-path leakage matrix**

For each required path record TRAIN permitted, PROBE permitted, metadata permitted, future guard location, fail-closed behavior, and future test obligation. Include normal/Smart Practice/due/weak/repair/follow-up/boss/stealth/restore/full restore/import/rebuild/prewarm/cache/render/history/analytics/export/debug/test-fixture paths and newly discovered paths.

- [ ] **Step 5: Define RRC-1 and prior-decay test metrics**

Define metric formulas and evidence requirements. Leave unjustified numeric thresholds explicitly unresolved rather than inventing values.

- [ ] **Step 6: Reconcile material noetic findings**

Classify each material item as resolved with evidence, non-material with basis, or still unresolved with a precise blocking statement.

- [ ] **Step 7: Run source/design validation**

```bash
python -m unittest tests.test_sc900_phase2 tests.test_sc900_bank_quality -v
```

and run the Phase-2 source-inventory validation path against `content/sc900/phase2/source_inventory.json`.

- [ ] **Step 8: Commit**

```bash
git add content/sc900/phase2/README.md content/sc900/phase2/source_inventory.json docs/research/SC900-BANK-PHASE2-001
git commit -m "docs: freeze SC-900 Phase 2 research contracts"
```

---

### Task 3: Author and review Phase-2 batches 01-03 (30 questions)

**Files:**
- Create: `content/sc900/phase2/batches/batch-01.jsonl`
- Create: `content/sc900/phase2/batches/batch-02.jsonl`
- Create: `content/sc900/phase2/batches/batch-03.jsonl`
- Create: matching review JSON files under `content/sc900/phase2/reviews/`

**Interfaces:**
- Consumes: official source inventory, taxonomy, existing canonical import schema, Phase-2 semantic-family rules.
- Produces: 30 original pending import records plus independent approved/withheld review receipts.

- [ ] **Step 1: Author batch 01 against underrepresented leaves/families**

Create ten original questions using the existing JSONL schema and Phase-1 metadata contract. Avoid semantic duplication with the accepted Phase-1 bank.

- [ ] **Step 2: Review batch 01 independently**

For each item verify factual source, objective/leaf, answer uniqueness, distractors, explanation, originality, duplicate status, semantic family, probe suitability, terminology freshness, reviewer, timestamp, disposition, and notes.

- [ ] **Step 3: Repeat for batch 02**

Use different semantic families where possible; do not manufacture superficial variants solely to fill quotas.

- [ ] **Step 4: Repeat for batch 03**

Keep the cumulative Phase-2 increment on track for the frozen `6 / 14 / 19 / 11` domain allocation and doubled objective totals.

- [ ] **Step 5: Validate/import in an isolated generated store**

Use the existing import/review tools. All imports must enter pending state before explicit review decisions are applied.

- [ ] **Step 6: Run focused quality checks**

```bash
python -m unittest tests.test_ingestion_importer tests.test_sc900_bank_quality tests.test_sc900_phase2 -v
```

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase2/batches content/sc900/phase2/reviews
git commit -m "content: add first 30 SC-900 Phase 2 reviewed questions"
```

---

### Task 4: Author and review Phase-2 batches 04-05 and close the 50-question increment

**Files:**
- Create: `content/sc900/phase2/batches/batch-04.jsonl`
- Create: `content/sc900/phase2/batches/batch-05.jsonl`
- Create: matching review JSON files.

**Interfaces:**
- Consumes: current allocation/coverage report after Task 3.
- Produces: final 20 Phase-2 candidates/reviews that close exactly the remaining objective/domain deficits.

- [ ] **Step 1: Compute remaining allocation gaps**

Compare the accepted Phase-1 50 plus approved Phase-2 batches 01-03 to the cumulative targets. Author only against the remaining deficits.

- [ ] **Step 2: Author/review batch 04**

Apply the same quality and independence gates; replace rejected items rather than weakening review.

- [ ] **Step 3: Author/review batch 05**

Close the exact cumulative allocation without creating duplicate/near-duplicate semantic families.

- [ ] **Step 4: Validate exactly 50 new approved items**

Run the Phase-2 set validator on the cumulative canonical store candidate. If fewer than 50 new items survive, author replacements and re-run review.

- [ ] **Step 5: Commit**

```bash
git add content/sc900/phase2/batches content/sc900/phase2/reviews
git commit -m "content: complete SC-900 Phase 2 reviewed question increment"
```

---

### Task 5: Generate cumulative store, compiled bank, and acceptance report

**Files:**
- Generate: `content/sc900/phase2/store/questions.json`
- Generate: `content/sc900/phase2/store/review_decisions.json`
- Generate: `content/sc900/phase2/compiled/sc900_phase2_reviewed_bank.json`
- Generate: `content/sc900/phase2/phase2_acceptance_report.json`

**Interfaces:**
- Consumes: accepted Phase-1 canonical store, five Phase-2 JSONL batches, five Phase-2 review files, source inventory.
- Produces: deterministic cumulative 100-question canonical/compiled artifacts and machine-readable terminal report.

- [ ] **Step 1: Build cumulative store through repository tooling**

Start from the accepted Phase-1 canonical data or re-import its authored batches deterministically. Import Phase-2 records through the normal importer so they first enter `pending`. Apply explicit decisions from the review receipts through the existing review tool/API.

- [ ] **Step 2: Compile approved records only**

Use `compile_question_bank(...)`; do not change its approval semantics.

- [ ] **Step 3: Run Phase-2 validator and write report**

The report must include approved/new/pending/withheld counts, domain/objective/leaf/family coverage, probe-suitability counts, source errors, quality errors, compiled count, bank-validation issues, candidate hash, default-bank invariant, Gate-2 status, and implementation authorization.

- [ ] **Step 4: Prove deterministic/idempotent generation**

Regenerate from the same authored/review inputs and compare hashes/content. Any drift is a failure.

- [ ] **Step 5: Run regression suite**

At minimum:

```bash
python -m unittest tests.test_sc900_phase2 tests.test_sc900_bank_quality tests.test_sc900_taxonomy tests.test_ingestion_importer tests.test_sc900_contract tests.test_smart_practice_core tests.test_study_question_utils -v
python -m unittest discover -s tests -v
```

Run bank lint/installation verification commands already used by repository CI where available.

- [ ] **Step 6: Commit generated artifacts**

```bash
git add content/sc900/phase2/store content/sc900/phase2/compiled content/sc900/phase2/phase2_acceptance_report.json
git commit -m "build: compile SC-900 Phase 2 reviewed bank"
```

---

### Task 6: Freeze terminal disposition, verify invariants, and open the review PR

**Files:**
- Create: `docs/research/SC900-BANK-PHASE2-001/06-phase2-disposition.md`
- Update only if needed: `docs/research/SC900-BANK-PHASE2-001/00-INDEX.md`

**Interfaces:**
- Consumes: final acceptance report, test results, current diff, protected refs.
- Produces: terminal Phase-2 receipt and review PR; no merge is implied by PR creation.

- [ ] **Step 1: Inspect final diff**

Confirm no changes to the default launch bank, Smart Practice scheduler/policy, RRC-1 runtime behavior, TRAIN/PROBE runtime guards, readiness, or protected learner-history paths.

- [ ] **Step 2: Verify protected refs**

Confirm:

- `sc900-v8.0.0-baseline` still dereferences to `fed4d4a44591ca93fe8428bc3ca02ec66a12f715`;
- `recovery/publish-exact-history/sc900-v8-20260910` remains `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`;
- `recovery/publish-sc900-v8-exact-history` remains `bbc3bd900b73bde89151dc51706ad62fc69e8196`.

- [ ] **Step 3: Write terminal disposition**

If evidence is clean, record:

```text
PHASE_2_STRUCTURALLY_ACCEPTED
APPROVED_QUESTIONS = 100
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NEXT = SC900-BANK-PHASE3-001 (100 -> approximately 200)
```

If evidence is not clean, record `PHASE_2_INCOMPLETE` and the exact blockers instead.

- [ ] **Step 4: Fresh final verification**

Re-run the complete required test/validation commands after the terminal documentation change. Completion claims must quote fresh results.

- [ ] **Step 5: Open one PR to `main`**

Title: `Complete SC-900 reviewed bank Phase 2`

PR body must summarize the 50 new/100 cumulative counts, coverage, source/review/semantic-family controls, design-only Gate-2 contract progress, exact verification results, current Gate-2/implementation status, and protected-ref proof.

Do not merge solely because the PR exists.
