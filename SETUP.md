# agent66 — SETUP

## Prerequisites
- Node.js ≥ 18 with Corepack enabled (pnpm per `packageManager` in package.json)
- Python 3 (venv recommended)
- Rust toolchain (rustup, cargo)
- Git, jq, curl

## Clone & Directory
```bash
cd /Users/arkadiuszfudali/Git
# repo assumed present as `agent66/`
cd agent66
```

## Node setup (frontend + Express)
```bash
corepack enable
pnpm install
```
- Dev ports: 5173 (Vite), 3002 (Express)
- Vite dev proxy: `/api` → `http://localhost:3002` (see `vite.config.ts`)

## Python setup (FastAPI & ML)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
```
- Dev port: 8000 (uvicorn)

## Rust setup (optional workers)
```bash
rustup toolchain install stable
cargo build
```

## Environment
- Copy and edit env example (names only shown):
```bash
cp env.example .env
# Fill values for: BINANCE_API_KEY, BINANCE_API_SECRET, DATABASE_URL, REDIS_URL, LOG_LEVEL, PROMETHEUS_PORT, GRAFANA_PORT, NODE_ENV, ...
```
Do not commit `.env`.

## Quickstart (local dev)
Terminal A — Express API (3002):
```bash
pnpm server:dev
```
Terminal B — FastAPI (8000):
```bash
python -m uvicorn api_fastapi:app --host 0.0.0.0 --port 8000
```
Terminal C — Frontend (5173, proxies to 3002):
```bash
pnpm client:dev
```

Alternatively, run combined scripts if available:
```bash
pnpm dev
```

## Smoke checks
```bash
curl -f http://localhost:3002/api/health
curl -f http://localhost:8000/health
open http://localhost:5173
```

## Build
```bash
pnpm build
```
- Output: `dist/` (frontend)

## Notes
- Use separate shells for API, FastAPI, and frontend during development.
- Ensure ports 3002, 8000, 5173 are free.
