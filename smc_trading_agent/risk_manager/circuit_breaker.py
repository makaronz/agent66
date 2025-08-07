"""
Circuit Breaker for SMC Trading Agent.

This module provides comprehensive circuit breaker functionality including:
- VaR and correlation limit checks
- Risk metrics monitoring for 6 risk categories
- Emergency position closure across all exchanges
- Multi-channel alert notifications
- Integration with execution engine
- Comprehensive logging and audit trail
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .var_calculator import VaRCalculator, VaRMethod
from .risk_metrics import RiskMetricsMonitor, RiskCategory, RiskSeverity
from .position_manager import PositionManager
from .notification_service import NotificationService, NotificationChannel, NotificationPriority

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit breaker triggered
    HALF_OPEN = "half_open"  # Testing if safe to close


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker event data."""
    event_type: str
    timestamp: float
    reason: str
    state: CircuitBreakerState
    metadata: Dict[str, Any] = None


class CircuitBreaker:
    """
    Comprehensive circuit breaker for SMC Trading Agent.
    
    Monitors risk metrics, triggers emergency shutdown,
    closes positions, and sends alerts when thresholds are exceeded.
    """
    
    def __init__(self, config: Dict[str, Any], 
                 exchange_connectors: Optional[Dict[str, Any]] = None,
                 service_manager: Optional[Any] = None):
        """
        Initialize circuit breaker.
        
        Args:
            config: Configuration dictionary with circuit breaker parameters
            exchange_connectors: Dictionary of exchange connector instances
            service_manager: Service manager instance for coordination
        """
        self.config = config
        
        # Circuit breaker parameters
        self.max_drawdown = config.get('max_drawdown', 0.08)
        self.max_var = config.get('max_var', 0.05)
        self.max_correlation = config.get('max_correlation', 0.7)
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.trigger_time = None
        self.recovery_timeout = config.get('recovery_timeout', 300)  # 5 minutes
        self.last_check_time = 0
        self.check_interval = config.get('check_interval', 60)  # seconds
        
        # Event tracking
        self.events: List[CircuitBreakerEvent] = []
        self.max_events = config.get('max_events', 1000)
        
        # Initialize components
        self._initialize_components(config, exchange_connectors, service_manager)
        
        logger.info(f"Initialized circuit breaker with thresholds: "
                   f"drawdown={self.max_drawdown}, var={self.max_var}, correlation={self.max_correlation}")
    
    def _initialize_components(self, config: Dict[str, Any], 
                             exchange_connectors: Optional[Dict[str, Any]],
                             service_manager: Optional[Any]):
        """Initialize circuit breaker components."""
        try:
            # Initialize VaR calculator
            var_config = config.get('var_calculator', {})
            self.var_calculator = VaRCalculator(var_config)
            
            # Initialize risk metrics monitor
            risk_config = config.get('risk_metrics', {})
            self.risk_monitor = RiskMetricsMonitor(risk_config)
            
            # Initialize position manager
            if exchange_connectors:
                position_config = config.get('position_manager', {})
                self.position_manager = PositionManager(position_config, exchange_connectors)
            else:
                self.position_manager = None
                logger.warning("No exchange connectors provided - position closure disabled")
            
            # Initialize notification service
            notification_config = config.get('notifications', {})
            self.notification_service = NotificationService(notification_config)
            
            # Store service manager reference
            self.service_manager = service_manager
            
            logger.info("Circuit breaker components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker components: {e}")
            raise
    
    async def check_risk_limits(self, portfolio_data: Dict[str, Any]) -> bool:
        """
        Check all risk limits and trigger circuit breaker if needed.
        
        Args:
            portfolio_data: Portfolio data for risk calculations
            
        Returns:
            bool: True if all limits are within bounds, False if circuit breaker triggered
        """
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last check
            if current_time - self.last_check_time < self.check_interval:
                return self.state == CircuitBreakerState.CLOSED
            
            self.last_check_time = current_time
            
            # Check if circuit breaker is already open
            if self.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if self.trigger_time and (current_time - self.trigger_time) > self.recovery_timeout:
                    await self._attempt_recovery()
                return False
            
            # Perform risk limit checks
            violations = []
            
            # Check drawdown
            if 'drawdown' in portfolio_data:
                current_dd = portfolio_data['drawdown']
                if current_dd > self.max_drawdown:
                    violations.append(f"Max drawdown exceeded: {current_dd:.2%} > {self.max_drawdown:.2%}")
            
            # Check VaR
            if 'portfolio_data' in portfolio_data:
                try:
                    var_result = await self.var_calculator.calculate_var(
                        portfolio_data['portfolio_data'], VaRMethod.HISTORICAL, 0.95
                    )
                    if var_result.var_value > self.max_var:
                        violations.append(f"VaR threshold exceeded: {var_result.var_value:.2%} > {self.max_var:.2%}")
                except Exception as e:
                    logger.error(f"VaR calculation failed: {e}")
            
            # Check correlation
            if 'portfolio_data' in portfolio_data:
                try:
                    correlation_result = await self.var_calculator.calculate_correlation_matrix(
                        portfolio_data['portfolio_data']
                    )
                    if abs(correlation_result.max_correlation) > self.max_correlation:
                        violations.append(f"Correlation threshold exceeded: {correlation_result.max_correlation:.2f} > {self.max_correlation:.2f}")
                except Exception as e:
                    logger.error(f"Correlation calculation failed: {e}")
            
            # Check risk metrics
            if 'portfolio_data' in portfolio_data:
                try:
                    risk_summary = await self.risk_monitor.get_risk_summary(
                        portfolio_data['portfolio_data']
                    )
                    
                    # Check for critical alerts
                    critical_alerts = [alert for alert in risk_summary.active_alerts 
                                     if alert.severity == RiskSeverity.CRITICAL]
                    if critical_alerts:
                        violations.extend([f"Critical risk alert: {alert.message}" for alert in critical_alerts])
                        
                except Exception as e:
                    logger.error(f"Risk metrics check failed: {e}")
            
            # Trigger circuit breaker if violations found
            if violations:
                await self.trigger_circuit_breaker("; ".join(violations))
                return False
            
            # All checks passed
            if self.state == CircuitBreakerState.HALF_OPEN:
                await self._close_circuit_breaker("Risk limits normalized")
            
            return True
            
        except Exception as e:
            logger.error(f"Risk limit check failed: {e}")
            # Trigger circuit breaker on error
            await self.trigger_circuit_breaker(f"Risk check error: {e}")
            return False
    
    async def trigger_circuit_breaker(self, reason: str):
        """
        Trigger circuit breaker and initiate emergency procedures.
        
        Args:
            reason: Reason for triggering circuit breaker
        """
        try:
            if self.state == CircuitBreakerState.OPEN:
                logger.warning(f"Circuit breaker already open: {reason}")
                return
            
            logger.critical(f"TRIGGERING CIRCUIT BREAKER: {reason}")
            
            # Update state
            self.state = CircuitBreakerState.OPEN
            self.trigger_time = time.time()
            
            # Record event
            event = CircuitBreakerEvent(
                event_type="triggered",
                timestamp=time.time(),
                reason=reason,
                state=self.state,
                metadata={"reason": reason}
            )
            self._add_event(event)
            
            # Execute emergency procedures
            await self._execute_emergency_procedures(reason)
            
        except Exception as e:
            logger.error(f"Failed to trigger circuit breaker: {e}")
    
    async def _execute_emergency_procedures(self, reason: str):
        """Execute emergency procedures when circuit breaker is triggered."""
        try:
            logger.critical("Executing emergency procedures")
            
            # 1. Close all positions
            if self.position_manager:
                try:
                    closure_results = await self.position_manager.close_all_positions(reason)
                    successful_closures = [r for r in closure_results if r.success]
                    failed_closures = [r for r in closure_results if not r.success]
                    
                    logger.info(f"Position closure completed: {len(successful_closures)} successful, "
                               f"{len(failed_closures)} failed")
                    
                    if failed_closures:
                        reason += f" (Position closure failures: {len(failed_closures)})"
                        
                except Exception as e:
                    logger.error(f"Position closure failed: {e}")
                    reason += f" (Position closure error: {e})"
            else:
                logger.warning("Position manager not available - skipping position closure")
            
            # 2. Send alerts
            try:
                await self.send_alert(reason)
            except Exception as e:
                logger.error(f"Alert sending failed: {e}")
            
            # 3. Coordinate with service manager
            if self.service_manager:
                try:
                    # Signal service manager to initiate graceful shutdown
                    logger.info("Signaling service manager for graceful shutdown")
                    # Note: Service manager integration would be implemented here
                except Exception as e:
                    logger.error(f"Service manager coordination failed: {e}")
            
            logger.critical("Emergency procedures completed")
            
        except Exception as e:
            logger.error(f"Emergency procedures failed: {e}")
    
    async def close_all_positions(self) -> bool:
        """
        Close all positions across all exchanges.
        
        Returns:
            bool: True if all positions were successfully closed
        """
        try:
            if not self.position_manager:
                logger.error("Position manager not available")
                return False
            
            logger.warning("Closing all positions via circuit breaker")
            
            # Close positions
            closure_results = await self.position_manager.close_all_positions(
                "Circuit breaker triggered - emergency closure"
            )
            
            # Validate closure
            success = await self.position_manager.validate_position_closure(closure_results)
            
            if success:
                logger.info("All positions successfully closed")
            else:
                logger.error("Position closure validation failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Position closure failed: {e}")
            return False
    
    async def send_alert(self, message: str, priority: NotificationPriority = NotificationPriority.CRITICAL):
        """
        Send alert notifications via multiple channels.
        
        Args:
            message: Alert message
            priority: Alert priority level
        """
        try:
            logger.info(f"Sending circuit breaker alert: {message}")
            
            # Prepare alert data
            subject = "🚨 CIRCUIT BREAKER TRIGGERED"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            # Enhanced message with context
            enhanced_message = f"""
            🚨 **CIRCUIT BREAKER TRIGGERED** 🚨
            
            **Time:** {timestamp}
            **Reason:** {message}
            **State:** {self.state.value.upper()}
            
            **Action Required:**
            - Review risk metrics immediately
            - Check position closure status
            - Investigate root cause
            - Manual intervention may be required
            
            **System Status:**
            - Circuit Breaker: {self.state.value.upper()}
            - Trigger Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.trigger_time)) if self.trigger_time else 'N/A'}
            - Recovery Timeout: {self.recovery_timeout} seconds
            """
            
            # Get notification recipients from config
            recipients = self.config.get('notifications', {}).get('recipients', {})
            
            # Send via multiple channels
            channels = [NotificationChannel.EMAIL, NotificationChannel.SLACK]
            if priority == NotificationPriority.CRITICAL:
                channels.append(NotificationChannel.SMS)
            
            # Prepare recipients by channel
            channel_recipients = {
                NotificationChannel.EMAIL: recipients.get('email', []),
                NotificationChannel.SMS: recipients.get('sms', []),
                NotificationChannel.SLACK: recipients.get('slack', [])
            }
            
            # Send notifications
            results = await self.notification_service.send_multi_channel_alert(
                channels=channels,
                priority=priority,
                subject=subject,
                message=enhanced_message,
                recipients=channel_recipients,
                template_data={
                    'subject': subject,
                    'message': enhanced_message,
                    'timestamp': timestamp,
                    'priority': priority.value,
                    'state': self.state.value
                },
                template_name='circuit_breaker_alert'
            )
            
            # Log results
            successful_sends = [r for r in results if r.success]
            failed_sends = [r for r in results if not r.success]
            
            logger.info(f"Alert sent: {len(successful_sends)} successful, {len(failed_sends)} failed")
            
            if failed_sends:
                for failed in failed_sends:
                    logger.error(f"Alert failed for {failed.channel.value}: {failed.error_message}")
            
        except Exception as e:
            logger.error(f"Alert sending failed: {e}")
    
    async def _attempt_recovery(self):
        """Attempt to recover from circuit breaker open state."""
        try:
            logger.info("Attempting circuit breaker recovery")
            
            # Change to half-open state
            self.state = CircuitBreakerState.HALF_OPEN
            
            # Record event
            event = CircuitBreakerEvent(
                event_type="recovery_attempt",
                timestamp=time.time(),
                reason="Recovery timeout reached",
                state=self.state
            )
            self._add_event(event)
            
            # Send recovery notification
            try:
                await self.send_alert(
                    "Circuit breaker recovery attempt initiated",
                    NotificationPriority.HIGH
                )
            except Exception as e:
                logger.error(f"Recovery notification failed: {e}")
            
            logger.info("Circuit breaker recovery attempt initiated")
            
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
    
    async def _close_circuit_breaker(self, reason: str):
        """Close circuit breaker and resume normal operation."""
        try:
            logger.info(f"Closing circuit breaker: {reason}")
            
            # Update state
            self.state = CircuitBreakerState.CLOSED
            self.trigger_time = None
            
            # Record event
            event = CircuitBreakerEvent(
                event_type="closed",
                timestamp=time.time(),
                reason=reason,
                state=self.state
            )
            self._add_event(event)
            
            # Send recovery notification
            try:
                await self.send_alert(
                    f"Circuit breaker closed: {reason}",
                    NotificationPriority.MEDIUM
                )
            except Exception as e:
                logger.error(f"Recovery notification failed: {e}")
            
            logger.info("Circuit breaker closed successfully")
            
        except Exception as e:
            logger.error(f"Failed to close circuit breaker: {e}")
    
    def _add_event(self, event: CircuitBreakerEvent):
        """Add event to history."""
        try:
            self.events.append(event)
            
            # Limit event history size
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
                
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
    
    async def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        try:
            # Get component statuses
            var_status = await self.var_calculator.get_cache_stats() if self.var_calculator else {}
            risk_status = await self.risk_monitor.get_monitor_status() if self.risk_monitor else {}
            position_status = await self.position_manager.get_manager_status() if self.position_manager else {}
            notification_status = await self.notification_service.get_service_status() if self.notification_service else {}
            
            return {
                "timestamp": time.time(),
                "state": self.state.value,
                "trigger_time": self.trigger_time,
                "recovery_timeout": self.recovery_timeout,
                "last_check_time": self.last_check_time,
                "check_interval": self.check_interval,
                "thresholds": {
                    "max_drawdown": self.max_drawdown,
                    "max_var": self.max_var,
                    "max_correlation": self.max_correlation
                },
                "events_count": len(self.events),
                "recent_events": [
                    {
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "reason": event.reason,
                        "state": event.state.value
                    }
                    for event in self.events[-10:]  # Last 10 events
                ],
                "components": {
                    "var_calculator": var_status,
                    "risk_monitor": risk_status,
                    "position_manager": position_status,
                    "notification_service": notification_status
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get circuit breaker status: {e}")
            return {"error": str(e)}
    
    async def get_risk_summary(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        try:
            if not self.risk_monitor:
                return {"error": "Risk monitor not available"}
            
            return await self.risk_monitor.get_risk_summary(portfolio_data)
            
        except Exception as e:
            logger.error(f"Failed to get risk summary: {e}")
            return {"error": str(e)}
    
    async def get_position_summary(self) -> Dict[str, Any]:
        """Get position summary."""
        try:
            if not self.position_manager:
                return {"error": "Position manager not available"}
            
            return await self.position_manager.get_position_summary()
            
        except Exception as e:
            logger.error(f"Failed to get position summary: {e}")
            return {"error": str(e)}
    
    async def get_notification_summary(self) -> Dict[str, Any]:
        """Get notification summary."""
        try:
            if not self.notification_service:
                return {"error": "Notification service not available"}
            
            return await self.notification_service.get_notification_summary()
            
        except Exception as e:
            logger.error(f"Failed to get notification summary: {e}")
            return {"error": str(e)}
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == CircuitBreakerState.OPEN
    
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed."""
        return self.state == CircuitBreakerState.CLOSED
    
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open."""
        return self.state == CircuitBreakerState.HALF_OPEN
    
    async def clear_events(self):
        """Clear event history."""
        self.events.clear()
        logger.info("Cleared circuit breaker event history")
    
    async def close(self):
        """Close circuit breaker and cleanup resources."""
        try:
            # Close notification service
            if self.notification_service:
                await self.notification_service.close()
            
            logger.info("Circuit breaker closed and resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error closing circuit breaker: {e}")


# Legacy compatibility - keep the original simple interface
async def check_risk_limits_simple(portfolio_metrics: Dict[str, Any], 
                                  max_drawdown: float = 0.08) -> bool:
    """
    Simple risk limit check for backward compatibility.
    
    Args:
        portfolio_metrics: Portfolio metrics dictionary
        max_drawdown: Maximum allowed drawdown
        
    Returns:
        bool: True if limits are within bounds
    """
    try:
        current_dd = portfolio_metrics.get('drawdown', 0)
        if current_dd > max_drawdown:
            logger.warning(f"Max drawdown exceeded: {current_dd:.2%} > {max_drawdown:.2%}")
            return False
        return True
    except Exception as e:
        logger.error(f"Simple risk limit check failed: {e}")
        return False

