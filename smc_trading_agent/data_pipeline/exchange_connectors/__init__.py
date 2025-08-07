"""
Exchange Connectors Package

This package contains exchange-specific connectors for real-time market data ingestion.
All connectors implement a unified interface for WebSocket and REST API connections.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class ExchangeConnector(ABC):
    """
    Abstract base class for all exchange connectors.
    
    Provides unified interface for WebSocket connections, REST API calls,
    and data normalization across different exchanges.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize exchange connector with configuration.
        
        Args:
            config: Exchange-specific configuration dictionary
        """
        self.config = config
        self.name = config.get('name', 'unknown')
        self.connected = False
        self.websocket = None
        self.rest_client = None
        self.rate_limiter = None
        
    @abstractmethod
    async def connect_websocket(self) -> bool:
        """
        Establish WebSocket connection to exchange.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect_websocket(self) -> bool:
        """
        Disconnect WebSocket connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def subscribe_to_streams(self, streams: List[str]) -> bool:
        """
        Subscribe to specific data streams.
        
        Args:
            streams: List of stream names to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Fetch data from REST API endpoint.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Dict: API response data
        """
        pass
    
    @abstractmethod
    async def normalize_data(self, raw_data: Dict, data_type: str) -> Dict:
        """
        Normalize exchange-specific data to unified format.
        
        Args:
            raw_data: Raw data from exchange
            data_type: Type of data (trade, orderbook, kline, etc.)
            
        Returns:
            Dict: Normalized data in unified format
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict:
        """
        Get current health status of the connector.
        
        Returns:
            Dict: Health status information
        """
        pass
    
    async def fetch_ohlcv_async(
        self, 
        symbol: str, 
        timeframe: str = '1m',
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: int = 1000
    ) -> Optional[Any]:
        """
        Fetch OHLCV data asynchronously (default implementation).
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (e.g., '1m', '5m', '1h')
            start_time: Start time for data fetch
            end_time: End time for data fetch
            limit: Maximum number of records to fetch
            
        Returns:
            Optional[pd.DataFrame]: OHLCV data or None if fetch fails
        """
        try:
            # Default implementation using REST API
            # This can be overridden by specific connectors for better performance
            import pandas as pd
            
            params = {
                'symbol': symbol.replace('/', ''),
                'interval': timeframe,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000) if hasattr(start_time, 'timestamp') else start_time
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000) if hasattr(end_time, 'timestamp') else end_time
            
            # This is a placeholder - actual implementation should be in specific connectors
            logger.warning(f"Using default OHLCV fetch for {self.name} - implement fetch_ohlcv_async for better performance")
            
            # Return empty DataFrame as fallback
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data for {symbol}: {str(e)}")
            return None
    
    async def start(self) -> bool:
        """
        Start the exchange connector.
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        try:
            logger.info(f"Starting {self.name} connector")
            success = await self.connect_websocket()
            if success:
                self.connected = True
                logger.info(f"{self.name} connector started successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to start {self.name} connector: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the exchange connector.
        
        Returns:
            bool: True if shutdown successful, False otherwise
        """
        try:
            logger.info(f"Stopping {self.name} connector")
            success = await self.disconnect_websocket()
            if success:
                self.connected = False
                logger.info(f"{self.name} connector stopped successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to stop {self.name} connector: {e}")
            return False


class ExchangeConnectorError(Exception):
    """Base exception for exchange connector errors."""
    pass


class WebSocketConnectionError(ExchangeConnectorError):
    """Exception raised when WebSocket connection fails."""
    pass


class RESTAPIError(ExchangeConnectorError):
    """Exception raised when REST API call fails."""
    pass


class RateLimitError(ExchangeConnectorError):
    """Exception raised when rate limit is exceeded."""
    pass


class DataNormalizationError(ExchangeConnectorError):
    """Exception raised when data normalization fails."""
    pass


def get_exchange_connector(exchange_name: str, config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create exchange connector instances.
    
    Args:
        exchange_name: Name of the exchange ('binance', 'bybit', etc.)
        config: Optional configuration dictionary
        
    Returns:
        ExchangeConnector: Initialized exchange connector instance
        
    Raises:
        ValueError: If exchange is not supported
    """
    if config is None:
        config = {}
    
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'binance':
        from .binance_connector import BinanceConnector
        return BinanceConnector(config)
    elif exchange_name == 'bybit':
        from .bybit_connector import ByBitConnector
        return ByBitConnector(config)
    else:
        supported_exchanges = ['binance', 'bybit']
        raise ValueError(f"Unsupported exchange: {exchange_name}. Supported exchanges: {supported_exchanges}")


# Package exports
__all__ = [
    'ExchangeConnector',
    'ExchangeConnectorError',
    'WebSocketConnectionError', 
    'RESTAPIError',
    'RateLimitError',
    'DataNormalizationError',
    'get_exchange_connector'
]
