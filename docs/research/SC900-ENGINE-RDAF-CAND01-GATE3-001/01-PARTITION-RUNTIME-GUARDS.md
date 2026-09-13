# 01 — Partition runtime guards

```text
RECEIPT = SC900-ENGINE-RDAF-CAND01-GATE3-001 / 01-PARTITION-RUNTIME-GUARDS
STATUS = IMPLEMENTED
```

## Shared eligibility boundary

Module: `cand01r3_partition.py`

```text
partition_eligibility(question, intended_use, runtime_authority)
  -> TRAIN | PROBE | NOT_ELIGIBLE
```

Intended uses: `TRAINING`, `MEASUREMENT`.

Authority inputs are hash-bound to the frozen Task-4 audit, Task-5 store, and Task-6 manifest. Hash comparison uses the repository canonical CRLF→LF digest. Frozen artifacts are not rewritten.

## Fail-closed TRAINING

TRAINING accepts TRAIN only. It rejects PROBE, UNASSIGNED, unknown/malformed/missing roles, missing manifest, hash mismatches, unknown questions, unknown/unresolved families, unapproved items, family-role inconsistency, and transfer-edge conflict.

An empty TRAIN pool stays empty. There is no fallback to PROBE or to the unpartitioned bank.

## Fail-closed MEASUREMENT

MEASUREMENT accepts PROBE only when approved, resolved, probe-eligible, family-consistent, and free of TRAIN members or transfer-edge crossings.

## Scoped activation

Module: `cand01r3_runtime.py`

CAND-01R3 is inactive by default. Partition filtering is a no-op until `activate_cand01r3_experiment(...)` is called. Inactive default-bank sessions remain operational without a Phase-3 manifest (G3-036, G3-037).

## Tests

G3-019 through G3-029, G3-035 through G3-037, plus frozen-hash binding tests in `tests/test_cand01r3_partition.py` and restore tests in `tests/test_cand01r3_all_paths.py`.
