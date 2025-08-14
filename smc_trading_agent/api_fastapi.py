"""
FastAPI application for SMC Trading Agent
Provides comprehensive OpenAPI documentation and trading engine endpoints
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# API version and metadata
API_VERSION = "v1"
API_TITLE = "SMC Trading Agent API"
API_DESCRIPTION = """
## Smart Money Concepts Trading Agent API

A sophisticated algorithmic trading system API that implements Smart Money Concepts (SMC) 
for automated cryptocurrency and forex trading.

### Key Features

- **Multi-Exchange Support**: Integrates with Binance, Bybit, and Oanda
- **SMC Pattern Detection**: Advanced algorithms for institutional trading patterns
- **Real-time Processing**: Live market data analysis with sub-second latency
- **Risk Management**: Comprehensive position sizing and risk controls
- **Model Ensemble**: Machine learning models for decision making

### Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Rate Limiting

API endpoints are rate-limited to ensure system stability and fair usage.

### Error Handling

All endpoints return consistent error responses with appropriate HTTP status codes.

### Environments

- **Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.smctradingagent.com`
- **Production**: `https://api.smctradingagent.com`

### API Versioning

This API uses URL path versioning. Current version: **v1**

- Version in URL: `/api/v1/endpoint`
- Version header: `X-API-Version: v1`
- OpenAPI spec: `/api/v1/openapi.json`

### Response Format

All API responses follow a consistent format:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional details",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Examples

#### Authentication Example
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"email": "trader@example.com", "password": "password"}'
```

#### Get Market Data Example
```bash
curl -X GET "http://localhost:8000/api/v1/market-data/BTC/USDT?timeframe=1h&limit=100" \\
  -H "Authorization: Bearer your-jwt-token"
```

#### Place Order Example
```bash
curl -X POST "http://localhost:8000/api/v1/orders" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-jwt-token" \\
  -d '{
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.001,
    "price": 45000.0
  }'
```
"""

# Create FastAPI application with comprehensive metadata
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_url=f"/api/{API_VERSION}/openapi.json",
    docs_url=f"/api/{API_VERSION}/docs",
    redoc_url=f"/api/{API_VERSION}/redoc",
    contact={
        "name": "SMC Trading Agent Support",
        "email": "support@smctradingagent.com",
        "url": "https://github.com/smc-trading-agent"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://smctradingagent.com/terms",
    servers=[
        {
            "url": f"http://localhost:8000/api/{API_VERSION}",
            "description": "Development server"
        },
        {
            "url": f"https://staging-api.smctradingagent.com/api/{API_VERSION}",
            "description": "Staging server"
        },
        {
            "url": f"https://api.smctradingagent.com/api/{API_VERSION}",
            "description": "Production server"
        }
    ],
    openapi_tags=[
        {
            "name": "System",
            "description": "System health and information endpoints"
        },
        {
            "name": "Authentication",
            "description": "User authentication and authorization"
        },
        {
            "name": "Market Data",
            "description": "Real-time and historical market data from exchanges"
        },
        {
            "name": "Trading Signals",
            "description": "SMC pattern detection and trading signals"
        },
        {
            "name": "Trading",
            "description": "Order placement and trade execution"
        },
        {
            "name": "Risk Management",
            "description": "Portfolio risk metrics and position management"
        },
        {
            "name": "Strategy Testing",
            "description": "Backtesting and strategy validation"
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("NODE_ENV") == "development" else [
        "https://smctradingagent.com",
        "https://app.smctradingagent.com",
        "https://staging.smctradingagent.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class ExchangeEnum(str, Enum):
    """Supported exchanges"""
    binance = "binance"
    bybit = "bybit"
    oanda = "oanda"

class OrderSideEnum(str, Enum):
    """Order side"""
    buy = "buy"
    sell = "sell"

class OrderTypeEnum(str, Enum):
    """Order type"""
    market = "market"
    limit = "limit"
    stop_loss = "stop_loss"
    take_profit = "take_profit"

class SignalTypeEnum(str, Enum):
    """SMC signal types"""
    order_block = "order_block"
    liquidity_zone = "liquidity_zone"
    fair_value_gap = "fair_value_gap"
    break_of_structure = "break_of_structure"

class TrendDirectionEnum(str, Enum):
    """Trend direction"""
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"

# Pydantic models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    code: Optional[str] = Field(None, description="Error code")

class HealthResponse(BaseResponse):
    """Health check response"""
    status: str = Field(..., description="Service status", example="healthy")
    version: str = Field(..., description="API version", example="1.0.0")
    uptime: float = Field(..., description="Uptime in seconds", example=3600.5)
    environment: str = Field(..., description="Environment", example="development")

class MarketDataPoint(BaseModel):
    """Market data point"""
    timestamp: datetime = Field(..., description="Data timestamp")
    open: float = Field(..., description="Opening price", example=45000.0)
    high: float = Field(..., description="Highest price", example=45500.0)
    low: float = Field(..., description="Lowest price", example=44500.0)
    close: float = Field(..., description="Closing price", example=45250.0)
    volume: float = Field(..., description="Trading volume", example=1234.56)

class SMCSignal(BaseModel):
    """SMC trading signal"""
    id: str = Field(..., description="Signal ID", example="sig_123456")
    symbol: str = Field(..., description="Trading symbol", example="BTC/USDT")
    signal_type: SignalTypeEnum = Field(..., description="Type of SMC signal")
    direction: TrendDirectionEnum = Field(..., description="Signal direction")
    confidence: float = Field(..., description="Signal confidence (0-1)", ge=0, le=1, example=0.85)
    entry_price: float = Field(..., description="Suggested entry price", example=45000.0)
    stop_loss: Optional[float] = Field(None, description="Stop loss price", example=44000.0)
    take_profit: Optional[float] = Field(None, description="Take profit price", example=46000.0)
    risk_reward_ratio: Optional[float] = Field(None, description="Risk/reward ratio", example=2.5)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Signal creation time")
    expires_at: Optional[datetime] = Field(None, description="Signal expiration time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional signal metadata")

class TradingOrder(BaseModel):
    """Trading order model"""
    id: str = Field(..., description="Order ID", example="ord_123456")
    symbol: str = Field(..., description="Trading symbol", example="BTC/USDT")
    side: OrderSideEnum = Field(..., description="Order side")
    type: OrderTypeEnum = Field(..., description="Order type")
    quantity: float = Field(..., description="Order quantity", gt=0, example=0.001)
    price: Optional[float] = Field(None, description="Order price", example=45000.0)
    filled_quantity: float = Field(0, description="Filled quantity", example=0.0005)
    status: str = Field(..., description="Order status", example="pending")
    exchange: ExchangeEnum = Field(..., description="Exchange")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Order creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

class CreateOrderRequest(BaseModel):
    """Create order request"""
    symbol: str = Field(..., description="Trading symbol", example="BTC/USDT")
    side: OrderSideEnum = Field(..., description="Order side")
    type: OrderTypeEnum = Field(..., description="Order type")
    quantity: float = Field(..., description="Order quantity", gt=0, example=0.001)
    price: Optional[float] = Field(None, description="Order price (required for limit orders)", example=45000.0)
    stop_loss: Optional[float] = Field(None, description="Stop loss price", example=44000.0)
    take_profit: Optional[float] = Field(None, description="Take profit price", example=46000.0)
    exchange: ExchangeEnum = Field(..., description="Target exchange")

    @validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        if values.get('type') == OrderTypeEnum.limit and v is None:
            raise ValueError('Price is required for limit orders')
        return v

class RiskMetrics(BaseModel):
    """Risk management metrics"""
    portfolio_value: float = Field(..., description="Total portfolio value", example=10000.0)
    daily_pnl: float = Field(..., description="Daily P&L", example=150.25)
    max_drawdown: float = Field(..., description="Maximum drawdown percentage", example=2.5)
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio", example=1.85)
    win_rate: float = Field(..., description="Win rate percentage", example=65.5)
    risk_score: float = Field(..., description="Risk score (0-100)", ge=0, le=100, example=25.0)
    open_positions: int = Field(..., description="Number of open positions", example=3)
    leverage_ratio: float = Field(..., description="Current leverage ratio", example=2.0)

class BacktestRequest(BaseModel):
    """Backtest request parameters"""
    strategy_name: str = Field(..., description="Strategy name", example="SMC_Scalping_v1")
    symbol: str = Field(..., description="Trading symbol", example="BTC/USDT")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: float = Field(10000.0, description="Initial capital", gt=0)
    risk_per_trade: float = Field(0.02, description="Risk per trade (0-1)", gt=0, le=1)
    parameters: Optional[Dict[str, Any]] = Field(None, description="Strategy parameters")

class BacktestResult(BaseModel):
    """Backtest results"""
    strategy_name: str = Field(..., description="Strategy name")
    symbol: str = Field(..., description="Trading symbol")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: float = Field(..., description="Initial capital")
    final_capital: float = Field(..., description="Final capital")
    total_return: float = Field(..., description="Total return percentage")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown percentage")
    win_rate: float = Field(..., description="Win rate percentage")
    total_trades: int = Field(..., description="Total number of trades")
    profitable_trades: int = Field(..., description="Number of profitable trades")
    avg_trade_duration: float = Field(..., description="Average trade duration in hours")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Result timestamp")

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    # Mock authentication - in production, validate JWT token
    if not credentials or credentials.credentials != "valid-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": "user_123", "email": "trader@example.com"}

# API Routes
@app.get("/", 
         response_model=BaseResponse,
         summary="API Root",
         description="Get basic API information and status")
async def root():
    """API root endpoint"""
    return BaseResponse(
        success=True,
        message=f"SMC Trading Agent API {API_VERSION} is running"
    )

@app.get("/health",
         response_model=HealthResponse,
         summary="Health Check",
         description="Check API health and status",
         tags=["System"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        success=True,
        status="healthy",
        version="1.0.0",
        uptime=3600.5,
        environment=os.getenv("NODE_ENV", "development")
    )

@app.get("/market-data/{symbol}",
         response_model=List[MarketDataPoint],
         summary="Get Market Data",
         description="Retrieve historical market data for a trading symbol",
         tags=["Market Data"])
async def get_market_data(
    symbol: str = Path(..., description="Trading symbol (e.g., BTC/USDT)", example="BTC/USDT"),
    timeframe: str = Query("1h", description="Timeframe (1m, 5m, 1h, 1d)", example="1h"),
    limit: int = Query(100, description="Number of data points", ge=1, le=1000),
    exchange: ExchangeEnum = Query(ExchangeEnum.binance, description="Exchange to fetch data from")
):
    """Get historical market data for a symbol"""
    # Mock data - in production, fetch from exchange APIs
    mock_data = [
        MarketDataPoint(
            timestamp=datetime.utcnow() - timedelta(hours=i),
            open=45000.0 + i * 10,
            high=45500.0 + i * 10,
            low=44500.0 + i * 10,
            close=45250.0 + i * 10,
            volume=1234.56 + i * 100
        ) for i in range(min(limit, 10))
    ]
    return mock_data

@app.get("/signals",
         response_model=List[SMCSignal],
         summary="Get SMC Signals",
         description="Retrieve active SMC trading signals",
         tags=["Trading Signals"],
         dependencies=[Depends(get_current_user)])
async def get_smc_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol", example="BTC/USDT"),
    signal_type: Optional[SignalTypeEnum] = Query(None, description="Filter by signal type"),
    min_confidence: float = Query(0.7, description="Minimum confidence threshold", ge=0, le=1),
    limit: int = Query(20, description="Maximum number of signals", ge=1, le=100)
):
    """Get active SMC trading signals"""
    # Mock signals - in production, fetch from signal detection engine
    mock_signals = [
        SMCSignal(
            id="sig_123456",
            symbol="BTC/USDT",
            signal_type=SignalTypeEnum.order_block,
            direction=TrendDirectionEnum.bullish,
            confidence=0.85,
            entry_price=45000.0,
            stop_loss=44000.0,
            take_profit=46000.0,
            risk_reward_ratio=2.5,
            metadata={"timeframe": "1h", "strength": "high"}
        )
    ]
    return mock_signals

@app.post("/orders",
          response_model=TradingOrder,
          summary="Create Trading Order",
          description="Place a new trading order on the specified exchange",
          tags=["Trading"],
          dependencies=[Depends(get_current_user)])
async def create_order(order: CreateOrderRequest = Body(..., description="Order details")):
    """Create a new trading order"""
    # Mock order creation - in production, integrate with exchange APIs
    new_order = TradingOrder(
        id=f"ord_{hash(str(order.dict()))}",
        symbol=order.symbol,
        side=order.side,
        type=order.type,
        quantity=order.quantity,
        price=order.price,
        status="pending",
        exchange=order.exchange
    )
    return new_order

@app.get("/orders",
         response_model=List[TradingOrder],
         summary="Get Trading Orders",
         description="Retrieve user's trading orders with optional filtering",
         tags=["Trading"],
         dependencies=[Depends(get_current_user)])
async def get_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    exchange: Optional[ExchangeEnum] = Query(None, description="Filter by exchange"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of orders", ge=1, le=200)
):
    """Get user's trading orders"""
    # Mock orders - in production, fetch from database
    mock_orders = [
        TradingOrder(
            id="ord_123456",
            symbol="BTC/USDT",
            side=OrderSideEnum.buy,
            type=OrderTypeEnum.limit,
            quantity=0.001,
            price=45000.0,
            filled_quantity=0.0005,
            status="partially_filled",
            exchange=ExchangeEnum.binance
        )
    ]
    return mock_orders

@app.get("/risk-metrics",
         response_model=RiskMetrics,
         summary="Get Risk Metrics",
         description="Retrieve current portfolio risk metrics and statistics",
         tags=["Risk Management"],
         dependencies=[Depends(get_current_user)])
async def get_risk_metrics():
    """Get portfolio risk metrics"""
    return RiskMetrics(
        portfolio_value=10000.0,
        daily_pnl=150.25,
        max_drawdown=2.5,
        sharpe_ratio=1.85,
        win_rate=65.5,
        risk_score=25.0,
        open_positions=3,
        leverage_ratio=2.0
    )

@app.post("/backtest",
          response_model=BacktestResult,
          summary="Run Strategy Backtest",
          description="Execute a backtest for a trading strategy with specified parameters",
          tags=["Strategy Testing"],
          dependencies=[Depends(get_current_user)])
async def run_backtest(request: BacktestRequest = Body(..., description="Backtest parameters")):
    """Run a strategy backtest"""
    # Mock backtest - in production, run actual backtest engine
    result = BacktestResult(
        strategy_name=request.strategy_name,
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        final_capital=request.initial_capital * 1.25,  # 25% return
        total_return=25.0,
        sharpe_ratio=1.85,
        max_drawdown=5.2,
        win_rate=68.5,
        total_trades=150,
        profitable_trades=103,
        avg_trade_duration=4.5
    )
    return result

# Custom OpenAPI schema with comprehensive documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_TITLE,
        version="1.0.0",
        description=API_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add comprehensive security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication. Obtain from /auth/login endpoint."
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication"
        }
    }
    
    # Add comprehensive response examples
    openapi_schema["components"]["examples"] = {
        "SuccessExample": {
            "summary": "Successful response",
            "value": {
                "success": True,
                "message": "Operation completed successfully",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        },
        "ValidationErrorExample": {
            "summary": "Validation error response",
            "value": {
                "success": False,
                "error": "Validation failed",
                "details": [
                    {
                        "field": "symbol",
                        "message": "Invalid trading symbol format",
                        "code": "invalid_format"
                    }
                ],
                "code": "VALIDATION_ERROR",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        },
        "AuthErrorExample": {
            "summary": "Authentication error response",
            "value": {
                "success": False,
                "error": "Authentication required",
                "details": "Valid JWT token must be provided in Authorization header",
                "code": "UNAUTHORIZED",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        },
        "RateLimitErrorExample": {
            "summary": "Rate limit exceeded response",
            "value": {
                "success": False,
                "error": "Rate limit exceeded",
                "details": "Too many requests, please try again later",
                "code": "RATE_LIMIT_EXCEEDED",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        },
        "ServerErrorExample": {
            "summary": "Internal server error response",
            "value": {
                "success": False,
                "error": "Internal server error",
                "details": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        }
    }
    
    # Add custom headers for responses
    openapi_schema["components"]["headers"] = {
        "X-RateLimit-Limit": {
            "description": "Request limit per time window",
            "schema": {"type": "integer", "example": 100}
        },
        "X-RateLimit-Remaining": {
            "description": "Remaining requests in current window",
            "schema": {"type": "integer", "example": 95}
        },
        "X-RateLimit-Reset": {
            "description": "Time when rate limit resets (Unix timestamp)",
            "schema": {"type": "integer", "example": 1705312800}
        },
        "X-API-Version": {
            "description": "API version used for this request",
            "schema": {"type": "string", "example": "v1"}
        }
    }
    
    # Add external documentation links
    openapi_schema["externalDocs"] = {
        "description": "SMC Trading Agent Documentation",
        "url": "https://docs.smctradingagent.com"
    }
    
    # Add webhook information for future use
    openapi_schema["webhooks"] = {
        "tradeExecuted": {
            "post": {
                "requestBody": {
                    "description": "Trade execution notification",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "event": {"type": "string", "example": "trade.executed"},
                                    "data": {"$ref": "#/components/schemas/TradingOrder"},
                                    "timestamp": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Webhook received successfully"
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom documentation endpoints
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/api/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
    )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=f"HTTP_{exc.status_code}"
        ).dict()
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=str(exc),
            code="VALIDATION_ERROR"
        ).dict()
    )

if __name__ == "__main__":
    uvicorn.run(
        "api_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("NODE_ENV") == "development" else False,
        log_level="info"
    )