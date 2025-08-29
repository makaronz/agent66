# SMC Trading Agent API Examples

This document provides comprehensive examples for all API endpoints with request/response samples.

## Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Exchange Integration](#exchange-integration)
4. [Market Data](#market-data)
5. [Trading Operations](#trading-operations)
6. [Risk Management](#risk-management)
7. [Error Handling](#error-handling)

## Authentication

### Register New User

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Trader"
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "trader@example.com",
    "full_name": "John Trader",
    "created_at": "2024-01-15T10:30:00.000Z"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### User Login

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjNlNDU2Ny1lODliLTEyZDMtYTQ1Ni00MjY2MTQxNzQwMDAiLCJlbWFpbCI6InRyYWRlckBleGFtcGxlLmNvbSIsImlhdCI6MTcwNTMxMjIwMCwiZXhwIjoxNzA1MzE1ODAwfQ.example-signature",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "trader@example.com",
    "full_name": "John Trader"
  },
  "expires_in": 3600,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Current User

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "trader@example.com",
  "full_name": "John Trader",
  "avatar_url": "https://example.com/avatar.jpg",
  "created_at": "2024-01-15T10:30:00.000Z",
  "updated_at": "2024-01-15T10:30:00.000Z"
}
```

## User Management

### Update User Profile

**Request:**

```bash
curl -X PUT "https://api.smctradingagent.com/api/v1/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "full_name": "John Smith",
    "avatar_url": "https://example.com/new-avatar.jpg"
  }'
```

**Response (200 OK):**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "trader@example.com",
  "full_name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "updated_at": "2024-01-15T11:00:00.000Z"
}
```

### Store Exchange API Keys

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/users/api-keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "exchange": "binance",
    "apiKey": "your-binance-api-key",
    "secret": "your-binance-secret",
    "isTestnet": true
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "API keys stored successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Stored API Keys

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/users/api-keys?exchange=binance" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "exchange": "binance",
    "is_testnet": true,
    "is_active": true,
    "has_api_key": true,
    "has_secret": true,
    "created_at": "2024-01-15T10:30:00.000Z"
  }
]
```

## Exchange Integration

### Test Binance Connection

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/binance/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "apiKey": "your-binance-testnet-key",
    "secret": "your-binance-testnet-secret",
    "sandbox": true,
    "saveKeys": false
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "Connection successful",
  "data": {
    "exchange": "Binance",
    "status": "ok",
    "updated": "2024-01-15T10:30:00.000Z",
    "sandbox": true
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Error Response (401 Unauthorized):**

```json
{
  "success": false,
  "error": "Invalid API key or secret. Please check your credentials.",
  "details": "Using testnet environment",
  "code": "INVALID_API_KEY",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Account Information

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/binance/account-info" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "apiKey": "your-binance-testnet-key",
    "secret": "your-binance-testnet-secret",
    "sandbox": true
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "balances": {
      "USDT": {
        "total": 1000.5,
        "free": 950.25,
        "used": 50.25
      },
      "BTC": {
        "total": 0.05,
        "free": 0.04,
        "used": 0.01
      }
    },
    "tradingFees": {
      "maker": 0.001,
      "taker": 0.001
    },
    "accountType": "Testnet",
    "timestamp": 1705312200000
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Market Data

### Get Market Data for Symbol

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/binance/market-data/BTC/USDT?sandbox=true"
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "symbol": "BTC/USDT",
    "price": 45000.5,
    "bid": 44999.75,
    "ask": 45001.25,
    "volume": 1234.56,
    "change": 500.25,
    "percentage": 1.12,
    "high": 45500.0,
    "low": 44000.0,
    "recentTrades": [
      {
        "price": 45000.5,
        "amount": 0.1,
        "side": "buy",
        "timestamp": 1705312200000
      },
      {
        "price": 44999.75,
        "amount": 0.05,
        "side": "sell",
        "timestamp": 1705312190000
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Historical Market Data (FastAPI)

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/market-data/BTC/USDT?timeframe=1h&limit=100&exchange=binance" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
[
  {
    "timestamp": "2024-01-15T10:00:00.000Z",
    "open": 44500.0,
    "high": 45000.0,
    "low": 44200.0,
    "close": 44800.0,
    "volume": 1234.56
  },
  {
    "timestamp": "2024-01-15T09:00:00.000Z",
    "open": 44200.0,
    "high": 44600.0,
    "low": 44000.0,
    "close": 44500.0,
    "volume": 987.65
  }
]
```

## Trading Operations

### Place Trading Order

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/binance/place-order" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 44000.00,
    "stopLoss": 43000.00,
    "takeProfit": 46000.00
  }'
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "orderId": "12345678",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 44000.0,
    "fillPrice": 44000.5,
    "status": "filled",
    "timestamp": 1705312200000,
    "stopLossOrderId": "12345679",
    "takeProfitOrderId": "12345680"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Error Response (400 Bad Request):**

```json
{
  "success": false,
  "error": "Insufficient balance to place this order",
  "details": "Available balance: 0.0005 BTC, Required: 0.001 BTC",
  "code": "INSUFFICIENT_BALANCE",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get SMC Trading Signals (FastAPI)

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/signals?symbol=BTC/USDT&min_confidence=0.8&limit=10" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
[
  {
    "id": "sig_123456",
    "symbol": "BTC/USDT",
    "signal_type": "order_block",
    "direction": "bullish",
    "confidence": 0.85,
    "entry_price": 45000.0,
    "stop_loss": 44000.0,
    "take_profit": 46000.0,
    "risk_reward_ratio": 2.5,
    "created_at": "2024-01-15T10:30:00.000Z",
    "expires_at": "2024-01-15T14:30:00.000Z",
    "metadata": {
      "timeframe": "1h",
      "strength": "high",
      "volume_confirmation": true
    }
  }
]
```

### Place Order via FastAPI

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 45000.0,
    "stop_loss": 44000.0,
    "take_profit": 46000.0,
    "exchange": "binance"
  }'
```

**Response (200 OK):**

```json
{
  "id": "ord_123456",
  "symbol": "BTC/USDT",
  "side": "buy",
  "type": "limit",
  "quantity": 0.001,
  "price": 45000.0,
  "filled_quantity": 0.0,
  "status": "pending",
  "exchange": "binance",
  "created_at": "2024-01-15T10:30:00.000Z",
  "updated_at": "2024-01-15T10:30:00.000Z"
}
```

## Risk Management

### Get Risk Metrics (FastAPI)

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/v1/risk-metrics" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**

```json
{
  "portfolio_value": 10000.0,
  "daily_pnl": 150.25,
  "max_drawdown": 2.5,
  "sharpe_ratio": 1.85,
  "win_rate": 65.5,
  "risk_score": 25.0,
  "open_positions": 3,
  "leverage_ratio": 2.0
}
```

### Run Strategy Backtest (FastAPI)

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/backtest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "strategy_name": "SMC_Scalping_v1",
    "symbol": "BTC/USDT",
    "start_date": "2024-01-01T00:00:00.000Z",
    "end_date": "2024-01-15T00:00:00.000Z",
    "initial_capital": 10000.0,
    "risk_per_trade": 0.02,
    "parameters": {
      "timeframe": "1h",
      "min_confidence": 0.8,
      "max_positions": 3
    }
  }'
```

**Response (200 OK):**

```json
{
  "strategy_name": "SMC_Scalping_v1",
  "symbol": "BTC/USDT",
  "start_date": "2024-01-01T00:00:00.000Z",
  "end_date": "2024-01-15T00:00:00.000Z",
  "initial_capital": 10000.0,
  "final_capital": 12500.0,
  "total_return": 25.0,
  "sharpe_ratio": 1.85,
  "max_drawdown": 5.2,
  "win_rate": 68.5,
  "total_trades": 150,
  "profitable_trades": 103,
  "avg_trade_duration": 4.5,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

## Error Handling

### Validation Error Example

**Request:**

```bash
curl -X POST "https://api.smctradingagent.com/api/v1/binance/place-order" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "symbol": "INVALID_SYMBOL",
    "side": "invalid_side",
    "type": "limit",
    "quantity": -1
  }'
```

**Response (400 Bad Request):**

```json
{
  "success": false,
  "error": "Validation failed",
  "details": [
    {
      "field": "symbol",
      "message": "Invalid trading symbol format",
      "code": "invalid_format"
    },
    {
      "field": "side",
      "message": "Side must be either 'buy' or 'sell'",
      "code": "invalid_enum"
    },
    {
      "field": "quantity",
      "message": "Quantity must be greater than 0",
      "code": "invalid_range"
    }
  ],
  "code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Rate Limit Error Example

**Response (429 Too Many Requests):**

```json
{
  "success": false,
  "error": "Too many trading requests",
  "details": "Please slow down your trading operations",
  "code": "TRADING_RATE_LIMIT_EXCEEDED",
  "retryAfter": 60,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Headers:**

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705312800
Retry-After: 60
```

### Authentication Error Example

**Response (401 Unauthorized):**

```json
{
  "success": false,
  "error": "Authentication required",
  "details": "Authorization header with Bearer token is required",
  "code": "UNAUTHORIZED",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Server Error Example

**Response (500 Internal Server Error):**

```json
{
  "success": false,
  "error": "Internal server error",
  "details": "An unexpected error occurred",
  "code": "INTERNAL_ERROR",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## API Versioning Examples

### Version in URL Path (Recommended)

```bash
# Current version (v1)
curl -X GET "https://api.smctradingagent.com/api/v1/auth/me"

# Future version (v2)
curl -X GET "https://api.smctradingagent.com/api/v2/auth/me"
```

### Version in Header

```bash
curl -X GET "https://api.smctradingagent.com/api/auth/me" \
  -H "X-API-Version: v1"
```

### Legacy Endpoint (Deprecated)

**Request:**

```bash
curl -X GET "https://api.smctradingagent.com/api/auth/me"
```

**Response Headers:**

```
Warning: 299 - "Unversioned API access is deprecated. Please specify version in URL path."
X-API-Version: v1
X-Deprecated-Endpoint: /api/auth/me
X-Recommended-Endpoint: /api/v1/auth/me
```

## SDK Examples

### JavaScript/TypeScript

```typescript
import { SMCTradingClient } from "@smc-trading-agent/sdk";

const client = new SMCTradingClient({
  baseURL: "https://api.smctradingagent.com",
  apiVersion: "v1",
  token: "your-jwt-token",
});

// Get market data
const marketData = await client.marketData.get("BTC/USDT", {
  timeframe: "1h",
  limit: 100,
});

// Place order
const order = await client.orders.create({
  symbol: "BTC/USDT",
  side: "buy",
  type: "limit",
  quantity: 0.001,
  price: 45000.0,
});
```

### Python

```python
from smc_trading_agent import SMCTradingClient

client = SMCTradingClient(
    base_url='https://api.smctradingagent.com',
    api_version='v1',
    token='your-jwt-token'
)

# Get market data
market_data = client.market_data.get('BTC/USDT', timeframe='1h', limit=100)

# Place order
order = client.orders.create(
    symbol='BTC/USDT',
    side='buy',
    type='limit',
    quantity=0.001,
    price=45000.0
)
```

## Webhook Examples

### Trade Execution Webhook

**Webhook URL:** `https://your-app.com/webhooks/smc-trading`

**Request:**

```json
{
  "event": "trade.executed",
  "data": {
    "id": "ord_123456",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 45000.0,
    "filled_quantity": 0.001,
    "status": "filled",
    "exchange": "binance",
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:15.000Z"
  },
  "timestamp": "2024-01-15T10:30:15.000Z"
}
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Webhook received successfully"
}
```

---

## Support and Resources

- **GitHub Repository:** https://github.com/smc-trading-agent
- **Documentation:** https://docs.smctradingagent.com
- **Support Email:** support@smctradingagent.com
- **Discord Community:** https://discord.gg/smc-trading-agent

For more examples and detailed documentation, visit our [interactive API documentation](https://api.smctradingagent.com/api/docs).
