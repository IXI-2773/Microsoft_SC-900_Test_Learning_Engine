# 08 — Post-publication cleanup

Prepare only. **Do not execute** as part of this package. Do not delete protected recovery refs.

## Pull requests

| PR | Action | When | Reason |
| --- | --- | --- | --- |
| #17 | Close without merge | After publication stack is on `main`, or immediately if desired (it is already superseded) | Superseded Segment-2 evidence; **contains PR #13 ancestry** |
| #18 | Close without merge | Immediately safe to close; required before any accidental merge | Unsafe topology / historical evidence; **contains PR #13 ancestry** |
| #13 | **KEEP OPEN and UNMERGED** | Always in this program | Frozen scientific measurement authority |
| #10–#12, #19–#24 | Merge per `07-RECOMMENDED-PUBLICATION-SEQUENCE.md` | Publication package (not this rehearsal) | Publication-safe stack |

Do not close #13. Do not merge #17 or #18 as a shortcut for BACKLOG-1.

## Issues

| Issue | Title | Close when |
| --- | --- | --- |
| #14 | BACKLOG-1 — Learner Identity / Bank Migration Integrity | Only after **PR #19** is published to `main` |
| #15 | BACKLOG-2 — Confidence Epistemics Integrity | Only after **PR #20** is published to `main` |
| #16 | BACKLOG-3 — Session Builder / Resume Identity Integrity | Only after **PR #21** is published to `main` |

Do not close #14/#15/#16 in this rehearsal.

## Branches deletable only AFTER successful publication

Delete only after the corresponding PR is merged to `main` and the post-merge tree has been verified. Never delete if a recovery or open scientific PR still needs the ref.

### Publication stack heads (deletable after their PR merges)

- `implementation/sc900-reviewed-bank-phase3` (PR #10)
- `research/sc900-cand01-gate2-reopen-001` (PR #11)
- `implementation/sc900-cand01r3-gate3` (PR #12) — **delay until PR #13 no longer uses it as base**, or accept that GitHub will retarget #13
- `publication/sc900-backlog1-without-measurement` (PR #19)
- `implementation/sc900-backlog2-confidence-epistemics` (PR #20)
- `implementation/sc900-backlog3-builder-resume-identity` (PR #21)
- `content/sc900-microsoft-learn-corpus` (PR #22)
- `content/sc900-final-semantic-expansion` (PR #23)
- `stabilization/sc900-final-bank-audit-debug` (PR #24)
- local `publication/sc900-final-reconciliation-rehearsal` after the operator no longer needs the topology proof

### Superseded / unsafe (deletable after #17/#18 closed, never merge)

- `implementation/sc900-backlog1-session-identity` (PR #17)
- `implementation/sc900-backlog1-adversarial-closure` (PR #18)
- `implementation/sc900-backlog1-identity-migration` (PR #13 ancestry; superseded by PR #19)

### Never delete

| Ref | SHA |
| --- | --- |
| `recovery/publish-exact-history/sc900-v8-20260910` | `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` |
| `recovery/publish-sc900-v8-exact-history` | `bbc3bd900b73bde89151dc51706ad62fc69e8196` |
| `sc900-v8.0.0-baseline` tag | object `9c80be5b20e652dc2eb86621dfdf7c32baa06528` |
| `research/sc900-cand01r3-measurement-001` | keep while PR #13 remains the scientific authority |

## Rehearsal branch

`publication/sc900-final-reconciliation-rehearsal` is evidence, not a publication vehicle. Do not merge it to `main`. A GitHub PR is unnecessary unless the operator needs remote preservation of the nine merge commits.
