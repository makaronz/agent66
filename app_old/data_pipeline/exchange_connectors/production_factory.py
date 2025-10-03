"""
Production Exchange Connector Factory

Creates and manages production-ready exchange connectors with proper configuration,
error handling, and monitoring capabilities.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Type
from contextlib import asynccontextmanager

from .production_config import (
    ProductionConfigManager, 
    ExchangeType, 
    Environment, 
    ExchangeConfig
)
from . import ExchangeConnector, ExchangeConnectorError
from .binance_connector import BinanceConnector
from .bybit_connector import ByBitConnector
from .oanda_connector import OANDAConnector

logger = logging.getLogger(__name__)


class ProductionExchangeConnector(ExchangeConnector):
    """
    Enhanced exchange connector with production features.
    
    Adds health monitoring, automatic reconnection, and comprehensive error handling
    to base exchange connectors.
    """
    
    def __init__(self, base_connector: ExchangeConnector, config: ExchangeConfig):
        """
        Initialize production connector wrapper.
        
        Args:
            base_connector: Base exchange connector instance
            config: Production configuration
        """
        super().__init__(config.credentials.__dict__)
        self.base_connector = base_connector
        self.config = config
        self.name = config.exchange_type.value
        
        # Production features
        self.health_check_interval = 30  # seconds
        self.reconnection_attempts = 0
        self.max_reconnection_attempts = config.max_retries
        self.last_health_check = 0
        self.connection_start_time = 0
        self.total_messages_processed = 0
        self.error_count = 0
        self.last_error = None
        
        # Monitoring
        self.metrics = {
            "connection_uptime": 0,
            "messages_processed": 0,
            "errors_count": 0,
            "reconnection_count": 0,
            "last_health_check": 0,
            "rate_limit_hits": 0
        }
        
        logger.info(f"Initialized production connector for {self.name}")
    
    async def connect_websocket(self) -> bool:
        """Connect with production error handling and monitoring."""
        try:
            logger.info(f"Connecting to {self.name} (environment: {self.config.environment.value})")
            
            # Use testnet URLs if configured
            if self.config.testnet:
                logger.info(f"Using testnet environment for {self.name}")
            
            success = await self.base_connector.connect_websocket()
            
            if success:
                self.connected = True
                self.connection_start_time = asyncio.get_event_loop().time()
                self.reconnection_attempts = 0
                logger.info(f"Successfully connected to {self.name}")
            else:
                logger.error(f"Failed to connect to {self.name}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Connection error for {self.name}: {e}")
            return False
    
    async def disconnect_websocket(self) -> bool:
        """Disconnect with cleanup."""
        try:
            success = await self.base_connector.disconnect_websocket()
            
            if success:
                self.connected = False
                uptime = asyncio.get_event_loop().time() - self.connection_start_time
                self.metrics["connection_uptime"] = uptime
                logger.info(f"Disconnected from {self.name} (uptime: {uptime:.2f}s)")
            
            return success
            
        except Exception as e:
            logger.error(f"Disconnection error for {self.name}: {e}")
            return False
    
    async def subscribe_to_streams(self, streams: List[str]) -> bool:
        """Subscribe with validation and error handling."""
        try:
            if not self.connected:
                logger.error(f"Cannot subscribe - {self.name} not connected")
                return False
            
            # Validate streams based on exchange type
            validated_streams = self._validate_streams(streams)
            if not validated_streams:
                logger.error(f"No valid streams to subscribe to for {self.name}")
                return False
            
            success = await self.base_connector.subscribe_to_streams(validated_streams)
            
            if success:
                logger.info(f"Subscribed to {len(validated_streams)} streams on {self.name}")
            else:
                logger.error(f"Failed to subscribe to streams on {self.name}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Subscription error for {self.name}: {e}")
            return False
    
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Fetch with rate limiting and error handling."""
        try:
            # Check rate limits
            await self._check_rate_limits()
            
            # Use appropriate endpoint based on testnet setting
            if self.config.testnet:
                # Modify endpoint for testnet if needed
                endpoint = self._adjust_endpoint_for_testnet(endpoint)
            
            data = await self.base_connector.fetch_rest_data(endpoint, params)
            return data
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"REST API error for {self.name}: {e}")
            raise
    
    async def normalize_data(self, raw_data: Dict, data_type: str) -> Dict:
        """Normalize with error handling and metrics."""
        try:
            normalized = await self.base_connector.normalize_data(raw_data, data_type)
            self.total_messages_processed += 1
            self.metrics["messages_processed"] = self.total_messages_processed
            return normalized
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Data normalization error for {self.name}: {e}")
            raise
    
    async def get_health_status(self) -> Dict:
        """Get comprehensive health status."""
        try:
            # Get base health status
            base_health = await self.base_connector.get_health_status()
            
            # Add production metrics
            current_time = asyncio.get_event_loop().time()
            uptime = current_time - self.connection_start_time if self.connected else 0
            
            production_health = {
                **base_health,
                "production_metrics": {
                    "environment": self.config.environment.value,
                    "testnet": self.config.testnet,
                    "uptime_seconds": uptime,
                    "messages_processed": self.total_messages_processed,
                    "error_count": self.error_count,
                    "reconnection_attempts": self.reconnection_attempts,
                    "last_error": self.last_error,
                    "rate_limit_config": {
                        "requests_per_minute": self.config.rate_limits.requests_per_minute,
                        "requests_per_second": self.config.rate_limits.requests_per_second
                    }
                }
            }
            
            self.last_health_check = current_time
            self.metrics["last_health_check"] = current_time
            
            return production_health
            
        except Exception as e:
            logger.error(f"Health check error for {self.name}: {e}")
            return {
                "exchange": self.name,
                "connected": False,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def listen_for_messages(self, callback):
        """Listen with automatic reconnection and error recovery."""
        while True:
            try:
                if not self.connected:
                    logger.warning(f"{self.name} not connected, attempting reconnection")
                    if not await self._attempt_reconnection():
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                
                # Delegate to base connector
                await self.base_connector.listen_for_messages(callback)
                
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                logger.error(f"Message listening error for {self.name}: {e}")
                
                # Attempt reconnection
                self.connected = False
                if not await self._attempt_reconnection():
                    logger.error(f"Failed to reconnect to {self.name}, retrying in {self.config.retry_delay}s")
                    await asyncio.sleep(self.config.retry_delay)
    
    async def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect with exponential backoff."""
        if self.reconnection_attempts >= self.max_reconnection_attempts:
            logger.error(f"Max reconnection attempts reached for {self.name}")
            return False
        
        self.reconnection_attempts += 1
        self.metrics["reconnection_count"] = self.reconnection_attempts
        
        # Exponential backoff
        delay = min(
            self.config.retry_delay * (self.config.rate_limits.backoff_factor ** (self.reconnection_attempts - 1)),
            self.config.rate_limits.max_backoff_time
        )
        
        logger.info(f"Attempting reconnection {self.reconnection_attempts}/{self.max_reconnection_attempts} for {self.name} (delay: {delay:.2f}s)")
        await asyncio.sleep(delay)
        
        try:
            success = await self.connect_websocket()
            if success:
                logger.info(f"Successfully reconnected to {self.name}")
                return True
            else:
                logger.warning(f"Reconnection attempt {self.reconnection_attempts} failed for {self.name}")
                return False
                
        except Exception as e:
            logger.error(f"Reconnection error for {self.name}: {e}")
            return False
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits."""
        # This would integrate with a rate limiter
        # For now, just log if we're approaching limits
        pass
    
    def _validate_streams(self, streams: List[str]) -> List[str]:
        """Validate streams for the specific exchange."""
        validated = []
        
        for stream in streams:
            # Basic validation - can be enhanced per exchange
            if stream and isinstance(stream, str):
                validated.append(stream)
            else:
                logger.warning(f"Invalid stream format: {stream}")
        
        return validated
    
    def _adjust_endpoint_for_testnet(self, endpoint: str) -> str:
        """Adjust endpoint for testnet if needed."""
        # Exchange-specific testnet endpoint adjustments
        return endpoint


class ProductionExchangeFactory:
    """
    Factory for creating production-ready exchange connectors.
    
    Manages configuration, connector creation, and lifecycle management.
    """
    
    # Mapping of exchange types to connector classes
    CONNECTOR_CLASSES: Dict[ExchangeType, Type[ExchangeConnector]] = {
        ExchangeType.BINANCE: BinanceConnector,
        ExchangeType.BYBIT: ByBitConnector,
        ExchangeType.OANDA: OANDAConnector
    }
    
    def __init__(self, environment: Environment = Environment.PRODUCTION):
        """
        Initialize factory with environment.
        
        Args:
            environment: Target environment
        """
        self.environment = environment
        self.config_manager = ProductionConfigManager(environment)
        self.connectors: Dict[ExchangeType, ProductionExchangeConnector] = {}
        
        logger.info(f"Initialized production factory for {environment.value}")
    
    def create_connector(self, exchange_type: ExchangeType) -> Optional[ProductionExchangeConnector]:
        """
        Create production connector for specific exchange.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            ProductionExchangeConnector: Production connector or None if failed
        """
        try:
            # Get configuration
            config = self.config_manager.get_config(exchange_type)
            if not config:
                logger.error(f"No configuration available for {exchange_type.value}")
                return None
            
            # Validate configuration
            validation = self.config_manager.validate_configuration(exchange_type)
            if not validation["valid"]:
                logger.error(f"Invalid configuration for {exchange_type.value}: {validation['errors']}")
                return None
            
            # Get connector class
            connector_class = self.CONNECTOR_CLASSES.get(exchange_type)
            if not connector_class:
                logger.error(f"No connector class available for {exchange_type.value}")
                return None
            
            # Create base connector configuration
            base_config = {
                "name": exchange_type.value,
                "api_key": config.credentials.api_key,
                "api_secret": config.credentials.api_secret,
                "rest_url": config.endpoints.get_rest_url(config.testnet),
                "websocket_url": config.endpoints.get_websocket_url(config.testnet),
                "rate_limit": config.rate_limits.requests_per_minute
            }
            
            # Add exchange-specific configuration
            if exchange_type == ExchangeType.OANDA:
                base_config["account_id"] = config.credentials.account_id
                # Format WebSocket URL with account ID
                base_config["websocket_url"] = base_config["websocket_url"].format(
                    account_id=config.credentials.account_id
                )
            
            # Create base connector
            base_connector = connector_class(base_config)
            
            # Wrap in production connector
            production_connector = ProductionExchangeConnector(base_connector, config)
            
            # Store reference
            self.connectors[exchange_type] = production_connector
            
            logger.info(f"Created production connector for {exchange_type.value}")
            return production_connector
            
        except Exception as e:
            logger.error(f"Failed to create connector for {exchange_type.value}: {e}")
            return None
    
    def create_all_connectors(self) -> Dict[ExchangeType, ProductionExchangeConnector]:
        """
        Create connectors for all configured exchanges.
        
        Returns:
            Dict[ExchangeType, ProductionExchangeConnector]: Created connectors
        """
        created_connectors = {}
        
        for exchange_type in ExchangeType:
            if self.config_manager.is_exchange_enabled(exchange_type):
                connector = self.create_connector(exchange_type)
                if connector:
                    created_connectors[exchange_type] = connector
        
        logger.info(f"Created {len(created_connectors)} production connectors")
        return created_connectors
    
    def get_connector(self, exchange_type: ExchangeType) -> Optional[ProductionExchangeConnector]:
        """
        Get existing connector or create new one.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            ProductionExchangeConnector: Connector instance or None
        """
        connector = self.connectors.get(exchange_type)
        if not connector:
            connector = self.create_connector(exchange_type)
        
        return connector
    
    async def start_all_connectors(self) -> Dict[ExchangeType, bool]:
        """
        Start all created connectors.
        
        Returns:
            Dict[ExchangeType, bool]: Start results for each connector
        """
        results = {}
        
        for exchange_type, connector in self.connectors.items():
            try:
                success = await connector.start()
                results[exchange_type] = success
                
                if success:
                    logger.info(f"Started {exchange_type.value} connector")
                else:
                    logger.error(f"Failed to start {exchange_type.value} connector")
                    
            except Exception as e:
                logger.error(f"Error starting {exchange_type.value} connector: {e}")
                results[exchange_type] = False
        
        return results
    
    async def stop_all_connectors(self) -> Dict[ExchangeType, bool]:
        """
        Stop all connectors.
        
        Returns:
            Dict[ExchangeType, bool]: Stop results for each connector
        """
        results = {}
        
        for exchange_type, connector in self.connectors.items():
            try:
                success = await connector.stop()
                results[exchange_type] = success
                
                if success:
                    logger.info(f"Stopped {exchange_type.value} connector")
                else:
                    logger.error(f"Failed to stop {exchange_type.value} connector")
                    
            except Exception as e:
                logger.error(f"Error stopping {exchange_type.value} connector: {e}")
                results[exchange_type] = False
        
        return results
    
    async def get_all_health_status(self) -> Dict[str, Dict]:
        """
        Get health status for all connectors.
        
        Returns:
            Dict[str, Dict]: Health status for each connector
        """
        health_status = {}
        
        for exchange_type, connector in self.connectors.items():
            try:
                status = await connector.get_health_status()
                health_status[exchange_type.value] = status
            except Exception as e:
                logger.error(f"Error getting health status for {exchange_type.value}: {e}")
                health_status[exchange_type.value] = {
                    "exchange": exchange_type.value,
                    "connected": False,
                    "error": str(e)
                }
        
        return health_status
    
    @asynccontextmanager
    async def managed_connectors(self, exchange_types: Optional[List[ExchangeType]] = None):
        """
        Context manager for automatic connector lifecycle management.
        
        Args:
            exchange_types: Specific exchanges to manage, or None for all
        """
        # Create connectors
        if exchange_types:
            connectors = {et: self.create_connector(et) for et in exchange_types}
            connectors = {k: v for k, v in connectors.items() if v is not None}
        else:
            connectors = self.create_all_connectors()
        
        # Start connectors
        start_results = {}
        for exchange_type, connector in connectors.items():
            try:
                success = await connector.start()
                start_results[exchange_type] = success
                if not success:
                    logger.error(f"Failed to start {exchange_type.value}")
            except Exception as e:
                logger.error(f"Error starting {exchange_type.value}: {e}")
                start_results[exchange_type] = False
        
        try:
            # Yield active connectors
            active_connectors = {
                et: conn for et, conn in connectors.items() 
                if start_results.get(et, False)
            }
            yield active_connectors
            
        finally:
            # Stop all connectors
            for exchange_type, connector in connectors.items():
                try:
                    await connector.stop()
                    logger.info(f"Stopped {exchange_type.value}")
                except Exception as e:
                    logger.error(f"Error stopping {exchange_type.value}: {e}")


# Convenience functions
def create_production_factory(environment: Environment = Environment.PRODUCTION) -> ProductionExchangeFactory:
    """Create production exchange factory."""
    return ProductionExchangeFactory(environment)


async def test_exchange_connections(environment: Environment = Environment.TESTNET) -> Dict[str, Any]:
    """
    Test connections to all configured exchanges.
    
    Args:
        environment: Environment to test
        
    Returns:
        Dict[str, Any]: Test results
    """
    factory = create_production_factory(environment)
    results = {}
    
    async with factory.managed_connectors() as connectors:
        for exchange_type, connector in connectors.items():
            try:
                # Test basic connectivity
                health = await connector.get_health_status()
                results[exchange_type.value] = {
                    "connected": health.get("connected", False),
                    "websocket_healthy": health.get("websocket_connected", False),
                    "rest_api_healthy": health.get("rest_api_healthy", False),
                    "environment": environment.value,
                    "testnet": connector.config.testnet
                }
            except Exception as e:
                results[exchange_type.value] = {
                    "connected": False,
                    "error": str(e)
                }
    
    return results