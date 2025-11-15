# SMC Trading Agent - Smart Money Concepts Automated Trading System

**Personal trading bot for ≤5 users** - Fast path to first paper trade with live Binance data.

A simplified, production-ready hybrid trading system combining Smart Money Concepts analysis with live market data for automated cryptocurrency paper trading.

## 🏗️ Simplified Architecture (Personal Use)

**Frontend (React 18 + TypeScript)**
- Modern React UI with real-time dashboard
- Live market data from Binance WebSocket
- Paper trading visualization

**Backend (Express.js + TypeScript)**
- RESTful API with WebSocket connections to Binance
- Real-time market data aggregation
- Circuit breaker patterns and rate limiting

**Trading Engine (Python + FastAPI)**
- **SMC Analysis**: Order block detection, pattern recognition
- **Paper Trading**: Simulated execution with live prices
- **Risk Management**: Position sizing, stop-loss, daily limits
- **Simple Heuristic**: Fast decisions without ML training (ML optional later)

**Key Simplifications vs Enterprise Version**:
- ❌ Kafka removed (direct REST API)
- ❌ Multiple exchanges removed (Binance only)
- ❌ PostgreSQL/Redis removed (SQLite)
- ❌ Prometheus/Grafana removed (simple logging)
- ❌ Complex ML ensemble removed (simple heuristic first, ML optional)
- ✅ 2 processes only: TypeScript backend + Python agent

## ✨ Key Features

- **🔄 Live Binance Data**: Real-time WebSocket price feeds
- **📊 SMC Pattern Detection**: Order block and reversal detection
- **🎯 Simple Heuristic**: Fast decisions based on SMC patterns (no ML training needed)
- **📄 Paper Trading**: Risk-free simulation with live prices
- **🛡️ Risk Management**: Position limits, stop loss, daily loss limits
- **📈 Live Dashboard**: Real-time P&L, positions, and trade history
- **🔒 Safety First**: Paper mode default, risk controls enforced
- **⚡ Fast Setup**: < 30 minutes to first paper trade

## 🚀 Quick Start (< 30 minutes to first paper trade)

### Prerequisites
- Node.js 18+
- Python 3.9+
- Binance API keys (read-only for paper trading)

### Installation

```bash
# 1. Install dependencies
npm install
pip install -r requirements.txt

# 2. Configure API keys
cp env.example .env
nano .env  # Add your BINANCE_API_KEY and BINANCE_API_SECRET

# 3. Start TypeScript backend (Terminal 1)
npm run server:dev

# 4. Start Python trading agent (Terminal 2)
python main.py

# 5. Start frontend (Terminal 3)
npm run client:dev

# 6. Open browser
open http://localhost:5173
```

**📖 Detailed guide**: See [docs/QUICK_START.md](docs/QUICK_START.md) for step-by-step instructions.

## 📡 Market Data Integration

The system automatically connects to multiple exchanges for real-time data:

### Supported Exchanges
- **Binance**: Primary source for cryptocurrency data
- **ByBit**: Secondary source with failover capabilities
- **OANDA**: Forex and commodities (planned)

### Real-Time Data Streams
- **Ticker Data**: Price changes, volume, 24h statistics
- **Order Book**: Live bid/ask spreads with depth analysis
- **Trade History**: Recent trades for market sentiment analysis
- **SMC Patterns**: Automatic detection of order blocks and reversals

## 🔧 Configuration

### Environment Variables
```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_secret

# Server Configuration
PORT=3001
NODE_ENV=development

# Trading Parameters
MAX_POSITION_SIZE=0.1
RISK_PER_TRADE=0.02
MAX_DRAWDOWN=0.05
```

### Trading Symbols
Default symbols: `['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT']`

Configure additional symbols in `api/routes/trading.ts`

## 📊 API Endpoints

### Market Data
- `GET /api/trading/market-data` - Real-time market prices
- `GET /api/trading/data-health` - System health and connection status
- `GET /api/trading/smc-patterns` - Detected SMC patterns

### Trading
- `POST /api/trading/execute-trade` - Manual trade execution
- `GET /api/trading/positions` - Current positions with real-time P&L
- `GET /api/trading/history` - Trading history

### Risk Management
- `GET /api/trading/risk-metrics` - Real-time risk exposure
- `GET /api/trading/performance` - Trading performance statistics
- `GET /api/trading/system-health` - Component health status

## 🛡️ Safety & Risk Management

### Circuit Breakers
- **API Call Protection**: Automatic failover after 5 consecutive failures
- **WebSocket Resilience**: Automatic reconnection with exponential backoff
- **Rate Limiting**: Exchange-specific rate limit protection
- **Position Limits**: Automatic position size limits based on account balance

### Risk Controls
- **Maximum Drawdown**: 5% maximum account drawdown
- **Position Sizing**: Risk per trade limited to 2%
- **Stop Loss**: Automatic stop-loss on all positions
- **Time-Based Exits**: Automatic position closure after set timeframes

## 🧪 Testing

```bash
# Run frontend tests
npm test

# Run backend tests
npm run test:api

# Run Python ML tests
pytest tests/

# Run comprehensive test suite
npm run test:all
```

## 📈 Monitoring & Observability

### Health Endpoints
- `GET /api/health` - Basic API health check
- `GET /api/trading/data-health` - Market data connection status
- WebSocket health monitoring with automatic alerts

### Metrics
- **Real-time P&L**: Live profit/loss tracking
- **Latency Monitoring**: WebSocket and API response times
- **Data Quality**: Confidence scores and data freshness metrics
- **System Performance**: Memory, CPU, and connection statistics

## 🔒 Security Considerations

- **API Key Protection**: Never commit API keys to version control
- **Rate Limiting**: Built-in protection against exchange API limits
- **Input Validation**: Comprehensive validation of all trading inputs
- **Error Handling**: Safe error responses that don't expose sensitive data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 Development Notes

### Architecture Decisions
- **Hybrid Stack**: React frontend with Python ML backend for performance
- **WebSocket First**: Real-time data prioritized over REST polling
- **Circuit Breakers**: Fault tolerance patterns throughout the system
- **Microservices**: Modular design for independent scaling

### Performance Optimizations
- **Data Aggregation**: Intelligent market data consolidation
- **Caching**: Redis caching for frequently accessed data
- **Batch Processing**: Efficient bulk operations for market data
- **Connection Pooling**: Reused connections for exchange APIs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
1. Check the [troubleshooting guide](docs/TROUBLESHOOTING.md)
2. Review [API documentation](docs/API.md)
3. Open an issue for bugs or feature requests

---

**⚠️ Risk Warning**: Cryptocurrency trading involves substantial risk of loss. This software is for educational and demonstration purposes. Always use proper risk management and never risk more than you can afford to lose.

**🔧 Built with**: React, TypeScript, Express, Python, TensorFlow, PyTorch, Rust