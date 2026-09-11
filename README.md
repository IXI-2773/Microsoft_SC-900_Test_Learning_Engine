
# Microsoft SC-900 Test Learning Engine v8

This repository is the SC-900 specialization of the frozen v8 learning engine.

The reusable application, analytics, persistence, Smart Practice, session, and UI subsystems are migrated from the pinned v8 source revision recorded in `docs/baseline/source-v8-contract.json`. Certification-specific identity and runtime bank selection are isolated in `cert_profile_sc900.json` and `cert_config.py`.

## Baseline scope

`SC900_V8_BASELINE` intentionally contains only eight original placeholder questions: two for each SC-900 skills domain. Large-scale question ingestion happens only after this baseline passes regression, quality, Windows build, and smoke-test gates.

The engine's readiness percentage is an internal study heuristic. It is not a conversion to Microsoft's reported scaled exam score.

## Run from source

```powershell
python app.py
```

## Verify

```powershell
python -m unittest discover -s tests -v
python tools/lint_bank.py
python tools/verify_installation.py
python tools/run_quality_checks.py
```

## Windows release

The verified baseline executable is packaged as `release/SC900TestLearningEngine/SC900TestLearningEngine.exe`.
