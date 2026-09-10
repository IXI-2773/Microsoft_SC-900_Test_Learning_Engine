# Phase 9–11 + Gate 1 — Claims, Measurement, Candidates, Checkpoint

IMPLEMENTATION_AUTHORIZED = NO  
GATE_2 = NOT_RUN  
GATE_3 = NOT_RUN  

Consequential claims use KNOWN / SUPPORTED / PLAUSIBLE / SPECULATIVE / UNKNOWN — not a single fake confidence number.

---

## Measurement requirements (Phase 10)

Do not recommend an improvement that cannot be evaluated. Preferred outcomes for any later experiment:

- 24-hour and 7-day **first-attempt success on items not used in the last 7 days**
- first-attempt success on **held-out** items (never selected by the policy)
- delayed transfer: new stem, same objective_code
- Brier, log loss, ECE of whatever readiness probability is shown
- false-mastery: items labeled mastered/super-confident that fail delayed unseen siblings
- false-weakness: items tagged weak that succeed on first-attempt unseen siblings
- repair relapse after ≥1 day
- exact-question exposure count
- domain coverage vs official weight bands
- time per durable gain (hours to +Δ 7-day held-out accuracy)
- session completion / dropout only as **secondary**, never as success

Avoid optimizing: immediate accuracy, XP, questions answered, combo heat.

The baseline 8-item bank **cannot host these outcomes**. A later epoch needs a reviewed bank **and** a held-out split. Extractor lane is not absorbed here.

---

## Claim / argument / evidence (Phase 9) — load-bearing claims only

### CLAIM C1

CLAIM = A much simpler due/weak/coverage selector is a serious successor candidate relative to Smart Practice 9.  
ARGUMENT = Evidence families attach to those three buckets; extra maps are unidentified and correlated; EDM shows simple models winning at small data.  
SUPPORTING_EVIDENCE = Cepeda 2006; Adesope 2017; Gervet 2020; Pelánek 2017; engine reconstruction (empty graph, unused Brier, 50+ knobs).  
CONTRARY_EVIDENCE = None showing *this* utility wins; ITS literature shows *good* KC-adaptive systems can help **with real KCs**.  
SOURCE_QUALITY = META_ANALYTIC + RECENT EDM + reconstruction KNOWN  
ASSUMPTIONS = SC-900 practice remains MC; bank will grow; one primary learner.  
UNCERTAINTY = Effect size vs current utility UNKNOWN  
GENERALIZATION_LIMIT = Not a claim that personalization never works.  
EXPECTED_ENGINE_EFFECT = Equal or better 7-day held-out accuracy; lower complexity  
MEASURABLE_OUTCOME = A/B or within-learner alternating policies on held-out accuracy  
FALSIFICATION_CONDITION = Current Smart Practice beats 3-bucket by >0.05 held-out 7-day accuracy with 95% interval excluding 0  
STATUS = SUPPORTED as a **candidate**, not as a proven win

### CLAIM C2

CLAIM = The current pass-predictor must not be interpreted as exam readiness.  
ARGUMENT = Validity is interpretation-specific; no link to Microsoft items or scaled scores; grinding and seen-item accuracy inflate the number; labels are speech acts.  
SUPPORTING_EVIDENCE = AERA/APA/NCME Standards; Pan & Rickard transfer limits; engine formula in `_build_pass_prediction`; profile disclaimer vs UI label.  
CONTRARY_EVIDENCE = Practice-test scores sometimes correlate with later exams **when items are representative** — not shown here.  
STATUS = SUPPORTED as a validity threat  
FALSIFICATION = Prospective correlation with official SC-900 outcomes after controlling for study time and dump overlap — data we do not have

### CLAIM C3

CLAIM = Immediate error twins are more likely massed practice than optimal repair.  
ARGUMENT = Spacing metas favor ISI matched to delay; twins occupy next slots.  
SUPPORTING_EVIDENCE = Cepeda 2006; desirable-difficulty immediate vs delayed split  
CONTRARY_EVIDENCE = Immediate restudy after error can correct the trace (feedback literature)  
STATUS = PLAUSIBLE  
FALSIFICATION = Immediate twins improve 7-day unseen-sibling success vs next-day new item

---

## Candidate portfolio (Phase 11)

### CAND-01 — Held-out delayed-retrieval objective + 3-bucket scheduler

NAME = Measurement-first practice policy (due / weak / blueprint coverage + novelty cap)  
CURRENT_PROBLEM = Smart Practice 9 cannot be shown to optimize durable unseen success; utility is unidentifiable  
EVIDENCE_BASIS = C1; Route A A1–A3; Route B B1/B2/B11  
PROPOSED_MECHANISM = Split bank into train/probe; select from train only with quotas: due, active-weak, under-covered official domain; never reselect exact item until freshness threshold; score probe first-attempts  
EXPECTED_BENEFIT = Aligns practice with retrieval+spacing+coverage; makes readiness evaluable  
EXPECTED_EFFECT_MAGNITUDE_IF_ESTIMABLE = UNKNOWN vs current; family effects moderate in labs  
IMPLEMENTATION_COMPLEXITY = Moderate (policy shrink + split) — **not authorized now**  
VALIDATION_COMPLEXITY = Moderate once bank ≥ ~80–200 items  
RISK = Learners dislike fewer "smart" features  
INTERACTION_RISK = Follow-up inserters can break the split if they pull probe items  
REVERSIBILITY = High (policy switch)  
REQUIRED_DATA = Larger reviewed bank; timestamps already exist  
PRIVACY_IMPACT = None (local)  
COMPATIBILITY_WITH_CURRENT_V8 = Can live beside Smart Practice as a shadow policy **later**; governance already has shadow slots  
DEPENDENCIES = Bank growth (not this package)  
SMALLEST_TESTABLE_VERSION = Offline replay of stored history scoring 3-bucket vs logged Smart Practice picks (still weak) then a within-app toggle  
GO / HOLD / REJECT / MORE_RESEARCH = **GO as design candidate** / HOLD implementation

### CAND-02 — Time-aware memory + next-day unseen sibling instead of immediate twin

NAME = Criterion-then-space repair  
CURRENT_PROBLEM = Memory ignores clock; follow-ups mass errors; Mastered/super-confident overclaim  
EVIDENCE_BASIS = Cepeda; Rawson & Dunlosky; C3  
PROPOSED_MECHANISM = After error: show feedback (keep immediate explanation); schedule a **different** item of same objective ≥1 day later; decay retrievability with elapsed time; cap super-confident  
EXPECTED_BENEFIT = Durable repair, less cue dependence  
MAGNITUDE = PLAUSIBLE moderate on delayed measures  
IMPLEMENTATION_COMPLEXITY = Moderate  
VALIDATION_COMPLEXITY = Needs 7-day outcomes  
RISK = Session feels less "responsive"  
INTERACTION_RISK = Quests that want immediate recovery hits  
REVERSIBILITY = High  
REQUIRED_DATA = objective_code already present  
PRIVACY_IMPACT = None  
COMPATIBILITY_WITH_CURRENT_V8 = Follow-up insert path would need later change  
DEPENDENCIES = CAND-01 measurement  
SMALLEST_TESTABLE_VERSION = Disable immediate twins; keep delayed probes at 1 day via due dates (not slot+3)  
GO/HOLD = **GO as design candidate** / HOLD implementation

### CAND-03 — Honest readiness: calibrated held-out probability + uncertainty; retire "Likely ready"

NAME = Criterion-referenced study forecast  
CURRENT_PROBLEM = False precision / false exam speech act  
EVIDENCE_BASIS = C2; N07; measurement module already has Brier/ECE unused by the predictor  
PROPOSED_MECHANISM = Report P̂(correct on held-out items) with interval or "insufficient data"; domain bars vs blueprint; never map to 700 scaled  
EXPECTED_BENEFIT = Calibration; reduced false confidence (P5)  
MAGNITUDE = SPECULATIVE on behavior; SUPPORTED as validity  
IMPLEMENTATION_COMPLEXITY = Low–moderate (mostly presentation + which number)  
VALIDATION_COMPLEXITY = ECE/Brier on probes; min n issues remain  
RISK = Product looks "less sure"  
INTERACTION_RISK = Medals at 70% still imply pass  
REVERSIBILITY = High  
REQUIRED_DATA = Probe outcomes  
PRIVACY_IMPACT = None  
COMPATIBILITY_WITH_CURRENT_V8 = PassPrediction TypedDict would change meaning later  
SMALLEST_TESTABLE_VERSION = Rename labels + show sample size and disclaimer as the only number change  
GO/HOLD = **GO as design candidate** / HOLD implementation

### CAND-04 — Blueprint-quota session assembly

NAME = Official-weight coverage constraints  
PROBLEM = Role shares ≠ SC-900 domain weights  
EVIDENCE = Open-world O2; profile already has weights  
MECHANISM = Hard quotas per domain in each n=40/50 set  
BENEFIT = Exam-representative practice mix  
MAGNITUDE = PLAUSIBLE for coverage, UNKNOWN for scores  
COMPLEXITY = Low  
RISK = Starves weak domain if bank unbalanced (placeholder is 2/domain — OK)  
REVERSIBILITY = High  
GO/HOLD = **GO as design candidate** / HOLD implementation  
Note: 8-item bank already balanced; value appears after ingestion

### CAND-05 — Rapid-guess filter + stop using slow RT as weak learning

NAME = RT as effort/idle only  
PROBLEM = slow_success and burnout encode reading speed  
EVIDENCE = Wise & Kong; N04  
COMPLEXITY = Low  
PRIVACY = None  
GO/HOLD = **GO as design candidate** (small) / HOLD implementation

### CAND-06 — Manual SC-900 product-confusion table (not a graph engine)

NAME = Named-concept contrast list  
PROBLEM = Trap-word regex ≠ Microsoft product confusions; graph edges empty  
EVIDENCE = O12; Brunmair similarity-between-categories  
COMPLEXITY = Low content, not a new subsystem  
RISK = Wrong pairs  
MORE_RESEARCH on which pairs; **not** auto-graph  
GO/HOLD = **MORE_RESEARCH** (content authority) then small design

### CAND-07 — Exam-date ISI

NAME = Retention-interval-aware spacing  
EVIDENCE = Cepeda joint ISI×RI  
COMPLEXITY = Low  
DEPENDENCIES = user-entered exam date (privacy: local only)  
GO/HOLD = **MORE_RESEARCH** on default if date missing

---

## Held / rejected

CANDIDATES_HELD =

- FSRS/SM-2 import (flashcard mismatch)
- Manual prerequisite graph (until SC-900 pedagogues supply one)
- Gamification retargeting (quests → due/held-out) — interesting, not top-3
- Shadow-policy governance activation — unreachable N; do not build cloud A/B

CANDIDATES_REJECTED (this epoch) =

- DKT / neural KT
- Operational IRT/CAT
- Auto-mined concept graph
- AI question generation
- Cloud telemetry / multi-user item calibration network
- RDAF workflow inside the study app
- Autonomous policy promotion
- Removing retrieval practice
- Removing exam mode
- Removing persistence/quarantine
- Automatic deletion of gamification (classify: heuristic + Goodhart risk, compare later)

---

## Prioritization

Rank by expected learning/reliability value, not novelty.

### TOP_3_HIGHEST_VALUE_IMPROVEMENTS

1. **CAND-01** — 3-bucket + held-out delayed objective (replaces Smart Practice as *optimizer*, not necessarily as UI name)
2. **CAND-02** — time-aware repair (space the next retrieval; stop massed twins as default)
3. **CAND-03** — honest calibrated readiness (stop false exam claims)

CAND-04 and CAND-05 are high-value **small** adjuncts if a later implementation epoch is authorized. They are not in the top 3 because 04 needs a real bank and 05 is local validity hygiene.

Prefer: high benefit + strong evidence + reversible experiment  
Over: high complexity + weak evidence

---

## Three-gate status

### GATE 1 — CONSTRUCTIVE MATURITY

Question: Is there enough research evidence to **define** one or more serious successor design candidates?

Answer: **YES.** CAND-01–03 are defined, measurable in principle, evidence-backed at the family level, and explicitly not implemented.

Caveat: they are **not** proven superior inside this engine. Bank n=8 blocks empirical confirmation. That does not block Gate 1; it blocks Gate 3.

GATE_1 = EARNED  
FINAL STATUS = `GATE_1_EARNED_DESIGN_REQUIRED`

### GATE 2 — ADVERSARIAL SURVIVAL

NOT_RUN. Route B already lists surviving attacks. A true Gate 2 needs a dedicated adversarial pass **on the candidate mechanisms** (3-bucket, delayed sibling repair, held-out calibration), including simpler competitors and boundary conditions, after candidates are specified in a design note. This tranche must not force Gate 2.

### GATE 3 — IMPLEMENTATION READINESS

NOT_RUN. N03 predictions unscored; N08 still active; no measurable in-engine experiment possible on placeholder bank; no authorization.

---

## Fail-closed notes

- Insufficient evidence on current utility's learning effect → MORE_RESEARCH, not "rewrite this week."
- Features lacking scientific support were classified (heuristic / measurement risk / complexity debt / compare), **not** auto-removed.
- Literature contradictions are recorded; baseline runtime is **untouched**.

---

## Next logical node

NEXT_LOGICAL_NODE =

1. Keep `research/sc900-engine-rdaf-001` unmerged.
2. Do **not** implement CAND-01–03.
3. When a reviewed bank exists (extractor lane remains separate), open epoch `SC900-RDAF-EPOCH-…-002` for **Gate 2** on CAND-01–03: pre-register P1–P6, specify the 3-bucket algorithm in a design-only note, and plan a reversible local comparison on 7-day held-out first-attempt accuracy.
4. Gate 3 only if Gate 2 survives and measurement requirements are instantiable.

STOP.
