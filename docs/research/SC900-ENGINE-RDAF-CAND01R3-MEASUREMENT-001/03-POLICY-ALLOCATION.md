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

| Day | Policy | Training | Primary policy contrast |
| --- | --- | --- | --- |
| 1 | SMART_PRACTICE | yes | yes |
| 2 | RRC_1 | yes | yes |
| 3 | SMART_PRACTICE | yes | yes |
| 4 | RRC_1 | yes | yes |
| 5 | SMART_PRACTICE | yes | yes |
| 6 | RRC_1 | yes | yes |
| 7 | DAY7_BALANCED_MEASUREMENT | yes, both arms, 10 TRAIN items each | no |

Days 1–6 give each policy three training/measurement days (12 scheduled PROBE items each). Day 7 is predeclared as a balanced dual TRAIN block (SMART_PRACTICE then RRC_1, 10 TRAIN items each) followed by the remaining five PROBE items. Those five items are descriptive / time-trend observations, not part of the simple Day 1–6 policy contrast.

SMART_PRACTICE still starts Day 1. That order is a logged confound, not hidden randomization.

## Shared universe

Both arms train on the same 171 TRAIN questions / 20 families. Neither may consume PROBE. Historical prior fields must not affect `allocated_policy_for_day`.

## No automatic promotion

At experiment completion the engine must not switch to whichever arm has higher raw accuracy. Promotion requires a later empirical adjudication package.
