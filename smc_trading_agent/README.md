# 🤖 SMC Trading Agent

Zaawansowany agent tradingowy oparty na Smart Money Concepts (SMC) z wykorzystaniem AI/ML.

## 🏗️ Architektura

System oparty na architekturze mikroserwisów:

- **Data Pipeline**: Ingestion danych z WebSocket/REST APIs (Binance, ByBit, OANDA)
- **SMC Detector**: Wykrywanie Order Blocks, CHOCH/BOS, FVG, Liquidity Sweeps
- **Decision Engine**: Ensemble modeli (LSTM, Transformer, PPO) z adaptive selection
- **Execution Engine**: Ultra-low latency execution w Rust (<50ms)
- **Risk Manager**: Circuit Breaker, VaR monitoring, SMC-specific risk management
- **Compliance**: MiFID II reporting, audit trails
- **Monitoring**: Prometheus/Grafana dashboards, health checks

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/smc-trading-agent
cd smc-trading-agent

# Set up environment variables
cp .env.example .env
# nano .env # Edit with your API keys

# Install dependencies
pip install -r requirements.txt

# Run with Docker Compose
docker-compose up -d

# Access Grafana dashboard
open http://localhost:3000
```

## 📊 Kluczowe Metryki

- **Sharpe Ratio**: > 1.5 (target)
- **Maximum Drawdown**: < 8%
- **CHOCH Hit Rate**: > 65%
- **Order Block Reaction Rate**: > 70%
- **Latency**: < 50ms (order execution)
- **Uptime**: 99.9%

## 🧪 Testing

```bash
# Unit & Integration tests
pytest smc_trading_agent/tests/ -v

# Backtesting (example command)
# python -m smc_trading_agent.training.backtest --start-date 2019-01-01 --end-date 2024-12-31
```

## 📋 Roadmap

- **Phase 1** (3 months): MVP Development
- **Phase 2** (6 months): Advanced Features
- **Phase 3** (12 months): Production Ready
- **Phase 4** (18 months): Scaling & Innovation

## ⚠️ Risk Disclaimer

Ten system jest przeznaczony wyłącznie do celów edukacyjnych i badawczych. Trading wiąże się z wysokim ryzykiem straty kapitału.

