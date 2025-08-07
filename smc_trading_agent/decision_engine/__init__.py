"""
Decision Engine Module - Trading Decision Logic and Model Ensemble

Implements advanced trading decision logic and model ensemble for the SMC Trading Agent.
Includes adaptive model selection, signal generation, decision optimization, and strategy execution.

Key Features:
- Adaptive model selection based on market conditions
- Multi-model ensemble for signal generation
- Decision optimization and strategy execution
- Performance-based model weighting
- Real-time decision making and signal processing
- Strategy backtesting and validation

Usage:
    from smc_trading_agent.decision_engine import get_adaptive_model_selector
    
    model_selector = get_adaptive_model_selector()
    decision = model_selector.generate_decision(market_data, patterns)
"""

__version__ = "1.0.0"
__description__ = "Trading decision logic and model ensemble"
__keywords__ = ["decision-engine", "model-ensemble", "signal-generation", "strategy-execution"]

# Package-level exports
__all__ = [
    'AdaptiveModelSelector',
    'get_adaptive_model_selector',
    '__version__',
    '__description__'
]

def get_adaptive_model_selector():
    """Get AdaptiveModelSelector instance for trading decisions.
    
    Returns:
        AdaptiveModelSelector: Configured instance for adaptive model selection
        
    Example:
        model_selector = get_adaptive_model_selector()
        decision = model_selector.generate_decision(market_data, patterns)
    """
    from .model_ensemble import AdaptiveModelSelector
    return AdaptiveModelSelector
