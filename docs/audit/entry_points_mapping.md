# Entry Points Mapping

## Overview
Entry points and their runtime characteristics across the stack.

### Python Backend – `smc_trading_agent/main.py`
- Purpose: Orchestrates services, health monitor, trading loop
- Ports: monitoring FastAPI server from `config.yaml` → `monitoring.port` (default 8008)
- Env: `.env` variables loaded by `load_secure_config` (e.g., exchange API keys, DB creds)
- Integration: `ServiceManager`, `EnhancedHealthMonitor`, data ingestion, detector, decision engine, risk manager, execution engine (Rust bridge TBD)
- Startup: `main()` → `asyncio.run(main_async())`

### Node API – `smc_trading_agent/api/server.ts`
- Purpose: Express server for API routes
- Port: `PORT` env or 3002
- Auth: Supabase token validation in `api/middleware/auth.ts`
- Integration: Routes in `api/routes/binance.ts` use CCXT to access Binance; optional DB writes via Supabase client

### React Frontend – `smc_trading_agent/src/main.tsx`
- Purpose: Bootstraps UI via Vite; renders `<App/>` with `ErrorBoundary`
- Integration: Calls Node API endpoints; displays realtime data (future alignment to WS endpoints)

## Flow Sketch
```mermaid
flowchart TD
  A[Browser] -- HTTP --> B[React (Vite)]
  B -- REST/WS --> C[Node API]
  C -- internal API / events --> D[Python Services]
  D -- FFI/IPC/API --> E[Rust Executor]
  D -- Kafka --> K[Stream]
  D -- DB --> P[Postgres (Supabase)]
```

## Configuration and Environment
- `smc_trading_agent/config.yaml` governs exchanges, Kafka, risk manager, monitoring, DB, Redis, API, security
- Sensitive env set via `.env` and environment variables in containers/CI

## Route and Service Mapping (Examples)
- Node `POST /api/binance/test-connection` → CCXT `exchange.fetchStatus()` + `fetchBalance()`
- Node `POST /api/binance/place-order` → CCXT order; optional Supabase insert into `trades`
- Python `/metrics` (Prometheus) via `EnhancedHealthMonitor`

## Integration Considerations
- JWT/MFA via Supabase middleware
- Align rate limits and idempotency for order routes
- Define Python↔Rust boundary with explicit contracts and timeouts
