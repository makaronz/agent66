"""
Advanced Rate Limit Management System

Implements intelligent rate limiting with per-exchange tracking, request queuing,
adaptive backoff strategies, and monitoring integration.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import json
from datetime import datetime, timedelta
import heapq

from .production_config import ExchangeType, RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limits."""
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    WEIGHT_PER_MINUTE = "weight_per_minute"  # For exchanges that use weight-based limits
    ORDERS_PER_SECOND = "orders_per_second"  # For trading-specific limits


class RequestPriority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RateLimitWindow:
    """Rate limit tracking window."""
    limit_type: RateLimitType
    limit_value: int
    window_size: float  # in seconds
    requests: deque = field(default_factory=deque)
    total_weight: int = 0
    
    def add_request(self, timestamp: float, weight: int = 1):
        """Add a request to the window."""
        self.requests.append((timestamp, weight))
        self.total_weight += weight
        self._cleanup_old_requests(timestamp)
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove requests outside the window."""
        cutoff_time = current_time - self.window_size
        while self.requests and self.requests[0][0] < cutoff_time:
            _, weight = self.requests.popleft()
            self.total_weight -= weight
    
    def get_current_usage(self, current_time: float) -> int:
        """Get current usage within the window."""
        self._cleanup_old_requests(current_time)
        if self.limit_type == RateLimitType.WEIGHT_PER_MINUTE:
            return self.total_weight
        return len(self.requests)
    
    def get_remaining_capacity(self, current_time: float) -> int:
        """Get remaining capacity in the window."""
        current_usage = self.get_current_usage(current_time)
        return max(0, self.limit_value - current_usage)
    
    def time_until_next_slot(self, current_time: float) -> float:
        """Get time until next request slot is available."""
        if self.get_remaining_capacity(current_time) > 0:
            return 0.0
        
        if not self.requests:
            return 0.0
        
        # Time until oldest request expires
        oldest_request_time = self.requests[0][0]
        return max(0.0, oldest_request_time + self.window_size - current_time)


@dataclass
class QueuedRequest:
    """Queued request waiting for rate limit availability."""
    request_id: str
    exchange_type: ExchangeType
    endpoint: str
    priority: RequestPriority
    weight: int
    queued_at: float
    timeout: float
    callback: Optional[Callable] = None
    future: Optional[asyncio.Future] = None
    
    def __lt__(self, other):
        """For priority queue ordering (higher priority first)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.queued_at < other.queued_at
    
    def is_expired(self, current_time: float) -> bool:
        """Check if request has expired."""
        return current_time > (self.queued_at + self.timeout)


class ExchangeRateLimiter:
    """
    Rate limiter for a specific exchange.
    
    Manages multiple rate limit windows and request queuing.
    """
    
    def __init__(self, exchange_type: ExchangeType, config: RateLimitConfig):
        """
        Initialize exchange rate limiter.
        
        Args:
            exchange_type: Exchange type
            config: Rate limit configuration
        """
        self.exchange_type = exchange_type
        self.config = config
        
        # Rate limit windows
        self.windows: Dict[RateLimitType, RateLimitWindow] = {}
        self._initialize_windows()
        
        # Request queue
        self.request_queue: List[QueuedRequest] = []
        self.processing_queue = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "queued_requests": 0,
            "rejected_requests": 0,
            "rate_limit_hits": 0,
            "average_wait_time": 0.0,
            "last_request_time": 0.0
        }
        
        # Adaptive backoff
        self.consecutive_rate_limits = 0
        self.backoff_multiplier = 1.0
        self.last_rate_limit_time = 0.0
        
        logger.info(f"Initialized rate limiter for {exchange_type.value}")
    
    def _initialize_windows(self):
        """Initialize rate limit windows based on exchange type."""
        # Common windows
        self.windows[RateLimitType.REQUESTS_PER_SECOND] = RateLimitWindow(
            limit_type=RateLimitType.REQUESTS_PER_SECOND,
            limit_value=self.config.requests_per_second,
            window_size=1.0
        )
        
        self.windows[RateLimitType.REQUESTS_PER_MINUTE] = RateLimitWindow(
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            limit_value=self.config.requests_per_minute,
            window_size=60.0
        )
        
        # Exchange-specific windows
        if self.exchange_type == ExchangeType.BINANCE:
            # Binance uses weight-based limits
            self.windows[RateLimitType.WEIGHT_PER_MINUTE] = RateLimitWindow(
                limit_type=RateLimitType.WEIGHT_PER_MINUTE,
                limit_value=1200,  # Default weight limit
                window_size=60.0
            )
            
            self.windows[RateLimitType.ORDERS_PER_SECOND] = RateLimitWindow(
                limit_type=RateLimitType.ORDERS_PER_SECOND,
                limit_value=10,  # Conservative order limit
                window_size=1.0
            )
    
    async def acquire_permit(
        self, 
        endpoint: str, 
        weight: int = 1, 
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float = 30.0
    ) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            endpoint: API endpoint being called
            weight: Request weight (for weight-based limits)
            priority: Request priority
            timeout: Maximum time to wait for permit
            
        Returns:
            bool: True if permit acquired, False if timeout/rejected
        """
        current_time = time.time()
        request_id = f"{self.exchange_type.value}_{current_time}_{id(endpoint)}"
        
        # Check if we can process immediately
        if self._can_process_immediately(weight, current_time):
            self._record_request(weight, current_time)
            return True
        
        # Queue the request
        future = asyncio.Future()
        queued_request = QueuedRequest(
            request_id=request_id,
            exchange_type=self.exchange_type,
            endpoint=endpoint,
            priority=priority,
            weight=weight,
            queued_at=current_time,
            timeout=timeout,
            future=future
        )
        
        heapq.heappush(self.request_queue, queued_request)
        self.stats["queued_requests"] += 1
        
        # Start queue processing if not already running
        if not self.processing_queue:
            asyncio.create_task(self._process_queue())
        
        try:
            # Wait for permit or timeout
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout for {self.exchange_type.value} endpoint {endpoint}")
            self.stats["rejected_requests"] += 1
            return False
    
    def _can_process_immediately(self, weight: int, current_time: float) -> bool:
        """Check if request can be processed immediately."""
        for window in self.windows.values():
            required_capacity = weight if window.limit_type == RateLimitType.WEIGHT_PER_MINUTE else 1
            if window.get_remaining_capacity(current_time) < required_capacity:
                return False
        return True
    
    def _record_request(self, weight: int, current_time: float):
        """Record a request in all applicable windows."""
        for window in self.windows.values():
            window.add_request(current_time, weight)
        
        self.stats["total_requests"] += 1
        self.stats["last_request_time"] = current_time
        
        # Reset consecutive rate limits on successful request
        self.consecutive_rate_limits = 0
        self.backoff_multiplier = 1.0
    
    async def _process_queue(self):
        """Process queued requests."""
        self.processing_queue = True
        
        try:
            while self.request_queue:
                current_time = time.time()
                
                # Remove expired requests
                self._cleanup_expired_requests(current_time)
                
                if not self.request_queue:
                    break
                
                # Get highest priority request
                next_request = self.request_queue[0]
                
                # Check if we can process it
                if self._can_process_immediately(next_request.weight, current_time):
                    # Remove from queue and process
                    heapq.heappop(self.request_queue)
                    self._record_request(next_request.weight, current_time)
                    
                    if next_request.future and not next_request.future.done():
                        next_request.future.set_result(True)
                else:
                    # Calculate wait time
                    wait_time = self._calculate_wait_time(next_request.weight, current_time)
                    if wait_time > 0:
                        await asyncio.sleep(min(wait_time, 1.0))  # Max 1 second sleep
                    continue
                
        except Exception as e:
            logger.error(f"Error processing queue for {self.exchange_type.value}: {e}")
        finally:
            self.processing_queue = False
    
    def _cleanup_expired_requests(self, current_time: float):
        """Remove expired requests from queue."""
        expired_requests = []
        
        for i, request in enumerate(self.request_queue):
            if request.is_expired(current_time):
                expired_requests.append(i)
                if request.future and not request.future.done():
                    request.future.set_result(False)
        
        # Remove expired requests (in reverse order to maintain indices)
        for i in reversed(expired_requests):
            del self.request_queue[i]
        
        # Re-heapify if we removed items
        if expired_requests:
            heapq.heapify(self.request_queue)
            self.stats["rejected_requests"] += len(expired_requests)
    
    def _calculate_wait_time(self, weight: int, current_time: float) -> float:
        """Calculate minimum wait time for a request."""
        max_wait_time = 0.0
        
        for window in self.windows.values():
            required_capacity = weight if window.limit_type == RateLimitType.WEIGHT_PER_MINUTE else 1
            if window.get_remaining_capacity(current_time) < required_capacity:
                wait_time = window.time_until_next_slot(current_time)
                max_wait_time = max(max_wait_time, wait_time)
        
        # Apply adaptive backoff
        if max_wait_time > 0:
            max_wait_time *= self.backoff_multiplier
        
        return max_wait_time
    
    def handle_rate_limit_error(self, retry_after: Optional[float] = None):
        """Handle rate limit error from exchange."""
        current_time = time.time()
        self.consecutive_rate_limits += 1
        self.last_rate_limit_time = current_time
        self.stats["rate_limit_hits"] += 1
        
        # Increase backoff multiplier
        self.backoff_multiplier = min(
            self.backoff_multiplier * self.config.backoff_factor,
            self.config.max_backoff_time / 60.0  # Max multiplier based on max backoff time
        )
        
        logger.warning(f"Rate limit hit for {self.exchange_type.value} (consecutive: {self.consecutive_rate_limits})")
        
        # If exchange provides retry-after, use it to adjust our limits
        if retry_after:
            self._adjust_limits_based_on_retry_after(retry_after)
    
    def _adjust_limits_based_on_retry_after(self, retry_after: float):
        """Adjust rate limits based on exchange retry-after header."""
        # Temporarily reduce limits by 20%
        reduction_factor = 0.8
        
        for window in self.windows.values():
            original_limit = window.limit_value
            window.limit_value = int(original_limit * reduction_factor)
            logger.info(f"Temporarily reduced {window.limit_type.value} limit from {original_limit} to {window.limit_value}")
        
        # Schedule limit restoration
        asyncio.create_task(self._restore_limits_after_delay(retry_after * 2))
    
    async def _restore_limits_after_delay(self, delay: float):
        """Restore original limits after delay."""
        await asyncio.sleep(delay)
        
        # Restore original limits
        for window in self.windows.values():
            if window.limit_type == RateLimitType.REQUESTS_PER_SECOND:
                window.limit_value = self.config.requests_per_second
            elif window.limit_type == RateLimitType.REQUESTS_PER_MINUTE:
                window.limit_value = self.config.requests_per_minute
        
        logger.info(f"Restored original rate limits for {self.exchange_type.value}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        current_time = time.time()
        
        window_status = {}
        for limit_type, window in self.windows.items():
            window_status[limit_type.value] = {
                "limit": window.limit_value,
                "current_usage": window.get_current_usage(current_time),
                "remaining_capacity": window.get_remaining_capacity(current_time),
                "time_until_next_slot": window.time_until_next_slot(current_time)
            }
        
        return {
            "exchange": self.exchange_type.value,
            "windows": window_status,
            "queue_size": len(self.request_queue),
            "processing_queue": self.processing_queue,
            "consecutive_rate_limits": self.consecutive_rate_limits,
            "backoff_multiplier": self.backoff_multiplier,
            "statistics": self.stats.copy()
        }


class RateLimitManager:
    """
    Global rate limit manager for all exchanges.
    
    Coordinates rate limiting across multiple exchanges and provides
    monitoring and analytics capabilities.
    """
    
    def __init__(self):
        """Initialize rate limit manager."""
        self.limiters: Dict[ExchangeType, ExchangeRateLimiter] = {}
        self.global_stats = {
            "total_requests": 0,
            "total_rate_limit_hits": 0,
            "average_queue_size": 0.0,
            "last_update": time.time()
        }
        
        # Monitoring
        self.monitoring_callbacks: List[Callable] = []
        self.monitoring_interval = 60.0  # seconds
        self.monitoring_task = None
        
        logger.info("Initialized global rate limit manager")
    
    def add_exchange(self, exchange_type: ExchangeType, config: RateLimitConfig):
        """
        Add exchange to rate limit management.
        
        Args:
            exchange_type: Exchange type
            config: Rate limit configuration
        """
        if exchange_type in self.limiters:
            logger.warning(f"Rate limiter for {exchange_type.value} already exists, replacing")
        
        self.limiters[exchange_type] = ExchangeRateLimiter(exchange_type, config)
        logger.info(f"Added rate limiter for {exchange_type.value}")
    
    def remove_exchange(self, exchange_type: ExchangeType):
        """Remove exchange from rate limit management."""
        if exchange_type in self.limiters:
            del self.limiters[exchange_type]
            logger.info(f"Removed rate limiter for {exchange_type.value}")
    
    async def acquire_permit(
        self, 
        exchange_type: ExchangeType,
        endpoint: str,
        weight: int = 1,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float = 30.0
    ) -> bool:
        """
        Acquire permit for exchange request.
        
        Args:
            exchange_type: Exchange type
            endpoint: API endpoint
            weight: Request weight
            priority: Request priority
            timeout: Timeout for permit acquisition
            
        Returns:
            bool: True if permit acquired
        """
        limiter = self.limiters.get(exchange_type)
        if not limiter:
            logger.warning(f"No rate limiter found for {exchange_type.value}, allowing request")
            return True
        
        success = await limiter.acquire_permit(endpoint, weight, priority, timeout)
        
        # Update global stats
        self.global_stats["total_requests"] += 1
        
        return success
    
    def handle_rate_limit_error(self, exchange_type: ExchangeType, retry_after: Optional[float] = None):
        """Handle rate limit error for exchange."""
        limiter = self.limiters.get(exchange_type)
        if limiter:
            limiter.handle_rate_limit_error(retry_after)
            self.global_stats["total_rate_limit_hits"] += 1
    
    def get_exchange_status(self, exchange_type: ExchangeType) -> Optional[Dict[str, Any]]:
        """Get status for specific exchange."""
        limiter = self.limiters.get(exchange_type)
        return limiter.get_status() if limiter else None
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status for all exchanges."""
        exchange_status = {}
        total_queue_size = 0
        
        for exchange_type, limiter in self.limiters.items():
            status = limiter.get_status()
            exchange_status[exchange_type.value] = status
            total_queue_size += status["queue_size"]
        
        # Update global stats
        self.global_stats["average_queue_size"] = total_queue_size / len(self.limiters) if self.limiters else 0
        self.global_stats["last_update"] = time.time()
        
        return {
            "global_statistics": self.global_stats.copy(),
            "exchanges": exchange_status
        }
    
    def add_monitoring_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for monitoring updates."""
        self.monitoring_callbacks.append(callback)
    
    def start_monitoring(self):
        """Start monitoring task."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started rate limit monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring task."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
            logger.info("Stopped rate limit monitoring")
    
    async def _monitoring_loop(self):
        """Monitoring loop for rate limit statistics."""
        try:
            while True:
                await asyncio.sleep(self.monitoring_interval)
                
                # Get current status
                status = self.get_all_status()
                
                # Notify callbacks
                for callback in self.monitoring_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(status)
                        else:
                            callback(status)
                    except Exception as e:
                        logger.error(f"Monitoring callback failed: {e}")
                
        except asyncio.CancelledError:
            logger.info("Rate limit monitoring cancelled")
        except Exception as e:
            logger.error(f"Rate limit monitoring error: {e}")
    
    def export_statistics(self, file_path: str):
        """Export rate limit statistics to file."""
        try:
            status = self.get_all_status()
            status["export_timestamp"] = datetime.utcnow().isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(status, f, indent=2)
            
            logger.info(f"Rate limit statistics exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export statistics: {e}")


# Global rate limit manager instance
rate_limit_manager = RateLimitManager()


# Convenience functions
async def acquire_rate_limit_permit(
    exchange_type: ExchangeType,
    endpoint: str,
    weight: int = 1,
    priority: RequestPriority = RequestPriority.NORMAL,
    timeout: float = 30.0
) -> bool:
    """Acquire rate limit permit using global manager."""
    return await rate_limit_manager.acquire_permit(
        exchange_type, endpoint, weight, priority, timeout
    )


def handle_rate_limit_error(exchange_type: ExchangeType, retry_after: Optional[float] = None):
    """Handle rate limit error using global manager."""
    rate_limit_manager.handle_rate_limit_error(exchange_type, retry_after)


def initialize_rate_limiters(exchange_configs: Dict[ExchangeType, RateLimitConfig]):
    """Initialize rate limiters for all exchanges."""
    for exchange_type, config in exchange_configs.items():
        rate_limit_manager.add_exchange(exchange_type, config)
    
    # Start monitoring
    rate_limit_manager.start_monitoring()
    
    logger.info(f"Initialized rate limiters for {len(exchange_configs)} exchanges")


# Decorator for automatic rate limiting
def rate_limited(
    exchange_type: ExchangeType,
    endpoint: str,
    weight: int = 1,
    priority: RequestPriority = RequestPriority.NORMAL,
    timeout: float = 30.0
):
    """
    Decorator for automatic rate limiting of functions.
    
    Args:
        exchange_type: Exchange type
        endpoint: API endpoint
        weight: Request weight
        priority: Request priority
        timeout: Timeout for permit acquisition
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Acquire permit
            permit_acquired = await acquire_rate_limit_permit(
                exchange_type, endpoint, weight, priority, timeout
            )
            
            if not permit_acquired:
                raise Exception(f"Failed to acquire rate limit permit for {exchange_type.value} {endpoint}")
            
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                # Check if it's a rate limit error
                if "rate limit" in str(e).lower() or "429" in str(e):
                    handle_rate_limit_error(exchange_type)
                raise
        
        return wrapper
    return decorator