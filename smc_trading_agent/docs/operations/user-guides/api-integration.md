# API Integration Guide

## Overview

The SMC Trading Agent provides a comprehensive REST API for programmatic access to trading functionality, market data, and account management. This guide covers authentication, endpoints, examples, and best practices for integrating with our API.

## 🔐 Authentication

### API Key Management

1. **Generate API Keys**:

   - Navigate to **Settings > API Access** in the web interface
   - Click **Generate New API Key**
   - Set permissions and IP restrictions
   - Save your API key and secret securely

2. **API Key Permissions**:
   ```json
   {
     "permissions": {
       "read_account": true,
       "read_positions": true,
       "read_orders": true,
       "place_orders": false,
       "cancel_orders": false,
       "modify_orders": false,
       "read_market_data": true,
       "read_signals": true
     }
   }
   ```

### Authentication Methods

#### 1. API Key Authentication

```bash
# Include API key in headers
curl -H "X-API-Key: your_api_key_here" \
     -H "X-API-Secret: your_api_secret_here" \
     https://api.smc-trading.com/v1/account/balance
```

#### 2. JWT Token Authentication

```bash
# First, get a JWT token
curl -X POST https://api.smc-trading.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your.email@domain.com",
    "password": "your_password",
    "totp_code": "123456"
  }'

# Use the token in subsequent requests
curl -H "Authorization: Bearer your_jwt_token_here" \
     https://api.smc-trading.com/v1/account/balance
```

#### 3. Signature-Based Authentication (Recommended for Trading)

```python
import hmac
import hashlib
import time
import requests

def create_signature(secret, method, path, body=""):
    timestamp = str(int(time.time() * 1000))
    message = timestamp + method + path + body
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return timestamp, signature

# Example usage
api_key = "your_api_key"
api_secret = "your_api_secret"
method = "GET"
path = "/v1/account/balance"

timestamp, signature = create_signature(api_secret, method, path)

headers = {
    "X-API-Key": api_key,
    "X-Timestamp": timestamp,
    "X-Signature": signature,
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.smc-trading.com" + path,
    headers=headers
)
```

## 📊 Core API Endpoints

### Account Management

#### Get Account Balance

```http
GET /v1/account/balance
```

**Response:**

```json
{
  "success": true,
  "data": {
    "total_balance": 10000.0,
    "available_balance": 8500.0,
    "margin_used": 1500.0,
    "unrealized_pnl": 250.0,
    "balances": [
      {
        "exchange": "binance",
        "currency": "USDT",
        "balance": 5000.0,
        "available": 4250.0
      },
      {
        "exchange": "bybit",
        "currency": "USDT",
        "balance": 5000.0,
        "available": 4250.0
      }
    ]
  }
}
```

#### Get Account Information

```http
GET /v1/account/info
```

**Response:**

```json
{
  "success": true,
  "data": {
    "user_id": "user_123456",
    "email": "trader@example.com",
    "account_type": "premium",
    "created_at": "2024-01-15T10:30:00Z",
    "last_login": "2024-01-20T14:22:00Z",
    "trading_enabled": true,
    "risk_level": "moderate",
    "connected_exchanges": ["binance", "bybit"],
    "subscription": {
      "plan": "professional",
      "expires_at": "2024-12-31T23:59:59Z"
    }
  }
}
```

### Position Management

#### Get Open Positions

```http
GET /v1/positions
```

**Query Parameters:**

- `exchange` (optional): Filter by exchange
- `symbol` (optional): Filter by trading pair
- `status` (optional): open, closed, pending

**Response:**

```json
{
  "success": true,
  "data": {
    "positions": [
      {
        "position_id": "pos_789012",
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "side": "long",
        "size": 0.1,
        "entry_price": 45000.0,
        "current_price": 46500.0,
        "unrealized_pnl": 150.0,
        "unrealized_pnl_percent": 3.33,
        "margin_used": 1500.0,
        "stop_loss": 43500.0,
        "take_profit": 48000.0,
        "opened_at": "2024-01-20T10:15:00Z",
        "strategy": "smc_order_block"
      }
    ],
    "total_positions": 1,
    "total_unrealized_pnl": 150.0
  }
}
```

#### Close Position

```http
POST /v1/positions/{position_id}/close
```

**Request Body:**

```json
{
  "close_type": "market",
  "quantity": 0.05,
  "reason": "manual_close"
}
```

### Order Management

#### Place Order

```http
POST /v1/orders
```

**Request Body:**

```json
{
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "side": "buy",
  "type": "limit",
  "quantity": 0.001,
  "price": 45000.0,
  "stop_loss": 43500.0,
  "take_profit": 48000.0,
  "strategy": "smc_liquidity_zone",
  "time_in_force": "GTC"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "order_id": "ord_345678",
    "exchange_order_id": "binance_987654321",
    "status": "pending",
    "created_at": "2024-01-20T15:30:00Z"
  }
}
```

#### Get Order Status

```http
GET /v1/orders/{order_id}
```

#### Cancel Order

```http
DELETE /v1/orders/{order_id}
```

### Market Data

#### Get Market Data

```http
GET /v1/market/ticker/{symbol}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "price": 46500.0,
    "change_24h": 1250.0,
    "change_24h_percent": 2.76,
    "volume_24h": 125000.5,
    "high_24h": 47200.0,
    "low_24h": 44800.0,
    "timestamp": "2024-01-20T16:00:00Z"
  }
}
```

#### Get OHLCV Data

```http
GET /v1/market/ohlcv/{symbol}
```

**Query Parameters:**

- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d
- `limit`: Number of candles (max 1000)
- `since`: Start timestamp

**Response:**

```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "candles": [
      {
        "timestamp": "2024-01-20T15:00:00Z",
        "open": 45800.0,
        "high": 46200.0,
        "low": 45600.0,
        "close": 46000.0,
        "volume": 1250.75
      }
    ]
  }
}
```

### SMC Signals

#### Get SMC Signals

```http
GET /v1/signals
```

**Query Parameters:**

- `symbol` (optional): Filter by trading pair
- `signal_type` (optional): order_block, liquidity_zone, fair_value_gap
- `status` (optional): active, triggered, expired
- `limit`: Number of signals (default 50, max 200)

**Response:**

```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "signal_id": "sig_123456",
        "symbol": "BTCUSDT",
        "signal_type": "order_block",
        "direction": "bullish",
        "confidence": 0.85,
        "price_level": 45500.0,
        "stop_loss": 44000.0,
        "take_profit": 48000.0,
        "status": "active",
        "created_at": "2024-01-20T14:30:00Z",
        "expires_at": "2024-01-21T14:30:00Z",
        "metadata": {
          "timeframe": "4h",
          "block_size": 150,
          "validation_touches": 3
        }
      }
    ],
    "total_signals": 1
  }
}
```

#### Subscribe to Signal Webhook

```http
POST /v1/signals/webhook
```

**Request Body:**

```json
{
  "url": "https://your-server.com/webhook/smc-signals",
  "events": ["signal_created", "signal_triggered", "signal_expired"],
  "filters": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "signal_types": ["order_block", "liquidity_zone"],
    "min_confidence": 0.7
  }
}
```

## 🔄 WebSocket API

### Connection

```javascript
const ws = new WebSocket("wss://api.smc-trading.com/ws");

ws.onopen = function () {
  // Authenticate
  ws.send(
    JSON.stringify({
      type: "auth",
      api_key: "your_api_key",
      signature: "calculated_signature",
      timestamp: Date.now(),
    })
  );
};

ws.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
};
```

### Subscriptions

#### Subscribe to Price Updates

```json
{
  "type": "subscribe",
  "channel": "ticker",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

#### Subscribe to SMC Signals

```json
{
  "type": "subscribe",
  "channel": "signals",
  "filters": {
    "signal_types": ["order_block"],
    "min_confidence": 0.8
  }
}
```

#### Subscribe to Position Updates

```json
{
  "type": "subscribe",
  "channel": "positions"
}
```

### WebSocket Message Format

**Price Update:**

```json
{
  "type": "ticker",
  "symbol": "BTCUSDT",
  "price": 46500.0,
  "timestamp": "2024-01-20T16:00:00Z"
}
```

**Signal Update:**

```json
{
  "type": "signal",
  "event": "created",
  "signal": {
    "signal_id": "sig_789012",
    "symbol": "BTCUSDT",
    "signal_type": "order_block",
    "direction": "bullish",
    "confidence": 0.87,
    "price_level": 45500.0
  }
}
```

## 💻 Code Examples

### Python SDK

#### Installation

```bash
pip install smc-trading-sdk
```

#### Basic Usage

```python
from smc_trading import SMCTradingClient

# Initialize client
client = SMCTradingClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    environment="production"  # or "sandbox"
)

# Get account balance
balance = client.get_balance()
print(f"Total Balance: ${balance['total_balance']}")

# Get open positions
positions = client.get_positions()
for position in positions:
    print(f"{position['symbol']}: {position['unrealized_pnl']}")

# Place a market order
order = client.place_order(
    exchange="binance",
    symbol="BTCUSDT",
    side="buy",
    type="market",
    quantity=0.001
)
print(f"Order placed: {order['order_id']}")

# Get SMC signals
signals = client.get_signals(
    signal_type="order_block",
    min_confidence=0.8
)
for signal in signals:
    print(f"Signal: {signal['symbol']} - {signal['direction']}")
```

#### Advanced Trading Bot

```python
import asyncio
from smc_trading import SMCTradingClient, WebSocketClient

class SMCTradingBot:
    def __init__(self, api_key, api_secret):
        self.client = SMCTradingClient(api_key, api_secret)
        self.ws_client = WebSocketClient(api_key, api_secret)

    async def start(self):
        # Subscribe to signals
        await self.ws_client.subscribe('signals', self.on_signal)

        # Subscribe to position updates
        await self.ws_client.subscribe('positions', self.on_position_update)

        # Start WebSocket connection
        await self.ws_client.connect()

    async def on_signal(self, signal):
        """Handle new SMC signals"""
        if signal['confidence'] >= 0.85:
            # Calculate position size based on risk management
            position_size = self.calculate_position_size(
                signal['price_level'],
                signal['stop_loss']
            )

            # Place order
            order = await self.client.place_order(
                exchange="binance",
                symbol=signal['symbol'],
                side="buy" if signal['direction'] == "bullish" else "sell",
                type="limit",
                quantity=position_size,
                price=signal['price_level'],
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit']
            )

            print(f"Order placed for signal {signal['signal_id']}: {order['order_id']}")

    async def on_position_update(self, position):
        """Handle position updates"""
        if position['unrealized_pnl_percent'] <= -2.0:
            # Emergency stop loss
            await self.client.close_position(position['position_id'])
            print(f"Emergency close for position {position['position_id']}")

    def calculate_position_size(self, entry_price, stop_loss):
        """Calculate position size based on risk management"""
        account_balance = self.client.get_balance()['available_balance']
        risk_amount = account_balance * 0.01  # 1% risk
        price_diff = abs(entry_price - stop_loss)
        return risk_amount / price_diff

# Usage
bot = SMCTradingBot("your_api_key", "your_api_secret")
asyncio.run(bot.start())
```

### JavaScript/Node.js

#### Installation

```bash
npm install smc-trading-js
```

#### Basic Usage

```javascript
const { SMCTradingClient } = require("smc-trading-js");

const client = new SMCTradingClient({
  apiKey: "your_api_key",
  apiSecret: "your_api_secret",
  environment: "production",
});

// Get account balance
client
  .getBalance()
  .then((balance) => {
    console.log(`Total Balance: $${balance.total_balance}`);
  })
  .catch((error) => {
    console.error("Error:", error);
  });

// Subscribe to signals via WebSocket
const ws = client.createWebSocket();

ws.on("connect", () => {
  ws.subscribe("signals", {
    signal_types: ["order_block", "liquidity_zone"],
    min_confidence: 0.8,
  });
});

ws.on("signal", (signal) => {
  console.log("New signal:", signal);

  if (signal.confidence >= 0.85) {
    // Place order based on signal
    client
      .placeOrder({
        exchange: "binance",
        symbol: signal.symbol,
        side: signal.direction === "bullish" ? "buy" : "sell",
        type: "limit",
        quantity: 0.001,
        price: signal.price_level,
        stopLoss: signal.stop_loss,
        takeProfit: signal.take_profit,
      })
      .then((order) => {
        console.log("Order placed:", order.order_id);
      });
  }
});

ws.connect();
```

### cURL Examples

#### Get Account Balance

```bash
curl -X GET "https://api.smc-trading.com/v1/account/balance" \
  -H "X-API-Key: your_api_key" \
  -H "X-API-Secret: your_api_secret"
```

#### Place Market Order

```bash
curl -X POST "https://api.smc-trading.com/v1/orders" \
  -H "X-API-Key: your_api_key" \
  -H "X-API-Secret: your_api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "market",
    "quantity": 0.001
  }'
```

#### Get SMC Signals

```bash
curl -X GET "https://api.smc-trading.com/v1/signals?signal_type=order_block&min_confidence=0.8" \
  -H "X-API-Key: your_api_key" \
  -H "X-API-Secret: your_api_secret"
```

## 🔧 Best Practices

### Rate Limiting

The API implements rate limiting to ensure fair usage:

```
General Endpoints: 100 requests per minute
Trading Endpoints: 50 requests per minute
Market Data: 200 requests per minute
WebSocket: 10 connections per API key
```

#### Handle Rate Limits

```python
import time
from smc_trading.exceptions import RateLimitError

def make_request_with_retry(client, method, *args, **kwargs):
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            return getattr(client, method)(*args, **kwargs)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
            raise e
```

### Error Handling

#### Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Insufficient balance for this order",
    "details": {
      "required": 1000.0,
      "available": 750.0
    }
  }
}
```

#### Common Error Codes

- `INVALID_API_KEY`: API key is invalid or expired
- `INSUFFICIENT_BALANCE`: Not enough balance for the operation
- `INVALID_SYMBOL`: Trading pair not supported
- `ORDER_NOT_FOUND`: Order ID does not exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `EXCHANGE_ERROR`: Error from exchange API
- `INVALID_PARAMETERS`: Request parameters are invalid

#### Error Handling Example

```python
from smc_trading.exceptions import (
    InsufficientBalanceError,
    InvalidSymbolError,
    RateLimitError
)

try:
    order = client.place_order(
        exchange="binance",
        symbol="BTCUSDT",
        side="buy",
        type="market",
        quantity=1.0
    )
except InsufficientBalanceError as e:
    print(f"Not enough balance: {e.details}")
except InvalidSymbolError as e:
    print(f"Invalid symbol: {e.message}")
except RateLimitError as e:
    print(f"Rate limit exceeded, retry after: {e.retry_after}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Security Best Practices

#### API Key Security

```python
import os
from cryptography.fernet import Fernet

# Store API keys encrypted
def encrypt_api_key(api_key, password):
    key = Fernet.generate_key()
    f = Fernet(key)
    encrypted_key = f.encrypt(api_key.encode())
    return encrypted_key, key

def decrypt_api_key(encrypted_key, key):
    f = Fernet(key)
    return f.decrypt(encrypted_key).decode()

# Use environment variables
api_key = os.getenv('SMC_API_KEY')
api_secret = os.getenv('SMC_API_SECRET')
```

#### IP Whitelisting

```bash
# Configure IP restrictions in API settings
# Only allow requests from specific IPs
curl -X POST "https://api.smc-trading.com/v1/settings/api-keys/{key_id}/ip-whitelist" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
    "ips": ["192.168.1.100", "203.0.113.0/24"]
  }'
```

### Performance Optimization

#### Batch Requests

```python
# Instead of multiple individual requests
orders = []
for signal in signals:
    order = client.place_order(...)  # Multiple API calls
    orders.append(order)

# Use batch operations
batch_orders = client.place_orders_batch([
    {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.001,
        "price": 45000
    },
    # ... more orders
])
```

#### WebSocket for Real-time Data

```python
# Instead of polling
while True:
    positions = client.get_positions()  # Polling every second
    time.sleep(1)

# Use WebSocket subscriptions
ws.subscribe('positions', callback=handle_position_update)
```

## 📚 API Reference

### Base URLs

- **Production**: `https://api.smc-trading.com`
- **Sandbox**: `https://sandbox-api.smc-trading.com`

### Response Format

All API responses follow this format:

```json
{
  "success": boolean,
  "data": object | array,
  "error": {
    "code": "string",
    "message": "string",
    "details": object
  },
  "timestamp": "ISO 8601 timestamp",
  "request_id": "unique_request_identifier"
}
```

### Pagination

For endpoints that return lists:

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total_pages": 10,
      "total_items": 500,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### Timestamps

All timestamps are in ISO 8601 format with UTC timezone:

```
2024-01-20T16:00:00Z
```

## 🧪 Testing

### Sandbox Environment

Use the sandbox environment for testing:

```python
client = SMCTradingClient(
    api_key="sandbox_api_key",
    api_secret="sandbox_api_secret",
    environment="sandbox"
)
```

### Test Data

The sandbox provides:

- Simulated market data
- Virtual balance of $100,000
- All API endpoints available
- No real money involved

### Integration Testing

```python
import unittest
from smc_trading import SMCTradingClient

class TestSMCAPI(unittest.TestCase):
    def setUp(self):
        self.client = SMCTradingClient(
            api_key="test_key",
            api_secret="test_secret",
            environment="sandbox"
        )

    def test_get_balance(self):
        balance = self.client.get_balance()
        self.assertIsInstance(balance['total_balance'], float)
        self.assertGreater(balance['total_balance'], 0)

    def test_place_order(self):
        order = self.client.place_order(
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            type="market",
            quantity=0.001
        )
        self.assertIn('order_id', order)
        self.assertEqual(order['status'], 'pending')

if __name__ == '__main__':
    unittest.main()
```

## 📞 Support

### API Support

- **Documentation**: [https://docs.smc-trading.com/api](https://docs.smc-trading.com/api)
- **Support Email**: api-support@smc-trading.com
- **Developer Forum**: [https://developers.smc-trading.com](https://developers.smc-trading.com)

### Rate Limit Increases

Contact support for higher rate limits:

- Include use case description
- Expected request volume
- Business justification

### Custom Integrations

For enterprise customers:

- Dedicated API endpoints
- Custom rate limits
- Priority support
- SLA guarantees

---

**Last Updated**: $(date)  
**API Version**: v1.0.0  
**SDK Versions**: Python 1.2.0, JavaScript 1.1.0  
**Next Review Date**: $(date -d "+1 month")
