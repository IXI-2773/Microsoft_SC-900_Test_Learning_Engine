# BACKLOG-3 Builder Resume Identity Plan

> **For agentic workers:** Implement task-by-task with TDD. Preserve genuine RED evidence before production repair. Do not weaken BACKLOG-1 or BACKLOG-2 tests, import PR #13, start Day 1, or treat mtime as identity.

**Goal:** Make builder-request identity a first-class versioned authority so randomize and other material construction choices cannot collapse, and so resume/cleanup match only exact canonical builder identity.

**Architecture:** Put one canonical normalizer, fingerprint, and migration status in `builder_identity.py`. Reuse it from snapshot persist/migrate, resume discovery, cleanup, restore validation, and builder UI round-trip. Keep BACKLOG-1 bank/question identity unchanged.

**Tech Stack:** Python 3, stdlib `hashlib`/`json`, repository `unittest`, existing session persistence mixins.

**Spec:** `docs/superpowers/specs/2026-09-12-backlog3-builder-resume-identity-design.md`

## Global Constraints

- Branch from `baf69ecf773cc929d7fb84a00494b434595aa8f3` onto `implementation/sc900-backlog3-builder-resume-identity`.
- Do not branch from `main`, PR #18, PR #19, or PR #13.
- Do not modify PR #19 or PR #20 heads.
- Do not import or modify PR #13.
- Do not start Day 1.
- TDD: add failing tests, run them, then implement the smallest coherent repair.

---

### Task 1: Canonical builder identity

**Files:**
- Add: `builder_identity.py`
- Modify: `session_models.py`, `session_store.py`
- Test: `tests/test_backlog3_builder_resume_identity.py`

- [ ] **Step 1: Write failing tests** for B3-001–B3-021, B3-040–B3-044, plus All-visible vs numeric count.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Implement `normalize_builder_context`, fingerprint, versioned identity, legacy statuses, fail-closed validation.**
- [ ] **Step 4: Persist builder identity on ordinary snapshots without weakening BACKLOG-1 fields.**
- [ ] **Step 5: Run those tests GREEN.**

### Task 2: Resume, cleanup, mtime, file identity

**Files:**
- Modify: `session_store.py`, `app_session_persistence_mixin.py`
- Test: `tests/test_backlog3_builder_resume_identity.py`

- [ ] **Step 1: Write failing tests** for B3-022–B3-039, B3-045, B3-048–B3-054.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Match and clear only by canonical fingerprint. mtime ranks equivalents only. Append builder fingerprint to ordinary session filenames. Leave CAND paths unchanged.**
- [ ] **Step 4: Run those tests GREEN.**

### Task 3: Wrapper, UI round-trip, Smart Practice intent

**Files:**
- Modify: `app_session_persistence_mixin.py`, `app_session_builder_mixin.py`
- Test: `tests/test_backlog3_builder_resume_identity.py`

- [ ] **Step 1: Write failing tests** for wrapper `randomize=True/False`, UI round-trip, Smart Practice requested randomize surviving builder identity.
- [ ] **Step 2: Forward explicit kwargs. Preserve `All visible`. Restore UI from canonical context. Do not let operational no-reshuffle overwrite builder intent.**
- [ ] **Step 3: Run GREEN.**

### Task 4: Verification, receipt, and draft PR

- [ ] **Step 1: Read-only verification on a clean tree.** Include BACKLOG-1 segments, BACKLOG-2 tests, BACKLOG-3 tests, Gate-3 CAND tests, Phase-3 tests, full suite, quality gates.
- [ ] **Step 2: Write `docs/research/SC900-BACKLOG-3-BUILDER-RESUME-IDENTITY-001/01-BUILDER-IDENTITY-CLOSURE.md`.**
- [ ] **Step 3: Open a new draft PR from the BACKLOG-3 branch onto `implementation/sc900-backlog2-confidence-epistemics`. Do not merge. Do not retarget PR #19 or PR #20.**
