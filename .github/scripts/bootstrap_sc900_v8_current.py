from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
RUNNER_TEMP = Path(os.environ.get("RUNNER_TEMP", ROOT / ".sc900-bootstrap"))
SOURCE = RUNNER_TEMP / "sc900-source-v8"
TESTS = ROOT / "tests"
TOOLS = ROOT / "tools"
BANK = ROOT / "sc900_bank_v8_baseline.json"
PROFILE = ROOT / "cert_profile_sc900.json"
RELEASE_DIR = ROOT / "release" / "SC900TestLearningEngine"
RELEASE_EXE = RELEASE_DIR / "SC900TestLearningEngine.exe"

SOURCE_REPO = "https://github.com/IXI-2773/Comptia-SY0-701-Test-Learning-Engine.git"
SOURCE_SHA = "5c099196525f2df236d4c80069e2b3a00a70bf94"
BRANCH = "implementation/sc900-v8-baseline"
BASELINE_TAG = "SC900_V8_BASELINE"

RUNTIME_FILES = [
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

GENERIC_TESTS = [
    "test_analytics_calculation.py",
    "test_application_bootstrap.py",
    "test_smart_practice_core.py",
    "test_smart_practice_worker.py",
    "test_study_question_utils.py",
]

SOURCE_TOOLS = [
    "benchmark_engine.py",
    "clean_bank.py",
    "validate_bank.py",
]

LEGACY_RUNTIME_TERMS = (
    "sy0-701",
    "comptia",
    "security+",
    "public_sy0701",
)


def run(args: list[str], *, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(str(arg) for arg in args)}", flush=True)
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture,
        check=False,
    )
    if capture:
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(args)}")
    return result


def expect_failure(args: list[str], *, cwd: Path = ROOT) -> None:
    print(f"$ {' '.join(str(arg) for arg in args)}  # expected RED", flush=True)
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode == 0:
        raise RuntimeError("TDD RED gate unexpectedly passed before implementation")
    print("TDD RED gate confirmed.", flush=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def branch_name() -> str:
    return run(["git", "branch", "--show-current"], capture=True).stdout.strip()


def ensure_isolated_branch() -> None:
    current = branch_name()
    if current != BRANCH:
        raise RuntimeError(f"Refusing migration on {current!r}; expected {BRANCH!r}")
    status = run(["git", "status", "--porcelain"], capture=True).stdout.strip()
    if status:
        raise RuntimeError(f"Working tree must be clean before migration:\n{status}")


def tag_exists() -> bool:
    tags = run(["git", "tag", "--list", BASELINE_TAG], capture=True).stdout.splitlines()
    return BASELINE_TAG in tags


def git_commit(message: str, *, force_paths: tuple[Path, ...] = ()) -> None:
    run(["git", "add", "-A"])
    for path in force_paths:
        run(["git", "add", "-f", str(path.relative_to(ROOT))])
    status = run(["git", "status", "--porcelain"], capture=True).stdout.strip()
    if not status:
        print(f"No changes to commit for: {message}", flush=True)
        return
    run(["git", "commit", "-m", message])


def clone_source() -> None:
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--no-checkout", "--filter=blob:none", SOURCE_REPO, str(SOURCE)])
    run(["git", "fetch", "--depth", "1", "origin", SOURCE_SHA], cwd=SOURCE)
    run(["git", "checkout", "--detach", SOURCE_SHA], cwd=SOURCE)
    actual = run(["git", "rev-parse", "HEAD"], cwd=SOURCE, capture=True).stdout.strip()
    if actual != SOURCE_SHA:
        raise RuntimeError(f"Frozen source mismatch: expected {SOURCE_SHA}, got {actual}")


def verify_source_contract() -> None:
    required = [
        "app.py",
        "app_info.py",
        "question_bank.py",
        "tools/build_release.py",
        "tools/validate_bank.py",
        "tests/test_security_testing_engine.py",
        "public_sy0701_bank_v4_clean.json",
        "public_sy0701_bank_v4_plus_studyguide_clean.json",
    ]
    missing = [name for name in required if not (SOURCE / name).exists()]
    if missing:
        raise RuntimeError(f"Frozen v8 source contract changed; missing: {missing}")

    # Run the source tests that exercise reusable, non-ingestion subsystems before touching them.
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_analytics_calculation",
            "tests.test_application_bootstrap",
            "tests.test_smart_practice_core",
            "tests.test_smart_practice_worker",
            "tests.test_study_question_utils",
            "-v",
        ],
        cwd=SOURCE,
    )


def copy_source_engine() -> None:
    TESTS.mkdir(exist_ok=True)
    TOOLS.mkdir(exist_ok=True)

    for name in RUNTIME_FILES:
        src = SOURCE / name
        if not src.exists():
            raise RuntimeError(f"Required reusable v8 module missing: {name}")
        shutil.copy2(src, ROOT / name)

    for name in SOURCE_TOOLS:
        src = SOURCE / "tools" / name
        if not src.exists():
            raise RuntimeError(f"Required reusable v8 tool missing: tools/{name}")
        shutil.copy2(src, TOOLS / name)

    for name in GENERIC_TESTS:
        shutil.copy2(SOURCE / "tests" / name, TESTS / name)

    for name in (".gitattributes", ".gitignore", "LICENSE", "pyproject.toml", "requirements-dev.txt"):
        shutil.copy2(SOURCE / name, ROOT / name)


def create_contract_test() -> None:
    write(
        TESTS / "test_sc900_contract.py",
        textwrap.dedent(
            '''
            import json
            import os
            import sys
            import unittest
            from collections import Counter
            from pathlib import Path
            from unittest import mock

            ROOT = Path(__file__).resolve().parents[1]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            import cert_config
            import app
            from app_info import APP_NAME, APP_VERSION
            from question_bank import load_bank
            from tools.validate_bank import validate_bank
            from tools import build_release


            class SC900BaselineContractTests(unittest.TestCase):
                def test_profile_is_sc900_and_keeps_official_scoring_separate_from_readiness(self):
                    profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
                    self.assertEqual("Microsoft", profile["vendor"])
                    self.assertEqual("SC-900", profile["exam_code"])
                    self.assertEqual(700, profile["official_scaled_pass_score"])
                    self.assertEqual(1000, profile["official_scaled_score_max"])
                    self.assertEqual(82.5, profile["internal_readiness_threshold_pct"])
                    self.assertIn("not a conversion", profile["scoring_disclaimer"].lower())
                    self.assertEqual([10, 20, 40, 50], profile["practice_question_count_options"])
                    self.assertEqual(50, profile["practice_question_count_default"])

                def test_config_is_single_sc900_runtime_identity(self):
                    self.assertEqual("SC-900", cert_config.EXAM_CODE)
                    self.assertEqual("Microsoft SC-900 Test Learning Engine", APP_NAME)
                    self.assertEqual("8.0.0", APP_VERSION)
                    self.assertEqual("sc900_bank_v8_baseline.json", cert_config.QUESTION_BANK_FILENAME)
                    self.assertEqual("SC900TestLearningEngine", cert_config.USER_DATA_DIRNAME)

                def test_launch_bank_has_eight_original_placeholder_questions_balanced_by_domain(self):
                    data = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)
                    questions = data["questions"]
                    self.assertEqual(8, len(questions))
                    self.assertEqual(8, len({q["id"] for q in questions}))
                    self.assertEqual({"1", "2", "3", "4"}, {q["domain_code"] for q in questions})
                    self.assertEqual({"1": 2, "2": 2, "3": 2, "4": 2}, dict(Counter(q["domain_code"] for q in questions)))
                    for question in questions:
                        self.assertTrue(question["prompt"].strip())
                        self.assertTrue(question["general_explanation"].strip())
                        self.assertEqual(4, len(question["choices"]))
                        self.assertEqual(set(question["choices"]), set(question["choice_explanations"]))
                        corpus = json.dumps(question).lower()
                        self.assertNotIn("comptia", corpus)
                        self.assertNotIn("sy0-701", corpus)
                        self.assertNotIn("security+", corpus)

                def test_runtime_defaults_to_sc900_bank_and_user_data_namespace(self):
                    self.assertEqual(cert_config.QUESTION_BANK_FILENAME, app.DEFAULT_BANK.name)
                    with (
                        mock.patch.object(app.sys, "frozen", True, create=True),
                        mock.patch.dict(os.environ, {"LOCALAPPDATA": str(ROOT / "tmp-local")}),
                    ):
                        self.assertEqual("SC900TestLearningEngine", app.resolve_user_data_dir().name)

                def test_validator_reports_clean_baseline_bank(self):
                    result = validate_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)
                    self.assertEqual(8, result["question_count"])
                    self.assertEqual([], result["issues"])
                    self.assertEqual([], result["warnings"])

                def test_release_contract_targets_sc900(self):
                    self.assertEqual(8, build_release.EXPECTED_QUESTION_COUNT)
                    self.assertEqual("SC900TestLearningEngine.exe", build_release.RELEASE_EXE.name)
                    self.assertEqual(cert_config.QUESTION_BANK_FILENAME, build_release.BANK_FILE.name)


            if __name__ == "__main__":
                unittest.main()
            '''
        ),
    )


def profile_payload() -> dict[str, object]:
    return {
        "vendor": "Microsoft",
        "exam_code": "SC-900",
        "exam_name": "Microsoft Security, Compliance, and Identity Fundamentals",
        "engine_version": "8.0.0",
        "runtime_bank": "sc900_bank_v8_baseline.json",
        "placeholder_bank_question_count": 8,
        "practice_question_count_options": [10, 20, 40, 50],
        "practice_question_count_default": 50,
        "official_scaled_pass_score": 700,
        "official_scaled_score_max": 1000,
        "internal_readiness_threshold_pct": 82.5,
        "internal_readiness_min_attempts": 120,
        "scoring_disclaimer": (
            "The internal readiness percentage is a study heuristic, not a conversion to Microsoft's scaled exam score. "
            "Microsoft's official passing score is 700 on its reported scaled score; the engine does not infer that "
            "scaled score from raw practice accuracy."
        ),
        "domains": [
            {
                "code": "1",
                "name": "Describe the concepts of security, compliance, and identity",
                "weight": "10-15%",
            },
            {
                "code": "2",
                "name": "Describe the capabilities of Microsoft Entra",
                "weight": "25-30%",
            },
            {
                "code": "3",
                "name": "Describe the capabilities of Microsoft security solutions",
                "weight": "35-40%",
            },
            {
                "code": "4",
                "name": "Describe the capabilities of Microsoft compliance solutions",
                "weight": "20-25%",
            },
        ],
    }


def choice_explanations(correct: str, choices: dict[str, str], reason: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for letter, value in choices.items():
        if letter == correct:
            output[letter] = f"{value} is the best answer here. {reason}"
        else:
            output[letter] = f"{value} does not best satisfy the scenario described in this question."
    return output


def make_question(
    number: int,
    domain_code: str,
    domain: str,
    topic: str,
    prompt: str,
    choices: dict[str, str],
    correct: str,
    reason: str,
) -> dict[str, object]:
    return {
        "id": f"SC900-PH-{number:03d}",
        "question_number": number,
        "prompt": prompt,
        "choices": choices,
        "correct": [correct],
        "general_explanation": reason,
        "choice_explanations": choice_explanations(correct, choices, reason),
        "domain": domain,
        "domain_code": domain_code,
        "chapter": domain,
        "topics": [topic],
        "objective_code": domain_code,
        "question_type": "single",
        "source_name": "SC-900 baseline original placeholder bank",
        "study_focus": topic,
        "flagged_issues": [],
    }


def bank_payload() -> dict[str, object]:
    domains = {
        "1": "Security, compliance, and identity concepts",
        "2": "Microsoft Entra capabilities",
        "3": "Microsoft security solutions",
        "4": "Microsoft compliance solutions",
    }
    questions = [
        make_question(
            1,
            "1",
            domains["1"],
            "Shared responsibility",
            "In a cloud service relationship, which statement best describes the shared responsibility model?",
            {"A": "Security duties are divided between the provider and customer", "B": "The provider owns every security task", "C": "The customer owns every infrastructure task", "D": "Responsibility disappears when services are managed"},
            "A",
            "Cloud security responsibilities are divided between the service provider and the customer, with the exact split depending on the service model.",
        ),
        make_question(
            2,
            "1",
            domains["1"],
            "Zero Trust",
            "Which Zero Trust principle requires access decisions to evaluate identity, device, location, and other available signals?",
            {"A": "Trust every corporate-network request", "B": "Verify explicitly", "C": "Disable identity checks for managed devices", "D": "Grant permanent administrator access"},
            "B",
            "Verify explicitly means using available signals and context when making authentication and authorization decisions.",
        ),
        make_question(
            3,
            "2",
            domains["2"],
            "Microsoft Entra ID",
            "Which Microsoft service provides cloud-based identity and access management for users, applications, and resources?",
            {"A": "Microsoft Purview", "B": "Microsoft Sentinel", "C": "Microsoft Entra ID", "D": "Azure Cost Management"},
            "C",
            "Microsoft Entra ID is Microsoft's cloud identity and access management service.",
        ),
        make_question(
            4,
            "2",
            domains["2"],
            "Conditional Access",
            "Which Microsoft Entra capability can require multifactor authentication when specified access conditions are met?",
            {"A": "Sensitivity labels", "B": "Data lifecycle management", "C": "Microsoft Defender for Cloud", "D": "Conditional Access"},
            "D",
            "Conditional Access evaluates signals and can enforce controls such as requiring multifactor authentication.",
        ),
        make_question(
            5,
            "3",
            domains["3"],
            "Microsoft Sentinel",
            "Which Microsoft security solution is designed to collect and analyze security data for SIEM and security orchestration use cases?",
            {"A": "Microsoft Sentinel", "B": "Microsoft Priva", "C": "Microsoft Entra ID", "D": "Microsoft Intune"},
            "A",
            "Microsoft Sentinel provides cloud-native SIEM and security orchestration, automation, and response capabilities.",
        ),
        make_question(
            6,
            "3",
            domains["3"],
            "Microsoft Defender XDR",
            "Which Microsoft solution correlates security signals across endpoints, identities, email, and applications for extended detection and response?",
            {"A": "Microsoft Purview Audit", "B": "Microsoft Defender XDR", "C": "Azure Policy", "D": "Microsoft Entra Verified ID"},
            "B",
            "Microsoft Defender XDR correlates signals across multiple security domains to support detection, investigation, and response.",
        ),
        make_question(
            7,
            "4",
            domains["4"],
            "Sensitivity labels",
            "Which Microsoft Purview capability can classify and protect organizational information by applying labels to files and emails?",
            {"A": "Conditional Access", "B": "Microsoft Sentinel analytics rules", "C": "Sensitivity labels", "D": "Microsoft Defender for Cloud recommendations"},
            "C",
            "Sensitivity labels classify and can apply protection settings to organizational content such as files and email.",
        ),
        make_question(
            8,
            "4",
            domains["4"],
            "Data loss prevention",
            "Which Microsoft Purview capability helps detect and restrict inappropriate sharing of sensitive information across supported locations?",
            {"A": "Privileged Identity Management", "B": "Microsoft Defender for Endpoint", "C": "Conditional Access", "D": "Data loss prevention"},
            "D",
            "Data loss prevention policies identify sensitive information and can restrict or warn about inappropriate sharing and use.",
        ),
    ]
    return {
        "title": "Microsoft SC-900 Baseline Practice Questions",
        "version": "8.0.0-baseline",
        "questions": questions,
    }


def write_profile_bank_and_config() -> None:
    write(PROFILE, json.dumps(profile_payload(), indent=2, ensure_ascii=False))
    write(BANK, json.dumps(bank_payload(), indent=2, ensure_ascii=False))
    write(
        ROOT / "cert_config.py",
        textwrap.dedent(
            '''
            from __future__ import annotations

            import json
            from pathlib import Path

            PROFILE_PATH = Path(__file__).resolve().with_name("cert_profile_sc900.json")
            PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

            VENDOR = str(PROFILE["vendor"])
            EXAM_CODE = str(PROFILE["exam_code"])
            EXAM_NAME = str(PROFILE["exam_name"])
            APP_NAME = "Microsoft SC-900 Test Learning Engine"
            APP_VERSION = str(PROFILE["engine_version"])
            QUESTION_BANK_FILENAME = str(PROFILE["runtime_bank"])
            USER_DATA_DIRNAME = "SC900TestLearningEngine"
            OFFICIAL_SCALED_PASS_SCORE = int(PROFILE["official_scaled_pass_score"])
            INTERNAL_READINESS_THRESHOLD_PCT = float(PROFILE["internal_readiness_threshold_pct"])
            INTERNAL_READINESS_MIN_ATTEMPTS = int(PROFILE["internal_readiness_min_attempts"])
            '''
        ),
    )


def brand_replace(text: str) -> str:
    replacements = [
        ("Public SY0-701 Questions", "Microsoft SC-900 Baseline Questions"),
        ("public_sy0701_bank_v4_plus_studyguide_clean.json", "sc900_bank_v8_baseline.json"),
        ("public_sy0701_bank_v4_plus_studyguide_clean", "sc900_bank_v8_baseline"),
        ("public_sy0701_bank_v4_clean.json", "sc900_bank_v8_baseline.json"),
        ("public_sy0701_bank_v4_clean", "sc900_bank_v8_baseline"),
        ("public_sy0701_bank_v4.json", "sc900_bank_v8_baseline.json"),
        ("public_sy0701_bank_v4", "sc900_bank_v8_baseline"),
        ("public_sy0701", "sc900"),
        ("SecurityTestingEngine", "SC900TestLearningEngine"),
        ("Security Testing Engine", "Microsoft SC-900 Test Learning Engine"),
        ("security_testing_engine.log", "sc900_test_learning_engine.log"),
        ("SY0-701", "SC-900"),
        ("CompTIA", "Microsoft"),
        ("Security+", "SC-900"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def rebrand_runtime() -> None:
    # Apply mechanical product/certification substitutions to the reusable v8 modules.
    for name in RUNTIME_FILES:
        path = ROOT / name
        write(path, brand_replace(path.read_text(encoding="utf-8")))

    app_path = ROOT / "app.py"
    app_text = app_path.read_text(encoding="utf-8")
    app_text = app_text.replace(
        "from app_info import APP_NAME, APP_VERSION\n",
        "from app_info import APP_NAME, APP_VERSION\nfrom cert_config import QUESTION_BANK_FILENAME, USER_DATA_DIRNAME\n",
        1,
    )
    bank_pattern = re.compile(
        r"DEFAULT_BANK_CLEAN = first_existing_path\(.*?DEFAULT_BANK = first_existing_path\(DEFAULT_BANK_MERGED, DEFAULT_BANK_CLEAN, DEFAULT_BANK_LEGACY\)",
        re.DOTALL,
    )
    app_text, count = bank_pattern.subn(
        'DEFAULT_BANK = first_existing_path(\n    APP_DIR / QUESTION_BANK_FILENAME,\n    RESOURCE_DIR / QUESTION_BANK_FILENAME,\n)',
        app_text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not isolate the v8 app default-bank block for SC-900")
    app_text = app_text.replace('return base / "SC900TestLearningEngine"', "return base / USER_DATA_DIRNAME")
    write(app_path, app_text)

    write(
        ROOT / "app_info.py",
        "from cert_config import APP_NAME, APP_VERSION\n",
    )

    config_path = ROOT / "config_store.py"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace("'session_count': '25'", "'session_count': '50'")
    write(config_path, config_text)


def write_release_tools() -> None:
    write(
        TOOLS / "build_release.py",
        textwrap.dedent(
            '''
            from __future__ import annotations

            import hashlib
            import json
            import shutil
            from datetime import UTC, datetime
            from pathlib import Path

            from app_info import APP_NAME, APP_VERSION
            from cert_config import QUESTION_BANK_FILENAME
            from pe_validation import pe_file_metadata, validate_pe_file

            ROOT = Path(__file__).resolve().parents[1]
            DIST_EXE = ROOT / "dist" / "SC900TestLearningEngine.exe"
            RELEASE_DIR = ROOT / "release" / "SC900TestLearningEngine"
            RELEASE_EXE = RELEASE_DIR / "SC900TestLearningEngine.exe"
            RELEASE_README = RELEASE_DIR / "README - Start Here.txt"
            RELEASE_MANIFEST = RELEASE_DIR / "release_manifest.json"
            BANK_FILE = ROOT / QUESTION_BANK_FILENAME
            EXPECTED_QUESTION_COUNT = 8


            def _sha256(path: Path) -> str:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                return digest.hexdigest()


            def build_release(_bank_path=None) -> Path:
                if not DIST_EXE.exists():
                    raise FileNotFoundError(f"Missing built executable: {DIST_EXE}")
                if not BANK_FILE.exists():
                    raise FileNotFoundError(f"Missing SC-900 bank: {BANK_FILE}")
                if RELEASE_DIR.exists():
                    shutil.rmtree(RELEASE_DIR)
                RELEASE_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DIST_EXE, RELEASE_EXE)
                failure = validate_pe_file(RELEASE_EXE)
                if failure is not None:
                    raise ValueError(f"Release EXE failed PE validation: {failure}")
                RELEASE_README.write_text(
                    f"{APP_NAME} v{APP_VERSION}\\n\\nDouble-click SC900TestLearningEngine.exe to study.\\n",
                    encoding="utf-8",
                )
                pe = pe_file_metadata(RELEASE_EXE)
                manifest = {
                    "application_name": APP_NAME,
                    "application_version": APP_VERSION,
                    "build_timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "executable_filename": RELEASE_EXE.name,
                    "executable_sha256": _sha256(RELEASE_EXE),
                    "executable_size": RELEASE_EXE.stat().st_size,
                    "question_bank_filename": BANK_FILE.name,
                    "question_bank_sha256": _sha256(BANK_FILE),
                    "expected_bank_count": EXPECTED_QUESTION_COUNT,
                    "pe_format": pe["format"],
                    "pe_machine_type": pe["machine_type"],
                }
                RELEASE_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
                return RELEASE_DIR


            if __name__ == "__main__":
                print(f"Release folder ready: {build_release()}")
            '''
        ),
    )

    write(
        TOOLS / "lint_bank.py",
        textwrap.dedent(
            '''
            from __future__ import annotations

            import sys
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            from cert_config import QUESTION_BANK_FILENAME
            from tools.validate_bank import validate_bank


            def main() -> int:
                result = validate_bank(ROOT / QUESTION_BANK_FILENAME)
                failures = []
                if result["question_count"] != 8:
                    failures.append(f"expected 8 baseline questions, got {result['question_count']}")
                failures.extend(f"{title}: {body}" for title, body in result["issues"])
                failures.extend(f"warning {title}: {body}" for title, body in result.get("warnings", []))
                if failures:
                    for failure in failures:
                        print(f"SC-900 bank lint failed: {failure}", file=sys.stderr)
                    return 1
                print("SC-900 bank lint passed: 8 clean baseline questions.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            '''
        ),
    )

    write(
        TOOLS / "verify_installation.py",
        textwrap.dedent(
            '''
            from __future__ import annotations

            import json
            import sys
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            import app
            import cert_config
            from question_bank import load_bank

            REQUIRED = (
                "app.py",
                "cert_config.py",
                "cert_profile_sc900.json",
                "sc900_bank_v8_baseline.json",
                "question_bank.py",
            )
            BANNED = ("sy0-701", "comptia", "security+", "public_sy0701")


            def main() -> int:
                failures = []
                for name in REQUIRED:
                    if not (ROOT / name).exists():
                        failures.append(f"missing required file: {name}")
                profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
                if profile.get("exam_code") != "SC-900":
                    failures.append("profile exam_code is not SC-900")
                bank = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)
                if len(bank["questions"]) != 8:
                    failures.append(f"runtime bank contains {len(bank['questions'])} questions instead of 8")
                if app.DEFAULT_BANK.name != cert_config.QUESTION_BANK_FILENAME:
                    failures.append("app default bank does not use SC-900 config")
                runtime_paths = [ROOT / name for name in (
                    "app.py", "app_info.py", "question_bank.py", "cert_config.py",
                    "app_analytics_mixin.py", "app_session_builder_mixin.py",
                )]
                for path in runtime_paths:
                    text = path.read_text(encoding="utf-8").lower()
                    for term in BANNED:
                        if term in text:
                            failures.append(f"legacy term {term!r} remains in {path.name}")
                if failures:
                    for failure in failures:
                        print(f"SC-900 installation verification failed: {failure}", file=sys.stderr)
                    return 1
                print("SC-900 installation verification passed.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            '''
        ),
    )

    quality_targets = [
        "analytics_models.py",
        "analytics_summary.py",
        "bank_models.py",
        "progress_models.py",
        "progress_store.py",
        "question_bank.py",
        "runtime_persistence.py",
        "save_queue.py",
        "render_cache.py",
        "session_models.py",
        "session_store.py",
        "smart_practice_profile.py",
        "smart_practice_cache.py",
        "source_trust.py",
        "cert_config.py",
    ]
    write(
        TOOLS / "run_quality_checks.py",
        textwrap.dedent(
            f'''
            from __future__ import annotations

            import subprocess
            import sys
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            QUALITY_TARGETS = {quality_targets!r}


            def run_step(label: str, args: list[str]) -> None:
                print(f"[{{label}}] {{' '.join(args)}}")
                result = subprocess.run(args, cwd=ROOT, check=False)
                if result.returncode != 0:
                    raise SystemExit(result.returncode)


            def main() -> None:
                python = sys.executable
                run_step("ruff", [python, "-m", "ruff", "check", *QUALITY_TARGETS])
                run_step("black", [python, "-m", "black", "--check", *QUALITY_TARGETS])
                run_step("mypy", [python, "-m", "mypy"])
                print("Quality checks passed.")


            if __name__ == "__main__":
                main()
            '''
        ),
    )

    write(
        TOOLS / "smoke_test.py",
        textwrap.dedent(
            '''
            from __future__ import annotations

            import hashlib
            import json
            import sys
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            from cert_config import QUESTION_BANK_FILENAME
            from pe_validation import validate_pe_file
            from tools.build_release import RELEASE_EXE, RELEASE_MANIFEST, RELEASE_README
            from tools.validate_bank import validate_bank


            def sha256(path: Path) -> str:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                return digest.hexdigest()


            def main() -> int:
                failures = []
                bank = ROOT / QUESTION_BANK_FILENAME
                for path in (RELEASE_EXE, RELEASE_README, RELEASE_MANIFEST, bank):
                    if not path.exists():
                        failures.append(f"missing release component: {path}")
                if RELEASE_EXE.exists():
                    pe_failure = validate_pe_file(RELEASE_EXE)
                    if pe_failure:
                        failures.append(f"invalid release PE: {pe_failure}")
                result = validate_bank(bank)
                if result["question_count"] != 8 or result["issues"] or result.get("warnings"):
                    failures.append("release bank failed 8-question clean-bank gate")
                if RELEASE_MANIFEST.exists() and RELEASE_EXE.exists():
                    manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
                    if manifest.get("executable_sha256") != sha256(RELEASE_EXE):
                        failures.append("release executable hash mismatch")
                    if manifest.get("question_bank_sha256") != sha256(bank):
                        failures.append("release bank hash mismatch")
                    if int(manifest.get("expected_bank_count", -1)) != 8:
                        failures.append("release manifest bank count mismatch")
                if failures:
                    for failure in failures:
                        print(f"Smoke test failed: {failure}", file=sys.stderr)
                    return 1
                print("Static release smoke test passed.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            '''
        ),
    )


def rebrand_tool_defaults() -> None:
    for name in SOURCE_TOOLS:
        path = TOOLS / name
        write(path, brand_replace(path.read_text(encoding="utf-8")))


def create_filtered_engine_regression() -> tuple[int, int, list[str]]:
    source_path = SOURCE / "tests" / "test_security_testing_engine.py"
    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    removed: list[str] = []
    retained = 0
    markers = (
        "public_sy0701",
        "import_chapter_screenshots",
        "free study guide a5",
        "build_release_module",
        "run_benchmark",
        "validate_bank(",
        "clean_bank(",
        "q743",
        "q1105",
        "evil twin",
    )

    new_body: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "tools":
            names = [alias for alias in node.names if alias.name != "import_chapter_screenshots"]
            if not names:
                continue
            node.names = names
        if isinstance(node, ast.ClassDef):
            class_body: list[ast.stmt] = []
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name.startswith("test_"):
                    segment = ast.get_source_segment(source_text, member) or ""
                    lower = segment.lower()
                    if any(marker in lower for marker in markers):
                        removed.append(f"{node.name}.{member.name}")
                        continue
                    retained += 1
                class_body.append(member)
            node.body = class_body
        new_body.append(node)
    tree.body = new_body
    ast.fix_missing_locations(tree)
    rendered = ast.unparse(tree) + "\n"
    rendered = brand_replace(rendered)
    write(TESTS / "test_sc900_engine_regression.py", rendered)
    return retained, len(removed), removed


def rebrand_generic_tests() -> None:
    for name in GENERIC_TESTS:
        path = TESTS / name
        write(path, brand_replace(path.read_text(encoding="utf-8")))


def write_readme() -> None:
    write(
        ROOT / "README.md",
        textwrap.dedent(
            '''
            # Microsoft SC-900 Test Learning Engine v8

            This repository is the SC-900 specialization of the frozen v8 learning engine.

            The reusable application, analytics, persistence, Smart Practice, session, and UI subsystems are migrated from the pinned v8 source revision recorded in `docs/baseline/source-v8-contract.json`. Certification-specific identity and runtime bank selection are isolated in `cert_profile_sc900.json` and `cert_config.py`.

            ## Baseline scope

            `SC900_V8_BASELINE` intentionally contains only eight original placeholder questions: two for each SC-900 skills domain. Large-scale question ingestion happens only after this baseline passes regression, quality, Windows build, and smoke-test gates.

            The engine's readiness percentage is an internal study heuristic. It is not a conversion to Microsoft's reported scaled exam score.

            ## Run from source

            ```powershell
            python app.py
            ```

            ## Verify

            ```powershell
            python -m unittest discover -s tests -v
            python tools/lint_bank.py
            python tools/verify_installation.py
            python tools/run_quality_checks.py
            ```

            ## Windows release

            The verified baseline executable is packaged as `release/SC900TestLearningEngine/SC900TestLearningEngine.exe`.
            '''
        ),
    )
    write(
        ROOT / "README - Start Here.txt",
        "Microsoft SC-900 Test Learning Engine v8\n\nDouble-click SC900TestLearningEngine.exe in the release folder to study.\n",
    )


def write_baseline_docs(retained: int, removed: int, removed_names: list[str]) -> None:
    baseline_dir = ROOT / "docs" / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = {
        "source_repository": SOURCE_REPO.removesuffix(".git"),
        "source_sha": SOURCE_SHA,
        "engine_version": "8.0.0",
        "runtime_modules": len(RUNTIME_FILES),
        "source_generic_tests_executed_before_migration": GENERIC_TESTS,
        "source_runtime_sha256": {name: sha256(SOURCE / name) for name in RUNTIME_FILES},
    }
    write(baseline_dir / "source-v8-contract.json", json.dumps(source_manifest, indent=2, sort_keys=True))

    removed_lines = "\n".join(f"- `{name}`" for name in removed_names)
    write(
        baseline_dir / "migration-regression-matrix.md",
        textwrap.dedent(
            f'''
            # SC-900 v8 migration regression matrix

            Frozen source: `{SOURCE_SHA}`

            The migration executes the five standalone reusable source test modules before changing source code. It then carries the large v8 engine regression suite forward through an AST filter that removes tests coupled to Security+ source banks, screenshot-ingestion tooling, source-specific benchmark fixtures, or the old release packager.

            - Retained v8 engine regression test methods: **{retained}**
            - Removed source-coupled test methods: **{removed}**
            - Replacement SC-900 contract coverage: profile/config isolation, 8-question bank invariants, clean validation, runtime default-bank routing, user-data namespace, release metadata, installation verification, quality tooling, Windows PE build, and launch smoke test.

            ## Removed source-coupled methods

            {removed_lines or '- None'}
            '''
        ),
    )


def full_regression() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "tools/lint_bank.py"])
    run([sys.executable, "tools/verify_installation.py"])
    run([sys.executable, "tools/run_quality_checks.py"])


def build_windows() -> None:
    separator = os.pathsep
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "SC900TestLearningEngine",
            "--add-data",
            f"{BANK}{separator}.",
            "--add-data",
            f"{PROFILE}{separator}.",
            "app.py",
        ]
    )
    run([sys.executable, "tools/build_release.py"])
    run([sys.executable, "tools/smoke_test.py"])


def launch_smoke() -> None:
    if os.name != "nt":
        raise RuntimeError("The baseline launch smoke must run on Windows")
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f'$p = Start-Process -FilePath "{RELEASE_EXE}" -PassThru; '
            "Start-Sleep -Seconds 5; "
            "if ($p.HasExited) { if ($p.ExitCode -ne 0) { exit $p.ExitCode } else { exit 0 } }; "
            "$p.Kill(); $p.WaitForExit(); exit 0"
        ),
    ]
    run(command)


def verify_no_legacy_runtime() -> None:
    scan_paths = [ROOT / name for name in RUNTIME_FILES]
    scan_paths.extend([ROOT / "cert_config.py", ROOT / "README.md"])
    failures = []
    for path in scan_paths:
        lower = path.read_text(encoding="utf-8").lower()
        for term in LEGACY_RUNTIME_TERMS:
            if term in lower:
                failures.append(f"{path.relative_to(ROOT)} contains {term!r}")
    if failures:
        raise RuntimeError("Legacy certification identifiers remain in runtime:\n" + "\n".join(failures))


def verify_before_freeze() -> None:
    if not RELEASE_EXE.exists():
        raise RuntimeError("Verified Windows release executable is missing")
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    if len(bank.get("questions", [])) != 8:
        raise RuntimeError("Baseline bank is not exactly 8 questions")
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if profile.get("exam_code") != "SC-900":
        raise RuntimeError("Certification profile is not SC-900")
    if not (ROOT / "docs" / "baseline" / "source-v8-contract.json").exists():
        raise RuntimeError("Frozen source audit manifest is missing")
    verify_no_legacy_runtime()
    status = run(["git", "status", "--porcelain"], capture=True).stdout.strip()
    if status:
        raise RuntimeError(f"Working tree is not clean at freeze gate:\n{status}")


def tag_and_publish() -> None:
    run(["git", "tag", "-a", BASELINE_TAG, "-m", "Verified Microsoft SC-900 v8 baseline"])
    run(["git", "push", "origin", f"HEAD:{BRANCH}"])
    run(["git", "push", "origin", BASELINE_TAG])


def main() -> None:
    print("=== SC-900 v8 current-architecture migration ===", flush=True)
    ensure_isolated_branch()
    if tag_exists():
        if not RELEASE_EXE.exists():
            raise RuntimeError(f"{BASELINE_TAG} exists but the committed release artifact is missing")
        print(f"{BASELINE_TAG} already exists; verified baseline migration is frozen.", flush=True)
        return

    clone_source()
    verify_source_contract()
    print("SOURCE CONTRACT: GREEN", flush=True)

    copy_source_engine()
    create_contract_test()
    expect_failure([sys.executable, "-m", "unittest", "tests.test_sc900_contract", "-v"])
    git_commit("test: define SC-900 v8 baseline contract")

    write_profile_bank_and_config()
    rebrand_runtime()
    rebrand_tool_defaults()
    write_release_tools()
    rebrand_generic_tests()
    write_readme()
    run([sys.executable, "-m", "unittest", "tests.test_sc900_contract", "-v"])
    print("SC-900 CONTRACT: GREEN", flush=True)
    git_commit("feat: specialize frozen v8 engine for Microsoft SC-900")

    retained, removed, removed_names = create_filtered_engine_regression()
    write_baseline_docs(retained, removed, removed_names)
    verify_no_legacy_runtime()
    full_regression()
    print(f"FULL REGRESSION: GREEN ({retained} migrated v8 engine methods retained)", flush=True)
    git_commit("test: preserve reusable v8 regression and quality gates")

    build_windows()
    launch_smoke()
    git_commit(
        "build: create verified SC-900 v8 Windows baseline",
        force_paths=(RELEASE_DIR,),
    )

    # Fresh evidence immediately before freezing/publishing.
    full_regression()
    run([sys.executable, "tools/smoke_test.py"])
    launch_smoke()
    verify_before_freeze()
    tag_and_publish()
    print(f"BASELINE FROZEN: {BASELINE_TAG}", flush=True)


if __name__ == "__main__":
    main()
