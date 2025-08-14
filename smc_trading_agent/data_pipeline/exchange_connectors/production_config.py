"""
Production Exchange Configuration Management

Handles production API configurations, credentials management, and environment-specific settings
for all supported exchanges (Binance, Bybit, Oanda).
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types for exchange configurations."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTNET = "testnet"


class ExchangeType(Enum):
    """Supported exchange types."""
    BINANCE = "binance"
    BYBIT = "bybit"
    OANDA = "oanda"


@dataclass
class ExchangeCredentials:
    """Exchange API credentials."""
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # For exchanges that require passphrase
    account_id: Optional[str] = None  # For OANDA
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required")


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 1200
    requests_per_second: int = 20
    burst_limit: int = 50
    backoff_factor: float = 1.5
    max_backoff_time: int = 300  # 5 minutes
    
    def __post_init__(self):
        """Validate rate limit configuration."""
        if self.requests_per_minute <= 0 or self.requests_per_second <= 0:
            raise ValueError("Rate limits must be positive")


@dataclass
class ExchangeEndpoints:
    """Exchange API endpoints configuration."""
    rest_url: str
    websocket_url: str
    testnet_rest_url: Optional[str] = None
    testnet_websocket_url: Optional[str] = None
    
    def get_rest_url(self, testnet: bool = False) -> str:
        """Get REST URL based on environment."""
        if testnet and self.testnet_rest_url:
            return self.testnet_rest_url
        return self.rest_url
    
    def get_websocket_url(self, testnet: bool = False) -> str:
        """Get WebSocket URL based on environment."""
        if testnet and self.testnet_websocket_url:
            return self.testnet_websocket_url
        return self.websocket_url


@dataclass
class ExchangeConfig:
    """Complete exchange configuration."""
    exchange_type: ExchangeType
    environment: Environment
    credentials: ExchangeCredentials
    endpoints: ExchangeEndpoints
    rate_limits: RateLimitConfig
    enabled: bool = True
    testnet: bool = False
    symbols: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=lambda: ["trade", "orderbook", "kline"])
    connection_timeout: int = 30
    read_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.symbols:
            logger.warning(f"No symbols configured for {self.exchange_type.value}")


class ProductionConfigManager:
    """
    Manages production configurations for all exchanges.
    
    Handles environment-specific settings, credential management,
    and configuration validation.
    """
    
    # Production endpoints for each exchange
    EXCHANGE_ENDPOINTS = {
        ExchangeType.BINANCE: ExchangeEndpoints(
            rest_url="https://api.binance.com",
            websocket_url="wss://stream.binance.com:9443/ws/",
            testnet_rest_url="https://testnet.binance.vision",
            testnet_websocket_url="wss://testnet.binance.vision/ws/"
        ),
        ExchangeType.BYBIT: ExchangeEndpoints(
            rest_url="https://api.bybit.com",
            websocket_url="wss://stream.bybit.com/v5/public/spot",
            testnet_rest_url="https://api-testnet.bybit.com",
            testnet_websocket_url="wss://stream-testnet.bybit.com/v5/public/spot"
        ),
        ExchangeType.OANDA: ExchangeEndpoints(
            rest_url="https://api-fxtrade.oanda.com/v3",
            websocket_url="wss://stream-fxtrade.oanda.com/v3/accounts/{account_id}/pricing/stream",
            testnet_rest_url="https://api-fxpractice.oanda.com/v3",
            testnet_websocket_url="wss://stream-fxpractice.oanda.com/v3/accounts/{account_id}/pricing/stream"
        )
    }
    
    # Default rate limits for each exchange
    DEFAULT_RATE_LIMITS = {
        ExchangeType.BINANCE: RateLimitConfig(
            requests_per_minute=1200,
            requests_per_second=20,
            burst_limit=50
        ),
        ExchangeType.BYBIT: RateLimitConfig(
            requests_per_minute=7200,  # 120 per second
            requests_per_second=120,
            burst_limit=200
        ),
        ExchangeType.OANDA: RateLimitConfig(
            requests_per_minute=7200,  # 120 per second
            requests_per_second=120,
            burst_limit=150
        )
    }
    
    # Default symbols for each exchange
    DEFAULT_SYMBOLS = {
        ExchangeType.BINANCE: ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
        ExchangeType.BYBIT: ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
        ExchangeType.OANDA: ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD"]
    }
    
    def __init__(self, environment: Environment = Environment.PRODUCTION):
        """
        Initialize production config manager.
        
        Args:
            environment: Target environment (production, staging, testnet)
        """
        self.environment = environment
        self.configs: Dict[ExchangeType, ExchangeConfig] = {}
        self._load_configurations()
    
    def _load_configurations(self):
        """Load configurations for all exchanges."""
        for exchange_type in ExchangeType:
            try:
                config = self._create_exchange_config(exchange_type)
                if config:
                    self.configs[exchange_type] = config
                    logger.info(f"Loaded {exchange_type.value} configuration for {self.environment.value}")
            except Exception as e:
                logger.error(f"Failed to load {exchange_type.value} configuration: {e}")
    
    def _create_exchange_config(self, exchange_type: ExchangeType) -> Optional[ExchangeConfig]:
        """
        Create exchange configuration from environment variables.
        
        Args:
            exchange_type: Type of exchange to configure
            
        Returns:
            ExchangeConfig: Complete exchange configuration or None if credentials missing
        """
        try:
            # Load credentials from environment variables
            credentials = self._load_credentials(exchange_type)
            if not credentials:
                logger.warning(f"No credentials found for {exchange_type.value}")
                return None
            
            # Get endpoints
            endpoints = self.EXCHANGE_ENDPOINTS[exchange_type]
            
            # Get rate limits
            rate_limits = self.DEFAULT_RATE_LIMITS[exchange_type]
            
            # Get symbols
            symbols = self._get_symbols_for_exchange(exchange_type)
            
            # Determine if testnet should be used
            testnet = self.environment == Environment.TESTNET
            
            return ExchangeConfig(
                exchange_type=exchange_type,
                environment=self.environment,
                credentials=credentials,
                endpoints=endpoints,
                rate_limits=rate_limits,
                enabled=True,
                testnet=testnet,
                symbols=symbols
            )
            
        except Exception as e:
            logger.error(f"Failed to create {exchange_type.value} configuration: {e}")
            return None
    
    def _load_credentials(self, exchange_type: ExchangeType) -> Optional[ExchangeCredentials]:
        """
        Load credentials from environment variables.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            ExchangeCredentials: Loaded credentials or None if missing
        """
        exchange_name = exchange_type.value.upper()
        
        # Standard environment variable names
        api_key_var = f"{exchange_name}_API_KEY"
        api_secret_var = f"{exchange_name}_API_SECRET"
        
        # Get API key and secret
        api_key = os.getenv(api_key_var)
        api_secret = os.getenv(api_secret_var)
        
        if not api_key or not api_secret:
            logger.warning(f"Missing credentials for {exchange_type.value}: {api_key_var}, {api_secret_var}")
            return None
        
        # Exchange-specific additional credentials
        additional_creds = {}
        
        if exchange_type == ExchangeType.OANDA:
            account_id = os.getenv(f"{exchange_name}_ACCOUNT_ID")
            if account_id:
                additional_creds["account_id"] = account_id
            else:
                logger.warning(f"Missing OANDA account ID: {exchange_name}_ACCOUNT_ID")
                return None
        
        try:
            return ExchangeCredentials(
                api_key=api_key,
                api_secret=api_secret,
                **additional_creds
            )
        except ValueError as e:
            logger.error(f"Invalid credentials for {exchange_type.value}: {e}")
            return None
    
    def _get_symbols_for_exchange(self, exchange_type: ExchangeType) -> List[str]:
        """
        Get symbols for exchange from environment or defaults.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            List[str]: List of symbols to trade
        """
        exchange_name = exchange_type.value.upper()
        symbols_var = f"{exchange_name}_SYMBOLS"
        
        # Try to get from environment variable
        symbols_str = os.getenv(symbols_var)
        if symbols_str:
            try:
                # Parse as JSON array or comma-separated string
                if symbols_str.startswith('['):
                    symbols = json.loads(symbols_str)
                else:
                    symbols = [s.strip() for s in symbols_str.split(',')]
                
                if symbols:
                    return symbols
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid symbols format for {exchange_type.value}: {e}")
        
        # Return default symbols
        return self.DEFAULT_SYMBOLS[exchange_type]
    
    def get_config(self, exchange_type: ExchangeType) -> Optional[ExchangeConfig]:
        """
        Get configuration for specific exchange.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            ExchangeConfig: Exchange configuration or None if not available
        """
        return self.configs.get(exchange_type)
    
    def get_all_configs(self) -> Dict[ExchangeType, ExchangeConfig]:
        """
        Get all loaded exchange configurations.
        
        Returns:
            Dict[ExchangeType, ExchangeConfig]: All configurations
        """
        return self.configs.copy()
    
    def is_exchange_enabled(self, exchange_type: ExchangeType) -> bool:
        """
        Check if exchange is enabled and configured.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            bool: True if exchange is enabled and configured
        """
        config = self.configs.get(exchange_type)
        return config is not None and config.enabled
    
    def validate_configuration(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """
        Validate exchange configuration.
        
        Args:
            exchange_type: Type of exchange to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        config = self.configs.get(exchange_type)
        if not config:
            return {
                "valid": False,
                "errors": ["Configuration not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Validate credentials
        try:
            if not config.credentials.api_key:
                errors.append("API key is empty")
            if not config.credentials.api_secret:
                errors.append("API secret is empty")
            if exchange_type == ExchangeType.OANDA and not config.credentials.account_id:
                errors.append("OANDA account ID is required")
        except Exception as e:
            errors.append(f"Credential validation error: {e}")
        
        # Validate endpoints
        try:
            if not config.endpoints.rest_url:
                errors.append("REST URL is empty")
            if not config.endpoints.websocket_url:
                errors.append("WebSocket URL is empty")
        except Exception as e:
            errors.append(f"Endpoint validation error: {e}")
        
        # Validate symbols
        if not config.symbols:
            warnings.append("No symbols configured")
        
        # Validate rate limits
        if config.rate_limits.requests_per_minute <= 0:
            errors.append("Invalid rate limit configuration")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def update_credentials(self, exchange_type: ExchangeType, credentials: ExchangeCredentials):
        """
        Update credentials for specific exchange.
        
        Args:
            exchange_type: Type of exchange
            credentials: New credentials
        """
        config = self.configs.get(exchange_type)
        if config:
            config.credentials = credentials
            logger.info(f"Updated credentials for {exchange_type.value}")
        else:
            logger.error(f"Cannot update credentials - no configuration for {exchange_type.value}")
    
    def rotate_api_keys(self, exchange_type: ExchangeType, new_api_key: str, new_api_secret: str):
        """
        Rotate API keys for specific exchange.
        
        Args:
            exchange_type: Type of exchange
            new_api_key: New API key
            new_api_secret: New API secret
        """
        config = self.configs.get(exchange_type)
        if config:
            old_key = config.credentials.api_key[:8] + "..."  # Log partial key for audit
            config.credentials.api_key = new_api_key
            config.credentials.api_secret = new_api_secret
            logger.info(f"Rotated API keys for {exchange_type.value} (old key: {old_key})")
        else:
            logger.error(f"Cannot rotate keys - no configuration for {exchange_type.value}")
    
    def export_config_template(self, file_path: str):
        """
        Export configuration template with environment variables.
        
        Args:
            file_path: Path to save template file
        """
        template = {
            "environment_variables": {
                "# Binance Configuration": "",
                "BINANCE_API_KEY": "your_binance_api_key_here",
                "BINANCE_API_SECRET": "your_binance_api_secret_here",
                "BINANCE_SYMBOLS": '["BTCUSDT", "ETHUSDT", "ADAUSDT"]',
                
                "# Bybit Configuration": "",
                "BYBIT_API_KEY": "your_bybit_api_key_here",
                "BYBIT_API_SECRET": "your_bybit_api_secret_here",
                "BYBIT_SYMBOLS": '["BTCUSDT", "ETHUSDT", "ADAUSDT"]',
                
                "# OANDA Configuration": "",
                "OANDA_API_KEY": "your_oanda_api_key_here",
                "OANDA_API_SECRET": "your_oanda_api_secret_here",
                "OANDA_ACCOUNT_ID": "your_oanda_account_id_here",
                "OANDA_SYMBOLS": '["EUR_USD", "GBP_USD", "USD_JPY"]'
            },
            "notes": [
                "Set these environment variables before starting the application",
                "For production, use a secure secrets management system",
                "Testnet/sandbox credentials should be used for testing",
                "Symbols can be JSON array or comma-separated string"
            ]
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(template, f, indent=2)
            logger.info(f"Configuration template exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export configuration template: {e}")


def create_production_config(environment: Environment = Environment.PRODUCTION) -> ProductionConfigManager:
    """
    Create production configuration manager.
    
    Args:
        environment: Target environment
        
    Returns:
        ProductionConfigManager: Configured manager instance
    """
    return ProductionConfigManager(environment)


def validate_all_configurations(config_manager: ProductionConfigManager) -> Dict[str, Any]:
    """
    Validate all exchange configurations.
    
    Args:
        config_manager: Configuration manager instance
        
    Returns:
        Dict[str, Any]: Validation results for all exchanges
    """
    results = {}
    
    for exchange_type in ExchangeType:
        results[exchange_type.value] = config_manager.validate_configuration(exchange_type)
    
    return results