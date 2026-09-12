# 01 — Current main divergence

## Live `main`

```text
origin/main = 1a206dfa920ee6fe398d5f5d45e0542ca46e0e6f
subject    = chore: remove Phase 3 batch 01 final authoring runner
```

Matches the expected SHA.

There is no local `main` ref in this worktree. `origin/main` is the live authority.

## PR #10

```text
PR            = #10
title         = Complete SC-900 reviewed bank Phase 3
head          = 06182c9dec6ddb7ef2090c5818228bb924aae20e
base          = main
GitHub state  = OPEN
```

## Shared merge-base

```text
git merge-base origin/main 06182c9dec6ddb7ef2090c5818228bb924aae20e
= a2cc5247706c938efc92b8ef21a453ed909ec738
```

## Ahead / behind

| Direction | Count | Meaning |
| --- | --- | --- |
| PR #10 ahead of current `main` | 28 | Phase-3 implementation/content/docs/tests |
| Current `main` ahead of PR #10 | 20 | Historical/ephemeral Phase-3 CI-runner add/remove pairs |

Those 20 main-only commits **cannot** be discarded from history. They are part of published `main`. Their **net tree effect is empty**: every runner added on `main` was later removed on `main`.

## Tree identity

```text
merge-base tree = aabd88b379fd118619460955e986b5f0579228a4
origin/main tree = aabd88b379fd118619460955e986b5f0579228a4
git diff a2cc524 origin/main = empty
```

Current `main`'s unique history is therefore **history-only**. The live tree of `main` equals the shared merge-base tree. Merging PR #10 onto current `main` is topologically a merge of Phase-3 content onto an unchanged tree, while preserving the 20 main-only commits in first-parent history.

## Divergence implication

Rehearsal merge of PR #10 into a branch based on current `main`:

- strategy: `ort`
- conflicts: none
- result tree: identical to PR #10's tree
- first parent: current `main` (cleanup history preserved)
- second parent: PR #10 head

That is the publication-safe way to keep main-only cleanup history without resurrecting the runners.
