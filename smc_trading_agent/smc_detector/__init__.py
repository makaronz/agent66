"""
SMC Detector Module

Implements Smart Money Concepts (SMC) pattern detection algorithms.
Includes order block detection, CHOCH/BOS identification, and liquidity sweep detection.
"""

__all__ = ['SMCIndicators']

def get_smc_indicators():
    """Get SMCIndicators instance."""
    from .indicators import SMCIndicators
    return SMCIndicators
