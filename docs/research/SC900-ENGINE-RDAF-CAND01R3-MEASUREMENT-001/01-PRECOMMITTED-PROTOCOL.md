# 01 — Precommitted protocol

```text
PROTOCOL_VERSION = cand01r3-measurement-001-v2
SUPERSEDED_PROTOCOL_VERSION = cand01r3-measurement-001-v1
MEASUREMENT_EPOCH = cand01r3-measurement-001
SCHEDULE_VERSION = cand01r3-probe-schedule-v1
POLICY_SEQUENCE_VERSION = cand01r3-alt-crossover-v1
ANALYSIS_VERSION = cand01r3-analysis-plan-v1
MACHINE_READABLE = content/sc900/measurement/cand01r3_protocol.json
```

Machine-readable protocol hash is computed from canonical JSON with `protocol_sha256` excluded, then stored on the committed object. No variable timestamps are included.

## Experimental question

Compare SMART_PRACTICE (champion) and RRC_1 (challenger) on the same frozen TRAIN universe, using clean first-attempt correctness on held-out SC-900 PROBE items.

Axis A (TRAIN/PROBE) is not Axis B (policy). Both arms train on TRAIN only. Neither may use PROBE for training. RRC-1 remains prior-neutral. Historical Security+ / SY0-701 data has zero runtime authority.

## Primary endpoint

```text
PRIMARY_ENDPOINT =
7-day first-attempt correctness on CLEAN HELD-OUT SC-900 PROBE items
```

A countable primary observation requires:

- observed = true
- first_attempt = true
- clean = true
- intended_use = MEASUREMENT
- question role = PROBE
- valid evaluation identity `(learner_id, SC-900, partition_epoch, question_id)`
- valid schedule/protocol authority

## Measurement unit

Record question-level and semantic-family-level outcomes. Primary interpretation must account for 7 independent PROBE families. Repeated same-family items are not fully independent.

## Stopping rule

Complete the scheduled 7-day protocol, or terminate the epoch on a protocol-invalidating event. Do not stop early because one policy looks ahead. Do not extend because a desired result has not appeared.

If a protocol defect is discovered after the first real observation: STOP the epoch. Do not rewrite history. Create a new protocol version and a new measurement epoch.

## Missingness rule

A missed scheduled PROBE is `UNOBSERVED`. It is not coerced to incorrect, correct, or zero, and it is not dropped from reporting.

## Contamination rule

Improper PROBE exposure is recorded as contaminated, excluded from the clean primary endpoint, and not silently replaced. Contamination is monotonic. No post-hoc replacement rule exists.

## First-attempt rule

Only the earliest valid clean scored PROBE attempt for `(learner_id, SC-900, partition_epoch, question_id)` is primary. Retry, redo, restored duplicates, and imported duplicates are excluded.

## Primary-day TRAIN exposure budget

v2 freezes 20 counted TRAIN exposures per active arm on Days 1–6. This is a methodological exposure-control constant, not an empirically optimized dose. SMART_PRACTICE and RRC_1 each receive 60 primary TRAIN exposures. Day 7 remains 10 + 10 and is not part of the simple Days 1–6 contrast.

A counted exposure is one TRAIN question presented in the scheduled policy-controlled training session. PROBE, rejected, preview, debug, and unobserved records do not count. Excess exposure is recorded as `OVER_BUDGET_TRAIN_EXPOSURE` and is not silently kept as in-budget dose.

## Activation

Normal startup does not activate this experiment. Activation requires explicit `begin_cand01r3_measurement(...)` with learner identity, measurement epoch, schedule version, policy sequence version, partition hashes, and candidate-bank identity.

## Protocol freeze lock

After the first real observation for this epoch, the protocol and policy sequence are immutable. Synthetic/TEST_ONLY events cannot enter the production ledger.
