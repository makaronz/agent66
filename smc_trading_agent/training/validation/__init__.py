"""
Training Validation Framework - Comprehensive Strategy Validation

This module provides advanced validation capabilities for trading strategy evaluation,
including statistical tests, cross-exchange validation, regime-specific backtesting,
Monte Carlo simulation, and enhanced out-of-sample testing.

Key Features:
- Statistical validation tests (Mann-Whitney U, SPA, Diebold-Mariano)
- Cross-exchange strategy validation and correlation analysis
- Regime-specific backtesting with market condition filtering
- Monte Carlo simulation for strategy robustness testing
- Enhanced out-of-sample testing with multiple time periods
- Integration with 2019-2025 data split timeline

Usage:
    from smc_trading_agent.training.validation import CrossExchangeValidator
    
    validator = CrossExchangeValidator(config)
    results = await validator.validate_across_exchanges(strategy_data)
"""

__version__ = "1.0.0"
__description__ = "Advanced trading strategy validation framework"
__keywords__ = ["validation", "cross-exchange", "statistical-tests", "backtesting", "monte-carlo"]

# Package-level exports
__all__ = [
    'CrossExchangeValidator',
    'StatisticalTestSuite', 
    'RegimeSpecificBacktester',
    'MonteCarloSimulator',
    'EnhancedOOSTester',
    'MannWhitneyTest',
    'SPATest',
    'DieboldMarianoTest',
    '__version__',
    '__description__'
]

def get_cross_exchange_validator(config: dict):
    """Get cross-exchange validation functionality.
    
    Args:
        config: Configuration dictionary with exchange and validation settings
        
    Returns:
        CrossExchangeValidator: Initialized cross-exchange validator
        
    Example:
        validator = get_cross_exchange_validator(config)
        results = await validator.validate_across_exchanges(data)
    """
    from .cross_exchange.validator import CrossExchangeValidator
    return CrossExchangeValidator(config)

def get_statistical_test_suite(config: dict):
    """Get statistical validation test suite.
    
    Args:
        config: Configuration dictionary with statistical test parameters
        
    Returns:
        StatisticalTestSuite: Initialized statistical test suite
        
    Example:
        tests = get_statistical_test_suite(config)
        results = await tests.run_all_tests(strategy_returns, benchmark_returns)
    """
    from .statistical_tests.test_suite import StatisticalTestSuite
    return StatisticalTestSuite(config)

def get_mann_whitney_test(config: dict):
    """Get Mann-Whitney U test functionality.
    
    Args:
        config: Configuration dictionary with test parameters
        
    Returns:
        MannWhitneyTest: Initialized Mann-Whitney test
        
    Example:
        test = get_mann_whitney_test(config)
        result = await test.test(strategy_returns, benchmark_returns)
    """
    from .statistical_tests.mann_whitney import MannWhitneyTest
    return MannWhitneyTest(config)

def get_spa_test(config: dict):
    """Get Superior Predictive Ability test functionality.
    
    Args:
        config: Configuration dictionary with SPA test parameters
        
    Returns:
        SPATest: Initialized SPA test
        
    Example:
        test = get_spa_test(config)
        result = await test.test(strategy_dict, benchmark_name)
    """
    from .statistical_tests.spa_test import SPATest
    return SPATest(config)

def get_diebold_mariano_test(config: dict):
    """Get Diebold-Mariano test functionality.
    
    Args:
        config: Configuration dictionary with DM test parameters
        
    Returns:
        DieboldMarianoTest: Initialized Diebold-Mariano test
        
    Example:
        test = get_diebold_mariano_test(config)
        result = await test.test(forecast1, forecast2, actual)
    """
    from .statistical_tests.diebold_mariano import DieboldMarianoTest
    return DieboldMarianoTest(config)

def get_regime_backtester(config: dict):
    """Get regime-specific backtesting functionality.
    
    Args:
        config: Configuration dictionary with regime detection parameters
        
    Returns:
        RegimeSpecificBacktester: Initialized regime-specific backtester
        
    Example:
        backtester = get_regime_backtester(config)
        results = await backtester.regime_specific_backtest(data)
    """
    from .regime_analysis.regime_backtester import RegimeSpecificBacktester
    return RegimeSpecificBacktester(config)

def get_monte_carlo_simulator(config: dict):
    """Get Monte Carlo simulation functionality.
    
    Args:
        config: Configuration dictionary with simulation parameters
        
    Returns:
        MonteCarloSimulator: Initialized Monte Carlo simulator
        
    Example:
        simulator = get_monte_carlo_simulator(config)
        results = await simulator.run_simulation(historical_data)
    """
    from .monte_carlo.simulator import MonteCarloSimulator
    return MonteCarloSimulator(config)

def get_enhanced_oos_tester(config: dict):
    """Get enhanced out-of-sample testing functionality.
    
    Args:
        config: Configuration dictionary with OOS testing parameters
        
    Returns:
        EnhancedOOSTester: Initialized enhanced OOS tester
        
    Example:
        tester = get_enhanced_oos_tester(config)
        results = await tester.enhanced_oos_testing(data)
    """
    from .out_of_sample.oos_tester import EnhancedOOSTester
    return EnhancedOOSTester(config)
