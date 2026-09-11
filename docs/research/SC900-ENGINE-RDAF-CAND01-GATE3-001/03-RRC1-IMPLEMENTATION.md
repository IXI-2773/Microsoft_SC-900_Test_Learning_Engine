# 03 — RRC-1 implementation

```text
RECEIPT = SC900-ENGINE-RDAF-CAND01-GATE3-001 / 03-RRC1-IMPLEMENTATION
STATUS = IMPLEMENTED
PRIOR_NEUTRAL = VERIFIED
```

Module: `cand01r3_rrc1.py`

Eligible universe: TRAIN only. PROBE never enters a class.

## Classes

At one assignment snapshot:

1. `REPAIR` if `is_active_weak(record)`
2. `REVIEW` if not REPAIR and `is_review_due(record)`
3. `COVERAGE` otherwise

Classes are mutually exclusive.

## Service

Round-robin `REPAIR → REVIEW → COVERAGE`. Empty classes emit `EMPTY_CLASS_SKIP` with no fake credit. Selection stops at session size or pool exhaustion.

In-class order:

- REPAIR: lowest recent correctness, then least recently seen, then stable question id
- REVIEW: oldest due timestamp, then least recently seen, then stable question id
- COVERAGE: largest blueprint deficit, unseen before seen, least recently seen, stable question id

No weighted utility. Historical SY0-701 prior, confidence, and response-time fields are not class inputs.

Fairness metrics are recorded without pass/fail thresholds.

## Tests

G3-008, G3-038, G3-039, G3-040, class exclusivity, round-robin, empty skip, deterministic ties, session-size limit.
