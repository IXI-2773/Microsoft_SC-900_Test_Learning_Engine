# Runtime bank equivalence

## Canonical calibrated artifact

Path: `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json`

| Gate | SHA-256 |
| --- | --- |
| CANONICAL_CALIBRATED_SHA_BEFORE | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| CANONICAL_CALIBRATED_SHA_AFTER | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |

`CANONICAL_CALIBRATED_BANK_CONTENT_CHANGED = NO`

The compiled candidate was not mutated, regenerated, or rewritten.

## Active runtime bank

Path: `sc900_bank_v8_final.json`

Created by `Path.write_bytes(canonical.read_bytes())`.

| Gate | Value |
| --- | --- |
| ACTIVE_RUNTIME_BANK_SHA | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Byte equality with canonical | YES |
| Size | 1407865 bytes |

`ACTIVE_BANK_BYTE_EQUIVALENCE = YES`

## Historical baseline

Path: `sc900_bank_v8_baseline.json`

| Gate | SHA-256 |
| --- | --- |
| BASELINE_BANK_SHA_BEFORE | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |
| BASELINE_BANK_SHA_AFTER | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |

`BASELINE_BANK_CONTENT_CHANGED = NO`

## Pointer

| Gate | Value |
| --- | --- |
| RUNTIME_BANK_POINTER_BEFORE | `sc900_bank_v8_baseline.json` |
| RUNTIME_BANK_POINTER_AFTER | `sc900_bank_v8_final.json` |
| RUNTIME_BANK_POINTER_CHANGED | YES |
