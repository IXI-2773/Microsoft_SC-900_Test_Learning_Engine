# Rollback plan

The activation commit is an ordinary forward commit. Rollback is a normal revert. Do not rewrite history, force-push, or move recovery refs.

## Concept

```
git revert <ACTIVATION_COMMIT_SHA>
```

Expected result:

- `cert_profile_sc900.json` `runtime_bank` returns to `sc900_bank_v8_baseline.json`
- production count authority introduced by activation is removed or no longer selected
- `sc900_bank_v8_baseline.json` was never modified, so it is immediately valid as the runtime bank
- PR #26 Exam-tier runtime code remains published
- canonical 454-question compiled artifact remains preserved
- `sc900_bank_v8_final.json` may remain as an unused file or be removed by the revert; it is not historical baseline evidence
- recovery refs and `sc900-v8.0.0-baseline` do not move

## What rollback must not do

- Do not `git reset --hard` published main
- Do not force-push
- Do not restore baseline by mutating the 454-question files
- Do not merge or retarget PR #13
- Do not delete `sc900_bank_v8_baseline.json`

## Verification after revert

1. `cert_config.QUESTION_BANK_FILENAME == sc900_bank_v8_baseline.json`
2. Baseline SHA-256 is `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`
3. Canonical calibrated SHA-256 remains `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`
4. Protected refs unchanged
5. PR #13 still OPEN at `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb`
