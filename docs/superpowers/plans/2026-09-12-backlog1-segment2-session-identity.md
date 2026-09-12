# BACKLOG-1 Segment 2 Session Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace question-number/stem-based ordinary session authority with canonical question IDs plus a deterministic bank/content fingerprint, and restore answer state by canonical ID with fail-closed validation.

**Architecture:** Add a dependency-neutral `session_identity.py` that computes bank fingerprints and canonical ordered session identity from Segment-1 question identity. Extend ordinary session schema in `session_store.py`/`session_models.py`, then integrate save/match/restore in `app_session_persistence_mixin.py`. CAND-01R3 experimental restoration remains isolated.

**Tech Stack:** Python 3, stdlib `hashlib`/`json`, repository `unittest` conventions, GitHub Actions verification.

**Spec:** `docs/superpowers/specs/2026-09-12-backlog1-segment2-session-identity-design.md`

## Global Constraints

- Start from `b19d5215dc1d79b02f4e805a510dcd9d901db259` through branch `implementation/sc900-backlog1-session-identity`.
- Do not modify PR #13 or frozen CAND-01R3 protocol/scientific artifacts.
- Do not start BACKLOG-2 confidence work or BACKLOG-3 builder-context work.
- Use Segment-1 canonical question identity; do not invent a competing question-ID format.
- Question number remains display/order/legacy metadata only.
- Legacy ordinary session snapshots that cannot prove bank/content epoch fail closed rather than silently resume.
- TDD: preserve RED evidence before production implementation and GREEN evidence afterward.

---

### Task 1: Canonical Bank and Session Identity Authority

**Files:**
- Create: `session_identity.py`
- Create: `tests/test_backlog1_segment2_session_identity.py`

**Interfaces:**
- Consumes: `question_identity.require_canonical_question_id(question)`.
- Produces: `bank_content_fingerprint(questions) -> str`, `ordered_question_ids(questions) -> list[str]`, `canonical_session_signature(mode, bank_fingerprint, question_ids) -> str`.

- [ ] **Step 1: Write failing tests** covering order/renumber-invariant bank fingerprint, content-sensitive fingerprint, duplicate/missing ID rejection, and ordered session-signature sensitivity.
- [ ] **Step 2: Run focused tests and preserve RED output.**
- [ ] **Step 3: Implement deterministic canonical projection and SHA-256 fingerprint.** Runtime/learner fields and `question_number` are excluded; projected questions are sorted by canonical ID.
- [ ] **Step 4: Implement ordered session signature from mode + fingerprint + ordered IDs.**
- [ ] **Step 5: Run focused tests GREEN and commit.**

### Task 2: Versioned Snapshot Schema and Fail-Closed Migration

**Files:**
- Modify: `session_models.py`
- Modify: `session_store.py`
- Test: `tests/test_backlog1_segment2_session_identity.py`

**Interfaces:**
- Consumes: Task-1 fingerprint/signature helpers.
- Produces: new ordinary snapshot schema containing `bank_fingerprint`, `question_ids`, `restore_question_ids`, and answer rows carrying `question_id`.

- [ ] **Step 1: Add RED tests** for fingerprint mismatch, legacy ordinary snapshot refusal, answer cardinality mismatch, duplicate/missing answer IDs, and canonical ID-based matching.
- [ ] **Step 2: Run focused tests RED.**
- [ ] **Step 3: Bump `SESSION_SCHEMA_VERSION` and extend TypedDicts.**
- [ ] **Step 4: Extend snapshot construction** so new snapshots include canonical IDs/fingerprint and ID-tagged answer rows while retaining number metadata.
- [ ] **Step 5: Harden `migrate_session_snapshot`** so new-schema snapshots validate canonical IDs, signatures, bank fingerprint input, answer cardinality, and answer identity. Legacy ordinary snapshots without proof fail closed.
- [ ] **Step 6: Replace ordinary `saved_session_matches_current` authority** with bank fingerprint + canonical session/restore IDs. Keep old helper compatibility only where needed to identify/reject legacy state, never to authorize new restore.
- [ ] **Step 7: Run focused tests GREEN and commit.**

### Task 3: Application Save/Restore by Canonical ID

**Files:**
- Modify: `app_session_persistence_mixin.py`
- Test: `tests/test_backlog1_segment2_session_identity.py`
- Test/adjust affected existing ordinary session regression tests as required.

**Interfaces:**
- Consumes: canonical bank fingerprint and schema from Tasks 1-2.
- Produces: ordinary session save/reload that binds and applies answer state by canonical question ID.

- [ ] **Step 1: Add RED integration tests** proving same stem/numbers with changed content cannot resume, renumbered unchanged canonical questions remain identifiable, positional swaps cannot misapply answers, and invalid snapshots are rejected/quarantined.
- [ ] **Step 2: Run integration tests RED.**
- [ ] **Step 3: Update current runtime identity construction** to derive current bank fingerprint and ordered canonical IDs from loaded master/session questions.
- [ ] **Step 4: Update session file/signature generation** to use canonical identity for ordinary sessions.
- [ ] **Step 5: Update snapshot save call** to persist fingerprint, current/restore IDs, numbers, and answer rows bound to IDs.
- [ ] **Step 6: Update restore** to map snapshot answer rows by canonical ID and apply each row only to the matching current canonical question; reject missing/duplicate/unresolvable IDs and cardinality mismatch.
- [ ] **Step 7: Keep CAND-01R3 restore branch unchanged in semantics** and avoid passing general session mutations into frozen measurement behavior.
- [ ] **Step 8: Run focused + affected ordinary regressions GREEN and commit.**

### Task 4: Verification, Documentation, and Frozen-Scope Audit

**Files:**
- Create: `docs/research/SC900-BACKLOG-1-IDENTITY-MIGRATION-001/02-SESSION-BANK-IDENTITY.md`
- Modify tests only if failures demonstrate legitimate stale assumptions; never weaken identity assertions to obtain green.

**Interfaces:**
- Consumes: completed Segment-2 implementation.
- Produces: acceptance evidence and exact scope audit.

- [ ] **Step 1: Run Segment-1 focused tests** to ensure the new branch did not regress canonical progress identity.
- [ ] **Step 2: Run Segment-2 focused tests.**
- [ ] **Step 3: Run affected session/application/CAND regression tests.**
- [ ] **Step 4: Run full `python -m unittest discover -s tests -v`.**
- [ ] **Step 5: Run repository `ruff`, `black --check`, and `mypy` commands using existing workflow conventions.**
- [ ] **Step 6: Compare branch to start and verify no frozen CAND-01R3 scientific artifact changed; verify PR #13 head/protocol hashes and protected refs remain unchanged.**
- [ ] **Step 7: Document schema before/after, fingerprint projection, legacy refusal/quarantine semantics, RED/GREEN counts, full verification, and exact changed files.**
- [ ] **Step 8: Commit documentation and stop. Do not begin Segment 3 or other backlogs automatically.**

## Self-review

- Spec coverage: B2, B3, B4, bank fingerprint, canonical IDs, ID-bound answers, cardinality, legacy fail-closed, and CAND isolation all have explicit tasks.
- No placeholder implementation steps remain.
- Interface names are consistent across tasks: `bank_content_fingerprint`, `ordered_question_ids`, `canonical_session_signature`.
- Scope excludes confidence and builder-context defects.