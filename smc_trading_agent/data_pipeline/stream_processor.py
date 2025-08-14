"""
Kafka Streams-based Real-time Data Processing for SMC Trading Agent

Implements real-time stream processing for market data with:
- Data transformation and enrichment
- Exactly-once processing semantics
- SMC pattern detection in streaming mode
- Performance optimization for high throughput
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, CommitFailedError
from pydantic import BaseModel, Field
from ..monitoring.data_quality_metrics import inc_anomaly

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Stream processing modes."""
    EXACTLY_ONCE = "exactly_once"
    AT_LEAST_ONCE = "at_least_once"
    AT_MOST_ONCE = "at_most_once"


class StreamState(Enum):
    """Stream processor states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class StreamMetrics:
    """Stream processing metrics."""
    messages_processed: int = 0
    messages_failed: int = 0
    processing_latency_ms: float = 0.0
    throughput_per_second: float = 0.0
    last_processed_timestamp: float = 0.0
    error_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketDataEnricher:
    """
    Market data enrichment processor.
    
    Adds technical indicators, volume profiles, and SMC context to raw market data.
    """
    
    def __init__(self):
        """Initialize market data enricher."""
        self.price_history = {}  # Symbol -> price history
        self.volume_profiles = {}  # Symbol -> volume profile
        self.smc_context = {}  # Symbol -> SMC context
        
    def enrich_trade_data(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich trade data with additional context.
        
        Args:
            trade_data: Raw trade data
            
        Returns:
            Dict: Enriched trade data
        """
        try:
            symbol = trade_data.get('symbol', '')
            price = float(trade_data.get('price', 0))
            volume = float(trade_data.get('volume', 0))
            timestamp = trade_data.get('timestamp', time.time())
            
            # Update price history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append({
                'price': price,
                'volume': volume,
                'timestamp': timestamp
            })
            
            # Keep only last 1000 data points
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]
            
            # Calculate technical indicators
            enriched_data = trade_data.copy()
            enriched_data.update(self._calculate_indicators(symbol, price, volume))
            enriched_data.update(self._detect_smc_patterns(symbol, price, volume))
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to enrich trade data: {e}")
            return trade_data
    
    def enrich_orderbook_data(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich orderbook data with liquidity analysis.
        
        Args:
            orderbook_data: Raw orderbook data
            
        Returns:
            Dict: Enriched orderbook data
        """
        try:
            symbol = orderbook_data.get('symbol', '')
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            enriched_data = orderbook_data.copy()
            enriched_data.update(self._analyze_liquidity(symbol, bids, asks))
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to enrich orderbook data: {e}")
            return orderbook_data
    
    def _calculate_indicators(self, symbol: str, price: float, volume: float) -> Dict[str, Any]:
        """Calculate technical indicators."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return {}
        
        prices = [p['price'] for p in self.price_history[symbol][-20:]]
        volumes = [p['volume'] for p in self.price_history[symbol][-20:]]
        
        # Simple moving averages
        sma_5 = np.mean(prices[-5:]) if len(prices) >= 5 else price
        sma_10 = np.mean(prices[-10:]) if len(prices) >= 10 else price
        sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else price
        
        # Volume weighted average price (VWAP)
        total_volume = sum(volumes)
        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume if total_volume > 0 else price
        
        # Price momentum
        momentum = (price - prices[0]) / prices[0] * 100 if prices[0] > 0 else 0
        
        return {
            'indicators': {
                'sma_5': sma_5,
                'sma_10': sma_10,
                'sma_20': sma_20,
                'vwap': vwap,
                'momentum': momentum,
                'relative_volume': volume / (np.mean(volumes) if volumes else 1)
            }
        }
    
    def _detect_smc_patterns(self, symbol: str, price: float, volume: float) -> Dict[str, Any]:
        """Detect SMC patterns in real-time."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 50:
            return {}
        
        prices = [p['price'] for p in self.price_history[symbol][-50:]]
        volumes = [p['volume'] for p in self.price_history[symbol][-50:]]
        
        # Simple SMC pattern detection
        patterns = {
            'order_block_detected': self._detect_order_block(prices, volumes),
            'liquidity_zone': self._detect_liquidity_zone(prices, volumes),
            'fair_value_gap': self._detect_fair_value_gap(prices),
            'market_structure_break': self._detect_structure_break(prices)
        }
        
        return {'smc_patterns': patterns}
    
    def _detect_order_block(self, prices: List[float], volumes: List[float]) -> bool:
        """Detect order block pattern."""
        if len(prices) < 10 or len(volumes) < 10:
            return False
        
        # Look for high volume at price extremes
        recent_high = max(prices[-10:])
        recent_low = min(prices[-10:])
        
        high_idx = prices[-10:].index(recent_high)
        low_idx = prices[-10:].index(recent_low)
        
        # Check if volume was significantly higher at extremes
        avg_volume = np.mean(volumes[-10:])
        high_volume = volumes[-10:][high_idx] if high_idx < len(volumes[-10:]) else 0
        low_volume = volumes[-10:][low_idx] if low_idx < len(volumes[-10:]) else 0
        
        return high_volume > avg_volume * 1.5 or low_volume > avg_volume * 1.5
    
    def _detect_liquidity_zone(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        """Detect liquidity zones."""
        if len(prices) < 20:
            return {}
        
        # Find price levels with high volume
        price_volume_map = {}
        for i, (price, volume) in enumerate(zip(prices[-20:], volumes[-20:])):
            price_level = round(price, 2)  # Round to 2 decimal places
            if price_level not in price_volume_map:
                price_volume_map[price_level] = 0
            price_volume_map[price_level] += volume
        
        # Find top liquidity zones
        sorted_zones = sorted(price_volume_map.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'support_zone': sorted_zones[0][0] if sorted_zones else 0,
            'resistance_zone': sorted_zones[1][0] if len(sorted_zones) > 1 else 0
        }
    
    def _detect_fair_value_gap(self, prices: List[float]) -> bool:
        """Detect fair value gaps."""
        if len(prices) < 5:
            return False
        
        # Look for price gaps in recent data
        for i in range(len(prices) - 3):
            gap_size = abs(prices[i + 2] - prices[i]) / prices[i]
            if gap_size > 0.002:  # 0.2% gap threshold
                return True
        
        return False
    
    def _detect_structure_break(self, prices: List[float]) -> bool:
        """Detect market structure breaks."""
        if len(prices) < 20:
            return False
        
        # Simple trend break detection
        recent_trend = np.polyfit(range(10), prices[-10:], 1)[0]
        previous_trend = np.polyfit(range(10), prices[-20:-10], 1)[0]
        
        # Check for trend reversal
        return (recent_trend > 0 and previous_trend < 0) or (recent_trend < 0 and previous_trend > 0)
    
    def _analyze_liquidity(self, symbol: str, bids: List[List[float]], asks: List[List[float]]) -> Dict[str, Any]:
        """Analyze orderbook liquidity."""
        try:
            if not bids or not asks:
                return {}
            
            # Calculate bid/ask spread
            best_bid = max(bids, key=lambda x: x[0])[0] if bids else 0
            best_ask = min(asks, key=lambda x: x[0])[0] if asks else 0
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0
            
            # Calculate liquidity depth
            bid_depth = sum(bid[1] for bid in bids[:10])  # Top 10 levels
            ask_depth = sum(ask[1] for ask in asks[:10])  # Top 10 levels
            
            # Calculate imbalance
            total_depth = bid_depth + ask_depth
            imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0
            
            return {
                'liquidity_analysis': {
                    'spread_bps': spread * 100,  # Basis points
                    'bid_depth': bid_depth,
                    'ask_depth': ask_depth,
                    'imbalance': imbalance,
                    'liquidity_score': min(bid_depth, ask_depth) / max(bid_depth, ask_depth) if max(bid_depth, ask_depth) > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze liquidity: {e}")
            return {}


class StreamProcessor:
    """
    High-performance Kafka stream processor with exactly-once semantics.
    
    Processes market data streams with transformation, enrichment, and SMC analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize stream processor.
        
        Args:
            config: Stream processor configuration
        """
        self.config = config
        self.state = StreamState.STOPPED
        self.metrics = StreamMetrics()
        self.enricher = MarketDataEnricher()
        
        # Kafka configuration
        self.bootstrap_servers = config.get('bootstrap_servers', ['localhost:9092'])
        self.consumer_group = config.get('consumer_group', 'smc-stream-processor')
        self.processing_mode = ProcessingMode(config.get('processing_mode', 'exactly_once'))
        
        # Processing configuration
        self.batch_size = config.get('batch_size', 100)
        self.commit_interval_ms = config.get('commit_interval_ms', 5000)
        self.max_poll_records = config.get('max_poll_records', 500)
        
        # Topic configuration
        self.input_topics = config.get('input_topics', [])
        self.output_topics = config.get('output_topics', {})
        
        # Kafka clients
        self.consumer = None
        self.producer = None
        
        # Processing state
        self.last_commit_time = time.time()
        self.processed_offsets = {}
        
        logger.info(f"Initialized stream processor with mode: {self.processing_mode.value}")
    
    async def start(self) -> bool:
        """
        Start the stream processor.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            self.state = StreamState.STARTING
            logger.info("Starting stream processor...")
            
            # Initialize Kafka consumer
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.consumer_group,
                'auto_offset_reset': 'latest',
                'enable_auto_commit': False,  # Manual commit for exactly-once
                'max_poll_records': self.max_poll_records,
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'key_deserializer': lambda m: m.decode('utf-8') if m else None
            }
            
            # Configure for exactly-once semantics
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                consumer_config.update({
                    'isolation_level': 'read_committed',
                    'enable_auto_commit': False
                })
            
            self.consumer = KafkaConsumer(**consumer_config)
            self.consumer.subscribe(self.input_topics)
            
            # Initialize Kafka producer
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None,
                'acks': 'all',
                'retries': 3,
                'batch_size': 16384,
                'linger_ms': 5,
                'compression_type': 'gzip'
            }
            
            # Configure for exactly-once semantics
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                producer_config.update({
                    'enable_idempotence': True,
                    'transactional_id': f'{self.consumer_group}-producer'
                })
            
            self.producer = KafkaProducer(**producer_config)
            
            # Initialize producer transactions for exactly-once
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                self.producer.init_transactions()
            
            self.state = StreamState.RUNNING
            logger.info("Stream processor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream processor: {e}")
            self.state = StreamState.ERROR
            return False
    
    async def stop(self) -> bool:
        """
        Stop the stream processor.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            self.state = StreamState.STOPPING
            logger.info("Stopping stream processor...")
            
            # Close Kafka clients
            if self.consumer:
                self.consumer.close()
                self.consumer = None
            
            if self.producer:
                self.producer.flush()
                self.producer.close()
                self.producer = None
            
            self.state = StreamState.STOPPED
            logger.info("Stream processor stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop stream processor: {e}")
            return False
    
    async def process_stream(self):
        """Main stream processing loop."""
        logger.info("Starting stream processing loop...")
        
        while self.state == StreamState.RUNNING:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process batch
                await self._process_message_batch(message_batch)
                
                # Commit offsets periodically
                if time.time() - self.last_commit_time > self.commit_interval_ms / 1000:
                    await self._commit_offsets()
                
            except Exception as e:
                logger.error(f"Error in stream processing loop: {e}")
                self.metrics.messages_failed += 1
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_message_batch(self, message_batch: Dict):
        """Process a batch of messages."""
        start_time = time.time()
        batch_size = 0
        
        try:
            # Begin transaction for exactly-once processing
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                self.producer.begin_transaction()
            
            for topic_partition, messages in message_batch.items():
                for message in messages:
                    await self._process_single_message(message)
                    batch_size += 1
                    
                    # Store offset for manual commit
                    self.processed_offsets[topic_partition] = message.offset + 1
            
            # Commit transaction
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                # Send offsets to transaction
                self.producer.send_offsets_to_transaction(
                    self.processed_offsets,
                    self.consumer_group
                )
                self.producer.commit_transaction()
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.messages_processed += batch_size
            self.metrics.processing_latency_ms = processing_time / batch_size if batch_size > 0 else 0
            self.metrics.throughput_per_second = batch_size / (processing_time / 1000) if processing_time > 0 else 0
            self.metrics.last_processed_timestamp = time.time()
            
            logger.debug(f"Processed batch of {batch_size} messages in {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Failed to process message batch: {e}")
            
            # Abort transaction on error
            if self.processing_mode == ProcessingMode.EXACTLY_ONCE:
                try:
                    self.producer.abort_transaction()
                except Exception as abort_error:
                    logger.error(f"Failed to abort transaction: {abort_error}")
            
            self.metrics.messages_failed += batch_size
            raise
    
    async def _process_single_message(self, message):
        """Process a single message."""
        try:
            # Parse message
            topic = message.topic
            key = message.key
            value = message.value
            timestamp = message.timestamp
            
            # Determine processing based on topic
            if 'trades' in topic:
                processed_data = await self._process_trade_message(value)
            elif 'orderbook' in topic:
                processed_data = await self._process_orderbook_message(value)
            elif 'klines' in topic:
                processed_data = await self._process_kline_message(value)
            else:
                logger.warning(f"Unknown topic type: {topic}")
                return
            
            # Send processed data to output topics
            await self._send_processed_data(processed_data, key, topic)
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            raise
    
    async def _process_trade_message(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process trade message with enrichment."""
        # Enrich trade data
        enriched_data = self.enricher.enrich_trade_data(trade_data)
        
        # Add processing metadata
        enriched_data['processing'] = {
            'processed_at': time.time(),
            'processor_id': self.consumer_group,
            'version': '1.0'
        }
        # Add simple lineage metadata
        enriched_data.setdefault('lineage', {})
        enriched_data['lineage'].update({
            'stage': 'stream_enrichment',
            'source': 'kafka',
            'pipeline': 'stream_processor'
        })
        
        return enriched_data
    
    async def _process_orderbook_message(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process orderbook message with liquidity analysis."""
        # Enrich orderbook data
        enriched_data = self.enricher.enrich_orderbook_data(orderbook_data)
        
        # Add processing metadata
        enriched_data['processing'] = {
            'processed_at': time.time(),
            'processor_id': self.consumer_group,
            'version': '1.0'
        }
        # Add simple lineage metadata
        enriched_data.setdefault('lineage', {})
        enriched_data['lineage'].update({
            'stage': 'stream_enrichment',
            'source': 'kafka',
            'pipeline': 'stream_processor'
        })
        
        return enriched_data
    
    async def _process_kline_message(self, kline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kline/candlestick message."""
        # Basic kline processing (can be extended)
        processed_data = kline_data.copy()
        
        # Calculate additional metrics
        if all(k in kline_data for k in ['open', 'high', 'low', 'close', 'volume']):
            open_price = float(kline_data['open'])
            high_price = float(kline_data['high'])
            low_price = float(kline_data['low'])
            close_price = float(kline_data['close'])
            volume = float(kline_data['volume'])
            
            # Calculate derived metrics
            processed_data['derived_metrics'] = {
                'price_change': close_price - open_price,
                'price_change_pct': (close_price - open_price) / open_price * 100 if open_price > 0 else 0,
                'true_range': max(high_price - low_price, abs(high_price - close_price), abs(low_price - close_price)),
                'typical_price': (high_price + low_price + close_price) / 3,
                'volume_weighted_price': (high_price + low_price + close_price * 2) / 4
            }
            # Flag extreme changes as anomalies for monitoring
            if abs(processed_data['derived_metrics']['price_change_pct']) > 10:
                inc_anomaly('extreme_price_change')
        
        # Add processing metadata
        processed_data['processing'] = {
            'processed_at': time.time(),
            'processor_id': self.consumer_group,
            'version': '1.0'
        }
        processed_data.setdefault('lineage', {})
        processed_data['lineage'].update({
            'stage': 'stream_enrichment',
            'source': 'kafka',
            'pipeline': 'stream_processor'
        })
        
        return processed_data
    
    async def _send_processed_data(self, processed_data: Dict[str, Any], key: str, original_topic: str):
        """Send processed data to appropriate output topics."""
        try:
            # Determine output topics based on data type and content
            output_topics = []
            
            # Always send to enriched data topic
            if 'trades' in original_topic:
                output_topics.append(self.output_topics.get('enriched_trades', 'enriched_trades'))
            elif 'orderbook' in original_topic:
                output_topics.append(self.output_topics.get('enriched_orderbook', 'enriched_orderbook'))
            elif 'klines' in original_topic:
                output_topics.append(self.output_topics.get('enriched_klines', 'enriched_klines'))
            
            # Send to SMC signals topic if patterns detected
            if 'smc_patterns' in processed_data:
                patterns = processed_data['smc_patterns']
                if any(patterns.values()):
                    output_topics.append(self.output_topics.get('smc_signals', 'smc_signals'))
            
            # Send to all determined output topics
            for topic in output_topics:
                future = self.producer.send(
                    topic=topic,
                    key=key,
                    value=processed_data
                )
                
                # For exactly-once, we don't wait for individual sends
                # The transaction commit will ensure delivery
                if self.processing_mode != ProcessingMode.EXACTLY_ONCE:
                    # Wait for delivery confirmation for other modes
                    record_metadata = future.get(timeout=10)
                    logger.debug(f"Sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            
        except Exception as e:
            logger.error(f"Failed to send processed data: {e}")
            raise
    
    async def _commit_offsets(self):
        """Commit processed offsets."""
        try:
            if self.processing_mode != ProcessingMode.EXACTLY_ONCE:
                # Manual commit for at-least-once and at-most-once
                self.consumer.commit()
                self.last_commit_time = time.time()
                logger.debug("Committed offsets manually")
            
        except CommitFailedError as e:
            logger.error(f"Failed to commit offsets: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics."""
        # Calculate error rate
        total_messages = self.metrics.messages_processed + self.metrics.messages_failed
        self.metrics.error_rate = self.metrics.messages_failed / total_messages if total_messages > 0 else 0
        
        return {
            'state': self.state.value,
            'metrics': self.metrics.to_dict(),
            'config': {
                'processing_mode': self.processing_mode.value,
                'consumer_group': self.consumer_group,
                'batch_size': self.batch_size,
                'input_topics': self.input_topics,
                'output_topics': self.output_topics
            },
            'timestamp': time.time()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the stream processor."""
        is_healthy = (
            self.state == StreamState.RUNNING and
            self.consumer is not None and
            self.producer is not None and
            self.metrics.error_rate < 0.1  # Less than 10% error rate
        )
        
        return {
            'healthy': is_healthy,
            'state': self.state.value,
            'last_processed': self.metrics.last_processed_timestamp,
            'error_rate': self.metrics.error_rate,
            'throughput': self.metrics.throughput_per_second,
            'timestamp': time.time()
        }


class StreamProcessorManager:
    """
    Manager for multiple stream processors.
    
    Handles lifecycle management, monitoring, and coordination of stream processors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize stream processor manager.
        
        Args:
            config: Manager configuration
        """
        self.config = config
        self.processors = {}
        self.running = False
        
    async def start_processor(self, processor_id: str, processor_config: Dict[str, Any]) -> bool:
        """
        Start a stream processor.
        
        Args:
            processor_id: Unique processor identifier
            processor_config: Processor configuration
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            if processor_id in self.processors:
                logger.warning(f"Processor {processor_id} already exists")
                return False
            
            processor = StreamProcessor(processor_config)
            
            if await processor.start():
                self.processors[processor_id] = processor
                
                # Start processing task
                asyncio.create_task(processor.process_stream())
                
                logger.info(f"Started stream processor: {processor_id}")
                return True
            else:
                logger.error(f"Failed to start processor: {processor_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting processor {processor_id}: {e}")
            return False
    
    async def stop_processor(self, processor_id: str) -> bool:
        """
        Stop a stream processor.
        
        Args:
            processor_id: Processor identifier
            
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            if processor_id not in self.processors:
                logger.warning(f"Processor {processor_id} not found")
                return False
            
            processor = self.processors[processor_id]
            
            if await processor.stop():
                del self.processors[processor_id]
                logger.info(f"Stopped stream processor: {processor_id}")
                return True
            else:
                logger.error(f"Failed to stop processor: {processor_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping processor {processor_id}: {e}")
            return False
    
    async def stop_all_processors(self):
        """Stop all stream processors."""
        logger.info("Stopping all stream processors...")
        
        for processor_id in list(self.processors.keys()):
            await self.stop_processor(processor_id)
        
        logger.info("All stream processors stopped")
    
    def get_processor_metrics(self, processor_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific processor."""
        if processor_id in self.processors:
            return self.processors[processor_id].get_metrics()
        return None
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all processors."""
        return {
            processor_id: processor.get_metrics()
            for processor_id, processor in self.processors.items()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all processors."""
        processor_health = {}
        overall_healthy = True
        
        for processor_id, processor in self.processors.items():
            health = processor.get_health_status()
            processor_health[processor_id] = health
            if not health['healthy']:
                overall_healthy = False
        
        return {
            'overall_healthy': overall_healthy,
            'processor_count': len(self.processors),
            'processors': processor_health,
            'timestamp': time.time()
        }