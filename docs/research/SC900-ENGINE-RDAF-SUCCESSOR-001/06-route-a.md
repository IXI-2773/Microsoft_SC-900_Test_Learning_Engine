# Phase 4 — Route A (PRIMARY / DIRECT / CONSTRUCTIVE)

**Question:** What does strong research suggest we should do to improve the engine?

This file is preserved **separately** from Route B. It is biased toward mechanisms with positive evidence for retention, transfer, assessment accuracy, calibration, efficiency, item quality, or persistence. It does **not** yet reconcile contrary findings.

SEARCH_INTENT: constructive "what works" in retrieval, spacing, feedback, transfer, measurement, adaptive testing, tutoring.

---

## A1. Retrieval practice / testing effect

EVIDENCE: META_ANALYTIC, REPLICATED, FOUNDATIONAL

- Roediger & Karpicke (2006), *Psychological Science* — testing > restudying for delayed retention.
- Adesope, Trevisan, & Sundararajan (2017), *Review of Educational Research*, DOI [10.3102/0034654316689306](https://doi.org/10.3102/0034654316689306) — practice tests beat restudy and other nontesting controls; moderated by test features and outcome type.
- Rowland (2014) meta-analysis — reliable testing effect; stronger with production than recognition, and when retrieval succeeds.
- Agarwal, Nunes, & Blunt (2021), *Educational Psychology Review* — classroom retrieval generally benefits learning; feedback usually present.

ENGINE IMPLICATION: Keep practice testing as the **core activity**. Do not replace answering with rereading explanations. Prefer conditions that require retrieval, not only recognition of a remembered letter.

EFFECT_DIRECTION: positive for delayed retention.  
EFFECT_SIZE: typically moderate (meta *g*/*d* often ~0.5 vs restudy; smaller vs strong elaborative controls).  
GENERALIZATION_LIMIT: many studies use prose/facts, not vendor-cert product matrices.

---

## A2. Spacing / distributed practice

EVIDENCE: META_ANALYTIC, FOUNDATIONAL, REPLICATED

- Cepeda, Pashler, Vul, Wixted, & Rohrer (2006), *Psychological Bulletin*, DOI [10.1037/0033-2909.132.3.354](https://doi.org/10.1037/0033-2909.132.3.354) — 839 assessments; optimal ISI grows with retention interval.
- Cepeda et al. (2008) expanding vs equal spacing — long-term retention favors substantial gaps, not cramming.
- Dunlosky et al. (2013) utility rating: distributed practice = high.

ENGINE IMPLICATION: Schedule re-attempts on a **delay matched to the exam horizon** (days–weeks), not only same-session follow-ups. Super-confident 120-day gaps may be too long for unstable items and too aggressive as a mastery declaration.

---

## A3. Transfer of test-enhanced learning

EVIDENCE: META_ANALYTIC

- Pan & Rickard (2018), *Psychological Bulletin*, DOI [10.1037/bul0000151](https://doi.org/10.1037/bul0000151) — transfer *d* = 0.40 vs restudy; strongest across formats / application-inference; **weakest** to untested materials and rearranged S–R. Publication-bias analyses shrink intercept when moderators are absent.
- Barnett & Ceci (2002) transfer taxonomy — near vs far.

ENGINE IMPLICATION: To claim exam readiness, measure **unseen items** (new stems, same objective), not restested exact questions. Same-item success is near transfer at best. If the bank is tiny, transfer cannot be observed.

---

## A4. Feedback (presence and timing)

EVIDENCE: META_ANALYTIC, CONTESTED ON TIMING, REPLICATED ON PRESENCE

- Feedback after retrieval improves learning vs no feedback, especially after errors (Pashler et al. 2005; Butler, Karpicke, & Roediger 2008).
- Kulik & Kulik (1988), DOI [10.3102/00346543058001079](https://doi.org/10.3102/00346543058001079) — classroom/applied: immediate often better; lab test-content: delayed often better.
- Agarwal et al. 2021: few classroom experiments manipulate delay; no-feedback effects smaller.

ENGINE IMPLICATION: Keep **immediate correctness + explanation in Practice/Smart Practice**. Keep **withheld feedback in Exam** as simulation. Do not treat delayed-feedback lab results as a mandate to hide answers during study. Do treat delayed **re-testing** as distinct from delayed **feedback**.

---

## A5. Desirable difficulties / successive relearning

EVIDENCE: FOUNDATIONAL, REPLICATED

- Bjork: difficulties that induce retrieval (spacing, variation) help later tests; they can hurt immediate performance.
- Rawson & Dunlosky: successive relearning (retrieve to criterion, then space) is efficient.

ENGINE IMPLICATION: Optimize **delayed** success, not session accuracy or XP. Criterion then space is closer to evidence than endless intra-session twins.

---

## A6. Interleaving (constructive reading)

EVIDENCE: META_ANALYTIC with **material moderators**

- Brunmair & Richter (2019), DOI [10.1037/bul0000209](https://doi.org/10.1037/bul0000209) — overall *g* = 0.42; visual categories strong; math small; **expository text ns**; **words g = −0.39** (blocking better). Helps when categories are similar between and distinct within.

ENGINE IMPLICATION: Interleave **confusable Microsoft capability families** (e.g., Entra Conditional Access vs Defender vs Purview DLP) for discrimination. Do not assume shuffling unrelated facts is "interleaving science."

---

## A7. Metacognition and confidence

EVIDENCE: FOUNDATIONAL, REPLICATED, MIXED UTILITY

- JOLs are imperfect; delayed JOLs better than immediate (Rhodes & Tauber).
- Calibration can be trained; overconfidence is common on recognition tests.
- Using confidence to **tag** guesses is reasonable; using it as a precise probability is not.

ENGINE IMPLICATION: Keep a coarse confidence tag if it is **honest and optional**. Do not let it dominate scheduling. Do not auto-stamp Sure in Exam if calibration is a goal.

---

## A8. Mastery estimation / knowledge tracing / IRT / CAT

EVIDENCE: FOUNDATIONAL in measurement; **data-hungry**

- IRT/CAT (Lord; Hambleton; van der Linden & Glas 2000) — gold standard **given a calibrated item pool**.
- BKT (Corbett & Anderson 1995) — KC-level binary skills in tutors.
- Logistic / PFA often competitive (Pelánek 2017 overview, DOI [10.1007/s11257-017-9193-2](https://doi.org/10.1007/s11257-017-9193-2)).
- Gervet, Koedinger, Schneider, & Mitchell (2020), *JEDM* — logistic regression wins on moderate/small data; DKT on large; BKT lags; **calibration of predictions matters for downstream use**.

ENGINE IMPLICATION: For a **local one-learner cert app**, a simple probability of success on unseen items in a domain, with **wide uncertainty**, is the constructive target — not DKT, not operational CAT, until a large reviewed bank and (ideally) multi-learner or strong simulation identification exist.

---

## A9. Item quality, discrimination, distractors, exposure

EVIDENCE: FOUNDATIONAL psychometrics

- Item analysis: difficulty, discrimination, distractor functioning (classical + IRT).
- Exposure control (Stocking & Lewis; Sympson–Hetter; van der Linden & Veldkamp shadow tests) — overexposed items threaten validity via memorization.

ENGINE IMPLICATION: When the bank grows, track **first-attempt** p-values and distractor choice frequencies. Penalize exact repeats. Do not call one person's wrong rate "discrimination."

---

## A10. Calibration metrics

EVIDENCE: FOUNDATIONAL

- Brier score; log loss; ECE (Guo et al. 2017 caveats on ECE with small n).
- Engine already implements Brier/log-loss/ECE with n≥20 — constructive: **use them as the readiness backend**.

---

## A11. Session length / fatigue / exam simulation

EVIDENCE: MIXED, WEAKER THAN RETRIEVAL/SPACING

- Practice tests similar in format to the criterion test help (test-potentiated learning; exam simulation).
- Fatigue/rapid-guessing harm score meaning (Wise & Kong 2005 — effort, not mastery).
- Constructive: offer SC-900-like timed blocks **without** turning every study session into a marathon.

---

## A12. Gamification (constructive)

EVIDENCE: META_ANALYTIC, HETEROGENEOUS

- Sailer & Homner (2020), DOI [10.1007/s10648-019-09498-w](https://doi.org/10.1007/s10648-019-09498-w) — cognitive *g* = 0.49, motivational 0.36, behavioral 0.25; motivational/behavioral less stable under rigor splits; fiction/social moderate behavior.

ENGINE IMPLICATION: Optional light rewards may help persistence. Tie rewards to **due reviews completed and unseen-item success**, not raw volume, if gamification is kept.

---

## A13. ITS / error-driven remediation

EVIDENCE: REPLICATED in tutors with KC models

- VanLehn (2011): step-based tutors often ≈ human tutoring on those domains.
- Requires a **real KC model**. Constructive for SC-900: **manual blueprint objectives** as KCs, not inferred graphs.

---

## Route A synthesis (before Route B)

Highest-leverage constructive moves:

1. Make **retrieval + spacing + feedback** the uncontroversial core.
2. Measure **delayed success on unseen same-objective items** as the primary outcome.
3. Shrink selection to **due / repair / coverage / novelty**, with explicit repeat-exposure control.
4. Recast readiness as a **calibrated probability with uncertainty**, using the measurement module that already exists.
5. Keep exam-mode simulation.
6. Do **not** invest in DKT/CAT/auto-graphs until data exist.

ROUTE_A_STATUS = COMPLETE_FOR_GATE_1
