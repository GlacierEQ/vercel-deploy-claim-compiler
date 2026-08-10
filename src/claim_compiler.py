"""Deploy claim compiler — claims cannot exceed coherent evidence chains.

A receipt type existing somewhere is not enough. Stronger claims require an
explicit chain from tested artifact -> deployment -> uptime observation.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ClaimStrength(str, Enum):
    MARKETING = "MARKETING"
    TESTED = "TESTED"
    DEPLOYED = "DEPLOYED"
    PRODUCTION_VERIFIED = "PRODUCTION_VERIFIED"


_STRENGTH_RANK = {
    ClaimStrength.MARKETING: 0,
    ClaimStrength.TESTED: 1,
    ClaimStrength.DEPLOYED: 2,
    ClaimStrength.PRODUCTION_VERIFIED: 3,
}
_ALLOWED_RECEIPT_TYPES = frozenset({"unit_tests", "e2e", "deploy", "uptime"})
_TEST_RECEIPT_TYPES = frozenset({"unit_tests", "e2e"})


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class EvidenceReceipt:
    receipt_type: str  # unit_tests | e2e | deploy | uptime
    ok: bool
    ref: str  # receipt-local identity: commit, deployment id, observation id
    subject_ref: str | None = None  # deploy -> tested ref; uptime -> deployment ref

    def fingerprint(self) -> str:
        return digest(
            {
                "type": self.receipt_type,
                "ok": self.ok,
                "ref": self.ref,
                "subject_ref": self.subject_ref,
            }
        )


@dataclass(frozen=True)
class Claim:
    text: str
    strength: ClaimStrength

    @staticmethod
    def parse_many(blob: str) -> list["Claim"]:
        """Heuristic parser for portfolio language."""
        claims: list[Claim] = []
        for line in blob.splitlines():
            t = line.strip()
            if not t:
                continue
            low = t.lower()
            if "production verified" in low or "verified production" in low:
                claims.append(Claim(t, ClaimStrength.PRODUCTION_VERIFIED))
            elif "deployed" in low or "live on" in low:
                claims.append(Claim(t, ClaimStrength.DEPLOYED))
            elif "tests passed" in low or re.search(r"\d+/\d+", t):
                claims.append(Claim(t, ClaimStrength.TESTED))
            else:
                claims.append(Claim(t, ClaimStrength.MARKETING))
        return claims


@dataclass(frozen=True)
class CompileResult:
    allowed: tuple[Claim, ...]
    blocked: tuple[tuple[Claim, str], ...]
    max_supported_strength: ClaimStrength
    supporting_receipt_fingerprints: tuple[str, ...]
    evidence_graph_fingerprint: str
    report_fingerprint: str


class DeployClaimCompiler:
    def __init__(self, receipts: Iterable[EvidenceReceipt]):
        self.receipts = tuple(receipts)
        self._validate_receipts()
        self._canonical_receipts = tuple(
            sorted(
                self.receipts,
                key=lambda r: (
                    r.receipt_type,
                    r.ref,
                    r.subject_ref or "",
                    r.ok,
                ),
            )
        )
        self.evidence_graph_fingerprint = digest(
            [
                {
                    "type": r.receipt_type,
                    "ok": r.ok,
                    "ref": r.ref,
                    "subject_ref": r.subject_ref,
                    "fingerprint": r.fingerprint(),
                }
                for r in self._canonical_receipts
            ]
        )

    @staticmethod
    def _nonempty(value: str | None) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _validate_receipts(self) -> None:
        seen: set[tuple[str, str]] = set()
        for receipt in self.receipts:
            if receipt.receipt_type not in _ALLOWED_RECEIPT_TYPES:
                raise ValueError(f"unknown receipt type: {receipt.receipt_type}")
            if not isinstance(receipt.ok, bool):
                raise ValueError("receipt ok must be boolean")
            if not self._nonempty(receipt.ref):
                raise ValueError("receipt ref must be non-empty")
            key = (receipt.receipt_type, receipt.ref)
            if key in seen:
                raise ValueError(
                    f"duplicate receipt identity: {receipt.receipt_type}:{receipt.ref}"
                )
            seen.add(key)

            if receipt.receipt_type in _TEST_RECEIPT_TYPES:
                if receipt.subject_ref is not None:
                    raise ValueError("test receipts must not declare subject_ref")
            elif not self._nonempty(receipt.subject_ref):
                raise ValueError(
                    f"{receipt.receipt_type} receipts require subject_ref linkage"
                )

    def _best_support(self) -> tuple[ClaimStrength, tuple[EvidenceReceipt, ...]]:
        tests = [
            r
            for r in self._canonical_receipts
            if r.ok and r.receipt_type in _TEST_RECEIPT_TYPES
        ]
        deploys = [
            r
            for r in self._canonical_receipts
            if r.ok and r.receipt_type == "deploy"
        ]
        uptimes = [
            r
            for r in self._canonical_receipts
            if r.ok and r.receipt_type == "uptime"
        ]

        production_chains: list[tuple[EvidenceReceipt, ...]] = []
        deployed_chains: list[tuple[EvidenceReceipt, ...]] = []
        tested_chains: list[tuple[EvidenceReceipt, ...]] = []

        for test in tests:
            tested_chains.append((test,))
            for deploy in deploys:
                if deploy.subject_ref != test.ref:
                    continue
                deployed_chains.append((test, deploy))
                for uptime in uptimes:
                    if uptime.subject_ref == deploy.ref:
                        production_chains.append((test, deploy, uptime))

        def chain_key(chain: tuple[EvidenceReceipt, ...]) -> tuple[str, ...]:
            return tuple(f"{r.receipt_type}:{r.ref}" for r in chain)

        if production_chains:
            return ClaimStrength.PRODUCTION_VERIFIED, min(
                production_chains, key=chain_key
            )
        if deployed_chains:
            return ClaimStrength.DEPLOYED, min(deployed_chains, key=chain_key)
        if tested_chains:
            return ClaimStrength.TESTED, min(tested_chains, key=chain_key)
        return ClaimStrength.MARKETING, ()

    def max_strength(self) -> ClaimStrength:
        strength, _ = self._best_support()
        return strength

    def compile(self, claims: Iterable[Claim]) -> CompileResult:
        claim_list = tuple(claims)
        for claim in claim_list:
            if not isinstance(claim.strength, ClaimStrength):
                raise ValueError("claim strength must be ClaimStrength")
            if not claim.text.strip():
                raise ValueError("claim text must be non-empty")

        max_s, support = self._best_support()
        support_fingerprints = tuple(r.fingerprint() for r in support)
        allowed: list[Claim] = []
        blocked: list[tuple[Claim, str]] = []
        for claim in claim_list:
            if _STRENGTH_RANK[claim.strength] <= _STRENGTH_RANK[max_s]:
                allowed.append(claim)
            else:
                blocked.append(
                    (
                        claim,
                        f"NEEDS_AT_LEAST_{claim.strength.value}_HAVE_{max_s.value}",
                    )
                )

        report = {
            "max": max_s.value,
            "allowed": [
                {"text": c.text, "strength": c.strength.value} for c in allowed
            ],
            "blocked": [
                {
                    "text": c.text,
                    "strength": c.strength.value,
                    "reason": reason,
                }
                for c, reason in blocked
            ],
            "evidence_graph_fingerprint": self.evidence_graph_fingerprint,
            "supporting_receipt_fingerprints": list(support_fingerprints),
        }
        return CompileResult(
            tuple(allowed),
            tuple(blocked),
            max_s,
            support_fingerprints,
            self.evidence_graph_fingerprint,
            digest(report),
        )
