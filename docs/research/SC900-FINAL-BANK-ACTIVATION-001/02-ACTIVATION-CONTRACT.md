# Activation contract

## Runtime pointer

| Field | Before | After |
| --- | --- | --- |
| `cert_profile_sc900.json` `runtime_bank` | `sc900_bank_v8_baseline.json` | `sc900_bank_v8_final.json` |
| `cert_config.QUESTION_BANK_FILENAME` | baseline filename | `sc900_bank_v8_final.json` |
| `app.DEFAULT_BANK` | baseline file | `sc900_bank_v8_final.json` |
| Active count | 8 | 454 |
| Active SHA-256 | baseline | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |

`RUNTIME_BANK_POINTER_CHANGED = YES`

`BASELINE_BANK_CONTENT_CHANGED = NO`

`CANONICAL_CALIBRATED_BANK_CONTENT_CHANGED = NO`

## Count authority

Production count is one explicit profile field:

```json
"runtime_bank_question_count": 454
```

`cert_config.RUNTIME_BANK_QUESTION_COUNT` is the implementation consumer. Release, installation verification, lint-of-launch-bank, and smoke tests derive expected active count from that field.

`placeholder_bank_question_count` remains `8` as historical/baseline metadata. It is not used by production validation.

## Byte equivalence

Preferred invariant, verified:

```
CANONICAL_CALIBRATED_BANK_BYTES == ACTIVE_RUNTIME_BANK_BYTES
```

The root-level runtime file is a byte-for-byte copy of the frozen compiled candidate. No transform, pretty-print, reorder, or recompile was performed.

A root-level copy was used because packaging and `QUESTION_BANK_FILENAME` resolution already assume a repository-root runtime bank name. Pointing the packaged app at the nested compiled path would have required a packaging-path redesign.

## Mode contracts after activation

| Mode | Pool | Stretch |
| --- | --- | --- |
| Ordinary Exam (new session) | 431 | excluded |
| Practice | 454 | available |
| Smart Practice candidate pool | 454 | available |

PR #26 already owns Exam eligibility. Activation consumes `exam_runtime_eligible` / `filter_new_exam_pool`; it does not add weighting, quotas, sliders, or sampling changes.

## Historical baseline

`sc900_bank_v8_baseline.json` remains in the repository and in the packaged resource set as historical/recovery evidence. It is no longer the production runtime bank.
