# SC-900 Answer-Length Leakage Repair Design

**Date:** 2026-09-17  
**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001`  
**Repository:** `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`  
**Design base:** `main` at `23d440b6976b9f6bbb3b77285bf0d11effc2513f`

## 1. Purpose

Reduce exploitable answer-length cues in the production SC-900 question bank without degrading factual correctness, distractor quality, learner-history integrity, question identity, or exam/runtime semantics.

The current bank exhibits a material pattern in which the correct choice is disproportionately the longest option. A learner can therefore gain an artificial advantage from answer formatting rather than SC-900 knowledge.

The repair must improve the bank semantically, not cosmetically. It must not equalize option lengths mechanically, pad distractors with filler, shorten correct answers into ambiguity, or change answer keys merely to improve statistics.

## 2. Baseline and strong acceptance target

The existing read-only audit established the following baseline over analyzable single-answer questions:

- strict longest correct: `291 / 449 = 64.81%`;
- correct among longest: `303 / 449 = 67.48%`;
- unique-longest heuristic success: `291 / 431 = 67.52%`;
- mean correct-answer length: `60.15` characters;
- mean longest-distractor length: `41.21` characters.

The final strong acceptance target is:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
NO_MATERIAL_SHORTEST_ANSWER_LEAKAGE
NO_MATERIAL_POSITIONAL_ANSWER_LEAKAGE
ALL_SEMANTIC_REVIEWS = PASS
BANK_INTEGRITY = PASS
FULL_REGRESSION = PASS
```

These are acceptance gates, not optimization objectives. The system must never sacrifice factual or pedagogical quality merely to drive a number downward.

## 3. Scope

### In scope

- deterministic answer-length leakage analysis for the final 454-question bank;
- ranking of strongest leakage outliers;
- bounded semantic rewriting of affected answer choices;
- Microsoft Learn verification when wording changes materially affect meaning;
- per-tranche before/after leakage reports;
- domain-level and bank-level bias checks;
- regression protection against future answer-length leakage;
- preservation checks for question identity and learner-history behavior.

### Out of scope

- UI work from PR #32;
- changes to scoring, Smart Practice selection, readiness, analytics semantics, exam eligibility, or confidence controls;
- changes to question count;
- changes to canonical IDs;
- changes to correct-answer keys unless separately justified and explicitly authorized outside this work package;
- changes to Core / Applied / Stretch tier assignment;
- changes to objective codes;
- CAND-01R3 scientific work or PR #13;
- recovery refs;
- production EXE refresh until all approved content work is integrated and consolidated-main verification passes.

## 4. Isolation and governance

This work is independent of the open UI repair.

```text
PR32 = UI REPAIR ONLY
ANSWER_LENGTH_REPAIR = SEPARATE BRANCH / PR SERIES
PR13 = UNTOUCHED / UNMERGED
RECOVERY_REFS = UNTOUCHED
PRODUCTION_EXE = UNTOUCHED UNTIL FINAL CONTENT INTEGRATION
```

Protected authorities remain:

- `research/sc900-cand01r3-measurement-001` at `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb`;
- `recovery/publish-exact-history/sc900-v8-20260910` at `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2`;
- `recovery/publish-sc900-v8-exact-history` at `bbc3bd900b73bde89151dc51706ad62fc69e8196`.

No implementation package may mutate, merge, delete, rebase, or retarget those authorities.

## 5. Repair strategy

The bank will be repaired in multiple bounded tranches rather than one large rewrite. Each tranche will target approximately 40-60 questions, prioritizing the strongest leakage cases first. A tranche may be smaller when semantic review burden is high.

Each tranche must stop after its own verification and external review. No later tranche is automatically authorized by the success of an earlier one.

### Per-question repair order

For each flagged question, use the following order:

1. **Tighten an unnecessarily verbose correct choice** if the same fact can be expressed more directly without losing required qualification.
2. **Strengthen unrealistically terse distractors** with plausible SC-900 concepts when doing so improves authenticity and remains clearly incorrect.
3. **Rebalance both sides** when the cue comes from a combination of verbose correct wording and weak distractors.
4. **Leave the question unchanged** if removing the cue would require ambiguity, filler, unsupported claims, or a substantive answer-key change.

Forbidden techniques:

- padding distractors with meaningless words;
- forcing all four options to equal character counts;
- introducing vague qualifiers only to alter length;
- changing the correct answer to satisfy statistics;
- copying Microsoft Practice Assessment wording or protected third-party question text;
- changing question difficulty or scope unintentionally.

## 6. Factual authority and semantic review

Microsoft Learn remains the factual authority for SC-900 content.

A wording edit is classified as either:

- **mechanical wording:** grammar, concision, duplicated phrasing, or equivalent wording that does not alter substantive meaning;
- **semantic wording:** an edit that changes, adds, removes, narrows, or broadens a product capability, scope condition, role, licensing implication, architectural relationship, or other factual claim.

Mechanical wording may be reviewed against the existing governed source context. Semantic wording must be checked against current official Microsoft Learn documentation before admission.

For every edited question, review must establish:

- prompt meaning preserved;
- original correct option remains correct;
- every distractor remains incorrect under the prompt as written;
- no distractor becomes partly correct or conditionally correct without the condition being represented;
- explanation remains consistent with the edited choices;
- objective and tier remain appropriate;
- no new stylistic clue is introduced.

If the reviewer cannot establish those points confidently, the question fails closed and remains unchanged until resolved.

## 7. Identity and learner-history preservation

The content repair must preserve stable question identity and runtime compatibility.

Every tranche must prove:

```text
QUESTION_COUNT = 454
QUESTION_IDS_CHANGED = 0
QUESTION_IDS_ADDED = 0
QUESTION_IDS_REMOVED = 0
CORRECT_KEYS_CHANGED = 0
OBJECTIVE_CODES_CHANGED = 0
TIERS_CHANGED = 0
EXAM_ELIGIBILITY_CHANGED = 0
```

Choice-text edits may legitimately alter content fingerprints. The implementation plan must therefore identify the repository's existing content-fingerprint, migration, progress-history, session-resume, and saved-state behavior and add regression coverage proving that approved wording changes do not silently orphan learner history.

If the current architecture treats wording changes as identity-breaking in a way that cannot be reconciled safely within existing migration semantics, implementation must stop and return that conflict for review rather than inventing a new identity system inside this package.

## 8. Leakage audit design

The permanent audit should be deterministic and produce machine-readable and human-readable results.

At minimum it must calculate:

- character and word length for every answer choice;
- whether the correct answer is strictly longest;
- whether the correct answer is tied for longest;
- whether the correct answer is strictly shortest;
- unique-longest heuristic success;
- unique-shortest heuristic success;
- correct-answer letter distribution overall and by domain;
- length-gap magnitude between correct answer and strongest distractor;
- per-domain strict-longest rates;
- list of worst outliers ordered by leakage severity.

The audit should not treat a one-character difference as pedagogically equivalent to an extreme 80-character gap. Severity should account for both absolute and relative separation so human review focuses on meaningful cues first.

The audit itself is read-only. It must never rewrite bank content automatically.

## 9. Bias substitution safeguards

Reducing longest-answer leakage must not create a replacement shortcut.

Each tranche must check at least:

- strict-longest correct rate;
- unique-longest heuristic success;
- strict-shortest correct rate;
- unique-shortest heuristic success;
- A/B/C/D correct-letter distribution;
- per-domain versions of the above where sample size is meaningful;
- extreme correct-vs-distractor length gaps.

A tranche fails if it materially improves the longest-answer metric by creating a new shortest-answer or positional bias.

No fixed target is imposed for natural average option length. Natural language variation is allowed and desirable. The goal is to remove a predictive cue, not make answer choices visually uniform.

## 10. Tranche admission gates

Each tranche must pass three independent layers before merge authorization can even be considered.

### Gate A — Mechanical integrity

- valid bank schema;
- exactly 454 questions;
- stable canonical IDs;
- unchanged correct keys;
- unchanged objective codes, tiers, and eligibility;
- bank lint pass with no new unexpected warnings;
- duplicate/equivalence checks pass;
- no unintended files changed;
- protected refs unchanged.

### Gate B — Semantic integrity

For every edited question:

- before/after diff reviewed;
- factual authority sufficient;
- correct option still uniquely defensible;
- distractors plausible but clearly incorrect;
- explanation consistent;
- no artificial filler or ambiguity.

### Gate C — Statistical integrity

- tranche leakage metrics improve or remain neutral for justified questions;
- bank-wide leakage moves toward the strong target;
- no material shortest-answer substitution;
- no material letter-position substitution;
- no domain is made materially worse without an explicit documented reason.

Passing the statistical gate alone is never sufficient.

## 11. Tranche sequencing

### Tranche 1 — strongest outliers

Target the highest-severity leakage cases first, using the deterministic audit ranking. Prefer approximately 40-60 questions, but reduce scope if semantic review becomes difficult.

Primary goal: prove the repair method, review process, history-preservation checks, and audit tooling on a bounded set.

### Later tranches

Recompute the audit from the newly accepted bank after each tranche. Do not reuse stale rankings. Continue selecting the strongest remaining leakage cases until the final acceptance gates are reached or remaining cases cannot be safely changed.

If the bank reaches a point where further statistical improvement would require lower-quality content, stop and report the residual metric rather than forcing the target.

## 12. Testing strategy

The implementation plan must use test-first development for all new audit/gating behavior.

Required regression classes include:

1. audit detects known synthetic longest-answer leakage;
2. audit detects shortest-answer substitution;
3. audit detects answer-letter distribution anomalies;
4. audit ordering of severe outliers is deterministic;
5. bank invariants fail when IDs, keys, tiers, objective codes, eligibility, or count change;
6. learner-history/session behavior remains valid across approved wording-only bank revisions;
7. existing runtime bank loading and session creation continue to pass;
8. final full repository regression passes.

Synthetic fixtures should be used for audit logic tests so the test suite does not depend on hard-coding the current production leakage defects as permanent truth.

## 13. Review artifacts

Every tranche should produce a review artifact containing:

- source bank SHA-256;
- candidate bank SHA-256;
- edited question IDs;
- before/after option text for each edited question;
- whether each edit was mechanical or semantic;
- factual authority references for semantic edits;
- unchanged-key/identity/tier/eligibility attestation;
- baseline and candidate leakage metrics;
- per-domain metrics;
- shortest-answer and letter-position checks;
- worst remaining leakage outliers;
- focused and full test results.

These artifacts exist to make content review possible without trusting a summary statement.

## 14. Merge and release model

No tranche is auto-merged. Each tranche requires external review and exact-head authorization.

After a tranche merge:

1. verify exact merge commit on `main`;
2. run consolidated-main CI;
3. recompute leakage metrics from `main`;
4. only then select the next tranche.

The repository-root Windows executable is not refreshed after every content drafting step. It is refreshed only after the approved content integration point and consolidated-main verification, using the established deterministic Windows release process.

## 15. Failure and stop conditions

Fail closed and stop when any of the following occurs:

- an edit would change a correct-answer key;
- an edit makes two answers defensible;
- official factual support is unavailable for a semantic rewrite;
- IDs, objective codes, tiers, eligibility, or count drift;
- learner-history compatibility cannot be proven;
- protected refs differ from recorded authority;
- leakage improves only by introducing shortest-answer or positional leakage;
- a tranche becomes too large for reliable human semantic review;
- PR #13 or recovery authorities are unexpectedly modified;
- implementation discovers that a new identity/storage architecture would be required.

## 16. Final completion criteria

The overall repair is complete only when the integrated production bank satisfies:

```text
STRICT_LONGEST_CORRECT_RATE < 40%
UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%
NO_DOMAIN > 45% STRICT_LONGEST_CORRECT
NO_MATERIAL_SHORTEST_ANSWER_LEAKAGE
NO_MATERIAL_POSITIONAL_ANSWER_LEAKAGE
QUESTION_COUNT = 454
QUESTION_IDS_CHANGED = 0
CORRECT_KEYS_CHANGED = 0
OBJECTIVE_CODES_CHANGED = 0
TIERS_CHANGED = 0
EXAM_ELIGIBILITY_CHANGED = 0
ALL_SEMANTIC_REVIEWS = PASS
BANK_INTEGRITY = PASS
LEARNER_HISTORY_COMPATIBILITY = PASS
FULL_REGRESSION = PASS
CONSOLIDATED_MAIN_CI = PASS
```

If those statistical thresholds cannot be reached without reducing factual or pedagogical quality, factual/pedagogical integrity wins. The work must stop with a documented residual-risk report rather than force the metric.

## 17. First implementation boundary

After this design is approved for implementation, the implementation plan should cover **Tranche 1 only** plus the reusable audit/gating infrastructure needed to support it. It must not pre-authorize all later content rewrites.

Tranche 1 should begin with a read-only reproducible baseline audit, then establish regression tests and preservation gates, then repair only the highest-severity bounded set, and stop for external review before any merge.
