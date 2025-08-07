# ASCII Diagram architektury technicznej SMC Trading Agent
ascii_diagram = """
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       🤖 SMC TRADING AGENT - TECHNICAL ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  DATA INGESTION │────▶│   FEATURE STORE  │────▶│   SMC DETECTOR  │────▶│ DECISION POLICY │
│                 │    │                  │    │                 │    │    (RL/PPO)     │
│ • WebSocket API │    │ • TimescaleDB    │    │ • Order Blocks  │    │                 │
│ • REST APIs     │    │ • Redis Cache    │    │ • CHOCH/BOS     │    │ • State: OHLCV+ │
│ • L2 Order Book │    │ • Feature Eng.   │    │ • Liquidity     │    │ • Action: L/S/H │
│ • Volume Profile│    │ • Multi-TF Data  │    │ • FVG Detection │    │ • Reward: PnL   │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ DATA SOURCES:   │    │ PROCESSED DATA:  │    │ SMC FEATURES:   │    │ ML MODELS:      │
│                 │    │                  │    │                 │    │                 │
│ • Binance WS    │    │ • OHLCV 1s-1h    │    │ • MSS Detection │    │ • PPO Agent     │
│ • ByBit API     │    │ • Order Book L2  │    │ • Swing H/L     │    │ • LSTM Network  │
│ • OANDA FIX     │    │ • Volume Delta   │    │ • Liquidity     │    │ • Transformer   │
│ • NewsAPI       │    │ • News Sentiment │    │ • Imbalances    │    │ • Ensemble      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
                                 │                        │                        │
                                 └────────────────────────┼────────────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  RISK MANAGER   │◀───│ TRADE EXECUTOR   │◀───│     LOGGER      │◀───│   MONITORING    │
│                 │    │     (CCXT)       │    │                 │    │                 │
│ • Position Size │    │                  │    │ • Trade Log     │    │ • Grafana       │
│ • Max Drawdown  │    │ • Order Routing  │    │ • Performance   │    │ • Prometheus    │
│ • Correlation   │    │ • Smart Routing  │    │ • Error Log     │    │ • Alerts        │
│ • VaR Limits    │    │ • Latency <100ms │    │ • Audit Trail   │    │ • Health Check  │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼ 
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ RISK CONTROLS:  │    │ EXCHANGES:       │    │ DATA STORAGE:   │    │ OPERATIONS:     │
│                 │    │                  │    │                 │    │                 │
│ • Circuit Breaker│   │ • Binance Spot   │    │ • PostgreSQL    │    │ • Docker        │
│ • Max DD 8%     │    │ • Binance Futures│    │ • TimescaleDB   │    │ • Kubernetes    │
│ • Stop Loss     │    │ • ByBit Perps    │    │ • Redis Cache   │    │ • CI/CD         │
│ • Take Profit   │    │ • OANDA Forex    │    │ • S3 Backups    │    │ • Load Balancer │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW LEGEND                                      │
│  ────▶ : Real-time data flow (WebSocket/streaming)                                  │
│  ◀──── : Feedback/control signals                                                   │
│  ═════▶: High-priority trading signals                                              │
│  ┌────┐ : Stateful components (databases, caches)                                   │
│  ◦ TF  : Multi-timeframe (1s, 5s, 1m, 5m, 15m, 1h)                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
"""

print(ascii_diagram)

# Format danych szczegółowy
data_format = """
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           📊 FORMAT DANYCH - SZCZEGÓŁOWA SPECYFIKACJA                │
└─────────────────────────────────────────────────────────────────────────────────────┘

🔹 OHLCV BASE DATA:
```json
{
  "timestamp": 1691366400000,           # Unix timestamp (ms)
  "symbol": "BTCUSDT",                  # Trading pair
  "timeframe": "1m",                    # 1s, 5s, 1m, 5m, 15m, 1h
  "open": 29156.78,                     # Open price
  "high": 29189.42,                     # High price  
  "low": 29145.33,                      # Low price
  "close": 29167.91,                    # Close price
  "volume": 145.234,                    # Base volume
  "quote_volume": 4234567.89,           # Quote volume
  "trades_count": 1547                  # Number of trades
}
```

🔹 ORDER BOOK L2 DATA:
```json
{
  "timestamp": 1691366400123,
  "symbol": "BTCUSDT", 
  "bids": [
    [29165.50, 0.045],                  # [price, quantity]
    [29165.25, 0.123],
    [29165.00, 0.234]
  ],
  "asks": [
    [29166.00, 0.078],
    [29166.25, 0.156], 
    [29166.50, 0.089]
  ],
  "bid_depth": 1.456,                   # Total bid volume
  "ask_depth": 1.234,                   # Total ask volume
  "spread": 0.50                        # Bid-ask spread
}
```

🔹 SMC FEATURES:
```json
{
  "timestamp": 1691366400000,
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  
  "order_blocks": {
    "bullish": [
      {
        "top": 29145.67,                # OB top price
        "bottom": 29134.22,             # OB bottom price  
        "volume": 234.56,               # Volume at formation
        "strength": 0.78,               # OB strength (0-1)
        "age": 145                      # Candles since formation
      }
    ],
    "bearish": [...]
  },
  
  "fair_value_gaps": [
    {
      "top": 29178.90,
      "bottom": 29165.45, 
      "direction": "bullish",           # bullish/bearish
      "filled": false,                  # Gap fill status
      "timeframe": "1m"
    }
  ],
  
  "market_structure": {
    "trend": "bullish",                 # bullish/bearish/ranging
    "choch": false,                     # Change of Character
    "bos": true,                        # Break of Structure  
    "swing_high": 29189.42,
    "swing_low": 29134.22,
    "structure_age": 23                 # Candles since last MSS
  },
  
  "liquidity": {
    "buy_side": [29195.50, 29201.25],  # Resistance levels
    "sell_side": [29128.75, 29115.30], # Support levels
    "sweep_detected": false,            # Recent liquidity sweep
    "sweep_direction": null             # "buy"/"sell"
  }
}
```
"""

print(data_format)

# Stop-loss/Take-profit strategies
strategies = """
┌─────────────────────────────────────────────────────────────────────────────────────┐
│              🎯 STRATEGIE STOP-LOSS/TAKE-PROFIT Z WYKORZYSTANIEM SMC                 │  
└─────────────────────────────────────────────────────────────────────────────────────┘

🔴 STOP-LOSS STRATEGIES:

1. ORDER BLOCK STOP-LOSS:
   • Long: SL poniżej 50% bullish order block  
   • Short: SL powyżej 50% bearish order block
   • Buffer: 0.1-0.2% poniżej/powyżej dla spread protection
   
2. LIQUIDITY VOID STOP-LOSS:
   • Umieszczenie SL w strefach niskiej płynności
   • Wykorzystanie Fair Value Gaps jako "safe zones"
   • Unikanie obszarów wysokiej liquidity concentration

3. STRUCTURE-BASED STOP-LOSS:
   • Long: SL poniżej ostatniego swing low
   • Short: SL powyżej ostatniego swing high  
   • Dodatkowy buffer na market noise (5-10 pips forex)

🟢 TAKE-PROFIT STRATEGIES:

1. OPPOSING ORDER BLOCK TP:
   • Long: TP na bearish order block resistance
   • Short: TP na bullish order block support
   • Partial profits: 50% na pierwszym OB, 50% na kolejnym

2. LIQUIDITY TARGET TP:
   • Targeting areas of high liquidity concentration
   • Buy-side/sell-side liquidity sweeps jako exit points
   • Dynamic TP adjustment based on liquidity depth

3. FIBONACCI + SMC TP:
   • 61.8%/78.6% Fibonacci levels combined z SMC zones
   • Order blocks acting as fibonacci confluence
   • Extension levels (127.2%, 161.8%) dla swing targets

```python
class SMCRiskManager:
    def calculate_stop_loss(self, entry_price, direction, order_blocks, structure):
        if direction == "LONG":
            # Find nearest bullish order block below entry
            relevant_ob = self.find_nearest_bullish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['bottom'] * 0.999  # 0.1% buffer
            else:
                # Fallback to structure-based SL
                sl_price = structure['swing_low'] * 0.995  # 0.5% buffer
        
        elif direction == "SHORT": 
            relevant_ob = self.find_nearest_bearish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['top'] * 1.001   # 0.1% buffer
            else:
                sl_price = structure['swing_high'] * 1.005  # 0.5% buffer
                
        return sl_price
    
    def calculate_take_profit(self, entry_price, direction, liquidity_zones, fvg_zones):
        targets = []
        
        if direction == "LONG":
            # Target 1: Next resistance/bearish OB
            target1 = self.find_next_resistance(entry_price, liquidity_zones)
            targets.append(target1)
            
            # Target 2: Unfilled FVG above
            unfilled_fvg = self.find_unfilled_fvg_above(entry_price, fvg_zones)
            if unfilled_fvg:
                targets.append(unfilled_fvg['bottom'])
                
        return targets[:2]  # Maximum 2 TP levels
```

🔄 DYNAMIC ADJUSTMENT:
• Real-time monitoring liquidity changes
• Adjustment based na market volatility (ATR)
• Trail stops using order block levels
• Risk-reward ratio minimum 1:2, target 1:3
"""  

print(strategies)

# Zapisanie do pliku
with open('smc_technical_architecture.txt', 'w', encoding='utf-8') as f:
    f.write(ascii_diagram + "\n\n" + data_format + "\n\n" + strategies)

print(f"\n✅ Architektura techniczna zapisana do 'smc_technical_architecture.txt'")