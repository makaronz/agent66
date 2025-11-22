"""
Configuration Validator

This module provides additional validation capabilities for the SMC Trading Agent
configuration, including type checking, value validation, and dependency validation.
"""

import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigValidator:
    """
    Configuration validator with comprehensive validation rules.
    
    Features:
    - Type validation for configuration values
    - Range validation for numeric values
    - Required field validation
    - Dependency validation
    - Custom validation rules
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate the complete configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        # Validate each section
        self._validate_app_section(config.get('app', {}))
        self._validate_data_pipeline_section(config.get('data_pipeline', {}))
        self._validate_smc_detector_section(config.get('smc_detector', {}))
        self._validate_decision_engine_section(config.get('decision_engine', {}))
        self._validate_execution_engine_section(config.get('execution_engine', {}))
        self._validate_risk_manager_section(config.get('risk_manager', {}))
        self._validate_monitoring_section(config.get('monitoring', {}))
        self._validate_logging_section(config.get('logging', {}))
        
        # Validate cross-section dependencies
        self._validate_dependencies(config)
        
        is_valid = len(self.validation_errors) == 0
        
        if self.validation_errors:
            logger.error(f"Configuration validation failed with {len(self.validation_errors)} errors")
            for error in self.validation_errors:
                logger.error(f"  - {error}")
        
        if self.validation_warnings:
            logger.warning(f"Configuration validation completed with {len(self.validation_warnings)} warnings")
            for warning in self.validation_warnings:
                logger.warning(f"  - {warning}")
        
        return is_valid, self.validation_errors, self.validation_warnings
    
    def _validate_app_section(self, app_config: Dict[str, Any]) -> None:
        """Validate the app section configuration."""
        if not app_config.get('name'):
            self.validation_errors.append("App name is required")
        
        if not app_config.get('version'):
            self.validation_errors.append("App version is required")
        
        # Validate version format (basic semantic versioning)
        version = app_config.get('version', '')
        if version and not self._is_valid_version(version):
            self.validation_errors.append(f"Invalid version format: {version}. Expected format: X.Y.Z")
    
    def _validate_data_pipeline_section(self, data_config: Dict[str, Any]) -> None:
        """Validate the data pipeline section configuration."""
        ingestion = data_config.get('ingestion', {})
        
        if not ingestion.get('source'):
            self.validation_errors.append("Data pipeline source is required")
        
        symbols = ingestion.get('symbols', [])
        if not symbols:
            self.validation_errors.append("At least one trading symbol is required")
        elif not isinstance(symbols, list):
            self.validation_errors.append("Trading symbols must be a list")
        
        timeframe = ingestion.get('timeframe')
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if timeframe and timeframe not in valid_timeframes:
            self.validation_errors.append(f"Invalid timeframe: {timeframe}. Valid options: {valid_timeframes}")
    
    def _validate_smc_detector_section(self, smc_config: Dict[str, Any]) -> None:
        """Validate the SMC detector section configuration."""
        indicators = smc_config.get('indicators', [])
        
        if not indicators:
            self.validation_warnings.append("No SMC indicators configured")
            return
        
        valid_indicator_names = ['order_block', 'liquidity_grab', 'fair_value_gap']
        
        for indicator in indicators:
            if not isinstance(indicator, dict):
                self.validation_errors.append("Each indicator must be a dictionary")
                continue
            
            name = indicator.get('name')
            if not name:
                self.validation_errors.append("Indicator name is required")
            elif name not in valid_indicator_names:
                self.validation_warnings.append(f"Unknown indicator name: {name}")
            
            params = indicator.get('params', {})
            if not isinstance(params, dict):
                self.validation_errors.append(f"Indicator {name} params must be a dictionary")
    
    def _validate_decision_engine_section(self, decision_config: Dict[str, Any]) -> None:
        """Validate the decision engine section configuration."""
        model_path = decision_config.get('model_path')
        if model_path and not Path(model_path).exists():
            self.validation_warnings.append(f"Decision model file not found: {model_path}")
        
        confidence_threshold = decision_config.get('confidence_threshold')
        if confidence_threshold is not None:
            if not isinstance(confidence_threshold, (int, float)):
                self.validation_errors.append("Confidence threshold must be a number")
            elif not 0 <= confidence_threshold <= 1:
                self.validation_errors.append("Confidence threshold must be between 0 and 1")
    
    def _validate_execution_engine_section(self, execution_config: Dict[str, Any]) -> None:
        """Validate the execution engine section configuration."""
        api_keys = execution_config.get('api_keys', {})
        
        if not api_keys:
            self.validation_warnings.append("No API keys configured for execution engine")
            return
        
        for exchange, keys in api_keys.items():
            if not isinstance(keys, dict):
                self.validation_errors.append(f"API keys for {exchange} must be a dictionary")
                continue
            
            if not keys.get('key'):
                self.validation_errors.append(f"API key for {exchange} is required")
            
            if not keys.get('secret'):
                self.validation_errors.append(f"API secret for {exchange} is required")
        
        max_risk = execution_config.get('max_risk_per_trade')
        if max_risk is not None:
            if not isinstance(max_risk, (int, float)):
                self.validation_errors.append("Max risk per trade must be a number")
            elif not 0 < max_risk <= 1:
                self.validation_errors.append("Max risk per trade must be between 0 and 1")
    
    def _validate_risk_manager_section(self, risk_config: Dict[str, Any]) -> None:
        """Validate the risk manager section configuration."""
        max_drawdown = risk_config.get('max_drawdown')
        if max_drawdown is not None:
            if not isinstance(max_drawdown, (int, float)):
                self.validation_errors.append("Max drawdown must be a number")
            elif not 0 < max_drawdown <= 1:
                self.validation_errors.append("Max drawdown must be between 0 and 1")
        
        circuit_breaker = risk_config.get('circuit_breaker_threshold')
        if circuit_breaker is not None:
            if not isinstance(circuit_breaker, int):
                self.validation_errors.append("Circuit breaker threshold must be an integer")
            elif circuit_breaker <= 0:
                self.validation_errors.append("Circuit breaker threshold must be positive")
    
    def _validate_monitoring_section(self, monitoring_config: Dict[str, Any]) -> None:
        """Validate the monitoring section configuration."""
        enabled = monitoring_config.get('enabled')
        if enabled is not None and not isinstance(enabled, bool):
            self.validation_errors.append("Monitoring enabled must be a boolean")
        
        port = monitoring_config.get('port')
        if port is not None:
            if not isinstance(port, int):
                self.validation_errors.append("Monitoring port must be an integer")
            elif not 1024 <= port <= 65535:
                self.validation_errors.append("Monitoring port must be between 1024 and 65535")
    
    def _validate_logging_section(self, logging_config: Dict[str, Any]) -> None:
        """Validate the logging section configuration."""
        if not logging_config:
            self.validation_warnings.append("No logging configuration provided")
            return
        
        version = logging_config.get('version')
        if version != 1:
            self.validation_warnings.append("Logging version should be 1 for dictConfig")
        
        handlers = logging_config.get('handlers', {})
        if not handlers:
            self.validation_warnings.append("No logging handlers configured")
        
        root = logging_config.get('root', {})
        if not root.get('handlers'):
            self.validation_warnings.append("No root logging handlers configured")
    
    def _validate_dependencies(self, config: Dict[str, Any]) -> None:
        """Validate cross-section dependencies."""
        # Check if data pipeline source matches execution engine API keys
        data_source = config.get('data_pipeline', {}).get('ingestion', {}).get('source')
        execution_keys = config.get('execution_engine', {}).get('api_keys', {})
        
        if data_source and execution_keys:
            if data_source not in execution_keys:
                self.validation_warnings.append(
                    f"Data pipeline source '{data_source}' doesn't have corresponding API keys configured"
                )
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string follows semantic versioning format."""
        import re
        pattern = r'^\d+\.\d+\.\d+(\-[a-zA-Z0-9\-\.]+)?(\+[a-zA-Z0-9\-\.]+)?$'
        return bool(re.match(pattern, version))

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = ConfigValidator()
    return validator.validate_config(config)
