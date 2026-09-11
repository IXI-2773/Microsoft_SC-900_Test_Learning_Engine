# SC900-BANK-PHASE3-001 — Task 6 TRAIN/PROBE Partition Acceptance

```text
TASK_6_TRAIN_PROBE_PARTITION_ACCEPTED
TOTAL_QUESTIONS = 200
SEMANTIC_FAMILIES = 27
QUESTION_ASSIGNMENTS = 200
DUPLICATE_ASSIGNMENTS = 0
MISSING_ASSIGNMENTS = 0
UNKNOWN_ASSIGNMENTS = 0
TRAIN_QUESTIONS = 171
PROBE_QUESTIONS = 29
UNASSIGNED_QUESTIONS = 0
TRAIN_FAMILIES = 20
PROBE_FAMILIES = 7
UNASSIGNED_FAMILIES = 0
EFFECTIVE_INDEPENDENT_PROBE_FAMILIES = 7
TRAIN_PROBE_FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
PROBE_ELIGIBILITY_ERRORS = []
MANIFEST_ERRORS = []
MANIFEST_REPRODUCIBLE = YES
RUNTIME_CONSUMER_COUNT = 0
RUNTIME_CONSUMER_AUTHORIZED = NO
DEFAULT_LAUNCH_BANK_UNCHANGED = YES
PROTECTED_REFS_UNCHANGED = YES
TASK_7_REQUIRED = YES
PHASE_3_STRUCTURALLY_ACCEPTED = NO
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_5_ACCEPTED_HEAD = `54fbfbc03379ade9f172db604085736a379dd386`
TASK_6_IMPLEMENTATION_HEAD = `f9f3f24b292aca44872f950f9c5b8a0447692b9a`
TASK_6_CONTENT_HEAD = `d9b72ff76a65f4308b04006a5bc54994c85c6c40`

The remote Phase-3 branch was fetched before work. HEAD matched the accepted Task-5 commit; no newer valid concurrent work required rebase or reset.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

The 200-question candidate bank and the 27-family semantic audit were trusted as frozen authority. An arbitrary TRAIN/PROBE percentage was not trusted. The partition was justified from family size, independence, domain/objective representation, probe eligibility, contamination risk, and a later 7-day first-attempt measurement protocol. Whole-family isolation and all 20 Task-4 transfer edges were verified before acceptance.

## Scope accepted

Task 6 is a design-time partition package. It does **not** implement runtime TRAIN/PROBE enforcement, modify Smart Practice, alter RRC-1 runtime, change learner state/history/scheduling, replace the launch/default bank, reopen Gate 2, authorize runtime implementation, declare Phase 3 structurally accepted, or merge.

## Design method

The 27 families were analyzed before roles were chosen. Measurement question first:

How many independent probe families are needed for a later 7-day first-attempt protocol while leaving enough TRAIN coverage?

Answer: **7 independent families**, not 29 independent questions. About four first-attempt items per day is defensible. Family identity is the semantic unit. Question count is sample size inside those units.

No 80/20, 70/30, or 90/10 quota was used as a premise. The resulting 171/29/0 split is a consequence of selecting 7 small-to-medium fully eligible families.

## Selected PROBE families

| Family | Members | Why PROBE |
| --- | --- | --- |
| `shared_responsibility_model` | 4 | Independent foundational-concept measurement |
| `zero_trust_and_identity_perimeter` | 4 | Independent two-leaf Zero Trust / identity-perimeter measurement |
| `multifactor_authentication` | 6 | Independent operational authentication measurement; `authentication_methods` stays TRAIN |
| `privileged_identity_management` | 4 | Independent PIM measurement without holding out the larger governance merge |
| `entra_roles_rbac` | 5 | Independent RBAC measurement without holding out Conditional Access |
| `azure_key_vault` | 3 | Independent secrets/key measurement without holding out NSG/Firewall/WAF/DDoS |
| `purview_portal` | 3 | Only small fully eligible compliance family |

Largest selected PROBE family: `multifactor_authentication` (6).
Smallest selected PROBE family: `azure_key_vault` (3).
Effective independent PROBE families: **7**.

Do not treat 29 probe questions as 29 independent semantic units.

## TRAIN / UNASSIGNED

TRAIN = the other 20 families (171 questions).

UNASSIGNED = 0 families / 0 questions. Every family is resolved, approved, and role-certain. UNASSIGNED remains a valid fail-closed role and was not needed.

`service_trust_privacy_compliance_manager` (13) contains the bank's only 2 `train_only` members. It is TRAIN as a whole family so those members are not forced into PROBE.

## Large-family consequences

Each large family was treated as one indivisible semantic unit:

| Family | Members | Assigned | Consequence |
| --- | --- | --- | --- |
| `defender_xdr_workload_suite` | 24 | TRAIN | Probing it would yield one independent unit, dominate probe N, and remove all Defender XDR training |
| `defender_for_cloud_cspm_cwp` | 16 | TRAIN | This family is the entire `azure_security_management` objective |
| `purview_information_protection_lifecycle` | 16 | TRAIN | This family is the entire information-protection objective |
| `azure_nsg_firewall_waf_ddos` | 15 | TRAIN | Probing it would remove most Azure network-control training without adding 15 independent units |

## Transfer-edge isolation proof

Task 4 recorded 20 explicit transfer edges. Adversarial check: do any edges connect distinct canonical families?

Result: **NO**. Every edge is intra-family (`cross_family_edges = 0`).

A whole-family partition is therefore sufficient. Connected transfer components were not required as a coarser block. Validator still fails closed on any TRAIN↔PROBE edge crossing.

```text
EXPLICIT_TRANSFER_EDGES = 20
CROSS_FAMILY_TRANSFER_EDGES = 0
TRAIN_PROBE_TRANSFER_EDGE_CROSSINGS = 0
TRAIN_PROBE_FAMILY_SPLITS = 0
```

## Domain / objective coverage

PROBE question counts by domain:

- `security_compliance_identity` = 8
- `microsoft_entra` = 15
- `microsoft_security_solutions` = 3
- `microsoft_compliance_solutions` = 3

TRAIN question counts by domain:

- `security_compliance_identity` = 16
- `microsoft_entra` = 41
- `microsoft_security_solutions` = 73
- `microsoft_compliance_solutions` = 41

Domains absent from PROBE: **none**.

Objectives absent from PROBE because the remaining coverage lives in large or otherwise TRAIN-retained families:

- `azure_security_management`
- `defender_xdr`
- `entra_identity_types_and_function`
- `microsoft_sentinel`
- `purview_information_protection_lifecycle`
- `purview_insider_risk_ediscovery_audit`
- `service_trust_privacy`

That absence is reported, not manufactured away.

PROBE leaf coverage = 8 leaves. TRAIN leaf coverage retains the rest of the 58-leaf blueprint.

## Artifact SHA-256 (LF-normalized)

| Artifact | SHA-256 |
| --- | --- |
| `content/sc900/phase3/train_probe_manifest.json` | `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90` |
| `content/sc900/phase3/semantic_family_audit.json` | `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701` |
| `content/sc900/phase3/store/questions.json` | `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c` |
| `content/sc900/phase3/compiled/sc900_phase3_reviewed_bank.json` | `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b` |
| `sc900_bank_v8_baseline.json` | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

Manifest header freezes `design_time_only = true`, `runtime_consumer_authorized = false`, `implementation_authorized = false`, `phase_3_structurally_accepted = false`, and `cand01_gate2_status = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`.

## Schema / Python parity

Phase-3 schema `content/sc900/phase3/train_probe_manifest.schema.json` is a versioned extension:

- `schema_version` = `sc900.phase3.train-probe-manifest/v1`
- `inherited_item_schema` = `sc900.train-probe-manifest/v1`

Item role, eligibility, receipt, and family-split semantics are projected into the Phase-2 Python validator. Phase-3 adds family assignments, allocation-report completeness, hash binding, transfer-edge isolation, and extra-field rejection. Schema property sets match the Python field constants.

Result: **SCHEMA_PYTHON_PARITY = PASS**

## Rebuild / verify

```text
python -m tools.build_sc900_phase3 --write-train-probe-manifest
python -m tools.build_sc900_phase3 --verify-train-probe-manifest
```

Verify result: `REPRODUCIBLE`

Task-5 `--verify-committed` remains `REPRODUCIBLE`.
Task-4 `--verify-semantic-audit` remains `REPRODUCIBLE`.

## Tests

Fail-closed Task-6 tests were RED first (missing validator/builder/manifest), then GREEN.

Focused suite:

`python -m unittest tests.test_sc900_phase3_train_probe tests.test_sc900_phase3 tests.test_sc900_phase3_builder tests.test_sc900_phase3_authoring_allocation tests.test_sc900_phase2 tests.test_sc900_phase2_deep_review tests.test_sc900_phase2_receipt_portability tests.test_sc900_taxonomy tests.test_sc900_bank_quality tests.test_ingestion_importer`

Result: **122 passed** (27 Task-6 partition tests + 95 prior focused tests).

## Quality gates

| Gate | Result |
| --- | --- |
| focused unittest | 122 passed |
| `python -m tools.build_sc900_phase3 --verify-train-probe-manifest` | `REPRODUCIBLE` |
| `python -m tools.build_sc900_phase3 --verify-committed` | `REPRODUCIBLE` |
| `python -m tools.build_sc900_phase3 --verify-semantic-audit` | `REPRODUCIBLE` |
| `python -m tools.lint_bank` | passed (8 clean baseline questions) |
| `python -m tools.verify_installation` | passed |
| `python -m mypy` | Success: no issues found in 22 source files |
| `black --check` on Task-6 Python | passed |
| ruff I/E/F on Task-6 tests and Phase-3 validator | passed |
| default launch bank | unchanged; SHA-256 `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |
| runtime application files | unchanged |

## Runtime-consumer search

Repository search for `content/sc900/phase3/train_probe_manifest.json` found only:

- design-time builder/validator
- Task-6 tests
- the Phase-3 implementation plan path listing

No runtime selector, scheduler, repair path, renderer, history mechanism, Smart Practice component, analytics code, importer, exporter, or restore code consumes the manifest.

`RUNTIME_CONSUMER_COUNT = 0`

## All-path leakage handoff for Task 7

The manifest records the partition contract that later guards must protect, without implementing those guards. Paths listed:

normal practice; Smart Practice; due/weak paths; twin/repeat paths; delayed recall; memory/confusion repair; wrong-answer repair; streak repair; boss/checkpoint flows; measurement/probe rendering; history; analytics; export/import; compiler/rebuild; restore; debug; fixtures/tests; any newly discovered question path.

Invariants to carry forward: one family one role; no TRAIN/PROBE family split; no TRAIN/PROBE transfer-edge crossing; PROBE requires approved+resolved+eligible; TRAIN requires approved+resolved.

## Protected refs

Fetched and verified unchanged:

```text
origin/recovery/publish-exact-history/sc900-v8-20260910 = b567d4b74a2f99e50022dd0dafd81ffa75dff0a2
origin/recovery/publish-sc900-v8-exact-history = bbc3bd900b73bde89151dc51706ad62fc69e8196
sc900-v8.0.0-baseline tag object = 9c80be5b20e652dc2eb86621dfdf7c32baa06528
```

## Explicitly not claimed

```text
PHASE_3_STRUCTURALLY_ACCEPTED = NO
Gate 2 = NOT REOPENED
runtime implementation = NOT AUTHORIZED
TRAIN/PROBE runtime guards = NOT IMPLEMENTED
merge = NOT PERFORMED
```

Stop at the Task-7 boundary: Gate-2 design-assurance carry-forward. Do not begin that work in Task 6.
