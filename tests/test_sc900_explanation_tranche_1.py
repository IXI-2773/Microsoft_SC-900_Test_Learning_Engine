from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from content_revision_authority import AdmissionStatus, canonical_manifest_sha256, sha256_file
from content_revision_correction_authority import admit_content_correction
from content_revision_explanation_authority import (
    admit_explanation_revision,
)
from question_bank import adaptive_shuffle_question, stable_shuffle_question
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint
from tools.build_sc900_explanation_tranche_1 import build_sc900_explanation_tranche_1
from tools.validate_bank import validate_bank

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "sc900_bank_v8_content_correction_001.json"
TARGET_PATH = ROOT / "sc900_bank_v8_explanation_tranche_1.json"
SPEC_PATH = ROOT / "content_revision_evidence/specs/sc900_explanation_tranche_1.json"
LEDGER_PATH = ROOT / "content_revision_evidence/reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json"
MANIFEST_PATH = ROOT / "content_revision_evidence/manifests/sc900_explanation_tranche_1.json"
RECEIPT_PATH = ROOT / "content_revision_evidence/receipts/sc900_explanation_tranche_1.json"

TARGET_IDS = (
    "sc900_p3_q025",
    "sc900_p3_q030",
    "sc900_p3_q037",
    "sc900_p3_q038",
    "sc900_p3_q056",
    "sc900_p3_q060",
    "sc900_p3_q076",
    "sc900_p3_q079",
    "sc900_p3_q088",
    "sc900_mlc_q029",
    "sc900_mlc_q033",
    "sc900_mlc_q039",
    "sc900_mlc_q040",
    "sc900_mlc_q041",
    "sc900_mlc_q048",
    "sc900_mlc_q051",
    "sc900_mlc_q054",
    "sc900_mlc_q058",
    "sc900_mlc_q071",
    "sc900_mlc_q073",
    "sc900_mlc_q091",
    "sc900_mlc_q100",
    "sc900_mlc_q105",
    "sc900_mlc_q114",
    "sc900_mlc_q120",
    "sc900_mlc_q130",
    "sc900_mlc_q132",
    "sc900_mlc_q147",
    "sc900_mlc_q168",
    "sc900_mlc_q174",
    "sc900_mlc_q175",
    "sc900_mlc_q183",
    "sc900_mlc_q194",
    "sc900_mlc_q195",
    "sc900_mlc_q200",
    "sc900_mlc_q218",
    "sc900_mlc_q223",
    "sc900_mlc_q225",
    "sc900_mlc_q230",
    "sc900_mlc_q235",
    "sc900_mlc_q241",
    "sc900_mlc_q243",
    "sc900_mlc_q271",
    "sc900_mlc_q272",
    "sc900_mlc_q273",
    "sc900_mlc_q288",
    "sc900_mlc_q292",
    "sc900_mlc_q297",
)
PR37_IDS = (
    "sc900_mlc_q064",
    "sc900_mlc_q118",
    "sc900_mlc_q150",
    "sc900_mlc_q198",
    "sc900_mlc_q219",
    "sc900_mlc_q226",
    "sc900_mlc_q242",
    "sc900_mlc_q249",
    "sc900_mlc_q269",
)
ALLOWED_FIELDS = {"general_explanation", "choice_explanations"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _questions(payload):
    return payload["questions"]


def _index(payload):
    return {canonical_question_id(q): q for q in _questions(payload)}


def _changed_fields(before, after):
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}


def _rehash_manifest(payload):
    payload = copy.deepcopy(payload)
    payload["payload_sha256"] = ""
    payload["payload_sha256"] = canonical_manifest_sha256(payload)
    return payload


class ExplanationTrancheOneContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = _load(SOURCE_PATH)
        cls.target = _load(TARGET_PATH)
        cls.spec = _load(SPEC_PATH)
        cls.ledger = _load(LEDGER_PATH)
        cls.manifest = _load(MANIFEST_PATH)
        cls.receipt = _load(RECEIPT_PATH)
        cls.source_by_id = _index(cls.source)
        cls.target_by_id = _index(cls.target)
        cls.spec_by_id = {row["question_id"]: row for row in cls.spec["revisions"]}
        cls.ledger_by_id = {row["question_id"]: row for row in cls.ledger["entries"]}

    def test_expl_001_required_general_explanations_exist(self):
        for qid in TARGET_IDS:
            self.assertTrue(str(self.target_by_id[qid]["general_explanation"]).strip())

    def test_expl_002_no_empty_admitted_selected_wrong_feedback(self):
        for qid in TARGET_IDS:
            for value in self.target_by_id[qid]["choice_explanations"].values():
                self.assertTrue(str(value).strip(), qid)

    def test_expl_003_exact_changed_id_set(self):
        changed = tuple(qid for qid in self.source_by_id if self.source_by_id[qid] != self.target_by_id[qid])
        self.assertEqual(TARGET_IDS, changed)

    def test_expl_004_exact_changed_fields(self):
        for qid in TARGET_IDS:
            self.assertEqual(ALLOWED_FIELDS, _changed_fields(self.source_by_id[qid], self.target_by_id[qid]))

    def test_expl_005_prompts_unchanged(self):
        for qid in TARGET_IDS:
            self.assertEqual(self.source_by_id[qid]["prompt"], self.target_by_id[qid]["prompt"])

    def test_expl_006_choices_unchanged(self):
        for qid in TARGET_IDS:
            self.assertEqual(self.source_by_id[qid]["choices"], self.target_by_id[qid]["choices"])

    def test_expl_007_keys_unchanged(self):
        for qid in TARGET_IDS:
            self.assertEqual(self.source_by_id[qid]["correct"], self.target_by_id[qid]["correct"])

    def test_expl_008_objectives_unchanged(self):
        for qid in TARGET_IDS:
            self.assertEqual(self.source_by_id[qid].get("objective_code"), self.target_by_id[qid].get("objective_code"))

    def test_expl_009_question_ids_unchanged(self):
        self.assertEqual(
            [canonical_question_id(q) for q in _questions(self.source)],
            [canonical_question_id(q) for q in _questions(self.target)],
        )

    def test_expl_010_question_order_unchanged(self):
        self.assertEqual(
            [q.get("question_number") for q in _questions(self.source)],
            [q.get("question_number") for q in _questions(self.target)],
        )

    def test_expl_011_ledger_stale_reference_removed_from_target_general(self):
        for qid in TARGET_IDS:
            frozen = self.ledger_by_id[qid]["frozen_semantic_entry_text"]
            match = re.search(
                r"(?ms)STALE_REFERENCE_TEXT\s*=\s*\n(.*?)\n\nSTALE_REFERENCE_REASON\s*=",
                frozen,
            )
            self.assertIsNotNone(match, qid)
            stale = match.group(1).strip()
            quoted = [term.strip() for term in re.findall(r'"([^"]+)"', stale) if term.strip()]
            general = self.target_by_id[qid]["general_explanation"].casefold()
            if quoted:
                for term in quoted:
                    self.assertNotIn(term.casefold(), general, f"{qid}: {term}")
            elif stale and stale.upper() not in {"NONE", "N/A"}:
                self.assertNotIn(stale.casefold(), general, qid)

    def test_expl_012_general_explanation_matches_frozen_semantics(self):
        for qid in TARGET_IDS:
            self.assertEqual(
                self.spec_by_id[qid]["target_general_explanation"],
                self.target_by_id[qid]["general_explanation"],
            )

    def test_expl_013_selected_wrong_feedback_matches_frozen_mapping(self):
        for qid in TARGET_IDS:
            self.assertEqual(
                self.spec_by_id[qid]["target_choice_explanations"],
                self.target_by_id[qid]["choice_explanations"],
            )
            self.assertFalse(
                set(self.target_by_id[qid]["choice_explanations"]) & set(self.target_by_id[qid]["correct"])
            )

    def test_expl_014_no_orphan_feedback(self):
        for qid in TARGET_IDS:
            q = self.target_by_id[qid]
            self.assertLessEqual(set(q["choice_explanations"]), set(q["choices"]))

    def test_expl_015_feedback_survives_stable_and_adaptive_choice_reorder(self):
        for qid in TARGET_IDS:
            q = self.target_by_id[qid]
            expected = {q["choices"][letter]: text for letter, text in q["choice_explanations"].items()}
            for shuffled in (stable_shuffle_question(q), adaptive_shuffle_question(q, "EXPL-015")):
                actual = {shuffled["choices"][letter]: text for letter, text in shuffled["choice_explanations"].items()}
                self.assertEqual(expected, actual, qid)

    def test_expl_016_fingerprint_deterministic(self):
        for qid in TARGET_IDS:
            self.assertEqual(
                question_content_fingerprint(self.target_by_id[qid]),
                question_content_fingerprint(copy.deepcopy(self.target_by_id[qid])),
            )

    def test_expl_017_all_target_fingerprints_match_frozen_packet(self):
        for qid in TARGET_IDS:
            self.assertNotEqual(
                self.spec_by_id[qid]["source_content_fingerprint"],
                self.spec_by_id[qid]["target_content_fingerprint"],
            )
            self.assertEqual(
                self.spec_by_id[qid]["target_content_fingerprint"],
                question_content_fingerprint(self.target_by_id[qid]),
            )

    def test_expl_018_source_bank_byte_immutable(self):
        self.assertEqual(
            "cd699a0e8af7c366bf5672bb2b1d90547c7071e87a47cbd766512bef59b2c791",
            sha256_file(SOURCE_PATH),
        )

    def test_expl_019_deterministic_two_build_equality(self):
        build_sc900_explanation_tranche_1(ROOT)
        first = {p: p.read_bytes() for p in (TARGET_PATH, MANIFEST_PATH, RECEIPT_PATH)}
        build_sc900_explanation_tranche_1(ROOT)
        second = {p: p.read_bytes() for p in first}
        self.assertEqual(first, second)

    def test_expl_030_protected_metadata_unchanged(self):
        for qid in TARGET_IDS:
            before = self.source_by_id[qid]
            after = self.target_by_id[qid]
            for field in set(before) | set(after):
                if field not in ALLOWED_FIELDS:
                    self.assertEqual(before.get(field), after.get(field), f"{qid}:{field}")

    def test_expl_031_package_b_v1_authority_rejects_explanation_manifest(self):
        from content_revision_authority import admit_content_revision

        result = admit_content_revision(
            self.manifest,
            source_questions=_questions(self.source),
            target_questions=_questions(self.target),
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            review_root=ROOT / "content_revision_evidence/reviews",
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_expl_032_wrong_change_class_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["permitted_change_class"] = "KEY_PRESERVING_CONTENT_CORRECTION"
        bad = _rehash_manifest(bad)
        result = admit_explanation_revision(
            bad,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_expl_033_pr37_corrected_records_preserved(self):
        for qid in PR37_IDS:
            self.assertEqual(self.source_by_id[qid], self.target_by_id[qid], qid)

    def test_expl_034_source_lineage_exact_post_correction_bank(self):
        source = self.manifest["source_bank"]
        self.assertEqual("sc900_bank_v8_content_correction_001.json", source["filename"])
        self.assertEqual(sha256_file(SOURCE_PATH), source["file_sha256"])
        self.assertEqual(bank_content_fingerprint(_questions(self.source)), source["content_fingerprint"])

    def test_expl_035_undeclared_content_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            bad_target = copy.deepcopy(self.target)
            _index(bad_target)[TARGET_IDS[0]]["prompt"] += " unauthorized"
            bad_path = Path(td) / TARGET_PATH.name
            bad_path.write_text(json.dumps(bad_target, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            bad_manifest = copy.deepcopy(self.manifest)
            bad_manifest["target_bank"]["file_sha256"] = sha256_file(bad_path)
            bad_manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(_questions(bad_target))
            bad_manifest = _rehash_manifest(bad_manifest)
            result = admit_explanation_revision(
                bad_manifest,
                source_bank_path=SOURCE_PATH,
                target_bank_path=bad_path,
                spec_path=SPEC_PATH,
                ledger_path=LEDGER_PATH,
            )
            self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_expl_036_missing_required_authority_evidence_fails(self):
        bad = copy.deepcopy(self.manifest)
        bad["edges"][0]["authority_refs"] = []
        bad = _rehash_manifest(bad)
        result = admit_explanation_revision(
            bad,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_expl_038_q118_unchanged(self):
        self.assertEqual(self.source_by_id["sc900_mlc_q118"], self.target_by_id["sc900_mlc_q118"])

    def test_expl_039_frozen_membership_enforced(self):
        self.assertEqual(TARGET_IDS, tuple(self.spec["target_ids"]))
        self.assertEqual(set(TARGET_IDS), {edge["question_id"] for edge in self.manifest["edges"]})

    def test_expl_040_no_blanket_abcd_duplication_in_targets(self):
        for qid in TARGET_IDS:
            q = self.target_by_id[qid]
            feedback = q["choice_explanations"]
            self.assertNotEqual(set(feedback), set(q["choices"]), qid)
            self.assertFalse(
                feedback
                and all(str(value).strip() == str(q["general_explanation"]).strip() for value in feedback.values()),
                qid,
            )

    def test_expl_041_sparse_choice_explanations_are_accepted(self):
        result = validate_bank(TARGET_PATH)
        feedback_issues = [
            issue for issue in result["issues"] if "Choice explanation" in issue[1] or "Sparse feedback" in issue[1]
        ]
        self.assertEqual([], feedback_issues)

    def test_expl_042_absent_optional_feedback_is_valid(self):
        with tempfile.TemporaryDirectory() as td:
            payload = copy.deepcopy(self.target)
            qid = TARGET_IDS[0]
            _index(payload)[qid]["choice_explanations"] = {}
            path = Path(td) / "sparse_empty.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = validate_bank(path)
            feedback_issues = [
                issue
                for issue in result["issues"]
                if f"Q{_index(payload)[qid]['question_number']}" == issue[0]
                and ("Choice explanation" in issue[1] or "Sparse feedback" in issue[1])
            ]
            self.assertEqual([], feedback_issues)

    def test_expl_044_semantic_correction_continuity_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["continuity_policy"] = "PRESERVE_HISTORICAL_EVIDENCE_RESET_ACTIVE_AFFECTED_STATE"
        bad = _rehash_manifest(bad)
        result = admit_explanation_revision(
            bad,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_expl_045_semantic_correction_v2_does_not_admit_explanation_class(self):
        result = admit_content_correction(
            self.manifest,
            spec=self.spec,
            currentness_record={"schema_version": 2},
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            currentness_path=SPEC_PATH,
            review_root=ROOT / "content_revision_evidence/reviews",
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)


if __name__ == "__main__":
    unittest.main()
