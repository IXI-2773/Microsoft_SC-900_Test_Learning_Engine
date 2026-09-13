# Release and installation contract

## Count and filename authority

| Consumer | Before | After |
| --- | --- | --- |
| `cert_profile_sc900.json` `runtime_bank` | `sc900_bank_v8_baseline.json` | `sc900_bank_v8_final.json` |
| `runtime_bank_question_count` | absent | `454` |
| `placeholder_bank_question_count` | `8` used as implied production size | `8` historical only |
| `cert_config.RUNTIME_BANK_QUESTION_COUNT` | absent | `454` |
| `tools/build_release.py` `EXPECTED_QUESTION_COUNT` | literal `8` | `RUNTIME_BANK_QUESTION_COUNT` |
| `tools/verify_installation.py` | literal `8` | `RUNTIME_BANK_QUESTION_COUNT` |
| `tools/lint_bank.py` default expected count | literal `8` | `RUNTIME_BANK_QUESTION_COUNT` |
| `tools/smoke_test.py` | 8-question zero-warning gate | `RUNTIME_BANK_QUESTION_COUNT`; issues still fail; the known frozen warning is not a release blocker |

## Release manifest fields

`build_release.py` still writes:

- `question_bank_filename` from `BANK_FILE.name` (`sc900_bank_v8_final.json`)
- `question_bank_sha256` from a SHA-256 of that file
- `expected_bank_count` from `EXPECTED_QUESTION_COUNT` (`454`)

Expected active SHA-256:

`177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`

A live `release_manifest.json` is produced only when a built `dist/SC900TestLearningEngine.exe` exists. This rehearsal verified the generator contract, not a committed release folder.

## Installation verification

`python -m tools.verify_installation`

Result: `SC-900 installation verification passed.`

Checks now include:

- configured runtime bank exists and loads
- question count matches `RUNTIME_BANK_QUESTION_COUNT`
- `app.DEFAULT_BANK` matches configured bank
- SC-900 identity remains correct
- historical baseline file still exists
- legacy Security+ terms remain absent from runtime modules

`RELEASE_CONTRACT_RECONCILED = YES`

`INSTALLATION_CONTRACT_RECONCILED = YES`
