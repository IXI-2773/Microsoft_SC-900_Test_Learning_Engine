import os
import unittest
from pathlib import Path

from release_resources import REQUIRED_RUNTIME_RESOURCES, pyinstaller_resource_args
from tools.verify_packaged_resources import archive_listing_members, missing_runtime_resources

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

    def test_packaged_resource_verifier_reads_data_paths_from_pyinstaller_listing(self):
        listing = """\
Contents of 'SC900TestLearningEngine' (PKG/CArchive):
 11480132, 552, 1339, 1, 'x', 'cert_profile_sc900.json'
 11480684, 268, 725, 1, 'x', 'config/certifications/sc900-2026.json'
"""

        self.assertEqual(
            {
                "cert_profile_sc900.json",
                "config/certifications/sc900-2026.json",
            },
            archive_listing_members(listing),
        )


if __name__ == "__main__":
    unittest.main()
