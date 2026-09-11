# Phase 8 — Open-World / Omitted-Mechanism Search

Question: what important mechanisms are **neither** already in the engine **nor** in the initial taxonomy as operationalized?

Adjacent fields searched at title/abstract level: cognitive psychology, educational measurement, human factors, decision science, behavioral science, memory science, psychometrics, ITS, HCI, learning analytics, causal inference, recommender explore/exploit (transfer only where legitimate).

## Omitted or under-operationalized families

### O1. Held-out / two-bank evaluation (measurement leakage control)

Engine tests the items it trains on. Psychometrics and ML both require a **criterion sample that was not trained**. Omitted as a first-class loop: freeze a probe set; never use it for Smart Practice selection; score first-attempt.

### O2. Blueprint-constrained assembly (not CAT)

Official weights 10–15 / 25–30 / 35–40 / 20–25 exist in `cert_profile_sc900.json` but do not constrain session assembly like a form blueprint. Shadow-test **idea** (constraints) can be used **without** IRT: enforce domain quotas. Omitted as a hard constraint.

### O3. Successive relearning to criterion, then space

Rawson & Dunlosky: retrieve until success, then drop until a planned ISI. Engine instead keeps inserting twins without a criterion-then-wait policy.

### O4. Pretesting / test-potentiated learning

Taking a test **before** studying can enhance later encoding. Engine always assumes bank items are "practice of known material." A new-item first-attempt is a pretest but is not used as an encoding event by design.

### O5. Transfer-appropriate processing / format match with a twist

Exam is MC. Practice is MC — good match — but **changing the stem** matters more than changing the letter order. Engine shuffles choices, not paraphrases. Paraphrase/item-cloning is **not** recommended as AI generation this epoch (quality unknown); the omitted **measurement** is paraphrase-equivalent items from human authors.

### O6. Rapid-guessing as data filter, not skill

Wise & Kong: filter or flag sub-reading-time responses. Engine sanitizes idle/long RT more than ultra-fast guesses as a validity filter on **learning estimates**.

### O7. Decision-label risk / choice architecture

How "Likely ready" is framed (traffic lights, medals at 70%) is a behavioral intervention. Omitted: treat UI claims as **experimental treatments** with harm potential.

### O8. Coverage vs mastery tradeoff as explicit explore/exploit

Recommenders: popularity bias analog is "re-ask weak seen items." UCB-style **uncertainty bonus for uncovered objectives** is only weakly present as unseen_bonus. Omitted: explicit objective-level exploration until each blueprint cell has a first-attempt.

### O9. Causal item-key review, not statistical quality at n=1

Human expert key check beats one-user discrimination. Ingestion/review lane exists in repo but is **out of subject**; still, engine-research omitted linking **readiness claims** to "bank not expert-reviewed at scale."

### O10. Accessibility as a validity facet

Time and RT-based grades can fail WCAG-aligned use. Omitted from Smart Practice policy.

### O11. Forgetting aligned to **exam date**, not generic stability

Cepeda: ISI should track retention interval. Engine has no exam-date input. Omitted scheduler parameter: days-until-exam.

### O12. Error type that is actually diagnostic for SC-900

Product-confusion (Entra vs Azure AD naming, Sentinel vs Defender, Purview vs 365 compliance) is the real misconception family. Trap-word regex (`best`, `except`) is test-wiseness. Omitted: a **small manual confusion table** for Microsoft naming, not a general graph.

### O13. Self-explanation / why-the-wrong-is-wrong without extra items

Prompting a one-sentence explanation after feedback can help (sometimes). Engine shows explanations; it does not require generation (and should not force it for accessibility). Omitted as optional, not a feature mandate.

### O14. Session-level stopping when learning rate drops for the **right reason**

Fatigue stop vs "accuracy dropped because items got harder." Engine burnout cannot tell. Omitted: stop rules based on **rapid guesses** and time-on-task, not accuracy vs difficulty mix.

## Open-world verdict

The largest omissions are **evaluative** (held-out items, first-attempt, exam-date spacing, blueprint quotas, claim-as-treatment), not new AI/graph/CAT subsystems.

OPEN_WORLD_FINDINGS = O1–O14 as above. Highest material: O1, O2, O7, O11, O12.
