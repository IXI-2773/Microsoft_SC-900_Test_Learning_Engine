from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import cert_config
from app_constants import MODE_PRACTICE, MODE_SMART_PRACTICE
from cand01r3_runtime import partition_cache_identity
from content_fingerprint_bridge import (
    DEFAULT_BRIDGE_PATH,
    FROZEN_BANK_FILENAMES,
    BridgeFailureReason,
    FingerprintBridge,
    FingerprintBridgeError,
    RuntimeBoundRevision,
    _verify_reviewed_projection_delta,
    build_bridge_payload,
    canonical_bridge_sha256,
    history_event_matches_runtime_bound_revision,
    history_events_for_runtime_bound_revision,
    verify_bridge_artifact,
)
from content_revision_authority import AdmissionStatus, canonical_manifest_sha256
from content_revision_registry import (
    AUTHORIZED_CONTENT_REVISION_MANIFESTS,
    resolve_registered_revision_for_target,
    runtime_bound_revision_for_admission,
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
    bank_content_fingerprint,
    canonical_question_id,
    migrate_progress_content_epoch,
    question_content_fingerprint,
    register_progress_identity_bank,
    registered_progress_identity_bank,
)
from runtime_persistence import (
    RuntimePersistence,
    _migrate_progress_for_revision,
    _migrate_session_for_revision,
)
from session_store import SESSION_SCHEMA_VERSION, build_session_snapshot, migrate_session_snapshot
from smart_practice_core import smart_practice_ordering_seed

ROOT = Path(__file__).resolve().parents[1]

MANIFEST_NAMES = (
    "sc900_answer_length_rebalance_t1.json",
    "sc900_answer_length_rebalance_t2.json",
    "sc900_answer_length_rebalance_t3.json",
    "sc900_answer_length_rebalance_t4.json",
    "sc900_answer_length_rebalance_t5.json",
    "sc900_content_correction_001.json",
    "sc900_explanation_tranche_1.json",
    "sc900_explanation_q118_repair_001.json",
)
TARGET_NAMES = FROZEN_BANK_FILENAMES[1:]


def _registry() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in MANIFEST_NAMES:
        relative = f"manifests/{name}"
        payload = json.loads((ROOT / "content_revision_evidence" / relative).read_text(encoding="utf-8"))
        result[relative] = canonical_manifest_sha256(payload)
    return result


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


class FingerprintBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = verify_bridge_artifact(DEFAULT_BRIDGE_PATH, repo_root=ROOT)
        cls.registry = _registry()

    def test_fp001_frozen_nine_bank_bridge_reproduces(self):
        self.assertEqual(9, len(self.bridge.nodes))
        self.assertEqual(list(FROZEN_BANK_FILENAMES), [node.bank_filename for node in self.bridge.nodes])
        regenerated = build_bridge_payload(ROOT)
        self.assertEqual(self.bridge.payload_sha256, canonical_bridge_sha256(regenerated))
        self.assertEqual(
            "875ba756392033279c8ab86abbbed287ca290ba780acd7852fe359b80752c8a6",
            self.bridge.nodes[-1].artifact_bank_fingerprint,
        )
        self.assertEqual(
            "10996a876d717d2bb60e44dd94688b022806a9a154cb23e3e88025ddf318c65f",
            self.bridge.nodes[-1].runtime_bank_fingerprint,
        )

    def test_fp002_only_reviewed_projection_delta_and_mapping_counts(self):
        mapping_count = sum(node.question_count for node in self.bridge.nodes)
        pairs = {
            (node.artifact_by_question[qid], node.runtime_by_question[qid])
            for node in self.bridge.nodes
            for qid in node.artifact_by_question
        }
        self.assertEqual(4086, mapping_count)
        self.assertEqual(745, len(pairs))
        self.assertTrue(
            all(
                node.artifact_by_question[qid] != node.runtime_by_question[qid]
                for node in self.bridge.nodes
                for qid in node.artifact_by_question
            )
        )

    def test_fp003_exact_node_question_translation_is_bidirectional(self):
        for node in self.bridge.nodes:
            for qid, artifact_fp in node.artifact_by_question.items():
                runtime_fp = node.runtime_by_question[qid]
                self.assertEqual(
                    runtime_fp,
                    self.bridge.translate_question(node.bank_node_id, qid, ARTIFACT_FINGERPRINT_DOMAIN, artifact_fp),
                )
                self.assertEqual(
                    artifact_fp,
                    self.bridge.translate_question(node.bank_node_id, qid, RUNTIME_FINGERPRINT_DOMAIN, runtime_fp),
                )

    def test_fp004_unknown_and_wrong_domain_fail_closed(self):
        node = self.bridge.nodes[0]
        qid = next(iter(node.artifact_by_question))
        with self.assertRaises(FingerprintBridgeError) as cm:
            self.bridge.translate_question(node.bank_node_id, qid, "unknown", node.artifact_by_question[qid])
        self.assertEqual(BridgeFailureReason.UNKNOWN_DOMAIN, cm.exception.reason)
        with self.assertRaises(FingerprintBridgeError):
            self.bridge.translate_question(
                node.bank_node_id,
                qid,
                ARTIFACT_FINGERPRINT_DOMAIN,
                node.runtime_by_question[qid],
            )
        with self.assertRaises(FingerprintBridgeError):
            self.bridge.node_for_runtime_bank_fingerprint("0" * 64)

    def test_fp005_progress_epoch_v1_upgrades_to_runtime_v2_without_record_loss(self):
        questions = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"]
        question = questions[0]
        qid = canonical_question_id(question)
        bank_fp = bank_content_fingerprint(questions)
        qfp = question_content_fingerprint(question)
        old = {
            "version": 3,
            "progress_identity_version": PROGRESS_IDENTITY_VERSION,
            "question_identity": PROGRESS_IDENTITY_KIND,
            "progress_content_epoch_version": 1,
            "bank_fingerprint": bank_fp,
            "question_content_fingerprints": {qid: qfp},
            "questions": {qid: {"attempts": 7, "wrong_count": 2}},
            "history": [],
        }
        migrated, changed = migrate_progress_content_epoch(old, questions)
        self.assertTrue(changed)
        self.assertEqual(7, migrated["questions"][qid]["attempts"])
        self.assertEqual(PROGRESS_CONTENT_EPOCH_VERSION, migrated["progress_content_epoch_version"])
        self.assertEqual(FINGERPRINT_SCHEMA_VERSION, migrated["fingerprint_schema_version"])
        self.assertEqual(RUNTIME_FINGERPRINT_DOMAIN, migrated["fingerprint_domain"])
        self.assertEqual(self.bridge.nodes[0].bank_node_id, migrated["bank_node_id"])

    def test_fp006_fp007_all_native_and_registry_admissions_have_runtime_binding(self):
        edge_count = 0
        for target in TARGET_NAMES:
            result = resolve_registered_revision_for_target(ROOT / target, registry=self.registry)
            self.assertIsNotNone(result)
            self.assertEqual(AdmissionStatus.PASS, result.status)
            self.assertIsNotNone(result.admitted)
            bound = runtime_bound_revision_for_admission(result)
            self.assertIsInstance(bound, RuntimeBoundRevision)
            self.assertEqual(target, bound.target_bank_filename)
            self.assertEqual(
                bound.target_node.runtime_bank_fingerprint,
                bound.target_bank_content_fingerprint,
            )
            edge_count += len(bound.edges)
        self.assertEqual(291, edge_count)

    def test_fp008_fp009_runtime_progress_crosses_all_eight_governed_edges(self):
        for target in TARGET_NAMES:
            result = resolve_registered_revision_for_target(ROOT / target, registry=self.registry)
            bound = runtime_bound_revision_for_admission(result)
            self.assertIsNotNone(bound)
            edge = bound.edges[0]
            raw_edge = bound.artifact_edge(edge.question_id)
            source_record = {
                "attempts": 3,
                "correct_count": 2,
                "wrong_count": 1,
                "flagged": True,
            }
            payload = {
                "version": 3,
                "progress_identity_version": PROGRESS_IDENTITY_VERSION,
                "question_identity": PROGRESS_IDENTITY_KIND,
                "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
                "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
                "fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
                "fingerprint_algorithm": "sha256",
                "loader_contract_version": 1,
                "bank_node_id": bound.source_node.bank_node_id,
                "bank_fingerprint": bound.source_node.runtime_bank_fingerprint,
                "question_content_fingerprints": {edge.question_id: edge.from_content_fingerprint},
                "questions": {edge.question_id: copy.deepcopy(source_record)},
                "history": [],
                "content_revision_lineage": [],
            }
            target_questions = load_bank(ROOT / target)["questions"]
            migrated = _migrate_progress_for_revision(payload, target_questions, bound, "2026-09-22T00:00:00")
            self.assertEqual(bound.target_node.runtime_bank_fingerprint, migrated.payload["bank_fingerprint"])
            self.assertEqual(
                edge.to_content_fingerprint,
                migrated.payload["question_content_fingerprints"][edge.question_id],
            )
            row = migrated.payload["content_revision_lineage"][-1]
            self.assertEqual(raw_edge.from_content_fingerprint, row["from_fingerprint"])
            self.assertEqual(raw_edge.to_content_fingerprint, row["to_fingerprint"])

    def test_fp010_session_v4_upgrades_to_v5_without_signature_change(self):
        questions = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"][:3]
        ids = [canonical_question_id(row) for row in questions]
        fp = bank_content_fingerprint(load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"])
        v5 = build_session_snapshot(
            app_version="test",
            bank_file=FROZEN_BANK_FILENAMES[0],
            mode=MODE_PRACTICE,
            builder_context={"mode": MODE_PRACTICE, "count": "3", "source_label": "All"},
            source_label="All",
            question_numbers=[row["question_number"] for row in questions],
            restore_question_numbers=[row["question_number"] for row in questions],
            session_base_question_count=3,
            session_question_limit=3,
            current_index=1,
            elapsed_seconds=11,
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
            bank_fingerprint=fp,
            question_ids=ids,
            restore_question_ids=ids,
        )
        v4 = copy.deepcopy(v5)
        v4["schema_version"] = 4
        for key in (
            "fingerprint_schema_version",
            "fingerprint_domain",
            "fingerprint_algorithm",
            "loader_contract_version",
            "bank_node_id",
        ):
            v4.pop(key, None)
        original_sig = v4["session_signature"]
        upgraded = migrate_session_snapshot(
            v4,
            MODE_PRACTICE,
            [row["question_number"] for row in questions],
            bank_fingerprint=fp,
            question_ids=ids,
            restore_question_ids=ids,
            available_question_ids=ids,
        )
        self.assertEqual(SESSION_SCHEMA_VERSION, upgraded["schema_version"])
        self.assertEqual(original_sig, upgraded["session_signature"])
        self.assertEqual(RUNTIME_FINGERPRINT_DOMAIN, upgraded["fingerprint_domain"])

    def test_fp021_v5_wrong_domain_is_rejected(self):
        questions = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"][:2]
        all_questions = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"]
        ids = [canonical_question_id(row) for row in questions]
        fp = bank_content_fingerprint(all_questions)
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=FROZEN_BANK_FILENAMES[0],
            mode=MODE_PRACTICE,
            builder_context={"mode": MODE_PRACTICE, "count": "2", "source_label": "All"},
            source_label="All",
            question_numbers=[row["question_number"] for row in questions],
            restore_question_numbers=[row["question_number"] for row in questions],
            session_base_question_count=2,
            session_question_limit=2,
            current_index=0,
            elapsed_seconds=0,
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
            bank_fingerprint=fp,
            question_ids=ids,
            restore_question_ids=ids,
        )
        snapshot["fingerprint_domain"] = ARTIFACT_FINGERPRINT_DOMAIN
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [row["question_number"] for row in questions],
                bank_fingerprint=fp,
                question_ids=ids,
                restore_question_ids=ids,
                available_question_ids=ids,
            )

    def test_fp018_fp024_tampered_bridge_and_duplicate_mapping_fail_closed(self):
        payload = json.loads(DEFAULT_BRIDGE_PATH.read_text(encoding="utf-8"))
        tampered = copy.deepcopy(payload)
        tampered["nodes"][0]["questions"][0]["runtime_fingerprint"] = "0" * 64
        tampered["payload_sha256"] = canonical_bridge_sha256(tampered)
        with self.assertRaises(FingerprintBridgeError):
            FingerprintBridge.from_payload(tampered)

        duplicate = copy.deepcopy(payload)
        duplicate["nodes"][0]["questions"].append(copy.deepcopy(duplicate["nodes"][0]["questions"][0]))
        duplicate["nodes"][0]["question_count"] += 1
        duplicate["payload_sha256"] = canonical_bridge_sha256(duplicate)
        with self.assertRaises(FingerprintBridgeError):
            FingerprintBridge.from_payload(duplicate)

    def test_fp022_bridge_verification_restores_process_global_identity(self):
        sentinel = ({"id": "sentinel-question", "question_number": 1},)
        register_progress_identity_bank(sentinel)
        verify_bridge_artifact(DEFAULT_BRIDGE_PATH, repo_root=ROOT)
        self.assertEqual(sentinel, registered_progress_identity_bank())

    def test_package_c_remains_inactive(self):
        self.assertEqual({}, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        self.assertEqual("sc900_bank_v8_final.json", cert_config.QUESTION_BANK_FILENAME)
        self.assertEqual(5, SESSION_SCHEMA_VERSION)
        self.assertEqual(2, PROGRESS_CONTENT_EPOCH_VERSION)

    def _runtime_progress_payload(self, bound, question_id, *, record=None, history=None):
        return {
            "version": 3,
            "progress_identity_version": PROGRESS_IDENTITY_VERSION,
            "question_identity": PROGRESS_IDENTITY_KIND,
            "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
            "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
            "fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
            "fingerprint_algorithm": "sha256",
            "loader_contract_version": 1,
            "bank_node_id": bound.source_node.bank_node_id,
            "bank_fingerprint": bound.source_node.runtime_bank_fingerprint,
            "question_content_fingerprints": {question_id: bound.runtime_source_question_fingerprint(question_id)},
            "questions": {
                question_id: copy.deepcopy(
                    record
                    or {
                        "attempts": 3,
                        "correct_count": 2,
                        "wrong_count": 1,
                        "flagged": False,
                        "suspended": False,
                    }
                )
            },
            "history": copy.deepcopy(list(history or [])),
            "content_revision_lineage": [],
        }

    def _bound_revision(self, target_name):
        result = resolve_registered_revision_for_target(ROOT / target_name, registry=self.registry)
        self.assertEqual(AdmissionStatus.PASS, result.status)
        bound = runtime_bound_revision_for_admission(result)
        self.assertIsInstance(bound, RuntimeBoundRevision)
        return bound

    def test_fp011_smart_practice_session_migrates_without_policy_identity_change(self):
        bound = self._bound_revision("sc900_bank_v8_length_rebalanced_t1.json")
        edge = bound.edges[0]
        source_questions = load_bank(ROOT / bound.source_bank_filename)["questions"]
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        source_lookup = {canonical_question_id(row): row for row in source_questions}
        question = source_lookup[edge.question_id]
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=bound.source_bank_filename,
            mode=MODE_SMART_PRACTICE,
            builder_context={
                "mode": MODE_SMART_PRACTICE,
                "count": "1",
                "source_label": "Smart Practice",
            },
            source_label="Smart Practice",
            question_numbers=[question["question_number"]],
            restore_question_numbers=[question["question_number"]],
            session_base_question_count=1,
            session_question_limit=1,
            current_index=0,
            elapsed_seconds=9,
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
            bank_fingerprint=bound.source_node.runtime_bank_fingerprint,
            question_ids=[edge.question_id],
            restore_question_ids=[edge.question_id],
        )
        before_builder = snapshot["builder_context_fingerprint"]
        migrated = _migrate_session_for_revision(
            snapshot,
            target_questions,
            bound,
            bound.target_bank_filename,
        )
        self.assertEqual(MODE_SMART_PRACTICE, migrated.payload["mode"])
        self.assertEqual([edge.question_id], migrated.payload["question_ids"])
        self.assertEqual(before_builder, migrated.payload["builder_context_fingerprint"])
        self.assertEqual(bound.target_node.runtime_bank_fingerprint, migrated.payload["bank_fingerprint"])
        self.assertEqual(SESSION_SCHEMA_VERSION, migrated.payload["schema_version"])

    def test_fp012_history_known_identities_match_unknown_is_preserved_but_filtered(self):
        bound = self._bound_revision("sc900_bank_v8_length_rebalanced_t1.json")
        edge = bound.edges[0]
        raw_edge = bound.artifact_edge(edge.question_id)
        events = [
            {
                "question_id": edge.question_id,
                "question_content_fingerprint": edge.from_content_fingerprint,
            },
            {
                "question_id": edge.question_id,
                "question_content_fingerprint": raw_edge.from_content_fingerprint,
            },
            {
                "question_id": edge.question_id,
                "question_content_fingerprint": "0" * 64,
            },
        ]
        payload = self._runtime_progress_payload(bound, edge.question_id, history=events)
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        migrated = _migrate_progress_for_revision(payload, target_questions, bound, "2026-09-22T00:00:00").payload
        self.assertEqual(events, migrated["history"])
        target = next(row for row in target_questions if canonical_question_id(row) == edge.question_id)
        self.assertTrue(history_event_matches_runtime_bound_revision(events[0], target, bound))
        self.assertTrue(history_event_matches_runtime_bound_revision(events[1], target, bound))
        self.assertFalse(history_event_matches_runtime_bound_revision(events[2], target, bound))
        matched = history_events_for_runtime_bound_revision({edge.question_id: migrated["history"]}, target, bound)
        self.assertEqual(events[:2], matched)

        root_questions = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"]
        root_question = root_questions[0]
        root_qid = canonical_question_id(root_question)
        root_fp = question_content_fingerprint(root_question)
        epoch_v1 = {
            "version": 3,
            "progress_identity_version": PROGRESS_IDENTITY_VERSION,
            "question_identity": PROGRESS_IDENTITY_KIND,
            "progress_content_epoch_version": 1,
            "bank_fingerprint": bank_content_fingerprint(root_questions),
            "question_content_fingerprints": {root_qid: root_fp},
            "questions": {root_qid: {"attempts": 1}},
            "history": [
                {"question_id": root_qid, "question_content_fingerprint": root_fp},
                {"question_id": root_qid, "question_content_fingerprint": "f" * 64},
            ],
        }
        upgraded, changed = migrate_progress_content_epoch(epoch_v1, root_questions)
        self.assertTrue(changed)
        self.assertEqual(RUNTIME_FINGERPRINT_DOMAIN, upgraded["history"][0]["fingerprint_domain"])
        self.assertNotIn("fingerprint_domain", upgraded["history"][1])

    def test_fp013_correction_resets_governed_active_state_and_quarantines_history_once(self):
        bound = self._bound_revision("sc900_bank_v8_content_correction_001.json")
        self.assertEqual(9, len(bound.edges))
        qid = "sc900_mlc_q118"
        event = {
            "question_id": qid,
            "question_content_fingerprint": bound.runtime_source_question_fingerprint(qid),
        }
        source_record = {
            "attempts": 7,
            "correct_count": 5,
            "wrong_count": 2,
            "flagged": True,
            "suspended": True,
            "last_confidence": "Sure",
        }
        payload = self._runtime_progress_payload(bound, qid, record=source_record, history=[event])
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        migrated = _migrate_progress_for_revision(payload, target_questions, bound, "2026-09-22T00:00:00").payload
        record = migrated["questions"][qid]
        self.assertEqual(0, record["attempts"])
        self.assertEqual(0, record["correct_count"])
        self.assertEqual(0, record["wrong_count"])
        self.assertTrue(record["flagged"])
        self.assertTrue(record["suspended"])
        self.assertEqual([], migrated["history"])
        self.assertEqual([event], migrated["quarantined_history"])

    def test_fp014_explanation_revision_preserves_learner_record_and_history(self):
        bound = self._bound_revision("sc900_bank_v8_explanation_tranche_1.json")
        edge = bound.edges[0]
        record = {
            "attempts": 8,
            "correct_count": 6,
            "wrong_count": 2,
            "flagged": True,
            "suspended": False,
        }
        event = {
            "question_id": edge.question_id,
            "question_content_fingerprint": edge.from_content_fingerprint,
        }
        payload = self._runtime_progress_payload(bound, edge.question_id, record=record, history=[event])
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        migrated = _migrate_progress_for_revision(payload, target_questions, bound, "2026-09-22T00:00:00").payload
        self.assertEqual(record, migrated["questions"][edge.question_id])
        self.assertEqual([event], migrated["history"])

    def test_fp015_q118_correction_then_explanations_do_not_reset_twice(self):
        qid = "sc900_mlc_q118"
        correction = self._bound_revision("sc900_bank_v8_content_correction_001.json")
        source_record = {
            "attempts": 9,
            "correct_count": 6,
            "wrong_count": 3,
            "flagged": True,
            "suspended": True,
        }
        payload = self._runtime_progress_payload(correction, qid, record=source_record)
        correction_questions = load_bank(ROOT / correction.target_bank_filename)["questions"]
        after_correction = _migrate_progress_for_revision(
            payload, correction_questions, correction, "2026-09-22T00:00:00"
        ).payload
        reset_record = copy.deepcopy(after_correction["questions"][qid])
        self.assertEqual(0, reset_record["attempts"])

        tranche = self._bound_revision("sc900_bank_v8_explanation_tranche_1.json")
        tranche_questions = load_bank(ROOT / tranche.target_bank_filename)["questions"]
        after_tranche = _migrate_progress_for_revision(
            after_correction, tranche_questions, tranche, "2026-09-22T00:01:00"
        ).payload
        self.assertEqual(reset_record, after_tranche["questions"][qid])

        q118 = self._bound_revision("sc900_bank_v8_explanation_q118_repair.json")
        q118_questions = load_bank(ROOT / q118.target_bank_filename)["questions"]
        after_q118 = _migrate_progress_for_revision(after_tranche, q118_questions, q118, "2026-09-22T00:02:00").payload
        self.assertEqual(reset_record, after_q118["questions"][qid])

    def test_fp016_same_node_smart_practice_seed_is_stable(self):
        node = self.bridge.nodes[0]
        material = {
            "builder_context_fingerprint": "builder",
            "bank_content_fingerprint": node.runtime_bank_fingerprint,
            "policy_id": "policy",
            "policy_version": "1",
            "policy_checksum": "checksum",
            "learner_state_revision": {"attempts": 3},
        }
        before = smart_practice_ordering_seed(material)
        verify_bridge_artifact(DEFAULT_BRIDGE_PATH, repo_root=ROOT)
        after = smart_practice_ordering_seed(material)
        self.assertEqual(before, after)
        changed = dict(material)
        changed["bank_content_fingerprint"] = self.bridge.nodes[1].runtime_bank_fingerprint
        self.assertNotEqual(before, smart_practice_ordering_seed(changed))

    def test_fp017_cand_authority_metadata_is_untouched_by_generic_bridge_migration(self):
        bound = self._bound_revision("sc900_bank_v8_length_rebalanced_t1.json")
        edge = bound.edges[0]
        cand_metadata = {
            "partition_epoch": "frozen-epoch",
            "manifest_sha256": "1" * 64,
            "store_sha256": "2" * 64,
            "semantic_audit_sha256": "3" * 64,
            "compiled_sha256": "4" * 64,
        }
        payload = self._runtime_progress_payload(bound, edge.question_id)
        payload["meta"] = {"cand01r3": copy.deepcopy(cand_metadata)}
        before_cache_identity = partition_cache_identity()
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        migrated = _migrate_progress_for_revision(payload, target_questions, bound, "2026-09-22T00:00:00").payload
        self.assertEqual(cand_metadata, migrated["meta"]["cand01r3"])
        self.assertEqual(before_cache_identity, partition_cache_identity())

    def test_fp019_missing_optional_fields_are_verified_as_exact_reviewed_defaults(self):
        prior = registered_progress_identity_bank()
        try:
            checked = 0
            for filename in FROZEN_BANK_FILENAMES:
                raw = json.loads((ROOT / filename).read_text(encoding="utf-8"))["questions"]
                runtime = load_bank(ROOT / filename)["questions"]
                raw_by_id = {canonical_question_id(row): row for row in raw}
                runtime_by_id = {canonical_question_id(row): row for row in runtime}
                for qid, raw_question in raw_by_id.items():
                    self.assertNotIn("subtitle", raw_question)
                    self.assertNotIn("study_focus", raw_question)
                    self.assertEqual("", runtime_by_id[qid]["subtitle"])
                    self.assertEqual("", runtime_by_id[qid]["study_focus"])
                    checked += 1
            self.assertEqual(4086, checked)
        finally:
            register_progress_identity_bank(prior)

    def test_fp020_unreviewed_normalization_delta_is_rejected(self):
        raw = json.loads((ROOT / FROZEN_BANK_FILENAMES[0]).read_text(encoding="utf-8"))["questions"][0]
        prior = registered_progress_identity_bank()
        try:
            runtime = load_bank(ROOT / FROZEN_BANK_FILENAMES[0])["questions"][0]
        finally:
            register_progress_identity_bank(prior)
        altered = copy.deepcopy(runtime)
        altered["prompt"] = str(altered.get("prompt") or "") + " changed"
        with self.assertRaises(FingerprintBridgeError) as cm:
            _verify_reviewed_projection_delta(raw, altered)
        self.assertEqual(BridgeFailureReason.UNREVIEWED_NORMALIZATION_DELTA, cm.exception.reason)

    def test_fp023_registry_wrapper_preserves_native_authority_exactly(self):
        for target in TARGET_NAMES:
            result = resolve_registered_revision_for_target(ROOT / target, registry=self.registry)
            bound = runtime_bound_revision_for_admission(result)
            self.assertIsNotNone(bound)
            self.assertIs(bound.admitted, result.admitted)
            self.assertEqual(tuple(result.admitted.edges), bound.artifact_edges)
            self.assertEqual(
                result.admitted.source_bank_content_fingerprint,
                bound.source_node.artifact_bank_fingerprint,
            )
            self.assertEqual(
                result.admitted.target_bank_content_fingerprint,
                bound.target_node.artifact_bank_fingerprint,
            )

    def test_fp025_exact_bank_binding_tamper_fails_closed(self):
        payload = json.loads(DEFAULT_BRIDGE_PATH.read_text(encoding="utf-8"))
        tampered = copy.deepcopy(payload)
        tampered["nodes"][0]["raw_file_sha256"] = "0" * 64
        tampered["payload_sha256"] = canonical_bridge_sha256(tampered)
        with self.assertRaises(FingerprintBridgeError):
            FingerprintBridge.from_payload(tampered)

    def _transaction_fixture(self, root: Path):
        result = resolve_registered_revision_for_target(
            ROOT / "sc900_bank_v8_length_rebalanced_t1.json",
            registry=self.registry,
        )
        bound = runtime_bound_revision_for_admission(result)
        assert bound is not None
        edge = bound.edges[0]
        source_questions = load_bank(ROOT / bound.source_bank_filename)["questions"]
        target_questions = load_bank(ROOT / bound.target_bank_filename)["questions"]
        source_lookup = {canonical_question_id(row): row for row in source_questions}
        question = source_lookup[edge.question_id]
        progress_source = root / "source_progress.json"
        progress_target = root / "target_progress.json"
        progress_source.write_text(
            json.dumps(
                {
                    "version": 3,
                    "progress_identity_version": PROGRESS_IDENTITY_VERSION,
                    "question_identity": PROGRESS_IDENTITY_KIND,
                    "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
                    "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
                    "fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
                    "fingerprint_algorithm": "sha256",
                    "loader_contract_version": 1,
                    "bank_node_id": bound.source_node.bank_node_id,
                    "bank_fingerprint": bound.source_node.runtime_bank_fingerprint,
                    "question_content_fingerprints": {edge.question_id: edge.from_content_fingerprint},
                    "questions": {edge.question_id: {"attempts": 4, "correct_count": 3}},
                    "history": [],
                    "content_revision_lineage": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        session_source = root / "source_session.json"
        session_target = root / "target_session.json"
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=bound.source_bank_filename,
            mode=MODE_PRACTICE,
            builder_context={"mode": MODE_PRACTICE, "count": "1", "source_label": "All"},
            source_label="All",
            question_numbers=[question["question_number"]],
            restore_question_numbers=[question["question_number"]],
            session_base_question_count=1,
            session_question_limit=1,
            current_index=0,
            elapsed_seconds=3,
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
            bank_fingerprint=bound.source_node.runtime_bank_fingerprint,
            question_ids=[edge.question_id],
            restore_question_ids=[edge.question_id],
        )
        session_source.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return (
            bound,
            source_questions,
            target_questions,
            progress_source,
            progress_target,
            session_source,
            session_target,
        )

    def test_atomic_revision_transaction_commits_progress_and_session_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (
                bound,
                source_questions,
                target_questions,
                progress_source,
                progress_target,
                session_source,
                session_target,
            ) = self._transaction_fixture(root)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            receipt, error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:00:00",
                source_questions=source_questions,
            )
            self.assertIsNone(error)
            self.assertTrue(receipt["committed"])
            self.assertTrue(progress_target.exists())
            self.assertTrue(session_target.exists())
            self.assertFalse(progress_source.exists())
            self.assertFalse(session_source.exists())
            progress = json.loads(progress_target.read_text(encoding="utf-8"))
            session = json.loads(session_target.read_text(encoding="utf-8"))
            self.assertEqual(bound.target_node.runtime_bank_fingerprint, progress["bank_fingerprint"])
            self.assertEqual(bound.target_node.runtime_bank_fingerprint, session["bank_fingerprint"])
            self.assertEqual(5, session["schema_version"])

    def test_atomic_revision_transaction_receipt_is_revalidated_on_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (
                bound,
                source_questions,
                target_questions,
                progress_source,
                progress_target,
                session_source,
                session_target,
            ) = self._transaction_fixture(root)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            receipt, error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:00:00",
                source_questions=source_questions,
            )
            self.assertIsNone(error)
            self.assertTrue(receipt["committed"])

            repeated, repeat_error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:01:00",
                source_questions=source_questions,
            )
            self.assertIsNone(repeat_error)
            self.assertEqual(receipt, repeated)

            tampered = json.loads(progress_target.read_text(encoding="utf-8"))
            tampered["questions"][next(iter(tampered["questions"]))]["attempts"] = 999
            progress_target.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
            rejected, reject_error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:02:00",
                source_questions=source_questions,
            )
            self.assertIsNone(rejected)
            self.assertIsNotNone(reject_error)

    def test_atomic_revision_transaction_tampered_journal_identity_fails_before_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (
                bound,
                source_questions,
                target_questions,
                progress_source,
                progress_target,
                session_source,
                session_target,
            ) = self._transaction_fixture(root)
            persistence = RuntimePersistence(root / "checkpoints", root / "backups")
            receipt, error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:00:00",
                source_questions=source_questions,
                failpoint="after_journal",
            )
            self.assertIsNone(receipt)
            self.assertIsNotNone(error)
            migration_id = persistence._revision_transaction_identity(bound)["migration_id"]
            journal_path = root / f".sc900_revision_{migration_id}.journal.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            journal["bridge_sha256"] = "0" * 64
            journal_path.write_text(json.dumps(journal, indent=2), encoding="utf-8")
            before_source = progress_source.read_bytes()
            recovered, recovery_error = persistence.migrate_revision_state_transaction(
                progress_source_path=progress_source,
                progress_target_path=progress_target,
                session_pairs=[(session_source, session_target)],
                target_questions=target_questions,
                revision=bound,
                target_bank_file=bound.target_bank_filename,
                migrated_at="2026-09-22T00:01:00",
                source_questions=source_questions,
            )
            self.assertIsNone(recovered)
            self.assertIsNotNone(recovery_error)
            self.assertEqual(before_source, progress_source.read_bytes())
            self.assertFalse(progress_target.exists())
            self.assertFalse(session_target.exists())

    def test_atomic_revision_transaction_recovers_injected_partial_commit(self):
        for failpoint in (
            "after_transform",
            "after_stage_0",
            "after_staging",
            "before_journal",
            "after_journal",
            "before_replace_0",
            "after_replace_0",
            "before_replace_1",
            "after_replace_1",
            "before_receipt",
            "after_receipt",
        ):
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (
                    bound,
                    source_questions,
                    target_questions,
                    progress_source,
                    progress_target,
                    session_source,
                    session_target,
                ) = self._transaction_fixture(root)
                persistence = RuntimePersistence(root / "checkpoints", root / "backups")
                receipt, error = persistence.migrate_revision_state_transaction(
                    progress_source_path=progress_source,
                    progress_target_path=progress_target,
                    session_pairs=[(session_source, session_target)],
                    target_questions=target_questions,
                    revision=bound,
                    target_bank_file=bound.target_bank_filename,
                    migrated_at="2026-09-22T00:00:00",
                    source_questions=source_questions,
                    failpoint=failpoint,
                )
                self.assertIsNone(receipt)
                self.assertIsNotNone(error)
                recovered, recovery_error = persistence.migrate_revision_state_transaction(
                    progress_source_path=progress_source,
                    progress_target_path=progress_target,
                    session_pairs=[(session_source, session_target)],
                    target_questions=target_questions,
                    revision=bound,
                    target_bank_file=bound.target_bank_filename,
                    migrated_at="2026-09-22T00:00:00",
                    source_questions=source_questions,
                )
                self.assertIsNone(recovery_error)
                self.assertTrue(recovered["committed"])
                self.assertTrue(progress_target.exists())
                self.assertTrue(session_target.exists())
                self.assertFalse(progress_source.exists())
                self.assertFalse(session_source.exists())


if __name__ == "__main__":
    unittest.main()
