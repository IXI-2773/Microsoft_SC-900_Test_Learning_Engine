# Final verification

## Bank hashes

| Bank | SHA-256 before | SHA-256 after |
| --- | --- | --- |
| Calibrated compiled bank | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` | unchanged |
| Default `sc900_bank_v8_baseline.json` | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` | unchanged |

CALIBRATED_BANK_CONTENT_CHANGED = NO  
DEFAULT_BANK_CHANGED = NO  
FINAL_BANK_ACTIVATED = NO

## Focused suites

| Suite | Result |
| --- | --- |
| Exam-tier reconstruction | 11 tests, OK |
| Exam calibration | PASS |
| Final-bank runtime | PASS |
| Microsoft corpus | PASS |
| BACKLOG-1 | PASS |
| BACKLOG-2 | PASS |
| BACKLOG-3 | PASS |
| Gate-3 CAND `test_cand01r3*.py` | 63 tests, OK |
| Phase-3 `test_sc900_phase3*.py` | 79 tests, OK |
| Engine regression | 423 tests, OK |

First focused combined batch (reconstruction, calibration, final-bank, corpus, BACKLOG-1/2/3): 212 tests, OK.

## Complete suite

```text
python -m unittest discover -s tests
Ran 871 tests in 52.201s
OK
```

0 failures, 0 errors. Governed display/environment-dependent skips remain acceptable under repository policy.

## Quality

| Check | Result |
| --- | --- |
| `python -m tools.run_quality_checks` | PASS |
| `python -m tools.lint_bank` | PASS, 8 questions |
| calibrated `lint_bank --allow-warnings` | PASS, 454 questions, 1 existing warning |
| `python -m tools.verify_installation` | PASS |
| ruff | PASS |
| black --check | PASS |
| mypy | PASS, 29 source files |

## Scientific boundary

| Control | Result |
| --- | --- |
| PR #13 remote | OPEN, UNMERGED, head `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` |
| PR13_IMPORTED | NO |
| PR13_MODIFIED | NO |
| PR13_MERGED | NO |
| DAY1_STARTED | NO |
| recovery/publish-exact-history/sc900-v8-20260910 | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` |
| recovery/publish-sc900-v8-exact-history | `bbc3bd900b73bde89151dc51706ad62fc69e8196` |
| tag sc900-v8.0.0-baseline | `9c80be5b20e652dc2eb86621dfdf7c32baa06528` |

No force push. Existing local clones and unpublished PR #13 tips were not reset, rebased, deleted, or used as this package's base.
