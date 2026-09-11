# SC900-ENGINE-RDAF-CAND01R3-MEASUREMENT-001 — Handoff

```text
WORK_ID = SC900-ENGINE-RDAF-CAND01R3-MEASUREMENT-001
CANDIDATE = CAND_01R3
PACKAGE = CONTROLLED SMART PRACTICE VS RRC-1 MEASUREMENT PROTOCOL
GATE_3_HEAD = f742dcc085d46f1999eb8782f709730323e9d7f0
MEASUREMENT_BRANCH = research/sc900-cand01r3-measurement-001
PROTOCOL_VERSION = cand01r3-measurement-001-v1
MEASUREMENT_EPOCH = cand01r3-measurement-001
REAL_OBSERVATIONS = 0
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
DEPLOYMENT_AUTHORIZED = NO
```

## Authority inherited, not reopened

Gate 3 remains accepted. Phase 3 remains structurally accepted. This package freezes the measurement protocol. It does not merge PR #10, #11, or #12. It does not activate the candidate bank as the application default. It does not declare a Smart Practice vs RRC-1 winner.

## Frozen inputs

| Artifact | SHA-256 |
| --- | --- |
| Task-4 semantic audit | `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701` |
| Task-5 reviewed store | `2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c` |
| Task-5 compiled candidate bank | `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b` |
| Task-6 TRAIN/PROBE manifest | `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90` |
| Default launch bank | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

```text
TRAIN_QUESTIONS = 171
PROBE_QUESTIONS = 29
INDEPENDENT_PROBE_FAMILIES = 7
TRAIN_PROBE_FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
```

Do not describe 29 PROBE questions as 29 independent semantic observations.

## What this package freezes

- Primary endpoint
- 7-day PROBE schedule
- Alternating / Day-7 balanced policy sequence
- Missingness, contamination, and first-attempt rules
- Analysis plan
- Operator-controlled `begin_cand01r3_measurement(...)`
- Append-only measurement ledger

## What this package does not do

```text
invent learner answers = NO
simulate empirical success = NO
populate outcomes = NO
change TRAIN/PROBE membership = NO
use historical SY0-701 prior = NO
promote a policy automatically = NO
issue RRC1_SUPPORTED / RRC1_NOT_SUPPORTED / INCONCLUSIVE = NO
```

## Next action

The human learner actually runs the controlled experiment. See `06-PRE-RUN-VERIFICATION.md` for the exact application steps.
