# SMC Trading Agent - Quick Start Guide

**Time to First Paper Trade: < 30 minutes**

This guide will get you from zero to your first paper trade with live Binance market data.

---

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ Live market data streaming from Binance
- ✅ SMC pattern detection running on real data
- ✅ Paper trading engine simulating trades with live prices
- ✅ Real-time dashboard showing positions and P&L
- ✅ All safety controls active (stop loss, position limits)

---

## 📋 Prerequisites

- **Node.js** 18+ installed
- **Python** 3.9+ installed
- **Binance account** with API keys (testnet or real)
- **5-10 minutes** of your time

---

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies (5 minutes)

```bash
cd /Users/arkadiuszfudali/Git/agent66/smc_trading_agent

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

**Expected output**: 
```
✓ Dependencies installed successfully
```

---

### Step 2: Configure API Keys (5 minutes)

```bash
# Copy environment template
cp env.example .env

# Edit with your API keys
nano .env
```

**Add your Binance API keys**:
```bash
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_secret_here
```

**Important**: 
- Get API keys from: https://www.binance.com/en/my/settings/api-management
- For paper trading, **read-only keys are sufficient**
- For real trading (later), enable **spot trading permissions**

---

### Step 3: Start TypeScript Backend (2 minutes)

```bash
# Terminal 1
npm run server:dev
```

**Expected output**:
```
✓ TypeScript backend started on http://localhost:3001
✓ Market data aggregator initialized
✓ WebSocket connection to Binance established
✓ Subscribing to BTCUSDT live data
```

**Verify**:
```bash
# In another terminal
curl http://localhost:3001/api/trading/market-data
```

Should return live BTC price.

---

### Step 4: Start Python Trading Agent (2 minutes)

```bash
# Terminal 2
python main.py
```

**Expected output**:
```
✓ SMC Trading Agent initialized
✓ Trading mode: PAPER with $10000.00 balance
✓ Live Data Client initialized
✓ Risk Manager initialized - Max Position: $1000, Max Daily Loss: $500
✓ Paper Trading Engine initialized with $10000.00 balance
✓ Starting orchestration cycle
```

---

### Step 5: Start Frontend (2 minutes)

```bash
# Terminal 3
npm run client:dev
```

**Expected output**:
```
✓ Frontend started
  ➜ Local:   http://localhost:5173
```

**Open in browser**: http://localhost:5173

---

### Step 6: Watch First Paper Trade (10 minutes)

**What happens automatically:**

1. **Minute 0-1**: System fetches live OHLCV data from TypeScript backend
2. **Minute 1-2**: SMC detector analyzes for order blocks
3. **Minute 2-3**: If pattern detected → generates BUY/SELL signal
4. **Minute 3-4**: Risk manager calculates stop loss & take profit
5. **Minute 4-5**: Paper trading engine executes simulated order
6. **Minute 5+**: Position tracked with live price updates

**Watch Terminal 2 logs for**:
```
📊 Fetched 100 bars of live data for BTC/USDT 1h (latency: 42.3ms, source: Binance)
✓ Market data received and validated
📍 Detected 1 valid order block(s)
🎯 SIMPLE SMC HEURISTIC: BUY signal generated (confidence: 82%, direction: bullish)
✓ Calculated SL based on bullish order block
✓ Calculated TP for 3.0:1 R/R
📈 PAPER ORDER EXECUTED: LONG 0.023 BTC/USDT @ $43,250.00 | SL: $42,385 | TP: $45,850
✅ Paper trade executed successfully
```

**Check Dashboard**:
- Go to http://localhost:5173
- You should see:
  - "PAPER TRADING MODE" yellow banner
  - Live BTC price updating
  - Your paper trade in "Active Positions"
  - P&L updating in real-time

---

## 🔍 Verification Checklist

### ✅ TypeScript Backend Health

```bash
curl http://localhost:3001/api/health
# Expected: {"success": true, "message": "ok"}

curl http://localhost:3001/api/trading/data-health
# Expected: JSON with activeSources: ["Binance"]
```

### ✅ Python Backend Health

```bash
curl http://localhost:8000/api/health
# Expected: Health status JSON

curl http://localhost:8000/api/python/account
# Expected: {success: true, data: {balance: 10000, equity: ...}}
```

### ✅ Live Data Flow

```bash
curl "http://localhost:3001/api/trading/live-ohlcv?symbol=BTCUSDT&limit=10"
# Expected: Array of 10 OHLCV candles with live data
```

### ✅ Paper Trades

```bash
curl http://localhost:8000/api/python/paper-trades
# Expected: Array of executed paper trades (empty initially)
```

---

## 🐛 Troubleshooting

### Issue: "Market data aggregator not initialized"

**Solution**:
```bash
# Check if Binance API keys are set
cat .env | grep BINANCE

# Restart TypeScript backend
# Check logs for WebSocket connection errors
```

### Issue: "Failed to fetch live OHLCV data"

**Solution**:
1. Ensure TypeScript backend is running on port 3001
2. Test endpoint manually:
   ```bash
   curl http://localhost:3001/api/trading/live-ohlcv?symbol=BTCUSDT
   ```
3. Check TypeScript backend logs for errors

### Issue: "No significant SMC patterns detected"

**Solution**:
- This is normal! Markets don't always have clear patterns
- Wait 5-10 minutes for market volatility
- Or lower the confidence threshold in `config.yaml`:
  ```yaml
  decision_engine:
    confidence_threshold: 0.60  # Lower from 0.70
  ```

### Issue: Python dependencies missing

**Solution**:
```bash
pip install --upgrade pip
pip install -r requirements.txt

# If specific package fails, install individually:
pip install fastapi uvicorn pandas numpy aiohttp
```

---

## 📊 Understanding the Dashboard

### Market Overview Card
- Shows live prices for configured symbols
- Updates every 30 seconds
- Source: Binance WebSocket

### Active Positions Card
- Shows open paper trades
- Real-time P&L based on live prices
- Entry price, current price, SL, TP

### System Health Card
- Data Pipeline: Connection to TypeScript backend
- SMC Detection: Pattern recognition status
- Execution Engine: Paper trading engine status
- Risk Manager: Risk controls active

### Performance Metrics
- Total P&L: Cumulative paper trading profit/loss
- Sharpe Ratio: Risk-adjusted returns
- Max Drawdown: Largest peak-to-trough decline
- Win Rate: Percentage of profitable trades

---

## ⚙️ Configuration

### Trading Parameters

Edit `config.yaml`:

```yaml
app:
  mode: "paper"  # Change to "real" only when ready

paper_trading:
  initial_balance: 10000.0  # Starting capital
  max_positions: 3          # Max concurrent positions

risk_manager:
  max_position_size: 1000   # Max USD per position
  max_daily_loss: 500       # Max daily loss
  stop_loss_percent: 2.0    # Stop loss % from entry
  take_profit_ratio: 3.0    # Risk:Reward ratio

decision_engine:
  confidence_threshold: 0.70  # Min confidence to trade
```

### Adjusting for Your Strategy

**More Conservative**:
```yaml
risk_manager:
  max_position_size: 500    # Smaller positions
  max_daily_loss: 200       # Tighter daily limit
  stop_loss_percent: 1.5    # Tighter stops
```

**More Aggressive**:
```yaml
risk_manager:
  max_position_size: 2000   # Larger positions
  max_daily_loss: 1000      # Higher daily limit
  stop_loss_percent: 3.0    # Wider stops

decision_engine:
  confidence_threshold: 0.60  # Lower threshold (more trades)
```

---

## 🎓 Next Steps

### After First Paper Trade

1. **Monitor Performance** (1 week)
   - Track win rate, Sharpe ratio, drawdowns
   - Adjust parameters based on results
   - Ensure strategy is consistently profitable

2. **Optimize Parameters** (ongoing)
   - Fine-tune stop loss / take profit ratios
   - Adjust confidence thresholds
   - Test different position sizing

3. **Add More Symbols** (optional)
   - Edit `config.yaml` to add more symbols:
     ```yaml
     exchanges:
       binance:
         symbols:
           - "BTCUSDT"
           - "ETHUSDT"
           - "ADAUSDT"
     ```

4. **Enable ML Models** (advanced)
   - Train models on historical data
   - Switch decision_engine mode to "ml"
   - Compare ML vs heuristic performance

### Switching to Real Trading

**⚠️ ONLY when ready and profitable in paper mode**:

1. Ensure 1-2 months of consistent paper trading profits
2. Start with MINIMAL capital (max $100-500)
3. Change config:
   ```yaml
   app:
     mode: "real"  # DANGER: Real money now!
   ```
4. Enable trading permissions on Binance API keys
5. Monitor VERY carefully for first few days

---

## 📈 Performance Expectations

### Realistic Metrics (Personal Use)

- **Trades per day**: 1-5
- **Win rate**: 55-70%
- **Average holding time**: 2-6 hours
- **Sharpe ratio**: 1.0-2.0
- **Max drawdown**: 5-15%

### System Performance

- **Data latency**: < 100ms
- **Decision latency**: < 1s
- **Execution latency**: Instant (paper) / 50-200ms (real)
- **Memory usage**: < 500MB
- **CPU usage**: < 5% idle, < 20% active

---

## 🆘 Support

### Getting Help

1. **Check logs**: Terminal 2 (Python) has detailed logs
2. **Health endpoints**: Test `/api/health` and `/api/trading/data-health`
3. **Configuration**: Review `config.yaml` for errors

### Common Questions

**Q: Why no trades after 30 minutes?**
A: SMC patterns are rare. Try lowering `confidence_threshold` or wait for market volatility.

**Q: Can I run this 24/7?**
A: Yes! Both TypeScript and Python backends are designed for continuous operation.

**Q: How much capital do I need?**
A: Paper trading = $0. Real trading = start with $100-500 until proven profitable.

**Q: When should I switch to real trading?**
A: After 1-2 months of consistent paper trading profits with acceptable drawdowns.

---

## 📝 Daily Workflow

### Morning Routine
```bash
# Terminal 1: Start TypeScript backend
npm run server:dev

# Terminal 2: Start Python agent
python main.py

# Terminal 3: Start frontend (optional)
npm run client:dev

# Check system status
curl http://localhost:3001/api/trading/data-health
```

### During the Day
- Monitor Dashboard: http://localhost:5173
- Check Python logs for trade executions
- Verify stop losses are working

### Evening Review
```bash
# Get today's performance
curl http://localhost:8000/api/python/account

# Review trade history
curl http://localhost:8000/api/python/paper-trades

# Export logs for analysis (optional)
```

---

## 🎉 Success Criteria

Your system is working correctly when you see:

✅ **Live prices updating** in Dashboard every 30s
✅ **Python logs showing** "Fetched X bars of live data"
✅ **At least 1 order block** detected within 60 minutes
✅ **At least 1 paper trade** executed within 2 hours
✅ **Stop loss/take profit** calculated for each trade
✅ **Position P&L updating** with live prices
✅ **No critical errors** in logs

---

**Built for speed. Keep it simple. Trade safely. 🚀**

