<<<<<<< Current (Your changes)
=======
"""
Secure Configuration Loader with Environment Variable Substitution

This module provides secure configuration loading with environment variable
substitution, validation, and proper error handling for sensitive values.
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

class EnvironmentVariableError(Exception):
    """Raised when required environment variables are missing."""
    pass

class SecureConfigLoader:
    """
    Secure configuration loader with environment variable substitution.
    
    Features:
    - Environment variable substitution using ${VAR_NAME} syntax
    - Secure handling of sensitive configuration values
    - Configuration validation
    - Proper error handling and logging
    - Support for .env files
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the secure configuration loader.
        
        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file
        self._load_environment_variables()
        
    def _load_environment_variables(self):
        """Load environment variables from .env file if specified."""
        if self.env_file and Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment variables from {self.env_file}")
        elif self.env_file:
            logger.warning(f"Environment file {self.env_file} not found, using system environment")
    
    def _substitute_environment_variables(self, value: str) -> str:
        """
        Substitute environment variables in a string value.
        
        Args:
            value: String value that may contain environment variable references
            
        Returns:
            String with environment variables substituted
            
        Raises:
            EnvironmentVariableError: If a required environment variable is missing
        """
        if not isinstance(value, str):
            return value
            
        # Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
        pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2)
            
            # Get environment variable value
            env_value = os.getenv(var_name)
            
            if env_value is not None:
                return env_value
            elif default_value is not None:
                logger.debug(f"Environment variable {var_name} not found, using default value")
                return default_value
            else:
                raise EnvironmentVariableError(
                    f"Required environment variable '{var_name}' is not set"
                )
        
        return re.sub(pattern, replace_var, value)
    
    def _recursive_substitution(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in configuration objects.
        
        Args:
            obj: Configuration object (dict, list, or primitive type)
            
        Returns:
            Object with environment variables substituted
        """
        if isinstance(obj, dict):
            return {key: self._recursive_substitution(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._recursive_substitution(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_environment_variables(obj)
        else:
            return obj
    
    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration structure and required values.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        required_sections = ['app', 'data_pipeline', 'smc_detector', 'decision_engine']
        
        for section in required_sections:
            if section not in config:
                raise ConfigValidationError(f"Required configuration section '{section}' is missing")
        
        # Validate execution engine API keys
        execution_engine = config.get('execution_engine', {})
        api_keys = execution_engine.get('api_keys', {})
        
        for exchange, keys in api_keys.items():
            if not keys.get('key') or keys['key'] == 'YOUR_API_KEY':
                raise ConfigValidationError(
                    f"API key for {exchange} is not properly configured. "
                    "Use environment variables like ${{BINANCE_API_KEY}}"
                )
            if not keys.get('secret') or keys['secret'] == 'YOUR_API_SECRET':
                raise ConfigValidationError(
                    f"API secret for {exchange} is not properly configured. "
                    "Use environment variables like ${{BINANCE_API_SECRET}}"
                )
    
    def _sanitize_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sanitized version of config for logging (removes sensitive data).
        
        Args:
            config: Original configuration dictionary
            
        Returns:
            Sanitized configuration dictionary safe for logging
        """
        sanitized = config.copy()
        
        # Remove sensitive API keys from logging
        if 'execution_engine' in sanitized:
            if 'api_keys' in sanitized['execution_engine']:
                sanitized['execution_engine']['api_keys'] = {
                    exchange: {
                        'key': '[REDACTED]' if keys.get('key') else None,
                        'secret': '[REDACTED]' if keys.get('secret') else None
                    }
                    for exchange, keys in sanitized['execution_engine']['api_keys'].items()
                }
        
        return sanitized
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load and process configuration file with environment variable substitution.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Processed configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file is not found
            yaml.YAMLError: If YAML parsing fails
            EnvironmentVariableError: If required environment variables are missing
            ConfigValidationError: If configuration validation fails
        """
        try:
            # Load YAML configuration
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            if config is None:
                raise ConfigValidationError("Configuration file is empty or invalid")
            
            logger.info(f"Loaded configuration from {config_path}")
            
            # Substitute environment variables
            config = self._recursive_substitution(config)
            
            # Validate configuration
            self._validate_configuration(config)
            
            # Log sanitized configuration
            sanitized_config = self._sanitize_config_for_logging(config)
            logger.info("Configuration loaded successfully", extra={'config': sanitized_config})
            
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except EnvironmentVariableError as e:
            logger.error(f"Environment variable error: {e}")
            raise
        except ConfigValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise

def load_secure_config(config_path: str = "config.yaml", 
                      env_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to load secure configuration.
    
    Args:
        config_path: Path to the configuration file
        env_file: Path to .env file (optional)
        
    Returns:
        Processed configuration dictionary
    """
    loader = SecureConfigLoader(env_file)
    return loader.load_config(config_path)
>>>>>>> Incoming (Background Agent changes)
