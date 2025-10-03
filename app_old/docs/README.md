# SMC Trading Agent API Documentation

Welcome to the comprehensive API documentation for the SMC Trading Agent - a sophisticated algorithmic trading system implementing Smart Money Concepts (SMC) for automated cryptocurrency and forex trading.

## 📚 Documentation Overview

This documentation provides complete coverage of both APIs that make up the SMC Trading Agent system:

1. **Express.js API** - Authentication, user management, and exchange integrations
2. **FastAPI** - Core trading engine with SMC pattern detection and risk management

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.10+ with pip
- Docker (optional)
- Exchange API keys (Binance, Bybit, or Oanda)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/smc-trading-agent/smc-trading-agent.git
   cd smc-trading-agent
   ```

2. **Install dependencies:**

   ```bash
   npm install
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the development servers:**

   ```bash
   # Start both APIs
   npm run api:start

   # Or start individually
   npm run server:dev  # Express.js API on port 3000
   python -m uvicorn api_fastapi:app --reload --port 8000  # FastAPI on port 8000
   ```

### First API Call

1. **Register a new user:**

   ```bash
   curl -X POST "http://localhost:3000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "trader@example.com",
       "password": "SecurePassword123!",
       "full_name": "Test Trader"
     }'
   ```

2. **Login to get JWT token:**

   ```bash
   curl -X POST "http://localhost:3000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "trader@example.com",
       "password": "SecurePassword123!"
     }'
   ```

3. **Use the token for authenticated requests:**
   ```bash
   curl -X GET "http://localhost:3000/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

## 📖 Documentation Formats

### Interactive Documentation

- **Express.js Swagger UI**: http://localhost:3000/api/docs
- **FastAPI Swagger UI**: http://localhost:8000/api/v1/docs
- **Combined Documentation**: [docs/api/index.html](api/index.html)

### Static Documentation

- **Express.js ReDoc**: [docs/api/express-api.html](api/express-api.html)
- **FastAPI ReDoc**: [docs/api/fastapi-api.html](api/fastapi-api.html)
- **API Examples**: [api-examples.md](api-examples.md)

### OpenAPI Specifications

- **Express.js OpenAPI**: [openapi-express.json](openapi-express.json)
- **FastAPI OpenAPI**: [openapi-fastapi.json](openapi-fastapi.json)

### Testing Collections

- **Postman Collection**: [postman/smc-trading-agent-collection.json](postman/smc-trading-agent-collection.json)
- **Development Environment**: [postman/development.json](postman/development.json)
- **Production Environment**: [postman/production.json](postman/production.json)

## 🏗️ API Architecture

### Express.js API (Port 3000)

**Purpose**: API Gateway, Authentication, User Management, Exchange Integrations

**Key Features**:

- JWT-based authentication with refresh tokens
- Multi-factor authentication (TOTP, WebAuthn, SMS)
- Exchange API key management with encryption
- Rate limiting and security middleware
- Comprehensive input validation

**Main Endpoints**:

- `/api/v1/auth/*` - Authentication and authorization
- `/api/v1/users/*` - User profile and settings management
- `/api/v1/binance/*` - Binance exchange integration
- `/api/v1/bybit/*` - Bybit exchange integration (future)
- `/api/v1/oanda/*` - Oanda forex integration (future)

### FastAPI (Port 8000)

**Purpose**: Trading Engine, SMC Pattern Detection, Risk Management

**Key Features**:

- SMC pattern detection algorithms
- Real-time market data processing
- Risk management and position sizing
- Strategy backtesting
- Model ensemble for decision making

**Main Endpoints**:

- `/api/v1/market-data/*` - Historical and real-time market data
- `/api/v1/signals/*` - SMC trading signals
- `/api/v1/orders/*` - Order placement and management
- `/api/v1/risk-metrics/*` - Portfolio risk analysis
- `/api/v1/backtest/*` - Strategy backtesting

## 🔐 Authentication

### JWT Token Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

1. **Register** or **Login** via the Express.js API
2. **Store the token** securely in your application
3. **Include the token** in subsequent API requests
4. **Refresh the token** before it expires

### Multi-Factor Authentication

For enhanced security, enable MFA:

1. **TOTP (Time-based One-Time Password)** - Google Authenticator, Authy
2. **WebAuthn** - Hardware security keys, biometrics
3. **SMS** - Text message verification

## 📊 API Versioning

### Current Version: v1

The API uses URL path versioning:

- **Versioned URLs**: `/api/v1/endpoint`
- **Version Header**: `X-API-Version: v1`
- **Legacy Support**: Unversioned URLs redirect to v1 with deprecation warnings

### Version Migration

When new versions are released:

1. **Backward Compatibility**: v1 endpoints remain functional
2. **Deprecation Warnings**: Headers indicate deprecated endpoints
3. **Migration Guides**: Documentation for upgrading to new versions
4. **Sunset Dates**: Advance notice before version retirement

## 🚦 Rate Limiting

API endpoints are rate-limited to ensure fair usage:

| Endpoint Type      | Limit        | Window     |
| ------------------ | ------------ | ---------- |
| General            | 100 requests | 15 minutes |
| Authentication     | 5 attempts   | 15 minutes |
| Trading            | 10 requests  | 1 minute   |
| Market Data        | 60 requests  | 1 minute   |
| API Key Operations | 5 requests   | 1 hour     |

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
Retry-After: 900
```

## 🛠️ Development Tools

### Generate Documentation

```bash
# Generate all documentation
npm run docs:generate

# Validate OpenAPI specs
npm run docs:validate

# Serve documentation locally
npm run docs:serve

# Build and validate
npm run docs:build
```

### Testing with Postman

1. **Import Collection**: Import `docs/postman/smc-trading-agent-collection.json`
2. **Set Environment**: Use `development.json` or `production.json`
3. **Configure Variables**: Update API keys and credentials
4. **Run Tests**: Execute individual requests or entire collection

### Testing with Newman (CLI)

```bash
# Install Newman
npm install -g newman

# Run collection with development environment
newman run docs/postman/smc-trading-agent-collection.json \
  -e docs/postman/development.json

# Run with detailed reporting
newman run docs/postman/smc-trading-agent-collection.json \
  -e docs/postman/development.json \
  --reporters cli,html \
  --reporter-html-export newman-report.html
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Server Configuration
NODE_ENV=development
PORT=3000
FASTAPI_PORT=8000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/smc_trading
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-key

# Authentication
JWT_SECRET=your-jwt-secret
JWT_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=7d

# Redis (for rate limiting and caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Exchange API Keys (for testing)
BINANCE_TESTNET_API_KEY=your-binance-testnet-key
BINANCE_TESTNET_SECRET=your-binance-testnet-secret

# Vault (for production secrets management)
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=your-vault-token

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

### Exchange Configuration

Configure exchange connections in the application:

1. **Binance**: Supports spot trading, testnet available
2. **Bybit**: Derivatives and spot trading (coming soon)
3. **Oanda**: Forex trading with MT4/MT5 integration (coming soon)

## 📈 Monitoring and Observability

### Health Checks

- **Express.js**: `GET /api/health`
- **FastAPI**: `GET /health`
- **Combined**: Both APIs report system status

### Metrics

- **Request/Response Times**: P50, P95, P99 latencies
- **Error Rates**: 4xx and 5xx response rates
- **Trading Metrics**: Orders placed, success rates, PnL
- **System Metrics**: CPU, memory, disk usage

### Logging

- **Structured Logging**: JSON format for easy parsing
- **Request Logging**: All API requests with correlation IDs
- **Error Logging**: Detailed error traces and context
- **Audit Logging**: Security events and sensitive operations

## 🚨 Error Handling

### Standard Error Format

All APIs return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional error details",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Common Error Codes

| Code                  | Status | Description              |
| --------------------- | ------ | ------------------------ |
| `VALIDATION_ERROR`    | 400    | Invalid request data     |
| `UNAUTHORIZED`        | 401    | Authentication required  |
| `FORBIDDEN`           | 403    | Insufficient permissions |
| `NOT_FOUND`           | 404    | Resource not found       |
| `RATE_LIMIT_EXCEEDED` | 429    | Too many requests        |
| `INTERNAL_ERROR`      | 500    | Server error             |

### Error Recovery

- **Retry Logic**: Exponential backoff for transient errors
- **Circuit Breakers**: Prevent cascade failures
- **Graceful Degradation**: Fallback to cached data when possible
- **User Feedback**: Clear error messages and recovery suggestions

## 🔒 Security

### Security Headers

All responses include security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'
```

### Input Validation

- **Schema Validation**: Zod schemas for TypeScript, Pydantic for Python
- **Sanitization**: XSS prevention and SQL injection protection
- **Rate Limiting**: Per-user and per-IP request limits
- **CORS**: Configured for specific origins only

### Data Protection

- **Encryption at Rest**: API keys and sensitive data encrypted
- **Encryption in Transit**: TLS 1.3 for all communications
- **PII Handling**: GDPR-compliant data processing
- **Audit Trails**: Complete logging of sensitive operations

## 🌐 Deployment

### Development

```bash
# Start development servers
npm run dev

# Start APIs only
npm run api:start

# Generate and serve documentation
npm run docs:build && npm run docs:serve
```

### Production

```bash
# Build applications
npm run build

# Start production servers
NODE_ENV=production npm start
NODE_ENV=production python -m uvicorn api_fastapi:app --host 0.0.0.0 --port 8000

# Or use Docker
docker-compose up -d
```

### Docker Deployment

```yaml
# docker-compose.yml
version: "3.8"
services:
  express-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production

  fastapi:
    build:
      context: .
      dockerfile: Dockerfile.python
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
```

## 📞 Support

### Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/smc-trading-agent/smc-trading-agent/issues)
- **Documentation**: [Full documentation site](https://docs.smctradingagent.com)
- **Email Support**: support@smctradingagent.com
- **Discord Community**: [Join our Discord](https://discord.gg/smc-trading-agent)

### Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests and documentation**
5. **Submit a pull request**

### Reporting Issues

When reporting issues, please include:

- **API version** and endpoint
- **Request/response examples**
- **Error messages** and stack traces
- **Environment details** (OS, Node.js/Python versions)
- **Steps to reproduce** the issue

## 📋 Changelog

### Version 1.0.0 (Current)

- ✅ Complete Express.js API with authentication
- ✅ FastAPI trading engine with SMC detection
- ✅ Comprehensive OpenAPI documentation
- ✅ Postman collections for testing
- ✅ CI/CD pipeline for documentation
- ✅ Rate limiting and security middleware
- ✅ Multi-exchange support (Binance ready)

### Upcoming Features

- 🔄 Bybit and Oanda exchange integrations
- 🔄 WebSocket real-time data streams
- 🔄 Advanced risk management features
- 🔄 Strategy marketplace and sharing
- 🔄 Mobile app API endpoints
- 🔄 Webhook notifications

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🙏 Acknowledgments

- **CCXT Library**: Multi-exchange trading library
- **FastAPI**: Modern Python web framework
- **Express.js**: Node.js web application framework
- **Swagger/OpenAPI**: API documentation standards
- **Postman**: API testing and collaboration platform

---

_Last updated: January 15, 2024_

For the most up-to-date documentation, visit our [interactive API documentation](http://localhost:3000/api/docs) or [live documentation site](https://docs.smctradingagent.com).
