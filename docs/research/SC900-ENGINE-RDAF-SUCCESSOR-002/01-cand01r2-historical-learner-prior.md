# CAND-01R2 — Historical Learner Prior + Held-Out Policy Verification

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`
DESIGN_STATUS = `DRAFT_FOR_REVIEW`
SUPERSEDES_WITHIN_THIS_BRANCH = `00-cand01-revised-design.md`
GATE_1 = `EARNED`
GATE_2 = `DESIGN_DEFINED_NOT_YET_EARNED`
GATE_3 = `NOT_RUN`
IMPLEMENTATION_AUTHORIZED = `NO`

## Revision purpose

CAND-01R2 keeps the useful parts of CAND-01R but adds a stronger cold-start mechanism:

- use historical SY0-701 learner data to infer **how this learner tends to learn**;
- do **not** transfer Security+ knowledge claims into SC-900;
- use the historical profile only as a bounded initial prior over existing study-policy choices;
- decay that prior as direct SC-900 evidence accumulates;
- verify policy value with the held-out delayed-outcome design already defined by CAND-01R.

This is an improvement of the existing engine, not a rebuild of its due/weak/coverage machinery.

---

## Core separation

The design maintains two distinct state layers.

### A. Learner Strategy Profile — cross-exam portable

This layer describes behavioral tendencies that may plausibly generalize across certification exams.

Candidate fields include:

- `spacing_response`
- `error_recovery_rate`
- `repeat_dependence`
- `confidence_calibration`
- `unseen_item_penalty`
- `weak_drill_effectiveness`
- `delayed_recall_decay`
- `session_fatigue_pattern`
- `preferred_effective_session_length`
- `novelty_tolerance`
- `recovery_after_confident_miss`
- `massed_vs_delayed_repair_response`

These are hypotheses inferred from behavior, not permanent learner labels.

### B. Exam Knowledge Profile — exam-local only

This layer remains specific to SC-900 and must not be initialized from Security+ content mastery.

Examples:

- SC-900 objective attempts and correctness;
- SC-900 domain coverage;
- SC-900 due state;
- SC-900 active-weak state;
- SC-900 held-out outcomes;
- SC-900 item exposure;
- SC-900 source/provenance state.

### Hard prohibition

SY0-701 history must **not** directly initialize or imply:

- SC-900 objective mastery;
- SC-900 domain mastery;
- SC-900 question difficulty;
- SC-900 concept-graph edges;
- SC-900 product knowledge;
- SC-900 readiness/pass probability;
- claims such as “strong at SC-900 identity because strong at Security+ IAM.”

Cross-exam transfer is about learner strategy, not content knowledge.

---

## Historical data already supported by the 701 engine

The existing SY0-701 engine records or can derive from stored history:

- attempts, correct/wrong counts, and correctness sequence;
- correct streak;
- last seen and next review;
- selected answers;
- confidence (`Sure`, `Unsure`, `Guessed`);
- miss reason;
- flags and suspension;
- learner-memory retrievability/stability values;
- success and lapse counts;
- response-time fields where present;
- session tags / delayed or transfer tags where present;
- history events up to the persisted history limit;
- question/objective/topic/domain metadata available from the matching bank.

Derived analytics may be inspected, but CAND-01R2 should prefer recomputing portable traits from the most primitive trustworthy history available rather than treating every legacy analytics score as ground truth.

`CODE OUTPUT != SCIENTIFIC VALIDITY` remains in force.

---

## Historical-data intake protocol

The future user-data zip is treated as evidence, not source code and not repository content.

### Stage H0 — custody and privacy

- Raw learner data remains local/private.
- Do not commit the zip, raw progress files, backups, or personally identifying study history to the public repository.
- Compute hashes and a file manifest for reproducibility.
- Record only non-sensitive schema/version metadata in the research record unless the user explicitly authorizes more.

### Stage H1 — schema-only inspection before outcome analysis

Before calculating learner performance:

1. enumerate files and archive structure;
2. identify progress/history/backup files;
3. read schema/app/bank versions;
4. identify which candidate fields are actually present;
5. identify duplicate snapshots/backups so they are not double-counted;
6. identify the matching SY0-701 engine/bank revision where possible;
7. freeze the extraction map and missingness rules.

This stage should avoid choosing thresholds after seeing which choice makes the learner look better.

### Stage H2 — pre-register trait definitions

Before using the historical outcomes to choose an SC-900 policy, freeze:

- exact definition of every portable learner trait;
- minimum observation count per trait;
- contamination/missingness rules;
- which fields are descriptive only;
- policy-choice rules;
- prior strength and decay schedule;
- falsification conditions.

### Stage H3 — historical profile extraction

Only after H2 is frozen, compute the SY0-701 learner-strategy profile.

Each trait must carry:

- estimate/value;
- supporting observation count;
- uncertainty or evidence grade;
- time range;
- source files used;
- known confounds;
- whether it is safe for policy initialization.

Unsupported traits remain `INSUFFICIENT_EVIDENCE`; they must not be filled with defaults disguised as findings.

---

## Cold-start policy use

Historical data does not create a new question-selection engine. It selects the **starting mix among existing, interpretable policy choices**.

Initial candidate policy families are:

1. `SMART_PRACTICE_CHAMPION` — current Smart Practice unchanged.
2. `DWC_1` — transparent due / weak / coverage comparator from CAND-01R.
3. `SPACING_HEAVY` — existing due/spacing mechanisms emphasized, without new memory math.
4. `WEAKNESS_HEAVY` — existing active-weak mechanisms emphasized.
5. `COVERAGE_HEAVY` — existing blueprint-gap mechanisms emphasized.

These are policy configurations or bounded comparators, not five new architectures.

A historical learner profile may rank or initialize these strategies, but must not permanently lock the learner into one mode.

---

## Initialize + decay rule

The SY0-701 profile is a **cold-start prior**.

It must decay as same-exam evidence becomes available.

### Required behavior

- At SC-900 start, the historical prior may influence strategy selection because direct SC-900 evidence is sparse.
- Every eligible direct SC-900 observation reduces the relative authority of the historical prior.
- Clean delayed/held-out SC-900 evidence has greater authority than immediate repeated-item evidence.
- Once SC-900 evidence is sufficient for a trait or policy decision, that decision should be driven by SC-900 data.
- The historical profile may remain visible for audit/explanation after its decision weight reaches zero.

### Decay schedule governance

The exact numeric decay schedule must be **pre-registered after schema-only inspection but before historical outcome analysis**.

This prevents tuning the decay rule to whichever historical result looks most favorable.

The schedule must satisfy all of the following:

- bounded initial influence;
- monotonic decay;
- no increase in 701 authority after SC-900 evidence accumulates;
- hard zero or effectively zero automatic decision influence after a predeclared amount of direct SC-900 evidence;
- no decay reset merely because the learner changes devices or imports a backup;
- no content-knowledge transfer at any weight.

Gate 2 must reject a decay rule that is so slow that Security+ history can dominate mature SC-900 evidence, or so fast that the historical profile has no practical cold-start value.

---

## Policy-selection logic

The historical learner profile should answer questions such as:

- Does delayed review historically outperform immediate re-asking for this learner?
- Does repeated exposure inflate same-item success without improving later unseen/sibling success?
- Are confidence labels predictive enough to use as a secondary signal, or too noisy/gameable?
- Does performance degrade materially after a certain session length?
- Does weak-item drilling produce durable recovery or only short-term session gains?
- Is the learner especially vulnerable to cue dependence?
- Does the learner recover better from errors with spacing than with massed repair?

It should **not** answer:

- Which SC-900 domain is weak?
- Which Microsoft product is confusing?
- Which SC-900 item is difficult?
- Whether the learner is ready for the SC-900 exam.

---

## Example bounded mapping

The following is illustrative design logic, not yet an implemented rule:

- strong historical spacing benefit + weak immediate-retake durability -> initialize with higher `SPACING_HEAVY` share;
- high durable recovery from focused weak-item sessions -> initialize with higher `WEAKNESS_HEAVY` share;
- strong repeat dependence / unseen-item drop -> increase novelty/exposure controls and favor held-out verification;
- poor confidence calibration -> reduce confidence influence rather than treating `Sure` as strong evidence;
- strong fatigue after long sessions -> recommend shorter sessions without labeling slower responses as low mastery;
- insufficient or contradictory 701 evidence -> start from the neutral current champion/comparator plan.

Every mapping must later be converted into explicit, testable rules before implementation.

---

## Held-out verification remains the judge

Historical personalization is not considered successful because the policy “feels tailored.”

The CAND-01R held-out framework remains the primary verification layer:

- hard TRAIN/PROBE separation;
- clean probe contamination tracking;
- 7-day first-attempt held-out probe correctness as the primary endpoint when the bank supports it;
- 24-hour held-out outcome as secondary;
- exact-item exposure tracked separately;
- same probe rules for champion and challengers;
- `UNOBSERVED` is not treated as failure or success;
- `INCONCLUSIVE` is allowed.

The personalized initialization must earn continued use by improving direct SC-900 outcomes.

---

## New pre-registered descendant predictions

Historical P1 and CAND-01R P1R remain preserved; this revision adds descendants rather than rewriting them.

### P1R2-A — cold-start usefulness

A cross-exam learner-strategy prior derived from sufficient SY0-701 history will improve early SC-900 policy selection relative to an uninformed fixed default **only if** the inferred trait is genuinely cross-exam portable.

Falsifier: after enough comparable SC-900 evidence, historically initialized choices show no improvement or systematically worse held-out/delayed outcomes than the neutral baseline.

### P1R2-B — same-exam dominance

As clean SC-900 evidence accumulates, direct SC-900 evidence will become more predictive of SC-900 outcomes than the SY0-701 prior.

Falsifier: after the predeclared maturity threshold, the 701 prior remains materially more predictive in repeated prospective comparisons.

### P1R2-C — no content transfer

Security+ domain/question performance will not be used as evidence of SC-900 domain/question mastery.

Violation of this rule is a design defect, not a testable optimization.

---

## Gate-2 attacks added by this revision

In addition to the CAND-01R adversarial list, Gate 2 must attack:

1. **Cross-exam validity:** Are the selected learner traits actually portable, or artifacts of Security+ content/style?
2. **Version drift:** Did historical engine changes alter stored semantics over time?
3. **Backup duplication:** Are repeated backup snapshots being counted as repeated observations?
4. **Survivorship:** Does the history omit abandoned/failed sessions and therefore make strategies look better?
5. **Confidence contamination:** Did UI defaults or rewards bias confidence labels?
6. **RT confounding:** Are timing traits actually reading speed, accessibility, item length, or idle time?
7. **Question-bank memorization:** Is apparent strategy success just repeated-item familiarity?
8. **Exam-format difference:** Are Security+ and SC-900 item styles different enough to invalidate a trait?
9. **Temporal drift in learner behavior:** Is older history still representative of the learner today?
10. **Prior overreach:** Can the 701 prior override contradictory SC-900 evidence?
11. **Decay gaming:** Can import/reset behavior restore a stronger historical prior?
12. **Sparse evidence:** Does the system make strong profile claims from too few observations?
13. **Trait multiplicity:** Are many correlated learner traits creating a new version of Smart Practice complexity?
14. **Policy attribution:** Can we identify which initialized strategy caused an outcome when several mechanisms are active?
15. **Privacy/custody:** Can raw personal study history leak into commits, logs, artifacts, or public CI?

Any material unresolved item blocks positive Gate-2 closure.

---

## Complexity constraint

CAND-01R2 must not become “Smart Practice 10 with more analytics.”

The historical profile should remain small and evidence-gated.

A trait is admitted only if:

1. it can be derived reproducibly from available history;
2. it has a plausible cross-exam interpretation;
3. it can change a bounded existing policy decision;
4. its decision can later be checked against SC-900 outcomes;
5. removing it would make a distinguishable prediction.

If a trait cannot satisfy those requirements, keep it descriptive or omit it.

---

## Expected later implementation boundaries

If Gate 2 is earned and Gate 3 later authorizes implementation, the smallest architecture should add interfaces rather than duplicate the legacy engine:

- `historical_profile_reader` — read-only import/normalization of supported historical learner records;
- `learner_strategy_profile` — small portable trait model with evidence counts and uncertainty;
- `prior_decay` — explicit, deterministic authority reduction as SC-900 evidence grows;
- `policy_initializer` — bounded mapping from supported traits to existing strategy configurations;
- existing CAND-01R train/probe partition and held-out measurement components.

No raw SY0-701 learner data should be bundled into the application or repository.

---

## Non-goals

CAND-01R2 does not authorize:

- importing Security+ knowledge mastery into SC-900;
- copying the old 701 scheduler wholesale;
- inventing a universal learner type/personality;
- training a neural learner model;
- cloud telemetry;
- uploading private learner history to GitHub;
- rewriting SC-900 Smart Practice before evidence exists;
- changing CAND-02 or CAND-03;
- treating legacy analytics names as validated scientific constructs;
- implementation before Gate 2 and Gate 3 authorization.

---

## Data-package handoff

When the historical zip is supplied, the next evidence step is **not** immediate profile scoring.

The required sequence is:

1. inventory and hash the archive;
2. identify canonical history/progress files and duplicates;
3. map versions/schemas;
4. inspect field availability only;
5. freeze extraction, trait, missingness, and decay rules;
6. then compute the learner-strategy profile;
7. produce an evidence report with supported / unsupported traits;
8. use that report as an input to the Gate-2 adversarial review.

Raw data remains outside the public repository.

---

## Current decision state

`CAND_01R2_DESIGN = DEFINED_FOR_REVIEW`

`GATE_2 = NOT_YET_EARNED`

`GATE_3 = NOT_RUN`

`IMPLEMENTATION_AUTHORIZED = NO`

The next step after design approval and receipt of the historical data package is schema/custody inspection, followed by pre-registration before any outcome-driven learner profiling.