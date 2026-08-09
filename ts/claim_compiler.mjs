/** Babel: TypeScript-domain claim compiler (ESM for Node without tsc). Vercel-native surface. */
export const Strength = { MARKETING: 0, TESTED: 1, DEPLOYED: 2, PRODUCTION_VERIFIED: 3 };

export function maxStrength(receipts) {
  const ok = new Set(receipts.filter(r => r.ok).map(r => r.type));
  if ((ok.has("unit_tests") || ok.has("e2e")) && ok.has("deploy") && ok.has("uptime"))
    return "PRODUCTION_VERIFIED";
  if (ok.has("deploy") && (ok.has("unit_tests") || ok.has("e2e"))) return "DEPLOYED";
  if (ok.has("unit_tests") || ok.has("e2e")) return "TESTED";
  return "MARKETING";
}

export function compile(receipts, claims) {
  const max = maxStrength(receipts);
  const maxR = Strength[max];
  const allowed = [], blocked = [];
  for (const c of claims) {
    const s = Strength[c.strength] ?? 0;
    if (s <= maxR) allowed.push(c);
    else blocked.push({ claim: c, reason: `NEEDS_${c.strength}_HAVE_${max}` });
  }
  return { max, allowed, blocked };
}
