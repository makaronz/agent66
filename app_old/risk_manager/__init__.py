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
    from smc_trading_agent.risk_manager import get_smc_risk_manager, get_circuit_breaker
    
    risk_manager = get_smc_risk_manager()
    circuit_breaker = get_circuit_breaker()
    
    position_size = risk_manager.calculate_position_size(capital, risk_per_trade)
"""

__version__ = "1.1.0"
__description__ = "Enhanced Risk Management Module for SMC Trading Agent with Kelly Criterion and MiFID II Compliance"
__keywords__ = ["risk", "management", "circuit", "breaker", "smc", "trading", "kelly", "criterion", "mifid", "compliance"]

from .circuit_breaker import CircuitBreaker
from .smc_risk_manager import SMCRiskManager
from .kelly_criterion import KellyCriterionCalculator, TradingRecord
from .position_manager import PositionManager
from .risk_metrics import RiskMetricsMonitor
from .var_calculator import VaRCalculator

__all__ = [
    'CircuitBreaker', 
    'SMCRiskManager', 
    'KellyCriterionCalculator', 
    'TradingRecord',
    'PositionManager',
    'RiskMetricsMonitor', 
    'VaRCalculator',
    'get_circuit_breaker',
    'get_smc_risk_manager',
    'get_kelly_calculator'
]

# Convenience functions
def get_circuit_breaker(config: dict = None) -> CircuitBreaker:
    """
    Factory function to create a CircuitBreaker instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        CircuitBreaker instance
    """
    return CircuitBreaker(config or {})

def get_smc_risk_manager(config: dict = None) -> SMCRiskManager:
    """
    Factory function to create an SMCRiskManager instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        SMCRiskManager instance
    """
    return SMCRiskManager(config or {})

def get_kelly_calculator(config: dict = None) -> KellyCriterionCalculator:
    """
    Factory function to create a KellyCriterionCalculator instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        KellyCriterionCalculator instance
    """
    kelly_config = config or {}
    return KellyCriterionCalculator(
        lookback_trades=kelly_config.get('lookback_trades', 100),
        min_trades_required=kelly_config.get('min_trades_required', 20),
        scaling_factor=kelly_config.get('scaling_factor', 0.25),
        max_kelly_fraction=kelly_config.get('max_kelly_fraction', 0.20),
        min_kelly_fraction=kelly_config.get('min_kelly_fraction', 0.01)
    )
