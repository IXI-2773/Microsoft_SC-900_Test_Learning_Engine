# SC900-BANK-PHASE3-001 — Task 4 Semantic-Family Audit Acceptance

```text
TASK_4_SEMANTIC_FAMILY_AUDIT_ACCEPTED
AUDITED_QUESTIONS = 200
UNIQUE_QUESTION_IDS = 200
SEMANTIC_FAMILIES = 27
MERGE_OVERRIDES = 158
SPLIT_OVERRIDES = 0
UNRESOLVED_FAMILIES = 0
EXPLICIT_TRANSFER_EDGES = 20
SEMANTIC_AUDIT_ERRORS = []
TASK_5_REQUIRED = YES
PHASE_3_STRUCTURALLY_ACCEPTED = NO
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_3_ACCEPTED_HEAD = `2ad2227cdaa8e9fec323194da2ad215e0c3c6705`
TASK_4_IMPLEMENTATION_HEAD = `0635387897a1c5e07b82c6b79dcabc4851acb6dc`
AUDIT_ARTIFACT = `content/sc900/phase3/semantic_family_audit.json`
AUDIT_SHA256 = `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701`
AUDIT_VERSION = `sc900-semantic-family-audit/v2`
AUDIT_EPOCH = `phase3-task4-cumulative-200`
REVIEWED_AT = `2026-09-11T18:00:00Z` (frozen; rebuilds do not inject wall-clock time)

The audit SHA-256 is of the committed artifact bytes (LF-normalized). Dict-level rebuild verification is `REPRODUCIBLE`.

The remote Phase-3 branch was fetched before work. HEAD matched the accepted Task-3 commit; no newer valid concurrent work required rebase or reset.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

Prior Phase-1/2 family labels and Task-3 authored family IDs were treated as hypotheses. All 200 approved items were re-audited together. Same-leaf independence was not assumed. Phase-3 unique family names were not treated as proof of independence. Family count was not optimized.

## Scope accepted

Task 4 is a cumulative semantic-family / leakage-assurance package over Phase 1 + Phase 2 + Phase 3. It does **not** author new questions, apply a TRAIN/PROBE partition, open Gate 2, or declare Phase 3 structurally accepted.

No Task-3 question required repair. Remaining leakage was resolved by conservative family merges rather than rewriting items.

## Published Task-4 artifacts

- `content/sc900/phase3/semantic_family_audit.json`
- `tools/build_sc900_phase3.py`
- `tests/test_sc900_phase3.py` (fail-closed Task-4 tests added before the audit machinery)

Rebuild:

`python -m tools.build_sc900_phase3 --write-semantic-audit`

Verify:

`python -m tools.build_sc900_phase3 --verify-semantic-audit`

Result: `REPRODUCIBLE`.

## Audit method

Inputs:

- Phase 1 batches `sc900_p1_q001`–`q050`
- Phase 2 batches `sc900_p2_q001`–`q050`
- Phase 3 batches `sc900_p3_q001`–`q100`
- Phase 2 semantic-family audit as prior family evidence, not authority
- Task-3 authored `semantic_family_id` values as hypotheses
- inherited transfer edge `sc900_p1_q037` ↔ `sc900_p2_q033`

Automated candidate detection used same-leaf grouping, shared normalized answers, source-objective proximity, and prior family IDs. Automated similarity was evidence for review, not the decision.

Adversarial review then asked, for suspicious pairs/clusters: whether exposure to one item would materially simplify another beyond ordinary blueprint-objective learning. Uncertain cases failed closed into the same family.

Rules frozen in the artifact:

- same blueprint leaf → merge unless an explicit independence adjudication exists
- same normalized correct-answer cue → merge unless an explicit independence adjudication exists
- known transfer edges must be merged, independently adjudicated, or explicitly unresolved
- unresolved/disputed family state cannot remain independently PROBE-eligible

No independence adjudications were issued. No splits were issued. No family remained unresolved.

## Relationship classes

| Class | Result |
| --- | --- |
| A. Exact duplicates | None found among the 200 stems. |
| B. Near duplicates | Same-leaf scenario rewrites and product-identification variants were merged. Phase-3 unique family names did not establish independence. |
| C. Same-leaf transfer | All 58 leaves were reviewed. Same-leaf members remain one family; independence was not defensible. |
| D. Shared answer / rationale | Cross-leaf shared answer `Microsoft Sentinel` joined SIEM/SOAR and Sentinel mitigation. Other shared answers were same-leaf. |
| E. Scenario-equivalent variants | Actor/resource substitutions on the same decision rule were merged. |
| F. Source-sibling coupling | Same official module did not auto-merge, but Purview information-protection workflow items and Defender XDR suite-composition items did transfer. |
| G. Cross-leaf transfer | Thirteen canonical families span multiple leaves. See below. |
| H. Phase-crossing transfer | Every multi-member family except a few two-item leaves contains more than one phase. Task-3 screening was reverified and was not treated as final. |

## Cross-leaf families

These merges are auditable in `families[]`, `transfer_edges[]`, and per-question `decision_type=merged` rows:

- `sentinel_siem_soar_automation` (12 items, 2 leaves) — inherited SOAR playbook edge plus Sentinel SIEM/SOAR identification
- `defender_for_cloud_cspm_cwp` (16 items, 4 leaves) — Defender for Cloud is taught as CSPM plus CWP plus recommendations/secure score
- `azure_nsg_firewall_waf_ddos` (15 items, 4 leaves) — explicit layer-discrimination items
- `purview_audit_ediscovery_insider_risk` (12 items, 3 leaves) — product-discrimination items
- `service_trust_privacy_compliance_manager` (13 items, 4 leaves) — STP paired with privacy principles and contrasted with Compliance Manager
- `entra_hybrid_identity_and_ad` (10 items, 3 leaves) — Entra ID versus AD DS and hybrid sync
- `conditional_access_and_identity_protection` (11 items, 2 leaves) — risk-signal-to-access-decision mapping
- `entra_id_governance_and_access_reviews` (8 items, 2 leaves) — lifecycle/entitlement contrasted with recertification
- `defender_xdr_workload_suite` (24 items, 8 leaves) — XDR suite composition names workload Defender services; portal/VM/TI are operations/posture faces of that mapping
- `purview_information_protection_lifecycle` (16 items, 6 leaves) — classification → labels → DLP / explorer / retention / records workflow
- `authentication_vs_authorization` (4 items, 2 leaves)
- `zero_trust_and_identity_perimeter` (4 items, 2 leaves)
- `federation_and_identity_providers` (4 items, 2 leaves)

Same-leaf families retained a proposition-oriented leaf ID when no cross-leaf merge applied (`shared_responsibility_model`, `azure_bastion`, `purview_portal`, `defense_in_depth`, MFA, authentication methods, PIM, and others).

## Probe-suitability consequence

All 200 decisions have `family_state=resolved`. Item `future_probe_suitability` remains `eligible` where the source item was eligible. Family consolidation increases co-family leakage; it does not create a TRAIN/PROBE partition. Task 6 must consume these families and must not split a family across TRAIN and PROBE.

UNASSIGNED is not used here because no family remained unresolved.

## Adversarial review of the resulting structure

Sampled especially:

- largest family `defender_xdr_workload_suite` (24)
- other high-risk cross-leaf families listed above
- every multi-phase family
- Phase-3 items that had unique Task-3 family IDs (merged unless independence was proven)
- there are no newly split families and no unresolved families

Question used throughout: “What evidence would prove this family decision wrong?” For the XDR suite, that evidence would be a workload-Defender item whose answer is not named or implied by XDR composition/portal/investigation items. The current stems do name those services. For Azure network controls, that evidence would be a discrimination item that does not restate the sibling control’s layer; the current contrast items do. For Purview information protection, classification-before-DLP and retention-versus-sensitivity items leak the sibling propositions.

If a later reviewer finds a genuinely independent operational proposition, a split requires an auditable independence adjudication. None is justified now.

## TDD and focused verification

Fail-closed RED tests were added first and failed because `tools.build_sc900_phase3` did not exist. After the validator and audit were implemented, the same tests passed without weakening negatives.

Command:

`python -m unittest tests.test_sc900_phase3 tests.test_sc900_phase3_authoring_allocation tests.test_sc900_phase2 tests.test_sc900_phase2_deep_review tests.test_sc900_phase2_receipt_portability tests.test_sc900_bank_quality tests.test_sc900_taxonomy tests.test_ingestion_importer -v`

Result: **76/76 passed**.

Additional Task-4 checks:

- audited/unique IDs = 200/200
- missing/duplicate/unknown audit IDs = 0
- semantic audit validation errors = []
- rebuild is byte-reproducible against the committed artifact

## Protected-ref verification

Unchanged after re-fetch:

- `recovery/publish-exact-history/sc900-v8-20260910` = `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`
- `recovery/publish-sc900-v8-exact-history` = `bbc3bd900b73bde89151dc51706ad62fc69e8196`
- tag object `sc900-v8.0.0-baseline` = `9c80be5b20e652dc2eb86621dfdf7c32baa06528`

`main` was not modified. No runtime selection, Smart Practice, RRC-1, learner/history, TRAIN/PROBE runtime, launch, or default-bank files are in this Task-4 scope. Temporary inventory helpers were removed before acceptance.

## Authority boundary

```text
PHASE_3_STRUCTURALLY_ACCEPTED = NO
TASK_5_REQUIRED = YES
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
```

STOP. Next required package is Task 5 — deterministic Phase-3 builder and evidence receipt. Do not begin Task 6 partition work. Do not reopen Gate 2. Do not merge.
