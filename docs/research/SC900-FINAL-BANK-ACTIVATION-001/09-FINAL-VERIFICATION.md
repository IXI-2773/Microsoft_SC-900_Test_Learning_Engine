# Final verification

## Targeted suites

Covered: activation contract, SC-900 contract, Exam-tier runtime, final-bank runtime, Microsoft corpus, question-bank loading, session migration/resume, BACKLOG-1, BACKLOG-2, BACKLOG-3, Gate-3 CAND, Phase-3, engine regressions, release/build contract, installation verification.

Full repository suite:

```
python -m unittest discover -s tests -q
```

`Ran 892 tests in 52.053s` — `OK` (0 failures, 0 errors)

## Quality

```
python -m tools.run_quality_checks
```

PASS (`ruff`, `black --check`, `mypy` on repository quality targets)

```
python -m tools.lint_bank --bank sc900_bank_v8_baseline.json --expected-count 8
```

PASS — historical baseline, 8 questions, 0 issues, 0 warnings

```
python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings
```

PASS — 454 questions, 0 issues, 1 known frozen warning (`C streak on Q394-Q399`)

```
python -m tools.lint_bank
```

FAIL as a fail-on-warnings diagnostic against the now-default 454 bank: the same known frozen warning. This is not a content-change defect; the calibrated artifact was accepted with that warning. The governed 454 gate is `--allow-warnings`.

Canonical calibrated artifact was linted as the byte-identical source of the active runtime copy.

```
python -m tools.verify_installation
```

PASS

## Content freeze

Canonical SHA before = canonical SHA after = active runtime SHA =

`177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`

Baseline SHA before = baseline SHA after =

`60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`

## Scientific / recovery boundary

| Gate | Result |
| --- | --- |
| PR #13 | OPEN, unmerged, head `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` |
| PR13_IMPORTED | NO |
| PR13_MODIFIED | NO |
| PR13_MERGED | NO |
| DAY1_STARTED | NO |
| Protected refs | unchanged; see `09` companion values in the package report |

`PACKAGING_CONTRACT_VERIFIED = YES` — resource tuple, release tests, and isolated archive listing all include `sc900_bank_v8_final.json`.

`PACKAGED_BINARY_EXECUTION_VERIFIED = NO` — windowed GUI exe was built in a temp directory and listed, not interactively launched.

## Activation flags

| Flag | Value |
| --- | --- |
| FINAL_BANK_ACTIVATION_REHEARSAL | PASS after remaining packaging/self-mutation gates |
| FINAL_BANK_ACTIVATED_ON_BRANCH | YES |
| FINAL_BANK_ACTIVATED_ON_MAIN | NO |
| ACTIVATION_PR_MERGED | NO |
