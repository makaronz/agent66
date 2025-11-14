"""
Comprehensive audit logging system for Python backend
Provides structured logging for security events and compliance
"""

import json
import logging
import os
import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from hashlib import sha256
import structlog
from structlog.processors import JSONRenderer
import aiofiles
import aiofiles.os


class AuditEventType(str, Enum):
    """Audit event types for security and compliance tracking"""
    
    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    TOKEN_REVOKE = "TOKEN_REVOKE"
    
    # Trading events
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_FAILED = "ORDER_FAILED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    
    # Risk management events
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    STOP_LOSS_TRIGGERED = "STOP_LOSS_TRIGGERED"
    TAKE_PROFIT_TRIGGERED = "TAKE_PROFIT_TRIGGERED"
    DRAWDOWN_LIMIT_REACHED = "DRAWDOWN_LIMIT_REACHED"
    
    # Data events
    MARKET_DATA_RECEIVED = "MARKET_DATA_RECEIVED"
    DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"
    DATA_PIPELINE_ERROR = "DATA_PIPELINE_ERROR"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_DELETION = "DATA_DELETION"
    
    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    CONFIGURATION_CHANGED = "CONFIGURATION_CHANGED"
    MODEL_RETRAINED = "MODEL_RETRAINED"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    
    # Security events
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    API_KEY_COMPROMISED = "API_KEY_COMPROMISED"
    SECURITY_SCAN_FAILED = "SECURITY_SCAN_FAILED"
    
    # Compliance events
    GDPR_REQUEST = "GDPR_REQUEST"
    AUDIT_TRAIL_ACCESS = "AUDIT_TRAIL_ACCESS"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    REGULATORY_REPORT = "REGULATORY_REPORT"


@dataclass
class AuditLogEntry:
    """Structured audit log entry"""
    id: str
    timestamp: str
    event_type: AuditEventType
    severity: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component: str  # trading_engine, execution_engine, data_pipeline, etc.
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    outcome: str = "SUCCESS"  # SUCCESS, FAILURE, PARTIAL
    risk_score: int = 1  # 1-10 scale
    details: Dict[str, Any] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None
    compliance_tags: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.compliance_tags is None:
            self.compliance_tags = []


class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(
        self,
        log_dir: str = "./logs/audit",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 2555,  # 7 years
        enable_console: bool = True,
        enable_file: bool = True,
        enable_remote: bool = False,
        remote_endpoint: Optional[str] = None
    ):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_remote = enable_remote
        self.remote_endpoint = remote_endpoint
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structured logging
        self._setup_logging()
        
        # Risk scoring configuration
        self.risk_scores = {
            AuditEventType.LOGIN_SUCCESS: 1,
            AuditEventType.LOGIN_FAILURE: 5,
            AuditEventType.LOGOUT: 1,
            AuditEventType.TOKEN_REFRESH: 1,
            AuditEventType.TOKEN_REVOKE: 3,
            
            AuditEventType.SIGNAL_GENERATED: 2,
            AuditEventType.ORDER_PLACED: 4,
            AuditEventType.ORDER_FILLED: 3,
            AuditEventType.ORDER_CANCELLED: 2,
            AuditEventType.ORDER_FAILED: 6,
            AuditEventType.POSITION_OPENED: 4,
            AuditEventType.POSITION_CLOSED: 3,
            
            AuditEventType.RISK_LIMIT_EXCEEDED: 8,
            AuditEventType.CIRCUIT_BREAKER_TRIGGERED: 9,
            AuditEventType.STOP_LOSS_TRIGGERED: 5,
            AuditEventType.TAKE_PROFIT_TRIGGERED: 3,
            AuditEventType.DRAWDOWN_LIMIT_REACHED: 9,
            
            AuditEventType.MARKET_DATA_RECEIVED: 1,
            AuditEventType.DATA_QUALITY_ISSUE: 6,
            AuditEventType.DATA_PIPELINE_ERROR: 7,
            AuditEventType.DATA_EXPORT: 5,
            AuditEventType.DATA_DELETION: 8,
            
            AuditEventType.SYSTEM_STARTUP: 2,
            AuditEventType.SYSTEM_SHUTDOWN: 2,
            AuditEventType.CONFIGURATION_CHANGED: 4,
            AuditEventType.MODEL_RETRAINED: 3,
            AuditEventType.PERFORMANCE_DEGRADATION: 6,
            
            AuditEventType.UNAUTHORIZED_ACCESS: 10,
            AuditEventType.SUSPICIOUS_ACTIVITY: 8,
            AuditEventType.RATE_LIMIT_EXCEEDED: 5,
            AuditEventType.API_KEY_COMPROMISED: 10,
            AuditEventType.SECURITY_SCAN_FAILED: 7,
            
            AuditEventType.GDPR_REQUEST: 4,
            AuditEventType.AUDIT_TRAIL_ACCESS: 6,
            AuditEventType.COMPLIANCE_VIOLATION: 9,
            AuditEventType.REGULATORY_REPORT: 3
        }
    
    def _setup_logging(self):
        """Configure structured logging with JSON output"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=None if not self.enable_console else None,
            level=logging.INFO,
        )
        
        self.logger = structlog.get_logger("audit")
    
    def _generate_id(self) -> str:
        """Generate unique audit log entry ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        random_data = os.urandom(16).hex()
        return sha256(f"{timestamp}-{random_data}".encode()).hexdigest()[:16]
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data for logging"""
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = {
                'password', 'secret', 'token', 'key', 'api_key', 'api_secret',
                'private_key', 'access_token', 'refresh_token', 'authorization'
            }
            
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
    
    async def log_event(
        self,
        event_type: AuditEventType,
        component: str,
        severity: str = "INFO",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        outcome: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
        compliance_tags: Optional[List[str]] = None
    ) -> str:
        """Log an audit event"""
        
        entry = AuditLogEntry(
            id=self._generate_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            component=component,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            outcome=outcome,
            risk_score=self.risk_scores.get(event_type, 5),
            details=self._sanitize_data(details or {}),
            error_message=error_message,
            stack_trace=stack_trace,
            performance_metrics=performance_metrics,
            compliance_tags=compliance_tags or []
        )
        
        # Write to structured log
        log_data = asdict(entry)
        
        if self.enable_console:
            self.logger.info("audit_event", **log_data)
        
        if self.enable_file:
            await self._write_to_file(entry)
        
        if self.enable_remote and self.remote_endpoint:
            await self._send_to_remote(entry)
        
        # Send alerts for high-risk events
        if entry.risk_score >= 8:
            await self._send_security_alert(entry)
        
        return entry.id
    
    async def _write_to_file(self, entry: AuditLogEntry):
        """Write audit entry to file"""
        try:
            log_file = self.log_dir / f"audit-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
            
            # Check file size and rotate if necessary
            if log_file.exists():
                stat = await aiofiles.os.stat(log_file)
                if stat.st_size > self.max_file_size:
                    await self._rotate_log_file(log_file)
            
            # Write log entry
            async with aiofiles.open(log_file, 'a', encoding='utf-8') as f:
                await f.write(json.dumps(asdict(entry), default=str) + '\n')
                
        except Exception as e:
            # Don't let logging failures break the application
            print(f"Failed to write audit log: {e}")
    
    async def _rotate_log_file(self, log_file: Path):
        """Rotate log file when it gets too large"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            rotated_file = log_file.with_name(f"{log_file.stem}-{timestamp}.jsonl")
            await aiofiles.os.rename(log_file, rotated_file)
        except Exception as e:
            print(f"Failed to rotate log file: {e}")
    
    async def _send_to_remote(self, entry: AuditLogEntry):
        """Send audit entry to remote logging service"""
        # TODO: Implement remote logging (e.g., to ELK stack, Splunk, etc.)
        pass
    
    async def _send_security_alert(self, entry: AuditLogEntry):
        """Send security alert for high-risk events"""
        alert_data = {
            'event_type': entry.event_type,
            'severity': entry.severity,
            'risk_score': entry.risk_score,
            'component': entry.component,
            'user_id': entry.user_id,
            'ip_address': entry.ip_address,
            'timestamp': entry.timestamp,
            'details': entry.details
        }
        
        print(f"🚨 HIGH RISK SECURITY EVENT: {json.dumps(alert_data, indent=2)}")
        
        # TODO: Implement actual alerting
        # - Send to Slack webhook
        # - Send to PagerDuty
        # - Send email to security team
        # - Store in security incident database
    
    async def cleanup_old_logs(self):
        """Clean up old audit logs based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for log_file in self.log_dir.glob("audit-*.jsonl"):
                stat = await aiofiles.os.stat(log_file)
                file_date = datetime.fromtimestamp(stat.st_mtime)
                
                if file_date < cutoff_date:
                    await aiofiles.os.remove(log_file)
                    print(f"Deleted old audit log: {log_file.name}")
                    
        except Exception as e:
            print(f"Failed to cleanup old audit logs: {e}")
    
    async def search_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        component: Optional[str] = None,
        severity: Optional[str] = None,
        min_risk_score: Optional[int] = None
    ) -> List[AuditLogEntry]:
        """Search audit logs with filters"""
        results = []
        
        try:
            for log_file in self.log_dir.glob("audit-*.jsonl"):
                async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                    async for line in f:
                        try:
                            data = json.loads(line.strip())
                            entry_date = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                            
                            # Date filter
                            if entry_date < start_date or entry_date > end_date:
                                continue
                            
                            # Event type filter
                            if event_types and data['event_type'] not in [et.value for et in event_types]:
                                continue
                            
                            # User ID filter
                            if user_id and data.get('user_id') != user_id:
                                continue
                            
                            # Component filter
                            if component and data.get('component') != component:
                                continue
                            
                            # Severity filter
                            if severity and data.get('severity') != severity:
                                continue
                            
                            # Risk score filter
                            if min_risk_score and data.get('risk_score', 0) < min_risk_score:
                                continue
                            
                            results.append(AuditLogEntry(**data))
                            
                        except (json.JSONDecodeError, TypeError) as e:
                            print(f"Failed to parse audit log line: {e}")
                            continue
                            
        except Exception as e:
            print(f"Failed to search audit logs: {e}")
        
        return sorted(results, key=lambda x: x.timestamp, reverse=True)


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions for common audit events
class AuditAuth:
    @staticmethod
    async def login_success(user_id: str, ip_address: str, session_id: str):
        return await audit_logger.log_event(
            AuditEventType.LOGIN_SUCCESS,
            "authentication",
            user_id=user_id,
            ip_address=ip_address,
            session_id=session_id
        )
    
    @staticmethod
    async def login_failure(ip_address: str, reason: str, attempted_user: str = None):
        return await audit_logger.log_event(
            AuditEventType.LOGIN_FAILURE,
            "authentication",
            severity="WARNING",
            ip_address=ip_address,
            outcome="FAILURE",
            details={"failure_reason": reason, "attempted_user": attempted_user}
        )


class AuditTrading:
    @staticmethod
    async def signal_generated(signal_data: Dict[str, Any], user_id: str = None):
        return await audit_logger.log_event(
            AuditEventType.SIGNAL_GENERATED,
            "trading_engine",
            user_id=user_id,
            resource_type="signal",
            details=signal_data
        )
    
    @staticmethod
    async def order_placed(order_data: Dict[str, Any], user_id: str = None):
        return await audit_logger.log_event(
            AuditEventType.ORDER_PLACED,
            "execution_engine",
            user_id=user_id,
            resource_id=order_data.get("order_id"),
            resource_type="order",
            details=order_data
        )
    
    @staticmethod
    async def risk_limit_exceeded(limit_type: str, current_value: float, limit_value: float, user_id: str = None):
        return await audit_logger.log_event(
            AuditEventType.RISK_LIMIT_EXCEEDED,
            "risk_manager",
            severity="ERROR",
            user_id=user_id,
            outcome="FAILURE",
            details={
                "limit_type": limit_type,
                "current_value": current_value,
                "limit_value": limit_value
            }
        )


class AuditSecurity:
    @staticmethod
    async def unauthorized_access(ip_address: str, endpoint: str, user_id: str = None):
        return await audit_logger.log_event(
            AuditEventType.UNAUTHORIZED_ACCESS,
            "security",
            severity="CRITICAL",
            user_id=user_id,
            ip_address=ip_address,
            outcome="FAILURE",
            details={"endpoint": endpoint}
        )
    
    @staticmethod
    async def suspicious_activity(activity_type: str, details: Dict[str, Any], ip_address: str = None, user_id: str = None):
        return await audit_logger.log_event(
            AuditEventType.SUSPICIOUS_ACTIVITY,
            "security",
            severity="WARNING",
            user_id=user_id,
            ip_address=ip_address,
            details={"activity_type": activity_type, **details}
        )


# Schedule log cleanup (run daily)
async def schedule_log_cleanup():
    """Schedule daily log cleanup"""
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 hours
        await audit_logger.cleanup_old_logs()


# Start cleanup scheduler
asyncio.create_task(schedule_log_cleanup())