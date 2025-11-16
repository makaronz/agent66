# 🚀 SMC Trading Agent - Web Application

## Quick Start - Web App

### Option 1: Automated Script (Recommended)

```bash
# Start everything with one command
./start_all.sh
```

This will start:
- ✅ TypeScript Backend (port 3001)
- ✅ Python Trading Agent (port 8000)  
- ✅ React Frontend (port 5173)

Then open: **http://localhost:5173**

### Option 2: Manual Start (3 Terminals)

#### Terminal 1: TypeScript Backend
```bash
npm start
# Runs on http://localhost:3001
```

#### Terminal 2: Python Trading Agent
```bash
python start_paper_trading.py
# Runs on http://localhost:8000
```

#### Terminal 3: React Frontend
```bash
npm run client:dev
# Runs on http://localhost:5173
```

Then open: **http://localhost:5173**

---

## 📊 Web Application Features

### Dashboard (`/`)
- Real-time market data
- Active positions
- Performance metrics
- System health status

### Trading Interface (`/trading`)
- Live price charts
- Manual trade execution
- Position management

### Analytics (`/analytics`)
- Trading performance
- Win rate statistics
- P&L analysis

### Risk Management (`/risk`)
- Position limits
- Risk metrics
- Stop-loss settings

### Configuration (`/config`)
- Trading parameters
- Risk settings
- Exchange configuration

### Monitoring (`/monitoring`)
- System health
- Data pipeline status
- Component metrics

---

## 🔧 Architecture

```
┌─────────────────┐
│  React Frontend │  (Port 5173)
│   (Vite Dev)    │
└────────┬─────────┘
         │ HTTP Proxy
         ▼
┌─────────────────┐
│ TypeScript API  │  (Port 3001)
│   (Express)     │
│                 │
│ • WebSocket     │
│ • Market Data   │
│ • Trading API   │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│ Python Agent    │  (Port 8000)
│                 │
│ • SMC Detection │
│ • Paper Trading │
│ • Risk Manager  │
└─────────────────┘
```

---

## 🌐 API Endpoints

### Frontend → TypeScript Backend (`/api/*`)

- `GET /api/trading/market-data` - Market data
- `GET /api/trading/positions` - Open positions
- `GET /api/trading/live-ohlcv` - OHLCV data for Python
- `GET /api/trading/paper-trades` - Paper trading history
- `GET /api/trading/account-summary` - Account balance
- `GET /api/trading/system-health` - System status

### TypeScript Backend → Python Backend (`http://localhost:8000`)

- `GET /api/python/paper-trades` - Trading history
- `GET /api/python/positions` - Open positions
- `GET /api/python/account` - Account summary

---

## 🔍 Troubleshooting

### Frontend shows "Failed to load data"
1. Check if TypeScript backend is running: `curl http://localhost:3001/api/health`
2. Check browser console for errors
3. Verify proxy configuration in `vite.config.ts`

### No market data
1. Check TypeScript backend logs: `tail -f logs/ts-backend.log`
2. Verify Binance WebSocket connection
3. Check if `MarketDataAggregator` initialized

### Python agent not responding
1. Check Python logs: `tail -f logs/python-agent.log`
2. Verify Python backend is running: `curl http://localhost:8000/api/python/account`
3. Check if TypeScript backend is accessible from Python

### Port already in use
```bash
# Kill processes on ports
lsof -ti:3001 | xargs kill -9
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

---

## 📝 Development

### Frontend Development
```bash
npm run client:dev
# Hot reload enabled
# Proxy configured to backend
```

### Backend Development
```bash
npm run server:dev
# Nodemon auto-restart
```

### Full Stack Development
```bash
npm run dev
# Runs both frontend and backend
```

---

## 🎯 Next Steps

1. **Open Dashboard**: http://localhost:5173
2. **Check System Health**: http://localhost:5173/monitoring
3. **View Paper Trades**: http://localhost:5173/trading
4. **Configure Settings**: http://localhost:5173/config

---

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Testing Guide](docs/TESTING_GUIDE.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)

