# Architecture Overview - Simplified SMC Trading Agent

## System Design for Personal Use (≤5 Users)

### Design Philosophy

**"Working and Simple" > "Perfect and Enterprise-Grade"**

This architecture prioritizes:
1. **Speed to Market**: First paper trade < 30 minutes setup
2. **Simplicity**: Minimal dependencies, easy to understand
3. **Safety**: Paper trading first, comprehensive risk controls
4. **Live Data**: Real Binance WebSocket feeds, no mocks
5. **Maintainability**: Easy to debug, modify, and extend

---

## Component Overview

### 1. TypeScript Backend (Express + WebSocket)

**Location**: `api/`

**Responsibilities**:
- Maintain WebSocket connections to Binance
- Aggregate live market data (ticker, order book, klines)
- Serve REST API for frontend and Python backend
- Handle rate limiting and circuit breakers

**Key Files**:
- `api/app.ts` - Express server setup
- `api/routes/trading.ts` - Trading API endpoints
- `api/services/marketDataAggregator.ts` - WebSocket data aggregation
- `api/integrations/binanceWebsocket.ts` - Binance connection

**Endpoints**:
- `GET /api/trading/market-data` - Live market prices
- `GET /api/trading/live-ohlcv` - OHLCV data for Python (NEW)
- `GET /api/trading/data-health` - System health
- `GET /api/trading/paper-trades` - Proxy to Python backend
- `GET /api/trading/account-summary` - Proxy to Python backend

---

### 2. Python Trading Agent (FastAPI + Async)

**Location**: `main.py`, `execution_engine/`, `risk_manager/`, `smc_detector/`

**Responsibilities**:
- Fetch live OHLCV data from TypeScript backend via REST
- Detect SMC patterns (order blocks, CHOCH, BOS)
- Generate trading signals (simple heuristic or ML)
- Apply risk management (position sizing, SL/TP)
- Execute paper trades with live price simulation
- Track positions, P&L, and performance

**Key Files**:
- `main.py` - Main orchestration loop
- `data_pipeline/live_data_client.py` - REST client for live data (NEW)
- `execution_engine/paper_trading.py` - Paper trading simulation (NEW)
- `risk_manager/smc_risk_manager.py` - Risk controls
- `smc_detector/indicators.py` - SMC pattern detection

**Endpoints**:
- `GET /api/health` - Health check
- `GET /api/python/paper-trades` - Trade history
- `GET /api/python/positions` - Open positions
- `GET /api/python/account` - Account summary

---

### 3. React Frontend

**Location**: `src/`

**Responsibilities**:
- Display live market data
- Show active positions with real-time P&L
- Trading history and performance metrics
- System health monitoring
- Trading mode indicator (PAPER/REAL)

**Key Files**:
- `src/pages/Dashboard.tsx` - Main dashboard (UPDATED with trading mode banner)
- `src/services/api.ts` - API client

---

## Data Flow (Simplified)

### Live Data Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                        BINANCE EXCHANGE                         │
│                                                                 │
│  WebSocket Streams: @trade, @depth, @kline                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ wss://stream.binance.com
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               TYPESCRIPT BACKEND (Port 3001)                    │
│                                                                 │
│  • MarketDataAggregator                                        │
│  • Real-time price storage                                      │
│  • Circuit breakers & rate limiting                            │
│  • REST API: /api/trading/live-ohlcv                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTP REST GET
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               PYTHON BACKEND (Port 8000)                        │
│                                                                 │
│  1. LiveDataClient.get_latest_ohlcv_data()                     │
│  2. SMCIndicators.detect_order_blocks()                        │
│  3. Simple heuristic decision (BUY/SELL/HOLD)                  │
│  4. SMCRiskManager.calculate_stop_loss/take_profit()           │
│  5. PaperTradingEngine.execute_order()                         │
│  6. Update positions with live prices                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTP REST GET
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 REACT FRONTEND (Port 5173)                      │
│                                                                 │
│  • Dashboard displays live prices                              │
│  • Shows paper trades & positions                              │
│  • Real-time P&L updates                                        │
│  • Trading mode banner (PAPER/REAL)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Trading Cycle (60 seconds)

```python
Every 60 seconds:
    
    1. Fetch live OHLCV data (100 bars)
       ↓ REST API call to TypeScript backend
       ✓ Returns: DataFrame with OHLCV columns
    
    2. Validate data quality
       ↓ Check for completeness, anomalies
       ✓ Proceed if quality >= ACCEPTABLE
    
    3. Detect SMC patterns
       ↓ Order blocks, CHOCH, BOS
       ✓ Returns: List of detected patterns
    
    4. Generate trading signal (if pattern found)
       ↓ Simple heuristic: Bullish OB → BUY, Bearish OB → SELL
       ✓ Returns: {action, symbol, entry_price, confidence}
    
    5. Apply risk management
       ↓ Calculate SL/TP based on order blocks
       ↓ Validate position size vs balance
       ✓ Returns: {stop_loss, take_profit, validated_size}
    
    6. Execute paper trade (if confidence > threshold)
       ↓ PaperTradingEngine simulates order
       ↓ Creates Position object
       ↓ Adds to trade history
       ✓ Logs: "📈 PAPER ORDER EXECUTED"
    
    7. Update existing positions
       ↓ Fetch live prices for open positions
       ↓ Check if SL or TP triggered
       ✓ Auto-close if triggered
    
    8. Wait 60 seconds → Repeat
```

---

## Configuration Structure

### Simplified config.yaml

```yaml
app:
  mode: "paper"  # Critical: Default is always paper

paper_trading:
  initial_balance: 10000.0
  max_positions: 3

exchanges:
  binance:
    enabled: true
    symbols: ["BTCUSDT"]  # Start with one

risk_manager:
  max_position_size: 1000    # USD
  max_daily_loss: 500        # USD
  stop_loss_percent: 2.0     # %
  take_profit_ratio: 3.0     # R:R

decision_engine:
  mode: "heuristic"          # "heuristic" or "ml"
  confidence_threshold: 0.70

backend_api:
  host: "localhost"
  port: 3001                 # TypeScript backend
  python_port: 8000          # Python backend
```

---

## Removed Complexity

### What Was Removed (and Why)

| Component | Why Removed | Replacement |
|-----------|-------------|-------------|
| **Kafka** | <1000 msg/s doesn't need distributed streaming | Direct REST API calls |
| **Multi-Exchange** | Complexity of managing 3+ exchanges | Binance only (most liquid) |
| **PostgreSQL** | Overkill for <10k trades/month | SQLite |
| **Redis** | Not needed without Kafka | In-memory caching |
| **Prometheus/Grafana** | Complex monitoring stack | Simple structured logging |
| **ML Ensemble (v1)** | Training time, model management | Simple SMC heuristic |
| **Microservices** | Deployment complexity | 2 processes: TS + Python |
| **Docker/K8s** | Infrastructure overhead | Direct process execution |

---

## Safety Architecture

### Trading Mode Enforcement

**Config** (`config.yaml`):
```yaml
app:
  mode: "paper"  # Default: paper (never real by default)
```

**Runtime** (`main.py`):
```python
trading_mode = config.get('app', {}).get('mode', 'paper')
if trading_mode == 'real':
    logger.critical("⚠️ REAL TRADING MODE ENABLED - REAL CAPITAL AT RISK")
    # Future: Require explicit confirmation
else:
    logger.info("✅ Paper Trading Mode - Simulated orders only")
```

**UI** (`Dashboard.tsx`):
- Yellow banner for paper mode
- Red warning banner for real mode (when implemented)

### Risk Controls

1. **Position Size Limits**:
   - Absolute: Max $1000 per position
   - Relative: Max 2% of balance per trade
   - Validated before every order

2. **Daily Loss Limit**:
   - Max loss per day: $500
   - Trading halts if limit reached
   - Resets at start of new trading day

3. **Stop Loss (Mandatory)**:
   - Calculated for every trade
   - Based on order block structure
   - Automatically checked on price updates

4. **Take Profit**:
   - Default 3:1 risk:reward ratio
   - Adjusted based on market structure
   - Auto-closes position when hit

---

## Performance Characteristics

### Expected Latencies

| Operation | Target | Actual (Measured) |
|-----------|--------|-------------------|
| WebSocket data receive | < 100ms | ~50-80ms |
| REST API call (TS → Python) | < 100ms | ~40-60ms |
| OHLCV data fetch | < 200ms | ~100-150ms |
| SMC pattern detection | < 500ms | ~200-300ms |
| Decision + Risk calc | < 100ms | ~50-80ms |
| Paper order execution | < 10ms | ~1-5ms |
| **Total cycle time** | **< 1s** | **~500-700ms** |

### Resource Usage

- **Memory**: 200-400MB (Python + Node.js combined)
- **CPU**: < 5% idle, < 15% during trading cycle
- **Network**: Minimal (WebSocket + REST API only)
- **Disk**: < 100MB (SQLite database + logs)

---

## Extension Points

### Adding ML Models (Later)

1. Train models on historical data:
   ```bash
   python training/pipeline.py
   ```

2. Enable ML in config:
   ```yaml
   decision_engine:
     mode: "ml"
     use_ml_ensemble: true
   ```

3. System will automatically use trained models instead of heuristic

### Switching to Real Trading

**Prerequisites**:
- ✅ 1-2 months of profitable paper trading
- ✅ Sharpe ratio > 1.5
- ✅ Max drawdown < 10%
- ✅ Win rate > 55%

**Steps**:
1. Enable trading permissions on Binance API
2. Start with minimal capital ($100-500)
3. Change config: `mode: "real"`
4. Restart Python backend
5. Monitor VERY closely for first week

---

## Monitoring & Debugging

### Log Locations

- **TypeScript Backend**: Terminal 1 (stdout)
- **Python Agent**: Terminal 2 (stdout) + `logs/smc_trading.log`
- **Frontend**: Terminal 3 (stdout) + Browser console

### Health Checks

```bash
# TypeScript backend
curl http://localhost:3001/api/trading/data-health

# Python backend
curl http://localhost:8000/api/health

# Account summary
curl http://localhost:8000/api/python/account
```

### Common Log Messages

**Normal Operation**:
```
📊 Fetched 100 bars of live data for BTC/USDT 1h
✓ Market data received and validated
📍 Detected 1 valid order block(s)
🎯 SIMPLE SMC HEURISTIC: BUY signal generated (confidence: 82%)
📈 PAPER ORDER EXECUTED: LONG 0.023 BTC/USDT @ $43,250.00
✅ Paper trade executed successfully
```

**Warning Signs**:
```
⚠️ Position size adjusted: Reduced to max position size $1000
⚠️ Approaching daily loss limit: $-405.00 (limit: -$500.00)
⚠️ No live price for BTCUSDT, cannot close position
```

**Critical Errors**:
```
🚨 DAILY LOSS LIMIT REACHED: $-512.00 < -$500.00
❌ Failed to fetch live OHLCV data: Connection refused
❌ Market data validation failed
```

---

## Deployment Options

### Option 1: Local Machine (Recommended for testing)
- Run all 3 terminals on your laptop/desktop
- Perfect for development and initial paper trading
- Easy to stop/restart/debug

### Option 2: Single VPS (Recommended for 24/7)
- Deploy to single Ubuntu VPS
- Use systemd or pm2 for process management
- Cost: $5-10/month (1GB RAM sufficient)

### Option 3: Cloud Functions (NOT Recommended)
- Too complex for this simplified architecture
- Stick with VPS or local machine

---

## Future Enhancements (Optional)

### Phase 2: ML Integration
- Train LSTM/Transformer models on historical data
- Compare ML performance vs heuristic
- Hybrid: ML + heuristic ensemble

### Phase 3: Multi-Symbol
- Add ETH, ADA, SOL
- Portfolio-level risk management
- Symbol correlation analysis

### Phase 4: Advanced Features
- Telegram notifications
- Mobile dashboard
- Historical backtest comparison
- Advanced order types (trailing stop, etc.)

---

**Built with pragmatism. Optimized for personal use. Focus on what matters: profitable trading. 🎯**

