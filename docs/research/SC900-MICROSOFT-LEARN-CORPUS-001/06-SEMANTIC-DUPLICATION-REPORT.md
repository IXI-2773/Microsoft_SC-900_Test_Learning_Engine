# 06 — Semantic duplication report

Audit artifact: `content/sc900/microsoft-learn-corpus/semantic_family_audit.json`

Fail-closed checks:

- exact stem duplicates
- same `semantic_family_id` + `tested_decision`

## Result

- Exact duplicates: 0
- Probable duplicates (importer 0.86 threshold on new JSONL vs predecessor): 0 at compile
- Semantic decision duplicates: 0
- Distinct semantic families: 27
- Average questions per family: 14.815

Family labels remain conservative and aligned with the Phase-3 merge map so reused items do not silently split measurement families. New items add distinct `tested_decision` values inside those families rather than paraphrase inflation.

Five new items originally shared the stem "Which pairing is accurate?" and were rewritten to unique stems before approval.
