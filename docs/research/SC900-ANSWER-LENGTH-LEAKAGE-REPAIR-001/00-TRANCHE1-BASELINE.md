# SC-900 Answer-Length Leakage Repair — Tranche 1 Baseline

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / TRANCHE1`  
**Authoritative main SHA:** `23d440b6976b9f6bbb3b77285bf0d11effc2513f`  
**Measurement branch SHA:** `3d4aaf7951900f4dbd8f0362d84f1b9ae854730d`  
**GitHub Actions run:** `35219213386` / PASS  

## Source authority

- Production bank: `sc900_bank_v8_final.json`
- Bank SHA-256: `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`
- Bank count: **454**
- Bank lint: **PASS** — 1 governed frozen warning, 0 unexpected warnings
- Installation verification: **PASS**
- `BANK_CONTENT_CHANGED = NO`

## Reproducibility

The audit was executed twice against the same exact bank:

```bash
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/sc900-answer-length-audit-1.json --markdown-out /tmp/sc900-answer-length-audit.md
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/sc900-answer-length-audit-2.json
cmp /tmp/sc900-answer-length-audit-1.json /tmp/sc900-answer-length-audit-2.json
```

Both JSON outputs were byte-identical with SHA-256 `7ba31b518395d6705538799c945c138c669e3e2d017d32efe781e1781e1fe732`.
Uploaded audit artifact ZIP digest: `sha256:ce299ce05858ba5604191ce0332b1c855023113f36c2dc2545bfb295dd1c00f2`.

## Overall baseline

| Metric | Result |
| --- | ---: |
| Analyzable single-answer questions | 449 |
| Strict-longest correct | 291 / 449 = 64.81% |
| Correct among longest | 303 / 449 = 67.48% |
| Unique-longest heuristic success | 291 / 431 = 67.52% |
| Strict-shortest correct | 47 / 449 = 10.47% |
| Unique-shortest heuristic success | 47 / 425 = 11.06% |
| Most-common answer-letter rate | 25.84% |
| Mean correct-answer length | 60.15 characters |
| Mean longest-distractor length | 41.21 characters |

The authoritative audit reproduces the previously observed baseline within tolerance: 449 analyzable questions, 64.81% strict-longest correct, and 67.52% unique-longest heuristic success.

## Correct-answer letter distribution

| Letter | Count | Rate |
| --- | ---: | ---: |
| A | 106 | 23.61% |
| B | 114 | 25.39% |
| C | 116 | 25.84% |
| D | 113 | 25.17% |

## Per-domain metrics

| Domain | N | Strict longest | Unique-longest heuristic | Strict shortest | Unique-shortest heuristic | Most-common letter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `microsoft_compliance_solutions` | 102 | 65.69% | 71.28% | 12.75% | 13.68% | 28.43% |
| `microsoft_entra` | 125 | 65.60% | 67.21% | 10.40% | 10.83% | 28.80% |
| `microsoft_security_solutions` | 163 | 67.48% | 69.18% | 8.59% | 9.21% | 30.06% |
| `security_compliance_identity` | 59 | 54.24% | 57.14% | 11.86% | 12.07% | 28.81% |

## Top 60 longest-answer leakage outliers

Ranked deterministically by relative gap descending, then absolute gap descending, then canonical question ID.

| # | Question ID | Q# | Domain | Key | Correct chars | Max distractor | Gap | Relative gap |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `sc900_mlc_q160` | 314 | `microsoft_compliance_solutions` | A | 108 | 18 | 90 | 83.33% |
| 2 | `sc900_mlc_q173` | 327 | `microsoft_compliance_solutions` | A | 96 | 21 | 75 | 78.12% |
| 3 | `sc900_mlc_q191` | 345 | `microsoft_compliance_solutions` | D | 102 | 23 | 79 | 77.45% |
| 4 | `sc900_mlc_q286` | 440 | `microsoft_compliance_solutions` | B | 99 | 23 | 76 | 76.77% |
| 5 | `sc900_mlc_q169` | 323 | `microsoft_compliance_solutions` | B | 109 | 28 | 81 | 74.31% |
| 6 | `sc900_p3_q043` | 112 | `microsoft_entra` | C | 124 | 32 | 92 | 74.19% |
| 7 | `sc900_mlc_q143` | 297 | `microsoft_security_solutions` | D | 81 | 21 | 60 | 74.07% |
| 8 | `sc900_mlc_q181` | 335 | `microsoft_compliance_solutions` | D | 77 | 20 | 57 | 74.03% |
| 9 | `sc900_mlc_q070` | 224 | `microsoft_entra` | A | 149 | 39 | 110 | 73.83% |
| 10 | `sc900_mlc_q105` | 259 | `microsoft_security_solutions` | D | 87 | 23 | 64 | 73.56% |
| 11 | `sc900_mlc_q183` | 337 | `microsoft_compliance_solutions` | A | 85 | 23 | 62 | 72.94% |
| 12 | `sc900_mlc_q177` | 331 | `security_compliance_identity` | D | 99 | 27 | 72 | 72.73% |
| 13 | `sc900_mlc_q154` | 308 | `microsoft_compliance_solutions` | D | 80 | 22 | 58 | 72.50% |
| 14 | `sc900_mlc_q116` | 270 | `microsoft_security_solutions` | D | 125 | 35 | 90 | 72.00% |
| 15 | `sc900_mlc_q184` | 338 | `microsoft_compliance_solutions` | A | 82 | 23 | 59 | 71.95% |
| 16 | `sc900_mlc_q218` | 372 | `microsoft_entra` | C | 67 | 19 | 48 | 71.64% |
| 17 | `sc900_mlc_q135` | 289 | `microsoft_security_solutions` | A | 81 | 23 | 58 | 71.60% |
| 18 | `sc900_p3_q091` | 147 | `security_compliance_identity` | C | 120 | 35 | 85 | 70.83% |
| 19 | `sc900_mlc_q085` | 239 | `microsoft_security_solutions` | C | 112 | 33 | 79 | 70.54% |
| 20 | `sc900_mlc_q192` | 346 | `microsoft_compliance_solutions` | B | 76 | 23 | 53 | 69.74% |
| 21 | `sc900_mlc_q134` | 288 | `microsoft_security_solutions` | B | 69 | 21 | 48 | 69.57% |
| 22 | `sc900_mlc_q086` | 240 | `microsoft_security_solutions` | A | 78 | 24 | 54 | 69.23% |
| 23 | `sc900_p2_q034` | 77 | `microsoft_security_solutions` | D | 111 | 35 | 76 | 68.47% |
| 24 | `sc900_mlc_q187` | 341 | `microsoft_compliance_solutions` | A | 81 | 26 | 55 | 67.90% |
| 25 | `sc900_mlc_q129` | 283 | `microsoft_security_solutions` | D | 102 | 33 | 69 | 67.65% |
| 26 | `sc900_mlc_q273` | 427 | `microsoft_security_solutions` | B | 102 | 33 | 69 | 67.65% |
| 27 | `sc900_mlc_q037` | 191 | `microsoft_entra` | D | 69 | 23 | 46 | 66.67% |
| 28 | `sc900_mlc_q179` | 333 | `security_compliance_identity` | C | 94 | 32 | 62 | 65.96% |
| 29 | `sc900_mlc_q170` | 324 | `microsoft_compliance_solutions` | C | 82 | 28 | 54 | 65.85% |
| 30 | `sc900_p3_q060` | 124 | `microsoft_compliance_solutions` | D | 73 | 25 | 48 | 65.75% |
| 31 | `sc900_mlc_q063` | 217 | `microsoft_entra` | B | 96 | 33 | 63 | 65.62% |
| 32 | `sc900_mlc_q127` | 281 | `microsoft_security_solutions` | C | 107 | 37 | 70 | 65.42% |
| 33 | `sc900_mlc_q253` | 407 | `microsoft_security_solutions` | A | 106 | 37 | 69 | 65.09% |
| 34 | `sc900_p2_q025` | 72 | `microsoft_security_solutions` | D | 111 | 39 | 72 | 64.86% |
| 35 | `sc900_mlc_q194` | 348 | `microsoft_compliance_solutions` | D | 71 | 25 | 46 | 64.79% |
| 36 | `sc900_p3_q095` | 151 | `microsoft_security_solutions` | C | 122 | 43 | 79 | 64.75% |
| 37 | `sc900_p3_q049` | 116 | `microsoft_compliance_solutions` | A | 87 | 31 | 56 | 64.37% |
| 38 | `sc900_mlc_q225` | 379 | `microsoft_entra` | D | 81 | 29 | 52 | 64.20% |
| 39 | `sc900_mlc_q099` | 253 | `microsoft_security_solutions` | B | 67 | 24 | 43 | 64.18% |
| 40 | `sc900_mlc_q079` | 233 | `microsoft_security_solutions` | B | 83 | 30 | 53 | 63.86% |
| 41 | `sc900_mlc_q075` | 229 | `microsoft_entra` | C | 60 | 22 | 38 | 63.33% |
| 42 | `sc900_p2_q029` | 73 | `microsoft_security_solutions` | A | 98 | 36 | 62 | 63.27% |
| 43 | `sc900_p3_q072` | 132 | `microsoft_entra` | D | 51 | 19 | 32 | 62.75% |
| 44 | `sc900_mlc_q290` | 444 | `microsoft_compliance_solutions` | B | 98 | 37 | 61 | 62.24% |
| 45 | `sc900_mlc_q161` | 315 | `microsoft_compliance_solutions` | A | 74 | 28 | 46 | 62.16% |
| 46 | `sc900_mlc_q115` | 269 | `microsoft_security_solutions` | C | 87 | 33 | 54 | 62.07% |
| 47 | `sc900_mlc_q155` | 309 | `microsoft_compliance_solutions` | D | 115 | 44 | 71 | 61.74% |
| 48 | `sc900_mlc_q109` | 263 | `microsoft_security_solutions` | A | 52 | 20 | 32 | 61.54% |
| 49 | `sc900_p3_q038` | 109 | `microsoft_compliance_solutions` | B | 123 | 48 | 75 | 60.98% |
| 50 | `sc900_mlc_q030` | 184 | `microsoft_entra` | A | 120 | 47 | 73 | 60.83% |
| 51 | `sc900_mlc_q132` | 286 | `microsoft_security_solutions` | B | 56 | 22 | 34 | 60.71% |
| 52 | `sc900_mlc_q125` | 279 | `microsoft_security_solutions` | B | 78 | 31 | 47 | 60.26% |
| 53 | `sc900_mlc_q102` | 256 | `microsoft_security_solutions` | A | 90 | 36 | 54 | 60.00% |
| 54 | `sc900_mlc_q084` | 238 | `microsoft_security_solutions` | D | 85 | 34 | 51 | 60.00% |
| 55 | `sc900_p3_q055` | 120 | `microsoft_security_solutions` | C | 127 | 51 | 76 | 59.84% |
| 56 | `sc900_p3_q039` | 110 | `microsoft_compliance_solutions` | C | 158 | 64 | 94 | 59.49% |
| 57 | `sc900_mlc_q054` | 208 | `microsoft_entra` | C | 74 | 30 | 44 | 59.46% |
| 58 | `sc900_mlc_q227` | 381 | `microsoft_entra` | A | 74 | 30 | 44 | 59.46% |
| 59 | `sc900_p2_q023` | 70 | `microsoft_security_solutions` | D | 102 | 42 | 60 | 58.82% |
| 60 | `sc900_mlc_q182` | 336 | `microsoft_compliance_solutions` | B | 68 | 28 | 40 | 58.82% |

## Baseline disposition

```text
BASELINE_AUDIT = PASS / REPRODUCIBLE
BANK_CONTENT_CHANGED = NO
QUESTION_COUNT = 454
ANALYZABLE_COUNT = 449
STRICT_LONGEST_CORRECT_RATE = 0.648106904232
UNIQUE_LONGEST_HEURISTIC_SUCCESS = 0.675174013921
STRICT_SHORTEST_CORRECT_RATE = 0.104677060134
UNIQUE_SHORTEST_HEURISTIC_SUCCESS = 0.110588235294
NEXT_GATE = LEARNER_HISTORY_COMPATIBILITY
```
