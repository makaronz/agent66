"""
Data Pipeline Ingestion Module

Real-time market data ingestion from multiple exchanges with WebSocket and REST API connections.
Integrates Binance, ByBit, and OANDA exchanges with Kafka streaming.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from .exchange_connectors import ExchangeConnector, BinanceConnector, ByBitConnector, OANDAConnector
from monitoring.data_quality_metrics import set_freshness
from .kafka_producer import KafkaProducerManager, KafkaConfig, DataType, DataSerializer, TopicManager

logger = logging.getLogger(__name__)


@dataclass
class ExchangeConfig:
    """Configuration for exchange connections."""
    name: str
    enabled: bool = True
    api_key: str = ""
    api_secret: str = ""
    account_id: str = ""  # For OANDA
    websocket_url: str = ""
    rest_url: str = ""
    rate_limit: int = 1200
    symbols: List[str] = None
    data_types: List[str] = None


class DataIngestion:
    """
    Main data ingestion service.
    
    Manages connections to multiple exchanges, handles real-time data streaming,
    normalizes data formats, and streams to Kafka.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data ingestion service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.exchanges: Dict[str, ExchangeConnector] = {}
        self.kafka_producer: Optional[KafkaProducerManager] = None
        self.topic_manager: Optional[TopicManager] = None
        self.data_serializer: Optional[DataSerializer] = None
        
        # Service state
        self.running = False
        self.health_check_interval = 30  # seconds
        self.reconnection_interval = 5   # seconds
        
        # Performance tracking
        self.metrics = {
            'total_messages_processed': 0,
            'total_messages_sent': 0,
            'total_errors': 0,
            'start_time': 0,
            'last_health_check': 0
        }
        
        # Initialize components
        self._initialize_exchanges()
        self._initialize_kafka()
        
        logger.info("Data ingestion service initialized")
    
    def _initialize_exchanges(self):
        """Initialize exchange connectors."""
        exchange_configs = self.config.get('exchanges', {})
        
        for exchange_name, exchange_config in exchange_configs.items():
            if not exchange_config.get('enabled', True):
                continue
            
            try:
                if exchange_name == 'binance':
                    connector = BinanceConnector(exchange_config)
                elif exchange_name == 'bybit':
                    connector = ByBitConnector(exchange_config)
                elif exchange_name == 'oanda':
                    connector = OANDAConnector(exchange_config)
                else:
                    logger.warning(f"Unknown exchange: {exchange_name}")
                    continue
                
                self.exchanges[exchange_name] = connector
                logger.info(f"Initialized {exchange_name} connector")
                
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_name} connector: {e}")
    
    def _initialize_kafka(self):
        """Initialize Kafka producer."""
        try:
            kafka_config = self.config.get('kafka', {})
            
            # Create Kafka configuration
            kafka_cfg = KafkaConfig(
                bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                topic_prefix=kafka_config.get('topic_prefix', 'market_data'),
                compression_type=kafka_config.get('compression_type', 'gzip'),
                acks=kafka_config.get('acks', 'all'),
                retries=kafka_config.get('retries', 3),
                batch_size=kafka_config.get('batch_size', 16384),
                linger_ms=kafka_config.get('linger_ms', 5)
            )
            
            self.kafka_producer = KafkaProducerManager(kafka_cfg)
            self.topic_manager = TopicManager(kafka_cfg.topic_prefix)
            self.data_serializer = DataSerializer()
            
            logger.info("Kafka producer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
    
    async def start(self) -> bool:
        """
        Start the data ingestion service.
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        try:
            logger.info("Starting data ingestion service")
            
            # Connect to Kafka
            if self.kafka_producer:
                kafka_connected = await self.kafka_producer.connect()
                if not kafka_connected:
                    logger.error("Failed to connect to Kafka")
                    return False
            
            # Start exchange connectors
            exchange_tasks = []
            for exchange_name, connector in self.exchanges.items():
                try:
                    # Start connector
                    success = await connector.start()
                    if success:
                        # Subscribe to streams
                        await self._subscribe_to_streams(exchange_name, connector)
                        
                        # Start message listener
                        task = asyncio.create_task(
                            self._listen_to_exchange(exchange_name, connector)
                        )
                        exchange_tasks.append(task)
                        
                        logger.info(f"Started {exchange_name} connector")
                    else:
                        logger.error(f"Failed to start {exchange_name} connector")
                        
                except Exception as e:
                    logger.error(f"Error starting {exchange_name} connector: {e}")
            
            # Start health monitoring
            health_task = asyncio.create_task(self._health_monitor())
            
            # Start performance monitoring
            metrics_task = asyncio.create_task(self._performance_monitor())
            
            # Store tasks for cleanup
            self.tasks = exchange_tasks + [health_task, metrics_task]
            
            self.running = True
            self.metrics['start_time'] = time.time()
            
            logger.info("Data ingestion service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start data ingestion service: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the data ingestion service.
        
        Returns:
            bool: True if shutdown successful, False otherwise
        """
        try:
            logger.info("Stopping data ingestion service")
            
            self.running = False
            
            # Cancel all tasks
            if hasattr(self, 'tasks'):
                for task in self.tasks:
                    task.cancel()
                
                # Wait for tasks to complete
                await asyncio.gather(*self.tasks, return_exceptions=True)
            
            # Stop exchange connectors
            for exchange_name, connector in self.exchanges.items():
                try:
                    await connector.stop()
                    logger.info(f"Stopped {exchange_name} connector")
                except Exception as e:
                    logger.error(f"Error stopping {exchange_name} connector: {e}")
            
            # Disconnect from Kafka
            if self.kafka_producer:
                await self.kafka_producer.disconnect()
                logger.info("Disconnected from Kafka")
            
            logger.info("Data ingestion service stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop data ingestion service: {e}")
            return False
    
    async def _subscribe_to_streams(self, exchange_name: str, connector: ExchangeConnector):
        """Subscribe to exchange-specific data streams."""
        try:
            exchange_config = self.config['exchanges'][exchange_name]
            symbols = exchange_config.get('symbols', [])
            data_types = exchange_config.get('data_types', ['trade', 'orderbook'])
            
            if not symbols:
                logger.warning(f"No symbols configured for {exchange_name}")
                return
            
            # Create stream names based on exchange
            streams = []
            for symbol in symbols:
                for data_type in data_types:
                    if exchange_name == 'binance':
                        if data_type == 'trade':
                            streams.append(f"{symbol.lower()}@trade")
                        elif data_type == 'orderbook':
                            streams.append(f"{symbol.lower()}@depth")
                        elif data_type == 'kline':
                            streams.append(f"{symbol.lower()}@kline_1m")
                    elif exchange_name == 'bybit':
                        if data_type == 'trade':
                            streams.append(f"publicTrade.{symbol}")
                        elif data_type == 'orderbook':
                            streams.append(f"orderbook.1.{symbol}")
                        elif data_type == 'kline':
                            streams.append(f"kline.1.{symbol}")
                    elif exchange_name == 'oanda':
                        # OANDA uses different subscription format
                        streams.append(symbol)
            
            # Subscribe to streams
            if streams:
                success = await connector.subscribe_to_streams(streams)
                if success:
                    logger.info(f"Subscribed to {len(streams)} streams for {exchange_name}")
                else:
                    logger.error(f"Failed to subscribe to streams for {exchange_name}")
            
        except Exception as e:
            logger.error(f"Error subscribing to streams for {exchange_name}: {e}")
    
    async def _listen_to_exchange(self, exchange_name: str, connector: ExchangeConnector):
        """Listen for messages from exchange and process them."""
        try:
            async def message_handler(data: Dict[str, Any]):
                """Handle incoming market data messages."""
                try:
                    # Determine data type from the data structure
                    data_type = self._determine_data_type(data, exchange_name)
                    
                    # Extract symbol from data
                    symbol = data.get('symbol', '')
                    # Update freshness gauge if timestamp present
                    ts = data.get('timestamp')
                    if ts:
                        try:
                            now = time.time()
                            age = max(0.0, now - float(ts))
                            set_freshness(exchange_name, symbol or 'unknown', age)
                        except Exception:
                            pass
                    
                    # Send to Kafka
                    if self.kafka_producer and symbol:
                        success = await self.kafka_producer.send_market_data(
                            exchange=exchange_name,
                            symbol=symbol,
                            data_type=data_type,
                            data=data
                        )
                        
                        if success:
                            self.metrics['total_messages_sent'] += 1
                        else:
                            self.metrics['total_errors'] += 1
                    
                    self.metrics['total_messages_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing message from {exchange_name}: {e}")
                    self.metrics['total_errors'] += 1
            
            # Start listening for messages
            await connector.listen_for_messages(message_handler)
            
        except Exception as e:
            logger.error(f"Error in exchange listener for {exchange_name}: {e}")
    
    def _determine_data_type(self, data: Dict[str, Any], exchange_name: str) -> DataType:
        """Determine the data type from the message structure."""
        try:
            # Check for specific fields that indicate data type
            if 'price' in data and 'quantity' in data and 'side' in data:
                return DataType.TRADE
            elif 'bids' in data and 'asks' in data:
                return DataType.ORDERBOOK
            elif 'open' in data and 'high' in data and 'low' in data and 'close' in data:
                return DataType.KLINE
            else:
                # Default to trade data
                return DataType.TRADE
                
        except Exception:
            return DataType.TRADE
    
    async def _health_monitor(self):
        """Monitor health of all exchange connectors and Kafka."""
        while self.running:
            try:
                current_time = time.time()
                
                # Check exchange health
                for exchange_name, connector in self.exchanges.items():
                    try:
                        health_status = await connector.get_health_status()
                        
                        # Send health status to Kafka
                        if self.kafka_producer:
                            await self.kafka_producer.send_health_status(
                                exchange=exchange_name,
                                health_data=health_status
                            )
                        
                        # Log health status
                        if not health_status.get('connected', False):
                            logger.warning(f"{exchange_name} health check failed: {health_status}")
                        
                    except Exception as e:
                        logger.error(f"Health check failed for {exchange_name}: {e}")
                
                # Check Kafka health
                if self.kafka_producer:
                    kafka_health = self.kafka_producer.get_health_status()
                    if not kafka_health.get('connected', False):
                        logger.warning(f"Kafka health check failed: {kafka_health}")
                
                self.metrics['last_health_check'] = current_time
                
                # Wait for next health check
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _performance_monitor(self):
        """Monitor performance metrics."""
        while self.running:
            try:
                # Log performance metrics every 60 seconds
                await asyncio.sleep(60)
                
                if self.running:
                    self._log_performance_metrics()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    def _log_performance_metrics(self):
        """Log current performance metrics."""
        try:
            uptime = time.time() - self.metrics['start_time']
            messages_per_second = self.metrics['total_messages_processed'] / max(1, uptime)
            error_rate = self.metrics['total_errors'] / max(1, self.metrics['total_messages_processed'])
            
            logger.info(f"Performance Metrics - "
                       f"Uptime: {uptime:.1f}s, "
                       f"Messages: {self.metrics['total_messages_processed']}, "
                       f"Sent: {self.metrics['total_messages_sent']}, "
                       f"Errors: {self.metrics['total_errors']}, "
                       f"Rate: {messages_per_second:.2f} msg/s, "
                       f"Error Rate: {error_rate:.2%}")
            
            # Log Kafka metrics if available
            if self.kafka_producer:
                kafka_metrics = self.kafka_producer.get_performance_metrics()
                logger.info(f"Kafka Metrics - "
                           f"Messages Sent: {kafka_metrics['messages_sent']}, "
                           f"Error Rate: {kafka_metrics['error_rate']:.2%}, "
                           f"Avg Size: {kafka_metrics['average_message_size']:.0f} bytes")
            
        except Exception as e:
            logger.error(f"Error logging performance metrics: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the data ingestion service.
        
        Returns:
            Dict: Health status information
        """
        try:
            exchange_health = {}
            for exchange_name, connector in self.exchanges.items():
                try:
                    exchange_health[exchange_name] = connector.get_health_status()
                except Exception as e:
                    exchange_health[exchange_name] = {
                        "error": str(e),
                        "connected": False
                    }
            
            kafka_health = {}
            if self.kafka_producer:
                kafka_health = self.kafka_producer.get_health_status()
            
            return {
                "service": "data_ingestion",
                "running": self.running,
                "exchanges": exchange_health,
                "kafka": kafka_health,
                "metrics": self.metrics.copy(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "service": "data_ingestion",
                "running": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def get_exchange_connector(self, exchange_name: str) -> Optional[ExchangeConnector]:
        """
        Get exchange connector by name.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            ExchangeConnector: Exchange connector instance or None
        """
        return self.exchanges.get(exchange_name)
    
    def get_kafka_producer(self) -> Optional[KafkaProducerManager]:
        """
        Get Kafka producer instance.
        
        Returns:
            KafkaProducerManager: Kafka producer instance or None
        """
        return self.kafka_producer
