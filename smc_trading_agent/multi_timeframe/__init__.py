"""
Multi-Timeframe Confluence Analysis System

Advanced multi-timeframe analysis for SMC trading with confluence detection,
market structure alignment, and intelligent signal generation.
"""

from .data_manager import MultiTimeframeDataManager
from .confluence_engine import ConfluenceAnalysisEngine
from .signal_generator import MultiTimeframeSignalGenerator
from .cache_manager import ConfluenceCacheManager

__all__ = [
    'MultiTimeframeDataManager',
    'ConfluenceAnalysisEngine',
    'MultiTimeframeSignalGenerator',
    'ConfluenceCacheManager'
]

VERSION = "1.0.0"