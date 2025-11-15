# Testing Guide - Verify Your SMC Trading Agent

Complete checklist to verify your trading system is working correctly.

---

## 🎯 Testing Philosophy

**Goal**: Verify that live data flows through the entire system and results in a paper trade.

**Time**: 15-20 minutes

---

## Pre-Flight Checklist

Before testing, ensure:

- [ ] All dependencies installed (`npm install` + `pip install -r requirements.txt`)
- [ ] `.env` file created with valid Binance API keys
- [ ] No other processes using ports 3001, 5173, or 8000

---

## Test Suite

### TEST 1: TypeScript Backend Startup

**Start**:
```bash
npm run server:dev
```

**Expected Output** (within 30 seconds):
```
✓ TypeScript backend started on http://localhost:3001
✓ Market data aggregator initialized successfully
✓ Binance WebSocket connected
```

**Verify**:
```bash
# Test basic health
curl http://localhost:3001/api/health

# Expected: {"success":true,"message":"ok"}
```

**✅ PASS if**: Health endpoint returns 200 OK

**❌ FAIL if**: Connection errors, port already in use

---

### TEST 2: Live Market Data Stream

**Test Endpoint**:
```bash
curl http://localhost:3001/api/trading/market-data
```

**Expected Response**:
```json
{
  "success": true,
  "data": [
    {
      "symbol": "BTCUSDT",
      "price": 43250.50,
      "change": 2.45,
      "volume": "1.2B",
      "source": "Binance",
      "timestamp": 1731686400000
    }
  ],
  "dataSource": "real-time"
}
```

**✅ PASS if**: 
- `success: true`
- `dataSource: "real-time"` (not "fallback")
- Price is realistic (current BTC range)

**❌ FAIL if**: 
- `dataSource: "fallback"` (means WebSocket failed)
- No data returned

---

### TEST 3: WebSocket Health

**Test Endpoint**:
```bash
curl http://localhost:3001/api/trading/data-health
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "marketData": {
      "activeSources": ["Binance"],
      "totalDataPoints": 5,
      "isHealthy": true
    },
    "connections": {
      "binance": true,
      "bybit": false,
      "total": 1
    }
  }
}
```

**✅ PASS if**:
- `activeSources` includes "Binance"
- `isHealthy: true`
- At least 1 connection active

---

### TEST 4: OHLCV Data Endpoint (Python Bridge)

**Test Endpoint**:
```bash
curl "http://localhost:3001/api/trading/live-ohlcv?symbol=BTCUSDT&limit=10"
```

**Expected Response**:
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-11-15T16:00:00.000Z",
      "open": 43200.50,
      "high": 43350.25,
      "low": 43180.00,
      "close": 43250.50,
      "volume": 1234567.89
    }
    // ... 9 more candles
  ],
  "symbol": "BTCUSDT",
  "source": "Binance"
}
```

**✅ PASS if**:
- Returns 10 OHLCV candles
- Prices are realistic
- Most recent candle has current price

---

### TEST 5: Python Backend Startup

**Start**:
```bash
python main.py
```

**Expected Output** (within 10 seconds):
```
INFO     SMC Trading Agent initialized
INFO     Trading mode: PAPER with $10000.00 balance
INFO     Live Data Client initialized for http://localhost:3001
INFO     Risk Manager initialized - Max Position: $1000, Max Daily Loss: $500
INFO     Paper Trading Engine initialized with $10000.00 balance
INFO     Starting orchestration cycle
```

**✅ PASS if**:
- No import errors
- "Trading mode: PAPER" displayed
- "Starting orchestration cycle" reached

**❌ FAIL if**:
- Import errors (missing dependencies)
- Connection errors to TypeScript backend

---

### TEST 6: Live Data Fetch by Python

**Watch Logs** (Terminal 2 - Python):

**Expected** (within 60 seconds of startup):
```
INFO     Starting new orchestration cycle
INFO     📊 Fetched 100 bars of live data for BTC/USDT 1h (latency: 45.2ms, source: Binance)
INFO     Market data received and validated (data_shape: (100, 6), quality_level: high)
```

**✅ PASS if**:
- "Fetched 100 bars" appears
- Source is "Binance" (not mock)
- Latency < 200ms

**❌ FAIL if**:
- "Failed to get market data"
- Connection refused errors

---

### TEST 7: SMC Pattern Detection

**Watch Logs** (within 5 minutes):

**Expected**:
```
INFO     📍 Detected 1 valid order block(s)
INFO     Order block detected: direction=bullish, strength=0.82, price_level=(43100, 43200)
```

**Or**:
```
INFO     No significant SMC patterns detected in this cycle
```

**✅ PASS if**:
- Either pattern detected OR "No significant patterns" (both valid)
- No exceptions or errors

---

### TEST 8: Trade Signal Generation

**Watch Logs** (when pattern is detected):

**Expected**:
```
INFO     🎯 SIMPLE SMC HEURISTIC: BUY signal generated (confidence: 82%, direction: bullish)
INFO     Calculated SL based on bullish order block (sl_price: 42,385.00)
INFO     Calculated TP for 3.0:1 R/R (tp_price: 45,850.00)
```

**✅ PASS if**:
- Signal generated (BUY or SELL)
- Stop loss calculated
- Take profit calculated
- Confidence > 70%

---

### TEST 9: Paper Trade Execution

**Watch Logs**:

**Expected**:
```
INFO     📈 PAPER ORDER EXECUTED: LONG 0.023 BTC/USDT @ $43,250.00 | SL: $42,385 | TP: $45,850 | Reason: SMC pattern detected with 82% confidence
INFO     ✅ Paper trade executed successfully
```

**Verify via API**:
```bash
curl http://localhost:8000/api/python/paper-trades
```

**Expected Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "paper_1731686400000",
      "symbol": "BTC/USDT",
      "side": "LONG",
      "size": 0.023,
      "entry_price": 43250.00,
      "stop_loss": 42385.00,
      "take_profit": 45850.00,
      "status": "OPEN",
      "pnl": 0.0,
      "timestamp": 1731686400.0,
      "datetime": "2025-11-15T16:00:00"
    }
  ]
}
```

**✅ PASS if**:
- Trade object returned
- Contains all required fields
- Status is "OPEN"

---

### TEST 10: Position Updates (Live P&L)

**Wait 60 seconds** (next cycle)

**Watch Logs**:
```
INFO     Update positions with live prices
INFO     Position BTCUSDT: unrealized P&L = $+12.50 (+0.58%)
```

**Verify via API**:
```bash
curl http://localhost:8000/api/python/positions
```

**Expected**: Position with updated `current_price` and `unrealized_pnl`

**✅ PASS if**:
- P&L updates with new price
- No errors

---

### TEST 11: Stop Loss Trigger (Simulated)

**Manually test** by modifying code temporarily:

```python
# In main.py, add after line 260:
# TEMPORARY TEST CODE
if execution_engine.positions:
    test_price = {validated_signal.symbol: validated_signal.entry_price * 0.97}  # -3% price
    execution_engine.update_positions(test_price)
```

**Expected Output**:
```
INFO     📉 POSITION CLOSED: LONG 0.023 BTC/USDT | Entry: $43,250 | Exit: $41,953 | P&L: $-29.85 (-1.30%) | Reason: Stop loss triggered
```

**✅ PASS if**: Position auto-closes when SL triggered

---

### TEST 12: Frontend Dashboard

**Open**: http://localhost:5173

**Verify**:
- [ ] Yellow "PAPER TRADING MODE" banner visible at top
- [ ] Market Overview shows BTC price (matches Binance)
- [ ] Active Positions card shows your paper trade
- [ ] System Health shows all components "healthy"
- [ ] Performance metrics display

**Test real-time updates**:
- Wait 30 seconds
- Refresh dashboard
- BTC price should update
- Position P&L should change slightly

**✅ PASS if**: All UI elements load and display data

---

### TEST 13: Risk Controls

**Test daily loss limit**:

**Manually trigger** (in Python console or modify code):
```python
# Set daily P&L to near limit
risk_manager.daily_pnl = -480  # Near $500 limit

# Check if warning appears
risk_manager.check_daily_loss_limit(risk_manager.daily_pnl)
```

**Expected Log**:
```
WARNING  ⚠️ Approaching daily loss limit: $-480.00 (limit: -$500.00)
```

**✅ PASS if**: Warning logged when near limit

---

### TEST 14: Account Summary

**Test Endpoint**:
```bash
curl http://localhost:8000/api/python/account
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "balance": 9990.00,
    "equity": 10002.50,
    "total_pnl": 2.50,
    "unrealized_pnl": 12.50,
    "open_positions": 1,
    "total_trades": 1,
    "win_rate": 0.0
  }
}
```

**✅ PASS if**:
- Balance + unrealized_pnl = equity
- Metrics are consistent

---

### TEST 15: End-to-End Integration

**Full flow test** (wait 10 minutes):

1. **TypeScript Backend**: Receives live price from Binance
2. **Python fetches** OHLCV via REST API
3. **SMC detector** finds order block
4. **Heuristic** generates BUY signal
5. **Risk manager** calculates SL/TP
6. **Paper engine** executes order
7. **Position updates** with live price
8. **Frontend displays** trade and P&L

**✅ PASS if**: Complete flow executes without errors

---

## 🚨 Critical Tests (Safety)

### Safety Test 1: Cannot Execute Real Orders

**Current System**:
- Paper trading engine only simulates
- No real order placement code exists
- Config default is `mode: "paper"`

**✅ PASS**: System CANNOT place real orders (yet)

---

### Safety Test 2: Stop Loss Always Calculated

**Check Logs** for every trade:
```
INFO     Calculated SL based on X order block
```

**✅ PASS if**: Every trade has stop loss

---

### Safety Test 3: Position Size Limits

**Test**:
```bash
# Try to open large position (should be rejected/adjusted)
# Modify position_size calculation to 100 BTC
```

**Expected Log**:
```
WARNING  Position value $4,325,000.00 exceeds max $1000.00
WARNING  Position size adjusted: Reduced to max position size $1000
```

**✅ PASS if**: Oversized positions are adjusted or rejected

---

## 📊 Success Criteria

Your system is **FULLY FUNCTIONAL** if:

- ✅ All 15 tests pass
- ✅ At least 1 paper trade executed within first hour
- ✅ P&L updates with live prices
- ✅ Stop loss and take profit calculated
- ✅ Dashboard shows live data
- ✅ No critical errors in logs
- ✅ Risk controls are enforced

---

## 🐛 Debugging Tips

### Enable Debug Logging

**Edit `config.yaml`**:
```yaml
app:
  log_level: "DEBUG"  # More verbose logs
```

**Restart Python backend** to see detailed logs.

### Check Process Logs

```bash
# TypeScript backend
tail -f logs/typescript-backend.log  # If logging to file

# Python backend
tail -f logs/smc_trading.log  # If logging to file
```

### Test Components Individually

**Test TypeScript WebSocket**:
```typescript
// In api/integrations/binanceWebsocket.ts
// Add console.log in onMessage handler
```

**Test Python LiveDataClient**:
```python
# In Python REPL
from data_pipeline.live_data_client import LiveDataClient
import asyncio

client = LiveDataClient()
data = asyncio.run(client.get_latest_ohlcv_data("BTC/USDT"))
print(data.head())
```

---

## 🎓 Next Steps After Passing Tests

1. **Run for 24 hours** - Verify stability
2. **Monitor daily P&L** - Track performance
3. **Adjust parameters** - Fine-tune based on results
4. **Add logging** - Export trade history for analysis
5. **Consider ML** - Train models on historical data (optional)

---

## 📈 Performance Benchmarks

### Expected Latencies (from logs)

```
Target: < 1s total per cycle

Actual breakdown:
- Live data fetch: 40-100ms
- SMC detection: 100-300ms
- Decision making: 10-50ms
- Risk calculations: 5-20ms
- Paper order execution: 1-5ms
─────────────────────────────
Total: ~200-500ms ✅
```

### System Resource Usage

**Check**:
```bash
# CPU and memory usage
ps aux | grep "node\|python"

# Expected:
# node: 50-100MB RAM, <5% CPU
# python: 150-300MB RAM, <10% CPU
```

---

## ✅ Final Verification

**Run this command sequence**:

```bash
# 1. Check TypeScript health
curl http://localhost:3001/api/trading/data-health | jq '.data.marketData.isHealthy'
# Expected: true

# 2. Check Python health  
curl http://localhost:8000/api/health | jq '.success'
# Expected: true

# 3. Get live OHLCV
curl "http://localhost:3001/api/trading/live-ohlcv?symbol=BTCUSDT&limit=5" | jq '.success'
# Expected: true

# 4. Check account
curl http://localhost:8000/api/python/account | jq '.data.balance'
# Expected: 10000 (or adjusted by P&L)

# 5. Open frontend
open http://localhost:5173
# Expected: Dashboard loads with live data
```

**If ALL 5 commands succeed**: 🎉 **SYSTEM IS FULLY OPERATIONAL**

---

## 🚀 Ready for Paper Trading

Once all tests pass, your system is ready for continuous paper trading.

**Recommended workflow**:
1. Let it run for 1 week
2. Monitor daily via Dashboard
3. Review logs for any issues
4. Adjust parameters based on performance
5. Only consider real trading after consistent profitability

**Good luck!** 🍀

