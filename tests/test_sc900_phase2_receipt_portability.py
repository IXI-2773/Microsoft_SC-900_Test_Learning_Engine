import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "content" / "sc900" / "phase2" / "phase2_build_receipt.json"


class Phase2BuildReceiptPortabilityTests(unittest.TestCase):
    def test_committed_input_paths_are_canonical_posix(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        for section in ("batches", "reviews"):
            keys = list(receipt["inputs"][section])
            self.assertTrue(keys, section)
            self.assertTrue(
                all("\\" not in key and "/" in key for key in keys),
                f"{section} contains platform-dependent paths: {keys}",
            )


if __name__ == "__main__":
    unittest.main()
