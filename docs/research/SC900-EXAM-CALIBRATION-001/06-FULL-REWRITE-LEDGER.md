# Full rewrite ledger

Authority files:

- Overlay: `content/sc900/microsoft-learn-corpus/calibration/rewrite_overlay.json`
- Per-item ledger: `content/sc900/microsoft-learn-corpus/calibration/ledger.jsonl`
- Generator: `tools/sc900_calibration_rewrites.py`

## Counts

| Action | Count |
| --- | --- |
| Approved items | 454 |
| Rewritten | 190 |
| Unchanged | 264 |
| Withheld | 0 additional (still 46 predecessor withholds from the prior audit) |
| Stem simplified | 20 |
| Choice-only repair | 170 |
| Semantic identity replacements | 0 |
| Tested-decision ID changes | 0 |
| Answer-key corrections | 0 |
| Source corrections | 0 |

Rewrites are overlays applied after review custody, so original batch hashes remain valid. Canonical question IDs are unchanged.

## Stretch keepers

23 items kept as Stretch for Smart Practice / hard review, including dual-capability pairings (Firewall vs WAF, MDE vs MDI, labels vs Teams DLP), "why X is not a substitute for Y" items, and the existing multi-select set. Joke distractors on those items were still repaired where needed.
