# SC900-ENGINE-RDAF-SUCCESSOR-002 — Pre-Gate-2 Authority

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-002`  
AUTHORITY_STATUS = `CURRENT_PRE_GATE2_DESIGN`  
GATE_1 = `EARNED`  
GATE_2 = `NOT_RUN`  
GATE_3 = `NOT_RUN`  
IMPLEMENTATION_AUTHORIZED = `NO`

## Purpose

This file is the single authority map for the CAND-01 successor revision immediately before Gate 2. Earlier files in this directory are preserved as design/evidence receipts and must not be read as competing current specifications.

The project goal is improvement, not reimplementation: reuse the engine's proven software mechanisms, test whether additional Smart Practice complexity adds durable learning value, and add only the measurement/personalization capabilities that are genuinely missing.

## Current authoritative candidate

> **CAND-01R2 — Historical Learner Prior + Held-Out Policy Verification**

The current design consists of four coupled elements:

1. **Smart Practice champion remains unchanged.** The existing engine is the incumbent policy and is not rewritten merely to create an experiment.
2. **RRC-1 challenger.** The simple comparator uses mutually exclusive `REPAIR / REVIEW / COVERAGE` service classes built from existing engine predicates and blueprint metadata. `REPAIR` owns active-weak items even when due; `REVIEW` contains due items not in repair; `COVERAGE` contains remaining eligible items serving under-covered blueprint units. This supersedes the earlier overlapping DWC-1 `DUE / WEAK / COVERAGE` comparator.
3. **Hard TRAIN / PROBE isolation.** Held-out probe items are excluded from all training, repair, twin, quest, exam-builder, prewarm, and answer-revealing paths until their designated scored first attempt. Exposure outside the probe path marks the observation `CONTAMINATED`.
4. **Historical learner-strategy prior with decay.** SY0-701 runtime history may initialize exam-independent strategy tendencies only. It never transfers Security+ content/domain mastery into SC-900. Its authority is `SEED` before 10 clean SC-900 probes, `ADVISORY` at 10–29, and `RETIRED` at 30 clean 7-day probes with all-domain coverage as frozen in the extraction protocol.

## Primary outcome

The common primary endpoint for champion and challenger is:

**7-day first-attempt correctness on clean held-out SC-900 probe items.**

Immediate repeated-bank accuracy, XP, streaks, answer count, and engagement are not primary success criteria.

## Current prediction

Historical Gate-1 P1 remains immutable. The DWC-1-specific P1R in `00-cand01-revised-design.md` is preserved as an intermediate design receipt and is superseded prospectively by:

### P1R2

On a sufficiently large reviewed SC-900 bank with clean TRAIN/PROBE separation, **RRC-1 will perform within 0.05 absolute accuracy of current Smart Practice on 7-day first-attempt held-out probe correctness for this learner unless the additional Smart Practice machinery contributes practically important incremental learning value.**

Let `Δ = SmartPractice_accuracy - RRC1_accuracy`.

- Smart Practice practical superiority: the uncertainty interval for `Δ` lies entirely above `+0.05`.
- RRC-1 practical superiority: the interval lies entirely below `-0.05`.
- Practical equivalence: the interval lies entirely inside `[-0.05, +0.05]`.
- Every other result is `INCONCLUSIVE`.

The `0.05` margin is inherited from historical P1 and is not retuned after outcomes are observed.

## Historical learner-profile consequence

A private SY0-701 runtime archive was processed under the precommitted extraction protocol. Raw history, answer text, question-level records, local paths, and private aggregate values remain outside the public repository.

The allowed non-private design consequences are:

- preserve due/review service;
- preserve weak-item repair service while requiring delayed verification rather than treating immediate recovery as durable;
- protect unseen/held-out evaluation because repeat familiarity is a material validity threat;
- keep confidence low-authority for CAND-01R2;
- use response time only for contamination/effort quality, never as a mastery penalty;
- treat session-endurance behavior as tentative and subject to direct SC-900 confirmation.

These consequences initialize hypotheses only. Direct SC-900 evidence must supersede the historical prior under the frozen decay rule.

## Authority map

- `00-cand01-revised-design.md` — historical CAND-01R/DWC-1 design receipt; **superseded for current comparator authority**.
- `01-cand01r2-historical-learner-prior.md` — historical introduction of cross-exam learner-prior concept; retained as design lineage.
- `02-historical-data-extraction-protocol.md` — **normative precommitment** for allowed traits, missingness, privacy, and SEED/ADVISORY/RETIRED decay.
- `03-runtime-archive-disposition.md` — evidence-custody/schema disposition for the supplied runtime archive.
- `04-profile-informed-cand01r2-revision.md` — **current detailed RRC-1 design consequences** derived after the frozen protocol was applied.
- `README.md` — **current authority map and operative pre-Gate-2 summary**.

If wording conflicts, this authority order applies:

`README.md` → `04` → `02` → `03` → `01` → `00`, while the original Gate-1 receipts in `SC900-ENGINE-RDAF-SUCCESSOR-001` remain historically immutable.

## Frozen boundaries before Gate 2

Gate 2 may challenge the design but must not silently alter these boundaries:

- no runtime implementation is authorized;
- Smart Practice remains champion during the evaluation design;
- only one challenger, RRC-1, is active in the first comparison;
- no Security+ content mastery transfers into SC-900;
- no raw/private learner history enters the public repository;
- probe contamination fails closed;
- missing delayed outcomes are `UNOBSERVED`, not failures or successes;
- confidence and response time do not enter RRC-1 scheduling;
- the historical prior cannot regain authority after reaching a later decay stage;
- no automatic policy promotion occurs.

## Gate-2 entry target

Gate 2 begins from this authority state and must adversarially test at minimum:

- RRC-1 fairness and whether mutual exclusivity actually removes due/weak double-counting;
- starvation behavior across repair, review, and coverage;
- every possible probe-leakage/question-injection path;
- train/probe objective-family leakage and cue overlap;
- reviewed-bank sparsity and blueprint balance after withholding probes;
- selection-quality and time-trend confounding;
- portability limits of the historical learner prior;
- exact enforcement of SEED/ADVISORY/RETIRED authority decay;
- one-learner generalization limits;
- whether any supposedly simple tie-breaker recreates Smart Practice complexity.

Any material unresolved attack blocks positive Gate-2 closure.

`GATE_2_NEXT = ADVERSARIAL_REVIEW_OF_CAND01R2_RRC1_AND_PROBE_ISOLATION`  
`IMPLEMENTATION_AUTHORIZED = NO`
