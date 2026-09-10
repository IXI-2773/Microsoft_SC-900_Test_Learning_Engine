# Phase 4 — Route B (CONTRARIAN / ADVERSARIAL / EPISTEMIC-DEEP)

**Question:** What if our existing assumptions about adaptive learning and this engine are wrong?

SEARCH_INTENT: null results, small effects, boundary conditions, replication problems, measurement leakage, memorization, false mastery, gaming, RT confounding, instability, over-personalization, simple methods beating elaborate ones, graph overclaim, difficulty/item confound, readiness-induced overconfidence.

This file is preserved **separately** from Route A. Disagreements are not averaged here.

---

## B1. Adaptive / complex models often fail to beat simple ones

EVIDENCE: RECENT, REPLICATED IN EDM, CONTESTED COMMERCIAL CLAIMS

- Gervet, Koedinger, Schneider, & Mitchell (2020), *JEDM* — DKT overfits small data; logistic regression leads on moderate datasets; original DKT AUC gains were inflated (Xiong et al. 2016). Khajah et al. 2016 and Wilson et al. 2016: BKT+/IRT extensions can match DKT.
- Pelánek (2017; methodological follow-ons) — metric computation details inflate "wins"; no universal best learner model; context (purpose, data, knowledge type) dominates.

ATTACK ON ENGINE: Smart Practice 9 + 40 analytics maps is a **complexity bet** without a loss function. At n_persons=1 it is exactly the regime where simple models win. Policy governance cannot rescue this: promotion data will never exist locally.

---

## B2. Retrieval practice is weaker for multiple-choice / when retrieval fails / for untested material

EVIDENCE: META_ANALYTIC MODERATORS, NOT A NULL OF TESTING

- Rowland 2014: smaller effects for recognition than production.
- Pan & Rickard 2018: transfer weakest to **untested materials**; PET-PEESE intercepts often imply **no positive transfer** when helpful moderators are absent.
- MC practice can teach the **answer option**, not the concept (cue dependence; recognition vs recall — Martinez and related assessment literature).

ATTACK: The engine's main loop *is* MC recognition of a finite bank. Optimizing same-item accuracy can produce **false mastery** relative to SC-900's unseen official items. Follow-up twins worsen cue dependence.

---

## B3. Spacing can be mistuned; massed practice wins immediately

EVIDENCE: FOUNDATIONAL, REPLICATED

- Cepeda et al.: wrong ISI for the retention interval hurts. Very long gaps → forgetting before restudy.
- Learners and products prefer massed schedules because **session scores look better**.

ATTACK: Intra-session repair chains (twins, confusion drills, boss rounds, streak rescue) are **massed**. Super-confident 120-day delay can exceed the stability the item actually has. The engine simultaneously mass-practices errors and over-spaces "Sure" items.

---

## B4. Interleaving can hurt

EVIDENCE: META_ANALYTIC BOUNDARY

- Brunmair & Richter 2019: words *g* = −0.39 for interleaving; expository text nonsignificant. Effect depends on between-category similarity.

ATTACK: Topic-shuffle interleaving of unrelated SC-900 facts may **add switching cost without discrimination benefit**. Variety-as-quality-score (set_quality) can **override** weak-repair items in the name of topic diversity (partially guarded, but the objective exists).

---

## B5. Feedback delay is not a resolved "more science = delay it" story

EVIDENCE: CONTESTED META

- Kulik & Kulik 1988: direction **reverses** by setting (classroom immediate vs lab delayed).
- Students often ignore delayed feedback; processing is the mediator.

ATTACK: Do not "improve" the engine by hiding explanations in study mode based on lab delayed-feedback effects. Conversely, exam-mode default confidence=Sure **invents metacognitive data**.

---

## B6. Confidence reports are noisy and gameable

EVIDENCE: FOUNDATIONAL METACOGNITION; ENGINE-SPECIFIC ANOMALY

- Immediate JOLs after seeing the answer are contaminated.
- Quests reward `sure_correct` — incentive to tap Sure.
- Exam path writes Sure automatically.

ATTACK: Confidence as a first-class scheduler input can encode **UI incentives**, not knowledge. Calibration tables in analytics can look "scientific" while the data-generating process is biased.

---

## B7. Response time is not a mastery thermometer

EVIDENCE: PSYCHOMETRIC RT / EFFORT, NOT SKILL

- Wise & Kong (2005), DOI [10.1207/s15324818ame1802_2](https://doi.org/10.1207/s15324818ame1802_2) — rapid responses index **effort** (guessing before reading), not high skill.
- Item length, accessibility, bilingual reading, and UI lag dominate slow times.
- Engine `slow_success` at ≥45s **penalizes careful readers**. Burnout uses RT drag.

ATTACK: Using RT to flatten difficulty or reduce memory credit risks discriminating against slower, more accurate processing — the opposite of exam-readiness for a reading-heavy MC test.

---

## B8. Item "difficulty" and "quality" from one person are not identified

EVIDENCE: FOUNDATIONAL MEASUREMENT

- Classical item analysis and IRT require a **sample of persons**.
- High miss rate can be: hard item, bad key, misread stem, weak learner, or overexposure fatigue.

ATTACK: `DifficultyCalibrationRow` and `question_quality_record` **cannot** do what their names claim on this product shape. Acting on them (skip "bad" items, treat as hard stretch) can remove the items the learner most needs or the items that are merely mis-keyed.

---

## B9. Concept graphs infer relations the data do not support

EVIDENCE: PRACTICAL + THEORETICAL

- Expert KC models in ITS are expensive and still often low quality (Gervet et al.: expert KCs sometimes add little).
- Co-error graphs pick up item wording, not prerequisites.
- Engine runtime **does not even add edges** — so the sophisticated diagnosis API is mostly dead code, which is safer than a wrong graph, but the **utility still names graph pressure**.

ATTACK: Either the graph is inert (wasted complexity) or, if auto-filled later, likely **wrong**. Do not "activate" edge mining as an improvement without external prerequisite evidence.

---

## B10. Readiness scores create false confidence

EVIDENCE: STANDARDS + DECISION SCIENCE

- AERA/APA/NCME *Standards*: validity is for **specified interpretations**. A study heuristic labeled "Likely ready" invites an exam-pass interpretation the README disclaims and the UI still suggests.
- Overconfidence literature: coarse labels move decisions.
- Sample_strength uses 180 attempts — grinding more questions **raises the score mechanically**.

ATTACK: The pass predictor is an engagement/coverage dashboard with an exam-speech act. That is a **validity threat**, not a missing feature.

---

## B11. Practice-test memorization / exposure

EVIDENCE: CAT EXPOSURE CONTROL LITERATURE; CERT-PREP ECOLOGY

- Overexposed items in adaptive tests leak. Stocking–Lewis / shadow-test machinery exists because **adaptation concentrates on informative items**, which humans then memorize.
- Certification prep culture includes dumps. A "smart" selector that re-asks high-utility seen items is a **dump trainer**.

ATTACK: Smart Practice's freshness penalty is a start; it still optimizes the learner's **seen bank**, not a hidden exam. Without held-out items, every adaptive policy overfits.

---

## B12. Gamification can undermine learning quality

EVIDENCE: META HETEROGENEITY + MOTIVATION

- Sailer & Homner: motivational/behavioral effects **unstable** under rigor; cognitive effect not well explained by design factors.
- Points/badges can reduce intrinsic motivation (Deci; Mekler et al. 2017 mixed/null on performance).
- Engine quests: answered_total, streaks, sure_correct — classic **Goodhart** metrics.

ATTACK: Boss rounds and combo heat can increase speed and Sure-tapping. Optional disable exists — good — but defaults matter.

---

## B13. Repair chains vs simple restudy/retrieval

EVIDENCE: WEAK FOR ELABORATE DIAGNOSIS; STRONG FOR FEEDBACK+RETRIEVE

- Elaborative feedback helps some tasks and can waste time on others (length/attention).
- Without a validated misconception library, "repair" is **repeat the item or a similar item**.

ATTACK: Confusion-pair drills may help if pairs are true confusions. If they are lexical trap-word matches, they train test-wiseness. Near-miss heuristics can chase phrasing.

---

## B14. False precision of many 0–100 scores

EVIDENCE: MEASUREMENT + EDM METHODOLOGY

- ECE unreliable with small n / few bins (Guo et al. caveats; engine uses 5 bins, min 20 — still one person).
- Pelánek: how you average metrics changes winners.

ATTACK: Analytics payload TypedDicts (50+ row types) create an **illusion of instrumentation**. Downstream Smart Practice then treats them as independent causes.

---

## B15. Accessibility / UX effects on "performance"

EVIDENCE: HUMAN FACTORS (DIRECTIONAL)

Font scaling, dense-answer mode, overlay toasts, auto-next, and RT scoring interact. A learner using larger fonts or reading explanations carefully looks "slow" and "fatigued."

ATTACK: Adaptation on RT/fatigue can encode **interface preference** as skill.

---

## Route B synthesis (before reconciliation)

Load-bearing doubts that survive this route:

1. Current Smart Practice is **not justified** as a learning optimizer.
2. Memory + streak "mastery" **overclaims** durability.
3. Readiness **misleads** more than it measures.
4. Graph, KT-by-name, item-quality, and difficulty are **measurement theater** at this data scale.
5. Follow-ups and gamification can **fight** spacing and honest confidence.
6. The constructive core (retrieve, space, feedback, simulate exam, cover blueprint, hold out unseen items) does **not** require the current machinery.

ROUTE_B_STATUS = COMPLETE_FOR_GATE_1  
ROUTE_B does **not** say "delete the engine." It says: **do not authorize more machinery until simpler policies are tested on delayed unseen-item outcomes.** Fail-closed: lack of support ≠ automatic removal; classify as heuristic / measurement risk / complexity debt.
