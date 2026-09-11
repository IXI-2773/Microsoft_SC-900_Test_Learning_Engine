# CAND-01 Revised Design — Held-Out Measurement + Simple Comparator Policy

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`  
DESIGN_STATUS = `DRAFT_FOR_REVIEW`  
GATE_1 = `EARNED`  
GATE_2 = `DESIGN_DEFINED_NOT_YET_EARNED`  
GATE_3 = `NOT_RUN`  
IMPLEMENTATION_AUTHORIZED = `NO`

## Authority boundary

This note revises **CAND-01 only**. It does not revise the historical Gate-1 receipts in `SC900-ENGINE-RDAF-SUCCESSOR-001`; those remain the record of what was originally proposed and why.

Design base / verified integration checkpoint:

- `checkpoint/sc900-v8.0.0-integrated-20260911`
- `00358cfdd9a4634b32d9ee77ce0a4f2bbaa7c537`

Protected frozen baseline remains:

- `sc900-v8.0.0-baseline`
- `fed4d4a44591ca93fe8428bc3ca02ec66a12f715`

No runtime code, question bank, tag, release, or production policy is changed by this design note.

---

## Revision decision

The original CAND-01 description overstated how much of the proposed scheduler was new.

The current engine already contains tested mechanisms for:

- due-review detection and prioritization;
- active-weak detection and prioritization;
- coverage-gap / blueprint-style prioritization;
- unseen-item preference;
- freshness / exact-repeat penalties;
- deterministic role allocation;
- 24-hour and 7-day delayed-outcome measurement;
- shadow-policy / challenger governance machinery.

Therefore **CAND-01 is not a request to rebuild due/weak/coverage scheduling**.

The revised candidate is:

> **CAND-01R — Held-Out Measurement + Simple Comparator Policy**
>
> Preserve current Smart Practice as the champion. Add a deliberately simple challenger assembled from existing due/weak/coverage primitives, plus hard train/probe isolation and a common delayed held-out objective. Use the comparison to determine whether the extra Smart Practice machinery adds measurable value.

The scientific question changes from:

> “Can we build a three-bucket scheduler?”

into:

> “Does current Smart Practice produce better durable unseen-item outcomes than a transparent scheduler made from the engine’s own proven core signals?”

This is an **improvement experiment**, not a rewrite.

---

## Design principles

1. **Reuse before replacement.** Existing due, weak, coverage, freshness, persistence, measurement, and governance primitives are inputs to the candidate, not targets for duplication.
2. **Champion stays intact.** Current Smart Practice remains available and unchanged while CAND-01R is evaluated.
3. **One new scientific capability at a time.** The essential new capability is uncontaminated held-out evaluation, not another pile of adaptive features.
4. **Same outcome for both policies.** Smart Practice and the comparator are judged on the same delayed probe outcome.
5. **No circular optimization.** Probe items cannot become training material, repair material, quest material, twins, or selector inputs before their scored first attempt.
6. **Complexity must earn itself.** If the champion does not outperform the simpler comparator on the pre-registered outcome, additional Smart Practice complexity has not earned a learning-effect claim.
7. **No automatic deletion.** Failure to demonstrate superiority does not immediately delete Smart Practice features; it triggers a later evidence-based simplification decision.

---

## Existing machinery to reuse

### Due

Reuse the current `is_review_due(...)` semantics and persisted review scheduling. CAND-01R does not introduce a second due-date model.

### Weak

Reuse current `is_active_weak(...)` semantics. CAND-01R does not invent another mastery or weakness scale.

### Coverage

Reuse existing objective/domain metadata and official SC-900 profile weights. Where the current engine computes coverage gaps, the comparator consumes those gaps rather than creating a second taxonomy.

### Freshness / exposure

Reuse existing exact-repeat / freshness information for training items. CAND-01R adds only the stronger rule that **probe membership overrides every training-selection path**.

### Delayed measurement

Reuse the existing delayed-outcome framework where possible: 24h/7d links, first eligible future attempt semantics, Brier/log-loss/ECE support, and persistence contracts. The new requirement is that a measurement can be explicitly labeled as a **held-out probe outcome** rather than merely a future attempt on the practiced bank.

### Governance / shadow comparison

Reuse the existing champion/challenger conceptual boundary. CAND-01R does not authorize autonomous policy promotion.

---

## New component 1 — Hard train/probe isolation

### Purpose

Prevent measurement leakage. A held-out item must remain genuinely unavailable to the training policy until its scored probe attempt.

### Partition model

A reviewed bank is partitioned into two logical sets:

- `TRAIN`: selectable for normal practice.
- `PROBE`: reserved for measurement.

The partition should be represented by a small evaluation manifest keyed by canonical question ID rather than by cloning or rewriting question objects. This keeps the canonical bank and provenance model unchanged.

### Probe exclusion contract

Before a probe’s scored first attempt, a `PROBE` item must be excluded from all of the following:

- Smart Practice normal selection;
- comparator selection;
- due review;
- weak review;
- coverage-fill selection;
- exact-repeat recovery;
- question twins;
- confusion drills;
- streak rescue / boss rounds;
- repair insertion;
- background prewarm pools;
- quests or gamification paths that inject questions;
- exam/practice builders unless the explicit activity is a designated probe event;
- analytics that would reveal the correct answer, explanation, or stem to the selector.

A probe item may still contribute **static metadata needed to construct a balanced partition** (for example domain/objective labels), but no learner outcome or answer content from that item may influence either policy before the probe is scored.

### Contamination state

If a probe item is exposed through any non-probe path before its scored first attempt, its measurement status becomes `CONTAMINATED` and it is excluded from the primary held-out endpoint. The system must not silently relabel it clean.

---

## New component 2 — Simple comparator built from existing signals

### Purpose

Create a transparent challenger with enough instructional plausibility to be a fair test, but few enough moving parts that its behavior is interpretable.

### Comparator identity

`DWC-1` = `DUE / WEAK / COVERAGE`, revision 1.

This is not marketed as “smarter” than Smart Practice. It is a control policy.

### Eligible pool

Only `TRAIN` items that are otherwise valid under the current engine’s normal safety rules are eligible. Suspended/quarantined/unapproved items stay excluded using existing semantics.

### Bucket membership

For every eligible training item:

- `DUE`: existing review-due predicate is true.
- `WEAK`: existing active-weak predicate is true.
- `COVERAGE`: item belongs to an under-covered SC-900 objective/domain according to the existing blueprint/coverage representation.

An item can satisfy multiple predicates. No new “mastery,” “difficulty,” graph, RT, confidence, source-trust, information-value, or pass-readiness signal is added to the comparator.

### Selection rule

Use deterministic round-robin service across the three buckets:

`DUE -> WEAK -> COVERAGE -> DUE -> ...`

For each bucket turn, choose the highest-priority **currently unselected** item according to the narrow bucket-specific ordering below. If that bucket has no eligible item, skip it and continue. Stop at the requested session size or pool exhaustion.

Bucket-specific ordering:

- `DUE`: oldest due timestamp first, then least-recently seen, then stable question ID.
- `WEAK`: strongest existing weak status first using the engine’s current weak ordering where available; otherwise lowest recent correctness, then least-recently seen, then stable question ID.
- `COVERAGE`: largest blueprint deficit first, then unseen before seen, then least-recently seen, then stable question ID.

No weighted sum combines the buckets.

### Fill behavior

If all three buckets are exhausted before the session is full, fill from remaining eligible `TRAIN` items using:

1. unseen first;
2. least-recently seen;
3. stable question ID.

This fallback is intentionally simple and prevents the comparator from failing merely because the learner has no due or weak items.

### Explicitly omitted from DWC-1

The comparator does **not** use:

- concept-graph diagnoses;
- information-value overlays;
- reaction time;
- confidence labels;
- gamification state;
- source-trust utility penalties except existing hard safety exclusions;
- inferred item difficulty;
- latent weakness models;
- misconception maps;
- transfer/generalization scores;
- momentum/fatigue scores;
- auto-tuned numeric policy weights.

These remain available to the champion. Their incremental value is part of what the comparison is meant to test.

---

## New component 3 — Common delayed held-out objective

### Primary outcome

**7-day first-attempt correctness on clean held-out probe items.**

A probe outcome counts for the primary endpoint only when:

- the item is `PROBE`;
- it was not exposed before the designated probe attempt;
- this is the learner’s first scored attempt on that exact item;
- the probe occurs in the pre-registered 7-day eligibility window tied to the relevant training period/objective;
- the record is otherwise valid under existing persistence/measurement checks.

### Secondary outcomes

- 24-hour held-out first-attempt correctness;
- delayed same-objective transfer on a new stem;
- exact training-item exposure count;
- domain/blueprint coverage;
- false-weakness rate;
- false-mastery rate where an existing label is available;
- time per durable gain;
- session completion/dropout as a secondary product metric only.

Immediate session accuracy, XP, streak, combo heat, questions answered, and engagement alone are **not** success criteria.

### Comparison target

Champion and challenger must be evaluated with the same probe rules. The comparator is not allowed an easier probe set, shorter delay, or different contamination rules.

---

## Experimental design choice

Three comparison structures were considered for the later implementation epoch.

### A. Alternate policies by session

**Advantage:** simplest operationally.  
**Problem:** strong carryover; one policy teaches material later measured during the other policy period.

### B. Split objectives between champion and challenger

**Advantage:** reduces direct item leakage and makes held-out probes attributable to one training policy.  
**Problem:** objective difficulty can confound policy effect.

### C. Stratified paired objective blocks — recommended

Within each SC-900 domain, reviewed objectives/item families are paired as closely as possible on available static characteristics, then one member of each pair is assigned to Smart Practice and the other to DWC-1 for the comparison period. Probe items are separately held out within each arm.

**Why recommended:** it reduces direct training contamination while avoiding a pure domain-vs-domain comparison. It still cannot create a population-level causal estimate from one learner, so results remain learner-local.

If the future bank cannot support matched blocks, Gate 2 must report `INSUFFICIENT_BANK_STRUCTURE` rather than silently falling back to a weaker design and calling it equivalent.

---

## Pre-registered CAND-01R prediction

Historical P1 remains preserved in the prior epoch. For this revision, define a narrower descendant prediction rather than rewriting P1:

### P1R

On a sufficiently large reviewed SC-900 bank with clean train/probe separation, **DWC-1 will perform within 0.05 absolute accuracy of current Smart Practice on 7-day first-attempt held-out probe correctness for this learner, unless the additional Smart Practice machinery contributes real incremental learning value.**

Interpretation:

- If Smart Practice exceeds DWC-1 by more than `0.05` and the uncertainty interval excludes `0`, the claim that simplification is equivalent is weakened.
- If DWC-1 is within `±0.05`, the engine has not demonstrated a practically important advantage from the extra selection complexity.
- If DWC-1 exceeds Smart Practice by more than `0.05` with adequate evidence, later simplification becomes a serious candidate.
- If sample size/coverage/contamination is inadequate, result = `INCONCLUSIVE`, not tie.

The `0.05` margin is inherited from the original P1 as the precommitted practical-difference threshold; this revision does not tune it after seeing outcomes.

---

## Gate-2 adversarial attacks that must be survived

CAND-01R does not earn Gate 2 merely because the design is cleaner. The dedicated Gate-2 pass must attack at least:

1. **Comparator unfairness:** Is DWC-1 intentionally too weak or accidentally advantaged?
2. **Bucket redundancy:** Do due and weak mostly select the same items, reducing the comparator to one effective bucket?
3. **Coverage starvation:** Can persistent due/weak backlog prevent blueprint coverage?
4. **Due starvation:** Can coverage cycling delay items whose review window is materially overdue?
5. **Probe leakage:** Can any repair, twin, quest, exam builder, analytics precomputation, or UI reveal contaminate probes?
6. **Objective contamination:** Can learning from one arm transfer to the matched objective in the other arm enough to destroy attribution?
7. **Small-bank instability:** At what reviewed-bank size do held-out partitions make sessions or domains unusably sparse?
8. **Blueprint imbalance:** Does the available bank support official domain proportions after probe withholding?
9. **Selection-quality confound:** Does one arm receive systematically better-written or easier questions?
10. **Time trend:** Does general improvement over weeks masquerade as a policy effect?
11. **Exposure burden:** Does holding out enough items harm ordinary study value?
12. **Multiple-choice cue dependence:** Do held-out siblings still share wording/product cues so closely that “unseen” is not meaningful transfer?
13. **One-learner limit:** Are conclusions explicitly local to this learner rather than generalized to all SC-900 learners?
14. **Missingness:** Are missed 7-day probes treated as unobserved rather than failures or successes?
15. **Complexity migration:** Does implementation of the “simple” comparator accidentally recreate Smart Practice through tie-breakers and hidden signals?

Any material unresolved attack blocks positive Gate-2 closure.

---

## Bank requirements

The current 8-item placeholder bank is **not sufficient** to run CAND-01R.

Design-time requirements for a future empirical run:

- reviewed/approved questions only;
- enough items per SC-900 domain and objective to support both training and probes;
- canonical IDs and provenance retained;
- no known exam-dump contamination;
- a pre-frozen train/probe manifest;
- enough clean 7-day probe observations to report uncertainty rather than a single accuracy percentage.

The historical P1 referenced `>=200` items. This design preserves that as the preferred target for the first serious comparison, while allowing Gate 2 to determine whether a smaller bank can support a valid pilot. A smaller pilot may test mechanics, but it must not be presented as decisive evidence of policy superiority.

---

## Failure handling

- Probe contamination -> mark measurement `CONTAMINATED`; do not silently reuse it.
- Missing 7-day observation -> `UNOBSERVED`.
- Insufficient eligible train items -> shrink the session rather than pull probe items.
- Insufficient matched objective blocks -> Gate-2 state `INSUFFICIENT_BANK_STRUCTURE`.
- Comparator bucket empty -> skip that bucket; do not synthesize fake weakness/due states.
- Existing Smart Practice failure -> record champion failure separately; do not repair it inside the comparator lane.
- Conflicting evidence -> preserve both results; do not average disagreement away.

---

## Expected later implementation boundaries

If Gate 2 is eventually earned and implementation is separately authorized, the smallest implementation should introduce focused modules/interfaces rather than enlarge `app.py`:

1. `evaluation_partition` — read-only train/probe membership and contamination state.
2. `simple_comparator_policy` — pure DWC-1 selection from snapshots using existing predicates/metadata.
3. `held_out_measurement` — label and aggregate clean probe outcomes using existing persistence/measurement primitives.
4. thin integration adapters into current session construction and governance/shadow paths.

This section is architectural guidance only. No implementation is authorized by this document.

---

## Non-goals

CAND-01R does **not** authorize:

- replacing Smart Practice;
- deleting analytics;
- changing the memory algorithm;
- changing repair behavior (CAND-02);
- changing readiness labels/probability (CAND-03);
- activating CAT, IRT, DKT, graph mining, AI items, or cloud telemetry;
- changing approved question content;
- merging the extractor with research logic;
- autonomous policy promotion;
- changing the frozen baseline or integrated checkpoint;
- claiming that simple scheduling is superior before evidence exists.

---

## Gate progression

### Gate 1

Already earned: CAND-01 was definable and measurable in principle.

### Gate 2

This revision is the **design object to attack**. Gate 2 is earned only if the comparator, probe-isolation contract, experimental structure, and measurement objective survive the adversarial checks above with no material unresolved blocker.

Current status:

`GATE_2 = NOT_YET_EARNED`

### Gate 3

Implementation readiness remains blocked until at minimum:

- Gate 2 is earned;
- a sufficiently large reviewed bank exists;
- the train/probe split is instantiable without crippling coverage;
- the evaluation plan can produce clean delayed outcomes;
- N03 prediction accountability is preserved;
- N08 self-attack has no material unresolved implementation blocker.

Current status:

`GATE_3 = NOT_RUN`  
`IMPLEMENTATION_AUTHORIZED = NO`

---

## Decision summary

**KEEP:** current Smart Practice, existing due/weak/coverage/freshness primitives, delayed measurement framework, persistence, safety exclusions, and governance boundaries.

**ADD LATER ONLY IF AUTHORIZED:** hard probe isolation, DWC-1 comparator, held-out outcome labeling/aggregation.

**MEASURE:** 7-day first-attempt held-out correctness as the primary policy-comparison objective.

**DO NOT REDO:** scheduling primitives the engine already has.

**NEXT_NODE:** adversarial Gate-2 review of this design. Do not implement runtime behavior yet.
