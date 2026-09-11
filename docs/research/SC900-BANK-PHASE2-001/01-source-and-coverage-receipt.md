# Phase-2 Source and Coverage Receipt

WORK_ID = `SC900-BANK-PHASE2-001`
VERIFIED_AT = `2026-09-11`

## Current Microsoft authority

The Microsoft SC-900 study guide was rechecked on 2026-09-11. It continues to identify the active skills set as **July 28, 2026** and the four weighted domains as:

| Domain | Weight |
| --- | ---: |
| Describe the concepts of security, compliance, and identity | 10–15% |
| Describe the capabilities of Microsoft Entra | 25–30% |
| Describe the capabilities of Microsoft security solutions | 35–40% |
| Describe the capabilities of Microsoft compliance solutions | 20–25% |

The repository's 14-objective taxonomy remains aligned with that study guide. No taxonomy remapping is authorized by Phase 2.

Official source inventory:

`content/sc900/phase2/source_inventory.json`

Primary teaching/factual sources remain the four Microsoft Learn paths for concepts, Microsoft Entra, Microsoft security solutions, and Microsoft Purview/privacy. The study guide is the final exam-scope authority when a Learn path contains additional training material not explicitly present in the current skills-measured list.

## Originality boundary

Phase-2 questions are authored from factual source material only. The following are excluded as question-content sources:

- Microsoft Practice Assessment question text;
- Microsoft Learn module assessments or knowledge checks;
- recalled live-exam questions;
- exam dumps;
- unlicensed commercial question banks.

`assessment_content_used = false` is required for every source-inventory entry.

## Cumulative allocation

Phase 1 accepted 50 questions at `6 / 14 / 19 / 11`. Phase 2 adds the same increment, producing:

| Domain | Phase 1 | Phase-2 increment | Cumulative |
| --- | ---: | ---: | ---: |
| Security/compliance/identity concepts | 6 | 6 | 12 |
| Microsoft Entra | 14 | 14 | 28 |
| Microsoft security solutions | 19 | 19 | 38 |
| Microsoft compliance solutions | 11 | 11 | 22 |
| **Total** | **50** | **50** | **100** |

Cumulative objective target:

```text
security_compliance_concepts                 6
identity_concepts                            6
entra_identity_types_and_function            6
entra_authentication                         8
entra_access_management                      6
entra_identity_protection_governance         8
azure_infrastructure_security               12
azure_security_management                    8
microsoft_sentinel                           6
defender_xdr                                12
service_trust_privacy                        4
purview_compliance_management                4
purview_information_protection_lifecycle     8
purview_insider_risk_ediscovery_audit        6
```

## Coverage rule

The numeric target is necessary but not sufficient. The second 50-question increment must be authored against distinct propositions/scenarios where practical and reviewed against the accepted Phase-1 set for semantic duplication.

A question does not count merely because its objective allocation fills a quota. It must survive factual-source, answer-uniqueness, distractor, explanation, originality, duplicate, semantic-family, probe-suitability, and terminology review.

If 50 new items do not survive review, Phase 2 is `PHASE_2_INCOMPLETE`; the allocation is not relaxed.
