# Essential Commands for SMC Trading Agent Development

## Testing Commands
```bash
# Run comprehensive test suite
pytest smc_trading_agent/tests/ -v --cov=smc_trading_agent --cov-report=html

# Run ML-specific tests
pytest smc_trading_agent/tests/test_model_ensemble.py -v
pytest smc_trading_agent/tests/test_ml_integration.py -v

# Performance testing
python smc_trading_agent/test_ml_integration.py --performance-test
python smc_trading_agent/performance_benchmark.py

# Integration testing
python smc_trading_agent/test_integration_comprehensive.py
python smc_trading_agent/system_integration_tests.py
```

## ML Training Commands
```bash
# Train ML models on historical data
python smc_trading_agent/train_smc_models.py --symbols BTC/USDT --months 12 --epochs 100

# Quick training for development
python smc_trading_agent/quick_start_training.py

# Training pipeline with validation
python smc_trading_agent/training/smc_training_pipeline.py --validate --walk-forward
```

## Development Commands
```bash
# Code formatting and linting
black smc_trading_agent/ --check
isort smc_trading_agent/ --check-only
flake8 smc_trading_agent/

# Type checking
mypy smc_trading_agent/ --ignore-missing-imports

# Configuration validation
python smc_trading_agent/config_validator.py

# System health check
python smc_trading_agent/run_system_validation.py
```

## Running the Application
```bash
# Main application
python smc_trading_agent/main.py

# Enhanced with ML
python smc_trading_agent/main_optimized.py

# Simple SMC execution
python smc_trading_agent/run_smc_simple.py

# Real-time integration
python smc_trading_agent/run_smc_real_integration.py

# Paper trading mode
python smc_trading_agent/start_paper_trading.py
```

## Docker Deployment
```bash
# Development deployment
docker-compose -f smc_trading_agent/deployment/docker-compose.yml up -d

# Production deployment
docker-compose -f smc_trading_agent/docker-compose.production.yml up -d

# Optimized deployment
docker-compose -f smc_trading_agent/docker-compose.optimized.yml up -d
```

## Monitoring Commands
```bash
# Health monitoring
python smc_trading_agent/monitoring/health_monitor.py

# Real-time dashboard
python smc_trading_agent/monitoring/real_time_dashboard.py

# Performance monitoring
python smc_trading_agent/monitoring/enhanced_monitoring.py

# Grafana dashboard setup
python smc_trading_agent/monitoring/grafana_dashboards.py
```

## Multi-timeframe System
```bash
# Quick multi-timeframe test
python smc_trading_agent/test_mt_simple.py

# Full multi-timeframe system
python smc_trading_agent/multi_timeframe/main.py

# Multi-timeframe integration test
python smc_trading_agent/test_multi_timeframe_quick.py
```

## Configuration Commands
```bash
# Setup configuration
python smc_trading_agent/config/config_setup.py

# Validate configuration
python smc_trading_agent/config_validator.py --production

# Test configuration
python smc_trading_agent/test_config.yaml
```

## Database Commands
```bash
# Historical data collection
python smc_trading_agent/training/historical_data_collector.py

# Data validation
python smc_trading_agent/training/validation/cross_exchange/validator.py

# Statistical tests
python smc_trading_agent/training/validation/statistical_tests/test_suite.py
```

## Utility Commands
```bash
# Comprehensive testing
python smc_trading_agent/run_comprehensive_tests.py

# Comprehensive testing framework
python smc_trading_agent/run_comprehensive_testing.py

# Demo testing framework
python smc_trading_agent/demo_testing_framework.py

# ML integration demo
python smc_trading_agent/demo_training_system.py
```

## Git Workflow
```bash
# Check status before starting
git status && git branch

# Create feature branch
git checkout -b feature/ml-enhancements

# Commit changes
git add .
git commit -m "feat: implement market regime detection module"

# Run tests before commit
pytest smc_trading_agent/tests/ -v

# Push changes
git push origin feature/ml-enhancements
```

## Environment Setup
```bash
# Copy environment file
cp smc_trading_agent/.env.example smc_trading_agent/.env

# Install dependencies
pip install -r smc_trading_agent/requirements.txt

# Install ML dependencies
pip install -r smc_trading_agent/requirements_ml.txt

# Setup environment
source smc_trading_agent/.env
```

## Performance Optimization
```bash
# Performance benchmark
python smc_trading_agent/performance_benchmark.py

# Latency validation
python smc_trading_agent/scripts/validate_latency.py

# System validation
python smc_trading_agent/run_system_validation.py
```

## Deployment Commands
```bash
# Deploy to production
python smc_trading_agent/scripts/deploy.sh

# Validate deployment
python smc_trading_agent/run_comprehensive_testing.py --production

# Setup monitoring
python smc_trading_agent/setup_enhanced_monitoring.py
```