"""
SMC Trading Agent - Advanced algorithmic trading system.

A comprehensive trading platform for detecting and executing SMC (Smart Money Concepts)
strategies with real-time market analysis, risk management, and automated execution.
The system includes data pipeline, SMC pattern detection, decision engine, risk management,
and execution components for cryptocurrency markets.

Author: SMC Trading Agent Team
Version: 1.0.0
License: MIT
URL: https://github.com/smc-trading/agent66
"""

__version__ = "1.0.0"
__author__ = "SMC Trading Agent Team"
__email__ = "team@smctrading.com"
__license__ = "MIT"
__description__ = "Advanced algorithmic trading system for SMC strategies"
__url__ = "https://github.com/smc-trading/agent66"
__keywords__ = ["trading", "algorithmic", "smc", "cryptocurrency", "finance"]

# Core package imports for direct access
from .config_loader import SecureConfigLoader, load_secure_config
from .error_handlers import (
    TradingError, DataValidationError, ComponentHealthError, 
    ExecutionError, DecisionError, RiskManagementError,
    CircuitBreaker, RetryHandler, safe_execute, error_boundary,
    health_monitor
)
from .health_monitor import HealthMonitor
from .service_manager import ServiceManager
from .config_validator import ConfigValidator
from .validators import DataValidator, MarketDataModel, TradeSignalModel, OrderBlockModel

# Package-level exports for clean import interface
__all__ = [
    # Core components
    "SecureConfigLoader",
    "load_secure_config",
    "TradingError",
    "DataValidationError", 
    "ComponentHealthError",
    "ExecutionError",
    "DecisionError",
    "RiskManagementError",
    "CircuitBreaker",
    "RetryHandler",
    "safe_execute",
    "error_boundary",
    "health_monitor",
    "HealthMonitor",
    "ServiceManager",
    "ConfigValidator",
    "DataValidator",
    "MarketDataModel",
    "TradeSignalModel",
    "OrderBlockModel",
    
    # Lazy-loaded components (via getter functions)
    "get_market_data_processor",
    "get_smc_indicators",
    "get_adaptive_model_selector", 
    "get_smc_risk_manager",
    
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
    "__license__",
    "__url__"
]

# Lazy imports to avoid dependency issues during package import
def get_market_data_processor():
    """Get MarketDataProcessor instance for data pipeline operations."""
    from .data_pipeline.ingestion import MarketDataProcessor
    return MarketDataProcessor

def get_smc_indicators():
    """Get SMCIndicators instance for pattern detection."""
    from .smc_detector.indicators import SMCIndicators
    return SMCIndicators

def get_adaptive_model_selector():
    """Get AdaptiveModelSelector instance for decision making."""
    from .decision_engine.model_ensemble import AdaptiveModelSelector
    return AdaptiveModelSelector

def get_smc_risk_manager():
    """Get SMCRiskManager instance for risk management."""
    from .risk_manager.smc_risk_manager import SMCRiskManager
    return SMCRiskManager
