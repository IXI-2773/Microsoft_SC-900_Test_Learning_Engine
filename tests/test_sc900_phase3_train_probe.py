from __future__ import annotations

import copy
import hashlib
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE3_ROOT = ROOT / "content" / "sc900" / "phase3"
SCHEMA_PATH = PHASE3_ROOT / "train_probe_manifest.schema.json"
MANIFEST_PATH = PHASE3_ROOT / "train_probe_manifest.json"
STORE_PATH = PHASE3_ROOT / "store" / "questions.json"
COMPILED_PATH = PHASE3_ROOT / "compiled" / "sc900_phase3_reviewed_bank.json"
AUDIT_PATH = PHASE3_ROOT / "semantic_family_audit.json"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"
EXPECTED_AUDIT_SHA256 = "e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701"
EXPECTED_STORE_SHA256 = "2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c"
EXPECTED_COMPILED_SHA256 = "72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b"
EXPECTED_DEFAULT_BANK_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"
GATE2_STATUS = "GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE"
RUNTIME_CONSUMER_ALLOWLIST = {
    "tools/build_sc900_phase3.py",
    "tools/validate_sc900_phase3.py",
    "tests/test_sc900_phase3_train_probe.py",
}


def _codes(errors):
    return {row["code"] if isinstance(row, dict) else str(row) for row in errors}


def _load_validator(testcase):
    module = importlib.import_module("tools.validate_sc900_phase3")
    testcase.assertTrue(
        hasattr(module, "validate_phase3_train_probe_manifest"),
        "tools.validate_sc900_phase3.validate_phase3_train_probe_manifest must exist",
    )
    return module


def _load_builder(testcase):
    module = importlib.import_module("tools.build_sc900_phase3")
    testcase.assertTrue(
        hasattr(module, "build_train_probe_manifest"),
        "tools.build_sc900_phase3.build_train_probe_manifest must exist",
    )
    return module


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


AUDIT_HASH = _sha("audit")
STORE_HASH = _sha("store")
COMPILED_HASH = _sha("compiled")


def _question(
    question_id,
    family,
    *,
    suitability="eligible",
    status="approved",
    domain="microsoft_entra",
    objective="entra_authentication",
    leaf="multifactor_authentication",
):
    return {
        "id": question_id,
        "domain": domain,
        "objective": objective,
        "promotion_status": status,
        "taxonomy_version": "2026-07-28",
        "metadata": {
            "blueprint_leaf_id": leaf,
            "future_probe_suitability": suitability,
            "semantic_family_id": family,
            "source_family_id": f"source-{family}",
        },
    }


def _item(
    question,
    role,
    *,
    family_state="resolved",
    suitability=None,
    status=None,
    evidence_epoch="phase3-task6-train-probe-partition",
):
    metadata = question["metadata"]
    family = metadata["semantic_family_id"]
    return {
        "assignment_evidence": {
            "approved_state_checked": True,
            "assigned_at": evidence_epoch,
            "assignment_method": "whole_family_inheritance",
            "assignment_reason": f"{family} assigned {role}",
            "family_isolation_checked": True,
            "family_resolved_checked": True,
            "partition_epoch": evidence_epoch,
            "probe_suitability_checked": True,
            "question_id": question["id"],
            "role": role,
            "semantic_family_id": family,
            "source_task4_audit_hash": AUDIT_HASH,
            "source_task5_store_hash": STORE_HASH,
        },
        "assignment_rationale": f"{family} assigned {role}",
        "assignment_receipt": {
            "override_type": "none",
            "prior_family_ids": [family],
            "reviewed_at": "2026-09-11T18:00:00Z",
            "reviewer": "cursor-grok-4.6-phase3-task6-partition",
        },
        "blueprint_version": "2026-07-28",
        "family_state": family_state,
        "future_probe_suitability": suitability or metadata["future_probe_suitability"],
        "promotion_status": status or question["promotion_status"],
        "question_id": question["id"],
        "role": role,
        "semantic_family_id": family,
        "source_family_id": metadata["source_family_id"],
    }


def _family_assignment(family_id, role, members, *, epoch="phase3-task6-train-probe-partition"):
    return {
        "approved_state_checked": True,
        "assignment_method": "whole_family_design_allocation",
        "assignment_reason": f"{family_id} assigned {role}",
        "family_isolation_checked": True,
        "family_resolved_checked": True,
        "family_state": "resolved",
        "member_count": len(members),
        "member_ids": list(members),
        "partition_epoch": epoch,
        "probe_suitability_checked": True,
        "role": role,
        "semantic_family_id": family_id,
        "source_task4_audit_hash": AUDIT_HASH,
        "source_task5_store_hash": STORE_HASH,
        "transfer_edge_isolation_checked": True,
    }


def _role_report(items, questions, family_assignments, role):
    role_items = [item for item in items if item["role"] == role]
    role_families = [row for row in family_assignments if row["role"] == role]
    qindex = {row["id"]: row for row in questions}
    sizes = sorted(row["member_count"] for row in role_families)
    report = {
        "domain_counts": {},
        "family_count": len(role_families),
        "family_ids": [row["semantic_family_id"] for row in role_families],
        "leaf_coverage": [],
        "objective_counts": {},
        "probe_eligible_count": 0,
        "question_count": len(role_items),
    }
    domains = {}
    objectives = {}
    leaves = []
    eligible = 0
    for item in role_items:
        question = qindex[item["question_id"]]
        domains[question["domain"]] = domains.get(question["domain"], 0) + 1
        objectives[question["objective"]] = objectives.get(question["objective"], 0) + 1
        leaf = question["metadata"]["blueprint_leaf_id"]
        if leaf not in leaves:
            leaves.append(leaf)
        if item["future_probe_suitability"] == "eligible":
            eligible += 1
    report["domain_counts"] = dict(sorted(domains.items()))
    report["objective_counts"] = dict(sorted(objectives.items()))
    report["leaf_coverage"] = sorted(leaves)
    report["probe_eligible_count"] = eligible
    if role == "PROBE":
        report["effective_independent_family_count"] = len(role_families)
        report["largest_family_size"] = sizes[-1] if sizes else 0
        report["smallest_family_size"] = sizes[0] if sizes else 0
    return report


def _valid_bundle():
    questions = [
        _question(
            "sc900_p1_q001",
            "family_train",
            domain="security_compliance_identity",
            objective="security_compliance_concepts",
            leaf="shared_responsibility_model",
        ),
        _question(
            "sc900_p1_q002",
            "family_train",
            domain="security_compliance_identity",
            objective="security_compliance_concepts",
            leaf="shared_responsibility_model",
        ),
        _question(
            "sc900_p1_q003",
            "family_probe",
            domain="microsoft_entra",
            objective="entra_authentication",
            leaf="multifactor_authentication",
        ),
        _question(
            "sc900_p1_q004",
            "family_probe",
            domain="microsoft_entra",
            objective="entra_authentication",
            leaf="multifactor_authentication",
        ),
    ]
    items = [
        _item(questions[0], "TRAIN"),
        _item(questions[1], "TRAIN"),
        _item(questions[2], "PROBE"),
        _item(questions[3], "PROBE"),
    ]
    family_assignments = [
        _family_assignment("family_probe", "PROBE", ["sc900_p1_q003", "sc900_p1_q004"]),
        _family_assignment("family_train", "TRAIN", ["sc900_p1_q001", "sc900_p1_q002"]),
    ]
    all_path_leakage_handoff = {
        "contract": "No runtime path may mix TRAIN and PROBE members of one family or transfer-edge component.",
        "design_time_only": True,
        "invariants": [
            "ONE_FAMILY_ONE_ROLE",
            "NO_TRAIN_PROBE_FAMILY_SPLIT",
            "NO_TRAIN_PROBE_TRANSFER_EDGE_CROSSING",
        ],
        "paths_requiring_future_guards": [
            "normal_practice",
            "smart_practice",
        ],
        "runtime_consumer_authorized": False,
    }
    audit = {
        "family_count": 2,
        "families": [
            {
                "family_state": "resolved",
                "members": ["sc900_p1_q003", "sc900_p1_q004"],
                "semantic_family_id": "family_probe",
            },
            {
                "family_state": "resolved",
                "members": ["sc900_p1_q001", "sc900_p1_q002"],
                "semantic_family_id": "family_train",
            },
        ],
        "transfer_edges": [],
    }
    allocation_report = {
        "objectives_absent_from_probe": ["security_compliance_concepts"],
        "probe": _role_report(items, questions, family_assignments, "PROBE"),
        "train": _role_report(items, questions, family_assignments, "TRAIN"),
        "transfer_edge_isolation": {
            "cross_family_edges": 0,
            "train_probe_crossings": 0,
        },
        "unassigned": _role_report(items, questions, family_assignments, "UNASSIGNED"),
    }
    manifest = {
        "all_path_leakage_handoff": all_path_leakage_handoff,
        "allocation_report": allocation_report,
        "blueprint_version": "2026-07-28",
        "cand01_gate2_status": GATE2_STATUS,
        "compiled_sha256": COMPILED_HASH,
        "design_time_only": True,
        "family_assignments": family_assignments,
        "implementation_authorized": False,
        "inherited_item_schema": "sc900.train-probe-manifest/v1",
        "items": items,
        "manifest_version": "sc900.phase3.train-probe-manifest/v1",
        "partition_epoch": "phase3-task6-train-probe-partition",
        "phase_3_structurally_accepted": False,
        "question_count": 4,
        "runtime_consumer_authorized": False,
        "schema_version": "sc900.phase3.train-probe-manifest/v1",
        "semantic_audit_sha256": AUDIT_HASH,
        "semantic_family_count": 2,
        "store_sha256": STORE_HASH,
        "work_id": "SC900-BANK-PHASE3-001",
    }
    return manifest, questions, audit


def _validate(testcase, manifest, questions, audit, **overrides):
    module = _load_validator(testcase)
    kwargs = {
        "expected_audit_sha256": AUDIT_HASH,
        "expected_compiled_sha256": COMPILED_HASH,
        "expected_family_count": 2,
        "expected_store_sha256": STORE_HASH,
    }
    kwargs.update(overrides)
    return module.validate_phase3_train_probe_manifest(
        manifest,
        questions=questions,
        audit=audit,
        **kwargs,
    )


class Phase3TrainProbeFailClosedTests(unittest.TestCase):
    def test_same_semantic_family_cannot_span_train_and_probe(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][1]["role"] = "PROBE"
        manifest["items"][1]["assignment_evidence"]["role"] = "PROBE"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("SEMANTIC_FAMILY_SPLIT", codes)

    def test_transfer_edge_cannot_cross_train_and_probe(self):
        manifest, questions, audit = _valid_bundle()
        audit = copy.deepcopy(audit)
        audit["transfer_edges"] = [
            {
                "left": "sc900_p1_q001",
                "right": "sc900_p1_q003",
                "semantic_family_id": "family_train",
            }
        ]
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("TRAIN_PROBE_TRANSFER_EDGE_CROSSING", codes)

    def test_unresolved_family_cannot_be_train(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["family_state"] = "disputed"
        manifest["family_assignments"][1]["family_state"] = "disputed"
        audit = copy.deepcopy(audit)
        audit["families"][1]["family_state"] = "disputed"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("TRAIN_REQUIRES_RESOLVED_FAMILY", codes)

    def test_unresolved_family_cannot_be_probe(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][2]["family_state"] = "unknown"
        manifest["family_assignments"][0]["family_state"] = "unknown"
        audit = copy.deepcopy(audit)
        audit["families"][0]["family_state"] = "unknown"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("PROBE_REQUIRES_RESOLVED_FAMILY", codes)

    def test_nonapproved_item_cannot_be_train(self):
        manifest, questions, audit = _valid_bundle()
        questions = copy.deepcopy(questions)
        questions[0]["promotion_status"] = "pending"
        manifest["items"][0]["promotion_status"] = "pending"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("TRAIN_REQUIRES_APPROVED", codes)

    def test_nonapproved_item_cannot_be_probe(self):
        manifest, questions, audit = _valid_bundle()
        questions = copy.deepcopy(questions)
        questions[2]["promotion_status"] = "withheld"
        manifest["items"][2]["promotion_status"] = "withheld"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("PROBE_REQUIRES_APPROVED", codes)

    def test_probe_ineligible_item_cannot_be_probe(self):
        manifest, questions, audit = _valid_bundle()
        questions = copy.deepcopy(questions)
        questions[2]["metadata"]["future_probe_suitability"] = "train_only"
        manifest["items"][2]["future_probe_suitability"] = "train_only"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("PROBE_REQUIRES_ELIGIBLE", codes)

    def test_missing_question_assignment_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"] = manifest["items"][:-1]
        manifest["question_count"] = 3
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("MISSING_QUESTION_ASSIGNMENT", codes)

    def test_duplicate_question_assignment_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"].append(copy.deepcopy(manifest["items"][0]))
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("DUPLICATE_MANIFEST_QUESTION_ID", codes)

    def test_unknown_question_id_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["question_id"] = "sc900_unknown_q999"
        manifest["items"][0]["assignment_evidence"]["question_id"] = "sc900_unknown_q999"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("UNKNOWN_QUESTION_ID", codes)

    def test_malformed_role_enum_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["role"] = "MAYBE"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("INVALID_MANIFEST_ROLE", codes)

    def test_malformed_family_id_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["semantic_family_id"] = "Not A Family"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("MALFORMED_SEMANTIC_FAMILY_ID", codes)

    def test_family_role_inconsistent_with_item_role_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["family_assignments"][1]["role"] = "UNASSIGNED"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("FAMILY_ROLE_ITEM_ROLE_MISMATCH", codes)

    def test_missing_assignment_receipt_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        del manifest["items"][0]["assignment_receipt"]
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("MISSING_ASSIGNMENT_RECEIPT", codes)

    def test_malformed_assignment_receipt_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["assignment_receipt"] = {"reviewed_at": ""}
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("INCOMPLETE_ASSIGNMENT_RECEIPT", codes)

    def test_missing_partition_epoch_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        del manifest["partition_epoch"]
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("MISSING_PARTITION_EPOCH", codes)

    def test_inconsistent_partition_epoch_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["items"][0]["assignment_evidence"]["partition_epoch"] = "other-epoch"
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("INCONSISTENT_PARTITION_EPOCH", codes)

    def test_incomplete_allocation_report_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        del manifest["allocation_report"]["probe"]["domain_counts"]
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("INCOMPLETE_ALLOCATION_REPORT", codes)

    def test_semantic_audit_hash_mismatch_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        codes = _codes(_validate(self, manifest, questions, audit, expected_audit_sha256="0" * 64))
        self.assertIn("SEMANTIC_AUDIT_HASH_MISMATCH", codes)

    def test_store_and_compiled_hash_mismatch_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        codes = _codes(
            _validate(
                self,
                manifest,
                questions,
                audit,
                expected_store_sha256="1" * 64,
                expected_compiled_sha256="2" * 64,
            )
        )
        self.assertIn("STORE_HASH_MISMATCH", codes)
        self.assertIn("COMPILED_HASH_MISMATCH", codes)

    def test_family_count_mismatch_from_27_family_authority_fails_closed(self):
        manifest, questions, audit = _valid_bundle()
        codes = _codes(_validate(self, manifest, questions, audit, expected_family_count=27))
        self.assertIn("SEMANTIC_FAMILY_COUNT_MISMATCH", codes)

    def test_unknown_manifest_fields_fail_closed(self):
        manifest, questions, audit = _valid_bundle()
        manifest["unexpected_manifest_field"] = True
        manifest["items"][0]["unexpected_item_field"] = True
        codes = _codes(_validate(self, manifest, questions, audit))
        self.assertIn("UNEXPECTED_MANIFEST_FIELD", codes)
        self.assertIn("UNEXPECTED_MANIFEST_ITEM_FIELD", codes)


class Phase3TrainProbeSchemaParityTests(unittest.TestCase):
    def test_schema_and_python_forbid_the_same_unknown_fields(self):
        self.assertTrue(SCHEMA_PATH.exists())
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        module = _load_validator(self)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]), module.PHASE3_MANIFEST_FIELDS)
        self.assertEqual(set(schema["required"]), module.PHASE3_MANIFEST_REQUIRED)
        self.assertFalse(schema["properties"]["items"]["items"]["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]["items"]["items"]["properties"]),
            module.PHASE3_ITEM_FIELDS,
        )


class Phase3TrainProbeCommittedArtifactTests(unittest.TestCase):
    def test_committed_manifest_validates_against_frozen_inputs(self):
        builder = _load_builder(self)
        validator = _load_validator(self)
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        questions = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        errors = validator.validate_phase3_train_probe_manifest(
            manifest,
            questions=questions,
            audit=audit,
            expected_audit_sha256=EXPECTED_AUDIT_SHA256,
            expected_store_sha256=EXPECTED_STORE_SHA256,
            expected_compiled_sha256=EXPECTED_COMPILED_SHA256,
            expected_family_count=27,
        )
        self.assertEqual([], errors)
        self.assertEqual(200, manifest["question_count"])
        self.assertEqual(200, len(manifest["items"]))
        self.assertEqual(27, manifest["semantic_family_count"])
        self.assertEqual(27, len(manifest["family_assignments"]))
        self.assertTrue(manifest["design_time_only"])
        self.assertFalse(manifest["runtime_consumer_authorized"])
        self.assertFalse(manifest["implementation_authorized"])
        self.assertFalse(manifest["phase_3_structurally_accepted"])
        self.assertEqual(GATE2_STATUS, manifest["cand01_gate2_status"])
        roles = {item["role"] for item in manifest["items"]}
        self.assertTrue(roles <= {"TRAIN", "PROBE", "UNASSIGNED"})
        self.assertEqual(
            0,
            builder.train_probe_family_split_count(manifest),
        )
        self.assertEqual(
            0,
            builder.train_probe_transfer_edge_crossing_count(manifest, audit),
        )

    def test_committed_manifest_is_reproducible(self):
        builder = _load_builder(self)
        errors = builder.verify_train_probe_manifest()
        self.assertEqual([], errors)

    def test_default_launch_bank_unchanged(self):
        actual = hashlib.sha256(DEFAULT_BANK.read_bytes()).hexdigest()
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, actual)

    def test_no_runtime_consumer_of_phase3_manifest(self):
        needle = "content/sc900/phase3/train_probe_manifest.json"
        hits = []
        for path in ROOT.rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if relative in RUNTIME_CONSUMER_ALLOWLIST:
                continue
            if any(part in {"__pycache__", ".git", ".ruff_cache"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            if needle in text:
                hits.append(relative)
        self.assertEqual([], hits)


if __name__ == "__main__":
    unittest.main()
