<<<<<<< Current (Your changes)
=======
"""
Risk Manager Module - Portfolio Risk Management and Position Sizing

Implements comprehensive risk management and position sizing for the SMC Trading Agent.
Includes circuit breakers, stop-loss calculations, portfolio risk controls, and risk monitoring.

Key Features:
- Dynamic position sizing based on portfolio risk
- Circuit breaker implementation for market volatility
- Stop-loss and take-profit calculation
- Portfolio risk monitoring and alerts
- Risk-adjusted return optimization
- Maximum drawdown protection

Usage:
    from risk_manager import get_smc_risk_manager, get_circuit_breaker
    
    risk_manager = get_smc_risk_manager()
    circuit_breaker = get_circuit_breaker()
    
    position_size = risk_manager.calculate_position_size(capital, risk_per_trade)
"""

__version__ = "1.0.0"
__description__ = "Portfolio risk management and position sizing"
__keywords__ = ["risk-management", "position-sizing", "circuit-breaker", "portfolio-control"]

# Package-level exports
__all__ = [
    'CircuitBreaker',
    'SMCRiskManager',
    'get_circuit_breaker',
    'get_smc_risk_manager',
    '__version__',
    '__description__'
]

def get_circuit_breaker():
    """Get CircuitBreaker instance for market volatility protection.
    
    Returns:
        CircuitBreaker: Configured instance for circuit breaker functionality
        
    Example:
        circuit_breaker = get_circuit_breaker()
        if circuit_breaker.should_trigger(volatility_metrics):
            circuit_breaker.activate()
    """
    from .circuit_breaker import CircuitBreaker
    return CircuitBreaker

def get_smc_risk_manager():
    """Get SMCRiskManager instance for portfolio risk management.
    
    Returns:
        SMCRiskManager: Configured instance for risk management operations
        
    Example:
        risk_manager = get_smc_risk_manager()
        position_size = risk_manager.calculate_position_size(capital, risk_per_trade)
    """
    from .smc_risk_manager import SMCRiskManager
    return SMCRiskManager
>>>>>>> Incoming (Background Agent changes)
