# agent66 — RUNBOOK

## Start / Stop
- Express API (3002): `pnpm server:dev` (uses `api/server.ts`, nodemon)
- FastAPI (8000): `python -m uvicorn api_fastapi:app --host 0.0.0.0 --port 8000`
- Frontend (5173): `pnpm client:dev`
- Combined (if available): `pnpm dev`

To stop: Ctrl + C in each terminal.

---

## Health & Readiness
- Express: `GET http://localhost:3002/api/health` → 200 OK
- FastAPI: `GET http://localhost:8000/health` → 200 OK
- Docs  
  - Express Swagger: `http://localhost:3002/api/docs`  
  - FastAPI docs: `http://localhost:8000/docs`

---

## Logs
- Express: middleware request logger (see `api/middleware/*`) prints method / path / status.
- Uvicorn: startup banner, access log to stdout.

---

## Common Issues
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `EADDRINUSE` | Port in use | Free 3002/8000/5173 or set `PORT` env |
| CORS errors | Wrong origin | Adjust CORS config in `api/middleware/cors.ts` |
| HTTP 429 | Rate-limit hit (`generalRateLimit`) | Relax policy or throttle client |
| 4xx/5xx | App error | Inspect stack traces & logs |

---

## Troubleshooting Checklist
1. Confirm routes mounted in `api/app.ts`.
2. Verify Vite proxy for `/api` in `vite.config.ts`.
3. Ensure `.env` loaded (copy from `env.example`).
4. Quick probes:
   ```bash
   curl -i http://localhost:3002/api/version
   curl -i http://localhost:3002/api/status
   ```

---

## Backup / Restore (local dev)
No database included by default. If one is configured, snapshot/restore using your DB tooling outside this repo.

---

## Observability
If metrics exporters are enabled:
- Prometheus Node metrics: `/api/metrics` (check `api/server.ts`)
- Python metrics via `prometheus_client` (path defined in `api_fastapi.py`)
- Rust exporter per `Cargo.toml` config

---

## Change Management
Create feature branch → commit → run lint/tests → open PR.  
Do **not** push directly to the default branch.  
Rotate any real keys found by secret scans.
