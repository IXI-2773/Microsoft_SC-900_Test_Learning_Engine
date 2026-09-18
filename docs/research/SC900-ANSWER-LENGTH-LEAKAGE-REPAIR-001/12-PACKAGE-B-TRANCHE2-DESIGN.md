# Package B Tranche 2 design

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE2-DESIGN`  
**Design base:** `main` at `e535daef6ea62e174c453c6a8ad91c7331ceaf82`  
**Status:** RESEARCH / DESIGN ONLY — implementation is not authorized by this document.

Governing leakage design remains `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md` on `origin/design/sc900-answer-length-leakage-repair-001`. This document does not weaken its statistical target or quality override.

Companion contract: `docs/superpowers/specs/2026-09-18-sc900-answer-length-leakage-repair-tranche2-design.md`.  
Implementation plan (not to be executed in this package): `docs/superpowers/plans/2026-09-18-sc900-content-revision-equivalence-migration-package-b-tranche2-implementation.md`.

## 1. Residual conclusion

Fresh audit of the admitted T1 candidate:

```text
STRICT_LONGEST_CORRECT = 287 / 449 = 63.92%
UNIQUE_LONGEST_HEURISTIC = 287 / 431 = 66.59%
DOMAIN_MAXIMUM = microsoft_security_solutions 108 / 163 = 66.26%
STRICT_SHORTEST_CORRECT = 47 / 449 (unchanged)
```

Package B is **partially complete**. Tranche 1 proved admission, evidence, and continuity. It did not meet the Package B completion target. Another bounded tranche is required.

```text
PACKAGE_B_REQUIRES_LATER_TRANCHE = YES
PACKAGE_B_EXPECTED_COMPLETE_AFTER_T2 = NO
PRODUCTION_ACTIVATION_READINESS = NOT_READY
```

Even a perfect 50-question T2 crossing would leave about 237 / 449 ≈ 53% strict-longest, still above 40%. T2 must not be treated as Package B closure.

## 2. T1 yield analysis

Direct before/after comparison of the 43 T1 `EDIT` questions:

| Observation | Count |
| --- | --- |
| Correct-choice-only edits | 36 |
| Two-sided (`BOTH`) edits | 7 |
| Distractor-only edits | 0 |
| Correct-only edits that crossed strict-longest | 0 |
| Two-sided edits that crossed | 4 |
| Two-sided edits that still missed | 2 |
| Gap reduced without crossing | 39 |

Causes supported by the actual banks, not speculation:

1. **Correct-only tightening does not cross large unique-longest gaps.** T1 shortened the correct choice by about 27 characters on average while leaving distractors untouched in 36/43 edits. Those 36 remained uniquely longest.
2. **T1 ranking selected extreme gaps.** Mean pre-edit absolute gap among T1 edits was 61.5 characters. After T1 the still-longest edited items still have a median gap of 34. Severity fell; the Boolean leakage flag did not.
3. **The only crossings were two-sided.** The four successes shortened the correct choice and lengthened at least one distractor enough that `correct_chars <= max_distractor_chars`.
4. **Semantic constraints limited distractor work in T1.** T1’s stated per-question order preferred tightening the correct choice first. Review notes often recorded B–D unchanged. That was a method choice, not proof that distractors cannot be strengthened equivalently.
5. **Skip set is real, not laziness.** Seven highest-severity items were left unchanged because product-scope or condition qualifiers are load-bearing. Those reasons remain binding.

T2 must not copy T1’s correct-only bias.

## 3. T2 repair strategy

Per-question order for T2:

1. **Prefer two-sided equivalent rebalancing** when the correct choice is verbose and at least one distractor is an underdeveloped but already-wrong proposition.
2. **Strengthen underdeveloped distractors** with the same wrong concept, using Microsoft Learn-backed scope that keeps them clearly incorrect.
3. **Tighten an unnecessarily verbose correct choice** when the same fact can be said more directly without dropping a required qualifier.
4. **SKIP** when crossing the length boundary would require filler, a different wrong concept, an answer-key change, prompt/explanation change, or unresolved Learn authority.

Forbidden techniques remain those in the governing leakage design: mechanical padding, equal-length forcing, copied Practice Assessment wording, key changes, and statistical-only rewrites.

T2 optimization target for the tranche is **strict-longest crossings achieved by equivalent wording**, not maximum character-gap reduction. Gap reduction without crossing is acceptable as a side effect, not as T2 success.

T1 `SKIP` IDs stay out of the T2 queue. T1 `EDIT` residuals stay out of the primary T2 queue. They may be a later distractor-strengthening pass after T2, because T1 already shortened many correct choices and left distractors terse. That later pass needs its own authorization.

## 4. Source / target architecture

Compared:

**Option A — chained T2**

```text
sc900_bank_v8_final.json
  --T1 admitted--> sc900_bank_v8_length_rebalanced_t1.json
  --T2 proposed--> sc900_bank_v8_length_rebalanced_t2.json
```

**Option B — collapsed rebuild**

```text
sc900_bank_v8_final.json
  --T2 proposed--> one candidate containing T1+T2 wording
```

**Selected: Option A, chained T2.**

Rationale against Package A:

- Version 1 live-state migration admits **one direct source→target edge per execution**.
- Historical events may traverse a complete approved chain `V1 → V2 → V3`.
- Production learners remain bound to `sc900_bank_v8_final.json`. T1 is admitted and inactive; T2 must not activate either candidate.
- T2 admission should prove only the new wording delta against the newly accepted T1 candidate. That keeps the T2 closed-world edge set bounded to T2 edits and leaves the T1 manifest/hash-bound receipts intact.
- A T2 collapsed rebuild from `final.json` would re-declare T1 edges, enlarge the T2 manifest to T1+T2 changed IDs, and risk T1 wording drift while duplicating already-admitted evidence.

Implications:

| Concern | T2 consequence |
| --- | --- |
| T2 source bank | `sc900_bank_v8_length_rebalanced_t1.json` |
| T2 target bank | `sc900_bank_v8_length_rebalanced_t2.json` (not created in this package) |
| T2 manifest | `t1 → t2` only |
| Production default | remains `sc900_bank_v8_final.json` |
| Registry | remains `{}` |
| Progress/session tests | migrate fixtures bound to **T1**, not to production `final.json` |
| Future T3+ | rank from the then-accepted candidate; do not reuse T2 stale ranks |
| Package C | **not authorized**. Activation from production `final.json` will need either sequential live migrations (`final→t1`, then `t1→t2`) or a later Package-C-owned collapsed `final→tN` admission. T2 must not build that activation pack. |

Option B is rejected for T2 because it conflates Package B candidate construction with Package C activation topology.

## 5. T2 question bound

Nominal bound: **50** unreviewed strict-longest questions (inside 40–60).

Selection rules used:

- Fresh T1-candidate ranking only; do not reuse T1 baseline ranks as the T2 queue.
- Exclude T1 `SKIP`.
- Exclude T1 `EDIT` residuals from the primary queue.
- Prefer non-label-like items in an absolute-gap band of 12–48 characters, or items with two-sided / sentence-like distractor structure.
- Domain mix follows residual share, slightly overweighting security because it holds the domain-rate maximum:

| Domain | Queue slots |
| --- | --- |
| microsoft_security_solutions | 19 |
| microsoft_entra | 14 |
| microsoft_compliance_solutions | 12 |
| security_compliance_identity | 5 |

The queue is a **design candidate queue**, not an approved `EDIT` set. Semantic review during implementation may `SKIP` any item. A smaller executed tranche is allowed if equivalence cannot be established.

Queue IDs, in residual-inventory rank order:

1. `sc900_mlc_q125`
2. `sc900_p3_q039`
3. `sc900_mlc_q054`
4. `sc900_mlc_q182`
5. `sc900_mlc_q278`
6. `sc900_p3_q090`
7. `sc900_mlc_q216`
8. `sc900_mlc_q041`
9. `sc900_mlc_q250`
10. `sc900_mlc_q046`
11. `sc900_mlc_q300`
12. `sc900_mlc_q012`
13. `sc900_p2_q011`
14. `sc900_p3_q067`
15. `sc900_p2_q004`
16. `sc900_mlc_q089`
17. `sc900_p3_q086`
18. `sc900_p2_q020`
19. `sc900_mlc_q252`
20. `sc900_mlc_q257`
21. `sc900_p3_q099`
22. `sc900_mlc_q288`
23. `sc900_p2_q005`
24. `sc900_mlc_q141`
25. `sc900_p3_q002`
26. `sc900_mlc_q137`
27. `sc900_p3_q047`
28. `sc900_mlc_q122`
29. `sc900_p1_q047`
30. `sc900_p3_q057`
31. `sc900_mlc_q126`
32. `sc900_mlc_q277`
33. `sc900_mlc_q254`
34. `sc900_mlc_q074`
35. `sc900_mlc_q138`
36. `sc900_mlc_q097`
37. `sc900_mlc_q267`
38. `sc900_p3_q050`
39. `sc900_mlc_q188`
40. `sc900_mlc_q280`
41. `sc900_mlc_q140`
42. `sc900_mlc_q034`
43. `sc900_p2_q013`
44. `sc900_p3_q034`
45. `sc900_p3_q054`
46. `sc900_mlc_q059`
47. `sc900_mlc_q295`
48. `sc900_mlc_q221`
49. `sc900_p1_q033`
50. `sc900_mlc_q217`

Exact ranks, gaps, and proposed repair posture: `13-PACKAGE-B-TRANCHE2-RESIDUAL-INVENTORY.json` → `t2_proposed_queue`.

## 6. Admission, stop, and quality gates

T2 implementation inherits Gates A/B/C from the governing leakage design and Package A fail-closed admission.

Stop and fail closed when:

- semantic equivalence cannot be established for a choice;
- Microsoft Learn authority is missing or insufficient for a semantic wording change;
- a repair would change correct key, letter mapping, prompt, objective, domain, topics, tier, eligibility, question type, or explanations;
- pedagogical quality would materially degrade;
- the candidate fails `admit_content_revision`;
- source/candidate identity, count, or non-choice fields drift;
- shortest-answer or positional leakage materially worsens;
- unauthorized paths change;
- T1 candidate SHA-256 is not exactly `45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8`;
- production `final.json` SHA-256 is not exactly `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.

T2 statistical goal: improve or justify neutrality on strict-longest versus the T1 candidate, with crossings preferred over gap-only reduction. T2 does **not** create a weaker Package B success target. If T2 finishes above 40% / 45% domain, report residual risk and stop for later-tranche design.

## 7. Non-authorization

```text
T2_CONTENT_EDITS = NOT_AUTHORIZED_BY_THIS_PACKAGE
T2_CANDIDATE_BANK = NOT_CREATED
T3_PLUS = NOT_AUTHORIZED
PACKAGE_C = NOT_AUTHORIZED
REGISTRY_ACTIVATION = NOT_AUTHORIZED
DEFAULT_BANK_CHANGE = NOT_AUTHORIZED
EXE_REBUILD = NOT_AUTHORIZED
T1_TEST_HARDENING = DEFERRED
```

Carried-forward T1 review findings remain deferred: the partial-transition negative test is SHA-mismatch-shallow, and `_admit()` still passes in-memory question lists. T2 tests, when later written, should pin finite admission reasons on negative twins rather than copying the nonempty-reason assertion. Do not modify T1 tests in the T2 design package.
