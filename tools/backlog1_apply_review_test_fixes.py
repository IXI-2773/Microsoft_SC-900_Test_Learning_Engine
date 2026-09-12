from pathlib import Path

root = Path(__file__).resolve().parents[1]

focused_path = root / "tests" / "test_backlog1_progress_identity_migration.py"
text = focused_path.read_text(encoding="utf-8")
old_import = "    register_progress_identity_bank,\n)\n"
new_import = "    register_progress_identity_bank,\n    resolve_registered_question_id_from_number,\n)\n"
if text.count(old_import) != 1:
    raise RuntimeError("focused test import boundary changed unexpectedly")
text = text.replace(old_import, new_import, 1)
old_test = '''    def test_b1_21_identifier_only_ui_reference_resolves_through_loaded_bank(self):\n        register_progress_identity_bank([question("sc900-a", 27)])\n        self.assertEqual(question_key({"question_number": 27}), "sc900-a")\n        with self.assertRaisesRegex(ValueError, "MISSING_CANONICAL_QUESTION_ID"):\n            question_key({"question_number": 999})\n'''
new_test = '''    def test_b1_21_identifier_only_ui_reference_uses_explicit_resolver(self):\n        register_progress_identity_bank([question("sc900-a", 27)])\n        with self.assertRaisesRegex(ValueError, "MISSING_CANONICAL_QUESTION_ID"):\n            question_key({"question_number": 27})\n        self.assertEqual(resolve_registered_question_id_from_number(27), "sc900-a")\n        with self.assertRaisesRegex(ValueError, "MISSING_CANONICAL_QUESTION_ID"):\n            resolve_registered_question_id_from_number(999)\n'''
if text.count(old_test) != 1:
    raise RuntimeError("focused B1-21 test boundary changed unexpectedly")
focused_path.write_text(text.replace(old_test, new_test, 1), encoding="utf-8")

review_path = root / "tests" / "test_backlog1_segment1_adversarial_review.py"
review = review_path.read_text(encoding="utf-8")
old_mock = 'with mock.patch.object(store, "backup_progress_file", side_effect=OSError("disk full")):'
new_mock = 'with mock.patch.object(RuntimePersistence, "backup_progress_file", side_effect=OSError("disk full")):'
if review.count(old_mock) != 1:
    raise RuntimeError("adversarial backup-failure test boundary changed unexpectedly")
review_path.write_text(review.replace(old_mock, new_mock, 1), encoding="utf-8")

print("Updated focused strict-boundary and backup-failure regressions.")
