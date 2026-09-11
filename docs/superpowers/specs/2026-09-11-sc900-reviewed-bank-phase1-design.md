# SC-900 Reviewed Bank Phase 1 Design

Status: DESIGN SPEC PENDING WRITTEN-SPEC REVIEW — no bank implementation is authorized until this document is explicitly approved.

Base main: `b94d6851fecc125913784f3e29d29a6250abecac`

Blueprint authority: Microsoft SC-900 **skills measured as of July 28, 2026**.

## 1. Purpose

Build the first serious SC-900 question bank without redoing the learning engine. Reuse the existing provenance-aware ingestion, pending/review/approval workflow, deterministic IDs, duplicate handling, runtime compiler, and bank validation machinery. The bank work must improve content quality and experimental validity while preserving the existing Smart Practice runtime.

Phase 1 produces **50 reviewed, approved, original SC-900 questions** sourced from official Microsoft Learn material. It is a structural-quality milestone, not a claim that Gate 2 is unblocked. Growth proceeds only after review checkpoints:

`50 -> 100 -> 200`

The 200-question stage remains the serious comparison target for reopening the blocked CAND-01R2 Gate 2 unless later evidence justifies a different target without overstating decisiveness.

## 2. Source authority

### 2.1 Primary authority hierarchy

1. **Microsoft SC-900 study guide** defines current exam scope, skill groups, and weighting.
   - https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900
2. **Official Microsoft Learn SC-900 learning paths and modules** provide factual teaching material for original question writing.
   - Concepts: https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/
   - Microsoft Entra: https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access/
   - Microsoft security solutions: https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions/
   - Microsoft Purview/privacy: https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-compliance-solutions/
3. **Official Microsoft product documentation** may resolve factual ambiguity or confirm product behavior where a Learn module is too high level.

Community posts, SEO summaries, unofficial study sites, exam dumps, and recalled live-exam questions are not load-bearing bank sources.

### 2.2 Copyright / assessment boundary

Questions must be newly authored. Do not copy or lightly paraphrase:

- Microsoft Practice Assessment questions;
- Microsoft Learn module-assessment questions;
- live-exam or recalled exam questions;
- commercial question-bank items without explicit reuse rights.

Product names, official feature names, and standard technical terms may of course be used. The factual concept may come from Microsoft Learn, but the stem, scenario, distractors, explanation structure, and answer presentation must be original.

Each question records the factual source URL(s) used to validate it.

## 3. Blueprint allocation

The current SC-900 study guide weights the four major areas as:

- Security, compliance, and identity concepts: `10-15%`
- Microsoft Entra: `25-30%`
- Microsoft security solutions: `35-40%`
- Microsoft compliance solutions: `20-25%`

Phase 1 fixes the 50-question allocation at:

| Domain | Questions | Share |
| --- | ---: | ---: |
| Security, compliance, and identity concepts | 6 | 12% |
| Microsoft Entra | 14 | 28% |
| Microsoft security solutions | 19 | 38% |
| Microsoft compliance solutions | 11 | 22% |
| **Total** | **50** | **100%** |

Every share is inside the corresponding official weight range.

Later targets preserve the same center allocation unless the study guide changes:

- 100 questions: `12 / 28 / 38 / 22`
- 200 questions: `24 / 56 / 76 / 44`

A Microsoft blueprint update triggers a new taxonomy/source review before further authoring; existing questions are not silently remapped.

## 4. Taxonomy refinement

The current repository taxonomy has one coarse objective per major domain. That is insufficient for quality review, coverage diagnostics, and future semantic TRAIN/PROBE partitioning.

Keep the four current domain IDs stable, but refine their objective layer to the current skill groups.

### 4.1 Domain 1 — 6 questions

`security_compliance_identity`:

- `security_compliance_concepts` — 3
- `identity_concepts` — 3

### 4.2 Domain 2 — 14 questions

`microsoft_entra`:

- `entra_identity_types_and_function` — 3
- `entra_authentication` — 4
- `entra_access_management` — 3
- `entra_identity_protection_governance` — 4

### 4.3 Domain 3 — 19 questions

`microsoft_security_solutions`:

- `azure_infrastructure_security` — 6
- `azure_security_management` — 4
- `microsoft_sentinel` — 3
- `defender_xdr` — 6

### 4.4 Domain 4 — 11 questions

`microsoft_compliance_solutions`:

- `service_trust_privacy` — 2
- `purview_compliance_management` — 2
- `purview_information_protection_lifecycle` — 4
- `purview_insider_risk_ediscovery_audit` — 3

The taxonomy should also represent blueprint leaf skills with stable IDs. A question maps to exactly one primary objective and one primary blueprint leaf. Secondary concepts may be tags, not competing primary classifications.

This refinement changes content classification only; it does not authorize changes to Smart Practice policy or learner-model behavior.

## 5. Question record design

Reuse the existing canonical question schema wherever possible. Required current fields remain:

- exam
- domain
- objective
- subobjective
- difficulty
- type
- stem
- choices
- correct_answer
- explanation
- references
- tags
- metadata
- provenance

The existing ingestion layer already supports stable canonical IDs, source provenance, arbitrary metadata, deterministic fingerprints, references, and approval gating. Phase 1 adds bank-quality metadata rather than creating a parallel content format.

### 5.1 Required Phase-1 metadata

Each candidate question must carry:

- `blueprint_leaf_id` — stable leaf skill identifier;
- `source_authority` — normally `microsoft_learn`;
- `source_urls` — one or more factual authority URLs;
- `source_retrieved_at` — date used for source review;
- `source_family_id` — module/product documentation family;
- `semantic_family_id` — identifies items that teach/test substantially the same proposition, template, or cue structure;
- `stem_style` — e.g. direct concept, short scenario, capability-selection, distinction/comparison;
- `review_status` — existing pending/approved workflow remains authoritative;
- `future_probe_suitability` — `eligible`, `train_only`, or `needs_review`;
- `authoring_origin` — `original_from_official_source` for this phase.

Do not add psychometric claims such as calibrated item difficulty or discrimination. Existing `difficulty` remains an editorial label only.

## 6. Semantic-family rules

The Gate-2 review established that exact-item withholding is insufficient. Phase 1 therefore labels semantic families from the first serious batch.

A `semantic_family_id` groups questions when prior exposure to one could materially reveal another because they share one or more of:

- the same core factual proposition;
- a near-identical scenario/template;
- a distinctive answer-option pattern;
- near-identical source wording;
- a narrow cue/product-name association that effectively gives away the answer.

Rules:

1. Same-family items may not later be split across TRAIN and PROBE.
2. A family label is conservative: when uncertain, group rather than claim independence.
3. Objective equality alone does not imply same semantic family.
4. Different wording alone does not establish independence.
5. Import duplicate detection is not a substitute for semantic-family review.

Phase 1 only records suitability and families. It does **not** implement the TRAIN/PROBE partition or unblock Gate 2.

## 7. Authoring and review workflow

Use the existing architecture:

`official source -> original candidate -> canonical import -> pending review -> quality review -> explicit approval -> compiled candidate bank`

`IMPORT != APPROVAL` remains a hard invariant.

### 7.1 Authoring cadence

Create Phase 1 in **five review batches of 10**. The aggregate 50-question blueprint allocation is authoritative; each individual ten-question batch need not exactly mirror the final percentages.

After each batch:

1. validate schema/taxonomy;
2. inspect provenance and source URLs;
3. review objective/leaf mapping;
4. review factual correctness against the cited official source;
5. review answer uniqueness and distractor quality;
6. run duplicate/near-duplicate checks;
7. assign/review semantic family;
8. check originality boundary;
9. approve only accepted items;
10. correct the process before authoring the next batch if systemic defects are found.

This prevents a taxonomy or authoring mistake from being multiplied across all 50 items.

### 7.2 Item acceptance checklist

An item may be approved only when all applicable checks pass:

- within current SC-900 scope;
- mapped to the correct domain/objective/leaf;
- factually supported by official source material;
- original wording and scenario construction;
- exactly one defensible correct answer for single-select items;
- every distractor is plausible enough to test understanding but demonstrably incorrect in context;
- explanation states why the correct answer is correct and, where useful, why common distractors fail;
- no unsupported claim is introduced by the explanation;
- no assessment/exam-dump provenance;
- semantic family reviewed;
- no unresolved exact or near duplicate;
- references and provenance present;
- future probe suitability explicitly classified.

Ambiguous or outdated questions remain pending or quarantined. They are not approved merely to meet a numeric quota.

## 8. Phase-1 content style

The bank should measure recognition plus practical conceptual discrimination rather than trivia memorization.

Use a mixture of:

- direct concept questions;
- short realistic scenarios;
- capability/service selection;
- compare/distinguish questions;
- responsibility or governance decisions appropriate to SC-900 fundamentals.

Avoid:

- intentionally deceptive wording;
- obscure portal-navigation trivia;
- version-sensitive UI details unless the exam blueprint explicitly requires them;
- answer choices differentiated only by tiny wording tricks;
- repeated product-name cue patterns that allow guessing without understanding.

Question length should stay appropriate for a fundamentals exam. Complexity belongs in the concept, not unnecessary prose.

## 9. Candidate-bank isolation from the launch bank

Phase-1 content should not automatically replace the current launch bank as individual questions are approved.

Until the complete 50-question Phase-1 acceptance gate is satisfied:

- preserve `sc900_bank_v8_baseline.json` as the existing launch baseline;
- compile reviewed Phase-1 content as a candidate bank/artifact through the existing compiler path;
- do not make partial batches the default runtime bank;
- do not use pending or quarantined items in normal runtime practice.

Promotion of the 50-question candidate to a default runtime bank is a separate integration decision after validation.

## 10. Phase-1 acceptance gate

Phase 1 is structurally complete only when fresh verification establishes:

1. exactly 50 approved questions in the candidate set;
2. domain distribution exactly `6 / 14 / 19 / 11`;
3. objective allocations match Section 4 unless a documented Microsoft blueprint change required a design revision;
4. every approved item has official-source provenance and at least one usable reference;
5. every approved item has a reviewed `blueprint_leaf_id` and `semantic_family_id`;
6. every approved item has future probe suitability classified;
7. no approved item is quarantined, malformed, or unresolved duplicate;
8. no known Practice Assessment/module-assessment/exam-dump item was copied into the bank;
9. candidate compilation is deterministic and idempotent;
10. bank lint/schema validation passes;
11. existing ingestion/review/runtime contract tests remain green;
12. protected baseline tag/history remains unchanged.

If fewer than 50 items survive review, the correct state is `PHASE_1_INCOMPLETE`; author more reviewed items rather than lowering the quality gate.

## 11. Relationship to CAND-01R2 Gate 2

The merged Gate-2 receipt remains authoritative:

`GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`

The 50-question Phase-1 bank is **not** sufficient to reverse that disposition. Its purpose is to validate the refined taxonomy, official-source provenance, authoring/review process, semantic-family labeling, and candidate-bank compilation at meaningful scale.

At 100 questions, expand breadth and inspect whether objective/family coverage remains healthy.

At approximately 200 reviewed questions, reassess whether the bank can support:

- blueprint-balanced TRAIN/PROBE withholding;
- meaningful semantic-family separation;
- matched champion/challenger allocation;
- adequate clean 7-day observations;
- the implementation-ready isolation contract and verification matrix required to reopen Gate 2.

No RRC-1 runtime implementation is authorized by this bank design.

## 12. Non-goals

Phase 1 does not:

- redesign Smart Practice;
- implement RRC-1;
- implement TRAIN/PROBE runtime guards;
- claim calibrated psychometric item difficulty;
- generate live-exam replicas;
- use exam dumps;
- copy Microsoft assessment questions;
- transfer SY0-701 content mastery;
- change readiness scoring;
- add AI-generated production questions without human review;
- automatically promote candidate content into the default launch bank.

## 13. Implementation-plan boundary

After this written spec is explicitly approved, the implementation plan should separate work into at least:

1. taxonomy refinement and validation;
2. metadata/semantic-family contract and tests;
3. official-source inventory and authoring ledger;
4. five ten-question author/review batches;
5. candidate-bank compile/validation;
6. Phase-1 acceptance report and promotion decision.

Each stage must be independently reviewable and must preserve the existing import-versus-approval boundary.