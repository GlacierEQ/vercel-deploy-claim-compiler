
"""Deploy claim compiler — claims cannot exceed evidence receipts."""
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


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class EvidenceReceipt:
    receipt_type: str  # unit_tests | e2e | deploy | uptime
    ok: bool
    ref: str  # commit, deployment id, etc.

    def fingerprint(self) -> str:
        return digest({"type": self.receipt_type, "ok": self.ok, "ref": self.ref})


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
    report_fingerprint: str


class DeployClaimCompiler:
    def __init__(self, receipts: Iterable[EvidenceReceipt]):
        self.receipts = tuple(receipts)

    def max_strength(self) -> ClaimStrength:
        types_ok = {r.receipt_type for r in self.receipts if r.ok}
        if {"unit_tests", "deploy", "uptime"} <= types_ok or {"e2e", "deploy", "uptime"} <= types_ok:
            return ClaimStrength.PRODUCTION_VERIFIED
        if "deploy" in types_ok and ("unit_tests" in types_ok or "e2e" in types_ok):
            return ClaimStrength.DEPLOYED
        if "unit_tests" in types_ok or "e2e" in types_ok:
            return ClaimStrength.TESTED
        return ClaimStrength.MARKETING

    def compile(self, claims: Iterable[Claim]) -> CompileResult:
        max_s = self.max_strength()
        allowed: list[Claim] = []
        blocked: list[tuple[Claim, str]] = []
        for c in claims:
            if _STRENGTH_RANK[c.strength] <= _STRENGTH_RANK[max_s]:
                allowed.append(c)
            else:
                blocked.append((c, f"NEEDS_AT_LEAST_{c.strength.value}_HAVE_{max_s.value}"))
        report = {
            "max": max_s.value,
            "allowed": [c.text for c in allowed],
            "blocked": [(c.text, r) for c, r in blocked],
            "receipts": [r.fingerprint() for r in self.receipts],
        }
        return CompileResult(tuple(allowed), tuple(blocked), max_s, digest(report))
