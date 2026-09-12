# 06 — Final verification

## Before / after (filled at verification)

See `07-RELEASE-READINESS.md` for HEAD and worktree hashes recorded after the documentation commits.

## Suites

| Suite | Result |
| --- | --- |
| Focused final-bank runtime | PASS (`tests/test_sc900_final_bank_runtime.py`, 8 tests) |
| Taxonomy | PASS |
| Microsoft corpus | PASS |
| BACKLOG-1 | PASS |
| BACKLOG-2 | PASS |
| BACKLOG-3 | PASS (168 backlog tests combined) |
| Gate-3 CAND | PASS (63 tests) |
| Phase-3 | PASS (79 tests) |
| Full `python -m unittest discover -s tests -v` | PASS **851 tests**, 0 failures, 0 errors |
| `python -m tools.run_quality_checks` | PASS (ruff, black --check, mypy on quality targets) |
| `python -m tools.verify_installation` | PASS |
| DEFAULT_BANK_LINT | PASS (8 questions) |
| FINAL_BANK_LINT | PASS (454 questions; 1 non-failing warning: C streak Q394–Q399) |

Default launch bank SHA-256 unchanged: `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`

Frozen candidate SHA-256: `8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254`
