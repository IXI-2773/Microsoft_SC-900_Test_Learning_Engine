# SC900-BACKLOG-2-CONFIDENCE-EPISTEMICS-001 — Confidence Integrity Closure

## Identity

| Field | Value |
| --- | --- |
| Repository | `IXI-2773/Microsoft_SC-900_Test_Learning_Engine` |
| Issue | #15 OPEN |
| Base branch | `publication/sc900-backlog1-without-measurement` |
| Base SHA | `5610d25009b3006183cb0ac1a63a7c99d1f89c66` |
| Implementation branch | `implementation/sc900-backlog2-confidence-epistemics` |
| Implementation verification SHA | `9782ee48f57d8604c063e28042b1e850b2697c2f` |
| Parent SHA | `5610d25009b3006183cb0ac1a63a7c99d1f89c66` |
| PR #12 Gate-3 head | `f742dcc085d46f1999eb8782f709730323e9d7f0` (ancestor: YES) |
| PR #13 frozen measurement head | `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` (ancestor: NO) |
| PR #19 | OPEN DRAFT UNMERGED; head `5610d25009b3006183cb0ac1a63a7c99d1f89c66`; not modified |

## Commit lineage

```
5610d25009b3006183cb0ac1a63a7c99d1f89c66 docs: record backlog-1 adversarial identity closure receipt
9782ee48f57d8604c063e28042b1e850b2697c2f feat: treat confidence as observed evidence with Unknown-neutral absence
```

A following docs commit may record this receipt. Implementation verification ran on `9782ee48f57d8604c063e28042b1e850b2697c2f`.

## Confidence-state contract

Canonical states: `Sure`, `Unsure`, `Guessed`, `Unknown`.

- Sure / Unsure / Guessed are explicit learner observations.
- Unknown means confidence was not observed or cannot be proven.
- Missing or invalid legacy values normalize to Unknown, never Sure.
- Capture/retag targets use fail-closed `require_observed_confidence`.
- Unanswered records keep empty `last_confidence`; empty on an unanswered question is not an answer event.

## Unknown semantics

Unknown is epistemically neutral:

- wrong + Unknown → empty miss_reason, `Unclassified miss`, review grade `lapse` (not `lapse_strong`)
- correct + Unknown → empty recall_failure, review grade `unobserved` (not `confident`)
- analytics weight `0.0` (not Sure's `1.0`)
- XP: no Sure/Unsure/Guessed bonus
- exam unrevealed and CAND non-TRAIN paths commit Unknown without a capture prompt

## Answer-event identity

`answer_event_id` is minted once at commit (`ae:` + uuid4 hex).

It is copied into:

- runtime current-attempt state
- `session_answer_history`
- persistent progress history
- session snapshot answers

Question number is not event identity. BACKLOG-1 canonical question ID remains question identity.

Legacy unique pairing uses `deterministic_legacy_answer_event_id`. Ambiguous pairing does not silently bind.

## Confidence-capture lifecycle

Ordinary non-experimental modes restore the existing popover path:

1. Stage selection (`toggle_choice` / `submit_answer` / Return)
2. Ask Sure / Unsure / Guessed
3. `_complete_feedback_choice` commits only after an observed choice

Keyboard Return cannot bypass capture. Open popover without an invoked confidence button does not persist an answer.

Exam before reveal and CAND non-TRAIN flows skip the prompt and commit Unknown.

## Retag reconciliation algorithm

`correct_answer_event_confidence(answer_event_id, confidence)` is the only mutation authority.

It locates the exact event, recomputes miss_reason and recall_failure, writes the same values into session history and persistent history, rebuilds confidence/miss-reason counts and learner-memory from that question's canonical history, updates progress `last_*` from the latest event, invalidates Smart Practice/analytics caches, and refreshes current-session quests.

`retag_current_answer_confidence` and `mark_current_question_super_confident` call this authority. Super-confident cooldown remains separate scheduling metadata; the observation is Sure.

## Learner-memory rebuild

No inverse arithmetic. Replay `update_learner_memory` in stored order, including the recovery-interval override used by `update_progress_record`. Canonical-ID scoped. Idempotent. Legacy events without `answer_event_id` still replay by chronology using normalized confidence (Unknown for absence).

## Downstream behavior

- Smart Practice: session-answer cache key includes `answer_event_id`, confidence, and miss_reason. Retag changes the identity; `invalidate_learning_state` drops stale payloads.
- Rewards/quests: current-session quest progress recomputes from `session_answer_history`. Already-unlocked badges and already-granted XP are monotonic and are not revoked.
- Analytics: Unknown is not treated as Sure. History/progress reads follow corrected events after cache invalidation.
- Restore: snapshots preserve `answer_event_id`, confidence, miss_reason, recall_failure. Retag after resume targets that event.
- Redo: clears runtime `answer_event_id` and creates a new event on the next commit. Retagging the latest attempt does not mutate the previous event.
- Exam: unrevealed answers record Unknown and do not reveal correctness through capture UI.
- Gate-3: no confidence prompts on PROBE; TRAIN/PROBE isolation unchanged.
- Legacy: explicit Sure/Unsure/Guessed unchanged; blank/invalid → Unknown.

## Confidence inventory

Material production classifications (tests excluded from F repair accounting):

| Class | Count | Notes |
| --- | --- | --- |
| A OBSERVED_CONFIDENCE_AUTHORITY | 14 | capture, normalize, require, record, correction, event/runtime fields |
| B DERIVED_CONFIDENCE_CONSUMER | 18 | miss-reason, recall-failure, review grade, memory, counts, SP, quests, XP, analytics |
| C LEGACY_MIGRATION | 6 | bind, deterministic IDs, restore empty→Unknown, invalid normalize |
| D PRESENTATION_ONLY | 5 | buttons, popover copy, palette, super-confident label |
| E EXPERIMENTAL_SUPPRESSED | 4 | exam Unknown, CAND non-TRAIN, unobserved_feedback, probe sanitizer unchanged |
| F DEFECT | 20 found / 20 repaired | all F defects repaired or unreachable after repair |

### F defects found and repaired

1. `_collect_answer_feedback` manufactured Sure.
2. `normalize_confidence` converted missing/invalid to Sure.
3. Single-choice `toggle_choice` recorded immediately.
4. Multi-choice `submit_answer` recorded immediately.
5. Keyboard Return/Submit could persist without observation.
6. Retag did not sync `session_answer_history`.
7. Derived fields (miss_reason, recall_failure, counts, learner-memory, review, analytics, SP, rewards) could disagree after retag.
8. Super-confident used divergent mutation logic.
9. `_infer_miss_reason_from_confidence` treated Unknown as Misread.
10. `classify_recall_failure` treated wrong+Unknown as cue/wording miss.
11. `infer_review_grade` treated correct+Unknown as confident.
12. `_apply_xp_for_answer` defaulted missing confidence to Sure.
13. Review UI defaulted displayed confidence to Sure.
14. Analytics `_confidence_weight` defaulted unknown/missing to 0.85.
15. `set_progress_super_confident` used `or "Sure"`.
16. No durable `answer_event_id`.
17. Session restore of empty confidence became Sure through `update_progress_record`.
18. Pending feedback lookup used question number.
19. `_show_feedback_popover` was missing while helpers expected it.
20. Return while a popover was active cancelled capture instead of preserving the contract.

## RED evidence

Focused unit tests on the approved base, before production repair:

- `normalize_confidence(None) == 'Sure'` (wanted Unknown)
- `normalize_confidence('bogus') == 'Sure'` (wanted Unknown)
- missing `confidence_epistemics` module
- redo did not clear `answer_event_id`

Genuine RED. Production code was not intentionally broken to manufacture RED.

## GREEN / verification evidence

Read-only verification on `9782ee48f57d8604c063e28042b1e850b2697c2f`.

| Check | Result |
| --- | --- |
| HEAD before | `9782ee48f57d8604c063e28042b1e850b2697c2f` |
| Worktree before | CLEAN |
| BACKLOG-1 Segment-1 | PASS |
| BACKLOG-1 Segment-2 | PASS |
| BACKLOG-1 Segment-3 | PASS |
| BACKLOG-2 focused | PASS (47 tests) |
| Gate-3 CAND (partition / all-path / RRC1 in full suite) | PASS |
| Full suite | PASS — 789 tests, 0 failures, 0 errors |
| `python -m tools.run_quality_checks` | PASS |
| `python -m tools.lint_bank` | PASS — 8 clean baseline questions |
| `python -m tools.verify_installation` | PASS |
| Phase-3 tests in full suite | PASS |
| HEAD after | `9782ee48f57d8604c063e28042b1e850b2697c2f` |
| Worktree after | CLEAN |
| TRACKED_SOURCE_MUTATION_DURING_VERIFICATION | NO |

## Protected refs

| Ref | SHA | Unchanged |
| --- | --- | --- |
| `recovery/publish-exact-history/sc900-v8-20260910` | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` | YES |
| `recovery/publish-sc900-v8-exact-history` | `bbc3bd900b73bde89151dc51706ad62fc69e8196` | YES |
| `sc900-v8.0.0-baseline` tag | `9c80be5b20e652dc2eb86621dfdf7c32baa06528` | YES |

## Publication / isolation status

- PR #13: OPEN, head `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb`, not imported, not modified, not merged
- PR #19: OPEN DRAFT, head/base unchanged, not modified by this branch
- Issue #15: remains OPEN until a later merge authorization
- Day 1: not started
- BACKLOG-3: not started
- No merge authorization is implied

## Acceptance

```
CONFIDENCE_IS_OBSERVED_EVIDENCE = YES
MISSING_CONFIDENCE_DEFAULTS_TO_SURE = NO
UNKNOWN_CONFIDENCE_STATE = IMPLEMENTED
SINGLE_CHOICE_CONFIDENCE_CAPTURE = VERIFIED
MULTI_CHOICE_CONFIDENCE_CAPTURE = VERIFIED
KEYBOARD_CONFIDENCE_CAPTURE = VERIFIED
CANONICAL_ANSWER_EVENT_ID = IMPLEMENTED
PERSISTENT_AND_SESSION_EVENT_IDENTITY = SYNCHRONIZED
RETAG_SPLIT_STATE = ELIMINATED
SUPER_CONFIDENT_SPLIT_STATE = ELIMINATED
MISS_REASON_RECOMPUTATION = VERIFIED
RECALL_FAILURE_RECOMPUTATION = VERIFIED
LEARNER_MEMORY_RECONCILIATION = VERIFIED
SMART_PRACTICE_CACHE_INVALIDATION = VERIFIED
REWARD_CONFIDENCE_STATE = SYNCHRONIZED
ANALYTICS_CONFIDENCE_STATE = SYNCHRONIZED
RESTORE_CONFIDENCE_STATE = VERIFIED
LEGACY_MISSING_CONFIDENCE = UNKNOWN
REDO_CREATES_NEW_EVENT = VERIFIED
BACKLOG1_REGRESSION = PASS
GATE3_CAND_REGRESSION = PASS
PR13_IMPORTED = NO
FULL_SUITE = PASS
QUALITY_GATES = PASS
SELF_MUTATING_VERIFICATION = NO
BACKLOG2_IMPLEMENTATION_COMPLETE = YES
BACKLOG2_PUBLISHED = NO
```
