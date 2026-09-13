# Packaging rehearsal

## Contract

`release_resources.REQUIRED_RUNTIME_RESOURCES` now includes:

1. `cert_profile_sc900.json`
2. `sc900_bank_v8_final.json` (active runtime bank, derived from `QUESTION_BANK_FILENAME`)
3. `sc900_bank_v8_baseline.json` (historical/recovery artifact)
4. `config/certifications/sc900-2026.json`

`tools/build_windows_release.py` still feeds `pyinstaller_resource_args()` into `--add-data`. Changing `QUESTION_BANK_FILENAME` alone would not have packaged the new file; the resource tuple was updated deliberately.

`tests/test_release_workflow.py` asserts the four resources and archive-listing acceptance for both POSIX and Windows separators.

`PACKAGING_CONTRACT_VERIFIED = YES`

## Isolated binary rehearsal

PyInstaller 6.22.2 built a one-file windowed executable in:

`C:\Users\Drago\AppData\Local\Temp\sc900-activation-packaging-rehearsal-001\dist\SC900TestLearningEngine.exe`

Archive listing (`PyInstaller.utils.cliutils.archive_viewer --list --brief`) includes:

- `sc900_bank_v8_final.json`
- `sc900_bank_v8_baseline.json`
- `cert_profile_sc900.json`
- `config\certifications\sc900-2026.json`

No `dist/`, `build/`, or `.spec` artifacts from that rehearsal are committed.

The packaged application can resolve the configured runtime bank by filename. The windowed GUI executable was not launched as an interactive learner session.

`PACKAGING_CONTRACT_VERIFIED = YES`

`PACKAGED_BINARY_EXECUTION_VERIFIED = NO`
