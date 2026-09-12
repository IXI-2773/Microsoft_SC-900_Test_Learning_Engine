# 03 — Policy allocation

```text
POLICY_SEQUENCE_VERSION = cand01r3-alt-crossover-v1
CHAMPION = SMART_PRACTICE
CHALLENGER = RRC_1
ARM_ASSIGNMENT_FROZEN_BEFORE_RESULTS = YES
RANDOMIZATION = NO
```

Task 7 (`10-TASK7-ALLOCATION-CONFOUNDS.md`) requires a predeclared policy order and warns that a single unbroken order is a confound, not a footnote. A 7-day one-learner design cannot eliminate time trend. This package therefore freezes an alternating crossover rather than Smart Practice for the whole window and RRC-1 second.

## Frozen sequence

| Day | Policy | TRAIN budget | Primary policy contrast |
| --- | --- | --- | --- |
| 1 | SMART_PRACTICE | 20 | yes |
| 2 | RRC_1 | 20 | yes |
| 3 | SMART_PRACTICE | 20 | yes |
| 4 | RRC_1 | 20 | yes |
| 5 | SMART_PRACTICE | 20 | yes |
| 6 | RRC_1 | 20 | yes |
| 7 | DAY7_BALANCED_MEASUREMENT | 10 SMART_PRACTICE then 10 RRC_1 | no |

```text
SMART_PRACTICE_PRIMARY_TRAIN_EXPOSURES = 60
RRC1_PRIMARY_TRAIN_EXPOSURES = 60
PRIMARY_TRAIN_EXPOSURE_DIFFERENCE = 0
```

Days 1–6 give each policy three training/measurement days (12 scheduled PROBE items each) and exactly 20 TRAIN exposures per day. Day 7 remains a balanced dual TRAIN block followed by five descriptive/time-trend PROBE items.

v1 left Days 1–6 `train_item_budget = null`. That unbounded dose is superseded before empirical collection. Policy order is unchanged.

SMART_PRACTICE still starts Day 1. That order is a logged confound, not hidden randomization.

## Shared universe

Both arms train on the same 171 TRAIN questions / 20 families. Neither may consume PROBE. Historical prior fields must not affect `allocated_policy_for_day`.

## No automatic promotion

At experiment completion the engine must not switch to whichever arm has higher raw accuracy. Promotion requires a later empirical adjudication package.
