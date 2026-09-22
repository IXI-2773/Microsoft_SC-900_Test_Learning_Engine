from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from content_revision_authority import AdmissionStatus, canonical_manifest_sha256, sha256_file
from content_revision_correction_authority import AdmittedCorrectionRevision
from content_revision_explanation_authority import (
    AdmittedExplanationRevision,
    ExplanationFailureReason,
    admit_explanation_revision,
)
from content_revision_registry import (
    AUTHORIZED_CONTENT_REVISION_MANIFESTS,
    resolve_registered_revision_for_target,
)
from question_identity import bank_content_fingerprint

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "content_revision_evidence"
SOURCE_PATH = ROOT / "sc900_bank_v8_content_correction_001.json"
TARGET_PATH = ROOT / "sc900_bank_v8_explanation_tranche_1.json"
SPEC_PATH = EVIDENCE / "specs/sc900_explanation_tranche_1.json"
LEDGER_PATH = EVIDENCE / "reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json"
MANIFEST_PATH = EVIDENCE / "manifests/sc900_explanation_tranche_1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload):
    payload = copy.deepcopy(payload)
    payload["payload_sha256"] = ""
    payload["payload_sha256"] = canonical_manifest_sha256(payload)
    return payload


class ExplanationAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = _load(MANIFEST_PATH)

    def _admit(self, manifest=None, *, target_path=TARGET_PATH, spec_path=SPEC_PATH, ledger_path=LEDGER_PATH):
        return admit_explanation_revision(
            self.manifest if manifest is None else manifest,
            source_bank_path=SOURCE_PATH,
            target_bank_path=target_path,
            spec_path=spec_path,
            ledger_path=ledger_path,
        )

    def test_actual_governed_package_admits(self):
        result = self._admit()
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertIsInstance(result.admitted, AdmittedExplanationRevision)
        self.assertEqual(48, len(result.admitted.edges))

    def test_wrong_manifest_kind_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["manifest_kind"] = "sc900_content_revision_correction"
        bad = _rehash(bad)
        result = self._admit(bad)
        self.assertEqual(AdmissionStatus.FAIL, result.status)
        self.assertIn(ExplanationFailureReason.AUTHORITY_KIND_MISMATCH, result.reasons)

    def test_wrong_change_class_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["permitted_change_class"] = "WORDING_ONLY_LENGTH_REBALANCE"
        bad = _rehash(bad)
        result = self._admit(bad)
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_wrong_continuity_policy_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["continuity_policy"] = "PRESERVE_HISTORICAL_EVIDENCE_RESET_ACTIVE_AFFECTED_STATE"
        bad = _rehash(bad)
        result = self._admit(bad)
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_missing_authority_reference_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["edges"][0]["authority_refs"] = []
        bad = _rehash(bad)
        result = self._admit(bad)
        self.assertEqual(AdmissionStatus.FAIL, result.status)
        self.assertIn(ExplanationFailureReason.AUTHORITY_EVIDENCE_MISSING, result.reasons)

    def test_target_bank_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            payload = _load(TARGET_PATH)
            payload["questions"][0]["prompt"] += " tamper"
            path = Path(td) / TARGET_PATH.name
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self._admit(target_path=path)
            self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_spec_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            spec = _load(SPEC_PATH)
            spec["revisions"][0]["target_general_explanation"] += " tamper"
            path = Path(td) / SPEC_PATH.name
            path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self._admit(spec_path=path)
            self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_ledger_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = _load(LEDGER_PATH)
            ledger["entries"][0]["currentness_status"] = "FAIL"
            path = Path(td) / LEDGER_PATH.name
            path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self._admit(ledger_path=path)
            self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_registry_dispatches_explanation_manifest_kind(self):
        expected = canonical_manifest_sha256(self.manifest)
        result = resolve_registered_revision_for_target(
            TARGET_PATH,
            evidence_root=EVIDENCE,
            registry={"manifests/sc900_explanation_tranche_1.json": expected},
        )
        self.assertIsNotNone(result)
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertIsInstance(result.admitted, AdmittedExplanationRevision)

    def test_registry_dispatches_existing_correction_v2_without_activation(self):
        correction_manifest_path = EVIDENCE / "manifests/sc900_content_correction_001.json"
        correction_manifest = _load(correction_manifest_path)
        result = resolve_registered_revision_for_target(
            SOURCE_PATH,
            evidence_root=EVIDENCE,
            registry={"manifests/sc900_content_correction_001.json": canonical_manifest_sha256(correction_manifest)},
        )
        self.assertIsNotNone(result)
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertIsInstance(result.admitted, AdmittedCorrectionRevision)

    def test_production_registry_is_activated(self):
        self.assertEqual(8, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))

    def test_manifest_target_binding_matches_actual_candidate(self):
        target = _load(TARGET_PATH)
        self.assertEqual(sha256_file(TARGET_PATH), self.manifest["target_bank"]["file_sha256"])
        self.assertEqual(
            bank_content_fingerprint(target["questions"]),
            self.manifest["target_bank"]["content_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
