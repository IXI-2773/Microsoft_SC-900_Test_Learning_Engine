import os
import unittest
from pathlib import Path

from release_resources import REQUIRED_RUNTIME_RESOURCES, pyinstaller_resource_args

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


if __name__ == "__main__":
    unittest.main()
