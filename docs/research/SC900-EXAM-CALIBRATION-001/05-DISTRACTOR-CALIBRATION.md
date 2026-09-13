# Distractor calibration

## Method

Each option was classified against conceptual super-families (Entra, Azure infrastructure, Defender XDR/Sentinel, Purview, Zero Trust concepts). Cross-product giveaways and absurd options were replaced from a leaf-neighbor list. Pairing items received neighboring wrong pairings rather than unrelated products.

## Volume

| | Pre-calibration heuristic | Post-calibration |
| --- | --- | --- |
| Overlay items touching choices | — | 188 of 190 |
| Choice-only repairs | — | 170 |
| Stem+choice repairs | — | 18 |
| Ambiguous distractors | 0 | 0 |

The pre-calibration heuristic over-counted giveaways (it treated unmatched short option text as unrelated). After a super-family correction, the remaining issue was still real: many misconception and scenario items used jokes such as Bastion in DLP, TAP in Sentinel, or WAF as PIM.

Those were replaced with neighbors. One weaker option is still allowed. "Which Microsoft service" items may still list distinct Microsoft products; that is a legitimate Fundamentals form when the products are in-scope SCI services rather than absurdities.

## Answer-length leakage

Mean correct/distractor word ratio was about 1.64 before and about 1.79 after. Correct answers were not shortened where precision would be lost. Neighbor replacements are often shorter labels, which can increase the ratio. This is recorded as a residual leakage risk, not repaired by stripping Microsoft terminology from correct options.

## Grammar / format leakage

Option parallelism was checked on rewritten items. Incorrect options use the same product-naming style as the key. No article/verb-agreement giveaways were introduced. No answer-key or source corrections were required.
