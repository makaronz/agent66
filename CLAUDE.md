# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a hybrid Python/Rust SMC (Smart Money Concepts) Trading Agent designed for automated trading using advanced AI/ML techniques. The system follows microservices architecture with real-time market data processing, ML-based decision making, and ultra-low latency trade execution.

## Architecture

The system consists of several interconnected components:

- **Data Pipeline** (`data_pipeline/`): Market data ingestion from multiple exchanges (Binance, ByBit, OANDA)
- **SMC Detector** (`smc_detector/`): Detects Smart Money Concepts patterns (Order Blocks, CHOCH/BOS, FVG, Liquidity Sweeps)
- **Decision Engine** (`decision_engine/`): Ensemble ML models (LSTM, Transformer, PPO) with adaptive selection
- **Execution Engine** (`src/execution_engine/`): Ultra-low latency Rust-based trade execution (<50ms)
- **Risk Manager** (`risk_manager/`): Circuit breakers, VaR monitoring, SMC-specific risk management
- **Compliance** (`compliance/`): MiFID II reporting and audit trails
- **Monitoring** (`monitoring/`): Prometheus/Grafana dashboards and health checks

## Development Commands

### Environment Setup
```bash
# Set up environment variables
cp env.example .env
# Edit .env with your API keys

# Install Python dependencies
pip install -r requirements.txt

# Build Rust components
cargo build --release
```

### Running the Application
```bash
# Run main Python application
python main.py

# Run with Docker Compose (recommended for development)
docker-compose -f deployment/docker-compose.yml up -d
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_risk_manager.py -v
pytest tests/test_smc_indicators.py -v
pytest tests/test_error_handling.py -v

# Run comprehensive test suite
python run_comprehensive_tests.py

# Test Rust components
cargo test
```

### Development Tools
```bash
# Code formatting and linting
black .
flake8 .

# Rust formatting
cargo fmt
cargo clippy
```

### Monitoring
```bash
# Access Grafana dashboard (when running with Docker)
open http://localhost:3000
# Default credentials: admin/admin

# Access Prometheus metrics
open http://localhost:9090
```

## Configuration

The main configuration is in `config.yaml` with environment variable substitution support:

- **API Keys**: Use `${BINANCE_API_KEY}`, `${BINANCE_API_SECRET}` format
- **Database**: PostgreSQL with TimescaleDB for time-series data
- **Caching**: Redis for real-time data caching
- **Risk Parameters**: Max drawdown, circuit breaker thresholds
- **Logging**: JSON structured logging with pythonjsonlogger

## Code Architecture Details

### Error Handling Strategy
The codebase implements comprehensive error handling with:
- **Circuit Breakers**: Prevent cascade failures across components
- **Retry Handlers**: Automatic retry with exponential backoff
- **Health Monitoring**: System-wide health checks and alerts
- **Validation Framework**: Multi-level data validation (see `validators.py`)

### Data Flow
1. **Market Data** → `data_pipeline.ingestion` → Validation → Redis Cache
2. **SMC Analysis** → `smc_detector.indicators` → Pattern Detection → Order Blocks
3. **Decision Making** → `decision_engine.model_ensemble` → ML Models → Trade Signals
4. **Risk Assessment** → `risk_manager.smc_risk_manager` → Stop Loss/Take Profit
5. **Trade Execution** → Rust `execution_engine` → Exchange APIs

### Key Data Structures

#### Order Blocks
Standard format across all components:
```python
{
    "price_level": (high_price, low_price),  # Tuple format
    "direction": "bullish" | "bearish",
    "strength": float,
    "timestamp": datetime
}
```

#### Trade Signals
```python
{
    "action": "buy" | "sell",
    "symbol": str,
    "entry_price": float,
    "confidence": float,
    "stop_loss": float,
    "take_profit": float
}
```

## Development Guidelines

### Python Components
- Follow existing error handling patterns with `@safe_execute` decorators
- Use circuit breakers and retry handlers for external API calls
- Implement comprehensive data validation before processing
- Follow the logging configuration in `config.yaml`

### Rust Components
- Located in `src/execution_engine/`
- Uses barter-execution and barter-integration crates
- Implements ultra-low latency trade execution
- All structs must be Serialize/Deserialize for Python interop

### Testing Requirements
- All new components must have corresponding test files in `tests/`
- Use pytest for Python tests, cargo test for Rust
- Integration tests should cover error scenarios and circuit breaker behavior
- Mock external APIs for reliable testing

### File Structure Conventions
```
.
├── data_pipeline/          # Market data ingestion
├── smc_detector/          # SMC pattern detection
├── decision_engine/       # ML models and decision logic
├── risk_manager/          # Risk management and circuit breakers
├── execution_engine/      # Python wrappers for Rust execution
├── src/execution_engine/  # Rust implementation
├── compliance/            # Regulatory compliance
├── monitoring/           # Health monitoring and metrics
├── tests/               # Test suites
├── deployment/          # Docker and Kubernetes configs
└── training/           # ML model training pipelines
```

## Important Notes

- **Security**: Never commit API keys or secrets. Use environment variables only.
- **Performance**: Execution engine targets <50ms latency for trade execution.
- **Risk Management**: All trades must pass through risk validation.
- **Data Quality**: Implement data validation at every pipeline stage.
- **Monitoring**: Add Prometheus metrics for new components.
- **Dependencies**: Keep `requirements.txt` updated with exact versions.

## Todo2 Workflow Integration

This project uses Todo2 workflow system (see `.cursor/rules/`). When working on this codebase:
- Always use Todo2 workflow for task management
- Follow research → implement → test → review cycle
- Create detailed task descriptions with acceptance criteria
- Use appropriate complexity assessment for task breakdown