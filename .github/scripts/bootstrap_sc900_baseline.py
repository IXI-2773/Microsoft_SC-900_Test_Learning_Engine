from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / ".migration-source"
SOURCE_REPO = "https://github.com/IXI-2773/Comptia-SY0-701-Test-Learning-Engine.git"
SOURCE_SHA = "5c099196525f2df236d4c80069e2b3a00a70bf94"
BRANCH = "implementation/sc900-v8-baseline"

ROOT_FILES = [
    ".gitattributes",
    ".gitignore",
    "LICENSE",
    "requirements-dev.txt",
    "run_quality_checks.bat",
    "analytics_models.py",
    "analytics_recommendations.py",
    "analytics_summary.py",
    "app.py",
    "app_analytics_mixin.py",
    "app_constants.py",
    "app_game_mixin.py",
    "app_info.py",
    "app_question_flow_mixin.py",
    "app_question_render_mixin.py",
    "app_session_builder_mixin.py",
    "app_session_persistence_mixin.py",
    "application_bootstrap.py",
    "bank_models.py",
    "config_store.py",
    "legacy_source_layout.py",
    "pe_validation.py",
    "progress_models.py",
    "progress_store.py",
    "pyproject.toml",
    "question_bank.py",
    "question_widgets.py",
    "render_cache.py",
    "runtime_persistence.py",
    "save_queue.py",
    "session_models.py",
    "session_store.py",
    "smart_practice_cache.py",
    "smart_practice_concept_graph.py",
    "smart_practice_core.py",
    "smart_practice_measurement.py",
    "smart_practice_policy.py",
    "smart_practice_profile.py",
    "smart_practice_question_value.py",
    "smart_practice_worker.py",
    "source_trust.py",
    "storage_utils.py",
    "study_question_utils.py",
    "ui_theme.py",
    "ui_typography.py",
    "widget_models.py",
]

TOOL_FILES = [
    "tools/benchmark_engine.py",
    "tools/build_release.py",
    "tools/clean_bank.py",
    "tools/cleanup_runtime_files.py",
    "tools/rebalance_bank_choice_order.py",
    "tools/run_quality_checks.py",
    "tools/smoke_test.py",
    "tools/validate_bank.py",
]

TEST_FILES = [
    "tests/test_analytics_calculation.py",
    "tests/test_application_bootstrap.py",
    "tests/test_release_tools.py",
    "tests/test_security_testing_engine.py",
    "tests/test_smart_practice_core.py",
    "tests/test_smart_practice_worker.py",
    "tests/test_study_question_utils.py",
]

REMOVED_TEST_METHODS = [
    "test_packaged_runtime_auto_migrates_stronger_project_progress",
    "test_release_packager_outputs_single_exe_folder",
    "test_chapter_screenshot_filename_parses_source_question_number",
    "test_chapter_screenshot_metadata_infers_chapter_three_architecture",
    "test_chapter_screenshot_ocr_parser_prefers_first_explanation_match",
    "test_chapter_screenshot_manifest_handles_missing_ocr_without_importing",
    "test_verified_chapter_screenshot_record_maps_to_domain_metadata",
    "test_chapter_screenshot_review_record_is_quarantined",
    "test_verified_chapter_screenshot_duplicate_is_skipped",
    "test_merged_bank_includes_imported_study_guide_assessments",
    "test_load_bank_infers_public_source_name_defaults",
    "test_merged_bank_q1105_uses_port_mirroring_answer_key",
]


def run(*args: str, check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(args, cwd=cwd, text=True)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed


def expect_fail(*args: str) -> None:
    completed = run(*args, check=False)
    if completed.returncode == 0:
        raise RuntimeError(f"Expected RED test to fail but it passed: {' '.join(args)}")
    print("RED confirmed: failure was observed as expected.", flush=True)


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def replace_exact(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if old not in text:
        raise RuntimeError(f"Expected text not found in {rel}: {old[:100]!r}")
    write(rel, text.replace(old, new, 1))


def replace_all(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if old not in text:
        raise RuntimeError(f"Expected text not found in {rel}: {old[:100]!r}")
    write(rel, text.replace(old, new))


def remove_method(text: str, name: str) -> str:
    pattern = re.compile(rf"(?ms)^    def {re.escape(name)}\(.*?(?=^    def |^class |\Z)")
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Test method not found: {name}")
    return text[: match.start()] + text[match.end() :]


def replace_method(text: str, name: str, replacement: str) -> str:
    pattern = re.compile(rf"(?ms)^    def {re.escape(name)}\(.*?(?=^    def |^class |\Z)")
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Test method not found: {name}")
    normalized = replacement.rstrip() + "\n\n"
    return text[: match.start()] + normalized + text[match.end() :]


def commit(message: str) -> None:
    run("git", "add", "-A")
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        print(f"No changes to commit for {message}")
        return
    run("git", "commit", "-m", message)


def clone_source() -> None:
    if SOURCE_DIR.exists():
        shutil.rmtree(SOURCE_DIR)
    run("git", "clone", "--filter=blob:none", "--no-checkout", SOURCE_REPO, str(SOURCE_DIR))
    run("git", "checkout", SOURCE_SHA, cwd=SOURCE_DIR)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE_DIR, text=True).strip()
    if head != SOURCE_SHA:
        raise RuntimeError(f"Wrong source revision: {head}")


def copy_allowlist() -> None:
    for rel in ROOT_FILES + TOOL_FILES + TEST_FILES:
        src = SOURCE_DIR / rel
        if not src.exists():
            raise FileNotFoundError(src)
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    gitignore = read(".gitignore").replace("SecurityTestingEngine.exe", "SC900TestLearningEngine.exe")
    write(".gitignore", gitignore)

    write(
        "docs/provenance/source-v8-baseline.md",
        """# v8 Source Baseline

The SC-900 Test Learning Engine baseline was derived from:

- Repository: `IXI-2773/Comptia-SY0-701-Test-Learning-Engine`
- Source commit: `5c099196525f2df236d4c80069e2b3a00a70bf94`
- Source application version: `8.0.0`

The SC-900 repository intentionally excludes the source repository's SY0-701 question banks and source-specific import artifacts. Certification content is maintained separately from reusable engine logic.
""",
    )


def create_profile_test() -> None:
    write(
        "tests/test_certification_profile.py",
        '''import os
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
''',
    )


def implement_profile() -> None:
    write(
        "certification_profile.py",
        '''ENGINE_NAME = "Test Learning Engine"
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
''',
    )
    write(
        "app_info.py",
        '''from certification_profile import APP_NAME, ENGINE_VERSION

APP_VERSION = ENGINE_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
''',
    )

    app = read("app.py")
    app = app.replace(
        "from config_store import DEFAULT_CONFIG, load_config, save_config\n",
        "from config_store import DEFAULT_CONFIG, load_config, save_config\n"
        "from certification_profile import DEFAULT_BANK_FILENAME, LOG_FILENAME, RUNTIME_NAMESPACE\n",
        1,
    )
    app = app.replace('return base / "SecurityTestingEngine"', "return base / RUNTIME_NAMESPACE", 1)
    legacy_pattern = re.compile(
        r"(?ms)^def packaged_legacy_user_data_dirs\(\) -> list\[Path\]:.*?(?=^def auto_migrate_packaged_runtime_data)"
    )
    app, count = legacy_pattern.subn("def packaged_legacy_user_data_dirs() -> list[Path]:\n    return []\n\n\n", app, count=1)
    if count != 1:
        raise RuntimeError("Could not replace packaged_legacy_user_data_dirs")
    bank_pattern = re.compile(
        r"(?ms)^DEFAULT_BANK_CLEAN = first_existing_path\(.*?^LOG_PATH = .*?$"
    )
    bank_replacement = '''DEFAULT_BANK = first_existing_path(
    APP_DIR / DEFAULT_BANK_FILENAME,
    RESOURCE_DIR / DEFAULT_BANK_FILENAME,
)
LOG_PATH = USER_DATA_DIR / "logs" / LOG_FILENAME'''
    app, count = bank_pattern.subn(bank_replacement, app, count=1)
    if count != 1:
        raise RuntimeError("Could not replace default-bank block")
    write("app.py", app)

    pyproject = read("pyproject.toml")
    pyproject = pyproject.replace('  "config_store",\n', '  "config_store",\n  "certification_profile",\n', 1)
    pyproject = pyproject.replace('  "bank_models.py",\n', '  "bank_models.py",\n  "certification_profile.py",\n', 1)
    write("pyproject.toml", pyproject)


def create_bank_test() -> None:
    write(
        "tests/test_sc900_bank.py",
        '''import unittest
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
''',
    )


def placeholder_questions() -> list[dict]:
    source = "Original SC-900 Practice Questions"
    rows = [
        (1, "Which Zero Trust principle requires each access request to be evaluated using available identity, device, location, and risk signals?", {"A": "Verify explicitly", "B": "Trust the internal network by default", "C": "Disable identity signals", "D": "Grant permanent access after the first sign-in"}, "A", "Verify explicitly means authentication and authorization decisions should use relevant signals instead of assuming trust from network location or a previous sign-in.", "Security, compliance, and identity concepts", "Zero Trust", ["Zero Trust"], "1", "Recognize the core Zero Trust principles."),
        (2, "In the shared responsibility model, which responsibility remains with the customer when using a cloud service?", {"A": "Operating the provider's physical datacenter", "B": "Maintaining the provider's cooling system", "C": "Protecting and governing the customer's data and identities according to the service model", "D": "Replacing failed hardware in the provider's server racks"}, "C", "Cloud providers operate provider infrastructure, while customers retain responsibilities for their own data, identities, access, and configuration according to the service model.", "Security, compliance, and identity concepts", "Shared responsibility", ["Shared responsibility"], "1", "Separate provider and customer responsibilities."),
        (3, "Which Microsoft service provides cloud identity and access management for users, groups, applications, and authentication?", {"A": "Microsoft Sentinel", "B": "Microsoft Entra ID", "C": "Microsoft Defender for Cloud", "D": "Microsoft Purview Data Loss Prevention"}, "B", "Microsoft Entra ID is Microsoft's cloud identity and access management service for identities, applications, authentication, and access controls.", "Microsoft Entra", "Identity", ["Microsoft Entra ID"], "2", "Identify the role of Microsoft Entra ID."),
        (4, "What is the main security benefit of multifactor authentication?", {"A": "It automatically grants administrator privileges", "B": "It requires evidence from more than one authentication factor", "C": "It removes the need for authorization", "D": "It encrypts every file stored by the user"}, "B", "Multifactor authentication reduces reliance on a password alone by requiring evidence from multiple authentication-factor categories.", "Microsoft Entra", "Authentication", ["MFA"], "2", "Understand why MFA reduces single-factor risk."),
        (5, "Which Microsoft service provides cloud security posture management and workload protection recommendations across cloud resources?", {"A": "Microsoft Defender for Cloud", "B": "Microsoft Sentinel", "C": "Microsoft Entra ID", "D": "Microsoft Purview Audit"}, "A", "Microsoft Defender for Cloud provides security posture management and workload protection capabilities for cloud resources.", "Microsoft security solutions", "Cloud security", ["Defender for Cloud"], "3", "Distinguish Defender for Cloud from identity, SIEM, and compliance services."),
        (6, "Which Microsoft service is a cloud-native SIEM and security orchestration platform used to collect, correlate, investigate, and respond to security data?", {"A": "Microsoft Compliance Manager", "B": "Microsoft Entra ID", "C": "Microsoft Sentinel", "D": "Microsoft Purview Data Loss Prevention"}, "C", "Microsoft Sentinel provides cloud-native SIEM capabilities along with security orchestration and response workflows.", "Microsoft security solutions", "SIEM and SOAR", ["Microsoft Sentinel"], "3", "Recognize Microsoft Sentinel's SIEM and orchestration role."),
        (7, "Which Microsoft Purview capability helps detect and prevent inappropriate sharing of sensitive information?", {"A": "eDiscovery", "B": "Data Loss Prevention", "C": "Audit", "D": "Compliance Manager"}, "B", "Microsoft Purview Data Loss Prevention uses policies to identify sensitive information and help prevent inappropriate use or sharing.", "Microsoft compliance solutions", "Information protection", ["Data Loss Prevention"], "4", "Distinguish DLP from investigation and assessment capabilities."),
        (8, "Which Microsoft Purview solution helps organizations assess and track improvement actions against compliance requirements?", {"A": "Compliance Manager", "B": "Data Loss Prevention", "C": "eDiscovery", "D": "Insider Risk Management"}, "A", "Compliance Manager helps organizations assess compliance posture and track recommended improvement actions against applicable requirements.", "Microsoft compliance solutions", "Compliance assessment", ["Compliance Manager"], "4", "Recognize Compliance Manager's assessment and improvement-action role."),
    ]
    questions = []
    for qnum, prompt, choices, correct, explanation, domain, subtitle, topics, objective, focus in rows:
        questions.append(
            {
                "question_number": qnum,
                "prompt": prompt,
                "choices": choices,
                "correct": [correct],
                "general_explanation": explanation,
                "choice_explanations": {},
                "domain": domain,
                "chapter": "Baseline placeholders",
                "subtitle": subtitle,
                "question_type": "single",
                "topics": topics,
                "flagged_issues": [],
                "source_page": "",
                "source_name": source,
                "objective_code": objective,
                "study_focus": focus,
                "duplicate_of": None,
            }
        )
    return questions


def implement_bank() -> None:
    write(
        "sc900_bank.json",
        json.dumps({"title": "SC-900 Baseline Placeholder Bank", "questions": placeholder_questions()}, indent=2)
        + "\n",
    )
    bank = read("question_bank.py")
    bank = bank.replace(
        "from bank_models import BankQuestion, QuestionBankData, as_bank_question\n",
        "from bank_models import BankQuestion, QuestionBankData, as_bank_question\n"
        "from certification_profile import DEFAULT_SOURCE_NAME\n",
        1,
    )
    pattern = re.compile(r"(?ms)^def infer_source_name\(.*?(?=^def _repair_mojibake)")
    replacement = '''def infer_source_name(question: BankQuestion, default_title: str = "Practice Test") -> str:
    source_name = sanitize_text(question.get("source_name", ""))
    if source_name:
        return source_name
    return DEFAULT_SOURCE_NAME


'''
    bank, count = pattern.subn(replacement, bank, count=1)
    if count != 1:
        raise RuntimeError("Could not replace infer_source_name")
    write("question_bank.py", bank)


def convert_generic_tools_and_regressions() -> None:
    for rel, old_line, new_import, new_line in [
        ("tools/benchmark_engine.py", 'DEFAULT_BANK = ROOT / "public_sy0701_bank_v4_plus_studyguide_clean.json"', "from certification_profile import DEFAULT_BANK_FILENAME\n", "DEFAULT_BANK = ROOT / DEFAULT_BANK_FILENAME"),
        ("tools/validate_bank.py", "DEFAULT_BANK = BASE_DIR / 'public_sy0701_bank_v4.json'", "from certification_profile import DEFAULT_BANK_FILENAME\n", "DEFAULT_BANK = BASE_DIR / DEFAULT_BANK_FILENAME"),
        ("tools/rebalance_bank_choice_order.py", "DEFAULT_BANK_PATH = ROOT / 'public_sy0701_bank_v4_clean.json'", "from certification_profile import DEFAULT_BANK_FILENAME\n", "DEFAULT_BANK_PATH = ROOT / DEFAULT_BANK_FILENAME"),
    ]:
        text = read(rel)
        insertion = "sys.path.insert(0, str(ROOT))\n"
        if insertion in text and new_import.strip() not in text:
            text = text.replace(insertion, insertion + new_import, 1)
        text = text.replace(old_line, new_line, 1)
        write(rel, text)

    clean = read("tools/clean_bank.py")
    clean = clean.replace(
        "from question_bank import load_bank, sanitize_text\n",
        "from certification_profile import DEFAULT_BANK_FILENAME\nfrom question_bank import load_bank, sanitize_text\n",
        1,
    )
    clean = clean.replace("DEFAULT_SOURCE = ROOT / 'public_sy0701_bank_v4.json'", "DEFAULT_SOURCE = ROOT / DEFAULT_BANK_FILENAME", 1)
    clean = clean.replace("DEFAULT_OUTPUT = ROOT / 'public_sy0701_bank_v4_clean.json'", "DEFAULT_OUTPUT = ROOT / 'sc900_bank_clean.json'", 1)
    write("tools/clean_bank.py", clean)

    tests = read("tests/test_security_testing_engine.py")
    tests = tests.replace("from tools import import_chapter_screenshots\n", "", 1)
    tests = tests.replace("SecurityTestingEngineTests", "SC900TestLearningEngineTests")
    tests = tests.replace("SecurityTestingEngineGuiTests", "SC900TestLearningEngineGuiTests")
    for name in REMOVED_TEST_METHODS:
        tests = remove_method(tests, name)

    tests = replace_method(
        tests,
        "test_frozen_runtime_data_uses_local_app_data",
        '''    def test_frozen_runtime_data_uses_local_app_data(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(app_module.sys, "frozen", True, create=True),
            mock.patch.dict(app_module.os.environ, {"LOCALAPPDATA": tmp}),
        ):
            self.assertEqual(Path(tmp) / "SC900TestLearningEngine", app_module.resolve_user_data_dir())''',
    )
    tests = replace_method(
        tests,
        "test_load_bank_has_expected_question_count",
        '''    def test_load_bank_has_expected_question_count(self):
        data = load_bank(ROOT / "sc900_bank.json")
        self.assertEqual(8, len(data["questions"]))''',
    )
    tests = replace_method(
        tests,
        "test_merged_bank_validator_has_no_warnings",
        '''    def test_merged_bank_validator_has_no_warnings(self):
        result = validate_bank(ROOT / "sc900_bank.json")
        self.assertEqual([], result["issues"])
        self.assertEqual([], result["warnings"])''',
    )
    tests = replace_method(
        tests,
        "test_bank_validation_report_has_no_issues",
        '''    def test_bank_validation_report_has_no_issues(self):
        result = validate_bank(ROOT / "sc900_bank.json")
        self.assertEqual(8, result["question_count"])
        self.assertEqual([], result["issues"])''',
    )
    tests = replace_method(
        tests,
        "test_merged_bank_benchmark_stays_within_regression_guardrails",
        '''    def test_merged_bank_benchmark_stays_within_regression_guardrails(self):
        result = run_benchmark(
            ROOT / "sc900_bank.json",
            smart_count="8",
            pool_randomize=False,
            repeat_count=3,
            pool_threshold_seconds=5.5,
            warm_pool_threshold_seconds=0.35,
            analytics_threshold_seconds=3.0,
        )
        self.assertEqual(8, result["question_count"])
        self.assertLessEqual(result["pool_size"], 8)
        self.assertEqual(3, result["repeat_count"])
        self.assertEqual(3, len(result["pool_timings"]))
        self.assertEqual(3, len(result["analytics_timings"]))''',
    )
    tests = replace_method(
        tests,
        "test_load_bank_trims_embedded_follow_on_questions_from_explanations",
        '''    def test_load_bank_trims_embedded_follow_on_questions_from_explanations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_bank.json"
            payload = {
                "title": "Synthetic",
                "questions": [
                    {
                        "question_number": 1,
                        "prompt": "Which answer is correct for this synthetic test?",
                        "choices": {"A": "Correct", "B": "Wrong"},
                        "correct": ["A"],
                        "general_explanation": "Keep this explanation. QUESTION 2 Remove this embedded follow-on.",
                    },
                    {
                        "question_number": 2,
                        "prompt": "Which answer is correct for the second synthetic test?",
                        "choices": {"A": "Correct", "B": "Wrong"},
                        "correct": ["A"],
                        "general_explanation": "Second explanation.",
                    },
                ],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            data = load_bank(path)
        self.assertEqual("Keep this explanation.", data["questions"][0]["general_explanation"])''',
    )
    tests = replace_method(
        tests,
        "test_clean_bank_default_preserves_runtime_file_stem",
        '''    def test_clean_bank_default_preserves_runtime_file_stem(self):
        app = self.make_app(start_session=False)
        bank_path = Path("C:/tmp/sc900_bank.json")

        self.assertEqual("sc900_bank", app.runtime_bank_stem(bank_path))
        self.assertEqual("sc900_bank_progress.json", app.progress_file_for_bank(bank_path).name)
        self.assertIn(
            "sc900_bank_practice_session_",
            app.session_file_for_bank(bank_path, mode="Practice", questions=[{"question_number": 1}]).name,
        )''',
    )
    write("tests/test_security_testing_engine.py", tests)


def create_branding_test() -> None:
    write(
        "tests/test_sc900_branding.py",
        '''import unittest
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

    def test_practice_target_does_not_claim_to_be_exam_pass_score(self):
        text = (ROOT / "app_game_mixin.py").read_text(encoding="utf-8")
        self.assertNotIn("Pass line crossed", text)
        self.assertNotIn("Pass score reached", text)
        self.assertIn("Practice target reached", text)


if __name__ == "__main__":
    unittest.main()
''',
    )


def implement_branding() -> None:
    launcher = 'from app import main\n\n\nif __name__ == "__main__":\n    main()\n'
    write("sc900_test_learning_engine_v8.py", launcher)
    write("sc900_test_learning_engine_v8.pyw", launcher)
    write(
        "run_sc900_v8.bat",
        '''@echo off
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
''',
    )
    game = read("app_game_mixin.py")
    game = game.replace("PASS_SCORE_THRESHOLD = 70.0", "PRACTICE_TARGET_THRESHOLD = 70.0\n    PASS_SCORE_THRESHOLD = PRACTICE_TARGET_THRESHOLD", 1)
    game = game.replace("Pass line crossed: ", "Practice target reached: ")
    game = game.replace("Pass line ", "Practice target ")
    game = game.replace("Pass score reached", "Practice target reached")
    write("app_game_mixin.py", game)


def adapt_release_tests() -> None:
    text = read("tests/test_release_tools.py")
    text = text.replace("SecurityTestingEngine", "SC900TestLearningEngine")
    text = text.replace("public_sy0701_bank_v4_plus_studyguide_clean.json", "sc900_bank.json")
    text = text.replace("1231", "8")
    text = text.replace("1200", "7")
    text = text.replace("expected 8, got 7", "expected 8, got 7")
    needle = 'self.assertEqual(bank_file.name, manifest["question_bank_filename"])\n'
    addition = needle + '            self.assertEqual(8, manifest["expected_bank_count"])\n'
    if needle not in text:
        raise RuntimeError("Release manifest assertion insertion point not found")
    text = text.replace(needle, addition, 1)
    write("tests/test_release_tools.py", text)


def implement_release_tools() -> None:
    write(
        "tools/build_release.py",
        '''import hashlib
import json
import os
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app_info import APP_VERSION
from certification_profile import (
    APP_NAME,
    DEFAULT_BANK_FILENAME,
    EXECUTABLE_BASENAME,
    EXPECTED_BANK_COUNT,
    RELEASE_DIRNAME,
    RUNTIME_NAMESPACE,
)
from pe_validation import pe_file_metadata, validate_pe_file

SOURCE_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_ROOT = SOURCE_ROOT.parent
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
DISCLAIMER = "Unofficial study application. Not affiliated with or endorsed by Microsoft."


def _copy_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing required release file: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _pe_header_is_valid(path: Path) -> bool:
    return validate_pe_file(path) is None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_manifest(build_profile: str) -> dict[str, object]:
    pe_info = pe_file_metadata(RELEASE_EXE)
    return {
        "application_version": APP_VERSION,
        "build_command": build_profile,
        "build_timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "executable_filename": RELEASE_EXE.name,
        "executable_sha256": _sha256(RELEASE_EXE),
        "executable_size": RELEASE_EXE.stat().st_size,
        "expected_bank_count": EXPECTED_QUESTION_COUNT,
        "pe_format": pe_info["format"],
        "pe_machine_type": pe_info["machine_type"],
        "python_version": platform.python_version(),
        "pyinstaller_version": os.environ.get("PYINSTALLER_VERSION", "unavailable"),
        "question_bank_filename": BANK_FILE.name,
        "question_bank_sha256": _sha256(BANK_FILE),
        "source_revision": os.environ.get("GITHUB_SHA") or os.environ.get("SOURCE_REVISION") or "unavailable",
    }


def _release_readme_text() -> str:
    return "\\n".join([
        f"{APP_NAME} v8", "", f"Double-click {EXECUTABLE_BASENAME}.exe to study.", "",
        "This folder is the clean distributable release.", "It contains the packaged EXE, launch note, and release manifest.", "",
        "Progress and history:", f"- %LOCALAPPDATA%\\\\{RUNTIME_NAMESPACE}", "", DISCLAIMER,
    ])


def _checkout_readme_text() -> str:
    return "\\n".join([
        f"{APP_NAME} v8", "", "Checkout launch copy:", f"- {EXECUTABLE_BASENAME}.exe", "",
        "Clean distributable release folder:", f"- release\\\\{RELEASE_DIRNAME}", "",
        "Progress and history:", f"- %LOCALAPPDATA%\\\\{RUNTIME_NAMESPACE}", "", DISCLAIMER,
    ])


def _source_readme_text() -> str:
    return "\\n".join([
        f"{APP_NAME} v8", "", "This folder is the authoritative source tree.", "",
        "Build outputs:", f"- dist\\\\{EXECUTABLE_BASENAME}.exe", f"- release\\\\{RELEASE_DIRNAME}", "", DISCLAIMER,
    ])


def _clean_release_dir() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def _remove_stale_source_tree_exe() -> None:
    if SOURCE_TREE_EXE.exists():
        SOURCE_TREE_EXE.unlink()


def build_release(_bank_path=None) -> Path:
    _clean_release_dir()
    _copy_required(DIST_EXE, RELEASE_EXE)
    _copy_required(DIST_EXE, CHECKOUT_EXE)
    _remove_stale_source_tree_exe()
    RELEASE_README.write_text(_release_readme_text(), encoding="utf-8")
    CHECKOUT_README.write_text(_checkout_readme_text(), encoding="utf-8")
    SOURCE_README.write_text(_source_readme_text(), encoding="utf-8")
    if not _pe_header_is_valid(RELEASE_EXE):
        raise ValueError(f"Release EXE is not a valid PE file: {RELEASE_EXE}")
    if not _pe_header_is_valid(CHECKOUT_EXE):
        raise ValueError(f"Checkout EXE is not a valid PE file: {CHECKOUT_EXE}")
    RELEASE_MANIFEST.write_text(
        json.dumps(_release_manifest("tools.build_release:build_release"), indent=2, sort_keys=True) + "\\n",
        encoding="utf-8",
    )
    return RELEASE_DIR


def main() -> None:
    path = build_release()
    print(f"Release folder ready: {path}")


if __name__ == "__main__":
    main()
''',
    )

    write(
        "tools/smoke_test.py",
        '''import hashlib
import io
import json
import sys
import unittest
from importlib import import_module
from pathlib import Path

from certification_profile import DEFAULT_BANK_FILENAME, EXECUTABLE_BASENAME, EXPECTED_BANK_COUNT, RELEASE_DIRNAME
from pe_validation import validate_pe_file

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

validate_bank_module = import_module("tools.validate_bank")
validate_bank = validate_bank_module.validate_bank
write_markdown_report = validate_bank_module.write_markdown_report

RELEASE = ROOT / "release" / RELEASE_DIRNAME
RELEASE_EXE = RELEASE / f"{EXECUTABLE_BASENAME}.exe"
RELEASE_README = RELEASE / "README - Start Here.txt"
RELEASE_MANIFEST = RELEASE / "release_manifest.json"
CHECKOUT_EXE = CHECKOUT_ROOT / f"{EXECUTABLE_BASENAME}.exe"
DEFAULT_BANK = ROOT / DEFAULT_BANK_FILENAME
EXPECTED_QUESTION_COUNT = EXPECTED_BANK_COUNT


def _validate_pe_file(path: Path, label: str) -> str | None:
    failure = validate_pe_file(path)
    return None if failure is None else f"{label} failed validation: {failure}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_release_tests() -> list[str]:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_release_tools.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    if result.wasSuccessful():
        return []
    details = []
    for case, traceback in result.failures + result.errors:
        summary = traceback.strip().splitlines()[-1] if traceback.strip() else "unknown failure"
        details.append(f"{case.id()}: {summary}")
    return details or ["Focused release tests failed."]


def run_smoke_checks(
    *, bank_path: Path = DEFAULT_BANK, release_exe: Path = RELEASE_EXE, release_readme: Path = RELEASE_README,
    checkout_exe: Path = CHECKOUT_EXE, report_path: Path | None = None, expected_question_count: int = EXPECTED_QUESTION_COUNT,
    validator=validate_bank, report_writer=write_markdown_report, release_test_runner=_run_release_tests,
) -> tuple[list[str], dict | None, Path]:
    failures: list[str] = []
    for label, path in (("release EXE", release_exe), ("checkout EXE", checkout_exe)):
        failure = _validate_pe_file(path, label)
        if failure:
            failures.append(failure)
    if not release_readme.exists():
        failures.append(f"Missing release README: {release_readme}")
    if not RELEASE_MANIFEST.exists():
        failures.append(f"Missing release manifest: {RELEASE_MANIFEST}")
    else:
        try:
            manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
            if manifest.get("executable_sha256") != _sha256(release_exe):
                failures.append("Release manifest executable hash mismatch.")
            if manifest.get("question_bank_sha256") != _sha256(bank_path):
                failures.append("Release manifest bank hash mismatch.")
            if int(manifest.get("expected_bank_count", -1)) != expected_question_count:
                failures.append("Release manifest expected bank count mismatch.")
        except Exception as exc:
            failures.append(f"Release manifest is unreadable: {exc}")
    try:
        result = validator(bank_path)
    except Exception as exc:
        return [f"Bank validation raised {exc.__class__.__name__}: {exc}"], None, (report_path or ROOT / "reports" / "bank_validation_report.md")
    if not isinstance(result, dict):
        failures.append("Bank validator returned malformed output.")
        return failures, None, (report_path or ROOT / "reports" / "bank_validation_report.md")
    try:
        question_count = int(result["question_count"])
        issues = list(result["issues"])
        warnings = list(result.get("warnings", []))
    except Exception as exc:
        failures.append(f"Bank validator returned malformed fields: {exc}")
        return failures, result, (report_path or ROOT / "reports" / "bank_validation_report.md")
    report_path = report_path or ROOT / "reports" / "bank_validation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_writer(result, report_path)
    if question_count != expected_question_count:
        failures.append(f"Unexpected bank count: expected {expected_question_count}, got {question_count}")
    if issues:
        failures.append(f"Bank validation reported {len(issues)} issue(s).")
    if warnings:
        failures.append(f"Bank validation reported {len(warnings)} warning(s).")
    failures.extend(release_test_runner())
    return failures, result, report_path


def main() -> int:
    failures, result, report_path = run_smoke_checks()
    if failures:
        for failure in failures:
            print(f"Smoke test failed: {failure}", file=sys.stderr)
        return 1
    print("Smoke test passed.")
    print(f"Validated release: {RELEASE}")
    print(f"Validation report: {report_path}")
    print(f"Question count: {result['question_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    )

    write(
        "build_sc900_v8.bat",
        '''@echo off
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
if not defined CI pause
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
if not defined CI pause
''',
    )


def write_docs_and_quality() -> None:
    quality = read("tools/run_quality_checks.py")
    quality = quality.replace('    "bank_models.py",\n', '    "bank_models.py",\n    "certification_profile.py",\n', 1)
    quality = quality.replace('    "tools/import_chapter_screenshots.py",\n', "", 1)
    write("tools/run_quality_checks.py", quality)

    write(
        "README.md",
        '''# SC-900 Test Learning Engine

Engine baseline: **v8.0.0**

Target certification: **Microsoft SC-900 — Security, Compliance, and Identity Fundamentals**.

The current baseline bank is `sc900_bank.json` and contains **8 original placeholder questions**. The large SC-900 content bank has not yet been imported. Smart Practice, Practice, Exam, analytics, progress persistence, validation, and question-quality controls are preserved from the v8 learning engine.

Future public/permitted study sources are intentionally handled separately:

`staging -> normalization -> validation -> deduplication -> review -> approved bank`

Unofficial study application. Not affiliated with or endorsed by Microsoft.

## Run

```bash
python app.py
```

On Windows, you may also run `run_sc900_v8.bat`.

## Validate and test

```bash
python -m unittest discover -s tests -v
python tools/validate_bank.py sc900_bank.json
python tools/run_quality_checks.py
```

## Windows build

Run `build_sc900_v8.bat`. The packaged executable is `SC900TestLearningEngine.exe` and packaged progress is stored under `%LOCALAPPDATA%\\SC900TestLearningEngine`.

## Content boundary

The eight-question bank exists only to verify the engine migration. It is not intended to represent the breadth or exact question count of the certification exam. External study material must be staged and reviewed before admission to the production question bank.
''',
    )
    write(
        "README - Start Here.txt",
        '''SC-900 Test Learning Engine v8

Run from source:
- Double-click run_sc900_v8.bat
- Or run: python app.py

Packaged release executable:
- SC900TestLearningEngine.exe

Progress for the packaged app is stored under:
%LOCALAPPDATA%\SC900TestLearningEngine

Unofficial study application. Not affiliated with or endorsed by Microsoft.
''',
    )
    write(
        "CHANGELOG.md",
        '''# Changelog

## 8.0.0-sc900-baseline — 2026-09-10

- Transplanted the proven v8 learning engine from the frozen SY0-701 source revision.
- Separated reusable engine identity from SC-900 certification identity.
- Rebranded runtime, launch, build, release, and storage surfaces for SC-900.
- Replaced Security+ content with an eight-question original SC-900 placeholder bank.
- Preserved Smart Practice, Practice, Exam, analytics, persistence, validation, and quality behavior for baseline verification.
- Established a separate staged content-ingestion boundary for later SC-900 source material.
''',
    )


def remove_harness() -> None:
    for rel in [".github/workflows/bootstrap-sc900-baseline.yml", ".github/scripts/bootstrap_sc900_baseline.py"]:
        path = ROOT / rel
        if path.exists():
            path.unlink()
    migration = ROOT / ".migration-source"
    if migration.exists():
        shutil.rmtree(migration)


def final_audit() -> None:
    forbidden = re.compile(r"CompTIA|SY0-701|Security Testing Engine|SecurityTestingEngine|public_sy0701", re.I)
    bad = []
    for pattern in ("*.py", "*.pyw", "*.bat"):
        for path in ROOT.rglob(pattern):
            rel = path.relative_to(ROOT)
            if ".git" in rel.parts or "tests" in rel.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if forbidden.search(text):
                bad.append(str(rel))
    if bad:
        raise RuntimeError(f"Old product identity remains in runtime/build files: {bad}")


def main() -> None:
    os.chdir(ROOT)
    print("SC-900 baseline migration starting", flush=True)
    clone_source()

    copy_allowlist()
    run(sys.executable, "-m", "compileall", "-q", ".")
    commit("chore: transplant frozen v8 engine baseline")

    create_profile_test()
    expect_fail(sys.executable, "-m", "unittest", "tests.test_certification_profile", "-v")
    implement_profile()
    run(sys.executable, "-m", "unittest", "tests.test_certification_profile", "tests.test_application_bootstrap", "-v")
    commit("feat: centralize SC-900 application identity")

    create_bank_test()
    expect_fail(sys.executable, "-m", "unittest", "tests.test_sc900_bank", "-v")
    implement_bank()
    run(sys.executable, "tools/validate_bank.py", "sc900_bank.json")
    run(sys.executable, "-m", "unittest", "tests.test_sc900_bank", "-v")
    commit("feat: add validated SC-900 placeholder bank")

    expect_fail(sys.executable, "-m", "unittest", "tests.test_security_testing_engine", "-v")
    convert_generic_tools_and_regressions()
    run(sys.executable, "-m", "unittest", "tests.test_security_testing_engine", "tests.test_sc900_bank", "-v")
    commit("test: decouple v8 regression suite from Security+ content")

    create_branding_test()
    expect_fail(sys.executable, "-m", "unittest", "tests.test_sc900_branding", "-v")
    implement_branding()
    run(sys.executable, "-m", "unittest", "tests.test_sc900_branding", "-v")
    commit("feat: rebrand SC-900 launch surfaces")

    adapt_release_tests()
    expect_fail(sys.executable, "-m", "unittest", "tests.test_release_tools", "-v")
    implement_release_tools()
    run(sys.executable, "-m", "unittest", "tests.test_release_tools", "-v")
    commit("feat: convert release tooling to SC-900 identity")

    write_docs_and_quality()
    run(sys.executable, "-m", "unittest", "tests.test_sc900_branding", "tests.test_certification_profile", "-v")
    commit("docs: establish SC-900 baseline identity and workflow")

    remove_harness()
    final_audit()
    run(sys.executable, "tools/validate_bank.py", "sc900_bank.json")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    run(sys.executable, "-m", "unittest", "tests.test_smart_practice_core", "tests.test_smart_practice_worker", "-v")
    run(sys.executable, "tools/benchmark_engine.py", "--bank", "sc900_bank.json", "--count", "8", "--repeat", "3", "--assert-pool-max", "4", "--assert-analytics-max", "3")
    run(sys.executable, "tools/run_quality_checks.py")
    run("git", "diff", "--check")
    commit("chore: remove temporary migration harness")

    run("cmd", "/c", "build_sc900_v8.bat")
    run(sys.executable, "tools/smoke_test.py")

    manifest_path = ROOT / "release" / "SC900TestLearningEngine" / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("application_version") != "8.0.0":
        raise RuntimeError("Wrong application version in release manifest")
    if manifest.get("executable_filename") != "SC900TestLearningEngine.exe":
        raise RuntimeError("Wrong executable identity in release manifest")
    if manifest.get("expected_bank_count") != 8 or manifest.get("question_bank_filename") != "sc900_bank.json":
        raise RuntimeError("Wrong bank identity in release manifest")
    if len(str(manifest.get("executable_sha256", ""))) != 64 or len(str(manifest.get("question_bank_sha256", ""))) != 64:
        raise RuntimeError("Release manifest hashes are invalid")

    verified_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write(
        "docs/SC900_V8_BASELINE.md",
        f'''# SC-900 v8 Baseline

- Source v8 revision: `{SOURCE_SHA}`
- Destination verified revision: `{verified_head}`
- Engine version: `8.0.0`
- Bank: `sc900_bank.json`
- Verified bank count: `{manifest['expected_bank_count']}`
- Executable: `{manifest['executable_filename']}`
- Executable SHA-256: `{manifest['executable_sha256']}`
- Question-bank SHA-256: `{manifest['question_bank_sha256']}`

## Verification

- `python tools/validate_bank.py sc900_bank.json` — PASS
- `python -m unittest discover -s tests -v` — PASS
- `python tools/run_quality_checks.py` — PASS
- `build_sc900_v8.bat` — PASS
- `python tools\\smoke_test.py` — PASS

SC-900 v8 baseline is frozen before large-bank ingestion or Smart Practice algorithm changes. The next development stage may improve the engine in the SC-900 repository, but content ingestion remains a separate validated pipeline.
''',
    )
    commit("docs: freeze verified SC-900 v8 baseline")

    final_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run("git", "tag", "-f", "-a", "sc900-v8-baseline", final_head, "-m", "Verified SC-900 Test Learning Engine v8 baseline")
    run("git", "push", "origin", f"HEAD:{BRANCH}")
    run("git", "push", "origin", "--force", "refs/tags/sc900-v8-baseline")
    print(f"SC-900 baseline migration completed at {final_head}", flush=True)


if __name__ == "__main__":
    main()
