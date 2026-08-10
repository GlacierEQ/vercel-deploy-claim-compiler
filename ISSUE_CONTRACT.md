# ISSUE CONTRACT
## Pain
Sites claim `tested`, `deployed`, or `production verified` from unrelated receipts that happen to have the right types.

## Success
- Claim strength is bounded by one coherent evidence chain
- `TESTED`: successful unit/e2e receipt for an exact artifact ref
- `DEPLOYED`: successful deploy receipt explicitly points to that tested artifact ref
- `PRODUCTION_VERIFIED`: successful uptime receipt explicitly points to that deployment ref
- Missing, failed, malformed, duplicate, or unrelated receipts cannot be composed into a stronger claim
- Evidence graph + supporting chain are deterministically fingerprinted

## Nonclaims
- Citation/evidence binding does not prove application correctness beyond supplied receipts
- No production deployment or Vercel affiliation/adoption is implied by this reference mechanism
