import unittest

from ingestion.models import load_taxonomy


class SC900TaxonomyTests(unittest.TestCase):
    def test_july_2026_taxonomy_has_14_objectives_and_58_unique_leaves(self):
        taxonomy = load_taxonomy()
        self.assertEqual("2026-07-28", taxonomy["skills_effective_date"])
        objective_ids = [
            objective
            for domain in taxonomy["domains"]
            for objective in domain["objectives"]
        ]
        self.assertEqual(14, len(objective_ids))
        self.assertEqual(14, len(set(objective_ids)))
        details = {row["id"]: row for row in taxonomy["objective_details"]}
        self.assertEqual(set(objective_ids), set(details))
        leaves = [leaf["id"] for row in details.values() for leaf in row["leaf_skills"]]
        self.assertEqual(58, len(leaves))
        self.assertEqual(58, len(set(leaves)))

    def test_objective_ownership_matches_frozen_phase1_design(self):
        taxonomy = load_taxonomy()
        owners = {
            objective: domain["id"]
            for domain in taxonomy["domains"]
            for objective in domain["objectives"]
        }
        self.assertEqual("microsoft_entra", owners["entra_authentication"])
        self.assertEqual("microsoft_security_solutions", owners["defender_xdr"])
        self.assertEqual(
            "microsoft_compliance_solutions",
            owners["purview_information_protection_lifecycle"],
        )


if __name__ == "__main__":
    unittest.main()
