# 01 — Semantic opportunity matrix

Audit of the starting 400-question bank against 58 leaves, 118 knowledge units, `tested_decision`, `semantic_family_id`, stem style, difficulty, and source authority.

Uniqueness unit: `semantic_family_id` + `tested_decision`, supplemented by scenario meaning, misconception, answer decision, and source proposition.

## Starting bank

- Approved: 400
- Distinct conservative families: 27
- Distinct family+decision pairs with a non-empty decision: 200 (plus 200 predecessor items whose `tested_decision` is empty)
- Exact duplicates: 0
- Probable duplicates: 0
- Difficulty: beginner 313 / intermediate 87
- Single / multi: 399 / 1

## Classification method

Raw count was not used alone. A leaf was:

- **UNDERCOVERED** if count ≤ 5 **and** remaining knowledge-unit propositions were untested, or if only 2 distinct decisions existed for a core concept leaf.
- **HEALTHY** if core definition, distinction, and at least one scenario/misconception were present, with room for one more useful intermediate discrimination item.
- **SATURATED** if additional items would mainly restate an existing decision with a new company name, stem style, or distractor rotation.

## Starting leaf classes

### UNDERCOVERED

`authentication`, `authorization`, `directory_services_active_directory`, `federation`, `identity_primary_security_perimeter`, `identity_providers`, `zero_trust_model`, `defense_in_depth`, `encryption_and_hashing`, `grc_concepts`, `compliance_manager`, `records_management`, `defender_portal`, `defender_threat_intelligence`, `defender_vulnerability_management`, `microsoft_privacy_principles`.

Typical pattern: 4–6 items, 2–3 decisions, mostly beginner definitions, few neighboring-concept distractors.

### HEALTHY

Most remaining leaves at 6–10 items with 3–5 distinct decisions, including shared responsibility, hybrid identity, ID Governance, PIM, ID Protection, DLP, retention, explorers, Sentinel SIEM/SOAR pairs, Defender workload splits, and Azure network controls.

### SATURATED

`authentication_methods` (12/6), `conditional_access` (12/5), `sentinel_threat_detection_mitigation` (11/5), `multifactor_authentication` (10/4), `siem_and_soar` (10/4), `entra_roles_rbac` (10/5).

These received new items only when a genuinely different decision remained (for example PHS vs PTA, named location, FIDO2 vs SMS, Sentinel vs XDR).

## Expansion targeting

Batches 09–12 added 100 questions preferentially as:

- intermediate scenario / distinction / misconception items
- neighboring-concept distractors (Entra vs Purview vs Defender vs Azure network)
- a small number of high-quality multi-selects (4 new; bank total 5)

Out of scope remained Security Copilot, Data Map, Unified Catalog, and Global Secure Access / SSE.

## After 500

No leaf is unrepresented. Minimum leaf count is 5. Domain mix is inside current exam weights. Remaining unused opportunities are listed in `04-SEMANTIC-EXHAUSTION-ASSESSMENT.md` and are not strong enough to continue toward 600 in this package.
