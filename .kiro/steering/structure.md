# SMC Trading Agent - Project Structure

## Repository Organization

The project follows a monorepo structure with clear separation between the main trading system and supporting tools:

```
agent66/
├── smc_trading_agent/           # Main trading system (primary workspace)
├── docs/                        # Project-wide documentation
├── tools/                       # Development utilities
├── tests/                       # Integration tests
└── README.md                    # Project overview
```

## Main Trading System Structure

The core application is located in `smc_trading_agent/` with a multi-language architecture:

### Frontend (React + TypeScript)

```
smc_trading_agent/src/
├── components/                  # Reusable UI components
│   ├── auth/                   # Authentication components
│   ├── charts/                 # Trading chart components
│   ├── mfa/                    # Multi-factor auth components
│   ├── realtime/               # Real-time data components
│   └── ui/                     # Base UI components
├── pages/                      # Route-based page components
├── hooks/                      # Custom React hooks
│   └── queries/                # React Query hooks
├── stores/                     # Zustand state management
├── services/                   # API and business logic services
├── lib/                        # Utility libraries
├── types/                      # TypeScript type definitions
└── utils/                      # Helper functions
```

### API Gateway (Node.js + TypeScript)

```
smc_trading_agent/api/
├── routes/                     # Express route handlers
├── middleware/                 # Custom middleware
├── types/                      # API type definitions
├── validation/                 # Request validation schemas
├── config/                     # API configuration
└── lib/                        # Shared utilities
```

### Python Trading Engine

```
smc_trading_agent/
├── data_pipeline/              # Market data ingestion
│   └── exchange_connectors/    # Exchange API integrations
├── smc_detector/               # SMC pattern detection
├── decision_engine/            # Trading decision logic
├── risk_manager/               # Risk management system
├── monitoring/                 # Observability and metrics
├── database/                   # Database utilities
├── compliance/                 # Regulatory compliance
└── training/                   # ML model training
```

### Rust Execution Engine

```
smc_trading_agent/src/execution_engine/
├── executor.rs                 # Order execution logic
├── metrics.rs                  # Performance metrics
└── tests/                      # Rust unit tests
```

## Configuration & Deployment

### Configuration Files

```
smc_trading_agent/
├── config.yaml                 # Main application config
├── .env.example                # Environment template
├── package.json                # Node.js dependencies
├── requirements.txt            # Python dependencies
├── Cargo.toml                  # Rust dependencies
├── vite.config.ts              # Frontend build config
├── tailwind.config.js          # Styling configuration
└── tsconfig.json               # TypeScript configuration
```

### Deployment Infrastructure

```
smc_trading_agent/deployment/
├── docker-compose.yml          # Local development stack
├── kubernetes/                 # K8s manifests
├── helm/                       # Helm charts
├── monitoring/                 # Prometheus/Grafana configs
├── scripts/                    # Deployment automation
└── Makefile                    # Build automation
```

### Docker Configuration

```
smc_trading_agent/
├── Dockerfile.frontend         # React app container
├── Dockerfile.api              # Node.js API container
├── Dockerfile.python          # Python engine container
├── Dockerfile.rust             # Rust execution container
├── data_pipeline.Dockerfile    # Data pipeline container
└── stream_processor.Dockerfile # Stream processing container
```

## Testing Structure

### Test Organization

```
smc_trading_agent/tests/
├── integration/                # Cross-service integration tests
├── mocks/                      # Test mocks and fixtures
├── conftest.py                 # Pytest configuration
├── test_*.py                   # Python unit tests
└── __pycache__/                # Python bytecode cache
```

### Frontend Tests

```
smc_trading_agent/src/
├── components/__tests__/       # Component tests
├── hooks/__tests__/            # Hook tests
├── services/__tests__/         # Service tests
└── utils/__tests__/            # Utility tests
```

## Documentation Structure

### Project Documentation

```
docs/
├── audit/                      # Architecture audit reports
│   ├── repository_audit_report.md
│   ├── architecture_context7.md
│   ├── security_gap_assessment.md
│   └── recommendations_roadmap.md
├── *.md                        # Technical documentation
└── diagrams/                   # Architecture diagrams
```

### API Documentation

```
smc_trading_agent/docs/
├── api-examples.md             # API usage examples
├── postman/                    # Postman collections
├── operations/                 # Operational guides
└── sbom/                       # Software Bill of Materials
```

## Development Tools

### Scripts & Automation

```
smc_trading_agent/scripts/
├── deploy.sh                   # Deployment script
├── generate-api-docs.sh        # API documentation generation
├── validate-env.sh             # Environment validation
└── setup-vercel-env.sh         # Vercel environment setup
```

### Development Utilities

```
tools/
├── architecture_mapper.py      # Project structure analysis
├── dependency_analyzer.py      # Dependency analysis
└── *.py                        # Additional dev tools
```

## Key Architectural Patterns

### Service Separation

- **Frontend**: Pure React SPA with TypeScript
- **API Gateway**: Express.js for HTTP API and authentication
- **Trading Engine**: Python for ML/AI and orchestration
- **Execution Engine**: Rust for high-performance order execution
- **Data Pipeline**: Separate service for market data ingestion

### Data Flow

1. **Market Data**: Exchange APIs → Kafka → Python Engine
2. **Signal Generation**: Python Engine → Decision Engine → Risk Manager
3. **Order Execution**: Risk Manager → Rust Engine → Exchange APIs
4. **User Interface**: React Frontend ↔ Node.js API ↔ Python Engine

### Configuration Management

- **Environment Variables**: `.env` files for local development
- **Secrets Management**: HashiCorp Vault for production secrets
- **Configuration Files**: YAML for application settings
- **Feature Flags**: Environment-based feature toggles

### Monitoring & Observability

- **Health Checks**: `/health` endpoints on all services
- **Metrics**: Prometheus metrics collection
- **Logging**: Structured JSON logs with correlation IDs
- **Tracing**: OpenTelemetry distributed tracing (planned)

## File Naming Conventions

### Frontend (TypeScript/React)

- **Components**: PascalCase (e.g., `TradingInterface.tsx`)
- **Hooks**: camelCase with `use` prefix (e.g., `useMarketData.ts`)
- **Services**: camelCase (e.g., `binanceApi.ts`)
- **Types**: PascalCase with `.types.ts` suffix
- **Utilities**: camelCase (e.g., `utils.ts`)

### Backend (Python)

- **Modules**: snake_case (e.g., `smc_detector.py`)
- **Classes**: PascalCase (e.g., `SMCRiskManager`)
- **Functions**: snake_case (e.g., `calculate_stop_loss`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_POSITION_SIZE`)

### Backend (Rust)

- **Files**: snake_case (e.g., `execution_engine.rs`)
- **Structs**: PascalCase (e.g., `OrderExecutor`)
- **Functions**: snake_case (e.g., `execute_trade`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)

## Import/Export Patterns

### Frontend Imports

```typescript
// Absolute imports using path aliases
import { Button } from "@/components/ui/Button";
import { useMarketData } from "@/hooks/useMarketData";
import { cn } from "@/utils";

// External libraries
import { useState } from "react";
import { toast } from "react-hot-toast";
```

### Python Imports

```python
# Standard library first
import asyncio
import logging
from typing import Dict, Any

# Third-party libraries
import pandas as pd
from fastapi import FastAPI

# Local imports (relative)
from .config_loader import load_secure_config
from .risk_manager.smc_risk_manager import SMCRiskManager
```

### Rust Imports

```rust
// Standard library
use std::collections::HashMap;

// External crates
use tokio::time::{sleep, Duration};
use serde::{Deserialize, Serialize};

// Local modules
use crate::execution_engine::OrderExecutor;
```

This structure promotes maintainability, scalability, and clear separation of concerns across the multi-language architecture.
