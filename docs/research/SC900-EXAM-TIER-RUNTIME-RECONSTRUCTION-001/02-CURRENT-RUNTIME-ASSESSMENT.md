# Current runtime assessment

Authority reviewed before implementation:

- `docs/research/SC900-EXAM-CALIBRATION-001/02-CALIBRATION-RUBRIC.md`
- `docs/research/SC900-EXAM-CALIBRATION-001/03-454-QUESTION-CLASSIFICATION.md`
- `docs/research/SC900-EXAM-CALIBRATION-001/08-RUNTIME-TIER-INTEGRATION-ASSESSMENT.md`
- `docs/research/SC900-EXAM-CALIBRATION-001/09-FINAL-CALIBRATION-DISPOSITION.md`
- calibration JSON/ledger and the compiled 454-question bank
- `app_session_builder_mixin.py`, `app_session_persistence_mixin.py`, `app_constants.py`, `question_bank.py`, `bank_models.py`, `builder_identity.py`
- Exam, Practice, Smart Practice, BACKLOG-1/2/3, persistence/restore, final-bank, and exam-calibration tests

## Published calibration contract

| Metric | Count |
| --- | --- |
| Approved items | 454 |
| FUNDAMENTALS_CORE | 301 |
| FUNDAMENTALS_APPLIED | 130 |
| STRETCH | 23 |
| Ordinary-Exam eligible | 431 |

Every approved calibrated item already carries `exam_calibration_tier`, `reasoning_steps`, `exam_simulation_eligible`, and `calibration_version`. Core and Applied are ordinary-Exam eligible. Stretch is not.

## Runtime gap on published main

`08-RUNTIME-TIER-INTEGRATION-ASSESSMENT.md` recorded `EXAM_TIER_RUNTIME_INTEGRATION_REQUIRED = YES`. Exam, Practice, and Smart Practice loaded the compiled bank and sampled from the full approved pool. They did not read `exam_simulation_eligible`.

Confirmed by RED evidence on this reconstruction:

- Ordered new Exam with count `1` selected the first Stretch item (`stretch-q`).
- Practice retained Stretch and other `exam_simulation_eligible=false` items.
- Smart Practice candidate population retained those same items.
- Questions missing `exam_simulation_eligible` remained in the Exam pool (legacy eligible).
- A persisted Exam snapshot containing Stretch restored its saved identity and order.

Existing filters already composed domain, topic, and learner-history source. Count handling already clamped to available pool size. No new sampling subsystem was required.

## Builder identity

BACKLOG-3 canonical builder/resume identity keys on mode, count, source, randomize, and domain/topic/status filters. Exam eligibility is a construction-pool filter, not a builder-request field. No fingerprint collision or resume defect was demonstrated, so builder identity was left unchanged.
