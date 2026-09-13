# Pre-activation state

## Remote authority

| Ref | SHA | Notes |
| --- | --- | --- |
| `origin/main` | `2820cd322bce8a0d94008622c2189be17f3a1c23` | PR #26 merge; matched expected current main |
| PR #26 runtime implementation | `5cfd689d5c7a721927febd34501d265c4afb8756` | already on main |
| PR #13 head | `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` | OPEN, unmerged; not touched |

Main had not advanced beyond the expected SHA. No reset was required.

## Runtime before activation

| Item | Value |
| --- | --- |
| `runtime_bank` | `sc900_bank_v8_baseline.json` |
| Active/default count | 8 |
| `placeholder_bank_question_count` | 8 |
| `tools/build_release.py` `EXPECTED_QUESTION_COUNT` | 8 |
| `tools/verify_installation.py` | failed unless runtime count was exactly 8 |
| `tools/lint_bank.py` default expected count | hardcoded 8 |
| `tools/smoke_test.py` | 8-question clean-bank gate, including zero warnings |
| `release_resources.py` bundled bank | `sc900_bank_v8_baseline.json` only |

## Frozen artifacts before activation

| Artifact | SHA-256 |
| --- | --- |
| Canonical calibrated bank | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Historical baseline bank | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

Canonical bank was already runtime-valid as a candidate: 454 questions, Core 301, Applied 130, Stretch 23, ordinary Exam eligible 431. It was not the active runtime pointer.

## Protected refs before activation

| Ref | SHA |
| --- | --- |
| `recovery/publish-exact-history/sc900-v8-20260910` | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` |
| `recovery/publish-sc900-v8-exact-history` | `bbc3bd900b73bde89151dc51706ad62fc69e8196` |
| tag `sc900-v8.0.0-baseline` | `9c80be5b20e652dc2eb86621dfdf7c32baa06528` |
