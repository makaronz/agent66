"""
Multi-Timeframe Data Manager

Handles real-time synchronization, storage, and retrieval of market data
across multiple timeframes with efficient caching and confluence detection.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

@dataclass
class TimeframeConfig:
    """Configuration for a specific timeframe."""
    name: str
    minutes: int
    priority: int  # Higher number = higher priority
    max_candles: int = 1000
    confluence_weight: float = 1.0
    trend_weight: float = 1.0

@dataclass
class MarketDataUpdate:
    """Represents a market data update."""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    exchange: str = "binance"

@dataclass
class ConfluenceZone:
    """Represents a confluence zone across timeframes."""
    price_level: float
    strength: float
    timeframes: Set[str]
    zone_type: str  # 'support', 'resistance', 'order_block'
    timestamp: datetime
    confidence: float
    source_patterns: List[str] = field(default_factory=list)

class DataSynchronizer:
    """Handles real-time data synchronization across timeframes."""

    def __init__(self, timeframes: List[TimeframeConfig]):
        self.timeframes = {tf.name: tf for tf in timeframes}
        self.data_buffers = defaultdict(lambda: defaultdict(deque))
        self.last_updates = defaultdict(lambda: defaultdict(datetime))
        self.sync_lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def add_tick_data(self, symbol: str, price: float, volume: float, timestamp: datetime):
        """Add tick data and update all timeframes."""
        with self.sync_lock:
            # Update M1 buffer
            self._update_timeframe_buffer(symbol, 'M1', price, volume, timestamp)

            # Update higher timeframes based on M1 completion
            self._sync_higher_timeframes(symbol, timestamp)

    def _update_timeframe_buffer(self, symbol: str, timeframe: str,
                                price: float, volume: float, timestamp: datetime):
        """Update buffer for specific timeframe."""
        buffer = self.data_buffers[symbol][timeframe]

        if not buffer:
            # Create new candle
            candle = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'timestamp': timestamp
            }
            buffer.append(candle)
        else:
            # Update current candle
            current = buffer[-1]
            current['high'] = max(current['high'], price)
            current['low'] = min(current['low'], price)
            current['close'] = price
            current['volume'] += volume

    def _sync_higher_timeframes(self, symbol: str, timestamp: datetime):
        """Synchronize higher timeframes based on M1 data."""
        m1_buffer = self.data_buffers[symbol]['M1']
        if len(m1_buffer) < 2:
            return

        current_candle = m1_buffer[-1]
        prev_candle = m1_buffer[-2]

        # Check if M1 candle completed (new timestamp minute)
        if current_candle['timestamp'].minute != prev_candle['timestamp'].minute:
            # Complete the previous M1 candle and update higher timeframes
            self._complete_candle_and_sync(symbol, 'M1', prev_candle, timestamp)

    def _complete_candle_and_sync(self, symbol: str, timeframe: str,
                                 candle: Dict, timestamp: datetime):
        """Complete a candle and propagate to higher timeframes."""
        tf_config = self.timeframes.get(timeframe)
        if not tf_config:
            return

        # Update higher timeframes
        for higher_tf_name, higher_tf_config in self.timeframes.items():
            if higher_tf_config.minutes > tf_config.minutes:
                if self._should_complete_higher_tf(symbol, higher_tf_name, candle['timestamp']):
                    self._aggregate_to_timeframe(symbol, higher_tf_name, candle, timestamp)

    def _should_complete_higher_tf(self, symbol: str, timeframe: str, timestamp: datetime) -> bool:
        """Check if higher timeframe candle should be completed."""
        buffer = self.data_buffers[symbol][timeframe]
        if not buffer:
            return True

        tf_config = self.timeframes[timeframe]
        current_time = timestamp

        # Check if we've moved to next timeframe interval
        interval_start = self._get_interval_start(current_time, tf_config.minutes)
        last_interval = self._get_interval_start(buffer[-1]['timestamp'], tf_config.minutes)

        return interval_start > last_interval

    def _aggregate_to_timeframe(self, symbol: str, timeframe: str,
                               m1_candle: Dict, timestamp: datetime):
        """Aggregate M1 candle to higher timeframe."""
        buffer = self.data_buffers[symbol][timeframe]
        tf_config = self.timeframes[timeframe]

        # Get all M1 candles for this timeframe interval
        interval_start = self._get_interval_start(m1_candle['timestamp'], tf_config.minutes)
        interval_end = interval_start + timedelta(minutes=tf_config.minutes)

        # Collect M1 candles in this interval
        m1_buffer = self.data_buffers[symbol]['M1']
        interval_candles = [
            c for c in m1_buffer
            if interval_start <= c['timestamp'] < interval_end
        ]

        if interval_candles:
            # Create aggregated candle
            aggregated = {
                'open': interval_candles[0]['open'],
                'high': max(c['high'] for c in interval_candles),
                'low': min(c['low'] for c in interval_candles),
                'close': interval_candles[-1]['close'],
                'volume': sum(c['volume'] for c in interval_candles),
                'timestamp': interval_end - timedelta(minutes=1)
            }

            buffer.append(aggregated)

            # Limit buffer size
            max_candles = tf_config.max_candles
            if len(buffer) > max_candles:
                for _ in range(len(buffer) - max_candles):
                    buffer.popleft()

    def _get_interval_start(self, timestamp: datetime, minutes: int) -> datetime:
        """Get the start of the interval for given timeframe."""
        total_minutes = timestamp.hour * 60 + timestamp.minute
        interval_start = (total_minutes // minutes) * minutes
        return timestamp.replace(
            hour=interval_start // 60,
            minute=interval_start % 60,
            second=0,
            microsecond=0
        )

    def get_ohlcv_data(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Get OHLCV data for symbol and timeframe."""
        with self.sync_lock:
            buffer = self.data_buffers[symbol][timeframe]
            if not buffer:
                return pd.DataFrame()

            # Convert to DataFrame
            data = list(buffer)
            if limit:
                data = data[-limit:]

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df.sort_values('timestamp').reset_index(drop=True)

class MultiTimeframeDataManager:
    """
    Main manager for multi-timeframe data operations.

    Handles data synchronization, confluence detection, and real-time updates
    across M5, M15, H1, H4, D1 timeframes with optimized performance.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbols = config.get('symbols', ['BTCUSDT'])

        # Initialize timeframe configurations
        self.timeframes = [
            TimeframeConfig('M5', 5, 1, max_candles=2000, confluence_weight=0.1),
            TimeframeConfig('M15', 15, 2, max_candles=1500, confluence_weight=0.2),
            TimeframeConfig('H1', 60, 3, max_candles=1000, confluence_weight=0.3),
            TimeframeConfig('H4', 240, 4, max_candles=500, confluence_weight=0.4),
            TimeframeConfig('D1', 1440, 5, max_candles=365, confluence_weight=0.5)
        ]

        # Initialize components
        self.synchronizer = DataSynchronizer(self.timeframes)
        self.confluence_zones: Dict[str, List[ConfluenceZone]] = defaultdict(list)
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)
        self.cache_timestamps: Dict[str, Dict[str, datetime]] = defaultdict(dict)

        # Performance monitoring
        self.metrics = {
            'total_updates': 0,
            'confluence_detections': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0.0
        }

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=8)

        logger.info("Multi-timeframe data manager initialized")

    async def initialize(self):
        """Initialize the data manager."""
        logger.info("Initializing multi-timeframe data manager...")

        # Start background tasks
        asyncio.create_task(self._confluence_monitor())
        asyncio.create_task(self._cache_cleanup())
        asyncio.create_task(self._performance_monitor())

        logger.info("Multi-timeframe data manager initialized successfully")

    def add_market_data(self, symbol: str, price: float, volume: float,
                       timestamp: Optional[datetime] = None):
        """
        Add real-time market data and synchronize across timeframes.

        Args:
            symbol: Trading symbol
            price: Current price
            volume: Trade volume
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        try:
            # Add to synchronizer
            self.synchronizer.add_tick_data(symbol, price, volume, timestamp)

            # Update metrics
            self.metrics['total_updates'] += 1

            # Invalidate cache for this symbol
            self._invalidate_symbol_cache(symbol)

        except Exception as e:
            logger.error(f"Error adding market data for {symbol}: {e}")

    def get_timeframe_data(self, symbol: str, timeframe: str,
                          limit: Optional[int] = None,
                          use_cache: bool = True) -> pd.DataFrame:
        """
        Get OHLCV data for specific timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M5, M15, H1, H4, D1)
            limit: Optional limit on number of candles
            use_cache: Whether to use cached data

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Check cache first
            if use_cache:
                cached_data = self._get_cached_data(symbol, timeframe)
                if cached_data is not None:
                    self.metrics['cache_hits'] += 1
                    if limit:
                        return cached_data.tail(limit)
                    return cached_data

            self.metrics['cache_misses'] += 1

            # Get fresh data
            data = self.synchronizer.get_ohlcv_data(symbol, timeframe, limit)

            # Cache the data
            if use_cache and not data.empty:
                self._cache_data(symbol, timeframe, data)

            return data

        except Exception as e:
            logger.error(f"Error getting timeframe data for {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def get_all_timeframes_data(self, symbol: str, limit: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Get data for all timeframes for a symbol.

        Args:
            symbol: Trading symbol
            limit: Optional limit on number of candles

        Returns:
            Dictionary mapping timeframes to DataFrames
        """
        results = {}

        # Use parallel processing for all timeframes
        futures = {}
        for tf in self.timeframes:
            future = self.executor.submit(self.get_timeframe_data, symbol, tf.name, limit)
            futures[tf.name] = future

        # Collect results
        for tf_name, future in futures.items():
            try:
                results[tf_name] = future.result(timeout=5)
            except Exception as e:
                logger.error(f"Error getting data for {tf_name}: {e}")
                results[tf_name] = pd.DataFrame()

        return results

    def detect_confluence_zones(self, symbol: str) -> List[ConfluenceZone]:
        """
        Detect confluence zones across all timeframes.

        Args:
            symbol: Trading symbol

        Returns:
            List of confluence zones with strength and timeframes
        """
        try:
            # Get data for all timeframes
            all_data = self.get_all_timeframes_data(symbol)

            # Detect patterns in parallel
            futures = []
            for tf_name, df in all_data.items():
                if df.empty:
                    continue

                future = self.executor.submit(self._detect_timeframe_patterns, tf_name, df)
                futures.append((tf_name, future))

            # Collect patterns
            all_patterns = {}
            for tf_name, future in futures:
                try:
                    patterns = future.result(timeout=10)
                    if patterns:
                        all_patterns[tf_name] = patterns
                except Exception as e:
                    logger.error(f"Error detecting patterns for {tf_name}: {e}")

            # Find confluence zones
            confluence_zones = self._find_confluence_zones(all_patterns)

            # Store results
            self.confluence_zones[symbol] = confluence_zones
            self.metrics['confluence_detections'] += 1

            return confluence_zones

        except Exception as e:
            logger.error(f"Error detecting confluence zones for {symbol}: {e}")
            return []

    def _detect_timeframe_patterns(self, timeframe: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect SMC patterns for a specific timeframe."""
        if df.empty or len(df) < 20:
            return []

        patterns = []

        try:
            # Simple pattern detection (can be enhanced with existing SMC indicators)

            # Support/Resistance levels
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            volumes = df['volume'].values

            # Find swing highs and lows
            swing_highs, _ = self._find_swing_points(highs, 'high')
            swing_lows, _ = self._find_swing_points(lows, 'low')

            # Create support/resistance levels
            for idx in swing_highs[-10:]:  # Last 10 swing highs
                patterns.append({
                    'type': 'resistance',
                    'price': highs[idx],
                    'strength': self._calculate_level_strength(df, idx, 'resistance'),
                    'timestamp': df.iloc[idx]['timestamp'],
                    'source': f'{timeframe}_swing_high'
                })

            for idx in swing_lows[-10:]:  # Last 10 swing lows
                patterns.append({
                    'type': 'support',
                    'price': lows[idx],
                    'strength': self._calculate_level_strength(df, idx, 'support'),
                    'timestamp': df.iloc[idx]['timestamp'],
                    'source': f'{timeframe}_swing_low'
                })

            # Volume spike zones
            volume_threshold = np.percentile(volumes, 90)
            spike_indices = np.where(volumes > volume_threshold)[0]

            for idx in spike_indices[-5:]:  # Last 5 volume spikes
                patterns.append({
                    'type': 'volume_zone',
                    'price': closes[idx],
                    'strength': volumes[idx] / np.mean(volumes),
                    'timestamp': df.iloc[idx]['timestamp'],
                    'source': f'{timeframe}_volume_spike'
                })

        except Exception as e:
            logger.error(f"Error detecting patterns for {timeframe}: {e}")

        return patterns

    def _find_swing_points(self, values: np.ndarray, point_type: str,
                          distance: int = 5, prominence: float = None) -> Tuple[np.ndarray, dict]:
        """Find swing points using scipy's find_peaks."""
        from scipy.signal import find_peaks

        if prominence is None:
            prominence = np.std(values) * 0.1

        if point_type == 'high':
            peaks, properties = find_peaks(values, distance=distance, prominence=prominence)
        else:  # low
            peaks, properties = find_peaks(-values, distance=distance, prominence=prominence)

        return peaks, properties

    def _calculate_level_strength(self, df: pd.DataFrame, idx: int,
                                 level_type: str) -> float:
        """Calculate strength of a support/resistance level."""
        try:
            if idx >= len(df) - 1:
                return 0.0

            level_price = df.iloc[idx]['high'] if level_type == 'resistance' else df.iloc[idx]['low']
            touches = 0
            rejections = 0

            # Check historical interactions with this level
            tolerance = level_price * 0.002  # 0.2% tolerance

            for i in range(max(0, idx - 50), min(len(df), idx + 20)):
                if i == idx:
                    continue

                candle = df.iloc[i]
                if level_type == 'resistance':
                    if abs(candle['high'] - level_price) <= tolerance:
                        touches += 1
                        if candle['close'] < candle['open']:
                            rejections += 1
                else:  # support
                    if abs(candle['low'] - level_price) <= tolerance:
                        touches += 1
                        if candle['close'] > candle['open']:
                            rejections += 1

            # Calculate strength based on touches and rejections
            if touches == 0:
                return 0.0

            strength = (touches * 0.1 + rejections * 0.2)
            return min(1.0, strength)

        except Exception as e:
            logger.error(f"Error calculating level strength: {e}")
            return 0.0

    def _find_confluence_zones(self, all_patterns: Dict[str, List[Dict[str, Any]]]) -> List[ConfluenceZone]:
        """Find confluence zones by analyzing patterns across timeframes."""
        confluence_zones = []

        try:
            # Group patterns by price levels
            price_levels = defaultdict(list)

            for tf_name, patterns in all_patterns.items():
                tf_config = self.timeframes.get(tf_name.replace('M', 'M').replace('H', 'H').replace('D', 'D'))
                if not tf_config:
                    continue

                for pattern in patterns:
                    price_key = round(pattern['price'] / 10) * 10  # Group by $10 intervals
                    price_levels[price_key].append({
                        'timeframe': tf_name,
                        'pattern': pattern,
                        'weight': tf_config.confluence_weight
                    })

            # Find confluence zones (levels with patterns from multiple timeframes)
            for price_level, level_patterns in price_levels.items():
                if len(level_patterns) >= 2:  # At least 2 timeframes agree
                    # Calculate overall strength
                    total_weight = sum(p['weight'] for p in level_patterns)
                    avg_confidence = np.mean([p['pattern'].get('strength', 0.5)
                                            for p in level_patterns])

                    # Determine zone type
                    resistance_count = sum(1 for p in level_patterns
                                         if p['pattern']['type'] == 'resistance')
                    support_count = sum(1 for p in level_patterns
                                      if p['pattern']['type'] == 'support')

                    if resistance_count > support_count:
                        zone_type = 'resistance'
                    elif support_count > resistance_count:
                        zone_type = 'support'
                    else:
                        zone_type = 'mixed'

                    confluence_zone = ConfluenceZone(
                        price_level=price_level,
                        strength=min(1.0, total_weight * avg_confidence),
                        timeframes={p['timeframe'] for p in level_patterns},
                        zone_type=zone_type,
                        timestamp=datetime.utcnow(),
                        confidence=min(1.0, avg_confidence),
                        source_patterns=[p['pattern']['source'] for p in level_patterns]
                    )

                    confluence_zones.append(confluence_zone)

            # Sort by strength
            confluence_zones.sort(key=lambda z: z.strength, reverse=True)

        except Exception as e:
            logger.error(f"Error finding confluence zones: {e}")

        return confluence_zones

    def _get_cached_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get cached data if available and not expired."""
        try:
            if symbol not in self.data_cache or timeframe not in self.data_cache[symbol]:
                return None

            cache_time = self.cache_timestamps.get(symbol, {}).get(timeframe)
            if not cache_time:
                return None

            # Cache expires after 30 seconds
            if (datetime.utcnow() - cache_time).total_seconds() > 30:
                return None

            return self.data_cache[symbol][timeframe].copy()

        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    def _cache_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Cache data for future use."""
        try:
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
                self.cache_timestamps[symbol] = {}

            self.data_cache[symbol][timeframe] = data.copy()
            self.cache_timestamps[symbol][timeframe] = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error caching data: {e}")

    def _invalidate_symbol_cache(self, symbol: str):
        """Invalidate cache for a specific symbol."""
        try:
            if symbol in self.cache_timestamps:
                for timeframe in list(self.cache_timestamps[symbol].keys()):
                    del self.cache_timestamps[symbol][timeframe]
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")

    async def _confluence_monitor(self):
        """Background task to monitor and update confluence zones."""
        while True:
            try:
                for symbol in self.symbols:
                    self.detect_confluence_zones(symbol)

                # Update every 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in confluence monitor: {e}")
                await asyncio.sleep(60)

    async def _cache_cleanup(self):
        """Background task to clean up expired cache entries."""
        while True:
            try:
                current_time = datetime.utcnow()

                # Clean up old cache entries
                for symbol in list(self.cache_timestamps.keys()):
                    for timeframe in list(self.cache_timestamps[symbol].keys()):
                        cache_time = self.cache_timestamps[symbol][timeframe]
                        if (current_time - cache_time).total_seconds() > 300:  # 5 minutes
                            if timeframe in self.cache_timestamps[symbol]:
                                del self.cache_timestamps[symbol][timeframe]
                            if symbol in self.data_cache and timeframe in self.data_cache[symbol]:
                                del self.data_cache[symbol][timeframe]

                # Run every 2 minutes
                await asyncio.sleep(120)

            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)

    async def _performance_monitor(self):
        """Monitor and log performance metrics."""
        while True:
            try:
                # Calculate average processing time
                if self.metrics['total_updates'] > 0:
                    self.metrics['avg_processing_time'] = (
                        sum(self.metrics.get('processing_times', [])) /
                        len(self.metrics.get('processing_times', [1]))
                    )

                # Log metrics every minute
                cache_hit_rate = (
                    self.metrics['cache_hits'] /
                    max(1, self.metrics['cache_hits'] + self.metrics['cache_misses'])
                )

                logger.info(f"Multi-TF Data Manager Metrics - "
                           f"Updates: {self.metrics['total_updates']}, "
                           f"Confluence Detections: {self.metrics['confluence_detections']}, "
                           f"Cache Hit Rate: {cache_hit_rate:.2%}, "
                           f"Avg Processing Time: {self.metrics['avg_processing_time']:.3f}s")

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(60)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        cache_hit_rate = (
            self.metrics['cache_hits'] /
            max(1, self.metrics['cache_hits'] + self.metrics['cache_misses'])
        )

        return {
            **self.metrics,
            'cache_hit_rate': cache_hit_rate,
            'active_symbols': list(self.data_cache.keys()),
            'total_confluence_zones': sum(len(zones) for zones in self.confluence_zones.values())
        }