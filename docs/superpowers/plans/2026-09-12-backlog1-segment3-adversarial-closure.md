# BACKLOG-1 Segment 3 Adversarial Closure Plan

> **For agentic workers:** Implement task-by-task with TDD. Preserve genuine RED evidence before production repair. Do not weaken Segment-1/Segment-2 tests or frozen CAND scientific semantics.

**Goal:** Close residual question-number identity across progress content epoch, history, session answer history, analytics/Smart Practice joins, follow-up dedup, and bank-revision migration, then make the full unittest suite green without altering CAND-01R3 scientific authority.

**Architecture:** One durable content projection shared by session and progress. Segment-1 number→ID migration stays intact. A new epoch-bind migration stamps per-question content fingerprints and bank fingerprint, quarantining changed/removed IDs. Runtime history and answer-history joins use canonical IDs.

**Tech Stack:** Python 3, stdlib `hashlib`/`json`, repository `unittest`, GitHub Actions read-only verification.

**Spec:** `docs/superpowers/specs/2026-09-12-backlog1-segment3-adversarial-closure-design.md`

## Global Constraints

- Branch from `909fca8a70232639bab0ad6ef458f1733816a1ec` onto `implementation/sc900-backlog1-adversarial-closure`.
- Do not implement on the Segment-2 branch.
- Do not modify PR #13 or frozen CAND-01R3 protocol/scientific artifacts.
- Do not start BACKLOG-2, BACKLOG-3, or Day 1.
- Question number is not durable learner identity.
- TDD: add failing tests, run them, then implement the smallest coherent repair.

---

### Task 1: Shared content fingerprint and progress epoch migration

**Files:**
- Modify: `question_identity.py`, `session_identity.py`, `progress_store.py`, `runtime_persistence.py`
- Test: `tests/test_backlog1_segment3_adversarial_closure.py`

- [x] **Step 1: Write failing tests** for S3-001, S3-003, S3-005, S3-007, S3-008, S3-009, S3-010, S3-011, S3-023, S3-024, S3-025.
- [x] **Step 2: Run focused tests RED.**
- [x] **Step 3: Extract one content projection and per-question fingerprint.** Keep bank fingerprint algorithm observationally identical.
- [x] **Step 4: Implement epoch bind, quarantine, backup, and idempotence.** Do not change Segment-1 `migrate_legacy_progress_keys` number→ID semantics.
- [x] **Step 5: Run Segment-1 + new epoch tests GREEN.**

### Task 2: History and session-answer identity

**Files:**
- Modify: `question_identity.py`, `session_models.py`, `session_store.py`, `app.py`, `app_question_flow_mixin.py`
- Test: `tests/test_backlog1_segment3_adversarial_closure.py`

- [x] **Step 1: Write failing tests** for S3-002, S3-004, S3-006, S3-012–S3-018.
- [x] **Step 2: Run focused tests RED.**
- [x] **Step 3: Runtime history match by canonical ID + content fingerprint; legacy number fallback migration-only.**
- [x] **Step 4: Require `question_id` on new `SessionAnswerEvent` writes and restore/join by ID.**
- [x] **Step 5: Run focused tests GREEN.**

### Task 3: Analytics / Smart Practice joins and follow-up dedup

**Files:**
- Modify: `app_analytics_mixin.py`, `app_session_builder_mixin.py`, `app_game_mixin.py`, `app_question_flow_mixin.py`, `smart_practice_measurement.py`, `smart_practice_question_value.py`, `smart_practice_core.py`
- Test: `tests/test_backlog1_segment3_adversarial_closure.py`

- [x] **Step 1: Write failing tests** for S3-019–S3-022.
- [x] **Step 2: Run focused tests RED.**
- [x] **Step 3: Key persisted-evidence joins by canonical question ID.**
- [x] **Step 4: Deduplicate follow-ups by canonical ID.**
- [x] **Step 5: Run focused tests GREEN.**

### Task 4: Full-suite CAND harness reconciliation

**Files:**
- Modify: `tests/test_cand01r3_rrc1.py`, `tests/test_cand01r3_all_paths.py`, `tests/cand01r3_fixtures.py` only as required for stale identity keys / missing harness methods
- Do not change TRAIN/PROBE membership, protocol timing, or RRC-1 class semantics

- [x] **Step 1: Reproduce the 5 FAIL + 1 ERROR on the Segment-3 base.**
- [x] **Step 2: Repair stale number-keyed records and `SessionBuilderHarness.compute_analytics` without changing scientific outcomes.**
- [x] **Step 3: Re-run CAND RRC1, all-path, and full suite.**

### Task 5: Verification, receipt, and draft PR

- [x] **Step 1: Read-only verification on a clean tree.**
- [x] **Step 2: Write `docs/research/SC900-BACKLOG-1-IDENTITY-MIGRATION-001/03-ADVERSARIAL-CLOSURE.md`.**
- [ ] **Step 3: Open a new draft PR from the Segment-3 branch. Do not merge PR #17 or close Issue #14.**
