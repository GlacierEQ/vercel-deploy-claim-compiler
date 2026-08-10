import assert from "node:assert/strict";
import { bestSupport, compile, maxStrength } from "./claim_compiler.mjs";

const tested = { type: "unit_tests", ok: true, ref: "sha_abc" };
const deploy = { type: "deploy", ok: true, ref: "dpl_1", subject_ref: "sha_abc" };
const uptime = { type: "uptime", ok: true, ref: "up_1", subject_ref: "dpl_1" };

assert.equal(maxStrength([tested]), "TESTED");
assert.equal(maxStrength([tested, deploy]), "DEPLOYED");
assert.equal(maxStrength([tested, deploy, uptime]), "PRODUCTION_VERIFIED");

const unrelatedDeploy = { type: "deploy", ok: true, ref: "dpl_other", subject_ref: "sha_other" };
const blocked = compile(
  [tested, unrelatedDeploy],
  [{ text: "Deployed", strength: "DEPLOYED" }],
);
assert.equal(blocked.max, "TESTED");
assert.equal(blocked.blocked.length, 1);

const production = compile(
  [uptime, tested, deploy],
  [{ text: "Verified production", strength: "PRODUCTION_VERIFIED" }],
);
assert.equal(production.allowed.length, 1);
assert.equal(production.supportingReceiptFingerprints.length, 3);

const reordered = compile(
  [deploy, uptime, tested],
  [{ text: "Verified production", strength: "PRODUCTION_VERIFIED" }],
);
assert.equal(production.evidenceGraphFingerprint, reordered.evidenceGraphFingerprint);
assert.equal(production.reportFingerprint, reordered.reportFingerprint);

const support = bestSupport([tested, deploy, uptime]);
assert.equal(support.chain.length, 3);

assert.throws(() => maxStrength([{ type: "deploy", ok: true, ref: "dpl_1" }]), /require subject_ref/);
assert.throws(() => maxStrength([{ type: "mystery", ok: true, ref: "x" }]), /unknown receipt type/);
assert.throws(
  () => compile([tested], [{ text: "", strength: "TESTED" }]),
  /claim text must be non-empty/,
);

console.log("ok");
