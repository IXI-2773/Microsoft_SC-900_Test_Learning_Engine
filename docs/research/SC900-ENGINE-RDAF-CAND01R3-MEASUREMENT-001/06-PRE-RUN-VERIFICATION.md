# 06 — Pre-run verification and learner instructions

```text
CAND01R3_MEASUREMENT_PROTOCOL_V2_FROZEN
PRIMARY_DAILY_TRAIN_BUDGET = 20
SMART_PRACTICE_PRIMARY_TRAIN_TOTAL = 60
RRC1_PRIMARY_TRAIN_TOTAL = 60
PRIMARY_EXPOSURE_DIFFERENCE = 0
REPOSITORY_REAL_OBSERVATIONS = 0
PRODUCTION_LEDGER_STATUS = UNVERIFIED_AUTHORIZED_MACHINE_OFFLINE
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
DEFAULT_BANK_UNCHANGED = YES
DEPLOYMENT_AUTHORIZED = NO
READY_FOR_DAY1 = NO
RUNTIME_RESUME_VERIFIED = YES
TRAIN_EXPOSURE_PERSISTENCE = VERIFIED
TRAIN_TO_MEASUREMENT_TRANSITION = VERIFIED
WRONG_DAY_PROBE_REJECTION = VERIFIED
EARLY_PROBE_REJECTION = VERIFIED
DAY7_POLICY_HANDOFF = VERIFIED
FROZEN_COMPILED_ANSWER_KEY_AUTHORITY = VERIFIED
MUTABLE_RUNTIME_ANSWER_KEY_AUTHORITY = PROHIBITED
DUPLICATE_SCORER_DEFINITIONS = 0
FINAL_MEASUREMENT_ADVERSARIAL_SWEEP = CLEAR
```

The earlier `READY_FOR_DAY1 = YES` disposition is superseded. Repository integrity checks are green, but the mandatory direct check of the authorized application's production empirical ledger cannot be completed while the authorized desktop is offline. Committed JSON indicating zero observations is not production-ledger proof. Until that check succeeds, Day 1 remains not started and readiness remains `NO`.

## Pre-run checks

Verified in the repository:

- 200 approved questions / 171 TRAIN / 29 PROBE / 7 PROBE families
- 0 role splits / 0 transfer crossings
- Gate-3 guards enable only after explicit `begin_cand01r3_measurement`
- RRC-1 prior-neutral
- default launch-bank SHA-256 `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`
- protocol version `cand01r3-measurement-001-v2`
- protocol SHA-256 `51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72`
- policy order and schedule frozen
- frozen compiled-bank answer authority required for measurement scoring
- runtime `question["correct"]` prohibited as measurement-scoring authority
- exactly one effective measurement scorer and recorder
- same frozen v2 epoch resumes after restart from append-only ledger evidence
- counted TRAIN exposures persist; Day-7 Smart Practice → RRC-1 handoff is automatic
- PROBE scoring requires completed TRAIN block plus explicit MEASUREMENT transition
- ordinary learner/training state does not mutate from PROBE scoring
- PROBE correctness/explanations are suppressed
- learner-facing PROBE persistence/export is redacted
- current-day calendar timing and today-only frozen PROBE order are enforced

Still required before first real observation:

- directly inspect the authorized application's runtime user-data ledger `cand01r3-measurement-001.jsonl`;
- prove `REAL_OBSERVATIONS = 0` from that production ledger;
- prove Day 1 has not already started in that production ledger;
- stop if the ledger is missing, malformed, non-empty, or otherwise inconsistent with the frozen authority.

## Current verification evidence

The repaired source content has passed:

```text
R2 = 41/41 PASS
R2-041 = PASS
R1 = 30/30 PASS
PROTOCOL_V2 = 20/20 PASS
ALL_CAND01R3 = 187/187 PASS
PHASE3 = 79/79 PASS
FULL_SUITE = 783 RUN / 0 FAILURES / 0 ERRORS / 230 SKIPPED
RUFF = PASS
BLACK_CHECK = PASS
MYPY = PASS
FINAL_MEASUREMENT_ADVERSARIAL_SWEEP = CLEAR
```

The permanent read-only exact-SHA verifier also enforces `lint_bank`, `verify_installation`, the three deterministic Phase-3 verifiers, frozen hash/protocol proofs, protected-ref proofs, and clean-tree invariants. See `09-PRE-DAY1-MEASUREMENT-INTEGRITY-REPAIR.md` for the repair history and terminal evidence.

## Learner instructions — BLOCKED until readiness changes

Do **not** begin the measurement epoch while `READY_FOR_DAY1 = NO`.

Once a later direct production-ledger check proves the ledger is empty and the terminal disposition is explicitly changed to `READY_FOR_DAY1 = YES`, the learner procedure remains:

1. Launch the application normally. The default 8-question launch bank must still load. Do not treat that bank as the experiment.
2. Open **Research → Begin CAND-01R3 Measurement Epoch...** and confirm. This is the only activation path. If the same frozen v2 epoch already exists, this resumes it; it does not mint a new epoch.
3. When asked, load the compiled candidate bank for this epoch only: `content/sc900/phase3/compiled/sc900_phase3_reviewed_bank.json`. This does not make it the application default.
4. Each calendar day, open **Research → Set Measurement Day...** and enter 1–7. Day N cannot start before `Day1 + (N-1)` local calendar days, and Day N+1 must not begin while Day N has unanswered scheduled PROBEs.
5. Train only on TRAIN items under that day's policy until the frozen budget is complete:
   - Days 1, 3, 5: Smart Practice, 20 TRAIN exposures.
   - Days 2, 4, 6: RRC-1, 20 TRAIN exposures.
   - Day 7: 10 Smart Practice TRAIN items, then automatic RRC-1 handoff for 10 RRC-1 TRAIN items.
6. After training, open **Research → Begin Today's PROBE Measurement...**. Answer only that day's scheduled PROBE items once as clean first attempts. Do not peek at explanations and do not redo/retry for the primary endpoint.
7. If a scheduled PROBE is missed, use **Research → Record Unobserved PROBE...**. Do not guess an answer to fill the cell.
8. If substantial outside SC-900 study occurred, use **Research → Record Outside-Study Declaration...**.
9. Stop after Day 7 or if a protocol-invalidating event occurs. Do not stop early because one policy appears ahead.
10. Do not declare a winner. Later adjudication analyzes the frozen ledger.

If the production ledger already contains a real event, do not edit the protocol or erase evidence. Stop and reconcile the frozen epoch before any further empirical action.
