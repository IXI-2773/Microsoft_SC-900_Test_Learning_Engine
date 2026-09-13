# SC-900 Exam-tier runtime reconstruction handoff

WORK_ID: `SC900-EXAM-TIER-RUNTIME-RECONSTRUCTION-001`

## Isolated worktree

| Field | Value |
| --- | --- |
| WORKTREE_PATH | `C:\Users\Drago\worktrees\sc900-exam-tier-runtime-reconstruction-001` |
| BRANCH_NAME | `implementation/sc900-exam-tier-runtime-reconstruction-001` |
| BASE_MAIN_SHA | `4386c104abc3a5b1e3a6aa51f35a51ac901267c0` |
| Starting worktree | CLEAN |

Remote `origin/main` at start matched the expected PR #25 merge. This package did not reset remote main and did not touch existing local clones or branches.

## What this package does

Newly constructed ordinary Exam sessions now exclude questions whose `exam_simulation_eligible` is explicitly `false`. Missing metadata remains eligible. Practice and Smart Practice still use the full approved pool, including Stretch. Persisted Exam sessions restore saved canonical identity and order without retroactive filtering.

## What this package does not do

- Recover or recreate lost commit `e16ca1994af33edc8ff50de7ee69202d911c4073`
- Change calibrated or default bank content
- Activate the 454-question bank
- Add 70/30 weighting, tier quotas, a Stretch toggle, or a new mode
- Import, retarget, rebase, or merge PR #13
- Start Day 1

## Implementation shape

Reusable predicate: `exam_runtime_eligible(question)` in `exam_runtime_eligibility.py`.

Applied only at new ordinary Exam construction:

- `SessionBuilderMixin.get_session_builder_pool()` when the current mode is Exam
- `SessionPersistenceMixin.start_session_from_pool()` when `mode == Exam`, before count sampling

Restore still resolves saved canonical IDs from `master_questions`. Builder identity was left unchanged because no resume collision was demonstrated.
