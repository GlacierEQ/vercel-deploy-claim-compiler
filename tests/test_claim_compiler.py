from __future__ import annotations

import unittest

from src.claim_compiler import (
    Claim,
    ClaimStrength,
    DeployClaimCompiler,
    EvidenceReceipt,
)


class CompilerTests(unittest.TestCase):
    def test_blocks_deployed_without_linked_deploy(self):
        compiler = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", True, "dpl_1", "sha_other"),
            ]
        )
        result = compiler.compile(
            [Claim("Deployed system", ClaimStrength.DEPLOYED)]
        )
        self.assertEqual(result.max_supported_strength, ClaimStrength.TESTED)
        self.assertEqual(len(result.blocked), 1)

    def test_blocks_production_without_linked_uptime(self):
        compiler = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", True, "dpl_1", "sha_abc"),
                EvidenceReceipt("uptime", True, "uptime_1", "dpl_other"),
            ]
        )
        result = compiler.compile(
            [Claim("Verified production system", ClaimStrength.PRODUCTION_VERIFIED)]
        )
        self.assertEqual(result.max_supported_strength, ClaimStrength.DEPLOYED)
        self.assertEqual(len(result.blocked), 1)

    def test_allows_production_only_on_complete_chain(self):
        compiler = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", True, "dpl_1", "sha_abc"),
                EvidenceReceipt("uptime", True, "uptime_1", "dpl_1"),
            ]
        )
        result = compiler.compile(
            [Claim("Verified production system", ClaimStrength.PRODUCTION_VERIFIED)]
        )
        self.assertEqual(
            result.max_supported_strength, ClaimStrength.PRODUCTION_VERIFIED
        )
        self.assertEqual(len(result.allowed), 1)
        self.assertEqual(len(result.supporting_receipt_fingerprints), 3)

    def test_allows_tested(self):
        compiler = DeployClaimCompiler(
            [EvidenceReceipt("unit_tests", True, "sha_abc")]
        )
        result = compiler.compile(
            [Claim("17/17 tests passed", ClaimStrength.TESTED)]
        )
        self.assertEqual(len(result.allowed), 1)
        self.assertEqual(len(result.blocked), 0)

    def test_failed_receipts_do_not_support_chain(self):
        compiler = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", False, "dpl_1", "sha_abc"),
                EvidenceReceipt("uptime", True, "uptime_1", "dpl_1"),
            ]
        )
        self.assertEqual(compiler.max_strength(), ClaimStrength.TESTED)

    def test_receipt_order_does_not_change_graph_or_report_identity(self):
        receipts = [
            EvidenceReceipt("unit_tests", True, "sha_abc"),
            EvidenceReceipt("deploy", True, "dpl_1", "sha_abc"),
            EvidenceReceipt("uptime", True, "uptime_1", "dpl_1"),
        ]
        claim = [Claim("Verified production system", ClaimStrength.PRODUCTION_VERIFIED)]
        first = DeployClaimCompiler(receipts).compile(claim)
        second = DeployClaimCompiler(reversed(receipts)).compile(claim)
        self.assertEqual(
            first.evidence_graph_fingerprint, second.evidence_graph_fingerprint
        )
        self.assertEqual(first.report_fingerprint, second.report_fingerprint)

    def test_graph_identity_changes_when_linkage_changes(self):
        first = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", True, "dpl_1", "sha_abc"),
            ]
        )
        second = DeployClaimCompiler(
            [
                EvidenceReceipt("unit_tests", True, "sha_abc"),
                EvidenceReceipt("deploy", True, "dpl_1", "sha_other"),
            ]
        )
        self.assertNotEqual(
            first.evidence_graph_fingerprint, second.evidence_graph_fingerprint
        )
        self.assertEqual(first.max_strength(), ClaimStrength.DEPLOYED)
        self.assertEqual(second.max_strength(), ClaimStrength.TESTED)

    def test_deploy_and_uptime_require_subject_linkage(self):
        with self.assertRaisesRegex(ValueError, "require subject_ref"):
            DeployClaimCompiler([EvidenceReceipt("deploy", True, "dpl_1")])
        with self.assertRaisesRegex(ValueError, "require subject_ref"):
            DeployClaimCompiler([EvidenceReceipt("uptime", True, "up_1")])

    def test_test_receipt_cannot_claim_subject_linkage(self):
        with self.assertRaisesRegex(ValueError, "must not declare subject_ref"):
            DeployClaimCompiler(
                [EvidenceReceipt("unit_tests", True, "sha_abc", "other")]
            )

    def test_duplicate_receipt_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate receipt identity"):
            DeployClaimCompiler(
                [
                    EvidenceReceipt("unit_tests", True, "sha_abc"),
                    EvidenceReceipt("unit_tests", False, "sha_abc"),
                ]
            )

    def test_unknown_receipt_type_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown receipt type"):
            DeployClaimCompiler([EvidenceReceipt("mystery", True, "x")])

    def test_empty_claim_text_refused(self):
        compiler = DeployClaimCompiler(
            [EvidenceReceipt("unit_tests", True, "sha_abc")]
        )
        with self.assertRaisesRegex(ValueError, "claim text must be non-empty"):
            compiler.compile([Claim("  ", ClaimStrength.TESTED)])


if __name__ == "__main__":
    unittest.main()
