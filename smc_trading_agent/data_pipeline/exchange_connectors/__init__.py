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
