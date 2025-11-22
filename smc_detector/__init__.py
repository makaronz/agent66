"""
SMC Detector Module - Smart Money Concepts Pattern Detection

Implements advanced Smart Money Concepts (SMC) pattern detection algorithms for market analysis.
Includes order block detection, CHOCH/BOS identification, liquidity sweep detection, and pattern recognition.

Key Features:
- Order block and fair value gap detection
- Change of Character (CHOCH) and Break of Structure (BOS) identification
- Liquidity sweep and stop hunt detection
- Market structure analysis and trend identification
- Pattern recognition and signal generation

Usage:
    from smc_detector import get_smc_indicators
    
    indicators = get_smc_indicators()
    patterns = indicators.detect_patterns(market_data)
"""

__version__ = "1.0.0"
__description__ = "Smart Money Concepts pattern detection algorithms"
__keywords__ = ["smc", "pattern-detection", "technical-analysis", "market-structure"]

# Package-level exports
__all__ = [
    'SMCIndicators',
    'get_smc_indicators',
    '__version__',
    '__description__'
]

def get_smc_indicators():
    """Get SMCIndicators instance for pattern detection.
    
    Returns:
        SMCIndicators: Configured instance for SMC pattern detection
        
    Example:
        indicators = get_smc_indicators()
        patterns = indicators.detect_patterns(market_data)
    """
    from .indicators import SMCIndicators
    return SMCIndicators
