# Final calibration disposition

The audited 454-question bank is recalibrated and refrozen on `content/sc900-exam-style-calibration`.

## Content freeze

`FINAL_BANK_FROZEN = YES` after:

- all 454 items classified
- 190 justified rewrites applied as a deterministic overlay
- two clean rebuilds with identical SHA-256
- calibration, corpus, and runtime tests green

`QUESTION_AUTHORING_FROZEN = YES`. No attempt to restore 500 questions. No default-bank change. No candidate-bank activation.

## Independent passes

1. Classification of all 454 against the rubric.
2. Selective rewrite (pilot, then remaining flagged items).
3. Answer/source preservation: no key or source URL changes; overlay does not edit explanations.
4. Exam-style review: Core majority, Stretch minority, neighboring distractors, short one-decision stems.

Disagreements: the first giveaway heuristic over-counted unmatched option text. Super-family classification replaced it. Pairing items were kept when the pairing itself was the tested decision.

## Publication boundary

PR #13 unmodified and unmerged. PR #24 unmodified. Protected history refs unchanged. Day 1 not started. Publication reconciliation remains unauthorized.
