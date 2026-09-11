# Phase 7 — Comparative Alternatives

Rule: do not recommend complexity unless incremental benefit is defensible. All comparisons are **design**, not implementation.

---

## 7.1 Selection: Smart Practice 9 vs alternatives

| Alternative | What it optimizes | Evidence | Fit to v8 local app | Incremental benefit vs current | Complexity |
| --- | --- | --- | --- | --- | --- |
| Current Smart Practice | 8-utility + 5 roles + 40 maps | HEURISTIC | Already built | Baseline | High |
| Simple spaced repetition (due first, then unseen) | delayed restudy | Strong spacing/retrieval | Excellent | Likely similar or better on delayed unseen | Low |
| Weak + due + blueprint coverage (3-bucket) | repair + memory + exam outline | Strong families | Excellent | **Preferred experimental control** | Low |
| Difficulty-weighted retrieval | target mid difficulty | Needs real *b* | Poor (unidentified) | Speculative | Med |
| IRT/CAT | P(θ) information | Strong **with pool** | Poor now | None until bank+persons | Very high |
| BKT / PFA / logistic KT | P(correct\|KC,history) | Mixed; logistic OK small data | Medium if KCs = objectives | Possible later | Med |
| Hybrid: 3-bucket + exposure cap + held-out probes | learning + validity | Families + psychometrics | High | **Highest expected value** | Low–med |

**Decision (design only):** hybrid 3-bucket is the successor **candidate**, not CAT/DKT.

---

## 7.2 Memory model

| Alternative | Notes |
| --- | --- |
| Current accumulators | No true forgetting in time; grade table |
| Simple forgetting curve R=e^{-t/S} | Interpretable; needs S updates (HLR/FSRS-like) |
| SM-2 / Anki | Practitioner; MC cert ≠ flashcards |
| FSRS | Recent scheduler; limited independent psychometrics; still flashcard-shaped |
| Bayesian mastery per objective | Good if items are exchangeable KCs; SC-900 items are not yet |

**Decision:** RESEARCH_MORE a **time-aware** update scored on 7-day unseen success; do not import FSRS wholesale.

---

## 7.3 Readiness

| Alternative | Validity |
| --- | --- |
| Current composite + "Likely ready" | Low for exam; high misleadingness |
| Raw recent accuracy | Honest but cue-dependent |
| Weighted domain accuracy using official weights | Better coverage story; still seen-item |
| Psychometric θ | Impossible now |
| Calibrated P(correct on **held-out** items) + interval | Best available interpretation |

**Decision:** replace the **speech act**, keep a dashboard.

---

## 7.4 Misconception repair

| Alternative | |
| --- | --- |
| Current diagnosis + immediate twins | Massed; graph dormant |
| Simple immediate feedback | Supported |
| Delayed correction | Contested; not for study-mode hide |
| Contrastive examples | Promising for confusable products |
| Retrieval retry after ≥1 day on a **new** item | Best-aligned with spacing+transfer |

**Decision:** delayed new-item retry > immediate twin as default.

---

## 7.5 Concept graph

| Alternative | |
| --- | --- |
| Current auto-ready graph with empty edges | Complexity debt |
| No graph | Matches runtime reality |
| Manual prerequisite graph (blueprint) | Honest, small |
| Data-supported graph | Needs data we do not have |

**Decision:** no graph in the **policy**; optional later manual edges. Do not mine co-errors.

---

## 7.6 Difficulty

Rename struggle; do not implement IRT *b* until persons exist.

---

## 7.7 Response time

Keep contamination/idle cap. Drop slow_success as a learning grade. Optional rapid-guess flag only.

---

## 7.8 Confidence

Keep 3-level optional tag. Remove exam default Sure and Sure-quests. Do not feed strongly into utility.

---

## 7.9 Gamification

Keep disable switch. Do not expand. If unchanged, treat as **harmless-to-moderate heuristic** with Goodhart risk, candidate for controlled comparison — **not** automatic removal.

---

## 7.10 Policy governance

Leave dormant. A second internal pass is not Gate 3. Do not create an in-app experiment platform.
