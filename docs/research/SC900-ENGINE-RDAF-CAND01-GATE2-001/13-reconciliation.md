# Reconciliation

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Constructive Findings

CAND-01R2 improves the prior design in several ways:

- RRC-1 replaces overlapping DWC-1 buckets with mutually exclusive precedence.
- Smart Practice remains the unchanged champion, avoiding an unnecessary rewrite.
- The primary endpoint is delayed held-out correctness, not repeated-bank score.
- Historical SY0-701 evidence is constrained to strategy tendencies and decays.
- Missing and contaminated observations are explicitly separated from failures.

These are real design improvements.

## Adversarial Findings

Positive Gate 2 closure still fails:

- current runtime has no all-path partition boundary;
- current bank is only eight placeholder questions;
- semantic/objective leakage is unresolved;
- RRC-1 starvation and service fairness need explicit reporting/safeguards;
- arm allocation and selection-quality confounds cannot be evaluated without a real reviewed bank;
- cross-exam prior portability remains plausible but unproven;
- noetic N02, N06, N07, and N08 remain material and unresolved.

## Required Design Revisions Before Gate 2 Can Be Reopened

1. Define an implementation-ready partition boundary that every selector, injector, restore, prewarm, render, analytics, and export path must call.
2. Define a probe-family ontology: exact item, same objective, same template, same source wording, same answer-option structure, and semantic paraphrase.
3. Define RRC-1 starvation metrics: rolling class share, maximum overdue delay, coverage starvation flag, and invalid-comparison conditions.
4. Define arm allocation rules for Smart Practice and RRC-1 using matched objective families and source/provenance balance.
5. Define clean-probe counting tests for SEED / ADVISORY / RETIRED monotonicity.
6. Obtain or build a sufficiently large reviewed SC-900 bank; preserve `>=200` as the serious comparison target unless a later document justifies a different target without claiming decisiveness.

## Reconciled Conclusion

CAND-01R2 survives as a research direction but not as a Gate-2-earned design. The correct disposition is fail-closed on bank structure and isolation proof.