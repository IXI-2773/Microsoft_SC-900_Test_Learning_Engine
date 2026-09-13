# SC-900 final-bank activation handoff

WORK_ID: `SC900-FINAL-BANK-ACTIVATION-REHEARSAL-001`

## Isolated worktree

| Field | Value |
| --- | --- |
| WORKTREE_PATH | `C:\Users\Drago\worktrees\sc900-final-bank-activation-001` |
| ACTIVATION_BRANCH | `activation/sc900-final-bank-001` |
| ACTIVATION_BASE_SHA | `2820cd322bce8a0d94008622c2189be17f3a1c23` |
| Starting worktree | CLEAN |

Remote `origin/main` at start matched the expected PR #26 merge SHA. This package did not reset remote main and did not touch existing local clones or branches.

## What this package does

Activates the frozen 454-question calibrated bank as the production runtime bank on a new branch, and reconciles release, installation, packaging, lint, smoke, and contract tests that still encoded the historical 8-question placeholder.

## What this package does not do

- Merge the activation PR
- Change calibrated or baseline question content
- Redesign Exam-tier, Practice, or Smart Practice sampling
- Import, retarget, rebase, or merge PR #13
- Start CAND-01R3 Day 1
- Move protected recovery refs or tags

## Required end-state flags

| Flag | Value |
| --- | --- |
| FINAL_BANK_ACTIVATED_ON_BRANCH | YES |
| FINAL_BANK_ACTIVATED_ON_MAIN | NO |
| ACTIVATION_PR_MERGE_READY | YES after review gates |
| ACTIVATION_PR_MERGED | NO |
| PR13_IMPORTED | NO |
| PR13_MODIFIED | NO |
| PR13_MERGED | NO |
| DAY1_STARTED | NO |

## Activation shape

- Canonical research artifact remains `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json`.
- Production runtime copy is root-level `sc900_bank_v8_final.json`, byte-identical to the canonical artifact.
- `cert_profile_sc900.json` `runtime_bank` points at that copy.
- `runtime_bank_question_count` is the explicit production count authority (`454`).
- `placeholder_bank_question_count` remains historical metadata (`8`) and does not drive production validation.
- Historical `sc900_bank_v8_baseline.json` is preserved byte-identical.

## Rollback

Revert the activation commit. Runtime pointer returns to `sc900_bank_v8_baseline.json`. Baseline artifact, canonical calibrated artifact, PR #26 runtime code, and recovery refs remain unchanged.
