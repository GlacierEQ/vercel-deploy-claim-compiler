from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text())


CANONICAL = load("machine/canonical-position.json")
CAPABILITIES = load("machine/capabilities.json")
TARGET = load("machine/target-contract.json")
STATE = load("machine/excellence-state.json")
PROOF = load("machine/canonical-position-proof.json")


class CanonicalPositionContractTests(unittest.TestCase):
    def test_repository_owns_evidence_graph_claim_compilation(self):
        self.assertEqual(CANONICAL["role"], "CANONICAL_SPECIALIST")
        self.assertEqual(
            CANONICAL["owns"], "evidence_graph_bound_deploy_claim_compilation"
        )
        self.assertIn("external deployment execution", CANONICAL["does_not_own"])
        self.assertIn(
            "external Vercel state verification", CANONICAL["does_not_own"]
        )

    def test_sibling_relationships_are_not_inflated_to_integration(self):
        for edge in CANONICAL["relationships"]:
            self.assertFalse(edge["integration_exercised"])

    def test_capabilities_are_repository_native(self):
        capabilities = set(CAPABILITIES["capabilities"])
        self.assertNotIn("hyper-scaling", capabilities)
        self.assertIn("coherent_test_deploy_uptime_chain", capabilities)
        self.assertIn("receipt_linkage_validation", capabilities)
        self.assertIn("order_independent_evidence_graph_fingerprint", capabilities)
        self.assertIn("python_node_claim_compiler_parity", capabilities)

    def test_machine_state_is_evolving_after_exact_proof(self):
        self.assertEqual(TARGET["current"]["state"], "EVOLVING")
        self.assertTrue(TARGET["current"]["canonical_position_resolved"])
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(
            STATE["gates"]["CANONICAL_POSITION_RESOLVED"]["status"], "PASS"
        )

    def test_proof_binds_exact_tested_source_and_run(self):
        self.assertEqual(
            PROOF["source_sha"],
            "5cdfaba8db55ae2e3bf66e5ebac38159f61542ea",
        )
        self.assertEqual(PROOF["workflow"]["run_id"], 31399843701)
        self.assertEqual(PROOF["workflow"]["conclusion"], "success")
        self.assertEqual(set(PROOF["workflow"]["jobs"]), {"py", "node"})

    def test_truth_boundary_excludes_external_runtime_claims(self):
        boundary = CAPABILITIES["truth_boundary"]
        self.assertIn("does not execute deployments", boundary)
        self.assertIn("verify external Vercel state", boundary)
        self.assertIn("Vercel affiliation/adoption", boundary)


if __name__ == "__main__":
    unittest.main()
