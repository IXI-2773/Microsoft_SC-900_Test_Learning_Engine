# 07 — Source currentness audit

Live study guide (fetched 2026-09-12): skills as of July 28, 2026; 58 leaves; taxonomy match; no silent rewrite.

## Provenance of approved 454

| Category | Count |
| --- | --- |
| MICROSOFT_PRODUCT_DOC_PRIMARY | 212 |
| EXISTING_REPOSITORY_REVERIFIED | 154 |
| MICROSOFT_LEARN_PRIMARY | 88 |

## Integrity checks

- Current authority URL present on each approved item
- Assessment / practice-exam content was not copied (`assessment_content_used = false` on inventory)
- Out-of-scope training extras were not promoted
- No fabricated sources
- Default launch bank SHA-256 unchanged: `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`
- SKU/licensing mentions appear only as distractors (“Azure Firewall SKU”), not as keyed claims
- Portal click-path volatility was not used as a keyed skill
- One regex false positive (`Azure ad` inside “Azure administrator”) is not an Azure AD terminology regression

`SOURCE_INTEGRITY = PASS`  
`CURRENT_SC900_SCOPE_RECONCILED = YES`  
`KNOWN_OUTDATED_APPROVED = 0`
