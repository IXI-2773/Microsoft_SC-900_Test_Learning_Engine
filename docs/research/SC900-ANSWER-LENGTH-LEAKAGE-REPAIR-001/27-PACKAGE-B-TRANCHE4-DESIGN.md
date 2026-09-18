# Package B Tranche 4 closure-feasibility design

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE4-CLOSURE-DESIGN`  
**Design base:** `implementation/sc900-content-revision-equivalence-migration-B-tranche3-001` at `400b7846189e6b12b599a4dcdd1da7ae2b321408`  
**Parent T3 design branch:** `design/sc900-answer-length-leakage-repair-tranche3-001`  
**Status:** RESEARCH / DESIGN ONLY — implementation is not authorized by this document.

Governing leakage design remains `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`. This document does not weaken its statistical target or quality override.

Companion contract: `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche4-design.md`.  
Implementation plan (not to be executed in this package): `docs/superpowers/plans/2026-09-18-sc900-content-revision-equivalence-migration-package-b-tranche4-implementation.md`.

Machine-readable companions:

- `23-PACKAGE-B-T3-CANDIDATE-RECOMPUTE.json` — independent `tools.audit_answer_length` rerun on the T3 candidate
- `24-PACKAGE-B-TRANCHE4-RESIDUAL-TOPOLOGY.json` — mutually exclusive residual partition and per-residual history census
- `25-PACKAGE-B-TRANCHE4-ANALYSIS.json` — yield, domain, unique-longest, load-bearing, and queue-size feasibility
- `26-PACKAGE-B-TRANCHE4-QUEUE.json` — deterministic selection rule and nominated design queue

```text
T4_DESIGN_AUTHORIZED = YES
T4_IMPLEMENTATION_AUTHORIZED = NO
CONTENT_EDITING_AUTHORIZED = NO
T5_IMPLEMENTATION_AUTHORIZED = NO
PACKAGE_C_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
REGISTRY_ACTIVATION_AUTHORIZED = NO
EXE_REBUILD_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

## 1. Exact T3 baseline recomputation

Verified before any T4 design inference:

```text
START_HEAD = 400b7846189e6b12b599a4dcdd1da7ae2b321408
SOURCE_BRANCH = implementation/sc900-content-revision-equivalence-migration-B-tranche3-001
SOURCE_BANK = sc900_bank_v8_length_rebalanced_t3.json
SOURCE_BANK_SHA256 = d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b
SOURCE_BANK_FINGERPRINT = 83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2
T3_EXTERNAL_REVIEW_STATE = IMPLEMENTED_UNMERGED
PACKAGE_B_COMPLETE = NO
REGISTRY = {}
RUNTIME_BANK = sc900_bank_v8_final.json
IDENTITY_MATCH = YES
```

Independent audit of the T3 candidate matches the frozen T3 verification receipt and `21-PACKAGE-B-TRANCHE3-CANDIDATE-METRICS.json`:

| Metric | T3 recomputation |
| --- | ---: |
| analyzable | 449 / 454 |
| skipped audit IDs | `sc900_mlc_q148`, `q202`, `q214`, `q285`, `q289` |
| strict-longest | **256 / 449 = 57.02%** |
| unique-longest | **256 / 425 = 60.24%** |
| correct-among-longest | 274 / 449 = 61.02% |
| strict-shortest | 47 / 449 = 10.47% |
| unique-shortest | 47 / 421 = 11.16% |
| letters A/B/C/D | 106 / 114 / 116 / 113 |

Per-domain strict-longest:

| Domain | Count / n | Rate | Max passing `< 45%` | Min crossings |
| --- | ---: | ---: | ---: | ---: |
| microsoft_security_solutions | 98 / 163 | **60.12%** | 73 | 25 |
| microsoft_compliance_solutions | 59 / 102 | 57.84% | 45 | 14 |
| microsoft_entra | 70 / 125 | 56.00% | 56 | 14 |
| security_compliance_identity | 29 / 59 | 49.15% | 26 | 3 |

Maximum domain rate is now security at 60.12%. No domain is under 45%.

T3 execution identity independently verified: 36 reviewed, 29 `EDIT`, 7 `SKIP`, 14 strict-longest crossings (11 to shorter, 3 to tie), 15 non-crossing edits, 10 `BOTH` crossings / 25 `BOTH` edits, 4 / 4 distractor-only crossings. The seven T3 SKIP IDs match the frozen list, including protected `sc900_mlc_q109`.

```text
PACKAGE_B_TARGET_REACHED = NO
PACKAGE_B_COMPLETE = NO
QUALITY_OVERRIDE_ALWAYS_CONTROLS = YES
PACKAGE_B_TARGET_UNCHANGED = YES
```

## 2. Target distance

Package B target is unchanged:

```text
STRICT_LONGEST < 40%
UNIQUE_LONGEST < 40%
NO_DOMAIN > 45%
QUALITY_OVERRIDE_ALWAYS_CONTROLS
```

### Strict-longest

At denominator 449, passing requires count ≤ **179**.

```text
CURRENT = 256 / 449
STRICT_TARGET_MAX_COUNT = 179
STRICT_REMAINING_REQUIRED_REDUCTION = 77
```

### Unique-longest

Unique-longest is stricter than strict-longest under the current denominator. The unique denominator falls only when a crossing creates a longest-choice tie. Do not treat 87 as an invariant.

| Scenario | Tie share | Crossings needed for unique `< 40%` | Resulting unique |
| --- | ---: | ---: | ---: |
| ALL_TO_SHORTER | 0% | **87** | 169 / 425 = 39.76% |
| T3_STYLE_TIE_MIX | 3 / 14 ≈ 21.4% | **95** | 161 / 404.6 ≈ 39.79% |
| HIGHER_TIE_SHARE | 50% | **108** | 148 / 371 ≈ 39.89% |

Do not deliberately engineer ties. This is closure arithmetic only.

```text
UNIQUE_LONGEST_IS_THE_STRICTER_GLOBAL_METRIC = YES
STRICT_PASS_DOES_NOT_IMPLY_UNIQUE_PASS = YES
FIXED_DENOMINATOR_87_IS_NOT_INVARIANT = YES
```

### Domains

```text
SECURITY    98 / 163  max 73  min reduction 25
COMPLIANCE  59 / 102  max 45  min reduction 14
ENTRA       70 / 125  max 56  min reduction 14
SCI         29 /  59  max 26  min reduction  3
DOMAIN_MINIMUM_REDUCTION_SUM = 56
```

Do not add 56 to 77. Global and domain requirements overlap. Global strict-longest is the larger count constraint; it does not protect domains.

## 3. Complete post-T3 residual topology

Every current strict-longest residual was classified against the governed T1, T2, and T3 semantic-review queues. Classes are mutually exclusive. Multi-revision lineage is not forced into a single-edit class.

| Class | Definition | Count |
| --- | --- | ---: |
| A. NEVER_REVIEWED | never in a T1/T2/T3 review queue | 165 |
| B. T1_EDIT_ONLY | T1 `EDIT` only; still strict-longest | 36 |
| C. T2_EDIT_ONLY | T2 `EDIT` only; still strict-longest | 25 |
| D. T3_EDIT | T3 `EDIT`; still strict-longest | 15 |
| E. MULTI_EDIT | two or more `EDIT`s; still strict-longest | 0 |
| F. PRIOR_SKIP | skipped and never later edited | 8 |
| G. REOPENED_THEN_SKIPPED | prior `EDIT`, then later `SKIP` | 7 |
| H. OTHER | none | 0 |
| **Sum** | | **256** |

```text
RESIDUAL_TOTAL = 256
NEVER_REVIEWED = 165
ONE_EDIT = 76
MULTI_EDIT = 0
SKIP = 15
OTHER = 0
T3_EDIT_RESIDUAL_COUNT = 15
PARTITION_CLOSED = YES
```

165 = 191 T3-era never-reviewed residuals minus the 26 T3 fresh reviews. Independently verified.

No residual sits in two classes. No strict-longest ID is unassigned. `T1_QUEUE ∩ T2_QUEUE = ∅`. T3 second-pass `EDIT`s (`q138`, `q177`, `q134`) all crossed, so they are no longer residuals and there is no current multi-edit residual.

## 4. Review-history census

For every residual, `24-PACKAGE-B-TRANCHE4-RESIDUAL-TOPOLOGY.json` records `REVIEW_COUNT`, `EDIT_COUNT`, `SKIP_COUNT`, `CURRENT_GAP`, `INITIAL_KNOWN_GAP`, total correct/distractor length change, max per-option growth, latest tactic, domain, answer structure, Learn authority, and semantic-headroom class.

Repairability classes used in design (not an edit authorization):

| Class | Meaning | Dominant topology |
| --- | --- | --- |
| UNTOUCHED_REPAIRABLE | never reviewed; unused contrast remains | A, TIER_A/B |
| PREVIOUSLY_EDITED_BUT_STILL_REPAIRABLE | one prior edit with unused distractor-job contrast | B, mainly T1 `CORRECT_ONLY` |
| LOAD_BEARING_LENGTH_DIFFERENCE | correct choice is naturally more specific; further length work is quality-risk | F, G, many C |
| QUALITY_LIMITED / SHOULD_SKIP | closed SKIP, watch-listed expanded false claim, or high-risk label/large-gap leftover | F, G, much of A labels, D watch items |

Counts:

```text
HIGH_CONFIDENCE_REPAIRABLE_COUNT = 59
QUALITY_LIMITED_COUNT = 94
LOAD_BEARING_RESIDUAL_COUNT = 40
FRESH_TIER_A_OR_B_POOL = 86
SECOND_PASS_ELIGIBLE_POOL = 36
T3_NEAR_CROSSING_REPEAT_POOL = 5
```

The five T3 near-crossing non-crossers (`q248`, `q228`, `q229`, `q266`, `q299`) are **not** in the nominated T4 queue. T3 already applied `BOTH`. A second T4 edit would be a second edit without a new unused-contrast finding.

## 5. T3 EDIT residuals (the 15)

T3 made 29 `EDIT`s and 14 crossings, leaving 15 still strict-longest. All 15 were fresh T3 first-edits (`previously_edited = NO`). Presence here does not authorize another edit.

| ID | Domain | Pre → post gap | Tactic | Second-pass |
| --- | --- | ---: | --- | --- |
| `sc900_mlc_q270` | security | 37 → 23 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q281` | compliance | 40 → 20 | BOTH | LOW_CONFIDENCE |
| `sc900_p3_q006` | security | 46 → 20 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q291` | compliance | 46 → 17 | BOTH | LOW_CONFIDENCE |
| `sc900_p3_q015` | security | 37 → 17 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q157` | compliance | 44 → 18 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q016` | SCI | 47 → 15 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q056` | entra | 33 → 11 | BOTH | **DO_NOT_REQUEUE** |
| `sc900_mlc_q299` | compliance | 46 → 14 | BOTH | POSSIBLE |
| `sc900_mlc_q266` | security | 40 → 13 | BOTH | POSSIBLE |
| `sc900_mlc_q229` | entra | 36 → 12 | BOTH | POSSIBLE |
| `sc900_mlc_q262` | security | 37 → 12 | BOTH | LOW_CONFIDENCE |
| `sc900_mlc_q228` | entra | 22 → 12 | BOTH | POSSIBLE |
| `sc900_mlc_q248` | security | 33 → 8 | BOTH | POSSIBLE |
| `sc900_mlc_q165` | compliance | 24 → 6 | BOTH | **DO_NOT_REQUEUE** |

`q056` D grew +31 and `q165` C grew +25. Those T3 edits remain valid, but the expanded false claims are a carried-forward watch. Do not requeue them to chase the remaining 11- and 6-character gaps.

## 6. T3 SKIP residuals

Treat as **CLOSED** by default. Numerical attractiveness is insufficient to reopen them.

| ID | Why closed |
| --- | --- |
| `sc900_mlc_q288` | T2 BOTH already complete; remaining 4-character gap is padding pressure |
| `sc900_mlc_q126` | T2 distractor-only already used the CWP/CSPM contrast; leftover identity-provider expansion would not naturally overtake the workload-protection statement |
| `sc900_mlc_q109` | **Protected.** Expanding leftover Regulations / Industry standards labels would create a second defensible reading of the assigned-standard list |
| `sc900_mlc_q216` | Policies/standards GRC roles already complete after 95 characters of prior distractor growth |
| `sc900_p3_q054` | Wrong DDoS, eDiscovery, and NSG planes already named; shortening identity-type would drop authentication or authorization |
| `sc900_mlc_q295` | Prior distractor growth 87; remaining gap 14 has no unused contrast |
| `sc900_mlc_q217` | DDoS, Purview, and Sentinel false planes already complete; shortening the tenant definition would drop the organization-boundary meaning |

No new semantic repair mechanism unavailable in T3 was found. T4 does not requeue these seven IDs.

Also remain closed: T1 SKIPs `q173`, `q070`, `q116`, `q085`, `q253`, `q075`, `q155` and T2 SKIP `q046`.

## 7. Gap-band census

All 256 strict-longest residuals:

| Band | Count |
| --- | ---: |
| 0–10 | 63 |
| 11–20 | 52 |
| 21–30 | 44 |
| 31–40 | 46 |
| 41–50 | 23 |
| > 50 | 28 |

Never-reviewed (165), by band and domain:

| Band | Security | Compliance | Entra | SCI | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0–10 | 21 | 11 | 23 | 3 | 58 |
| 11–20 | 12 | 5 | 12 | 7 | 36 |
| 21–30 | 10 | 4 | 11 | 3 | 28 |
| 31–40 | 10 | 4 | 4 | 6 | 24 |
| 41–50 | 2 | 0 | 1 | 0 | 3 |
| > 50 | 9 | 2 | 2 | 3 | 16 |

Never-reviewed structure: LABEL_LIKE 74, SENTENCE_LIKE 54, SHORT_PHRASE 37.

T3’s 21–50 fresh preference is still the right primary band, but the remaining 21–50 never-reviewed mass is now 55 (28+24+3), not an inexhaustible pool. T4 will also need 11–20 sentence/short-phrase items after 21–40 is consumed.

`> 50` is not banned forever. Nine never-reviewed residuals are sentence-like and `> 50`. T2’s 0 / 24 in `> 50` was a severity-first mix, not a proof that every large-gap sentence is irreparable. T4 may admit at most a last-rank TIER_B sentence-like `> 50` item after ≤ 50 bands are used for a domain. The nominated 64-queue contains one such ID (`sc900_mlc_q197`). That is not a license to restock T2’s zero-yield trap.

## 8. Load-bearing residual analysis

Design-only class. Not a metric exemption.

Forty residuals are load-bearing candidates. They include:

- all 8 prior SKIPs (T1 seven + T2 `q046`)
- all 7 T3 reopened-then-skipped IDs
- T2 `BOTH` leftovers whose distractors already name complete false planes and whose remaining gap is still large (`q039`, `q278`, `q250`, `q097`, `q300`, and similar)
- T3 non-crossing `q270`, where both sides already moved and a 23-character gap remains

Diagnostic questions, applied as a class:

- Is the correct answer naturally more specific? **Often yes** — qualifying conditions, dual capabilities, or tenant/organization-boundary definitions.
- Are distractors short because the products genuinely do less? **Sometimes yes**; leftover labels are the opposite case and are *not* load-bearing.
- Would further distractor expansion merely restate irrelevant product jobs? **Yes for the T3 SKIP set.**
- Has the question already undergone one or more legitimate repairs? **Yes for classes C, D, G.**
- Would shortening the correct answer lose qualifying conditions? **Yes for the T1 SKIP set and several T2 BOTH leftovers.**
- Would another repair make the choices less natural? **Yes when remaining contrast is exhausted.**

Load-bearing residuals are the quality-risk floor. If all 40 never cross, 40 / 449 ≈ 8.9% would remain, which is compatible with `< 40%` *if* the other 216 can still supply 77 crossings. They are not permission to weaken the target.

## 9. T1 / T2 / T3 yield study

Raw counts. Do not average across tranches whose selection rules changed.

### T1 (43 `EDIT`, severity-first, correct-only bias)

| Slice | Edits | Crossings |
| --- | ---: | ---: |
| CORRECT_ONLY | 36 | **0 / 36** |
| BOTH | 7 | 4 / 7 |
| DISTRACTOR_ONLY | 0 | n/a |
| initial gap 31–40 | 2 | 1 / 2 |
| initial gap 41–50 | 7 | 1 / 7 |
| initial gap > 50 | 34 | 2 / 34 |
| max-distractor Δ ≤ 20 | 36 | 0 / 36 |
| overall | 43 | 4 / 43 |

### T2 (49 `EDIT`, two-sided, still admitted many `> 50`)

| Slice | Edits | Crossings |
| --- | ---: | ---: |
| BOTH | 43 | 13 / 43 |
| DISTRACTOR_ONLY | 6 | 4 / 6 |
| CORRECT_ONLY | 0 | n/a |
| initial gap 21–30 | 2 | 2 / 2 |
| initial gap 31–40 | 12 | 10 / 12 |
| initial gap 41–50 | 11 | 5 / 11 |
| initial gap > 50 | 24 | **0 / 24** |
| entra | 13 | 8 / 13 |
| security | 19 | 6 / 19 |
| SCI | 5 | 1 / 5 |
| compliance | 12 | 2 / 12 |
| max-distractor Δ ≤ 20 | 26 | 0 / 26 |
| max-distractor Δ > 30 | 14 | 13 / 14 |
| to shorter / to tie | — | 14 / 3 |
| overall | 49 | 17 / 49 |

### T3 (29 `EDIT` + 7 `SKIP`; second-pass + fresh 21–50)

| Slice | n | Crossings |
| --- | ---: | ---: |
| reviewed overall | 36 | 14 / 36 |
| EDIT overall | 29 | 14 / 29 |
| SECOND_PASS reviewed | 10 | 3 / 10 |
| SECOND_PASS EDIT | 3 | **3 / 3** |
| SECOND_PASS SKIP | 7 | 0 / 7 |
| FRESH reviewed | 26 | 11 / 26 |
| FRESH SKIP | 26 | 0 / 26 |
| BOTH | 25 | 10 / 25 |
| DISTRACTOR_ONLY | 4 | 4 / 4 |
| CORRECT_ONLY | 0 | n/a |
| compliance | 10 | 5 / 10 |
| security | 10 | 4 / 10 |
| entra | 6 | 3 / 6 |
| SCI | 3 | 2 / 3 |
| max-distractor Δ ≤ 20 | 24 | 9 / 24 |
| to shorter / to tie | — | 11 / 3 |

T3’s 9 / 24 crossings with max-distractor Δ ≤ 20 does **not** contradict T2’s 0 / 26. T3 started from smaller gaps. Do not impose a T2-style growth quota on T4.

Selection changed every tranche. Naive pooled rates are not T4 forecasts. The usable forecasts are:

- fresh yield-band reviewed crossing ≈ T3 11 / 26 = 42.3%
- second-pass reviewed crossing ≈ T3 3 / 10 = 30%, because SKIP dominated near-exhausted items
- second-pass `EDIT` crossing = 3 / 3, but only where unused contrast still existed
- overall reviewed crossing ≈ 14 / 36 = 38.9%

## 10. Distractor-only mechanism study

Combined T2 + T3 distractor-only: **8 / 10**. `LOW_SAMPLE_SIZE = YES`.

| ID | Tranche | Crossed? | Shared move |
| --- | --- | --- | --- |
| `q034` | T2 | yes | DDoS / Azure public-IP job named on an access-review question |
| `q074` | T2 | yes | DDoS job named on an Entra-roles question |
| `q126` | T2 | no | CWP job expanded; T3 later SKIPPED the remainder |
| `q138` | T2 | no | CSPM leftover; T3 second-pass later crossed |
| `q140` | T2 | yes | Entra ID Protection user/sign-in-risk job named versus Defender for Identity |
| `p3_q034` | T2 | yes | same-factor knowledge-type MFA near-miss made explicit |
| `q134` | T3 | yes | leftover Azure Firewall / DDoS labels stated their network jobs versus WAF |
| `q138` | T3 | yes | leftover Bastion label stated private RDP/SSH |
| `q177` | T3 | yes | RDP-exposure and access-review jobs named versus digital signatures |
| `q282` | T3 | yes | ISO-certification / STP-replacement false claims made explicit versus compliance score |

Shared mechanism: **UNUSED_REAL_PRODUCT_JOB_CONTRAST**.

A leftover product/control label or under-specified false plane is expanded into that named product’s actual wrong-plane job and remains clearly incorrect for the tested concept. Selection must start from a genuine unused discriminative contrast, not from “this distractor needs N more characters.”

`q126` is the negative control: after the real CWP/CSPM jobs were already stated, more length was padding. That is why T3 closed it, and why T4 must not reopen it.

## 11. Domain closure design

```text
MINIMUM_DOMAIN_COVERAGE =
  SECURITY 18, COMPLIANCE 12, ENTRA 12, SCI 4

RECOMMENDED_DOMAIN_QUOTAS (T4 64) =
  SECURITY 24, COMPLIANCE 15, ENTRA 17, SCI 8
```

Rationale:

1. **Do not allocate only by deficit.** Security’s deficit is 25, but it also has the largest never-reviewed mass (64) and 29 TIER_A/B fresh eligible. Quota 24 is deficit-aware without consuming the whole T5 remainder.
2. **Compliance is population-capped.** Deficit 14, but only 12 TIER_A/B never-reviewed remain. Quota 15 uses those 12 plus T1 `CORRECT_ONLY` leftovers. A 17–25 compliance quota cannot be filled from the current repairable pool without pulling TIER_C labels.
3. **Entra has unused fresh headroom.** Deficit 14, 26 TIER_A/B fresh eligible, T3 3 / 6 edits. Quota 17 is available without starving T5.
4. **SCI 8 is a domain-closure attempt, not padding.** Deficit is only 3. T3 SCI edit yield was 2 / 3. Nineteen TIER_A/B fresh eligible exist. Eight reviews can plausibly take SCI under 45% without being a mechanical 3-slot token.

T4 is **not** expected to close security, compliance, or entra. SCI closure is possible, not promised.

## 12. Unique-longest closure design

T4 must track `TO_TIE` versus `TO_SHORTER` in implementation metrics. Ties help unique successes and shrink the unique denominator.

Needed crossings for unique `< 40%`: 87 / 95 / 108 under the three scenarios above. T4 baseline ~23 crossings cannot close unique-longest under any of them.

T4+T5 at baseline 23 + 23 = 46 still fails unique. Optimistic 29 + 29 = 58 still fails unique. Unique-longest is the reason T6 is plausible even if strict-longest later looks close.

## 13. Queue-size feasibility

Required realized crossing rate to close **strict** 77 in one tranche:

| Family | Queue | Rate needed for 77 | Versus T3 14 / 36 ≈ 38.9% | Closure tranche? |
| --- | ---: | ---: | --- | --- |
| BOUNDED 48 | 48 | **160%** | exceeds queue size | **NO** |
| INTERMEDIATE 64 | 64 | **120%** | exceeds queue size | **NO** |
| LARGE 80 | 80 | **96.3%** | implausible | **NO** |
| CLOSURE_SCALE 96 | 96 | **80.2%** | more than double T3 | **NO** |

Unique ALL_TO_SHORTER needs 87, which is already > 80 and 90.6% of 96.

Expected T4 scenario ranges (reviewed crossing, not a performance target):

| Family | Fresh / second-pass | Conservative | Baseline | Optimistic | Expected strict after baseline |
| --- | --- | --- | --- | --- | ---: |
| 48 | 40 / 8 | 9–15 | 14–20 | 19–25 | 239 / 449 ≈ 53.2% |
| **64** | **54 / 10** | **13–19** | **20–26** | **26–32** | **233 / 449 ≈ 51.9%** |
| 80 | 70 / 10 | 17–23 | 26–32 | 34–40 | 227 / 449 ≈ 50.6% |
| 96 | 86 / 10 | 21–27 | 32–38 | 41–47 | 221 / 449 ≈ 49.2% |

A 96-queue exhausts the entire TIER_A/B never-reviewed pool (86) and still leaves ~221 strict-longest. It also over-samples SCI once security/compliance caps are hit. Oversizing T4 does not make it a closure tranche; it spends the T5 learning set.

## 14. T4 vs T4+T5

| | OPTION_A single large T4 | OPTION_B bounded 48 + T5 | OPTION_C 64 + T5 |
| --- | --- | --- | --- |
| Semantic reviews now | 96 | 48 | **64** |
| Repeat-edit candidates | 10 T1 leftovers; pressure to reopen T3 | 8 T1 leftovers | **10 T1 leftovers; 0 multi-edit** |
| Quality pressure | HIGH; consumes all TIER_A/B fresh | BOUNDED | **MODERATE** |
| Learn from T4 before T5 | NO | YES | **YES** |
| Domain closure risk | SCI oversampled; compliance still capped at 15 | SCI maybe untouched enough | **SCI 8 can attempt closure; others remain open** |
| Unique-longest | still far | still far | **still far** |
| Implementation/test burden | largest one-shot | two packages | **two packages, T4 still bounded** |
| Another tranche after that | still T5+T6 | T6 likely | **T6 plausible** |

**Nominated safest shortest path: OPTION_C.** Do not optimize for tranche count. A fake T4 closure attempt would spend the remaining high-quality population without hitting 40%, then force a worse T5 from TIER_C.

T4+T5 at historical rates still does not close Package B. That is expected and is why T6 remains plausible.

## 15. Repeat-edit policy

Validated against actual residual history:

```text
FIRST EDIT     = ordinary governed semantic review
SECOND EDIT    = requires explicit unused semantic contrast
THIRD OR LATER = presumptively SKIP unless exceptional evidence exists
```

Evidence:

- Zero current multi-edit residuals. The only T3 second-pass `EDIT`s all crossed; the rest were SKIPPED rather than forced.
- T1 `CORRECT_ONLY` leftovers still have untouched distractors. Those are legitimate second-edit candidates under UNUSED_REAL_PRODUCT_JOB_CONTRAST.
- T2 `BOTH` leftovers and T3 `BOTH` leftovers already used both sides. Remaining gap is not unused contrast.
- T3 SKIPs are reopen-then-skip closures. Do not count them as unused contrast.

Do not authorize another edit merely because a question is close to crossing (`q109` gap 1, `q165` gap 6, `q248` gap 8).

## 16. Repair-tactic policy

Do not automatically carry forward `MIXED_BY_CANDIDATE`.

**Primary T4 tactic: `SEMANTIC_CONTRAST_FIRST`.**

Operational split inside that policy:

1. T1 `CORRECT_ONLY` second-pass: **DISTRACTOR_JOB_CONTRAST** — expand leftover false planes into the named product’s real wrong-plane job. Do not shorten the already-tightened correct choice unless a redundant qualifier is still present.
2. Fresh sentence-like 21–40: two-sided equivalent rebalancing when the correct choice is verbose **and** at least one distractor is underdeveloped.
3. Fresh short-phrase: prefer distractor-job contrast over correct-only tightening.
4. `CORRECT_ONLY` as a tranche default remains forbidden (T1: 0 / 36).
5. Do not globally mandate distractor growth from 8 / 10 distractor-only. Low-N.

Still subordinate to:

```text
NO_FILLER
NO_PADDING
NO_KEY_CHANGE
NO_PROMPT_DRIFT
NO_OBJECTIVE_DRIFT
NO_CONCEPT_REPLACEMENT_FOR_LENGTH
LEARN_AUTHORITY
QUALITY_OVERRIDE
```

## 17. Nominated T4 queue

```text
QUEUE_SIZE = 64
FRESH_COUNT = 54
SECOND_PASS_COUNT = 10
MULTI_EDIT_COUNT = 0
DOMAIN_QUOTAS = SECURITY 24, COMPLIANCE 15, ENTRA 17, SCI 8
```

Selection rule `T4_BOUNDED_FRESH_YIELD_PLUS_STRICT_SECOND_PASS`, reconstructible from the frozen T3 state:

1. Partition residuals into A–H.
2. Close all SKIP IDs, including the seven T3 reopened-then-skipped IDs and `q109`.
3. Do not requeue T3 non-crossing `EDIT`s as a class.
4. Second-pass eligible: exactly one prior `EDIT`, unused distractor contrast, HIGH_CONFIDENCE or POSSIBLE, cap 10, sort by confidence then gap then `question_id`.
5. Fresh eligible: NEVER_REVIEWED, Learn authority, TIER_A or TIER_B.
6. Rank fresh by band `21–30`, `31–40`, `41–50`, `11–20`, `0–10`, `>50`; then structure sentence-like, short-phrase, label-like; then relative gap desc, absolute gap desc, `question_id`.
7. Fill the 64 quotas. Compliance 15 is population-capped.

Gap bands in the nominated 64: 0–10: 2; 11–20: 14; 21–30: 24; 31–40: 20; 41–50: 3; `>50`: 1.  
Structure: sentence-like 33, short-phrase 31, label-like 0.  
Tier: TIER_A 38, TIER_B 26.  
Tactic-candidate counts: DISTRACTOR_JOB_CONTRAST 35, TWO_SIDED_OR_DISTRACTOR_JOB 29.

Second-pass core (10), all T1 `CORRECT_ONLY` leftovers, zero T3 repeats:

`sc900_p2_q025`, `sc900_p3_q095`, `sc900_mlc_q129`, `sc900_mlc_q030`, `sc900_p3_q038`, `sc900_p3_q049`, `sc900_mlc_q169`, `sc900_mlc_q179`, `sc900_p3_q091`, `sc900_mlc_q063`

Full 64 IDs are listed in `26-PACKAGE-B-TRANCHE4-QUEUE.json`.

**No queue item is pre-approved for `EDIT`.** Future implementation must independently resolve every row to `EDIT` or `SKIP`.

## 18. Source / target architecture

```text
SELECTED = CHAINED_T4
T4_SOURCE = sc900_bank_v8_length_rebalanced_t3.json
T4_TARGET = future T4 candidate
EDGE = T3 → T4
PRODUCTION_DEFAULT = sc900_bank_v8_final.json
REGISTRY = {}
```

Do not design ordinary tranche implementation as `final → T4`. Package A remains sequential. No implicit multi-hop live migration.

T3 merge is a predecessor gate, not an implied T4 authorization. Future implementation must start from a commit that still contains the frozen T3 candidate identity, not from this design branch.

```text
T3_TO_T4_ARCHITECTURE_VALID = YES
```

## 19. Package B closure architecture (design only)

Distinguish:

```text
TRANCHE DEVELOPMENT LINEAGE =
  sc900_bank_v8_final.json
    --T1--> sc900_bank_v8_length_rebalanced_t1.json
    --T2--> sc900_bank_v8_length_rebalanced_t2.json
    --T3--> sc900_bank_v8_length_rebalanced_t3.json
    --T4--> future T4 candidate
    --T5+--> later candidates

PRODUCTION ACTIVATION / COLLAPSED REVISION ARTIFACT =
  later Package C work. Not designed, not built, not authorized here.
```

A later Package C design would need, at minimum:

- frozen final Package B candidate file hash and content fingerprint
- decision between sequential live admissions (`final→t1→…→tN`) versus one collapsed `final→tN` artifact
- Package A `admit_content_revision` / progress / session interfaces bound to production `final.json` as live source
- closed-world changed-edge set across the whole lineage, or a newly reviewed collapsed edge
- proof that `AUTHORIZED_CONTENT_REVISION_MANIFESTS` activation and runtime-bank cutover are a separate production act
- independent strict, unique, and domain recomputation on the activation target

This package identifies those interfaces only.

## 20. Future T4 implementation test plan

Design only. Do not implement in this package.

Required gates, mirroring T3 with T3 as source:

- exact T3 source identity (`SHA-256` / fingerprint above)
- deterministic T4 target identity after build
- exact queue binding to the 64 IDs
- closed-world changed edges = manifest `EDIT` set
- SKIP invariants for all T1/T2/T3 SKIP IDs, including the seven T3 closures and `q109`
- semantic invariants: prompt, IDs, correct mapping, objective, domain, topics, tier, eligibility, type unchanged
- Learn authority on every `EDIT`
- receipt binding to source/candidate fingerprints
- tamper fail-closed (`SEMANTIC_REVIEW_HASH_MISMATCH`)
- missing evidence (`SEMANTIC_REVIEW_MISSING`, `AUTHORITY_EVIDENCE_MISSING`)
- source mismatch (`SOURCE_BANK_FILE_HASH_MISMATCH`)
- target mismatch (`TARGET_BANK_FILE_HASH_MISMATCH`)
- prompt drift (`PROMPT_CHANGED`)
- finite `RevisionFailureReason` pins, not merely nonempty reasons
- real T3→T4 admission
- progress continuity from T3-bound fixtures
- session continuity from T3-bound snapshots
- idempotence / already-current
- registry freeze `{}`
- runtime-bank freeze `sc900_bank_v8_final.json`
- independent strict + unique + domain recomputation
- `TO_TIE` / `TO_SHORTER` crossing accounting
- extra inspection when any option grows by > 30 characters, total distractor growth exceeds 60, or max-distractor grows by > 30 (review triggers, not caps)

## 21. Risks / watch items

- Required 77 strict crossings exceed any bounded T4 yield. Calling T4 a closure tranche would be false.
- Unique-longest needs 87–108 crossings. Ties make it harder.
- Compliance repairable fresh pool is only 12 TIER_A/B. Domain closure of compliance cannot be forced in T4.
- Another mass second-pass on T3 SKIPs would recreate padding pressure, especially `q109`.
- T2 `> 50` 0 / 24 still warns against severity ranking. One last-rank sentence-like `> 50` ID is allowed; a `> 50` restock is not.
- Combined distractor-only 8 / 10 is low-N. Mechanism is real; quota is not.
- `q056` and `q165` expanded false claims: do not requeue.
- Load-bearing set of 40 is a quality floor, not a metric exemption.
- C-streak Q394–Q399 and ruff I001 in `answer_length_audit.py` / `tools/build_package_b_tranche1.py` remain unrepaired.

## 22. Carried-forward findings

Preserve without repairing:

- ruff I001: `answer_length_audit.py`, `tools/build_package_b_tranche1.py`
- C-streak: Q394–Q399
- T3 nonblocking observations: `sc900_mlc_q056` D and `sc900_mlc_q165` C

T1/T2/T3 SKIP IDs remain closed.

## 23. Required conclusions

```text
PACKAGE_B_CLOSURE_FEASIBLE_WITH_CURRENT_ARCHITECTURE = YES (multi-tranche; not T4-alone)
T4_RECOMMENDED_QUEUE_SIZE = 64
T4_RECOMMENDED_QUEUE_COMPOSITION = 54 fresh + 10 T1 unused-distractor second-pass + 0 multi-edit
T4_DOMAIN_QUOTAS = SECURITY 24, COMPLIANCE 15, ENTRA 17, SCI 8
T4_FRESH_COUNT = 54
T4_SECOND_PASS_COUNT = 10
T4_MULTI_EDIT_COUNT = 0
PRIMARY_REPAIR_TACTIC = SEMANTIC_CONTRAST_FIRST
EXPECTED_T4_CROSSING_RANGE = conservative 13-19 / baseline 20-26 / optimistic 26-32
T4_EXPECTED_TO_CLOSE_STRICT_TARGET = NO
T4_EXPECTED_TO_CLOSE_UNIQUE_TARGET = NO
T4_EXPECTED_TO_CLOSE_ALL_DOMAINS = NO
T5_LIKELY_REQUIRED = YES
T6_PLAUSIBLY_REQUIRED = YES
QUALITY_RISK = MODERATE
PACKAGE_B_TARGET_UNCHANGED = YES
T3_TO_T4_ARCHITECTURE_VALID = YES
IMPLEMENTATION_PLAN_READY = YES
T4_IMPLEMENTATION_AUTHORIZED = NO
```

The remaining Package B target can still be pursued with the existing answer-quality-preserving architecture. Residual repairable population is the 86 TIER_A/B never-reviewed items plus T1 `CORRECT_ONLY` leftovers with unused distractor jobs; leftover-label product-job contrast remains unused semantic headroom for T5/T6. Safe remaining crossings are a scenario range, not a quota. Much of the previously edited remainder is now load-bearing or quality-limited. T4 must stay bounded and intentionally require T5. Another T3-style second-pass on already-skipped near-crossings would create unacceptable padding pressure. The frozen `< 40% / no domain > 45%` target is still the right target; it is not T4-completable without degrading pedagogical quality.
