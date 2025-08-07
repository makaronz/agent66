"""
Data Pipeline Module

Handles market data ingestion, processing, and storage for the SMC Trading Agent.
Includes real-time data feeds, historical data management, and data validation.
"""

__all__ = ['MarketDataProcessor']

def get_market_data_processor():
    """Get MarketDataProcessor instance."""
    from .ingestion import MarketDataProcessor
    return MarketDataProcessor
