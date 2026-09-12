# 05 — PR #13 exclusion proof

```text
PR13_IMPORTED = NO
PR13_MODIFIED = NO
PR13_MERGED = NO
DAY1_STARTED = NO
```

PR #13 remains frozen scientific authority:

```text
PR     = #13
title  = Freeze CAND-01R3 controlled measurement protocol
head   = fc7d32f976c0b4c75658ff67d8d47ebe53d854bb
branch = research/sc900-cand01r3-measurement-001
base   = implementation/sc900-cand01r3-gate3
state  = OPEN, not draft, UNMERGED
```

This rehearsal did not check out, retarget, edit, or merge that branch.

## Ancestry

```text
git merge-base --is-ancestor fc7d32f HEAD
= false   (exit 1)

git merge-base --is-ancestor fc7d32f fdec8ea   # PR #24
= false

git merge-base --is-ancestor fc7d32f <each of PR#10,11,12,19,20,21,22,23>
= false
```

PR #13 is **not** on the publication line. Gate-3 **is** an ancestor of PR #13 (`f742dcc` ⊂ `fc7d32f`). That is why #13 must stay unmerged after Gate-3 publishes: GitHub may retarget it to `main`, but the measurement commits themselves are not in the publication stack.

## Named artifact absence (rehearsal HEAD)

| Path | Present |
| --- | --- |
| `cand01r3_protocol.py` | NO |
| `content/sc900/measurement/cand01r3_protocol.json` | NO |
| `docs/research/SC900-ENGINE-RDAF-CAND01R3-MEASUREMENT-001/` | NO |
| `tests/test_cand01r3_measurement_protocol.py` | NO |
| `tests/test_cand01r3_measurement_protocol_v2.py` | NO |
| `tests/test_cand01r3_measurement_runtime_resume.py` | NO |
| `tests/test_cand01r3_measurement_integrity.py` | NO |
| `tests/test_cand01r3_scorer_structure.py` | NO |
| `.github/workflows/verify-cand01r3-pre-day1-readonly.yml` | NO |

`git ls-files 'tests/test_cand01r3*'` on rehearsal HEAD:

```text
tests/test_cand01r3_all_paths.py
tests/test_cand01r3_measurement.py
tests/test_cand01r3_partition.py
tests/test_cand01r3_rrc1.py
```

Those four files are Gate-3 runtime tests from PR #12, not PR #13 protocol tests.

Broader name scan of rehearsal HEAD for `cand01r3_protocol`, `CAND01R3-MEASUREMENT`, `pre-day1`, `pre_day1` returned no publication-tree matches (the only `protocol` hit is historical `docs/research/SC900-ENGINE-RDAF-SUCCESSOR-002/02-historical-data-extraction-protocol.md`, unrelated).

## Gate-3 files that are present and allowed

These are **not** PR #13-only:

- `cand01r3_measurement.py`
- `cand01r3_partition.py`
- `cand01r3_paths.py`
- `cand01r3_rrc1.py`
- `cand01r3_runtime.py`
- `docs/research/SC900-ENGINE-RDAF-CAND01-GATE3-001/`

They enter via PR #12.

## Unsafe PRs that do contain PR #13

```text
git merge-base --is-ancestor fc7d32f origin/implementation/sc900-backlog1-adversarial-closure  = true  (PR #18)
git merge-base --is-ancestor fc7d32f origin/implementation/sc900-backlog1-session-identity     = true  (PR #17)
git merge-base --is-ancestor fc7d32f origin/implementation/sc900-backlog1-identity-migration   = true
git merge-base --is-ancestor fc7d32f origin/publication/sc900-backlog1-without-measurement     = false (PR #19)
```

PR #18 must never be published. PR #19 is the publication-safe BACKLOG-1 substitute.

## Conflict involvement

No merge conflict occurred. No `PR13_SCIENTIFIC` ownership decision was required.
