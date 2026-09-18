# Package B Tranche 2 Verification Receipt

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE2-IMPLEMENTATION-001`  
**Design head:** `6380ec57ee95ade8eaaef827b96ada721bbe2778`  
**Implementation branch:** `implementation/sc900-content-revision-equivalence-migration-B-tranche2-001`  
**Revision edge:** `sc900_bank_v8_length_rebalanced_t1.json` → `sc900_bank_v8_length_rebalanced_t2.json`

## 1. Exact identities

| Artifact | SHA-256 / fingerprint |
| --- | --- |
| T1 source bank file | `45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8` |
| T1 source content fingerprint | `e0b4394b6faa8d0f9053291521b2dd83983e84990f1a169a25ab745694a7aabb` |
| T2 candidate bank file | `9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800` |
| T2 candidate content fingerprint | `34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b` |
| T2 manifest payload | `2f04ae1d2d22bdea1a8b96d470691700d59ea119bf34fb02d686d423b93bc571` |
| Production `sc900_bank_v8_final.json` | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Production EXE | `9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558` |

A temp-directory rebuild from the same T1 source and semantic review reproduced the T2 bank hash, content fingerprint, and manifest payload hash.

## 2. Queue dispositions

- Queue size: **50**
- EDIT: **49**
- SKIP: **1** (`sc900_mlc_q046`)
- T1 SKIP IDs were not re-queued or edited.
- T1 EDIT residuals were not folded into the primary T2 queue.

Carried-forward T1 BOTH residuals remain visible for a later pass and are not counted as two items:

| ID | Remaining gap | Status |
| --- | ---: | --- |
| `sc900_mlc_q109` | 1 | T1 EDIT residual; cheap later candidate |
| `sc900_mlc_q177` | 10 | T1 EDIT residual |
| `sc900_mlc_q134` | 16 | T1 EDIT residual |

Exclusion from the T2 primary queue is not a permanent rejection.

## 3. Leakage metrics versus T1

Analyzable population **449 / 454**. Audit skipped IDs unchanged: `sc900_mlc_q148`, `q202`, `q214`, `q285`, `q289`.

| Metric | T1 | T2 | Delta |
| --- | ---: | ---: | ---: |
| Strict-longest | 287 / 449 = 63.92% | 270 / 449 = 60.13% | **-17** |
| Unique-longest | 287 / 431 = 66.59% | 270 / 428 = 63.08% | **-17 successes** |
| Strict-shortest | 47 / 449 = 10.47% | 47 / 449 = 10.47% | 0 |
| Unique-shortest | 47 / 425 = 11.06% | 47 / 423 = 11.11% | 0 successes |

Correct-letter distribution is unchanged at A 106, B 114, C 116, D 113.

Per-domain strict-longest:

| Domain | T1 | T2 |
| --- | ---: | ---: |
| microsoft_security_solutions | 108 / 163 = 66.26% | 102 / 163 = 62.58% |
| microsoft_entra | 81 / 125 = 64.80% | 73 / 125 = 58.40% |
| microsoft_compliance_solutions | 66 / 102 = 64.71% | 64 / 102 = 62.75% |
| security_compliance_identity | 32 / 59 = 54.24% | 31 / 59 = 52.54% |

Maximum domain rate moved from security 66.26% to compliance 62.75%. No domain is under 45%.

Independent `tools.audit_answer_length` recomputation matched the T2 candidate metrics artifact on strict/unique longest and shortest, letter counts, and skipped IDs.

## 4. Edit yield and distractor growth

- EDIT yield: 49 reviewed changes, 17 strict-longest crossings
- CORRECT_ONLY edits: 0 (0 crossings)
- DISTRACTOR_ONLY edits: 6 (4 crossings)
- BOTH edits: 43 (13 crossings)
- Max-distractor growth: max **39**, mean **19.37**
- Per-letter distractor growth stayed at or below the prior 27–49 crossing band except where a nearby product's actual job was named; the largest per-letter growth is **+48** on `sc900_mlc_q125` A (Defender XDR unified-incident role)
- No correct choice was lengthened
- Cosmetic padding was not used; quality override controlled `sc900_mlc_q046` SKIP

Large-growth crossings and near-crossings are evidenced in `14-PACKAGE-B-TRANCHE2-SEMANTIC-REVIEW.json` with original length, revised length, delta, and the discriminative-value note. A metric crossing alone was not treated as acceptance.

The T2 two-sided preference is a tranche-local tactic. It remains subordinate to the parent forbidden-technique rules.

## 5. Admission and continuity

| Gate | Result |
| --- | --- |
| Real T1→T2 admission | PASS; 49 edges; registry `{}` |
| Closed-world changed-edge agreement | actual changed IDs == manifest EDIT set |
| Semantic invariants | prompt, IDs, correct mapping, objective, domain, topics, tier, eligibility, type unchanged |
| SKIP invariant | `sc900_mlc_q046` byte-identical |
| Receipt binding | each receipt hash binds to source/candidate fingerprints |
| Progress continuity | APPLIED; IDs, seen/correct/confidence/counters preserved; lineage written |
| Session continuity | APPLIED from T1-bound snapshot; edited unanswered selections cleared; history preserved |
| Idempotence | progress already-applied; session rebuild from the same T1 snapshot is identical |
| Tamper rejection | `SEMANTIC_REVIEW_HASH_MISMATCH` |
| Missing receipt | `SEMANTIC_REVIEW_MISSING` |
| Missing Learn authority | `AUTHORITY_EVIDENCE_MISSING` |
| Wrong T2 hash | `TARGET_BANK_FILE_HASH_MISMATCH` before migration |
| Wrong T1 hash | `SOURCE_BANK_FILE_HASH_MISMATCH` before migration |
| Non-choice drift | `PROMPT_CHANGED` |
| Unresolved queue | builder fail-closed; no candidate write |
| Registry | `AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}` |
| Runtime bank | `sc900_bank_v8_final.json` |

## 6. Validation

| Check | Result |
| --- | --- |
| `tests.test_package_b_tranche2` | PASS (36) |
| Package A + T1 + T2 + audit tests | PASS (191) |
| Identity/session wall | PASS (88) |
| `unittest discover -s tests` | PASS (1108) |
| `tools.lint_bank` T1 and T2 | PASS with the pre-existing C-streak warning on Q394–Q399 |
| mypy | PASS (32 files) |
| ruff/black on T2 builder, T2 tests, quality-target update | PASS |
| `tools.run_quality_checks` | FAIL on **pre-existing** ruff I001 in `answer_length_audit.py` and `tools/build_package_b_tranche1.py`; not repaired |

## 7. Closure boundary

```text
PACKAGE_B_TARGET_REACHED = NO
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T2 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
T3_AUTHORIZED = NO
PACKAGE_C_STARTED = NO
PRODUCTION_ACTIVATION = NO
MERGE_AUTHORIZED = NO
REGISTRY = {}
RUNTIME_BANK = sc900_bank_v8_final.json
```

T2 improved strict-longest from 63.92% to 60.13% and did not complete Package B. Later-tranche design is required.
