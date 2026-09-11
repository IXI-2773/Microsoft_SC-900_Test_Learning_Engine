import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ingestion.importer import apply_review_decision, compile_question_bank, import_jsonl
from ingestion.models import ValidationError, load_taxonomy
from question_bank import load_bank


def question(index: int, *, stem: str | None = None, page: int | None = None):
    return {
        "exam": "SC-900",
        "domain": "microsoft_entra",
        "objective": "entra_identity_access",
        "difficulty": "beginner",
        "type": "multiple_choice",
        "stem": stem or f"Which Entra capability applies rule {index}?",
        "choices": [{"id": "a", "text": "Microsoft Purview"}, {"id": "b", "text": "Microsoft Entra ID"}],
        "correct_answer": "b",
        "explanation": "Entra ID manages identity and access.",
        "source": {"book_id": "guide", "page": page or index},
        "tags": ["entra"],
        "metadata": {"origin": "extracted", "batch": "batch-1"},
    }


class ImporterTests(unittest.TestCase):
    def _write_jsonl(self, path: Path, records):
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def test_import_quarantines_invalid_skips_exact_and_leaves_runtime_uncompiled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "input.jsonl"
            self._write_jsonl(
                incoming,
                [
                    question(1),
                    question(1),
                    dict(question(2), stem=""),
                    {
                        "record_kind": "source_material",
                        "exam": "SC-900",
                        "body": "Entra is an identity service.",
                        "source": {"book_id": "guide", "page": 2},
                        "metadata": {"origin": "extracted"},
                    },
                ],
            )
            report = import_jsonl(incoming, root / "store", load_taxonomy())
            self.assertEqual(2, report["accepted"])
            self.assertEqual(1, report["skipped"])
            self.assertEqual(1, report["rejected"])
            self.assertIn("MISSING_STEM", report["reason_codes"])
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            self.assertEqual(["pending"], [row["promotion_status"] for row in stored])
            promotion = compile_question_bank(root / "store", root / "runtime.json")
            self.assertEqual(0, promotion["compiled"])
            self.assertEqual(0, promotion["approved"])
            self.assertEqual(1, promotion["pending"])
            runtime = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual([], runtime["questions"])

    def test_pending_withheld_and_quarantined_material_cannot_silently_compile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "input.jsonl"
            self._write_jsonl(
                incoming,
                [
                    question(1, stem="Which service stores identities?"),
                    question(2, stem="Which service evaluates Conditional Access?"),
                    dict(question(3), stem=""),
                ],
            )
            import_jsonl(incoming, root / "store", load_taxonomy())
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            first_id, second_id = stored[0]["id"], stored[1]["id"]
            apply_review_decision(root / "store", first_id, "approved", actor="reviewer")
            apply_review_decision(root / "store", second_id, "withheld", actor="reviewer")
            promotion = compile_question_bank(root / "store", root / "runtime.json")
            self.assertEqual(
                {"approved": 1, "pending": 0, "withheld": 1, "compiled": 1, "output": str(root / "runtime.json")},
                {key: promotion[key] for key in ("approved", "pending", "withheld", "compiled", "output")},
            )
            compiled = load_bank(root / "runtime.json")["questions"]
            self.assertEqual([first_id], [item["id"] for item in compiled])
            quarantine = json.loads((root / "store" / "quarantine.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(quarantine))
            decisions = json.loads((root / "store" / "review_decisions.json").read_text(encoding="utf-8"))
            self.assertEqual(["pending", "pending", "approved", "withheld"], [row["decision"] for row in decisions])
            self.assertEqual([first_id, second_id, first_id, second_id], [row["id"] for row in decisions])
            with self.assertRaises(ValidationError):
                apply_review_decision(root / "store", "missing-id", "approved")

    def test_large_import_is_idempotent_and_flags_probable_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "large.jsonl"
            records = [
                question(
                    index, stem=f"Which identity control applies {hashlib.sha256(str(index).encode()).hexdigest()}?"
                )
                for index in range(1000)
            ]
            records.append(question(1001, stem="Which Entra capability applies a conditional access rule?"))
            records.append(question(1002, stem="Which Entra capability applies conditional-access rules?"))
            self._write_jsonl(incoming, records)
            first = import_jsonl(incoming, root / "store", load_taxonomy())
            second = import_jsonl(incoming, root / "store", load_taxonomy())
            self.assertEqual(1001, first["accepted"])
            self.assertGreaterEqual(first["review"], 1)
            self.assertEqual(0, second["accepted"])
            self.assertEqual(1001, second["skipped"])
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            self.assertTrue(all(row["promotion_status"] == "pending" for row in stored))
            self.assertEqual(stored[0]["id"], json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))[0]["id"])


if __name__ == "__main__":
    unittest.main()
