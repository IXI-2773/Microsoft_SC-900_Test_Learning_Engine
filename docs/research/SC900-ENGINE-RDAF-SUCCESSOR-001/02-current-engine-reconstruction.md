# Phase 0 — Current Engine Reconstruction (frozen baseline)

Subject: exact tree of `fed4d4a44591ca93fe8428bc3ca02ec66a12f715` (`sc900-v8.0.0-baseline`).  
Method: inspect runtime modules and tests at that SHA. Do not trust prior summaries as authority.

Origin: transplant of SY0-701 v8 architecture (`docs/baseline/source-v8-contract.json`, source SHA `5c099196525f2df236d4c80069e2b3a00a70bf94`). SC-900 conversion froze engine behavior; Smart Practice was **not** redesigned for SC-900. Policy label in code is `smart-practice-9`.

Runtime bank at baseline: **8 original placeholder questions**, two per SC-900 domain. Readiness is explicitly disclaimed as **not** Microsoft scaled-score conversion (`cert_profile_sc900.json`).

Legend used below:

- IMPLEMENTED = present in frozen runtime code
- TESTED = covered by unit/regression tests for **behavior**
- EMPIRICALLY_SUPPORTED = supported by learner-outcome evidence **in this engine** (none found)
- THEORETICALLY_SUPPORTED = maps onto a named scientific construct
- HEURISTIC = plausible weighted formula without identified calibration data
- UNVERIFIED = claimed or named in code/UI without a defensible measurement backing

CODE COVERAGE ≠ SCIENTIFIC VALIDITY. TEST PASSING ≠ LEARNING EFFECTIVENESS.

---

## CURRENT_ENGINE_CAPABILITY_MAP

### Smart Practice selection — IMPLEMENTED, TESTED, HEURISTIC, UNVERIFIED as learning optimizer

`smart_practice_core.build_smart_practice_score` computes an 8-component utility:

```
retention_risk + expected_learning_gain + blueprint_importance
+ misconception_repair_value + exploration_value
- repetition_cost - source_quality_risk - fatigue_cost
```

Role mix (default): due_retention 25%, weak_repair 25%, blueprint_coverage 25%, transfer 15%, controlled_stretch 10%. Selection then applies variety shaping (topics/domains/source-label cap), freshness, high-signal pinning, and a set-quality retry. `SMART_PRACTICE_SCORING` contains **dozens** of additional weights (half-life, cue dependence, ladder, counterfactual, knowledge-trace, etc.) that are mixed into those eight buckets via analytics maps.

Primary-role assignment is a **priority cascade**, not a learned policy: weak_repair → due_retention → blueprint_coverage → transfer → controlled_stretch.

Tests prove: role mix, variety, interleaving, screenshot burst, super-confident skip, freshness penalty, objective focus. Tests do **not** prove delayed retention or exam transfer.

### Learner memory — IMPLEMENTED, TESTED (schedule behavior), HEURISTIC, not a calibrated forgetting curve

Per-question `learner_memory`: `retrievability`, `stability`, `last_grade`, `next_review_at`, success/lapse counts (`progress_store.py`).

Grade inference mixes correctness, confidence (Sure/Unsure/Guessed), miss reason, response time ≥45s (`slow_success`), and session tags (`transfer`, `retrieval`/`delayed`).

Review days by grade (stability-modulated): lapse 0d; recognition/partial/slow_success 1d; confident 2+6s days; retrieval 3+4s; transfer/easy 7+7s. Legacy streak intervals `[1,3,7,14,30]` still override next review during early recovery (streak ≤2 after a miss).

This is **not** SM-2, **not** FSRS, **not** a power-law forgetting curve. Retrievability is a clamped accumulator, not `R = exp(-t/S)`.

`study_status_name` can label a question "Mastered" at correct_streak ≥ 4. That is a local streak heuristic, not delayed retention.

### Spaced review — IMPLEMENTED, TESTED, THEORETICALLY_SUPPORTED as a family, HEURISTIC in parameterization

Due-review pool uses `next_review_at`. Smart Practice `due_retention` role and `retention_risk` boost due items. Super-confident cooldown is **120 days** with retrievability forced ≥0.995.

No expanding-interval optimization against a target retention probability. Policy `review_interval_multiplier` exists but bootstrap value is 1.0.

### Difficulty handling — IMPLEMENTED, TESTED (analytics rows), HEURISTIC, UNVERIFIED as item difficulty

`_build_difficulty_calibration_rows`: score from this learner's wrong rate, fragile-confidence rate, volatility, stability, source conflict. Labels Hard/Moderate/Stable.

This is **person × item recent struggle**, not IRT *b*. It cannot separate learner weakness from item defect. Sample is one person. Placeholder bank has 8 items.

### Confidence — IMPLEMENTED, TESTED (UI/progress), HEURISTIC as adaptation input

Options: Sure / Unsure / Guessed. After answering, confidence is collected; miss reason is inferred from confidence unless overridden. Confidence feeds: memory grade, knowledge-trace likelihoods, decision-quality analytics, pass-prediction, Super Confident 120-day skip.

Exam mode defaults `_collect_answer_feedback` to confidence `"Sure"` — so exam answers contaminate the confidence channel.

### Misconception repair — IMPLEMENTED, TESTED (follow-up insertion / wrong-answer memory), HEURISTIC, UNVERIFIED as misconception diagnosis

Mechanisms: active-weak filter, wrong-answer memory pressure, near-miss pressure, confusion-pair follow-ups, tempting-distractor recycling, recovery ladder (Fragile→Recovering→Stable→Trusted→Mastered).

There is **no validated misconception taxonomy**. "Wrong-answer family" is lexical/heuristic. Repair success is not measured as delayed relapse on **unseen** items of the same concept.

### Concept graph — IMPLEMENTED, TESTED in isolation, DORMANT IN RUNTIME, UNVERIFIED

`smart_practice_concept_graph.py` supports concepts, edges (`prerequisite_of`, `confusable_with`, …), diagnosis types, edge calibration, audits.

**Runtime fact (load-bearing):** `make_edge` / `calibrate_edges` are **not called** from application mixins. `normalize_graph(meta, pool)` creates **concept nodes from questions** and preserves stored edges. Fresh progress stores have **empty edges**. Diagnoses that require edges (`missing_prerequisite`, `concept_confusion`) therefore collapse to `insufficient_evidence` in ordinary use.

Runtime **does** call `store_diagnosis` when a non-insufficient diagnosis occurs. Diagnoses that can fire without edges: `transfer_failure`, `item_specific_failure`, `source_quality_problem`, and sometimes `target_concept_weakness` (needs counterevidence of stable prerequisites, which empty graphs rarely provide).

Graph is infrastructure + tests, not an operating knowledge graph.

### Question-quality handling — IMPLEMENTED, TESTED (status machine), EMPIRICALLY INERT at baseline

Statuses: healthy / needs_review / ambiguous / source_conflicted / poor_discriminator / possible_bad_key / insufficient_data. Discrimination = strong-retrievability accuracy minus weak-retrievability accuracy. Minimum samples 10 (20 for bad-key).

With one learner and 8 items, status remains `insufficient_data`. Quality cannot be estimated from a single person's retries.

### Source trust — IMPLEMENTED, TESTED (warning UI), HEURISTIC

`source_trust.py` warns only on Source conflict / Decayed. Smart Practice penalizes trust below baseline 85, plus decayed/conflict penalties. Placeholder bank is a single original source, so agreement/conflict analytics are mostly vacuous.

### Progress / history — IMPLEMENTED, TESTED

Per-question attempts/correct/wrong/streak/confidence/miss-reason/flag/suspend/memory. History capped at 4000 events. Autosave, backups, checkpoints, restore, quarantine of corrupt runtime files.

### Readiness analytics / prediction / calibration — IMPLEMENTED, TESTED (formula), HEURISTIC, UNVERIFIED as exam readiness

Pass predictor (`_build_pass_prediction`): weighted mix of recent50 accuracy (0.28), decision quality (0.24), stability (0.24), Sure accuracy (0.14), sample strength vs 180 attempts (0.10), plus source-trust bonus and penalties for active-weak count, due count, volatility, coverage gaps. Labels: Likely ready ≥78, Borderline ≥64, else Not ready. `readiness_floor = min(score, stability_score)`.

Internal threshold in profile: 82.5% with min 120 attempts. Official Microsoft pass is 700/1000 scaled. Engine **does not** estimate that scaled score.

Separate measurement module **does** implement Brier, log loss, ECE (5 bins), pairwise discrimination, 24h and 7d outcome windows, with `minimum=20` samples. These are **local post-hoc reports**, not the pass-predictor formula. They cannot populate on an 8-item first-run.

### Recommendations — IMPLEMENTED, TESTED, HEURISTIC

`analytics_recommendations.py` emits imperative study advice from whichever analytics row is hottest (due, weak, volatility, clusters, burnout, source trust, …). Not an experiment-backed tutor policy.

### Policy governance — IMPLEMENTED, TESTED (schema/gates), INERT IN SINGLE-LEARNER USE

`smart_practice_policy.py`: draft/shadow/candidate/active/rollback. Promotion needs ≥50 shadow decisions, ≥30 supported challenger outcomes, ≥20 24h outcomes, ≥10 7d outcomes, ≥7 observation days. Bootstrap policy is active from `legacy_migration` with **no empirical evidence_reference beyond "legacy configuration"**.

A local SC-900 learner cannot satisfy promotion thresholds. Governance is a transplanted multi-learner experiment harness, not an operating loop.

### Adaptive answer ordering — IMPLEMENTED, TESTED

Unseen items: stable shuffle. After attempts on single-correct items: `adaptive_shuffle_question` seeded by qnum, epoch, attempts, wrong/correct counts. Prevents letter-position memorization. Does not estimate choice-position bias in the population.

### Session construction / modes — IMPLEMENTED, TESTED

Modes: Smart Practice, Practice, Exam, Weak retest, Due review. Practice source filters: All / Unseen / Previously answered / Previously wrong / Due/flagged weak. Count options 10/20/40/50 (default 50) — **larger than the 8-item bank**, so sessions are bank-capped.

Exam: `exam_reveal=False` until finish; forced-finish exists. Practice/Smart Practice: immediate correctness + explanation.

Session limit equals requested count; follow-ups replace unprotected future slots rather than growing the set.

### Interleaving / variety — IMPLEMENTED, TESTED, HEURISTIC as learning mechanism

`_interleave_questions` avoids back-to-back same topic/source/stem-style when alternatives exist. Variety shaping targets ≥4 topics, ≥2 domains, source-label cap 35% for sets ≥10. On an 8-item 4-domain bank, variety is mostly automatic.

### Fatigue / speed — IMPLEMENTED, TESTED (analytics), HEURISTIC

Burnout from last-10 vs earlier-half accuracy drop, response-time drag, fragile-confidence rate. High burnout increases `fatigue_cost` on hard items. Response times sanitized (idle cap, contamination flag). Slow correct (≥45s) is graded `slow_success` (weaker memory credit). Speed-risk and latency analytics exist.

RT is **not** a psychometric response-time model. It can confound reading speed, UI, and item length with mastery.

### Quests / gamification — IMPLEMENTED, TESTED, HEURISTIC as learning aid

22 quest variants, milestones, XP, medals, combo heat, boss round after 10 answers, stealth checkpoints, optional celebration sound. Can be disabled. Pass overlay threshold 70% (unrelated to Microsoft 700 scaled). Quests optimize answered/correct/streak/sure/recovery counts — **not** delayed retention.

### Review scheduling / follow-ups — IMPLEMENTED, TESTED

Immediate twins, confusion-pair drills, delayed same-concept probes, retrieval ramps, wrong-answer-memory follow-ups, streak rescue, boss rounds. Delayed probes are **within-session slot delays**, not 24h/7d delays.

### Question quarantine / provenance — IMPLEMENTED, TESTED

Issue reports suspend questions. Duplicate_of / flagged_issues fields exist. Ingestion pipeline exists in repo but is **out of subject** except as future bank-quality input. Runtime bank is the 8-item placeholder.

### Runtime-bank behavior — IMPLEMENTED, TESTED

JSON bank load, sanitization, shuffle, screenshot-review path, Windows packaging. Baseline bank is original placeholders, not Microsoft exam content.

---

## CURRENT_ENGINE_ASSUMPTIONS

1. A weighted utility over many analytics signals selects better practice than simpler due/weak/unseen rules.
2. Per-question retrievability/stability tracks durable memory.
3. Confidence reports improve grading and adaptation more than they add noise.
4. Concept-graph diagnoses can identify prerequisite vs item vs source failures.
5. Item difficulty can be inferred from one learner's miss pattern.
6. A composite "readiness" score forecasts exam pass likelihood.
7. Interleaving topic/source/style improves certification learning.
8. Immediate repair chains (twins, confusion drills) outperform spaced re-retrieval of the same concept.
9. Source-trust penalties improve outcomes by avoiding bad items.
10. Response time distinguishes mastery from struggling.
11. Question-level history generalizes to concept mastery.
12. Policy governance can empirically promote better policies.
13. More analytics dimensions = more intelligent personalization.
14. Gamification increases persistence without harming learning quality.
15. Recognition success on seen multiple-choice items is a valid proxy for SC-900 exam competence.

---

## CURRENT_ENGINE_MEASUREMENT_MODEL

**What is actually measured (local, one learner):**

- binary correctness, selected letters, confidence, inferred miss reason
- raw/effective response seconds with contamination flag
- streaks, due dates, flags, suspends
- session completion, XP, quests (engagement)

**What is computed but not population-calibrated:**

- Brier / log loss / ECE on stored predictions vs later events (n≥20 gate)
- 24h / 7d recall windows in `smart_practice_measurement.WINDOWS`
- pairwise discrimination of predicted probabilities
- role performance, repair relapse, source-band performance
- item discrimination from **this learner's** strong vs weak retrievability splits

**What is presented as if measured:**

- pass-prediction 0–100 and Likely ready / Borderline / Not ready
- knowledge-trace "mastery_prob" from a 1-parameter Bayesian update with **hand-set** known/unknown likelihoods by confidence, prior 0.38, no slip/guess estimation, no KC parameter fit
- difficulty labels Hard/Moderate/Stable
- dozens of 0–100 analytics rows (transfer strength, robustness, half-life, burnout, …)

**Identifiability failure:** one learner × 8 items cannot identify item difficulty, item discrimination, ability, source quality, and concept mastery separately.

---

## CURRENT_ENGINE_ADAPTATION_MODEL

Offline session construction (not item-by-item CAT):

1. Build ~30 analytics maps from history.
2. Score every eligible question with the 8-utility + role cascade.
3. Fill role quotas, then variety/freshness/quality retry.
4. Interleave the ordered set.
5. During the session, insert/replace follow-ups (twins, probes, boss, streak rescue) under a hard count cap.
6. After answers, update progress/memory and optionally store predictions.

Exploration vs exploitation is a **fixed role share**, not a bandit with regret control. There is no information-maximizing IRT selection. `information_value()` is another heuristic sum, bounded to ±6.

---

## CURRENT_ENGINE_LEARNING_MODEL

Implicit theory:

- Retrieval + spacing + error repair + coverage + transfer checks + desirable difficulty − repetition − bad sources − fatigue.

Actual credit assignment:

- Immediate correctness dominates memory updates.
- Confidence and RT reshape grade.
- Within-session follow-ups create massed extra practice after errors (often the opposite of spacing).
- Super-confident removes items for 120 days (high risk of premature drop-out).
- Exam mode withholds feedback (closer to test) but stamps Sure.

There is **no explicit model of transfer to unseen official items**. Transfer analytics compare stem-style/source diversity in the local bank.

---

## CURRENT_ENGINE_KNOWN_GAPS

1. Placeholder bank (n=8) cannot support adaptive, IRT, quality, or readiness claims.
2. Concept-graph edges are not generated at runtime.
3. `calibrate_edges` unused in app path.
4. Measurement 24h/7d / Brier stack is disconnected from the pass-predictor and from promotion (promotion thresholds unreachable).
5. Knowledge "trace" is not BKT/PFA/IRT; parameters are constants.
6. Difficulty ≠ psychometric difficulty.
7. Mastered/Trusted labels are streak-based.
8. Exam-mode confidence default = Sure.
9. Follow-ups can convert spaced plans into massed repair.
10. Analytics mixin (~230KB) computes a large number of correlated 0–100 scores from the same events (false precision / double counting).
11. No delayed retention experiment harness in the learner UI.
12. No population item statistics; single-user desktop app.
13. Gamification rewards volume and streaks.
14. Official blueprint weights exist in profile but Smart Practice role shares are not blueprint-weight CAT constraints.
15. Recognition/MC cue dependence is only a heuristic row, not a first-class outcome.

---

## CURRENT_ENGINE_UNPROVEN_ASSUMPTIONS

All 15 numbered assumptions above are **UNPROVEN in this engine**. Several are theoretically plausible (spacing, retrieval, feedback, exposure control). Several are theoretically contested (confidence as reliable signal; RT as mastery; concept graphs without data; composite readiness; many-signal utility).

No EMPIRICALLY_SUPPORTED learning-effect claim survives Phase 0.
