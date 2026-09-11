# RRC-1 Fairness And Starvation Review

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Repository Semantics

The existing predicates are separable:

- `progress_store.py:299` defines `is_active_weak(record)`.
- `progress_store.py:479` defines `is_review_due(record, on_date=None)`.
- `progress_store.py:542` defines `select_due_review_questions(...)`.
- `app_session_builder_mixin.py:944` builds the current weak-retest pool.
- `app_session_builder_mixin.py:987` builds the current due-review pool.

`is_active_weak(...)` returns true when the item is unsuspended, has wrong attempts, and either the last answer was wrong or wrong count exceeds correct count. `is_review_due(...)` returns true when the normalized next-review date is due or when an attempted item lacks a next-review date and has very low retrievability.

These semantics support RRC-1 class precedence in principle: a future RRC-1 snapshot can evaluate `is_active_weak(...)` first and assign REPAIR before REVIEW.

## Mutual Exclusivity Finding

RRC-1's proposed precedence genuinely removes the DWC-1 double-membership problem at the class-label level:

1. active weak items enter REPAIR;
2. due items already owned by REPAIR cannot also enter REVIEW;
3. COVERAGE receives only items not assigned to REPAIR or REVIEW.

This is a design improvement over overlapping DUE / WEAK / COVERAGE buckets.

Disposition: `SUPPORTED_IN_PRINCIPLE`

## Remaining Corner Cases

RRC-1 is not yet implementation-safe because class membership can shift after every answer:

- a wrong answer immediately changes active-weak state;
- a correct answer may still schedule near-term recovery review;
- `slow_success` and confidence can affect the legacy learner-memory next-review date even though RRC-1 itself must not consume confidence or response time directly;
- progress restore can import records whose due/weak status was not produced under the future partition rules.

Disposition: `UNRESOLVED_IMPLEMENTATION_DETAIL`

## Starvation Attack

Plain round-robin is not automatically fair.

Potential failures:

- persistent REPAIR backlog may consume every first service slot and repeatedly delay highly overdue REVIEW items;
- REPAIR plus REVIEW may leave too little COVERAGE to sample under-covered blueprint units;
- if COVERAGE is sparse, the apparent challenger may become mostly a repair/review policy rather than the intended transparent comparator;
- if due items differ sharply in overdue age, round-robin gives no urgency beyond intra-class sorting.

The design currently says empty classes are skipped, but it does not specify:

- maximum allowable REVIEW lateness;
- minimum COVERAGE share over a rolling window;
- how to report RRC-1 sessions where one class dominates;
- whether a session with no COVERAGE remains valid for the policy comparison.

Disposition: `MATERIAL_UNRESOLVED`

## Fairness Attack

RRC-1 is meaningful only if it is not deliberately weak and not accidentally advantaged.

Risk against RRC-1:

- Smart Practice uses many additional signals, while RRC-1 uses only three service classes. If bank quality is poor, RRC-1 may look worse because it lacks source-quality protections.

Risk favoring RRC-1:

- RRC-1's simplicity could avoid noisy Smart Practice overfitting, especially when analytics are under-sampled.
- If RRC-1 receives cleaner, easier, or better-balanced question blocks, it could appear superior for non-policy reasons.

Disposition: `MATERIAL_UNRESOLVED_UNTIL_BANK_ALLOCATION_EXISTS`

## Gate Consequence

RRC-1 is a plausible comparator, but positive Gate 2 closure is blocked until starvation reporting, overdue safeguards, coverage minimums, and arm allocation controls are specified against a real reviewed bank.