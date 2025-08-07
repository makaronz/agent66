"""
Error handling utilities for SMC Trading Agent.

This module provides comprehensive error handling patterns including:
- Custom exception classes for trading-specific errors
- Circuit breaker pattern for component health monitoring
- Graceful degradation strategies
- Retry mechanisms for transient failures
- Structured error logging and monitoring
"""

import logging
import time
import functools
from typing import Any, Callable, Dict, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass
from contextlib import contextmanager


class ErrorSeverity(Enum):
    """Error severity levels for trading operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradingError(Exception):
    """Base exception for all trading-related errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 component: str = "unknown", context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.component = component
        self.context = context or {}
        self.timestamp = time.time()


class DataValidationError(TradingError):
    """Raised when data validation fails."""
    pass


class ComponentHealthError(TradingError):
    """Raised when a component is unhealthy or unavailable."""
    pass


class ExecutionError(TradingError):
    """Raised when trade execution fails."""
    pass


class DecisionError(TradingError):
    """Raised when decision engine fails."""
    pass


class RiskManagementError(TradingError):
    """Raised when risk management calculations fail."""
    pass


@dataclass
class CircuitBreakerState:
    """Circuit breaker state information."""
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    threshold: int = 5
    timeout: float = 60.0  # seconds


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for component health monitoring.
    
    Prevents cascading failures by temporarily disabling unhealthy components.
    """
    
    def __init__(self, name: str, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0, logger: Optional[logging.Logger] = None):
        self.name = name
        self.state = CircuitBreakerState(
            threshold=failure_threshold,
            timeout=recovery_timeout
        )
        self.logger = logger or logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state.state == "OPEN":
            if time.time() - self.state.last_failure_time > self.state.timeout:
                self.state.state = "HALF_OPEN"
                self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
            else:
                raise ComponentHealthError(
                    f"Circuit breaker {self.name} is OPEN",
                    severity=ErrorSeverity.HIGH,
                    component=self.name,
                    context={"state": self.state.state, "last_failure": self.state.last_failure_time}
                )
        
        try:
            result = func(*args, **kwargs)
            if self.state.state == "HALF_OPEN":
                self._reset()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def _record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.state.failure_count += 1
        self.state.last_failure_time = time.time()
        
        if self.state.failure_count >= self.state.threshold:
            self.state.state = "OPEN"
            self.logger.error(
                f"Circuit breaker {self.name} opened after {self.state.failure_count} failures",
                extra={
                    "component": self.name,
                    "failure_count": self.state.failure_count,
                    "threshold": self.state.threshold
                }
            )
    
    def _reset(self):
        """Reset the circuit breaker to closed state."""
        self.state.failure_count = 0
        self.state.last_failure_time = None
        self.state.state = "CLOSED"
        self.logger.info(f"Circuit breaker {self.name} reset to CLOSED")


class RetryHandler:
    """Retry mechanism for handling transient failures."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0,
                 logger: Optional[logging.Logger] = None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.logger = logger or logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    self.logger.error(
                        f"Function {func.__name__} failed after {self.max_retries} retries",
                        extra={
                            "function": func.__name__,
                            "attempts": attempt + 1,
                            "max_retries": self.max_retries,
                            "error": str(e)
                        }
                    )
                    raise
                
                delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
                self.logger.warning(
                    f"Function {func.__name__} failed, retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries + 1})",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries,
                        "delay": delay,
                        "error": str(e)
                    }
                )
                time.sleep(delay)
        
        raise last_exception


@contextmanager
def error_boundary(component: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                  fallback: Optional[Callable] = None, logger: Optional[logging.Logger] = None):
    """
    Context manager for error boundary pattern.
    
    Provides a safe execution environment with optional fallback handling.
    """
    log = logger or logging.getLogger(__name__)
    
    try:
        yield
    except Exception as e:
        log.error(
            f"Error in component {component}: {str(e)}",
            extra={
                "component": component,
                "severity": severity.value,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        
        if fallback:
            try:
                log.info(f"Executing fallback for component {component}")
                fallback()
            except Exception as fallback_error:
                log.error(
                    f"Fallback for component {component} also failed: {str(fallback_error)}",
                    extra={
                        "component": component,
                        "fallback_error": str(fallback_error)
                    }
                )
        
        # Re-raise as TradingError if it's not already
        if not isinstance(e, TradingError):
            raise TradingError(
                f"Error in {component}: {str(e)}",
                severity=severity,
                component=component,
                context={"original_error": str(e), "error_type": type(e).__name__}
            ) from e
        raise


def safe_execute(func: Callable, component: str, 
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                fallback: Optional[Callable] = None,
                logger: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator for safe execution with error handling.
    
    Wraps a function with error boundary and optional fallback.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with error_boundary(component, severity, fallback, logger):
            return func(*args, **kwargs)
    return wrapper


class HealthMonitor:
    """Component health monitoring and reporting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.components: Dict[str, Dict[str, Any]] = {}
    
    def register_component(self, name: str, health_check: Callable[[], bool],
                          critical: bool = False):
        """Register a component for health monitoring."""
        self.components[name] = {
            "health_check": health_check,
            "critical": critical,
            "last_check": None,
            "healthy": True,
            "error_count": 0
        }
    
    def check_health(self, component_name: str) -> bool:
        """Check health of a specific component."""
        if component_name not in self.components:
            return True
        
        component = self.components[component_name]
        try:
            is_healthy = component["health_check"]()
            component["healthy"] = is_healthy
            component["last_check"] = time.time()
            
            if not is_healthy:
                component["error_count"] += 1
                self.logger.warning(
                    f"Component {component_name} health check failed",
                    extra={
                        "component": component_name,
                        "error_count": component["error_count"],
                        "critical": component["critical"]
                    }
                )
            
            return is_healthy
        except Exception as e:
            component["healthy"] = False
            component["error_count"] += 1
            component["last_check"] = time.time()
            
            self.logger.error(
                f"Health check for component {component_name} raised exception: {str(e)}",
                extra={
                    "component": component_name,
                    "error": str(e),
                    "error_count": component["error_count"],
                    "critical": component["critical"]
                }
            )
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        health_status = {
            "overall_healthy": True,
            "components": {},
            "critical_failures": 0,
            "total_failures": 0
        }
        
        for name, component in self.components.items():
            is_healthy = self.check_health(name)
            health_status["components"][name] = {
                "healthy": is_healthy,
                "critical": component["critical"],
                "error_count": component["error_count"],
                "last_check": component["last_check"]
            }
            
            if not is_healthy:
                health_status["total_failures"] += 1
                if component["critical"]:
                    health_status["critical_failures"] += 1
                    health_status["overall_healthy"] = False
        
        return health_status


# Global health monitor instance
health_monitor = HealthMonitor()
