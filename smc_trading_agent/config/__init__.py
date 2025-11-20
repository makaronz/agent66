"""
Configuration module for SMC Trading Agent

Provides easy access to configuration management functionality.
"""

from .enhanced_config_manager import (
    EnhancedConfigManager,
    EnhancedConfig,
    ConfigEnvironment,
    ConfigFormat,
    ConfigurationError,
    ConfigValidationError,
    ConfigFileNotFoundError,
    get_config_manager,
    load_config,
    get_config,
    get_value
)

__all__ = [
    "EnhancedConfigManager",
    "EnhancedConfig",
    "ConfigEnvironment",
    "ConfigFormat",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileNotFoundError",
    "get_config_manager",
    "load_config",
    "get_config",
    "get_value"
]