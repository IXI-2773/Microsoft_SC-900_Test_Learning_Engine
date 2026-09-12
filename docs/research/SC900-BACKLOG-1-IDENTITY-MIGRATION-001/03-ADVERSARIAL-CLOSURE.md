# BACKLOG-1 Segment 3 — Adversarial Identity, History, Bank-Epoch, and Migration Closure

## Scope

Final BACKLOG-1 implementation from Issue #14. Segments 1 and 2 remain accepted. This segment closes residual learner-identity authority across progress content epoch, persisted history, session answer history, analytics/Smart Practice joins, follow-up deduplication, and explicit bank-revision migration.

This work does not start BACKLOG-2, BACKLOG-3, or CAND-01R3 Day 1. PR #13 was not modified.

## Exact SHAs

| Item | SHA |
| --- | --- |
| Segment-3 base / Segment-2 SHA | `909fca8a70232639bab0ad6ef458f1733816a1ec` |
| Segment-1 SHA | `b19d5215dc1d79b02f4e805a510dcd9d901db259` |
| PR #13 frozen head | `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` |
| Implementation verification SHA | `ffc7725e692f7029549ebf24d2f74f2510fba6e5` |
| Implementation parent SHA | `909fca8a70232639bab0ad6ef458f1733816a1ec` |
| Documentation SHA | this commit on `implementation/sc900-backlog1-adversarial-closure` |
| Segment-2 implementation verification SHA | `a88d03af31ba683a15c5e3750d140d40ddf109be` |

Branch: `implementation/sc900-backlog1-adversarial-closure`, created from exactly `909fca8`. The Segment-2 branch was not used for Segment-3 implementation and still pointed at `909fca8` at branch creation.

## Commit lineage

1. `909fca8` docs: record backlog-1 session identity receipts after non-mutating verification — Segment-3 base
2. `ffc7725` feat: close backlog-1 remaining learner identity authority — implementation, tests, workflow, design/plan
3. this documentation commit — research receipt

## Identity-authority inventory

Material `question_number` occurrences were classified before closure. Mechanical replacement of every number was rejected.

| Class | Meaning | Inventory result |
| --- | --- | --- |
| A | Canonical durable authority | Must use `question_id` + content/bank epoch. Remaining number-as-durable-A = **0** |
| B | Legacy migration only | Number permitted solely to transform old state into canonical state |
| C | Presentation / order | Labels, sort, Q17 UI, ranking tie-break |
| D | Runtime-local non-durable | Current-bank maps rebuilt in one call after an ID join; cannot survive a bank reload as identity |
| E | Defect | Number still acts as durable/cross-session/cross-bank learner identity |

Counts of **material defects (E)** found and repaired: **13 found, 13 repaired, 0 remaining**.

Remaining production `question_number` uses after closure:

- **A:** 0
- **B:** 6 material sites — `migrate_legacy_progress_keys`, `build_number_to_question_id_index`, `migrate_legacy_history_events`, `legacy_history_event_matches_question`, schema-4 session answer-history stamp from that snapshot’s own number→ID pairing, numeric-only `progress_record_for_question` fallback when every key is numeric
- **C:** models/UI/diagnostics/order/`question_number` fields retained on events for display
- **D:** current-bank scoring maps still keyed by number *after* history is joined by ID (`source_map`, `question_stability`, `question_meta`, some Smart Practice priority maps). These are rebuilt from the live pool each call and do not persist as identity.
- **E:** 0

## E defects found and repaired

1. Progress canonical IDs unbound from bank/content epoch
2. Runtime `history_event_matches_question` number fallback after migration
3. `SessionAnswerEvent` without mandatory canonical ID
4. Analytics/Smart Practice history maps joining persisted evidence by question number
5. Follow-up / stealth uniqueness by reused question number
6. Smart Practice `same_question` / quality / information-value identity by number
7. Persistent Smart Practice `record_id` / quality outcomes keyed by qnum
8. CAND RRC1 and all-path records keyed by `"1"` / `"9"` instead of canonical IDs
9. `SessionBuilderHarness` missing `compute_analytics` / follow-up ID helpers (stale harness, not scientific)
10. Stealth latent-weakness history map keyed by qnum while lookup used canonical ID
11. Quality calibration ignoring outcome `id` when `question_id` was absent
12. Content fingerprint including runtime choice-letter shuffle and empty explanation maps
13. Smart Practice `outcomes_by_qnum` as the durable quality join after renumber

## Progress epoch / content identity

`PROGRESS_IDENTITY_VERSION` remains `1` so Segment-1 tests stay valid.

Added a separate epoch layer:

- `progress_content_epoch_version = 1`
- `bank_fingerprint`
- `question_content_fingerprints: {question_id: fingerprint}`
- `quarantined_questions`

One hashing algorithm lives in `question_identity.py`. `session_identity.bank_content_fingerprint` is a re-export.

Per-question content identity is SHA-256 of a letter-independent projection:

- canonical ID
- durable fields: prompt, explanations, domain, chapter, subtitle, question_type, topics, objective_code, study_focus
- sorted choice texts, correct texts, and explanation texts
- excludes `question_number`, `choice_order`, runtime/learner state, empty explanation maps

Same durable content + reorder/renumber/choice-letter shuffle = same fingerprint. Changed prompt/correct text/distractor text = different fingerprint. Bank add/remove changes the bank fingerprint even when existing question fingerprints are unchanged.

## Bank revision migration

`migrate_progress_content_epoch` is chained after Segment-1 `migrate_legacy_progress_keys`. Persistence backups before any identity-changing write.

| Case | Behavior |
| --- | --- |
| Same ID + same content, possibly new number | Preserve learner state |
| New ID | Initialize empty; do not disturb valid state |
| Missing ID | Quarantine `REMOVED_QUESTION`; never reassign |
| Same ID + different content | Quarantine `CHANGED_CONTENT`; never silently inherit |
| Same number + different ID | No inheritance |
| Reorder only | Bank fingerprint unchanged; no state loss |
| Duplicate / missing canonical IDs | Fail closed |
| First bind of Segment-1 canonical state | Stamp current bank as assumed epoch |
| Empty bank authority | Return unchanged (do not quarantine everything) |
| Idempotent second pass | No extra mutation |

## History and session answer history

New `QuestionHistoryEvent` and `SessionAnswerEvent` writes include `question_id` and `question_content_fingerprint`. `question_number` remains display metadata.

Runtime matching is canonical ID plus fingerprint agreement when the event carries a fingerprint. Number fallback is `legacy_history_event_matches_question` only.

Legacy history without `question_id`:

- unique number→ID mapping → explicit migration stamps ID + current fingerprint
- ambiguous mapping → quarantine / do not attach
- unmapped number → preserve unresolved; do not attach
- number reused by a different ID → never cross-attach

Schema-4 session restore may stamp missing answer-history IDs from **that snapshot’s own** `question_ids`/`question_numbers` pairing, then fail closed if still missing.

## Smart Practice / analytics / builder / follow-up

- Persisted history joins use `canonical_question_history_map` + `history_events_for_question`.
- Quality calibration matches `question_id` / `canonical_question_id` / question-shaped `id`; it does not number-match a different ID.
- Scoring context carries `outcomes_by_question_id`; ID-bearing questions do not fall back to `outcomes_by_qnum`.
- Follow-up, twin, rescue, ramp, stealth, and delayed-recall uniqueness use canonical IDs. Question number remains ranking/order metadata.
- Builder filters (domain/topic/status/count/randomize) stay generic preferences. Question-specific builder/session reuse remains bounded by bank fingerprint and canonical session identity from Segment 2. `seen_question_ids` was added to Smart Practice session context.

## Full-suite failure debt disposition

Segment-2 leftover: 837 run, 5 FAIL, 1 ERROR.

| Failure | Root cause | Disposition |
| --- | --- | --- |
| CAND RRC1 class/record selection | Tests keyed records by question number `"1"`/`"9"` after production keys became canonical IDs | Stale test identity keys repaired to `repair_q` / `train_a` / `probe_a`. Frozen TRAIN/PROBE membership and RRC-1 scientific semantics unchanged. |
| `g3_007` | Same number-keyed CAND records | Canonical IDs in all-path records |
| weak-retest / `SessionBuilderHarness` compatibility | Harness lacked `compute_analytics`, `_recent_history`, `_session_question_ids` | Harness methods added; no CAND scientific change |
| `compute_analytics` missing on harness | Stale interface | Added on `SessionBuilderHarness` |
| RRC1 class selection | Number-keyed lookup missed ID-keyed records | Tests now use canonical IDs |

After those harness/key repairs, a new 6-fail set appeared and was repaired with TDD:

- quality calibration ID join (`test_sp12_32`–`35`)
- memory-ramp history fingerprint vs choice shuffle
- stealth latent-weakness map keying

Final full suite: **866 tests, 0 failures, 0 errors**.

## RED / GREEN evidence

RED (genuine, before the corresponding repair):

- S3-001–S3-025 in `tests/test_backlog1_segment3_adversarial_closure.py`
- `test_s3_content_fingerprint_ignores_choice_letter_shuffle`
- `test_s3_quality_joins_id_bearing_rows_without_question_id_field`
- engine-regression quality and follow-up tests listed above

GREEN (implementation verification SHA `ffc7725`):

- Segment-1: `tests.test_backlog1_progress_identity_migration` + `tests.test_backlog1_segment1_adversarial_review` PASS
- Segment-2: session identity + app integration PASS
- Segment-3 focused: 29 tests PASS
- Combined identity set: 83 tests PASS
- Full suite: `python -m unittest discover -s tests -v` → **Ran 866 tests in 47.868s OK**
- `python -m tools.run_quality_checks` PASS (ruff/black scoped targets + mypy)
- Ruff on Segment-3 identity files PASS
- `python -m tools.lint_bank` PASS (8 clean baseline questions)
- `python -m tools.verify_installation` PASS

## Source-tree proof (implementation verification)

```
HEAD_BEFORE=ffc7725e692f7029549ebf24d2f74f2510fba6e5
WORKTREE_BEFORE=CLEAN
HEAD_AFTER=ffc7725e692f7029549ebf24d2f74f2510fba6e5
WORKTREE_AFTER=CLEAN
TRACKED_SOURCE_MUTATION_DURING_VERIFICATION=NO
SELF_MUTATING_VERIFICATION=NO
```

## Exact changed files (implementation commit `ffc7725`)

```
.github/workflows/verify-backlog1-segment3.yml
app.py
app_analytics_mixin.py
app_game_mixin.py
app_question_flow_mixin.py
app_session_builder_mixin.py
docs/superpowers/plans/2026-09-12-backlog1-segment3-adversarial-closure.md
docs/superpowers/specs/2026-09-12-backlog1-segment3-adversarial-closure-design.md
progress_store.py
question_identity.py
runtime_persistence.py
session_identity.py
session_models.py
session_store.py
smart_practice_core.py
smart_practice_measurement.py
smart_practice_question_value.py
tests/cand01r3_fixtures.py
tests/test_backlog1_segment1_adversarial_review.py
tests/test_backlog1_segment3_adversarial_closure.py
tests/test_cand01r3_all_paths.py
tests/test_cand01r3_rrc1.py
```

## Frozen CAND-01R3 hashes (unchanged)

- PROTOCOL_VERSION: `cand01r3-measurement-001-v2`
- PROTOCOL_SHA256: `51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72`
- Task-4 semantic audit: `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701`
- Task-5 reviewed store: `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c`
- Task-5 compiled: `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b`
- Task-6 manifest: `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90`
- Default bank: `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`

`git diff --name-only 909fca8 -- cand01r3_partition.py cand01r3_runtime.py content/sc900/phase3` is empty.

## Protected refs (unchanged)

- `recovery/publish-exact-history/sc900-v8-20260910` = `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`
- `recovery/publish-sc900-v8-exact-history` = `bbc3bd900b73bde89151dc51706ad62fc69e8196`
- tag `sc900-v8.0.0-baseline` = `9c80be5b20e652dc2eb86621dfdf7c32baa06528`

## Remaining explicitly out-of-scope debt

- BACKLOG-2 and BACKLOG-3
- Day 1 empirical CAND observations
- Repo-wide historical Ruff/Black debt outside `tools.run_quality_checks` targets and this segment’s identity files
- Presentation `question_number` fields and current-bank D maps listed above
- PR #17 remains Segment-2 evidence (superseded, not deleted)
- Issue #14 remains open until this PR is merged or the operator directs closure

## Completion flags for operator review

```
SEGMENT_1_ACCEPTED = YES
SEGMENT_2_ACCEPTED = YES
SEGMENT_3_ACCEPTED = YES  # implementation verified; awaiting operator merge
BACKLOG1_COMPLETE = YES   # implementation complete; Issue #14 stays open until merge
FULL_SUITE_PASS = YES
QUESTION_NUMBER_AS_DURABLE_IDENTITY = NO
DAY1_STARTED = NO
PR13_MODIFIED = NO
PROTECTED_REFS_UNCHANGED = YES
```
