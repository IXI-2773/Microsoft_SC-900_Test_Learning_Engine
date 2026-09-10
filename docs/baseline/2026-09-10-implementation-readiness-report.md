# SC-900 v8 Implementation Readiness Report

## Status

**AUTH_REQUIRED.** The local engineering, ingestion baseline, and release infrastructure are verified, but the required Windows build and executable smoke test have not run for this branch head. A supported GitHub connection is authenticated, but it cannot push the existing local Git history intact.

## Branch and commits

- Branch: `implementation/sc900-v8-baseline`
- Starting head: `89e565719b7004117bcaea1d26ae6d27bb007acf`
- Current head: `a0badb8f8cbbf8d2dd8888fe48248a06d380d34e`
- Remote head: `bbc3bd900b73bde89151dc51706ad62fc69e8196`
- Local commits beyond the remote: 10

## Release infrastructure repair

- The Windows workflow now verifies the exact pull-request checkout rather than running the one-time migration/bootstrap script.
- It records and compares `GITHUB_SHA` with `git rev-parse HEAD`, runs test/quality gates, and asserts no tracked-source modification before and after build preparation.
- `release_resources.py` is the single source of truth for the certification profile, placeholder bank, and versioned taxonomy. The PyInstaller build command includes all three, with the taxonomy bundled at `config/certifications/sc900-2026.json` for `_MEIPASS` lookup.
- `tools/verify_installation.py` verifies the taxonomy source resource, and regression tests reject a workflow that invokes migration/bootstrap or omits a required resource.

## Ingestion baseline

- Versioned SC-900 taxonomy: `config/certifications/sc900-2026.json`
- Canonical question/source-material schema with source provenance and origin tracking: `ingestion/models.py`
- JSONL importer and persistent question/material/quarantine/review stores: `ingestion/importer.py`
- Exact duplicates are skipped; probable duplicates are placed in review; conceptually related records retain a relation; malformed rows are quarantined with reason codes.
- Imports are deterministic/idempotent by canonical ID, report source statistics and reason counts, and have a 1,000-record integration test.
- Only accepted question records compile to the current runtime-bank contract. Source material never enters the runnable bank.
- CLI: `python tools/import_sc900_content.py EXPORT.jsonl --store data/sc900-content --compile imported_sc900_bank.json`

## Verification

- `python -m unittest discover -s tests`: 445 passed, 230 skipped because the Linux worker has no Tk display.
- `python tools/lint_bank.py`: passed.
- `python tools/verify_installation.py`: passed.
- `python tools/run_quality_checks.py`: Ruff, Black, and mypy passed.
- New ingestion modules: Ruff, Black, mypy, and focused importer/schema tests passed.

## Blocking gates

1. Push `implementation/sc900-v8-baseline` using a Git-capable authenticated environment that preserves the existing commit history.
2. Run the repaired Windows GitHub Actions workflow for `a0badb8f8cbbf8d2dd8888fe48248a06d380d34e`.
3. Verify the Windows PyInstaller build and release smoke test, including bundled SC-900 configuration, taxonomy, and bank loading.
4. Do not create a baseline tag until all three gates are green for the same SHA.

## Follow-up technical debt

- The importer uses JSON files as a portable persistent store; move to a transactional database if concurrent writers or substantially larger banks require it.
- Probable duplicate review is heuristic and intentionally conservative; add human-review tooling before automated merging.
- Integrate the compiler output into a release-approved bank promotion workflow rather than changing the placeholder-bank default automatically.
