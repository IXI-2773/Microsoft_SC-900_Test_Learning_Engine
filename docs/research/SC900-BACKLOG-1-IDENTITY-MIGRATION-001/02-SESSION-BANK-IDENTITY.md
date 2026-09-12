# BACKLOG-1 Segment 2 — Session / Bank Identity

## Scope

Implement BACKLOG-1 Segment 2 from Issue #14: bind ordinary durable/resumable session state to canonical question IDs and a deterministic bank/content fingerprint, and restore answer rows by canonical ID.

This work does not start Segment 3, BACKLOG-2, BACKLOG-3, CAND-01R3 Day 1, or any merge of PR #10–#13.

## Starting and reconciled heads

- Segment-1 base: `b19d5215dc1d79b02f4e805a510dcd9d901db259` on `implementation/sc900-backlog1-identity-migration`
- Reconciled live Segment-2 head before this repair: `75e8d417f6ea5467702f6ad4e2d3ab2c24550172` on `implementation/sc900-backlog1-session-identity`
- That live head was 15 commits ahead of Segment 1 and 0 behind it. No newer legitimate descendant existed at fetch time.
- PR #13 frozen head: `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` on `research/sc900-cand01r3-measurement-001`
- Implementation verification SHA: `a88d03af31ba683a15c5e3750d140d40ddf109be`
- Parent of that SHA: `75e8d417f6ea5467702f6ad4e2d3ab2c24550172`

## Commit lineage reviewed (`b19d521` → `75e8d41`)

1. `943fb20` docs: define backlog-1 segment-2 session identity design
2. `e13edbd` docs: plan backlog-1 segment-2 implementation
3. `f757025` test: reproduce segment-2 session identity defects — **RED tests**
4. `7ae8049` ci: verify backlog-1 segment-2 session identity — **self-mutating workflow introduced**
5. `01af511` feat: add canonical session identity authority — **`session_identity.py`**
6. `444c0ff` test: stage segment-2 session schema repair — **temporary `tools/backlog1_segment2_apply_core.py`**
7. `0b622b8` ci: apply and verify segment-2 core repair
8. `8ee54cf` feat: add canonical session snapshot identity — **GitHub Actions bot**; modified `session_models.py`, `session_store.py`; deleted apply-core script
9. `9da1557` test: cover cand legacy and id-bound answer restore — **additional RED/coverage tests**
10. `1b1c76c` test: reproduce app session identity integration defects — **RED app tests**
11. `719da28` ci: include segment-2 app integration tests
12. `2940750` feat: stage canonical session app integration — **temporary `tools/backlog1_segment2_apply_integration.py`**
13. `338d914` ci: fix segment-2 verified repair commit staging
14. `78a37d0` feat: bind ordinary session restore to canonical identity — **GitHub Actions bot**; modified `app_session_persistence_mixin.py`, `session_store.py`; deleted apply-integration script
15. `75e8d41` ci: collect complete segment-2 verification evidence

Forward repair after that lineage:

16. `a88d03a` fix: stop self-mutating BACKLOG-1 verification and commit staged identity repairs

## Self-mutating CI defect

Both Segment-1 and Segment-2 workflows used `permissions: contents: write`, executed staged apply scripts, committed resulting source, and pushed back to the implementation branch.

Bot-generated Segment-2 implementation commits:

- `8ee54cf` — canonical snapshot schema in `session_models.py` / `session_store.py`
- `78a37d0` — ordinary restore bound to canonical identity in `app_session_persistence_mixin.py` / `session_store.py`

Those source changes were **preserved**. They are technically correct against the approved design. They were not deleted or reverted for authorship.

Temporary Segment-2 apply scripts no longer existed at `75e8d41`. Segment-1 still had `tools/backlog1_apply_review_fixes.py` and `tools/backlog1_apply_review_test_fixes.py`; those scripts contained uncommitted review implementation. They were executed once as ordinary local source edits, then deleted so verification cannot manufacture the tree it tests.

Final permanent workflows on this lineage:

- `.github/workflows/verify-backlog1-segment1.yml` — `contents: read`; no apply/commit/push
- `.github/workflows/verify-backlog1-segment2.yml` — `contents: read`; no apply/commit/push

The remote branch `implementation/sc900-backlog1-identity-migration` still points at `b19d521` and therefore still contains the old mutating Segment-1 workflow until this lineage is the published authority.

## Canonical bank fingerprint

Authority module: `session_identity.py`.

- `bank_content_fingerprint(questions)` SHA-256 over a canonical JSON projection
- Projection includes canonical `question_id` plus durable content fields: prompt, choices, correct, explanations, domain, chapter, subtitle, question_type, topics, objective_code, study_focus, choice_order
- Excludes `question_number` and runtime/learner state
- Questions are sorted by canonical ID before hashing, so mere reorder/renumber does not change the fingerprint
- Missing or duplicate canonical IDs fail closed

## Canonical session signature

- `canonical_session_signature(mode, bank_fingerprint, question_ids)` SHA-256 truncated to 24 hex characters
- Binds mode + bank fingerprint + **ordered** canonical question IDs
- Duplicate or blank IDs fail closed
- Order of IDs is significant; bank fingerprint is not

## Snapshot schema before / after

Before (schema 3 / legacy ordinary):

- Identity: `mode` + question-number sequence
- Filename/signature: `session_signature(mode, question_numbers)`
- Restore: question numbers, then positional `answers[i] -> questions[i]`
- No bank fingerprint, no canonical IDs on answers

After (schema 4 ordinary):

- `session_identity_version = 1`
- `session_identity = canonical_question_id+bank_fingerprint`
- `bank_fingerprint`
- `question_ids` / `restore_question_ids`
- `question_numbers` / `restore_question_numbers` retained as presentation/legacy metadata only
- Each answer row carries `question_id`
- `session_signature` / `restore_signature` computed from mode + fingerprint + ordered canonical IDs
- CAND-01R3 experimental snapshots remain on the legacy/experimental path when `cand01r3` is active or `allow_legacy=True`

## Answer restore before / after

Before: after number validation/reordering, apply `zip(questions, answers)` by list position.

After:

1. Fail closed unless schema, fingerprint, signatures, unique canonical IDs, and answer cardinality all prove
2. Rebuild the session question list from saved canonical IDs
3. Map answer rows with `answer_states_by_question_id`
4. Apply each row only to the current question with that exact canonical ID

Fail closed on missing/duplicate answer ID, missing current question, duplicate current canonical ID, cardinality mismatch, fingerprint mismatch, signature mismatch, and unverifiable legacy ordinary snapshots.

## Legacy ordinary session disposition

Unverifiable ordinary snapshots are not auto-promoted from bank stem, filename, question numbers, or legacy signatures. `saved_session_matches_current` returns false without `allow_legacy`. `migrate_session_snapshot` raises unless `allow_legacy=True`. Forced migrate of such a file quarantines it through existing invalid-runtime-file policy.

CAND-01R3 experimental restore remains isolated and was regression-tested.

## RED / GREEN evidence

RED that existed in history before production:

- `f757025` Segment-2 identity defects
- `1b1c76c` app integration defects
- Segment-1 adversarial tests at `75e8d41`: 10 failed/errored because implementation lived only in apply scripts

GREEN on verification SHA `a88d03a`:

- Segment-1 focused: **31/31 OK**
- Segment-2 focused: **23/23 OK**
- CAND runtime-resume: **30/30 OK**
- CAND protocol v2: **20/20 OK**
- Additional Segment-2 cases added without deleting prior tests: signature mismatch, duplicate current IDs, ID-bound restore after reorder, legacy non-resume, quarantine on forced legacy migrate

## Full-suite and quality

Executed on `a88d03a` with clean tree:

- Full suite: **837 run, 5 failed, 1 error** — `FAILED`
- Remaining failures are the same pre-existing CAND RRC1 / `g3_007` failures observed on `75e8d41` before this repair. They are not recorded as Segment-2 identity regressions.
- `python -m tools.run_quality_checks`: **PASS** (ruff, black `--check`, mypy on repository quality targets)
- Repo-wide `ruff check .` remains a pre-existing FAIL on both `75e8d41` and `a88d03a` (~190 findings) and is not treated as a new Segment-2 defect
- `python -m tools.lint_bank`: **PASS** (8 clean baseline questions)
- `python -m tools.verify_installation`: **PASS**

## Source-tree invariant

- `HEAD_BEFORE = a88d03af31ba683a15c5e3750d140d40ddf109be`
- `HEAD_AFTER = a88d03af31ba683a15c5e3750d140d40ddf109be`
- `TRACKED_SOURCE_MUTATION_DURING_VERIFICATION = NO`
- `WORKTREE_AFTER_VERIFICATION = CLEAN`

## Frozen CAND-01R3 hashes

Unchanged:

- `PROTOCOL_VERSION = cand01r3-measurement-001-v2`
- `PROTOCOL_SHA256 = 51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72`
- Task-4 semantic audit `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701`
- Task-5 reviewed store `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c`
- Task-5 compiled bank `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b`
- Task-6 TRAIN/PROBE manifest `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90`
- Default launch bank `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`

No diff vs Segment-1 for `cand01r3_partition.py`, `cand01r3_runtime.py`, or `content/sc900/phase3`. PR #13 was not modified.

## Protected refs

Unchanged:

- `recovery/publish-exact-history/sc900-v8-20260910` = `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`
- `recovery/publish-sc900-v8-exact-history` = `bbc3bd900b73bde89151dc51706ad62fc69e8196`
- tag object `sc900-v8.0.0-baseline` = `9c80be5b20e652dc2eb86621dfdf7c32baa06528`

## Exact files changed by the forward repair (`75e8d41` → `a88d03a`)

- `.github/workflows/verify-backlog1-segment1.yml`
- `.github/workflows/verify-backlog1-segment2.yml`
- `app.py`
- `app_game_mixin.py`
- `app_question_flow_mixin.py`
- `app_session_persistence_mixin.py`
- `progress_models.py`
- `progress_store.py`
- `question_identity.py`
- `runtime_persistence.py`
- `session_models.py`
- `session_store.py`
- `smart_practice_measurement.py`
- `tests/test_backlog1_progress_identity_migration.py`
- `tests/test_backlog1_segment1_adversarial_review.py`
- `tests/test_backlog1_segment2_session_app_integration.py`
- `tests/test_backlog1_segment2_session_identity.py`
- `tests/test_sc900_engine_regression.py`
- deleted `tools/backlog1_apply_review_fixes.py`
- deleted `tools/backlog1_apply_review_test_fixes.py`

Plus this receipt and the Segment-1 receipt update in the documentation commit that follows verification.

## Deferred Segment-3 work

Do not treat this document as BACKLOG-1 completion.

Still deferred:

- remaining full BACKLOG-1 migration/adversarial closure
- cross-engine/history/builder-context compatibility that is not required for ordinary session identity
- pre-existing CAND RRC1 / weak-retest harness failures (`compute_analytics` missing on `SessionBuilderHarness`, RRC1 class selection)
- repo-wide `ruff check .` cleanup outside quality-target files

## Disposition

- `BACKLOG1_SEGMENT2_SESSION_IDENTITY = ACCEPTED`
- `CANONICAL_BANK_CONTENT_FINGERPRINT = IMPLEMENTED`
- `CANONICAL_SESSION_SIGNATURE = IMPLEMENTED`
- `QUESTION_NUMBER_AS_SESSION_AUTHORITY = REMOVED_FOR_NEW_SESSIONS`
- `POSITIONAL_ANSWER_RESTORE_AUTHORITY = REMOVED`
- `ANSWER_RESTORE_BY_CANONICAL_ID = VERIFIED`
- `BANK_FINGERPRINT_MISMATCH = FAIL_CLOSED`
- `ANSWER_CARDINALITY_MISMATCH = FAIL_CLOSED`
- `DUPLICATE_ANSWER_ID = FAIL_CLOSED`
- `LEGACY_UNPROVEN_SESSION_RESTORE = FAIL_CLOSED`
- `SEGMENT1_REGRESSION = PASS`
- `DEFAULT_BANK_BEHAVIOR = UNCHANGED`
- `CAND01R3_SCIENTIFIC_AUTHORITY = UNCHANGED`
- `SELF_MUTATING_SEGMENT1_CI = REMOVED_OR_READ_ONLY`
- `SELF_MUTATING_SEGMENT2_CI = REMOVED_OR_READ_ONLY`
- `BACKLOG1_COMPLETE = NO`
- `SEGMENT_3_STARTED = NO`
- `SEGMENT_2_ACCEPTED = YES`
