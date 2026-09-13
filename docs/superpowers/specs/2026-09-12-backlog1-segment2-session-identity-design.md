# BACKLOG-1 Segment 2 — Session Identity Design

## Scope

Implement only BACKLOG-1 Segment 2 from Issue #14: bind durable/resumable session state to canonical question identity and immutable bank/content identity. Do not begin BACKLOG-2 confidence work or BACKLOG-3 builder-identity work, and do not modify PR #13 or frozen CAND-01R3 scientific artifacts.

Starting point: `b19d5215dc1d79b02f4e805a510dcd9d901db259` on `implementation/sc900-backlog1-identity-migration`.

Implementation branch: `implementation/sc900-backlog1-session-identity`.

## Confirmed defects

1. Session signature authority is `mode + question_number sequence`.
2. Session filenames inherit that weak signature.
3. Snapshot authority stores `question_numbers` / `restore_question_numbers` without canonical question IDs or bank fingerprint.
4. Saved-session matching can accept a stale snapshot when a changed bank reuses the same filename/stem and number sequence.
5. Answer rows are restored positionally after number-based validation/reordering.
6. Snapshot answer cardinality is not strictly tied to session-question cardinality.

## Durable identity hierarchy

New ordinary session authority is:

`canonical question_id -> immutable bank/content fingerprint -> question_number as display/order metadata only`.

A new session identity is derived from:

- session mode;
- bank fingerprint;
- ordered canonical session question IDs.

Question number remains stored for diagnostics, UI/order compatibility, and legacy inspection, but never proves durable session identity.

## Canonical question identity

Reuse the production-general canonical question-ID authority introduced in Segment 1 (`question_identity.py`). New ordinary session snapshots require a non-empty canonical ID for every question participating in durable session state. Missing or duplicate canonical IDs fail closed for durable snapshot construction/restoration.

## Bank fingerprint

Define a deterministic SHA-256 fingerprint over a canonical, path-independent projection of bank question identity and content.

For each question, project only durable content fields that establish question meaning/answer authority, including canonical ID, stem/question text, choices/answers, correct-answer authority, explanation/objective/domain/topic metadata when present. Exclude mutable runtime/learner state such as selected answers, confidence, flags, suspension, mastery/progress, rewards, timestamps, and UI-only ordering fields such as `question_number`.

Sort projected questions by canonical ID before hashing. Therefore pure reordering or renumbering of otherwise unchanged canonical questions does not alter the bank fingerprint; changing canonical identity or durable question content does.

Serialize the projection using deterministic JSON (`sort_keys=True`, compact separators, UTF-8) and hash with SHA-256.

## Session snapshot schema

Bump the ordinary session schema version. New snapshots include:

- `bank_fingerprint: str`;
- `question_ids: list[str]` in current session order;
- `restore_question_ids: list[str]` for the original session selection/order authority;
- existing `question_numbers` and `restore_question_numbers` retained as presentation/legacy metadata;
- `answers`, where each answer row carries `question_id` in addition to answer state.

`session_signature` and `restore_signature` are computed from mode + bank fingerprint + ordered canonical question IDs.

## Restore contract

New snapshots restore only when all of these hold:

1. schema is supported;
2. bank fingerprint equals the currently loaded bank fingerprint;
3. canonical session/restore IDs are present, unique, and resolvable exactly once against current bank authority;
4. answer cardinality equals canonical session question cardinality;
5. every answer row has exactly one canonical `question_id` and the set/order is valid for the snapshot;
6. mode/signatures match the canonical identity inputs.

Answers are applied by canonical question ID, not by list position alone. Positional order may be used only after canonical ID mapping proves which row belongs to which question.

Any mismatch fails closed. Invalid runtime snapshots may be quarantined through existing runtime-persistence behavior; they are never silently attached to different content.

## Legacy snapshots

Legacy snapshots lacking bank fingerprint and canonical question-ID authority cannot prove they belong to the currently loaded content epoch. They must not be auto-promoted solely from bank stem, filename, question numbers, or legacy signatures.

Ordinary legacy snapshots therefore fail closed for automatic resume and remain preserved/quarantined according to the existing invalid-runtime-file policy. Segment 1 already preserves learner progress separately, so an unverifiable unfinished session is safer to refuse than to attach stale answer state to different questions.

CAND-01R3 experimental session restoration remains under its frozen experimental runtime path and must retain externally observable measurement behavior.

## File boundaries

Expected production files:

- `session_identity.py` — bank fingerprint and canonical session-identity helpers;
- `session_models.py` — schema typing for canonical session identity / answer row identity;
- `session_store.py` — schema migration/build/match/signature logic;
- `app_session_persistence_mixin.py` — construct current identity, save, select, restore, and apply state by canonical ID.

Expected tests:

- `tests/test_backlog1_segment2_session_identity.py`;
- affected existing session/application regressions;
- CAND-01R3 regression suites without protocol/artifact mutation.

## Acceptance cases

At minimum:

1. same numbers + changed canonical ID/content cannot resume;
2. same canonical IDs/content survive pure reorder/renumber because the bank fingerprint is order/number independent;
3. ordered session signature still distinguishes different session question-ID order;
4. answer state is restored to its canonical question ID, not a different positional question;
5. answer cardinality mismatch fails closed;
6. missing/duplicate answer question IDs fail closed;
7. bank fingerprint mismatch fails closed;
8. legacy ordinary snapshot without canonical/bank authority is not automatically resumed;
9. default current-bank save/reload behavior remains functional;
10. CAND-01R3 frozen measurement behavior and artifacts remain unchanged.

## Non-goals

Do not redesign confidence epistemics (Issue #15), builder-context/randomize identity (Issue #16), general content ingestion, progress migration already owned by Segment 1, or frozen CAND-01R3 protocol/scientific artifacts.