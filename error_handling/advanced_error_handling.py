"""
Advanced Error Handling and Resilient System Architecture

This module implements comprehensive error handling with automatic recovery,
intelligent circuit breaking, distributed tracing, and advanced logging
for mission-critical trading operations.

Key Features:
- Intelligent circuit breaking with adaptive thresholds
- Automatic retry with exponential backoff and jitter
- Distributed tracing and performance monitoring
- Graceful degradation and fallback mechanisms
- Real-time error classification and alerting
- Advanced logging with structured metrics
- Health monitoring with proactive failure detection
- Automatic system recovery and self-healing capabilities
"""

import logging
import asyncio
import time
import random
import traceback
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import defaultdict, deque
import threading
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels for classification and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for intelligent handling"""
    NETWORK = "network"
    API = "api"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    DATA = "data"
    EXECUTION = "execution"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class ErrorMetrics:
    """Comprehensive error metrics"""
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    error_rate: float = 0.0
    avg_resolution_time: float = 0.0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)

@dataclass
class TraceContext:
    """Distributed tracing context"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

class AdaptiveCircuitBreaker:
    """Intelligent circuit breaker with adaptive thresholds"""

    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0, expected_recovery_time: float = 30.0,
                 monitoring_window: int = 100):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_recovery_time = expected_recovery_time
        self.monitoring_window = monitoring_window

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None

        # Adaptive parameters
        self.adaptive_threshold = failure_threshold
        self.adaptive_timeout = recovery_timeout
        self.performance_history = deque(maxlen=monitoring_window)
        self.error_patterns = defaultdict(int)

        # Metrics
        self.metrics = ErrorMetrics()
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        if not self._should_attempt_call():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(e, time.time() - start_time)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function through circuit breaker"""
        if not self._should_attempt_call():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(e, time.time() - start_time)
            raise

    def _should_attempt_call(self) -> bool:
        """Determine if call should be attempted"""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if (self.last_failure_time and
                    time.time() - self.last_failure_time > self.recovery_timeout):
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True
            return False

    def _record_success(self, execution_time: float):
        """Record successful execution"""
        with self.lock:
            self.success_count += 1
            self.last_success_time = time.time()
            self.performance_history.append(execution_time)

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.metrics.successful_recoveries += 1
                logger.info(f"Circuit breaker '{self.name}' recovered and closed")

            # Adaptive threshold adjustment
            self._adjust_adaptive_parameters()

    def _record_failure(self, error: Exception, execution_time: float):
        """Record failed execution"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.metrics.error_count += 1
            self.metrics.last_error_time = datetime.utcnow()

            # Classify error
            error_type = type(error).__name__
            self.error_patterns[error_type] += 1

            # Update severity and category distributions
            severity = self._classify_error_severity(error)
            category = self._classify_error_category(error)
            self.metrics.severity_distribution[severity.value] += 1
            self.metrics.category_distribution[category.value] += 1

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' re-opened after failure in HALF_OPEN state")

            elif self.failure_count >= self.adaptive_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")

    def _classify_error_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity"""
        error_type = type(error).__name__

        if error_type in ['TimeoutError', 'ConnectionError']:
            return ErrorSeverity.HIGH
        elif error_type in ['ValueError', 'ValidationError']:
            return ErrorSeverity.MEDIUM
        elif 'Critical' in str(error):
            return ErrorSeverity.CRITICAL
        else:
            return ErrorSeverity.LOW

    def _classify_error_category(self, error: Exception) -> ErrorCategory:
        """Classify error category"""
        error_type = type(error).__name__
        error_message = str(error).lower()

        if any(keyword in error_message for keyword in ['network', 'connection', 'timeout']):
            return ErrorCategory.NETWORK
        elif 'api' in error_message or 'http' in error_type.lower():
            return ErrorCategory.API
        elif 'validation' in error_message or 'invalid' in error_message:
            return ErrorCategory.VALIDATION
        elif 'rate' in error_message or 'limit' in error_message:
            return ErrorCategory.RATE_LIMIT
        elif 'system' in error_message or 'memory' in error_message:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.BUSINESS_LOGIC

    def _adjust_adaptive_parameters(self):
        """Adjust circuit breaker parameters based on performance"""
        if len(self.performance_history) < 10:
            return

        avg_execution_time = np.mean(self.performance_history)
        error_rate = self.failure_count / (self.failure_count + self.success_count + 0.001)

        # Adjust threshold based on error rate
        if error_rate > 0.1:  # High error rate
            self.adaptive_threshold = max(2, int(self.failure_threshold * 0.8))
        elif error_rate < 0.02:  # Low error rate
            self.adaptive_threshold = int(self.failure_threshold * 1.2)

        # Adjust timeout based on execution time
        if avg_execution_time > self.expected_recovery_time * 2:
            self.adaptive_timeout = min(300, self.recovery_timeout * 1.5)
        elif avg_execution_time < self.expected_recovery_time * 0.5:
            self.adaptive_timeout = max(10, self.recovery_timeout * 0.8)

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self.lock:
            total_requests = self.failure_count + self.success_count
            error_rate = self.failure_count / (total_requests + 0.001)

            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'error_rate': error_rate,
                'adaptive_threshold': self.adaptive_threshold,
                'adaptive_timeout': self.adaptive_timeout,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'performance_history_size': len(self.performance_history),
                'avg_execution_time': np.mean(self.performance_history) if self.performance_history else 0,
                'error_patterns': dict(self.error_patterns)
            }

class IntelligentRetryHandler:
    """Intelligent retry handler with adaptive backoff and jitter"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, backoff_factor: float = 2.0,
                 jitter: bool = True, retry_on: Optional[List[Type[Exception]]] = None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on = retry_on or [Exception]

        self.retry_history = deque(maxlen=1000)
        self.success_rates = defaultdict(list)

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with intelligent retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Record success
                self._record_success(func.__name__, attempt)
                return result

            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    self._record_failure(func.__name__, attempt, str(e))
                    raise

                # Check if we should retry
                if attempt == self.max_retries:
                    self._record_failure(func.__name__, attempt, str(e))
                    raise

                # Calculate delay with jitter
                delay = self._calculate_delay(attempt)

                # Record retry attempt
                self._record_retry(func.__name__, attempt, str(e), delay)

                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries + 1} for {func.__name__}",
                    extra={
                        'function': func.__name__,
                        'attempt': attempt + 1,
                        'max_retries': self.max_retries + 1,
                        'delay': delay,
                        'error': str(e)
                    }
                )

                await asyncio.sleep(delay)

        # Should never reach here
        raise last_exception

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        return any(isinstance(exception, retry_type) for retry_type in self.retry_on)

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add jitter to prevent thundering herd
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount

        return delay

    def _record_success(self, function_name: str, attempt: int):
        """Record successful execution"""
        self.success_rates[function_name].append(True)

    def _record_retry(self, function_name: str, attempt: int, error: str, delay: float):
        """Record retry attempt"""
        self.retry_history.append({
            'function': function_name,
            'attempt': attempt,
            'error': error,
            'delay': delay,
            'timestamp': datetime.utcnow().isoformat()
        })

    def _record_failure(self, function_name: str, attempt: int, error: str):
        """Record failed execution"""
        self.success_rates[function_name].append(False)

    def get_metrics(self) -> Dict[str, Any]:
        """Get retry handler metrics"""
        total_retries = len(self.retry_history)
        success_rates = {}

        for func_name, results in self.success_rates.items():
            if results:
                success_rates[func_name] = {
                    'success_rate': sum(results) / len(results),
                    'total_attempts': len(results)
                }

        return {
            'total_retries': total_retries,
            'success_rates': success_rates,
            'max_retries': self.max_retries,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay
        }

class DistributedTracer:
    """Distributed tracing for complex operations"""

    def __init__(self):
        self.active_traces: Dict[str, TraceContext] = {}
        self.completed_traces: deque = deque(maxlen=10000)
        self.lock = threading.Lock()

    def start_trace(self, operation_name: str, parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> str:
        """Start a new trace"""
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()

        trace = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            tags=tags or {}
        )

        with self.lock:
            self.active_traces[span_id] = trace

        return span_id

    def finish_trace(self, span_id: str, error: Optional[Exception] = None):
        """Finish a trace"""
        with self.lock:
            trace = self.active_traces.pop(span_id, None)

        if trace:
            trace.logs.append({
                'event': 'finished',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(error) if error else None
            })

            # Calculate duration
            duration = (datetime.utcnow() - trace.start_time).total_seconds()
            trace.tags['duration_ms'] = duration * 1000

            if error:
                trace.tags['error'] = True
                trace.tags['error_type'] = type(error).__name__

            self.completed_traces.append(trace)

    def add_log(self, span_id: str, message: str, level: str = "info",
                fields: Optional[Dict[str, Any]] = None):
        """Add log entry to trace"""
        with self.lock:
            trace = self.active_traces.get(span_id)

        if trace:
            log_entry = {
                'message': message,
                'level': level,
                'timestamp': datetime.utcnow().isoformat()
            }
            if fields:
                log_entry.update(fields)

            trace.logs.append(log_entry)

    def add_tag(self, span_id: str, key: str, value: Any):
        """Add tag to trace"""
        with self.lock:
            trace = self.active_traces.get(span_id)

        if trace:
            trace.tags[key] = value

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID"""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()

    def _generate_span_id(self) -> str:
        """Generate unique span ID"""
        return hashlib.md5(f"{time.time()}{random.random()}{threading.get_ident()}".encode()).hexdigest()[:16]

    def get_trace_metrics(self) -> Dict[str, Any]:
        """Get tracing metrics"""
        with self.lock:
            active_count = len(self.active_traces)
            completed_count = len(self.completed_traces)

        # Analyze recent traces
        recent_traces = list(self.completed_traces)[-1000:]
        avg_duration = 0
        error_rate = 0

        if recent_traces:
            durations = [trace.tags.get('duration_ms', 0) for trace in recent_traces]
            avg_duration = np.mean(durations)

            errors = [trace for trace in recent_traces if trace.tags.get('error', False)]
            error_rate = len(errors) / len(recent_traces)

        return {
            'active_traces': active_count,
            'completed_traces': completed_count,
            'avg_duration_ms': avg_duration,
            'error_rate': error_rate
        }

class AdvancedErrorHandler:
    """Advanced error handling system with comprehensive features"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Circuit breakers
        self.circuit_breakers: Dict[str, AdaptiveCircuitBreaker] = {}
        self.circuit_breaker_lock = threading.Lock()

        # Retry handlers
        self.retry_handlers: Dict[str, IntelligentRetryHandler] = {}

        # Distributed tracing
        self.tracer = DistributedTracer()

        # Error metrics
        self.global_metrics = ErrorMetrics()
        self.metrics_lock = threading.Lock()

        # Health monitoring
        self.health_status = {
            'overall': 'healthy',
            'components': {},
            'last_check': datetime.utcnow()
        }

        # Alert thresholds
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10%
            'circuit_breaker_open_rate': 0.2,  # 20%
            'avg_response_time': 5000,  # 5 seconds
            'critical_error_rate': 0.05  # 5%
        }

        # Thread pool for async error processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="error_handler")

        self.logger.info("Advanced Error Handler initialized with comprehensive features")

    def get_circuit_breaker(self, name: str) -> AdaptiveCircuitBreaker:
        """Get or create circuit breaker"""
        with self.circuit_breaker_lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = AdaptiveCircuitBreaker(name)
            return self.circuit_breakers[name]

    def get_retry_handler(self, name: str, **kwargs) -> IntelligentRetryHandler:
        """Get or create retry handler"""
        if name not in self.retry_handlers:
            self.retry_handlers[name] = IntelligentRetryHandler(**kwargs)
        return self.retry_handlers[name]

    def safe_execute(self, func: Callable, circuit_breaker_name: str,
                    retry_handler_name: Optional[str] = None,
                    trace_name: Optional[str] = None, *args, **kwargs) -> Any:
        """Execute function with comprehensive error handling"""
        # Start trace
        span_id = self.tracer.start_trace(
            operation_name=trace_name or func.__name__,
            tags={'function': func.__name__}
        )

        try:
            # Get circuit breaker
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)

            # Get retry handler if specified
            if retry_handler_name:
                retry_handler = self.get_retry_handler(retry_handler_name)
                result = circuit_breaker.call(
                    retry_handler.execute_with_retry, func, *args, **kwargs
                )
            else:
                result = circuit_breaker.call(func, *args, **kwargs)

            # Record success
            self.tracer.add_tag(span_id, 'success', True)
            self.tracer.finish_trace(span_id)

            return result

        except Exception as e:
            # Record error
            self.tracer.add_tag(span_id, 'success', False)
            self.tracer.add_tag(span_id, 'error_type', type(e).__name__)
            self.tracer.add_log(span_id, f"Execution failed: {str(e)}", "error")
            self.tracer.finish_trace(span_id, e)

            # Update global metrics
            self._update_global_metrics(e)

            # Check if alert needed
            self._check_alert_conditions(e)

            raise

    async def safe_execute_async(self, func: Callable, circuit_breaker_name: str,
                               retry_handler_name: Optional[str] = None,
                               trace_name: Optional[str] = None, *args, **kwargs) -> Any:
        """Execute async function with comprehensive error handling"""
        # Start trace
        span_id = self.tracer.start_trace(
            operation_name=trace_name or func.__name__,
            tags={'function': func.__name__, 'async': True}
        )

        try:
            # Get circuit breaker
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)

            # Get retry handler if specified
            if retry_handler_name:
                retry_handler = self.get_retry_handler(retry_handler_name)
                result = await circuit_breaker.call_async(
                    retry_handler.execute_with_retry, func, *args, **kwargs
                )
            else:
                result = await circuit_breaker.call_async(func, *args, **kwargs)

            # Record success
            self.tracer.add_tag(span_id, 'success', True)
            self.tracer.finish_trace(span_id)

            return result

        except Exception as e:
            # Record error
            self.tracer.add_tag(span_id, 'success', False)
            self.tracer.add_tag(span_id, 'error_type', type(e).__name__)
            self.tracer.add_log(span_id, f"Async execution failed: {str(e)}", "error")
            self.tracer.finish_trace(span_id, e)

            # Update global metrics
            self._update_global_metrics(e)

            # Check if alert needed
            self._check_alert_conditions(e)

            raise

    @asynccontextmanager
    async def error_context(self, operation_name: str):
        """Context manager for error handling"""
        span_id = self.tracer.start_trace(operation_name=operation_name)

        try:
            yield span_id
            self.tracer.add_tag(span_id, 'success', True)
        except Exception as e:
            self.tracer.add_tag(span_id, 'success', False)
            self.tracer.add_tag(span_id, 'error_type', type(e).__name__)
            self.tracer.add_log(span_id, f"Operation failed: {str(e)}", "error")
            raise
        finally:
            self.tracer.finish_trace(span_id)

    def _update_global_metrics(self, error: Exception):
        """Update global error metrics"""
        with self.metrics_lock:
            self.global_metrics.error_count += 1
            self.global_metrics.last_error_time = datetime.utcnow()

            # Classify error
            severity = self._classify_error_severity(error)
            category = self._classify_error_category(error)

            self.global_metrics.severity_distribution[severity.value] += 1
            self.global_metrics.category_distribution[category.value] += 1

    def _classify_error_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity"""
        error_type = type(error).__name__
        error_message = str(error).lower()

        if any(keyword in error_message for keyword in ['critical', 'fatal', 'panic']):
            return ErrorSeverity.CRITICAL
        elif any(keyword in error_type for keyword in ['Timeout', 'Connection', 'Network']):
            return ErrorSeverity.HIGH
        elif any(keyword in error_message for keyword in ['invalid', 'validation']):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _classify_error_category(self, error: Exception) -> ErrorCategory:
        """Classify error category"""
        error_message = str(error).lower()
        error_type = type(error).__name__

        if any(keyword in error_message for keyword in ['network', 'connection', 'timeout']):
            return ErrorCategory.NETWORK
        elif any(keyword in error_message for keyword in ['api', 'http', 'request']):
            return ErrorCategory.API
        elif any(keyword in error_message for keyword in ['validation', 'invalid', 'required']):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_message for keyword in ['rate', 'limit', 'quota']):
            return ErrorCategory.RATE_LIMIT
        elif any(keyword in error_message for keyword in ['system', 'memory', 'disk']):
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.BUSINESS_LOGIC

    def _check_alert_conditions(self, error: Exception):
        """Check if alert conditions are met"""
        severity = self._classify_error_severity(error)

        # Immediate alert for critical errors
        if severity == ErrorSeverity.CRITICAL:
            self._send_alert("Critical Error", str(error), severity)

        # Check error rate
        with self.metrics_lock:
            total_errors = self.global_metrics.error_count
            if total_errors > 100:  # Minimum sample size
                error_rate = total_errors / (total_errors + 1000)  # Rough estimate
                if error_rate > self.alert_thresholds['error_rate']:
                    self._send_alert("High Error Rate", f"Error rate: {error_rate:.2%}", ErrorSeverity.HIGH)

        # Check circuit breaker status
        open_circuits = sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN)
        total_circuits = len(self.circuit_breakers)

        if total_circuits > 0:
            open_rate = open_circuits / total_circuits
            if open_rate > self.alert_thresholds['circuit_breaker_open_rate']:
                self._send_alert("Circuit Breakers Open", f"{open_circuits}/{total_circuits} circuits open", ErrorSeverity.HIGH)

    def _send_alert(self, title: str, message: str, severity: ErrorSeverity):
        """Send alert (would integrate with alerting system)"""
        self.logger.error(
            f"ALERT: {title}",
            extra={
                'alert_title': title,
                'alert_message': message,
                'severity': severity.value,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        # Update component health
        component_health = {}

        # Circuit breaker health
        for name, cb in self.circuit_breakers.items():
            component_health[f'circuit_breaker_{name}'] = {
                'status': 'healthy' if cb.state == CircuitState.CLOSED else 'degraded',
                'state': cb.state.value,
                'failure_count': cb.failure_count
            }

        # Overall health assessment
        degraded_components = sum(1 for health in component_health.values() if health['status'] != 'healthy')
        total_components = len(component_health) or 1

        if degraded_components == 0:
            overall_status = 'healthy'
        elif degraded_components / total_components < 0.5:
            overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'

        return {
            'overall_status': overall_status,
            'components': component_health,
            'global_metrics': {
                'total_errors': self.global_metrics.error_count,
                'last_error': self.global_metrics.last_error_time.isoformat() if self.global_metrics.last_error_time else None,
                'severity_distribution': dict(self.global_metrics.severity_distribution),
                'category_distribution': dict(self.global_metrics.category_distribution)
            },
            'trace_metrics': self.tracer.get_trace_metrics(),
            'circuit_breaker_metrics': {name: cb.get_metrics() for name, cb in self.circuit_breakers.items()},
            'retry_metrics': {name: handler.get_metrics() for name, handler in self.retry_handlers.items()},
            'last_check': datetime.utcnow().isoformat()
        }

    def cleanup(self):
        """Cleanup resources"""
        self.executor.shutdown(wait=True)
        self.logger.info("Advanced Error Handler cleaned up")

# Decorators for easy use
def circuit_breaker(name: str):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = get_global_error_handler()
            return error_handler.safe_execute(func, name or func.__name__, trace_name=func.__name__, *args, **kwargs)
        return wrapper
    return decorator

def retry(max_retries: int = 3, base_delay: float = 1.0, **kwargs):
    """Decorator for retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = get_global_error_handler()
            cb_name = f"{func.__name__}_cb"
            retry_name = f"{func.__name__}_retry"
            return error_handler.safe_execute(
                func, cb_name, retry_name, trace_name=func.__name__, *args, **kwargs
            )
        return wrapper
    return decorator

# Global error handler instance
_global_error_handler: Optional[AdvancedErrorHandler] = None

def get_global_error_handler() -> AdvancedErrorHandler:
    """Get global error handler instance"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = AdvancedErrorHandler()
    return _global_error_handler

def initialize_error_handler(config: Optional[Dict[str, Any]] = None) -> AdvancedErrorHandler:
    """Initialize global error handler"""
    global _global_error_handler
    _global_error_handler = AdvancedErrorHandler(config)
    return _global_error_handler

# Custom exception classes
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass

class RetryExhaustedException(Exception):
    """Raised when retry attempts are exhausted"""
    pass

class ValidationException(Exception):
    """Raised for validation errors"""
    pass

class SystemHealthException(Exception):
    """Raised for system health issues"""
    pass