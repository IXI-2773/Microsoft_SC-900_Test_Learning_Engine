# 06 — Final expanded bank report

## Artifact

- Path: `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json`
- `FINAL_EXPANDED_BANK_SHA256`: `84f9370909ebe4572e0b0766e6ecaadc239e816d1d78e6d275736cebd45f747f`
- `REBUILD_SHA256`: `84f9370909ebe4572e0b0766e6ecaadc239e816d1d78e6d275736cebd45f747f`
- `FINAL_EXPANDED_BANK_REPRODUCIBLE`: YES (compiler `build_corpus(write=False)` twice matches)
- `FINAL_EXPANSION_IDEMPOTENT`: YES (re-emit + rebuild does not grow duplicates or drift IDs)

Baseline 400 SHA-256 confirmed before authoring: `86cd49dc74017b204048f6bd55d48e695f6bb7bce328b0e08db50dde032326b7`.

## Promotion

- Approved 500
- Pending 0
- Withheld 0 in the compiled bank
- Default bank unchanged
- Final bank not activated

## Identity

New IDs `sc900_mlc_q201`–`sc900_mlc_q300`. Predecessor and first 200 MLC IDs unchanged. Frozen probe families remain unassigned (`future_probe_suitability = not_assigned_to_frozen_probe`).

## Tooling hygiene deferred to cleanup

Do not delete in this package:

- `tools/capture_sc900_microsoft_corpus.py` (one-shot capture)
- `tools/sc900_microsoft_corpus_knowledge.py` (one-shot KU emitter)
- `tools/sc900_microsoft_corpus_existing_audit.py`
- `ANSWER_REVIEWS` constant in the builder (defined, unused by compile)
- generated `batches/*.jsonl` and `reviews/*-review.json` (build inputs, not the launch bank)
- parked `docs/research/SC900-BOOK-SUPPLEMENT-001/00-HANDOFF.md` (superseded requirement, not deleted)
- untracked `local/` book PDF (operator machine; not this lineage)

Inspect Python generators by contents, not GitHub empty-diff statistics.

## Runtime compatibility

Bounded load of the 500-question candidate bank succeeded for parsing, canonical IDs, bank fingerprint, ordered IDs, shuffled subset, Practice and Exam session signatures, and Smart Practice role allocation. Default launch bank was not swapped.
