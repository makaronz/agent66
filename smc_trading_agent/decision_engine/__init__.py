"""
Decision Engine Module

Implements the trading decision logic and model ensemble for the SMC Trading Agent.
Includes adaptive model selection, signal generation, and decision optimization.
"""

__all__ = ['AdaptiveModelSelector']

def get_adaptive_model_selector():
    """Get AdaptiveModelSelector instance."""
    from .model_ensemble import AdaptiveModelSelector
    return AdaptiveModelSelector
