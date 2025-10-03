# agent66 — TESTS

## Smoke Tests
```bash
# Express health
curl -f http://localhost:3002/api/health
# FastAPI health
curl -f http://localhost:8000/health
# Frontend reachable
open http://localhost:5173
```

## Node / TypeScript
- Unit tests (if `vitest` present):
```bash
pnpm exec vitest run
```
- Lint:
```bash
pnpm exec eslint .
```

## Python
```bash
pytest -q
```

## Contract / API
- Validate OpenAPI spec:
```bash
curl -s http://localhost:3002/api/docs/openapi.json | jq .info
```
- Sample authenticated flow (JWT):
```bash
TOKEN="$(curl -s -X POST http://localhost:3002/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"u":"demo","p":"demo"}' | jq -r .token)"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:3002/api/v1/users/me | jq .
```

## Performance (quick check)
```bash
ab -n 200 -c 20 http://localhost:3002/api/health
```

## Future (V2)
- CI pipeline: lint → type-check → unit/integration tests
- Frontend e2e: Playwright or Cypress
- Contract tests: generate stubs from OpenAPI, verify with Prism
- Load tests: k6 or Locust, gated on staging
