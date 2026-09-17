# Package A verification

Observed closure for SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 Package A, including PACKAGE-A-EXTERNAL-REVIEW-REPAIR-002.

```text
WORK_ID = SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A
REPAIR_ID = PACKAGE-A-EXTERNAL-REVIEW-REPAIR-002
PACKAGE-A-EXTERNAL-REVIEW-REPAIR-001 = APPLIED
PACKAGE-A-EXTERNAL-REVIEW-REPAIR-002 = APPLIED
DESIGN_REVIEW_HEAD = 0e4f76ba2917e04427321a80de698867fc54ed95
DESIGN_AUTHORITY = 0e4f76ba2917e04427321a80de698867fc54ed95
START_MAIN_SHA = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
PRIOR_REVIEWED_HEAD = f20d252472429ff1931ef15cdf2892d4bae13ea1
START_HEAD = caee25ead7915e2260c23ce010a9c82dafa8d11c
IMPLEMENTATION_HEAD = a34a0e8206503694936730c3564fd5d3117f1bbb
EXACT_HEAD = receipt commit immediately following IMPLEMENTATION_HEAD on this branch

PRODUCTION_QUESTION_WORDING_CHANGES = 0
PRODUCTION_BANK_ACTIVATION = NO
AUTHORIZED_CONTENT_REVISION_MANIFESTS_COUNT = 0
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
PRODUCTION_EXE_CHANGED = NO
MERGED = NO
PACKAGE_B_STARTED = NO

PACKAGE_A_TESTS = PASS (Ran 113 tests in 5.299s OK)
IDENTITY_SESSION_REGRESSION_WALL = PASS (Ran 88 tests in 0.305s OK)
FULL_UNITTEST_DISCOVERY = PASS (Ran 1030 tests in 54.376s OK; 0 failures, 0 errors, 0 skips)
QUALITY_CHECKS = PASS
BANK_LINT = PASS (python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings; 454 questions; 1 frozen warning)
INSTALLATION_VERIFICATION = PASS

PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
PRODUCTION_EXE_PRESENT = YES
PRODUCTION_EXE_SHA256 = 9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558

NO_AUTHORITY_BEHAVIOR = CURRENT_FAIL_CLOSED_BEHAVIOR_PRESERVED
REGISTERED_AUTHORITY_FAIL_BLOCKS_ORDINARY_LOAD = PASS
PROGRESS_PAYLOAD_SHAPE_VALIDATED_BEFORE_TRANSFORM = PASS
MICROSOFT_LEARN_AUTHORITY_ALLOWS_SUPPLEMENTAL_REFS = PASS
DUPLICATE_JSON_KEY_REASON_PRESERVED = PASS
TARGET_BOUND_PROGRESS_VERIFIED_WITHOUT_TIMESTAMP_COUPLING = PASS
STALE_AUTHORITY_CLEARED_ON_NO_REGISTRY = PASS
LEFTOVER_SOURCE_EXACT_RECONCILIATION = PASS
DIVERGENT_SOURCE_PROGRESS_PRESERVED = PASS
DIVERGENT_SOURCE_HISTORY_PRESERVED = PASS
MALFORMED_LEFTOVER_SOURCE_PRESERVED = PASS
RETRY_TIMESTAMP_INDEPENDENCE = PASS
TARGET_BYTES_UNCHANGED_ON_VALID_RECOVERY = PASS
ADMITTED_SYNTHETIC_REVISION = PASS
HISTORICAL_EVENTS_REWRITTEN = NO
QUARANTINE_RESURRECTION = NO
PENDING_SELECTION_ON_CHANGED_UNANSWERED_QUESTION = LOCAL_RESET
MIGRATION_IDEMPOTENCE = PASS
ATOMIC_BACKUP_WRITE_RECOVERY = PASS
TARGET_REGISTRATION_RESTORED = PASS
NONMUTATING_MIGRATION_READS = PASS

PACKAGE_A = STOPPED_FOR_INDEPENDENT_REVIEW
PACKAGE_B_AUTHORIZED = NO
PACKAGE_B_STARTED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

## 10.1 Diff boundary

`git diff --name-status 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD` at verification:

```text
M	app.py
M	app_analytics_mixin.py
M	app_game_mixin.py
M	app_session_builder_mixin.py
M	app_session_persistence_mixin.py
A	content_revision_authority.py
A	content_revision_migration.py
A	content_revision_registry.py
A	docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md
M	pyproject.toml
M	runtime_persistence.py
A	tests/test_content_revision_app_integration.py
A	tests/test_content_revision_authority.py
A	tests/test_content_revision_migration.py
M	tools/run_quality_checks.py
```

External-review repair files versus `PRIOR_REVIEWED_HEAD`:

```text
M	app.py
M	content_revision_authority.py
M	content_revision_migration.py
M	content_revision_registry.py
M	runtime_persistence.py
M	tests/test_content_revision_app_integration.py
M	tests/test_content_revision_authority.py
M	tests/test_content_revision_migration.py
```

`git status --short` was empty after the repair commit. No bank JSON, EXE, production evidence, PR13 artifact, recovery artifact, or unrelated source path appeared.

## 10.2 Focused Package-A tests

```text
python -m unittest tests.test_content_revision_authority tests.test_content_revision_migration tests.test_content_revision_app_integration -q
Ran 106 tests in 4.950s
OK
```

## 10.3 Identity/session regression wall

```text
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment1_adversarial_review tests.test_backlog1_segment2_session_identity tests.test_backlog1_segment2_session_app_integration tests.test_backlog1_segment3_adversarial_closure tests.test_sc900_final_bank_activation_migration -q
Ran 88 tests in 0.293s
OK
```

Existing no-authority fail-closed behavior remains unchanged. Failed registered admission now blocks `load_progress_if_present()`.

## 10.4 Full repository tests

```text
python -m unittest discover -s tests -q
Ran 1023 tests in 52.464s
OK
```

## 10.5 Quality / bank / install

```text
python -m tools.run_quality_checks
Quality checks passed.

python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings
SC-900 default-bank lint passed: 454 questions. (1 warnings reported, diagnostic --allow-warnings)

python -m tools.verify_installation
SC-900 installation verification passed.
```

The plan's positional `lint_bank` invocation is not accepted by the current CLI; the equivalent `--bank` form was used.

## 10.6 Production immutability

```text
BANK 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
EXE_PRESENT True
EXE 9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
```

Module-level `AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}`. No production manifest/review evidence was added. EXE was not rebuilt.

## 10.7 External-review repair outcomes

1. Registered authority FAIL keeps `content_revision_authority=None`, sets `progress_write_blocked=True`, preserves progress files, and does not call `load_progress_if_present()`.
2. Parseable malformed progress (`history` mapping, non-mapping questions/fingerprints, non-mapping quarantine, non-list lineage) fails closed before transform; source bytes remain unchanged.
3. Edge and review `authority_refs` require at least one normalized `https://learn.microsoft.com/` string; supplemental non-Microsoft refs are allowed; schema remains `list[str]`.
4. Registered duplicate JSON keys return `DUPLICATE_JSON_KEY`; missing/unreadable manifests remain `REGISTRY_HASH_MISMATCH`.
5. Target whole-bank fingerprint is not sufficient proof of an applied migration. Crash/retry with leftover source + verified target at a later timestamp archives leftover source, leaves target bytes unchanged, and does not duplicate lineage.

## 10.8 PACKAGE-A-EXTERNAL-REVIEW-REPAIR-002

Fresh verification from implementation head `a34a0e8206503694936730c3564fd5d3117f1bbb`.

```text
STALE_AUTHORITY_CLEARED_ON_NO_REGISTRY = PASS
LEFTOVER_SOURCE_EXACT_RECONCILIATION = PASS
DIVERGENT_SOURCE_PROGRESS_PRESERVED = PASS
DIVERGENT_SOURCE_HISTORY_PRESERVED = PASS
MALFORMED_LEFTOVER_SOURCE_PRESERVED = PASS
RETRY_TIMESTAMP_INDEPENDENCE = PASS
TARGET_BYTES_UNCHANGED_ON_VALID_RECOVERY = PASS
```

Repair files versus `START_HEAD` `caee25ead7915e2260c23ce010a9c82dafa8d11c`:

```text
M	app.py
M	runtime_persistence.py
M	tests/test_content_revision_app_integration.py
M	docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md
```

`content_revision_migration.py` was an authorized primary file and did not need to change: leftover recovery now reuses `migrate_progress_payload()` plus a retry-timestamp-only compare in `runtime_persistence.py`.

### Repair-002 tests

```text
python -m unittest tests.test_content_revision_authority tests.test_content_revision_migration tests.test_content_revision_app_integration -q
Ran 113 tests in 5.299s
OK
```

```text
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment1_adversarial_review tests.test_backlog1_segment2_session_identity tests.test_backlog1_segment2_session_app_integration tests.test_backlog1_segment3_adversarial_closure tests.test_sc900_final_bank_activation_migration -q
Ran 88 tests in 0.305s
OK
```

```text
python -m unittest discover -s tests -q
Ran 1030 tests in 54.376s
OK
```

```text
python -m tools.run_quality_checks
Quality checks passed.

python -m tools.lint_bank --bank sc900_bank_v8_final.json --allow-warnings
SC-900 default-bank lint passed: 454 questions. (1 warnings reported, diagnostic --allow-warnings)

python -m tools.verify_installation
SC-900 installation verification passed.
```

```text
BANK 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
EXE_PRESENT True
EXE 9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
AUTHORIZED_CONTENT_REVISION_MANIFESTS = {}
```

Outcomes:

1. Loading an unregistered Bank B after admitted REV_A clears `content_revision_authority`, keeps `progress_write_blocked=False`, permits ordinary `load_progress_if_present()`, and does not reuse REV_A history continuity or source-session discovery.
2. Registered authority FAIL still keeps authority `None`, sets `progress_write_blocked=True`, and does not call `load_progress_if_present()`.
3. Exact leftover source retry at a later timestamp archives/removes source, leaves target bytes unchanged, and preserves original `migrated_at`.
4. Leftover source with newer attempts, extra history, malformed parseable `history`, wrong source fingerprint, or invalid target lineage fails closed and preserves source and target byte-for-byte. Matching whole-bank fingerprint alone is never sufficient to delete source.

```text
PACKAGE-A-EXTERNAL-REVIEW-REPAIR-002 = APPLIED
PACKAGE_A = STOPPED_FOR_INDEPENDENT_REVIEW
PACKAGE_B_STARTED = NO
MERGE_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
```

## PACKAGE-A-CI-EVIDENCE-CLOSURE-001

Existing `pull_request` workflows against `main` are branch-scoped and skipped Package A. Path B added `.github/workflows/package-a-verification.yml` only. No application, runtime, or test semantics were changed.

```text
WORK_ID = SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A-CI-EVIDENCE-CLOSURE-001
PR_NUMBER = 33
PR_URL = https://github.com/IXI-2773/Microsoft_SC-900_Test_Learning_Engine/pull/33
PR_STATE = OPEN / DRAFT / UNMERGED
MERGE_AUTHORIZED = NO

PRIOR_EXTERNALLY_REVIEWED_HEAD = 972e4020261a6a3c7f1cc4c87f275d5cedbaac45
CI_WORKFLOW_COMMIT = 87ccf1a8a38138fd87062e29236836f8319acec3
CI_VERIFIED_HEAD = 87ccf1a8a38138fd87062e29236836f8319acec3
CHECKED_OUT_SHA = 87ccf1a8a38138fd87062e29236836f8319acec3
FINAL_CHECKED_OUT_SHA = 87ccf1a8a38138fd87062e29236836f8319acec3

WORKFLOW_RUN_ID = 35270373851
JOB_IDS = 105367872509
WORKFLOW_NAME = Verify Package A content-revision equivalence
CI_CHECKS = verify-package-a
PACKAGE_A_CI = PASS

PACKAGE_A_TESTS_CI = PASS / 113
IDENTITY_SESSION_WALL_CI = PASS / 88
FULL_UNITTEST_DISCOVERY_CI = PASS / 1030
QUALITY_CHECKS_CI = PASS
BANK_LINT_CI = PASS
INSTALLATION_VERIFICATION_CI = PASS

PRODUCTION_BANK_SHA256_CI = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
PRODUCTION_EXE_SHA256_CI = 9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
AUTHORIZED_CONTENT_REVISION_MANIFESTS_CI = {}

OBSERVED_NON_PACKAGE_A_CHECKS =
  verify-consolidated-main SKIPPED (run 35270373924 / job 105367906614)
  verify-extractor SKIPPED (run 35270373863 / job 105367925234)
  verify-existing-source SKIPPED (run 35270373879 / job 105367873811)

PACKAGE_A_CODE_REVIEW = PASS
PACKAGE_A_CI_EVIDENCE = PASS
PACKAGE_A = VERIFIED_FOR_INTEGRATION_DECISION
PACKAGE_B_STARTED = NO
PACKAGE_B_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

