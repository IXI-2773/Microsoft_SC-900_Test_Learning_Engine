# 02 — Smart Practice isolation

```text
RECEIPT = SC900-ENGINE-RDAF-CAND01-GATE3-001 / 02-SMART-PRACTICE-ISOLATION
STATUS = IMPLEMENTED
CHAMPION_BEHAVIOR = UNCHANGED_EXCEPT_TRAIN_UNIVERSE
```

Inside an active CAND-01R3 context, Smart Practice remains the current champion policy. Only the eligible universe is restricted to TRAIN.

## Early filter

`_build_smart_practice_signal_payload` now builds derived state from `training_source_questions(...)` before signal computation. Remaining payload maps that previously iterated `master_questions` use the TRAIN-only `signal_questions` set.

## Worker / cache

`_smart_practice_worker_snapshot` copies TRAIN-only `master_questions` and `base_pool`. Cache keys include `partition_cache_identity()`, so partition epoch, manifest hash, store hash, experiment id, and policy changes invalidate pre-partition snapshots.

## Tests

G3-002, G3-003, G3-004, G3-005, plus `test_smart_practice_champion_is_not_rewritten`.
