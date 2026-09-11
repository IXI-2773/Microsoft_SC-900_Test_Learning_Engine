# SC-900 v8 Baseline Plan Amendment

This amendment refines the approved implementation plan after direct inspection of additional v8 surfaces. It does not change the approved architecture.

## 1. Rebrand `.gitignore`

The source `.gitignore` explicitly ignores `SecurityTestingEngine.exe`. During the SC-900 transplant, replace that entry with `SC900TestLearningEngine.exe`. Treat `.gitignore` as a copy-then-modify file rather than an unchanged copy.

## 2. Do not present a practice percentage as the Microsoft passing score

`app_game_mixin.py` currently uses `PASS_SCORE_THRESHOLD = 70.0` and learner-facing strings such as `Pass line crossed` and `Pass score reached`. Preserve the numerical 70% gamification trigger for baseline behavioral stability, but rebrand it as an internal practice target rather than implying that 70% accuracy is Microsoft's scaled SC-900 passing score.

Use, directly or equivalently:

```python
PRACTICE_TARGET_THRESHOLD = 70.0
PASS_SCORE_THRESHOLD = PRACTICE_TARGET_THRESHOLD  # compatibility alias during v8 baseline
```

Learner-facing replacements:

- `Pass line crossed` -> `Practice target reached`
- `Pass score reached` -> `Practice target reached`
- `Keep it above 70` may remain only when clearly labeled as the app's practice target.

Add a regression test that fails if `app_game_mixin.py` contains learner-facing `Pass line crossed` or `Pass score reached` text after conversion.

The analytics `Pass predictor` remains an internal readiness model expressed as a percentage and is not converted into a Microsoft scaled exam score in this baseline.

## 3. Dedicated release tests own packaging behavior

The large `tests/test_security_testing_engine.py` contains an older duplicate release-packager fixture tied to `SecurityTestingEngine.exe`. Remove that duplicate method during the SC-900 conversion and retain/adapt the dedicated `tests/test_release_tools.py` coverage instead. This reduces duplicate certification-specific fixtures without reducing the release invariant coverage.

## 4. Isolation execution note

Because this chat runtime cannot clone GitHub through the local container network, implementation may use the isolated `implementation/sc900-v8-baseline` GitHub branch and a temporary GitHub Actions migration harness. The harness must not modify `main`; it may push the implementation branch only after its staged tests and verification succeed. Temporary bootstrap workflow/script files should be removed from the final baseline unless they provide ongoing product value.
