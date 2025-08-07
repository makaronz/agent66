"""
SMC Trading Agent - Smart Money Concepts Trading System

A comprehensive automated trading system that implements Smart Money Concepts (SMC)
for cryptocurrency markets. The system includes data pipeline, SMC pattern detection,
decision engine, risk management, and execution components.

Author: SMC Trading Agent Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "SMC Trading Agent Team"
__description__ = "Smart Money Concepts Trading System"

# Import main components for easy access
# These imports are available but may require external dependencies
__all__ = [
    'MarketDataProcessor',
    'SMCIndicators', 
    'AdaptiveModelSelector',
    'SMCRiskManager',
]

# Lazy imports to avoid dependency issues during package import
def get_market_data_processor():
    """Get MarketDataProcessor instance."""
    from .data_pipeline.ingestion import MarketDataProcessor
    return MarketDataProcessor

def get_smc_indicators():
    """Get SMCIndicators instance."""
    from .smc_detector.indicators import SMCIndicators
    return SMCIndicators

def get_adaptive_model_selector():
    """Get AdaptiveModelSelector instance."""
    from .decision_engine.model_ensemble import AdaptiveModelSelector
    return AdaptiveModelSelector

def get_smc_risk_manager():
    """Get SMCRiskManager instance."""
    from .risk_manager.smc_risk_manager import SMCRiskManager
    return SMCRiskManager
