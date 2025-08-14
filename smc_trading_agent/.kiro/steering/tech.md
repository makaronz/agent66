# Technology Stack

## Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 6.x with HMR
- **Styling**: Tailwind CSS with PostCSS
- **UI Components**: Headless UI, Heroicons, Lucide React
- **State Management**: Zustand, React Query (TanStack Query)
- **Authentication**: Supabase Auth with MFA support
- **Charts**: Recharts, TradingView integration
- **Forms**: React Hook Form with Zod validation

## Backend
- **API Layer**: Express.js with TypeScript
- **Authentication**: JWT, WebAuthn, TOTP, SMS MFA
- **Database**: Supabase (PostgreSQL) with TimescaleDB
- **Caching**: Redis
- **Real-time**: Socket.io, WebSockets

## Trading Engine
- **Core Logic**: Python 3.10+ with FastAPI
- **Execution Engine**: Rust with Tokio async runtime
- **Exchange APIs**: CCXT library for multi-exchange support
- **ML/AI**: TensorFlow, PyTorch, scikit-learn
- **Data Processing**: Pandas, NumPy
- **Streaming**: Kafka with confluent-kafka

## Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose, Kubernetes ready
- **Monitoring**: Prometheus, Grafana
- **Deployment**: Vercel (frontend), self-hosted (backend)
- **CI/CD**: GitHub Actions ready

## Development Tools
- **Linting**: ESLint with TypeScript rules
- **Testing**: Vitest, pytest, Rust cargo test
- **Package Management**: pnpm (Node.js), pip (Python), cargo (Rust)
- **Type Checking**: TypeScript strict mode

## Common Commands

### Development
```bash
# Start full development environment
npm run dev

# Frontend only
npm run client:dev

# Backend API only  
npm run server:dev

# Python trading engine
python main.py

# Rust execution engine
cargo run
```

### Building
```bash
# Build frontend
npm run build

# Type check
npm run check

# Lint code
npm run lint

# Python tests
pytest

# Rust tests
cargo test
```

### Docker
```bash
# Start all services
docker-compose -f deployment/docker-compose.yml up

# Build specific service
docker build -f smc_agent.Dockerfile .
docker build -f data_pipeline.Dockerfile .
```