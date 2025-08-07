"""
Risk Manager Module

Implements risk management and position sizing for the SMC Trading Agent.
Includes circuit breakers, stop-loss calculations, and portfolio risk controls.
"""

__all__ = ['CircuitBreaker', 'SMCRiskManager']

def get_circuit_breaker():
    """Get CircuitBreaker instance."""
    from .circuit_breaker import CircuitBreaker
    return CircuitBreaker

def get_smc_risk_manager():
    """Get SMCRiskManager instance."""
    from .smc_risk_manager import SMCRiskManager
    return SMCRiskManager
