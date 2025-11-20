"""
Confluence Cache Manager

High-performance caching system for computed confluence zones with real-time
updates, memory-efficient storage, and intelligent cache invalidation.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import pickle
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, OrderedDict
import threading
import time
import weakref
from pathlib import Path

from .data_manager import ConfluenceZone

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Any
    timestamp: datetime
    expiry_time: Optional[datetime]
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)
    priority: int = 0  # Higher priority = less likely to be evicted

@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    avg_access_time_ms: float = 0.0
    memory_utilization: float = 0.0
    oldest_entry_age_minutes: float = 0.0

class MemoryEfficientStorage:
    """Memory-efficient storage for large datasets."""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_bytes = 0
        self.data: Dict[str, Any] = {}
        self.size_map: Dict[str, int] = {}
        self.access_order = OrderedDict()
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get data from storage."""
        with self.lock:
            if key in self.data:
                # Move to end (most recently used)
                self.access_order.move_to_end(key)
                return self.data[key]
            return None

    def put(self, key: str, data: Any, size_bytes: int) -> bool:
        """Put data in storage with eviction if needed."""
        with self.lock:
            # Calculate size if not provided
            if size_bytes == 0:
                size_bytes = self._estimate_size(data)

            # Check if we need to evict
            while (self.current_memory_bytes + size_bytes > self.max_memory_bytes and
                   len(self.data) > 0):
                if not self._evict_lru():
                    break  # Can't evict more

            # Store data
            self.data[key] = data
            self.size_map[key] = size_bytes
            self.access_order[key] = datetime.utcnow()
            self.current_memory_bytes += size_bytes

            return True

    def remove(self, key: str) -> bool:
        """Remove data from storage."""
        with self.lock:
            if key in self.data:
                size_bytes = self.size_map.get(key, 0)
                del self.data[key]
                del self.size_map[key]
                self.access_order.pop(key, None)
                self.current_memory_bytes -= size_bytes
                return True
            return False

    def clear(self):
        """Clear all data from storage."""
        with self.lock:
            self.data.clear()
            self.size_map.clear()
            self.access_order.clear()
            self.current_memory_bytes = 0

    def _evict_lru(self) -> bool:
        """Evict least recently used item."""
        if not self.access_order:
            return False

        # Get oldest key
        oldest_key = next(iter(self.access_order))
        return self.remove(oldest_key)

    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data in bytes."""
        try:
            if isinstance(data, (str, bytes)):
                return len(data)
            elif isinstance(data, pd.DataFrame):
                return data.memory_usage(deep=True).sum()
            elif isinstance(data, (list, tuple)):
                return sum(self._estimate_size(item) for item in data)
            elif isinstance(data, dict):
                return sum(self._estimate_size(v) for v in data.values())
            else:
                # Use pickle size as fallback
                return len(pickle.dumps(data))
        except Exception:
            return 1024  # Default estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self.lock:
            return {
                'total_entries': len(self.data),
                'current_memory_bytes': self.current_memory_bytes,
                'max_memory_bytes': self.max_memory_bytes,
                'memory_utilization': self.current_memory_bytes / self.max_memory_bytes,
                'oldest_entry_age_minutes': self._get_oldest_age_minutes()
            }

    def _get_oldest_age_minutes(self) -> float:
        """Get age of oldest entry in minutes."""
        if not self.access_order:
            return 0.0

        oldest_time = min(self.access_order.values())
        return (datetime.utcnow() - oldest_time).total_seconds() / 60

class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        self.max_size = max_size
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Statistics
        self.stats = CacheStats()
        self.access_times = []

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        start_time = time.time()
        try:
            with self.lock:
                entry = self.cache.get(key)
                if entry is None:
                    self.stats.miss_count += 1
                    return None

                # Check if expired
                if entry.expiry_time and datetime.utcnow() > entry.expiry_time:
                    self._remove_entry(key)
                    self.stats.miss_count += 1
                    return None

                # Update access info
                entry.access_count += 1
                entry.last_access = datetime.utcnow()
                self.cache.move_to_end(key)  # Move to end (most recently used)

                self.stats.hit_count += 1
                return entry.data

        finally:
            self._update_access_time(start_time)

    def put(self, key: str, value: Any, ttl_minutes: Optional[int] = None,
            priority: int = 0, tags: Set[str] = None) -> bool:
        """Put value in cache with optional TTL and metadata."""
        try:
            with self.lock:
                # Calculate expiry time
                expiry_time = None
                if ttl_minutes is not None:
                    expiry_time = datetime.utcnow() + timedelta(minutes=ttl_minutes)
                elif self.default_ttl:
                    expiry_time = datetime.utcnow() + self.default_ttl

                # Estimate size
                size_bytes = self._estimate_size(value)

                # Check if we need to evict
                while (len(self.cache) >= self.max_size and
                       key not in self.cache):
                    if not self._evict_lru():
                        break

                # Create entry
                entry = CacheEntry(
                    key=key,
                    data=value,
                    timestamp=datetime.utcnow(),
                    expiry_time=expiry_time,
                    size_bytes=size_bytes,
                    tags=tags or set(),
                    priority=priority
                )

                # Update or insert
                if key in self.cache:
                    old_size = self.cache[key].size_bytes
                    self.stats.total_size_bytes -= old_size

                self.cache[key] = entry
                self.cache.move_to_end(key)

                self.stats.total_size_bytes += size_bytes
                self.stats.total_entries = len(self.cache)

                return True

        except Exception as e:
            logger.error(f"Error putting key {key} in cache: {e}")
            return False

    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            return self._remove_entry(key)

    def _remove_entry(self, key: str) -> bool:
        """Internal remove entry method."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.total_entries = len(self.cache)
            return True
        return False

    def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self.cache:
            return False

        # Find entry with lowest priority among oldest entries
        lru_keys = list(self.cache.keys())[:10]  # Check first 10 oldest
        if not lru_keys:
            return False

        # Select entry with lowest priority
        evict_key = min(lru_keys, key=lambda k: self.cache[k].priority)
        return self._remove_entry(evict_key)

    def clear(self):
        """Clear all entries from cache."""
        with self.lock:
            self.cache.clear()
            self.stats.total_entries = 0
            self.stats.total_size_bytes = 0

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        try:
            with self.lock:
                current_time = datetime.utcnow()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if entry.expiry_time and current_time > entry.expiry_time
                ]

                for key in expired_keys:
                    self._remove_entry(key)

                return len(expired_keys)

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            return 0

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, pd.DataFrame):
                return value.memory_usage(deep=True).sum()
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._estimate_size(v) for v in value.values())
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024

    def _update_access_time(self, start_time: float):
        """Update access time statistics."""
        access_time_ms = (time.time() - start_time) * 1000
        self.access_times.append(access_time_ms)

        # Keep only recent access times
        if len(self.access_times) > 1000:
            self.access_times = self.access_times[-1000:]

        if self.access_times:
            self.stats.avg_access_time_ms = np.mean(self.access_times)

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self.lock:
            self.stats.memory_utilization = self.stats.total_size_bytes / (512 * 1024 * 1024)  # Assuming 512MB limit

            if self.cache:
                oldest_entry = min(self.cache.values(), key=lambda e: e.timestamp)
                self.stats.oldest_entry_age_minutes = (
                    datetime.utcnow() - oldest_entry.timestamp
                ).total_seconds() / 60

            return self.stats

class ComputedDataCache:
    """Cache for computationally expensive data like confluence zones and indicators."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize caches for different data types
        self.confluence_cache = LRUCache(
            max_size=config.get('confluence_cache_size', 500),
            default_ttl_minutes=config.get('confluence_ttl_minutes', 10)
        )

        self.indicator_cache = LRUCache(
            max_size=config.get('indicator_cache_size', 1000),
            default_ttl_minutes=config.get('indicator_ttl_minutes', 5)
        )

        self.analysis_cache = LRUCache(
            max_size=config.get('analysis_cache_size', 200),
            default_ttl_minutes=config.get('analysis_ttl_minutes', 15)
        )

        # Memory storage for large data
        self.memory_storage = MemoryEfficientStorage(
            max_memory_mb=config.get('max_memory_mb', 512)
        )

        # Background cleanup task
        self.cleanup_task = None
        self.running = False

        logger.info("Computed data cache initialized")

    async def start(self):
        """Start background cleanup tasks."""
        self.running = True
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Cache cleanup task started")

    async def stop(self):
        """Stop background tasks and cleanup."""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache cleanup task stopped")

    def get_confluence_zones(self, symbol: str, timeframes: List[str],
                           hash_key: Optional[str] = None) -> Optional[List[ConfluenceZone]]:
        """Get cached confluence zones."""
        if not hash_key:
            hash_key = self._generate_confluence_key(symbol, timeframes)

        return self.confluence_cache.get(hash_key)

    def cache_confluence_zones(self, symbol: str, timeframes: List[str],
                             zones: List[ConfluenceZone],
                             ttl_minutes: Optional[int] = None) -> bool:
        """Cache confluence zones."""
        hash_key = self._generate_confluence_key(symbol, timeframes)

        # Convert confluence zones to serializable format
        serializable_zones = [asdict(zone) for zone in zones]

        return self.confluence_cache.put(
            hash_key, serializable_zones, ttl_minutes,
            priority=1, tags={'confluence', symbol}
        )

    def get_indicators(self, symbol: str, timeframe: str, indicator_type: str,
                      params_hash: str) -> Optional[Any]:
        """Get cached technical indicators."""
        key = f"indicators:{symbol}:{timeframe}:{indicator_type}:{params_hash}"
        return self.indicator_cache.get(key)

    def cache_indicators(self, symbol: str, timeframe: str, indicator_type: str,
                        params_hash: str, indicators: Any,
                        ttl_minutes: Optional[int] = None) -> bool:
        """Cache technical indicators."""
        key = f"indicators:{symbol}:{timeframe}:{indicator_type}:{params_hash}"
        return self.indicator_cache.put(
            key, indicators, ttl_minutes,
            priority=0, tags={'indicators', symbol, timeframe}
        )

    def get_analysis_result(self, analysis_type: str, symbol: str,
                          params_hash: str) -> Optional[Any]:
        """Get cached analysis result."""
        key = f"analysis:{analysis_type}:{symbol}:{params_hash}"
        return self.analysis_cache.get(key)

    def cache_analysis_result(self, analysis_type: str, symbol: str,
                             params_hash: str, result: Any,
                             ttl_minutes: Optional[int] = None) -> bool:
        """Cache analysis result."""
        key = f"analysis:{analysis_type}:{symbol}:{params_hash}"
        return self.analysis_cache.put(
            key, result, ttl_minutes,
            priority=2, tags={'analysis', symbol, analysis_type}
        )

    def store_large_dataset(self, key: str, data: Any) -> bool:
        """Store large dataset in memory-efficient storage."""
        try:
            # Pickle the data for efficient storage
            serialized_data = pickle.dumps(data)
            return self.memory_storage.put(key, serialized_data, len(serialized_data))
        except Exception as e:
            logger.error(f"Error storing large dataset {key}: {e}")
            return False

    def get_large_dataset(self, key: str) -> Optional[Any]:
        """Get large dataset from memory-efficient storage."""
        try:
            serialized_data = self.memory_storage.get(key)
            if serialized_data:
                return pickle.loads(serialized_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving large dataset {key}: {e}")
            return None

    def invalidate_symbol(self, symbol: str):
        """Invalidate all cache entries for a symbol."""
        try:
            # Invalidate confluence cache
            self._invalidate_by_tag('confluence', symbol)

            # Invalidate indicator cache
            self._invalidate_by_tag('indicators', symbol)

            # Invalidate analysis cache
            self._invalidate_by_tag('analysis', symbol)

            # Clear large datasets for symbol
            keys_to_remove = [
                key for key in self.memory_storage.data.keys()
                if symbol in key
            ]
            for key in keys_to_remove:
                self.memory_storage.remove(key)

            logger.info(f"Invalidated cache entries for symbol {symbol}")

        except Exception as e:
            logger.error(f"Error invalidating symbol {symbol}: {e}")

    def _invalidate_by_tag(self, cache_type: str, symbol: str):
        """Invalidate cache entries by tag and symbol."""
        cache_map = {
            'confluence': self.confluence_cache,
            'indicators': self.indicator_cache,
            'analysis': self.analysis_cache
        }

        cache = cache_map.get(cache_type)
        if not cache:
            return

        keys_to_remove = []
        for key, entry in cache.cache.items():
            if symbol in entry.tags:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            cache.remove(key)

    def _generate_confluence_key(self, symbol: str, timeframes: List[str]) -> str:
        """Generate cache key for confluence data."""
        timeframes_str = ','.join(sorted(timeframes))
        key_string = f"{symbol}:{timeframes_str}"
        return hashlib.md5(key_string.encode()).hexdigest()

    async def _periodic_cleanup(self):
        """Periodic cleanup of expired entries."""
        while self.running:
            try:
                # Cleanup expired entries
                confluence_cleaned = self.confluence_cache.cleanup_expired()
                indicator_cleaned = self.indicator_cache.cleanup_expired()
                analysis_cleaned = self.analysis_cache.cleanup_expired()

                if confluence_cleaned + indicator_cleaned + analysis_cleaned > 0:
                    logger.debug(f"Cleaned {confluence_cleaned + indicator_cleaned + analysis_cleaned} expired cache entries")

                # Run every 5 minutes
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
                await asyncio.sleep(60)

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            stats = {
                'confluence_cache': asdict(self.confluence_cache.get_stats()),
                'indicator_cache': asdict(self.indicator_cache.get_stats()),
                'analysis_cache': asdict(self.analysis_cache.get_stats()),
                'memory_storage': self.memory_storage.get_stats(),
                'total_memory_mb': sum([
                    self.confluence_cache.stats.total_size_bytes,
                    self.indicator_cache.stats.total_size_bytes,
                    self.analysis_cache.stats.total_size_bytes,
                    self.memory_storage.current_memory_bytes
                ]) / (1024 * 1024)
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}

    def export_cache_state(self, filepath: str):
        """Export current cache state for debugging."""
        try:
            state = {
                'timestamp': datetime.utcnow().isoformat(),
                'statistics': self.get_comprehensive_stats(),
                'confluence_entries': len(self.confluence_cache.cache),
                'indicator_entries': len(self.indicator_cache.cache),
                'analysis_entries': len(self.analysis_cache.cache)
            }

            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info(f"Cache state exported to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting cache state: {e}")

    def warm_cache(self, symbols: List[str], timeframes: List[str]):
        """Warm up cache with commonly accessed data."""
        try:
            logger.info("Starting cache warm-up...")

            # This is a placeholder for cache warming logic
            # In practice, you would pre-compute and cache common calculations
            # like basic indicators for major symbols and timeframes

            logger.info("Cache warm-up completed")

        except Exception as e:
            logger.error(f"Error during cache warm-up: {e}")

    def optimize_memory_usage(self):
        """Optimize memory usage by cleaning up low-priority entries."""
        try:
            # Remove low-priority entries if memory usage is high
            memory_usage = self.memory_storage.current_memory_bytes
            max_memory = self.memory_storage.max_memory_bytes

            if memory_usage / max_memory > 0.8:  # 80% threshold
                logger.info("Memory usage high, optimizing cache...")

                # Clear analysis cache first (lowest priority)
                self.analysis_cache.clear()

                # Clear older indicator entries
                with self.indicator_cache.lock:
                    keys_to_remove = []
                    for key, entry in self.indicator_cache.cache.items():
                        if (entry.priority == 0 and
                            (datetime.utcnow() - entry.last_access).total_seconds() > 300):  # 5 minutes
                            keys_to_remove.append(key)

                    for key in keys_to_remove:
                        self.indicator_cache._remove_entry(key)

                logger.info(f"Removed {len(keys_to_remove)} low-priority indicator entries")

        except Exception as e:
            logger.error(f"Error optimizing memory usage: {e}")

class ConfluenceCacheManager:
    """
    Main cache manager for the multi-timeframe confluence system.

    Provides high-performance caching with intelligent invalidation,
    memory optimization, and real-time updates.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache = ComputedDataCache(config.get('cache', {}))
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Performance metrics
        self.metrics = {
            'cache_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'invalidations': 0,
            'optimizations': 0
        }

        logger.info("Confluence cache manager initialized")

    async def initialize(self):
        """Initialize the cache manager."""
        await self.cache.start()

        # Start background optimization task
        asyncio.create_task(self._periodic_optimization())

        logger.info("Confluence cache manager initialized successfully")

    async def shutdown(self):
        """Shutdown the cache manager."""
        await self.cache.stop()
        self.executor.shutdown(wait=True)

    def get_cached_confluence(self, symbol: str, timeframes: List[str],
                            current_data_hash: Optional[str] = None) -> Optional[List[ConfluenceZone]]:
        """Get cached confluence zones for symbol and timeframes."""
        try:
            self.metrics['cache_operations'] += 1

            cached_data = self.cache.get_confluence_zones(symbol, timeframes, current_data_hash)

            if cached_data is not None:
                self.metrics['cache_hits'] += 1
                # Convert back to ConfluenceZone objects
                zones = [ConfluenceZone(**zone_data) for zone_data in cached_data]
                return zones
            else:
                self.metrics['cache_misses'] += 1
                return None

        except Exception as e:
            logger.error(f"Error getting cached confluence: {e}")
            self.metrics['cache_misses'] += 1
            return None

    def cache_confluence_result(self, symbol: str, timeframes: List[str],
                              zones: List[ConfluenceZone],
                              ttl_minutes: Optional[int] = None) -> bool:
        """Cache confluence analysis result."""
        try:
            success = self.cache.cache_confluence_zones(
                symbol, timeframes, zones, ttl_minutes
            )

            if success:
                logger.debug(f"Cached confluence zones for {symbol} across {timeframes}")

            return success

        except Exception as e:
            logger.error(f"Error caching confluence result: {e}")
            return False

    def invalidate_symbol_cache(self, symbol: str):
        """Invalidate all cached data for a symbol."""
        try:
            self.cache.invalidate_symbol(symbol)
            self.metrics['invalidations'] += 1
            logger.debug(f"Invalidated cache for symbol {symbol}")

        except Exception as e:
            logger.error(f"Error invalidating symbol cache: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        try:
            cache_stats = self.cache.get_comprehensive_stats()

            # Calculate hit rates
            total_ops = self.metrics['cache_hits'] + self.metrics['cache_misses']
            hit_rate = self.metrics['cache_hits'] / max(1, total_ops)

            return {
                'operations': self.metrics,
                'cache_statistics': cache_stats,
                'hit_rate': hit_rate,
                'total_memory_mb': cache_stats.get('total_memory_mb', 0)
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}

    async def _periodic_optimization(self):
        """Background task for periodic cache optimization."""
        while True:
            try:
                # Optimize memory usage every 10 minutes
                self.cache.optimize_memory_usage()
                self.metrics['optimizations'] += 1

                await asyncio.sleep(600)

            except Exception as e:
                logger.error(f"Error during periodic optimization: {e}")
                await asyncio.sleep(60)