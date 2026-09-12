# Runtime tier integration assessment

Exam, Practice, and Smart Practice already load the compiled bank, preserve canonical IDs, and sample from the full approved pool. They do not read `exam_calibration_tier` or `exam_simulation_eligible`.

Existing filters are domain, topic, and learner-history status. Bank `beginner` / `intermediate` labels are not an Exam-mode sampling control. Empirical difficulty calibration in analytics is learner-performance based, not authoring-tier based.

A tiny configuration path could later exclude Stretch from ordinary Exam simulation by filtering `exam_simulation_eligible == true`. That is a bounded later change. This package does not add a sampling subsystem.

## Decision

`EXAM_TIER_RUNTIME_INTEGRATION_REQUIRED = YES`

Leave runtime behavior unchanged here. Stretch items remain in the candidate bank for Smart Practice and hard review. Ordinary Exam mode will keep drawing from the full 454 until a later authorized package consumes the new metadata.

Compatibility exercised against the calibrated bank: load, parse, canonical IDs, fingerprint, Practice/Exam signatures, ordered and randomized order, resume snapshot, confidence progress records, and analytics builders. No production engine feature work was added.
