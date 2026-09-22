from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "cand01r3_protocol.py"


class Cand01R3ScorerStructureTests(unittest.TestCase):
    def test_measurement_probe_scorer_definitions_are_unique(self) -> None:
        tree = ast.parse(PROTOCOL_PATH.read_text(encoding="utf-8"), filename=str(PROTOCOL_PATH))
        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertEqual(1, names.count("score_measurement_probe_answer"))
        self.assertEqual(1, names.count("record_measurement_probe_answer"))


if __name__ == "__main__":
    unittest.main()
