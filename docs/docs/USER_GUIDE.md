# SMC Trading Agent User Guide

This comprehensive user guide provides everything you need to know about using the SMC Trading Agent, from basic setup to advanced trading strategies.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [System Overview](#system-overview)
4. [Configuration](#configuration)
5. [Trading Operations](#trading-operations)
6. [Risk Management](#risk-management)
7. [Market Analysis](#market-analysis)
8. [Performance Monitoring](#performance-monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)

## Introduction

### What is SMC Trading Agent?

The SMC (Smart Money Concepts) Trading Agent is an advanced automated trading system that combines sophisticated market analysis with risk management to execute trades across multiple cryptocurrency exchanges. The system uses Smart Money Concepts, a proven trading methodology that identifies institutional order flow and market manipulation patterns.

### Key Features

- **Smart Money Concepts (SMC) Analysis**: Advanced pattern recognition for institutional trading setups
- **Multi-Exchange Support**: Trade on Binance, ByBit, and OANDA
- **Risk Management**: Comprehensive risk controls with position sizing and stop losses
- **Real-time Market Data**: Live market data streaming and analysis
- **Paper Trading**: Test strategies without financial risk
- **Performance Analytics**: Detailed trading performance analysis and reporting
- **Web Interface**: User-friendly dashboard for monitoring and control
- **API Access**: REST and WebSocket APIs for custom integrations

### Who Should Use This System?

**Suitable for:**
- Experienced traders familiar with Smart Money Concepts
- Quantitative traders seeking automated execution
- Investment firms requiring systematic trading
- Traders wanting to implement algorithmic strategies
- Risk-averse traders requiring strict risk management

**Not suitable for:**
- Complete beginners to trading
- Traders seeking "get rich quick" solutions
- Those unwilling to learn risk management
- Users seeking guaranteed profits

## Getting Started

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- Memory: 4GB RAM
- Storage: 20GB
- Network: Stable internet connection
- OS: Windows 10+, macOS 10.15+, or Linux

**Recommended Requirements:**
- CPU: 4+ cores
- Memory: 8GB+ RAM
- Storage: 50GB+ SSD
- Network: Low-latency connection (<100ms to exchanges)

### Installation Steps

**1. System Setup**

```bash
# Clone the repository
git clone https://github.com/your-org/smc-trading-agent.git
cd smc-trading-agent

# Create environment configuration
cp .env.example .env
```

**2. Configure API Keys**

Edit the `.env` file with your exchange API credentials:

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Optional additional exchanges
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
OANDA_API_KEY=your_oanda_api_key
OANDA_TOKEN=your_oanda_token
```

**3. Install Dependencies**

```bash
# Python dependencies
pip install -r requirements.txt

# Rust execution engine (if needed)
cd src/execution_engine
cargo build --release
```

**4. Initial Configuration**

Configure basic trading parameters:

```yaml
# config.yaml
app:
  mode: "paper"  # Start with paper trading
  log_level: "INFO"

trading:
  initial_balance: 10000.0
  max_positions: 3
  position_size_percent: 1.0

exchanges:
  binance:
    enabled: true
    symbols:
      - "BTCUSDT"

risk_manager:
  max_position_size: 1000.0
  max_daily_loss: 500.0
  stop_loss_percent: 2.0
```

**5. Start the System**

```bash
# Start with Docker Compose (recommended)
docker-compose up -d

# Or run natively
python main.py
```

**6. Verify Installation**

Access the web interface:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Health Check: http://localhost:8000/health

### First Run Checklist

- [ ] Exchange API keys configured and tested
- [ ] Paper trading mode enabled
- [ ] Initial settings reviewed
- [ ] Risk limits set appropriately
- [ ] System health check passing
- [ ] Market data flowing correctly

## System Overview

### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Web UI                     │
│                  (React Dashboard)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   API Gateway                           │
│              (Authentication & Routing)                │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Core Trading Engine                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ SMC Detector│ │ Decision    │ │ Execution       │   │
│  │             │ │ Engine      │ │ Engine          │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                Risk Manager                             │
│        (Position Sizing & Risk Controls)               │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Data Pipeline                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ Market Data │ │ WebSocket   │ │ Historical      │   │
│  │ Ingestion   │ │ Streaming   │ │ Database       │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Components Explained

**SMC Detector**
- Identifies Smart Money Concepts patterns
- Detects Order Blocks, CHoCH/BOS, FVGs
- Analyzes liquidity sweeps and market structure
- Provides confluence scoring

**Decision Engine**
- Combines multiple analysis techniques
- ML-enhanced signal generation
- Confidence scoring for trade signals
- Risk-adjusted position sizing

**Execution Engine**
- Ultra-low latency trade execution (<50ms)
- Smart order routing
- Slippage minimization
- Real-time execution monitoring

**Risk Manager**
- Pre-trade risk validation
- Real-time position monitoring
- Dynamic position sizing
- Circuit breaker protection

**Data Pipeline**
- Real-time market data processing
- Historical data management
- WebSocket streaming
- Data quality validation

### Trading Workflow

1. **Market Data Ingestion**
   - Real-time price feeds from exchanges
   - Order book depth data
   - Trade flow analysis
   - Volume and volatility metrics

2. **SMC Pattern Recognition**
   - Identify Order Blocks
   - Detect CHoCH/BOS patterns
   - Find Fair Value Gaps (FVGs)
   - Analyze liquidity sweeps

3. **Signal Generation**
   - Pattern confluence analysis
   - Multi-timeframe confirmation
   - Risk-reward assessment
   - Confidence scoring

4. **Risk Validation**
   - Position size calculation
   - Stop loss placement
   - Exposure limits checking
   - Correlation analysis

5. **Trade Execution**
   - Order placement
   - Execution monitoring
   - Slippage tracking
   - Fill confirmation

6. **Post-Trade Management**
   - Position monitoring
   - Trailing stops
   - Profit targets
   - Performance tracking

## Configuration

### Main Configuration File

The system is configured through `config.yaml`:

```yaml
# Application Settings
app:
  name: "SMC Trading Agent"
  mode: "paper"  # paper or live
  log_level: "INFO"
  debug: false

# Trading Configuration
trading:
  initial_balance: 10000.0
  max_positions: 3
  position_size_percent: 1.0
  update_interval: 10

# Exchange Settings
exchanges:
  binance:
    enabled: true
    testnet: true  # Use testnet for paper trading
    symbols:
      - "BTCUSDT"
      - "ETHUSDT"
    rate_limit: 1200

# Risk Management
risk_manager:
  max_position_size: 1000.0
  max_daily_loss: 500.0
  max_drawdown: 0.10  # 10%
  stop_loss_percent: 2.0
  take_profit_ratio: 3.0
  position_limits:
    BTCUSDT: 0.1
    ETHUSDT: 2.0

# SMC Detection Settings
smc_detector:
  min_volume_threshold: 1000000
  min_price_change: 0.001
  time_window: 300  # 5 minutes
  confidence_threshold: 0.7
  indicators:
    volume_spike: true
    price_momentum: true
    order_flow_imbalance: true
    liquidity_analysis: true

# Decision Engine
decision_engine:
  mode: "hybrid"  # heuristic, ml_ensemble, hybrid
  confidence_threshold: 0.70
  use_ml_ensemble: true
  min_ml_confidence: 0.60

# Execution Engine
execution_engine:
  max_slippage: 0.001  # 0.1%
  execution_timeout: 30
  retry_attempts: 3
  order_types:
    - "market"
    - "limit"
    - "stop_loss"
    - "take_profit"

# Monitoring
monitoring:
  health_check_interval: 60
  port: 8000
  metrics_collection: true

# Database
database:
  type: "sqlite"
  path: "data/trades.db"
```

### Environment Variables

Sensitive configuration should use environment variables:

```bash
# Exchange API Credentials
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_API_SECRET="your_binance_api_secret"
export BYBIT_API_KEY="your_bybit_api_key"
export BYBIT_API_SECRET="your_bybit_api_secret"

# Database Credentials
export DATABASE_URL="postgresql://user:pass@localhost:5432/smc_trading"
export REDIS_URL="redis://localhost:6379"

# Security
export JWT_SECRET="your_jwt_secret_key"
export API_KEY_REQUIRED="true"

# Trading Mode
export TRADING_MODE="paper"  # paper or live
export INITIAL_BALANCE="10000"

# Logging
export LOG_LEVEL="INFO"
export METRICS_ENABLED="true"
```

### Advanced Configuration

**Multi-Timeframe Analysis:**
```yaml
multi_timeframe:
  enabled: true
  symbols: ["BTCUSDT", "ETHUSDT"]
  timeframes: ["M5", "M15", "H1", "H4", "D1"]
  analysis_interval_minutes: 5
  min_confidence: 0.7
  max_concurrent_symbols: 10
```

**ML Ensemble Configuration:**
```yaml
ml_ensemble:
  enabled: true
  models:
    lstm:
      enabled: true
      confidence_weight: 0.3
    transformer:
      enabled: true
      confidence_weight: 0.4
    ppo:
      enabled: true
      confidence_weight: 0.3
  retraining_interval: 24  # hours
  min_confidence: 0.6
```

**Notification Settings:**
```yaml
notifications:
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your_email@gmail.com"
    password: "your_app_password"

  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    channel: "#trading-alerts"

  discord:
    enabled: false
    webhook_url: "https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK"
```

## Trading Operations

### Paper Trading vs Live Trading

**Paper Trading (Recommended for Beginners):**
- No real money at risk
- Uses simulated market data
- Full feature testing
- Strategy validation
- Risk-free learning

**Live Trading (Advanced Users Only):**
- Real money trading
- Requires thorough testing
- Higher stakes and risks
- Real market conditions
- Requires experience

### Starting Paper Trading

**1. Enable Paper Mode:**
```yaml
app:
  mode: "paper"
```

**2. Set Initial Balance:**
```yaml
trading:
  initial_balance: 10000.0
```

**3. Configure Risk Limits:**
```yaml
risk_manager:
  max_position_size: 1000.0
  max_daily_loss: 500.0
```

**4. Start Trading:**
```bash
# Start with paper trading configuration
python main.py --mode=paper
```

### Executing Trades

**Manual Trade Execution:**

**Via Web Interface:**
1. Navigate to Trading Dashboard
2. Select symbol (e.g., BTCUSDT)
3. Choose order type (market/limit)
4. Enter quantity
5. Set stop loss and take profit
6. Confirm and execute

**Via API:**
```bash
curl -X POST http://localhost:8000/v1/trades \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "market",
    "quantity": 0.1,
    "stop_loss": 44000.0,
    "take_profit": 46000.0
  }'
```

**Via Python SDK:**
```python
from smc_trading import SMCClient

client = SMCClient(api_token="YOUR_TOKEN")

# Execute trade
trade = client.execute_trade(
    symbol="BTCUSDT",
    side="buy",
    quantity=0.1,
    type="market",
    stop_loss=44000.0,
    take_profit=46000.0
)

print(f"Trade executed: {trade}")
```

### Automated Trading

**Enable Automated Trading:**

**1. Configure Trading Strategy:**
```yaml
decision_engine:
  mode: "hybrid"
  confidence_threshold: 0.70
  auto_trade: true
```

**2. Set Risk Parameters:**
```yaml
risk_manager:
  auto_position_sizing: true
  risk_per_trade: 0.02  # 2% risk per trade
  max_correlation: 0.7
```

**3. Start Automated Trading:**
```python
# Start automated trading
client.start_auto_trading()

# Monitor automated trades
trades = client.get_recent_trades(limit=10)
for trade in trades:
    print(f"Auto trade: {trade}")
```

### Order Management

**View Open Orders:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/orders
```

**Cancel Order:**
```bash
curl -X DELETE http://localhost:8000/v1/orders/ORDER_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Modify Order:**
```bash
curl -X PUT http://localhost:8000/v1/orders/ORDER_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 0.2,
    "price": 45500.0
  }'
```

### Position Management

**View Current Positions:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/positions
```

**Close Position:**
```bash
curl -X POST http://localhost:8000/v1/positions/close \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "quantity": 0.1
  }'
```

**Set Trailing Stop:**
```bash
curl -X POST http://localhost:8000/v1/positions/trailing-stop \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "trailing_stop_percent": 2.0
  }'
```

## Risk Management

### Understanding Risk Management

Risk management is the most critical component of successful trading. The SMC Trading Agent implements multiple layers of risk protection:

**1. Position Sizing**
- Calculates optimal position size based on account balance
- Considers risk per trade and volatility
- Adjusts for correlation with existing positions

**2. Stop Loss Protection**
- Automatic position closure at predefined loss levels
- Trailing stops for profit protection
- Emergency stop for market volatility

**3. Exposure Limits**
- Maximum total market exposure
- Per-symbol position limits
- Daily loss limits

**4. Correlation Management**
- Prevents overexposure to correlated assets
- Portfolio diversification enforcement
- Sector concentration limits

### Configuring Risk Parameters

**Basic Risk Settings:**
```yaml
risk_manager:
  # Position sizing
  max_position_size: 1000.0  # Maximum position value in USD
  risk_per_trade: 0.02  # Risk 2% of account per trade

  # Stop loss settings
  stop_loss_percent: 2.0  # 2% stop loss
  trailing_stop_enabled: true
  trailing_stop_percent: 1.5

  # Exposure limits
  max_total_exposure: 0.5  # 50% of account balance
  max_daily_loss: 500.0  # Maximum daily loss in USD
  max_drawdown: 0.15  # 15% maximum drawdown

  # Position limits per symbol
  position_limits:
    BTCUSDT: 0.1  # Maximum 0.1 BTC
    ETHUSDT: 2.0  # Maximum 2 ETH
```

**Advanced Risk Settings:**
```yaml
risk_manager:
  # Correlation management
  correlation_matrix:
    BTCUSDT-ETHUSDT: 0.8
    BTCUSDT-ADAUSDT: 0.6
  max_correlation_exposure: 0.3

  # Volatility-based sizing
  volatility_adjustment: true
  atr_multiplier: 2.0
  max_volatility: 0.05  # 5% daily volatility

  # Time-based risk
  max_holding_time: 72  # hours
  overnight_risk_reduction: 0.5

  # Circuit breakers
  circuit_breaker_enabled: true
  consecutive_loss_limit: 5
  volume_spike_threshold: 3.0
```

### Position Sizing Explained

The system uses sophisticated position sizing algorithms:

**1. Fixed Fractional Sizing**
```python
# Risk 2% per trade
account_balance = 10000
risk_per_trade = 0.02
max_risk = account_balance * risk_per_trade  # $200

# Position size based on stop loss
entry_price = 45000
stop_loss = 44100  # 2% stop loss
risk_per_share = entry_price - stop_loss  # $900

position_size = max_risk / risk_per_share  # 0.222 BTC
```

**2. Volatility-Adjusted Sizing**
```python
# Adjust position size based on volatility
atr = 500  # Average True Range
volatility_multiplier = 2.0
adjusted_risk = atr * volatility_multiplier  # $1000

# Recalculate position size
position_size = max_risk / adjusted_risk  # Smaller position
```

**3. Correlation-Adjusted Sizing**
```python
# Reduce position size for correlated assets
existing_btc_position = 0.1
eth_btc_correlation = 0.8
correlation_adjustment = 1 - (existing_btc_position * correlation)

base_position_size = 0.2
adjusted_position_size = base_position_size * correlation_adjustment  # 0.084
```

### Stop Loss Strategies

**1. Fixed Percentage Stop Loss**
```yaml
risk_manager:
  stop_loss_type: "percentage"
  stop_loss_percent: 2.0
```

**2. Volatility-Based Stop Loss (ATR)**
```yaml
risk_manager:
  stop_loss_type: "atr"
  atr_multiplier: 2.0
  atr_period: 14
```

**3. Support/Resistance Stop Loss**
```yaml
risk_manager:
  stop_loss_type: "sma"
  stop_loss_distance: 2.0
  stop_loss_period: 20
```

**4. Trailing Stop Loss**
```yaml
risk_manager:
  trailing_stop_enabled: true
  trailing_stop_type: "percentage"
  trailing_stop_percent: 1.5
  trailing_stop_activation: 1.0  # Activate after 1% profit
```

### Monitoring Risk Metrics

**Current Risk Exposure:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/risk/current
```

**Risk History:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/risk/history?days=30"
```

**Portfolio Analysis:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/risk/portfolio
```

### Emergency Controls

**Emergency Stop All Trading:**
```bash
curl -X POST http://localhost:8000/v1/trading/emergency-stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Close All Positions:**
```bash
curl -X POST http://localhost:8000/v1/positions/close-all \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Reduce Exposure:**
```bash
curl -X POST http://localhost:8000/v1/risk/reduce-exposure \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reduction_percentage": 0.5
  }'
```

## Market Analysis

### Smart Money Concepts (SMC)

SMC is based on understanding how institutional traders (smart money) operate in the market:

**Core Concepts:**

**1. Market Structure**
- **Market Structure Shift (CHoCH)**: Change in market trend
- **Break of Structure (BOS)**: Confirmation of trend continuation
- **Order Blocks**: Price levels where institutions placed large orders
- **Fair Value Gaps (FVGs)**: Imbalances between buyers and sellers

**2. Liquidity**
- **Liquidity Sweeps**: Price moves to trigger stop losses
- **Equal Highs/Lows**: Multiple tests of price levels
- **Inducement**: Price setups that encourage retail trading

**3. Smart Entry Points**
- **Mitigation**: Entering at favorable prices within order blocks
- **Premium/Discount**: Trading at extreme price levels
- **Wyckoff Accumulation/Distribution**: Accumulation and distribution phases

### SMC Pattern Recognition

**Order Block Identification:**
```python
# Bullish Order Block Characteristics
- Strong bullish candle followed by reversal
- High volume at order block level
- Price returns to test the level
- Multiple touches without breaking

# Bearish Order Block Characteristics
- Strong bearish candle followed by reversal
- High volume at order block level
- Price returns to test the level
- Multiple touches without breaking
```

**CHoCH/BOS Patterns:**
```python
# CHoCH (Change of Character)
- Break of market structure
- Higher high and higher low (bullish)
- Lower low and lower high (bearish)
- Confirmation with volume

# BOS (Break of Structure)
- Continuation of trend
- Breaks previous highs/lows
- Momentum confirmation
- Follow-through expected
```

**Fair Value Gaps (FVGs):**
```python
# FVG Identification
- Three-candle pattern
- Gap between candle 1 high and candle 3 low (bullish)
- Gap between candle 1 low and candle 3 high (bearish)
- Imbalance indicates likely reversal area
```

### Using the SMC Analysis Tools

**Get Current SMC Analysis:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/analytics/smc/BTCUSDT
```

**Sample Response:**
```json
{
  "symbol": "BTCUSDT",
  "timestamp": "2024-01-01T12:00:00Z",
  "analysis": {
    "trend": "bullish",
    "market_structure": {
      "choch": {
        "detected": true,
        "price_level": 45500.0,
        "confidence": 0.85,
        "direction": "bullish"
      },
      "bos": {
        "detected": true,
        "price_level": 46000.0,
        "confidence": 0.90,
        "direction": "bullish"
      }
    },
    "order_blocks": [
      {
        "price_level": [44000.0, 44200.0],
        "type": "bullish",
        "strength": 0.85,
        "volume_ratio": 1.5,
        "touches": 2,
        "mitigation_distance": 0.002
      }
    ],
    "fvgs": [
      {
        "top": 44800.0,
        "bottom": 44600.0,
        "type": "bullish",
        "filled": false,
        "age_hours": 12
      }
    ],
    "liquidity_levels": [
      {
        "price": 44300.0,
        "type": "swing_low",
        "swept": false,
        "strength": 0.75
      }
    ],
    "entry_signals": [
      {
        "type": "order_block_entry",
        "price": 44050.0,
        "confidence": 0.80,
        "risk_reward": 3.2,
        "reason": "Bullish order block with CHoCH confirmation"
      }
    ]
  }
}
```

### Multi-Timeframe Analysis

**Configure Multi-Timeframe Analysis:**
```yaml
multi_timeframe:
  enabled: true
  symbols: ["BTCUSDT", "ETHUSDT"]
  timeframes: ["M5", "M15", "H1", "H4", "D1"]
  weights:
    M5: 0.1
    M15: 0.2
    H1: 0.3
    H4: 0.25
    D1: 0.15
  confluence_threshold: 0.7
```

**Multi-Timeframe Confluence:**
```python
# Confluence Scoring
def calculate_confluence(mtf_analysis):
    weights = {
        'M5': 0.1, 'M15': 0.2, 'H1': 0.3, 'H4': 0.25, 'D1': 0.15
    }

    total_score = 0
    total_weight = 0

    for timeframe, analysis in mtf_analysis.items():
        if analysis['signal']:
            score = analysis['confidence']
            weight = weights.get(timeframe, 0)
            total_score += score * weight
            total_weight += weight

    return total_score / total_weight if total_weight > 0 else 0
```

### Custom Analysis

**Create Custom Indicators:**
```python
# Custom SMC indicator example
class CustomSMCIndicator:
    def __init__(self, period=20):
        self.period = period

    def detect_order_blocks(self, df):
        order_blocks = []

        for i in range(self.period, len(df)):
            # Check for strong candle followed by reversal
            current_candle = df.iloc[i]
            previous_candles = df.iloc[i-self.period:i]

            # Bullish order block criteria
            if (current_candle['close'] < current_candle['open'] and  # Bearish candle
                previous_candles['close'].max() > current_candle['high']):  # Previous high broken

                order_blocks.append({
                    'price_level': [
                        previous_candles['low'].min(),
                        previous_candles['high'].max()
                    ],
                    'type': 'bearish',
                    'strength': self.calculate_strength(previous_candles)
                })

        return order_blocks

    def calculate_strength(self, candles):
        # Calculate order block strength based on volume and price action
        volume_ratio = candles['volume'].iloc[-1] / candles['volume'].mean()
        price_range = candles['high'].max() - candles['low'].min()

        return min(1.0, volume_ratio * price_range / candles['close'].iloc[0])
```

### Market Scanners

**Configure Market Scanner:**
```yaml
market_scanner:
  enabled: true
  scan_interval: 300  # 5 minutes
  symbols: ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
  filters:
    min_volume: 1000000
    min_price_change: 0.01
    smc_setup_min_confidence: 0.7
  alerts:
    enabled: true
    channels: ["slack", "email"]
```

**Run Market Scanner:**
```bash
curl -X POST http://localhost:8000/v1/scanner/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "timeframes": ["H1", "H4"]
  }'
```

## Performance Monitoring

### Key Performance Metrics

**Trading Metrics:**
- **Total Return**: Overall profit/loss percentage
- **Sharpe Ratio**: Risk-adjusted returns
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Average Trade**: Average profit/loss per trade

**Risk Metrics:**
- **Value at Risk (VaR)**: Potential loss at confidence level
- **Expected Shortfall**: Average loss beyond VaR
- **Beta**: Systematic risk relative to market
- **Alpha**: Excess returns over market
- **Correlation**: Relationship with other positions

**Operational Metrics:**
- **Execution Speed**: Time from signal to execution
- **Slippage**: Difference between expected and actual price
- **Fill Rate**: Percentage of orders successfully filled
- **System Uptime**: Percentage of time system is operational

### Performance Dashboard

**Web Dashboard Features:**
- Real-time P&L tracking
- Trade history visualization
- Risk metric monitoring
- Performance attribution analysis
- Drawdown analysis
- Trade statistics breakdown

**Access Dashboard:**
```
http://localhost:3000
```

### Performance Reports

**Daily Performance Report:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/reports/performance?period=daily"
```

**Weekly Performance Report:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/reports/performance?period=weekly"
```

**Monthly Performance Report:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/reports/performance?period=monthly"
```

**Custom Performance Analysis:**
```python
# Custom performance analysis example
def analyze_performance(trades_df):
    # Calculate basic metrics
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['pnl'] > 0])
    losing_trades = len(trades_df[trades_df['pnl'] < 0])

    win_rate = winning_trades / total_trades * 100
    total_pnl = trades_df['pnl'].sum()
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean()
    avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean()

    # Calculate Sharpe ratio
    daily_returns = trades_df.groupby(trades_df['timestamp'].dt.date)['pnl'].sum()
    sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)

    # Calculate maximum drawdown
    cumulative_pnl = trades_df['pnl'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = (cumulative_pnl - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': abs(avg_win * winning_trades / (avg_loss * losing_trades))
    }
```

### Trade Analysis

**Trade Attribution Analysis:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/analytics/trade-attribution?days=30"
```

**Setup Performance Analysis:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/analytics/setup-performance?days=30"
```

**Risk-Adjusted Performance:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/v1/analytics/risk-adjusted-performance?days=30"
```

### Benchmarking

**Compare with Benchmark:**
```python
# Compare performance with Bitcoin
def compare_with_benchmark(trades_df, btc_data):
    # Calculate portfolio returns
    portfolio_returns = trades_df.groupby(trades_df['timestamp'].dt.date)['pnl'].sum()

    # Calculate Bitcoin returns
    btc_returns = btc_data['close'].pct_change()

    # Calculate correlation
    correlation = portfolio_returns.corr(btc_returns)

    # Calculate beta
    covariance = portfolio_returns.cov(btc_returns)
    btc_variance = btc_returns.var()
    beta = covariance / btc_variance

    # Calculate alpha
    market_return = btc_returns.mean() * 252
    portfolio_return = portfolio_returns.mean() * 252
    alpha = portfolio_return - (0.02 + beta * (market_return - 0.02))

    return {
        'correlation': correlation,
        'beta': beta,
        'alpha': alpha,
        'portfolio_return': portfolio_return,
        'market_return': market_return
    }
```

## Best Practices

### Risk Management Best Practices

**1. Start Small**
- Begin with paper trading
- Use minimum position sizes
- Test strategies thoroughly
- Gradually increase exposure

**2. Set Realistic Expectations**
- Aim for 1-2% monthly returns
- Expect drawdowns of 10-20%
- Focus on consistency over big wins
- Avoid over-leveraging

**3. Diversification**
- Trade multiple uncorrelated assets
- Don't concentrate in one sector
- Use different strategies
- Consider market conditions

**4. Continuous Monitoring**
- Review performance daily
- Monitor risk metrics
- Check system health
- Adjust parameters as needed

### Strategy Development

**1. Backtesting**
```python
# Backtesting best practices
def backtest_strategy(strategy, historical_data, initial_balance=10000):
    results = []
    balance = initial_balance
    position = None

    for data_point in historical_data:
        # Generate signal
        signal = strategy.generate_signal(data_point)

        # Execute trade logic
        if signal == 'buy' and position is None:
            position = execute_buy(balance * 0.02, data_point['price'])
            balance -= position['cost']
        elif signal == 'sell' and position is not None:
            pnl = calculate_pnl(position, data_point['price'])
            balance += position['value'] + pnl
            results.append(pnl)
            position = None

    return results, balance
```

**2. Strategy Validation**
- Use out-of-sample testing
- Validate across different market conditions
- Consider transaction costs and slippage
- Test with realistic position sizing

**3. Strategy Optimization**
- Use walk-forward analysis
- Avoid overfitting
- Keep strategies simple
- Regular performance review

### Operational Best Practices

**1. System Maintenance**
- Regular software updates
- Monitor system resources
- Backup configurations
- Test disaster recovery

**2. Security**
- Use strong API keys
- Enable two-factor authentication
- Monitor for unauthorized access
- Regular security audits

**3. Documentation**
- Document all configuration changes
- Keep trading logs
- Record strategy changes
- Maintain performance records

### Trading Psychology

**1. Emotional Discipline**
- Stick to your trading plan
- Don't chase losses
- Avoid overconfidence after wins
- Take regular breaks

**2. Risk Acceptance**
- Accept that losses are normal
- Focus on long-term performance
- Don't risk more than you can afford
- Maintain proper perspective

**3. Continuous Learning**
- Review all trades (wins and losses)
- Learn from mistakes
- Stay updated on market conditions
- Network with other traders

## Troubleshooting

### Common Issues

**1. Connection Issues**

**Problem**: Cannot connect to exchange APIs
**Solution**:
```bash
# Check API key validity
curl -X POST "https://api.binance.com/api/v3/account" \
  -H "X-MBX-APIKEY: YOUR_API_KEY" \
  -d "timestamp=$(date +%s)000&signature=YOUR_SIGNATURE"

# Check network connectivity
ping api.binance.com

# Check system time
ntpdate -q time.nist.gov
```

**2. Performance Issues**

**Problem**: Slow response times or high latency
**Solution**:
```bash
# Check system resources
top
htop

# Check network latency
ping -c 10 api.binance.com

# Check API rate limits
curl -I https://api.binance.com/api/v3/ticker/price
```

**3. Order Execution Issues**

**Problem**: Orders not executing or failing
**Solution**:
```bash
# Check account balance
curl -H "X-MBX-APIKEY: YOUR_API_KEY" \
  "https://api.binance.com/api/v3/account"

# Check order status
curl -H "X-MBX-APIKEY: YOUR_API_KEY" \
  "https://api.binance.com/api/v3/openOrders"

# Check system logs
tail -f /var/log/smc-agent/trading.log
```

### Debug Mode

**Enable Debug Logging:**
```yaml
app:
  log_level: "DEBUG"
  debug: true

# Or via environment variable
export LOG_LEVEL=DEBUG
```

**Debug Commands:**
```bash
# Check system status
curl http://localhost:8000/v1/health

# View detailed logs
docker logs smc-agent --tail 100

# Test API connectivity
python -c "
import requests
response = requests.get('http://localhost:8000/v1/health')
print(response.json())
"
```

### Performance Issues

**Memory Usage Optimization:**
```bash
# Check memory usage
docker stats smc-agent

# Optimize database queries
EXPLAIN ANALYZE SELECT * FROM trades WHERE symbol = 'BTCUSDT';

# Clean up old data
python -c "
import sqlite3
conn = sqlite3.connect('data/trades.db')
conn.execute('DELETE FROM trades WHERE timestamp < datetime(\"now\", \"-30 days\")')
conn.commit()
"
```

**CPU Usage Optimization:**
```bash
# Profile application performance
python -m cProfile -o profile.stats main.py

# Check running processes
ps aux | grep python

# Optimize configuration
export PYTHONOPTIMIZE=2
export UVLOOP_ENABLED=1
```

### System Recovery

**Emergency Restart:**
```bash
# Stop all services
docker-compose down

# Clear caches
docker system prune -f

# Restart services
docker-compose up -d

# Verify recovery
curl http://localhost:8000/v1/health
```

**Data Recovery:**
```bash
# Restore from backup
python -c "
import sqlite3
conn = sqlite3.connect('data/trades.db')
backup = sqlite3.connect('backup/trades_backup.db')
with backup:
    backup.execute('DROP TABLE IF EXISTS trades')
    backup.execute('CREATE TABLE trades AS SELECT * FROM main.trades')
"
```

## FAQ

### General Questions

**Q: Is the SMC Trading Agent suitable for beginners?**
A: While the system is powerful, it's recommended for users with some trading experience. Beginners should start with paper trading and spend time learning both Smart Money Concepts and proper risk management.

**Q: Can I guarantee profits with this system?**
A: No trading system can guarantee profits. The SMC Trading Agent is designed to improve trading probabilities through systematic analysis and risk management, but losses are still possible.

**Q: How much capital do I need to start?**
A: You can start paper trading with no capital. For live trading, it's recommended to have at least $5,000-$10,000 to allow for proper position sizing and risk management.

### Technical Questions

**Q: Which exchanges are supported?**
A: Currently supported exchanges include:
- Binance (recommended)
- ByBit
- OANDA

**Q: Can I use my own trading strategies?**
A: Yes, the system is extensible and allows for custom strategy development through the API and SDK.

**Q: Is the system open-source?**
A: Yes, the core system is open-source, with additional premium features available.

### Configuration Questions

**Q: How do I switch from paper to live trading?**
A: Change the `app.mode` setting from "paper" to "live" in your configuration file and ensure you have live exchange API keys configured.

**Q: What are the recommended risk settings?**
A: For beginners:
- Risk no more than 1-2% per trade
- Maximum daily loss of 2-3% of account
- Use stop losses on all trades
- Maximum drawdown of 15-20%

**Q: Can I run multiple instances of the system?**
A: Yes, but be careful about correlation and overexposure. Each instance should have its own configuration and API keys.

### Performance Questions

**Q: What kind of returns can I expect?**
A: Realistic expectations are 1-3% monthly returns with proper risk management. Performance varies based on market conditions and strategy effectiveness.

**Q: How often should I review performance?**
A: Daily monitoring is recommended, with weekly and monthly performance reviews for strategic adjustments.

**Q: What happens if the system crashes?**
A: The system includes automatic recovery mechanisms and all open positions have stop-loss protection. Enable notifications for immediate alerts on system issues.

### Support Questions

**Q: Where can I get help?**
A: Support options include:
- Documentation and user guides
- Community forums and Discord
- Email support for premium users
- Professional consulting services

**Q: How often is the system updated?**
A: The system is regularly updated with new features, bug fixes, and performance improvements. Check for updates monthly.

**Q: Can I request new features?**
A: Yes, feature requests can be submitted through GitHub issues or the support portal. Popular requests are prioritized in development.

---

**Disclaimer**: Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. The SMC Trading Agent is a tool to assist in trading decisions, but past performance does not guarantee future results. Always trade with money you can afford to lose and consider seeking professional financial advice.