# SC-900 v8 Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transplant the proven Security Testing Engine v8 codebase into the SC-900 repository, isolate certification-specific identity/content, and produce a fully rebranded SC-900 Test Learning Engine baseline without changing Smart Practice behavior.

**Architecture:** Copy the reusable v8 engine from the frozen SY0-701 source revision, exclude Security+ question/source artifacts, centralize SC-900 identity in one profile module, add a small original SC-900 placeholder bank, and adapt runtime/build/test surfaces around that profile. Content ingestion from a public/permitted book is a later stage and must enter through staging/validation rather than directly into the production bank.

**Tech Stack:** Python 3.11, Tkinter, unittest, PyInstaller, JSON question banks, Ruff, Black, mypy, Windows batch launch/build tooling.

**Spec:** `docs/superpowers/specs/2026-09-10-sc900-v8-baseline-design.md`

## Global Constraints

- Source repository: `IXI-2773/Comptia-SY0-701-Test-Learning-Engine`.
- Frozen source revision: `5c099196525f2df236d4c80069e2b3a00a70bf94`.
- Destination repository: `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`.
- Application brand: `SC-900 Test Learning Engine`.
- Reusable engine version remains `8.0.0` during the baseline conversion.
- Certification vendor: `Microsoft`.
- Certification exam code: `SC-900`.
- Certification name: `Security, Compliance, and Identity Fundamentals`.
- Default bank filename: `sc900_bank.json`.
- Runtime namespace: `SC900TestLearningEngine`.
- Windows executable basename: `SC900TestLearningEngine`.
- Do not ship any SY0-701, screenshot-derived, or Security+ study-guide question bank as SC-900 content.
- Do not redesign Smart Practice, learner modeling, analytics, progress semantics, confidence controls, answer shuffling, autosave/session migration, backup/checkpoint behavior, or issue quarantine during this migration.
- External/public/permitted SC-900 source material is not part of this plan; the production bank must not be populated from such material until a separate staged import/validation task.
- Learner-facing runtime/build surfaces must not identify the application as CompTIA, Security+, SY0-701, Security Testing Engine, or SecurityTestingEngine after conversion.
- Repository provenance documentation may name the SY0-701 source repository and frozen source revision.
- Include this disclaimer in learner-facing documentation: `Unofficial study application. Not affiliated with or endorsed by Microsoft.`

## File Structure

### Copy unchanged from the frozen v8 source revision

Root engine modules:

`analytics_models.py`, `analytics_recommendations.py`, `analytics_summary.py`, `app_analytics_mixin.py`, `app_constants.py`, `app_game_mixin.py`, `app_question_flow_mixin.py`, `app_question_render_mixin.py`, `app_session_builder_mixin.py`, `app_session_persistence_mixin.py`, `application_bootstrap.py`, `bank_models.py`, `config_store.py`, `legacy_source_layout.py`, `pe_validation.py`, `progress_models.py`, `progress_store.py`, `question_widgets.py`, `render_cache.py`, `runtime_persistence.py`, `save_queue.py`, `session_models.py`, `session_store.py`, `smart_practice_cache.py`, `smart_practice_concept_graph.py`, `smart_practice_core.py`, `smart_practice_measurement.py`, `smart_practice_policy.py`, `smart_practice_profile.py`, `smart_practice_question_value.py`, `smart_practice_worker.py`, `source_trust.py`, `storage_utils.py`, `study_question_utils.py`, `ui_theme.py`, `ui_typography.py`, `widget_models.py`.

Repository/tooling files:

`.gitattributes`, `.gitignore`, `LICENSE`, `requirements-dev.txt`, `run_quality_checks.bat`, `tools/benchmark_engine.py`, `tools/clean_bank.py`, `tools/cleanup_runtime_files.py`, `tools/rebalance_bank_choice_order.py`, `tools/validate_bank.py`.

Tests to transplant and adapt as needed:

`tests/test_analytics_calculation.py`, `tests/test_application_bootstrap.py`, `tests/test_release_tools.py`, `tests/test_security_testing_engine.py`, `tests/test_smart_practice_core.py`, `tests/test_smart_practice_worker.py`, `tests/test_study_question_utils.py`.

### Copy then modify

`app.py`, `app_info.py`, `question_bank.py`, `pyproject.toml`, `tools/build_release.py`, `tools/run_quality_checks.py`, `tools/smoke_test.py`.

### Create

`certification_profile.py`, `sc900_bank.json`, `sc900_test_learning_engine_v8.py`, `sc900_test_learning_engine_v8.pyw`, `run_sc900_v8.bat`, `build_sc900_v8.bat`, `tests/test_certification_profile.py`, `tests/test_sc900_bank.py`, `tests/test_sc900_branding.py`, `docs/provenance/source-v8-baseline.md`, `README.md`, `README - Start Here.txt`, `CHANGELOG.md`.

### Do not transplant

All `public_sy0701_*.json` files, all `chapter*_screenshot_*.json` files, `chapter_screenshot_ocr_draft_bank.json`, `chapter_screenshot_review_stubs_import_bank.json`, `free_study_guide_a5_assessments_bank.json`, `free_study_guide_a5_import_bank.json`, `docs/public_sy0701_audit_v4.md`, `tools/import_chapter_screenshots.py`, and `tools/import_free_study_guide.py`.

---

### Task 1: Transplant the frozen v8 engine without Security+ content

**Files:**
- Create/copy the reusable files listed under `File Structure`.
- Create: `docs/provenance/source-v8-baseline.md`.
- Preserve: `docs/superpowers/specs/2026-09-10-sc900-v8-baseline-design.md`.

**Interfaces:**
- Consumes: source repository revision `5c099196525f2df236d4c80069e2b3a00a70bf94`.
- Produces: a destination source tree with the v8 engine present and no Security+ question banks.

- [ ] **Step 1: Check out the exact source revision and destination branch**

```bash
git -C ../Comptia-SY0-701-Test-Learning-Engine fetch origin
git -C ../Comptia-SY0-701-Test-Learning-Engine checkout 5c099196525f2df236d4c80069e2b3a00a70bf94
git checkout implementation/sc900-v8-baseline
```

Expected: source `HEAD` prints `5c099196525f2df236d4c80069e2b3a00a70bf94`; destination is on `implementation/sc900-v8-baseline`.

- [ ] **Step 2: Copy only the approved reusable source/test/tool files**

Use the exact allow-list from `File Structure`; do not use a whole-repository copy. After copying, the following command must return no paths:

```bash
git ls-files | grep -E '(^|/)(public_sy0701_.*\.json|chapter.*screenshot.*\.json|free_study_guide_a5_.*\.json|public_sy0701_audit_v4\.md|import_chapter_screenshots\.py|import_free_study_guide\.py)$'
```

Expected: no output.

- [ ] **Step 3: Record source provenance**

Create `docs/provenance/source-v8-baseline.md` with exactly this factual core:

```markdown
# v8 Source Baseline

The SC-900 Test Learning Engine baseline was derived from:

- Repository: `IXI-2773/Comptia-SY0-701-Test-Learning-Engine`
- Source commit: `5c099196525f2df236d4c80069e2b3a00a70bf94`
- Source application version: `8.0.0`

The SC-900 repository intentionally excludes the source repository's SY0-701 question banks and source-specific import artifacts. Certification content is maintained separately from reusable engine logic.
```

- [ ] **Step 4: Verify the copied Python tree is syntactically valid before rebranding**

```bash
python -m compileall -q .
```

Expected: exit code `0`.

- [ ] **Step 5: Commit the frozen-engine transplant**

```bash
git add .
git commit -m "chore: transplant frozen v8 engine baseline"
```

---

### Task 2: Centralize SC-900 application identity and isolate runtime storage

**Files:**
- Create: `certification_profile.py`.
- Create: `tests/test_certification_profile.py`.
- Modify: `app_info.py`.
- Modify: `app.py`.
- Modify: `pyproject.toml`.

**Interfaces:**
- Produces constants `ENGINE_NAME`, `ENGINE_VERSION`, `APP_NAME`, `CERT_VENDOR`, `CERT_EXAM_CODE`, `CERT_NAME`, `DEFAULT_BANK_FILENAME`, `DEFAULT_SOURCE_NAME`, `RUNTIME_NAMESPACE`, `EXECUTABLE_BASENAME`, `RELEASE_DIRNAME`, `LOG_FILENAME`, `EXPECTED_BANK_COUNT`.
- `app_info.APP_NAME` and `app_info.APP_VERSION` remain compatibility exports for existing engine modules.

- [ ] **Step 1: Write the failing profile tests**

Create `tests/test_certification_profile.py`:

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import certification_profile as profile
import app


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

    def test_sc900_build_does_not_import_security_plus_runtime(self):
        with mock.patch.object(app.sys, "frozen", True, create=True):
            self.assertEqual([], app.packaged_legacy_user_data_dirs())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the profile tests and verify they fail**

```bash
python -m unittest tests.test_certification_profile -v
```

Expected: failure because `certification_profile.py` does not yet exist and/or `app.py` still uses the old runtime namespace.

- [ ] **Step 3: Create the central profile**

Create `certification_profile.py`:

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

Replace its contents with:

```python
from certification_profile import APP_NAME, ENGINE_VERSION

APP_VERSION = ENGINE_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
```

- [ ] **Step 5: Replace certification/runtime hard-coding in `app.py`**

Add imports:

```python
from certification_profile import DEFAULT_BANK_FILENAME, LOG_FILENAME, RUNTIME_NAMESPACE
```

Change packaged runtime resolution to:

```python
def resolve_user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / RUNTIME_NAMESPACE
    return APP_DIR / "user_data"
```

For this first SC-900 release, prevent import of unrelated historical Security+ packaged data:

```python
def packaged_legacy_user_data_dirs() -> list[Path]:
    return []
```

Replace the three SY0-701 default-bank constants with one SC-900 bank resolution:

```python
DEFAULT_BANK = first_existing_path(
    APP_DIR / DEFAULT_BANK_FILENAME,
    RESOURCE_DIR / DEFAULT_BANK_FILENAME,
)
LOG_PATH = USER_DATA_DIR / "logs" / LOG_FILENAME
```

Remove `DEFAULT_BANK_CLEAN`, `DEFAULT_BANK_MERGED`, and `DEFAULT_BANK_LEGACY` from the SC-900 application.

- [ ] **Step 6: Register the new profile as first-party code**

Add `"certification_profile"` to `[tool.ruff.lint.isort].known-first-party` and `certification_profile.py` to the mypy `files` list in `pyproject.toml`.

- [ ] **Step 7: Run the profile/bootstrap tests**

```bash
python -m unittest tests.test_certification_profile tests.test_application_bootstrap -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit identity/runtime isolation**

```bash
git add certification_profile.py app_info.py app.py pyproject.toml tests/test_certification_profile.py
git commit -m "feat: centralize SC-900 application identity"
```

---

### Task 3: Add the original placeholder SC-900 bank and generic source fallback

**Files:**
- Create: `sc900_bank.json`.
- Create: `tests/test_sc900_bank.py`.
- Modify: `question_bank.py`.

**Interfaces:**
- `load_bank(Path("sc900_bank.json"))` returns eight valid `BankQuestion` records.
- Missing `source_name` falls back to `certification_profile.DEFAULT_SOURCE_NAME`, never a SY0-701 label.

- [ ] **Step 1: Write the failing bank tests**

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

- [ ] **Step 2: Run the bank tests and verify they fail**

```bash
python -m unittest tests.test_sc900_bank -v
```

Expected: failure because `sc900_bank.json` is absent and the old source fallback still references SY0-701 behavior.

- [ ] **Step 3: Make source-name inference certification-neutral**

In `question_bank.py`, import `DEFAULT_SOURCE_NAME` and replace `infer_source_name` with:

```python
def infer_source_name(question: BankQuestion, default_title: str = "Practice Test") -> str:
    source_name = sanitize_text(question.get("source_name", ""))
    if source_name:
        return source_name
    return DEFAULT_SOURCE_NAME
```

Keep the remainder of bank sanitization, validation, duplicate metadata, and answer-order logic unchanged.

- [ ] **Step 4: Create the eight-question original placeholder bank**

Create `sc900_bank.json` as valid UTF-8 JSON with title `SC-900 Baseline Placeholder Bank` and exactly eight original records: two records in each of the four current top-level SC-900 skill areas. Use these prompts and correct concepts so the placeholder bank is independently authored rather than copied from an exam or commercial question source:

```text
1. Which Zero Trust principle requires each access request to be evaluated using available identity, device, location, and risk signals? -> Verify explicitly.
2. In the shared responsibility model, which responsibility remains with the customer when using a cloud service? -> Protecting and governing the customer's data and identities according to the service model.
3. Which Microsoft service provides cloud identity and access management for users, groups, applications, and authentication? -> Microsoft Entra ID.
4. What is the main security benefit of multifactor authentication? -> It requires evidence from more than one authentication factor, reducing reliance on a password alone.
5. Which Microsoft service provides cloud security posture management and workload protection recommendations across cloud resources? -> Microsoft Defender for Cloud.
6. Which Microsoft service is a cloud-native SIEM and security orchestration platform used to collect, correlate, investigate, and respond to security data? -> Microsoft Sentinel.
7. Which Microsoft Purview capability helps detect and prevent inappropriate sharing of sensitive information? -> Data Loss Prevention.
8. Which Microsoft Purview solution helps organizations assess and track improvement actions against compliance requirements? -> Compliance Manager.
```

For every record use four choices `A` through `D`, one correct answer, a short original explanation, an empty `choice_explanations` object, `question_type: "single"`, `flagged_issues: []`, `duplicate_of: null`, `source_name: "Original SC-900 Practice Questions"`, and `source_page: ""`. Assign domain/objective metadata as follows: questions 1-2 domain `Security, compliance, and identity concepts` objective `1`; questions 3-4 domain `Microsoft Entra` objective `2`; questions 5-6 domain `Microsoft security solutions` objective `3`; questions 7-8 domain `Microsoft compliance solutions` objective `4`.

- [ ] **Step 5: Validate the placeholder bank**

```bash
python tools/validate_bank.py sc900_bank.json
python -m unittest tests.test_sc900_bank -v
```

Expected: validator exit code `0`; two bank tests pass.

- [ ] **Step 6: Commit the SC-900 placeholder content boundary**

```bash
git add sc900_bank.json question_bank.py tests/test_sc900_bank.py
git commit -m "feat: add validated SC-900 placeholder bank"
```

---

### Task 4: Rebrand learner-facing launch surfaces without changing engine behavior

**Files:**
- Create: `sc900_test_learning_engine_v8.py`.
- Create: `sc900_test_learning_engine_v8.pyw`.
- Create: `run_sc900_v8.bat`.
- Create: `tests/test_sc900_branding.py`.
- Remove from destination if copied: `security_test_app_windows_v8.py`, `security_test_app_windows_v8.pyw`, `run_windows_v8.bat`, `build_windows_v8.bat`.

**Interfaces:**
- Both Python launchers call `app.main()`.
- `run_sc900_v8.bat` launches `app.py` with `pyw`, `pythonw`, `py`, or `python` in that order.

- [ ] **Step 1: Write a failing branding-surface test**

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

- [ ] **Step 2: Run branding tests and verify they fail until launch files exist**

```bash
python -m unittest tests.test_sc900_branding -v
```

Expected: failure for missing SC-900 launch surfaces or old identity remnants.

- [ ] **Step 3: Create the Python launchers**

Both `sc900_test_learning_engine_v8.py` and `sc900_test_learning_engine_v8.pyw` contain:

```python
from app import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create the renamed Windows runner**

Create `run_sc900_v8.bat` with the same interpreter fallback behavior as the source `run_windows_v8.bat`, but with SC-900 naming in any displayed text. It must execute `app.py`; it must not invoke a Security+ launcher.

- [ ] **Step 5: Remove old-named copied launch/build files**

```bash
git rm -f security_test_app_windows_v8.py security_test_app_windows_v8.pyw run_windows_v8.bat build_windows_v8.bat 2>/dev/null || true
```

- [ ] **Step 6: Run branding tests**

```bash
python -m unittest tests.test_sc900_branding -v
```

Expected: all branding tests pass.

- [ ] **Step 7: Commit launcher rebranding**

```bash
git add sc900_test_learning_engine_v8.py sc900_test_learning_engine_v8.pyw run_sc900_v8.bat tests/test_sc900_branding.py
git commit -m "feat: rebrand SC-900 launch surfaces"
```

---

### Task 5: Rebrand release packaging and smoke-test invariants

**Files:**
- Modify: `tools/build_release.py`.
- Modify: `tools/smoke_test.py`.
- Modify: `tests/test_release_tools.py`.
- Create: `build_sc900_v8.bat`.

**Interfaces:**
- Build output: `dist/SC900TestLearningEngine.exe`.
- Clean release directory: `release/SC900TestLearningEngine/`.
- Release executable: `release/SC900TestLearningEngine/SC900TestLearningEngine.exe`.
- Manifest bank: `sc900_bank.json` with expected baseline count `8`.

- [ ] **Step 1: Adapt release tests first**

In `tests/test_release_tools.py`, change all product-specific fixtures from `SecurityTestingEngine` to `SC900TestLearningEngine`, all bank fixtures from `public_sy0701_bank_v4_plus_studyguide_clean.json` to `sc900_bank.json`, and all expected bank counts from `1231` to `8`. Preserve PE validation and malformed-manifest tests unchanged in behavior.

Add these assertions to `test_build_release_stages_only_clean_artifacts`:

```python
self.assertEqual(
    ["README - Start Here.txt", "SC900TestLearningEngine.exe", "release_manifest.json"],
    sorted(path.name for path in release_dir.iterdir()),
)
self.assertEqual("SC900TestLearningEngine.exe", manifest["executable_filename"])
self.assertEqual("sc900_bank.json", manifest["question_bank_filename"])
self.assertEqual(8, manifest["expected_bank_count"])
```

- [ ] **Step 2: Run focused release tests and verify failure against old packaging**

```bash
python -m unittest tests.test_release_tools -v
```

Expected: product/bank identity assertions fail until release and smoke modules are converted.

- [ ] **Step 3: Centralize release constants in `tools/build_release.py`**

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

Resolve paths with those constants:

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
```

Keep `EXPECTED_QUESTION_COUNT = EXPECTED_BANK_COUNT` as a compatibility name inside the release module so existing call sites remain stable.

Rewrite generated launch-note strings to use `APP_NAME`, `EXECUTABLE_BASENAME`, `RELEASE_DIRNAME`, and `RUNTIME_NAMESPACE`. The generated note must include `Unofficial study application. Not affiliated with or endorsed by Microsoft.`

- [ ] **Step 4: Convert `tools/smoke_test.py` to the centralized SC-900 profile**

Import `DEFAULT_BANK_FILENAME`, `EXECUTABLE_BASENAME`, `EXPECTED_BANK_COUNT`, and `RELEASE_DIRNAME`; define release/bank paths from those constants and set `EXPECTED_QUESTION_COUNT = EXPECTED_BANK_COUNT`. Preserve hash, PE, validator, report, and focused-release-test checks.

- [ ] **Step 5: Create the SC-900 Windows build script**

Create `build_sc900_v8.bat` by preserving the source script's Python detection, bank validation, unit-test, PyInstaller, release-package, and smoke-test sequence, with these exact substitutions:

```text
BANK_FILE=sc900_bank.json
--name SC900TestLearningEngine
EXE path: dist\SC900TestLearningEngine.exe
Release folder: release\SC900TestLearningEngine
```

The PyInstaller data argument remains `--add-data "%BANK_FILE%;."`.

- [ ] **Step 6: Run focused packaging tests**

```bash
python -m unittest tests.test_release_tools -v
```

Expected: all release/smoke unit tests pass; the actual-release executable test may skip when no EXE has been built.

- [ ] **Step 7: Commit release rebranding**

```bash
git add tools/build_release.py tools/smoke_test.py tests/test_release_tools.py build_sc900_v8.bat
git commit -m "feat: convert release tooling to SC-900 identity"
```

---

### Task 6: Update quality targets and learner-facing documentation

**Files:**
- Modify: `tools/run_quality_checks.py`.
- Create/replace: `README.md`.
- Create/replace: `README - Start Here.txt`.
- Create/replace: `CHANGELOG.md`.

**Interfaces:**
- Quality checks cover the maintained core plus `certification_profile.py` and no longer reference excluded Security+-specific importers.
- README identifies the project as unofficial and explains the placeholder-bank state.

- [ ] **Step 1: Update quality targets**

In `tools/run_quality_checks.py`, remove `tools/import_chapter_screenshots.py` from `QUALITY_TARGETS`, add `certification_profile.py`, and retain the remaining engine/core quality targets.

- [ ] **Step 2: Write the SC-900 README**

`README.md` must state all of the following explicitly:

```text
SC-900 Test Learning Engine
Engine baseline: v8.0.0
Target certification: Microsoft SC-900 — Security, Compliance, and Identity Fundamentals
Current included bank: sc900_bank.json
Current baseline bank size: 8 original placeholder questions
Smart Practice / Practice / Exam are preserved from the v8 learning engine
The large SC-900 content bank has not yet been imported
External/public/permitted sources will be staged, normalized, validated, deduplicated, and reviewed before admission
Unofficial study application. Not affiliated with or endorsed by Microsoft.
```

Include run commands `python app.py` and `run_sc900_v8.bat`, test command `python -m unittest discover -s tests -v`, validator command `python tools/validate_bank.py sc900_bank.json`, quality command `python tools/run_quality_checks.py`, and build command `build_sc900_v8.bat`.

- [ ] **Step 3: Write `README - Start Here.txt`**

Use this content:

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

- [ ] **Step 4: Start the SC-900 changelog**

`CHANGELOG.md` begins with:

```markdown
# Changelog

## 8.0.0-sc900-baseline — 2026-09-10

- Transplanted the proven v8 learning engine from the frozen SY0-701 source revision.
- Separated engine identity from SC-900 certification identity.
- Rebranded runtime, launch, build, release, and storage surfaces for SC-900.
- Replaced Security+ content with an eight-question original SC-900 placeholder bank.
- Preserved Smart Practice, Practice, Exam, analytics, persistence, validation, and quality behavior for baseline verification.
- Established a separate staged content-ingestion boundary for later SC-900 source material.
```

- [ ] **Step 5: Run the runtime/build branding audit**

```bash
git grep -nEi 'CompTIA|SY0-701|Security Testing Engine|SecurityTestingEngine' -- '*.py' '*.pyw' '*.bat' ':!tests/**' || true
```

Expected: no output. Provenance/spec/plan Markdown is intentionally outside this runtime/build audit.

- [ ] **Step 6: Run branding and profile tests**

```bash
python -m unittest tests.test_sc900_branding tests.test_certification_profile -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit documentation and quality conversion**

```bash
git add tools/run_quality_checks.py README.md "README - Start Here.txt" CHANGELOG.md
git commit -m "docs: establish SC-900 baseline identity and workflow"
```

---

### Task 7: Run the full regression/quality gate and repair migration-only failures

**Files:**
- Modify only files already in the migration scope when a failing test proves a conversion defect.
- Do not change Smart Practice policy or analytics algorithms to make migration tests pass.

**Interfaces:**
- Produces a source-level passing baseline before Windows packaging.

- [ ] **Step 1: Validate the bank**

```bash
python tools/validate_bank.py sc900_bank.json
```

Expected: exit code `0`, question count `8`, no blocking issues.

- [ ] **Step 2: Run the complete unittest suite**

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass except tests explicitly designed to skip when a built Windows executable is absent.

- [ ] **Step 3: Run Smart Practice-focused regression tests separately**

```bash
python -m unittest tests.test_smart_practice_core tests.test_smart_practice_worker -v
```

Expected: all tests pass without changes to selection policy.

- [ ] **Step 4: Run the placeholder-bank benchmark guard**

```bash
python tools/benchmark_engine.py --count 8 --repeat 3 --assert-pool-max 4 --assert-analytics-max 3
```

Expected: benchmark completes within configured regression thresholds. If the benchmark requires a larger pool by design, preserve the benchmark implementation and record that the final large-bank benchmark is deferred until validated SC-900 content exists; do not fabricate extra questions merely to satisfy benchmarking.

- [ ] **Step 5: Run maintained-code quality checks**

```bash
python tools/run_quality_checks.py
```

Expected: Ruff, Black check, and mypy all pass.

- [ ] **Step 6: Re-run the old-product runtime/build string audit**

```bash
git grep -nEi 'CompTIA|SY0-701|Security Testing Engine|SecurityTestingEngine' -- '*.py' '*.pyw' '*.bat' ':!tests/**' || true
```

Expected: no output.

- [ ] **Step 7: Commit only evidence-backed migration repairs if any were required**

```bash
git status --short
git add <only-files-changed-to-fix-proven-migration-failures>
git commit -m "fix: close SC-900 baseline migration regressions"
```

If `git status --short` is empty after the gate, skip the commit.

---

### Task 8: Build and verify the Windows release, then freeze the baseline

**Files:**
- Generated: `dist/SC900TestLearningEngine.exe`.
- Generated: `release/SC900TestLearningEngine/SC900TestLearningEngine.exe`.
- Generated: `release/SC900TestLearningEngine/release_manifest.json`.
- Generated: `release/SC900TestLearningEngine/README - Start Here.txt`.
- Create after success: `docs/SC900_V8_BASELINE.md`.

**Interfaces:**
- Produces the verified SC-900 v8 baseline release and freeze point.

- [ ] **Step 1: Build from a Windows environment**

```bat
build_sc900_v8.bat
```

Expected: bank validation passes, unit tests pass, PyInstaller creates `dist\SC900TestLearningEngine.exe`, release packaging succeeds, and smoke test passes.

- [ ] **Step 2: Inspect the release manifest**

Verify `release/SC900TestLearningEngine/release_manifest.json` reports:

```json
{
  "application_version": "8.0.0",
  "executable_filename": "SC900TestLearningEngine.exe",
  "expected_bank_count": 8,
  "question_bank_filename": "sc900_bank.json"
}
```

The manifest also retains generated hashes, PE metadata, Python/PyInstaller versions, timestamp, and source revision.

- [ ] **Step 3: Run the smoke test once more against the completed release**

```bat
python tools\smoke_test.py
```

Expected: `Smoke test passed.` and question count `8`.

- [ ] **Step 4: Create the baseline status document**

Create `docs/SC900_V8_BASELINE.md` containing the exact source revision, destination commit SHA being frozen, the commands run, pass/skip counts, bank count, executable SHA-256 from the release manifest, and this boundary statement:

```text
SC-900 v8 baseline is frozen before large-bank ingestion or Smart Practice algorithm changes. The next development stage may improve the engine in the SC-900 repository, but content ingestion remains a separate validated pipeline.
```

Use the actual values produced by the completed verification run; do not invent evidence that was not observed.

- [ ] **Step 5: Commit the baseline evidence document**

```bash
git add docs/SC900_V8_BASELINE.md
git commit -m "docs: freeze verified SC-900 v8 baseline"
```

- [ ] **Step 6: Mark the verified commit**

```bash
git tag -a sc900-v8-baseline -m "Verified SC-900 Test Learning Engine v8 baseline"
git push origin implementation/sc900-v8-baseline
git push origin sc900-v8-baseline
```

Do not create the tag until Tasks 1-8 have passed to the extent required by the verification gate; if Windows build evidence is unavailable, leave the baseline explicitly untagged and record the remaining gate rather than claiming completion.

## Final Acceptance Check

Before merging the implementation branch, verify all of the following in one review:

```text
SC-900 Test Learning Engine identity is centralized.
Runtime storage is isolated under SC900TestLearningEngine.
No SY0-701 question bank is shipped.
The only initial SC-900 bank is the eight-question original placeholder bank.
Practice, Smart Practice, and Exam still use the existing v8 engine behavior.
Bank loading/validation, progress, analytics, autosave, session restore, issue quarantine, and answer shuffling remain covered by the transplanted tests.
Release/build tooling produces SC900TestLearningEngine artifacts.
Learner-facing runtime/build files contain no accidental CompTIA/SY0-701/Security Testing Engine identity.
The disclaimer is present.
Source-level unit, validation, and quality gates pass.
Windows build/smoke evidence exists before the baseline tag is created.
Large public/permitted SC-900 source ingestion has not been mixed into this migration.
```
