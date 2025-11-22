"""
Optimized Async Kafka Producer for Market Data Streaming

Implements high-performance async Kafka producer with batching, connection pooling,
and non-blocking message delivery to achieve <10ms message latency.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from aiokafka import AIOKafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Market data types."""
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    KLINE = "kline"
    HEALTH = "health"


@dataclass
class KafkaConfig:
    """Kafka producer configuration."""
    bootstrap_servers: List[str]
    topic_prefix: str = "smc_market_data"
    batch_size: int = 1000  # Increased from 100 for better throughput
    linger_ms: int = 5      # Reduced for lower latency
    compression_type: str = 'gzip'
    max_request_size: int = 1048576
    delivery_timeout_ms: int = 5000
    request_timeout_ms: int = 3000
    retry_backoff_ms: int = 100
    max_in_flight_requests: int = 5
    enable_idempotence: bool = True
    acks: str = "1"  # Changed to "1" for lower latency


class MarketData(BaseModel):
    """Market data message model."""
    exchange: str
    symbol: str
    timestamp: float
    data_type: DataType
    price: Optional[float] = None
    volume: Optional[float] = None
    side: Optional[str] = None
    orderbook: Optional[Dict[str, Any]] = None
    ohlcv: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizedKafkaProducer:
    """
    High-performance async Kafka producer with optimized batching and connection pooling.
    
    Key optimizations:
    - Uses aiokafka for truly async operations (no thread pool)
    - Implements adaptive batching with size and time triggers
    - Connection pooling and reuse
    - Non-blocking send operations
    - Efficient error handling and retry logic
    """
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer: Optional[AIOKafkaProducer] = None
        self._message_queue: List[Dict[str, Any]] = field(default_factory=list)
        self._pending_futures: List[asyncio.Future] = field(default_factory=list)
        
        # Performance metrics
        self.messages_sent = 0
        self.error_count = 0
        self.last_error_time = 0
        self.avg_latency = 0.0
        self._latency_samples = []
        
        # Batch processing control
        self._batch_lock = asyncio.Lock()
        self._flush_interval = 0.01  # 10ms flush interval for low latency
        self._last_flush_time = time.time()
        
        logger.info("Optimized Kafka Producer initialized")

    async def start(self) -> None:
        """Start the Kafka producer with optimized configuration."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                batch_size=self.config.batch_size,
                linger_ms=self.config.linger_ms,
                compression_type=self.config.compression_type,
                max_request_size=self.config.max_request_size,
                request_timeout_ms=self.config.request_timeout_ms,
                delivery_timeout_ms=self.config.delivery_timeout_ms,
                retry_backoff_ms=self.config.retry_backoff_ms,
                max_in_flight_requests=self.config.max_in_flight_requests,
                enable_idempotence=self.config.enable_idempotence,
                acks=self.config.acks,
                # Performance optimizations
                buffer_memory=67108864,  # 64MB buffer
                max_block_ms=10,  # Don't block for more than 10ms
                connections_max_idle_ms=540000,  # Keep connections alive
            )
            
            await self.producer.start()
            
            # Start background batch processor
            asyncio.create_task(self._batch_processor())
            
            logger.info(f"Optimized Kafka producer started on {self.config.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def send_market_data(
        self,
        exchange: str,
        symbol: str,
        data_type: DataType,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Send market data message with ultra-low latency.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            data_type: Type of market data
            data: Market data content
            key: Optional message key for partitioning
            
        Returns:
            bool: True if message queued successfully
        """
        try:
            # Create message
            message = MarketData(
                exchange=exchange,
                symbol=symbol,
                timestamp=time.time(),
                data_type=data_type,
                **data
            )
            
            # Prepare message key for partitioning
            message_key = key or f"{exchange}_{symbol}"
            
            # Queue message for batch processing (non-blocking)
            topic = f"{self.config.topic_prefix}_{data_type.value}"
            
            message_dict = {
                'topic': topic,
                'key': message_key,
                'value': message.model_dump(),
                'timestamp': time.time()
            }
            
            async with self._batch_lock:
                self._message_queue.append(message_dict)
                
                # Trigger immediate batch if queue is getting large
                if len(self._message_queue) >= self.config.batch_size:
                    await self._flush_batch()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue market data: {e}")
            self.error_count += 1
            self.last_error_time = time.time()
            return False

    async def _batch_processor(self) -> None:
        """Background task to process message batches efficiently."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                
                async with self._batch_lock:
                    if self._message_queue:
                        await self._flush_batch()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processor error: {e}")

    async def _flush_batch(self) -> None:
        """Flush current message batch to Kafka."""
        if not self._message_queue or not self.producer:
            return
            
        current_batch = self._message_queue.copy()
        self._message_queue.clear()
        
        if not current_batch:
            return
            
        try:
            # Send all messages in parallel
            send_tasks = []
            for msg in current_batch:
                task = asyncio.create_task(
                    self.producer.send_and_wait(
                        topic=msg['topic'],
                        key=msg['key'],
                        value=msg['value']
                    )
                )
                send_tasks.append(task)
            
            # Wait for all sends to complete with timeout
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to send message: {result}")
                    self.error_count += 1
                else:
                    self.messages_sent += 1
                    
                    # Calculate latency
                    latency = time.time() - current_batch[i]['timestamp']
                    self._latency_samples.append(latency)
                    
                    # Keep only last 1000 samples for moving average
                    if len(self._latency_samples) > 1000:
                        self._latency_samples.pop(0)
                    
                    # Update average latency
                    self.avg_latency = sum(self._latency_samples) / len(self._latency_samples)
            
            self._last_flush_time = time.time()
            
            if len(current_batch) > 0:
                logger.debug(f"Batch sent: {len(current_batch)} messages, avg latency: {self.avg_latency:.3f}ms")
                
        except Exception as e:
            logger.error(f"Batch send failed: {e}")
            self.error_count += 1
            self.last_error_time = time.time()

    async def send_health_status(self, exchange: str, health_data: Dict[str, Any]) -> bool:
        """Send exchange health status."""
        return await self.send_market_data(
            exchange=exchange,
            symbol="system",
            data_type=DataType.HEALTH,
            data=health_data
        )

    async def flush(self) -> None:
        """Flush all pending messages."""
        async with self._batch_lock:
            await self._flush_batch()
        
        if self.producer:
            await self.producer.flush()

    async def close(self) -> None:
        """Close the producer and clean up resources."""
        try:
            # Flush any remaining messages
            await self.flush()
            
            if self.producer:
                await self.producer.stop()
                self.producer = None
                
            logger.info("Optimized Kafka producer closed")
            
        except Exception as e:
            logger.error(f"Error closing producer: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            'messages_sent': self.messages_sent,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.messages_sent + self.error_count),
            'avg_latency_ms': self.avg_latency * 1000,
            'queue_size': len(self._message_queue),
            'pending_futures': len(self._pending_futures),
            'last_error_time': self.last_error_time
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check producer health."""
        try:
            is_healthy = (
                self.producer is not None and
                not self.producer._closed and
                (time.time() - self.last_error_time) > 60  # No errors in last minute
            )
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'producer_connected': self.producer is not None,
                'metrics': self.get_metrics()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'metrics': self.get_metrics()
            }


# Factory function for easy instantiation
async def create_optimized_kafka_producer(
    bootstrap_servers: List[str],
    topic_prefix: str = "smc_market_data",
    **kwargs
) -> OptimizedKafkaProducer:
    """
    Create and start optimized Kafka producer.
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic_prefix: Topic prefix for market data
        **kwargs: Additional configuration options
        
    Returns:
        OptimizedKafkaProducer: Started producer instance
    """
    config = KafkaConfig(
        bootstrap_servers=bootstrap_servers,
        topic_prefix=topic_prefix,
        **kwargs
    )
    
    producer = OptimizedKafkaProducer(config)
    await producer.start()
    
    return producer