# agent66 — API

## Overview
Two API surfaces  
• **Express** (TypeScript) — `http://localhost:3002/api/*` (code: `api/app.ts`, `api/routes/*`)  
• **FastAPI** (Python) — `http://localhost:8000/*` (code: `api_fastapi.py`)

---

## Docs
- Express Swagger UI `GET http://localhost:3002/api/docs`  
- Express OpenAPI JSON `GET http://localhost:3002/api/docs/openapi.json`  
- FastAPI interactive docs `GET http://localhost:8000/docs`

---

## Express — Common Endpoints
Health & meta:
```http
GET /api/health
GET /api/version
GET /api/status
```

Versioned API fragments (see `api/routes/v1/`):
```http
POST /api/v1/auth/login
POST /api/v1/auth/mfa/verify
GET  /api/v1/users/me
GET  /api/v1/exchanges/binance/symbols
```

Example:
```bash
curl -s http://localhost:3002/api/health | jq .
```

---

## FastAPI — Common Endpoints
```http
GET /health
```
(Extra ML/analytics endpoints are defined per module imports in `api_fastapi.py`.)

---

## Authentication
JWT flows under `/api/v1/auth/*` (`api/routes/v1/auth/*`).  
Include header: `Authorization: Bearer <token>`.

---

## Errors
- Express uses centralized error handler (`api/middleware/errorHandler.ts`) → JSON `{ message, status }`.
- FastAPI returns JSON error responses; full stack traces in Uvicorn stdout.

---

## Notes
During frontend dev (`vite` on port **5173**), requests to `/api/*` are proxied to `http://localhost:3002` (see `vite.config.ts`).
