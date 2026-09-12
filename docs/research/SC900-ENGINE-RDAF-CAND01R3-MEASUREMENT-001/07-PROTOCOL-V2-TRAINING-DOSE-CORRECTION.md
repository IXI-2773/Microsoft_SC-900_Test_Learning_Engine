# 07 — Protocol v2 training-dose correction

```text
V1_SUPERSEDED_BEFORE_EMPIRICAL_RUN = YES
SUPERSESSION_REASON = PRIMARY_DAYS_TRAINING_DOSE_WAS_UNBOUNDED
REAL_OBSERVATIONS_AT_SUPERSESSION = 0
EMPIRICAL_DATA_INVALIDATED = NO
READY_FOR_DAY1 = YES
```

## Versions

| Field | v1 | v2 |
| --- | --- | --- |
| protocol_version | `cand01r3-measurement-001-v1` | `cand01r3-measurement-001-v2` |
| protocol_sha256 | `493b371d6200c88fe51428953947fac864fae8535667374e38050198b018e081` | `51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72` |
| Days 1–6 train_item_budget | `null` | `20` |
| SMART_PRACTICE primary TRAIN total | unbounded | 60 |
| RRC_1 primary TRAIN total | unbounded | 60 |
| Day 7 | 10 + 10 | 10 + 10 |
| PROBE schedule | frozen | unchanged |
| TRAIN/PROBE partition | frozen | unchanged |
| primary endpoint | frozen | unchanged |
| policy order | frozen | unchanged |

v1 is retained as historical authority. It is not rewritten as if it never existed. This correction happened because REAL_OBSERVATIONS = 0. No empirical events were discarded.

## What changed

Only the primary-day TRAIN exposure budget. 20 is a methodological exposure-control constant: both arms receive equal opportunity; each scheduler can still choose different TRAIN items; Day 7 already used a 20-exposure total as 10+10.

## What did not change

PROBE question order, semantic-family assignments, policy order, primary endpoint, first-attempt / missingness / contamination / stopping rules, Gate-3 guards, RRC-1 algorithm, Smart Practice scoring, historical-prior prohibition, default launch bank.
