# SC-900 Reviewed Bank Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the first 50-question reviewed SC-900 candidate bank from official Microsoft sources without changing the default launch bank or Smart Practice behavior.

**Architecture:** Extend the existing SC-900 ingestion/review/compiler path rather than create a parallel bank system. First refine the taxonomy and bank-quality metadata contract, then freeze an official-source inventory, author five independently reviewed 10-question batches, compile only explicitly approved items, and finish with an automated Phase-1 acceptance report. The existing `IMPORT != APPROVAL` invariant remains authoritative throughout.

**Tech Stack:** Python 3.11, standard library `json`/`unittest`, existing `ingestion` package, existing review CLI, existing bank validator, JSON/JSONL content artifacts, official Microsoft Learn web sources.

**Spec:** `docs/superpowers/specs/2026-09-11-sc900-reviewed-bank-phase1-design.md`

## Global Constraints

- Base branch state for this design: `b94d6851fecc125913784f3e29d29a6250abecac`.
- Blueprint authority: Microsoft SC-900 skills measured as of **July 28, 2026**.
- Phase-1 approved-bank target: exactly **50** questions.
- Domain allocation: exactly `6 / 14 / 19 / 11` across concepts / Entra / security solutions / compliance solutions.
- Objective allocation: exactly `3/3`, `3/4/3/4`, `6/4/3/6`, and `2/2/4/3` as frozen in the design spec.
- Questions must be newly authored from official Microsoft material; do not copy or lightly paraphrase Microsoft Practice Assessment questions, Learn module-assessment questions, recalled live-exam questions, or unlicensed commercial bank items.
- Official factual sources are Microsoft Learn and, where needed, official Microsoft product documentation.
- Every approved question must have official-source provenance, a stable blueprint leaf ID, a reviewed semantic family ID, and future probe suitability.
- Existing `promotion_status` / `review_decisions.json` remains the authoritative review-state mechanism. Do **not** create a second mutable approval state; expose `review_status` as a derived view of `promotion_status` when reporting.
- Same-semantic-family items must later remain in the same TRAIN/PROBE partition; Phase 1 only records family/suitability metadata and does not implement partitioning.
- Preserve `sc900_bank_v8_baseline.json` as the default launch bank throughout Phase 1.
- Do not implement RRC-1, TRAIN/PROBE runtime guards, readiness changes, learner-model changes, CAT/IRT/DKT, or Smart Practice redesign.
- The blocked research disposition remains `GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`; Phase 1 does not reverse it.
- Use `python -m unittest ...` for required tests; `pytest` is not a project dependency requirement.
- No completion claim without fresh diff/test/validation evidence.

---

## File Structure

The implementation should converge on these responsibilities:

- `config/certifications/sc900-2026.json` — authoritative four-domain taxonomy, 14 skill-group objectives, and 58 July-28-2026 blueprint leaves.
- `ingestion/bank_quality.py` — Phase-1 quality/metadata validation only; no scheduler logic.
- `ingestion/models.py` — keep canonicalization generic; only minimal changes if needed to preserve approved Phase-1 metadata.
- `ingestion/importer.py` — preserve quality metadata in compiled candidate banks; keep approval gating unchanged.
- `tools/validate_sc900_phase1.py` — deterministic Phase-1 structural acceptance validator/report generator.
- `tests/test_sc900_taxonomy.py` — taxonomy shape and objective/leaf ownership tests.
- `tests/test_sc900_bank_quality.py` — metadata, semantic-family, provenance, compile-preservation, and final-set validation tests.
- `content/sc900/phase1/README.md` — public authoring/review/source rules for the bank package.
- `content/sc900/phase1/source_inventory.json` — official-source inventory keyed to blueprint objectives/leaves.
- `content/sc900/phase1/batches/batch-01.jsonl` ... `batch-05.jsonl` — original authored source records.
- `content/sc900/phase1/reviews/batch-01-review.json` ... `batch-05-review.json` — item-level review receipts.
- `content/sc900/phase1/store/` — canonical imported questions and explicit review decisions used by the existing workflow.
- `content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json` — non-default compiled 50-question candidate bank.
- `content/sc900/phase1/phase1_acceptance_report.json` — machine-readable terminal Phase-1 structural report.

The committed JSONL batches remain the human-reviewable authoring source. The review store and compiled bank are auditable derived artifacts and must never become the launch default during this plan.

---

### Task 1: Refine the SC-900 taxonomy to the July 28, 2026 blueprint

**Files:**
- Modify: `config/certifications/sc900-2026.json`
- Create: `tests/test_sc900_taxonomy.py`

**Interfaces:**
- Consumes: existing `load_taxonomy()` from `ingestion.models`.
- Produces: domain `objectives` lists compatible with existing `_taxonomy_objectives(...)`, plus top-level `objective_details` records whose `leaf_skills` are used by later quality validation.

The taxonomy must keep the four existing domain IDs but replace the four coarse objectives with these 14 objective IDs:

```text
security_compliance_identity:
  security_compliance_concepts
  identity_concepts

microsoft_entra:
  entra_identity_types_and_function
  entra_authentication
  entra_access_management
  entra_identity_protection_governance

microsoft_security_solutions:
  azure_infrastructure_security
  azure_security_management
  microsoft_sentinel
  defender_xdr

microsoft_compliance_solutions:
  service_trust_privacy
  purview_compliance_management
  purview_information_protection_lifecycle
  purview_insider_risk_ediscovery_audit
```

Represent these 58 leaf IDs exactly once under their owning objective:

```text
security_compliance_concepts:
  shared_responsibility_model
  defense_in_depth
  zero_trust_model
  encryption_and_hashing
  grc_concepts

identity_concepts:
  identity_primary_security_perimeter
  authentication
  authorization
  identity_providers
  directory_services_active_directory
  federation

entra_identity_types_and_function:
  entra_id_overview
  identity_types_including_agent_id
  hybrid_identity

entra_authentication:
  authentication_methods
  multifactor_authentication
  password_protection_management

entra_access_management:
  conditional_access
  entra_roles_rbac

entra_identity_protection_governance:
  entra_id_governance
  access_reviews
  privileged_identity_management
  entra_id_protection

azure_infrastructure_security:
  azure_ddos_protection
  azure_firewall
  azure_web_application_firewall
  azure_virtual_network_segmentation
  network_security_groups
  azure_bastion
  azure_key_vault

azure_security_management:
  microsoft_defender_for_cloud
  cloud_security_posture_management
  security_policies_standards_recommendations
  cloud_workload_protection

microsoft_sentinel:
  siem_and_soar
  sentinel_threat_detection_mitigation

defender_xdr:
  defender_xdr_services
  defender_for_office_365
  defender_for_endpoint
  defender_for_cloud_apps
  defender_for_identity
  defender_vulnerability_management
  defender_threat_intelligence
  defender_portal

service_trust_privacy:
  service_trust_portal_offerings
  microsoft_privacy_principles

purview_compliance_management:
  purview_portal
  compliance_manager
  compliance_score

purview_information_protection_lifecycle:
  data_classification
  content_and_activity_explorer
  sensitivity_labels_and_policies
  data_loss_prevention
  records_management
  retention_policies_labels

purview_insider_risk_ediscovery_audit:
  insider_risk_management
  ediscovery
  audit
```

- [ ] **Step 1: Write the failing taxonomy test**

Create `tests/test_sc900_taxonomy.py` with assertions that:

```python
import unittest
from ingestion.models import load_taxonomy


class SC900TaxonomyTests(unittest.TestCase):
    def test_july_2026_taxonomy_has_12_objectives_and_58_unique_leaves(self):
        taxonomy = load_taxonomy()
        self.assertEqual("2026-07-28", taxonomy["skills_effective_date"])
        objective_ids = [
            objective
            for domain in taxonomy["domains"]
            for objective in domain["objectives"]
        ]
        self.assertEqual(12, len(objective_ids))
        self.assertEqual(12, len(set(objective_ids)))
        details = {row["id"]: row for row in taxonomy["objective_details"]}
        self.assertEqual(set(objective_ids), set(details))
        leaves = [leaf["id"] for row in details.values() for leaf in row["leaf_skills"]]
        self.assertEqual(58, len(leaves))
        self.assertEqual(58, len(set(leaves)))

    def test_objective_ownership_matches_frozen_phase1_design(self):
        taxonomy = load_taxonomy()
        owners = {
            objective: domain["id"]
            for domain in taxonomy["domains"]
            for objective in domain["objectives"]
        }
        self.assertEqual("microsoft_entra", owners["entra_authentication"])
        self.assertEqual("microsoft_security_solutions", owners["defender_xdr"])
        self.assertEqual("microsoft_compliance_solutions", owners["purview_information_protection_lifecycle"])
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m unittest tests.test_sc900_taxonomy -v
```

Expected: FAIL because the current taxonomy has four coarse objectives and no `skills_effective_date` / `objective_details`.

- [ ] **Step 3: Implement the refined taxonomy**

Update `config/certifications/sc900-2026.json` to:

- retain `schema_version` and `exam`;
- set `blueprint_version` to a string that still identifies the 2026 blueprint;
- add `skills_effective_date: "2026-07-28"`;
- retain the four current domain IDs and weight ranges;
- replace each domain's coarse `objectives` list with the objective IDs above;
- add `objective_details`, each with `id`, `name`, `domain_id`, and `leaf_skills` entries `{ "id": ..., "name": ... }` matching the official wording.

Do not change runtime policy code.

- [ ] **Step 4: Run taxonomy and existing ingestion tests**

```bash
python -m unittest tests.test_sc900_taxonomy tests.test_ingestion_importer tests.test_sc900_contract -v
```

Expected: all pass after test fixtures that used the old coarse objective ID are updated to a valid refined objective ID.

- [ ] **Step 5: Commit**

```bash
git add config/certifications/sc900-2026.json tests/test_sc900_taxonomy.py tests/test_ingestion_importer.py
git commit -m "feat: refine SC-900 July 2026 taxonomy"
```

---

### Task 2: Add the Phase-1 bank-quality contract and preserve metadata through compilation

**Files:**
- Create: `ingestion/bank_quality.py`
- Modify: `ingestion/importer.py`
- Create: `tests/test_sc900_bank_quality.py`
- Modify: `tests/test_ingestion_importer.py`

**Interfaces:**
- Consumes: canonical question records and the refined taxonomy.
- Produces:
  - `validate_phase1_question(record: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> None`
  - `phase1_review_status(record: Mapping[str, Any]) -> str`
  - compiled runtime records that retain Phase-1 quality metadata without altering approval semantics.

Required metadata values:

```python
PHASE1_STEM_STYLES = {
    "direct_concept",
    "short_scenario",
    "capability_selection",
    "distinction_comparison",
    "responsibility_governance",
}
PHASE1_PROBE_SUITABILITY = {"eligible", "train_only", "needs_review"}
PHASE1_AUTHORING_ORIGIN = "original_from_official_source"
```

Treat `review_status` as a derived view of existing `promotion_status`; do not store two independently mutable states.

- [ ] **Step 1: Write failing unit tests for the metadata contract**

In `tests/test_sc900_bank_quality.py`, construct a valid canonical-style question with:

```python
"metadata": {
    "blueprint_leaf_id": "multifactor_authentication",
    "source_authority": "microsoft_learn",
    "source_urls": ["https://learn.microsoft.com/en-us/training/..."],
    "source_retrieved_at": "2026-09-11",
    "source_family_id": "learn-entra-authentication",
    "semantic_family_id": "entra-mfa-purpose",
    "stem_style": "short_scenario",
    "future_probe_suitability": "eligible",
    "authoring_origin": "original_from_official_source",
}
```

Tests must prove that validation rejects:

- missing `blueprint_leaf_id`;
- leaf/objective mismatch;
- non-HTTPS or non-Microsoft source URL;
- empty `source_family_id` or `semantic_family_id`;
- invalid `stem_style`;
- invalid `future_probe_suitability`;
- wrong `authoring_origin`;
- missing references;
- metadata that points at Microsoft Practice Assessment or a module-assessment URL.

Also test:

```python
self.assertEqual("pending", phase1_review_status({"promotion_status": "pending"}))
self.assertEqual("approved", phase1_review_status({"promotion_status": "approved"}))
```

- [ ] **Step 2: Run the tests and verify failure**

```bash
python -m unittest tests.test_sc900_bank_quality -v
```

Expected: FAIL because `ingestion.bank_quality` does not exist.

- [ ] **Step 3: Implement `ingestion/bank_quality.py` minimally**

Implement:

```python
def validate_phase1_question(record, taxonomy) -> None:
    """Raise ValidationError with explicit reason codes for any Phase-1 quality-contract violation."""


def phase1_review_status(record) -> str:
    status = str(record.get("promotion_status") or "pending")
    return status if status in {"approved", "pending", "withheld"} else "pending"
```

Use explicit reason codes such as:

```text
MISSING_BLUEPRINT_LEAF
BLUEPRINT_LEAF_OBJECTIVE_MISMATCH
INVALID_SOURCE_AUTHORITY
INVALID_SOURCE_URL
ASSESSMENT_SOURCE_PROHIBITED
MISSING_SOURCE_RETRIEVED_AT
MISSING_SOURCE_FAMILY
MISSING_SEMANTIC_FAMILY
INVALID_STEM_STYLE
INVALID_PROBE_SUITABILITY
INVALID_AUTHORING_ORIGIN
MISSING_REFERENCE
```

A source URL is acceptable for this phase only when it is HTTPS and on `learn.microsoft.com` or another official `microsoft.com` documentation host. Explicitly reject source URLs whose path identifies Practice Assessment or module assessment content.

- [ ] **Step 4: Write a failing compile-preservation test**

Extend importer tests so an approved Phase-1 record compiles with these fields preserved:

```python
self.assertEqual("multifactor_authentication", compiled[0]["blueprint_leaf_id"])
self.assertEqual("entra-mfa-purpose", compiled[0]["semantic_family_id"])
self.assertEqual("learn-entra-authentication", compiled[0]["source_family_id"])
self.assertEqual("short_scenario", compiled[0]["stem_style"])
self.assertEqual("eligible", compiled[0]["future_probe_suitability"])
self.assertEqual("original_from_official_source", compiled[0]["authoring_origin"])
self.assertTrue(compiled[0]["references"])
```

- [ ] **Step 5: Modify the compiler to retain the Phase-1 fields**

In `compile_question_bank(...)`, preserve approved record metadata as explicit compiled fields:

```python
metadata = dict(record.get("metadata") or {})
...
"subobjective": record.get("subobjective", ""),
"blueprint_leaf_id": metadata.get("blueprint_leaf_id", ""),
"semantic_family_id": metadata.get("semantic_family_id", ""),
"source_family_id": metadata.get("source_family_id", ""),
"stem_style": metadata.get("stem_style", ""),
"future_probe_suitability": metadata.get("future_probe_suitability", "needs_review"),
"authoring_origin": metadata.get("authoring_origin", ""),
"references": list(record.get("references") or []),
```

Do not change which records compile: only `promotion_status == "approved"` may compile.

- [ ] **Step 6: Run focused tests**

```bash
python -m unittest tests.test_sc900_bank_quality tests.test_ingestion_importer -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add ingestion/bank_quality.py ingestion/importer.py tests/test_sc900_bank_quality.py tests/test_ingestion_importer.py
git commit -m "feat: add SC-900 Phase 1 bank quality contract"
```

---

### Task 3: Add the official-source inventory and Phase-1 acceptance validator

**Files:**
- Create: `content/sc900/phase1/README.md`
- Create: `content/sc900/phase1/source_inventory.json`
- Create: `tools/validate_sc900_phase1.py`
- Modify: `tests/test_sc900_bank_quality.py`

**Interfaces:**
- Consumes: source inventory, canonical review store, compiled candidate bank, refined taxonomy.
- Produces:
  - `validate_source_inventory(inventory, taxonomy) -> list[dict[str, str]]`
  - `validate_phase1_set(questions, taxonomy, review_receipts) -> dict[str, Any]`
  - CLI output/report used by Task 9.

The source inventory must freeze the following authority roots:

```text
https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900
https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/
https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access/
https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions/
https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-compliance-solutions/
```

For each objective/leaf, record the specific official Learn module/product-doc URL actually used for authoring or factual verification, with retrieval date `2026-09-11` or the actual execution date if later.

- [ ] **Step 1: Write failing tests for source inventory and final-set validation**

Tests must assert that:

- every one of the 14 objectives has at least one official source entry;
- every source host is official Microsoft;
- no source URL is a Practice Assessment or module assessment;
- every referenced leaf ID exists in the refined taxonomy;
- `validate_phase1_set(...)` requires exactly 50 approved records for terminal success;
- domain counts must equal `6 / 14 / 19 / 11`;
- objective counts must equal the spec allocations;
- each approved record passes `validate_phase1_question(...)`;
- each approved ID has a review receipt;
- every approved semantic family is non-empty;
- `promotion_status != approved` never counts toward the 50.

- [ ] **Step 2: Run tests and verify they fail**

```bash
python -m unittest tests.test_sc900_bank_quality -v
```

Expected: FAIL because the validator/source inventory does not yet exist.

- [ ] **Step 3: Create the source inventory**

Create `content/sc900/phase1/source_inventory.json` with:

```json
{
  "exam": "SC-900",
  "skills_effective_date": "2026-07-28",
  "inventory_frozen_at": "2026-09-11",
  "authority": "Microsoft Learn / official Microsoft documentation",
  "sources": []
}
```

Each `sources` entry must include:

```json
{
  "source_id": "stable-id",
  "url": "https://learn.microsoft.com/...",
  "title": "official page title",
  "source_type": "study_guide|learning_path|module|product_documentation",
  "objective_ids": ["..."],
  "leaf_ids": ["..."],
  "retrieved_at": "2026-09-11",
  "assessment_content_used": false
}
```

Do not put Practice Assessment or module-assessment question URLs in this file.

- [ ] **Step 4: Create the Phase-1 package README**

Document:

- original-authoring requirement;
- exact 50-question target and distributions;
- `IMPORT != APPROVAL`;
- semantic-family meaning;
- candidate-bank-not-default rule;
- how to run import, review, compile, and validation commands.

- [ ] **Step 5: Implement the validator CLI**

CLI shape:

```bash
python tools/validate_sc900_phase1.py \
  --store content/sc900/phase1/store \
  --compiled content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json \
  --reviews content/sc900/phase1/reviews \
  --source-inventory content/sc900/phase1/source_inventory.json \
  --report content/sc900/phase1/phase1_acceptance_report.json
```

Exit `0` only when the Phase-1 acceptance gate is fully satisfied. Exit `1` with explicit reason codes otherwise. The report must include at least:

```text
status
approved_count
pending_count
withheld_count
domain_counts
objective_counts
distinct_leaf_count
semantic_family_count
probe_suitability_counts
source_inventory_errors
quality_errors
bank_validation_issues
compiled_count
```

Before 50 approved items exist, status must be `PHASE_1_INCOMPLETE`, not success.

- [ ] **Step 6: Run tests**

```bash
python -m unittest tests.test_sc900_bank_quality tests.test_sc900_taxonomy -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase1/README.md content/sc900/phase1/source_inventory.json tools/validate_sc900_phase1.py tests/test_sc900_bank_quality.py
git commit -m "feat: add SC-900 Phase 1 source and acceptance contracts"
```

---

### Task 4: Author, import, independently review, and approve Batch 01

**Files:**
- Create: `content/sc900/phase1/batches/batch-01.jsonl`
- Create: `content/sc900/phase1/reviews/batch-01-review.json`
- Modify/generated through existing importer: `content/sc900/phase1/store/*`

**Interfaces:**
- Consumes: refined taxonomy, source inventory, quality validator, existing import/review CLI.
- Produces: 10 canonical questions with explicit review decisions.

Batch-01 allocation is exactly:

```text
security_compliance_concepts ............... 1
identity_concepts .......................... 1
entra_identity_types_and_function .......... 1
entra_authentication ....................... 1
entra_identity_protection_governance ....... 1
azure_infrastructure_security ............... 1
azure_security_management ................... 1
defender_xdr ................................ 1
service_trust_privacy ....................... 1
purview_information_protection_lifecycle .... 1
TOTAL ...................................... 10
```

Use a mixed stem-style target of roughly 2 direct concept, 3 short scenario, 3 capability/service-selection, and 2 distinction/governance items across the batch. Prefer a leaf not yet represented before repeating a leaf.

- [ ] **Step 1: Author 10 original JSONL records from official sources**

Each row must conform to the existing canonical input format and include Phase-1 metadata. Example shape only—do not reuse the example as a production item:

```json
{
  "exam": "SC-900",
  "domain": "microsoft_entra",
  "objective": "entra_authentication",
  "subobjective": "multifactor authentication",
  "difficulty": "beginner",
  "type": "multiple_choice",
  "stem": "<new original stem>",
  "choices": [
    {"id": "a", "text": "<plausible distractor>"},
    {"id": "b", "text": "<correct answer>"},
    {"id": "c", "text": "<plausible distractor>"},
    {"id": "d", "text": "<plausible distractor>"}
  ],
  "correct_answer": "b",
  "explanation": "<source-supported original explanation>",
  "references": ["https://learn.microsoft.com/..."],
  "tags": ["entra", "authentication"],
  "source": {"title": "Microsoft Learn", "url": "https://learn.microsoft.com/..."},
  "metadata": {
    "origin": "manual",
    "batch": "phase1-batch-01",
    "blueprint_leaf_id": "multifactor_authentication",
    "source_authority": "microsoft_learn",
    "source_urls": ["https://learn.microsoft.com/..."],
    "source_retrieved_at": "2026-09-11",
    "source_family_id": "learn-entra-authentication",
    "semantic_family_id": "entra-mfa-purpose",
    "stem_style": "short_scenario",
    "future_probe_suitability": "eligible",
    "authoring_origin": "original_from_official_source"
  }
}
```

- [ ] **Step 2: Import Batch 01**

```bash
python tools/import_sc900_content.py content/sc900/phase1/batches/batch-01.jsonl \
  --store content/sc900/phase1/store
```

Expected: 10 accepted unless a genuine duplicate/quality issue is detected. Any rejected/review item must be corrected or explicitly withheld; never lower the gate to preserve the number 10.

- [ ] **Step 3: Produce an independent review receipt**

For each question ID, record in `batch-01-review.json`:

```text
question_id
factual_source_checked
objective_leaf_checked
correct_answer_unique
all_distractors_defensibly_wrong
explanation_supported
originality_boundary_checked
duplicate_reviewed
semantic_family_reviewed
probe_suitability_reviewed
reviewer
reviewed_at
disposition
notes
```

A fresh reviewer/subagent must verify the cited official page rather than simply accepting the authoring rationale.

- [ ] **Step 4: Apply explicit review decisions**

For every accepted item:

```bash
python tools/review_sc900_content.py decide approved <question-id> \
  --store content/sc900/phase1/store \
  --actor phase1-independent-review
```

Use `withheld` or leave `pending` for any item that does not pass review. Author a replacement until Batch 01 contributes 10 approved items matching its allocation.

- [ ] **Step 5: Run batch validation and regression tests**

```bash
python tools/review_sc900_content.py report --store content/sc900/phase1/store
python -m unittest tests.test_sc900_bank_quality tests.test_ingestion_importer -v
```

Expected: 10 approved Phase-1 items at this checkpoint and no quality-contract failures for those IDs.

- [ ] **Step 6: Commit**

```bash
git add content/sc900/phase1/batches/batch-01.jsonl content/sc900/phase1/reviews/batch-01-review.json content/sc900/phase1/store
git commit -m "content: add reviewed SC-900 phase 1 batch 01"
```

---

### Task 5: Author and review Batch 02

**Files:**
- Create: `content/sc900/phase1/batches/batch-02.jsonl`
- Create: `content/sc900/phase1/reviews/batch-02-review.json`
- Modify: `content/sc900/phase1/store/*`

**Allocation:**

```text
security_compliance_concepts ........ 1
entra_identity_types_and_function ... 1
entra_authentication ................ 1
entra_access_management ............. 1
azure_infrastructure_security ....... 1
azure_security_management ........... 1
microsoft_sentinel .................. 1
defender_xdr ........................ 1
purview_compliance_management ....... 1
purview_information_protection_lifecycle ... 1
TOTAL ............................... 10
```

- [ ] **Step 1: Author 10 original records, preferring not-yet-used leaves**
- [ ] **Step 2: Import with the existing importer and inspect accepted/review/rejected counts**
- [ ] **Step 3: Independently verify every source, key, distractor set, objective/leaf, semantic family, and originality boundary**
- [ ] **Step 4: Apply explicit `approved` / `withheld` / `pending` decisions through `tools/review_sc900_content.py`**
- [ ] **Step 5: Author replacements until cumulative approved count is exactly 20 and Batch-02 allocation is satisfied**
- [ ] **Step 6: Run**

```bash
python tools/review_sc900_content.py report --store content/sc900/phase1/store
python -m unittest tests.test_sc900_bank_quality tests.test_ingestion_importer -v
```

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase1/batches/batch-02.jsonl content/sc900/phase1/reviews/batch-02-review.json content/sc900/phase1/store
git commit -m "content: add reviewed SC-900 phase 1 batch 02"
```

---

### Task 6: Author and review Batch 03

**Files:**
- Create: `content/sc900/phase1/batches/batch-03.jsonl`
- Create: `content/sc900/phase1/reviews/batch-03-review.json`
- Modify: `content/sc900/phase1/store/*`

**Allocation:**

```text
identity_concepts .......................... 1
entra_authentication ....................... 1
entra_access_management .................... 1
entra_identity_protection_governance ....... 1
azure_infrastructure_security ............... 1
azure_security_management ................... 1
microsoft_sentinel .......................... 1
defender_xdr ................................ 1
purview_information_protection_lifecycle .... 1
purview_insider_risk_ediscovery_audit ....... 1
TOTAL ...................................... 10
```

- [ ] **Step 1: Author the batch from official sources using the same JSONL contract**
- [ ] **Step 2: Import and resolve genuine duplicate/quarantine outcomes without bypassing them**
- [ ] **Step 3: Complete fresh independent review receipts for all 10 accepted replacements**
- [ ] **Step 4: Apply explicit promotion decisions**
- [ ] **Step 5: Verify cumulative approved count is exactly 30**
- [ ] **Step 6: Run focused tests and report command**

```bash
python tools/review_sc900_content.py report --store content/sc900/phase1/store
python -m unittest tests.test_sc900_bank_quality tests.test_ingestion_importer -v
```

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase1/batches/batch-03.jsonl content/sc900/phase1/reviews/batch-03-review.json content/sc900/phase1/store
git commit -m "content: add reviewed SC-900 phase 1 batch 03"
```

---

### Task 7: Author and review Batch 04

**Files:**
- Create: `content/sc900/phase1/batches/batch-04.jsonl`
- Create: `content/sc900/phase1/reviews/batch-04-review.json`
- Modify: `content/sc900/phase1/store/*`

**Allocation:**

```text
security_compliance_concepts ............... 1
entra_identity_types_and_function .......... 1
entra_access_management .................... 1
entra_identity_protection_governance ....... 1
azure_infrastructure_security ............... 2
microsoft_sentinel .......................... 1
defender_xdr ................................ 1
service_trust_privacy ....................... 1
purview_insider_risk_ediscovery_audit ....... 1
TOTAL ...................................... 10
```

- [ ] **Step 1: Author 10 original records, maintaining semantic-family conservatism**
- [ ] **Step 2: Import and review importer diagnostics**
- [ ] **Step 3: Independently verify source, answer, distractor, taxonomy, semantic-family, and probe-suitability claims**
- [ ] **Step 4: Apply explicit decisions; replace any failed item rather than lowering acceptance criteria**
- [ ] **Step 5: Verify cumulative approved count is exactly 40**
- [ ] **Step 6: Run tests/report**

```bash
python tools/review_sc900_content.py report --store content/sc900/phase1/store
python -m unittest tests.test_sc900_bank_quality tests.test_ingestion_importer -v
```

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase1/batches/batch-04.jsonl content/sc900/phase1/reviews/batch-04-review.json content/sc900/phase1/store
git commit -m "content: add reviewed SC-900 phase 1 batch 04"
```

---

### Task 8: Author and review Batch 05 and close the 50-question allocation

**Files:**
- Create: `content/sc900/phase1/batches/batch-05.jsonl`
- Create: `content/sc900/phase1/reviews/batch-05-review.json`
- Modify: `content/sc900/phase1/store/*`

**Allocation:**

```text
identity_concepts .......................... 1
entra_authentication ....................... 1
entra_identity_protection_governance ....... 1
azure_infrastructure_security ............... 1
azure_security_management ................... 1
defender_xdr ................................ 2
purview_compliance_management ............... 1
purview_information_protection_lifecycle .... 1
purview_insider_risk_ediscovery_audit ....... 1
TOTAL ...................................... 10
```

After Batch 05, the exact objective totals must be:

```text
security_compliance_concepts ............... 3
identity_concepts .......................... 3
entra_identity_types_and_function .......... 3
entra_authentication ....................... 4
entra_access_management .................... 3
entra_identity_protection_governance ....... 4
azure_infrastructure_security ............... 6
azure_security_management ................... 4
microsoft_sentinel .......................... 3
defender_xdr ................................ 6
service_trust_privacy ....................... 2
purview_compliance_management ............... 2
purview_information_protection_lifecycle .... 4
purview_insider_risk_ediscovery_audit ....... 3
```

- [ ] **Step 1: Author the final 10 records**
- [ ] **Step 2: Import and resolve importer diagnostics**
- [ ] **Step 3: Perform independent item review and create receipts**
- [ ] **Step 4: Apply explicit decisions and author replacements until exactly 50 items are approved**
- [ ] **Step 5: Verify the exact domain/objective allocation before compiling**

Use a short Python check or the Phase-1 validator; expected domain counts are:

```python
{
    "security_compliance_identity": 6,
    "microsoft_entra": 14,
    "microsoft_security_solutions": 19,
    "microsoft_compliance_solutions": 11,
}
```

- [ ] **Step 6: Commit**

```bash
git add content/sc900/phase1/batches/batch-05.jsonl content/sc900/phase1/reviews/batch-05-review.json content/sc900/phase1/store
git commit -m "content: complete reviewed SC-900 phase 1 authoring"
```

---

### Task 9: Compile the candidate bank and run the full Phase-1 acceptance gate

**Files:**
- Create: `content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json`
- Create: `content/sc900/phase1/phase1_acceptance_report.json`
- Modify if defects are found: only the smallest relevant taxonomy/quality/content files.

**Interfaces:**
- Consumes: 50 approved records from `content/sc900/phase1/store`, review receipts, source inventory.
- Produces: deterministic non-default candidate bank and acceptance report.

- [ ] **Step 1: Compile the approved bank**

```bash
python tools/review_sc900_content.py report \
  --store content/sc900/phase1/store \
  --compile content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json
```

Expected:

```text
approved = 50
compiled = 50
```

Pending/withheld records may exist in the review store only if they are rejected authoring attempts; they must not appear in the compiled bank.

- [ ] **Step 2: Prove compilation is deterministic from the same frozen store**

```bash
cp content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json /tmp/sc900-phase1-first.json
python tools/review_sc900_content.py report \
  --store content/sc900/phase1/store \
  --compile content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json
python - <<'PY'
from pathlib import Path
import hashlib
for path in [Path('/tmp/sc900-phase1-first.json'), Path('content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json')]:
    print(path, hashlib.sha256(path.read_bytes()).hexdigest())
assert Path('/tmp/sc900-phase1-first.json').read_bytes() == Path('content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json').read_bytes()
PY
```

Expected: byte-identical outputs.

- [ ] **Step 3: Run generic bank validation against the candidate path**

Use `tools.validate_bank.validate_bank(Path(...))` directly rather than `tools/lint_bank.py`, because `lint_bank.py` intentionally asserts the eight-question baseline.

```bash
python - <<'PY'
from pathlib import Path
from tools.validate_bank import validate_bank
result = validate_bank(Path('content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json'))
print(result)
assert not result['issues'], result['issues']
PY
```

Warnings must be reviewed. Do not ignore duplicate, answer-pattern, explanation, or prompt-quality warnings without a written disposition.

- [ ] **Step 4: Run the Phase-1 acceptance validator**

```bash
python tools/validate_sc900_phase1.py \
  --store content/sc900/phase1/store \
  --compiled content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json \
  --reviews content/sc900/phase1/reviews \
  --source-inventory content/sc900/phase1/source_inventory.json \
  --report content/sc900/phase1/phase1_acceptance_report.json
```

Expected terminal status:

```text
PHASE_1_STRUCTURALLY_ACCEPTED
```

If the validator reports any quality, source, distribution, duplicate, or review-receipt failure, fix the underlying item/process and rerun. Never edit the acceptance report to manufacture success.

- [ ] **Step 5: Run regression tests**

At minimum:

```bash
python -m unittest \
  tests.test_sc900_taxonomy \
  tests.test_sc900_bank_quality \
  tests.test_ingestion_importer \
  tests.test_sc900_contract \
  tests.test_smart_practice_core \
  tests.test_study_question_utils -v
```

Then run the repository's full supported unittest suite or existing quality-check entry point if available in the execution environment.

The eight-question default baseline contract must remain green because Phase 1 does not replace the launch bank.

- [ ] **Step 6: Verify protected state and diff scope**

Freshly verify:

```text
main/base relationship
sc900-v8.0.0-baseline -> fed4d4a44591ca93fe8428bc3ca02ec66a12f715
sc900_bank_v8_baseline.json unchanged
default cert_config bank filename unchanged
no Smart Practice/runtime scheduling files changed except importer metadata preservation explicitly planned above
```

- [ ] **Step 7: Commit**

```bash
git add content/sc900/phase1/compiled/sc900_phase1_reviewed_bank.json content/sc900/phase1/phase1_acceptance_report.json
git commit -m "test: verify SC-900 reviewed bank phase 1"
```

---

### Task 10: Final review package and PR preparation

**Files:**
- Create: `docs/research/SC900-BANK-PHASE1-001/00-INDEX.md`
- Create: `docs/research/SC900-BANK-PHASE1-001/01-source-and-blueprint-receipt.md`
- Create: `docs/research/SC900-BANK-PHASE1-001/02-quality-and-review-receipt.md`
- Create: `docs/research/SC900-BANK-PHASE1-001/03-phase1-disposition.md`

**Interfaces:**
- Consumes: source inventory, acceptance report, git diff, test outputs.
- Produces: compact auditable Phase-1 receipt and review PR.

- [ ] **Step 1: Write the Phase-1 receipts from actual evidence only**

`00-INDEX.md` must report:

```text
WORK_ID = SC900-BANK-PHASE1-001
BASE_MAIN_SHA = <actual implementation base>
APPROVED_QUESTIONS = 50
DOMAIN_ALLOCATION = 6/14/19/11
DEFAULT_BANK_CHANGED = NO
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
PHASE1_STATUS = PHASE_1_STRUCTURALLY_ACCEPTED | PHASE_1_INCOMPLETE
```

Do not claim `PHASE_1_STRUCTURALLY_ACCEPTED` unless the validator actually emitted it in Task 9.

- [ ] **Step 2: Record source and blueprint evidence**

Document:

- Microsoft SC-900 skills effective July 28, 2026;
- 14 objective groups / 58 taxonomy leaves;
- official-source-only policy;
- no assessment/exam-dump reuse;
- actual source inventory hash.

- [ ] **Step 3: Record quality/review evidence**

Document:

- import/approval separation;
- approved/pending/withheld counts;
- review-receipt completeness;
- semantic-family counts and any families with multiple items;
- probe-suitability counts;
- generic bank validator results;
- regression-test command and result.

- [ ] **Step 4: Record the Phase-1 disposition and next boundary**

If accepted, explicitly state:

```text
Phase 1 validates the content/taxonomy/review pipeline at 50 questions.
It does NOT earn CAND-01R2 Gate 2.
Next bank milestone = 100 reviewed questions.
Serious Gate-2 reopening target remains approximately 200 reviewed questions plus the still-unresolved design-contract requirements.
```

- [ ] **Step 5: Run final verification before opening a PR**

Verify the complete branch diff and ensure there are no:

- launch-bank replacements;
- RRC-1 changes;
- TRAIN/PROBE runtime changes;
- private learner-history files;
- Microsoft assessment copies;
- unrelated refactors.

- [ ] **Step 6: Open a review PR and do not merge automatically**

PR summary must include:

- exact branch head SHA;
- exact base SHA;
- question counts/distribution;
- test/validator evidence;
- statement that the default 8-question baseline remains unchanged;
- statement that Gate 2 remains blocked.

Leave the PR open for review unless the operator explicitly authorizes merge.
