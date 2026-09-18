# SC-900 Content-Revision Equivalence Migration Package B Tranche 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task **only after a separate exact-head implementation authorization**. This design package does **not** authorize executing the tasks below.

**Goal:** Build and prove a bounded Tranche-4 candidate bank that continues answer-length leakage reduction from the implemented T3 candidate through wording-only A–D edits, with Microsoft Learn-backed semantic-equivalence evidence and Package A admission/migration proof, without activating production and without claiming Package B closure.

**Architecture:** Chained Package B. T4 source is the T3 candidate `sc900_bank_v8_length_rebalanced_t3.json`. A human-reviewed T4 edit-set records only semantically equivalent A–D wording changes. A deterministic builder produces a future T4 candidate bank, per-question review receipts, and a hash-bound `t3 → t4` manifest. Existing `admit_content_revision`, `migrate_progress_payload`, and `migrate_session_payload` prove continuity from T3 to T4. Production bank selection, registry activation, EXE rebuild, and release remain Package C.

**Tech Stack:** Python 3.11, stdlib `json`/`hashlib`/`argparse`, `unittest`, existing `answer_length_audit.py`, `content_revision_authority.py`, `content_revision_migration.py`, `tools.lint_bank`, `tools.run_quality_checks`, `tools.verify_installation`.

**Spec:**

- `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche4-design.md`
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/27-PACKAGE-B-TRANCHE4-DESIGN.md`
- Parent leakage design: `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`
- Package A: `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Proposed implementation work ID: `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-B-TRANCHE4-001`.
- Proposed implementation branch: `implementation/sc900-content-revision-equivalence-migration-B-tranche4-001`.
- Exact implementation base SHA must be supplied by a later operator prompt and must contain T3 candidate SHA-256 `d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b` and fingerprint `83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2`. Do not start from this design branch.
- T4 source bank: `sc900_bank_v8_length_rebalanced_t3.json`.
- Production bank `sc900_bank_v8_final.json` SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.
- T4 candidate filename must be distinct from `final.json`, the T1 candidate, the T2 candidate, and `sc900_bank_v8_length_rebalanced_t3.json`.
- Version-1 changes: keyed `choices[A]`–`choices[D]` wording only.
- Question count remains 454. Canonical IDs, prompt, correct keys, letter mapping, question type, objective, domain, topics, `exam_calibration_tier`, `exam_simulation_eligible`, `study_focus`, chapter/subtitle, explanations, reasoning steps, calibration version, and all other non-choice fields remain unchanged.
- No filler, mechanical equal-length padding, copied Practice Assessment wording, third-party protected wording, correct-key changes, prompt changes, explanation changes, or semantic distractor replacement (different wrong concept).
- Every edited question must have at least one normalized `https://learn.microsoft.com/` authority reference in both its review receipt and manifest edge.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains exactly `{}`.
- T1 SKIP IDs must not be silently re-queued: `sc900_mlc_q173`, `q070`, `q116`, `q085`, `q253`, `q075`, `q155`.
- T2 SKIP `sc900_mlc_q046` must not be silently re-queued.
- T3 SKIP IDs must not be silently re-queued: `sc900_mlc_q288`, `q126`, `q109`, `q216`, `sc900_p3_q054`, `q295`, `q217`. `q109` is padding-protected.
- Do not requeue T3 watch items `sc900_mlc_q056` and `sc900_mlc_q165` to chase remaining gaps.
- Repair posture: `SEMANTIC_CONTRAST_FIRST`. Prefer distractor-job contrast on T1 `CORRECT_ONLY` leftovers with unused product-job contrast; prefer two-sided on fresh sentence-like 21–40-gap items. Do not default to correct-only. Do not globally mandate distractor growth. Third or later edits are presumptively SKIP.
- Record max-distractor metric delta and per-option length deltas. Extra semantic inspection is required when any option grows by > 30 characters, total distractor growth exceeds 60, or the max-distractor metric grows by > 30. These are review triggers, not hard caps. Also record `TO_TIE` versus `TO_SHORTER`.
- Production activation, Package C, EXE rebuild, T5+, and merge are not authorized by this plan.
- Primary design queue is 64 questions listed in the T4 design. Semantic review may SKIP any item; a smaller executed set is allowed.
- TDD-first where code is introduced. Semantic edits fail closed when equivalence cannot be established.
- Package B statistical target is not weakened. T4 is not Package B closure.

## Design queue

Not an approved EDIT set. Implementation semantic review starts from these 64 IDs and must resolve every row to `EDIT` or `SKIP`:

`sc900_p2_q025`, `sc900_p3_q095`, `sc900_mlc_q129`, `sc900_mlc_q030`, `sc900_p3_q038`, `sc900_p3_q049`, `sc900_mlc_q169`, `sc900_mlc_q179`, `sc900_p3_q091`, `sc900_mlc_q063`, `sc900_mlc_q180`, `sc900_mlc_q025`, `sc900_mlc_q017`, `sc900_p1_q042`, `sc900_mlc_q018`, `sc900_p3_q077`, `sc900_p3_q075`, `sc900_p1_q048`, `sc900_mlc_q265`, `sc900_mlc_q224`, `sc900_mlc_q195`, `sc900_mlc_q077`, `sc900_mlc_q052`, `sc900_p3_q033`, `sc900_mlc_q133`, `sc900_mlc_q130`, `sc900_p3_q093`, `sc900_p3_q036`, `sc900_mlc_q212`, `sc900_p3_q064`, `sc900_p3_q089`, `sc900_mlc_q049`, `sc900_mlc_q015`, `sc900_p1_q031`, `sc900_p2_q041`, `sc900_p3_q024`, `sc900_p3_q018`, `sc900_mlc_q274`, `sc900_mlc_q275`, `sc900_mlc_q104`, `sc900_p3_q045`, `sc900_mlc_q171`, `sc900_p2_q031`, `sc900_mlc_q255`, `sc900_mlc_q298`, `sc900_mlc_q269`, `sc900_mlc_q272`, `sc900_p2_q015`, `sc900_mlc_q031`, `sc900_mlc_q123`, `sc900_mlc_q256`, `sc900_mlc_q226`, `sc900_mlc_q172`, `sc900_mlc_q222`, `sc900_mlc_q261`, `sc900_p3_q023`, `sc900_mlc_q073`, `sc900_mlc_q283`, `sc900_mlc_q131`, `sc900_mlc_q249`, `sc900_mlc_q241`, `sc900_mlc_q284`, `sc900_mlc_q174`, `sc900_mlc_q197`

Domain mix: security 24, compliance 15, Entra 17, SCI 8. Fresh 54, second-pass 10, multi-edit 0.

---

### Task 1: T4 builder RED tests

**Files:**

- Create: `tests/test_package_b_tranche4.py`
- Create: `tools/build_package_b_tranche4.py`

**Requirements:**

- Builder refuses to run if T3 source SHA-256 ≠ `d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b`.
- Builder refuses `EDIT` rows that change non-choice fields, correct keys, or letter mapping.
- Builder refuses missing Learn URLs, unresolved queue rows, or any T1/T2/T3 SKIP ID appearing as `EDIT`.
- Builder writes a distinct target filename and a manifest whose `source_bank.filename` is the T3 candidate and `target_bank.filename` is the T4 candidate.
- Synthetic fixture tests must go RED before implementation.

```text
python -m unittest tests.test_package_b_tranche4 -q
```

### Task 2: T4 builder GREEN

Implement the minimal deterministic builder. No semantic inference. Semantic review JSON is the only edit source.

Commit when focused builder tests PASS and no production/T1/T2/T3 files changed.

### Task 3: Semantic review of the T4 queue

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/28-PACKAGE-B-TRANCHE4-SEMANTIC-REVIEW.json`

Every queue ID must become `EDIT` or `SKIP`. `EDIT` requires exact after A–D strings, `EQUIVALENT` on all four choices, Learn authority, and a review note that records max-distractor delta and per-option length deltas. Do not pad. Do not include prior SKIP IDs. Do not treat the design queue as pre-approved. Do not reopen `q109`.

This task is the only place T4 wording is authored, and only in the later implementation package.

### Task 4: Build T4 candidate and evidence

Run the builder against the T3 candidate and Task 3 review. Stop on admission failure.

Immediately verify:

```text
T3 candidate SHA-256 unchanged
final.json SHA-256 unchanged
AUTHORIZED_CONTENT_REVISION_MANIFESTS == {}
```

### Task 5: Real T4 admission, continuity, and leakage gates

**Files:**

- Modify: `tests/test_package_b_tranche4.py`
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/29-PACKAGE-B-TRANCHE4-CANDIDATE-METRICS.json`

Prove:

- `admit_content_revision` PASS against T3 source, T4 target, T4 reviews/manifest.
- Progress and session migration from **T3-bound** fixtures to T4, including idempotence and already-current behavior.
- Negative twins with finite reasons (tamper, missing Learn URL, missing receipt, wrong T4 hash, wrong T3 hash, non-choice drift). Do not assert merely nonempty reasons.
- Closed-world changed-edge agreement: actual changed IDs == manifest EDIT set.
- T4 candidate strict-longest ≤ T3 candidate 256 / 449, or a documented quality-neutral exception for specific skipped IDs.
- Independent recomputation of strict-longest, unique-longest, unique denominator, domain rates, and `TO_TIE` / `TO_SHORTER`.
- No material shortest-answer or positional substitution.
- Registry freeze and runtime-bank freeze.
- `python -m tools.lint_bank --bank <t4-candidate>.json --allow-warnings`

### Task 6: Verification receipt and stop

**Files:**

- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/30-PACKAGE-B-TRANCHE4-VERIFICATION.md`

Run Package A + T1 + T2 + T3 + T4 focused tests, identity/session wall, quality checks, source and candidate lints, and installation verification. Record hashes, edited IDs, skipped IDs, leakage before/after versus T3, registry `{}`, and:

```text
PACKAGE_B_TARGET_REACHED = NO or YES with independent arithmetic
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T4 = NO unless the frozen target is actually met
T5_AUTHORIZED = NO
PACKAGE_C_STARTED = NO
PRODUCTION_ACTIVATION = NO
MERGE_AUTHORIZED = NO
```

Preserve without repairing: ruff I001 in `answer_length_audit.py` and `tools/build_package_b_tranche1.py`; C-streak Q394–Q399.

Do not merge. Do not begin T5 or Package C from the T4 implementation package.
