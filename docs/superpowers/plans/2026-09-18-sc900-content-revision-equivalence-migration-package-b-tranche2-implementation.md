# SC-900 Content-Revision Equivalence Migration Package B Tranche 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task **only after a separate exact-head implementation authorization**. This design package does **not** authorize executing the tasks below.

**Goal:** Build and prove a bounded Tranche-2 candidate bank that continues answer-length leakage reduction from the admitted T1 candidate through wording-only A–D edits, with Microsoft Learn-backed semantic-equivalence evidence and Package A admission/migration proof, without activating production.

**Architecture:** Chained Package B. T2 source is the admitted T1 candidate `sc900_bank_v8_length_rebalanced_t1.json`. A human-reviewed T2 edit-set records only semantically equivalent A–D wording changes. A deterministic builder produces `sc900_bank_v8_length_rebalanced_t2.json`, per-question review receipts, and a hash-bound `t1 → t2` manifest. Existing `admit_content_revision`, `migrate_progress_payload`, and `migrate_session_payload` prove continuity from T1 to T2. Production bank selection, registry activation, EXE rebuild, and release remain Package C.

**Tech Stack:** Python 3.11, stdlib `json`/`hashlib`/`argparse`, `unittest`, existing `answer_length_audit.py`, `content_revision_authority.py`, `content_revision_migration.py`, `tools.lint_bank`, `tools.run_quality_checks`, `tools.verify_installation`.

**Spec:**

- `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche2-design.md`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/12-PACKAGE-B-TRANCHE2-DESIGN.md`
- Parent leakage design: `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`
- Package A: `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Proposed implementation work ID: `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE2-001`.
- Proposed implementation branch: `implementation/sc900-content-revision-equivalence-migration-B-tranche2-001`.
- Exact implementation base SHA must be supplied by a later operator prompt. Do not start from this design branch.
- T2 source bank: `sc900_bank_v8_length_rebalanced_t1.json`.
- T2 source SHA-256 must remain `45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8`.
- Production bank `sc900_bank_v8_final.json` SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.
- Production EXE SHA-256 must remain `9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558`.
- T2 candidate filename: `sc900_bank_v8_length_rebalanced_t2.json`; distinct from both `final.json` and the T1 candidate.
- Version-1 changes: keyed `choices[A]`–`choices[D]` wording only.
- Question count remains 454. Canonical IDs, prompt, correct keys, letter mapping, question type, objective, domain, topics, `exam_calibration_tier`, `exam_simulation_eligible`, `study_focus`, chapter/subtitle, explanations, reasoning steps, calibration version, and all other non-choice fields remain unchanged.
- No filler, mechanical equal-length padding, copied Practice Assessment wording, third-party protected wording, correct-key changes, prompt changes, explanation changes, or semantic distractor replacement (different wrong concept).
- Every edited question must have at least one normalized `https://learn.microsoft.com/` authority reference in both its review receipt and manifest edge.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains exactly `{}`.
- T1 SKIP IDs must not be silently re-queued: `sc900_mlc_q173`, `q070`, `q116`, `q085`, `q253`, `q075`, `q155`.
- T1 EDIT residuals are not in the primary T2 queue.
- Repair posture: prefer two-sided equivalent rebalancing. Do not default to correct-only tightening.
- Production activation, Package C, EXE rebuild, T3+, and merge are not authorized by this plan.
- PR #13, recovery branches, and `sc900-v8.0.0-baseline` remain untouched.
- Primary design queue is 50 unreviewed questions listed in the T2 design. Semantic review may SKIP any item; a smaller executed set is allowed.
- TDD-first where code is introduced. Semantic edits fail closed when equivalence cannot be established.
- Package B statistical target is not weakened. T2 is not Package B closure.

```text
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T2 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
```

## File Map

**Create**

- `tools/build_package_b_tranche2.py` — deterministic T2 candidate/review/manifest builder; no semantic inference; source is the T1 candidate.
- `tests/test_package_b_tranche2.py` — builder, exact `t1 → t2` admission, and T1-bound continuity tests.
- `sc900_bank_v8_length_rebalanced_t2.json` — T2 candidate generated from the T1 candidate (implementation package only).
- `content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T2/*.json`
- `content_revision_evidence/manifests/sc900_answer_length_rebalance_t2.json`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/14-PACKAGE-B-TRANCHE2-SEMANTIC-REVIEW.json`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/15-PACKAGE-B-TRANCHE2-CANDIDATE-METRICS.json`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/16-PACKAGE-B-TRANCHE2-VERIFICATION.md`

**Reuse unchanged**

- `answer_length_audit.py`
- `tools/audit_answer_length.py`
- `content_revision_authority.py`
- `content_revision_migration.py`
- T1 tests and T1 evidence files

**Intentionally unchanged**

- `sc900_bank_v8_final.json`
- `sc900_bank_v8_length_rebalanced_t1.json`
- `content_revision_registry.py` (`AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}`)
- `cert_profile_sc900.json`
- `cert_config.py`
- `question_identity.py`
- `SC900TestLearningEngine.exe`
- T1 tests (`tests/test_package_b_tranche1.py`), except that new T2 tests must not copy the shallow nonempty-reason partial-transition assertion. Pin finite `RevisionFailureReason` values on T2 negative twins.

## Design candidate queue

Not an approved EDIT set. Implementation semantic review starts from these 50 IDs and must resolve every row to `EDIT` or `SKIP`:

`sc900_mlc_q125`, `sc900_p3_q039`, `sc900_mlc_q054`, `sc900_mlc_q182`, `sc900_mlc_q278`, `sc900_p3_q090`, `sc900_mlc_q216`, `sc900_mlc_q041`, `sc900_mlc_q250`, `sc900_mlc_q046`, `sc900_mlc_q300`, `sc900_mlc_q012`, `sc900_p2_q011`, `sc900_p3_q067`, `sc900_p2_q004`, `sc900_mlc_q089`, `sc900_p3_q086`, `sc900_p2_q020`, `sc900_mlc_q252`, `sc900_mlc_q257`, `sc900_p3_q099`, `sc900_mlc_q288`, `sc900_p2_q005`, `sc900_mlc_q141`, `sc900_p3_q002`, `sc900_mlc_q137`, `sc900_p3_q047`, `sc900_mlc_q122`, `sc900_p1_q047`, `sc900_p3_q057`, `sc900_mlc_q126`, `sc900_mlc_q277`, `sc900_mlc_q254`, `sc900_mlc_q074`, `sc900_mlc_q138`, `sc900_mlc_q097`, `sc900_mlc_q267`, `sc900_p3_q050`, `sc900_mlc_q188`, `sc900_mlc_q280`, `sc900_mlc_q140`, `sc900_mlc_q034`, `sc900_p2_q013`, `sc900_p3_q034`, `sc900_p3_q054`, `sc900_mlc_q059`, `sc900_mlc_q295`, `sc900_mlc_q221`, `sc900_p1_q033`, `sc900_mlc_q217`

Domain mix: security 19, Entra 14, compliance 12, SCI 5.

---

### Task 1: T2 builder RED tests

**Files:**

- Create: `tests/test_package_b_tranche2.py`
- Create: `tools/build_package_b_tranche2.py`

**Requirements:**

- Builder refuses to run if T1 source SHA-256 ≠ `45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8`.
- Builder refuses `EDIT` rows that change non-choice fields, correct keys, or letter mapping.
- Builder refuses missing Learn URLs, unresolved queue rows, or T1 SKIP IDs appearing as `EDIT`.
- Builder writes a distinct target filename and a manifest whose `source_bank.filename` is the T1 candidate and `target_bank.filename` is the T2 candidate.
- Synthetic fixture tests must go RED before implementation.

```text
python -m unittest tests.test_package_b_tranche2 -q
```

### Task 2: T2 builder GREEN

Implement the minimal deterministic builder. No semantic inference. Semantic review JSON is the only edit source.

Commit when focused builder tests PASS and no production/T1 files changed.

### Task 3: Semantic review of the T2 queue

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/14-PACKAGE-B-TRANCHE2-SEMANTIC-REVIEW.json`

Every queue ID must become `EDIT` or `SKIP`. `EDIT` requires exact after A–D strings, `EQUIVALENT` on all four choices, Learn authority, and a review note. Prefer two-sided rebalancing. Do not pad. Do not include T1 SKIP IDs. Do not treat the design queue as pre-approved.

This task is the only place T2 wording is authored, and only in the later implementation package.

### Task 4: Build T2 candidate and evidence

Run the builder against the T1 candidate and Task 3 review. Stop on admission failure.

Immediately verify:

```text
T1 candidate SHA-256 unchanged
final.json SHA-256 unchanged
AUTHORIZED_CONTENT_REVISION_MANIFESTS == {}
```

### Task 5: Real T2 admission, continuity, and leakage gates

**Files:**

- Modify: `tests/test_package_b_tranche2.py`
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/15-PACKAGE-B-TRANCHE2-CANDIDATE-METRICS.json`

Prove:

- `admit_content_revision` PASS against T1 source, T2 target, T2 reviews/manifest.
- Progress and session migration from **T1-bound** fixtures to T2, including idempotence.
- Negative twins with finite reasons (tamper, missing Learn URL, wrong T2 hash, non-choice drift). Do not assert merely nonempty reasons.
- T2 candidate strict-longest ≤ T1 candidate 287 / 449, or a documented quality-neutral exception for specific skipped IDs.
- No material shortest-answer or positional substitution.
- `python -m tools.lint_bank --bank sc900_bank_v8_length_rebalanced_t2.json --allow-warnings`

```text
python -m tools.audit_answer_length --bank sc900_bank_v8_length_rebalanced_t2.json --json-out docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/15-PACKAGE-B-TRANCHE2-CANDIDATE-METRICS.json
```

### Task 6: Verification receipt and stop

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/16-PACKAGE-B-TRANCHE2-VERIFICATION.md`

Run Package A + T1 + T2 focused tests, identity/session wall, quality checks, both source and candidate lints, and installation verification. Record hashes, edited IDs, skipped IDs, leakage before/after versus T1, registry `{}`, and:

```text
PACKAGE_C_STARTED = NO
MERGE_AUTHORIZED = NO
PRODUCTION_ACTIVATION = NO
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T2 = NO
```

Push only if a later operator prompt authorizes it. Stop for independent external review. Do not merge, activate, register, rebuild the EXE, or open T3/Package C.

## Plan self-review

- T2 is sourced from the admitted T1 candidate, not from a collapsed `final.json` rebuild.
- Production default bank and registry stay frozen.
- Statistical Package B target is unchanged and not claimed as T2 success.
- T1 SKIP set is preserved.
- Two-sided repair is the default method because T1 correct-only edits did not cross.
- Package C activation from `final.json` is explicitly deferred.
