# Phase 2 — Prior Exposure / Precommitment

Recorded **after** frozen-baseline reconstruction and **before** literature synthesis, so later evidence is not selected merely to justify v8.

These are **expected answers**, not findings. Status after reconciliation is in `11-reconciliation.md`.

## Engine's implicit theory (as read from code)

The engine behaves as if:

1. Learning is maximizing a linear utility of retention risk, expected gain, coverage, repair, and exploration, minus repetition, source risk, and fatigue.
2. Many weakly correlated analytics improve selection if they are all added.
3. Durable memory is a pair of [0,1] accumulators updated from the last trial.
4. A local composite score can be labeled exam readiness.
5. Diagnosing *why* an error occurred (prerequisite, confusion, item, source) is worth a graph subsystem.
6. Immediate, tagged follow-ups implement "repair."
7. Confidence and latency are informative enough to change grades and difficulty.

## Precommitted questions and expected answers

### Q1. Does adaptive selection outperform simpler spaced retrieval here?

EXPECTED: **Unlikely to be proven, and possibly false at current complexity.** With 8 items and one learner, "adaptive" cannot beat a due+weak+unseen shuffle by enough to measure. Even with a large bank, the current utility has too many uncalibrated weights to expect a unique advantage over a 3-bucket scheduler.

### Q2. Does the current memory model measure durable retention or merely recent performance?

EXPECTED: **Mostly recent performance.** Retrievability rises on success and falls on failure without an explicit time-decay term. Due dates exist, but "Mastered" is a streak. Super-confident freezes high values for 120 days.

### Q3. Does confidence improve adaptation or introduce noise?

EXPECTED: **Mixed, with a net risk of noise.** Three-level self-report after MC recognition is a coarse JOL. Exam mode stamps Sure. Guessed-correct is treated as weak encoding (plausible) but Sure-wrong can mean item defect, misread, or overconfidence.

### Q4. Does misconception / concept-graph reasoning produce measurable value?

EXPECTED: **Not in the current runtime.** Edges are not populated. Diagnosis will usually be `insufficient_evidence`. Follow-up "confusion drills" may still help as extra retrieval, independent of the graph.

### Q5. Does difficulty calibration represent actual item difficulty?

EXPECTED: **No.** It represents this learner's struggle. Confounds ability, item quality, and exposure.

### Q6. Are Smart Practice utility components evidence-based?

EXPECTED: **Family-level yes, parameterization no.** Retention, coverage, and repair names map to real literatures. The numeric bounds (25/20/15/20/10/15/15/10) and the 50+ scoring-profile knobs are designer heuristics.

### Q7. Does interleaving help this certification-learning context?

EXPECTED: **Uncertain / possibly small.** SC-900 is conceptual MC across named product families. Interleaving helps most for discriminable similar categories. Mixing Entra vs Purview vs Defender *might* help contrast; mixing unrelated facts may not.

### Q8. Are repair chains better than simple repeated retrieval?

EXPECTED: **Immediate twins are more likely massed practice than superior repair.** Delayed probes inside the same session are not 24h delays. Contrastive distractor reuse could help *if* distractors encode real confusions.

### Q9. Do gamification mechanisms improve persistence without reducing learning quality?

EXPECTED: **Persistence maybe; quality risk real.** Quests reward answered-count, streaks, and Sure-correct. That can push speed, overconfidence, and massed grinding.

### Q10. Can readiness estimates legitimately predict exam readiness?

EXPECTED: **Not as currently constructed.** No link to official items, scaled scores, or unseen-item success. Composite of recent accuracy + sample size + local stability is a study dashboard, not a predictive model.

### Q11. Does question-level history generalize to concept mastery?

EXPECTED: **Weakly.** Coverage units are objective/topic/domain strings. Two items per domain cannot identify a concept. Repeat success on the same stem is cue-dependent recognition.

### Q12. Do source-trust penalties improve learning outcomes?

EXPECTED: **Only if sources actually differ in key accuracy.** At baseline, one original placeholder source. Penalties can starve coverage if "Watch" is the default.

### Q13. Can reaction-time signals distinguish mastery from reading speed / UI effects?

EXPECTED: **Not with the current model.** 45s slow_success and burnout drag treat latency as cognitive. Prompt length, explanation reading, and alt-tab idle (partially sanitized) remain confounds.

### Q14. Will policy governance empirically improve Smart Practice?

EXPECTED: **No, in this product shape.** Promotion thresholds need weeks of delayed outcomes and dozens of shadow decisions. Bootstrap policy is already active from legacy_migration.

### Q15. Is more analytics always more intelligence?

EXPECTED: **No.** Correlated 0–100 scores from the same events create false precision and make the utility uninterpretable.

## Precommitted ranking of where the engine is probably overbuilt vs underbuilt

OVERBUILT: concept graph, policy promotion, 40+ analytics row types, information-value overlay, knowledge-trace naming, difficulty-as-IRT-language.

UNDERBUILT: delayed retention outcomes, unseen-item first-attempt tracking, exposure/memorization control against a real bank, uncertainty on readiness, item-quality with multiple learners, blueprint-weighted coverage vs official weights.

KEEP-AS-HARMLESS-HEURISTIC (precommit): due dates, weak-retest, flag/suspend, exam mode delayed reveal, answer shuffling, autosave.

## Falsifiers we accept in advance

- If delayed unseen-item success is higher under current Smart Practice than under due+weak+coverage, Q1 weakens.
- If 7-day recall tracks retrievability better than recent accuracy, Q2 weakens.
- If Sure accuracy is well calibrated (low ECE) and predicts delayed success, Q3 weakens.
- If graph diagnoses with real edges reduce repair relapse vs no-graph, Q4 weakens.

These falsifiers require data the baseline bank cannot produce. That is itself a precommitted constraint: **no positive implementation authorization from this epoch's engine-internal data.**
