# CAND-01R2 Profile-Informed Revision — RRC-1 Comparator

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`  
STATUS = `PROFILE_INFORMED_DESIGN_REVISION`  
GATE_2 = `NOT_YET_EARNED`  
GATE_3 = `NOT_RUN`  
IMPLEMENTATION_AUTHORIZED = `NO`

## Purpose

Use the private historical learner-profile extraction to improve the CAND-01R2 design **without publishing personal learner outcomes** and without re-creating machinery the engine already has.

The private profile is not committed. This note records only design consequences that are safe and necessary for the candidate architecture.

## Finding 1 — DWC-1 contains avoidable bucket redundancy

The historical runtime state shows that the engine's existing `is_review_due(...)` and `is_active_weak(...)` predicates frequently describe the same event state. This is unsurprising from the legacy scheduling semantics: an error can simultaneously create active weakness and an immediate/near-term review obligation.

Therefore the earlier DWC-1 round robin:

`DUE -> WEAK -> COVERAGE`

is not as clean a three-way comparator as intended. Even though exact questions are not selected twice in a session, separate DUE and WEAK turns can repeatedly draw from substantially the same recovery pool. That can unintentionally double-weight one semantic need and make the comparator less interpretable.

### Revision

DWC-1 is retained as historical design evidence but is **superseded for Gate-2 review** by:

> **RRC-1 — REPAIR / REVIEW / COVERAGE**

The classes are mutually exclusive by precedence.

### RRC-1 class assignment

For every eligible `TRAIN` item:

1. `REPAIR` — existing `is_active_weak(...)` is true. This class owns the item even if it is also due.
2. `REVIEW` — not in `REPAIR`, and existing `is_review_due(...)` is true.
3. `COVERAGE` — not in `REPAIR` or `REVIEW`, and the item serves an under-covered SC-900 objective/domain according to the existing blueprint representation.

An item belongs to at most one service class for a selection snapshot.

### RRC-1 service rule

Use deterministic round-robin service:

`REPAIR -> REVIEW -> COVERAGE -> REPAIR -> ...`

If a class is empty, skip it. Stop at requested session size or eligible-pool exhaustion.

Within classes:

- `REPAIR`: use existing weak-state ordering where already defined; otherwise lowest recent correctness, then least-recently seen, then stable question ID.
- `REVIEW`: oldest due timestamp first, then least-recently seen, then stable question ID.
- `COVERAGE`: largest existing blueprint deficit first, then unseen before seen, then least-recently seen, then stable question ID.

Fallback after all service classes are exhausted remains:

1. unseen training item;
2. least-recently seen;
3. stable question ID.

No weighted utility is introduced.

## Finding 2 — held-out novelty remains essential

The historical profile contains enough evidence of repeat/seen-item advantage to make exact-item familiarity a material threat to interpreting local accuracy as learning.

Design consequence:

- keep hard `TRAIN` / `PROBE` isolation;
- keep unseen/held-out performance as the judge;
- do not promote a policy because it raises repeated-bank accuracy;
- maintain exact-item exposure counts as a required secondary outcome.

This strengthens rather than replaces the original CAND-01R held-out design.

## Finding 3 — confidence must remain low-authority

Historical confidence labels are directionally informative but not sufficiently reliable to justify aggressive scheduler authority in this candidate.

Design consequence for CAND-01R2:

- RRC-1 does not use confidence as a service-class input or tie-breaker;
- historical confidence is descriptive context only for CAND-01;
- any later change to confidence-driven memory suppression belongs to CAND-02/CAND-03 or a separately authorized candidate.

## Finding 4 — response time is contamination/effort evidence, not mastery

A material subset of historical timing records is explicitly contaminated by idle/outlier behavior. Clean records also show that slower answers cannot safely be interpreted as lower knowledge without confounding item difficulty, reading behavior, and other factors.

Design consequence:

- RRC-1 does not use response time;
- response time may only flag contamination/effort quality in this candidate;
- the legacy `slow_success` interpretation is not imported into the cross-exam prior.

## Finding 5 — session endurance is useful but not mature enough for a hard rule

Explicit completed-session histories show a possible late-session performance decline, but the number of independently reconstructed completed sessions is limited.

Design consequence:

- preserve session-endurance as a **TENTATIVE** learner-strategy trait;
- it may initialize a conservative session-size recommendation;
- it must not hard-code a permanent limit or alter question mastery;
- SC-900 session outcomes must confirm or reject it.

## Cold-start decision after private profile extraction

The historical profile does **not** justify replacing current Smart Practice.

For CAND-01R2, the recommended initial experimental structure is now:

- `SMART_PRACTICE_CHAMPION` — current engine, unchanged;
- `RRC_1_CHALLENGER` — mutually exclusive repair / review / coverage comparator;
- common hard train/probe isolation;
- common delayed held-out outcome;
- historical learner profile used only as a SEED prior for starting emphasis;
- direct SC-900 evidence takes authority according to the frozen SEED / ADVISORY / RETIRED rule.

The earlier five-way family list remains a design universe, not five simultaneous active policies. For the first controlled comparison, **do not activate multiple challengers at once**. That would destroy attribution and rebuild Smart Practice complexity under different names.

## Gate-2 consequence

The profile resolves or narrows several attacks:

- duplicate-backup inflation is controllable through canonical-history selection;
- due/weak redundancy is addressed by RRC-1 mutual exclusivity;
- confidence overreach is blocked from comparator logic;
- RT confounding is blocked from comparator logic;
- memorization risk is directly addressed by held-out probes;
- trait multiplicity is constrained by using one challenger, not a portfolio optimizer.

Material attacks remain for Gate 2:

1. cross-exam strategy portability cannot be assumed merely because historical evidence is strong;
2. RRC-1 must be checked against SC-900 bank sparsity and official blueprint balance;
3. train/probe isolation must be proven against every existing question-injection path;
4. objective-family leakage between train and probe must be bounded;
5. the historical prior must be demonstrated to decay exactly as precommitted;
6. the first SC-900 comparison still needs enough reviewed items to support held-out evaluation.

Therefore:

`GATE_2 = NOT_YET_EARNED`

`GATE_2_NEXT = ADVERSARIAL_REVIEW_OF_RRC1_AND_PROBE_ISOLATION`

`IMPLEMENTATION_AUTHORIZED = NO`
