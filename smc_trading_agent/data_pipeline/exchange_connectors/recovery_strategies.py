"""
Rate Limit Recovery Strategies

Implements intelligent recovery strategies for rate limit violations,
including adaptive backoff, circuit breakers, and failover mechanisms.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import statistics

from .production_config import ExchangeType
from .error_handling import ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    ADAPTIVE_BACKOFF = "adaptive_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    JITTERED_BACKOFF = "jittered_backoff"
    GRADUAL_RECOVERY = "gradual_recovery"


class RecoveryState(Enum):
    """Recovery state for tracking."""
    NORMAL = "normal"
    BACKING_OFF = "backing_off"
    CIRCUIT_OPEN = "circuit_open"
    CIRCUIT_HALF_OPEN = "circuit_half_open"
    RECOVERING = "recovering"


@dataclass
class RecoveryMetrics:
    """Metrics for recovery strategy performance."""
    total_rate_limits: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    average_recovery_time: float = 0.0
    max_recovery_time: float = 0.0
    recovery_times: List[float] = field(default_factory=list)
    strategy_effectiveness: Dict[RecoveryStrategy, float] = field(default_factory=dict)
    
    def record_recovery(self, recovery_time: float, success: bool, strategy: RecoveryStrategy):
        """Record a recovery attempt."""
        self.recovery_times.append(recovery_time)
        
        if success:
            self.successful_recoveries += 1
        else:
            self.failed_recoveries += 1
        
        # Update averages
        if self.recovery_times:
            self.average_recovery_time = statistics.mean(self.recovery_times[-100:])  # Last 100
            self.max_recovery_time = max(self.recovery_times[-100:])
        
        # Update strategy effectiveness
        if strategy not in self.strategy_effectiveness:
            self.strategy_effectiveness[strategy] = 1.0 if success else 0.0
        else:
            # Exponential moving average
            alpha = 0.1
            current_effectiveness = self.strategy_effectiveness[strategy]
            self.strategy_effectiveness[strategy] = (
                alpha * (1.0 if success else 0.0) + (1 - alpha) * current_effectiveness
            )


@dataclass
class BackoffConfig:
    """Configuration for backoff strategies."""
    initial_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes
    multiplier: float = 2.0
    jitter_factor: float = 0.1
    reset_threshold: float = 300.0  # Reset after 5 minutes of success


class RateLimitRecoveryManager:
    """
    Manages rate limit recovery for a specific exchange.
    
    Implements multiple recovery strategies and adapts based on effectiveness.
    """
    
    def __init__(
        self,
        exchange_type: ExchangeType,
        primary_strategy: RecoveryStrategy = RecoveryStrategy.ADAPTIVE_BACKOFF,
        config: Optional[BackoffConfig] = None
    ):
        """
        Initialize recovery manager.
        
        Args:
            exchange_type: Exchange type
            primary_strategy: Primary recovery strategy
            config: Backoff configuration
        """
        self.exchange_type = exchange_type
        self.primary_strategy = primary_strategy
        self.config = config or BackoffConfig()
        
        # State tracking
        self.current_state = RecoveryState.NORMAL
        self.current_delay = self.config.initial_delay
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.last_rate_limit_time = 0.0
        self.recovery_start_time = 0.0
        
        # Circuit breaker state
        self.circuit_failure_count = 0
        self.circuit_failure_threshold = 5
        self.circuit_timeout = 60.0  # 1 minute
        self.circuit_half_open_max_requests = 3
        self.circuit_half_open_requests = 0
        
        # Fibonacci sequence for fibonacci backoff
        self.fibonacci_sequence = [1, 1]
        self.fibonacci_index = 0
        
        # Metrics
        self.metrics = RecoveryMetrics()
        
        # Callbacks
        self.recovery_callbacks: List[Callable] = []
        
        logger.info(f"Initialized recovery manager for {exchange_type.value}")
    
    def add_recovery_callback(self, callback: Callable[[RecoveryState, float], None]):
        """Add callback for recovery state changes."""
        self.recovery_callbacks.append(callback)
    
    async def handle_rate_limit(
        self,
        retry_after: Optional[float] = None,
        error_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Handle rate limit violation and return recovery delay.
        
        Args:
            retry_after: Retry-after header from exchange (seconds)
            error_context: Additional error context
            
        Returns:
            float: Delay before next attempt (seconds)
        """
        current_time = time.time()
        self.last_rate_limit_time = current_time
        self.consecutive_failures += 1
        self.metrics.total_rate_limits += 1
        
        # Start recovery timing
        if self.recovery_start_time == 0:
            self.recovery_start_time = current_time
        
        logger.warning(f"Rate limit hit for {self.exchange_type.value} (consecutive: {self.consecutive_failures})")
        
        # Calculate recovery delay based on strategy
        if retry_after:
            # Use exchange-provided retry-after with some buffer
            delay = retry_after * 1.1  # 10% buffer
            logger.info(f"Using exchange retry-after: {delay:.2f}s")
        else:
            delay = await self._calculate_recovery_delay()
        
        # Update state
        self._update_recovery_state(delay)
        
        # Notify callbacks
        await self._notify_callbacks(self.current_state, delay)
        
        return delay
    
    async def _calculate_recovery_delay(self) -> float:
        """Calculate recovery delay based on current strategy."""
        if self.primary_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            return self._exponential_backoff()
        elif self.primary_strategy == RecoveryStrategy.LINEAR_BACKOFF:
            return self._linear_backoff()
        elif self.primary_strategy == RecoveryStrategy.FIBONACCI_BACKOFF:
            return self._fibonacci_backoff()
        elif self.primary_strategy == RecoveryStrategy.JITTERED_BACKOFF:
            return self._jittered_backoff()
        elif self.primary_strategy == RecoveryStrategy.ADAPTIVE_BACKOFF:
            return await self._adaptive_backoff()
        elif self.primary_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            return await self._circuit_breaker_delay()
        elif self.primary_strategy == RecoveryStrategy.GRADUAL_RECOVERY:
            return self._gradual_recovery()
        else:
            return self._exponential_backoff()  # Default fallback
    
    def _exponential_backoff(self) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.config.initial_delay * (self.config.multiplier ** (self.consecutive_failures - 1)),
            self.config.max_delay
        )
        self.current_delay = delay
        return delay
    
    def _linear_backoff(self) -> float:
        """Calculate linear backoff delay."""
        delay = min(
            self.config.initial_delay * self.consecutive_failures,
            self.config.max_delay
        )
        self.current_delay = delay
        return delay
    
    def _fibonacci_backoff(self) -> float:
        """Calculate Fibonacci backoff delay."""
        # Extend Fibonacci sequence if needed
        while len(self.fibonacci_sequence) <= self.consecutive_failures:
            next_fib = self.fibonacci_sequence[-1] + self.fibonacci_sequence[-2]
            self.fibonacci_sequence.append(next_fib)
        
        fib_value = self.fibonacci_sequence[min(self.consecutive_failures - 1, len(self.fibonacci_sequence) - 1)]
        delay = min(self.config.initial_delay * fib_value, self.config.max_delay)
        self.current_delay = delay
        return delay
    
    def _jittered_backoff(self) -> float:
        """Calculate jittered exponential backoff delay."""
        base_delay = self._exponential_backoff()
        jitter = base_delay * self.config.jitter_factor * (2 * random.random() - 1)  # ±jitter_factor
        delay = max(0.1, base_delay + jitter)  # Minimum 0.1 seconds
        self.current_delay = delay
        return delay
    
    async def _adaptive_backoff(self) -> float:
        """Calculate adaptive backoff based on historical performance."""
        # Start with exponential backoff as base
        base_delay = self._exponential_backoff()
        
        # Adjust based on recent success rate
        if self.metrics.recovery_times:
            recent_times = self.metrics.recovery_times[-10:]  # Last 10 recoveries
            if recent_times:
                avg_recovery_time = statistics.mean(recent_times)
                
                # If recent recoveries are taking longer, increase delay
                if avg_recovery_time > 30:  # 30 seconds threshold
                    base_delay *= 1.5
                elif avg_recovery_time < 10:  # 10 seconds threshold
                    base_delay *= 0.8
        
        # Adjust based on time since last success
        time_since_success = time.time() - self.last_success_time
        if time_since_success > 300:  # 5 minutes
            base_delay *= 1.2  # Increase delay if we haven't succeeded recently
        
        delay = min(base_delay, self.config.max_delay)
        self.current_delay = delay
        return delay
    
    async def _circuit_breaker_delay(self) -> float:
        """Calculate delay using circuit breaker pattern."""
        current_time = time.time()
        
        if self.current_state == RecoveryState.CIRCUIT_OPEN:
            # Check if circuit should move to half-open
            if current_time - self.last_rate_limit_time >= self.circuit_timeout:
                self.current_state = RecoveryState.CIRCUIT_HALF_OPEN
                self.circuit_half_open_requests = 0
                logger.info(f"Circuit breaker half-open for {self.exchange_type.value}")
                return 0.1  # Small delay for test request
            else:
                # Circuit still open
                remaining_time = self.circuit_timeout - (current_time - self.last_rate_limit_time)
                return remaining_time
        
        elif self.current_state == RecoveryState.CIRCUIT_HALF_OPEN:
            # Allow limited requests in half-open state
            if self.circuit_half_open_requests < self.circuit_half_open_max_requests:
                return 0.1  # Small delay between test requests
            else:
                # Too many requests in half-open, go back to open
                self.current_state = RecoveryState.CIRCUIT_OPEN
                self.last_rate_limit_time = current_time
                return self.circuit_timeout
        
        else:
            # Normal state, increment failure count
            self.circuit_failure_count += 1
            if self.circuit_failure_count >= self.circuit_failure_threshold:
                self.current_state = RecoveryState.CIRCUIT_OPEN
                logger.warning(f"Circuit breaker opened for {self.exchange_type.value}")
                return self.circuit_timeout
            else:
                return self._exponential_backoff()
    
    def _gradual_recovery(self) -> float:
        """Calculate delay for gradual recovery strategy."""
        # Start with longer delays and gradually reduce
        base_delay = self.config.max_delay / (2 ** max(0, 5 - self.consecutive_failures))
        delay = max(self.config.initial_delay, base_delay)
        self.current_delay = delay
        return delay
    
    def _update_recovery_state(self, delay: float):
        """Update recovery state based on delay."""
        if delay >= self.config.max_delay:
            self.current_state = RecoveryState.CIRCUIT_OPEN
        elif delay > self.config.initial_delay * 2:
            self.current_state = RecoveryState.BACKING_OFF
        else:
            self.current_state = RecoveryState.RECOVERING
    
    async def handle_successful_request(self):
        """Handle successful request after rate limit recovery."""
        current_time = time.time()
        
        # Calculate recovery time if we were recovering
        recovery_time = 0.0
        if self.recovery_start_time > 0:
            recovery_time = current_time - self.recovery_start_time
            self.recovery_start_time = 0.0
        
        # Update metrics
        if self.consecutive_failures > 0:  # We were in recovery
            self.metrics.record_recovery(recovery_time, True, self.primary_strategy)
            logger.info(f"Successful recovery for {self.exchange_type.value} in {recovery_time:.2f}s")
        
        # Reset state
        self.last_success_time = current_time
        self.consecutive_failures = 0
        self.current_delay = self.config.initial_delay
        self.current_state = RecoveryState.NORMAL
        
        # Reset circuit breaker
        self.circuit_failure_count = 0
        if self.current_state == RecoveryState.CIRCUIT_HALF_OPEN:
            logger.info(f"Circuit breaker closed for {self.exchange_type.value}")
        
        # Notify callbacks
        await self._notify_callbacks(RecoveryState.NORMAL, 0.0)
    
    async def handle_failed_recovery(self):
        """Handle failed recovery attempt."""
        current_time = time.time()
        
        # Calculate recovery time
        recovery_time = 0.0
        if self.recovery_start_time > 0:
            recovery_time = current_time - self.recovery_start_time
        
        # Update metrics
        self.metrics.record_recovery(recovery_time, False, self.primary_strategy)
        
        logger.warning(f"Failed recovery attempt for {self.exchange_type.value} after {recovery_time:.2f}s")
        
        # Update circuit breaker state
        if self.current_state == RecoveryState.CIRCUIT_HALF_OPEN:
            self.current_state = RecoveryState.CIRCUIT_OPEN
            self.last_rate_limit_time = current_time
            logger.warning(f"Circuit breaker re-opened for {self.exchange_type.value}")
    
    async def _notify_callbacks(self, state: RecoveryState, delay: float):
        """Notify recovery callbacks."""
        for callback in self.recovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(state, delay)
                else:
                    callback(state, delay)
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        if self.current_state == RecoveryState.CIRCUIT_OPEN:
            current_time = time.time()
            if current_time - self.last_rate_limit_time >= self.circuit_timeout:
                self.current_state = RecoveryState.CIRCUIT_HALF_OPEN
                self.circuit_half_open_requests = 0
                return True
            return False
        
        elif self.current_state == RecoveryState.CIRCUIT_HALF_OPEN:
            if self.circuit_half_open_requests < self.circuit_half_open_max_requests:
                self.circuit_half_open_requests += 1
                return True
            return False
        
        return True  # Allow requests in other states
    
    def get_status(self) -> Dict[str, Any]:
        """Get current recovery status."""
        current_time = time.time()
        
        return {
            "exchange": self.exchange_type.value,
            "strategy": self.primary_strategy.value,
            "state": self.current_state.value,
            "current_delay": self.current_delay,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success": current_time - self.last_success_time,
            "time_since_last_rate_limit": current_time - self.last_rate_limit_time if self.last_rate_limit_time > 0 else 0,
            "circuit_breaker": {
                "failure_count": self.circuit_failure_count,
                "failure_threshold": self.circuit_failure_threshold,
                "timeout": self.circuit_timeout,
                "half_open_requests": self.circuit_half_open_requests,
                "max_half_open_requests": self.circuit_half_open_max_requests
            },
            "metrics": {
                "total_rate_limits": self.metrics.total_rate_limits,
                "successful_recoveries": self.metrics.successful_recoveries,
                "failed_recoveries": self.metrics.failed_recoveries,
                "success_rate": (
                    self.metrics.successful_recoveries / 
                    max(1, self.metrics.successful_recoveries + self.metrics.failed_recoveries)
                ) * 100,
                "average_recovery_time": self.metrics.average_recovery_time,
                "max_recovery_time": self.metrics.max_recovery_time,
                "strategy_effectiveness": {
                    strategy.value: effectiveness 
                    for strategy, effectiveness in self.metrics.strategy_effectiveness.items()
                }
            }
        }
    
    def reset_state(self):
        """Reset recovery state (for testing or manual intervention)."""
        logger.info(f"Resetting recovery state for {self.exchange_type.value}")
        
        self.current_state = RecoveryState.NORMAL
        self.current_delay = self.config.initial_delay
        self.consecutive_failures = 0
        self.circuit_failure_count = 0
        self.recovery_start_time = 0.0
        self.fibonacci_index = 0


class GlobalRecoveryManager:
    """
    Global manager for rate limit recovery across all exchanges.
    
    Coordinates recovery strategies and provides cross-exchange insights.
    """
    
    def __init__(self):
        """Initialize global recovery manager."""
        self.recovery_managers: Dict[ExchangeType, RateLimitRecoveryManager] = {}
        self.global_metrics = {
            "total_rate_limits": 0,
            "total_recoveries": 0,
            "average_recovery_time": 0.0,
            "most_effective_strategy": None
        }
        
        logger.info("Initialized global recovery manager")
    
    def add_exchange(
        self,
        exchange_type: ExchangeType,
        strategy: RecoveryStrategy = RecoveryStrategy.ADAPTIVE_BACKOFF,
        config: Optional[BackoffConfig] = None
    ):
        """Add recovery manager for exchange."""
        if exchange_type in self.recovery_managers:
            logger.warning(f"Recovery manager for {exchange_type.value} already exists, replacing")
        
        manager = RateLimitRecoveryManager(exchange_type, strategy, config)
        
        # Add callback for global metrics
        manager.add_recovery_callback(self._update_global_metrics)
        
        self.recovery_managers[exchange_type] = manager
        logger.info(f"Added recovery manager for {exchange_type.value}")
    
    async def handle_rate_limit(
        self,
        exchange_type: ExchangeType,
        retry_after: Optional[float] = None,
        error_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Handle rate limit for specific exchange."""
        manager = self.recovery_managers.get(exchange_type)
        if not manager:
            logger.warning(f"No recovery manager for {exchange_type.value}, using default delay")
            return 60.0  # Default 1 minute delay
        
        delay = await manager.handle_rate_limit(retry_after, error_context)
        self.global_metrics["total_rate_limits"] += 1
        
        return delay
    
    async def handle_successful_request(self, exchange_type: ExchangeType):
        """Handle successful request for exchange."""
        manager = self.recovery_managers.get(exchange_type)
        if manager:
            await manager.handle_successful_request()
    
    async def handle_failed_recovery(self, exchange_type: ExchangeType):
        """Handle failed recovery for exchange."""
        manager = self.recovery_managers.get(exchange_type)
        if manager:
            await manager.handle_failed_recovery()
    
    def should_allow_request(self, exchange_type: ExchangeType) -> bool:
        """Check if request should be allowed for exchange."""
        manager = self.recovery_managers.get(exchange_type)
        if manager:
            return manager.should_allow_request()
        return True  # Allow if no manager
    
    def get_exchange_status(self, exchange_type: ExchangeType) -> Optional[Dict[str, Any]]:
        """Get recovery status for specific exchange."""
        manager = self.recovery_managers.get(exchange_type)
        return manager.get_status() if manager else None
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get recovery status for all exchanges."""
        exchange_status = {}
        
        for exchange_type, manager in self.recovery_managers.items():
            exchange_status[exchange_type.value] = manager.get_status()
        
        # Calculate global metrics
        self._calculate_global_metrics()
        
        return {
            "global_metrics": self.global_metrics.copy(),
            "exchanges": exchange_status
        }
    
    def _calculate_global_metrics(self):
        """Calculate global recovery metrics."""
        total_recoveries = 0
        total_recovery_time = 0.0
        strategy_scores = defaultdict(list)
        
        for manager in self.recovery_managers.values():
            metrics = manager.metrics
            total_recoveries += metrics.successful_recoveries
            
            if metrics.recovery_times:
                total_recovery_time += sum(metrics.recovery_times)
            
            # Collect strategy effectiveness scores
            for strategy, effectiveness in metrics.strategy_effectiveness.items():
                strategy_scores[strategy].append(effectiveness)
        
        # Update global metrics
        self.global_metrics["total_recoveries"] = total_recoveries
        
        if total_recoveries > 0:
            self.global_metrics["average_recovery_time"] = total_recovery_time / total_recoveries
        
        # Find most effective strategy
        if strategy_scores:
            strategy_averages = {
                strategy: statistics.mean(scores) 
                for strategy, scores in strategy_scores.items()
            }
            self.global_metrics["most_effective_strategy"] = max(
                strategy_averages, key=strategy_averages.get
            ).value
    
    async def _update_global_metrics(self, state: RecoveryState, delay: float):
        """Callback to update global metrics."""
        # This is called by individual recovery managers
        pass
    
    def reset_all_states(self):
        """Reset all recovery states."""
        logger.info("Resetting all recovery states")
        
        for manager in self.recovery_managers.values():
            manager.reset_state()
    
    def export_recovery_report(self, file_path: str):
        """Export comprehensive recovery report."""
        try:
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "global_summary": self.global_metrics.copy(),
                "exchange_details": {}
            }
            
            for exchange_type, manager in self.recovery_managers.items():
                report["exchange_details"][exchange_type.value] = manager.get_status()
            
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Recovery report exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export recovery report: {e}")


# Global recovery manager instance
global_recovery_manager = GlobalRecoveryManager()


# Convenience functions
def initialize_recovery_managers(
    exchange_configs: Dict[ExchangeType, Dict[str, Any]]
):
    """Initialize recovery managers for all exchanges."""
    for exchange_type, config in exchange_configs.items():
        strategy = RecoveryStrategy(config.get("strategy", "adaptive_backoff"))
        
        backoff_config = BackoffConfig(
            initial_delay=config.get("initial_delay", 1.0),
            max_delay=config.get("max_delay", 300.0),
            multiplier=config.get("multiplier", 2.0),
            jitter_factor=config.get("jitter_factor", 0.1)
        )
        
        global_recovery_manager.add_exchange(exchange_type, strategy, backoff_config)
    
    logger.info(f"Initialized recovery managers for {len(exchange_configs)} exchanges")


async def handle_exchange_rate_limit(
    exchange_type: ExchangeType,
    retry_after: Optional[float] = None,
    error_context: Optional[Dict[str, Any]] = None
) -> float:
    """Handle rate limit using global recovery manager."""
    return await global_recovery_manager.handle_rate_limit(
        exchange_type, retry_after, error_context
    )


def should_allow_exchange_request(exchange_type: ExchangeType) -> bool:
    """Check if request should be allowed using global recovery manager."""
    return global_recovery_manager.should_allow_request(exchange_type)