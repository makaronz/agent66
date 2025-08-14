# Project Structure

## Root Level Organization

### Frontend (React/TypeScript)
- `src/` - React application source code
- `public/` - Static assets and HTML template
- `dist/` - Built frontend assets (generated)

### Backend API (Node.js/Express)
- `api/` - Express.js API server and routes
- `api/middleware/` - Authentication and request middleware
- `api/routes/` - API endpoint definitions
- `api/types/` - TypeScript type definitions

### Trading Engine (Python)
- `main.py` - Main application entry point
- `data_pipeline/` - Market data ingestion and processing
- `smc_detector/` - Smart Money Concepts pattern detection
- `decision_engine/` - Trading decision algorithms
- `risk_manager/` - Risk management and position sizing
- `execution_engine/` - Trade execution logic (Python wrapper)
- `monitoring/` - Health monitoring and metrics
- `compliance/` - Regulatory compliance modules
- `training/` - ML model training and validation

### Execution Engine (Rust)
- `src/execution_engine/` - High-performance trade execution
- `src/lib.rs` - Rust library entry point
- `Cargo.toml` - Rust dependencies and configuration

### Configuration & Deployment
- `config.yaml` - Main application configuration
- `deployment/` - Docker Compose and Kubernetes manifests
- `supabase/migrations/` - Database schema migrations
- `tests/` - Python test suite

## Key Conventions

### File Naming
- **Python**: snake_case for modules and functions
- **TypeScript/React**: PascalCase for components, camelCase for utilities
- **Rust**: snake_case following Rust conventions
- **Config files**: kebab-case or standard names (package.json, Cargo.toml)

### Import Patterns
- **React**: Use path aliases (`@/components`, `@/lib`, `@/hooks`)
- **Python**: Relative imports within modules, absolute for cross-module
- **API**: Centralized type definitions in `api/types/`

### Component Organization
- **React Components**: Group by feature in `src/components/`
- **Pages**: Route components in `src/pages/`
- **Hooks**: Custom hooks in `src/hooks/`
- **Services**: API clients and business logic in `src/services/`

### Configuration Management
- Environment variables for secrets (`.env` files)
- YAML configuration for application settings
- Separate configs for development/production
- Validation for all configuration inputs

### Testing Structure
- **Python**: Tests mirror source structure in `tests/`
- **React**: Co-located test files or `__tests__` directories
- **Rust**: Tests in `src/*/tests/` modules
- Integration tests separate from unit tests

### Docker & Deployment
- Separate Dockerfiles for different services
- Multi-stage builds for optimization
- Docker Compose for local development
- Kubernetes manifests for production deployment

## Module Dependencies

### Data Flow
1. `data_pipeline/` → `smc_detector/` → `decision_engine/` → `risk_manager/` → `execution_engine/`
2. Frontend communicates via `api/` layer
3. Real-time updates through WebSocket connections
4. Monitoring data flows to Prometheus/Grafana

### Critical Paths
- Market data ingestion must be fault-tolerant
- Risk management validates all trade decisions
- Execution engine handles high-frequency operations
- Authentication required for all API access