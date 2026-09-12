# 05 — Semantic-decision audit

## Empty tested_decision gap

Before this package: 300 MLC items had explicit `tested_decision`; 200 predecessors did not.

After overlay: **0** approved items have an empty tested_decision. Predecessor slugs are meaningful learner-decision identities, not question-id hashes.

## Duplicates

Compiler uniqueness is family + tested_decision, with an allowed independent-variant exception when a predecessor keeps the same decision as an MLC scenario/distinction sibling.

True predecessor paraphrases (same family, same decision, no independent scenario or misconception value) were withheld.

| Metric | Value |
| --- | --- |
| Semantic duplicates found (predecessor paraphrases) | 46 |
| Semantic duplicates removed (withheld) | 46 |
| Bounded replacement questions | 0 |
| Approved independent same-decision variants | retained, documented `INDEPENDENT_OR_PRIMARY` |

Withhold map lives in `tools/sc900_final_predecessor_overlay.py` (`WITHHELD`).

`SEMANTIC_DUPLICATION_WITHIN_POLICY = YES`
