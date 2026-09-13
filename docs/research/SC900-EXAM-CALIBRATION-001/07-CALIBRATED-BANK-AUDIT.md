# Calibrated bank audit

Path: `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json`

| Rebuild | SHA-256 |
| --- | --- |
| Pre-calibration | `8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254` |
| Calibrated build 1 | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Calibrated build 2 | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |

Idempotence: PASS. Default bank SHA-256 unchanged: `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`.

## Gates

| Gate | Result |
| --- | --- |
| ALL_APPROVED_ITEMS_CALIBRATED | YES |
| CURRENT_MICROSOFT_AUTHORITY | PASS |
| ALL_58_CURRENT_LEAVES_COVERED | YES |
| KNOWN_WRONG_ANSWERS | 0 |
| KNOWN_AMBIGUOUS_APPROVED | 0 |
| KNOWN_OUTDATED_APPROVED | 0 |
| SEMANTIC_DUPLICATES | 0 |
| EMPTY_TESTED_DECISION | 0 |
| ACCIDENTAL_OVERDIFFICULTY_MATERIALLY_REDUCED | YES |
| CROSS_PRODUCT_GIVEAWAYS_MATERIALLY_REDUCED | YES |
| FUNDAMENTALS_CORE_MAJORITY | YES (301/454) |
| STRETCH_IS_MINORITY | YES (23/454) |
| EXPLANATION_QUALITY_PRESERVED | YES |
| ANSWER_POSITION_PREDICTABILITY | NO |
| COPYRIGHTED_REFERENCE_TEXT_IMPORTED | NO |
| MICROSOFT_EXAM_STYLE_CALIBRATION | PASS |
| BANK_SUFFICIENT_FOR_SC900_PREPARATION | YES |

## Distributions after calibration

Difficulty labels unchanged for runtime compatibility: beginner 267, intermediate 187.

Stem styles: short_scenario 143, direct_concept 87, concept_distinction 69, capability_selection 67, misconception_correction 37, distinction_comparison 34, multi_select 6, current_topic 4, service_selection 3, responsibility_governance 3, governance_compliance 1.

Single/multi: 449 / 5.

Answer positions: A 111, B 114, C 116, D 113. Longest natural run remains 6. Serial-modulo match rate 0.343. Not algorithmically predictable. Keys were not manually rotated.

Domain counts unchanged: concepts 61, Entra 125, security solutions 164, compliance 104.

Microsoft-current terminology: PASS. No Azure AD / Azure Sentinel / Microsoft 365 Defender / Azure Purview regressions were introduced.

Explanations were not simplified with the stems.
