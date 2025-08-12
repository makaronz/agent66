# Security Gap Assessment

## Current Controls
- Auth: Supabase token verification in `api/middleware/auth.ts`; MFA checks
- DB: RLS policies enforced in `001_initial_schema.sql`
- Config: Secrets expected from env; some placeholders in `config.yaml`

## Gaps
- API Security: Missing rate limiting, request size limits, CSP/Helmet, input validation normalization
- Transport: No mTLS between services; no service‑to‑service auth
- Secrets: No centralized secret store usage (e.g., Vault/SM)
- Key Management: API keys encryption/rotation policy not codified in code

## Recommendations
- Add Helmet/CSP middleware; define strict CSP
- Introduce global rate limiter + per‑route idempotency for order placement
- Adopt mTLS + service identity (SPIFFE/SPIRE or mTLS in mesh)
- Use managed secret store; remove secrets from images
- Harden JWT handling: short TTLs, audience/issuer checks
