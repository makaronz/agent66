# agent66 — ARCHITECTURE

## Overview
agent66 is a multi-runtime application composed of:

| Layer | Tech | Location | Default Dev Port |
|-------|------|----------|------------------|
| Web UI | React + Vite | `agent66/src/` | 5173 |
| REST API | Express (TypeScript) | `agent66/api/` | 3002 |
| Aux API / ML Ops | FastAPI (Python) | `agent66/api_fastapi.py` | 8000 |
| Workers / Engines | Python modules (`agent66/**`) & Rust crate (`Cargo.toml`) | n/a | — |

The Vite dev server proxies `/api/*` to the Express API, keeping a single origin during frontend development.

---

## Ports
* **3002** — Express REST API (`api/server.ts`)
* **8000** — FastAPI (uvicorn) (`api_fastapi.py`)
* **5173** — Vite dev server (`vite.config.ts`)

---

## Key Directories & Files
* **Frontend**
  * `src/main.tsx` – Vite entry
  * `vite.config.ts` – aliases, build, dev proxy
* **Express API (`api/`)**
  * `api/server.ts` – starts HTTP server (`PORT` env, fallback 3002)
  * `api/app.ts` – constructs Express app
  * `api/routes/` – route modules (e.g. `health.ts`, `version.ts`, `auth/`)
  * `api/middleware/` – CORS, security headers, rate-limit, logging
  * `api/services/` – domain & integration logic (Binance, DB, etc.)
* **Python API**
  * `api_fastapi.py` – FastAPI app with health & ML endpoints
  * `requirements.txt` – FastAPI, pandas, tensorflow, etc.
* **Rust**
  * `Cargo.toml` – tokio, tracing, prometheus; binaries / libs under `src/`

---

## Middleware & Security (Express)
Declared in `api/app.ts`, sourced from `api/middleware/`:

* CORS (`corsOptions`)
* Helmet security headers
* Input sanitization
* Request logging
* Rate limiting (`generalRateLimit`)
* Error handler
* Swagger UI at `/api/docs` (OpenAPI JSON `/api/docs/openapi.json`)

---

## Routing (Express)
Typical mounts in `api/app.ts`:

| Route | Purpose | Source file |
|-------|---------|-------------|
| `/api/health` | liveness | `api/routes/health.ts` |
| `/api/version` | git & build info | `api/routes/version.ts` |
| `/api/status` | runtime metrics | `api/routes/status.ts` |
| `/api/v1/*` | versioned business API | `api/routes/v1/` |

---

## FastAPI Surface
`api_fastapi.py` defines:

* `/health` — basic liveness
* ML / analytics endpoints (e.g., `/predict`, `/train`) imported from internal Python modules used by workers.

---

## Frontend Details
* Path aliases: `@`, `@/components`, etc. (see `vite.config.ts`)
* Dev proxy: `server.proxy['/api'] → http://localhost:3002`
* Production build: Rollup manualChunks for vendor splitting, terser minification.

---

## Observability
* **Logging** — winston (Node) + Python logging; traces via `tracing` (Rust)
* **Metrics** — `prometheus-client` (Python) & `prometheus` crate (Rust)
* **Swagger / OpenAPI** — Express `/api/docs`, FastAPI auto-docs at `/docs`

---

## Configuration & Environment
Variable names listed in `env.example`; runtime values supplied via `.env` or deployment secrets. Key categories:

* Exchange keys & secrets
* Database / cache URLs
* Logging & metrics ports
* Environment flags (`NODE_ENV`, etc.)

No secrets are committed to the repository.

---

## External Integrations
* **Crypto exchanges** — `ccxt` via `api/services/exchanges/`
* **Databases** — SQLAlchemy (Python) & potentially Prisma/knex in Node
* **Caching / queues** — Redis via `ioredis` (Node) and `redis` (Python)

---

## Build & Deployment Flow
1. **Frontend**  
   `pnpm --filter agent66 build` → `dist/` static assets
2. **Express API**  
   `pnpm --filter agent66 api:start` (nodemon / ts-node)
3. **FastAPI**  
   `python -m uvicorn api_fastapi:app --port 8000`
4. **Rust workers**  
   `cargo build --release` → invoked by scheduler / Python orchestrator

Docker & compose definitions will be added in V2 migration.
