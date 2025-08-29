"""
Intelligent Request Queuing System

Advanced request queuing with priority management, load balancing,
and adaptive scheduling for optimal exchange API utilization.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import heapq
import json
from datetime import datetime, timedelta
import statistics

from .production_config import ExchangeType
from .rate_limiter import RequestPriority, RateLimitType

logger = logging.getLogger(__name__)


class QueueStrategy(Enum):
    """Request queuing strategies."""
    FIFO = "fifo"  # First In, First Out
    PRIORITY = "priority"  # Priority-based
    WEIGHTED_FAIR = "weighted_fair"  # Weighted fair queuing
    ADAPTIVE = "adaptive"  # Adaptive based on performance


class RequestType(Enum):
    """Types of requests for categorization."""
    MARKET_DATA = "market_data"
    ACCOUNT_INFO = "account_info"
    ORDER_MANAGEMENT = "order_management"
    HISTORICAL_DATA = "historical_data"
    SYSTEM_INFO = "system_info"


@dataclass
class QueuedRequest:
    """Enhanced queued request with additional metadata."""
    request_id: str
    exchange_type: ExchangeType
    request_type: RequestType
    endpoint: str
    method: str
    params: Dict[str, Any]
    priority: RequestPriority
    weight: int
    queued_at: float
    timeout: float
    max_retries: int
    retry_count: int = 0
    estimated_duration: float = 0.1  # seconds
    callback: Optional[Callable] = None
    future: Optional[asyncio.Future] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering."""
        # Higher priority first, then earlier queued time
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.queued_at < other.queued_at
    
    def is_expired(self, current_time: float) -> bool:
        """Check if request has expired."""
        return current_time > (self.queued_at + self.timeout)
    
    def should_retry(self) -> bool:
        """Check if request should be retried."""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "request_id": self.request_id,
            "exchange": self.exchange_type.value,
            "request_type": self.request_type.value,
            "endpoint": self.endpoint,
            "method": self.method,
            "priority": self.priority.value,
            "weight": self.weight,
            "queued_at": self.queued_at,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "estimated_duration": self.estimated_duration
        }


@dataclass
class QueueMetrics:
    """Queue performance metrics."""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    expired_requests: int = 0
    average_wait_time: float = 0.0
    average_processing_time: float = 0.0
    throughput_per_second: float = 0.0
    queue_size_history: deque = field(default_factory=lambda: deque(maxlen=100))
    wait_times: deque = field(default_factory=lambda: deque(maxlen=100))
    processing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_completion(self, wait_time: float, processing_time: float):
        """Update metrics on request completion."""
        self.completed_requests += 1
        self.wait_times.append(wait_time)
        self.processing_times.append(processing_time)
        
        # Update averages
        if self.wait_times:
            self.average_wait_time = statistics.mean(self.wait_times)
        if self.processing_times:
            self.average_processing_time = statistics.mean(self.processing_times)
    
    def update_failure(self):
        """Update metrics on request failure."""
        self.failed_requests += 1
    
    def update_expiration(self):
        """Update metrics on request expiration."""
        self.expired_requests += 1
    
    def calculate_throughput(self, time_window: float = 60.0) -> float:
        """Calculate throughput over time window."""
        current_time = time.time()
        recent_completions = sum(1 for t in self.processing_times 
                               if current_time - t <= time_window)
        return recent_completions / time_window


class IntelligentRequestQueue:
    """
    Intelligent request queue for a specific exchange.
    
    Features:
    - Multiple queuing strategies
    - Priority-based scheduling
    - Load balancing
    - Adaptive performance optimization
    - Comprehensive metrics
    """
    
    def __init__(
        self, 
        exchange_type: ExchangeType,
        strategy: QueueStrategy = QueueStrategy.PRIORITY,
        max_queue_size: int = 1000,
        max_concurrent_requests: int = 10
    ):
        """
        Initialize intelligent request queue.
        
        Args:
            exchange_type: Exchange type
            strategy: Queuing strategy
            max_queue_size: Maximum queue size
            max_concurrent_requests: Maximum concurrent requests
        """
        self.exchange_type = exchange_type
        self.strategy = strategy
        self.max_queue_size = max_queue_size
        self.max_concurrent_requests = max_concurrent_requests
        
        # Queues for different strategies
        self.priority_queue: List[QueuedRequest] = []
        self.fifo_queue: deque = deque()
        self.weighted_queues: Dict[RequestType, deque] = defaultdict(deque)
        
        # Active requests
        self.active_requests: Dict[str, QueuedRequest] = {}
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Metrics and monitoring
        self.metrics = QueueMetrics()
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        
        # Adaptive parameters
        self.endpoint_weights: Dict[str, float] = {}
        self.endpoint_success_rates: Dict[str, float] = {}
        self.adaptive_priorities: Dict[RequestType, float] = {
            RequestType.ORDER_MANAGEMENT: 1.0,
            RequestType.MARKET_DATA: 0.8,
            RequestType.ACCOUNT_INFO: 0.6,
            RequestType.HISTORICAL_DATA: 0.4,
            RequestType.SYSTEM_INFO: 0.2
        }
        
        # Queue processing
        self.processing_task: Optional[asyncio.Task] = None
        self.is_processing = False
        
        logger.info(f"Initialized intelligent request queue for {exchange_type.value}")
    
    async def enqueue_request(
        self,
        request_type: RequestType,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        weight: int = 1,
        timeout: float = 30.0,
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> asyncio.Future:
        """
        Enqueue a request for processing.
        
        Args:
            request_type: Type of request
            endpoint: API endpoint
            method: HTTP method
            params: Request parameters
            priority: Request priority
            weight: Request weight
            timeout: Request timeout
            max_retries: Maximum retry attempts
            context: Additional context
            
        Returns:
            asyncio.Future: Future that resolves when request is processed
        """
        current_time = time.time()
        request_id = f"{self.exchange_type.value}_{current_time}_{id(endpoint)}"
        
        # Check queue size limit
        if self._get_total_queue_size() >= self.max_queue_size:
            logger.warning(f"Queue full for {self.exchange_type.value}, rejecting request")
            future = asyncio.Future()
            future.set_exception(Exception("Queue full"))
            return future
        
        # Estimate request duration based on history
        estimated_duration = self._estimate_request_duration(endpoint, request_type)
        
        # Create queued request
        future = asyncio.Future()
        queued_request = QueuedRequest(
            request_id=request_id,
            exchange_type=self.exchange_type,
            request_type=request_type,
            endpoint=endpoint,
            method=method,
            params=params or {},
            priority=priority,
            weight=weight,
            queued_at=current_time,
            timeout=timeout,
            max_retries=max_retries,
            estimated_duration=estimated_duration,
            future=future,
            context=context or {}
        )
        
        # Add to appropriate queue based on strategy
        self._add_to_queue(queued_request)
        
        # Update metrics
        self.metrics.total_requests += 1
        self.metrics.queue_size_history.append(self._get_total_queue_size())
        
        # Start processing if not already running
        if not self.is_processing:
            self.processing_task = asyncio.create_task(self._process_queue())
        
        logger.debug(f"Enqueued request {request_id} for {self.exchange_type.value}")
        return future
    
    def _add_to_queue(self, request: QueuedRequest):
        """Add request to appropriate queue based on strategy."""
        if self.strategy == QueueStrategy.FIFO:
            self.fifo_queue.append(request)
        elif self.strategy == QueueStrategy.PRIORITY:
            heapq.heappush(self.priority_queue, request)
        elif self.strategy == QueueStrategy.WEIGHTED_FAIR:
            self.weighted_queues[request.request_type].append(request)
        elif self.strategy == QueueStrategy.ADAPTIVE:
            # Use priority queue with adaptive priorities
            request.priority = self._calculate_adaptive_priority(request)
            heapq.heappush(self.priority_queue, request)
    
    def _calculate_adaptive_priority(self, request: QueuedRequest) -> RequestPriority:
        """Calculate adaptive priority based on performance metrics."""
        base_priority = self.adaptive_priorities.get(request.request_type, 0.5)
        
        # Adjust based on endpoint success rate
        success_rate = self.endpoint_success_rates.get(request.endpoint, 1.0)
        priority_adjustment = success_rate * 0.2  # Max 20% adjustment
        
        # Adjust based on queue age
        queue_age_factor = min(1.0, (time.time() - request.queued_at) / 60.0)  # Max factor at 1 minute
        priority_adjustment += queue_age_factor * 0.1  # Max 10% adjustment
        
        final_priority = base_priority + priority_adjustment
        
        # Map to RequestPriority enum
        if final_priority >= 0.8:
            return RequestPriority.CRITICAL
        elif final_priority >= 0.6:
            return RequestPriority.HIGH
        elif final_priority >= 0.4:
            return RequestPriority.NORMAL
        else:
            return RequestPriority.LOW
    
    async def _process_queue(self):
        """Process queued requests."""
        self.is_processing = True
        
        try:
            while self._has_pending_requests():
                # Get next request based on strategy
                next_request = self._get_next_request()
                
                if not next_request:
                    await asyncio.sleep(0.1)  # Brief pause if no requests
                    continue
                
                # Check if request has expired
                if next_request.is_expired(time.time()):
                    logger.warning(f"Request {next_request.request_id} expired")
                    self._handle_expired_request(next_request)
                    continue
                
                # Acquire semaphore for concurrent request limit
                await self.processing_semaphore.acquire()
                
                # Process request asynchronously
                asyncio.create_task(self._process_request(next_request))
                
        except Exception as e:
            logger.error(f"Error in queue processing for {self.exchange_type.value}: {e}")
        finally:
            self.is_processing = False
    
    def _get_next_request(self) -> Optional[QueuedRequest]:
        """Get next request based on queuing strategy."""
        if self.strategy == QueueStrategy.FIFO:
            return self.fifo_queue.popleft() if self.fifo_queue else None
        
        elif self.strategy == QueueStrategy.PRIORITY or self.strategy == QueueStrategy.ADAPTIVE:
            return heapq.heappop(self.priority_queue) if self.priority_queue else None
        
        elif self.strategy == QueueStrategy.WEIGHTED_FAIR:
            # Round-robin through request types with weights
            for request_type in RequestType:
                queue = self.weighted_queues[request_type]
                if queue:
                    weight = self.adaptive_priorities.get(request_type, 1.0)
                    # Simple weighted selection (could be more sophisticated)
                    if len(queue) * weight >= 1.0:
                        return queue.popleft()
            return None
        
        return None
    
    async def _process_request(self, request: QueuedRequest):
        """Process individual request."""
        start_time = time.time()
        
        try:
            # Add to active requests
            self.active_requests[request.request_id] = request
            
            # Calculate wait time
            wait_time = start_time - request.queued_at
            
            # Simulate request processing (in real implementation, this would call the actual API)
            processing_start = time.time()
            
            # Here you would integrate with the actual exchange connector
            # For now, we'll simulate processing
            await asyncio.sleep(request.estimated_duration)
            
            processing_time = time.time() - processing_start
            
            # Update performance metrics
            self._update_performance_metrics(request.endpoint, processing_time, True)
            
            # Complete the request
            if request.future and not request.future.done():
                request.future.set_result({
                    "success": True,
                    "request_id": request.request_id,
                    "processing_time": processing_time,
                    "wait_time": wait_time
                })
            
            # Update metrics
            self.metrics.update_completion(wait_time, processing_time)
            
            logger.debug(f"Completed request {request.request_id} in {processing_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            
            # Update performance metrics
            self._update_performance_metrics(request.endpoint, 0, False)
            
            # Handle retry or failure
            if request.should_retry():
                request.retry_count += 1
                logger.info(f"Retrying request {request.request_id} (attempt {request.retry_count})")
                
                # Re-queue with exponential backoff
                await asyncio.sleep(min(2 ** request.retry_count, 30))
                self._add_to_queue(request)
            else:
                # Fail the request
                if request.future and not request.future.done():
                    request.future.set_exception(e)
                
                self.metrics.update_failure()
        
        finally:
            # Remove from active requests
            self.active_requests.pop(request.request_id, None)
            
            # Release semaphore
            self.processing_semaphore.release()
    
    def _handle_expired_request(self, request: QueuedRequest):
        """Handle expired request."""
        if request.future and not request.future.done():
            request.future.set_exception(asyncio.TimeoutError("Request expired in queue"))
        
        self.metrics.update_expiration()
        logger.warning(f"Request {request.request_id} expired after {time.time() - request.queued_at:.2f}s")
    
    def _update_performance_metrics(self, endpoint: str, processing_time: float, success: bool):
        """Update performance metrics for endpoint."""
        # Update processing time history
        if endpoint not in self.performance_history:
            self.performance_history[endpoint] = []
        
        self.performance_history[endpoint].append(processing_time)
        
        # Keep only recent history
        if len(self.performance_history[endpoint]) > 100:
            self.performance_history[endpoint] = self.performance_history[endpoint][-100:]
        
        # Update success rate
        if endpoint not in self.endpoint_success_rates:
            self.endpoint_success_rates[endpoint] = 1.0 if success else 0.0
        else:
            # Exponential moving average
            alpha = 0.1
            current_rate = self.endpoint_success_rates[endpoint]
            self.endpoint_success_rates[endpoint] = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_rate
    
    def _estimate_request_duration(self, endpoint: str, request_type: RequestType) -> float:
        """Estimate request duration based on history."""
        if endpoint in self.performance_history and self.performance_history[endpoint]:
            return statistics.mean(self.performance_history[endpoint][-10:])  # Last 10 requests
        
        # Default estimates by request type
        defaults = {
            RequestType.MARKET_DATA: 0.1,
            RequestType.ACCOUNT_INFO: 0.2,
            RequestType.ORDER_MANAGEMENT: 0.3,
            RequestType.HISTORICAL_DATA: 0.5,
            RequestType.SYSTEM_INFO: 0.1
        }
        
        return defaults.get(request_type, 0.2)
    
    def _get_total_queue_size(self) -> int:
        """Get total number of queued requests."""
        total = len(self.fifo_queue) + len(self.priority_queue)
        total += sum(len(queue) for queue in self.weighted_queues.values())
        return total
    
    def _has_pending_requests(self) -> bool:
        """Check if there are pending requests."""
        return self._get_total_queue_size() > 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        current_time = time.time()
        
        return {
            "exchange": self.exchange_type.value,
            "strategy": self.strategy.value,
            "queue_sizes": {
                "total": self._get_total_queue_size(),
                "fifo": len(self.fifo_queue),
                "priority": len(self.priority_queue),
                "weighted": {rt.value: len(q) for rt, q in self.weighted_queues.items()}
            },
            "active_requests": len(self.active_requests),
            "max_concurrent": self.max_concurrent_requests,
            "is_processing": self.is_processing,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "completed_requests": self.metrics.completed_requests,
                "failed_requests": self.metrics.failed_requests,
                "expired_requests": self.metrics.expired_requests,
                "average_wait_time": self.metrics.average_wait_time,
                "average_processing_time": self.metrics.average_processing_time,
                "success_rate": (self.metrics.completed_requests / max(1, self.metrics.total_requests)) * 100,
                "throughput_per_second": self.metrics.calculate_throughput()
            },
            "performance": {
                "endpoint_success_rates": dict(self.endpoint_success_rates),
                "adaptive_priorities": {rt.value: p for rt, p in self.adaptive_priorities.items()}
            }
        }
    
    async def shutdown(self):
        """Shutdown the queue gracefully."""
        logger.info(f"Shutting down request queue for {self.exchange_type.value}")
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Fail all pending requests
        all_requests = []
        all_requests.extend(self.fifo_queue)
        all_requests.extend(self.priority_queue)
        for queue in self.weighted_queues.values():
            all_requests.extend(queue)
        all_requests.extend(self.active_requests.values())
        
        for request in all_requests:
            if request.future and not request.future.done():
                request.future.set_exception(Exception("Queue shutdown"))
        
        # Clear all queues
        self.fifo_queue.clear()
        self.priority_queue.clear()
        self.weighted_queues.clear()
        self.active_requests.clear()
        
        logger.info(f"Request queue for {self.exchange_type.value} shutdown complete")


class RequestQueueManager:
    """
    Global manager for all exchange request queues.
    
    Coordinates queuing across multiple exchanges and provides
    load balancing and monitoring capabilities.
    """
    
    def __init__(self):
        """Initialize request queue manager."""
        self.queues: Dict[ExchangeType, IntelligentRequestQueue] = {}
        self.global_metrics = {
            "total_requests": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_throughput": 0.0
        }
        
        logger.info("Initialized request queue manager")
    
    def add_exchange_queue(
        self,
        exchange_type: ExchangeType,
        strategy: QueueStrategy = QueueStrategy.PRIORITY,
        max_queue_size: int = 1000,
        max_concurrent_requests: int = 10
    ):
        """Add request queue for exchange."""
        if exchange_type in self.queues:
            logger.warning(f"Queue for {exchange_type.value} already exists, replacing")
        
        self.queues[exchange_type] = IntelligentRequestQueue(
            exchange_type, strategy, max_queue_size, max_concurrent_requests
        )
        
        logger.info(f"Added request queue for {exchange_type.value}")
    
    async def enqueue_request(
        self,
        exchange_type: ExchangeType,
        request_type: RequestType,
        endpoint: str,
        **kwargs
    ) -> asyncio.Future:
        """Enqueue request for specific exchange."""
        queue = self.queues.get(exchange_type)
        if not queue:
            raise ValueError(f"No queue found for {exchange_type.value}")
        
        self.global_metrics["total_requests"] += 1
        return await queue.enqueue_request(request_type, endpoint, **kwargs)
    
    def get_queue_status(self, exchange_type: ExchangeType) -> Optional[Dict[str, Any]]:
        """Get status for specific exchange queue."""
        queue = self.queues.get(exchange_type)
        return queue.get_status() if queue else None
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status for all queues."""
        exchange_status = {}
        total_throughput = 0.0
        
        for exchange_type, queue in self.queues.items():
            status = queue.get_status()
            exchange_status[exchange_type.value] = status
            total_throughput += status["metrics"]["throughput_per_second"]
        
        self.global_metrics["average_throughput"] = total_throughput / len(self.queues) if self.queues else 0
        
        return {
            "global_metrics": self.global_metrics.copy(),
            "exchanges": exchange_status
        }
    
    async def shutdown_all(self):
        """Shutdown all queues."""
        logger.info("Shutting down all request queues")
        
        shutdown_tasks = []
        for queue in self.queues.values():
            shutdown_tasks.append(queue.shutdown())
        
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        self.queues.clear()
        
        logger.info("All request queues shutdown complete")


# Global request queue manager
request_queue_manager = RequestQueueManager()


# Convenience functions
def initialize_request_queues(exchange_configs: Dict[ExchangeType, Dict[str, Any]]):
    """Initialize request queues for all exchanges."""
    for exchange_type, config in exchange_configs.items():
        strategy = QueueStrategy(config.get("strategy", "priority"))
        max_queue_size = config.get("max_queue_size", 1000)
        max_concurrent = config.get("max_concurrent_requests", 10)
        
        request_queue_manager.add_exchange_queue(
            exchange_type, strategy, max_queue_size, max_concurrent
        )
    
    logger.info(f"Initialized request queues for {len(exchange_configs)} exchanges")


async def enqueue_exchange_request(
    exchange_type: ExchangeType,
    request_type: RequestType,
    endpoint: str,
    **kwargs
) -> Any:
    """Enqueue and wait for exchange request."""
    future = await request_queue_manager.enqueue_request(
        exchange_type, request_type, endpoint, **kwargs
    )
    return await future