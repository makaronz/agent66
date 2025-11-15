# SMC Trading Agent - Smart Money Concepts Automated Trading System

A sophisticated hybrid trading system that combines AI/ML techniques with Smart Money Concepts analysis for automated cryptocurrency trading with real-time market data integration.

## 🏗️ Architecture

**Frontend (React 18 + TypeScript)**
- Modern React UI with Vite for fast development
- Real-time trading dashboard with WebSocket connections
- Advanced charting and technical analysis visualization
- Tailwind CSS for responsive, professional design

**Backend (Express.js + TypeScript)**
- RESTful API server with WebSocket support
- Real-time market data aggregation from multiple exchanges
- Circuit breaker patterns for fault tolerance
- Comprehensive rate limiting and error handling

**Trading Engine**
- **Python ML Pipeline**: TensorFlow/PyTorch for pattern recognition
- **Smart Money Concepts (SMC)**: Order block detection, CHOCH/BOS analysis
- **Risk Management**: Circuit breakers, position sizing, stop-loss automation
- **Multi-Exchange Integration**: Binance, ByBit, OANDA real-time data

## ✨ Key Features

- **🔄 Real-Time Market Data**: Live WebSocket connections to multiple exchanges
- **📊 SMC Pattern Detection**: Advanced Smart Money Concepts analysis
- **🤖 ML-Based Decisions**: Ensemble models for trading signals
- **⚡ Ultra-Low Latency**: <50ms trade execution with Rust engine
- **🛡️ Risk Management**: Comprehensive circuit breakers and monitoring
- **📈 Live Dashboard**: Real-time P&L, positions, and system health
- **🔒 Security**: API key protection and safe trading practices

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Rust 1.70+ (optional, for execution engine)
- Valid exchange API keys (Binance, ByBit)

### Installation

1. **Clone and install dependencies**
```bash
git clone <repository-url>
cd agent66

# Frontend and Backend dependencies
npm install

# Python ML dependencies
pip install -r requirements.txt

# Rust execution engine (optional)
cd src/execution_engine && cargo build --release
```

2. **Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Configure your API keys
nano .env
```

3. **Start Development Servers**
```bash
# Start both frontend and backend concurrently
npm run dev

# Or start individually:
npm run client:dev  # Frontend at http://localhost:5173
npm run server:dev  # Backend API at http://localhost:3001
```

4. **Start Python Trading Engine** (Optional)
```bash
python run_smc_agent.py
```

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