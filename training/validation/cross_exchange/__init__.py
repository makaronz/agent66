"""
Cross-Exchange Validation Module

Provides comprehensive cross-exchange validation functionality for trading strategy evaluation,
including data alignment, correlation analysis, and performance consistency testing.

Key Features:
- Multi-exchange data synchronization and alignment
- Cross-exchange correlation analysis with statistical significance
- Performance consistency validation across exchanges
- Exchange-specific metrics calculation and comparison
- Async processing for efficient multi-exchange operations

Usage:
    from training.validation.cross_exchange import CrossExchangeValidator
    
    validator = CrossExchangeValidator(config)
    results = await validator.validate_across_exchanges(strategy_data)
"""

__version__ = "1.0.0"
__description__ = "Cross-exchange validation and correlation analysis"
__keywords__ = ["cross-exchange", "validation", "correlation", "data-alignment", "async"]

# Package-level exports
__all__ = [
    'CrossExchangeValidator',
    'TimeSeriesAligner',
    'CorrelationAnalyzer',
    'DataQualityValidator',
    '__version__',
    '__description__'
]

def get_cross_exchange_validator(config: dict):
    """Get cross-exchange validator instance.
    
    Args:
        config: Configuration dictionary with exchange and validation settings
        
    Returns:
        CrossExchangeValidator: Initialized cross-exchange validator
    """
    from .validator import CrossExchangeValidator
    return CrossExchangeValidator(config)

def get_time_series_aligner(config: dict):
    """Get time series alignment functionality.
    
    Args:
        config: Configuration dictionary with alignment parameters
        
    Returns:
        TimeSeriesAligner: Initialized time series aligner
    """
    from .data_aligner import TimeSeriesAligner
    return TimeSeriesAligner(config)

def get_correlation_analyzer(config: dict):
    """Get correlation analysis functionality.
    
    Args:
        config: Configuration dictionary with correlation parameters
        
    Returns:
        CorrelationAnalyzer: Initialized correlation analyzer
    """
    from .correlation_analyzer import CorrelationAnalyzer
    return CorrelationAnalyzer(config)
