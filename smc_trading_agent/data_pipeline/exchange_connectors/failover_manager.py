"""
Exchange Failover Manager

Implements automatic failover logic between exchanges with health monitoring,
priority-based routing, and comprehensive testing capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import statistics

from .production_config import ExchangeType, Environment
from .error_handling import ErrorSeverity, ErrorCategory, ExchangeError
from .recovery_strategies import RecoveryState, global_recovery_manager

logger = logging.getLogger(__name__)


class FailoverTrigger(Enum):
    """Triggers that can cause failover."""
    CONNECTION_FAILURE = "connection_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    API_ERROR = "api_error"
    HIGH_LATENCY = "high_latency"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    MANUAL_TRIGGER = "manual_trigger"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class FailoverState(Enum):
    """Current failover state."""
    NORMAL = "normal"
    FAILING_OVER = "failing_over"
    FAILED_OVER = "failed_over"
    RECOVERING = "recovering"
    TESTING = "testing"


@dataclass
class ExchangeHealthMetrics:
    """Health metrics for an exchange."""
    exchange_type: ExchangeType
    is_connected: bool = False
    last_successful_request: float = 0.0
    last_failed_request: float = 0.0
    consecutive_failures: int = 0
    success_rate_1min: float = 100.0
    success_rate_5min: float = 100.0
    average_latency_ms: float = 0.0
    rate_limit_violations: int = 0
    data_quality_score: float = 100.0
    uptime_percentage: float = 100.0
    last_health_check: float = 0.0
    
    # Request tracking
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Latency tracking
    latency_samples: List[float] = field(default_factory=list)
    
    def update_request_result(self, success: bool, latency_ms: float = 0.0):
        """Update metrics with request result."""
        current_time = time.time()
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.last_successful_request = current_time
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.last_failed_request = current_time
            self.consecutive_failures += 1
        
        # Update latency
        if latency_ms > 0:
            self.latency_samples.append(latency_ms)
            # Keep only last 100 samples
            if len(self.latency_samples) > 100:
                self.latency_samples = self.latency_samples[-100:]
            
            self.average_latency_ms = statistics.mean(self.latency_samples)
        
        # Update success rates
        self._calculate_success_rates()
    
    def _calculate_success_rates(self):
        """Calculate success rates for different time windows."""
        if self.total_requests == 0:
            return
        
        # Overall success rate
        overall_rate = (self.successful_requests / self.total_requests) * 100
        
        # For simplicity, use overall rate for time-based rates
        # In production, this would track time-windowed metrics
        self.success_rate_1min = overall_rate
        self.success_rate_5min = overall_rate
    
    def get_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        scores = []
        
        # Connection score
        scores.append(100.0 if self.is_connected else 0.0)
        
        # Success rate score
        scores.append(self.success_rate_5min)
        
        # Latency score (lower is better)
        if self.average_latency_ms > 0:
            latency_score = max(0, 100 - (self.average_latency_ms / 10))  # 1000ms = 0 score
            scores.append(latency_score)
        else:
            scores.append(100.0)
        
        # Data quality score
        scores.append(self.data_quality_score)
        
        # Consecutive failures penalty
        failure_penalty = min(50, self.consecutive_failures * 10)
        scores.append(max(0, 100 - failure_penalty))
        
        return statistics.mean(scores) if scores else 0.0


@dataclass
class FailoverRule:
    """Rule for triggering failover."""
    trigger: FailoverTrigger
    threshold: float
    duration_seconds: float = 0.0
    priority: int = 1  # Lower number = higher priority
    enabled: bool = True
    
    def should_trigger(self, metrics: ExchangeHealthMetrics) -> bool:
        """Check if this rule should trigger failover."""
        if not self.enabled:
            return False
        
        current_time = time.time()
        
        if self.trigger == FailoverTrigger.CONNECTION_FAILURE:
            return not metrics.is_connected
        
        elif self.trigger == FailoverTrigger.RATE_LIMIT_EXCEEDED:
            return metrics.rate_limit_violations >= self.threshold
        
        elif self.trigger == FailoverTrigger.HIGH_LATENCY:
            return metrics.average_latency_ms >= self.threshold
        
        elif self.trigger == FailoverTrigger.HEALTH_CHECK_FAILURE:
            time_since_check = current_time - metrics.last_health_check
            return time_since_check >= self.threshold
        
        elif self.trigger == FailoverTrigger.API_ERROR:
            return metrics.consecutive_failures >= self.threshold
        
        elif self.trigger == FailoverTrigger.DATA_QUALITY_ISSUE:
            return metrics.data_quality_score <= self.threshold
        
        return False


@dataclass
class FailoverEvent:
    """Record of a failover event."""
    timestamp: float
    from_exchange: ExchangeType
    to_exchange: ExchangeType
    trigger: FailoverTrigger
    trigger_value: float
    duration_ms: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp,
            "from_exchange": self.from_exchange.value,
            "to_exchange": self.to_exchange.value,
            "trigger": self.trigger.value,
            "trigger_value": self.trigger_value,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message
        }


class ExchangeFailoverManager:
    """
    Manages failover between exchanges based on health monitoring and rules.
    
    Provides automatic failover, manual failover, and recovery capabilities.
    """
    
    def __init__(self, environment: Environment = Environment.PRODUCTION):
        """
        Initialize failover manager.
        
        Args:
            environment: Target environment
        """
        self.environment = environment
        
        # Exchange management
        self.exchanges: Dict[ExchangeType, Any] = {}  # Exchange connectors
        self.health_metrics: Dict[ExchangeType, ExchangeHealthMetrics] = {}
        self.exchange_priorities: Dict[ExchangeType, int] = {}
        
        # Failover state
        self.current_state = FailoverState.NORMAL
        self.primary_exchange: Optional[ExchangeType] = None
        self.active_exchange: Optional[ExchangeType] = None
        self.failed_exchanges: Set[ExchangeType] = set()
        
        # Rules and configuration
        self.failover_rules: List[FailoverRule] = []
        self.health_check_interval = 30.0  # seconds
        self.recovery_check_interval = 60.0  # seconds
        self.failover_timeout = 10.0  # seconds
        
        # Event tracking
        self.failover_events: List[FailoverEvent] = []
        self.max_event_history = 1000
        
        # Callbacks
        self.failover_callbacks: List[Callable] = []
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._recovery_check_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Initialize default rules
        self._initialize_default_rules()
        
        logger.info(f"Initialized failover manager for {environment.value}")
    
    def _initialize_default_rules(self):
        """Initialize default failover rules."""
        self.failover_rules = [
            # High priority rules
            FailoverRule(
                trigger=FailoverTrigger.CONNECTION_FAILURE,
                threshold=1,
                priority=1,
                duration_seconds=0.0
            ),
            FailoverRule(
                trigger=FailoverTrigger.CIRCUIT_BREAKER_OPEN,
                threshold=1,
                priority=1,
                duration_seconds=0.0
            ),
            
            # Medium priority rules
            FailoverRule(
                trigger=FailoverTrigger.API_ERROR,
                threshold=5,  # 5 consecutive failures
                priority=2,
                duration_seconds=30.0
            ),
            FailoverRule(
                trigger=FailoverTrigger.HIGH_LATENCY,
                threshold=1000.0,  # 1000ms
                priority=2,
                duration_seconds=60.0
            ),
            
            # Lower priority rules
            FailoverRule(
                trigger=FailoverTrigger.RATE_LIMIT_EXCEEDED,
                threshold=3,  # 3 violations
                priority=3,
                duration_seconds=120.0
            ),
            FailoverRule(
                trigger=FailoverTrigger.DATA_QUALITY_ISSUE,
                threshold=70.0,  # Below 70% quality
                priority=3,
                duration_seconds=300.0
            )
        ]
    
    def add_exchange(
        self,
        exchange_type: ExchangeType,
        connector: Any,
        priority: int = 10
    ):
        """
        Add exchange to failover management.
        
        Args:
            exchange_type: Type of exchange
            connector: Exchange connector instance
            priority: Priority (lower number = higher priority)
        """
        self.exchanges[exchange_type] = connector
        self.exchange_priorities[exchange_type] = priority
        self.health_metrics[exchange_type] = ExchangeHealthMetrics(exchange_type)
        
        # Set primary exchange if not set (highest priority)
        if self.primary_exchange is None or priority < self.exchange_priorities.get(self.primary_exchange, 999):
            self.primary_exchange = exchange_type
            self.active_exchange = exchange_type
        
        logger.info(f"Added {exchange_type.value} to failover management (priority: {priority})")
    
    def remove_exchange(self, exchange_type: ExchangeType):
        """Remove exchange from failover management."""
        if exchange_type in self.exchanges:
            del self.exchanges[exchange_type]
            del self.health_metrics[exchange_type]
            del self.exchange_priorities[exchange_type]
            
            # Update primary if needed
            if self.primary_exchange == exchange_type:
                self._select_new_primary()
            
            # Update active if needed
            if self.active_exchange == exchange_type:
                self._select_best_exchange()
            
            logger.info(f"Removed {exchange_type.value} from failover management")
    
    def set_exchange_priority(self, exchange_type: ExchangeType, priority: int):
        """Update exchange priority."""
        if exchange_type in self.exchange_priorities:
            old_priority = self.exchange_priorities[exchange_type]
            self.exchange_priorities[exchange_type] = priority
            
            logger.info(f"Updated {exchange_type.value} priority: {old_priority} -> {priority}")
            
            # Recalculate primary if needed
            if priority < self.exchange_priorities.get(self.primary_exchange, 999):
                self.primary_exchange = exchange_type
    
    def add_failover_rule(self, rule: FailoverRule):
        """Add custom failover rule."""
        self.failover_rules.append(rule)
        # Sort by priority
        self.failover_rules.sort(key=lambda r: r.priority)
        
        logger.info(f"Added failover rule: {rule.trigger.value} (threshold: {rule.threshold})")
    
    def add_failover_callback(self, callback: Callable[[FailoverEvent], None]):
        """Add callback for failover events."""
        self.failover_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start background health monitoring and recovery tasks."""
        if self._running:
            logger.warning("Failover monitoring already running")
            return
        
        self._running = True
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start recovery check task
        self._recovery_check_task = asyncio.create_task(self._recovery_check_loop())
        
        logger.info("Started failover monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._recovery_check_task:
            self._recovery_check_task.cancel()
            try:
                await self._recovery_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped failover monitoring")
    
    async def _health_check_loop(self):
        """Background task for health checking."""
        while self._running:
            try:
                await self._perform_health_checks()
                await self._evaluate_failover_rules()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5.0)  # Short delay on error
    
    async def _recovery_check_loop(self):
        """Background task for checking recovery of failed exchanges."""
        while self._running:
            try:
                await self._check_failed_exchange_recovery()
                await asyncio.sleep(self.recovery_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery check loop error: {e}")
                await asyncio.sleep(10.0)  # Short delay on error
    
    async def _perform_health_checks(self):
        """Perform health checks on all exchanges."""
        for exchange_type, connector in self.exchanges.items():
            try:
                # Get health status from connector
                health_status = await connector.get_health_status()
                metrics = self.health_metrics[exchange_type]
                
                # Update basic connectivity
                metrics.is_connected = health_status.get("connected", False)
                metrics.last_health_check = time.time()
                
                # Update from production metrics if available
                if "production_metrics" in health_status:
                    prod_metrics = health_status["production_metrics"]
                    metrics.total_requests = prod_metrics.get("messages_processed", 0)
                    metrics.consecutive_failures = prod_metrics.get("error_count", 0)
                
                # Test latency with a simple ping
                start_time = time.time()
                try:
                    # This would be a lightweight test request
                    await connector.get_health_status()
                    latency_ms = (time.time() - start_time) * 1000
                    metrics.update_request_result(True, latency_ms)
                except Exception:
                    metrics.update_request_result(False)
                
                logger.debug(f"Health check for {exchange_type.value}: score={metrics.get_health_score():.1f}")
                
            except Exception as e:
                logger.error(f"Health check failed for {exchange_type.value}: {e}")
                metrics = self.health_metrics[exchange_type]
                metrics.is_connected = False
                metrics.update_request_result(False)
    
    async def _evaluate_failover_rules(self):
        """Evaluate failover rules and trigger if needed."""
        if self.current_state == FailoverState.FAILING_OVER:
            return  # Already in progress
        
        active_metrics = self.health_metrics.get(self.active_exchange)
        if not active_metrics:
            return
        
        # Check rules in priority order
        for rule in self.failover_rules:
            if rule.should_trigger(active_metrics):
                logger.warning(f"Failover rule triggered: {rule.trigger.value} (threshold: {rule.threshold})")
                
                # Find best alternative exchange
                target_exchange = self._select_best_exchange(exclude={self.active_exchange})
                
                if target_exchange and target_exchange != self.active_exchange:
                    await self._trigger_failover(
                        target_exchange,
                        rule.trigger,
                        rule.threshold
                    )
                    break  # Only trigger one failover at a time
                else:
                    logger.error(f"No suitable exchange for failover from {self.active_exchange.value}")
    
    async def _trigger_failover(
        self,
        target_exchange: ExchangeType,
        trigger: FailoverTrigger,
        trigger_value: float
    ) -> bool:
        """
        Trigger failover to target exchange.
        
        Args:
            target_exchange: Exchange to fail over to
            trigger: What triggered the failover
            trigger_value: Value that triggered the failover
            
        Returns:
            bool: True if failover successful
        """
        if self.current_state == FailoverState.FAILING_OVER:
            logger.warning("Failover already in progress")
            return False
        
        start_time = time.time()
        from_exchange = self.active_exchange
        
        # Create failover event
        event = FailoverEvent(
            timestamp=start_time,
            from_exchange=from_exchange,
            to_exchange=target_exchange,
            trigger=trigger,
            trigger_value=trigger_value
        )
        
        try:
            logger.info(f"Starting failover: {from_exchange.value} -> {target_exchange.value}")
            self.current_state = FailoverState.FAILING_OVER
            
            # Get connectors
            from_connector = self.exchanges.get(from_exchange)
            to_connector = self.exchanges.get(target_exchange)
            
            if not to_connector:
                raise Exception(f"Target exchange {target_exchange.value} not available")
            
            # Test target exchange health
            target_health = await to_connector.get_health_status()
            if not target_health.get("connected", False):
                # Try to connect
                logger.info(f"Attempting to connect to {target_exchange.value}")
                if not await to_connector.connect_websocket():
                    raise Exception(f"Failed to connect to {target_exchange.value}")
            
            # Perform failover
            success = await self._execute_failover(from_connector, to_connector)
            
            if success:
                # Update state
                self.active_exchange = target_exchange
                self.failed_exchanges.add(from_exchange)
                self.current_state = FailoverState.FAILED_OVER
                
                event.success = True
                event.duration_ms = (time.time() - start_time) * 1000
                
                logger.info(f"Failover completed successfully in {event.duration_ms:.1f}ms")
            else:
                raise Exception("Failover execution failed")
        
        except Exception as e:
            error_msg = str(e)
            event.error_message = error_msg
            event.success = False
            event.duration_ms = (time.time() - start_time) * 1000
            
            logger.error(f"Failover failed: {error_msg}")
            self.current_state = FailoverState.NORMAL  # Reset state
        
        # Record event
        self._record_failover_event(event)
        
        # Notify callbacks
        await self._notify_failover_callbacks(event)
        
        return event.success
    
    async def _execute_failover(self, from_connector: Any, to_connector: Any) -> bool:
        """
        Execute the actual failover between connectors.
        
        Args:
            from_connector: Source connector
            to_connector: Target connector
            
        Returns:
            bool: True if successful
        """
        try:
            # This is where the actual failover logic would be implemented
            # For now, we'll simulate the process
            
            # 1. Ensure target is connected and healthy
            if not await to_connector.get_health_status().get("connected", False):
                if not await to_connector.start():
                    return False
            
            # 2. Transfer any necessary state (subscriptions, etc.)
            # This would be implemented based on specific requirements
            
            # 3. Gracefully disconnect from source if possible
            if from_connector:
                try:
                    await from_connector.stop()
                except Exception as e:
                    logger.warning(f"Error stopping source connector: {e}")
            
            # 4. Verify target is working
            target_health = await to_connector.get_health_status()
            if not target_health.get("connected", False):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failover execution error: {e}")
            return False
    
    async def _check_failed_exchange_recovery(self):
        """Check if failed exchanges have recovered."""
        if not self.failed_exchanges:
            return
        
        recovered_exchanges = set()
        
        for exchange_type in self.failed_exchanges:
            try:
                connector = self.exchanges.get(exchange_type)
                if not connector:
                    continue
                
                # Test if exchange has recovered
                health_status = await connector.get_health_status()
                metrics = self.health_metrics[exchange_type]
                
                # Update metrics
                metrics.is_connected = health_status.get("connected", False)
                
                # Check if exchange is healthy enough to be considered recovered
                health_score = metrics.get_health_score()
                
                if health_score >= 80.0:  # 80% health threshold
                    logger.info(f"Exchange {exchange_type.value} has recovered (health: {health_score:.1f}%)")
                    recovered_exchanges.add(exchange_type)
                    
                    # If this was the primary exchange, consider failing back
                    if exchange_type == self.primary_exchange and self.active_exchange != exchange_type:
                        await self._consider_failback(exchange_type)
                
            except Exception as e:
                logger.error(f"Recovery check failed for {exchange_type.value}: {e}")
        
        # Remove recovered exchanges from failed set
        self.failed_exchanges -= recovered_exchanges
    
    async def _consider_failback(self, recovered_exchange: ExchangeType):
        """Consider failing back to recovered primary exchange."""
        if self.current_state != FailoverState.FAILED_OVER:
            return
        
        # Only failback to primary exchange
        if recovered_exchange != self.primary_exchange:
            return
        
        # Check if current active exchange is having issues
        active_metrics = self.health_metrics.get(self.active_exchange)
        recovered_metrics = self.health_metrics.get(recovered_exchange)
        
        if not active_metrics or not recovered_metrics:
            return
        
        active_health = active_metrics.get_health_score()
        recovered_health = recovered_metrics.get_health_score()
        
        # Failback if recovered exchange is significantly healthier
        if recovered_health > active_health + 20.0:  # 20% better
            logger.info(f"Initiating failback to {recovered_exchange.value}")
            await self._trigger_failover(
                recovered_exchange,
                FailoverTrigger.MANUAL_TRIGGER,
                recovered_health
            )
    
    def _select_best_exchange(self, exclude: Optional[Set[ExchangeType]] = None) -> Optional[ExchangeType]:
        """
        Select the best available exchange based on health and priority.
        
        Args:
            exclude: Set of exchanges to exclude from selection
            
        Returns:
            Optional[ExchangeType]: Best exchange or None if none available
        """
        exclude = exclude or set()
        candidates = []
        
        for exchange_type, connector in self.exchanges.items():
            if exchange_type in exclude:
                continue
            
            metrics = self.health_metrics.get(exchange_type)
            if not metrics:
                continue
            
            # Only consider connected exchanges
            if not metrics.is_connected:
                continue
            
            priority = self.exchange_priorities.get(exchange_type, 999)
            health_score = metrics.get_health_score()
            
            # Combined score: lower priority number is better, higher health is better
            # Normalize priority (invert so higher is better) and combine with health
            priority_score = 100 - min(priority, 100)  # Cap at 100
            combined_score = (priority_score * 0.3) + (health_score * 0.7)
            
            candidates.append((exchange_type, combined_score))
        
        if not candidates:
            return None
        
        # Sort by combined score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        best_exchange = candidates[0][0]
        logger.debug(f"Selected best exchange: {best_exchange.value} (score: {candidates[0][1]:.1f})")
        
        return best_exchange
    
    def _select_new_primary(self):
        """Select new primary exchange based on priorities."""
        if not self.exchange_priorities:
            self.primary_exchange = None
            return
        
        # Find exchange with lowest priority number (highest priority)
        primary = min(self.exchange_priorities.items(), key=lambda x: x[1])
        self.primary_exchange = primary[0]
        
        logger.info(f"New primary exchange: {self.primary_exchange.value}")
    
    def _record_failover_event(self, event: FailoverEvent):
        """Record failover event in history."""
        self.failover_events.append(event)
        
        # Maintain history size limit
        if len(self.failover_events) > self.max_event_history:
            self.failover_events = self.failover_events[-self.max_event_history:]
    
    async def _notify_failover_callbacks(self, event: FailoverEvent):
        """Notify failover callbacks."""
        for callback in self.failover_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Failover callback failed: {e}")
    
    async def manual_failover(self, target_exchange: ExchangeType) -> bool:
        """
        Manually trigger failover to specific exchange.
        
        Args:
            target_exchange: Exchange to fail over to
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Manual failover requested to {target_exchange.value}")
        
        return await self._trigger_failover(
            target_exchange,
            FailoverTrigger.MANUAL_TRIGGER,
            0.0
        )
    
    async def test_failover_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Test failover scenario in controlled environment.
        
        Args:
            scenario: Scenario name to test
            
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Testing failover scenario: {scenario}")
        
        original_state = self.current_state
        original_active = self.active_exchange
        test_start = time.time()
        
        try:
            self.current_state = FailoverState.TESTING
            
            if scenario == "connection_failure":
                # Simulate connection failure
                if self.active_exchange:
                    metrics = self.health_metrics[self.active_exchange]
                    metrics.is_connected = False
                    metrics.consecutive_failures = 10
                
                # Trigger evaluation
                await self._evaluate_failover_rules()
            
            elif scenario == "high_latency":
                # Simulate high latency
                if self.active_exchange:
                    metrics = self.health_metrics[self.active_exchange]
                    metrics.average_latency_ms = 2000.0  # 2 seconds
                
                await self._evaluate_failover_rules()
            
            elif scenario == "manual_failover":
                # Test manual failover to next best exchange
                target = self._select_best_exchange(exclude={self.active_exchange})
                if target:
                    await self.manual_failover(target)
            
            else:
                return {"success": False, "error": f"Unknown scenario: {scenario}"}
            
            test_duration = time.time() - test_start
            
            return {
                "success": True,
                "scenario": scenario,
                "duration_ms": test_duration * 1000,
                "original_active": original_active.value if original_active else None,
                "new_active": self.active_exchange.value if self.active_exchange else None,
                "failover_occurred": self.active_exchange != original_active
            }
        
        except Exception as e:
            return {
                "success": False,
                "scenario": scenario,
                "error": str(e),
                "duration_ms": (time.time() - test_start) * 1000
            }
        
        finally:
            # Restore original state if this was just a test
            if original_state != FailoverState.TESTING:
                self.current_state = original_state
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive failover status."""
        return {
            "environment": self.environment.value,
            "current_state": self.current_state.value,
            "primary_exchange": self.primary_exchange.value if self.primary_exchange else None,
            "active_exchange": self.active_exchange.value if self.active_exchange else None,
            "failed_exchanges": [ex.value for ex in self.failed_exchanges],
            "exchange_health": {
                ex.value: {
                    "health_score": metrics.get_health_score(),
                    "is_connected": metrics.is_connected,
                    "consecutive_failures": metrics.consecutive_failures,
                    "average_latency_ms": metrics.average_latency_ms,
                    "success_rate_5min": metrics.success_rate_5min,
                    "priority": self.exchange_priorities.get(ex, 999)
                }
                for ex, metrics in self.health_metrics.items()
            },
            "failover_rules": [
                {
                    "trigger": rule.trigger.value,
                    "threshold": rule.threshold,
                    "priority": rule.priority,
                    "enabled": rule.enabled
                }
                for rule in self.failover_rules
            ],
            "recent_events": [
                event.to_dict() for event in self.failover_events[-10:]
            ],
            "statistics": {
                "total_failovers": len(self.failover_events),
                "successful_failovers": sum(1 for e in self.failover_events if e.success),
                "average_failover_time_ms": statistics.mean([
                    e.duration_ms for e in self.failover_events if e.duration_ms > 0
                ]) if self.failover_events else 0.0
            }
        }
    
    def export_failover_report(self, file_path: str):
        """Export comprehensive failover report."""
        try:
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "environment": self.environment.value,
                "status": self.get_status(),
                "detailed_events": [event.to_dict() for event in self.failover_events]
            }
            
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Failover report exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export failover report: {e}")


# Global failover manager instance
global_failover_manager: Optional[ExchangeFailoverManager] = None


def initialize_failover_manager(environment: Environment = Environment.PRODUCTION) -> ExchangeFailoverManager:
    """Initialize global failover manager."""
    global global_failover_manager
    global_failover_manager = ExchangeFailoverManager(environment)
    return global_failover_manager


def get_failover_manager() -> Optional[ExchangeFailoverManager]:
    """Get global failover manager instance."""
    return global_failover_manager


async def test_all_failover_scenarios() -> Dict[str, Any]:
    """Test all failover scenarios."""
    if not global_failover_manager:
        return {"error": "Failover manager not initialized"}
    
    scenarios = [
        "connection_failure",
        "high_latency", 
        "manual_failover"
    ]
    
    results = {}
    
    for scenario in scenarios:
        try:
            result = await global_failover_manager.test_failover_scenario(scenario)
            results[scenario] = result
        except Exception as e:
            results[scenario] = {"success": False, "error": str(e)}
    
    return {
        "test_timestamp": datetime.utcnow().isoformat(),
        "scenarios_tested": len(scenarios),
        "results": results
    }