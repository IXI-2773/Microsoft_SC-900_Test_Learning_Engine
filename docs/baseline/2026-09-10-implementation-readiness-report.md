# SC-900 v8 Implementation Readiness Report

## Status

**NOT READY to freeze or release.** The local engineering and ingestion baseline is verified, but the required Windows build and executable smoke test have not run. The implementation branch could not be pushed from this environment, so GitHub Actions CI has not run either.

## Branch and commits

- Branch: `implementation/sc900-v8-baseline`
- Local commits beyond the remote: `0657135`, `b7d31d1`, `944a261`, `b4734cf`, `196788c`, `dd27cfb`, `7999d53`, `34b4a9b`

## Ingestion baseline

- Versioned SC-900 taxonomy: `config/certifications/sc900-2026.json`
- Canonical question/source-material schema with source provenance and origin tracking: `ingestion/models.py`
- JSONL importer and persistent question/material/quarantine/review stores: `ingestion/importer.py`
- Exact duplicates are skipped; probable duplicates are placed in review; conceptually related records retain a relation; malformed rows are quarantined with reason codes.
- Imports are deterministic/idempotent by canonical ID, report source statistics and reason counts, and have a 1,000-record integration test.
- Only accepted question records compile to the current runtime-bank contract. Source material never enters the runnable bank.
- CLI: `python tools/import_sc900_content.py EXPORT.jsonl --store data/sc900-content --compile imported_sc900_bank.json`

## Verification

- `python -m unittest discover -s tests`: 443 passed, 230 skipped because the Linux worker has no Tk display.
- `python tools/lint_bank.py`: passed.
- `python tools/verify_installation.py`: passed.
- `python tools/run_quality_checks.py`: Ruff, Black, and mypy passed.
- New ingestion modules: Ruff, Black, mypy, and focused importer/schema tests passed.

## Blocking gates

1. Push `implementation/sc900-v8-baseline` with a GitHub-authenticated environment.
2. Run the Windows GitHub Actions workflow.
3. Verify the Windows PyInstaller build and release smoke test, including bundled SC-900 configuration/bank loading.
4. Do not create `SC900_V8_BASELINE` until all three gates are green.

## Follow-up technical debt

- The importer uses JSON files as a portable persistent store; move to a transactional database if concurrent writers or substantially larger banks require it.
- Probable duplicate review is heuristic and intentionally conservative; add human-review tooling before automated merging.
- Integrate the compiler output into a release-approved bank promotion workflow rather than changing the placeholder-bank default automatically.
