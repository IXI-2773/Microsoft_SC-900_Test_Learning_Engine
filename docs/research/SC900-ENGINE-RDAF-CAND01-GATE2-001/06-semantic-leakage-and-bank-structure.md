# Semantic Leakage And Bank Structure

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Current Bank

Repository inspection found:

- runtime bank: `sc900_bank_v8_baseline.json`
- question count: `8`
- domain-code distribution: `{'1': 2, '2': 2, '3': 2, '4': 2}`
- objective-code distribution: `{'1': 2, '2': 2, '3': 2, '4': 2}`
- source: all eight questions come from `SC-900 baseline original placeholder bank`

`tests/test_sc900_contract.py:41` explicitly verifies that the launch bank has eight placeholder questions balanced by broad domain code.

## Official Blueprint Weights

Microsoft's current SC-900 study guide lists the skills measured as:

- security, compliance, and identity concepts: `10-15%`
- Microsoft Entra capabilities: `25-30%`
- Microsoft security solutions: `35-40%`
- Microsoft compliance solutions: `20-25%`

The placeholder bank's 2/2/2/2 domain distribution does not match the official weights and is far too small to support withholding probes while preserving training coverage.

## Bank Sufficiency Conditions

A serious CAND-01R2 bank must have, at minimum:

- reviewed and approved questions only;
- canonical question IDs stable across import/compile;
- no known exam-dump contamination;
- provenance for source family and source quality;
- enough items in all four SC-900 domains to approximate official blueprint weights after PROBE withholding;
- enough objective/subobjective coverage for paired arm allocation;
- enough same-objective and same-family items to identify semantic leakage risk;
- explicit family/template labels or a conservative manual family review;
- distinct TRAIN and PROBE items per objective family;
- enough clean 7-day observations to report uncertainty, not a single percentage.

Historical P1's `>=200` preferred target remains a reasonable serious-bank floor. A smaller pilot may test mechanics only.

## Exact-Item vs Meaningful Transfer

Exact-item held out means the same canonical ID was not shown before probe.

Meaningful-transfer held out requires more:

- TRAIN and PROBE items must not share the same stem template;
- answer-option structure must not make the probe answer obvious;
- source wording must not be near-identical;
- objective family must be broad enough that training does not directly teach the probe answer;
- repeated Microsoft product-name cues must be tracked.

The repository has duplicate and related-question detection in import (`ingestion/importer.py:44`), but that is an import-review heuristic, not an experimental family-partition guarantee.

## Blueprint Balance Attack

If PROBE withholding removes too many items from Microsoft security solutions or Microsoft Entra, a policy arm could receive distorted practice compared with the SC-900 blueprint. Conversely, forcing exact blueprint balance with a sparse bank could leave too few probes per objective family.

Disposition: `MATERIAL_UNRESOLVED_UNTIL_REVIEWED_BANK_EXISTS`

## Gate Consequence

The current placeholder bank produces the terminal blocker:

`GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`