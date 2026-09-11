from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ingestion.adapter import adapt_exchange_jsonl, exchange_question
from ingestion.importer import compile_question_bank, import_jsonl
from ingestion.models import load_taxonomy


class ScaleTests(unittest.TestCase):
    def test_thousand_extracted_records_are_idempotent_and_uncompiled(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "exchange.jsonl"
            rows = [
                exchange_question(
                    index,
                    question_text=f"Which identity control applies {hashlib.sha256(str(index).encode()).hexdigest()}?",
                    source_page=index,
                )
                for index in range(1, 1001)
            ]
            incoming.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
            canonical = adapt_exchange_jsonl(incoming, root / "canonical.jsonl", load_taxonomy())
            self.assertEqual(1000, canonical["adapted"])
            first = import_jsonl(root / "canonical.jsonl", root / "store", load_taxonomy())
            second = import_jsonl(root / "canonical.jsonl", root / "store", load_taxonomy())
            self.assertEqual(1000, first["accepted"])
            self.assertEqual(1000, first["pending"])
            self.assertEqual(0, first["approved"])
            self.assertEqual(0, second["accepted"])
            self.assertEqual(1000, second["skipped"])
            promotion = compile_question_bank(root / "store", root / "runtime.json")
            self.assertEqual(0, promotion["compiled"])
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            self.assertEqual(1000, len(stored))
            self.assertTrue(all(row["promotion_status"] == "pending" for row in stored))


if __name__ == "__main__":
    unittest.main()
