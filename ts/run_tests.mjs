import { compile, maxStrength } from "./claim_compiler.mjs";
import assert from "node:assert/strict";

const r1 = compile(
  [{ type: "unit_tests", ok: true }, { type: "deploy", ok: true }],
  [{ text: "Verified production", strength: "PRODUCTION_VERIFIED" }]
);
assert.equal(r1.blocked.length, 1);
assert.equal(maxStrength([{ type: "unit_tests", ok: true }]), "TESTED");
const r2 = compile([{ type: "unit_tests", ok: true }], [{ text: "17/17", strength: "TESTED" }]);
assert.equal(r2.allowed.length, 1);
console.log("ok");
