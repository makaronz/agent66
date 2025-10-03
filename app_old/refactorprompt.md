### Role
Act as an experienced full-stack principal engineer specializing in Python/TypeScript, FastAPI/Express, React/Vite with expertise in offline-first applications, performance optimization, and developer experience.

### Task
Refactor and stabilize the SMC Trading Agent - a complex multi-language trading system with React frontend, Express/FastAPI backends, and Rust execution engine - fixing critical build/runtime blockers, import errors, configuration inconsistencies, and implementing offline-first architecture with comprehensive testing.

### Context
- Repository scope: Complete multi-service trading application (Frontend: React+Vite+TS, API Gateway: Express+TS, Trading Engine: FastAPI+Python, Execution: Rust)
- **Critical Issues Identified:**
  - `src/components/ErrorBoundary.tsx` — Missing proper error handling; needs structured error reporting
  - `config.yaml` — Duplicate JWT_SECRET keys (lines 200, 202); inconsistent environment variable handling
  - `package.json` — Complex dependency tree with potential conflicts; missing offline-first scripts
  - `main.py` — Mock services for offline mode but no proper service discovery; missing health checks
  - `api_fastapi.py` — Minimal implementation; lacks proper error handling and validation
  - `vite.config.ts` — Over-optimized build config; missing offline service worker configuration
  - Import errors in data pipeline (`exchange_connectors` exports missing)
  - Configuration validation inconsistencies across Python/TypeScript boundaries
  - Missing unified environment variable schema validation
  - No proper offline-first data persistence layer
  - Incomplete test coverage for critical trading components
  - Security vulnerabilities in dependency chain (identified via Trivy scans)
  - Performance bottlenecks in WebSocket connection management
  - Missing graceful degradation for network failures

### Expected Output
- Provide a **unified diff patch** for all critical fixes
- Implement centralized configuration management with Zod/Pydantic schema validation
- Add comprehensive error boundaries and structured logging
- Create offline-first service worker and data persistence
- Fix all import errors and dependency conflicts
- Add unit/e2e tests proving offline functionality
- Implement health checks and monitoring endpoints
- No external network calls after setup script execution

### Guidance for Codex
1. **Structured CoT**: Analyze configuration → Fix imports → Implement offline-first → Add tests
2. **Self-critique**: Generate solution → Review for offline compliance → Optimize for performance
3. **Priority order**: Critical blockers → Configuration → Testing → Performance
4. **Token efficiency**: Focus on high-impact changes; summarize large file modifications
5. **Security**: Never expose secrets; implement proper validation at all boundaries

### Setup Script
```bash
#!/bin/bash
# Offline-first setup for SMC Trading Agent
set -e

# Install Node.js dependencies
npm ci --prefer-offline

# Install Python dependencies with offline capability
pip install -r requirements.txt --cache-dir .pip-cache

# Build Rust components
cargo build --release

# Generate offline configuration
cp .env.example .env.local
echo "OFFLINE_MODE=true" >> .env.local
echo "MOCK_EXCHANGES=true" >> .env.local

# Initialize offline database
python -c "from database.connection_pool import initialize_pool; initialize_pool('smc_offline.db', 5)"

# Build frontend with offline service worker
npm run build

echo "✅ Offline setup complete. Run 'npm run dev:offline' to start."
```

### Quality Gates
- ✅ Builds and starts locally (frontend + all backends) with zero network dependency
- ✅ TypeScript/Python type-checking passes (tsc --noEmit, mypy)
- ✅ All linting passes (ESLint, ruff, Prettier)
- ✅ Unit tests achieve 90%+ coverage offline
- ✅ Integration tests pass with mock exchanges
- ✅ Performance: <2s initial load, <100ms API responses
- ✅ Security: No secrets in code, input validation at boundaries

### End