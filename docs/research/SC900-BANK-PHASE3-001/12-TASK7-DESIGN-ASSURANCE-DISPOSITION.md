# SC900-BANK-PHASE3-001 — Task 7 Design-Assurance Disposition

```text
TASK_7_DESIGN_ASSURANCE_ACCEPTED
ALL_PATH_LEAKAGE_INVENTORY = RECONCILED
TRAIN_PROBE_EXCLUSION_CONTRACT = IMPLEMENTATION_READY
FAIL_CLOSED_SEMANTICS = FROZEN
FUTURE_VERIFICATION_MATRIX = COMPLETE
RRC1_FAIRNESS_METRICS = SPECIFIED
RRC1_STARVATION_METRICS = SPECIFIED
RRC1_EMPIRICAL_THRESHOLDS = NOT_INVENTED
PRIOR_DECAY_TEST_OBLIGATIONS = FROZEN
ALLOCATION_CONFOUND_CONTROLS = FROZEN
NOETIC_REASSESSMENT = COMPLETE
RUNTIME_GUARDS_IMPLEMENTED = NO
RUNTIME_RRC1_IMPLEMENTED = NO
TASK_8_REQUIRED = YES
PHASE_3_STRUCTURALLY_ACCEPTED = NO
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
GATE2_REOPENED = NO
MERGE_PERFORMED = NO
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
VERIFIED_TASK_6_HEAD = `f2c9a04d109de1d5d91e3fd32d9e39568f3828c1`
CANDIDATE = `CAND-01R2 - Historical Learner Prior + Held-Out Policy Verification`
CHAMPION = `Current Smart Practice, unchanged`
CHALLENGER = `RRC-1 - REPAIR / REVIEW / COVERAGE`
PRIMARY_ENDPOINT = `7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items`

This receipt is the Task-7 terminal design-assurance disposition. It does not reopen Gate 2, authorize implementation, implement runtime guards or RRC-1, consume the TRAIN/PROBE manifest from runtime, declare Phase 3 structurally accepted, or merge.

Gate 2 evaluates whether the all-path guard design, fail-closed semantics, and future verification matrix are implementation-ready. Runtime enforcement belongs to Gate 3 or later. Task 7 freezes design-assurance requirements for later empirical evaluation. It does not prove learning effectiveness.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

Accepted Tasks 1–6 were trusted as cumulative evidence and then re-verified by current-source inspection and reproducibility commands. A complete leakage inventory on paper is not runtime isolation. 29 PROBE questions are not 29 independent measurements. Bank growth does not resolve N02 or N06.

## Package map

| Receipt | Content |
| --- | --- |
| `07-TASK7-LEAKAGE-RECONCILIATION.md` | All-path inventory, exclusion contract, fail-closed rule, cache/custody rules, future tests |
| `08-TASK7-RRC1-FAIRNESS-STARVATION.md` | RRC-1 classes, measurable metrics, no invented thresholds, starvation attacks |
| `09-TASK7-PRIOR-DECAY-OBLIGATIONS.md` | Countable unit, SEED/ADVISORY/RETIRED, missingness, contamination, PD tests |
| `10-TASK7-ALLOCATION-CONFOUNDS.md` | TRAIN/PROBE ≠ arm allocation; time, order, selection confounds |
| `11-TASK7-NOETIC-REASSESSMENT.md` | N02 / N06 / N07 / N08 |
| `12-TASK7-DESIGN-ASSURANCE-DISPOSITION.md` | This matrix and acceptance |

Original Gate-2 files `04`–`14` are referenced, not overwritten.

## Frozen Phase-3 facts

```text
APPROVED_QUESTIONS = 200
COMPILED_QUESTIONS = 200
DISTINCT_BLUEPRINT_LEAVES = 58
SEMANTIC_FAMILIES = 27
UNRESOLVED_SEMANTIC_FAMILIES = 0
TRAIN_QUESTIONS = 171
PROBE_QUESTIONS = 29
UNASSIGNED = 0
TRAIN_FAMILIES = 20
PROBE_FAMILIES = 7
EFFECTIVE_INDEPENDENT_PROBE_UNITS = 7
FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
RUNTIME_CONSUMER_COUNT = 0
RUNTIME_CONSUMER_AUTHORIZED = NO
```

Artifact SHA-256 (LF-normalized), carried forward from Task 6:

| Artifact | SHA-256 |
| --- | --- |
| Task-4 semantic audit | `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701` |
| Task-5 store | `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c` |
| Task-5 compiled candidate bank | `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b` |
| Task-6 TRAIN/PROBE manifest | `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90` |
| Default launch bank | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

## Design-assurance evidence matrix

Each row keeps design, runtime, and empirical states separate. There is no single PASS field.

### BANK SIZE / REVIEW QUALITY

- ORIGINAL_GATE2_STATE: 8 placeholder launch-bank questions; `GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE`
- PHASE3_NEW_EVIDENCE: 200 approved reviewed questions; 58 leaves; provenance and review receipts from Tasks 1–5
- CURRENT_DESIGN_STATE: serious-bank floor `>=200` now met at candidate-bank level
- RUNTIME_STATE: default launch bank still 8 placeholders; candidate bank not launched
- EMPIRICAL_STATE: no learning-effect data
- OPEN_OBLIGATION: Task 8 verifies immutability; a later package would be required to change launch authority
- TASK7_DISPOSITION: `DESIGN_ADVANCED_LAUNCH_UNCHANGED`

### SEMANTIC-FAMILY CONTROL

- ORIGINAL_GATE2_STATE: exact-item vs meaningful-transfer unresolved; no family ontology
- PHASE3_NEW_EVIDENCE: 27 families; 158 merges; 20 transfer edges; 0 unresolved; 0 splits
- CURRENT_DESIGN_STATE: ontology specified
- RUNTIME_STATE: runtime does not consume family roles
- EMPIRICAL_STATE: transfer validity not proven
- OPEN_OBLIGATION: runtime family-role enforcement; empirical transfer check in later measurement
- TASK7_DISPOSITION: `DESIGN_ADVANCED_EMPIRICAL_UNPROVEN`

### TRAIN/PROBE PARTITION

- ORIGINAL_GATE2_STATE: no real partition against a reviewed bank
- PHASE3_NEW_EVIDENCE: 171/29/0; 20/7/0 families; 0 crossings; design-time manifest
- CURRENT_DESIGN_STATE: measurement holdout frozen
- RUNTIME_STATE: `RUNTIME_CONSUMER_COUNT = 0`
- EMPIRICAL_STATE: 0 clean probe outcomes
- OPEN_OBLIGATION: Task 8 verification; later authorized consumption
- TASK7_DISPOSITION: `DESIGN_TIME_PARTITION_FROZEN`

### ALL-PATH LEAKAGE INVENTORY

- ORIGINAL_GATE2_STATE: partial inventory; contract not frozen
- PHASE3_NEW_EVIDENCE: current-source re-audit; original paths re-verified; new paths documented (session restore, follow-up index, screenshot review, detached worker, misnamed delayed-probe analytics, redo, bank load, extraction, etc.)
- CURRENT_DESIGN_STATE: 48-path inventory reconciled
- RUNTIME_STATE: no path is partition-aware
- EMPIRICAL_STATE: no live leakage experiment
- OPEN_OBLIGATION: Gate 3/later must implement and prove every path
- TASK7_DISPOSITION: `RECONCILED_CONTRACT_FROZEN`

### FAIL-CLOSED GUARD CONTRACT

- ORIGINAL_GATE2_STATE: conceptually fail-closed; not implementation-ready across paths
- PHASE3_NEW_EVIDENCE: Task-7 contract: missing/unknown/malformed/hash-mismatch/absent/unresolved/unapproved never default to TRAIN
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: n/a
- OPEN_OBLIGATION: implement shared eligibility boundary
- TASK7_DISPOSITION: `FROZEN_UNIMPLEMENTED`

### FUTURE VERIFICATION MATRIX

- ORIGINAL_GATE2_STATE: required but not written per path
- PHASE3_NEW_EVIDENCE: positive/negative/fail-closed/family/transfer/restore/cache/render/history/analytics tests specified for every inventory path
- CURRENT_DESIGN_STATE: complete as design obligations
- RUNTIME_STATE: tests not implemented where they need guards
- EMPIRICAL_STATE: n/a
- OPEN_OBLIGATION: later authorized test implementation
- TASK7_DISPOSITION: `COMPLETE_AS_OBLIGATION`

### RRC-1 CLASS EXCLUSIVITY

- ORIGINAL_GATE2_STATE: supported in principle; overlapping current weak-retest union remains in code
- PHASE3_NEW_EVIDENCE: snapshot rule REPAIR then REVIEW then COVERAGE; PROBE = EXCLUDED
- CURRENT_DESIGN_STATE: specified
- RUNTIME_STATE: RRC-1 not implemented; current `build_weak_retest_pool` still unions flagged/due/weak
- EMPIRICAL_STATE: n/a
- OPEN_OBLIGATION: do not copy the current union if RRC-1 is later implemented
- TASK7_DISPOSITION: `SPECIFIED_UNIMPLEMENTED`

### RRC-1 FAIRNESS METRICS

- ORIGINAL_GATE2_STATE: material unresolved; no numerators
- PHASE3_NEW_EVIDENCE: MAX_SERVICE_DELAY, OVERDUE_RATE, QUEUE_AGE, DOMAIN/OBJECTIVE_SERVICE_BALANCE, CLASS_SERVICE_SHARE, SESSION_CLASS_DOMINANCE defined
- CURRENT_DESIGN_STATE: measurable
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: thresholds unresolved
- OPEN_OBLIGATION: implement reporting; do not invent cuts
- TASK7_DISPOSITION: `SPECIFIED_THRESHOLDS_NOT_INVENTED`

### RRC-1 STARVATION METRICS

- ORIGINAL_GATE2_STATE: material unresolved
- PHASE3_NEW_EVIDENCE: STARVATION_RATE, COVERAGE_DEBT, BACKLOG_SIZE, attack matrix
- CURRENT_DESIGN_STATE: measurable
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: thresholds unresolved
- OPEN_OBLIGATION: implement reporting and attack tests
- TASK7_DISPOSITION: `SPECIFIED_THRESHOLDS_NOT_INVENTED`

### PRIOR DECAY

- ORIGINAL_GATE2_STATE: conceptually acceptable; enforcement unproven
- PHASE3_NEW_EVIDENCE: countable unit frozen against Task-6 PROBE; PD01–PD20 tests specified
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: 0 clean outcomes; still SEED if the rule were running
- OPEN_OBLIGATION: later implementation of monotonic stage logic
- TASK7_DISPOSITION: `OBLIGATIONS_FROZEN`

### MISSINGNESS

- ORIGINAL_GATE2_STATE: UNOBSERVED required; not operationalized
- PHASE3_NEW_EVIDENCE: missed delayed probe is UNOBSERVED, not wrong/correct; excluded from counts
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: no probe window has been run
- OPEN_OBLIGATION: later measurement protocol
- TASK7_DISPOSITION: `FROZEN`

### CONTAMINATION

- ORIGINAL_GATE2_STATE: listed; monotonicity not fully specified
- PHASE3_NEW_EVIDENCE: contamination monotonic; excludes primary and RETIRED; family-level reporting required; forgetting does not clean
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: none
- OPEN_OBLIGATION: later custody implementation
- TASK7_DISPOSITION: `FROZEN`

### SELECTION CONFOUNDS

- ORIGINAL_GATE2_STATE: unresolved until reviewed bank exists
- PHASE3_NEW_EVIDENCE: bank exists; matched TRAIN universe required; imbalance must be reported
- CURRENT_DESIGN_STATE: obligation frozen
- RUNTIME_STATE: no arm assignment
- EMPIRICAL_STATE: none
- OPEN_OBLIGATION: future comparison protocol
- TASK7_DISPOSITION: `FROZEN_UNIMPLEMENTED`

### TIME TREND

- ORIGINAL_GATE2_STATE: one-learner vulnerability stated
- PHASE3_NEW_EVIDENCE: predeclared windows, dose, order accounting required; alternation insufficient
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: none
- OPEN_OBLIGATION: later analysis protocol
- TASK7_DISPOSITION: `FROZEN`

### POLICY ORDER

- ORIGINAL_GATE2_STATE: order effects unresolved
- PHASE3_NEW_EVIDENCE: explicit policy-order accounting required; single order is a confound
- CURRENT_DESIGN_STATE: frozen
- RUNTIME_STATE: unimplemented
- EMPIRICAL_STATE: none
- OPEN_OBLIGATION: later experiment design
- TASK7_DISPOSITION: `FROZEN`

### ARM ALLOCATION

- ORIGINAL_GATE2_STATE: Smart Practice vs RRC-1 not allocable without a bank
- PHASE3_NEW_EVIDENCE: Axis A (TRAIN/PROBE) ≠ Axis B (champion/challenger); both arms TRAIN-only
- CURRENT_DESIGN_STATE: distinction frozen
- RUNTIME_STATE: no assignment
- EMPIRICAL_STATE: none
- OPEN_OBLIGATION: do not implement assignment in Phase 3
- TASK7_DISPOSITION: `DISTINCTION_FROZEN_ASSIGNMENT_NOT_MADE`

### NOETIC N02

- ORIGINAL_GATE2_STATE: `UNRESOLVED`
- PHASE3_NEW_EVIDENCE: still 0 clean SC-900 held-out outcomes
- CURRENT_DESIGN_STATE: instrument ready, origin problem unsolved
- RUNTIME_STATE: n/a
- EMPIRICAL_STATE: unresolved
- OPEN_OBLIGATION: collect independent SC-900 outcomes under the countable-unit rule
- TASK7_DISPOSITION: `UNRESOLVED`

### NOETIC N06

- ORIGINAL_GATE2_STATE: `UNRESOLVED`
- PHASE3_NEW_EVIDENCE: design anomalies mapped; no outcome anomalies
- CURRENT_DESIGN_STATE: advanced
- RUNTIME_STATE: n/a
- EMPIRICAL_STATE: unresolved
- OPEN_OBLIGATION: mine real SC-900 outcome anomalies later
- TASK7_DISPOSITION: `DESIGN_ADVANCED_BUT_EMPIRICALLY_UNRESOLVED`

### NOETIC N07

- ORIGINAL_GATE2_STATE: `UNRESOLVED` (exact-item ≠ transfer)
- PHASE3_NEW_EVIDENCE: whole-family partition, 0 splits, 0 transfer crossings
- CURRENT_DESIGN_STATE: ontology advanced/specified
- RUNTIME_STATE: not proven
- EMPIRICAL_STATE: not proven
- OPEN_OBLIGATION: runtime enforcement + empirical transfer proof
- TASK7_DISPOSITION: `MATERIAL_DESIGN_ADVANCED_PENDING_RUNTIME_AND_EMPIRICAL_PROOF`

### NOETIC N08

- ORIGINAL_GATE2_STATE: `UNRESOLVED`
- PHASE3_NEW_EVIDENCE: several assumptions now specified rather than missing; remaining uncertainties listed
- CURRENT_DESIGN_STATE: improved, not retired
- RUNTIME_STATE: guards/RRC-1 absent
- EMPIRICAL_STATE: portability and contamination in use unproven
- OPEN_OBLIGATION: do not treat specification as self-attack closure
- TASK7_DISPOSITION: `UNRESOLVED`

## Acceptance conditions

Fresh evidence in this package:

```text
ALL_KNOWN_QUESTION_PATHS_RECONCILED = YES
NEWLY_DISCOVERED_PATHS_DOCUMENTED = YES
IMPLEMENTATION_READY_EXCLUSION_CONTRACT = FROZEN
FAIL_CLOSED_SEMANTICS = FROZEN
FUTURE_PATH_TEST_MATRIX = COMPLETE
RRC1_METRICS_DEFINED = YES
UNSUPPORTED_RRC1_THRESHOLDS_INVENTED = NO
PRIOR_DECAY_OBLIGATIONS_FROZEN = YES
MISSINGNESS_RULE_FROZEN = YES
CONTAMINATION_RULE_FROZEN = YES
ALLOCATION_CONFOUND_CONTROLS_FROZEN = YES
NOETIC_REASSESSMENT_COMPLETE = YES
RUNTIME_GUARDS_IMPLEMENTED = NO
RUNTIME_RRC1_IMPLEMENTED = NO
GATE2_REOPENED = NO
MERGE_PERFORMED = NO
```

## Standing authority (unchanged)

```text
PHASE_3_STRUCTURALLY_ACCEPTED = NO
CAND01_GATE2_STATUS = GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE
IMPLEMENTATION_AUTHORIZED = NO
NOETIC_GATE = BLOCK_POSITIVE_CLOSURE
```

The Gate-2 status string is preserved on purpose. Task 7 is not a Gate-2 reopening. Remaining blockers for any later reopening package include runtime-unproven enforcement, unresolved noetic items, unimplemented RRC-1 fairness calibration, and the still-unlaunched candidate bank. Task 8 must not treat this disposition as Gate-2 approval.

`GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE` remains the frozen CAND-01 status label. Task 7 does not rewrite that label merely because the candidate bank now has 200 reviewed questions. Launch/runtime structure is still the 8-question placeholder, and Gate 2 itself is not reopened here.

## Task-8 boundary

Stop.

Next package: **TASK 8 — FINAL VERIFICATION AND GATE-2 REOPENING HANDOFF**

Task 8 will:

- run complete Phase-3 and regression verification;
- run full unittest discovery;
- run lint/install/ruff/black/mypy;
- verify default/runtime immutability;
- verify protected refs;
- adversarially review the complete Phase-3 diff;
- determine Phase-3 structural acceptance;
- if structurally accepted, prepare the separate `SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001` handoff.

Even then, Gate 2 does not automatically become approved. The separate reopening package must receive its own adversarial decision.

Do not create `SC900-ENGINE-RDAF-CAND01-GATE2-REOPEN-001` in Task 7.

## Explicitly not claimed

```text
PHASE_3_STRUCTURALLY_ACCEPTED = NO
Gate 2 = NOT REOPENED
runtime implementation = NOT AUTHORIZED
TRAIN/PROBE runtime guards = NOT IMPLEMENTED
RRC-1 runtime = NOT IMPLEMENTED
learning effectiveness = NOT PROVEN
29 independent probe measurements = NO
N02/N06 resolved by bank growth = NO
merge = NOT PERFORMED
```
