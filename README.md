# SMC Trading Agent

A comprehensive Smart Money Concepts (SMC) trading system built with React, TypeScript, Python, and Rust. The system provides automated trading capabilities with advanced market structure analysis, risk management, and real-time execution.

## 🏗️ Architecture

- **Frontend**: React + TypeScript + Vite
- **API Gateway**: Node.js + Express + TypeScript
- **Trading Engine**: Python (FastAPI) with ML/AI capabilities
- **Execution Engine**: Rust for high-performance order execution
- **Database**: PostgreSQL with Supabase
- **Cache**: Redis
- **Deployment**: Vercel (Frontend), Kubernetes (Backend)

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Rust 1.70+
- PostgreSQL 14+
- Redis 6+

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd smc_trading_agent
   ```

2. **Install dependencies**

   ```bash
   # Frontend and API
   npm install

   # Python dependencies
   pip install -r requirements.txt

   # Rust dependencies
   cargo build
   ```

3. **Environment setup**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database setup**

   ```bash
   # Run migrations
   npm run db:migrate

   # Seed data (optional)
   npm run db:seed
   ```

### Development

```bash
# Start all services
npm run dev

# Or start individually:
npm run client:dev    # Frontend (port 5173)
npm run server:dev    # API Gateway (port 3000)
python main.py        # Trading Engine (port 8000)
cargo run            # Execution Engine (port 8080)
```

## 📦 Deployment

### Vercel Deployment (Frontend + API)

1. **Install Vercel CLI**

   ```bash
   npm install -g vercel
   ```

2. **Configure environment variables**

   ```bash
   # Copy production template
   cp .env.production .env.local

   # Set required variables in Vercel dashboard:
   # - VITE_SUPABASE_URL
   # - VITE_SUPABASE_ANON_KEY
   # - SUPABASE_SERVICE_ROLE_KEY
   # - ENCRYPTION_KEY
   # - BINANCE_API_KEY
   # - BINANCE_API_SECRET
   ```

3. **Deploy**

   ```bash
   # Preview deployment
   npm run deploy:preview

   # Production deployment
   npm run deploy:vercel
   ```

### Kubernetes Deployment (Backend Services)

```bash
# Build and push images
npm run build:images

# Deploy to staging
kubectl apply -f deployment/k8s/staging/

# Deploy to production
kubectl apply -f deployment/k8s/production/
```

## 🧪 Testing

```bash
# Run comprehensive test suite
npm test                    # All tests
npm run test:frontend       # React/TypeScript tests
npm run api:test           # Node.js API tests
pytest                     # Python backend tests
cargo test                 # Rust execution engine tests
npm run test:e2e           # End-to-end tests
npm run test:integration   # Integration tests

# Coverage reports
npm run coverage           # Generate coverage reports
pytest --cov=.            # Python coverage
```

### Test Status (Latest Audit)

- **Unit Tests**: 90%+ coverage across all components
- **Integration Tests**: Exchange connectors, API contracts
- **Performance Tests**: Load testing for high-frequency scenarios
- **Security Tests**: Vulnerability scanning with Trivy

## 🔒 Security

### Current Implementation

- **Security headers**: Configured in `vercel.json` and `nginx.conf`
- **Input validation**: Zod schemas for TypeScript, Pydantic for Python
- **Authentication**: Supabase Auth with MFA support
- **Rate limiting**: Implemented across all API endpoints
- **Secrets management**: Environment variables, never committed

### Security Audit Findings (2025)

Based on recent security assessment:

✅ **Implemented**:

- Supabase Auth with Row Level Security (RLS)
- Input validation and sanitization
- HTTPS enforcement and secure headers

⚠️ **In Progress**:

- Content Security Policy (CSP) and Helmet.js integration
- mTLS between internal services
- Enhanced rate limiting with Redis
- Secrets rotation automation

🔄 **Planned**:

- Post-quantum cryptography implementation
- RBAC/ABAC authorization model
- STRIDE threat modeling completion
- Security scanning in CI/CD pipeline

See [Security Gap Assessment](docs/audit/security_gap_assessment.md) for detailed analysis.

## 📊 Monitoring & Observability

### Current Implementation

- **Health checks**: `/health` endpoints on all services
- **Metrics**: Prometheus-compatible metrics collection
- **Logging**: Structured JSON logs with correlation IDs
- **Alerts**: Configured for critical system events

### Observability Stack

- **Metrics**: Prometheus + Grafana dashboards
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: OpenTelemetry distributed tracing (planned)
- **APM**: Application Performance Monitoring
- **Alerting**: AlertManager with Slack/email notifications

### Key Metrics Tracked

- **Trading Performance**: Win rate, Sharpe ratio, drawdown
- **System Health**: CPU, memory, disk usage
- **API Performance**: Response times, error rates
- **Exchange Connectivity**: Latency, success rates
- **Risk Metrics**: Position sizes, VaR calculations

### Monitoring Endpoints

```bash
# Health checks
curl http://localhost:8008/health    # Python orchestrator
curl http://localhost:3002/health    # Node.js API
curl http://localhost:8080/health    # Rust execution engine

# Metrics
curl http://localhost:8008/metrics   # Prometheus metrics
```

See [Monitoring Assessment](docs/audit/monitoring_observability_assessment.md) for detailed configuration.

## 🛠️ Development Tools

```bash
# Code quality
npm run lint          # ESLint
npm run type-check    # TypeScript
npm run format        # Prettier

# Security scanning
npm run security:scan # Trivy + Semgrep

# Documentation
npm run docs:generate # API documentation
npm run docs:serve    # Serve docs locally

# Build analysis
npm run build:analyze # Bundle analyzer
```

## 📚 API Documentation

API documentation is available at:

- Development: `http://localhost:3000/docs`
- Production: `https://your-domain.vercel.app/docs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security scans
5. Submit a pull request

## 🔍 Recent Audit & Improvements (2025)

### Context-7 Architecture Audit Completed

A comprehensive audit using the Context-7 framework has been completed, providing detailed analysis of:

- **System Architecture**: Multi-service orchestration patterns
- **Entry Points**: Python, Node.js, React, and Rust integration
- **Data Flow**: Kafka streaming and database interactions
- **Security Posture**: Gap analysis and hardening roadmap
- **Deployment Configuration**: Kubernetes and Docker optimization
- **Integration Points**: API contracts and service boundaries

### Key Improvements Implemented

✅ **Enhanced Error Handling**: Circuit breakers and retry mechanisms  
✅ **Comprehensive Testing**: 90%+ code coverage with integration tests  
✅ **Documentation**: Complete audit trail and technical specifications  
✅ **Monitoring**: Health checks and metrics collection  
✅ **Risk Management**: Advanced position sizing and VaR calculations

### Roadmap (Next 6 Months)

🔄 **Security Hardening**: CSP, mTLS, secrets management  
🔄 **CI/CD Pipeline**: Automated testing, security scanning, SBOM generation  
🔄 **Observability**: OpenTelemetry tracing and advanced alerting  
🔄 **Performance**: Rust-Python bridge optimization  
🔄 **Compliance**: GDPR/PII data handling and retention policies

### Audit Documentation

- [Repository Audit Report](docs/audit/repository_audit_report.md)
- [Architecture Analysis](docs/audit/architecture_context7.md)
- [Security Assessment](docs/audit/security_gap_assessment.md)
- [Recommendations Roadmap](docs/audit/recommendations_roadmap.md)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
