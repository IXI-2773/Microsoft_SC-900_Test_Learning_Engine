# Package B Tranche 3 design

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE3-DESIGN`  
**Design base:** `implementation/sc900-content-revision-equivalence-migration-B-tranche2-001` at `56739154999795434abe761e4032d465ec967f20`  
**Parent T2 design head:** `6380ec57ee95ade8eaaef827b96ada721bbe2778`  
**Status:** RESEARCH / DESIGN ONLY — implementation is not authorized by this document.

Governing leakage design remains `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`. This document does not weaken its statistical target or quality override.

Companion contract: `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche3-design.md`.  
Implementation plan (not to be executed in this package): `docs/superpowers/plans/2026-09-18-sc900-content-revision-equivalence-migration-package-b-tranche3-implementation.md`.

Machine-readable companions:

- `17a-PACKAGE-B-T2-CANDIDATE-RECOMPUTE.json` — independent `tools.audit_answer_length` rerun on the T2 candidate
- `18-PACKAGE-B-TRANCHE3-ANALYSIS.json` — residual topology, yield, prior-edit, and fresh-residual inventory
- `19-PACKAGE-B-TRANCHE3-QUEUE.json` — deterministic selection rule and nominated design queue

## 1. T2 baseline recomputation

Verified before any T3 design inference:

```text
START_HEAD = 56739154999795434abe761e4032d465ec967f20
PARENT_T2_DESIGN_HEAD = 6380ec57ee95ade8eaaef827b96ada721bbe2778
SOURCE_BANK = sc900_bank_v8_length_rebalanced_t2.json
SOURCE_BANK_SHA256 = 9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800
SOURCE_BANK_FINGERPRINT = 34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b
T2_EXTERNAL_REVIEW_STATE = IMPLEMENTED_UNMERGED
REGISTRY = {}
RUNTIME_BANK = sc900_bank_v8_final.json
```

Independent audit of the T2 candidate matches the frozen T2 verification receipt and `15-PACKAGE-B-TRANCHE2-CANDIDATE-METRICS.json`:

| Metric | T2 recomputation |
| --- | ---: |
| analyzable | 449 / 454 |
| skipped audit IDs | `sc900_mlc_q148`, `q202`, `q214`, `q285`, `q289` |
| strict-longest | **270 / 449 = 60.13%** |
| unique-longest | **270 / 428 = 63.08%** |
| correct-among-longest | 285 / 449 = 63.47% |
| strict-shortest | 47 / 449 = 10.47% |
| unique-shortest | 47 / 423 = 11.11% |
| letters A/B/C/D | 106 / 114 / 116 / 113 |

Per-domain strict-longest:

| Domain | Count / n | Rate | Max passing `< 45%` | Min crossings |
| --- | ---: | ---: | ---: | ---: |
| microsoft_compliance_solutions | 64 / 102 | **62.75%** | 45 | 19 |
| microsoft_security_solutions | 102 / 163 | 62.58% | 73 | 29 |
| microsoft_entra | 73 / 125 | 58.40% | 56 | 17 |
| security_compliance_identity | 31 / 59 | 52.54% | 26 | 5 |

Maximum domain rate remains `microsoft_compliance_solutions` at 62.75%. No domain is under 45%.

T2 execution identity independently verified: 49 `EDIT`, 1 `SKIP` (`sc900_mlc_q046`), 17 strict-longest crossings, 32 non-crossing edits, 43 `BOTH` / 13 crossings, 6 distractor-only / 4 crossings.

```text
PACKAGE_B_TARGET_REACHED = NO
PACKAGE_B_COMPLETE = NO
QUALITY_OVERRIDE_ALWAYS_CONTROLS = YES
```

## 2. Residual topology

Every current strict-longest residual was classified against the governed T1 and T2 semantic-review queues. Classes are mutually exclusive.

| Class | Definition | Count |
| --- | --- | ---: |
| A. T1 EDIT residuals | T1 `EDIT` IDs still strict-longest after T2 | 39 |
| B. T1 SKIP residuals | T1 `SKIP` IDs still strict-longest | 7 |
| C. T2 EDIT residuals | T2 `EDIT` IDs that did not cross | 32 |
| D. T2 SKIP residuals | T2 `SKIP` IDs still strict-longest | 1 |
| E. NEVER_REVIEWED | strict-longest IDs never in a T1 or T2 review queue | 191 |
| **Sum** | | **270** |

```text
A + B + C + D + E = 39 + 7 + 32 + 1 + 191 = 270
RESIDUAL_PARTITION_CLOSED = YES
T1_QUEUE ∩ T2_QUEUE = ∅
```

No residual sits in two classes. No strict-longest ID is unassigned. T2 did not re-queue T1 `EDIT` or T1 `SKIP` IDs.

Discrepancy versus an earlier T1 residual narrative: `11-PACKAGE-B-TRANCHE1-RESIDUAL-STATE.md` said T1 `BOTH` left “2 still longest.” Independent recomputation finds **3** T1 `BOTH` residuals still strict-longest: `sc900_mlc_q109`, `q177`, `q134`. That matches the T2 verification carried-forward list. The T1 “2 still longest” clause was a writeup error; the ID list was already complete.

## 3. Target-distance analysis

Package B target is unchanged:

```text
STRICT_LONGEST < 40%
UNIQUE_LONGEST < 40%
NO_DOMAIN > 45%
QUALITY_OVERRIDE_ALWAYS_CONTROLS
```

### Strict-longest

At denominator 449, passing requires count / 449 < 0.40 → count ≤ **179**.

```text
CURRENT = 270 / 449
MAXIMUM_PASSING_COUNT = 179
MINIMUM_REQUIRED_REDUCTION = 91
```

### Unique-longest

Unique-longest is not “strict-longest with a fixed 428 denominator.” The audit counts a unique-longest **success** only when exactly one choice is strictly longest and that choice is correct. The denominator is the number of questions with a unique longest choice (ties for longest are excluded).

Currently every strict-longest residual is also a unique-longest success (270 = 270). Fifteen additional questions are tied for longest including the correct choice (`correct_among_longest` 285), so they are already outside unique-longest.

Crossing effects:

| Crossing type | T2 count | Unique successes | Unique denominator |
| --- | ---: | --- | --- |
| shorter-than-max | 14 / 17 | −1 | usually unchanged |
| tie for longest | 3 / 17 | −1 | −1 |

If 91 strict crossings all go shorter-than-max and the unique denominator stays 428:

```text
179 / 428 = 41.82%  → unique-longest still FAIL
```

Maximum passing unique-longest count at denominator 428 is **171** (171 / 428 = 39.95%; 172 / 428 = 40.19%). That requires **99** unique-longest successes to disappear if the denominator does not shrink.

If every remaining crossing were a tie, unique-longest would get harder: `(270 − n) / (428 − n) < 0.40` requires **n ≥ 165**.

T2’s empirical mix was 3 ties / 17 crossings (17.6%). Under that mix the unique-longest closure requirement is about **107** crossings, not 91.

```text
UNIQUE_LONGEST_IS_THE_STRICTER_GLOBAL_METRIC = YES
STRICT_PASS_DOES_NOT_IMPLY_UNIQUE_PASS = YES
```

### Domains

Sum of per-domain minimums = 19 + 29 + 17 + 5 = **70**, which is less than the global strict-longest need of 91. Global strict-longest is the larger count constraint, but it does not protect domains. A security-heavy tranche can improve 270 / 449 while leaving compliance above 45%. T3 selection must therefore carry explicit domain quotas.

Compliance unique-longest is 64 / 94 = 68.09%, worse than its strict rate. Unique-longest remains a global metric; per-domain unique rates are watch items, not separate Package B gates.

## 4. T1 / T2 yield analysis

Raw counts, not overgeneralized percentages.

### T1 (43 `EDIT`)

| Slice | Edits | Crossings | Rate |
| --- | ---: | ---: | ---: |
| CORRECT_ONLY | 36 | 0 | 0 / 36 |
| BOTH | 7 | 4 | 4 / 7 |
| DISTRACTOR_ONLY | 0 | 0 | n/a |
| initial gap 31–50 | 9 | 2 | 2 / 9 |
| initial gap > 50 | 34 | 2 | 2 / 34 |
| overall | 43 | 4 | 4 / 43 |

Verified: T1 correct-only produced **zero** crossings. The four crossings were two-sided.

### T2 (49 `EDIT`)

| Slice | Edits | Crossings | Rate |
| --- | ---: | ---: | ---: |
| BOTH | 43 | 13 | 13 / 43 |
| DISTRACTOR_ONLY | 6 | 4 | 4 / 6 |
| CORRECT_ONLY | 0 | 0 | n/a |
| initial gap 21–30 | 2 | 2 | 2 / 2 |
| initial gap 31–50 | 23 | 15 | 15 / 23 |
| initial gap > 50 | 24 | 0 | **0 / 24** |
| entra | 13 | 8 | 8 / 13 |
| security | 19 | 6 | 6 / 19 |
| SCI | 5 | 1 | 1 / 5 |
| compliance | 12 | 2 | 2 / 12 |
| max-distractor growth > 30 | 14 | 13 | 13 / 14 |
| max-distractor growth ≤ 20 | 26 | 0 | 0 / 26 |
| crossing-to-shorter | 14 | — | 14 / 17 crossings |
| crossing-to-tie | 3 | — | 3 / 17 crossings |
| overall | 49 | 17 | 17 / 49 |

Material findings:

1. **The T2 > 50 gap band had zero crossings.** Severity-first ranking wasted 24 reviews.
2. **The T2 21–50 initial-gap band produced 17 / 25 crossings.** That is the empirical high-yield band.
3. **T2 distractor-only 4 / 6 is a small sample.** It is not a license to mandate distractor growth. Both noncrossing distractor-only items (`q126`, `q138`) are now near-crossing residuals.
4. **Compliance was T2’s weakest domain (2 / 12) and is now the maximum-rate domain.** T3 must not copy T2’s security overweight as if it were still the binding domain.
5. **Crossings required large max-distractor growth in T2.** Growth ≤ 20 never crossed. That is a quality-risk signal, not a growth quota.

## 5. Prior-edit residual analysis

Prior `EDIT` residuals are not exhausted. They are a bounded T3 second-pass population.

### Named T1 `BOTH` residuals

| ID | Domain | T1 tactic | Current gap | Correct Δ | Max-distractor Δ | Total distractor growth | Repairability |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `sc900_mlc_q109` | security | BOTH | **1** | +1 | +32 | +32 | NEAR_CROSSING_SECOND_PASS |
| `sc900_mlc_q177` | SCI | BOTH | **10** | −41 | +21 | +27 | BOUNDED_SECOND_PASS_CANDIDATE |
| `sc900_mlc_q134` | security | BOTH | **16** | −9 | +23 | +25 | POSSIBLE_DISTRACTOR_STRENGTHENING |

Previously reported T1 gaps (1 / 10 / 16) are unchanged after T2 because T2 did not touch these IDs.

`q109` is the cheapest remaining crossing on paper, but it is label-like. A second pass is justified only if one distractor can gain a real wrong-plane qualifier. It is not authorized by gap = 1 alone.

### All 39 T1 `EDIT` residuals

| Remaining gap | Count | Dominant prior tactic |
| --- | ---: | --- |
| 0–5 | 1 | BOTH (`q109`) |
| 6–10 | 1 | BOTH (`q177`) |
| 11–20 | 1 | BOTH (`q134`) |
| 21–30 | 11 | CORRECT_ONLY |
| 31–50 | 25 | CORRECT_ONLY |

36 / 39 T1 residuals are correct-only leftovers. Distractors were typically untouched, so a later distractor-strengthening pass is structurally possible. T3 does **not** re-queue the whole 39. Most remaining T1 gaps are still 31–50 and many are label-like (`LOW_YIELD_OR_LABEL_PRESSURE` = 21). Those wait unless T3 second-pass evidence later shows label-like distractor strengthening is safe.

### All 32 T2 non-crossing `EDIT`s

Verified major gap reductions:

| ID | Gap before → after | Mechanism |
| --- | --- | --- |
| `sc900_mlc_q288` | 40 → **4** | BOTH |
| `sc900_mlc_q126` | 42 → **5** | DISTRACTOR_ONLY |
| `sc900_p3_q002` | 89 → **21** | BOTH |

T2 non-crossing gap bands:

| Band | Count | T3 second-pass priority |
| --- | ---: | --- |
| 0–5 | 2 | include |
| 6–10 | 1 | include |
| 11–20 | 4 | include |
| 21–30 | 4 | watch; not in nominated T3 core |
| 31–50 | 15 | exclude from T3 second-pass |
| > 50 | 6 | exclude; matches T2 zero-yield trap |

A second semantically meaningful strengthening pass on the 7 T2 residuals with remaining gap ≤ 20 has materially higher expected yield than selecting another 7 untouched > 50 items. That is the scientific justification for folding a **bounded** prior-edit set into T3. It is not a blanket second-edit authorization.

## 6. Skip analysis

Default: `PRIOR_SKIP_PRESERVED`.

| ID | Tranche | Domain | Current gap | Reason still applies? |
| --- | --- | --- | ---: | --- |
| `sc900_mlc_q173` | T1 | compliance | 75 | Yes. Audit-versus-DLP qualifiers remain load-bearing. |
| `sc900_mlc_q070` | T1 | entra | 110 | Yes, and gap > 50 is a T2 zero-yield trap. |
| `sc900_mlc_q116` | T1 | security | 90 | Yes. Product-scope comparison. |
| `sc900_mlc_q085` | T1 | security | 79 | Yes. Workload-protection versus CSPM qualifiers. |
| `sc900_mlc_q253` | T1 | security | 69 | Yes. Compact posture/runtime distinction. |
| `sc900_mlc_q075` | T1 | entra | 38 | Yes for T3. Only in-band T1 SKIP, but the recorded blocker is the correct-choice possession-factor wording, not a reviewed distractor-only plan. |
| `sc900_mlc_q155` | T1 | compliance | 71 | Yes. Score-scope comparison. |
| `sc900_mlc_q046` | T2 | entra | 48 | Yes. Already reviewed under the two-sided policy; distractor expansion was judged to add length without new discriminative value. |

T2 distractor-only success is a new method **in principle** for SKIP items whose blocker was correct-choice shortening. It is not enough to reopen the set. Six of seven T1 SKIPs have gaps > 50, where T2 had 0 / 24 crossings; reopening them would recreate padding pressure. `q075` is a T4+ watch item only after T3 second-pass yield is known. `q046` stays closed.

```text
PRIOR_SKIPS_REOPENED = NO
```

## 7. Fresh-residual analysis

Class E = 191 never-reviewed strict-longest questions.

| Gap band | Count | Label-like | Sentence-like | Short-phrase |
| --- | ---: | ---: | ---: | ---: |
| 0–5 | 38 | 29 | 5 | 4 |
| 6–10 | 20 | 13 | 3 | 4 |
| 11–20 | 36 | 15 | 11 | 10 |
| 21–30 | 32 | 8 | 7 | 17 |
| 31–50 | 49 | 9 | 27 | 13 |
| > 50 | 16 | 3 | 6 | 7 |

Domain share of fresh residuals: security 72, entra 59, compliance 36, SCI 24.

The T2 heuristic (prefer non-label-like items in a 12–48 absolute-gap band, or sentence-like / two-sided structure) was directionally right, but T2 still admitted many > 50 items and under-weighted the domain that later became the maximum. T3 **replaces raw next-N-by-severity ranking**. It retains the non-label-like / sentence-like preference, tightens the yield band to **≤ 50 with 21–50 first**, and adds domain quotas plus a bounded second-pass core.

Fresh items with gap > 50 are excluded from the T3 queue. Label-like items with gap > 10 are excluded. Label-like 0–10 remain eligible only as a last structure class; the nominated 36-queue contains one such item (`q109`, a T1 residual), not a mass of fresh labels.

## 8. Domain-pressure analysis

T3 cannot close any domain. It must not optimize the global metric while leaving compliance or security structurally above 45%.

| Domain | Current SL | Min closure need | T3 MEDIUM queue | Expected repairable (not guaranteed) |
| --- | ---: | ---: | ---: | --- |
| microsoft_compliance_solutions | 64 | 19 | 12 | 3–7 |
| microsoft_security_solutions | 102 | 29 | 12 | 4–8 |
| microsoft_entra | 73 | 17 | 8 | 3–6 |
| security_compliance_identity | 31 | 5 | 4 | 1–3 |

Compliance is overweighted versus residual share (23.7% of residuals, 33% of the T3 queue) because it is the current maximum-rate domain and T2 delivered only 2 / 12 there. Security keeps an equal quota because it still needs the most crossings (29).

## 9. Queue-size alternatives

Do not assume T3 = 50.

| | SMALL | MEDIUM (nominated) | LARGE |
| --- | ---: | ---: | ---: |
| QUEUE_SIZE | 24 | **36** | 50 |
| PRIOR_EDIT_RESIDUAL_COUNT | 10 | **10** | 10 |
| FRESH_COUNT | 14 | **26** | 40 |
| SKIP_REOPEN_COUNT | 0 | **0** | 0 |
| DOMAIN_COMPOSITION | C8 S8 E5 SCI3 | **C12 S12 E8 SCI4** | C16 S16 E12 SCI6 |
| ESTIMATED_CROSSING_RANGE | 7–14 | **10–20** | 13–25 |
| QUALITY_RISK | lowest; slowest domain movement | mixed second-pass + fresh, still inside the 21–50 band | same yield band, larger review load |
| REVIEW_COST | low | moderate | high (T1/T2 convention) |
| LIKELIHOOD_OF_REQUIRING_T4 | certain | certain | certain |

Ranges are statistical estimates from T2 21–50 yield (17 / 25) and second-pass near-crossing structure. They are **not guaranteed**. Compliance’s T2 2 / 12 result is a downward bias on the compliance subset.

### Package B closure feasibility

1. Can T3 close strict-longest? **No.** Best plausible LARGE range (~25) leaves about 245 / 449 ≈ 55%.
2. Can T3 close unique-longest? **No.** Unique-longest needs ~99–107 success removals, not 91.
3. Can T3 close every domain threshold? **No.** Compliance alone needs 19 crossings; T3 queues 12.
4. Would attempting full closure in one T3 create unacceptable semantic pressure? **Yes.** 91 crossings at T2’s 17 / 49 rate implies ~260 reviews, i.e. almost the entire residual population including SKIPs, label-like items, and the > 50 zero-yield band.
5. Is T3 + T4 safer than an oversized T3? **Yes.** T4 is also not a closure tranche. Later bounded tranches remain required.
6. Does the evidence support changing the 50-question convention? **Yes, modestly.** Keep a bounded tranche, but stop stuffing it with > 50-gap items. MEDIUM 36 captures the entire high-value second-pass core and a domain-balanced 21–50 fresh slice, and it leaves an intact 21–50 remainder for T4 after second-pass yield is observed.

A larger tranche is not preferable merely because it could numerically reach the target. Quality remains the override.

## 10. Deterministic candidate-selection rule

Name: `T3_SECOND_PASS_PLUS_FRESH_YIELD_BAND_WITH_DOMAIN_QUOTAS`.

Reconstructible from the T2 candidate, T1 review dispositions, and T2 review dispositions. It does not use answer-key manipulation, future implementation outcomes, or unrecorded hand-picks.

1. Partition current strict-longest into A–E as in §2.
2. `SECOND_PASS_CORE`, in this order:
   - T2 `EDIT` residuals with current gap 0–10
   - T1 `EDIT` residuals with current gap 0–10
   - T2 `EDIT` residuals with current gap 11–20
   - T1 `EDIT` residuals with current gap 11–20  
   Sort each slice by gap ascending, then `question_id`.
3. Do not reopen T1 or T2 `SKIP` IDs.
4. `FRESH_ELIGIBLE` = class E with gap ≤ 50 and not (label-like and gap > 10).
5. Rank fresh by band (`21–50`, then `11–20`, then `6–10`, then `0–5`), then structure (sentence-like, short-phrase, label-like), then relative gap descending, absolute gap descending, `question_id`.
6. Fill remaining MEDIUM domain quotas from that rank: compliance 12, security 12, entra 8, SCI 4.

A question’s presence in this design queue does not authorize `EDIT`.

## 11. Nominated T3 design queue

```text
T3_RECOMMENDED_QUEUE_SIZE = 36
T3_RECOMMENDED_QUEUE_COMPOSITION = 10 prior-edit second-pass + 26 fresh yield-band
PRIOR_EDIT_RESIDUALS_INCLUDED = 10
PRIOR_SKIPS_REOPENED = 0
```

Queue IDs, in selection order:

1. `sc900_mlc_q288`
2. `sc900_mlc_q126`
3. `sc900_mlc_q138`
4. `sc900_mlc_q109`
5. `sc900_mlc_q177`
6. `sc900_mlc_q216`
7. `sc900_p3_q054`
8. `sc900_mlc_q295`
9. `sc900_mlc_q217`
10. `sc900_mlc_q134`
11. `sc900_mlc_q124`
12. `sc900_mlc_q291`
13. `sc900_mlc_q006`
14. `sc900_p3_q097`
15. `sc900_mlc_q016`
16. `sc900_p3_q062`
17. `sc900_p3_q070`
18. `sc900_mlc_q233`
19. `sc900_mlc_q299`
20. `sc900_p3_q006`
21. `sc900_mlc_q270`
22. `sc900_mlc_q281`
23. `sc900_mlc_q279`
24. `sc900_mlc_q296`
25. `sc900_mlc_q282`
26. `sc900_p3_q015`
27. `sc900_mlc_q157`
28. `sc900_mlc_q287`
29. `sc900_mlc_q266`
30. `sc900_mlc_q248`
31. `sc900_mlc_q262`
32. `sc900_mlc_q229`
33. `sc900_mlc_q236`
34. `sc900_mlc_q165`
35. `sc900_mlc_q228`
36. `sc900_mlc_q056`

Exact ranks, gaps, domains, and proposed repair modes: `19-PACKAGE-B-TRANCHE3-QUEUE.json`.

## 12. Repair-tactic policy

```text
PRIMARY_REPAIR_TACTIC = MIXED_BY_CANDIDATE
```

Do not globally mandate two-sided growth because T2 distractor-only yield was 4 / 6. Do not repeat T1 correct-only as the default.

| Tactic | When allowed | When disallowed | Quality risk | Expected semantic evidence |
| --- | --- | --- | --- | --- |
| DISTRACTOR_ONLY | Second-pass items whose correct choice is already tight; fresh items whose correct choice is already compact | When the only lengthening available is filler or a different wrong concept | Medium if growth is large | Same wrong concept; added words are the named product’s actual wrong-plane job |
| TWO_SIDED | Fresh sentence-like items in the 21–50 band with a verbose correct choice and underdeveloped distractors | When shortening would drop a required qualifier | Medium | Both sides remain equivalent; no key/prompt change |
| CORRECT_ONLY | Only if distractors are already complete false claims and a redundant correct qualifier exists | As a tranche default (T1: 0 / 36 crossings) | High for leakage, lower for semantics | Qualifier removal does not change the tested fact |
| SKIP | Any item where crossing needs padding, a new wrong concept, a key change, or unresolved Learn authority | Using SKIP to protect a statistical target | Quality override | Recorded reason |

Maximum acceptable manipulation pressure: no artificial character-count target may override natural wording. A crossing that requires filler is a `SKIP`.

### Distractor-growth safety

T2 `DISTRACTOR_GROWTH_MAX` = 39 is the **max-distractor metric** delta (`max_distractor_after − max_distractor_before`). Per-option deltas were larger: T2 `q125` A grew +48; T2 noncrossing `q288` had +46 on one option and +94 total distractor growth without crossing.

T3 evidence must record both:

- `MAX_DISTRACTOR_BEFORE/AFTER DELTA`
- `PER_OPTION_LENGTH_DELTA` for every changed distractor

Review trigger, not a hard cap:

```text
TRIGGER extra semantic inspection if any of:
  any single distractor option grows by > 30 characters
  total distractor growth > 60
  max-distractor metric grows by > 30
```

Fail closed on padding, wrong-concept substitution, or missing Learn authority. Do not fail merely because a triggered delta is large when the added words are the named product’s actual job.

## 13. Source / target architecture

Selected: **chained T3**, not a collapsed `final → T3` rebuild.

```text
sc900_bank_v8_final.json
  --T1 admitted--> sc900_bank_v8_length_rebalanced_t1.json
  --T2 implemented, inactive--> sc900_bank_v8_length_rebalanced_t2.json
  --T3 proposed--> sc900_bank_v8_length_rebalanced_t3.json
```

```text
T3_SOURCE = sc900_bank_v8_length_rebalanced_t2.json
T3_TARGET = sc900_bank_v8_length_rebalanced_t3.json   # not created in this package
T3_MANIFEST = t2 -> t3
PRODUCTION_DEFAULT = sc900_bank_v8_final.json
REGISTRY = {}
```

Package A requires one admitted source→target edge per revision, sequential live migration, and explicit historical lineage. T3 admission should prove only the new wording delta against the T2 candidate. A collapsed `final → t3` artifact may eventually be required for Package C activation; it is not designed or authorized here.

T2 remains unmerged. Future T3 implementation, when separately authorized, must start from a commit that still contains this exact T2 bank identity. It must not start from this design branch, and it must not treat T2 merge as implied.

## 14. Future implementation test plan

Not authorized now. When separately authorized, T3 implementation must retain:

- exact T2 source identity (`9c208309…` / `34b52785…`)
- deterministic T3 candidate identity
- closed-world changed-edge agreement
- semantic equivalence
- unchanged answer-key mapping
- unchanged prompt / objective / domain / topics / tier / eligibility / type
- Microsoft Learn authority
- deterministic review receipts
- finite fail-closed `RevisionFailureReason` assertions
- progress continuity from **T2-bound** fixtures
- session continuity
- idempotence
- registry freeze `{}`
- runtime-bank freeze `sc900_bank_v8_final.json`

Task sketch (design only): T3 builder RED/GREEN tests; semantic review of the 36-ID queue; builder run T2→T3; real admission/continuity/leakage gates versus T2; verification receipt; stop for external review. Do not create those files in this package.

## 15. Activation boundary, quality, and watch items

```text
T3_IMPLEMENTATION_AUTHORIZED = NO
PACKAGE_C_AUTHORIZED = NO
PRODUCTION_ACTIVATION_OCCURRED = NO
MERGE_AUTHORIZED = NO
MANIFEST_CREATION_FOR_IMPLEMENTATION = NO
RECEIPT_CREATION_FOR_IMPLEMENTATION = NO
```

Carried-forward, not T3-design repair work:

1. Pre-existing ruff I001 in `answer_length_audit.py` and `tools/build_package_b_tranche1.py`
2. Pre-existing C-streak warning on Q394–Q399

Material design findings:

- Unique-longest does not close when strict-longest first reaches 179 / 449 if the unique denominator stays 428.
- T2 > 50-gap edits: 0 / 24 crossings.
- T2 21–50-gap edits: 17 / 25 crossings.
- Compliance is now the maximum domain and was T2’s weakest domain.
- Bounded second-pass of near-crossing prior EDITs is justified; wholesale re-edit of all 39 + 32 residuals is not.

Nonblocking findings:

- T1 residual writeup said “2 still longest”; the correct count is 3.
- T2 distractor-only 4 / 6 remains a small sample.
- `q075` is the only in-band T1 SKIP and is a later-tranche watch item, not a T3 reopen.

Unresolved risks:

- Second-pass items already absorbed large distractor growth; remaining gaps may be load-bearing.
- `q109` is gap 1 and label-like; padding pressure is high.
- Compliance yield may stay below security/entra yield.
- Unique-longest may still fail after a later strict-longest pass if too many crossings are ties.
- T2 is implemented but unmerged; T3 implementation has a predecessor-gate dependency.

## Design conclusions

```text
T3_RECOMMENDED_QUEUE_SIZE = 36
T3_RECOMMENDED_QUEUE_COMPOSITION = 10_SECOND_PASS + 26_FRESH_YIELD_BAND
PRIOR_EDIT_RESIDUALS_INCLUDED = 10
PRIOR_SKIPS_REOPENED = NO
PRIMARY_REPAIR_TACTIC = MIXED_BY_CANDIDATE
DOMAIN_QUOTAS = compliance_12 security_12 entra_8 sci_4
EXPECTED_CROSSING_RANGE = 10-20
T3_EXPECTED_TO_CLOSE_PACKAGE_B = NO
T4_LIKELY_REQUIRED = YES
PACKAGE_B_TARGET_UNCHANGED = YES
T2_TO_T3_ARCHITECTURE_VALID = YES
QUALITY_OVERRIDE_PRESERVED = YES
```
