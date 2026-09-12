# SC900-BACKLOG-3-BUILDER-RESUME-IDENTITY-001 — Handoff

## Decision

BACKLOG-3 is authorized for implementation now. Do not wait for the seven-day CAND-01R3 measurement.

## Publication-safe base

- Repository: `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`
- BACKLOG-2 branch: `implementation/sc900-backlog2-confidence-epistemics`
- BACKLOG3_BASE_SHA: `baf69ecf773cc929d7fb84a00494b434595aa8f3`
- BACKLOG-3 branch: `implementation/sc900-backlog3-builder-resume-identity`
- PR #20 head: `baf69ecf773cc929d7fb84a00494b434595aa8f3` (OPEN DRAFT UNMERGED)
- BACKLOG-1 publication-safe head / PR #19: `5610d25009b3006183cb0ac1a63a7c99d1f89c66` (OPEN DRAFT UNMERGED)
- PR #12 Gate-3 head: `f742dcc085d46f1999eb8782f709730323e9d7f0` (ancestor: yes)
- PR #13 frozen measurement head: `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` (ancestor: no)

Verified before branch creation: `implementation/sc900-backlog2-confidence-epistemics` still pointed at the expected SHA. The BACKLOG-3 branch was created from that exact SHA.

## Confirmed defects at the approved base

1. `SessionPersistenceMixin.normalize_builder_context(...)` accepts `randomize=` but does not forward it to `session_store.normalize_builder_context(...)`.
2. Shared normalizer derives `randomize` only from `raw["randomize"]`, so `True` and `False` collapse.
3. `find_resumable_session_for_builder()` matches via that collapsed dict equality (cross-resume).
4. `clear_resumable_sessions_for_builder()` uses the same weak comparison (cross-cleanup).
5. Equal collapsed candidates are ranked by filesystem mtime, so mtime becomes accidental identity.
6. Builder identity is a repeatedly normalized dictionary, not a versioned fingerprint authority.
7. Legacy snapshots missing `randomize` are silently treated as `False` without an explicit migration status, and missing `builder_context` is synthesized into a matchable context.
8. `current_builder_context` / `start_session_from_pool` can collapse `All visible` into the current pool size.
9. Smart Practice builder context forces `randomize=False` even when pool construction randomized.
10. Ordinary session filenames are question-set based, so distinct builder intents that yield the same IDs can collide.

## Non-goals

- Do not import PR #13.
- Do not start Day 1.
- Do not merge.
- Do not close Issue #16.
- Do not weaken BACKLOG-1 canonical identity.
- Do not weaken BACKLOG-2 confidence integrity.
- Do not modify PR #19 or PR #20.

## Spec / plan

- `docs/superpowers/specs/2026-09-12-backlog3-builder-resume-identity-design.md`
- `docs/superpowers/plans/2026-09-12-backlog3-builder-resume-identity.md`
