# SC-900 Content-Revision Equivalence Migration Package B Tranche 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and prove a bounded Tranche-1 candidate bank that reduces answer-length leakage through wording-only A-D choice edits, with exact Microsoft Learn-backed semantic-equivalence evidence and Package-A admission/migration proof, without activating production.

**Architecture:** Package B is a candidate-and-evidence pipeline layered on the already-merged Package-A authority/migration infrastructure. A pure deterministic audit ranks leakage outliers; a human-reviewed edit-set records only semantically equivalent A-D wording changes and Microsoft Learn references; a deterministic builder produces a distinct candidate bank, per-question review receipts, and an exact hash-bound manifest; existing `admit_content_revision`, `migrate_progress_payload`, and `migrate_session_payload` prove continuity. Production bank selection, registry activation, EXE rebuild, and release remain Package C.

**Tech Stack:** Python 3.11, stdlib `json`/`hashlib`/`dataclasses`/`argparse`, `unittest`, existing `question_identity.py`, `content_revision_authority.py`, `content_revision_migration.py`, `tools.lint_bank`, `tools.run_quality_checks`, `tools.verify_installation`.

**Spec:**
- `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`
- `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Exact implementation base: `main` at `3a23512d9ffd55dfa5681d406f7c69331393b1c0`.
- Authorized branch: `implementation/sc900-content-revision-equivalence-migration-B-tranche1-001`.
- Production source bank: `sc900_bank_v8_final.json`.
- Production source bank SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.
- Production EXE SHA-256 must remain `9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558`.
- Candidate bank filename: `sc900_bank_v8_length_rebalanced_t1.json`; it must be distinct from the source filename.
- Version-1 candidate changes are limited to keyed `choices[A]`, `choices[B]`, `choices[C]`, `choices[D]` wording only.
- Question count remains 454; canonical IDs, prompt, correct keys, letter mapping, question type, objective, domain, topics, `exam_calibration_tier`, `exam_simulation_eligible`, `study_focus`, chapter/subtitle, explanations, reasoning steps, calibration version, and all other non-choice fields remain unchanged.
- No filler, mechanical equal-length padding, copied Practice Assessment wording, third-party protected question wording, correct-key changes, prompt changes, explanation changes, or semantic distractor replacement.
- Every edited question must have at least one normalized `https://learn.microsoft.com/` authority reference in both its review receipt and manifest edge.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains exactly `{}` during Package B.
- Production bank activation, Package C, EXE rebuild, and merge are not authorized by this plan.
- PR #13, `research/sc900-cand01r3-measurement-001`, recovery branches, and `sc900-v8.0.0-baseline` remain untouched.
- Tranche 1 is bounded to the highest-severity safe cases, nominally 40-60 questions; if semantic review cannot safely support that many, use a smaller set and document skipped outliers.
- Each task is TDD-first where code is introduced. Semantic content edits are admitted only after explicit evidence review and fail closed when equivalence cannot be established.

---

## File Map

**Create**
- `answer_length_audit.py` — pure deterministic leakage metrics/ranking library.
- `tools/audit_answer_length.py` — CLI for baseline/candidate reports.
- `tools/build_package_b_tranche1.py` — deterministic candidate/review/manifest builder; no semantic inference.
- `tests/test_answer_length_audit.py` — synthetic audit regression tests.
- `tests/test_package_b_tranche1.py` — builder, exact admission, and real-candidate continuity tests.
- `sc900_bank_v8_length_rebalanced_t1.json` — distinct candidate bank generated from the exact production source.
- `content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1/*.json` — one review receipt per changed question.
- `content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json` — exact source→candidate manifest.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/08-PACKAGE-B-TRANCHE1-BASELINE.json` — machine-readable baseline audit/ranking.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/09-PACKAGE-B-TRANCHE1-SEMANTIC-REVIEW.json` — human-reviewed tranche selection/edit source.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json` — machine-readable candidate audit.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/11-PACKAGE-B-TRANCHE1-VERIFICATION.md` — closure receipt.

**Modify**
- `tools/run_quality_checks.py` — include new Python sources in quality checks if its source list is explicit.

**Intentionally unchanged**
- `sc900_bank_v8_final.json`
- `content_revision_registry.py` production registry contents (`AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}`)
- `question_identity.py`
- `cert_config.py`
- `SC900TestLearningEngine.exe`

---

### Task 1: Deterministic Answer-Length Audit Core

**Files:**
- Create: `answer_length_audit.py`
- Create: `tests/test_answer_length_audit.py`

**Interfaces:**
- Produces: `audit_questions(questions: Sequence[Mapping[str, Any]]) -> dict[str, Any]`
- Produces: `ranked_strict_longest_outliers(questions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]`
- Produces stable JSON-compatible metrics consumed by the CLI and Package-B receipt.

- [ ] **Step 1: Write synthetic failing tests for analyzability and length metrics**

Create fixtures with exact A-D strings and one correct letter. Tests must prove:

```python
result = audit_questions(fixtures)
assert result["analyzable_single_answer"] == 4
assert result["strict_longest_correct"]["count"] == 1
assert result["strict_shortest_correct"]["count"] == 1
assert result["unique_longest_heuristic"]["denominator"] == 3
assert result["unique_shortest_heuristic"]["denominator"] == 3
```

Use `len(text.strip())` for character length and `len(text.strip().split())` for word length. A question is analyzable only when `choices` is an exact A-D string mapping and `correct` resolves to exactly one A-D letter.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python -m unittest tests.test_answer_length_audit -q
```

Expected: import/function failures because `answer_length_audit.py` does not yet exist.

- [ ] **Step 3: Implement the minimal pure audit model**

`audit_questions()` must return JSON-compatible fields at minimum:

```text
question_count
analyzable_single_answer
skipped_question_ids
strict_longest_correct {count, denominator, rate}
correct_among_longest {count, denominator, rate}
strict_shortest_correct {count, denominator, rate}
unique_longest_heuristic {successes, denominator, rate}
unique_shortest_heuristic {successes, denominator, rate}
correct_letter_counts {A,B,C,D}
domains {<domain>: same key leakage metrics}
mean_correct_chars
mean_longest_distractor_chars
ranked_outliers[]
```

For strict-longest outlier severity use the deterministic tuple:

```python
absolute_gap = correct_chars - max_distractor_chars
relative_gap = absolute_gap / max(1, max_distractor_chars)
order = (-relative_gap, -absolute_gap, question_id)
```

Each ranked row records `question_id`, `domain`, `correct_letter`, all A-D char/word lengths, `absolute_gap`, and `relative_gap`.

- [ ] **Step 4: Add deterministic ordering/domain/position tests**

Prove ties are stable by canonical question ID, domain metrics use the same denominator rules as bank-level metrics, and A/B/C/D counts match fixture truth.

- [ ] **Step 5: Run focused tests GREEN**

```bash
python -m unittest tests.test_answer_length_audit -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add answer_length_audit.py tests/test_answer_length_audit.py
git commit -m "test: add deterministic answer-length leakage audit"
```

---

### Task 2: Baseline CLI and Exact Tranche Ranking

**Files:**
- Create: `tools/audit_answer_length.py`
- Modify: `tests/test_answer_length_audit.py`
- Create on execution: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/08-PACKAGE-B-TRANCHE1-BASELINE.json`
- Modify if required: `tools/run_quality_checks.py`

**Interfaces:**
- CLI: `python -m tools.audit_answer_length --bank <path> --json-out <path>`
- CLI exits non-zero on unreadable/malformed bank or missing `questions` list.
- JSON output is exactly the `audit_questions()` payload plus `bank_file_sha256` and `bank_content_fingerprint`.

- [ ] **Step 1: Add failing CLI integration test**

Use a temporary JSON bank and assert the CLI writes deterministic JSON with the expected SHA-256 and metrics. Add malformed-bank and missing-questions negative twins.

- [ ] **Step 2: Run focused test RED**

```bash
python -m unittest tests.test_answer_length_audit -q
```

Expected: CLI module missing/failing.

- [ ] **Step 3: Implement CLI without mutation**

Read the bank, call `audit_questions()`, compute raw file SHA-256 using `hashlib.sha256(path.read_bytes())`, compute content fingerprint using existing `question_identity.bank_content_fingerprint`, and write JSON with `sort_keys=True`, `indent=2`, UTF-8, terminating newline.

- [ ] **Step 4: Run focused tests GREEN**

```bash
python -m unittest tests.test_answer_length_audit -q
```

- [ ] **Step 5: Generate the production baseline report**

```bash
python -m tools.audit_answer_length \
  --bank sc900_bank_v8_final.json \
  --json-out docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/08-PACKAGE-B-TRANCHE1-BASELINE.json
```

Verify the source SHA exactly equals:

```text
177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
```

The report must reproduce the established baseline or stop and explain any discrepancy before candidate edits.

- [ ] **Step 6: Freeze the Tranche-1 review queue**

Take the first 50 strict-longest outliers from `ranked_outliers` as the review queue. The queue is review priority, not automatic edit authorization. Every queue entry must later end in either `EDIT` or `SKIP` with a concrete reason.

- [ ] **Step 7: Add the new Python sources to repository quality coverage if the quality tool uses an explicit file list**

Do not alter quality semantics; only include the new modules.

- [ ] **Step 8: Commit Task 2**

```bash
git add tools/audit_answer_length.py tests/test_answer_length_audit.py tools/run_quality_checks.py docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/08-PACKAGE-B-TRANCHE1-BASELINE.json
git commit -m "feat: freeze Package B tranche 1 leakage baseline"
```

---

### Task 3: Deterministic Package-B Evidence Builder

**Files:**
- Create: `tools/build_package_b_tranche1.py`
- Create: `tests/test_package_b_tranche1.py`

**Interfaces:**
- Consumes: exact source bank, human-reviewed semantic-review JSON, candidate output path, review root, manifest output path.
- Produces: candidate bank, one review JSON per `EDIT`, manifest JSON, and an `AdmissionResult` that must be PASS.
- Function:

```python
def build_package_b_tranche1(
    source_bank_path: Path,
    semantic_review_path: Path,
    candidate_bank_path: Path,
    review_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    ...
```

The returned summary contains `edited_question_ids`, source/target file SHA-256, source/target bank fingerprints, manifest SHA-256, review count, and admission status.

**Semantic-review input schema:**

```json
{
  "work_id": "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / PACKAGE-B / TRANCHE-1",
  "source_bank": "sc900_bank_v8_final.json",
  "candidate_bank": "sc900_bank_v8_length_rebalanced_t1.json",
  "review_queue": [
    {
      "question_id": "<canonical id>",
      "disposition": "EDIT",
      "after": {"A":"...","B":"...","C":"...","D":"..."},
      "semantic_review": {"A":"EQUIVALENT","B":"EQUIVALENT","C":"EQUIVALENT","D":"EQUIVALENT"},
      "authority_refs": ["https://learn.microsoft.com/..."],
      "review_note": "Concise factual note explaining why meaning and distractor role are preserved."
    }
  ]
}
```

`SKIP` rows contain `question_id`, `disposition: "SKIP"`, and a nonblank `review_note`; they do not alter the candidate and do not receive manifest edges.

- [ ] **Step 1: Write failing builder tests using a generated 454-question synthetic source bank**

Tests must prove:

1. two valid EDIT rows produce a distinct candidate, two review receipts, and an admitted manifest;
2. candidate differs only in A-D choice text for edited IDs;
3. source bytes remain unchanged;
4. candidate filename equal to source filename fails;
5. duplicate question IDs in the review queue fail;
6. unknown IDs fail;
7. EDIT with missing/non-Microsoft-only authority fails;
8. EDIT with any semantic value other than `EQUIVALENT` fails;
9. unchanged `after` choices fail because an edge for an unchanged question would be invalid;
10. `AUTHORIZED_CONTENT_REVISION_MANIFESTS` is never modified.

- [ ] **Step 2: Run builder tests RED**

```bash
python -m unittest tests.test_package_b_tranche1 -q
```

- [ ] **Step 3: Implement deterministic candidate generation**

Mechanically deep-copy the source bank and replace only exact A-D choice strings for `EDIT` rows. Validate that all source/candidate non-choice fields are deep-equal before writing.

Candidate JSON serialization must be deterministic:

```python
json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
```

- [ ] **Step 4: Implement per-question review receipt generation**

For each changed question write under:

```text
content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1/<question_id>.json
```

with exactly the Package-A review schema:

```text
question_id
from_content_fingerprint
to_content_fingerprint
before {A-D}
after {A-D}
semantic_review {A-D = EQUIVALENT}
correct_key_before
correct_key_after
authority_refs
disposition = APPROVED_FOR_FULL_CONTINUITY
```

Compute each raw review SHA-256 after writing.

- [ ] **Step 5: Implement manifest generation**

Write:

```text
content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json
```

with:

```text
schema_version = 1
manifest_kind = sc900_content_revision_equivalence
continuity_policy = FULL_CONTINUITY
permitted_change_class = WORDING_ONLY_LENGTH_REBALANCE
```

Edges are sorted by `question_id`, bind exact from/to fingerprints, use all Package-A boolean assertions `true`, all A-D `choice_semantics = EQUIVALENT`, `review_status = APPROVED`, exact review relative path/hash, and the same reviewed authority refs. Compute `payload_sha256` with `canonical_manifest_sha256()`.

- [ ] **Step 6: Require Package-A admission PASS before returning success**

Call:

```python
admit_content_revision(
    manifest,
    source_questions=source_questions,
    target_questions=target_questions,
    source_bank_path=source_bank_path,
    target_bank_path=candidate_bank_path,
    review_root=review_root,
)
```

Require `AdmissionStatus.PASS`, empty reasons, and non-`None` `admitted`.

- [ ] **Step 7: Run builder tests GREEN**

```bash
python -m unittest tests.test_package_b_tranche1 -q
```

- [ ] **Step 8: Commit Task 3**

```bash
git add tools/build_package_b_tranche1.py tests/test_package_b_tranche1.py tools/run_quality_checks.py
git commit -m "feat: add deterministic Package B evidence builder"
```

---

### Task 4: Human Semantic Review and Candidate Construction

**Files:**
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/09-PACKAGE-B-TRANCHE1-SEMANTIC-REVIEW.json`
- Generate: `sc900_bank_v8_length_rebalanced_t1.json`
- Generate: `content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1/*.json`
- Generate: `content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json`

**Interfaces:**
- Consumes: the frozen top-50 baseline review queue.
- Produces: bounded `EDIT` rows plus documented `SKIP` rows; the builder admits only exact EDIT rows.

- [ ] **Step 1: Review queue entries in baseline rank order**

For each question, first inspect prompt, all A-D choices, correct key, explanation, objective/domain/tier, and the baseline length gap. Choose only one of:

```text
EDIT — all four resulting propositions can be proven semantically equivalent and the correct key remains uniquely defensible.
SKIP — safe equivalence cannot be proven without changing prompt, explanation, answer key, distractor concept, or pedagogical quality.
```

- [ ] **Step 2: For every EDIT, verify current official Microsoft Learn authority**

Record at least one exact `https://learn.microsoft.com/` URL that supports the product/capability propositions needed to preserve correctness and distractor roles. Supplemental references may be included, but Microsoft Learn is mandatory.

- [ ] **Step 3: Author only meaning-preserving A-D wording changes**

Preferred order:

1. tighten an unnecessarily verbose correct choice;
2. strengthen unrealistically terse distractors using the same underlying wrong propositions;
3. rebalance both when safe;
4. otherwise SKIP.

Do not change a distractor to a different wrong concept. Do not introduce filler. Do not force equal character counts.

- [ ] **Step 4: Complete every reviewed queue row**

No queue row may remain unresolved. Every `EDIT` row has exact after A-D strings, all four semantic dispositions `EQUIVALENT`, authority refs, and a nonblank review note. Every `SKIP` row has a concrete reason.

- [ ] **Step 5: Run the deterministic builder**

```bash
python -m tools.build_package_b_tranche1 \
  --source-bank sc900_bank_v8_final.json \
  --semantic-review docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/09-PACKAGE-B-TRANCHE1-SEMANTIC-REVIEW.json \
  --candidate-bank sc900_bank_v8_length_rebalanced_t1.json \
  --review-root content_revision_evidence/reviews \
  --manifest content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json
```

Stop on any admission failure; do not patch around Package-A rejection.

- [ ] **Step 6: Verify source-bank immutability immediately**

```bash
python -c "import hashlib,pathlib; p=pathlib.Path('sc900_bank_v8_final.json'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

Required:

```text
177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
```

- [ ] **Step 7: Commit semantic review + generated candidate/evidence as one auditable unit**

```bash
git add docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/09-PACKAGE-B-TRANCHE1-SEMANTIC-REVIEW.json sc900_bank_v8_length_rebalanced_t1.json content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1 content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json
git commit -m "content: build Package B tranche 1 leakage candidate"
```

---

### Task 5: Real Candidate Admission, Continuity, and Leakage Gates

**Files:**
- Modify: `tests/test_package_b_tranche1.py`
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json`

**Interfaces:**
- Consumes: real source bank, candidate bank, review receipts, manifest.
- Produces: exact admission proof, progress/session continuity proof, before/after leakage evidence.

- [ ] **Step 1: Add real-package admission test**

Load the real manifest and call `admit_content_revision(...)` against `sc900_bank_v8_final.json`, `sc900_bank_v8_length_rebalanced_t1.json`, and `content_revision_evidence/reviews`. Assert PASS, no reasons, `admitted is not None`, edge count equals actual changed-question count, and edge IDs equal the exact changed fingerprint set.

- [ ] **Step 2: Add real progress migration test**

Build an in-memory source-bound progress payload containing at least one changed question and one unchanged question. Call:

```python
migrate_progress_payload(payload, target_questions, admitted, "2026-09-17T00:00:00")
```

Assert learner records/history are deep-equal, bank fingerprint advances to target, changed active fingerprint advances to edge.to, unchanged fingerprint stays identical, lineage is appended exactly once, and a second application returns `MIGRATION_ALREADY_APPLIED` without duplication.

- [ ] **Step 3: Add real saved-session migration test**

Use an existing valid canonical source session fixture/pattern, include a changed completed answer and a changed unanswered pending selection, and call `migrate_session_payload(...)`. Assert completed answer is preserved, changed unanswered pending state is cleared locally, session-answer history is unchanged, target bank file/fingerprint/signatures are regenerated, and unchanged state remains intact.

- [ ] **Step 4: Add fail-closed negative twins**

At minimum prove:

```text
manifest/review tamper -> admission FAIL
missing Learn authority -> admission FAIL
wrong candidate hash -> admission FAIL
source progress changed record already at edge.to -> migration FAIL
candidate with non-choice drift -> admission FAIL
```

- [ ] **Step 5: Run Package-B focused tests**

```bash
python -m unittest tests.test_answer_length_audit tests.test_package_b_tranche1 -q
```

Expected: PASS.

- [ ] **Step 6: Generate candidate leakage metrics**

```bash
python -m tools.audit_answer_length \
  --bank sc900_bank_v8_length_rebalanced_t1.json \
  --json-out docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json
```

Compare against baseline. Tranche admission requires improvement or justified neutrality, no material shortest-answer substitution, no material A/B/C/D positional substitution, and no materially worsened domain without documented reason. Statistical improvement never overrides semantic quality.

- [ ] **Step 7: Candidate bank lint**

```bash
python -m tools.lint_bank --bank sc900_bank_v8_length_rebalanced_t1.json --allow-warnings
```

Expected: PASS with no new unexpected warning class.

- [ ] **Step 8: Commit Task 5**

```bash
git add tests/test_package_b_tranche1.py docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json
git commit -m "test: prove Package B tranche 1 candidate continuity"
```

---

### Task 6: Full Verification and Package-B Tranche-1 Receipt

**Files:**
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/11-PACKAGE-B-TRANCHE1-VERIFICATION.md`

**Interfaces:**
- Produces exact closure evidence for external review; does not authorize merge or activation.

- [ ] **Step 1: Run Package-A + Package-B focused verification**

```bash
python -m unittest \
  tests.test_content_revision_authority \
  tests.test_content_revision_migration \
  tests.test_content_revision_app_integration \
  tests.test_answer_length_audit \
  tests.test_package_b_tranche1 -q
```

Expected: PASS.

- [ ] **Step 2: Run the identity/session regression wall**

```bash
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment1_adversarial_review \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment2_session_app_integration \
  tests.test_backlog1_segment3_adversarial_closure \
  tests.test_sc900_final_bank_activation_migration -q
```

Expected: PASS.

- [ ] **Step 3: Run full unittest discovery**

```bash
python -m unittest discover -s tests -q
```

Expected: zero failures/errors.

- [ ] **Step 4: Run quality checks**

```bash
python -m tools.run_quality_checks
```

Expected: PASS.

- [ ] **Step 5: Run source and candidate bank lint**

```bash
python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings
python -m tools.lint_bank --bank sc900_bank_v8_length_rebalanced_t1.json --allow-warnings
```

- [ ] **Step 6: Run installation verification**

```bash
python -m tools.verify_installation
```

Expected: PASS against still-active production configuration.

- [ ] **Step 7: Recompute immutable hashes and registry state**

Record exact SHA-256 for source bank, candidate bank, manifest, and production EXE. Assert source bank and EXE equal the frozen values and `AUTHORIZED_CONTENT_REVISION_MANIFESTS == {}`.

- [ ] **Step 8: Write the verification receipt**

`11-PACKAGE-B-TRANCHE1-VERIFICATION.md` must record:

```text
BASE_MAIN_SHA
BRANCH
IMPLEMENTATION_HEAD
EXACT_HEAD
SOURCE_BANK
SOURCE_BANK_SHA256
CANDIDATE_BANK
CANDIDATE_BANK_SHA256
SOURCE_BANK_CONTENT_FINGERPRINT
CANDIDATE_BANK_CONTENT_FINGERPRINT
EDITED_QUESTION_COUNT
EDITED_QUESTION_IDS
SKIPPED_REVIEW_QUEUE_IDS_WITH_REASONS
MANIFEST_PATH
MANIFEST_SHA256
REVIEW_ARTIFACT_COUNT
PACKAGE_A_ADMISSION_RESULT
BASELINE_LEAKAGE_METRICS
CANDIDATE_LEAKAGE_METRICS
DOMAIN_METRICS
SHORTEST_BIAS_RESULT
POSITION_BIAS_RESULT
FOCUSED_TEST_RESULT
IDENTITY_SESSION_WALL_RESULT
FULL_TEST_RESULT
QUALITY_RESULT
SOURCE_BANK_LINT_RESULT
CANDIDATE_BANK_LINT_RESULT
INSTALLATION_RESULT
PRODUCTION_BANK_SHA256
PRODUCTION_EXE_SHA256
AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}
PACKAGE_C_STARTED = NO
MERGE_AUTHORIZED = NO
```

- [ ] **Step 9: Self-review diff boundaries**

Confirm no changes to `sc900_bank_v8_final.json`, `cert_config.py`, `content_revision_registry.py` registry contents, EXE, PR #13 authority, or recovery refs. Confirm candidate question differences are exactly A-D choice text for manifest edge IDs.

- [ ] **Step 10: Commit receipt and stop**

```bash
git add docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/11-PACKAGE-B-TRANCHE1-VERIFICATION.md
git commit -m "docs: record Package B tranche 1 verification"
```

Push the same branch and STOP for independent external review. Do not open Package C, activate the candidate, register the manifest, rebuild the EXE, or merge without separate exact-head authorization.

---

## Plan Self-Review

- **Spec coverage:** audit, deterministic ranking, bounded tranche, semantic review, Microsoft Learn authority, candidate bank, per-question receipts, exact manifest, Package-A admission, progress/session continuity, shortest/position safeguards, full regression, production immutability, and stop gates are all mapped to explicit tasks.
- **No architecture bypass:** the plan uses existing Package-A admission/migration functions and does not weaken `question_identity.py` or activate the registry.
- **No hidden Package C work:** production selection, registry activation, EXE rebuild, Windows QA, and release are explicitly excluded.
- **Type/interface consistency:** builder and test calls use the merged `admit_content_revision(...)`, `migrate_progress_payload(...)`, and `migrate_session_payload(...)` interfaces.
- **No unresolved implementation placeholders:** dynamic question IDs and wording are produced by the deterministic audit plus human semantic-review task rather than guessed in advance; every reviewed queue entry must resolve to explicit EDIT or SKIP evidence before candidate construction.
