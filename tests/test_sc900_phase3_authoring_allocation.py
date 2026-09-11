import json
import unittest
from collections import Counter
from pathlib import Path

from ingestion.models import load_taxonomy

ROOT = Path(__file__).resolve().parents[1]
ALLOCATION_PATH = ROOT / "content" / "sc900" / "phase3" / "authoring_allocation.json"

EXPECTED_INCREMENT_DOMAINS = {
    "security_compliance_identity": 12,
    "microsoft_entra": 28,
    "microsoft_security_solutions": 38,
    "microsoft_compliance_solutions": 22,
}
EXPECTED_INCREMENT_OBJECTIVES = {
    "security_compliance_concepts": 6,
    "identity_concepts": 6,
    "entra_identity_types_and_function": 6,
    "entra_authentication": 8,
    "entra_access_management": 6,
    "entra_identity_protection_governance": 8,
    "azure_infrastructure_security": 12,
    "azure_security_management": 8,
    "microsoft_sentinel": 6,
    "defender_xdr": 12,
    "service_trust_privacy": 4,
    "purview_compliance_management": 4,
    "purview_information_protection_lifecycle": 8,
    "purview_insider_risk_ediscovery_audit": 6,
}


class Phase3AuthoringAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ALLOCATION_PATH.exists():
            raise AssertionError(f"missing frozen Task-3 allocation: {ALLOCATION_PATH}")
        cls.allocation = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
        cls.items = cls.allocation["items"]
        cls.taxonomy = load_taxonomy()

    def test_exactly_100_unique_sequential_phase3_ids(self):
        ids = [row["question_id"] for row in self.items]
        self.assertEqual(100, len(ids))
        self.assertEqual(100, len(set(ids)))
        self.assertEqual(
            [f"sc900_p3_q{index:03d}" for index in range(1, 101)],
            ids,
        )

    def test_exact_incremental_domain_and_objective_allocation(self):
        self.assertEqual(
            EXPECTED_INCREMENT_DOMAINS,
            dict(Counter(row["domain"] for row in self.items)),
        )
        self.assertEqual(
            EXPECTED_INCREMENT_OBJECTIVES,
            dict(Counter(row["objective"] for row in self.items)),
        )

    def test_all_58_blueprint_leaves_are_represented(self):
        taxonomy_leaves = {
            leaf["id"] for detail in self.taxonomy["objective_details"] for leaf in detail["leaf_skills"]
        }
        allocation_leaves = {row["blueprint_leaf_id"] for row in self.items}
        self.assertEqual(58, len(taxonomy_leaves))
        self.assertEqual(taxonomy_leaves, allocation_leaves)

    def test_each_batch_has_exactly_10_items_and_bounded_domain_mix(self):
        batches = Counter(row["batch"] for row in self.items)
        self.assertEqual({f"batch-{index:02d}" for index in range(1, 11)}, set(batches))
        self.assertTrue(all(count == 10 for count in batches.values()))
        for batch in batches:
            rows = [row for row in self.items if row["batch"] == batch]
            domains = Counter(row["domain"] for row in rows)
            self.assertGreaterEqual(domains["security_compliance_identity"], 1)
            self.assertGreaterEqual(domains["microsoft_entra"], 2)
            self.assertGreaterEqual(domains["microsoft_security_solutions"], 3)
            self.assertGreaterEqual(domains["microsoft_compliance_solutions"], 2)

    def test_source_assignment_is_first_party_and_inventory_addressable(self):
        inventory_path = ROOT / "content" / "sc900" / "phase3" / "source_inventory.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        sources = {row["source_id"]: row for row in inventory["sources"]}
        for row in self.items:
            source_id = row["source_inventory_id"]
            self.assertIn(source_id, sources)
            source = sources[source_id]
            self.assertEqual(row["source_url"], source["url"])
            self.assertTrue(row["source_url"].startswith("https://learn.microsoft.com/"))
            self.assertIn(row["objective"], source["objective_ids"])
            self.assertIn(row["blueprint_leaf_id"], source["leaf_ids"])
            self.assertFalse(source["assessment_content_used"])

    def test_answer_position_targets_are_exactly_balanced_without_streaks(self):
        positions = [row["display_correct_position_target"] for row in self.items]
        self.assertEqual({"A": 25, "B": 25, "C": 25, "D": 25}, dict(Counter(positions)))
        longest = 1
        current = 1
        for left, right in zip(positions, positions[1:], strict=False):
            if left == right:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        self.assertLessEqual(longest, 2)


if __name__ == "__main__":
    unittest.main()
