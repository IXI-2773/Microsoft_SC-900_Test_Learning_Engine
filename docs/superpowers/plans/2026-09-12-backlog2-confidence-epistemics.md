# BACKLOG-2 Confidence Epistemics Plan

> **For agentic workers:** Implement task-by-task with TDD. Preserve genuine RED evidence before production repair. Do not weaken BACKLOG-1 tests, import PR #13, or start BACKLOG-3.

**Goal:** Make confidence observed evidence with an Unknown-neutral absence state, capture-before-commit lifecycle, canonical answer-event identity, and one correction authority that reconciles derived state.

**Architecture:** Keep UI capture as Sure/Unsure/Guessed. Put normalization, diagnosis, event identity, legacy bind, and learner-memory replay in `confidence_epistemics.py`. Route ordinary answers through the restored popover. Route retag and super-confident through `correct_answer_event_confidence`.

**Tech Stack:** Python 3, stdlib `hashlib`/`uuid`, repository `unittest`, existing Tk popover helpers.

**Spec:** `docs/superpowers/specs/2026-09-12-backlog2-confidence-epistemics-design.md`

## Global Constraints

- Branch from `5610d25009b3006183cb0ac1a63a7c99d1f89c66` onto `implementation/sc900-backlog2-confidence-epistemics`.
- Do not branch from PR #18 or PR #13.
- Do not modify PR #19's branch. This is a child branch.
- Do not import or modify PR #13.
- Do not start Day 1 or BACKLOG-3.
- TDD: add failing tests, run them, then implement the smallest coherent repair.

---

### Task 1: Unknown semantics and diagnosis

**Files:**
- Add: `confidence_epistemics.py`
- Modify: `progress_store.py`
- Test: `tests/test_backlog2_confidence_epistemics.py`

- [ ] **Step 1: Write failing tests** for B2-004, B2-005, B2-008–B2-014, B2-031–B2-034.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Implement `normalize_confidence` → Unknown, observed-only require, miss-reason/recall-failure/review-grade contracts.**
- [ ] **Step 4: Run those tests GREEN.**

### Task 2: Capture-before-commit lifecycle

**Files:**
- Modify: `app_question_flow_mixin.py`
- Test: `tests/test_backlog2_confidence_epistemics.py`

- [ ] **Step 1: Write failing tests** for B2-001–B2-003, B2-006, B2-007, B2-039, B2-041, B2-043.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Restore `_show_feedback_popover`. Stage then capture. Keyboard cannot bypass. Exam/PROBE commit Unknown.**
- [ ] **Step 4: Run those tests GREEN.** Keep existing regression stubs of `_show_feedback_popover` working.

### Task 3: Canonical answer-event identity and correction authority

**Files:**
- Modify: `confidence_epistemics.py`, `session_models.py`, `progress_store.py`, `app.py`, `app_question_flow_mixin.py`, `app_session_persistence_mixin.py`
- Test: `tests/test_backlog2_confidence_epistemics.py`

- [ ] **Step 1: Write failing tests** for B2-015–B2-025, B2-029, B2-035–B2-038, B2-040.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Mint `answer_event_id` at commit; copy into all representations; implement `correct_answer_event_confidence` with history rebuild.**
- [ ] **Step 4: Route retag and super-confident through that authority.**
- [ ] **Step 5: Run those tests GREEN.**

### Task 4: Downstream consumers and restore

**Files:**
- Modify: `app_game_mixin.py`, `app_analytics_mixin.py`, `app_question_render_mixin.py`, `app_session_builder_mixin.py` only as required
- Test: `tests/test_backlog2_confidence_epistemics.py`

- [ ] **Step 1: Write failing tests** for B2-026–B2-028, B2-030.
- [ ] **Step 2: Neutral Unknown weighting. Invalidate Smart Practice/analytics caches. Recompute current-session quests from history.**
- [ ] **Step 3: Run GREEN.**

### Task 5: Verification, receipt, and draft PR

- [ ] **Step 1: Read-only verification on a clean tree.** Include BACKLOG-1 segments, BACKLOG-2 tests, Gate-3 CAND tests, full suite, quality gates.
- [ ] **Step 2: Write `docs/research/SC900-BACKLOG-2-CONFIDENCE-EPISTEMICS-001/01-CONFIDENCE-INTEGRITY-CLOSURE.md`.**
- [ ] **Step 3: Open a new draft PR from the BACKLOG-2 branch onto `publication/sc900-backlog1-without-measurement`. Do not merge. Do not retarget PR #19.**
