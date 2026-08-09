
from __future__ import annotations
import unittest
from src.claim_compiler import Claim, ClaimStrength, DeployClaimCompiler, EvidenceReceipt

class CompilerTests(unittest.TestCase):
    def test_blocks_production_without_uptime(self):
        c = DeployClaimCompiler([
            EvidenceReceipt("unit_tests", True, "abc"),
            EvidenceReceipt("deploy", True, "dpl_1"),
        ])
        claims = [Claim("Verified production system", ClaimStrength.PRODUCTION_VERIFIED)]
        r = c.compile(claims)
        self.assertEqual(len(r.blocked), 1)
        self.assertEqual(r.max_supported_strength, ClaimStrength.DEPLOYED)

    def test_allows_tested(self):
        c = DeployClaimCompiler([EvidenceReceipt("unit_tests", True, "abc")])
        r = c.compile([Claim("17/17 tests passed", ClaimStrength.TESTED)])
        self.assertEqual(len(r.allowed), 1)
        self.assertEqual(len(r.blocked), 0)

if __name__ == "__main__":
    unittest.main()
