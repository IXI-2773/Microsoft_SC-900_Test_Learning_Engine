# 05 — 500-question checkpoint

Generation froze at 500 approved unique questions.

## Disposition

`500_SUFFICIENT = YES`

`500_STILL_HAS_MEANINGFUL_GAPS = NO` for this authoring package. Residual opportunities exist (see `04`) but are not substantial uncovered SC-900 decisions.

Generation did **not** continue into batches 13–16.

## Checkpoint metrics

| Metric | Value |
| --- | --- |
| Approved | 500 |
| Leaves covered | 58 / 58 |
| Uncovered leaves | 0 |
| Distinct semantic families | 27 |
| Distinct family+decision pairs | 300 |
| Empty `tested_decision` (predecessor) | 200 |
| Questions per non-empty tested decision | 1 |
| Exact duplicates | 0 |
| Probable duplicates | 0 |
| Semantic decision duplicates | 0 |
| Beginner / intermediate | 313 / 187 |
| Single / multi | 495 / 5 |
| Stem styles | short_scenario 161, direct_concept 106, capability_selection 69, concept_distinction 69, misconception_correction 44, others 51 |
| Sources | EXISTING_REPOSITORY_REVERIFIED 200, MICROSOFT_PRODUCT_DOC_PRIMARY 212, MICROSOFT_LEARN_PRIMARY 88 |
| Answer positions | A 128, B 124, C 124, D 124 |

## Domain allocation

| Domain | Count | Exam weight |
| --- | --- | --- |
| security_compliance_identity | 68 | 10–15% |
| microsoft_entra | 136 | 25–30% |
| microsoft_security_solutions | 182 | 35–40% |
| microsoft_compliance_solutions | 114 | 20–25% |

## Objective allocation

See `analytics.json`. All 14 objectives remain represented.

## Leaf allocation

Minimum 5 (`authorization`, `directory_services_active_directory`, `identity_primary_security_perimeter`). Maximum 15 (`conditional_access`). Full table is in `content/sc900/microsoft-learn-corpus/analytics.json`.
