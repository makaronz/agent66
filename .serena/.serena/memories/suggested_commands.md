# Essential Commands for SMC Trading Agent Development

## Testing Commands
```bash
# Run comprehensive test suite
pytest tests/ -v --cov=. --cov-report=html

# Run ML-specific tests
pytest tests/test_model_ensemble.py -v
pytest tests/test_ml_integration.py -v

# Performance testing
python test_ml_integration.py --performance-test
python performance_benchmark.py

# Integration testing
python test_integration_comprehensive.py
python system_integration_tests.py
```

## ML Training Commands
```bash
# Train ML models on historical data
python train_smc_models.py --symbols BTC/USDT --months 12 --epochs 100

# Quick training for development
python quick_start_training.py

# Training pipeline with validation
python training/smc_training_pipeline.py --validate --walk-forward
```

## Development Commands
```bash
# Code formatting and linting
black  --check
isort  --check-only
flake8 
# Type checking
mypy  --ignore-missing-imports

# Configuration validation
python config_validator.py

# System health check
python run_system_validation.py
```

## Running the Application
```bash
# Main application
python main.py

# Enhanced with ML
python main_optimized.py

# Simple SMC execution
python run_smc_simple.py

# Real-time integration
python run_smc_real_integration.py

# Paper trading mode
python start_paper_trading.py
```

## Docker Deployment
```bash
# Development deployment
docker-compose -f deployment/docker-compose.yml up -d

# Production deployment
docker-compose -f docker-compose.production.yml up -d

# Optimized deployment
docker-compose -f docker-compose.optimized.yml up -d
```

## Monitoring Commands
```bash
# Health monitoring
python monitoring/health_monitor.py

# Real-time dashboard
python monitoring/real_time_dashboard.py

# Performance monitoring
python monitoring/enhanced_monitoring.py

# Grafana dashboard setup
python monitoring/grafana_dashboards.py
```

## Multi-timeframe System
```bash
# Quick multi-timeframe test
python test_mt_simple.py

# Full multi-timeframe system
python multi_timeframe/main.py

# Multi-timeframe integration test
python test_multi_timeframe_quick.py
```

## Configuration Commands
```bash
# Setup configuration
python config/config_setup.py

# Validate configuration
python config_validator.py --production

# Test configuration
python test_config.yaml
```

## Database Commands
```bash
# Historical data collection
python training/historical_data_collector.py

# Data validation
python training/validation/cross_exchange/validator.py

# Statistical tests
python training/validation/statistical_tests/test_suite.py
```

## Utility Commands
```bash
# Comprehensive testing
python run_comprehensive_tests.py

# Comprehensive testing framework
python run_comprehensive_testing.py

# Demo testing framework
python demo_testing_framework.py

# ML integration demo
python demo_training_system.py
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
pytest tests/ -v

# Push changes
git push origin feature/ml-enhancements
```

## Environment Setup
```bash
# Copy environment file
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Install ML dependencies
pip install -r requirements_ml.txt

# Setup environment
source .env
```

## Performance Optimization
```bash
# Performance benchmark
python performance_benchmark.py

# Latency validation
python scripts/validate_latency.py

# System validation
python run_system_validation.py
```

## Deployment Commands
```bash
# Deploy to production
python scripts/deploy.sh

# Validate deployment
python run_comprehensive_testing.py --production

# Setup monitoring
python setup_enhanced_monitoring.py
```