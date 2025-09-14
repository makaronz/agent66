"""
Pydantic models for comprehensive input validation in Python backend
Provides type-safe validation for all API endpoints and data processing
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator, EmailStr, constr, conint, confloat
import re


class ExchangeEnum(str, Enum):
    """Supported exchanges"""
    BINANCE = "binance"
    BYBIT = "bybit"
    OANDA = "oanda"


class OrderSideEnum(str, Enum):
    """Order side types"""
    BUY = "buy"
    SELL = "sell"


class OrderTypeEnum(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TimeInForceEnum(str, Enum):
    """Time in force options"""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill


class IntervalEnum(str, Enum):
    """Timeframe intervals"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


# Base validation models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: conint(ge=1) = 1
    limit: conint(ge=1, le=100) = 20
    sort: Optional[constr(max_length=50)] = None
    order: str = Field(default="desc", regex="^(asc|desc)$")


# Authentication models
class UserRegistration(BaseModel):
    """User registration model"""
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    full_name: Optional[constr(min_length=2, max_length=100, regex="^[a-zA-Z\\s'-]+$")] = None
    terms_accepted: bool

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]', v):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one number, and one special character'
            )
        return v

    @validator('terms_accepted')
    def validate_terms(cls, v):
        """Ensure terms are accepted"""
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: constr(min_length=1, max_length=128)


class ChangePassword(BaseModel):
    """Change password model"""
    current_password: str
    new_password: constr(min_length=8, max_length=128)
    confirm_password: str

    @validator('new_password')
    def validate_new_password_strength(cls, v):
        """Validate new password strength"""
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]', v):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one number, and one special character'
            )
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# User profile models
class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_alerts: bool = True
    push_notifications: bool = True
    trading_alerts: bool = True


class UpdateProfile(BaseModel):
    """Update user profile model"""
    full_name: Optional[constr(min_length=2, max_length=100, regex="^[a-zA-Z\\s'-]+$")] = None
    avatar_url: Optional[str] = None
    timezone: Optional[constr(max_length=50)] = None
    notification_preferences: Optional[NotificationPreferences] = None

    @validator('avatar_url')
    def validate_avatar_url(cls, v):
        """Validate avatar URL"""
        if v and not re.match(r'^https?://.+\.(jpg|jpeg|png|gif|webp)$', v, re.IGNORECASE):
            raise ValueError('Avatar URL must be a valid image URL')
        return v


# API key management models
class ApiKeyStorage(BaseModel):
    """API key storage model"""
    exchange: ExchangeEnum
    api_key: constr(min_length=10, max_length=256, regex="^[A-Za-z0-9_-]+$")
    secret: constr(min_length=10, max_length=512, regex="^[A-Za-z0-9+/=_-]+$")
    is_testnet: bool = True
    label: Optional[constr(min_length=1, max_length=50, regex="^[a-zA-Z0-9\\s_-]+$")] = None


class TestConnection(BaseModel):
    """Test exchange connection model"""
    api_key: constr(min_length=10, max_length=256, regex="^[A-Za-z0-9_-]+$")
    secret: constr(min_length=10, max_length=512, regex="^[A-Za-z0-9+/=_-]+$")
    sandbox: bool = True
    save_keys: bool = False
    exchange: Optional[ExchangeEnum] = None


# Trading models
class PlaceOrder(BaseModel):
    """Place trading order model"""
    symbol: constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")
    side: OrderSideEnum
    type: OrderTypeEnum
    quantity: confloat(gt=0, le=1000000)
    price: Optional[confloat(gt=0, le=1000000)] = None
    stop_loss: Optional[confloat(gt=0, le=1000000)] = None
    take_profit: Optional[confloat(gt=0, le=1000000)] = None
    time_in_force: TimeInForceEnum = TimeInForceEnum.GTC
    client_order_id: Optional[constr(max_length=36, regex="^[a-zA-Z0-9_-]+$")] = None

    @validator('symbol')
    def normalize_symbol(cls, v):
        """Normalize symbol to uppercase"""
        return v.upper()

    @validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        """Require price for limit orders"""
        if values.get('type') == OrderTypeEnum.LIMIT and not v:
            raise ValueError('Price is required for limit orders')
        return v

    @validator('stop_loss')
    def validate_stop_loss(cls, v, values):
        """Validate stop loss logic"""
        if v and 'price' in values and 'side' in values and values['price']:
            if values['side'] == OrderSideEnum.BUY and v >= values['price']:
                raise ValueError('Stop loss must be below entry price for buy orders')
            elif values['side'] == OrderSideEnum.SELL and v <= values['price']:
                raise ValueError('Stop loss must be above entry price for sell orders')
        return v

    @validator('take_profit')
    def validate_take_profit(cls, v, values):
        """Validate take profit logic"""
        if v and 'price' in values and 'side' in values and values['price']:
            if values['side'] == OrderSideEnum.BUY and v <= values['price']:
                raise ValueError('Take profit must be above entry price for buy orders')
            elif values['side'] == OrderSideEnum.SELL and v >= values['price']:
                raise ValueError('Take profit must be below entry price for sell orders')
        return v


class CancelOrder(BaseModel):
    """Cancel order model"""
    order_id: str = Field(min_length=1)
    symbol: constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")
    client_order_id: Optional[str] = None

    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper()


class OrderHistory(BaseModel):
    """Order history query model"""
    symbol: Optional[constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")] = None
    start_time: Optional[conint(gt=0)] = None
    end_time: Optional[conint(gt=0)] = None
    limit: conint(ge=1, le=1000) = 100
    offset: conint(ge=0) = 0

    @validator('symbol')
    def normalize_symbol(cls, v):
        if v:
            return v.upper()
        return v

    @validator('end_time')
    def validate_time_range(cls, v, values):
        """Ensure end time is after start time"""
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


# Market data models
class MarketDataRequest(BaseModel):
    """Market data request model"""
    symbol: constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")
    interval: IntervalEnum = IntervalEnum.ONE_HOUR
    limit: conint(ge=1, le=1000) = 100
    start_time: Optional[conint(gt=0)] = None
    end_time: Optional[conint(gt=0)] = None

    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper()

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class TickerRequest(BaseModel):
    """Ticker data request model"""
    symbol: Optional[constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")] = None

    @validator('symbol')
    def normalize_symbol(cls, v):
        if v:
            return v.upper()
        return v


# Configuration models
class RiskManagementConfig(BaseModel):
    """Risk management configuration"""
    max_position_size: confloat(gt=0)
    max_daily_loss: confloat(gt=0)
    max_drawdown: confloat(ge=0, le=100)
    stop_loss_percentage: Optional[confloat(ge=0, le=100)] = None
    take_profit_percentage: Optional[confloat(ge=0, le=100)] = None


class TradingParameters(BaseModel):
    """Trading parameters configuration"""
    symbols: List[constr(min_length=3, max_length=20, regex="^[A-Z0-9/_-]+$")] = Field(min_items=1)
    timeframes: List[IntervalEnum] = Field(min_items=1)
    max_concurrent_trades: conint(ge=1, le=100)
    min_confidence_threshold: confloat(ge=0, le=100)

    @validator('symbols')
    def normalize_symbols(cls, v):
        return [symbol.upper() for symbol in v]


class SMCSettings(BaseModel):
    """Smart Money Concepts settings"""
    detect_order_blocks: bool = True
    detect_liquidity_zones: bool = True
    detect_fair_value_gaps: bool = True
    min_volume_threshold: Optional[confloat(gt=0)] = None
    confidence_threshold: confloat(ge=0, le=100) = 70.0


class TradingConfiguration(BaseModel):
    """Complete trading configuration"""
    risk_management: Optional[RiskManagementConfig] = None
    trading_parameters: Optional[TradingParameters] = None
    smc_settings: Optional[SMCSettings] = None


class SaveConfiguration(BaseModel):
    """Save configuration model"""
    config_name: constr(min_length=1, max_length=50, regex="^[a-zA-Z0-9\\s_-]+$")
    config: TradingConfiguration


# MFA models
class SetupTOTP(BaseModel):
    """Setup TOTP model"""
    secret: constr(min_length=16)
    token: constr(min_length=6, max_length=6, regex="^\\d{6}$")


class VerifyTOTP(BaseModel):
    """Verify TOTP model"""
    token: constr(min_length=6, max_length=6, regex="^\\d{6}$")


class SetupSMS(BaseModel):
    """Setup SMS MFA model"""
    phone_number: constr(regex="^\\+[1-9]\\d{1,14}$")

    @validator('phone_number')
    def validate_phone_length(cls, v):
        """Validate phone number length"""
        digits = re.sub(r'[^\d]', '', v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError('Phone number must be between 10 and 15 digits')
        return v


class VerifySMS(BaseModel):
    """Verify SMS code model"""
    phone_number: constr(regex="^\\+[1-9]\\d{1,14}$")
    code: constr(min_length=6, max_length=6, regex="^\\d{6}$")


# WebAuthn models
class WebAuthnCredentialResponse(BaseModel):
    """WebAuthn credential response"""
    attestation_object: str = Field(min_length=1)
    client_data_json: str = Field(min_length=1)


class WebAuthnCredential(BaseModel):
    """WebAuthn credential"""
    id: str = Field(min_length=1)
    raw_id: str = Field(min_length=1)
    response: WebAuthnCredentialResponse
    type: str = Field(regex="^public-key$")


class WebAuthnRegistration(BaseModel):
    """WebAuthn registration model"""
    credential: WebAuthnCredential
    name: constr(min_length=1, max_length=50)


class WebAuthnAuthResponse(BaseModel):
    """WebAuthn authentication response"""
    authenticator_data: str = Field(min_length=1)
    client_data_json: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    user_handle: Optional[str] = None


class WebAuthnAuthCredential(BaseModel):
    """WebAuthn authentication credential"""
    id: str = Field(min_length=1)
    raw_id: str = Field(min_length=1)
    response: WebAuthnAuthResponse
    type: str = Field(regex="^public-key$")


class WebAuthnAuthentication(BaseModel):
    """WebAuthn authentication model"""
    credential: WebAuthnAuthCredential


# Data pipeline models
class MarketDataPoint(BaseModel):
    """Market data point model"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    exchange: ExchangeEnum


class SMCSignal(BaseModel):
    """SMC signal model"""
    symbol: str
    signal_type: str
    direction: OrderSideEnum
    confidence: confloat(ge=0, le=100)
    price_level: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None


class TradingDecision(BaseModel):
    """Trading decision model"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    confidence: confloat(ge=0, le=100)
    reasoning: str
    risk_score: confloat(ge=0, le=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Response models
class OrderResponse(BaseResponse):
    """Order response model"""
    data: Optional[Dict[str, Any]] = None


class MarketDataResponse(BaseResponse):
    """Market data response model"""
    data: Optional[Dict[str, Any]] = None


class ConfigurationResponse(BaseResponse):
    """Configuration response model"""
    data: Optional[Dict[str, Any]] = None


class UserResponse(BaseResponse):
    """User response model"""
    data: Optional[Dict[str, Any]] = None


# Health check model
class HealthCheck(BaseModel):
    """Health check model"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime: float
    memory_usage: Dict[str, int]
    version: str
    environment: str
    services: Optional[Dict[str, str]] = None