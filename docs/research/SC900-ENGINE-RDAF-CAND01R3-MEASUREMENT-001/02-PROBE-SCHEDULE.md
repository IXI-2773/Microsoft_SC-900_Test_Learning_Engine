# 02 — Frozen PROBE schedule

```text
SCHEDULE_VERSION = cand01r3-probe-schedule-v1
PROBE_QUESTIONS = 29
DAYS = 7
DAY_CAPACITIES = 4,4,4,4,4,4,5
FAMILY_CLUSTERING_ON_A_DAY = 0
```

## Why this distribution

Task 6 justified about four first-attempt PROBE items per day. 4×6+5=29 covers every PROBE ID once. The extra Day-7 slot is required by the 29-item remainder, not by a desire to overweight one policy.

A greedy occupancy-balancing placer clustered the largest family on Day 7. That is avoidable contamination of family-level independence. The frozen schedule therefore uses a deterministic largest-first interleaved backtracking pack:

1. Order families by descending size, then family id.
2. Interleave one remaining member from each family.
3. Assign each item to the earliest day that still has capacity and does not already contain that family.
4. Backtrack if a later item cannot be placed without clustering.

This keeps every family on distinct days. MFA (6) occupies six different days. No TRAIN IDs appear. Each question appears once.

## Frozen assignments

| Day | Policy context | Question ID | Family |
| --- | --- | --- | --- |
| 1 | SMART_PRACTICE | sc900_p1_q023 | entra_roles_rbac |
| 1 | SMART_PRACTICE | sc900_p1_q004 | multifactor_authentication |
| 1 | SMART_PRACTICE | sc900_p1_q024 | privileged_identity_management |
| 1 | SMART_PRACTICE | sc900_p1_q001 | shared_responsibility_model |
| 2 | RRC_1 | sc900_p1_q006 | azure_key_vault |
| 2 | RRC_1 | sc900_p1_q042 | multifactor_authentication |
| 2 | RRC_1 | sc900_p2_q042 | purview_portal |
| 2 | RRC_1 | sc900_p1_q011 | zero_trust_and_identity_perimeter |
| 3 | SMART_PRACTICE | sc900_p2_q015 | entra_roles_rbac |
| 3 | SMART_PRACTICE | sc900_p2_q018 | privileged_identity_management |
| 3 | SMART_PRACTICE | sc900_p2_q003 | shared_responsibility_model |
| 3 | SMART_PRACTICE | sc900_p2_q004 | zero_trust_and_identity_perimeter |
| 4 | RRC_1 | sc900_p2_q026 | azure_key_vault |
| 4 | RRC_1 | sc900_p3_q062 | entra_roles_rbac |
| 4 | RRC_1 | sc900_p2_q011 | multifactor_authentication |
| 4 | RRC_1 | sc900_p3_q029 | purview_portal |
| 5 | SMART_PRACTICE | sc900_p3_q034 | multifactor_authentication |
| 5 | SMART_PRACTICE | sc900_p3_q053 | privileged_identity_management |
| 5 | SMART_PRACTICE | sc900_p3_q002 | shared_responsibility_model |
| 5 | SMART_PRACTICE | sc900_p3_q001 | zero_trust_and_identity_perimeter |
| 6 | RRC_1 | sc900_p3_q097 | azure_key_vault |
| 6 | RRC_1 | sc900_p3_q073 | entra_roles_rbac |
| 6 | RRC_1 | sc900_p3_q052 | multifactor_authentication |
| 6 | RRC_1 | sc900_p3_q040 | purview_portal |
| 7 | DAY7_BALANCED_MEASUREMENT | sc900_p3_q084 | entra_roles_rbac |
| 7 | DAY7_BALANCED_MEASUREMENT | sc900_p3_q063 | multifactor_authentication |
| 7 | DAY7_BALANCED_MEASUREMENT | sc900_p3_q064 | privileged_identity_management |
| 7 | DAY7_BALANCED_MEASUREMENT | sc900_p3_q012 | shared_responsibility_model |
| 7 | DAY7_BALANCED_MEASUREMENT | sc900_p3_q051 | zero_trust_and_identity_perimeter |

Do not regenerate this schedule at runtime. Authority is the committed protocol JSON.
