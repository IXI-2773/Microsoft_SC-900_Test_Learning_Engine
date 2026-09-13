# 04 — Distractor and ambiguity audit

## Findings

Predecessor identification items often use cross-product distractors (Bastion, DDoS Protection, NSG, Key Vault, Sentinel) when the keyed answer is an Entra or Purview capability. Those options are unambiguously wrong, so they do not create a second valid key, but they can make the keyed product family guessable.

MLC batches generally use same-family misconceptions (WAF vs DDoS, PIM vs access reviews, CSPM vs CWP). That is the stronger pattern.

## Disposition

- No approved item was withheld solely for weak distractors.
- Cross-product tells are recorded on the ledger as `WEAK_CROSS_PRODUCT`.
- Repairing every weak predecessor distractor would have been a broad rewrite, not a bounded defect repair, and would have risked new answer errors.
- The 300 MLC items plus remaining predecessor distinction/scenario items supply plausible same-family distractors for exam preparation.
- `DISTRACTOR_QUALITY_ACCEPTABLE = YES` for the bank as a whole, with residual weakness documented rather than hidden.

## Ambiguity

No approved stem was found where two options could both be correct under a reasonable interpretation. Multi-select wording uses “Choose two.”

## Answer-position leakage

Before repair, 297/300 MLC single-select items matched `(serial - 1) % 4`. That is a guessable periodic key.

Repair: `redistribute_single_select` now places the keyed option using `sha256(question_id)` rather than serial number. After re-emit:

- serial-mod-4 match rate ≈ 26.8% (near chance)
- overall positions A/B/C/D = 111/114/116/113
- `ANSWER_POSITION_LEAKAGE = NO`

Option-length leakage remains on many scenario items (correct option often a complete statement). That is typical of fundamentals scenario keys and is not a deterministic positional tell after shuffle.
