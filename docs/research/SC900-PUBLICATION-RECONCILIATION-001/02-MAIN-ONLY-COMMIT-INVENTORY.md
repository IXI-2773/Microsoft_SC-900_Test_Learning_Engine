# 02 — Main-only commit inventory

`MAIN_ONLY_COMMITS_INSPECTED = 20`

Reachable from `origin/main`, absent from PR #10 lineage `06182c9dec6ddb7ef2090c5818228bb924aae20e`. Listed oldest-first.

| # | SHA | Subject | Classification | Paths |
| --- | --- | --- | --- | --- |
| 1 | `854a9ab94fa9aae50156b8a1c0d6e14f799a3434` | ci: run Phase 3 Task 1 RED contract | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task12-red.yml` |
| 2 | `17ec4751dce790b8187f1b81f859e2b3ffae543e` | chore: remove Phase 3 Task 1 RED runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 3 | `4d8ad977f746a7f28d4ff0d93f15be1ed02790db` | ci: verify published Phase 3 Task 1-2 package | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task12-green.yml` |
| 4 | `b5e8a7057db6deaff8023827cfd418259ebf73d9` | chore: remove Phase 3 Task 1-2 verification runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 5 | `19f085ea72a6e5d559e474aff59384d8f9176573` | ci: rerun Phase 3 Task 1-2 verification with full history | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task12-green-retry.yml` |
| 6 | `f4fa20a4db31410fdbf63320a1c01ca77e4afa45` | chore: remove Phase 3 Task 1-2 retry runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 7 | `8bc62f45faa058af0fe6dab70574a52783c8d472` | ci: run Phase 3 Task 3 allocation RED contract | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task3-allocation-red.yml` |
| 8 | `c5d50236d2dc254320a551cf08647485f4de5b77` | chore: remove Phase 3 Task 3 allocation RED runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 9 | `332a917a42ccdc8a31abde341c6a63578e4eb77b` | ci: freeze and verify Phase 3 Task 3 allocation | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task3-allocation-green.yml` |
| 10 | `71e818fb37a0a70e9c64303f49035c145f582bdd` | chore: remove Phase 3 Task 3 allocation GREEN runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 11 | `2db2a36ff4a6232669a1e59979fe12a8f64dce2c` | ci: correct and verify Phase 3 Task 3 allocation | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task3-allocation-green-retry.yml` |
| 12 | `b54530ec20f797bac1c89cb8aa970b6682adc222` | chore: remove Phase 3 Task 3 allocation retry runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 13 | `4ee5c20ef70761ed661612c28c2ea2cfed71a963` | ci: tighten Phase 3 insider-risk provenance | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-task3-provenance-correction.yml` |
| 14 | `0cf48d576bafa5d0b745950a7b1dd5801bc86971` | chore: remove Phase 3 Task 3 provenance runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 15 | `781ece068c8bada92b7bd746b037407bf95dc8e0` | ci: verify SC-900 Phase 3 batch 01 authoring | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-batch01-authoring-verify.yml` |
| 16 | `60afdbd19a7ce08f8766cb66a1c971b72bf3b098` | chore: remove Phase 3 batch 01 authoring runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 17 | `fecf3bd86e0d644dcb54787f3e2622efac15bf6d` | ci: correct Phase 3 batch 01 stem styles | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-batch01-stemstyle-fix.yml` |
| 18 | `4340226bcaa9f5d8feb54cd454f7a17f6250c888` | chore: remove Phase 3 batch 01 correction runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |
| 19 | `05d0b001f7727b549324f209c1d634bbc6be9c20` | ci: finalize Phase 3 batch 01 authoring validation | `EPHEMERAL_RUNNER_ADD` | `.github/workflows/phase3-batch01-final-authoring-fix.yml` |
| 20 | `1a206dfa920ee6fe398d5f5d45e0542ca46e0e6f` | chore: remove Phase 3 batch 01 final authoring runner | `EPHEMERAL_RUNNER_REMOVE` | same file deleted |

## Classification totals

| Class | Count |
| --- | --- |
| `EPHEMERAL_RUNNER_ADD` | 10 |
| `EPHEMERAL_RUNNER_REMOVE` | 10 |
| `VALID_MAIN_ONLY_FIX` | 0 |
| `DOCUMENTATION` | 0 |
| `CI_CONFIGURATION` | 0 (these workflows were temporary runners, not lasting CI) |
| `OTHER` | 0 |

No main-only commit changed application code, question content, or lasting workflows. Each add is paired with a later remove of the same path.

## Net tree effect

```text
git diff --name-status a2cc5247706c938efc92b8ef21a453ed909ec738 origin/main
= empty

MAIN_ONLY_NET_EFFECT_PRESERVED = YES
EPHEMERAL_RUNNERS_RESURRECTED = NO
```

The publication tree must keep these files **absent**. Rehearsal HEAD does not contain any of the ten workflow paths.

Intentional current-`main` cleanup is therefore preserved as the continued absence of those runners, while the 20 commits remain in first-parent history after the PR #10 merge commit.
