# SC900-BACKLOG-3-BUILDER-RESUME-IDENTITY-001 — Closure

## Decision

`BACKLOG3_IMPLEMENTATION_COMPLETE = YES`  
`BACKLOG3_PUBLISHED = NO`  
Issue #16 remains OPEN. Implementation acceptance is not publication.

## Exact SHAs

| Ref | SHA |
| --- | --- |
| BACKLOG3_BASE_SHA / PR #20 head | `baf69ecf773cc929d7fb84a00494b434595aa8f3` |
| Implementation verification SHA | `a7c7202fcfcaf1f46317e22cf495ed7dd35827c3` |
| Parent SHA | `baf69ecf773cc929d7fb84a00494b434595aa8f3` |
| PR #19 / publication-safe BACKLOG-1 | `5610d25009b3006183cb0ac1a63a7c99d1f89c66` |
| PR #12 Gate-3 | `f742dcc085d46f1999eb8782f709730323e9d7f0` |
| PR #13 frozen measurement | `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` |

Final docs SHA is recorded in the commit that adds this receipt.

## Lineage

```
baf69ec docs: record backlog-2 confidence epistemics integrity closure receipt
a7c7202 feat: bind session resume and cleanup to canonical builder identity
<this docs commit>
```

PR #12 is an ancestor. PR #13 is not.

## Inventory counts (material occurrences)

Classified before repair and re-checked after. Counts are occurrence groups, not raw grep hits.

| Class | Count | Notes |
| --- | ---: | --- |
| A CANONICAL_BUILDER_AUTHORITY | 10 | `BuilderContext`; `normalize_builder_context`; fingerprint; versioned identity; resolve/migrate; match; snapshot attach; constants |
| B BUILDER_IDENTITY_CONSUMER | 16 | resume, cleanup, create, save, restore, file path, builder UI, Smart Practice start, tests |
| C LEGACY_MIGRATION | 6 | complete context migrate; explicit True/False; missing randomize → False; missing context → ambiguous; schema-3 allow_legacy; fail-closed claimed identity |
| D PRESENTATION_ONLY | 8 | labels, badges, combo layout, question numbers, widget text |
| E EXPERIMENTAL/CAND | 9 | `is_cand01r3_active` file/signature/save/load; TRAIN filter; experimental restore; persistable authority metadata |
| F DEFECT | 12 found / 12 repaired / 0 remaining | see below |
| G RUNTIME-LOCAL | 11 | `preserve_if_saved`, clocks, index, reveal, checkpoints, shuffle result, mtime tie-break, cache keys, operational no-reshuffle |

## F defects found and repaired

1. Mixin accepted `randomize=` but did not forward it (S1).
2. Shared normalizer read only `raw["randomize"]`, collapsing True/False (S1).
3. Resume matched via collapsed dict equality (S2).
4. Cleanup used the same weak comparison (S3).
5. mtime ranked collapsed identities (S4).
6. Builder identity was an unversioned dictionary (S5).
7. Missing `builder_context` was synthesized into a matchable context (S6).
8. Missing `randomize` was silently `False` without migration status.
9. `All visible` was collapsed to current pool size.
10. Mixin `count or session_base` truthiness could drop a meaningful zero/empty request.
11. Smart Practice builder context forced `randomize=False` while pool construction could randomize.
12. Ordinary filenames were question-set only, so distinct builders could collide.

## Canonical BuilderContext contract

Keyword-only precedence:

1. explicit keyword argument
2. canonical raw field
3. documented default

`False` is meaningful. Never `randomize or existing`.

Identity-bearing fields:

- `mode`
- `count` (`All visible` stays distinct from a numeric count)
- `source_label`
- `session_source` (aliases such as `All visible` → `All`; empty → `All`)
- `randomize`
- `domain_filter` (empty/`all domains` → `All domains`)
- `topic_filter` (empty/`all topics` → `All topics`)
- `status_filter` (aliases from `STATUS_FILTER_ALIASES`)

Non-identity fields: question numbers, elapsed time, current index, exam reveal, checkpoints, filesystem mtime/path, `preserve_if_saved`, `reset_clock`, resulting shuffle order (recorded as BACKLOG-1 question IDs).

No immutable source ID exists beyond normalized `session_source` + `source_label`. That bounded limitation is accepted.

## Builder identity

- Kind: `canonical_builder_request`
- Version: `1`
- Algorithm: SHA-256 of canonical JSON (`sort_keys=True`, `separators=(",", ":")`, UTF-8, `ensure_ascii=False`)
- Payload: `{builder_identity, builder_identity_version, builder_context}`

Example (Practice / 50 / randomize=True / Full bank / All filters):

Fingerprint: `bd60c17b0fb35697ec5429dea9fdc442df88418c79fdba37c8320b6d651defc8`

Statuses: `canonical`, `migrated`, `legacy_defaulted`, `ambiguous`, `invalid`.

## Snapshot schema

`SESSION_SCHEMA_VERSION` remains `4`. Builder identity is a complementary versioned authority, not a competing session schema.

Before: `builder_context` dict only.  
After: `builder_context` + `builder_identity` + `builder_identity_version` + `builder_context_fingerprint` + `builder_identity_status`.

BACKLOG-1 fields unchanged.

## Session file / same-question-set decision

Builder intent is material even when two requests yield the same canonical question IDs.

Ordinary path:

`{stem}_{mode}_session_{count}_{session_sig}_{builder_fp12}.json`

CAND/experimental path remains question-number identity. Resume still globs, so pre-suffix files remain discoverable.

## Resume / cleanup / mtime

Before: normalize dicts, compare fields, sort survivors by mtime. Collapsed randomize compared equal.

After: canonicalize once; require valid schema + bank + question identity + builder fingerprint equality + incomplete; mtime ranks only equivalent fingerprints.

Cleanup uses the same matcher. Ordered cleanup cannot delete randomized snapshots.

`_latest_completed_session_timestamp` no longer treats mode+source as identity. It only applies when history carries a matching builder fingerprint.

## Restore / UI / legacy

Restore recomputes the fingerprint from stored context and fails closed on mismatch. Automatic resume also requires current vs saved fingerprint when current builder identity is present.

UI restoration reads canonical context into mode/count/source/randomize/domain/topic/status. UI is not identity authority.

Legacy complete context → `migrated`.  
Legacy explicit True/False preserved.  
Legacy missing `randomize` → `legacy_defaulted` / `False` (historical `bool(payload.get("randomize"))`).  
Missing `builder_context` → `ambiguous`: no auto-resume, no unrelated cleanup, file preserved.

## CAND / PR #13 / BACKLOG-1 / BACKLOG-2

- `PR13_IMPORTED = NO`
- `PR13_MODIFIED = NO`
- `PR13_MERGED = NO`
- `DAY1_STARTED = NO`
- Gate-3 CAND file identity and deterministic session behavior unchanged
- BACKLOG-1 segments 1–3 passed
- BACKLOG-2 focused suite passed

## RED evidence

First focused run against the unmodified BACKLOG-2 head:

- `ModuleNotFoundError: No module named 'builder_identity'`
- B3-002: `randomize=True` wrapper result was `False`
- B3-003: explicit `randomize=False` did not override raw `True`
- B3-020/B3-021: tampered context/fingerprint did not fail closed

38 tests: 4 failures, 26 errors.

## GREEN / verification evidence

Implementation SHA `a7c7202fcfcaf1f46317e22cf495ed7dd35827c3`

| Check | Result |
| --- | --- |
| BACKLOG-1 Segment-1 + Segment-2 + Segment-3 + progress identity | PASS (included in 168-test focused run) |
| BACKLOG-2 focused | PASS |
| BACKLOG-3 focused | PASS (38 tests) |
| Focused combined | `Ran 168 tests ... OK` |
| Gate-3 CAND (`test_cand01r3*.py`) | `Ran 63 tests ... OK` |
| Phase-3 | `Ran 79 tests ... OK` |
| Full suite | `Ran 827 tests in 51.858s OK` |
| `python -m tools.run_quality_checks` | Quality checks passed |
| `python -m tools.lint_bank` | passed (8 clean baseline questions) |
| `python -m tools.verify_installation` | passed |
| Ruff / Black / mypy on identity files | passed |

HEAD before verification: `a7c7202fcfcaf1f46317e22cf495ed7dd35827c3`  
HEAD after verification: `a7c7202fcfcaf1f46317e22cf495ed7dd35827c3`  
Worktree before/after: CLEAN  
`TRACKED_SOURCE_MUTATION_DURING_VERIFICATION = NO`

## Protected refs / PR states at verification

| Ref | SHA / state |
| --- | --- |
| `recovery/publish-exact-history/sc900-v8-20260910` | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` |
| `recovery/publish-sc900-v8-exact-history` | `bbc3bd900b73bde89151dc51706ad62fc69e8196` |
| `sc900-v8.0.0-baseline` tag object | `9c80be5b20e652dc2eb86621dfdf7c32baa06528` |
| PR #13 | OPEN, head `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` |
| PR #19 | OPEN DRAFT, head `5610d25009b3006183cb0ac1a63a7c99d1f89c66` |
| PR #20 | OPEN DRAFT, head `baf69ecf773cc929d7fb84a00494b434595aa8f3` |
| Issue #16 | OPEN |

## Acceptance flags

```
RANDOMIZE_CALLER_INTENT_PRESERVED = YES
CANONICAL_BUILDER_NORMALIZER = IMPLEMENTED
CANONICAL_BUILDER_IDENTITY = IMPLEMENTED
BUILDER_IDENTITY_VERSIONED = YES
BUILDER_CONTEXT_FINGERPRINT = IMPLEMENTED
BUILDER_FINGERPRINT_DETERMINISTIC = YES
RANDOMIZED_ORDERED_IDENTITY_COLLISION = ELIMINATED
CROSS_BUILDER_RESUME = ELIMINATED
CROSS_BUILDER_CLEANUP = ELIMINATED
MTIME_AS_IDENTITY = NO
MTIME_AS_EQUIVALENT_CANDIDATE_TIEBREAKER = YES
BUILDER_RESTORE_VALIDATION = VERIFIED
LEGACY_BUILDER_MIGRATION = VERIFIED
AMBIGUOUS_LEGACY_AUTO_RESUME = NO
BACKLOG1_IDENTITY_INTACT = YES
BACKLOG2_CONFIDENCE_INTEGRITY_INTACT = YES
GATE3_CAND_BEHAVIOR_UNCHANGED = YES
PR13_IMPORTED = NO
FULL_SUITE = PASS
QUALITY_GATES = PASS
SELF_MUTATING_VERIFICATION = NO
BACKLOG3_IMPLEMENTATION_COMPLETE = YES
BACKLOG3_PUBLISHED = NO
ISSUE16_CLOSED = NO
```
