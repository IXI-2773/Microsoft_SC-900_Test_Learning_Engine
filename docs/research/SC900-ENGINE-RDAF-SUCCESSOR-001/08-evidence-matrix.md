# Phase 6 — Current Engine ↔ Research Evidence Matrix

Each row: one major mechanism. CODE COVERAGE ≠ VALIDITY.

KEEP / MODIFY / REPLACE / REMOVE / RESEARCH_MORE are **design dispositions for a later implementation epoch**, not authorization to edit runtime now.

---

### 1. Smart Practice selection (utility + roles)

ENGINE_CAPABILITY = 8-component utility, 5 roles, variety retry, policy version smart-practice-9  
INTENDED_LEARNING_MECHANISM = allocate practice among due, weak, coverage, transfer, stretch  
CURRENT_IMPLEMENTATION = `smart_practice_core` + profile knobs + analytics maps  
CURRENT_TEST_EVIDENCE = role mix, variety, freshness, screenshots — **behavioral**  
EXTERNAL_EVIDENCE = retrieval/spacing/coverage are supported **as families**; linear utility of 8+50 knobs is not  
EFFECT_DIRECTION = unknown vs simple 3-bucket scheduler  
EFFECT_SIZE_IF_KNOWN = n/a  
CONFIDENCE = low that current form is optimal  
BOUNDARY_CONDITIONS = tiny bank; one learner; correlated signals  
CONTRADICTORY_EVIDENCE = Gervet 2020; Pelánek 2017 — simple models win at small data  
CURRENT_ASSUMPTION_STATUS = WEAKENED  
DISPOSITION = **MODIFY** (shrink to few evidence-backed terms) / RESEARCH_MORE vs simple baseline  
RATIONALE = complexity debt + measurement risk; not automatic removal

---

### 2. Forgetting / memory scheduling

ENGINE_CAPABILITY = retrievability/stability accumulators + grade→days  
INTENDED = spaced retrieval  
CURRENT_IMPLEMENTATION = `update_learner_memory`; no exp(-t/S)  
TEST_EVIDENCE = due dates, recovery ladder, super-confident 120d  
EXTERNAL = Cepeda 2006/2008 strong for spacing; SM-2/FSRS are **schedulers**, weaker as theory  
EFFECT_DIRECTION = spacing family positive; this parameterization UNVERIFIED  
CONFIDENCE = medium that *some* delay helps; low that these numbers are right  
CONTRADICTORY = massed same-session follow-ups; 120d freeze  
STATUS = WEAKENED as durable-memory measure  
DISPOSITION = **MODIFY** toward explicit time + delayed outcomes; RESEARCH_MORE vs FSRS-like  
RATIONALE = theoretically supported family, heuristic instance

---

### 3. Mastery estimation / knowledge tracing

ENGINE_CAPABILITY = named knowledge_trace with fixed Bayes likelihoods; streak "Mastered"  
INTENDED = P(know)  
IMPLEMENTATION = prior 0.38, confidence-conditional likelihoods, no parameter fit  
TEST_EVIDENCE = rows exist and sort  
EXTERNAL = BKT/PFA/IRT exist; engine is not those models  
CONTRADICTORY = prestige naming; one person  
STATUS = WEAKENED / misnamed  
DISPOSITION = **REPLACE** user-facing "mastery_prob" with uncertain domain success; keep internal heuristic if needed  
RATIONALE = measurement risk

---

### 4. Question difficulty

ENGINE_CAPABILITY = Hard/Moderate/Stable from this learner's misses  
INTENDED = item difficulty  
EXTERNAL = IRT/CTT need persons  
STATUS = REJECTED as item difficulty; KEEP as "struggle flag" if renamed  
DISPOSITION = **MODIFY** (rename; do not drive stretch as if IRT *b*)

---

### 5. Question discrimination / quality

ENGINE_CAPABILITY = quality statuses; min samples 10/20  
INTENDED = item analysis  
EXTERNAL = real discrimination is across persons  
STATUS = INERT at baseline; UNVERIFIED when n_persons=1  
DISPOSITION = **HOLD** until multi-attempt **and** preferably multi-learner or expert review; do not auto-drop items

---

### 6. Distractor quality

ENGINE_CAPABILITY = wrong-answer families, trap words, recycling tempting choices  
INTENDED = misconception contrast  
EXTERNAL = distractor analysis is psychometric; contrastive examples help some discrimination learning  
CONTRADICTORY = trap-word drills may teach test-wiseness  
DISPOSITION = **RESEARCH_MORE**; KEEP as harmless contrast practice if not overweighted

---

### 7. Misconception repair / repair chains

ENGINE_CAPABILITY = weak role, follow-up twins/confusion/delayed probes  
INTENDED = error-driven remediation  
EXTERNAL = feedback + later retrieval supported; elaborate diagnosis not  
CONTRADICTORY = massing; cue dependence  
DISPOSITION = **MODIFY** — prefer **spaced** re-retrieval and unseen siblings over immediate twins as default

---

### 8. Concept graph

ENGINE_CAPABILITY = graph schema + diagnose_root_cause  
IMPLEMENTATION = nodes from questions; **edges not generated in app**  
TEST_EVIDENCE = isolated graph tests inject edges  
EXTERNAL = KC models valuable when real; inferred graphs dangerous  
STATUS = complexity debt; currently mostly inert  
DISPOSITION = **KEEP schema, do not activate auto-edges**; RESEARCH_MORE for **manual** SC-900 prerequisite list if ever needed  
RATIONALE = fail-closed: do not remove files this tranche; do not build RDAF-graph product

---

### 9. Response-time use

ENGINE_CAPABILITY = sanitize RT; slow_success; burnout drag; latency rows  
INTENDED = effort/mastery/fatigue  
EXTERNAL = Wise & Kong: RT as **effort/rapid-guess**, not skill  
CONTRADICTORY = 45s penalty; accessibility  
DISPOSITION = **MODIFY** — use RT only for rapid-guess / idle contamination (already partly there); stop using slow RT as weak memory

---

### 10. Confidence use

ENGINE_CAPABILITY = Sure/Unsure/Guessed; quests; exam default Sure  
INTENDED = metacognitive calibration + grading  
EXTERNAL = coarse JOLs can help tagging guesses; poor as probabilities; incentives bias  
DISPOSITION = **MODIFY** — stop exam Sure-stamp; stop Sure-quest coupling; keep optional tag  
STATUS = WEAKENED as adaptation weight

---

### 11. Readiness prediction

ENGINE_CAPABILITY = pass predictor 0–100 + labels  
INTENDED = exam readiness  
EXTERNAL = validity requires specified criterion; no official-item link  
CONTRADICTORY = grinding raises sample_strength; disclaimer vs label  
DISPOSITION = **REPLACE** interpretation: calibrated P(success on held-out bank items) with uncertainty; never imply Microsoft scaled score  
STATUS = REJECTED as exam-pass predictor; KEEP as study dashboard if renamed

---

### 12. Adaptive test generation (session construction)

ENGINE_CAPABILITY = offline set builder, not CAT  
EXTERNAL = CAT needs calibrated pool + exposure control  
DISPOSITION = **KEEP** session builder; **REJECT** operational CAT this epoch  
RESEARCH_MORE = blueprint-weighted coverage (official 10–15 / 25–30 / 35–40 / 20–25)

---

### 13. Session length / fatigue

ENGINE_CAPABILITY = burnout row; fatigue_cost; count 10/20/40/50  
EXTERNAL = weaker than retrieval; fatigue real but mis-measured via RT  
DISPOSITION = **KEEP** user-chosen length; **MODIFY** burnout so it does not over-flatten based on RT

---

### 14. Interleaving / variety

ENGINE_CAPABILITY = interleave + set quality variety targets  
EXTERNAL = Brunmair & Richter: material-dependent; can be negative  
DISPOSITION = **MODIFY** — interleave **confusable pairs**, not generic topic shuffle as quality

---

### 15. Spacing (due review mode)

ENGINE_CAPABILITY = Due review pool  
EXTERNAL = strong family support  
DISPOSITION = **KEEP** (high value, low complexity)

---

### 16. Feedback timing

ENGINE_CAPABILITY = immediate in practice; hidden in exam  
EXTERNAL = presence strong; delay contested  
DISPOSITION = **KEEP** this split

---

### 17. Repeat exposure

ENGINE_CAPABILITY = freshness penalty, cooldown, super-confident skip  
EXTERNAL = exposure control literature; memorization risk  
DISPOSITION = **KEEP and strengthen** against exact-item repeats; measure first-attempt unseen

---

### 18. Exam simulation

ENGINE_CAPABILITY = Exam mode, no reveal, force finish  
EXTERNAL = format similarity helps; practice-test validity still needs representative items  
DISPOSITION = **KEEP**; do not treat exam % as Microsoft score

---

### 19. Gamification / quests

ENGINE_CAPABILITY = XP, medals, 22 quests, boss rounds  
EXTERNAL = small heterogeneous effects; Goodhart risk  
DISPOSITION = **KEEP optional**; RESEARCH_MORE on default-on; do not add more game loops

---

### 20. Source trust penalties

ENGINE_CAPABILITY = conflict/decayed warnings + utility penalty  
EXTERNAL = none that penalties improve *learning*; item-key accuracy matters  
DISPOSITION = **KEEP warnings**; **HOLD** strong selection penalties until sources actually conflict in a real bank

---

### 21. Policy governance / shadow promotion

ENGINE_CAPABILITY = full promotion/rollback/drift  
EXTERNAL = A/B in products needs N; local learner cannot  
DISPOSITION = **KEEP as dormant code** this tranche; do not build autonomous experimentation (non-goal). Complexity debt.

---

### 22. Autosave / resume / quarantine

ENGINE_CAPABILITY = persistence, checkpoints, corrupt-file quarantine  
EXTERNAL = n/a (software reliability)  
DISPOSITION = **KEEP** — not a learning-science object

---

### 23. Adaptive answer order

ENGINE_CAPABILITY = reshuffle choices after attempts  
EXTERNAL = reduces letter-memory; good for measurement of the *item*  
DISPOSITION = **KEEP**

---

### 24. Progress/history

ENGINE_CAPABILITY = 4000 events, per-item stats  
DISPOSITION = **KEEP**; add held-out / first-attempt flags in a later epoch (not now)

---

## Matrix-level verdict

ASSUMPTIONS_SUPPORTED (family-level): retrieval practice; spacing; feedback presence; exam-format practice; reducing exact-item letter memory; due/weak filters.

ASSUMPTIONS_WEAKENED: current utility as optimizer; memory as durability; confidence/RT as skill; interleaving-as-generic-variety; repair chains; gamification defaults; source-trust selection penalties.

ASSUMPTIONS_REJECTED (as stated): difficulty = item difficulty; knowledge_trace = KT; readiness = exam pass probability; graph diagnoses operate in production; item quality/discrimination estimable from one learner; policy promotion is an empirical loop in this app.
