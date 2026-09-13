# SC900-BANK-PHASE3-001 — Task 7 RRC-1 Fairness and Starvation Obligations

```text
RRC1_FAIRNESS_METRICS = SPECIFIED
RRC1_STARVATION_METRICS = SPECIFIED
RRC1_EMPIRICAL_THRESHOLDS = NOT_INVENTED
RRC1_CLASS_EXCLUSIVITY = SPECIFIED
RUNTIME_RRC1_IMPLEMENTED = NO
UNSUPPORTED_RRC1_THRESHOLDS_INVENTED = NO
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_6_ACCEPTED_HEAD = `f2c9a04d109de1d5d91e3fd32d9e39568f3828c1`
SUPERSEDES_FOR_PHASE3 = `docs/research/SC900-ENGINE-RDAF-CAND01-GATE2-001/04-rrc1-fairness-and-starvation.md`
DOES_NOT_OVERWRITE = original Gate-2 file `04-rrc1-fairness-and-starvation.md`

Task 7 freezes measurable RRC-1 design-assurance requirements. It does **not** implement RRC-1, authorize Smart Practice changes, or invent pass/fail thresholds that repository authority and external evidence do not already establish.

A plausible comparator is not a fair comparator until service, starvation, and allocation obligations are measurable.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

Existing due/weak predicates were trusted as separable building blocks and then re-verified in current `progress_store.py`. Fairness was not inferred from class names. Bank growth does not prove RRC-1 would serve items fairly.

## Standing constraint

```text
IMPLEMENTATION_AUTHORIZED = NO
RUNTIME_RRC1_IMPLEMENTED = NO
```

RRC-1 remains the designated challenger to unchanged Smart Practice. TRAIN vs PROBE is **not** arm allocation. Both future arms may train only on TRAIN. See `10-TASK7-ALLOCATION-CONFOUNDS.md`.

## Frozen class model

RRC-1 conceptual classes remain:

```text
REPAIR
REVIEW
COVERAGE
```

Precedence at one assignment snapshot `t`:

1. REPAIR first
2. then REVIEW
3. then COVERAGE

Class membership is mutually exclusive at one snapshot.

### Assignment snapshot rule

Unit of assignment: one TRAIN-eligible canonical question ID.

Evaluation clock: calendar date `on_date` using the same date semantics as `progress_store.is_review_due(..., on_date=)`.

Authoritative predicates, re-verified:

- `progress_store.is_active_weak(record)` — unsuspended, `wrong_count > 0`, and either last answer wrong or wrong count exceeds correct count.
- `progress_store.is_review_due(record, on_date=None)` — normalized `next_review_at` / `next_review` is on or before `on_date`, or an attempted item lacks a next-review date and retrievability `<= 0.05`.

Assignment at snapshot `t`:

| Condition | Class |
| --- | --- |
| not TRAIN-eligible (PROBE, UNASSIGNED, missing/malformed role, unapproved, unresolved family, hash mismatch) | `EXCLUDED` — not in any RRC-1 class |
| TRAIN-eligible AND `is_active_weak` | `REPAIR` |
| TRAIN-eligible AND not REPAIR AND `is_review_due` | `REVIEW` |
| TRAIN-eligible AND not REPAIR AND not REVIEW | `COVERAGE` |

Suspended items are not served. They are reported separately and are not COVERAGE credit.

Flagged-but-not-weak-and-not-due items remain COVERAGE. Task 7 does not invent a fourth FLAG class. Flag status is a covariate, not a service class.

Confidence, response time, and `slow_success` must not determine class membership. Those fields may appear in reports as covariates only.

After every answer, the next snapshot may reassign the item. That is expected. Metrics therefore use both snapshot membership and service-event labels recorded at the moment of service.

Empty-class behavior: an empty class is skipped for that service slot. Skipping is allowed. It must be recorded as `EMPTY_CLASS_SKIP`, not treated as successful service of that class.

PROBE items never enter RRC-1 queues. A PROBE item with due or weak progress is contamination evidence, not a REPAIR/REVIEW candidate.

## Service event

A **service event** is one RRC-1-scheduled scored presentation of a TRAIN-eligible item during a training session.

Not service events:

- prewarm/cache computation without display;
- list-row visibility without opening the item;
- analytics rows;
- restore/import without a new scored attempt;
- follow-up injectors that are not the RRC-1 scheduler (those are Smart Practice / current-engine paths, not RRC-1 until RRC-1 is implemented).

Until RRC-1 exists, these metric definitions are obligations on the future implementation. Current Smart Practice/due/weak pools are **not** treated as RRC-1 service.

## Required metrics

No metric below carries an invented acceptable value. Where a threshold is not already established by repository authority or cited external evidence:

```text
THRESHOLD_STATUS = UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER
```

Report the statistic. Do not convert it into a silent pass.

Default analysis windows, unless a later protocol predeclares otherwise:

- `SESSION` — one RRC-1 session;
- `ROLLING_7D` — calendar 7 days ending at evaluation time;
- `EPOCH` — one predeclared policy-exposure epoch.

### MAX_SERVICE_DELAY

Question answered: how long can a due REVIEW (or a REPAIR) item wait after becoming eligible before it is served?

- Unit of analysis: TRAIN-eligible canonical question ID.
- Clock: calendar days. `due_at` is the first `on_date` on which the item is in REVIEW (or, for REPAIR delay, first date in REPAIR). `served_at` is the date of the first subsequent RRC-1 service event in that class.
- For still-unserved items, `open_delay = evaluation_date - due_at`.
- Statistic: maximum of closed delays among items served in the window, and separately the maximum open delay among still-unserved items in that class.
- Also report median and 90th percentile. The named metric is the maximum.
- Numerator/denominator: not a rate. It is a duration.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

Do not invent a maximum acceptable days overdue.

### OVERDUE_RATE

- Window: `ROLLING_7D` and `SESSION`.
- Snapshot used: last snapshot in the window, plus any item that was REVIEW-eligible at any snapshot in the window (report both; label them `POINT` and `EVER`).
- Numerator (`POINT`): count of TRAIN-eligible items in REVIEW at evaluation whose `is_review_due` is true and who received zero REVIEW-class service in the window.
- Denominator (`POINT`): count of TRAIN-eligible items in REVIEW at evaluation.
- Numerator (`EVER`): items that were REVIEW-due at some snapshot in the window and received zero REVIEW service while due.
- Denominator (`EVER`): items that were REVIEW-due at some snapshot in the window.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

### STARVATION_RATE

Starvation event: an item remains in class `C` for the entire window, the class was non-empty, at least one RRC-1 service event occurred in the window, and the item received zero service.

- Unit: TRAIN-eligible canonical question ID.
- Numerator: starved items in class `C`.
- Denominator: items that were in class `C` for the entire window (stable membership). Also report a second denominator: items that spent at least one snapshot in `C` (`EVER`).
- Compute separately for REPAIR, REVIEW, and COVERAGE.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

Do not invent an acceptable starvation percentage.

### QUEUE_AGE

- Unit: TRAIN-eligible item currently in class `C`.
- Clock: calendar days since the item’s current continuous class-membership start.
- Statistics: mean, median, max per class at evaluation snapshot.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

### COVERAGE_DEBT

Coverage is about unseen or under-served TRAIN material, not about probe items.

Primary leaf version:

- Numerator: count of TRAIN-eligible blueprint leaves with zero RRC-1 COVERAGE service in the window.
- Denominator: count of TRAIN-eligible blueprint leaves present in the frozen TRAIN set.

Family version (required companion):

- Numerator: TRAIN semantic families with zero COVERAGE service in the window.
- Denominator: 20 TRAIN families.

Item version:

- Numerator: TRAIN-eligible items with attempts = 0 at evaluation and zero COVERAGE service in the window.
- Denominator: TRAIN-eligible items with attempts = 0 at window start.

THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

Do not invent a minimum acceptable COVERAGE percentage.

### DOMAIN_SERVICE_BALANCE

- Unit: service events in the window.
- Numerator: service events whose item domain = `D`.
- Denominator: all RRC-1 service events in the window.
- Comparator: share of TRAIN questions in domain `D` (Task-6 TRAIN counts: identity 16, Entra 41, security 73, compliance 41).
- Report signed difference `(service_share - train_share)` per domain. Do not treat difference = 0 as a pass requirement.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

### OBJECTIVE_SERVICE_BALANCE

Same construction as domain balance, using SC-900 objective codes as the grouping key.

- Numerator: service events in objective `O`.
- Denominator: all RRC-1 service events in the window.
- Comparator: TRAIN question share in objective `O`.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

### CLASS_SERVICE_SHARE

- Numerator: RRC-1 service events labeled REPAIR, REVIEW, or COVERAGE.
- Denominator: all RRC-1 service events in the same window.
- Windows: `SESSION` and `ROLLING_7D`.
- Empty-class skips are not counted as service.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

### BACKLOG_SIZE

- Unit: items.
- Value: count of TRAIN-eligible items in REPAIR, REVIEW, COVERAGE, and EXCLUDED at the evaluation snapshot.
- Also report suspended count as a sidecar.
- THRESHOLD_STATUS = not applicable (stock statistic). No invented “healthy backlog” size.

### SESSION_CLASS_DOMINANCE

- For each session, `dominance = max(CLASS_SERVICE_SHARE over {REPAIR, REVIEW, COVERAGE})`.
- Also record:
  - `ZERO_COVERAGE_SESSION` = session with COVERAGE share = 0;
  - `ZERO_COVERAGE_WHILE_BACKLOG` = ZERO_COVERAGE_SESSION AND COVERAGE BACKLOG_SIZE > 0 at session start;
  - `SINGLE_CLASS_SESSION` = two classes have share = 0 and one class has share = 1.
- Report counts and rates over sessions in the epoch.
- THRESHOLD_STATUS = `UNRESOLVED_POLICY_OR_EMPIRICAL_PARAMETER`

A session with no COVERAGE is not automatically invalid. It is invalid **as a complete three-class demonstration** when COVERAGE backlog existed and received no service. Whether such sessions remain usable in a policy comparison is an unresolved analysis rule, not a hidden pass.

## Fair comparator contract

RRC-1 must be neither deliberately weak nor accidentally advantaged relative to Smart Practice.

Future comparison must measure and report, for each policy arm, over the same TRAIN set:

| Factor | Why it can confound |
| --- | --- |
| Source quality / source family | Smart Practice already uses source-risk settings; RRC-1 must not receive only high-trust leftovers or only low-trust leftovers |
| Question difficulty / calibration | An arm that sees easier items can look more effective |
| Blueprint / domain / objective balance | Task-6 TRAIN is 171 items across 20 families; imbalance is a selection confound |
| Semantic-family distribution | Family-level teaching, not item count, is the transfer unit |
| Number of training exposures | Dose, not scheduler intelligence, can drive later probe scores |
| Timing / due-age distribution | RRC-1 REVIEW is due-driven; Smart Practice mixes many signals |
| Repair backlog severity | A larger weak set makes REPAIR-first look either heroic or starved |
| Policy exposure dose before each PROBE measurement | See allocation receipt |

Hard rules:

- RRC-1 must not receive easier or cleaner material than Smart Practice by construction.
- Smart Practice must not receive systematically richer coverage, with the difference then attributed solely to scheduling intelligence.
- Both arms train only on TRAIN. PROBE is measurement holdout for both.
- If matching cannot be complete, the imbalance is modeled/reported. Unreported imbalance invalidates causal attribution.

Task 7 does not implement arm assignment.

## Starvation-attack matrix

Each attack is a design test the future RRC-1 implementation and its tests must be able to expose. Metrics named below are the detection instruments, not pass thresholds.

| Attack | What it looks like | Metric that exposes it | Future obligation |
| --- | --- | --- | --- |
| Persistent REPAIR backlog | Weak items consume every first slot | `CLASS_SERVICE_SHARE(REPAIR)` near 1; `MAX_SERVICE_DELAY(REVIEW)` and `OVERDUE_RATE` rise | Implementation must record class of every service event; test fixture with a large weak set and due items |
| Persistent overdue REVIEW backlog | Due items remain due while other classes are served | `OVERDUE_RATE`; `QUEUE_AGE(REVIEW)`; `STARVATION_RATE(REVIEW)` | Test with many overdue TRAIN items and a small REPAIR set |
| COVERAGE receiving no service | Scheduler never samples unseen TRAIN material | `COVERAGE_DEBT`; `ZERO_COVERAGE_WHILE_BACKLOG`; `STARVATION_RATE(COVERAGE)` | Test with non-empty COVERAGE backlog |
| One domain monopolizing service | One SC-900 domain takes nearly all slots | `DOMAIN_SERVICE_BALANCE` | Test with unbalanced due/weak by domain |
| One objective monopolizing service | One objective consumes the window | `OBJECTIVE_SERVICE_BALANCE` | Same, at objective grain |
| Old REVIEW items never served | Newest due items always win intra-class sort | `MAX_SERVICE_DELAY`; `QUEUE_AGE` max vs median gap | Test must include old and new due dates; current `select_due_review_questions` sorts by `next_review` then wrong_count, which can starve older-but-not-most-due items depending on dates — future RRC-1 must report this, not assume round-robin inside class is enough |
| New REPAIR items permanently jumping queue | Fresh wrongs preempt older REPAIR | `QUEUE_AGE(REPAIR)` for old members vs service share of items whose REPAIR age < 1 day | Test: one chronic weak item plus a stream of new wrongs |
| Empty-class behavior | No due items, or no weak items | `EMPTY_CLASS_SKIP` count; remaining class shares | Empty skip is allowed; test that skip does not invent fake service and does not pull PROBE fillers |
| Restore/import pathological backlog | Restored progress marks many items weak/due | `BACKLOG_SIZE` jump; `OVERDUE_RATE`; RESTORE test from leakage matrix | Restored class membership is recomputed; PROBE records cannot enter backlog |
| Sessions with zero COVERAGE | Session is only repair/review | `SESSION_CLASS_DOMINANCE`; `ZERO_COVERAGE_SESSION` | Report; do not silently drop those sessions from fairness reporting |
| Sessions dominated by one class | One class share = 1 | `SINGLE_CLASS_SESSION`; `CLASS_SERVICE_SHARE` | Report as a fairness diagnostic |

Current engine observation relevant to a later implementation: `build_weak_retest_pool` currently unions flagged, due, and active-weak, then may fall back to analytics-weak domains. RRC-1 must **not** copy that union. Mutual exclusivity is the design improvement over overlapping DUE/WEAK/COVERAGE buckets. Copying the current weak-retest union would reintroduce double membership.

## What remains unresolved on purpose

```text
maximum acceptable days overdue = NOT INVENTED
minimum COVERAGE percentage = NOT INVENTED
acceptable starvation percentage = NOT INVENTED
dominance pass/fail cut = NOT INVENTED
whether a zero-COVERAGE session is excluded from the policy comparison = UNRESOLVED_ANALYSIS_RULE
```

Task 7 makes the metrics measurable. It does not pretend the acceptable values are already known. Gate 2 still must not be reopened by this receipt. Empirical calibration, if it ever exists, belongs to later measurement work, not to invented constants.
