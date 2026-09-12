# BACKLOG-2 — Confidence Epistemics Integrity

## Scope

Issue #15 implementation from the publication-safe BACKLOG-1 lineage. Confidence is observed learner evidence. Unknown is neutral absence. Capture precedes persistence. One canonical answer-event identity. One correction authority. All derived state reconciles from canonical evidence.

Do not import PR #13. Do not start BACKLOG-3 or Day 1. Do not weaken BACKLOG-1 identity semantics or Gate-3 TRAIN/PROBE isolation.

Starting point: `5610d25009b3006183cb0ac1a63a7c99d1f89c66` on `publication/sc900-backlog1-without-measurement`.

Implementation branch: `implementation/sc900-backlog2-confidence-epistemics`.

## Invariant

```
observed confidence ∈ {Sure, Unsure, Guessed}
unobserved confidence = Unknown
Unknown ≠ Sure
missing/invalid legacy confidence ≠ Sure
```

The system must distinguish "learner explicitly chose Sure" from "no confidence value exists."

## Lifecycle

```
answer selection
  → confidence capture (or explicit unobserved commit)
  → answer commit
  → derived epistemic classification
  → canonical event persistence
  → current-session history
  → learner-memory / Smart Practice / rewards / analytics
```

Do not persist an ordinary answer as Sure and later ask the learner to correct it.

## Confidence states

| State | Meaning | Source |
| --- | --- | --- |
| Sure | learner explicitly chose Sure | observed |
| Unsure | learner explicitly chose Unsure | observed |
| Guessed | learner explicitly chose Guessed | observed |
| Unknown | not observed, or cannot be proven | absence / experimental-neutral / exam-unrevealed |

UI capture buttons remain the three observed values. Unknown is never a capture choice.

## Normalization

`normalize_confidence` is the user/legacy boundary:

- `Sure` / `Unsure` / `Guessed` remain unchanged
- `None`, `""`, whitespace, invalid labels → `Unknown`
- never `Sure`

Fail-closed `require_observed_confidence` is the capture/retag API boundary. Invalid programmer targets raise. Do not silently coerce retag/capture targets to Unknown or Sure.

Unanswered records keep empty `last_confidence`. Empty on an unanswered question is not an answer event.

## Capture UX

Restore the existing popover path (`pending_feedback_request`, `_complete_feedback_choice`, feedback popover controls).

Ordinary non-experimental modes:

- Single-choice: stage selection → ask Sure/Unsure/Guessed → commit
- Multi-choice: stage choices → Submit → ask confidence → commit
- Keyboard Submit/Return enters the same contract and cannot bypass capture

Exam mode before reveal: do not collect confidence and do not reveal correctness. Commit `Unknown`. After reveal, retag may supply observed confidence.

CAND/PROBE or other Gate-3 suppressed-feedback paths: do not introduce a confidence prompt. Commit `Unknown`. Never Sure.

## Diagnosis

Observed confidence drives miss-reason and recall-failure:

| Outcome | Confidence | miss_reason | recall_failure | review grade |
| --- | --- | --- | --- | --- |
| wrong | Guessed | Did not know | Blank recall | lapse |
| wrong | Unsure | Narrowed to two | Concept interference | lapse |
| wrong | Sure | Misread | Cue / wording miss | lapse_strong |
| wrong | Unknown | (empty unless proven) | Unclassified miss | lapse |
| correct | Guessed | (empty) | Recognition without recall | recognition |
| correct | Unsure | (empty) | Fragile retrieval | partial |
| correct | Sure | (empty) | (empty) | confident |
| correct | Unknown | (empty) | (empty) | unobserved |

Unknown must not fabricate Misread, Did not know, Concept interference, or confident-miss.

## Answer-event identity

Each committed answer gets `answer_event_id` once.

Properties:

- generated at commit
- unique within learner history
- copied into progress history, `session_answer_history`, runtime current-attempt state, and session snapshots
- preserved through save/restore
- not a question number
- canonical question ID remains question identity (BACKLOG-1)

New attempts (redo/retry) create a new event. They do not mutate the previous event.

## Correction authority

`correct_answer_event_confidence(answer_event_id, confidence)` is the only mutation path for confidence on a committed event.

It must atomically update, as applicable:

1. runtime question state for that event
2. canonical progress record
3. persistent progress-history event
4. matching `session_answer_history` event
5. confidence counts rebuilt from that question's history
6. miss-reason counts rebuilt from that question's history
7. miss_reason
8. recall_failure
9. learner-memory rebuilt from that question's canonical history
10. next-review consequences
11. Smart Practice cache/signal invalidation
12. current-session reward/quest inputs recomputed from session history
13. analytics cache invalidation
14. persisted session snapshot

`retag_current_answer_confidence` and `mark_current_question_super_confident` call this authority.

Super-confident cooldown/status stays separate from the confidence observation. Super-confident implies `confidence = Sure` plus scheduling metadata. Do not treat cooldown as a fourth confidence state.

## Learner-memory reconciliation

Do not invert arithmetic ("subtract old effect, add new effect").

Rebuild the affected question's derived learner-memory from canonical answer-event history, in stored order, canonical-ID scoped, content-epoch safe, idempotent.

Legacy events without `answer_event_id` still replay by chronological order using normalized confidence (Unknown for absence). That is bounded fail-safe migration, not invented certainty.

## Legacy event-ID migration

If one snapshot answer can be uniquely paired with one canonical persisted event and one session event, bind a deterministic `answer_event_id`.

If pairing is ambiguous, do not silently bind. Preserve usable learner state. Do not invent Sure.

Explicit legacy Sure/Unsure/Guessed remain unchanged.

## Rewards / quests / analytics

Current-session quest progress and analytics rebuild from canonical session/progress events after correction.

Already-unlocked irreversible badges/XP remain monotonic. Do not silently revoke historical achievements. XP granted at original commit is not rewritten.

Unknown does not receive Sure's XP or weighting.

## Restore / redo / exam / CAND

A restored session preserves `answer_event_id`, confidence, miss_reason, and recall_failure for committed answers. Retag after resume targets that event.

Redo creates a new event. Retagging the latest attempt does not mutate the previous attempt.

Exam unrevealed answers record Unknown and do not surface correctness through the capture UI.

Gate-3 TRAIN/PROBE isolation is unchanged. PR #13 measurement code is absent and must remain absent.

## Out of scope

BACKLOG-3. PR #13 import. Day 1. Publication merge. Changing exam scoring. Changing TRAIN/PROBE membership.
