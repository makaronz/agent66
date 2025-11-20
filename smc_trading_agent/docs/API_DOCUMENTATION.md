# SMC Trading Agent API Documentation

This comprehensive API documentation covers all REST endpoints, WebSocket connections, and integration examples for the SMC Trading Agent.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [REST API Endpoints](#rest-api-endpoints)
4. [WebSocket API](#websocket-api)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Integration Examples](#integration-examples)
8. [SDKs and Libraries](#sdks-and-libraries)
9. [API Versioning](#api-versioning)
10. [Testing and Debugging](#testing-and-debugging)

## API Overview

### Base URL

**Production:**
```
https://api.smc-trading.com/v1
```

**Development:**
```
http://localhost:8000/v1
```

### Supported Protocols

- **REST API**: HTTP/HTTPS with JSON payloads
- **WebSocket**: Real-time data streaming
- **GraphQL**: Advanced query capabilities (coming soon)

### API Gateway Architecture

```
Client → Load Balancer → API Gateway → Microservices
                            ↓
                        Authentication
                            ↓
                        Rate Limiting
                            ↓
                        Request Routing
```

## Authentication

### API Key Authentication

All API requests must include authentication credentials:

```http
Authorization: Bearer YOUR_API_TOKEN
```

### Obtaining API Tokens

**1. Generate API Key:**
```bash
curl -X POST http://localhost:8000/api/auth/generate-token \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "permissions": ["read_trades", "write_trades"],
    "expires_in": 3600
  }'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-01-01T12:00:00Z",
  "permissions": ["read_trades", "write_trades"]
}
```

**2. Refresh Token:**
```bash
curl -X POST http://localhost:8000/api/auth/refresh-token \
  -H "Authorization: Bearer YOUR_REFRESH_TOKEN"
```

### Token Scopes

Available permission scopes:

- `read_trades`: Read trade history and positions
- `write_trades`: Execute trades and manage positions
- `read_market_data`: Access market data and analytics
- `read_risk_metrics`: Access risk management data
- `admin_full`: Full administrative access (internal use only)

### Authentication Examples

**Python:**
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_API_TOKEN',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:8000/v1/trades',
    headers=headers
)
```

**JavaScript:**
```javascript
const headers = {
  'Authorization': 'Bearer YOUR_API_TOKEN',
  'Content-Type': 'application/json'
};

fetch('http://localhost:8000/v1/trades', { headers })
  .then(response => response.json())
  .then(data => console.log(data));
```

**cURL:**
```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/v1/trades
```

## REST API Endpoints

### Trading Endpoints

#### Get Current Positions

```http
GET /v1/positions
```

**Response:**
```json
{
  "positions": [
    {
      "id": "pos_123",
      "symbol": "BTCUSDT",
      "side": "long",
      "quantity": 0.1,
      "entry_price": 45000.0,
      "current_price": 45100.0,
      "unrealized_pnl": 10.0,
      "percentage_pnl": 0.22,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z"
    }
  ],
  "total_exposure": 4500.0,
  "total_pnl": 10.0
}
```

**Query Parameters:**
- `symbol` (optional): Filter by trading symbol
- `status` (optional): Filter by status (open, closed)
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

#### Execute Trade

```http
POST /v1/trades
```

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "side": "buy",
  "type": "market",
  "quantity": 0.1,
  "price": null,
  "time_in_force": "GTC",
  "stop_loss": 44000.0,
  "take_profit": 46000.0,
  "client_order_id": "order_123"
}
```

**Response:**
```json
{
  "order_id": "order_456",
  "client_order_id": "order_123",
  "symbol": "BTCUSDT",
  "side": "buy",
  "type": "market",
  "quantity": 0.1,
  "price": 45000.0,
  "status": "filled",
  "filled_quantity": 0.1,
  "average_price": 45000.0,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:01Z"
}
```

#### Cancel Order

```http
DELETE /v1/orders/{order_id}
```

**Response:**
```json
{
  "order_id": "order_456",
  "status": "cancelled",
  "cancelled_at": "2024-01-01T12:05:00Z"
}
```

#### Get Trade History

```http
GET /v1/trades/history
```

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `start_date` (optional): Start date (ISO 8601)
- `end_date` (optional): End date (ISO 8601)
- `status` (optional): Filter by status
- `limit` (optional): Maximum results (default: 100)

**Response:**
```json
{
  "trades": [
    {
      "id": "trade_123",
      "symbol": "BTCUSDT",
      "side": "buy",
      "quantity": 0.1,
      "price": 45000.0,
      "commission": 0.45,
      "timestamp": "2024-01-01T12:00:00Z",
      "pnl": 10.0
    }
  ],
  "total_count": 150,
  "page": 1,
  "total_pages": 2
}
```

### Market Data Endpoints

#### Get Market Data

```http
GET /v1/market-data/{symbol}
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "price": 45123.45,
  "bid": 45123.44,
  "ask": 45123.45,
  "volume_24h": 1234567.89,
  "change_24h": 2.34,
  "high_24h": 46000.0,
  "low_24h": 44000.0,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Get OHLCV Data

```http
GET /v1/market-data/{symbol}/ohlcv
```

**Query Parameters:**
- `interval`: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
- `start_time`: Start timestamp (Unix timestamp)
- `end_time`: End timestamp (Unix timestamp)
- `limit`: Number of candles (max: 1000)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "data": [
    {
      "timestamp": 1704110400,
      "open": 45000.0,
      "high": 45200.0,
      "low": 44800.0,
      "close": 45100.0,
      "volume": 123.45
    }
  ]
}
```

#### Get Order Book

```http
GET /v1/market-data/{symbol}/orderbook
```

**Query Parameters:**
- `limit`: Number of price levels (default: 20, max: 100)

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "timestamp": 1704110400,
  "bids": [
    ["45123.44", "0.123"],
    ["45123.43", "0.456"]
  ],
  "asks": [
    ["45123.45", "0.789"],
    ["45123.46", "0.234"]
  ]
}
```

### Risk Management Endpoints

#### Get Risk Metrics

```http
GET /v1/risk/metrics
```

**Response:**
```json
{
  "account_balance": 10000.0,
  "available_balance": 5500.0,
  "total_exposure": 4500.0,
  "daily_pnl": 50.0,
  "daily_loss": 0.0,
  "max_drawdown": 5.2,
  "var_95": 123.45,
  "risk_score": 0.35,
  "position_limits": {
    "BTCUSDT": {"used": 0.1, "limit": 1.0},
    "total": {"used": 4500.0, "limit": 10000.0}
  },
  "margin_used": 45.0,
  "margin_available": 55.0
}
```

#### Update Risk Limits

```http
PUT /v1/risk/limits
```

**Request Body:**
```json
{
  "max_position_size": 2000.0,
  "max_daily_loss": 1000.0,
  "max_drawdown": 0.15,
  "stop_loss_percent": 2.5,
  "position_limits": {
    "BTCUSDT": 0.5,
    "ETHUSDT": 10.0
  }
}
```

#### Get Risk Events

```http
GET /v1/risk/events
```

**Query Parameters:**
- `severity`: Filter by severity (low, medium, high, critical)
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)

**Response:**
```json
{
  "events": [
    {
      "id": "risk_123",
      "type": "position_limit_warning",
      "severity": "medium",
      "message": "Position limit approaching for BTCUSDT",
      "timestamp": "2024-01-01T12:00:00Z",
      "resolved": false
    }
  ]
}
```

### Analytics Endpoints

#### Get Performance Analytics

```http
GET /v1/analytics/performance
```

**Query Parameters:**
- `period`: Analysis period (1d, 1w, 1m, 3m, 6m, 1y)
- `symbol`: Filter by symbol (optional)

**Response:**
```json
{
  "period": "1m",
  "total_trades": 150,
  "winning_trades": 90,
  "losing_trades": 60,
  "win_rate": 60.0,
  "total_pnl": 1234.56,
  "average_win": 25.67,
  "average_loss": -12.34,
  "profit_factor": 1.85,
  "sharpe_ratio": 1.23,
  "max_drawdown": 5.2,
  "average_trade_duration": 4.5,
  "best_trade": 123.45,
  "worst_trade": -67.89
}
```

#### Get SMC Analysis

```http
GET /v1/analytics/smc/{symbol}
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "timestamp": "2024-01-01T12:00:00Z",
  "analysis": {
    "trend": "bullish",
    "order_blocks": [
      {
        "price_level": [44000.0, 44200.0],
        "type": "bullish",
        "strength": 0.85,
        "volume_ratio": 1.5
      }
    ],
    "choch_bos": {
      "confirmed": true,
      "price_level": 45500.0,
      "direction": "bullish"
    },
    "fvg": {
      "detected": true,
      "top": 44800.0,
      "bottom": 44600.0
    },
    "liquidity_sweeps": [
      {
        "price": 44300.0,
        "volume": 1234567.0,
        "timestamp": "2024-01-01T11:45:00Z"
      }
    ]
  }
}
```

### System Administration Endpoints

#### Get System Health

```http
GET /v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "uptime": 86400,
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 12
    },
    "redis": {
      "status": "healthy",
      "response_time": 2
    },
    "exchange_api": {
      "binance": {
        "status": "healthy",
        "response_time": 45,
        "rate_limit_remaining": 1180
      }
    },
    "execution_engine": {
      "status": "healthy",
      "active_orders": 0
    }
  }
}
```

#### Get System Metrics

```http
GET /v1/metrics
```

**Response (Prometheus format):**
```
# HELP smc_trades_total Total number of trades
smc_trades_total 150
# HELP smc_pnl_total Total profit and loss
smc_pnl_total 1234.56
# HELP smc_api_requests_total Total API requests
smc_api_requests_total{status="200"} 1234
smc_api_requests_total{status="429"} 12
# HELP smc_cpu_usage CPU usage percentage
smc_cpu_usage 45.2
# HELP smc_memory_usage Memory usage percentage
smc_memory_usage 67.8
```

#### Configuration Management

```http
GET /v1/config
```

**Response:**
```json
{
  "trading": {
    "max_position_size": 1000.0,
    "max_daily_loss": 500.0,
    "risk_enabled": true
  },
  "exchanges": {
    "binance": {
      "enabled": true,
      "symbols": ["BTCUSDT", "ETHUSDT"]
    }
  },
  "notifications": {
    "slack_enabled": true,
    "email_enabled": false
  }
}
```

```http
PUT /v1/config
```

**Request Body:**
```json
{
  "trading.max_position_size": 1500.0,
  "exchanges.binance.symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
}
```

## WebSocket API

### WebSocket Connections

**Production WebSocket URL:**
```
wss://ws.smc-trading.com/v1/ws
```

**Development WebSocket URL:**
```
ws://localhost:8000/v1/ws
```

### Connection Authentication

WebSocket connections require authentication via query parameters:

```
ws://localhost:8000/v1/ws?token=YOUR_API_TOKEN
```

### WebSocket Messages

All WebSocket messages follow this format:

```json
{
  "type": "message_type",
  "data": {...},
  "timestamp": "2024-01-01T12:00:00Z",
  "id": "unique_message_id"
}
```

### Real-time Market Data

**Subscribe to Market Data:**
```json
{
  "type": "subscribe",
  "channel": "market_data",
  "symbol": "BTCUSDT"
}
```

**Market Data Update:**
```json
{
  "type": "market_data_update",
  "data": {
    "symbol": "BTCUSDT",
    "price": 45123.45,
    "bid": 45123.44,
    "ask": 45123.45,
    "volume_24h": 1234567.89,
    "change_24h": 2.34,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Real-time Trade Updates

**Subscribe to Trade Updates:**
```json
{
  "type": "subscribe",
  "channel": "trades"
}
```

**Trade Update:**
```json
{
  "type": "trade_update",
  "data": {
    "order_id": "order_456",
    "symbol": "BTCUSDT",
    "side": "buy",
    "quantity": 0.1,
    "price": 45000.0,
    "status": "filled",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Real-time Position Updates

**Subscribe to Position Updates:**
```json
{
  "type": "subscribe",
  "channel": "positions"
}
```

**Position Update:**
```json
{
  "type": "position_update",
  "data": {
    "symbol": "BTCUSDT",
    "quantity": 0.1,
    "entry_price": 45000.0,
    "current_price": 45100.0,
    "unrealized_pnl": 10.0,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### WebSocket Example (JavaScript)

```javascript
class SMCTradingWebSocket {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.subscriptions = new Set();
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/v1/ws?token=${this.token}`);

    this.ws.onopen = () => {
      console.log('Connected to SMC WebSocket API');
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
      // Implement reconnection logic
      setTimeout(() => this.connect(), 5000);
    };
  }

  subscribe(channel, symbol = null) {
    const subscription = { channel, symbol };
    this.subscriptions.add(subscription);

    const message = {
      type: 'subscribe',
      channel: channel,
      ...(symbol && { symbol: symbol })
    };

    this.ws.send(JSON.stringify(message));
  }

  handleMessage(message) {
    switch (message.type) {
      case 'market_data_update':
        this.onMarketDataUpdate(message.data);
        break;
      case 'trade_update':
        this.onTradeUpdate(message.data);
        break;
      case 'position_update':
        this.onPositionUpdate(message.data);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  onMarketDataUpdate(data) {
    // Handle market data updates
    console.log('Market data update:', data);
  }

  onTradeUpdate(data) {
    // Handle trade updates
    console.log('Trade update:', data);
  }

  onPositionUpdate(data) {
    // Handle position updates
    console.log('Position update:', data);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage example
const wsClient = new SMCTradingWebSocket('YOUR_API_TOKEN');
wsClient.connect();

// Subscribe to BTCUSDT market data
wsClient.subscribe('market_data', 'BTCUSDT');

// Subscribe to all trade updates
wsClient.subscribe('trades');
```

### WebSocket Example (Python)

```python
import websocket
import json
import threading

class SMCTradingWebSocket:
    def __init__(self, token):
        self.token = token
        self.ws_url = f"ws://localhost:8000/v1/ws?token={token}"
        self.ws = None
        self.subscriptions = set()

    def on_message(self, ws, message):
        data = json.loads(message)
        self.handle_message(data)

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")
        # Implement reconnection logic
        threading.Timer(5.0, self.connect).start()

    def on_open(self, ws):
        print("Connected to SMC WebSocket API")

    def handle_message(self, message):
        message_type = message.get('type')
        data = message.get('data')

        if message_type == 'market_data_update':
            self.on_market_data_update(data)
        elif message_type == 'trade_update':
            self.on_trade_update(data)
        elif message_type == 'position_update':
            self.on_position_update(data)

    def on_market_data_update(self, data):
        print(f"Market data update: {data}")

    def on_trade_update(self, data):
        print(f"Trade update: {data}")

    def on_position_update(self, data):
        print(f"Position update: {data}")

    def subscribe(self, channel, symbol=None):
        subscription = {'channel': channel}
        if symbol:
            subscription['symbol'] = symbol

        self.subscriptions.add(subscription)

        message = {
            'type': 'subscribe',
            'channel': channel,
            **({'symbol': symbol} if symbol else {})
        }

        self.ws.send(json.dumps(message))

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        # Run WebSocket in a separate thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def disconnect(self):
        if self.ws:
            self.ws.close()

# Usage example
if __name__ == "__main__":
    ws_client = SMCTradingWebSocket("YOUR_API_TOKEN")
    ws_client.connect()

    # Subscribe to BTCUSDT market data
    ws_client.subscribe('market_data', 'BTCUSDT')

    # Subscribe to all trade updates
    ws_client.subscribe('trades')

    # Keep the main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        ws_client.disconnect()
```

## Error Handling

### HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **502 Bad Gateway**: Upstream service error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Insufficient balance to execute trade",
    "details": {
      "required": 5000.0,
      "available": 3000.0
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123"
  }
}
```

### Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_SYMBOL` | 400 | Invalid trading symbol |
| `INSUFFICIENT_BALANCE` | 400 | Insufficient account balance |
| `POSITION_LIMIT_EXCEEDED` | 400 | Position size limit exceeded |
| `INVALID_ORDER_TYPE` | 400 | Invalid order type |
| `MARKET_CLOSED` | 400 | Market is closed |
| `ORDER_NOT_FOUND` | 404 | Order ID not found |
| `AUTHENTICATION_FAILED` | 401 | Invalid authentication credentials |
| `INSUFFICIENT_PERMISSIONS` | 403 | Insufficient API permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | API rate limit exceeded |
| `EXCHANGE_API_ERROR` | 502 | Exchange API error |
| `SYSTEM_OVERLOAD` | 503 | System temporarily overloaded |

### Error Handling Best Practices

**1. Implement Exponential Backoff:**
```python
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def make_api_request(url, headers, data=None):
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
```

**2. Handle Rate Limiting:**
```python
def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limit exceeded. Retrying after {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False
```

**3. Validate Inputs:**
```python
def validate_trade_request(symbol, quantity, side):
    errors = []

    if not symbol or not isinstance(symbol, str):
        errors.append("Invalid symbol")

    if not isinstance(quantity, (int, float)) or quantity <= 0:
        errors.append("Invalid quantity")

    if side not in ['buy', 'sell']:
        errors.append("Invalid side")

    if errors:
        raise ValueError(f"Validation errors: {', '.join(errors)}")
```

## Rate Limiting

### Rate Limit Configuration

- **Default Rate Limit**: 100 requests per minute
- **Burst Limit**: 20 requests per second
- **WebSocket Connections**: 10 concurrent connections per token

### Rate Limit Headers

API responses include rate limit headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704110400
```

### Rate Limit Response

When rate limits are exceeded:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 100,
      "window": 60,
      "retry_after": 30
    }
  }
}
```

### Rate Limit Implementation

**Python Rate Limiter:**
```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def is_allowed(self):
        now = time.time()

        # Remove old requests outside the time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()

        # Check if we can make a new request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True

        return False

    def wait_time(self):
        if not self.requests:
            return 0
        return max(0, self.time_window - (time.time() - self.requests[0]))

# Usage
rate_limiter = RateLimiter(max_requests=100, time_window=60)

def make_rate_limited_request(url, headers):
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.wait_time()
        time.sleep(wait_time)

    return requests.get(url, headers=headers)
```

## Integration Examples

### Trading Bot Integration

**Complete Trading Bot Example:**
```python
import requests
import websocket
import json
import time
import logging
from threading import Thread

class SMCTradingBot:
    def __init__(self, api_token, config):
        self.api_token = api_token
        self.config = config
        self.base_url = "http://localhost:8000/v1"
        self.ws_url = "ws://localhost:8000/v1/ws"
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        self.running = False
        self.positions = {}
        self.market_data = {}

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the trading bot"""
        self.logger.info("Starting SMC Trading Bot...")
        self.running = True

        # Start WebSocket connection
        self.start_websocket()

        # Start main trading loop
        self.start_trading_loop()

    def stop(self):
        """Stop the trading bot"""
        self.logger.info("Stopping SMC Trading Bot...")
        self.running = False

        # Close all positions
        self.close_all_positions()

        # Close WebSocket connection
        if self.ws:
            self.ws.close()

    def start_websocket(self):
        """Start WebSocket connection for real-time data"""
        def on_message(ws, message):
            data = json.loads(message)
            self.handle_websocket_message(data)

        def on_error(ws, error):
            self.logger.error(f"WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.logger.warning("WebSocket connection closed")
            if self.running:
                # Reconnect
                time.sleep(5)
                self.start_websocket()

        def on_open(ws):
            self.logger.info("WebSocket connection established")
            # Subscribe to market data and position updates
            ws.send(json.dumps({
                "type": "subscribe",
                "channel": "market_data",
                "symbol": self.config['symbol']
            }))
            ws.send(json.dumps({
                "type": "subscribe",
                "channel": "positions"
            }))

        self.ws = websocket.WebSocketApp(
            f"{self.ws_url}?token={self.api_token}",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run WebSocket in separate thread
        ws_thread = Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def handle_websocket_message(self, message):
        """Handle incoming WebSocket messages"""
        message_type = message.get('type')
        data = message.get('data')

        if message_type == 'market_data_update':
            self.handle_market_data_update(data)
        elif message_type == 'position_update':
            self.handle_position_update(data)

    def handle_market_data_update(self, data):
        """Handle market data updates"""
        symbol = data['symbol']
        self.market_data[symbol] = data

        # Trigger trading decision
        if self.running:
            self.analyze_market(symbol)

    def handle_position_update(self, data):
        """Handle position updates"""
        symbol = data['symbol']
        self.positions[symbol] = data
        self.logger.info(f"Position updated for {symbol}: {data}")

    def start_trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Analyze all configured symbols
                for symbol in self.config['symbols']:
                    self.analyze_market(symbol)

                # Risk management check
                self.perform_risk_check()

                # Sleep before next iteration
                time.sleep(self.config.get('analysis_interval', 60))

            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(10)

    def analyze_market(self, symbol):
        """Analyze market conditions and make trading decisions"""
        try:
            # Get current market data
            market_data = self.market_data.get(symbol)
            if not market_data:
                return

            # Get SMC analysis
            analysis = self.get_smc_analysis(symbol)

            # Get current position
            position = self.positions.get(symbol)

            # Make trading decision
            signal = self.generate_trading_signal(market_data, analysis, position)

            if signal:
                self.execute_trading_signal(symbol, signal)

        except Exception as e:
            self.logger.error(f"Error analyzing market for {symbol}: {e}")

    def get_smc_analysis(self, symbol):
        """Get SMC analysis from API"""
        try:
            response = requests.get(
                f"{self.base_url}/analytics/smc/{symbol}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error getting SMC analysis for {symbol}: {e}")
            return None

    def generate_trading_signal(self, market_data, analysis, position):
        """Generate trading signal based on analysis"""
        # Simple example strategy - replace with your actual logic
        signal = {
            'action': None,
            'confidence': 0.0,
            'stop_loss': None,
            'take_profit': None,
            'reason': ''
        }

        try:
            if analysis and analysis.get('analysis'):
                smc_analysis = analysis['analysis']

                # Check for bullish setup
                if (smc_analysis.get('trend') == 'bullish' and
                    smc_analysis.get('choch_bos', {}).get('direction') == 'bullish' and
                    not position):

                    signal['action'] = 'buy'
                    signal['confidence'] = 0.8
                    signal['reason'] = 'Bullish CHoCH/BO with trend alignment'

                    # Set stop loss and take profit
                    current_price = market_data['price']
                    signal['stop_loss'] = current_price * 0.98  # 2% stop loss
                    signal['take_profit'] = current_price * 1.06  # 6% take profit

                # Check for bearish setup
                elif (smc_analysis.get('trend') == 'bearish' and
                      smc_analysis.get('choch_bos', {}).get('direction') == 'bearish' and
                      not position):

                    signal['action'] = 'sell'
                    signal['confidence'] = 0.8
                    signal['reason'] = 'Bearish CHoCH/BO with trend alignment'

                    current_price = market_data['price']
                    signal['stop_loss'] = current_price * 1.02  # 2% stop loss
                    signal['take_profit'] = current_price * 0.94  # 6% take profit

                # Check for position exit
                elif position:
                    # Exit logic based on analysis
                    if (position['side'] == 'long' and
                        smc_analysis.get('trend') == 'bearish'):
                        signal['action'] = 'sell'
                        signal['confidence'] = 0.7
                        signal['reason'] = 'Trend reversal detected'

                    elif (position['side'] == 'short' and
                          smc_analysis.get('trend') == 'bullish'):
                        signal['action'] = 'buy'
                        signal['confidence'] = 0.7
                        signal['reason'] = 'Trend reversal detected'

        except Exception as e:
            self.logger.error(f"Error generating trading signal: {e}")

        return signal if signal['action'] and signal['confidence'] > 0.5 else None

    def execute_trading_signal(self, symbol, signal):
        """Execute trading signal"""
        try:
            # Calculate position size based on risk management
            position_size = self.calculate_position_size(symbol, signal)

            if position_size <= 0:
                self.logger.warning(f"Invalid position size for {symbol}: {position_size}")
                return

            # Prepare trade request
            trade_request = {
                "symbol": symbol,
                "side": signal['action'],
                "type": "market",
                "quantity": position_size,
                "stop_loss": signal.get('stop_loss'),
                "take_profit": signal.get('take_profit')
            }

            # Execute trade
            response = requests.post(
                f"{self.base_url}/trades",
                headers=self.headers,
                json=trade_request
            )
            response.raise_for_status()

            trade_result = response.json()
            self.logger.info(f"Trade executed: {trade_result}")

            # Log trade
            self.log_trade(symbol, signal, trade_result)

        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")

    def calculate_position_size(self, symbol, signal):
        """Calculate position size based on risk management"""
        try:
            # Get account balance
            response = requests.get(
                f"{self.base_url}/risk/metrics",
                headers=self.headers
            )
            response.raise_for_status()
            risk_metrics = response.json()

            available_balance = risk_metrics['available_balance']
            risk_per_trade = self.config.get('risk_per_trade', 0.02)  # 2% risk per trade
            max_position_value = available_balance * risk_per_trade

            # Get current price
            market_data = self.market_data.get(symbol)
            if not market_data:
                return 0

            current_price = market_data['price']

            # Calculate position size
            if signal['action'] in ['buy', 'sell']:
                position_size = max_position_value / current_price

                # Apply maximum position size limits
                max_size = self.config.get('max_position_size', float('inf'))
                position_size = min(position_size, max_size)

                return position_size

        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")

        return 0

    def perform_risk_check(self):
        """Perform comprehensive risk management check"""
        try:
            response = requests.get(
                f"{self.base_url}/risk/metrics",
                headers=self.headers
            )
            response.raise_for_status()
            risk_metrics = response.json()

            # Check daily loss limit
            daily_loss = risk_metrics.get('daily_loss', 0)
            max_daily_loss = self.config.get('max_daily_loss', 1000)

            if daily_loss > max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {daily_loss}")
                self.stop_trading()

            # Check maximum drawdown
            max_drawdown = risk_metrics.get('max_drawdown', 0)
            max_allowed_drawdown = self.config.get('max_drawdown', 0.1)

            if max_drawdown > max_allowed_drawdown:
                self.logger.warning(f"Maximum drawdown exceeded: {max_drawdown}")
                self.reduce_positions()

        except Exception as e:
            self.logger.error(f"Error performing risk check: {e}")

    def stop_trading(self):
        """Stop all trading activities"""
        self.logger.warning("Stopping trading due to risk limits")
        self.close_all_positions()
        self.running = False

    def reduce_positions(self):
        """Reduce position sizes to manage risk"""
        self.logger.warning("Reducing position sizes")
        # Implement position reduction logic
        for symbol, position in self.positions.items():
            if position.get('quantity', 0) > 0:
                # Close 50% of position
                close_quantity = position['quantity'] * 0.5
                side = 'sell' if position['side'] == 'long' else 'buy'

                trade_request = {
                    "symbol": symbol,
                    "side": side,
                    "type": "market",
                    "quantity": close_quantity
                }

                try:
                    response = requests.post(
                        f"{self.base_url}/trades",
                        headers=self.headers,
                        json=trade_request
                    )
                    response.raise_for_status()
                    self.logger.info(f"Reduced position for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error reducing position for {symbol}: {e}")

    def close_all_positions(self):
        """Close all open positions"""
        self.logger.info("Closing all positions")

        for symbol, position in self.positions.items():
            if position.get('quantity', 0) > 0:
                side = 'sell' if position['side'] == 'long' else 'buy'

                trade_request = {
                    "symbol": symbol,
                    "side": side,
                    "type": "market",
                    "quantity": position['quantity']
                }

                try:
                    response = requests.post(
                        f"{self.base_url}/trades",
                        headers=self.headers,
                        json=trade_request
                    )
                    response.raise_for_status()
                    self.logger.info(f"Closed position for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error closing position for {symbol}: {e}")

    def log_trade(self, symbol, signal, trade_result):
        """Log trade for analysis"""
        log_entry = {
            'timestamp': time.time(),
            'symbol': symbol,
            'signal': signal,
            'trade_result': trade_result
        }

        # Save to database or file
        self.logger.info(f"Trade logged: {json.dumps(log_entry)}")

# Configuration example
config = {
    'symbols': ['BTCUSDT', 'ETHUSDT'],
    'risk_per_trade': 0.02,  # 2% risk per trade
    'max_daily_loss': 1000,  # $1000 max daily loss
    'max_drawdown': 0.1,  # 10% max drawdown
    'max_position_size': 0.1,  # Max 0.1 BTC per trade
    'analysis_interval': 60  # Analyze every 60 seconds
}

# Usage example
if __name__ == "__main__":
    # Initialize trading bot
    bot = SMCTradingBot(
        api_token="YOUR_API_TOKEN",
        config=config
    )

    try:
        # Start the bot
        bot.start()

        # Keep running
        while bot.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping bot...")
        bot.stop()
```

### Data Analysis Integration

**Python Data Analysis Example:**
```python
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

class SMCDataAnalyzer:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "http://localhost:8000/v1"
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def get_historical_trades(self, symbol, start_date, end_date):
        """Get historical trades for analysis"""
        params = {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        }

        response = requests.get(
            f"{self.base_url}/trades/history",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()

        return pd.DataFrame(response.json()['trades'])

    def get_market_data(self, symbol, interval, start_time, end_time):
        """Get historical market data"""
        params = {
            'interval': interval,
            'start_time': start_time,
            'end_time': end_time,
            'limit': 1000
        }

        response = requests.get(
            f"{self.base_url}/market-data/{symbol}/ohlcv",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()

        data = response.json()['data']
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)

        return df

    def analyze_trading_performance(self, symbol, days=30):
        """Analyze trading performance over specified period"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get trades
        trades = self.get_historical_trades(
            symbol,
            start_date.isoformat(),
            end_date.isoformat()
        )

        if trades.empty:
            print(f"No trades found for {symbol} in the last {days} days")
            return None

        # Calculate performance metrics
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades['pnl'] = pd.to_numeric(trades['pnl'])

        total_trades = len(trades)
        winning_trades = len(trades[trades['pnl'] > 0])
        losing_trades = len(trades[trades['pnl'] < 0])

        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        total_pnl = trades['pnl'].sum()
        avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades[trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        # Calculate profit factor
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Calculate daily returns and Sharpe ratio
        daily_returns = trades.groupby(trades['timestamp'].dt.date)['pnl'].sum()
        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns)

        # Calculate maximum drawdown
        cumulative_pnl = trades['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / running_max
        max_drawdown = drawdown.min()

        performance_metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,  # Convert to percentage
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }

        return performance_metrics

    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
        """Calculate Sharpe ratio for a series of returns"""
        if len(returns) < 2:
            return 0

        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)

    def plot_equity_curve(self, symbol, days=30):
        """Plot equity curve for trades"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        trades = self.get_historical_trades(
            symbol,
            start_date.isoformat(),
            end_date.isoformat()
        )

        if trades.empty:
            print(f"No trades found for {symbol} in the last {days} days")
            return

        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades['pnl'] = pd.to_numeric(trades['pnl'])

        # Calculate cumulative P&L
        trades_sorted = trades.sort_values('timestamp')
        cumulative_pnl = trades_sorted['pnl'].cumsum()

        plt.figure(figsize=(12, 6))
        plt.plot(trades_sorted['timestamp'], cumulative_pnl, linewidth=2)
        plt.title(f'Equity Curve - {symbol} (Last {days} days)')
        plt.xlabel('Date')
        plt.ylabel('Cumulative P&L')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def analyze_market_conditions(self, symbol, days=30):
        """Analyze market conditions and trading opportunities"""
        end_time = int(datetime.now().timestamp())
        start_time = end_time - (days * 24 * 3600)

        # Get market data
        market_data = self.get_market_data(
            symbol, '1h', start_time, end_time
        )

        # Get SMC analysis
        try:
            response = requests.get(
                f"{self.base_url}/analytics/smc/{symbol}",
                headers=self.headers
            )
            response.raise_for_status()
            smc_analysis = response.json()['analysis']
        except:
            smc_analysis = {}

        # Calculate technical indicators
        market_data['sma_20'] = market_data['close'].rolling(window=20).mean()
        market_data['sma_50'] = market_data['close'].rolling(window=50).mean()
        market_data['rsi'] = self.calculate_rsi(market_data['close'])
        market_data['atr'] = self.calculate_atr(market_data)

        # Volatility analysis
        volatility = market_data['close'].pct_change().std() * np.sqrt(252)

        # Trend analysis
        current_price = market_data['close'].iloc[-1]
        sma_20 = market_data['sma_20'].iloc[-1]
        sma_50 = market_data['sma_50'].iloc[-1]

        trend = "neutral"
        if current_price > sma_20 > sma_50:
            trend = "bullish"
        elif current_price < sma_20 < sma_50:
            trend = "bearish"

        # RSI analysis
        current_rsi = market_data['rsi'].iloc[-1]
        rsi_signal = "neutral"
        if current_rsi < 30:
            rsi_signal = "oversold"
        elif current_rsi > 70:
            rsi_signal = "overbought"

        analysis = {
            'current_price': current_price,
            'trend': trend,
            'rsi': current_rsi,
            'rsi_signal': rsi_signal,
            'volatility': volatility,
            'atr': market_data['atr'].iloc[-1],
            'smc_analysis': smc_analysis,
            'recommendation': self.generate_recommendation(
                trend, rsi_signal, smc_analysis
            )
        }

        return analysis

    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_atr(self, data, period=14):
        """Calculate Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()

    def generate_recommendation(self, trend, rsi_signal, smc_analysis):
        """Generate trading recommendation based on analysis"""
        recommendation = {
            'action': 'hold',
            'confidence': 0.5,
            'reasoning': []
        }

        # Trend-based recommendation
        if trend == 'bullish' and rsi_signal != 'overbought':
            recommendation['action'] = 'buy'
            recommendation['confidence'] += 0.2
            recommendation['reasoning'].append('Bullish trend')

        elif trend == 'bearish' and rsi_signal != 'oversold':
            recommendation['action'] = 'sell'
            recommendation['confidence'] += 0.2
            recommendation['reasoning'].append('Bearish trend')

        # RSI-based adjustment
        if rsi_signal == 'oversold' and recommendation['action'] != 'sell':
            recommendation['action'] = 'buy'
            recommendation['confidence'] += 0.15
            recommendation['reasoning'].append('RSI oversold')

        elif rsi_signal == 'overbought' and recommendation['action'] != 'buy':
            recommendation['action'] = 'sell'
            recommendation['confidence'] += 0.15
            recommendation['reasoning'].append('RSI overbought')

        # SMC analysis integration
        if smc_analysis:
            smc_trend = smc_analysis.get('trend')
            if smc_trend == 'bullish' and recommendation['action'] != 'sell':
                recommendation['confidence'] += 0.25
                recommendation['reasoning'].append('SMC bullish analysis')
            elif smc_trend == 'bearish' and recommendation['action'] != 'buy':
                recommendation['confidence'] += 0.25
                recommendation['reasoning'].append('SMC bearish analysis')

        # Cap confidence
        recommendation['confidence'] = min(recommendation['confidence'], 1.0)

        # Set action to hold if confidence is too low
        if recommendation['confidence'] < 0.6:
            recommendation['action'] = 'hold'
            recommendation['reasoning'].append('Low confidence')

        return recommendation

# Usage example
if __name__ == "__main__":
    analyzer = SMCDataAnalyzer("YOUR_API_TOKEN")

    # Analyze BTCUSDT performance
    performance = analyzer.analyze_trading_performance('BTCUSDT', days=30)
    if performance:
        print("Trading Performance Analysis:")
        for key, value in performance.items():
            print(f"{key}: {value}")

    # Plot equity curve
    analyzer.plot_equity_curve('BTCUSDT', days=30)

    # Analyze current market conditions
    market_analysis = analyzer.analyze_market_conditions('BTCUSDT', days=30)
    print("\nMarket Analysis:")
    for key, value in market_analysis.items():
        print(f"{key}: {value}")
```

## SDKs and Libraries

### Python SDK

**Installation:**
```bash
pip install smc-trading-sdk
```

**Usage:**
```python
from smc_trading import SMCClient

# Initialize client
client = SMCClient(api_token="YOUR_API_TOKEN")

# Get positions
positions = client.get_positions()

# Execute trade
trade = client.execute_trade(
    symbol="BTCUSDT",
    side="buy",
    quantity=0.1,
    type="market"
)

# Get market data
market_data = client.get_market_data("BTCUSDT")

# Subscribe to WebSocket updates
def on_trade_update(data):
    print(f"Trade update: {data}")

client.subscribe_to_trades(on_trade_update)
```

### JavaScript SDK

**Installation:**
```bash
npm install smc-trading-sdk
```

**Usage:**
```javascript
import { SMCClient } from 'smc-trading-sdk';

// Initialize client
const client = new SMCClient('YOUR_API_TOKEN');

// Get positions
async function getPositions() {
  const positions = await client.getPositions();
  console.log(positions);
}

// Execute trade
async function executeTrade() {
  const trade = await client.executeTrade({
    symbol: 'BTCUSDT',
    side: 'buy',
    quantity: 0.1,
    type: 'market'
  });
  console.log(trade);
}

// WebSocket subscription
client.onTradeUpdate((data) => {
  console.log('Trade update:', data);
});

client.connect();
```

## API Versioning

### Version Strategy

The SMC Trading Agent API follows semantic versioning:

- **Major version (X.0.0)**: Breaking changes
- **Minor version (X.Y.0)**: New features, backward compatible
- **Patch version (X.Y.Z)**: Bug fixes, backward compatible

### Current Versions

- **API v1**: Current stable version
- **API v2**: In development (alpha)

### Version Specification

Specify API version in the URL:

```http
https://api.smc-trading.com/v1/trades
https://api.smc-trading.com/v2/trades  # Future version
```

### Migration Guide

**v1 to v2 Migration:**

Breaking changes in v2:
- Renamed endpoints
- Changed response formats
- Updated authentication
- New required fields

**Migration Steps:**
1. Update API base URL to use v2
2. Update authentication method
3. Modify request/response handling
4. Test with v2 endpoints
5. Deploy updated integration

## Testing and Debugging

### API Testing Tools

**Postman Collection:**
```json
{
  "info": {
    "name": "SMC Trading API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{api_token}}",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "api_token",
      "value": "YOUR_API_TOKEN"
    }
  ]
}
```

### Debug Mode

Enable debug mode for detailed logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('smc_trading')

# Enable API debug mode
client = SMCClient(api_token="YOUR_TOKEN", debug=True)
```

### Test Environment

Use the test environment for development:

```http
https://test-api.smc-trading.com/v1
```

Test environment features:
- Paper trading only
- Simulated market data
- Rate limits: 1000 requests per hour
- No financial risk

### Health Check Endpoint

Monitor API health:

```http
GET /v1/health
```

### Performance Testing

**Load Testing Script:**
```python
import asyncio
import aiohttp
import time

async def load_test(base_url, token, concurrent_requests=50, duration=60):
    """Load test the API"""

    async def make_request(session, url):
        start_time = time.time()
        try:
            async with session.get(url) as response:
                await response.text()
                return {
                    'status': response.status,
                    'response_time': time.time() - start_time
                }
        except Exception as e:
            return {
                'status': 500,
                'response_time': time.time() - start_time,
                'error': str(e)
            }

    headers = {'Authorization': f'Bearer {token}'}
    url = f"{base_url}/v1/health"

    async with aiohttp.ClientSession(headers=headers) as session:
        start_time = time.time()
        requests = []
        response_times = []
        errors = 0

        while time.time() - start_time < duration:
            # Create batch of requests
            tasks = []
            for _ in range(concurrent_requests):
                task = make_request(session, url)
                tasks.append(task)

            # Execute batch
            results = await asyncio.gather(*tasks)

            for result in results:
                requests.append(result)
                response_times.append(result['response_time'])
                if result['status'] != 200:
                    errors += 1

            # Small delay between batches
            await asyncio.sleep(0.1)

        # Calculate statistics
        total_requests = len(requests)
        successful_requests = total_requests - errors
        success_rate = (successful_requests / total_requests) * 100
        avg_response_time = sum(response_times) / len(response_times)

        print(f"Load Test Results:")
        print(f"Total requests: {total_requests}")
        print(f"Successful requests: {successful_requests}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Errors: {errors}")

# Usage
asyncio.run(load_test(
    "http://localhost:8000",
    "YOUR_API_TOKEN",
    concurrent_requests=20,
    duration=30
))
```

---

This comprehensive API documentation provides all the information needed to integrate with the SMC Trading Agent API effectively. For additional support, refer to the example code and SDKs provided, or contact the development team for assistance.