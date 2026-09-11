# 05 — Analysis plan (frozen before results)

```text
ANALYSIS_VERSION = cand01r3-analysis-plan-v1
EMPIRICAL_DISPOSITION = NOT_YET
REAL_OBSERVATIONS = 0
```

This plan is frozen before any real learner observation. Do not change the primary endpoint after seeing results.

## Primary comparison

Clean held-out first attempts from Days 1–6, split by scheduled policy context:

- SMART_PRACTICE: Days 1, 3, 5 (12 scheduled PROBE items)
- RRC_1: Days 2, 4, 6 (12 scheduled PROBE items)

Do not use training accuracy, retry accuracy, raw lifetime correctness, question familiarity, or Smart Practice internal scores as the primary endpoint.

Day 7 five-item block is predeclared descriptive/time-trend, labeled `DAY7_BALANCED_MEASUREMENT`.

## Required reports

- question-level clean accuracy by policy
- family-level directional summary (7 independent families)
- domain-level descriptive results
- objective-level descriptive results where sample allows
- missingness (`UNOBSERVED` counts)
- contamination count
- TRAIN exposure dose
- policy exposure dose
- RRC-1 service metrics
- order/time trend across days 1–7

## Uncertainty

There are 7 independent semantic families. Do not rely solely on naive question-level p-values treating all 29 items as independent. Report:

- raw question-level difference
- family-level directional comparison
- confidence/uncertainty intervals only where defensible
- number of independent families = 7

Do not manufacture significance. Do not promise statistical certainty this sample cannot support.

## Later adjudication only

Do not issue `RRC1_SUPPORTED`, `RRC1_NOT_SUPPORTED`, or `INCONCLUSIVE_MORE_EVIDENCE_REQUIRED` in this package. Those belong to `SC900-ENGINE-RDAF-CAND01R3-EMPIRICAL-ADJUDICATION-001` after the human learner completes the experiment.
