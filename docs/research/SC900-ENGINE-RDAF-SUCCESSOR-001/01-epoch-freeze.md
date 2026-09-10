# Phase 1 — Frozen Research Epoch

Do not research against a moving undefined target. This file freezes the denominator for `SC900-ENGINE-RDAF-SUCCESSOR-001`. Later research may create a new epoch. This investigation must not silently change these values.

## Frozen identifiers

```
RDAF_RESEARCH_EPOCH_ID = SC900-RDAF-EPOCH-2026-09-10-001
WORK_ID = SC900-ENGINE-RDAF-SUCCESSOR-001
BASELINE_SHA = fed4d4a44591ca93fe8428bc3ca02ec66a12f715
FROZEN_TAG = sc900-v8.0.0-baseline
OBSERVATION_CUTOFF = 2026-09-10T21:00:00-07:00
RESEARCH_CUTOFF = 2026-09-10T21:00:00-07:00
CURRENT_PUBLIC_RESEARCH_CUTOFF = 2026-09-10
CURRENT_ENGINE_SUBJECT = SC-900 Test Learning Engine v8.0.0 at frozen baseline SHA fed4d4a, policy label smart-practice-9, placeholder bank sc900_bank_v8_baseline.json (8 original items)
EXTRACTOR_LANE_EXCLUDED = integration/sc900-extractor-v1 @ 338fd7d9a4ca96aa120d344300dc9e9f37608068
PR1_STATUS = OPEN / DRAFT / NOT MERGED
```

## Tag custody (verified this epoch)

- Annotated tag `sc900-v8.0.0-baseline` object still names commit `fed4d4a44591ca93fe8428bc3ca02ec66a12f715`.
- Tag message records verified source SHA, GitHub Actions run `34525163742`, artifact ID `10171308236`.
- This package **must not move the tag**.

## SOURCE_UNIVERSE_POLICY

1. Prefer peer-reviewed primary studies, systematic reviews, and meta-analyses over blogs/tutorials.
2. Prefer educational-measurement, cognitive-psychology, learning-science, psychometrics, ITS, and official assessment-standard sources.
3. Blogs/tutorials may identify terminology only. They may not carry consequential claims when stronger evidence exists.
4. Do not ingest or commit copyrighted article PDFs.
5. Record DOI / stable URL / ERIC / PubMed IDs when available.
6. Distinguish FOUNDATIONAL / REPLICATED / META_ANALYTIC / RECENT / CONTESTED / WEAK / CONTRADICTED.
7. Citation count is not a proxy for truth.
8. Certification self-study is **not** automatically equivalent to classroom learning, medical-student retrieval, or flashcard SRS.
9. Single-learner local desktop use is **not** equivalent to population CAT/IRT calibration.
10. Engine unit/regression tests are evidence of **implementation behavior**, not of **learning effectiveness**.

## MATERIALITY_POLICY

A finding is material if it can change whether a current mechanism should be KEPT, MODIFIED, REPLACED, REMOVED, or held for RESEARCH_MORE, **or** if it changes the validity of a learner-facing claim (readiness, mastery, difficulty, calibration).

Non-material: cosmetic UI, packaging, Windows path spelling, extractor-lane content pipeline, and any RDAF-inside-the-app proposal.

## STOP_CONDITION

Stop this epoch (do not broaden to evade) if any of:

- research denominator is incomplete
- source access prevents defensible conclusions
- a material N01–N08 item remains UNRESOLVED **and** a positive design closure is attempted
- Route B exposes an unresolved load-bearing contradiction that would be required to authorize implementation
- candidate improvements cannot be measured
- current implementation is insufficiently understood
- a recommendation requires data the v8 local engine does not possess
- positive Gate 1 is unsupported

This tranche **stops after Gate 1**. Gate 2 and Gate 3 are not forced.

## Out of epoch

- runtime algorithm rewrites
- Smart Practice v13 or any named successor implementation
- scoring/UI/bank changes
- AI question generation
- cloud telemetry / user-data collection
- autonomous experimentation
- merging PR #1
- absorbing `integration/sc900-extractor-v1`
