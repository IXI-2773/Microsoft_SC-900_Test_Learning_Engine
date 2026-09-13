# 02 — 500-question audit method

## Scope

Every original approved item (200 predecessors + 300 MLC) received a final disposition. Validators were not treated as sufficient. The live SC-900 study guide was re-fetched on 2026-09-12.

## Live scope

- Skills measured as of **July 28, 2026**
- 4 domains, 14 objectives, **58 leaves**
- Live guide matches repository taxonomy; no taxonomy rewrite
- Training extras remain out of scope: Security Copilot, Purview Data Map / Unified Catalog, Security Service Edge / Global Secure Access
- Minor live wording still lists identity types “including agent ID”; that leaf already exists

## Passes

1. **Identity / tested_decision.** Assigned a durable decision slug to all 200 predecessors. Same slug as an MLC sibling when the learner decision is genuinely the same. Distinct slug only when the stem tests a different decision.
2. **Semantic duplication.** Carbon-copy predecessor paraphrases were withheld. Definition vs scenario vs distinction pairs with independent misconception value were kept, including same-decision variants marked `INDEPENDENT_OR_PRIMARY`.
3. **Answer key.** Each keyed answer was resolved against current Microsoft fundamentals authority (frozen inventory URLs, product docs, and live study-guide leaves). No approved item remains with an unresolvable or contradictory key.
4. **Distractors / ambiguity / leakage.** Unrelated Bastion / DDoS / TAP / NSG tells were scored. Serial `(n-1) mod 4` answer-position periodicity on MLC items was repaired with a SHA-256(id) placement.
5. **Difficulty, multi-select, sources, leaves.** Distributions were recomputed after withholds.

## Ledger

`content/sc900/microsoft-learn-corpus/research/final_audit_ledger.json` contains one row per original item (500), including withheld paraphrases.
