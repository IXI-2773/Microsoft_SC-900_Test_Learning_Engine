import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from release_resources import REQUIRED_RUNTIME_RESOURCES, pyinstaller_resource_args
from tools import build_windows_release
from tools.verify_packaged_resources import (
    archive_listing_members,
    missing_runtime_resources,
    verify_packaged_resources,
)
from tools.verify_packaged_resources import (
    main as verify_packaged_resources_main,
)

ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_verifies_checkout_without_bootstrapping_migration(self):
        workflow = (ROOT / ".github" / "workflows" / "bootstrap-sc900-baseline.yml").read_text(encoding="utf-8")
        self.assertIn("git diff --exit-code", workflow)
        self.assertIn("python -m tools.build_windows_release", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn('test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.head.sha }}"', workflow)
        self.assertNotIn("bootstrap_sc900", workflow)
        self.assertNotIn("migration/bootstrap", workflow.lower())

    def test_required_runtime_resources_include_profile_bank_and_taxonomy(self):
        self.assertEqual(
            (
                Path("cert_profile_sc900.json"),
                Path("sc900_bank_v8_baseline.json"),
                Path("config/certifications/sc900-2026.json"),
            ),
            REQUIRED_RUNTIME_RESOURCES,
        )
        args = pyinstaller_resource_args(os.pathsep)
        self.assertEqual(6, len(args))
        self.assertIn(f"{ROOT / 'config/certifications/sc900-2026.json'}{os.pathsep}config/certifications", args)

    def test_packaged_resource_verifier_rejects_a_missing_taxonomy(self):
        members = {
            "cert_profile_sc900.json",
            "sc900_bank_v8_baseline.json",
        }

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

    @mock.patch("tools.verify_packaged_resources.subprocess.run")
    def test_packaged_resource_verifier_accepts_archive_with_all_resources(self, run):
        run.return_value = subprocess_result(
            """\
Contents of 'SC900TestLearningEngine' (PKG/CArchive):
 cert_profile_sc900.json
 sc900_bank_v8_baseline.json
 config/certifications/sc900-2026.json
"""
        )

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

    @mock.patch("tools.build_windows_release.run")
    def test_windows_release_build_verifies_archive_before_creating_release(self, run):
        build_windows_release.main()

        self.assertEqual([sys.executable, "tools/verify_packaged_resources.py"], run.call_args_list[1].args[0])
        self.assertEqual([sys.executable, "tools/build_release.py"], run.call_args_list[2].args[0])


def subprocess_result(stdout: str, returncode: int = 0, stderr: str = ""):
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    unittest.main()
