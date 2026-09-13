# Exam / Practice / Smart Practice

Verified against the **active** runtime bank (`sc900_bank_v8_final.json`), not only the nested compiled candidate.

| Metric | Count |
| --- | --- |
| TOTAL ACTIVE | 454 |
| FUNDAMENTALS_CORE | 301 |
| FUNDAMENTALS_APPLIED | 130 |
| STRETCH | 23 |
| Ordinary Exam eligible (`exam_runtime_eligible`) | 431 |
| Ordinary Exam Stretch selectable | NO |
| Practice pool | 454 |
| Practice Stretch available | YES |
| Smart Practice source/candidate eligibility includes Stretch | YES |

New ordinary Exam construction uses PR #26 `filter_new_exam_pool()`. Missing `exam_simulation_eligible` remains eligible; explicit `false` is excluded. Stretch rows are explicitly ineligible.

Practice and Smart Practice continue to use the full 454-question master/candidate population. No new tier weighting, quota, slider, setting, or sampling algorithm was added.
