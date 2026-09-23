from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import cert_config
from cand01r3_protocol import build_protocol, default_production_ledger_path
from content_fingerprint_bridge import DEFAULT_BRIDGE_PATH, FROZEN_BANK_FILENAMES, verify_bridge_artifact
from content_revision_registry import (
    AUTHORIZED_CONTENT_REVISION_MANIFESTS,
    FROZEN_BRIDGE_BANKS,
    reconstruct_registered_lineage,
)
from tools.bank_warning_policy import (
    GOVERNED_ACTIVE_BANK_FILENAME,
    GOVERNED_ACTIVE_BANK_SHA256,
    evaluate_production_warnings,
)
from tools.validate_bank import validate_bank

ROOT = Path(__file__).resolve().parents[1]
TERMINAL_BANK = "sc900_bank_v8_final_content_correction_002.json"
TERMINAL_SHA256 = "f97f76591ebb41dd1b92ca5623c6f040b2d9a75ca6f7f1d5b0ebd9adf371581f"
BRIDGE_PAYLOAD_SHA256 = "fb9bb7f339f360e52aacb51372c5cda01545f3e19fb3914ba7cc15b503f7a379"
BRIDGE_FILE_SHA256 = "144a8268ad17d5eefe2ca78d16502512833e14f1951143d35799efb59ae1e847"
CAND_PROTOCOL_SHA256 = "51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72"
TERMINAL_MANIFESTS = (
    "manifests/sc900_explanation_final_454_repair.json",
    "manifests/sc900_final_two_question_content_correction.json",
)


class TerminalTwoHopActivationTests(unittest.TestCase):
    def test_terminal_lineage_is_the_single_production_bridge(self):
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(list(TERMINAL_MANIFESTS), list(AUTHORIZED_CONTENT_REVISION_MANIFESTS)[-2:])
        self.assertEqual(TERMINAL_BANK, cert_config.QUESTION_BANK_FILENAME)
        self.assertEqual(11, len(FROZEN_BANK_FILENAMES))
        self.assertEqual(11, len(FROZEN_BRIDGE_BANKS))
        self.assertEqual(TERMINAL_BANK, FROZEN_BANK_FILENAMES[-1])

        bridge = verify_bridge_artifact(DEFAULT_BRIDGE_PATH, repo_root=ROOT)
        self.assertEqual(11, len(bridge.nodes))
        self.assertEqual(BRIDGE_PAYLOAD_SHA256, bridge.payload_sha256)
        self.assertEqual(BRIDGE_FILE_SHA256, hashlib.sha256(DEFAULT_BRIDGE_PATH.read_bytes()).hexdigest())

        lineage = reconstruct_registered_lineage()
        self.assertEqual(11, len(lineage.bank_filenames))
        self.assertEqual(10, len(lineage.revisions))
        self.assertEqual(299, sum(len(revision.edges) for revision in lineage.revisions))
        self.assertEqual(1, len({revision.bridge_sha256 for revision in lineage.revisions}))
        self.assertEqual(list(FROZEN_BANK_FILENAMES), list(lineage.bank_filenames))
        self.assertEqual(TERMINAL_BANK, lineage.bank_filenames[-1])

    def test_terminal_warning_policy_matches_the_active_bank(self):
        bank = ROOT / TERMINAL_BANK
        validated = validate_bank(bank)
        decision = evaluate_production_warnings(bank, validated["warnings"])
        self.assertEqual(TERMINAL_BANK, GOVERNED_ACTIVE_BANK_FILENAME)
        self.assertEqual(TERMINAL_SHA256, GOVERNED_ACTIVE_BANK_SHA256)
        self.assertEqual(TERMINAL_SHA256, decision.bank_sha256)
        self.assertTrue(decision.governed)
        self.assertTrue(decision.passed)
        self.assertEqual((), decision.failures)
        self.assertEqual(0, decision.unexpected_warning_count)

    def test_cand_protocol_hash_is_unchanged(self):
        self.assertEqual(CAND_PROTOCOL_SHA256, build_protocol()["protocol_sha256"])
        ledger = default_production_ledger_path()
        self.assertEqual("measurement", ledger.parent.name)
        self.assertTrue(ledger.name.endswith(".jsonl"))
