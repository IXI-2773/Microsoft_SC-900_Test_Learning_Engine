# 06 — Pre-run verification and learner instructions

```text
CAND01R3_MEASUREMENT_PROTOCOL_V2_FROZEN
PRIMARY_DAILY_TRAIN_BUDGET = 20
SMART_PRACTICE_PRIMARY_TRAIN_TOTAL = 60
RRC1_PRIMARY_TRAIN_TOTAL = 60
PRIMARY_EXPOSURE_DIFFERENCE = 0
REAL_OBSERVATIONS = 0
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
DEFAULT_BANK_UNCHANGED = YES
DEPLOYMENT_AUTHORIZED = NO
```

## Pre-run checks

Verify before the first real observation:

- 200 approved questions / 171 TRAIN / 29 PROBE / 7 PROBE families
- 0 role splits / 0 transfer crossings
- Gate-3 guards enable only after explicit `begin_cand01r3_measurement`
- RRC-1 prior-neutral
- default launch-bank SHA-256 `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`
- protocol and schedule deterministic
- policy order frozen
- measurement ledger empty for epoch `cand01r3-measurement-001`
- no preexisting first-attempt PROBE outcome in that epoch

## What the human learner must do next

1. Launch the application normally. The default 8-question launch bank must still load. Do not treat that bank as the experiment.
2. Open **Research → Begin CAND-01R3 Measurement Epoch...** and confirm. This is the only activation path.
3. When asked, load the compiled candidate bank for this epoch only. Path: `content/sc900/phase3/compiled/sc900_phase3_reviewed_bank.json`. This does **not** make it the application default.
4. Each calendar day, open **Research → Set Measurement Day...** and enter 1–7.
5. Train only on TRAIN items under that day's policy until the frozen budget is complete:
   - Days 1, 3, 5: Smart Practice, **20 TRAIN exposures**
   - Days 2, 4, 6: RRC-1, **20 TRAIN exposures**
   - Day 7: 10 Smart Practice TRAIN items, then 10 RRC-1 TRAIN items
   The measurement card shows remaining count. Stop when it says TRAINING BLOCK COMPLETE. Do not add extra TRAIN items before that day's PROBE.
6. After training, answer **only that day's scheduled PROBE items**, once, as clean first attempts. Use **Research → Show Today's Measurement Card...** for the IDs. Do not peek at explanations before scoring. Do not redo/retry for the primary endpoint.
7. If a scheduled PROBE is missed, use **Research → Record Unobserved PROBE...**. Do not guess an answer to fill the cell.
8. If substantial outside SC-900 study happened, use **Research → Record Outside-Study Declaration...**.
9. Stop after Day 7 or if a protocol-invalidating event occurs. Do not stop early because one policy looks ahead.
10. Do not declare a winner. The later adjudication package analyzes the frozen ledger.

If the epoch ledger already contains a real event, do not edit the protocol. Stop and open a new epoch.
