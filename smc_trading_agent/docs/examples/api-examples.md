# SMC Trading Agent API Examples

This document provides comprehensive examples for all API endpoints with sample requests and responses.

## Table of Contents

- [Authentication](#authentication)
- [User Management](#user-management)
- [Trading Operations](#trading-operations)
- [Market Data](#market-data)
- [Risk Management](#risk-management)
- [Error Handling](#error-handling)

## Authentication

### Register User

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Trader"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": 2,
    "email": "trader@example.com",
    "full_name": "John Trader"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Login User

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "user": {
    "id": 1,
    "email": "trader@example.com",
    "name": "John Trader"
  },
  "expires_in": 3600,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Current User

**Request:**
```bash
curl -X GET "http://localhost:3000/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "id": 1,
  "email": "trader@example.com",
  "name": "John Trader",
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

## User Management

### Get User Profile

**Request:**
```bash
curl -X GET "http://localhost:3000/api/v1/users/profile" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
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

### Update User Profile

**Request:**
```bash
curl -X PUT "http://localhost:3000/api/v1/users/profile" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Smith",
    "avatar_url": "https://example.com/new-avatar.jpg"
  }'
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "trader@example.com",
  "full_name": "John Smith",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "updated_at": "2024-01-15T11:00:00.000Z"
}
```

### Store API Keys

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/users/api-keys" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "apiKey": "your-binance-api-key",
    "secret": "your-binance-secret",
    "isTestnet": true
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "API keys stored successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get API Keys

**Request:**
```bash
curl -X GET "http://localhost:3000/api/v1/users/api-keys?exchange=binance" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "exchange": "binance",
    "is_testnet": true,
    "is_active": true,
    "has_api_key": true,
    "has_secret": true,
    "created_at": "2024-01-15T10:30:00.000Z"
  }
]
```

## Trading Operations

### Test Exchange Connection

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/binance/test-connection" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "your-testnet-api-key",
    "secret": "your-testnet-secret",
    "sandbox": true,
    "saveKeys": false
  }'
```

**Response:**
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

### Get Account Information

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/binance/account-info" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "your-testnet-api-key",
    "secret": "your-testnet-secret",
    "sandbox": true
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "balances": {
      "USDT": {
        "total": 1000.50,
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
  }
}
```

### Place Trading Order

**Request (Market Order):**
```bash
curl -X POST "http://localhost:3000/api/v1/binance/place-order" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "market",
    "quantity": 0.001
  }'
```

**Request (Limit Order with Stop Loss):**
```bash
curl -X POST "http://localhost:3000/api/v1/binance/place-order" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "side": "sell",
    "type": "limit",
    "quantity": 0.001,
    "price": 50000.00,
    "stopLoss": 48000.00,
    "takeProfit": 52000.00
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "orderId": "12345678",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "market",
    "quantity": 0.001,
    "price": null,
    "fillPrice": 45000.50,
    "status": "filled",
    "timestamp": 1705312200000,
    "stopLossOrderId": null,
    "takeProfitOrderId": null
  }
}
```

## Market Data

### Get Market Data

**Request:**
```bash
curl -X GET "http://localhost:3000/api/v1/binance/market-data/BTC%2FUSDT?sandbox=true"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTC/USDT",
    "price": 45000.50,
    "bid": 44999.75,
    "ask": 45001.25,
    "volume": 1234.56,
    "change": 500.25,
    "percentage": 1.12,
    "high": 45500.00,
    "low": 44000.00,
    "recentTrades": [
      {
        "price": 45000.50,
        "amount": 0.1,
        "side": "buy",
        "timestamp": 1705312200000
      },
      {
        "price": 45000.25,
        "amount": 0.05,
        "side": "sell",
        "timestamp": 1705312190000
      }
    ]
  }
}
```

### Get Historical Market Data (FastAPI)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/market-data/BTC%2FUSDT?timeframe=1h&limit=100&exchange=binance"
```

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T10:00:00.000Z",
    "open": 45000.0,
    "high": 45500.0,
    "low": 44500.0,
    "close": 45250.0,
    "volume": 1234.56
  },
  {
    "timestamp": "2024-01-15T09:00:00.000Z",
    "open": 44800.0,
    "high": 45200.0,
    "low": 44600.0,
    "close": 45000.0,
    "volume": 1156.78
  }
]
```

## Risk Management

### Get SMC Signals (FastAPI)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/signals?symbol=BTC%2FUSDT&min_confidence=0.8&limit=10" \
  -H "Authorization: Bearer valid-token"
```

**Response:**
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
      "confluence": ["support_level", "fibonacci_618"]
    }
  }
]
```

### Get Risk Metrics (FastAPI)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/risk-metrics" \
  -H "Authorization: Bearer valid-token"
```

**Response:**
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

### Run Backtest (FastAPI)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Authorization: Bearer valid-token" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "SMC_Scalping_v1",
    "symbol": "BTC/USDT",
    "start_date": "2024-01-01T00:00:00.000Z",
    "end_date": "2024-01-15T00:00:00.000Z",
    "initial_capital": 10000.0,
    "risk_per_trade": 0.02,
    "parameters": {
      "timeframe": "1h",
      "min_confidence": 0.75,
      "max_positions": 3
    }
  }'
```

**Response:**
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

## System Endpoints

### Health Check

**Request:**
```bash
curl -X GET "http://localhost:3000/api/health"
```

**Response:**
```json
{
  "success": true,
  "message": "SMC Trading Agent API is running",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### API Version Information

**Request:**
```bash
curl -X GET "http://localhost:3000/api/version"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "current_version": "v1",
    "supported_versions": [
      {
        "version": "v1",
        "deprecated": false,
        "sunset_date": null,
        "migration_guide": null
      }
    ],
    "versioning_strategy": "url_path",
    "documentation": {
      "openapi_spec": "/api/v1/openapi.json",
      "swagger_ui": "/api/v1/docs",
      "redoc": "/api/v1/redoc"
    }
  }
}
```

## Error Handling

### Validation Error

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invalid-email",
    "password": ""
  }'
```

**Response:**
```json
{
  "success": false,
  "error": "Validation failed",
  "details": "Invalid email format and password is required",
  "code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Authentication Error

**Request:**
```bash
curl -X GET "http://localhost:3000/api/v1/users/profile" \
  -H "Authorization: Bearer invalid-token"
```

**Response:**
```json
{
  "success": false,
  "error": "Authentication required",
  "details": "Invalid or expired token",
  "code": "UNAUTHORIZED",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Rate Limit Error

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "details": "Too many requests, please try again later",
  "code": "RATE_LIMIT_EXCEEDED",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705312800
```

### Exchange API Error

**Request:**
```bash
curl -X POST "http://localhost:3000/api/v1/binance/place-order" \
  -H "Authorization: Bearer valid-token" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 1000000.00
  }'
```

**Response:**
```json
{
  "success": false,
  "error": "Invalid price - check symbol price filter requirements",
  "details": "Using testnet environment",
  "code": "PRICE_FILTER_ERROR",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## SDK Examples

### TypeScript SDK

```typescript
import { SMCTradingAgentAPI } from 'smc-trading-agent-sdk';

const api = new SMCTradingAgentAPI({
  baseURL: 'http://localhost:3000/api/v1',
  apiKey: 'your-jwt-token'
});

// Get market data
const marketData = await api.getMarketData('BTC/USDT');
console.log(marketData.data);

// Place order
const order = await api.placeOrder({
  symbol: 'BTC/USDT',
  side: 'buy',
  type: 'market',
  quantity: 0.001
});
console.log(order.data);
```

### Python SDK

```python
from smc_trading_agent_sdk import SMCTradingAgentAPI

api = SMCTradingAgentAPI(
    base_url='http://localhost:8000/api/v1',
    api_key='your-jwt-token'
)

# Get SMC signals
signals = api.get_smc_signals(symbol='BTC/USDT', min_confidence=0.8)
print(signals)

# Run backtest
backtest_result = api.run_backtest({
    'strategy_name': 'SMC_Scalping_v1',
    'symbol': 'BTC/USDT',
    'start_date': '2024-01-01T00:00:00.000Z',
    'end_date': '2024-01-15T00:00:00.000Z',
    'initial_capital': 10000.0,
    'risk_per_trade': 0.02
})
print(backtest_result)
```

## Postman Collection

Import the generated Postman collection from `/docs/postman/express-api-collection.json` or `/docs/postman/fastapi-collection.json` to test all endpoints interactively.

### Environment Variables

Set up the following environment variables in Postman:

- `baseUrl`: `http://localhost:3000/api/v1` (Express.js) or `http://localhost:8000/api/v1` (FastAPI)
- `authToken`: Your JWT token from login response
- `apiKey`: Your exchange API key (for testing)
- `apiSecret`: Your exchange API secret (for testing)

This completes the comprehensive API examples documentation with real request/response examples for all endpoints.