# agent66 — SECURITY NOTES

## Threats (high level)
- Credential exposure (exchange API keys, DB URLs)
- Injection (JSON bodies, query, path)
- XSS/CSRF (web UI), CORS misconfig
- Abuse (bruteforce, scraping) → rate-limit

## In-Code Controls (Express)
- CORS policy — `api/middleware/*` (see `corsOptions`)
- Security headers — helmet via `securityHeaders`
- Input sanitization — `sanitizeInput`
- Rate limiting — `generalRateLimit`
- Central error handler — `errorHandler`
- Swagger behind `/api/docs` (read-only)

## Python & Rust
- FastAPI default validation; add Pydantic models for inputs
- Metrics via Prometheus libs; ensure ports not exposed publicly
- Rust uses `tracing`, `thiserror` — prefer structured errors, avoid panics

## Secrets Management
- Example names in `env.example`; do not commit real values
- Suggested local pattern: `.env` loaded by Node/Python
- Rotation: if any key was ever committed or shared, rotate immediately

## Validation Steps (local)
```bash
# CORS & headers
curl -I http://localhost:3002/api/health | sed -n '1,15p'

# Swagger reachable (should render, not modify state)
open http://localhost:3002/api/docs

# Rate-limit check (expect 429 on burst)
ab -n 200 -c 50 http://localhost:3002/api/health
```

## Build/Deploy Guidance (V2)
- Store secrets in OS keychain or .env + dotenv-vault for local, and in cloud secret manager for prod
- Enforce HTTPS and HSTS at the edge; set secure cookies if any session used
- Enable audit logs for auth endpoints; monitor 4xx/5xx and 429 rates
