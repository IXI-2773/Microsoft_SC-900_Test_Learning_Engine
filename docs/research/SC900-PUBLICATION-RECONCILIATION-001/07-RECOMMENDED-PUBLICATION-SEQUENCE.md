# 07 — Recommended publication sequence

Rehearsal conclusion: the **exact expected nine-step sequence remains safe**. No corrected sequence is required. Do not collapse the stack into a cumulative mega-PR.

This file is a plan. **Do not execute it as part of this package.**

## Why the expected sequence is still safe

1. The nine heads are already a linear ancestor chain.
2. Current `main` diverges from PR #10 by 20 empty-net runner commits. Merging #10 onto `main` preserves that history and yields PR #10's tree.
3. Each subsequent head fast-applies as an `ort` merge with zero conflicts in rehearsal.
4. Final tree equals PR #24. Frozen 454-question bank is present. Default bank is unchanged. PR #13 is absent.
5. Full suite 851/851 PASS on that tree.

## Exact GitHub operations

After each merge, verify the GitHub diff still matches the corresponding rehearsal step before merging the next PR. Retarget is required because PRs #11–#24 currently target predecessor stack branches, not `main`.

1. Merge **PR #10** into `main`.
   - Already targets `main`.
   - Verify: Phase-3 content appears; ephemeral runner workflows remain absent.
2. Retarget **PR #11** to `main`; verify diff (Gate-2 reopen docs only relative to post-#10 `main`); merge.
3. Retarget **PR #12** to `main`; verify diff (Gate-3 runtime); merge.
4. Retarget **PR #19** to `main`; **verify PR #13 ancestry absent**; merge.
   - Required proof: `git merge-base --is-ancestor fc7d32f <PR19 head>` is false, and named protocol artifacts are absent from the PR diff.
5. Retarget **PR #20** to `main`; verify diff; merge.
6. Retarget **PR #21** to `main`; verify diff; merge.
7. Retarget **PR #22** to `main`; verify diff; merge.
8. Retarget **PR #23** to `main`; verify diff; merge.
9. Retarget **PR #24** to `main`; verify diff (frozen bank SHA `8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254`, default bank unchanged); merge.

GitHub may auto-retarget a PR onto `main` when its base branch is merged. Still verify the diff. Do not skip the PR #13 absence check at step 4.

## Retarget map (current GitHub bases)

| After this merge | Retarget this PR from | To |
| --- | --- | --- |
| #10 | #11 (`implementation/sc900-reviewed-bank-phase3`) | `main` |
| #11 | #12 (`research/sc900-cand01-gate2-reopen-001`) | `main` |
| #12 | #19 (`implementation/sc900-cand01r3-gate3`) | `main` |
| #19 | #20 (`publication/sc900-backlog1-without-measurement`) | `main` |
| #20 | #21 (`implementation/sc900-backlog2-confidence-epistemics`) | `main` |
| #21 | #22 (`implementation/sc900-backlog3-builder-resume-identity`) | `main` |
| #22 | #23 (`content/sc900-microsoft-learn-corpus`) | `main` |
| #23 | #24 (`content/sc900-final-semantic-expansion`) | `main` |

## PR #13 hazard after step 3

PR #13 is based on `implementation/sc900-cand01r3-gate3` (PR #12). When #12 merges, GitHub may auto-retarget **#13 to `main`**.

Required operator behavior:

- Keep PR #13 **OPEN and UNMERGED**.
- Do not merge it when it appears as a `main`-targeted PR.
- This package does not modify PR #13 (no conversion, no retarget, no comment).
- PR #19 is also based on Gate-3; after step 3 it may sit beside #13 as another `main`-targeted PR. Merge **#19 only**.

## Not part of publication

- Do not merge PR #13, #17, or #18.
- Do not activate the 454-question bank during these nine merges.
- Do not create a squash mega-PR of #10–#24.

## Expected post-#24 `main` tree

Byte-identical to PR #24 / rehearsal stack tree `5bb7645475a0f32d03019d810c79e7423ea95336`, with first-parent history that includes current `main`'s 20 empty-net commits plus nine merge commits (or GitHub's equivalent merge commits).
