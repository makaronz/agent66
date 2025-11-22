"""
Statistical Validation Tests Module

Provides comprehensive statistical validation capabilities for trading strategy evaluation,
including Mann-Whitney U test, Superior Predictive Ability (SPA) test, and Diebold-Mariano test.

Key Features:
- Mann-Whitney U test for non-parametric comparison of return distributions
- Superior Predictive Ability (SPA) test for multiple strategy comparison with bootstrap
- Diebold-Mariano test for forecast accuracy comparison
- Unified test suite interface with comprehensive result reporting
- Statistical significance testing with confidence intervals
- Integration with async validation pipeline

Usage:
    from training.validation.statistical_tests import StatisticalTestSuite
    
    test_suite = StatisticalTestSuite(config)
    results = await test_suite.run_all_tests(strategy_returns, benchmark_returns)
"""

__version__ = "1.0.0"
__description__ = "Statistical validation tests for trading strategy evaluation"
__keywords__ = ["statistical-tests", "mann-whitney", "spa-test", "diebold-mariano", "validation"]

# Package-level exports
__all__ = [
    'StatisticalTestSuite',
    'MannWhitneyTest',
    'SPATest', 
    'DieboldMarianoTest',
    'StatisticalTestResult',
    '__version__',
    '__description__'
]

def get_statistical_test_suite(config: dict):
    """Get statistical test suite instance.
    
    Args:
        config: Configuration dictionary with statistical test parameters
        
    Returns:
        StatisticalTestSuite: Initialized statistical test suite
    """
    from .test_suite import StatisticalTestSuite
    return StatisticalTestSuite(config)

def get_mann_whitney_test(config: dict):
    """Get Mann-Whitney U test instance.
    
    Args:
        config: Configuration dictionary with test parameters
        
    Returns:
        MannWhitneyTest: Initialized Mann-Whitney test
    """
    from .mann_whitney import MannWhitneyTest
    return MannWhitneyTest(config)

def get_spa_test(config: dict):
    """Get Superior Predictive Ability test instance.
    
    Args:
        config: Configuration dictionary with SPA test parameters
        
    Returns:
        SPATest: Initialized SPA test
    """
    from .spa_test import SPATest
    return SPATest(config)

def get_diebold_mariano_test(config: dict):
    """Get Diebold-Mariano test instance.
    
    Args:
        config: Configuration dictionary with DM test parameters
        
    Returns:
        DieboldMarianoTest: Initialized Diebold-Mariano test
    """
    from .diebold_mariano import DieboldMarianoTest
    return DieboldMarianoTest(config)
