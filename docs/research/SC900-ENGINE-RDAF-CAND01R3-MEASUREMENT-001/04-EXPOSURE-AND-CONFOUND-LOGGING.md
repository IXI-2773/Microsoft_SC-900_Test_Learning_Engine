# 04 — Exposure and confound logging

Every real PROBE event stores raw provenance, not a mutable summary in place of the event.

## Event fields

`event_id`, `evaluation_id`, `learner_id`, `exam`, `measurement_epoch`, `calendar_timestamp`, `scheduled_day`, `question_id`, `semantic_family_id`, `domain`, `objective`, `policy_context`, `intended_use`, `first_attempt`, `clean`, `contaminated`, `contamination_reason`, `observed`, `correct` if observed, selected option ids, TRAIN exposure snapshot, policy exposure snapshot.

## TRAIN exposure snapshot (by policy)

- TRAIN questions seen
- unique TRAIN questions seen
- semantic families seen
- domain counts
- objective counts
- REPAIR / REVIEW / COVERAGE service counts
- session duration if reliable

Exposure is an explanatory/confound variable. It is not a hidden score adjustment.

## Counted TRAIN exposure

One counted exposure = one TRAIN question presented in the scheduled policy-controlled training session, including repeats if the same TRAIN item is shown again. Do not count PROBE items, rejected/not-eligible items, render failures, administrative previews, debug/review views, measurement-card display, or unobserved PROBE records.

Days 1–6 stop at 20 counted exposures. Further policy-controlled TRAIN items are `OVER_BUDGET_TRAIN_EXPOSURE` / `TRAINING_AFTER_BLOCK_COMPLETE` deviations. They are recorded, not erased, and they do not count toward the frozen dose.

If an arm cannot supply 20 eligible TRAIN items, fail closed as `INSUFFICIENT_TRAIN_CAPACITY`. Do not fill the deficit with PROBE or uncontrolled items.

## RRC-1 fairness fields collected for later computation

`MAX_SERVICE_DELAY`, `OVERDUE_RATE`, `STARVATION_RATE`, `QUEUE_AGE`, `COVERAGE_DEBT`, `DOMAIN_SERVICE_BALANCE`, `OBJECTIVE_SERVICE_BALANCE`, `CLASS_SERVICE_SHARE`, `BACKLOG_SIZE`, `SESSION_CLASS_DOMINANCE`

No pass/fail threshold is authorized. Report measurements. Do not invent acceptable thresholds.

## Smart Practice exposure

Collect equivalent domain, objective, semantic-family, question-count, and session-length summaries. The challenger must not receive a different question universe.

## Order-effect fields

calendar day, policy used, session order, TRAIN exposures before each PROBE, domain/objective/family exposures, session length, outside-study declaration, experiment day / app familiarity.

## Outside-study declaration

Operator-recorded, not inferred:

`NONE`, `MICROSOFT_LEARN`, `BOOK`, `VIDEO_COURSE`, `PRACTICE_TEST`, `OTHER`

This metadata does not block study.

## Ledger location

Production events append to the learner user-data measurement JSONL for this epoch. Tests may use temporary ledgers. `TEST_ONLY` / `SYNTHETIC` events are rejected from the production ledger.
