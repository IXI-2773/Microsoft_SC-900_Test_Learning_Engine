from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from content_revision_authority import (
    ContentRevisionManifestError,
    RevisionFailureReason,
    canonical_manifest_sha256,
    parse_json_duplicate_safe,
    sha256_file,
)


class ContentRevisionAuthorityPrimitiveTests(unittest.TestCase):
    def test_equivalent_json_key_order_and_whitespace_share_canonical_hash(self) -> None:
        compact = '{"work_id":"SC900","schema_version":1,"edges":[]}'
        reordered = '{"schema_version": 1, "edges": [], "work_id": "SC900"}'
        pretty = """
        {
          "edges": [],
          "work_id": "SC900",
          "schema_version": 1
        }
        """
        hashes = {
            canonical_manifest_sha256(parse_json_duplicate_safe(compact)),
            canonical_manifest_sha256(parse_json_duplicate_safe(reordered)),
            canonical_manifest_sha256(parse_json_duplicate_safe(pretty)),
        }
        self.assertEqual(1, len(hashes))

    def test_stored_payload_sha256_is_excluded_from_self_hash(self) -> None:
        payload = {"schema_version": 1, "work_id": "SC900", "edges": []}
        hashed = dict(payload)
        hashed["payload_sha256"] = "deadbeef"
        self.assertEqual(canonical_manifest_sha256(payload), canonical_manifest_sha256(hashed))

    def _parse_reason(self, raw: str) -> RevisionFailureReason:
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            parse_json_duplicate_safe(raw)
        return ctx.exception.reason

    def test_duplicate_manifest_key_fails_closed(self) -> None:
        raw = '{"schema_version":1,"work_id":"SC900","work_id":"OTHER"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_duplicate_review_authority_key_fails_closed(self) -> None:
        raw = '{"question_id":"q1","question_id":"q2","disposition":"APPROVED_FOR_FULL_CONTINUITY"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_duplicate_bank_authority_key_fails_closed(self) -> None:
        raw = '{"title":"bank","questions":[],"title":"other"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_malformed_json_is_schema_unsupported(self) -> None:
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._parse_reason("{not json"))

    def test_non_object_top_level_manifest_review_and_bank_are_schema_unsupported(self) -> None:
        for raw in ("[]", "null", '"string"', "1", "true"):
            with self.subTest(raw=raw):
                self.assertEqual(
                    RevisionFailureReason.SCHEMA_UNSUPPORTED,
                    self._parse_reason(raw),
                )

    def test_sha256_file_hashes_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"abc\r\n")
            self.assertEqual(hashlib.sha256(b"abc\r\n").hexdigest(), sha256_file(path))


if __name__ == "__main__":
    unittest.main()
