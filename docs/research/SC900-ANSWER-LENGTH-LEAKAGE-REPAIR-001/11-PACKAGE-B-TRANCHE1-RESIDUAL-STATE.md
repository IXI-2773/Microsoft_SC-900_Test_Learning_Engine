# Package B Tranche 1 residual state

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE2-DESIGN`  
**Start SHA:** `e535daef6ea62e174c453c6a8ad91c7331ceaf82`  
**Purpose:** Recompute post-merge Tranche-1 leakage and residual inventory from current `main`. This is not the missing T1 Task 6 verification receipt and does not authorize Tranche-2 edits.

Machine-readable companions:

- `11a-PACKAGE-B-SOURCE-RECOMPUTE.json`
- `11b-PACKAGE-B-T1-CANDIDATE-RECOMPUTE.json`
- `13-PACKAGE-B-TRANCHE2-RESIDUAL-INVENTORY.json`

## Authority freeze

```text
PRODUCTION_DEFAULT_BANK = sc900_bank_v8_final.json
PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
T1_CANDIDATE_BANK = sc900_bank_v8_length_rebalanced_t1.json
T1_CANDIDATE_SHA256 = 45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8
T1_CANDIDATE_CONTENT_FINGERPRINT = e0b4394b6faa8d0f9053291521b2dd83983e84990f1a169a25ab745694a7aabb
AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}
RUNTIME_BANK = sc900_bank_v8_final.json
CANDIDATE_ADMITTED = YES
CANDIDATE_ACTIVE = NO
```

Fresh audits used `python -m tools.audit_answer_length` against both banks. Source SHA-256 matches the frozen Package B production hash. T1 candidate strict-longest matches file `10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json` exactly: **287 / 449**.

## Fresh leakage recomputation

| Metric | Source `final.json` | T1 candidate |
| --- | --- | --- |
| question_count | 454 | 454 |
| analyzable_single_answer | 449 | 449 |
| skipped_question_ids | `sc900_mlc_q148`, `q202`, `q214`, `q285`, `q289` | same five |
| strict_longest_correct | 291 / 449 = 64.81% | **287 / 449 = 63.92%** |
| unique_longest_heuristic | 291 / 431 = 67.52% | **287 / 431 = 66.59%** |
| strict_shortest_correct | 47 / 449 = 10.47% | 47 / 449 = 10.47% |
| unique_shortest_heuristic | 47 / 425 = 11.06% | 47 / 425 = 11.06% |
| correct-letter A/B/C/D | 106 / 114 / 116 / 113 | 106 / 114 / 116 / 113 |
| mean correct chars | 60.15 | 57.53 |
| mean longest distractor chars | 41.21 | 41.68 |

Shortest-answer and positional counts did not move. T1 did not create a shortest-answer or letter-position substitute cue.

### Per-domain strict-longest after T1

| Domain | T1 count / n | T1 rate | Source rate | Domain cap 45% |
| --- | --- | --- | --- | --- |
| microsoft_security_solutions | 108 / 163 | 66.26% | 67.48% | FAIL |
| microsoft_entra | 81 / 125 | 64.80% | 65.60% | FAIL |
| microsoft_compliance_solutions | 66 / 102 | 64.71% | 65.69% | FAIL |
| security_compliance_identity | 32 / 59 | 54.24% | 54.24% | FAIL |

Maximum domain rate after T1: **microsoft_security_solutions 66.26%**. No domain meets the governing `< 45%` cap.

Governing Package B target remains:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
```

287 / 449 does not satisfy it. Quality override is unchanged: do not force unsafe wording.

## Residual inventory

T1 semantic review queued 50 questions: 43 `EDIT`, 7 `SKIP`.

| Class | Count | T2 primary-queue eligible |
| --- | --- | --- |
| A. T1_EDITED_STILL_STRICT_LONGEST | 39 | No; reserved for a later distractor-strengthening pass |
| B. T1_SKIPPED | 7 | No; skip reasons preserved |
| C. UNREVIEWED_STRICT_LONGEST | 241 | Yes; T2 draws from this set |
| D. NO_LONGER_STRICT_LONGEST_AFTER_T1 | 4 | No; already crossed |
| Remaining strict-longest | 287 | 39 + 7 + 241 |

39 + 7 + 241 = 287. The four crossings account for the 291 → 287 bank-level delta.

### D. No longer strict-longest after T1

All four crossings were two-sided (`BOTH`) edits:

- `sc900_mlc_q135`
- `sc900_mlc_q079`
- `sc900_p3_q072`
- `sc900_mlc_q161`

### B. T1 SKIP set (preserved; not returned to the T2 queue)

| ID | Domain | Residual abs gap | T1 skip reason |
| --- | --- | --- | --- |
| `sc900_mlc_q173` | microsoft_compliance_solutions | 75 | Audit-versus-DLP distinction depends on detection, prevention, and policy-mode qualifiers; shortening could change the prevention claim. |
| `sc900_mlc_q070` | microsoft_entra | 110 | Cloud identity-risk versus on-premises AD threat distinction needs both product scopes and later-stage risk language. |
| `sc900_mlc_q116` | microsoft_security_solutions | 90 | CASB versus CSPM and workload-protection comparison relies on stated product-scope qualifiers. |
| `sc900_mlc_q085` | microsoft_security_solutions | 79 | Workload-protection versus CSPM depends on threat-detection, running-workload, and configuration-posture qualifiers. |
| `sc900_mlc_q253` | microsoft_security_solutions | 69 | Posture/misconfiguration versus runtime-threat distinction is already compact; further shortening risks oversimplification. |
| `sc900_mlc_q075` | microsoft_entra | 38 | Possession-factor wording depends on the certificate being held on a device or smart card. |
| `sc900_mlc_q155` | microsoft_compliance_solutions | 71 | Compliance Manager score versus Defender for Cloud secure-score comparison needs both product and measurement scopes. |

Reconsideration requires materially new evidence or a materially different safe repair strategy. T2 does not silently retry these IDs.

### A. T1 edited still strict-longest (39)

`sc900_mlc_q030`, `q037`, `q063`, `q086`, `q099`, `q105`, `q109`, `q115`, `q127`, `q129`, `q134`, `q143`, `q154`, `q160`, `q169`, `q170`, `q177`, `q179`, `q181`, `q183`, `q184`, `q187`, `q191`, `q192`, `q194`, `q218`, `q225`, `q273`, `q286`, `q290`, `sc900_p2_q025`, `p2_q029`, `p2_q034`, `sc900_p3_q038`, `p3_q043`, `p3_q049`, `p3_q060`, `p3_q091`, `p3_q095`.

Typical residual: correct choice already shortened, distractors unchanged, remaining absolute gap median **34**. Many still have terse distractors, so a later **distractor-strengthening** pass is structurally possible. That pass is not the T2 primary queue.

### C. Unreviewed strict-longest (241)

Full ranked rows, domains, gaps, and structural flags are in `13-PACKAGE-B-TRANCHE2-RESIDUAL-INVENTORY.json`. T2 selection is drawn only from this class.

## T1 yield (summary)

Observed on the 43 T1 `EDIT` items, by comparing `sc900_bank_v8_final.json` to `sc900_bank_v8_length_rebalanced_t1.json`:

- 36 correct-only wording changes; **0 crossed** strict-longest.
- 7 two-sided (`BOTH`) changes; **4 crossed**, 2 still longest.
- Mean absolute gap 61.5 → 29.2 characters; median remaining gap among still-longest edits: 34.
- Mean correct-choice change −27.4 characters; mean max-distractor change +4.9 (most distractors untouched).
- Correct-letter distribution unchanged.

T1 ranking targeted the largest gaps. Tightening the correct choice reduced severity but almost never crossed the unique-longest boundary unless a distractor was also strengthened.

## Production immutability at residual freeze

```text
REGISTRY_CHANGED = NO
DEFAULT_BANK_CHANGED = NO
CONTENT_EDITED = NO
NEW_CANDIDATE_CREATED = NO
EXE_REBUILT = NO
PACKAGE_C_STARTED = NO
```
