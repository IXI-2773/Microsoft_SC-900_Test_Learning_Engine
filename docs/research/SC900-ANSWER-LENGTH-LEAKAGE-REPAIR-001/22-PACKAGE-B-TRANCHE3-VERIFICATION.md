# Package B Tranche 3 Verification Receipt

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE3-IMPLEMENTATION-001`  
**Design head:** `64dd27a71da03e8ea5a2fa2f86e1820465efe02a`  
**Implementation branch:** `implementation/sc900-content-revision-equivalence-migration-B-tranche3-001`  
**Start head:** `56739154999795434abe761e4032d465ec967f20`  
**Revision edge:** `sc900_bank_v8_length_rebalanced_t2.json` → `sc900_bank_v8_length_rebalanced_t3.json`

## 1. Exact identities

| Artifact | SHA-256 / fingerprint |
| --- | --- |
| T2 source bank file | `c53ba19ee26992643969d546a73da5aa8396041ebe4e138f6b30db637756aa65` |
| T2 source content fingerprint | `34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b` |
| T3 candidate bank file | `0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd` |
| T3 candidate content fingerprint | `83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2` |
| T3 manifest payload | `d89a6708b08f2afc5bfc3a30cbd4c5708b6022acbacdb3a91db360d12c18c2ea` |
| Production `sc900_bank_v8_final.json` | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Production EXE | `9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558` |

A temp-directory rebuild from the same T2 source and semantic review reproduced the T3 bank hash, content fingerprint, and manifest payload hash.

## 2. Queue dispositions

- Queue size: **36** (10 second-pass + 26 fresh yield-band)
- EDIT: **29**
- SKIP: **7** (`sc900_mlc_q288`, `q126`, `q109`, `q216`, `sc900_p3_q054`, `q295`, `q217`)
- Second-pass EDIT / SKIP / crossing: **3 / 7 / 3**
- Fresh EDIT / SKIP / crossing: **26 / 0 / 11**
- T1 SKIP IDs were not re-queued or edited.
- T2 SKIP `sc900_mlc_q046` was not re-queued or edited.

Second-pass SKIPs remain candidate-review closures, not permanent irreparability findings. `sc900_mlc_q109` stays closed because expanding leftover label-like C/D would create a second defensible reading of the assigned-standard list.

## 3. Leakage metrics versus T2

Analyzable population **449 / 454**. Audit skipped IDs unchanged: `sc900_mlc_q148`, `q202`, `q214`, `q285`, `q289`.

| Metric | T2 | T3 | Delta |
| --- | ---: | ---: | ---: |
| Strict-longest | 270 / 449 = 60.13% | 256 / 449 = 57.02% | **-14** |
| Unique-longest | 270 / 428 = 63.08% | 256 / 425 = 60.24% | **-14 successes** |
| Strict-shortest | 47 / 449 = 10.47% | 47 / 449 = 10.47% | 0 |
| Unique-shortest | 47 / 423 = 11.11% | 47 / 421 = 11.16% | 0 successes |

Correct-letter distribution is unchanged at A 106, B 114, C 116, D 113.

Per-domain strict-longest:

| Domain | T2 | T3 |
| --- | ---: | ---: |
| microsoft_security_solutions | 102 / 163 = 62.58% | 98 / 163 = 60.12% |
| microsoft_compliance_solutions | 64 / 102 = 62.75% | 59 / 102 = 57.84% |
| microsoft_entra | 73 / 125 = 58.40% | 70 / 125 = 56.00% |
| security_compliance_identity | 31 / 59 = 52.54% | 29 / 59 = 49.15% |

Maximum domain rate moved from compliance 62.75% to security 60.12%. No domain is under 45%.

Independent `tools.audit_answer_length` recomputation matched the T3 candidate metrics artifact on strict/unique longest and shortest, letter counts, skipped IDs, and domain rates.

## 4. Edit yield and distractor growth

- EDIT yield: 29 reviewed changes, 14 strict-longest crossings (3 to tie, 11 to shorter)
- CORRECT_ONLY edits: 0 (0 crossings)
- DISTRACTOR_ONLY edits: 4 (4 crossings)
- BOTH edits: 25 (10 crossings)
- Max-distractor growth: max **37**, mean **11.59**
- Unique-longest was measured with strict-longest; both declined by 14 and neither is used as a T3 closure claim
- Cosmetic padding was not used; quality override controlled the seven second-pass SKIPs

Large per-option growth is leftover-label or short-phrase expansion into the named product's actual wrong-plane job, recorded in `20-PACKAGE-B-TRANCHE3-SEMANTIC-REVIEW.json` with before/after/delta for A–D and max-distractor. Notable extra-inspection items:

| ID | Trigger | Why it is not padding |
| --- | --- | --- |
| `sc900_p3_q097` C | +62 | SIEM distractor now names Sentinel log-analytics/detection, still wrong for Key Vault |
| `sc900_mlc_q279` C | +62 | leftover `Compliance Manager` label expanded into a false STP/DLP pairing |
| `sc900_mlc_q134` A | +47 | leftover `Azure Firewall` label now states network filtering |
| `sc900_mlc_q262` D | +45 | leftover Defender for Office 365 label now falsely claims one product covers both problems |
| `sc900_mlc_q124` A | +45 | WAF job named on a Key Vault question |
| `sc900_mlc_q138` D | +39 | Bastion private RDP/SSH job named on a CSPM question |
| `sc900_mlc_q282` A | +37 | Compliance Manager false ISO-certification claim made explicit |

A metric crossing alone was not treated as acceptance. Remaining non-crossing EDITs keep equivalent wording and are not padded to force the 10–20 design estimate.

## 5. Admission and continuity

| Gate | Result |
| --- | --- |
| Real T2→T3 admission | PASS; 29 edges; registry `{}` |
| Closed-world changed-edge agreement | actual changed IDs == manifest EDIT set |
| Semantic invariants | prompt, IDs, correct mapping, objective, domain, topics, tier, eligibility, type unchanged |
| SKIP invariant | all 7 T3 SKIPs byte-identical; all 8 prior T1/T2 SKIPs unchanged |
| Receipt binding | each receipt hash binds to source/candidate fingerprints |
| Progress continuity | APPLIED; IDs, seen/correct/confidence/counters preserved; lineage written |
| Session continuity | APPLIED from T2-bound snapshot; edited unanswered selections cleared; history preserved |
| Idempotence | progress already-applied; session rebuild from the same T2 snapshot is identical |
| Tamper rejection | `SEMANTIC_REVIEW_HASH_MISMATCH` |
| Missing receipt | `SEMANTIC_REVIEW_MISSING` |
| Missing Learn authority | `AUTHORITY_EVIDENCE_MISSING` |
| Wrong T3 hash | `TARGET_BANK_FILE_HASH_MISMATCH` before migration |
| Wrong T2 hash | `SOURCE_BANK_FILE_HASH_MISMATCH` before migration |
| Non-choice drift | `PROMPT_CHANGED` |
| Unresolved queue | builder fail-closed; no candidate write |
| Registry | `AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}` |
| Runtime bank | `sc900_bank_v8_final.json` |

## 6. Validation

| Check | Result |
| --- | --- |
| `tests.test_package_b_tranche3` | PASS (37) |
| Package A + T1 + T2 + T3 + audit tests | PASS (228) |
| Identity/session wall | PASS (82) |
| `unittest discover -s tests` | PASS (1145) |
| `tools.lint_bank` T2 and T3 | PASS with the pre-existing C-streak warning on Q394–Q399 |
| `tools.verify_installation` | PASS |
| mypy | PASS (32 files) |
| ruff/black on T3 builder, T3 tests, quality-target update | PASS |
| `tools.run_quality_checks` | FAIL on **pre-existing** ruff I001 in `answer_length_audit.py` and `tools/build_package_b_tranche1.py`; not repaired |

## 7. Closure boundary

```text
PACKAGE_B_TARGET_REACHED = NO
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T3 = NO
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
T4_AUTHORIZED = NO
PACKAGE_C_STARTED = NO
PRODUCTION_ACTIVATION = NO
MERGE_AUTHORIZED = NO
REGISTRY = {}
RUNTIME_BANK = sc900_bank_v8_final.json
```

T3 improved strict-longest from 60.13% to 57.02% and unique-longest from 63.08% to 60.24%. Package B remains open. T4 is likely required and is not authorized by this package.
