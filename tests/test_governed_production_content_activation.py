from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import TestingEngineApp
from app_constants import MODE_PRACTICE, MODE_SMART_PRACTICE
from content_fingerprint_bridge import (
    DEFAULT_BRIDGE_PATH,
    FingerprintBridgeError,
    canonical_bridge_sha256,
    verify_bridge_artifact,
)
from content_revision_authority import (
    AdmissionStatus,
    RevisionFailureReason,
    canonical_manifest_sha256,
)
from content_revision_registry import (
    AUTHORIZED_CONTENT_REVISION_MANIFESTS,
    history_event_matches_registered_lineage,
    history_events_for_registered_lineage,
    reconstruct_registered_lineage,
)
from fingerprint_identity import (
    ARTIFACT_FINGERPRINT_DOMAIN,
    FINGERPRINT_SCHEMA_VERSION,
    RUNTIME_FINGERPRINT_DOMAIN,
)
from question_bank import load_bank
from question_identity import (
    PROGRESS_CONTENT_EPOCH_VERSION,
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    canonical_question_id,
    question_content_fingerprint,
)
from runtime_persistence import (
    RuntimePersistence,
    supported_revision_transaction_failpoints,
)
from session_store import SESSION_SCHEMA_VERSION, build_session_snapshot, session_file_path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "content_revision_evidence"
TARGET_BANK = "sc900_bank_v8_final_content_correction_002.json"
SOURCE_BANK = "sc900_bank_v8_final.json"
CORRECTION_IDS = (
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


def _blank_answer() -> dict:
    return {
        "selected": [],
        "pending": [],
        "answered": False,
        "flagged": False,
        "suspended": False,
        "last_confidence": "",
        "last_miss_reason": "",
        "recall_ready": False,
        "session_tag": "",
        "smart_primary_role": "",
        "smart_selection_reasons": [],
        "smart_utility": 0.0,
        "smart_utility_breakdown": {},
        "smart_policy_version": "",
        "smart_policy_id": "",
        "smart_concept_key": "",
        "smart_root_cause": "",
        "smart_root_cause_confidence": 0.0,
        "smart_supporting_concepts": [],
        "smart_graph_version": "",
        "smart_information_value": 0.0,
        "smart_information_breakdown": {},
        "smart_question_quality_status": "",
        "smart_question_quality_confidence": 0.0,
        "smart_graph_bottleneck": 0.0,
        "repair_stage": "",
        "repair_concept_key": "",
        "legacy_repair_concept_key": "",
        "prediction_id": "",
        "prediction_snapshot": {},
    }


def _progress(node, records: dict, history: list | None = None) -> dict:
    return {
        "version": 3,
        "progress_identity_version": PROGRESS_IDENTITY_VERSION,
        "question_identity": PROGRESS_IDENTITY_KIND,
        "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
        "fingerprint_algorithm": "sha256",
        "loader_contract_version": 1,
        "bank_node_id": node.bank_node_id,
        "bank_fingerprint": node.runtime_bank_fingerprint,
        "question_content_fingerprints": {qid: node.runtime_by_question[qid] for qid in records},
        "questions": copy.deepcopy(records),
        "history": copy.deepcopy(history or []),
        "content_revision_lineage": [],
    }


class GovernedProductionContentActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = verify_bridge_artifact(DEFAULT_BRIDGE_PATH, repo_root=ROOT)
        cls.lineage = reconstruct_registered_lineage()
        cls.questions = {name: load_bank(ROOT / name)["questions"] for name in cls.lineage.bank_filenames}
        cls.questions_by_id = {
            name: {canonical_question_id(row): row for row in rows} for name, rows in cls.questions.items()
        }

    def test_registry_pins_exact_manifest_hashes(self):
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        for relative, expected in AUTHORIZED_CONTENT_REVISION_MANIFESTS.items():
            payload = json.loads((EVIDENCE / relative).read_text(encoding="utf-8"))
            self.assertEqual(expected, canonical_manifest_sha256(payload))
            self.assertEqual(expected, payload["payload_sha256"])

    def test_registry_failure_modes_fail_closed(self):
        missing = dict(AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        missing["manifests/missing.json"] = "a" * 64
        missing_result = reconstruct_registered_lineage(registry=missing)
        self.assertEqual(AdmissionStatus.FAIL, missing_result.status)
        self.assertIn(RevisionFailureReason.REGISTRY_HASH_MISMATCH, missing_result.reasons)

        wrong = dict(AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        first = next(iter(wrong))
        wrong[first] = "b" * 64
        wrong_result = reconstruct_registered_lineage(registry=wrong)
        self.assertEqual(AdmissionStatus.FAIL, wrong_result.status)
        self.assertIn(RevisionFailureReason.REGISTRY_HASH_MISMATCH, wrong_result.reasons)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifests = root / "manifests"
            manifests.mkdir()
            payloads = []
            for source, target in (
                ("left.json", "middle.json"),
                ("left.json", "other.json"),
            ):
                payload = {
                    "manifest_kind": "unsupported",
                    "source_bank": {"filename": source},
                    "target_bank": {"filename": target},
                }
                digest = canonical_manifest_sha256(payload)
                name = f"{target}.json"
                (manifests / name).write_text(json.dumps(payload), encoding="utf-8")
                payloads.append((f"manifests/{name}", digest))
            duplicate = reconstruct_registered_lineage(
                evidence_root=root,
                registry=dict(payloads),
            )
            self.assertEqual(AdmissionStatus.FAIL, duplicate.status)
            self.assertIn(RevisionFailureReason.LINEAGE_CONFLICT, duplicate.reasons)

            shared_target = {
                "manifest_kind": "unsupported",
                "source_bank": {"filename": "alpha.json"},
                "target_bank": {"filename": "shared.json"},
            }
            other_source = {
                "manifest_kind": "unsupported",
                "source_bank": {"filename": "beta.json"},
                "target_bank": {"filename": "shared.json"},
            }
            shared_pairs = []
            for index, payload in enumerate((shared_target, other_source)):
                digest = canonical_manifest_sha256(payload)
                name = f"shared-{index}.json"
                (manifests / name).write_text(json.dumps(payload), encoding="utf-8")
                shared_pairs.append((f"manifests/{name}", digest))
            duplicate_target = reconstruct_registered_lineage(
                evidence_root=root,
                registry=dict(shared_pairs),
            )
            self.assertEqual(AdmissionStatus.FAIL, duplicate_target.status)
            self.assertIn(RevisionFailureReason.LINEAGE_CONFLICT, duplicate_target.reasons)

            single = {
                "manifest_kind": "unsupported-kind",
                "source_bank": {"filename": "source.json"},
                "target_bank": {"filename": "target.json"},
            }
            digest = canonical_manifest_sha256(single)
            (manifests / "single.json").write_text(json.dumps(single), encoding="utf-8")
            unsupported = reconstruct_registered_lineage(
                evidence_root=root,
                registry={"manifests/single.json": digest},
                bank_dir=ROOT,
            )
            self.assertEqual(AdmissionStatus.FAIL, unsupported.status)

        self.assertIsNone(reconstruct_registered_lineage(registry={}))

    def test_complete_lineage_is_ten_hops_and_299_transitions(self):
        self.assertEqual(11, len(self.lineage.bank_filenames))
        self.assertEqual(SOURCE_BANK, self.lineage.bank_filenames[0])
        self.assertEqual(TARGET_BANK, self.lineage.bank_filenames[-1])
        self.assertEqual(10, len(self.lineage.revisions))
        edge_count = 0
        for index, revision in enumerate(self.lineage.revisions):
            self.assertEqual(self.lineage.bank_filenames[index], revision.source_bank_filename)
            self.assertEqual(self.lineage.bank_filenames[index + 1], revision.target_bank_filename)
            edge_count += len(revision.edges)
            if index:
                self.assertEqual(
                    self.lineage.revisions[index - 1].target_node.bank_node_id,
                    revision.source_node.bank_node_id,
                )
        self.assertEqual(299, edge_count)
        self.assertEqual(
            [node.bank_filename for node in self.bridge.nodes],
            list(self.lineage.bank_filenames),
        )

    def test_dual_domain_bridge_authority(self):
        bridge_bytes = hashlib_file(DEFAULT_BRIDGE_PATH)
        self.assertEqual("144a8268ad17d5eefe2ca78d16502512833e14f1951143d35799efb59ae1e847", bridge_bytes)
        self.assertEqual("fb9bb7f339f360e52aacb51372c5cda01545f3e19fb3914ba7cc15b503f7a379", self.bridge.payload_sha256)
        node = self.lineage.revisions[0].source_node
        qid = next(iter(node.artifact_by_question))
        self.assertEqual(
            node.runtime_by_question[qid],
            self.bridge.translate_question(
                node.bank_node_id,
                qid,
                ARTIFACT_FINGERPRINT_DOMAIN,
                node.artifact_by_question[qid],
            ),
        )
        with self.assertRaises(FingerprintBridgeError):
            self.bridge.translate_question(node.bank_node_id, qid, "other-domain", node.artifact_by_question[qid])
        with self.assertRaises(FingerprintBridgeError):
            self.bridge.translate_question(
                node.bank_node_id,
                qid,
                ARTIFACT_FINGERPRINT_DOMAIN,
                node.runtime_by_question[qid],
            )
        with self.assertRaises(FingerprintBridgeError):
            self.bridge.node_for_filename("not-a-bank.json")
        tampered = json.loads(DEFAULT_BRIDGE_PATH.read_text(encoding="utf-8"))
        tampered["nodes"][0]["questions"][0]["runtime_fingerprint"] = "0" * 64
        tampered["payload_sha256"] = canonical_bridge_sha256(tampered)
        from content_fingerprint_bridge import FingerprintBridge

        with self.assertRaises(FingerprintBridgeError):
            FingerprintBridge.from_payload(tampered)

    def test_progress_continuity_across_lineage_families(self):
        stable = self._stable_question_id()
        changed = self.lineage.revisions[0].edges[0].question_id
        records = {
            stable: {"attempts": 4, "correct_count": 3, "wrong_count": 1, "flagged": True},
            changed: {"attempts": 2, "correct_count": 1, "wrong_count": 1, "flagged": False},
            "sc900_mlc_q118": {"attempts": 6, "correct_count": 4, "wrong_count": 2, "flagged": True},
        }
        families = {
            SOURCE_BANK: self.lineage.revisions,
            "sc900_bank_v8_length_rebalanced_t2.json": self.lineage.revisions[2:],
            "sc900_bank_v8_length_rebalanced_t5.json": self.lineage.revisions[5:],
            "sc900_bank_v8_content_correction_001.json": self.lineage.revisions[6:],
            "sc900_bank_v8_explanation_tranche_1.json": self.lineage.revisions[7:],
        }
        for source_name, hops in families.items():
            with self.subTest(source=source_name):
                node = hops[0].source_node
                included = {
                    qid: records[qid]
                    for qid in records
                    if qid == stable or any(edge.question_id == qid for hop in hops for edge in hop.edges)
                }
                if "sc900_mlc_q118" in node.runtime_by_question and source_name != SOURCE_BANK:
                    included.setdefault("sc900_mlc_q118", records["sc900_mlc_q118"])
                migrated = self._migrate(source_name, hops, _progress(node, included))
                self.assertEqual(hops[-1].target_node.runtime_bank_fingerprint, migrated["bank_fingerprint"])
                self.assertEqual(included[stable]["attempts"], migrated["questions"][stable]["attempts"])

    def test_q118_repair_target_progress_is_not_rewritten(self):
        node = self.lineage.revisions[-1].target_node
        record = {"attempts": 9, "correct_count": 7, "wrong_count": 2, "flagged": True}
        payload = _progress(node, {"sc900_mlc_q118": record})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_data = root / "user"
            banks = root / "banks"
            user_data.mkdir()
            banks.mkdir()
            bank_path = banks / TARGET_BANK
            bank_path.write_bytes(b"unused-bank-bytes")
            host = TestingEngineApp.__new__(TestingEngineApp)
            host.bank_path = bank_path
            host.user_data_dir = user_data
            host.progress_path = host.progress_file_for_bank(bank_path)
            host.persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            host.progress_write_blocked = False
            host.progress_path.write_text(json.dumps(payload), encoding="utf-8")
            before = host.progress_path.read_bytes()
            self.assertFalse(host._migrate_registered_lineage(self.lineage))
            self.assertFalse(host.progress_write_blocked)
            self.assertEqual(before, host.progress_path.read_bytes())
            self.assertEqual(record, json.loads(before)["questions"]["sc900_mlc_q118"])
            self.assertFalse(any(root.glob(".sc900_revision_*")))

    def test_correction_resets_governed_ids_once_and_preserves_others(self):
        stable = self._stable_question_id()
        node = self.lineage.revisions[0].source_node
        records = {stable: {"attempts": 3, "correct_count": 3, "wrong_count": 0, "flagged": False}}
        for qid in CORRECTION_IDS:
            records[qid] = {"attempts": 8, "correct_count": 5, "wrong_count": 3, "flagged": True, "suspended": True}
        history = [
            {
                "question_id": "sc900_mlc_q118",
                "question_content_fingerprint": node.runtime_by_question["sc900_mlc_q118"],
            }
        ]
        migrated = self._migrate(SOURCE_BANK, self.lineage.revisions, _progress(node, records, history))
        for qid in CORRECTION_IDS:
            self.assertEqual(0, migrated["questions"][qid]["attempts"], qid)
            self.assertTrue(migrated["questions"][qid]["flagged"], qid)
        self.assertEqual(3, migrated["questions"][stable]["attempts"])
        self.assertEqual([], [event for event in migrated["history"] if event.get("question_id") == "sc900_mlc_q118"])
        self.assertEqual(
            1, len([event for event in migrated["quarantined_history"] if event.get("question_id") == "sc900_mlc_q118"])
        )
        correction_rows = [
            row
            for row in migrated["content_revision_lineage"]
            if row["question_id"] == "sc900_mlc_q118"
            and row["manifest_sha256"] == self.lineage.revisions[5].manifest_sha256
        ]
        self.assertEqual(1, len(correction_rows))

    def test_explanation_continuity_does_not_reset_q118_again(self):
        tranche = self.lineage.revisions[7]
        node = tranche.source_node
        record = {"attempts": 4, "correct_count": 3, "wrong_count": 1, "flagged": True}
        migrated = self._migrate(
            tranche.source_bank_filename,
            (tranche,),
            _progress(node, {"sc900_mlc_q118": record}),
        )
        self.assertEqual(record, migrated["questions"]["sc900_mlc_q118"])
        self.assertEqual(tranche.target_node.runtime_bank_fingerprint, migrated["bank_fingerprint"])

    def test_sessions_upgrade_schema_and_preserve_queue(self):
        for mode in (MODE_PRACTICE, MODE_SMART_PRACTICE):
            with self.subTest(mode=mode):
                payload = self._migrate_session(mode, schema_version=4)
                self.assertEqual(SESSION_SCHEMA_VERSION, payload["schema_version"])
                self.assertEqual(5, payload["schema_version"])
                self.assertEqual(1, payload["current_index"])
                self.assertEqual(payload["question_ids"], payload["restore_question_ids"])
                self.assertEqual(
                    self.lineage.revisions[-1].target_node.runtime_bank_fingerprint,
                    payload["bank_fingerprint"],
                )

    def test_history_domains_match_and_unknown_is_filtered(self):
        revision = self.lineage.revisions[0]
        qid = revision.edges[0].question_id
        source = revision.source_node
        target_question = self.questions_by_id[TARGET_BANK][qid]
        events = [
            {"question_id": qid, "question_content_fingerprint": source.runtime_by_question[qid]},
            {"question_id": qid, "question_content_fingerprint": source.artifact_by_question[qid]},
            {"question_id": qid, "question_content_fingerprint": "0" * 64},
        ]
        node = self.lineage.revisions[0].source_node
        migrated = self._migrate(
            SOURCE_BANK,
            self.lineage.revisions,
            _progress(node, {qid: {"attempts": 1, "correct_count": 1, "wrong_count": 0}}, events),
        )
        self.assertEqual(events, migrated["history"])
        self.assertEqual(question_content_fingerprint(target_question), migrated["question_content_fingerprints"][qid])
        self.assertTrue(history_event_matches_registered_lineage(events[0], target_question, self.lineage.revisions))
        self.assertTrue(history_event_matches_registered_lineage(events[1], target_question, self.lineage.revisions))
        self.assertFalse(history_event_matches_registered_lineage(events[2], target_question, self.lineage.revisions))
        matched = history_events_for_registered_lineage({qid: events}, target_question, self.lineage.revisions)
        self.assertEqual(events[:2], matched)

    def test_unknown_current_bank_fails_before_target_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, target, _session_source, _session_target = self._paths(root)
            payload = _progress(
                self.lineage.revisions[0].source_node,
                {self._stable_question_id(): {"attempts": 1, "correct_count": 1, "wrong_count": 0}},
            )
            payload["bank_fingerprint"] = "f" * 64
            source.write_text(json.dumps(payload), encoding="utf-8")
            before = source.read_bytes()
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[],
                revisions=self.lineage.revisions,
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(receipt)
            self.assertIsNotNone(error)
            self.assertFalse(target.exists())
            self.assertEqual(before, source.read_bytes())
            self.assertFalse(any(root.glob(".sc900_revision_*.lock")))

    def test_atomicity_failpoints_conflict_tamper_and_idempotence(self):
        failpoints = supported_revision_transaction_failpoints(2)
        self.assertEqual(
            (
                "after_transform",
                "after_stage_0",
                "after_stage_1",
                "after_staging",
                "before_journal",
                "after_journal",
                "before_replace_0",
                "after_replace_0",
                "before_replace_1",
                "after_replace_1",
                "before_receipt",
                "after_receipt",
            ),
            failpoints,
        )
        for failpoint in failpoints:
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                persistence = RuntimePersistence(root / "checkpoints", root / "backups")
                source, target, session_source, session_target = self._write_fixture(root)
                receipt, error = persistence.migrate_lineage_state_transaction(
                    progress_source_path=source,
                    progress_target_path=target,
                    session_pairs=[(session_source, session_target)],
                    revisions=self.lineage.revisions[:1],
                    questions_by_bank=self.questions,
                    migrated_at="2026-09-22T00:00:00",
                    failpoint=failpoint,
                )
                self.assertIsNone(receipt)
                self.assertIsNotNone(error)
                recovered, recovery_error = persistence.migrate_lineage_state_transaction(
                    progress_source_path=source,
                    progress_target_path=target,
                    session_pairs=[(session_source, session_target)],
                    revisions=self.lineage.revisions[:1],
                    questions_by_bank=self.questions,
                    migrated_at="2026-09-22T00:00:00",
                )
                self.assertIsNone(recovery_error)
                self.assertTrue(recovered["committed"])
                self.assertTrue(target.exists())
                self.assertTrue(session_target.exists())
                self.assertFalse(source.exists())
                self.assertFalse(session_source.exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            source, target, session_source, session_target = self._write_fixture(root)
            target.write_text('{"conflict": true}\n', encoding="utf-8")
            receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(receipt)
            self.assertIsNotNone(error)
            self.assertTrue(source.exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            source, target, session_source, session_target = self._write_fixture(root)
            receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
                failpoint="after_journal",
            )
            self.assertIsNone(receipt)
            identity = persistence._lineage_transaction_identity(self.lineage.revisions[:1])
            journal_path = root / f".sc900_revision_{identity['migration_id']}.journal.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["bridge_sha256"] = "0" * 64
            journal_path.write_text(json.dumps(journal), encoding="utf-8")
            before = source.read_bytes()
            recovered, recovery_error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(recovered)
            self.assertIsNotNone(recovery_error)
            self.assertEqual(before, source.read_bytes())
            self.assertFalse(target.exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            source, target, session_source, session_target = self._write_fixture(root)
            receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(error)
            repeated, repeat_error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:01:00",
            )
            self.assertIsNone(repeat_error)
            self.assertEqual(receipt, repeated)
            identity = persistence._lineage_transaction_identity(self.lineage.revisions[:1])
            receipt_path = root / f".sc900_revision_{identity['migration_id']}.receipt.json"
            tampered = json.loads(receipt_path.read_text(encoding="utf-8"))
            tampered["committed"] = False
            receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
            rejected, reject_error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[(session_source, session_target)],
                revisions=self.lineage.revisions[:1],
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:02:00",
            )
            self.assertIsNone(rejected)
            self.assertIsNotNone(reject_error)

    def _stable_question_id(self) -> str:
        nodes = [self.lineage.revisions[0].source_node, *[revision.target_node for revision in self.lineage.revisions]]
        changed = {edge.question_id for revision in self.lineage.revisions for edge in revision.edges}
        for qid in nodes[0].runtime_by_question:
            if qid in changed:
                continue
            fingerprint = nodes[0].runtime_by_question[qid]
            if all(node.runtime_by_question[qid] == fingerprint for node in nodes):
                return qid
        self.fail("expected an unchanged question")

    def _migrate(self, source_name: str, hops, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / f"{Path(source_name).stem}_progress.json"
            target = root / f"{Path(hops[-1].target_bank_filename).stem}_progress.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            _receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[],
                revisions=hops,
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(error)
            migrated = json.loads(target.read_text(encoding="utf-8"))
            _again, again_error = persistence.migrate_lineage_state_transaction(
                progress_source_path=source,
                progress_target_path=target,
                session_pairs=[],
                revisions=hops,
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(again_error)
            return migrated

    def _migrate_session(self, mode: str, *, schema_version: int) -> dict:
        questions = self.questions[SOURCE_BANK][:3]
        ids = [canonical_question_id(row) for row in questions]
        source_node = self.lineage.revisions[0].source_node
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=SOURCE_BANK,
            mode=mode,
            builder_context={"mode": mode, "count": "3", "source_label": "All"},
            source_label="All",
            question_numbers=[row["question_number"] for row in questions],
            restore_question_numbers=[row["question_number"] for row in questions],
            session_base_question_count=3,
            session_question_limit=3,
            current_index=1,
            elapsed_seconds=12,
            exam_reveal=True,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[_blank_answer() for _ in questions],
            bank_fingerprint=source_node.runtime_bank_fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
        )
        if schema_version == 4:
            snapshot["schema_version"] = 4
            for key in (
                "fingerprint_schema_version",
                "fingerprint_domain",
                "fingerprint_algorithm",
                "loader_contract_version",
                "bank_node_id",
            ):
                snapshot.pop(key, None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = session_file_path(
                root,
                ROOT / SOURCE_BANK,
                mode,
                [row["question_number"] for row in questions],
                bank_fingerprint=source_node.runtime_bank_fingerprint,
                question_ids=ids,
                builder_context_fingerprint=snapshot["builder_context_fingerprint"],
            )
            target = session_file_path(
                root,
                ROOT / TARGET_BANK,
                mode,
                [row["question_number"] for row in questions],
                bank_fingerprint=self.lineage.revisions[-1].target_node.runtime_bank_fingerprint,
                question_ids=ids,
                builder_context_fingerprint=snapshot["builder_context_fingerprint"],
            )
            source.write_text(json.dumps(snapshot), encoding="utf-8")
            progress_source = root / "source_progress.json"
            progress_target = root / "target_progress.json"
            stable = self._stable_question_id()
            progress_source.write_text(
                json.dumps(_progress(source_node, {stable: {"attempts": 1, "correct_count": 1, "wrong_count": 0}})),
                encoding="utf-8",
            )
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            _receipt, error = persistence.migrate_lineage_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(source, target)],
                revisions=self.lineage.revisions,
                questions_by_bank=self.questions,
                migrated_at="2026-09-22T00:00:00",
            )
            self.assertIsNone(error)
            return json.loads(target.read_text(encoding="utf-8"))

    def _paths(self, root: Path):
        source = root / "sc900_bank_v8_final_progress.json"
        target = root / "sc900_bank_v8_explanation_q118_repair_progress.json"
        session_source = root / "sc900_bank_v8_final_practice_session_1_src.json"
        session_target = root / "sc900_bank_v8_explanation_q118_repair_practice_session_1_dst.json"
        return source, target, session_source, session_target

    def _write_fixture(self, root: Path):
        source, target, session_source, session_target = self._paths(root)
        hop = self.lineage.revisions[0]
        qid = hop.edges[0].question_id
        source.write_text(
            json.dumps(_progress(hop.source_node, {qid: {"attempts": 2, "correct_count": 1, "wrong_count": 1}})),
            encoding="utf-8",
        )
        questions = self.questions[hop.source_bank_filename]
        question = self.questions_by_id[hop.source_bank_filename][qid]
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=hop.source_bank_filename,
            mode=MODE_PRACTICE,
            builder_context={"mode": MODE_PRACTICE, "count": "1", "source_label": "All"},
            source_label="All",
            question_numbers=[question["question_number"]],
            restore_question_numbers=[question["question_number"]],
            session_base_question_count=1,
            session_question_limit=1,
            current_index=0,
            elapsed_seconds=1,
            exam_reveal=True,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[_blank_answer()],
            bank_fingerprint=hop.source_node.runtime_bank_fingerprint,
            question_ids=[qid],
            restore_question_ids=[qid],
        )
        del questions
        session_source.write_text(json.dumps(snapshot), encoding="utf-8")
        return source, target, session_source, session_target


def hashlib_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
