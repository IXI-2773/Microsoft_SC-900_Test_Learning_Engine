# 06 — Rehearsal verification

Recorded against rehearsal stack HEAD `0e4d3ce71d885347b8d3dee10be7633ad146a67c` (tree identical to PR #24). Documentation files in this directory were added after this run. Post-commit read-only verification is reported in the operator return and must not amend this file.

## Bank SHA

| Bank | Path | SHA-256 | Count |
| --- | --- | --- | --- |
| Frozen candidate | `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json` | `8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254` | 454 |
| Default launch | `sc900_bank_v8_baseline.json` | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` | 8 |

```text
DEFAULT_BANK_SHA_REHEARSAL = 60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426
DEFAULT_BANK_CHANGED = NO
FINAL_BANK_ACTIVATED = NO
```

Content fingerprints (identity layer, not file SHA):

| Bank | `bank_content_fingerprint` |
| --- | --- |
| Frozen 454 | `058053324cbf1928759b6e97147dd0e47000ec34ff93dcc25477f3c7909b4793` |
| Default 8 | `a59a0c07132b8f31fea453d8d331f1bbc6415ddca5d2854365591928e69cda3a` |

## Suites

Command family: `python -m unittest` (discover where noted). Zero failures, zero errors.

| Suite | Command | Result |
| --- | --- | --- |
| Final-bank runtime | `python -m unittest tests.test_sc900_final_bank_runtime` | PASS **8** tests, 0.046s |
| BACKLOG-1 | `discover -s tests -p test_backlog1*.py` | PASS **83** tests, 0.056s |
| BACKLOG-2 | `discover -s tests -p test_backlog2*.py` | PASS **47** tests, 3.942s |
| BACKLOG-3 | `discover -s tests -p test_backlog3*.py` | PASS **38** tests, 0.043s |
| Gate-3 CAND | `discover -s tests -p test_cand01r3*.py` | PASS **63** tests, 0.085s |
| Phase-3 | `discover -s tests -p test_sc900_phase3*.py` | PASS **79** tests, 11.264s |
| Microsoft corpus | `python -m unittest tests.test_sc900_microsoft_corpus` | PASS **16** tests, 0.249s |
| Full suite | `python -m unittest discover -s tests` | PASS **851** tests, 53.777s |
| Quality gates | `python -m tools.run_quality_checks` | PASS (ruff, black `--check`, mypy on quality targets) |
| Default-bank lint | `python -m tools.lint_bank` | PASS (8 questions) |
| Final-bank lint | `python -m tools.lint_bank --bank content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json --expected-count 454 --allow-warnings` | PASS (454 questions; 1 non-failing warning: C streak Q394–Q399) |
| Installation | `python -m tools.verify_installation` | PASS |

Gate-3 discover matched only the four Gate-3 test modules. PR #13 protocol test modules were not present and were not executed.

Expected warnings during BACKLOG-1/full-suite (fail-closed fixtures): quarantine of invalid session JSON, ambiguous legacy progress rejection, simulated disk-full backup failure. These are test-owned, not product failures.

## Tree assurance (stack HEAD)

| Check | Result |
| --- | --- |
| PR #24 files present | YES (tree identical to `fdec8ea`) |
| Current-main cleanup preserved | YES (ephemeral runner workflows absent) |
| PR #13-only artifacts absent | YES |
| PR #13 commit ancestry absent | YES |
| `EPHEMERAL_RUNNERS_RESURRECTED` | NO |

## Protected refs (verified during rehearsal, before documentation commit)

| Ref | Object |
| --- | --- |
| `recovery/publish-exact-history/sc900-v8-20260910` | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` |
| `recovery/publish-sc900-v8-exact-history` | `bbc3bd900b73bde89151dc51706ad62fc69e8196` |
| `sc900-v8.0.0-baseline` tag object | `9c80be5b20e652dc2eb86621dfdf7c32baa06528` |
| peeled tag commit | `fed4d4a44591ca93fe8428bc3ca02ec66a12f715` |

```text
PROTECTED_REFS_UNCHANGED = YES
```
