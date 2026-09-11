# SC-900 v8 Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transplant the proven v8 learning engine into the SC-900 repository, isolate certification-specific identity/content, and produce a fully rebranded SC-900 Test Learning Engine baseline without changing Smart Practice behavior.

**Architecture:** Copy only reusable v8 engine/test/tool files from the frozen SY0-701 source revision. Centralize SC-900 identity in one profile module, replace Security+-specific content with an eight-question original placeholder bank, make generic bank/release tools resolve that bank from the profile, and adapt source-specific regression tests rather than carrying obsolete Security+ fixtures forward.

**Tech Stack:** Python 3.11, Tkinter, unittest, JSON question banks, PyInstaller, Ruff, Black, mypy, Windows batch launch/build tooling.

**Spec:** `docs/superpowers/specs/2026-09-10-sc900-v8-baseline-design.md`

## Global Constraints

- Source repository: `IXI-2773/Comptia-SY0-701-Test-Learning-Engine`.
- Frozen source revision: `5c099196525f2df236d4c80069e2b3a00a70bf94`.
- Destination repository: `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`.
- Application brand: `SC-900 Test Learning Engine`.
- Reusable engine version: `8.0.0`.
- Certification vendor: `Microsoft`.
- Certification exam code: `SC-900`.
- Certification name: `Security, Compliance, and Identity Fundamentals`.
- Default bank filename: `sc900_bank.json`.
- Baseline placeholder-bank count: `8`.
- Runtime namespace: `SC900TestLearningEngine`.
- Windows executable basename: `SC900TestLearningEngine`.
- Do not ship SY0-701, screenshot-derived, or Security+ study-guide question banks as SC-900 content.
- Do not redesign Smart Practice, learner modeling, analytics, progress semantics, confidence controls, answer shuffling, autosave/session migration, backup/checkpoint behavior, or issue quarantine during this migration.
- External/public/permitted SC-900 source material is outside this plan and later enters through staging, normalization, validation, deduplication, and review.
- Learner-facing runtime/build surfaces must not identify the application as CompTIA, Security+, SY0-701, Security Testing Engine, or SecurityTestingEngine after conversion.
- Provenance/spec/plan documents may name the SY0-701 source repository because that is historical provenance.
- Learner-facing documentation must include: `Unofficial study application. Not affiliated with or endorsed by Microsoft.`

## File Map

### Copy unchanged from source commit

Root modules:

`analytics_models.py`, `analytics_recommendations.py`, `analytics_summary.py`, `app_analytics_mixin.py`, `app_constants.py`, `app_game_mixin.py`, `app_question_flow_mixin.py`, `app_question_render_mixin.py`, `app_session_builder_mixin.py`, `app_session_persistence_mixin.py`, `application_bootstrap.py`, `bank_models.py`, `config_store.py`, `legacy_source_layout.py`, `pe_validation.py`, `progress_models.py`, `progress_store.py`, `question_widgets.py`, `render_cache.py`, `runtime_persistence.py`, `save_queue.py`, `session_models.py`, `session_store.py`, `smart_practice_cache.py`, `smart_practice_concept_graph.py`, `smart_practice_core.py`, `smart_practice_measurement.py`, `smart_practice_policy.py`, `smart_practice_profile.py`, `smart_practice_question_value.py`, `smart_practice_worker.py`, `source_trust.py`, `storage_utils.py`, `study_question_utils.py`, `ui_theme.py`, `ui_typography.py`, `widget_models.py`.

Repository/tooling:

`.gitattributes`, `.gitignore`, `LICENSE`, `requirements-dev.txt`, `run_quality_checks.bat`, `tools/cleanup_runtime_files.py`.

Tests initially copied:

`tests/test_analytics_calculation.py`, `tests/test_application_bootstrap.py`, `tests/test_release_tools.py`, `tests/test_security_testing_engine.py`, `tests/test_smart_practice_core.py`, `tests/test_smart_practice_worker.py`, `tests/test_study_question_utils.py`.

### Copy then modify

`app.py`, `app_info.py`, `question_bank.py`, `pyproject.toml`, `tools/benchmark_engine.py`, `tools/build_release.py`, `tools/clean_bank.py`, `tools/rebalance_bank_choice_order.py`, `tools/run_quality_checks.py`, `tools/smoke_test.py`, `tools/validate_bank.py`, `tests/test_release_tools.py`, `tests/test_security_testing_engine.py`.

### Create

`certification_profile.py`, `sc900_bank.json`, `sc900_test_learning_engine_v8.py`, `sc900_test_learning_engine_v8.pyw`, `run_sc900_v8.bat`, `build_sc900_v8.bat`, `tests/test_certification_profile.py`, `tests/test_sc900_bank.py`, `tests/test_sc900_branding.py`, `docs/provenance/source-v8-baseline.md`, `README.md`, `README - Start Here.txt`, `CHANGELOG.md`.

### Never transplant

`public_sy0701_bank_v4.json`, `public_sy0701_bank_v4_clean.json`, `public_sy0701_bank_v4_plus_screenshot_drafts_review.json`, `public_sy0701_bank_v4_plus_studyguide_clean.json`, every `chapter*_screenshot_*.json`, `chapter_screenshot_ocr_draft_bank.json`, `chapter_screenshot_review_stubs_import_bank.json`, `free_study_guide_a5_assessments_bank.json`, `free_study_guide_a5_import_bank.json`, `docs/public_sy0701_audit_v4.md`, `tools/import_chapter_screenshots.py`, `tools/import_free_study_guide.py`.

---

### Task 1: Transplant the frozen v8 engine without Security+ content

**Files:** use the allow-lists in `File Map`; create `docs/provenance/source-v8-baseline.md`.

**Interfaces:** consumes source commit `5c099196525f2df236d4c80069e2b3a00a70bf94`; produces a syntactically valid v8 source tree with no copied Security+ banks/importers.

- [ ] **Step 1: Verify the source revision**

```bash
git -C ../Comptia-SY0-701-Test-Learning-Engine fetch origin
git -C ../Comptia-SY0-701-Test-Learning-Engine checkout 5c099196525f2df236d4c80069e2b3a00a70bf94
git -C ../Comptia-SY0-701-Test-Learning-Engine rev-parse HEAD
```

Expected final line: `5c099196525f2df236d4c80069e2b3a00a70bf94`.

- [ ] **Step 2: Copy only files in the `Copy unchanged` and `Copy then modify` allow-lists**

Do not copy the `Never transplant` files. Preserve the destination's existing `docs/superpowers/` tree.

- [ ] **Step 3: Prove excluded source artifacts are absent**

```bash
git ls-files | grep -E '(^|/)(public_sy0701_.*\.json|chapter.*screenshot.*\.json|free_study_guide_a5_.*\.json|public_sy0701_audit_v4\.md|import_chapter_screenshots\.py|import_free_study_guide\.py)$' && exit 1 || true
```

Expected: no matching tracked paths and exit code `0`.

- [ ] **Step 4: Create provenance record**

Create `docs/provenance/source-v8-baseline.md`:

```markdown
# v8 Source Baseline

The SC-900 Test Learning Engine baseline was derived from:

- Repository: `IXI-2773/Comptia-SY0-701-Test-Learning-Engine`
- Source commit: `5c099196525f2df236d4c80069e2b3a00a70bf94`
- Source application version: `8.0.0`

The SC-900 repository intentionally excludes the source repository's SY0-701 question banks and source-specific import artifacts. Certification content is maintained separately from reusable engine logic.
```

- [ ] **Step 5: Compile the copied tree**

```bash
python -m compileall -q .
```

Expected: exit code `0`.

- [ ] **Step 6: Commit the transplant**

```bash
git add .
git commit -m "chore: transplant frozen v8 engine baseline"
```

---

### Task 2: Centralize SC-900 identity and isolate runtime storage

**Files:** create `certification_profile.py`, `tests/test_certification_profile.py`; modify `app_info.py`, `app.py`, `pyproject.toml`.

**Interfaces:** `certification_profile.py` owns all certification/build identity constants; `app_info.py` remains a compatibility export of `APP_NAME` and `APP_VERSION`.

- [ ] **Step 1: Write failing profile/runtime tests**

Create `tests/test_certification_profile.py`:

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app
import certification_profile as profile


class CertificationProfileTests(unittest.TestCase):
    def test_sc900_identity_is_centralized(self):
        self.assertEqual("Test Learning Engine", profile.ENGINE_NAME)
        self.assertEqual("8.0.0", profile.ENGINE_VERSION)
        self.assertEqual("SC-900 Test Learning Engine", profile.APP_NAME)
        self.assertEqual("Microsoft", profile.CERT_VENDOR)
        self.assertEqual("SC-900", profile.CERT_EXAM_CODE)
        self.assertEqual("Security, Compliance, and Identity Fundamentals", profile.CERT_NAME)
        self.assertEqual("sc900_bank.json", profile.DEFAULT_BANK_FILENAME)
        self.assertEqual("SC900TestLearningEngine", profile.RUNTIME_NAMESPACE)
        self.assertEqual("SC900TestLearningEngine", profile.EXECUTABLE_BASENAME)
        self.assertEqual(8, profile.EXPECTED_BANK_COUNT)

    def test_packaged_runtime_uses_sc900_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(app.sys, "frozen", True, create=True),
                mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}, clear=False),
            ):
                self.assertEqual(Path(tmp) / "SC900TestLearningEngine", app.resolve_user_data_dir())

    def test_sc900_has_no_cross_product_packaged_migration_sources(self):
        with mock.patch.object(app.sys, "frozen", True, create=True):
            self.assertEqual([], app.packaged_legacy_user_data_dirs())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to prove the old identity fails**

```bash
python -m unittest tests.test_certification_profile -v
```

Expected: import/value failures before profile conversion.

- [ ] **Step 3: Create `certification_profile.py`**

```python
ENGINE_NAME = "Test Learning Engine"
ENGINE_VERSION = "8.0.0"

APP_NAME = "SC-900 Test Learning Engine"
CERT_VENDOR = "Microsoft"
CERT_EXAM_CODE = "SC-900"
CERT_NAME = "Security, Compliance, and Identity Fundamentals"

DEFAULT_BANK_FILENAME = "sc900_bank.json"
DEFAULT_SOURCE_NAME = "Original SC-900 Practice Questions"
EXPECTED_BANK_COUNT = 8

RUNTIME_NAMESPACE = "SC900TestLearningEngine"
EXECUTABLE_BASENAME = "SC900TestLearningEngine"
RELEASE_DIRNAME = "SC900TestLearningEngine"
LOG_FILENAME = "sc900_test_learning_engine.log"
```

- [ ] **Step 4: Convert `app_info.py` into compatibility exports**

```python
from certification_profile import APP_NAME, ENGINE_VERSION

APP_VERSION = ENGINE_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
```

- [ ] **Step 5: Replace identity/runtime hard-coding in `app.py`**

Add:

```python
from certification_profile import DEFAULT_BANK_FILENAME, LOG_FILENAME, RUNTIME_NAMESPACE
```

Use:

```python
def resolve_user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / RUNTIME_NAMESPACE
    return APP_DIR / "user_data"


def packaged_legacy_user_data_dirs() -> list[Path]:
    return []
```

Replace `DEFAULT_BANK_CLEAN`, `DEFAULT_BANK_MERGED`, and `DEFAULT_BANK_LEGACY` with:

```python
DEFAULT_BANK = first_existing_path(
    APP_DIR / DEFAULT_BANK_FILENAME,
    RESOURCE_DIR / DEFAULT_BANK_FILENAME,
)
LOG_PATH = USER_DATA_DIR / "logs" / LOG_FILENAME
```

Do not alter `progress_file_strength`, `best_progress_strength`, `auto_migrate_packaged_runtime_data`, or session-snapshot migration logic; the empty packaged source list prevents cross-product import while preserving those engine helpers.

- [ ] **Step 6: Register `certification_profile` with Ruff/mypy**

Add `"certification_profile"` to `known-first-party` and `certification_profile.py` to the mypy `files` list in `pyproject.toml`.

- [ ] **Step 7: Run focused tests**

```bash
python -m unittest tests.test_certification_profile tests.test_application_bootstrap -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add certification_profile.py app_info.py app.py pyproject.toml tests/test_certification_profile.py
git commit -m "feat: centralize SC-900 application identity"
```

---

### Task 3: Add an exact original eight-question SC-900 placeholder bank

**Files:** create `sc900_bank.json`, `tests/test_sc900_bank.py`; modify `question_bank.py`.

**Interfaces:** `load_bank(Path("sc900_bank.json"))` returns 8 valid questions across 4 domains; blank `source_name` falls back to `DEFAULT_SOURCE_NAME`.

- [ ] **Step 1: Write failing bank tests**

Create `tests/test_sc900_bank.py`:

```python
import unittest
from pathlib import Path

from bank_models import as_bank_question
from certification_profile import DEFAULT_SOURCE_NAME
from question_bank import infer_source_name, load_bank

ROOT = Path(__file__).resolve().parents[1]


class SC900BankTests(unittest.TestCase):
    def test_placeholder_bank_has_expected_coverage(self):
        bank = load_bank(ROOT / "sc900_bank.json")
        self.assertEqual(8, len(bank["questions"]))
        self.assertEqual(
            {
                "Security, compliance, and identity concepts",
                "Microsoft Entra",
                "Microsoft security solutions",
                "Microsoft compliance solutions",
            },
            {q["domain"] for q in bank["questions"]},
        )
        self.assertTrue(all(q["source_name"] == DEFAULT_SOURCE_NAME for q in bank["questions"]))

    def test_missing_source_name_uses_sc900_fallback(self):
        question = as_bank_question({"prompt": "x", "choices": {"A": "a"}, "correct": ["A"]})
        self.assertEqual(DEFAULT_SOURCE_NAME, infer_source_name(question, "SC-900"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the bank tests and verify failure**

```bash
python -m unittest tests.test_sc900_bank -v
```

Expected: failure because the new bank/profile fallback is not complete.

- [ ] **Step 3: Replace Security+-specific source inference**

Import `DEFAULT_SOURCE_NAME` into `question_bank.py` and replace `infer_source_name` with:

```python
def infer_source_name(question: BankQuestion, default_title: str = "Practice Test") -> str:
    source_name = sanitize_text(question.get("source_name", ""))
    if source_name:
        return source_name
    return DEFAULT_SOURCE_NAME
```

Leave sanitation, answer validation, duplicate metadata, and shuffling logic unchanged.

- [ ] **Step 4: Generate the exact placeholder JSON**

Run this script once from repository root:

```python
import json
from pathlib import Path

source = "Original SC-900 Practice Questions"
questions = [
    {
        "question_number": 1,
        "prompt": "Which Zero Trust principle requires each access request to be evaluated using available identity, device, location, and risk signals?",
        "choices": {"A": "Verify explicitly", "B": "Trust the internal network by default", "C": "Disable identity signals", "D": "Grant permanent access after the first sign-in"},
        "correct": ["A"],
        "general_explanation": "Verify explicitly means authentication and authorization decisions should use relevant signals instead of assuming trust from network location or a previous sign-in.",
        "choice_explanations": {}, "domain": "Security, compliance, and identity concepts", "chapter": "Baseline placeholders", "subtitle": "Zero Trust", "question_type": "single", "topics": ["Zero Trust"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "1", "study_focus": "Recognize the core Zero Trust principles.", "duplicate_of": None,
    },
    {
        "question_number": 2,
        "prompt": "In the shared responsibility model, which responsibility remains with the customer when using a cloud service?",
        "choices": {"A": "Operating the provider's physical datacenter", "B": "Maintaining the provider's cooling system", "C": "Protecting and governing the customer's data and identities according to the service model", "D": "Replacing failed hardware in the provider's server racks"},
        "correct": ["C"],
        "general_explanation": "Cloud providers operate provider infrastructure, while customers retain responsibilities for their own data, identities, access, and configuration according to the service model.",
        "choice_explanations": {}, "domain": "Security, compliance, and identity concepts", "chapter": "Baseline placeholders", "subtitle": "Shared responsibility", "question_type": "single", "topics": ["Shared responsibility"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "1", "study_focus": "Separate provider and customer responsibilities.", "duplicate_of": None,
    },
    {
        "question_number": 3,
        "prompt": "Which Microsoft service provides cloud identity and access management for users, groups, applications, and authentication?",
        "choices": {"A": "Microsoft Sentinel", "B": "Microsoft Entra ID", "C": "Microsoft Defender for Cloud", "D": "Microsoft Purview Data Loss Prevention"},
        "correct": ["B"],
        "general_explanation": "Microsoft Entra ID is Microsoft's cloud identity and access management service for identities, applications, authentication, and access controls.",
        "choice_explanations": {}, "domain": "Microsoft Entra", "chapter": "Baseline placeholders", "subtitle": "Identity", "question_type": "single", "topics": ["Microsoft Entra ID"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "2", "study_focus": "Identify the role of Microsoft Entra ID.", "duplicate_of": None,
    },
    {
        "question_number": 4,
        "prompt": "What is the main security benefit of multifactor authentication?",
        "choices": {"A": "It automatically grants administrator privileges", "B": "It requires evidence from more than one authentication factor", "C": "It removes the need for authorization", "D": "It encrypts every file stored by the user"},
        "correct": ["B"],
        "general_explanation": "Multifactor authentication reduces reliance on a password alone by requiring evidence from multiple authentication-factor categories.",
        "choice_explanations": {}, "domain": "Microsoft Entra", "chapter": "Baseline placeholders", "subtitle": "Authentication", "question_type": "single", "topics": ["MFA"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "2", "study_focus": "Understand why MFA reduces single-factor risk.", "duplicate_of": None,
    },
    {
        "question_number": 5,
        "prompt": "Which Microsoft service provides cloud security posture management and workload protection recommendations across cloud resources?",
        "choices": {"A": "Microsoft Defender for Cloud", "B": "Microsoft Sentinel", "C": "Microsoft Entra ID", "D": "Microsoft Purview Audit"},
        "correct": ["A"],
        "general_explanation": "Microsoft Defender for Cloud provides security posture management and workload protection capabilities for cloud resources.",
        "choice_explanations": {}, "domain": "Microsoft security solutions", "chapter": "Baseline placeholders", "subtitle": "Cloud security", "question_type": "single", "topics": ["Defender for Cloud"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "3", "study_focus": "Distinguish Defender for Cloud from identity, SIEM, and compliance services.", "duplicate_of": None,
    },
    {
        "question_number": 6,
        "prompt": "Which Microsoft service is a cloud-native SIEM and security orchestration platform used to collect, correlate, investigate, and respond to security data?",
        "choices": {"A": "Microsoft Compliance Manager", "B": "Microsoft Entra ID", "C": "Microsoft Sentinel", "D": "Microsoft Purview Data Loss Prevention"},
        "correct": ["C"],
        "general_explanation": "Microsoft Sentinel provides cloud-native SIEM capabilities along with security orchestration and response workflows.",
        "choice_explanations": {}, "domain": "Microsoft security solutions", "chapter": "Baseline placeholders", "subtitle": "SIEM and SOAR", "question_type": "single", "topics": ["Microsoft Sentinel"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "3", "study_focus": "Recognize Microsoft Sentinel's SIEM and orchestration role.", "duplicate_of": None,
    },
    {
        "question_number": 7,
        "prompt": "Which Microsoft Purview capability helps detect and prevent inappropriate sharing of sensitive information?",
        "choices": {"A": "eDiscovery", "B": "Data Loss Prevention", "C": "Audit", "D": "Compliance Manager"},
        "correct": ["B"],
        "general_explanation": "Microsoft Purview Data Loss Prevention uses policies to identify sensitive information and help prevent inappropriate use or sharing.",
        "choice_explanations": {}, "domain": "Microsoft compliance solutions", "chapter": "Baseline placeholders", "subtitle": "Information protection", "question_type": "single", "topics": ["Data Loss Prevention"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "4", "study_focus": "Distinguish DLP from investigation and assessment capabilities.", "duplicate_of": None,
    },
    {
        "question_number": 8,
        "prompt": "Which Microsoft Purview solution helps organizations assess and track improvement actions against compliance requirements?",
        "choices": {"A": "Compliance Manager", "B": "Data Loss Prevention", "C": "eDiscovery", "D": "Insider Risk Management"},
        "correct": ["A"],
        "general_explanation": "Compliance Manager helps organizations assess compliance posture and track recommended improvement actions against applicable requirements.",
        "choice_explanations": {}, "domain": "Microsoft compliance solutions", "chapter": "Baseline placeholders", "subtitle": "Compliance assessment", "question_type": "single", "topics": ["Compliance Manager"], "flagged_issues": [], "source_page": "", "source_name": source, "objective_code": "4", "study_focus": "Recognize Compliance Manager's assessment and improvement-action role.", "duplicate_of": None,
    },
]
Path("sc900_bank.json").write_text(json.dumps({"title": "SC-900 Baseline Placeholder Bank", "questions": questions}, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 5: Validate/test the bank**

```bash
python tools/validate_bank.py sc900_bank.json
python -m unittest tests.test_sc900_bank -v
```

Expected: validator exits `0`; bank tests pass.

- [ ] **Step 6: Commit**

```bash
git add sc900_bank.json question_bank.py tests/test_sc900_bank.py
git commit -m "feat: add validated SC-900 placeholder bank"
```

---

### Task 4: Convert generic bank tools and remove source-specific regression fixtures

**Files:** modify `tools/benchmark_engine.py`, `tools/clean_bank.py`, `tools/rebalance_bank_choice_order.py`, `tools/validate_bank.py`, `tests/test_security_testing_engine.py`.

**Interfaces:** every generic bank tool defaults to `sc900_bank.json`; the large engine regression suite no longer imports the excluded screenshot importer or requires excluded SY0-701 bank files.

- [ ] **Step 1: Add SC-900 defaults to generic bank tools**

For `tools/benchmark_engine.py` and `tools/validate_bank.py`, import `DEFAULT_BANK_FILENAME` from `certification_profile` and set the existing default path constant to `ROOT / DEFAULT_BANK_FILENAME`.

For `tools/clean_bank.py`, import `DEFAULT_BANK_FILENAME` and use:

```python
DEFAULT_SOURCE = ROOT / DEFAULT_BANK_FILENAME
DEFAULT_OUTPUT = ROOT / "sc900_bank_clean.json"
```

For `tools/rebalance_bank_choice_order.py`, import `DEFAULT_BANK_FILENAME` and use:

```python
DEFAULT_BANK_PATH = ROOT / DEFAULT_BANK_FILENAME
```

Do not change each tool's cleaning, validation, benchmark, or answer-order algorithm.

- [ ] **Step 2: Remove the excluded screenshot-import dependency from the regression suite**

Delete this import from `tests/test_security_testing_engine.py`:

```python
from tools import import_chapter_screenshots
```

Delete these seven source-importer tests because the importer itself is intentionally excluded from the SC-900 baseline:

```text
test_chapter_screenshot_filename_parses_source_question_number
test_chapter_screenshot_metadata_infers_chapter_three_architecture
test_chapter_screenshot_ocr_parser_prefers_first_explanation_match
test_chapter_screenshot_manifest_handles_missing_ocr_without_importing
test_verified_chapter_screenshot_record_maps_to_domain_metadata
test_chapter_screenshot_review_record_is_quarantined
test_verified_chapter_screenshot_duplicate_is_skipped
```

- [ ] **Step 3: Replace Security+-specific runtime migration test**

Delete `test_packaged_runtime_auto_migrates_stronger_project_progress`; runtime helper behavior remains covered by generic progress/persistence tests, while SC-900 cross-product isolation is now asserted by `test_sc900_has_no_cross_product_packaged_migration_sources`.

Change `test_frozen_runtime_data_uses_local_app_data` expected suffix to `SC900TestLearningEngine`.

- [ ] **Step 4: Replace bank-content regression tests with SC-900 baseline equivalents**

In `tests/test_security_testing_engine.py`:

- change `test_load_bank_has_expected_question_count` to load `sc900_bank.json` and expect `8`;
- delete `test_merged_bank_includes_imported_study_guide_assessments` because it verifies an excluded source;
- change `test_merged_bank_validator_has_no_warnings` to validate `sc900_bank.json`;
- change `test_bank_validation_report_has_no_issues` to validate `sc900_bank.json` and expect count `8`;
- change `test_merged_bank_benchmark_stays_within_regression_guardrails` to benchmark `sc900_bank.json` with `smart_count="8"`, preserving the timing assertions;
- delete `test_merged_bank_q1105_uses_port_mirroring_answer_key` because Q1105 is excluded content;
- delete `test_load_bank_infers_public_source_name_defaults` because `tests/test_sc900_bank.py` now tests the profile fallback;
- replace `test_load_bank_trims_embedded_follow_on_questions_from_explanations` with a temporary-bank fixture containing two synthetic prompts and an explanation containing `QUESTION 2`, then assert the first explanation is trimmed before the embedded marker; this preserves sanitation behavior without depending on Q743;
- replace `test_clean_bank_default_preserves_runtime_file_stem` paths with `C:/tmp/sc900_bank.json` and assert the runtime stem/progress prefix is `sc900_bank`.

- [ ] **Step 5: Convert the release packager fixture embedded in the large test module**

In `test_release_packager_outputs_single_exe_folder`, replace every `SecurityTestingEngine` path/name with `SC900TestLearningEngine`; patch `BANK_FILE` to a temporary `sc900_bank.json` containing the eight-question bank or patch `_release_manifest` only if the test intentionally isolates staging. Expected output must include `SC900TestLearningEngine.exe`, not the legacy name.

- [ ] **Step 6: Prove no excluded-content dependency remains in executable tests/tools**

```bash
git grep -nE 'public_sy0701|import_chapter_screenshots|Free Study Guide A5|q1105' -- tests tools '*.py' || true
```

Expected: no results except provenance/spec/plan files, which are outside the supplied path set.

- [ ] **Step 7: Run the converted regression subset**

```bash
python -m unittest tests.test_security_testing_engine tests.test_sc900_bank -v
```

Expected: all non-GUI-environment-dependent tests pass; any existing display-dependent skip behavior remains unchanged.

- [ ] **Step 8: Commit**

```bash
git add tools/benchmark_engine.py tools/clean_bank.py tools/rebalance_bank_choice_order.py tools/validate_bank.py tests/test_security_testing_engine.py
git commit -m "test: decouple v8 regression suite from Security+ content"
```

---

### Task 5: Rebrand launch surfaces

**Files:** create `sc900_test_learning_engine_v8.py`, `sc900_test_learning_engine_v8.pyw`, `run_sc900_v8.bat`, `tests/test_sc900_branding.py`; remove old-named launch/build files if present.

**Interfaces:** both Python launchers call `app.main()`; Windows runner retains interpreter fallback order.

- [ ] **Step 1: Write failing branding tests**

Create `tests/test_sc900_branding.py`:

```python
import unittest
from pathlib import Path

import app_info
import certification_profile as profile

ROOT = Path(__file__).resolve().parents[1]


class SC900BrandingTests(unittest.TestCase):
    def test_app_identity(self):
        self.assertEqual("SC-900 Test Learning Engine", app_info.APP_NAME)
        self.assertEqual("8.0.0", app_info.APP_VERSION)
        self.assertEqual("SC900TestLearningEngine", profile.EXECUTABLE_BASENAME)

    def test_runtime_and_launcher_sources_have_no_old_product_identity(self):
        paths = [
            ROOT / "app.py",
            ROOT / "app_info.py",
            ROOT / "certification_profile.py",
            ROOT / "question_bank.py",
            ROOT / "sc900_test_learning_engine_v8.py",
            ROOT / "sc900_test_learning_engine_v8.pyw",
            ROOT / "run_sc900_v8.bat",
        ]
        forbidden = ("SY0-701", "CompTIA", "Security Testing Engine", "SecurityTestingEngine")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{token!r} leaked into {path.name}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure before launchers exist**

```bash
python -m unittest tests.test_sc900_branding -v
```

Expected: missing-file and/or old-identity failure.

- [ ] **Step 3: Create both Python launchers**

`sc900_test_learning_engine_v8.py` and `sc900_test_learning_engine_v8.pyw` both contain:

```python
from app import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create the exact Windows runner**

`run_sc900_v8.bat`:

```bat
@echo off
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw app.py
  goto :eof
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw app.py
  goto :eof
)
where py >nul 2>nul
if %errorlevel%==0 (
  py app.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python app.py
  goto :eof
)
echo Python was not found. Use Anaconda Prompt, py launcher, or install Python.
pause
```

- [ ] **Step 5: Remove old-named launch/build files if they were copied**

```bash
for f in security_test_app_windows_v8.py security_test_app_windows_v8.pyw run_windows_v8.bat build_windows_v8.bat; do
  if [ -e "$f" ]; then git rm "$f"; fi
done
```

- [ ] **Step 6: Run branding tests**

```bash
python -m unittest tests.test_sc900_branding -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add sc900_test_learning_engine_v8.py sc900_test_learning_engine_v8.pyw run_sc900_v8.bat tests/test_sc900_branding.py
git commit -m "feat: rebrand SC-900 launch surfaces"
```

---

### Task 6: Rebrand release packaging and smoke-test invariants

**Files:** modify `tools/build_release.py`, `tools/smoke_test.py`, `tests/test_release_tools.py`; create `build_sc900_v8.bat`.

**Interfaces:** output is `dist/SC900TestLearningEngine.exe`; clean release is `release/SC900TestLearningEngine/`; manifest identifies `sc900_bank.json` and baseline count `8`.

- [ ] **Step 1: Convert release tests first**

In `tests/test_release_tools.py`, replace product-specific fixture paths/names with `SC900TestLearningEngine`, bank fixture names with `sc900_bank.json`, and expected counts with `8`. Preserve PE-corruption fixtures and hash checks.

In `test_build_release_stages_only_clean_artifacts`, assert:

```python
self.assertEqual(
    ["README - Start Here.txt", "SC900TestLearningEngine.exe", "release_manifest.json"],
    sorted(path.name for path in release_dir.iterdir()),
)
self.assertEqual("SC900TestLearningEngine.exe", manifest["executable_filename"])
self.assertEqual("sc900_bank.json", manifest["question_bank_filename"])
self.assertEqual(8, manifest["expected_bank_count"])
```

- [ ] **Step 2: Run focused release tests and verify failure against legacy packaging**

```bash
python -m unittest tests.test_release_tools -v
```

Expected: identity/count assertions fail before tool conversion.

- [ ] **Step 3: Convert `tools/build_release.py` to profile constants**

Import:

```python
from certification_profile import (
    APP_NAME,
    DEFAULT_BANK_FILENAME,
    EXECUTABLE_BASENAME,
    EXPECTED_BANK_COUNT,
    RELEASE_DIRNAME,
    RUNTIME_NAMESPACE,
)
```

Define:

```python
DIST_EXE = SOURCE_ROOT / "dist" / f"{EXECUTABLE_BASENAME}.exe"
RELEASE_DIR = SOURCE_ROOT / "release" / RELEASE_DIRNAME
RELEASE_EXE = RELEASE_DIR / f"{EXECUTABLE_BASENAME}.exe"
RELEASE_README = RELEASE_DIR / "README - Start Here.txt"
RELEASE_MANIFEST = RELEASE_DIR / "release_manifest.json"
CHECKOUT_EXE = CHECKOUT_ROOT / f"{EXECUTABLE_BASENAME}.exe"
CHECKOUT_README = CHECKOUT_ROOT / "README - Start Here.txt"
SOURCE_README = SOURCE_ROOT / "README - Start Here.txt"
SOURCE_TREE_EXE = SOURCE_ROOT / f"{EXECUTABLE_BASENAME}.exe"
BANK_FILE = SOURCE_ROOT / DEFAULT_BANK_FILENAME
EXPECTED_QUESTION_COUNT = EXPECTED_BANK_COUNT
```

Generated release/checkout/source notes must use these constants and include the Microsoft non-affiliation disclaimer. Preserve PE validation, SHA-256 hashing, manifest metadata, clean-release behavior, and copy semantics.

- [ ] **Step 4: Convert `tools/smoke_test.py` defaults**

Import `DEFAULT_BANK_FILENAME`, `EXECUTABLE_BASENAME`, `EXPECTED_BANK_COUNT`, `RELEASE_DIRNAME`; derive all release/bank paths from them and retain `EXPECTED_QUESTION_COUNT = EXPECTED_BANK_COUNT`. Preserve manifest/hash/PE/bank-validator/release-test checks.

- [ ] **Step 5: Create the exact SC-900 build script**

`build_sc900_v8.bat`:

```bat
@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON_CMD=py
  goto :have_python
)
where python >nul 2>nul
if %errorlevel%==0 (
  set PYTHON_CMD=python
  goto :have_python
)
echo Python was not found.
pause
exit /b 1

:have_python
if "%~1"=="" (
  set BANK_FILE=sc900_bank.json
) else (
  set BANK_FILE=%~1
)

%PYTHON_CMD% tools\validate_bank.py "%BANK_FILE%"
if errorlevel 1 exit /b 1
%PYTHON_CMD% -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
%PYTHON_CMD% -m pip install pyinstaller
if errorlevel 1 exit /b 1
%PYTHON_CMD% -m PyInstaller --onefile --windowed --name SC900TestLearningEngine --add-data "%BANK_FILE%;." app.py
if errorlevel 1 exit /b 1
%PYTHON_CMD% tools\build_release.py
if errorlevel 1 exit /b 1
%PYTHON_CMD% tools\smoke_test.py
if errorlevel 1 exit /b 1

echo Build finished.
echo EXE path: dist\SC900TestLearningEngine.exe
echo Release folder: release\SC900TestLearningEngine
pause
```

- [ ] **Step 6: Run focused tests**

```bash
python -m unittest tests.test_release_tools -v
```

Expected: all pass; actual-release PE test may skip before a Windows build exists.

- [ ] **Step 7: Commit**

```bash
git add tools/build_release.py tools/smoke_test.py tests/test_release_tools.py build_sc900_v8.bat
git commit -m "feat: convert release tooling to SC-900 identity"
```

---

### Task 7: Update quality targets and documentation

**Files:** modify `tools/run_quality_checks.py`; create/replace `README.md`, `README - Start Here.txt`, `CHANGELOG.md`.

**Interfaces:** quality checks no longer reference excluded importers; documentation accurately identifies the placeholder-bank state and source/content boundary.

- [ ] **Step 1: Fix quality targets**

Remove `tools/import_chapter_screenshots.py` from `QUALITY_TARGETS`. Add `certification_profile.py`. Add `tools/benchmark_engine.py`, `tools/clean_bank.py`, `tools/rebalance_bank_choice_order.py`, and `tools/validate_bank.py` if any are absent after transplant. Retain the existing maintained-core targets.

- [ ] **Step 2: Write `README.md`**

It must identify:

```text
SC-900 Test Learning Engine
Engine baseline: v8.0.0
Target: Microsoft SC-900 — Security, Compliance, and Identity Fundamentals
Current bank: sc900_bank.json
Current bank size: 8 original placeholder questions
Preserved modes: Smart Practice, Practice, Exam
Large SC-900 content bank: not yet imported
Future source flow: staging -> normalization -> validation -> deduplication -> review -> approved bank
Unofficial study application. Not affiliated with or endorsed by Microsoft.
```

Include these commands exactly:

```bash
python app.py
python -m unittest discover -s tests -v
python tools/validate_bank.py sc900_bank.json
python tools/run_quality_checks.py
```

And Windows commands `run_sc900_v8.bat` and `build_sc900_v8.bat`.

- [ ] **Step 3: Write `README - Start Here.txt`**

```text
SC-900 Test Learning Engine v8

Run from source:
- Double-click run_sc900_v8.bat
- Or run: python app.py

Packaged release executable:
- SC900TestLearningEngine.exe

Progress for the packaged app is stored under:
%LOCALAPPDATA%\SC900TestLearningEngine

Unofficial study application. Not affiliated with or endorsed by Microsoft.
```

- [ ] **Step 4: Write `CHANGELOG.md`**

```markdown
# Changelog

## 8.0.0-sc900-baseline — 2026-09-10

- Transplanted the proven v8 learning engine from the frozen SY0-701 source revision.
- Separated reusable engine identity from SC-900 certification identity.
- Rebranded runtime, launch, build, release, and storage surfaces for SC-900.
- Replaced Security+ content with an eight-question original SC-900 placeholder bank.
- Preserved Smart Practice, Practice, Exam, analytics, persistence, validation, and quality behavior for baseline verification.
- Established a separate staged content-ingestion boundary for later SC-900 source material.
```

- [ ] **Step 5: Run old-product runtime/build audit**

```bash
git grep -nEi 'CompTIA|SY0-701|Security Testing Engine|SecurityTestingEngine|public_sy0701' -- '*.py' '*.pyw' '*.bat' ':!tests/**' && exit 1 || true
```

Expected: no output.

- [ ] **Step 6: Run branding/profile tests**

```bash
python -m unittest tests.test_sc900_branding tests.test_certification_profile -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add tools/run_quality_checks.py README.md "README - Start Here.txt" CHANGELOG.md
git commit -m "docs: establish SC-900 baseline identity and workflow"
```

---

### Task 8: Run the complete source-level regression and quality gate

**Files:** modify only an already-scoped migration file if a failing test demonstrates a conversion defect. Do not modify Smart Practice/analytics algorithms merely to obtain a green migration run.

**Interfaces:** produces a source-level passing baseline before Windows packaging.

- [ ] **Step 1: Validate the SC-900 bank**

```bash
python tools/validate_bank.py sc900_bank.json
```

Expected: question count `8`, no blocking validation issues.

- [ ] **Step 2: Run all unit/regression tests**

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass except established environment-dependent GUI/actual-EXE skips.

- [ ] **Step 3: Run Smart Practice core regressions separately**

```bash
python -m unittest tests.test_smart_practice_core tests.test_smart_practice_worker -v
```

Expected: all pass with no policy changes.

- [ ] **Step 4: Run the small-bank benchmark using the converted default**

```bash
python tools/benchmark_engine.py --bank sc900_bank.json --count 8 --repeat 3 --assert-pool-max 4 --assert-analytics-max 3
```

Expected: benchmark completes and records `question_count: 8` and `pool_size` no greater than `8`. This is a functional baseline only; meaningful large-bank performance comparison waits for validated SC-900 ingestion.

- [ ] **Step 5: Run quality checks**

```bash
python tools/run_quality_checks.py
```

Expected: Ruff, Black check, and mypy all pass.

- [ ] **Step 6: Run the final runtime/build string audit**

```bash
git grep -nEi 'CompTIA|SY0-701|Security Testing Engine|SecurityTestingEngine|public_sy0701' -- '*.py' '*.pyw' '*.bat' ':!tests/**' && exit 1 || true
```

Expected: no output.

- [ ] **Step 7: Inspect working-tree repairs**

```bash
git status --short
```

If output is empty, make no repair commit. If files are listed, review each diff and commit only proven migration corrections with:

```bash
git diff --check
git add -u
git commit -m "fix: close SC-900 baseline migration regressions"
```

Expected: `git diff --check` reports no whitespace errors.

---

### Task 9: Build/verify Windows release and freeze the baseline

**Files:** generated `dist/SC900TestLearningEngine.exe`, `release/SC900TestLearningEngine/SC900TestLearningEngine.exe`, `release/SC900TestLearningEngine/release_manifest.json`, `release/SC900TestLearningEngine/README - Start Here.txt`; create `docs/SC900_V8_BASELINE.md` only after observed verification.

**Interfaces:** produces the verified SC-900 v8 release and freeze point.

- [ ] **Step 1: Build on Windows**

```bat
build_sc900_v8.bat
```

Expected: validation, full tests, PyInstaller, release packaging, and smoke test all succeed.

- [ ] **Step 2: Verify manifest identity**

Run:

```python
import json
from pathlib import Path
m = json.loads(Path("release/SC900TestLearningEngine/release_manifest.json").read_text(encoding="utf-8"))
assert m["application_version"] == "8.0.0"
assert m["executable_filename"] == "SC900TestLearningEngine.exe"
assert m["expected_bank_count"] == 8
assert m["question_bank_filename"] == "sc900_bank.json"
assert len(m["executable_sha256"]) == 64
assert len(m["question_bank_sha256"]) == 64
print(m["executable_sha256"])
```

Expected: assertions pass and the executable SHA-256 prints.

- [ ] **Step 3: Re-run smoke test against built release**

```bat
python tools\smoke_test.py
```

Expected: `Smoke test passed.` and question count `8`.

- [ ] **Step 4: Generate the baseline evidence document from observed state**

Run this Python script from repository root after Step 3:

```python
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path("release/SC900TestLearningEngine/release_manifest.json").read_text(encoding="utf-8"))
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
text = f"""# SC-900 v8 Baseline

- Source v8 revision: `5c099196525f2df236d4c80069e2b3a00a70bf94`
- Destination verified revision: `{head}`
- Engine version: `8.0.0`
- Bank: `sc900_bank.json`
- Verified bank count: `{manifest['expected_bank_count']}`
- Executable: `{manifest['executable_filename']}`
- Executable SHA-256: `{manifest['executable_sha256']}`
- Question-bank SHA-256: `{manifest['question_bank_sha256']}`

## Verification

- `python tools/validate_bank.py sc900_bank.json` — PASS
- `python -m unittest discover -s tests -v` — PASS at the release-build gate
- `python tools/run_quality_checks.py` — PASS before release build
- `build_sc900_v8.bat` — PASS
- `python tools\\smoke_test.py` — PASS

SC-900 v8 baseline is frozen before large-bank ingestion or Smart Practice algorithm changes. The next development stage may improve the engine in the SC-900 repository, but content ingestion remains a separate validated pipeline.
"""
Path("docs/SC900_V8_BASELINE.md").write_text(text, encoding="utf-8")
```

Do not run this generator if one of the stated PASS conditions was not actually observed.

- [ ] **Step 5: Commit baseline evidence**

```bash
git add docs/SC900_V8_BASELINE.md
git commit -m "docs: freeze verified SC-900 v8 baseline"
```

- [ ] **Step 6: Tag only the fully verified commit**

```bash
git tag -a sc900-v8-baseline -m "Verified SC-900 Test Learning Engine v8 baseline"
git push origin implementation/sc900-v8-baseline
git push origin sc900-v8-baseline
```

If the Windows build/smoke gate has not been observed, do not create or push this tag.

## Final Acceptance Check

Before merge, confirm all of the following: SC-900 identity is centralized; packaged runtime uses `SC900TestLearningEngine`; excluded Security+ banks/importers are absent; `sc900_bank.json` contains only the eight original baseline questions; generic bank tools default to the SC-900 bank; source-specific regression fixtures are removed or converted; Smart Practice/Practice/Exam retain v8 behavior; validation/progress/analytics/autosave/session restore/quarantine/shuffling remain covered; build/release output uses `SC900TestLearningEngine`; runtime/build code has no accidental CompTIA/SY0-701 identity; disclaimer is present; source-level tests and quality gates pass; Windows build/smoke evidence exists before tagging; and large source ingestion has not been mixed into the baseline migration.
