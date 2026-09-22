import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from release_resources import (
    REQUIRED_RUNTIME_RESOURCES,
    packaged_lineage_resource_closure,
    pyinstaller_resource_args,
)
from tools import build_windows_release
from tools.verify_packaged_resources import (
    archive_listing_members,
    missing_runtime_resources,
    packaged_resource_target_sha256,
    verify_packaged_resources,
)
from tools.verify_packaged_resources import (
    main as verify_packaged_resources_main,
)

ROOT = Path(__file__).resolve().parents[1]


def required_member_names() -> set[str]:
    return {path.as_posix() for path in REQUIRED_RUNTIME_RESOURCES}


def complete_archive_listing(*, windows: bool = False) -> str:
    lines = ["Contents of 'SC900TestLearningEngine' (PKG/CArchive):"]
    for resource in REQUIRED_RUNTIME_RESOURCES:
        name = resource.as_posix().replace("/", "\\") if windows else resource.as_posix()
        lines.append(f" {name}")
    return "\n".join(lines) + "\n"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_verifies_checkout_without_bootstrapping_migration(self):
        workflow = (ROOT / ".github" / "workflows" / "bootstrap-sc900-baseline.yml").read_text(encoding="utf-8")
        self.assertIn("git diff --exit-code", workflow)
        self.assertIn("python -m tools.build_windows_release", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn('test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.head.sha }}"', workflow)
        self.assertNotIn("bootstrap_sc900", workflow)
        self.assertNotIn("migration/bootstrap", workflow.lower())

    def test_required_runtime_resources_include_profile_banks_and_taxonomy(self):
        self.assertEqual(
            (
                Path("cert_profile_sc900.json"),
                Path("sc900_bank_v8_explanation_q118_repair.json"),
                Path("sc900_bank_v8_baseline.json"),
                Path("config/certifications/sc900-2026.json"),
            ),
            REQUIRED_RUNTIME_RESOURCES[:4],
        )
        self.assertIn(
            Path("content_revision_evidence/manifests/sc900_content_correction_001.json"), REQUIRED_RUNTIME_RESOURCES
        )
        args = pyinstaller_resource_args(os.pathsep)
        self.assertEqual(2 * len(REQUIRED_RUNTIME_RESOURCES), len(args))
        self.assertIn(f"{ROOT / 'config/certifications/sc900-2026.json'}{os.pathsep}config/certifications", args)
        manifest = ROOT / "content_revision_evidence/manifests/sc900_content_correction_001.json"
        self.assertIn(f"{manifest}{os.pathsep}content_revision_evidence/manifests", args)

    def test_packaged_resource_verifier_rejects_a_missing_taxonomy(self):
        members = set(required_member_names())
        members.remove("config/certifications/sc900-2026.json")

        self.assertEqual(
            ["config/certifications/sc900-2026.json"],
            missing_runtime_resources(members),
        )

    def test_packaged_resource_verifier_accepts_posix_and_windows_taxonomy_spelling(self):
        posix_members = required_member_names()
        windows_members = {name.replace("/", "\\") for name in posix_members}

        self.assertEqual([], missing_runtime_resources(posix_members))
        self.assertEqual([], missing_runtime_resources(windows_members))

    def test_packaged_resource_verifier_rejects_unrelated_similarly_named_taxonomy(self):
        members = set(required_member_names())
        members.remove("config/certifications/sc900-2026.json")
        members.update(
            {
                "sc900-2026.json",
                "config/certifications/sc900-2026.json.bak",
                "config\\certifications\\other-sc900-2026.json",
            }
        )

        self.assertEqual(
            ["config/certifications/sc900-2026.json"],
            missing_runtime_resources(members),
        )

    def test_packaged_resource_verifier_reads_data_paths_from_brief_pyinstaller_listing(self):
        listing = """\
Contents of 'SC900TestLearningEngine' (PKG/CArchive):
 cert_profile_sc900.json
 config/certifications/sc900-2026.json
"""

        self.assertEqual(
            {
                "cert_profile_sc900.json",
                "config/certifications/sc900-2026.json",
            },
            archive_listing_members(listing),
        )

    def test_packaged_resource_verifier_reads_windows_separator_brief_listing(self):
        listing = (
            "Contents of 'SC900TestLearningEngine.exe' (PKG/CArchive):\n"
            " cert_profile_sc900.json\n"
            " sc900_bank_v8_explanation_q118_repair.json\n"
            " sc900_bank_v8_baseline.json\n"
            " config\\certifications\\sc900-2026.json\n"
        )

        self.assertEqual(
            {
                "cert_profile_sc900.json",
                "sc900_bank_v8_explanation_q118_repair.json",
                "sc900_bank_v8_baseline.json",
                "config/certifications/sc900-2026.json",
            },
            archive_listing_members(listing),
        )
        self.assertEqual([], missing_runtime_resources(archive_listing_members(complete_archive_listing(windows=True))))

    @mock.patch("tools.verify_packaged_resources.subprocess.run")
    def test_packaged_resource_verifier_accepts_archive_with_all_resources(self, run):
        run.return_value = subprocess_result(complete_archive_listing())

        self.assertEqual([], verify_packaged_resources(ROOT / "dist" / "SC900TestLearningEngine.exe"))
        self.assertEqual(
            [
                sys.executable,
                "-m",
                "PyInstaller.utils.cliutils.archive_viewer",
                str(ROOT / "dist" / "SC900TestLearningEngine.exe"),
                "--list",
                "--brief",
            ],
            run.call_args.args[0],
        )

    @mock.patch("tools.verify_packaged_resources.subprocess.run")
    def test_packaged_resource_verifier_accepts_windows_archive_listing(self, run):
        run.return_value = subprocess_result(complete_archive_listing(windows=True))

        self.assertEqual([], verify_packaged_resources(ROOT / "dist" / "SC900TestLearningEngine.exe"))

    @mock.patch("tools.verify_packaged_resources.subprocess.run")
    def test_packaged_resource_verifier_reports_archive_reader_error(self, run):
        run.return_value = subprocess_result("", returncode=2, stderr="not a PyInstaller archive")

        with self.assertRaisesRegex(RuntimeError, "not a PyInstaller archive"):
            verify_packaged_resources(ROOT / "dist" / "SC900TestLearningEngine.exe")

    @mock.patch(
        "tools.verify_packaged_resources.verify_packaged_resources",
        side_effect=RuntimeError("not a PyInstaller archive"),
    )
    def test_packaged_resource_verifier_main_reports_archive_reader_error(self, _verify):
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            self.assertEqual(1, verify_packaged_resources_main())

        self.assertIn("Packaged resource verification failed: not a PyInstaller archive", stderr.getvalue())

    def test_packaged_lineage_closure_rejects_each_required_evidence_class(self):
        closure = {path.as_posix() for path in packaged_lineage_resource_closure()}
        required = {
            "sc900_bank_v8_final.json": "missing bank",
            "content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json": "missing manifest",
            "content_revision_evidence/fingerprint_bridges/sc900_content_fingerprint_bridge_v1.json": "missing bridge",
            "content_revision_evidence/specs/sc900_content_correction_001.json": "missing correction spec",
            "content_revision_evidence/currentness/sc900_content_correction_001.json": "missing currentness",
            "content_revision_evidence/specs/sc900_explanation_tranche_1.json": "missing explanation spec",
            "content_revision_evidence/reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json": "missing ledger",
            "content_revision_evidence/reviews/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1/sc900_mlc_q030.json": "missing equivalence review",
            "content_revision_evidence/reviews/SC900-SEPARATE-CONTENT-CORRECTION-001/sc900_mlc_q118.json": "missing correction review",
            "content_revision_evidence/specs/sc900_explanation_q118_repair_001.json": "missing q118 spec",
            "content_revision_evidence/reviews/SC900-EXPLANATION-Q118-REPAIR-001/semantic_review_ledger.json": "missing q118 ledger",
        }
        self.assertTrue(set(required).issubset(closure))
        members = required_member_names()
        for missing_path in required:
            self.assertEqual([missing_path], missing_runtime_resources(members - {missing_path}))

    def test_packaged_resource_verifier_records_target_sha256(self):
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"packaged-target")
            target = Path(handle.name)
        try:
            self.assertEqual(64, len(packaged_resource_target_sha256(target)))
        finally:
            target.unlink()

    @mock.patch("PyInstaller.__main__.run")
    @mock.patch("tools.build_windows_release.run")
    def test_windows_release_build_verifies_archive_before_creating_release(self, run, pyinstaller_run):
        build_windows_release.main()

        pyinstaller_args = pyinstaller_run.call_args.args[0]
        manifest = ROOT / "content_revision_evidence/manifests/sc900_content_correction_001.json"
        self.assertIn(f"{manifest}{os.pathsep}content_revision_evidence/manifests", pyinstaller_args)
        self.assertEqual([sys.executable, "tools/verify_packaged_resources.py"], run.call_args_list[0].args[0])
        self.assertEqual([sys.executable, "tools/build_release.py"], run.call_args_list[1].args[0])
        self.assertEqual([sys.executable, "tools/smoke_test.py"], run.call_args_list[2].args[0])

    def test_build_release_script_imports_app_info_when_invoked_as_a_file(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import runpy; runpy.run_path('tools/build_release.py', run_name='not_main')",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("No module named 'app_info'", result.stderr)


def subprocess_result(stdout: str, returncode: int = 0, stderr: str = ""):
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    unittest.main()
