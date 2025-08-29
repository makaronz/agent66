"""
Failover Integration Module

Integrates failover capabilities with the existing production exchange factory
and provides a unified interface for production-ready exchange management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from contextlib import asynccontextmanager

from .production_config import ExchangeType, Environment
from .production_factory import ProductionExchangeFactory, ProductionExchangeConnector
from .failover_manager import ExchangeFailoverManager, FailoverEvent, FailoverTrigger
from .error_handling import ExchangeError, ErrorCategory, ErrorSeverity
from .recovery_strategies import global_recovery_manager

logger = logging.getLogger(__name__)


class FailoverEnabledExchangeConnector(ProductionExchangeConnector):
    """
    Enhanced production connector with integrated failover capabilities.
    
    Extends ProductionExchangeConnector to work seamlessly with the failover manager.
    """
    
    def __init__(self, base_connector, config, failover_manager: ExchangeFailoverManager):
        """
        Initialize failover-enabled connector.
        
        Args:
            base_connector: Base exchange connector
            config: Production configuration
            failover_manager: Failover manager instance
        """
        super().__init__(base_connector, config)
        self.failover_manager = failover_manager
        
        # Register with failover manager
        self.failover_manager.add_exchange(
            config.exchange_type,
            self,
            priority=config.failover_priority if hasattr(config, 'failover_priority') else 10
        )
        
        logger.info(f"Initialized failover-enabled connector for {self.name}")
    
    async def connect_websocket(self) -> bool:
        """Connect with failover integration."""
        try:
            success = await super().connect_websocket()
            
            # Update failover manager health metrics
            if self.config.exchange_type in self.failover_manager.health_metrics:
                metrics = self.failover_manager.health_metrics[self.config.exchange_type]
                metrics.is_connected = success
                
                if success:
                    metrics.update_request_result(True)
                else:
                    metrics.update_request_result(False)
            
            return success
            
        except Exception as e:
            # Update failover metrics on connection failure
            if self.config.exchange_type in self.failover_manager.health_metrics:
                metrics = self.failover_manager.health_metrics[self.config.exchange_type]
                metrics.is_connected = False
                metrics.update_request_result(False)
            
            raise
    
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Fetch with failover-aware error handling."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            data = await super().fetch_rest_data(endpoint, params)
            
            # Update success metrics
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            if self.config.exchange_type in self.failover_manager.health_metrics:
                metrics = self.failover_manager.health_metrics[self.config.exchange_type]
                metrics.update_request_result(True, latency_ms)
            
            return data
            
        except Exception as e:
            # Update failure metrics
            if self.config.exchange_type in self.failover_manager.health_metrics:
                metrics = self.failover_manager.health_metrics[self.config.exchange_type]
                metrics.update_request_result(False)
            
            # Check if this should trigger failover
            await self._handle_request_error(e)
            
            raise
    
    async def _handle_request_error(self, error: Exception):
        """Handle request error and potentially trigger failover."""
        try:
            # Classify the error
            from .error_handling import handle_exchange_error
            
            exchange_error = await handle_exchange_error(
                error,
                self.config.exchange_type,
                "rest_request"
            )
            
            # Check if this error should trigger failover
            if self._should_trigger_failover(exchange_error):
                logger.warning(f"Error may trigger failover for {self.name}: {exchange_error.error_message}")
                
                # The failover manager's health check loop will detect the degraded state
                # and trigger failover if rules are met
            
        except Exception as e:
            logger.error(f"Error handling request error: {e}")
    
    def _should_trigger_failover(self, error: ExchangeError) -> bool:
        """Determine if error should contribute to failover decision."""
        # Critical errors should contribute to failover
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return True
        
        # Connection and authentication errors
        if error.category in [ErrorCategory.CONNECTION, ErrorCategory.AUTHENTICATION]:
            return True
        
        # Rate limit errors if excessive
        if error.category == ErrorCategory.RATE_LIMIT and error.retry_count >= 3:
            return True
        
        return False


class ProductionFailoverFactory(ProductionExchangeFactory):
    """
    Enhanced production factory with integrated failover management.
    
    Extends ProductionExchangeFactory to create failover-enabled connectors.
    """
    
    def __init__(self, environment: Environment = Environment.PRODUCTION):
        """
        Initialize production failover factory.
        
        Args:
            environment: Target environment
        """
        super().__init__(environment)
        
        # Initialize failover manager
        self.failover_manager = ExchangeFailoverManager(environment)
        
        # Enhanced connector storage
        self.failover_connectors: Dict[ExchangeType, FailoverEnabledExchangeConnector] = {}
        
        logger.info(f"Initialized production failover factory for {environment.value}")
    
    def create_connector(self, exchange_type: ExchangeType) -> Optional[FailoverEnabledExchangeConnector]:
        """
        Create failover-enabled production connector.
        
        Args:
            exchange_type: Type of exchange
            
        Returns:
            FailoverEnabledExchangeConnector: Enhanced connector or None if failed
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
                base_config["websocket_url"] = base_config["websocket_url"].format(
                    account_id=config.credentials.account_id
                )
            
            # Create base connector
            base_connector = connector_class(base_config)
            
            # Create failover-enabled connector
            failover_connector = FailoverEnabledExchangeConnector(
                base_connector, 
                config, 
                self.failover_manager
            )
            
            # Store reference
            self.failover_connectors[exchange_type] = failover_connector
            self.connectors[exchange_type] = failover_connector  # Also store in parent
            
            logger.info(f"Created failover-enabled connector for {exchange_type.value}")
            return failover_connector
            
        except Exception as e:
            logger.error(f"Failed to create failover connector for {exchange_type.value}: {e}")
            return None
    
    def create_all_connectors(self) -> Dict[ExchangeType, FailoverEnabledExchangeConnector]:
        """
        Create failover-enabled connectors for all configured exchanges.
        
        Returns:
            Dict[ExchangeType, FailoverEnabledExchangeConnector]: Created connectors
        """
        created_connectors = {}
        
        for exchange_type in ExchangeType:
            if self.config_manager.is_exchange_enabled(exchange_type):
                connector = self.create_connector(exchange_type)
                if connector:
                    created_connectors[exchange_type] = connector
        
        logger.info(f"Created {len(created_connectors)} failover-enabled connectors")
        return created_connectors
    
    async def start_all_connectors(self) -> Dict[ExchangeType, bool]:
        """Start all connectors and failover monitoring."""
        # Start connectors
        results = await super().start_all_connectors()
        
        # Start failover monitoring
        await self.failover_manager.start_monitoring()
        
        logger.info("Started all connectors with failover monitoring")
        return results
    
    async def stop_all_connectors(self) -> Dict[ExchangeType, bool]:
        """Stop all connectors and failover monitoring."""
        # Stop failover monitoring
        await self.failover_manager.stop_monitoring()
        
        # Stop connectors
        results = await super().stop_all_connectors()
        
        logger.info("Stopped all connectors and failover monitoring")
        return results
    
    def get_active_exchange(self) -> Optional[ExchangeType]:
        """Get currently active exchange from failover manager."""
        return self.failover_manager.active_exchange
    
    def get_active_connector(self) -> Optional[FailoverEnabledExchangeConnector]:
        """Get currently active connector."""
        active_exchange = self.get_active_exchange()
        if active_exchange:
            return self.failover_connectors.get(active_exchange)
        return None
    
    async def manual_failover(self, target_exchange: ExchangeType) -> bool:
        """Manually trigger failover to specific exchange."""
        return await self.failover_manager.manual_failover(target_exchange)
    
    async def test_failover_scenarios(self) -> Dict[str, Any]:
        """Test all failover scenarios."""
        from .failover_manager import test_all_failover_scenarios
        return await test_all_failover_scenarios()
    
    def get_failover_status(self) -> Dict[str, Any]:
        """Get comprehensive failover status."""
        return self.failover_manager.get_status()
    
    @asynccontextmanager
    async def managed_failover_connectors(self, exchange_types: Optional[List[ExchangeType]] = None):
        """
        Context manager for automatic failover-enabled connector lifecycle management.
        
        Args:
            exchange_types: Specific exchanges to manage, or None for all
        """
        # Create connectors
        if exchange_types:
            connectors = {et: self.create_connector(et) for et in exchange_types}
            connectors = {k: v for k, v in connectors.items() if v is not None}
        else:
            connectors = self.create_all_connectors()
        
        # Start connectors and failover monitoring
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
        
        # Start failover monitoring
        await self.failover_manager.start_monitoring()
        
        try:
            # Yield active connectors and failover manager
            active_connectors = {
                et: conn for et, conn in connectors.items() 
                if start_results.get(et, False)
            }
            yield {
                "connectors": active_connectors,
                "failover_manager": self.failover_manager,
                "active_exchange": self.failover_manager.active_exchange,
                "get_active_connector": lambda: self.get_active_connector()
            }
            
        finally:
            # Stop failover monitoring
            await self.failover_manager.stop_monitoring()
            
            # Stop all connectors
            for exchange_type, connector in connectors.items():
                try:
                    await connector.stop()
                    logger.info(f"Stopped {exchange_type.value}")
                except Exception as e:
                    logger.error(f"Error stopping {exchange_type.value}: {e}")


class FailoverAwareDataPipeline:
    """
    Data pipeline that automatically uses the active exchange from failover manager.
    
    Provides a unified interface for data ingestion that automatically adapts
    to failover events.
    """
    
    def __init__(self, factory: ProductionFailoverFactory):
        """
        Initialize failover-aware data pipeline.
        
        Args:
            factory: Production failover factory
        """
        self.factory = factory
        self.failover_manager = factory.failover_manager
        
        # Data handlers
        self.data_callbacks: List[callable] = []
        
        # State
        self.is_running = False
        self._data_task: Optional[asyncio.Task] = None
        
        # Register for failover events
        self.failover_manager.add_failover_callback(self._handle_failover_event)
        
        logger.info("Initialized failover-aware data pipeline")
    
    def add_data_callback(self, callback: callable):
        """Add callback for processed data."""
        self.data_callbacks.append(callback)
    
    async def start_data_ingestion(self, streams: List[str]):
        """
        Start data ingestion from active exchange.
        
        Args:
            streams: List of streams to subscribe to
        """
        if self.is_running:
            logger.warning("Data ingestion already running")
            return
        
        self.is_running = True
        self._data_task = asyncio.create_task(self._data_ingestion_loop(streams))
        
        logger.info("Started failover-aware data ingestion")
    
    async def stop_data_ingestion(self):
        """Stop data ingestion."""
        self.is_running = False
        
        if self._data_task:
            self._data_task.cancel()
            try:
                await self._data_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped data ingestion")
    
    async def _data_ingestion_loop(self, streams: List[str]):
        """Main data ingestion loop with failover awareness."""
        while self.is_running:
            try:
                # Get active connector
                active_connector = self.factory.get_active_connector()
                
                if not active_connector:
                    logger.warning("No active connector available, waiting...")
                    await asyncio.sleep(5.0)
                    continue
                
                # Subscribe to streams
                if not await active_connector.subscribe_to_streams(streams):
                    logger.error(f"Failed to subscribe to streams on {active_connector.name}")
                    await asyncio.sleep(5.0)
                    continue
                
                # Listen for messages
                await active_connector.listen_for_messages(self._process_data)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Data ingestion error: {e}")
                await asyncio.sleep(5.0)  # Wait before retry
    
    async def _process_data(self, data: Dict[str, Any]):
        """Process incoming data and notify callbacks."""
        try:
            # Add metadata about source exchange
            data["source_exchange"] = self.failover_manager.active_exchange.value if self.failover_manager.active_exchange else "unknown"
            data["failover_state"] = self.failover_manager.current_state.value
            
            # Notify all callbacks
            for callback in self.data_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Data callback error: {e}")
        
        except Exception as e:
            logger.error(f"Data processing error: {e}")
    
    async def _handle_failover_event(self, event: FailoverEvent):
        """Handle failover events."""
        logger.info(f"Failover event: {event.from_exchange.value} -> {event.to_exchange.value}")
        
        # Data ingestion will automatically adapt to the new active exchange
        # in the next iteration of the ingestion loop


# Convenience functions
def create_production_failover_factory(environment: Environment = Environment.PRODUCTION) -> ProductionFailoverFactory:
    """Create production failover factory."""
    return ProductionFailoverFactory(environment)


async def test_production_failover_system(environment: Environment = Environment.TESTNET) -> Dict[str, Any]:
    """
    Comprehensive test of the production failover system.
    
    Args:
        environment: Environment to test
        
    Returns:
        Dict[str, Any]: Test results
    """
    logger.info(f"Testing production failover system in {environment.value}")
    
    test_results = {
        "test_timestamp": asyncio.get_event_loop().time(),
        "environment": environment.value,
        "tests": {}
    }
    
    try:
        # Create factory
        factory = create_production_failover_factory(environment)
        
        async with factory.managed_failover_connectors() as context:
            connectors = context["connectors"]
            failover_manager = context["failover_manager"]
            
            # Test 1: Basic connectivity
            test_results["tests"]["connectivity"] = {
                "connected_exchanges": len(connectors),
                "active_exchange": failover_manager.active_exchange.value if failover_manager.active_exchange else None,
                "health_scores": {
                    ex.value: metrics.get_health_score()
                    for ex, metrics in failover_manager.health_metrics.items()
                }
            }
            
            # Test 2: Health monitoring
            logger.info("Testing health monitoring...")
            await asyncio.sleep(2.0)  # Let health checks run
            
            health_status = failover_manager.get_status()
            test_results["tests"]["health_monitoring"] = {
                "exchanges_monitored": len(health_status["exchange_health"]),
                "monitoring_active": failover_manager._running,
                "health_scores": health_status["exchange_health"]
            }
            
            # Test 3: Failover scenarios
            logger.info("Testing failover scenarios...")
            scenario_results = await factory.test_failover_scenarios()
            test_results["tests"]["failover_scenarios"] = scenario_results
            
            # Test 4: Data pipeline integration
            logger.info("Testing data pipeline integration...")
            pipeline = FailoverAwareDataPipeline(factory)
            
            # Add test callback
            received_data = []
            pipeline.add_data_callback(lambda data: received_data.append(data))
            
            # Start brief data ingestion test
            await pipeline.start_data_ingestion(["btcusdt@trade"])
            await asyncio.sleep(5.0)  # Collect data for 5 seconds
            await pipeline.stop_data_ingestion()
            
            test_results["tests"]["data_pipeline"] = {
                "data_received": len(received_data),
                "pipeline_functional": len(received_data) > 0,
                "sample_data": received_data[:3] if received_data else []
            }
            
            test_results["success"] = True
            
    except Exception as e:
        logger.error(f"Failover system test failed: {e}")
        test_results["success"] = False
        test_results["error"] = str(e)
    
    test_results["duration_seconds"] = asyncio.get_event_loop().time() - test_results["test_timestamp"]
    
    return test_results


async def run_production_failover_demo():
    """
    Run a demonstration of the production failover system.
    
    This function showcases the key capabilities of the failover system.
    """
    logger.info("Starting production failover system demonstration")
    
    try:
        # Create factory for testnet environment
        factory = create_production_failover_factory(Environment.TESTNET)
        
        async with factory.managed_failover_connectors() as context:
            connectors = context["connectors"]
            failover_manager = context["failover_manager"]
            get_active_connector = context["get_active_connector"]
            
            logger.info(f"Connected to {len(connectors)} exchanges")
            logger.info(f"Active exchange: {failover_manager.active_exchange.value}")
            
            # Create data pipeline
            pipeline = FailoverAwareDataPipeline(factory)
            
            # Add demo data handler
            def demo_data_handler(data):
                logger.info(f"Received data from {data.get('source_exchange', 'unknown')}: {data.get('symbol', 'N/A')}")
            
            pipeline.add_data_callback(demo_data_handler)
            
            # Start data ingestion
            await pipeline.start_data_ingestion(["btcusdt@trade", "ethusdt@trade"])
            
            # Let it run for a bit
            logger.info("Data ingestion running... (10 seconds)")
            await asyncio.sleep(10.0)
            
            # Demonstrate manual failover
            if len(connectors) > 1:
                current_active = failover_manager.active_exchange
                other_exchanges = [ex for ex in connectors.keys() if ex != current_active]
                
                if other_exchanges:
                    target_exchange = other_exchanges[0]
                    logger.info(f"Demonstrating manual failover to {target_exchange.value}")
                    
                    success = await factory.manual_failover(target_exchange)
                    if success:
                        logger.info(f"Failover successful! New active: {failover_manager.active_exchange.value}")
                        
                        # Let data flow from new exchange
                        await asyncio.sleep(5.0)
                    else:
                        logger.error("Manual failover failed")
            
            # Show final status
            status = factory.get_failover_status()
            logger.info(f"Final status: {status['current_state']} - Active: {status['active_exchange']}")
            
            # Stop data ingestion
            await pipeline.stop_data_ingestion()
            
        logger.info("Production failover demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # Run demonstration if executed directly
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_production_failover_demo())