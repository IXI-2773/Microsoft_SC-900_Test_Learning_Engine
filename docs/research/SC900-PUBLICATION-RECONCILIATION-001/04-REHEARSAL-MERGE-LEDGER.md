# 04 — Rehearsal merge ledger

## Branch

```text
created from = origin/main 1a206dfa920ee6fe398d5f5d45e0542ca46e0e6f
branch       = publication/sc900-final-reconciliation-rehearsal
method       = git merge --no-edit <exact publication head>
source heads = not rewritten, not checked out for mutation
```

Author/committer identity for local merge commits used existing repository identity `Umu <frailtycraven@gmail.com>` via process environment only. Git config was not modified.

## Ledger

All nine merges used strategy `ort`. Conflicts: **none**. No ours/theirs resolution was required.

| Step | Publication head | Before | After | Parents | Conflicts | Ownership if conflicted |
| --- | --- | --- | --- | --- | --- | --- |
| 1 PR #10 | `06182c9dec6ddb7ef2090c5818228bb924aae20e` | `1a206dfa920ee6fe398d5f5d45e0542ca46e0e6f` | `9e15edc500f4d6cbb1e7b7df53a8753dec4704d6` | `1a206df` + `06182c9` | none | n/a |
| 2 PR #11 | `a9d66c093fa821a1db0b4f4cae348052f0357e25` | `9e15edc500f4d6cbb1e7b7df53a8753dec4704d6` | `96a69f0d8a8b0fe386f4503bdb192762b9c35a80` | `9e15edc` + `a9d66c0` | none | n/a |
| 3 PR #12 | `f742dcc085d46f1999eb8782f709730323e9d7f0` | `96a69f0d8a8b0fe386f4503bdb192762b9c35a80` | `766853bd32d61122fbf1ffde2eac07ca5ca09b47` | `96a69f0` + `f742dcc` | none | n/a |
| 4 PR #19 | `5610d25009b3006183cb0ac1a63a7c99d1f89c66` | `766853bd32d61122fbf1ffde2eac07ca5ca09b47` | `8c6e83b74d7e9b455dd3fe87eecdd53564f4776c` | `766853b` + `5610d25` | none | n/a |
| 5 PR #20 | `baf69ecf773cc929d7fb84a00494b434595aa8f3` | `8c6e83b74d7e9b455dd3fe87eecdd53564f4776c` | `d2fe36bae0839d232d3627dc9dc586aba389e324` | `8c6e83b` + `baf69ec` | none | n/a |
| 6 PR #21 | `7129fac53c71934801a1eabc21885e1db20af519` | `d2fe36bae0839d232d3627dc9dc586aba389e324` | `eced28512234e60cc01b1c3b2c8c0924df97a40b` | `d2fe36b` + `7129fac` | none | n/a |
| 7 PR #22 | `622ff338a0609b9a34ed390001f00403e1c73a7f` | `eced28512234e60cc01b1c3b2c8c0924df97a40b` | `1f95bcd489fcc4b7987e6755620f887f251d32f6` | `eced285` + `622ff33` | none | n/a |
| 8 PR #23 | `9656f3b196878a25542c1e3f6248dedc87e09421` | `1f95bcd489fcc4b7987e6755620f887f251d32f6` | `847758e9f9901db41cca54a0cc14d95515fd2aad` | `1f95bcd` + `9656f3b` | none | n/a |
| 9 PR #24 | `fdec8eaba44a18cb4c3482a65b1ce812a4ac440a` | `847758e9f9901db41cca54a0cc14d95515fd2aad` | `0e4d3ce71d885347b8d3dee10be7633ad146a67c` | `847758e` + `fdec8ea` | none | n/a |

## Conflict policy result

No conflict required classification. Vacuously:

- no `MAIN_ONLY_CLEANUP` conflict
- no `PR13_SCIENTIFIC` conflict
- no wholesale ours/theirs

## Tree after nine merges

```text
rehearsal stack HEAD = 0e4d3ce71d885347b8d3dee10be7633ad146a67c
rehearsal tree       = 5bb7645475a0f32d03019d810c79e7423ea95336
PR #24 tree          = 5bb7645475a0f32d03019d810c79e7423ea95336
git diff fdec8ea HEAD = empty
```

The nine-merge rehearsal tree is **byte-identical** to PR #24. Current-`main` unique history is present as first-parent ancestry of merge 1 and does not alter the tree.

## Source heads unchanged after rehearsal merges

```text
origin/main                                           = 1a206dfa920ee6fe398d5f5d45e0542ca46e0e6f
PR #10                                                = 06182c9dec6ddb7ef2090c5818228bb924aae20e
PR #24                                                = fdec8eaba44a18cb4c3482a65b1ce812a4ac440a
PR #13                                                = fc7d32f976c0b4c75658ff67d8d47ebe53d854bb
```
