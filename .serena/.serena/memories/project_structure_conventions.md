# Project Structure & Conventions

## Code Organization
```
├── decision_engine/          # ML models and decision logic
│   ├── model_ensemble.py     # LSTM, Transformer, PPO ensemble
│   ├── ml_decision_engine.py # Production-ready ML engine
│   ├── smc_training_pipeline.py # Training pipeline
│   └── ml_config.py         # Configuration management
├── smc_detector/            # SMC pattern detection
│   ├── indicators.py        # Numba-optimized SMC indicators
│   └── enhanced_smc_detector.py
├── data_pipeline/           # Market data ingestion
│   ├── ingestion.py         # Data collection
│   └── exchange_connectors/ # Exchange-specific connectors
├── risk_manager/           # Risk management and circuit breakers
├── execution_engine/       # Rust-based ultra-low latency execution
├── monitoring/            # System health and performance monitoring
├── tests/                 # Comprehensive test suites
├── config/               # Configuration management
└── api/                  # REST API and WebSocket server
```

## Technology Stack
- **Languages**: Python 3.9+, Rust
- **ML Frameworks**: PyTorch 2.1.2, TensorFlow 2.15.0, scikit-learn 1.3.2
- **Database**: PostgreSQL + TimescaleDB, Redis
- **Message Queue**: Apache Kafka
- **Monitoring**: Prometheus, Grafana
- **API**: FastAPI, WebSockets
- **Testing**: pytest, asyncio, httpx

## Code Style & Conventions
- **Python**: Black formatting, isort imports, flake8 linting
- **Type Hints**: Full type annotation coverage
- **Docstrings**: Comprehensive documentation with examples
- **Error Handling**: Circuit breakers, retry handlers, structured logging
- **Performance**: Numba JIT compilation for critical paths
- **Testing**: 95%+ coverage with unit, integration, and E2E tests

## Development Commands
```bash
# Environment setup
cp env.example .env
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=.

# Code formatting
black .
isort .
flake8 .

# Run application
python main.py

# Docker deployment
docker-compose -f deployment/docker-compose.yml up -d
```

## Configuration Management
- **Environment Variables**: Use ${VAR_NAME} format in YAML
- **Configuration Files**: config.yaml with environment substitution
- **ML Configuration**: config/ml_config.json for model parameters
- **Deployment Stages**: Shadow → Canary → Gradual → Full

## Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Latency and memory benchmarking
- **Load Tests**: High-volume data processing validation
- **ML Validation**: Model accuracy and statistical validation