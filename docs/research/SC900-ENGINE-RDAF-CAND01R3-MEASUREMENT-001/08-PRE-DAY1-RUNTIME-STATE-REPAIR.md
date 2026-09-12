# 08 — Pre-Day-1 runtime state-machine repair

```text
CAND01R3_PRE_DAY1_RUNTIME_REPAIR_ACCEPTED
PROTOCOL_VERSION = cand01r3-measurement-001-v2
PROTOCOL_SHA256 = 51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72
SCIENTIFIC_PROTOCOL_CHANGED = NO
MEASUREMENT_EPOCH = cand01r3-measurement-001
RUNTIME_STATE_MACHINE = IMPLEMENTED
SAME_EPOCH_RESTART_RESUME = VERIFIED
TRAIN_EXPOSURE_PERSISTENCE = VERIFIED
TRAIN_TO_MEASUREMENT_TRANSITION = VERIFIED
EARLY_PROBE_REJECTION = VERIFIED
WRONG_DAY_PROBE_REJECTION = VERIFIED
WRONG_POLICY_DEVIATION_PERSISTENCE = VERIFIED
DAY7_AUTOMATIC_POLICY_HANDOFF = VERIFIED
PRIMARY_DAILY_TRAIN_BUDGET = 20
SMART_PRACTICE_PRIMARY_TOTAL = 60
RRC1_PRIMARY_TOTAL = 60
PROBE_SCHEDULE = UNCHANGED
TRAIN_PROBE_PARTITION = UNCHANGED
REAL_OBSERVATIONS = 0
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
DEFAULT_BANK_UNCHANGED = YES
DEPLOYMENT_AUTHORIZED = NO
READY_FOR_DAY1 = YES
```

This is a runtime/state-machine repair. It does not redesign the frozen v2 scientific protocol. Day 1 has not started. No real observations were created.

## Defects found

A pre-Day-1 runtime review found that the frozen v2 design could not actually be executed as a seven-day experiment:

1. `begin_cand01r3_measurement(...)` reused `allow_v2_supersession(real_observations)` as the ordinary resume gate. That gate exists only for v1 → v2 pre-run supersession at `REAL_OBSERVATIONS = 0`. After one legitimate Day-1 observation, restarting and reopening the same frozen v2 epoch failed closed with `NEW_MEASUREMENT_EPOCH_REQUIRED`.
2. `set_measurement_day()` always left `get_context().intended_use = TRAINING`. The measurement card could say `TRAINING_BLOCK_COMPLETE`, but the renderer still rejected PROBE items.
3. `record_measurement_event()` checked that a PROBE existed in the seven-day schedule, not that it belonged to the current day, that the required TRAIN block was complete, and that runtime state was `MEASUREMENT`. Early and wrong-day PROBEs could become `PRIMARY`.
4. Counted TRAIN exposures lived in `_SESSION.train_log` only. Restart lost 20-item budget progress, policy dose, and family/domain/objective history.
5. Day 7 could identify the next 10-item block, but runtime policy did not automatically advance from Smart Practice to RRC-1 after the 10th counted Smart Practice exposure.

## Root causes

- Protocol supersession and same-epoch resume were one gate.
- Display text was not a durable state machine.
- PROBE scoring trusted schedule membership instead of current-day MEASUREMENT eligibility.
- TRAIN accounting was process memory, not append-only ledger evidence.
- Day-7 block selection did not write the active runtime policy after the first block completed.

## RED evidence

`tests/test_cand01r3_measurement_runtime_resume.py` was written first and run against HEAD `9d9fe5095ac0a2222de67bc94c795ef070f94d6d` before implementation.

```text
Ran 30 tests in 0.206s
FAILED (failures=5, errors=21)
```

Observed RED:

- R1-001..R1-004, R1-014..R1-016, R1-018..R1-025, R1-030: missing `begin_todays_probe_measurement` / `measurement_runtime_state`
- R1-005, R1-006, R1-009: TRAIN progress and over-budget state were memory-only
- R1-007: 0 `TRAIN_EXPOSURE` ledger rows after 3 counted trains
- R1-008: `WRONG_POLICY_USED` not persisted
- R1-010, R1-011: Day-1 PROBE after `set_measurement_day(1)` with 0 TRAIN recorded as `PRIMARY`
- R1-026: Day 2 could begin while Day 1 was incomplete
- R1-017, R1-027, R1-028, R1-029 already passed (renderer already rejected PROBE during TRAINING; protocol SHA and production ledger were already clean)

## Implemented repair

### Resume semantics

`allow_v2_supersession` remains the v1 → v2 pre-run gate only. It is not the normal resume gate.

`begin_cand01r3_measurement(...)`:

- ledger absent/empty → `BEGIN_NEW_FROZEN_EPOCH` and append `EPOCH_BEGIN`
- ledger belongs to the same epoch, protocol version, protocol hash, partition epoch, manifest/store/semantic-audit/compiled hashes, learner identity, and candidate-bank identity → `RESUME_EXISTING_EPOCH`
- otherwise fail closed (`WRONG_MEASUREMENT_EPOCH`, `PROTOCOL_HASH_MISMATCH`, `AUTHORITY_HASH_MISMATCH`, `LEARNER_IDENTITY_MISMATCH`, `PARTITION_EPOCH_MISMATCH`)

A valid same-epoch resume after real observations is allowed. Resume reconstructs TRAIN counts, Day-7 block counts, PROBE outcomes, contamination, UNOBSERVED, and day completion from the append-only ledger.

### State machine

Days 1–6: `DAY_NOT_STARTED` → `TRAINING` → `TRAINING_COMPLETE` → `MEASUREMENT` → `DAY_COMPLETE`

Day 7: `DAY_NOT_STARTED` → `SMART_PRACTICE_TRAINING` → `RRC1_TRAINING` → `RRC1_COMPLETE` → `MEASUREMENT` → `DAY_COMPLETE`

`set_measurement_day` starts TRAINING (or Day-7 Smart Practice). At the frozen TRAIN budget, state becomes `TRAINING_COMPLETE` / `RRC1_COMPLETE` without changing intended use. The operator must call **Research → Begin Today's PROBE Measurement...** (`begin_todays_probe_measurement()`), which switches `intended_use` to `MEASUREMENT` and restricts eligibility to that day's frozen PROBE list. A day becomes complete only when every scheduled PROBE has a terminal disposition (`PRIMARY`, `CONTAMINATED`, or `UNOBSERVED`). Calendar day does not auto-advance. Starting Day N+1 while Day N is incomplete fails closed with `PREVIOUS_DAY_INCOMPLETE`.

### Fail-closed PROBE gating

Before a scheduled PROBE can become `PRIMARY`, the runtime requires an active session, a current day, `MEASUREMENT` mode, PROBE role, `scheduled_day == current_scheduled_day`, completed required TRAIN block, membership in today's frozen PROBE list, and valid protocol/epoch/first-attempt identity. Otherwise the event is rejected as `PROBE_BEFORE_TRAIN_BLOCK_COMPLETE`, `MEASUREMENT_MODE_NOT_ACTIVE`, `WRONG_MEASUREMENT_DAY`, or `UNSCHEDULED_PROBE`.

### Ledger event additions

Counted TRAIN exposures append `TRAIN_EXPOSURE` rows with epoch/protocol/learner/day/policy/question/family/domain/objective/service_class/`counted=true`/timestamp/authority identity. PROBE answer material is not stored on those rows. Durable deviations include `WRONG_POLICY_USED`, `OVER_BUDGET_TRAIN_EXPOSURE`, `TRAINING_AFTER_BLOCK_COMPLETE`, `PROBE_BEFORE_TRAIN_BLOCK_COMPLETE`, `WRONG_MEASUREMENT_DAY`, `MEASUREMENT_MODE_NOT_ACTIVE`, and `INSUFFICIENT_TRAIN_CAPACITY` when encountered. The ledger remains the evidence authority; in-memory session state is reconstructed from it.

### Day-7 handoff

Day 7 starts on Smart Practice with budget 10. After the 10th counted Smart Practice TRAIN exposure, runtime policy advances to RRC-1 automatically. After the 10th counted RRC-1 exposure, state is `RRC1_COMPLETE`. Only then may the operator begin today's PROBE measurement and see the five frozen Day-7 PROBEs.

## Proof the scientific protocol is unchanged

- `PROTOCOL_VERSION` remains `cand01r3-measurement-001-v2`
- Protocol SHA-256 remains `51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72`
- `content/sc900/measurement/cand01r3_protocol.json` was not modified
- PROBE schedule, TRAIN/PROBE membership, semantic families, primary endpoint, 20-item Days 1–6 budget, Day-7 10+10 structure, first-attempt / contamination / missingness / stopping rules, Smart Practice algorithm, RRC-1 algorithm, historical-prior prohibition, and default launch bank are unchanged

## Proof REAL_OBSERVATIONS = 0

- committed protocol `real_observations` = 0
- production ledger path for `cand01r3-measurement-001` is absent
- all resume/restart tests used temporary TEST ledgers, not the production ledger
- no Day-1 empirical run was started
