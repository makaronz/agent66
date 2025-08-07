"""
Kafka Producer for Market Data Streaming

Implements async Kafka producer for streaming real-time market data
from all exchanges with proper serialization, partitioning, and error handling.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Market data types."""
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    KLINE = "kline"
    HEALTH = "health"


class MarketDataMessage(BaseModel):
    """Unified market data message format."""
    exchange: str
    symbol: str
    data_type: DataType
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any]
    message_id: str = Field(default_factory=lambda: str(int(time.time() * 1000000)))


@dataclass
class KafkaConfig:
    """Kafka configuration."""
    bootstrap_servers: List[str]
    topic_prefix: str = "market_data"
    compression_type: str = "gzip"
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 5
    buffer_memory: int = 33554432
    max_request_size: int = 1048576
    request_timeout_ms: int = 30000
    delivery_timeout_ms: int = 120000


class KafkaProducerManager:
    """
    Async Kafka producer manager for market data streaming.
    
    Handles connection management, message serialization, topic routing,
    error handling, and performance optimization.
    """
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka producer manager.
        
        Args:
            config: Kafka configuration
        """
        self.config = config
        self.producer = None
        self.connected = False
        self.message_count = 0
        self.error_count = 0
        self.last_error_time = 0
        
        # Topic templates
        self.topic_templates = {
            DataType.TRADE: f"{config.topic_prefix}.{{exchange}}.{{symbol}}.trades",
            DataType.ORDERBOOK: f"{config.topic_prefix}.{{exchange}}.{{symbol}}.orderbook",
            DataType.KLINE: f"{config.topic_prefix}.{{exchange}}.{{symbol}}.klines",
            DataType.HEALTH: f"{config.topic_prefix}.{{exchange}}.health"
        }
        
        # Performance tracking
        self.performance_metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'total_bytes_sent': 0,
            'average_message_size': 0,
            'last_message_time': 0
        }
        
        logger.info(f"Initialized Kafka producer for {config.bootstrap_servers}")
    
    async def connect(self) -> bool:
        """
        Connect to Kafka cluster.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Kafka cluster: {self.config.bootstrap_servers}")
            
            # Create Kafka producer with configuration
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                compression_type=self.config.compression_type,
                acks=self.config.acks,
                retries=self.config.retries,
                batch_size=self.config.batch_size,
                linger_ms=self.config.linger_ms,
                buffer_memory=self.config.buffer_memory,
                max_request_size=self.config.max_request_size,
                request_timeout_ms=self.config.request_timeout_ms,
                delivery_timeout_ms=self.config.delivery_timeout_ms,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Test connection
            await self._test_connection()
            
            self.connected = True
            logger.info("Kafka producer connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from Kafka cluster.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.producer:
                # Flush any pending messages
                self.producer.flush()
                
                # Close producer
                self.producer.close()
                self.producer = None
                
                self.connected = False
                logger.info("Kafka producer disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from Kafka: {e}")
            return False
    
    async def send_market_data(self, exchange: str, symbol: str, data_type: DataType, 
                             data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Send market data to Kafka.
        
        Args:
            exchange: Exchange name (binance, bybit, oanda)
            symbol: Trading symbol (BTCUSDT, EUR_USD, etc.)
            data_type: Type of market data
            data: Market data payload
            key: Optional message key for partitioning
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            if not self.connected or not self.producer:
                logger.error("Kafka producer not connected")
                return False
            
            # Create market data message
            message = MarketDataMessage(
                exchange=exchange,
                symbol=symbol,
                data_type=data_type,
                data=data
            )
            
            # Determine topic
            topic = self._get_topic(exchange, symbol, data_type)
            
            # Prepare message key for partitioning
            message_key = key or f"{exchange}_{symbol}"
            
            # Send message asynchronously
            future = self.producer.send(
                topic=topic,
                key=message_key,
                value=message.model_dump()
            )
            
            # Wait for delivery confirmation
            record_metadata = await asyncio.get_event_loop().run_in_executor(
                None, future.get, self.config.delivery_timeout_ms / 1000
            )
            
            # Update metrics
            self._update_metrics(record_metadata)
            
            logger.debug(f"Message sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
            
        except KafkaTimeoutError as e:
            logger.error(f"Kafka timeout error: {e}")
            self.error_count += 1
            self.last_error_time = time.time()
            return False
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            self.error_count += 1
            self.last_error_time = time.time()
            return False
        except Exception as e:
            logger.error(f"Failed to send market data: {e}")
            self.error_count += 1
            self.last_error_time = time.time()
            return False
    
    async def send_health_status(self, exchange: str, health_data: Dict[str, Any]) -> bool:
        """
        Send exchange health status to Kafka.
        
        Args:
            exchange: Exchange name
            health_data: Health status data
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        return await self.send_market_data(
            exchange=exchange,
            symbol="",  # No symbol for health data
            data_type=DataType.HEALTH,
            data=health_data,
            key=exchange
        )
    
    def _get_topic(self, exchange: str, symbol: str, data_type: DataType) -> str:
        """
        Get Kafka topic name for given exchange, symbol, and data type.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            data_type: Type of market data
            
        Returns:
            str: Kafka topic name
        """
        template = self.topic_templates[data_type]
        
        if data_type == DataType.HEALTH:
            return template.format(exchange=exchange)
        else:
            return template.format(exchange=exchange, symbol=symbol.lower())
    
    def _update_metrics(self, record_metadata):
        """Update performance metrics."""
        self.performance_metrics['messages_sent'] += 1
        self.performance_metrics['total_bytes_sent'] += record_metadata.serialized_value_size
        self.performance_metrics['last_message_time'] = time.time()
        
        # Calculate average message size
        if self.performance_metrics['messages_sent'] > 0:
            self.performance_metrics['average_message_size'] = (
                self.performance_metrics['total_bytes_sent'] / 
                self.performance_metrics['messages_sent']
            )
    
    async def _test_connection(self):
        """Test Kafka connection."""
        try:
            # Send a test message to verify connection
            test_topic = f"{self.config.topic_prefix}.test"
            future = self.producer.send(test_topic, value={"test": "connection"})
            
            # Wait for delivery
            await asyncio.get_event_loop().run_in_executor(
                None, future.get, 5  # 5 second timeout
            )
            
            logger.info("Kafka connection test successful")
            
        except Exception as e:
            logger.error(f"Kafka connection test failed: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get Kafka producer health status.
        
        Returns:
            Dict: Health status information
        """
        return {
            "connected": self.connected,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "last_error_time": self.last_error_time,
            "performance_metrics": self.performance_metrics.copy(),
            "timestamp": time.time()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics.
        
        Returns:
            Dict: Performance metrics
        """
        return {
            "messages_sent": self.performance_metrics['messages_sent'],
            "messages_failed": self.performance_metrics['messages_failed'],
            "total_bytes_sent": self.performance_metrics['total_bytes_sent'],
            "average_message_size": self.performance_metrics['average_message_size'],
            "last_message_time": self.performance_metrics['last_message_time'],
            "error_rate": (
                self.performance_metrics['messages_failed'] / 
                max(1, self.performance_metrics['messages_sent'] + self.performance_metrics['messages_failed'])
            ),
            "timestamp": time.time()
        }


class DataSerializer:
    """
    Data serialization utilities for market data.
    
    Handles data validation, compression, and format conversion.
    """
    
    @staticmethod
    def serialize_market_data(data: Dict[str, Any]) -> bytes:
        """
        Serialize market data to bytes.
        
        Args:
            data: Market data dictionary
            
        Returns:
            bytes: Serialized data
        """
        try:
            return json.dumps(data, default=str, separators=(',', ':')).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize market data: {e}")
            raise
    
    @staticmethod
    def deserialize_market_data(data: bytes) -> Dict[str, Any]:
        """
        Deserialize market data from bytes.
        
        Args:
            data: Serialized data bytes
            
        Returns:
            Dict: Deserialized market data
        """
        try:
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to deserialize market data: {e}")
            raise
    
    @staticmethod
    def validate_market_data(data: Dict[str, Any]) -> bool:
        """
        Validate market data structure.
        
        Args:
            data: Market data dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ['exchange', 'symbol', 'timestamp']
        
        try:
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate timestamp
            if not isinstance(data['timestamp'], (int, float)):
                logger.error("Invalid timestamp format")
                return False
            
            # Validate exchange
            if data['exchange'] not in ['binance', 'bybit', 'oanda']:
                logger.error(f"Invalid exchange: {data['exchange']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False


class TopicManager:
    """
    Kafka topic management utilities.
    
    Handles topic creation, configuration, and routing logic.
    """
    
    def __init__(self, topic_prefix: str = "market_data"):
        """
        Initialize topic manager.
        
        Args:
            topic_prefix: Prefix for all topics
        """
        self.topic_prefix = topic_prefix
        self.topic_configs = {
            "trades": {
                "partitions": 6,
                "replication_factor": 3,
                "retention_ms": 86400000,  # 24 hours
                "cleanup_policy": "delete"
            },
            "orderbook": {
                "partitions": 6,
                "replication_factor": 3,
                "retention_ms": 3600000,  # 1 hour
                "cleanup_policy": "delete"
            },
            "klines": {
                "partitions": 6,
                "replication_factor": 3,
                "retention_ms": 604800000,  # 7 days
                "cleanup_policy": "delete"
            },
            "health": {
                "partitions": 3,
                "replication_factor": 3,
                "retention_ms": 3600000,  # 1 hour
                "cleanup_policy": "delete"
            }
        }
    
    def get_topic_name(self, exchange: str, symbol: str, data_type: str) -> str:
        """
        Generate topic name for given parameters.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            data_type: Type of data
            
        Returns:
            str: Topic name
        """
        if data_type == "health":
            return f"{self.topic_prefix}.{exchange}.health"
        else:
            return f"{self.topic_prefix}.{exchange}.{symbol.lower()}.{data_type}"
    
    def get_topic_config(self, data_type: str) -> Dict[str, Any]:
        """
        Get topic configuration for data type.
        
        Args:
            data_type: Type of data
            
        Returns:
            Dict: Topic configuration
        """
        return self.topic_configs.get(data_type, {})
    
    def get_partition_key(self, exchange: str, symbol: str) -> str:
        """
        Generate partition key for consistent partitioning.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            
        Returns:
            str: Partition key
        """
        return f"{exchange}_{symbol}".lower()
