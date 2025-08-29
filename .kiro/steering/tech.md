# SMC Trading Agent - Technology Stack

## Architecture Overview

Multi-language microservices architecture optimized for performance, scalability, and maintainability:

- **Frontend**: React + TypeScript + Vite
- **API Gateway**: Node.js + Express + TypeScript
- **Trading Engine**: Python (FastAPI) with ML/AI capabilities
- **Execution Engine**: Rust for high-performance order execution
- **Database**: PostgreSQL with Supabase + TimescaleDB for time-series data
- **Cache**: Redis for session management and real-time data
- **Message Queue**: Kafka for event streaming and data pipeline
- **Deployment**: Vercel (Frontend), Kubernetes (Backend), Docker containers

## Frontend Stack

### Core Technologies

- **React 18.3+**: Component-based UI with hooks and context
- **TypeScript**: Type-safe development with strict configuration
- **Vite**: Fast build tool with HMR and optimized bundling
- **Tailwind CSS**: Utility-first styling with custom design system
- **Framer Motion**: Smooth animations and transitions

### Key Libraries

- **State Management**: Zustand for global state, React Query for server state
- **Routing**: React Router DOM v7 with lazy loading
- **Forms**: React Hook Form with Zod validation
- **UI Components**: Headless UI, Heroicons, Lucide React
- **Charts**: Recharts for trading visualizations
- **Authentication**: Supabase Auth with MFA support

### Build Configuration

```bash
# Development
npm run client:dev    # Start Vite dev server (port 5173)
npm run server:dev    # Start API gateway (port 3000)
npm run dev          # Start both frontend and API

# Production Build
npm run build        # TypeScript compilation + Vite build
npm run preview      # Preview production build
```

## Backend Stack

### Python Trading Engine

- **FastAPI**: High-performance async API framework
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: ORM with async support
- **Pandas + NumPy**: Data analysis and numerical computing
- **Scikit-learn**: Machine learning models
- **TensorFlow/PyTorch**: Deep learning for pattern recognition

### Node.js API Gateway

- **Express**: Web framework with TypeScript
- **Helmet**: Security headers and middleware
- **CORS**: Cross-origin resource sharing
- **Rate Limiting**: Redis-backed request throttling
- **JWT**: Authentication and authorization
- **Swagger**: API documentation generation

### Rust Execution Engine

- **Tokio**: Async runtime for high-performance I/O
- **Serde**: Serialization/deserialization
- **CCXT-RS**: Exchange connectivity
- **Prometheus**: Metrics collection
- **Tracing**: Structured logging and observability

## Database & Storage

### Primary Database

- **PostgreSQL 14+**: ACID-compliant relational database
- **Supabase**: Managed PostgreSQL with real-time subscriptions
- **TimescaleDB**: Time-series extension for market data

### Caching & Sessions

- **Redis 6+**: In-memory data store for caching and sessions
- **Connection Pooling**: PgBouncer for database connections

### Data Pipeline

- **Kafka**: Event streaming for real-time data processing
- **Exchange APIs**: Direct integration with Binance, Bybit, Oanda
- **WebSocket**: Real-time market data feeds

## Development Tools

### Code Quality

```bash
# Linting & Formatting
npm run lint         # ESLint for TypeScript/JavaScript
npm run format       # Prettier code formatting
npm run type-check   # TypeScript type checking

# Python Quality
black .              # Code formatting
isort .              # Import sorting
flake8 .             # Linting
mypy .               # Type checking
```

### Testing

```bash
# Frontend Tests
npm test             # Vitest unit tests
npm run test:e2e     # End-to-end tests

# Backend Tests
pytest               # Python unit/integration tests
cargo test           # Rust unit tests
npm run test:api     # API contract tests
```

### Security & Compliance

```bash
# Security Scanning
npm run security:scan     # Trivy + Semgrep scanning
npm run security:check    # Quick vulnerability check
npm run sbom:generate     # Generate Software Bill of Materials

# Dependency Management
npm audit                 # Node.js dependency audit
pip-audit                 # Python dependency audit
cargo audit               # Rust dependency audit
```

## Common Development Commands

### Environment Setup

```bash
# Initial setup
git clone <repository-url>
cd smc_trading_agent

# Install dependencies
npm install              # Node.js dependencies
pip install -r requirements.txt  # Python dependencies
cargo build             # Rust dependencies

# Environment configuration
cp .env.example .env    # Copy environment template
# Edit .env with your configuration
```

### Development Workflow

```bash
# Start development environment
npm run dev             # All services
python main.py          # Python trading engine only
cargo run               # Rust execution engine only

# Database operations
npm run db:migrate      # Run database migrations
npm run db:seed         # Seed development data
npm run db:reset        # Reset database
```

### Build & Deployment

```bash
# Production builds
npm run build           # Frontend production build
docker-compose up -d    # Local containerized environment

# Deployment
npm run deploy:vercel   # Deploy to Vercel
kubectl apply -f deployment/k8s/  # Deploy to Kubernetes
```

## Configuration Management

### Environment Variables

- **Development**: `.env` file with local configuration
- **Production**: Environment-specific variables via deployment platform
- **Secrets**: HashiCorp Vault integration for sensitive data

### Configuration Files

- **Frontend**: `vite.config.ts`, `tailwind.config.js`, `tsconfig.json`
- **Python**: `config.yaml`, `requirements.txt`, `pytest.ini`
- **Rust**: `Cargo.toml` with feature flags
- **Docker**: Multi-stage Dockerfiles for each service

## Performance Optimization

### Frontend

- **Code Splitting**: Lazy loading with React.lazy()
- **Bundle Analysis**: Rollup visualizer for bundle optimization
- **Caching**: Service worker for offline capabilities
- **CDN**: Static assets served via Vercel Edge Network

### Backend

- **Async Processing**: Non-blocking I/O throughout the stack
- **Connection Pooling**: Database and Redis connection management
- **Caching Strategy**: Multi-layer caching (Redis, application, CDN)
- **Load Balancing**: Kubernetes ingress with multiple replicas

## Monitoring & Observability

### Metrics Collection

- **Prometheus**: Time-series metrics database
- **Grafana**: Visualization and alerting dashboards
- **OpenTelemetry**: Distributed tracing (planned)

### Health Monitoring

```bash
# Health check endpoints
curl http://localhost:8000/health    # Python service
curl http://localhost:3000/health    # Node.js API
curl http://localhost:8080/health    # Rust service
```

### Logging

- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Centralized logging with ELK stack
- **Error Tracking**: Comprehensive error monitoring and alerting
