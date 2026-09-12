# 454-question classification

Machine-readable authority:

- `content/sc900/microsoft-learn-corpus/calibration/classification.json`
- `content/sc900/microsoft-learn-corpus/calibration/ledger.jsonl`
- Stage-1 measurements: `content/sc900/microsoft-learn-corpus/calibration/precalibration_measurements.json`

## Pre-calibration measurements

| Metric | Value |
| --- | --- |
| Approved items | 454 |
| Beginner / intermediate | 267 / 187 |
| Mean / median / p90 stem words | 18.7 / 20 / 28 |
| Multi-select | 5 |
| Negative-wording stems | 32 |
| Answer positions (single-select first letter in analytics) | A 111, B 114, C 116, D 113 |
| Serial-modulo match rate | 0.343 |
| Chi-square vs uniform | 0.506 |
| Predictable answer key | NO |

Stem styles before calibration: short_scenario 150, direct_concept 82, concept_distinction 69, capability_selection 61, misconception_correction 44, distinction_comparison 31, other remaining.

The reading load was already Fundamentals-like. Overdifficulty came from two-step pairing, claim-diagnosis wrappers, and cross-product joke distractors.

## Final classification

| Tier | Count | Share | Exam simulation |
| --- | --- | --- | --- |
| FUNDAMENTALS_CORE | 301 | 66.3% | eligible |
| FUNDAMENTALS_APPLIED | 130 | 28.6% | eligible |
| STRETCH | 23 | 5.1% | not eligible for ordinary Exam mode |

All 454 approved items received `exam_calibration_tier`, `reasoning_steps`, `exam_simulation_eligible`, and `calibration_version`. Empty `tested_decision` count remains 0. All 58 leaves remain covered.

Classification is not a mechanical word-count map. Short stems can be Stretch (stacked pairing). Longer stems can be Core (one decision). Explicit Stretch keepers are listed in `tools/sc900_calibration_rewrites.py`.
