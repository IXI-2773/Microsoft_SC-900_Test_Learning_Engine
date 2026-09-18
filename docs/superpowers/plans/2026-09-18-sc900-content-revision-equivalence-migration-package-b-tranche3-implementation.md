# SC-900 Content-Revision Equivalence Migration Package B Tranche 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task **only after a separate exact-head implementation authorization**. This design package does **not** authorize executing the tasks below.

**Goal:** Build and prove a bounded Tranche-3 candidate bank that continues answer-length leakage reduction from the implemented T2 candidate through wording-only A–D edits, with Microsoft Learn-backed semantic-equivalence evidence and Package A admission/migration proof, without activating production.

**Architecture:** Chained Package B. T3 source is the T2 candidate `sc900_bank_v8_length_rebalanced_t2.json`. A human-reviewed T3 edit-set records only semantically equivalent A–D wording changes. A deterministic builder produces `sc900_bank_v8_length_rebalanced_t3.json`, per-question review receipts, and a hash-bound `t2 → t3` manifest. Existing `admit_content_revision`, `migrate_progress_payload`, and `migrate_session_payload` prove continuity from T2 to T3. Production bank selection, registry activation, EXE rebuild, and release remain Package C.

**Tech Stack:** Python 3.11, stdlib `json`/`hashlib`/`argparse`, `unittest`, existing `answer_length_audit.py`, `content_revision_authority.py`, `content_revision_migration.py`, `tools.lint_bank`, `tools.run_quality_checks`, `tools.verify_installation`.

**Spec:**

- `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche3-design.md`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/17-PACKAGE-B-TRANCHE3-DESIGN.md`
- Parent leakage design: `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`
- Package A: `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Proposed implementation work ID: `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE3-001`.
- Proposed implementation branch: `implementation/sc900-content-revision-equivalence-migration-B-tranche3-001`.
- Exact implementation base SHA must be supplied by a later operator prompt and must contain T2 candidate SHA-256 `9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800` and fingerprint `34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b`. Do not start from this design branch.
- T3 source bank: `sc900_bank_v8_length_rebalanced_t2.json`.
- Production bank `sc900_bank_v8_final.json` SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.
- T3 candidate filename: `sc900_bank_v8_length_rebalanced_t3.json`; distinct from `final.json`, the T1 candidate, and the T2 candidate.
- Version-1 changes: keyed `choices[A]`–`choices[D]` wording only.
- Question count remains 454. Canonical IDs, prompt, correct keys, letter mapping, question type, objective, domain, topics, `exam_calibration_tier`, `exam_simulation_eligible`, `study_focus`, chapter/subtitle, explanations, reasoning steps, calibration version, and all other non-choice fields remain unchanged.
- No filler, mechanical equal-length padding, copied Practice Assessment wording, third-party protected wording, correct-key changes, prompt changes, explanation changes, or semantic distractor replacement (different wrong concept).
- Every edited question must have at least one normalized `https://learn.microsoft.com/` authority reference in both its review receipt and manifest edge.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains exactly `{}`.
- T1 SKIP IDs must not be silently re-queued: `sc900_mlc_q173`, `q070`, `q116`, `q085`, `q253`, `q075`, `q155`.
- T2 SKIP `sc900_mlc_q046` must not be silently re-queued.
- Repair posture: `MIXED_BY_CANDIDATE`. Prefer distractor-only on second-pass near-crossings; prefer two-sided on fresh sentence-like 21–50-gap items. Do not default to correct-only. Do not globally mandate distractor growth.
- Record max-distractor metric delta and per-option length deltas. Extra semantic inspection is required when any option grows by > 30 characters, total distractor growth exceeds 60, or the max-distractor metric grows by > 30. These are review triggers, not hard caps.
- Production activation, Package C, EXE rebuild, T4+, and merge are not authorized by this plan.
- Primary design queue is 36 questions listed in the T3 design. Semantic review may SKIP any item; a smaller executed set is allowed.
- TDD-first where code is introduced. Semantic edits fail closed when equivalence cannot be established.
- Package B statistical target is not weakened. T3 is not Package B closure.

## Design queue

Not an approved EDIT set. Implementation semantic review starts from these 36 IDs and must resolve every row to `EDIT` or `SKIP`:

`sc900_mlc_q288`, `sc900_mlc_q126`, `sc900_mlc_q138`, `sc900_mlc_q109`, `sc900_mlc_q177`, `sc900_mlc_q216`, `sc900_p3_q054`, `sc900_mlc_q295`, `sc900_mlc_q217`, `sc900_mlc_q134`, `sc900_mlc_q124`, `sc900_mlc_q291`, `sc900_mlc_q006`, `sc900_p3_q097`, `sc900_mlc_q016`, `sc900_p3_q062`, `sc900_p3_q070`, `sc900_mlc_q233`, `sc900_mlc_q299`, `sc900_p3_q006`, `sc900_mlc_q270`, `sc900_mlc_q281`, `sc900_mlc_q279`, `sc900_mlc_q296`, `sc900_mlc_q282`, `sc900_p3_q015`, `sc900_mlc_q157`, `sc900_mlc_q287`, `sc900_mlc_q266`, `sc900_mlc_q248`, `sc900_mlc_q262`, `sc900_mlc_q229`, `sc900_mlc_q236`, `sc900_mlc_q165`, `sc900_mlc_q228`, `sc900_mlc_q056`

Domain mix: compliance 12, security 12, Entra 8, SCI 4.

---

### Task 1: T3 builder RED tests

**Files:**

- Create: `tests/test_package_b_tranche3.py`
- Create: `tools/build_package_b_tranche3.py`

**Requirements:**

- Builder refuses to run if T2 source SHA-256 ≠ `9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800`.
- Builder refuses `EDIT` rows that change non-choice fields, correct keys, or letter mapping.
- Builder refuses missing Learn URLs, unresolved queue rows, T1 SKIP IDs appearing as `EDIT`, or T2 SKIP `sc900_mlc_q046` appearing as `EDIT`.
- Builder writes a distinct target filename and a manifest whose `source_bank.filename` is the T2 candidate and `target_bank.filename` is the T3 candidate.
- Synthetic fixture tests must go RED before implementation.

```text
python -m unittest tests.test_package_b_tranche3 -q
```

### Task 2: T3 builder GREEN

Implement the minimal deterministic builder. No semantic inference. Semantic review JSON is the only edit source.

Commit when focused builder tests PASS and no production/T1/T2 files changed.

### Task 3: Semantic review of the T3 queue

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/20-PACKAGE-B-TRANCHE3-SEMANTIC-REVIEW.json`

Every queue ID must become `EDIT` or `SKIP`. `EDIT` requires exact after A–D strings, `EQUIVALENT` on all four choices, Learn authority, and a review note that records max-distractor delta and per-option length deltas. Do not pad. Do not include prior SKIP IDs. Do not treat the design queue as pre-approved.

This task is the only place T3 wording is authored, and only in the later implementation package.

### Task 4: Build T3 candidate and evidence

Run the builder against the T2 candidate and Task 3 review. Stop on admission failure.

Immediately verify:

```text
T2 candidate SHA-256 unchanged
final.json SHA-256 unchanged
AUTHORIZED_CONTENT_REVISION_MANIFESTS == {}
```

### Task 5: Real T3 admission, continuity, and leakage gates

**Files:**

- Modify: `tests/test_package_b_tranche3.py`
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/21-PACKAGE-B-TRANCHE3-CANDIDATE-METRICS.json`

Prove:

- `admit_content_revision` PASS against T2 source, T3 target, T3 reviews/manifest.
- Progress and session migration from **T2-bound** fixtures to T3, including idempotence.
- Negative twins with finite reasons (tamper, missing Learn URL, wrong T3 hash, non-choice drift). Do not assert merely nonempty reasons.
- T3 candidate strict-longest ≤ T2 candidate 270 / 449, or a documented quality-neutral exception for specific skipped IDs.
- No material shortest-answer or positional substitution.
- `python -m tools.lint_bank --bank sc900_bank_v8_length_rebalanced_t3.json --allow-warnings`

### Task 6: Verification receipt and stop

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/22-PACKAGE-B-TRANCHE3-VERIFICATION.md`

Run Package A + T1 + T2 + T3 focused tests, identity/session wall, quality checks, source and candidate lints, and installation verification. Record hashes, edited IDs, skipped IDs, leakage before/after versus T2, registry `{}`, and:

```text
PACKAGE_C_STARTED = NO
MERGE_AUTHORIZED = NO
PRODUCTION_ACTIVATION = NO
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T3 = NO
T4_AUTHORIZED = NO
```

Push only if a later operator prompt authorizes it. Stop for independent external review. Do not merge, activate, register, rebuild the EXE, or open T4/Package C.

Do not modify `answer_length_audit.py` or `tools/build_package_b_tranche1.py` merely to clear pre-existing ruff I001. Do not treat the Q394–Q399 C-streak warning as T3 repair work.

## Plan self-review

- T3 is sourced from the T2 candidate, not from a collapsed `final.json` rebuild.
- Production default bank and registry stay frozen.
- Statistical Package B target is unchanged and not claimed as T3 success.
- T1 and T2 SKIP sets are preserved.
- Mixed-by-candidate repair is the default method because T1 correct-only did not cross and T2 distractor-only is a small sample.
- Package C activation from `final.json` is explicitly deferred.
