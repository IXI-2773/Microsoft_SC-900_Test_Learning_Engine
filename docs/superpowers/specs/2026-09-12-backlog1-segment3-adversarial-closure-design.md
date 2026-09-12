# BACKLOG-1 Segment 3 — Adversarial Identity, History, Bank-Epoch, and Migration Closure

## Scope

Final BACKLOG-1 implementation from Issue #14. Close residual learner-identity authority across progress content epoch, persisted history, session answer history, analytics/Smart Practice joins, follow-up deduplication, and explicit bank-revision migration.

Do not begin BACKLOG-2 or BACKLOG-3. Do not modify PR #13 or frozen CAND-01R3 scientific artifacts.

Starting point: `909fca8a70232639bab0ad6ef458f1733816a1ec` on `implementation/sc900-backlog1-session-identity`.

Implementation branch: `implementation/sc900-backlog1-adversarial-closure`.

## Durable identity hierarchy

```
canonical question_id
  → per-question content fingerprint + bank/content fingerprint
    → question_number as presentation/order/legacy-migration metadata only
```

Question number remains valid for UI labels, ordering, diagnostics, explicit legacy migration lookup, and proven runtime-local non-durable operations inside one current-bank pass.

## Content identity

Reuse the Segment-2 canonical projection. Move the durable-field projection into `question_identity.py` so progress and session share one hashing algorithm.

Per-question content fingerprint:

- SHA-256 of the same path-independent projection used by `bank_content_fingerprint`
- includes canonical ID plus durable content fields
- choice identity is letter-independent: sorted choice texts, correct texts, and explanation texts
- excludes `question_number`, runtime/learner state, timestamps, provenance bookkeeping, `choice_order`, and empty explanation maps
- same durable content + reorder/renumber/choice-letter shuffle = same fingerprint
- authoritative content change (prompt, correct text, distractor text, etc.) = different fingerprint

Bank/content fingerprint remains the ordered-by-ID hash of those projections. Bank expansion/removal changes the bank fingerprint even when existing question fingerprints are unchanged.

## Progress schema

Keep Segment-1 `progress_identity_version = 1` / `question_identity = canonical_question_id` as the canonical-ID layer.

Add a separate identity-specific epoch layer rather than abusing `PROGRESS_VERSION`:

- `progress_content_epoch_version = 1`
- `bank_fingerprint`
- `question_content_fingerprints: {question_id: fingerprint}`
- `quarantined_questions` for removed or changed-content records

Segment-1 `migrate_legacy_progress_keys` remains number→ID only. Persistence chains a new `migrate_progress_content_epoch` after that migration.

## Bank revision algorithm

Deterministic and idempotent, with a pre-mutation backup when the persisted payload changes.

| Case | Behavior |
| --- | --- |
| Same ID + same content fingerprint, possibly new number | Preserve learner state |
| New ID | Initialize empty; do not disturb valid state |
| Missing ID | Quarantine; never reassign onto another item |
| Same ID + different content fingerprint | Quarantine; never silently inherit |
| Same number + different ID | No inheritance; number is not authority |
| Reorder only | Bank fingerprint unchanged; no state loss |
| Duplicate / missing canonical IDs in bank | Fail closed |

First bind of Segment-1 canonical state (ID present, fingerprints absent) stamps the current bank as the assumed epoch. That is the only unproven content bind, and it is explicit migration rather than runtime matching. Later content mutation is detected.

## History

New `QuestionHistoryEvent` writes include `question_id` and `question_content_fingerprint`. `question_number` remains display metadata.

Runtime matching is canonical ID plus content-fingerprint agreement when the event carries a fingerprint. Number fallback is not a general runtime rule.

Legacy history without `question_id` migrates only inside an explicit migration boundary:

- unique number→ID mapping under current bank authority → stamp ID + current fingerprint
- ambiguous mapping → fail closed / quarantine
- unmapped number → preserve as unresolved historical evidence; do not attach
- number reused by a different ID → never cross-attach

## Session answer history

New `SessionAnswerEvent` writes require `question_id` and carry content fingerprint. Restore and Smart Practice signal keys join by canonical ID. Schema-4 snapshots that already have session `question_ids` may stamp missing answer-history IDs only from that snapshot’s own ID/number pairing, never from the live bank’s numbers.

## Joins, builder, follow-up

Persisted learner evidence joined to current questions uses canonical ID (and content fingerprint when present). Internal scoring maps may still index the current bank by `question_number` only after that join, inside one call, without cache survival across bank epochs.

Generic builder filters are not question identity. Question-specific builder/session state is already bounded by Segment-2 bank fingerprint + canonical session identity.

Follow-up / insertion uniqueness is canonical question ID. CAND TRAIN/PROBE enforcement is unchanged.

## Full-suite debt

Segment-2 left 5 FAIL + 1 ERROR. Treat CAND record maps keyed by question number and `SessionBuilderHarness.compute_analytics` as stale interface mismatches against Segment-1 canonical keys, not as scientific-authority changes. Repair harness/test record identity so observational TRAIN/PROBE/RRC1 class membership remains the same.

## Non-goals

Do not redesign confidence epistemics, generic builder-preference identity, content ingestion, or frozen CAND-01R3 protocol/timing/membership.
