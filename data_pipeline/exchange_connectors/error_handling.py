"""
Exchange-Specific Error Handling

Comprehensive error handling system for all supported exchanges with
specific error codes, recovery strategies, and monitoring integration.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import traceback

from .production_config import ExchangeType

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    DATA_ERROR = "data_error"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery actions that can be taken."""
    RETRY = "retry"
    RECONNECT = "reconnect"
    BACKOFF = "backoff"
    FAILOVER = "failover"
    ALERT = "alert"
    IGNORE = "ignore"
    SHUTDOWN = "shutdown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    exchange_type: ExchangeType
    operation: str
    timestamp: float
    request_id: Optional[str] = None
    symbol: Optional[str] = None
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    response_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "exchange": self.exchange_type.value,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "symbol": self.symbol,
            "endpoint": self.endpoint,
            "parameters": self.parameters,
            "response_code": self.response_code,
            "response_data": self.response_data
        }


@dataclass
class ExchangeError:
    """Structured exchange error information."""
    exchange_type: ExchangeType
    error_code: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_actions: List[RecoveryAction]
    context: ErrorContext
    original_exception: Optional[Exception] = None
    retry_count: int = 0
    max_retries: int = 3
    backoff_delay: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/monitoring."""
        return {
            "exchange": self.exchange_type.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recovery_actions": [action.value for action in self.recovery_actions],
            "context": self.context.to_dict(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "backoff_delay": self.backoff_delay,
            "exception_type": type(self.original_exception).__name__ if self.original_exception else None
        }


class ExchangeErrorHandler(ABC):
    """Abstract base class for exchange-specific error handlers."""
    
    @abstractmethod
    def classify_error(self, exception: Exception, context: ErrorContext) -> ExchangeError:
        """Classify an exception into a structured error."""
        pass
    
    @abstractmethod
    def get_recovery_strategy(self, error: ExchangeError) -> List[RecoveryAction]:
        """Get recovery strategy for a specific error."""
        pass
    
    @abstractmethod
    def should_retry(self, error: ExchangeError) -> bool:
        """Determine if an error should be retried."""
        pass


class BinanceErrorHandler(ExchangeErrorHandler):
    """Error handler for Binance exchange."""
    
    # Binance-specific error codes and their classifications
    ERROR_CLASSIFICATIONS = {
        # Authentication errors
        -2014: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Invalid API key"),
        -2015: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Invalid API key format"),
        -1022: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Signature verification failed"),
        
        # Rate limiting
        -1003: (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, "Too many requests"),
        -1015: (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, "Too many orders"),
        
        # API errors
        -1000: (ErrorCategory.API_ERROR, ErrorSeverity.LOW, "Unknown error"),
        -1001: (ErrorCategory.CONNECTION, ErrorSeverity.MEDIUM, "Disconnected"),
        -1002: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Unauthorized"),
        -1006: (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM, "Unexpected response"),
        -1007: (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM, "Timeout"),
        
        # Data errors
        -1100: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Illegal characters"),
        -1101: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Too many parameters"),
        -1102: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Mandatory parameter missing"),
        -1121: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Invalid symbol"),
        
        # Network errors
        -1006: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Unexpected response"),
        -1007: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Timeout waiting for response")
    }
    
    def classify_error(self, exception: Exception, context: ErrorContext) -> ExchangeError:
        """Classify Binance-specific errors."""
        error_code = "UNKNOWN"
        error_message = str(exception)
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        # Try to extract Binance error code from response
        if hasattr(exception, 'response') and exception.response:
            try:
                response_data = exception.response.json() if hasattr(exception.response, 'json') else {}
                if 'code' in response_data:
                    binance_code = response_data['code']
                    if binance_code in self.ERROR_CLASSIFICATIONS:
                        category, severity, error_message = self.ERROR_CLASSIFICATIONS[binance_code]
                        error_code = f"BINANCE_{binance_code}"
                    
                    if 'msg' in response_data:
                        error_message = response_data['msg']
                        
            except Exception as e:
                logger.warning(f"Failed to parse Binance error response: {e}")
        
        # Classify by exception type if no specific code found
        if category == ErrorCategory.UNKNOWN:
            if "timeout" in error_message.lower():
                category = ErrorCategory.NETWORK
                severity = ErrorSeverity.MEDIUM
            elif "connection" in error_message.lower():
                category = ErrorCategory.CONNECTION
                severity = ErrorSeverity.HIGH
            elif "rate limit" in error_message.lower():
                category = ErrorCategory.RATE_LIMIT
                severity = ErrorSeverity.MEDIUM
        
        # Determine recovery actions
        recovery_actions = self.get_recovery_strategy_for_category(category, severity)
        
        return ExchangeError(
            exchange_type=ExchangeType.BINANCE,
            error_code=error_code,
            error_message=error_message,
            category=category,
            severity=severity,
            recovery_actions=recovery_actions,
            context=context,
            original_exception=exception
        )
    
    def get_recovery_strategy(self, error: ExchangeError) -> List[RecoveryAction]:
        """Get recovery strategy for Binance errors."""
        return self.get_recovery_strategy_for_category(error.category, error.severity)
    
    def get_recovery_strategy_for_category(self, category: ErrorCategory, severity: ErrorSeverity) -> List[RecoveryAction]:
        """Get recovery strategy based on category and severity."""
        if category == ErrorCategory.RATE_LIMIT:
            return [RecoveryAction.BACKOFF, RecoveryAction.RETRY]
        elif category == ErrorCategory.CONNECTION:
            return [RecoveryAction.RECONNECT, RecoveryAction.RETRY]
        elif category == ErrorCategory.NETWORK:
            return [RecoveryAction.BACKOFF, RecoveryAction.RETRY]
        elif category == ErrorCategory.AUTHENTICATION:
            return [RecoveryAction.ALERT, RecoveryAction.SHUTDOWN]
        elif category == ErrorCategory.DATA_ERROR:
            return [RecoveryAction.ALERT]
        else:
            return [RecoveryAction.RETRY, RecoveryAction.ALERT]
    
    def should_retry(self, error: ExchangeError) -> bool:
        """Determine if Binance error should be retried."""
        if error.retry_count >= error.max_retries:
            return False
        
        # Don't retry authentication errors
        if error.category == ErrorCategory.AUTHENTICATION:
            return False
        
        # Don't retry data errors
        if error.category == ErrorCategory.DATA_ERROR:
            return False
        
        # Retry network and connection errors
        if error.category in [ErrorCategory.NETWORK, ErrorCategory.CONNECTION, ErrorCategory.RATE_LIMIT]:
            return True
        
        return False


class BybitErrorHandler(ExchangeErrorHandler):
    """Error handler for Bybit exchange."""
    
    # Bybit-specific error codes
    ERROR_CLASSIFICATIONS = {
        # Authentication
        10001: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Invalid API key"),
        10003: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Invalid signature"),
        10004: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Invalid timestamp"),
        
        # Rate limiting
        10006: (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, "Rate limit exceeded"),
        
        # API errors
        10000: (ErrorCategory.API_ERROR, ErrorSeverity.LOW, "Unknown error"),
        10002: (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM, "Invalid request"),
        10005: (ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM, "Permission denied"),
        
        # Data errors
        10007: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Invalid parameter"),
        10008: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Missing parameter"),
        10009: (ErrorCategory.DATA_ERROR, ErrorSeverity.LOW, "Invalid symbol")
    }
    
    def classify_error(self, exception: Exception, context: ErrorContext) -> ExchangeError:
        """Classify Bybit-specific errors."""
        error_code = "UNKNOWN"
        error_message = str(exception)
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        # Try to extract Bybit error code
        if hasattr(exception, 'response') and exception.response:
            try:
                response_data = exception.response.json() if hasattr(exception.response, 'json') else {}
                if 'ret_code' in response_data:
                    bybit_code = response_data['ret_code']
                    if bybit_code in self.ERROR_CLASSIFICATIONS:
                        category, severity, error_message = self.ERROR_CLASSIFICATIONS[bybit_code]
                        error_code = f"BYBIT_{bybit_code}"
                    
                    if 'ret_msg' in response_data:
                        error_message = response_data['ret_msg']
                        
            except Exception as e:
                logger.warning(f"Failed to parse Bybit error response: {e}")
        
        # Fallback classification
        if category == ErrorCategory.UNKNOWN:
            if "timeout" in error_message.lower():
                category = ErrorCategory.NETWORK
            elif "connection" in error_message.lower():
                category = ErrorCategory.CONNECTION
        
        recovery_actions = self.get_recovery_strategy_for_category(category, severity)
        
        return ExchangeError(
            exchange_type=ExchangeType.BYBIT,
            error_code=error_code,
            error_message=error_message,
            category=category,
            severity=severity,
            recovery_actions=recovery_actions,
            context=context,
            original_exception=exception
        )
    
    def get_recovery_strategy(self, error: ExchangeError) -> List[RecoveryAction]:
        """Get recovery strategy for Bybit errors."""
        return self.get_recovery_strategy_for_category(error.category, error.severity)
    
    def get_recovery_strategy_for_category(self, category: ErrorCategory, severity: ErrorSeverity) -> List[RecoveryAction]:
        """Get recovery strategy based on category and severity."""
        if category == ErrorCategory.RATE_LIMIT:
            return [RecoveryAction.BACKOFF, RecoveryAction.RETRY]
        elif category == ErrorCategory.CONNECTION:
            return [RecoveryAction.RECONNECT, RecoveryAction.RETRY]
        elif category == ErrorCategory.AUTHENTICATION:
            return [RecoveryAction.ALERT, RecoveryAction.SHUTDOWN]
        else:
            return [RecoveryAction.RETRY, RecoveryAction.ALERT]
    
    def should_retry(self, error: ExchangeError) -> bool:
        """Determine if Bybit error should be retried."""
        if error.retry_count >= error.max_retries:
            return False
        
        if error.category == ErrorCategory.AUTHENTICATION:
            return False
        
        if error.category in [ErrorCategory.NETWORK, ErrorCategory.CONNECTION, ErrorCategory.RATE_LIMIT]:
            return True
        
        return False


class OandaErrorHandler(ExchangeErrorHandler):
    """Error handler for OANDA exchange."""
    
    def classify_error(self, exception: Exception, context: ErrorContext) -> ExchangeError:
        """Classify OANDA-specific errors."""
        error_code = "UNKNOWN"
        error_message = str(exception)
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        # OANDA uses HTTP status codes primarily
        if hasattr(exception, 'response') and exception.response:
            status_code = getattr(exception.response, 'status_code', None)
            
            if status_code == 401:
                category = ErrorCategory.AUTHENTICATION
                severity = ErrorSeverity.HIGH
                error_code = "OANDA_401"
                error_message = "Authentication failed"
            elif status_code == 403:
                category = ErrorCategory.AUTHENTICATION
                severity = ErrorSeverity.HIGH
                error_code = "OANDA_403"
                error_message = "Forbidden - insufficient permissions"
            elif status_code == 429:
                category = ErrorCategory.RATE_LIMIT
                severity = ErrorSeverity.MEDIUM
                error_code = "OANDA_429"
                error_message = "Rate limit exceeded"
            elif status_code >= 500:
                category = ErrorCategory.API_ERROR
                severity = ErrorSeverity.HIGH
                error_code = f"OANDA_{status_code}"
                error_message = "Server error"
        
        recovery_actions = self.get_recovery_strategy_for_category(category, severity)
        
        return ExchangeError(
            exchange_type=ExchangeType.OANDA,
            error_code=error_code,
            error_message=error_message,
            category=category,
            severity=severity,
            recovery_actions=recovery_actions,
            context=context,
            original_exception=exception
        )
    
    def get_recovery_strategy(self, error: ExchangeError) -> List[RecoveryAction]:
        """Get recovery strategy for OANDA errors."""
        return self.get_recovery_strategy_for_category(error.category, error.severity)
    
    def get_recovery_strategy_for_category(self, category: ErrorCategory, severity: ErrorSeverity) -> List[RecoveryAction]:
        """Get recovery strategy based on category and severity."""
        if category == ErrorCategory.RATE_LIMIT:
            return [RecoveryAction.BACKOFF, RecoveryAction.RETRY]
        elif category == ErrorCategory.CONNECTION:
            return [RecoveryAction.RECONNECT, RecoveryAction.RETRY]
        elif category == ErrorCategory.AUTHENTICATION:
            return [RecoveryAction.ALERT, RecoveryAction.SHUTDOWN]
        else:
            return [RecoveryAction.RETRY, RecoveryAction.ALERT]
    
    def should_retry(self, error: ExchangeError) -> bool:
        """Determine if OANDA error should be retried."""
        if error.retry_count >= error.max_retries:
            return False
        
        if error.category == ErrorCategory.AUTHENTICATION:
            return False
        
        return True


class ErrorHandlerManager:
    """
    Manages error handling for all exchanges.
    
    Provides unified error handling interface with exchange-specific handlers.
    """
    
    def __init__(self):
        """Initialize error handler manager."""
        self.handlers: Dict[ExchangeType, ExchangeErrorHandler] = {
            ExchangeType.BINANCE: BinanceErrorHandler(),
            ExchangeType.BYBIT: BybitErrorHandler(),
            ExchangeType.OANDA: OandaErrorHandler()
        }
        
        self.error_callbacks: List[Callable[[ExchangeError], None]] = []
        self.error_history: List[ExchangeError] = []
        self.max_history_size = 1000
        
        logger.info("Initialized error handler manager")
    
    def add_error_callback(self, callback: Callable[[ExchangeError], None]):
        """
        Add callback to be called when errors occur.
        
        Args:
            callback: Function to call with error information
        """
        self.error_callbacks.append(callback)
    
    async def handle_error(
        self, 
        exception: Exception, 
        exchange_type: ExchangeType,
        operation: str,
        **context_kwargs
    ) -> ExchangeError:
        """
        Handle an error from a specific exchange.
        
        Args:
            exception: The exception that occurred
            exchange_type: Which exchange the error came from
            operation: What operation was being performed
            **context_kwargs: Additional context information
            
        Returns:
            ExchangeError: Structured error information
        """
        # Create error context
        context = ErrorContext(
            exchange_type=exchange_type,
            operation=operation,
            timestamp=time.time(),
            **context_kwargs
        )
        
        # Get appropriate handler
        handler = self.handlers.get(exchange_type)
        if not handler:
            logger.error(f"No error handler found for {exchange_type.value}")
            # Create generic error
            error = ExchangeError(
                exchange_type=exchange_type,
                error_code="NO_HANDLER",
                error_message=str(exception),
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                recovery_actions=[RecoveryAction.ALERT],
                context=context,
                original_exception=exception
            )
        else:
            # Classify the error
            error = handler.classify_error(exception, context)
        
        # Log the error
        await self._log_error(error)
        
        # Store in history
        self._store_error(error)
        
        # Notify callbacks
        await self._notify_callbacks(error)
        
        return error
    
    async def execute_recovery_actions(self, error: ExchangeError, connector=None) -> bool:
        """
        Execute recovery actions for an error.
        
        Args:
            error: The error to recover from
            connector: Optional connector instance for recovery actions
            
        Returns:
            bool: True if recovery was successful
        """
        success = False
        
        for action in error.recovery_actions:
            try:
                if action == RecoveryAction.RETRY:
                    if self.should_retry(error):
                        error.retry_count += 1
                        logger.info(f"Retrying operation for {error.exchange_type.value} (attempt {error.retry_count})")
                        success = True
                    
                elif action == RecoveryAction.BACKOFF:
                    backoff_time = error.backoff_delay * (2 ** error.retry_count)
                    logger.info(f"Backing off for {backoff_time:.2f}s for {error.exchange_type.value}")
                    await asyncio.sleep(backoff_time)
                    success = True
                    
                elif action == RecoveryAction.RECONNECT:
                    if connector:
                        logger.info(f"Attempting reconnection for {error.exchange_type.value}")
                        await connector.disconnect_websocket()
                        success = await connector.connect_websocket()
                    
                elif action == RecoveryAction.ALERT:
                    logger.error(f"Alert triggered for {error.exchange_type.value}: {error.error_message}")
                    # This would integrate with alerting system
                    success = True
                    
                elif action == RecoveryAction.FAILOVER:
                    logger.warning(f"Failover triggered for {error.exchange_type.value}")
                    # This would trigger failover to another exchange
                    success = True
                    
                elif action == RecoveryAction.SHUTDOWN:
                    logger.critical(f"Shutdown triggered for {error.exchange_type.value}: {error.error_message}")
                    # This would trigger graceful shutdown
                    success = False
                    break
                    
            except Exception as e:
                logger.error(f"Recovery action {action.value} failed for {error.exchange_type.value}: {e}")
        
        return success
    
    def should_retry(self, error: ExchangeError) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error: The error to check
            
        Returns:
            bool: True if should retry
        """
        handler = self.handlers.get(error.exchange_type)
        if handler:
            return handler.should_retry(error)
        
        # Default retry logic
        return error.retry_count < error.max_retries and error.category != ErrorCategory.AUTHENTICATION
    
    def get_error_statistics(self, exchange_type: Optional[ExchangeType] = None) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Args:
            exchange_type: Filter by exchange type, or None for all
            
        Returns:
            Dict[str, Any]: Error statistics
        """
        errors = self.error_history
        if exchange_type:
            errors = [e for e in errors if e.exchange_type == exchange_type]
        
        if not errors:
            return {"total_errors": 0}
        
        # Calculate statistics
        total_errors = len(errors)
        by_category = {}
        by_severity = {}
        by_exchange = {}
        
        for error in errors:
            # By category
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # By severity
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # By exchange
            exchange = error.exchange_type.value
            by_exchange[exchange] = by_exchange.get(exchange, 0) + 1
        
        return {
            "total_errors": total_errors,
            "by_category": by_category,
            "by_severity": by_severity,
            "by_exchange": by_exchange,
            "recent_errors": [e.to_dict() for e in errors[-10:]]  # Last 10 errors
        }
    
    async def _log_error(self, error: ExchangeError):
        """Log error with appropriate level."""
        error_dict = error.to_dict()
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {error.exchange_type.value}: {error.error_message}", extra=error_dict)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {error.exchange_type.value}: {error.error_message}", extra=error_dict)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error in {error.exchange_type.value}: {error.error_message}", extra=error_dict)
        else:
            logger.info(f"Low severity error in {error.exchange_type.value}: {error.error_message}", extra=error_dict)
    
    def _store_error(self, error: ExchangeError):
        """Store error in history with size limit."""
        self.error_history.append(error)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    async def _notify_callbacks(self, error: ExchangeError):
        """Notify all registered callbacks."""
        for callback in self.error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")


# Global error handler instance
error_handler_manager = ErrorHandlerManager()


# Convenience functions
async def handle_exchange_error(
    exception: Exception,
    exchange_type: ExchangeType,
    operation: str,
    **context_kwargs
) -> ExchangeError:
    """Handle an exchange error using the global error handler."""
    return await error_handler_manager.handle_error(
        exception, exchange_type, operation, **context_kwargs
    )


def add_error_callback(callback: Callable[[ExchangeError], None]):
    """Add error callback to the global error handler."""
    error_handler_manager.add_error_callback(callback)


async def execute_with_error_handling(
    func: Callable,
    exchange_type: ExchangeType,
    operation: str,
    max_retries: int = 3,
    **context_kwargs
) -> Any:
    """
    Execute a function with comprehensive error handling.
    
    Args:
        func: Function to execute
        exchange_type: Exchange type for error handling
        operation: Operation name for logging
        max_retries: Maximum number of retries
        **context_kwargs: Additional context for error handling
        
    Returns:
        Any: Function result
        
    Raises:
        Exception: If all retries are exhausted
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
                
        except Exception as e:
            error = await handle_exchange_error(
                e, exchange_type, operation, attempt=attempt, **context_kwargs
            )
            last_error = error
            
            if attempt < max_retries and error_handler_manager.should_retry(error):
                # Execute recovery actions
                success = await error_handler_manager.execute_recovery_actions(error)
                if success:
                    continue
            
            # If we're here, either max retries reached or recovery failed
            break
    
    # All retries exhausted
    if last_error:
        raise last_error.original_exception or Exception(f"Operation failed after {max_retries} retries")
    else:
        raise Exception("Operation failed with unknown error")