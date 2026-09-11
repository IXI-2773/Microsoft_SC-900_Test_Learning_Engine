# Authority Reconstruction

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Authority Chain Read

The current authority map is `docs/research/SC900-ENGINE-RDAF-SUCCESSOR-002/README.md`.

Authority order:

1. `README.md`
2. `04-profile-informed-cand01r2-revision.md`
3. `02-historical-data-extraction-protocol.md`
4. `03-runtime-archive-disposition.md`
5. `01-cand01r2-historical-learner-prior.md`
6. `00-cand01-revised-design.md`

The earlier DWC-1 comparator remains historical lineage only. Current comparator authority is RRC-1.

## Current Candidate

`CAND-01R2 - Historical Learner Prior + Held-Out Policy Verification`

It consists of four coupled elements:

1. **Smart Practice champion unchanged.** The incumbent remains the existing Smart Practice runtime.
2. **RRC-1 challenger.** RRC-1 uses existing engine predicates and metadata through mutually exclusive `REPAIR`, `REVIEW`, and `COVERAGE` classes.
3. **Hard TRAIN / PROBE isolation.** PROBE items must not be exposed through training, repair, review, coverage, twins, follow-ups, quests, exam/practice builders, prewarm pools, analytics, restore, or other answer-revealing paths before the scored probe attempt.
4. **Historical learner-strategy prior with decay.** SY0-701 history may initialize exam-independent study strategy only, never SC-900 content mastery.

## RRC-1 Reconstruction

For each eligible TRAIN item:

- `REPAIR`: `is_active_weak(...)` is true. REPAIR owns the item even if also due.
- `REVIEW`: not REPAIR and `is_review_due(...)` is true.
- `COVERAGE`: not REPAIR or REVIEW, and serves an under-covered SC-900 blueprint unit.

Service order:

`REPAIR -> REVIEW -> COVERAGE -> repeat`

Empty classes are skipped. No weighted utility model is allowed.

## Primary Endpoint

Champion and challenger share one primary endpoint:

`7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items`

Immediate repeated-bank accuracy, XP, streaks, total questions answered, session score, and engagement are not substitutes.

## Prospective Prediction

Active prediction:

`P1R2`

On a sufficiently large reviewed SC-900 bank with clean TRAIN / PROBE separation, RRC-1 will perform within `0.05` absolute accuracy of current Smart Practice on the primary endpoint unless Smart Practice's additional machinery contributes practically important incremental learning value.

Let `Delta = SmartPractice_accuracy - RRC1_accuracy`.

- Smart Practice practical superiority: interval for Delta entirely above `+0.05`.
- RRC-1 practical superiority: interval for Delta entirely below `-0.05`.
- Practical equivalence: interval entirely inside `[-0.05, +0.05]`.
- Otherwise: `INCONCLUSIVE`.

## Authority Anomaly

`03-runtime-archive-disposition.md` still includes a historical attack bullet asking whether "DWC-1 is a fair challenger." Under the README and `04` authority, this is superseded wording. Gate 2 treats the current challenger as RRC-1 while preserving that note as lineage evidence that comparator fairness remains a live issue.