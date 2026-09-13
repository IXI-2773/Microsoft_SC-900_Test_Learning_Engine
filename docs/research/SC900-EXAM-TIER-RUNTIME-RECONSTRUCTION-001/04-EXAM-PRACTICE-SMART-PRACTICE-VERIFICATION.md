# Exam / Practice / Smart Practice verification

## A. Calibrated bank metadata

Frozen compiled bank SHA-256: `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`

| Check | Result |
| --- | --- |
| 454 total | PASS |
| 301 Core | PASS |
| 130 Applied | PASS |
| 23 Stretch | PASS |
| 431 `exam_simulation_eligible=true` | PASS |
| 23 `exam_simulation_eligible=false` | PASS |
| 0 approved items missing required calibration metadata | PASS |

## B. New ordinary Exam

Synthetic fixture places Stretch first, then Core, Applied, explicit ineligible, and a legacy item missing the field.

| Check | Result |
| --- | --- |
| Eligible pool for the fixture | Core + Applied + legacy |
| Core selectable | YES |
| Applied selectable | YES |
| Stretch selectable | NO |
| Explicit false-eligible selectable | NO |
| Ordered mode | PASS |
| Randomized mode with `random.seed(7)` | PASS |
| Domain filter (`Identity`) | PASS, Core only, no Stretch backfill |
| Topic filter (`Entra`) | PASS, Core only, no Stretch backfill |
| History/source `Unseen` | PASS, Stretch excluded |
| Count clamp (`10` requested, 3 eligible) | PASS |
| Count slice (`2` ordered) | PASS |

Calibrated 454-question contract: ordinary Exam eligible pool = 431.

## C. Practice

| Check | Result |
| --- | --- |
| Pool availability | 5/5 synthetic items, 454 calibrated |
| Stretch available | YES |

## D. Smart Practice

| Check | Result |
| --- | --- |
| Stretch remains in eligible candidate population | YES |

No random Stretch selection requirement was imposed. Adaptive ranking, question-value scoring, learner history, concept graph, measurement, governance, calibration, and reward behavior were not changed.
