# Integration Points Analysis

## React ↔ Node API
- REST endpoints `/api/binance/*`; JWT via Supabase; flows for test‑connection, account‑info, place‑order

## Node ↔ Exchanges (CCXT)
- Direct CCXT calls for status, balance, orders; map errors to HTTP responses; add idempotency & backoff

## Python Services
- Data ingestion → Kafka topics; health + performance monitors; decision/risk pipelines

## Python ↔ Rust Executor
- Bridge TBD; recommend gRPC over Unix domain sockets for low overhead; strict timeouts

## DB and Caching
- Supabase Postgres with RLS; Redis for caching per config; ensure TLS & auth

```mermaid
sequenceDiagram
  participant UI as React
  participant API as Node API
  participant SVC as Python Services
  participant EXE as Rust Executor
  participant DB as Postgres

  UI->>API: POST /api/binance/place-order
  API->>API: Validate JWT/MFA
  API->>EXTERNAL: CCXT create order
  API-->>UI: Order result + DB write (Supabase)
  SVC->>EXE: Execute signal (contract TBD)
  EXE-->>SVC: Result + metrics
```
