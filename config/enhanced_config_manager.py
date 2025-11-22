#!/usr/bin/env python3
"""
Enhanced Configuration Manager with Environment Variable Support

Provides comprehensive configuration management with:
- Environment variable substitution
- Configuration validation
- Hot reloading capabilities
- Multiple configuration sources
- Type safety and validation
- Configuration versioning
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union, List, Type, TypeVar, Callable
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging
from enum import Enum
import re
from pydantic import BaseModel, ValidationError, validator
import threading
import time

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ConfigEnvironment(Enum):
    """Supported deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigFormat(Enum):
    """Supported configuration file formats"""
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"


@dataclass
class ConfigSource:
    """Configuration source definition"""
    name: str
    path: Path
    format: ConfigFormat
    required: bool = True
    priority: int = 100
    last_modified: Optional[float] = None


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


class ConfigValidationError(ConfigurationError):
    """Configuration validation errors"""
    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file not found error"""
    pass


class EnvironmentVariableSubstitutor:
    """Advanced environment variable substitution"""

    SUBSTITUTION_PATTERN = re.compile(r'\$\{([^}]+)\}')

    @classmethod
    def substitute(cls, value: Any, context: Dict[str, Any] = None) -> Any:
        """
        Recursively substitute environment variables in configuration values.

        Supports patterns:
        - ${VAR_NAME} - Simple substitution
        - ${VAR_NAME:default_value} - With default
        - ${VAR_NAME:?error_message} - Required with error message
        """
        if not isinstance(value, (str, bytes)):
            if isinstance(value, dict):
                return {k: cls.substitute(v, context) for k, v in value.items()}
            elif isinstance(value, list):
                return [cls.substitute(item, context) for item in value]
            return value

        if isinstance(value, bytes):
            value = value.decode('utf-8')

        def replace_var(match):
            var_expr = match.group(1)

            # Parse variable expression
            if ':' in var_expr:
                var_name, default = var_expr.split(':', 1)
                if default.startswith('?'):
                    # Required variable with error message
                    error_msg = default[1:]
                    if var_name not in os.environ:
                        raise ConfigValidationError(
                            f"Required environment variable '{var_name}' not set: {error_msg}"
                        )
                else:
                    # Variable with default value
                    return os.environ.get(var_name, default)
            else:
                # Simple variable substitution
                return os.environ.get(var_expr, '')

            return os.environ[var_name]

        # Apply substitutions
        result = cls.SUBSTITUTION_PATTERN.sub(replace_var, value)

        # Handle numeric conversions
        try:
            if '.' in result:
                return float(result)
            elif result.isdigit():
                return int(result)
            elif result.lower() in ('true', 'false'):
                return result.lower() == 'true'
        except ValueError:
            pass

        # Handle boolean strings
        if result.lower() in ('null', 'none'):
            return None

        return result


class ConfigurationValidator:
    """Configuration validation using Pydantic models"""

    @staticmethod
    def validate(config_data: Dict[str, Any], model_class: Type[T]) -> T:
        """Validate configuration data against a Pydantic model"""
        try:
            return model_class(**config_data)
        except ValidationError as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")

    @staticmethod
    def validate_section(section_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration section against custom schema"""
        errors = []

        for key, rules in schema.items():
            if key not in section_data:
                if rules.get('required', False):
                    errors.append(f"Required field '{key}' is missing")
                continue

            value = section_data[key]
            expected_type = rules.get('type')

            if expected_type and not isinstance(value, expected_type):
                errors.append(f"Field '{key}' must be of type {expected_type.__name__}")

            # Custom validation rules
            if 'validator' in rules:
                try:
                    rules['validator'](value)
                except Exception as e:
                    errors.append(f"Field '{key}' validation failed: {e}")

        if errors:
            raise ConfigValidationError(f"Validation errors: {'; '.join(errors)}")

        return section_data


# Configuration Models with Pydantic for type safety

class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    name: str
    username: str
    password: str
    ssl_mode: str = "require"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600

    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class RedisConfig(BaseModel):
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


class ExchangeConfig(BaseModel):
    """Exchange API configuration"""
    api_key: str
    api_secret: str
    sandbox: bool = False
    timeout: int = 30
    rate_limit: int = 1200
    testnet: bool = False

    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        if v <= 0:
            raise ValueError('Rate limit must be positive')
        return v


class RiskConfig(BaseModel):
    """Risk management configuration"""
    max_position_size: float = 1000.0
    max_portfolio_risk: float = 0.02
    max_daily_loss: float = 500.0
    max_drawdown: float = 0.15
    min_risk_reward: float = 1.5
    max_leverage: float = 3.0
    var_limit: float = 0.05
    stress_test_loss: float = 0.10
    position_sizing_method: str = "adaptive"
    stop_loss_method: str = "adaptive"

    @validator('max_portfolio_risk', 'max_drawdown', 'var_limit', 'stress_test_loss')
    def validate_percentages(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Percentage values must be between 0 and 1')
        return v


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = True
    prometheus_port: int = 8000
    grafana_port: int = 3000
    health_check_interval: int = 30
    metrics_collection_interval: int = 60
    alert_error_rate: float = 0.1
    alert_circuit_breaker_rate: float = 0.2
    alert_avg_response_time: int = 5000
    alert_critical_error_rate: float = 0.05
    log_level: str = "INFO"


class TradingConfig(BaseModel):
    """Trading system configuration"""
    symbols: List[str]
    timeframe: str = "1h"
    max_concurrent_positions: int = 5
    order_timeout: int = 30
    slippage_tolerance: float = 0.001
    execution_delay_tolerance: float = 0.05  # 50ms

    @validator('symbols')
    def validate_symbols(cls, v):
        if not v:
            raise ValueError('At least one trading symbol must be specified')
        return v


class EnhancedConfig(BaseModel):
    """Main enhanced configuration model"""
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Sub-configurations
    database: DatabaseConfig
    redis: RedisConfig
    exchanges: Dict[str, ExchangeConfig]
    risk: RiskConfig
    monitoring: MonitoringConfig
    trading: TradingConfig

    # Advanced settings
    features: Dict[str, bool] = field(default_factory=dict)
    experimental: Dict[str, Any] = field(default_factory=dict)

    @validator('environment')
    def validate_environment(cls, v):
        if v not in [env.value for env in ConfigEnvironment]:
            raise ValueError(f'Environment must be one of {[env.value for env in ConfigEnvironment]}')
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()


class EnhancedConfigManager:
    """Enhanced configuration manager with advanced features"""

    def __init__(self, config_dir: Optional[Union[str, Path]] = None,
                 environment: Optional[str] = None,
                 auto_reload: bool = False,
                 reload_interval: int = 60):
        """
        Initialize enhanced configuration manager.

        Args:
            config_dir: Directory containing configuration files
            environment: Target environment (auto-detected if not provided)
            auto_reload: Enable hot reloading of configuration
            reload_interval: Reload check interval in seconds
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.environment = environment or self._detect_environment()
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval

        self._config: Optional[EnhancedConfig] = None
        self._config_sources: List[ConfigSource] = []
        self._last_load_time: Optional[float] = None
        self._reload_thread: Optional[threading.Thread] = None
        self._stop_reload = threading.Event()

        # Setup default configuration sources
        self._setup_default_sources()

        # Start auto-reload if enabled
        if self.auto_reload:
            self._start_auto_reload()

    def _detect_environment(self) -> str:
        """Auto-detect current environment"""
        env = os.environ.get('ENVIRONMENT', os.environ.get('ENV', 'development'))

        # Validate environment
        try:
            ConfigEnvironment(env.lower())
            return env.lower()
        except ValueError:
            logger.warning(f"Invalid environment '{env}', defaulting to 'development'")
            return "development"

    def _setup_default_sources(self):
        """Setup default configuration sources"""
        # Base configuration
        self.add_config_source(
            name="base",
            path=self.config_dir / "base.yaml",
            format=ConfigFormat.YAML,
            required=False,
            priority=100
        )

        # Environment-specific configuration
        self.add_config_source(
            name=f"env_{self.environment}",
            path=self.config_dir / f"{self.environment}.yaml",
            format=ConfigFormat.YAML,
            required=False,
            priority=200
        )

        # Local overrides
        self.add_config_source(
            name="local",
            path=self.config_dir / "local.yaml",
            format=ConfigFormat.YAML,
            required=False,
            priority=300
        )

        # Secrets configuration (should not be committed)
        self.add_config_source(
            name="secrets",
            path=self.config_dir / "secrets.yaml",
            format=ConfigFormat.YAML,
            required=False,
            priority=400
        )

    def add_config_source(self, name: str, path: Path, format: ConfigFormat,
                          required: bool = True, priority: int = 100):
        """Add a configuration source"""
        source = ConfigSource(
            name=name,
            path=path,
            format=format,
            required=required,
            priority=priority
        )
        self._config_sources.append(source)

        # Sort by priority (lower priority = applied first)
        self._config_sources.sort(key=lambda x: x.priority)

    def load_config(self) -> EnhancedConfig:
        """Load and merge configuration from all sources"""
        merged_config = {}

        for source in self._config_sources:
            if not source.path.exists():
                if source.required:
                    raise ConfigFileNotFoundError(f"Required config file not found: {source.path}")
                logger.debug(f"Optional config file not found: {source.path}")
                continue

            try:
                config_data = self._load_config_file(source)
                merged_config = self._deep_merge(merged_config, config_data)
                source.last_modified = source.path.stat().st_mtime
                logger.debug(f"Loaded configuration from: {source.path}")
            except Exception as e:
                if source.required:
                    raise ConfigurationError(f"Failed to load required config {source.path}: {e}")
                logger.warning(f"Failed to load optional config {source.path}: {e}")

        # Apply environment variable substitution
        merged_config = EnvironmentVariableSubstitutor.substitute(merged_config)

        # Validate configuration
        try:
            self._config = EnhancedConfig(**merged_config)
            self._last_load_time = time.time()
            logger.info(f"Configuration loaded successfully for environment: {self.environment}")
            return self._config
        except ValidationError as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")

    def _load_config_file(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from a specific file"""
        with open(source.path, 'r', encoding='utf-8') as f:
            if source.format == ConfigFormat.YAML:
                return yaml.safe_load(f) or {}
            elif source.format == ConfigFormat.JSON:
                return json.load(f) or {}
            else:
                raise ConfigurationError(f"Unsupported format: {source.format}")

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get_config(self) -> EnhancedConfig:
        """Get current configuration, loading if necessary"""
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> bool:
        """Reload configuration if any sources have changed"""
        changed = False

        for source in self._config_sources:
            if not source.path.exists():
                continue

            current_mtime = source.path.stat().st_mtime
            if source.last_modified and current_mtime > source.last_modified:
                changed = True
                break

        if changed:
            logger.info("Configuration change detected, reloading...")
            self.load_config()
            return True

        return False

    def _start_auto_reload(self):
        """Start auto-reload background thread"""
        self._reload_thread = threading.Thread(target=self._auto_reload_worker, daemon=True)
        self._reload_thread.start()
        logger.debug("Auto-reload thread started")

    def _auto_reload_worker(self):
        """Background worker for auto-reload"""
        while not self._stop_reload.wait(self.reload_interval):
            try:
                self.reload_config()
            except Exception as e:
                logger.error(f"Error during auto-reload: {e}")

    def stop_auto_reload(self):
        """Stop auto-reload background thread"""
        if self._reload_thread:
            self._stop_reload.set()
            self._reload_thread.join(timeout=5)
            logger.debug("Auto-reload thread stopped")

    def get_section(self, section_name: str) -> Any:
        """Get a specific configuration section"""
        config = self.get_config()
        return getattr(config, section_name, None)

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value using dot notation.

        Example: get_value("database.port") -> database port
        """
        config = self.get_config()
        keys = key_path.split('.')

        current = config
        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set_value(self, key_path: str, value: Any):
        """Set a configuration value using dot notation (runtime only)"""
        if self._config is None:
            self.load_config()

        keys = key_path.split('.')
        current = self._config

        # Navigate to parent
        for key in keys[:-1]:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict):
                current = current
            else:
                raise ConfigurationError(f"Invalid configuration path: {key_path}")

        # Set the value
        final_key = keys[-1]
        if hasattr(current, final_key):
            setattr(current, final_key, value)
        elif isinstance(current, dict):
            current[final_key] = value
        else:
            raise ConfigurationError(f"Invalid configuration path: {key_path}")

    def export_config(self, format: str = "yaml", include_secrets: bool = False) -> str:
        """Export current configuration to string"""
        config = self.get_config()
        config_dict = asdict(config)

        # Remove secrets if requested
        if not include_secrets:
            self._remove_secrets(config_dict)

        if format.lower() == "yaml":
            return yaml.dump(config_dict, default_flow_style=False, indent=2)
        elif format.lower() == "json":
            return json.dumps(config_dict, indent=2)
        else:
            raise ConfigurationError(f"Unsupported export format: {format}")

    def _remove_secrets(self, config_dict: Dict[str, Any]):
        """Remove sensitive information from configuration dictionary"""
        sensitive_keys = ['password', 'api_key', 'api_secret', 'token', 'secret']

        def remove_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        obj[key] = "***REDACTED***"
                    else:
                        remove_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_recursive(item)

        remove_recursive(config_dict)

    def validate_config(self) -> List[str]:
        """Validate current configuration and return list of issues"""
        issues = []

        try:
            config = self.get_config()

            # Custom validation rules
            if config.risk.max_position_size <= 0:
                issues.append("max_position_size must be positive")

            if config.trading.order_timeout <= 0:
                issues.append("order_timeout must be positive")

            if not config.trading.symbols:
                issues.append("At least one trading symbol must be specified")

            # Validate exchange configurations
            for exchange_name, exchange_config in config.exchanges.items():
                if not exchange_config.api_key or not exchange_config.api_secret:
                    issues.append(f"Exchange {exchange_name} missing API credentials")

        except Exception as e:
            issues.append(f"Configuration validation failed: {e}")

        return issues

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_auto_reload()


# Global configuration manager instance
_config_manager: Optional[EnhancedConfigManager] = None


def get_config_manager() -> EnhancedConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = EnhancedConfigManager()
    return _config_manager


def load_config(config_dir: Optional[str] = None,
                environment: Optional[str] = None) -> EnhancedConfig:
    """Load configuration using global manager"""
    manager = get_config_manager()
    if config_dir:
        manager.config_dir = Path(config_dir)
    if environment:
        manager.environment = environment
    return manager.load_config()


def get_config() -> EnhancedConfig:
    """Get current configuration using global manager"""
    return get_config_manager().get_config()


def get_value(key_path: str, default: Any = None) -> Any:
    """Get configuration value using dot notation"""
    return get_config_manager().get_value(key_path, default)


# Example usage and initialization
if __name__ == "__main__":
    # Example configuration usage
    with EnhancedConfigManager(
        config_dir="config",
        environment="development",
        auto_reload=True
    ) as config_manager:

        # Load configuration
        config = config_manager.load_config()
        print(f"Loaded configuration for environment: {config.environment}")
        print(f"Database host: {config.database.host}")
        print(f"Risk limit: {config.risk.max_portfolio_risk}")

        # Get specific values
        api_key = config_manager.get_value("exchanges.binance.api_key")
        print(f"Binance API Key: {api_key[:8]}...")

        # Validate configuration
        issues = config_manager.validate_config()
        if issues:
            print("Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Configuration validation passed!")