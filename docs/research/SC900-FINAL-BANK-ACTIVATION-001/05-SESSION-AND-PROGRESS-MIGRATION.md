# Session and progress migration

Activation changes active bank identity from 8 placeholder questions (`SC900-PH-*`) to 454 calibrated questions (`sc900_p1_q*` and successors). No broad conversion migrator was added. Isolation and fail-closed behavior already exist and were proven sufficient.

## Isolation by runtime stem

`runtime_bank_stem()` uses the bank filename stem.

| Bank | Stem | Progress file | Session file prefix |
| --- | --- | --- | --- |
| Historical baseline | `sc900_bank_v8_baseline` | `sc900_bank_v8_baseline_progress.json` | `sc900_bank_v8_baseline_*_session_*` |
| Active final | `sc900_bank_v8_final` | `sc900_bank_v8_final_progress.json` | `sc900_bank_v8_final_*_session_*` |

Existing baseline progress/session files are therefore not opened as 454-bank state.

## Proven behaviors

1. Application starts with the final active bank (`TestingEngineApp` loaded 454 master questions).
2. Existing baseline progress in the user-data directory does not crash startup.
3. Baseline session snapshots are not treated as valid 454-bank sessions: fingerprints and stems differ; `saved_session_matches_current` returns false.
4. `migrate_session_snapshot` raises `ValueError` on bank fingerprint mismatch.
5. Baseline progress bytes were unchanged after startup and after a new final-bank session save.
6. Canonical learner-history structure remains valid for new final-bank sessions.
7. Placeholder IDs are disjoint from calibrated IDs. Feeding baseline canonical progress into `migrate_progress_content_epoch` against the 454 bank quarantines `SC900-PH-*` as `REMOVED_QUESTION` and does not bind `sc900_p1_q001`.
8. New final-bank Practice sessions persist and resume by fingerprint + canonical IDs.
9. Historical final-bank Exam snapshots that include Stretch restore saved identity/order under PR #26 semantics; new Exam construction still excludes Stretch.

`SESSION_MIGRATION_SAFETY = PASS`

`BASELINE_PROGRESS_COMPATIBILITY = PASS` (non-destructive isolation)

`BASELINE_SESSION_ISOLATION = PASS`

`FINAL_BANK_SESSION_RESUME = PASS`

No speculative conversion of 8-question history onto 454-question IDs was implemented.
