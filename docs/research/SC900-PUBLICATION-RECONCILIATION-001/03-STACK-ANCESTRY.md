# 03 — Stack ancestry

## Intended publication-safe stack

All nine heads exist locally as commits. Source heads were not rewritten.

| Order | PR | Role | Head | GitHub base → head branch |
| --- | --- | --- | --- | --- |
| 1 | #10 | Complete SC-900 reviewed bank Phase 3 | `06182c9dec6ddb7ef2090c5818228bb924aae20e` | `main` → `implementation/sc900-reviewed-bank-phase3` |
| 2 | #11 | Gate-2 reopening | `a9d66c093fa821a1db0b4f4cae348052f0357e25` | `implementation/sc900-reviewed-bank-phase3` → `research/sc900-cand01-gate2-reopen-001` |
| 3 | #12 | Gate-3 runtime | `f742dcc085d46f1999eb8782f709730323e9d7f0` | `research/sc900-cand01-gate2-reopen-001` → `implementation/sc900-cand01r3-gate3` |
| 4 | #19 | publication-safe BACKLOG-1 | `5610d25009b3006183cb0ac1a63a7c99d1f89c66` | `implementation/sc900-cand01r3-gate3` → `publication/sc900-backlog1-without-measurement` |
| 5 | #20 | BACKLOG-2 | `baf69ecf773cc929d7fb84a00494b434595aa8f3` | `publication/sc900-backlog1-without-measurement` → `implementation/sc900-backlog2-confidence-epistemics` |
| 6 | #21 | BACKLOG-3 | `7129fac53c71934801a1eabc21885e1db20af519` | `implementation/sc900-backlog2-confidence-epistemics` → `implementation/sc900-backlog3-builder-resume-identity` |
| 7 | #22 | Microsoft Learn corpus | `622ff338a0609b9a34ed390001f00403e1c73a7f` | `implementation/sc900-backlog3-builder-resume-identity` → `content/sc900-microsoft-learn-corpus` |
| 8 | #23 | final semantic expansion | `9656f3b196878a25542c1e3f6248dedc87e09421` | `content/sc900-microsoft-learn-corpus` → `content/sc900-final-semantic-expansion` |
| 9 | #24 | final bank audit + stabilization | `fdec8eaba44a18cb4c3482a65b1ce812a4ac440a` | `content/sc900-final-semantic-expansion` → `stabilization/sc900-final-bank-audit-debug` |

## Linear ancestor chain

`git merge-base --is-ancestor` is true for every consecutive pair:

```text
PR#10 ⊂ PR#11 ⊂ PR#12 ⊂ PR#19 ⊂ PR#20 ⊂ PR#21 ⊂ PR#22 ⊂ PR#23 ⊂ PR#24
```

PR #10 is an ancestor of every later publication head. The stack is already a single line of development. Sequential merges onto `main` therefore replay that line while inserting current-`main` as first-parent history at the first merge.

## Direct parents of each head

| Head | Parent(s) |
| --- | --- |
| PR #10 `06182c9` | `04e728cf4e6ddc0ec5b3e322f2602f6ce9056840` |
| PR #11 `a9d66c0` | `06182c9` (exactly PR #10) |
| PR #12 `f742dcc` | `586cee03c92e4c4367f6c5db39dbf21d174c7af4` |
| PR #19 `5610d25` | `e2d5671a20cb28b80ec8ec71904cff3ee6de40ae` |
| PR #20 `baf69ec` | `9782ee48f57d8604c063e28042b1e850b2697c2f` |
| PR #21 `7129fac` | `a7c7202fcfcaf1f46317e22cf495ed7dd35827c3` |
| PR #22 `622ff33` | `7129fac` (exactly PR #21) |
| PR #23 `9656f3b` | `622ff33` (exactly PR #22) |
| PR #24 `fdec8ea` | `4472a4c2995d428de6bd64c228df1aad69f8abaa` |

## Excluded lineage

| PR | Head | Why excluded |
| --- | --- | --- |
| #13 | `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb` | Frozen scientific measurement authority. Not an ancestor of any publication head. |
| #18 | `origin/implementation/sc900-backlog1-adversarial-closure` | Contains PR #13 ancestry. Unsafe topology. |
| #17 | `origin/implementation/sc900-backlog1-session-identity` | Superseded Segment-2 evidence **and** contains PR #13 ancestry. |

`git merge-base --is-ancestor fc7d32f <publication-head>` is **false** for every publication head including PR #24.

`git merge-base --is-ancestor fc7d32f origin/publication/sc900-backlog1-without-measurement` is **false** (PR #19 is the publication-safe BACKLOG-1).

`git merge-base --is-ancestor f742dcc origin/research/sc900-cand01r3-measurement-001` is **true**: PR #13 is stacked **on** Gate-3, not the reverse. After PR #12 publishes, GitHub may auto-retarget #13 to `main`. That is a merge-risk, not an import. See `07-RECOMMENDED-PUBLICATION-SEQUENCE.md`.
