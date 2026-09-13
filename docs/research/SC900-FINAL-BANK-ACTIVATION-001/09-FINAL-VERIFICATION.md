# Final verification

## Targeted suites

Covered: activation contract, SC-900 contract, Exam-tier runtime, final-bank runtime, Microsoft corpus, question-bank loading, session migration/resume, BACKLOG-1, BACKLOG-2, BACKLOG-3, Gate-3 CAND, Phase-3, engine regressions, release/build contract, installation verification.

Full repository suite:

```
python -m unittest discover -s tests -q
```

`Ran 915 tests in 50.151s` — `OK` (0 failures, 0 errors). Includes 23 warning-governance tests.

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
python tools/lint_bank.py
```

`STANDARD_ACTIVE_LINT = PASS`

The ordinary production command now encodes the governed warning policy. It does **not** claim the bank is warning-free.

| Field | Value |
| --- | --- |
| `ACTIVE_BANK_WARNING_COUNT` | 1 |
| `KNOWN_FROZEN_WARNING_COUNT` | 1 |
| `UNEXPECTED_WARNING_COUNT` | 0 |
| `WARNING_POLICY_BOUND_TO_ACTIVE_SHA` | YES |
| Bound filename | `sc900_bank_v8_final.json` |
| Bound SHA-256 | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Exact frozen warning | `Repeated answer-pattern bias` / `C streak on Q394-Q399 (6 in a row)` |

`--allow-warnings` remains a diagnostic override only. Production acceptance requires `EXPECTED_WARNING_SET == ACTUAL_WARNING_SET` for that exact frozen SHA. Missing, extra, substituted, or SHA-mismatched warnings fail closed.

```
python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings
```

Diagnostic PASS — same 454-question bank, same one frozen warning reported, not used as the production gate.

Canonical calibrated artifact remains the byte-identical source of the active runtime copy.

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

`SMOKE_WARNING_GATE = PASS` — release smoke uses the same production warning authority as `python tools/lint_bank.py`.

`POSTMERGE_MAIN_COMMAND_SEQUENCE = PASS` after the warning-gate repair.

`PACKAGING_CONTRACT_VERIFIED = YES` — resource tuple, release tests, and archive listing include `sc900_bank_v8_final.json`. Warning-gate packaging rehearsal rebuilt the Windows one-file exe; `release_manifest.json` recorded 454 questions and bank SHA `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`; static smoke passed the exact frozen warning set.

`PACKAGED_BINARY_EXECUTION_VERIFIED = NO` — the windowed GUI exe was built and archive-listed, not interactively launched.

## Activation flags

| Flag | Value |
| --- | --- |
| FINAL_BANK_ACTIVATION_REHEARSAL | PASS after remaining packaging/self-mutation gates |
| FINAL_BANK_ACTIVATED_ON_BRANCH | YES |
| FINAL_BANK_ACTIVATED_ON_MAIN | NO |
| ACTIVATION_PR_MERGED | NO |
