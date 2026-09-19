from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from question_identity import bank_content_fingerprint
from tools import build_package_b_tranche1, build_package_b_tranche2, build_package_b_tranche3, build_package_b_tranche4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
T2_CANDIDATE = REPOSITORY_ROOT / "sc900_bank_v8_length_rebalanced_t2.json"
T3_CANDIDATE = REPOSITORY_ROOT / "sc900_bank_v8_length_rebalanced_t3.json"
T4_CANDIDATE = REPOSITORY_ROOT / "sc900_bank_v8_length_rebalanced_t4.json"
T2_MANIFEST = REPOSITORY_ROOT / "content_revision_evidence/manifests/sc900_answer_length_rebalance_t2.json"
T3_MANIFEST = REPOSITORY_ROOT / "content_revision_evidence/manifests/sc900_answer_length_rebalance_t3.json"
T4_MANIFEST = REPOSITORY_ROOT / "content_revision_evidence/manifests/sc900_answer_length_rebalance_t4.json"

T2_CANONICAL_FILE_SHA256 = "c53ba19ee26992643969d546a73da5aa8396041ebe4e138f6b30db637756aa65"
T3_CANONICAL_FILE_SHA256 = "0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd"
T4_CANONICAL_FILE_SHA256 = "c40f919bb10cf2a5b965e1525b4771572a7f36fd63ef8749e277d988a04688b4"
T2_CONTENT_FINGERPRINT = "34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b"
T3_CONTENT_FINGERPRINT = "83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2"
T4_CONTENT_FINGERPRINT = "99db6d4cbec9a722ef85280debb80f7c60c7acc0e7dba7d9663f2e1744bdae3c"
T3_REJECTED_CRLF_SHA256 = "d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b"


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _windows_translating_write_text(path: Path, data: str, *, encoding: str | None = None, **_: object) -> int:
    """Model text-mode output on a host that translates LF to CRLF."""
    raw = data.replace("\n", "\r\n").encode(encoding or "utf-8")
    path.write_bytes(raw)
    return len(data)


class PackageBCanonicalByteRegressionTests(unittest.TestCase):
    def test_t2_and_t3_semantics_are_newline_independent_but_byte_hashes_are_not(self) -> None:
        cases = (
            (T2_CANDIDATE, T2_CANONICAL_FILE_SHA256, T2_CONTENT_FINGERPRINT),
            (T3_CANDIDATE, T3_CANONICAL_FILE_SHA256, T3_CONTENT_FINGERPRINT),
            (T4_CANDIDATE, T4_CANONICAL_FILE_SHA256, T4_CONTENT_FINGERPRINT),
        )
        for path, expected_lf_sha256, expected_fingerprint in cases:
            with self.subTest(path=path.name):
                lf_bytes = path.read_bytes()
                crlf_bytes = lf_bytes.replace(b"\n", b"\r\n")

                self.assertEqual(expected_lf_sha256, _raw_sha256(lf_bytes))
                self.assertNotEqual(_raw_sha256(lf_bytes), _raw_sha256(crlf_bytes))
                self.assertEqual(
                    expected_fingerprint,
                    bank_content_fingerprint(json.loads(lf_bytes.decode("utf-8"))["questions"]),
                )
                self.assertEqual(
                    expected_fingerprint,
                    bank_content_fingerprint(json.loads(crlf_bytes.decode("utf-8"))["questions"]),
                )

    def test_frozen_t2_and_t3_manifests_bind_committed_lf_candidate_bytes(self) -> None:
        t2_manifest = json.loads(T2_MANIFEST.read_text(encoding="utf-8"))
        t3_manifest = json.loads(T3_MANIFEST.read_text(encoding="utf-8"))
        t4_manifest = json.loads(T4_MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(T2_CANONICAL_FILE_SHA256, t2_manifest["target_bank"]["file_sha256"])
        self.assertEqual(T2_CANONICAL_FILE_SHA256, t3_manifest["source_bank"]["file_sha256"])
        self.assertEqual(T3_CANONICAL_FILE_SHA256, t3_manifest["target_bank"]["file_sha256"])
        self.assertEqual(T3_CANONICAL_FILE_SHA256, t4_manifest["source_bank"]["file_sha256"])
        self.assertEqual(T4_CANONICAL_FILE_SHA256, t4_manifest["target_bank"]["file_sha256"])
        self.assertEqual(T4_CONTENT_FINGERPRINT, t4_manifest["target_bank"]["content_fingerprint"])

    def test_package_b_writers_emit_lf_bytes_when_text_mode_would_translate_newlines(self) -> None:
        payload = {"title": "Canonical JSON", "questions": []}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.object(Path, "write_text", new=_windows_translating_write_text):
                build_package_b_tranche2._write_json(root / "t2.json", payload)
                build_package_b_tranche3._write_json(root / "t3.json", payload)
                build_package_b_tranche1._write_json(root / "t1.json", payload)
                build_package_b_tranche4._write_json(root / "t4.json", payload)

            for path in (root / "t1.json", root / "t2.json", root / "t3.json", root / "t4.json"):
                with self.subTest(path=path.name):
                    raw = path.read_bytes()
                    self.assertNotIn(b"\r\n", raw)
                    self.assertTrue(raw.endswith(b"\n"))
                    self.assertEqual(payload, json.loads(raw.decode("utf-8")))

    def test_real_t2_and_t3_fresh_materialization_reproduces_canonical_bytes(self) -> None:
        research_root = REPOSITORY_ROOT / "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            t2_path = root / T2_CANDIDATE.name
            t3_path = root / T3_CANDIDATE.name

            t2_summary = build_package_b_tranche2.build_package_b_tranche2(
                REPOSITORY_ROOT / "sc900_bank_v8_length_rebalanced_t1.json",
                research_root / "14-PACKAGE-B-TRANCHE2-SEMANTIC-REVIEW.json",
                t2_path,
                root / "reviews",
                root / "t2-manifest.json",
            )
            t3_summary = build_package_b_tranche3.build_package_b_tranche3(
                t2_path,
                research_root / "20-PACKAGE-B-TRANCHE3-SEMANTIC-REVIEW.json",
                t3_path,
                root / "reviews",
                root / "t3-manifest.json",
            )
            t4_path = root / T4_CANDIDATE.name
            t4_summary = build_package_b_tranche4.build_package_b_tranche4(
                t3_path,
                research_root / "28-PACKAGE-B-TRANCHE4-SEMANTIC-REVIEW.json",
                t4_path,
                root / "reviews",
                root / "t4-manifest.json",
            )

            for path, expected_sha256, expected_fingerprint, summary in (
                (t2_path, T2_CANONICAL_FILE_SHA256, T2_CONTENT_FINGERPRINT, t2_summary),
                (t3_path, T3_CANONICAL_FILE_SHA256, T3_CONTENT_FINGERPRINT, t3_summary),
                (t4_path, T4_CANONICAL_FILE_SHA256, T4_CONTENT_FINGERPRINT, t4_summary),
            ):
                with self.subTest(path=path.name):
                    raw = path.read_bytes()
                    self.assertNotIn(b"\r\n", raw)
                    self.assertTrue(raw.endswith(b"\n"))
                    self.assertEqual(expected_sha256, _raw_sha256(raw))
                    self.assertEqual(expected_sha256, summary["target_file_sha256"])
                    self.assertEqual(
                        expected_fingerprint,
                        bank_content_fingerprint(json.loads(raw.decode("utf-8"))["questions"]),
                    )

    def test_t3_crlf_source_is_rejected_and_fingerprint_equality_does_not_override_raw_sha(self) -> None:
        research_root = REPOSITORY_ROOT / "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / T3_CANDIDATE.name
            crlf_bytes = T3_CANDIDATE.read_bytes().replace(b"\n", b"\r\n")
            source_path.write_bytes(crlf_bytes)
            self.assertEqual(T3_REJECTED_CRLF_SHA256, _raw_sha256(crlf_bytes))
            self.assertEqual(
                T3_CONTENT_FINGERPRINT,
                bank_content_fingerprint(json.loads(crlf_bytes.decode("utf-8"))["questions"]),
            )
            candidate_path = root / T4_CANDIDATE.name
            with self.assertRaises(ValueError) as ctx:
                build_package_b_tranche4.build_package_b_tranche4(
                    source_path,
                    research_root / "28-PACKAGE-B-TRANCHE4-SEMANTIC-REVIEW.json",
                    candidate_path,
                    root / "reviews",
                    root / "t4-manifest.json",
                )
            self.assertFalse(candidate_path.exists())
            message = str(ctx.exception)
            self.assertTrue("CRLF" in message or "raw-SHA mismatch" in message or "SHA-256" in message)
