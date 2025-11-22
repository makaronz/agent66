<<<<<<< Current (Your changes)
=======
"""
Data Pipeline Module - Market Data Ingestion and Processing

Handles comprehensive market data ingestion, processing, and storage for the SMC Trading Agent.
Includes real-time data feeds, historical data management, data validation, and pipeline orchestration.

Key Features:
- Real-time market data ingestion from multiple exchanges
- Historical data retrieval and management
- Data validation and quality assurance
- Pipeline orchestration and monitoring
- Data transformation and preprocessing

Usage:
    from data_pipeline import get_market_data_processor
    
    processor = get_market_data_processor()
    data = processor.ingest_market_data()
"""

__version__ = "1.0.0"
__description__ = "Market data ingestion and processing pipeline"
__keywords__ = ["data", "pipeline", "ingestion", "market-data", "processing"]

# Package-level exports
__all__ = [
    'MarketDataProcessor',
    'get_market_data_processor',
    '__version__',
    '__description__'
]

def get_market_data_processor():
    """Get MarketDataProcessor instance for data pipeline operations.
    
    Returns:
        MarketDataProcessor: Configured instance for market data processing
        
    Example:
        processor = get_market_data_processor()
        data = processor.ingest_market_data()
    """
    from .ingestion import MarketDataProcessor
    return MarketDataProcessor
>>>>>>> Incoming (Background Agent changes)
