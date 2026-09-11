# CAND-01R2 Historical Learner-Data Extraction Protocol

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`  
STATUS = `PRECOMMITTED_BEFORE_OUTCOME_ANALYSIS`  
GATE_2 = `NOT_YET_EARNED`  
GATE_3 = `NOT_RUN`  
IMPLEMENTATION_AUTHORIZED = `NO`

## Purpose

Freeze the rules for extracting cross-exam learner-strategy evidence from historical SY0-701 runtime data **before** inspecting learner-performance outcomes. This prevents post-hoc tuning of trait definitions to whatever happens to look favorable in one person's history.

The historical data may initialize a learner-strategy prior for SC-900. It must never transfer Security+ content mastery, domain mastery, question difficulty, concept relationships, or exam-specific readiness into SC-900.

Raw historical learner data, local paths, account identifiers, answer text, and other private material must not be committed to the public repository.

---

## Expected authoritative runtime records

The SY0-701 engine code defines runtime progress files separately from the project tree. For a frozen/package run, the user-data root is the platform-local `SecurityTestingEngine` application-data directory. Relevant runtime artifacts are expected to include some subset of:

- `*_progress.json`
- `*_session_*.json`
- `checkpoints/*_checkpoint_*.json`
- `backups/*`
- `config.json`
- `logs/security_testing_engine.log`

The authoritative learner-history source is a progress payload with question records plus its chronological `history` events. Session/checkpoint/backup files are secondary evidence used for recovery, deduplication, session boundaries, and missingness reconstruction.

Logs are **not** treated as an equivalent substitute for progress history unless a field is explicitly present and its semantics are proven from code.

---

## Schema fields allowed for cross-exam strategy extraction

Historical extraction may use these learner-behavior fields when present and structurally valid:

### Per-question progress

- attempts
- correct_count
- wrong_count
- correct_streak
- last_seen
- next_review / learner_memory.next_review_at
- last_correct
- last_confidence
- last_miss_reason
- confidence_counts
- miss_reason_counts
- flagged / suspended
- learner_memory success_count / lapse_count

`learner_memory.retrievability` and `learner_memory.stability` may be retained as **legacy-engine state descriptors only**. They are not accepted as validated latent-memory measurements.

### Chronological history events

When present:

- timestamp/day
- question identifier
- correct
- confidence
- miss_reason
- mode
- response-time fields plus contamination flag
- was_due
- was_active_weak
- session_tag
- Smart Practice role/reasons/policy identifiers
- repair-stage markers
- objective/domain labels only for within-SY0-701 stratification, never SC-900 knowledge transfer

Answer text, selected answer text, correct answer text, trap words, product names, concept keys, and Security+ objective labels are **not** features of the cross-exam learner prior.

---

## Precommitted portable traits

Only the following traits may contribute to CAND-01R2 cold-start recommendations. Each is descriptive and must carry an evidence count and missingness state.

### T1 — Delayed-retention response

Question: after an item is attempted, how does the learner perform on the **next** valid attempt of that same item at increasing time gaps?

Use non-overlapping next-attempt pairs for the same canonical question. Gap bins are frozen as:

- same day: `< 24h`
- short delay: `1–2 days`
- medium delay: `3–7 days`
- long delay: `8–30 days`
- very long: `>30 days`

Report correctness and observation count per bin. Do not fit a memory-decay curve from one learner unless a later Gate explicitly authorizes it.

### T2 — Error-recovery response

For each incorrect attempt, evaluate the learner's next valid attempt on that exact item, classified by the same delay bins as T1. Report recovery probability descriptively by delay and count.

Do not call immediate same-item improvement durable recovery.

### T3 — Seen-item dependence / unseen-item penalty

Compare first scored attempts on previously unseen questions with later attempts on previously seen questions within the same historical exam. Report raw differences plus counts.

Because item difficulty is not identified from one learner, this is a **memorization/cue-dependence warning signal**, not a causal estimate.

### T4 — Confidence reliability

For `Sure`, `Unsure`, and `Guessed`, report empirical correctness rate and count. Do not invent numeric probabilities for the labels and do not calculate ECE unless the historical record contains an actual predicted probability.

A confidence label with insufficient observations remains `INSUFFICIENT_DATA`.

### T5 — Due-review response

For history events explicitly marked `was_due`, report first-attempt correctness, lapse rate, and count. Compare descriptively with non-due attempts while preserving the confounding warning that due items are not randomly assigned.

### T6 — Weak-retest response

For events explicitly marked `was_active_weak` or an equivalent proven legacy status, report correctness and subsequent next-attempt recovery. Do not infer weakness from question topic or Security+ content.

### T7 — Session-endurance signal

Use only if explicit session boundaries/order can be reconstructed from session files or durable session identifiers. Compare early/middle/late first attempts inside completed sessions and report response-time contamination separately.

If session boundaries cannot be established without an arbitrary time-gap heuristic, T7 = `UNAVAILABLE`; do not infer a preferred session length from timestamps alone.

### T8 — Response-time quality signal

Response time may be used only for rapid-response/idle contamination and descriptive effort patterns. Slow response time is not a mastery penalty and must not be converted into cross-exam weakness.

---

## Traits explicitly prohibited from cross-exam transfer

Do not transfer:

- SY0-701 domain/topic/objective mastery
- specific question difficulty
- Security+ concept-graph relationships
- source-trust judgments tied to Security+ material
- legacy pass/readiness score
- inferred item quality from one learner
- product or vendor knowledge assumptions
- graph diagnoses
- raw Smart Practice utility values as if they were learning effects
- any claim that IAM/Security+ success means Entra/SC-900 mastery

---

## Missingness and data-quality rules

Every portable trait must return one of:

- `SUPPORTED_BY_HISTORY`
- `TENTATIVE`
- `INSUFFICIENT_DATA`
- `UNAVAILABLE`
- `CONTAMINATED`

Minimum descriptive thresholds are precommitted as follows:

- `<5` relevant observations: `INSUFFICIENT_DATA`
- `5–14`: `TENTATIVE`
- `>=15`: eligible for `SUPPORTED_BY_HISTORY`, subject to contamination and representation checks

These thresholds are engineering guardrails, not claims of statistical power.

Duplicate backups/checkpoints must be deduplicated before counting observations. Recovered copies of the same event must not multiply evidence.

Missing delayed observations are `UNOBSERVED`, never counted as incorrect or correct.

Malformed timestamps, impossible chronological order, or unknown schema fields that change event semantics trigger `CONTAMINATED` for the affected trait until resolved.

---

## Historical prior authority and decay

The SY0-701 prior may recommend the **initial** SC-900 strategy but cannot permanently control it.

Authority stages are frozen as:

### SEED

Before 10 clean SC-900 held-out probe outcomes, supported historical traits may choose or rank the initial study-policy recommendation.

### ADVISORY

From 10 through 29 clean SC-900 held-out probe outcomes, historical evidence may act only as a tie-breaker when direct SC-900 evidence is inconclusive. It cannot override a clear SC-900 signal.

### RETIRED

At 30 clean SC-900 held-out 7-day probe outcomes, provided the observations cover all four SC-900 domains with at least 4 observations per domain, the SY0-701 prior loses decision authority. It remains archived for research/audit only.

If the coverage condition is not met, the prior remains `ADVISORY`; it does not regain `SEED` authority.

This stage rule is intentionally coarse to avoid fake precision from a numerically weighted cross-exam prior.

---

## How historical traits may influence the initial strategy

Historical evidence may select among **existing or separately approved** strategy variants; it does not create a new hidden optimizer.

Allowed initial recommendations include:

- current Smart Practice champion
- DWC-1 due/weak/coverage comparator
- a spacing-heavier configuration built only from already-approved scheduling controls
- a weak-recovery-heavier configuration built only from already-approved controls
- a novelty/coverage-heavier configuration built only from already-approved controls

A historical recommendation is a starting hypothesis, not a promotion decision.

Examples of precommitted interpretation:

- strong seen-item advantage plus weaker first-attempt unseen performance -> increase the priority of held-out/novel evaluation; do not reward more exact-item repetition
- stronger recovery at delayed rather than immediate retest -> prefer spacing over same-session repetition
- high lapse rate on explicitly due items -> preserve/increase due-service priority
- supported weak-retest recovery -> preserve weak-bucket service
- poor confidence reliability -> do not give confidence extra policy authority
- unavailable trait -> no policy consequence

No single trait can delete Smart Practice or promote DWC-1.

---

## Outcome-analysis sequence

After this protocol is frozen, process a private historical package in this exact order:

1. custody receipt and archive hash outside the public repo;
2. safe inventory; reject traversal/encryption/bomb-like archive behavior;
3. identify authoritative progress/session/checkpoint/backup candidates;
4. determine schema/app/bank versions without inspecting learner outcomes;
5. deduplicate backup/recovery copies;
6. verify field availability against this protocol;
7. only then compute T1–T8;
8. produce a private learner-strategy profile containing aggregate traits/counts only;
9. commit only non-private methodological findings to the research branch;
10. submit the resulting prior to Gate-2 adversarial review before runtime use.

---

## First supplied package — structural disposition

The first supplied archive for this epoch is structurally a project/release package. It includes source/build/release material and a log under the project-local `user_data/logs` path, but no authoritative `*_progress.json`, saved session JSON, checkpoint JSON, or backup JSON artifacts were present in the archive inventory.

Therefore:

`HISTORICAL_PROFILE_STATUS = BLOCKED_RUNTIME_DATA_REQUIRED`

The log may be used later for corroboration of versions/events, but it does not by itself satisfy the historical-profile evidence contract.

No learner-performance profile is computed from this package.

---

## Gate consequence

This protocol does not earn Gate 2. It only prevents post-hoc trait construction and defines what evidence is required.

`GATE_2 = NOT_YET_EARNED`  
`IMPLEMENTATION_AUTHORIZED = NO`
