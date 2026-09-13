# SC900-BACKLOG-2-CONFIDENCE-EPISTEMICS-001 — Handoff

## Decision

BACKLOG-2 is authorized for implementation now. Do not wait for the seven-day CAND-01R3 measurement.

## Publication-safe base

- Repository: `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`
- Base branch: `publication/sc900-backlog1-without-measurement`
- Base SHA: `5610d25009b3006183cb0ac1a63a7c99d1f89c66`
- Implementation branch: `implementation/sc900-backlog2-confidence-epistemics`
- PR #12 Gate-3 head: `f742dcc085d46f1999eb8782f709730323e9d7f0` (ancestor: yes)
- PR #13 frozen measurement head: `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` (ancestor: no)
- PR #19: OPEN DRAFT UNMERGED; do not push onto its branch

## Confirmed defects at the approved base

1. `_collect_answer_feedback()` manufactures `confidence = "Sure"`.
2. `normalize_confidence()` converts missing/invalid values into `"Sure"`.
3. Single-choice `toggle_choice` calls `_record_answer` immediately.
4. Multi-choice `submit_answer` follows the same path.
5. Keyboard Return/Submit can persist without a genuine confidence observation.
6. `retag_current_answer_confidence` updates runtime/progress/history but not `session_answer_history`.
7. Confidence-derived fields can disagree after retag.
8. `mark_current_question_super_confident` has the same split-state risk.
9. Smart Practice cache identity can retain stale session confidence.
10. Reward/streak logic reads `session_answer_history` directly.

Popover helpers already exist (`pending_feedback_request`, `_complete_feedback_choice`) but `_show_feedback_popover` is missing and unused by the live path.

## Non-goals

- Do not import PR #13.
- Do not start Day 1.
- Do not start BACKLOG-3.
- Do not merge.
- Do not close Issue #15.
- Do not weaken BACKLOG-1 canonical identity.

## Spec / plan

- `docs/superpowers/specs/2026-09-12-backlog2-confidence-epistemics-design.md`
- `docs/superpowers/plans/2026-09-12-backlog2-confidence-epistemics.md`
