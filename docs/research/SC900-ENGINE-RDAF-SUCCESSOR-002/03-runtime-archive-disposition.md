# CAND-01R2 Runtime Archive Disposition

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`  
STATUS = `PRIVATE_PROFILE_EXTRACTED_GATE2_PENDING`  
GATE_2 = `NOT_YET_EARNED`  
GATE_3 = `NOT_RUN`  
IMPLEMENTATION_AUTHORIZED = `NO`

## Purpose

Record the non-private methodological disposition of the second historical SY0-701 runtime archive without publishing learner outcomes or raw history.

## Structural result

The supplied runtime archive contains the authoritative artifact classes required by the precommitted extraction protocol:

- a current `*_progress.json` payload with chronological history;
- an automatic progress backup;
- saved practice / Smart Practice session files;
- checkpoint files;
- application configuration;
- application log material.

Archive inspection found no path-traversal entries and no encrypted members. The current progress record is newer than the automatic backup, and the backup history is an exact prefix of the current history. The current progress payload is therefore the authoritative learner-history source for this extraction; the backup is retained only as corroborating/recovery evidence and is not double-counted.

The runtime payload identifies the legacy engine as app version `8.0.0` and the SY0-701 v4 public bank. This is sufficient to apply the schema contract already frozen in `02-historical-data-extraction-protocol.md`.

## Field-availability result

The authoritative history provides the fields needed to evaluate the precommitted portable traits T1–T6 and T8. Explicit saved-session histories provide a bounded basis for T7 session-endurance analysis without inventing session boundaries from timestamp gaps.

Per the precommitment, learner outcomes, question-level history, answer text, local paths, and private aggregate profile values are not committed to this public repository.

A private aggregate learner-strategy profile has been produced from the supplied runtime archive. Its policy consequences are treated only as a CAND-01R2 cold-start prior and remain subject to Gate-2 adversarial review and the frozen SEED / ADVISORY / RETIRED decay rule.

## Gate consequence

The presence of usable historical data does **not** itself earn Gate 2 and does not authorize runtime implementation.

Next Gate-2 work must challenge at least:

- whether the historical prior is confounded by legacy Smart Practice selection;
- whether same-item recovery is cue dependence rather than durable learning;
- whether session-endurance observations are stable enough to influence session policy;
- whether confidence and response-time signals should have any scheduler authority;
- whether DWC-1 is a fair challenger rather than an intentionally weak control;
- whether SC-900 held-out evidence can override the historical prior exactly as precommitted.

`GATE_2 = NOT_YET_EARNED`  
`IMPLEMENTATION_AUTHORIZED = NO`
