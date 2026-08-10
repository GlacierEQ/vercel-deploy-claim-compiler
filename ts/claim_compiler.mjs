import crypto from "node:crypto";

export const Strength = {
  MARKETING: 0,
  TESTED: 1,
  DEPLOYED: 2,
  PRODUCTION_VERIFIED: 3,
};

const RECEIPT_TYPES = new Set(["unit_tests", "e2e", "deploy", "uptime"]);
const TEST_TYPES = new Set(["unit_tests", "e2e"]);

function digest(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function validateReceipts(receipts) {
  const seen = new Set();
  for (const receipt of receipts) {
    if (!RECEIPT_TYPES.has(receipt.type)) throw new Error(`unknown receipt type: ${receipt.type}`);
    if (typeof receipt.ok !== "boolean") throw new Error("receipt ok must be boolean");
    if (typeof receipt.ref !== "string" || !receipt.ref.trim()) throw new Error("receipt ref must be non-empty");
    const key = `${receipt.type}:${receipt.ref}`;
    if (seen.has(key)) throw new Error(`duplicate receipt identity: ${key}`);
    seen.add(key);
    if (TEST_TYPES.has(receipt.type)) {
      if (receipt.subject_ref !== undefined && receipt.subject_ref !== null)
        throw new Error("test receipts must not declare subject_ref");
    } else if (typeof receipt.subject_ref !== "string" || !receipt.subject_ref.trim()) {
      throw new Error(`${receipt.type} receipts require subject_ref linkage`);
    }
  }
}

function canonicalReceipts(receipts) {
  return [...receipts].sort((a, b) => {
    const ak = [a.type, a.ref, a.subject_ref ?? "", String(a.ok)];
    const bk = [b.type, b.ref, b.subject_ref ?? "", String(b.ok)];
    return ak.join("\u0000").localeCompare(bk.join("\u0000"));
  });
}

function receiptFingerprint(receipt) {
  return digest({
    type: receipt.type,
    ok: receipt.ok,
    ref: receipt.ref,
    subject_ref: receipt.subject_ref ?? null,
  });
}

export function bestSupport(receipts) {
  validateReceipts(receipts);
  const canonical = canonicalReceipts(receipts);
  const graphFingerprint = digest(canonical.map(r => ({
    type: r.type,
    ok: r.ok,
    ref: r.ref,
    subject_ref: r.subject_ref ?? null,
    fingerprint: receiptFingerprint(r),
  })));
  const tests = canonical.filter(r => r.ok && TEST_TYPES.has(r.type));
  const deploys = canonical.filter(r => r.ok && r.type === "deploy");
  const uptimes = canonical.filter(r => r.ok && r.type === "uptime");

  const production = [];
  const deployed = [];
  const tested = tests.map(t => [t]);
  for (const test of tests) {
    for (const deploy of deploys) {
      if (deploy.subject_ref !== test.ref) continue;
      deployed.push([test, deploy]);
      for (const uptime of uptimes) {
        if (uptime.subject_ref === deploy.ref) production.push([test, deploy, uptime]);
      }
    }
  }
  const key = chain => chain.map(r => `${r.type}:${r.ref}`).join("\u0000");
  const pick = chains => [...chains].sort((a, b) => key(a).localeCompare(key(b)))[0];
  if (production.length) return { max: "PRODUCTION_VERIFIED", chain: pick(production), graphFingerprint };
  if (deployed.length) return { max: "DEPLOYED", chain: pick(deployed), graphFingerprint };
  if (tested.length) return { max: "TESTED", chain: pick(tested), graphFingerprint };
  return { max: "MARKETING", chain: [], graphFingerprint };
}

export function maxStrength(receipts) {
  return bestSupport(receipts).max;
}

export function compile(receipts, claims) {
  const support = bestSupport(receipts);
  const maxR = Strength[support.max];
  const allowed = [];
  const blocked = [];
  for (const claim of claims) {
    if (!(claim.strength in Strength)) throw new Error("unknown claim strength");
    if (typeof claim.text !== "string" || !claim.text.trim()) throw new Error("claim text must be non-empty");
    const rank = Strength[claim.strength];
    if (rank <= maxR) allowed.push(claim);
    else blocked.push({ claim, reason: `NEEDS_AT_LEAST_${claim.strength}_HAVE_${support.max}` });
  }
  const supportingReceiptFingerprints = support.chain.map(receiptFingerprint);
  const report = {
    max: support.max,
    allowed: allowed.map(c => ({ text: c.text, strength: c.strength })),
    blocked: blocked.map(x => ({ text: x.claim.text, strength: x.claim.strength, reason: x.reason })),
    evidence_graph_fingerprint: support.graphFingerprint,
    supporting_receipt_fingerprints: supportingReceiptFingerprints,
  };
  return {
    max: support.max,
    allowed,
    blocked,
    evidenceGraphFingerprint: support.graphFingerprint,
    supportingReceiptFingerprints,
    reportFingerprint: digest(report),
  };
}
