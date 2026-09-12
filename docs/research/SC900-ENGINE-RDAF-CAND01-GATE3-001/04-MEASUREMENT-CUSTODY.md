# 04 — Measurement custody

```text
RECEIPT = SC900-ENGINE-RDAF-CAND01-GATE3-001 / 04-MEASUREMENT-CUSTODY
STATUS = IMPLEMENTED
ENDPOINT_MEASURED = NO
```

Module: `cand01r3_measurement.py`

This module implements observation identity and contamination rules. It does not claim policy effectiveness or that the 7-day endpoint has been measured.

## Identity

```text
evaluation_id = (learner_id, exam=SC-900, partition_epoch, canonical_question_id)
```

The local single-user learner id is `local-single-user`.

## First attempt

Only the earliest valid clean scored PROBE attempt is `PRIMARY`. Redo, retry, restore duplicates, and imported duplicates are `DUPLICATE_NOT_PRIMARY`.

## Missingness

Missed delayed measurement is `UNOBSERVED`. It is neither correct nor wrong and does not enter the primary numerator or denominator.

## Contamination

Contamination is monotonic for the affected evaluation identity. Contaminated observations are stored separately and excluded from the clean primary endpoint.

Persisted PROBE records store question id, selected option ids, correctness, and measurement metadata. Stem, explanation, and correct-answer text are not persisted.

Reporting identity preserves `PROBE_QUESTIONS = 29` and `INDEPENDENT_PROBE_FAMILIES = 7`.

## Tests

G3-030 through G3-034, plus custody and identity tests in `tests/test_cand01r3_measurement.py`.
