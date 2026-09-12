# BACKLOG-1 Segment 1 — Canonical Progress Identity

## Scope and starting authority

- Branch: `implementation/sc900-backlog1-identity-migration`
- Starting commit: `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb`
- PR #13 measurement branch/head was treated as frozen and was not modified.
- Segment 2 session snapshot identity work was not started.
- Issue #14 remains open.

## Root cause

Durable learner progress used `str(question_number)` as the primary key. Question number is mutable presentation/order metadata, so renumbering could orphan progress and replacement content reusing a number could inherit unrelated learner history.

## Old identity contract

Progress `questions` was a JSON mapping keyed by decimal question-number strings such as `"27"`. `progress_store.question_key()` returned `str(question_number)`. The envelope had `version: 3` but no explicit field identifying the authority used for progress keys.

## New identity contract

`question_identity.py` is the production-general authority. Canonical IDs resolve deterministically in this order:

1. `id`
2. `question_id`
3. `canonical_question_id`
4. `metadata.question_id`
5. `metadata.canonical_question_id`

Whitespace-only values are invalid. A real bank question missing canonical identity raises `MISSING_CANONICAL_QUESTION_ID`; it does not use its question number as a durable key.

The pre-existing CAND-01R3 resolver was not rewritten. Its externally observable authority order is regression-tested against the production-general resolver so frozen research behavior is not coupled to ordinary persistence.

The app also has an existing identifier-only `{question_number: ...}` UI reference for issue/suspension maintenance. That is not treated as a bank question. It resolves through the currently loaded bank to exactly one canonical ID and fails closed if no unique canonical match exists. The durable key remains the canonical ID.

## Progress schema revision

The existing top-level progress envelope version remains `3` for compatibility. Segment 1 adds an explicit identity migration/version contract:

```json
{
  "version": 3,
  "progress_identity_version": 1,
  "question_identity": "canonical_question_id",
  "questions": {
    "SC900-PH-001": {}
  }
}
```

New blank progress is created with those identity metadata fields. Unversioned numeric question keys are classified as legacy number-keyed progress. Unversioned non-numeric keys are not guessed and fail with `PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS`.

## Legacy migration algorithm

1. Read the complete progress payload.
2. Classify its identity schema.
3. If already canonical identity version 1, deep-copy and return without a write.
4. For non-empty legacy numeric progress, validate the current bank as identity authority: every migration-relevant bank question must have a canonical ID and canonical IDs must be unique.
5. Build an unambiguous normalized `question_number -> canonical question ID` index.
6. Transform every legacy progress record in memory, preserving each record unchanged.
7. Reject any unmapped, ambiguous, duplicate-ID, or destination-collision condition.
8. Add explicit identity metadata.
9. Only after successful transformation/validation, back up the original progress file.
10. Replace the progress file with the repository safe JSON writer, which writes/fsyncs a temporary file and atomically replaces the target.

An empty legacy `questions` mapping can be schema-upgraded without requiring question mappings because there is no learner record to attach to content.

## Fail-closed reasons

- `MISSING_CANONICAL_QUESTION_ID`
- `DUPLICATE_CANONICAL_QUESTION_ID`
- `LEGACY_PROGRESS_AMBIGUOUS`
- `LEGACY_PROGRESS_UNMAPPED`
- `LEGACY_PROGRESS_COLLISION`
- `PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS`

Migration validation failure returns an error and leaves the original progress file unchanged.

## Backup and write semantics

`RuntimePersistence.load_progress_with_identity_migration()` performs migration before the app accepts progress. On a real migration it creates a timestamped `before_identity_migration_v1` backup using existing progress backup infrastructure, then writes with `safe_write_json`. A failed validation does not rewrite the source. Already-canonical state creates no migration backup and performs no migration write.

## Idempotence contract

Canonical identity version-1 payloads are returned unchanged apart from a defensive deep copy. Re-running persistent migration therefore does not remap records, change timestamps, rewrite equivalent progress, or create another migration backup.

Required invariant: `migrate(migrate(X)) == migrate(X)` for canonical state.

## TDD evidence

The initial focused RED test commit was created before the production identity implementation:

- `db990c44c03a1cd7980e82ba142b0095f72e9484` — `test: reproduce canonical progress identity defects`

The focused module was subsequently expanded to 21 `unittest` cases covering canonical key separation, renumbering stability, unique migration, record preservation, idempotence, ambiguous number mapping, duplicate IDs, collision, unmapped records, source preservation on failure, pre-replacement backup, canonical new writes, missing-ID rejection, default-bank IDs, CAND-01R3 resolver parity, canonical aggregation, no-extra-backup idempotence, schema ambiguity, and identifier-only UI-reference resolution.

### Verification limitation

Actual RED/GREEN execution evidence is **not available in this work session**. The authorized repository desktop/terminal connector reported that no device was connected, and the repository's existing GitHub Actions workflows are intentionally restricted to other named verification branches. No workflow was modified merely to manufacture a green result.

Therefore this document does **not** claim Segment-1 acceptance yet. Focused tests, affected regression tests, full suite, ruff, black, and mypy still require direct execution before acceptance can be asserted.

## Files changed by Segment 1

- `bank_models.py`
- `progress_store.py`
- `question_bank.py`
- `question_identity.py` (new)
- `runtime_persistence.py`
- `tests/test_backlog1_progress_identity_migration.py` (new)
- `docs/research/SC900-BACKLOG-1-IDENTITY-MIGRATION-001/01-CANONICAL-PROGRESS-IDENTITY.md` (new)

No session snapshot/restore module was changed.

## Deferred work

Explicitly deferred to Segments 2/3:

- session signature/file-path/restore signature redesign;
- session snapshot canonical identity and position-based answer restoration;
- bank fingerprint enforcement;
- session restore quarantine;
- builder context/randomization identity redesign;
- full cross-engine migration/adversarial closure;
- legacy history rewriting. Existing history continues retaining `question_number`; adding/migrating canonical history identity remains a Segment-3 compatibility task because Segment-1 durable progress lookup no longer depends on history keys.

## Current disposition

- `CANONICAL_QUESTION_ID_AUTHORITY = IMPLEMENTED_IN_BRANCH`
- `QUESTION_NUMBER_AS_DURABLE_PROGRESS_AUTHORITY = REMOVED_FOR_REAL_QUESTION_WRITES`
- `LEGACY_PROGRESS_MIGRATION = IMPLEMENTED_IN_BRANCH`
- `AMBIGUOUS_MIGRATION = FAIL_CLOSED_BY_DESIGN`
- `MIGRATION_BACKUP = IMPLEMENTED_IN_BRANCH`
- `MIGRATION_IDEMPOTENCE = IMPLEMENTED_IN_BRANCH`
- `SESSION_RESTORE_IDENTITY = DEFERRED_TO_SEGMENT_2`
- `BACKLOG1_COMPLETE = NO`
- `SEGMENT_2_STARTED = NO`
- `SEGMENT_1_ACCEPTED = NO` pending executable verification evidence.
