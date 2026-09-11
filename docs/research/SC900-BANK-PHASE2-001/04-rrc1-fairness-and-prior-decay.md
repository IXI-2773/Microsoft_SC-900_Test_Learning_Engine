# RRC-1 Fairness, Starvation, and Historical-Prior Decay Contract

WORK_ID = `SC900-BANK-PHASE2-001`
STATUS = `DESIGN_ONLY`

## RRC-1 service metrics

The Gate-2 attack established that mutually exclusive REPAIR / REVIEW / COVERAGE classes are coherent in principle but plain round-robin is not automatically fair. Phase 2 therefore freezes measurable service-risk definitions without inventing unsupported pass/fail thresholds.

### Maximum service delay

For each eligible item/class request:

```text
service_delay = service_time - first_eligible_time
maximum_service_delay(class, window) = max(service_delay)
```

Report separately for REPAIR, REVIEW, and COVERAGE. Averages cannot hide a starved tail.

### Overdue-service rate

For REVIEW-eligible items with a scheduled due time:

```text
overdue_age = service_time - due_time
overdue_service_rate(T) = serviced_review_items_with_overdue_age>T / serviced_review_items
```

`T` is not frozen in Phase 2. Gate 2 needs empirical SC-900 service traces or a defensible policy requirement before assigning a threshold.

### Starvation rate

Within a declared observation window:

```text
starvation_rate(class) = eligible_items_not_served_before_window_end / eligible_items_observed
```

Items that cease to be eligible for legitimate state reasons must be reported separately rather than counted as serviced.

### Queue age

Track current and terminal age distributions for:

- REPAIR queue;
- REVIEW queue.

Report maximum, median, and upper-tail quantiles rather than only mean age.

### Coverage debt

For each domain/objective, compare actual COVERAGE service share with the frozen allocation target appropriate to the experiment block:

```text
coverage_debt(unit) = target_service_count(unit) - actual_coverage_service_count(unit)
```

Positive debt indicates under-service. The report must preserve sign and unit identity; debts must not cancel across objectives.

### Domain/objective service balance

Report service counts/shares by domain and objective for each arm and service class. Arm comparisons must make selection-quality/blueprint imbalance visible rather than treating the scheduler label as the only independent variable.

## Threshold disposition

Phase 2 does not invent:

- a maximum allowable REVIEW lateness;
- a minimum COVERAGE share;
- a maximum acceptable starvation rate;
- a class-dominance cutoff.

These remain `UNRESOLVED_PARAMETER` until calibration has either:

1. prospective SC-900 service traces under both policies; or
2. an explicit experimental/policy requirement justified independently of observed outcomes.

Thresholds must be frozen before outcome inspection if they are later used as pass/fail gates.

## Historical-prior authority

The previously frozen authority rule remains unchanged:

- `SEED`: fewer than 10 clean SC-900 held-out probe outcomes;
- `ADVISORY`: 10–29 clean SC-900 held-out probe outcomes;
- `RETIRED`: at least 30 clean 7-day probe outcomes, all four domains represented, and at least 4 observations per domain.

After `RETIRED`, the historical prior loses decision authority and must never regain it.

## Future prior-decay tests

Later implementation must prove at least:

1. **Clean-count filtering** — contaminated, non-PROBE, non-SC-900, repeated, restored-duplicate, or otherwise invalid observations do not advance the stage.
2. **SEED→ADVISORY boundary** — the 10th valid observation changes authority exactly once as specified.
3. **All-domain retirement condition** — 30 total observations without all four domains or without four per domain cannot retire the prior.
4. **Retirement boundary** — once total/domain conditions are satisfied, authority becomes `RETIRED`.
5. **Monotonicity** — restore/import/device/bank-path changes cannot move `ADVISORY` back to `SEED` or `RETIRED` back to an active stage.
6. **Irreversible retirement** — after retirement the prior never regains decision authority.
7. **Direct-evidence precedence** — contradictory direct SC-900 evidence wins during ADVISORY according to the frozen authority semantics.
8. **No side-channel resurrection** — confidence, response time, legacy Security+ mastery, or unrelated analytics cannot increase prior authority.
9. **Missed observation semantics** — an unobserved 7-day probe is `UNOBSERVED`, not automatically wrong or correct.
10. **Duplicate custody** — retry/redo/backup/restore/export-import cannot double-count one evaluation observation.

## Gate effect

This package converts fairness/starvation and prior-decay concerns into measurable definitions and future tests, but runtime enforcement remains unproven. RRC-1 numeric fairness thresholds and prospective SC-900 evidence remain material Gate-2 work.
