#!/usr/bin/env python3
"""
Enhanced Monitoring and Metrics System for SMC Trading Agent

Provides comprehensive monitoring with:
- Prometheus metrics collection
- Grafana dashboard integration
- Real-time performance monitoring
- Health checks and alerts
- Distributed tracing
- Custom business metrics
"""

import time
import logging
import threading
import asyncio
import psutil
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import traceback

# Prometheus metrics
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        start_http_server, CollectorRegistry,
        push_to_gateway, CONTENT_TYPE_LATEST,
        generate_latest, MetricWrapperBase
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Install with: pip install prometheus_client")

# Grafana integration
try:
    import requests
    GRAFANA_AVAILABLE = True
except ImportError:
    GRAFANA_AVAILABLE = False
    logging.warning("Requests not available. Install with: pip install requests")

logger = logging.getLogger(__name__)


@dataclass
class MetricConfig:
    """Configuration for a metric"""
    name: str
    description: str
    metric_type: str  # counter, histogram, gauge, summary
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    percentiles: Optional[List[float]] = None  # For summaries


@dataclass
class AlertConfig:
    """Configuration for alerts"""
    name: str
    condition: str  # Metric expression
    threshold: float
    operator: str  # >, <, >=, <=, ==, !=
    severity: str  # critical, warning, info
    message: str
    cooldown: int = 300  # Cooldown in seconds
    enabled: bool = True


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_func: Callable[[], bool]
    timeout: int = 10
    critical: bool = True


class MetricRegistry:
    """Central metric registry with Prometheus integration"""

    def __init__(self, registry_name: str = "smc_trading_agent"):
        self.registry_name = registry_name
        self.metrics: Dict[str, MetricWrapperBase] = {}
        self.custom_metrics: Dict[str, Any] = {}

        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()
        else:
            self.registry = None
            logger.warning("Prometheus not available - using fallback metrics storage")

    def create_metric(self, config: MetricConfig) -> bool:
        """Create a new metric based on configuration"""
        try:
            if not PROMETHEUS_AVAILABLE:
                # Fallback storage
                self.custom_metrics[config.name] = {
                    'type': config.metric_type,
                    'value': 0.0,
                    'labels': {},
                    'description': config.description
                }
                return True

            if config.name in self.metrics:
                logger.warning(f"Metric {config.name} already exists")
                return False

            # Create metric based on type
            if config.metric_type == "counter":
                metric = Counter(
                    config.name,
                    config.description,
                    labelnames=config.labels,
                    registry=self.registry
                )
            elif config.metric_type == "histogram":
                metric = Histogram(
                    config.name,
                    config.description,
                    labelnames=config.labels,
                    buckets=config.buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                    registry=self.registry
                )
            elif config.metric_type == "gauge":
                metric = Gauge(
                    config.name,
                    config.description,
                    labelnames=config.labels,
                    registry=self.registry
                )
            elif config.metric_type == "summary":
                metric = Summary(
                    config.name,
                    config.description,
                    labelnames=config.labels,
                    registry=self.registry
                )
            else:
                logger.error(f"Unsupported metric type: {config.metric_type}")
                return False

            self.metrics[config.name] = metric
            logger.info(f"Created metric: {config.name} ({config.metric_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to create metric {config.name}: {e}")
            return False

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        if PROMETHEUS_AVAILABLE and name in self.metrics:
            metric = self.metrics[name]
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
        else:
            # Fallback storage
            if name in self.custom_metrics:
                self.custom_metrics[name]['value'] += value

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a histogram metric"""
        if PROMETHEUS_AVAILABLE and name in self.metrics:
            metric = self.metrics[name]
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
        else:
            # Fallback storage
            if name in self.custom_metrics:
                self.custom_metrics[name]['value'] = value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        if PROMETHEUS_AVAILABLE and name in self.metrics:
            metric = self.metrics[name]
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
        else:
            # Fallback storage
            if name in self.custom_metrics:
                self.custom_metrics[name]['value'] = value

    def get_metric_value(self, name: str) -> Optional[float]:
        """Get current value of a metric (fallback mode only)"""
        if not PROMETHEUS_AVAILABLE and name in self.custom_metrics:
            return self.custom_metrics[name]['value']
        return None

    def generate_metrics_output(self) -> str:
        """Generate metrics output for Prometheus"""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self.registry).decode('utf-8')
        else:
            # Fallback JSON output
            return json.dumps(self.custom_metrics, indent=2)


class SystemMonitor:
    """System resource monitoring"""

    def __init__(self, metric_registry: MetricRegistry):
        self.metric_registry = metric_registry
        self.monitoring = False
        self.monitor_thread = None
        self.interval = 30  # seconds

        # System metrics configuration
        self.system_metrics = [
            MetricConfig("system_cpu_usage", "CPU usage percentage", "gauge"),
            MetricConfig("system_memory_usage", "Memory usage percentage", "gauge"),
            MetricConfig("system_disk_usage", "Disk usage percentage", "gauge"),
            MetricConfig("system_network_bytes_sent", "Network bytes sent", "counter"),
            MetricConfig("system_network_bytes_recv", "Network bytes received", "counter"),
            MetricConfig("system_process_count", "Number of processes", "gauge"),
            MetricConfig("system_load_average", "System load average", "gauge")
        ]

        # Create metrics
        for metric_config in self.system_metrics:
            self.metric_registry.create_metric(metric_config)

    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(5)

    def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metric_registry.set_gauge("system_cpu_usage", cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.metric_registry.set_gauge("system_memory_usage", memory.percent)

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metric_registry.set_gauge("system_disk_usage", disk_percent)

            # Network I/O
            network = psutil.net_io_counters()
            self.metric_registry.increment_counter("system_network_bytes_sent", network.bytes_sent)
            self.metric_registry.increment_counter("system_network_bytes_recv", network.bytes_recv)

            # Process count
            process_count = len(psutil.pids())
            self.metric_registry.set_gauge("system_process_count", process_count)

            # Load average (Unix-like systems only)
            if hasattr(psutil, 'getloadavg'):
                load_avg = psutil.getloadavg()[0]  # 1-minute average
                self.metric_registry.set_gauge("system_load_average", load_avg)

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class BusinessMetricsCollector:
    """Business-specific metrics for trading system"""

    def __init__(self, metric_registry: MetricRegistry):
        self.metric_registry = metric_registry
        self.trade_history = deque(maxlen=1000)
        self.performance_history = deque(maxlen=100)

        # Trading metrics configuration
        self.trading_metrics = [
            MetricConfig("trades_total", "Total number of trades", "counter", ["symbol", "side"]),
            MetricConfig("trade_volume", "Total trading volume", "counter", ["symbol"]),
            MetricConfig("trade_pnl", "Trade P&L", "histogram", ["symbol"], [-1000, -100, -10, 0, 10, 100, 1000]),
            MetricConfig("trade_execution_time", "Trade execution time", "histogram", [], [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]),
            MetricConfig("position_size", "Current position size", "gauge", ["symbol"]),
            MetricConfig("portfolio_value", "Total portfolio value", "gauge"),
            MetricConfig("risk_score", "Current risk score", "gauge"),
            MetricConfig("signal_confidence", "Trading signal confidence", "histogram", [], [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]),
            MetricConfig("slippage", "Trade slippage", "histogram", [], [0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01]),
            MetricConfig("latency", "System latency", "histogram", ["component"], [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25])
        ]

        # Create metrics
        for metric_config in self.trading_metrics:
            self.metric_registry.create_metric(metric_config)

    def record_trade(self, symbol: str, side: str, quantity: float, price: float,
                     execution_time: float, pnl: float = 0.0, slippage: float = 0.0):
        """Record a trade execution"""
        try:
            # Update trade counters
            self.metric_registry.increment_counter(
                "trades_total",
                labels={"symbol": symbol, "side": side}
            )

            self.metric_registry.increment_counter(
                "trade_volume",
                quantity * price,
                labels={"symbol": symbol}
            )

            # Record execution metrics
            self.metric_registry.observe_histogram("trade_execution_time", execution_time)
            self.metric_registry.observe_histogram("trade_pnl", pnl, labels={"symbol": symbol})
            self.metric_registry.observe_histogram("slippage", slippage)

            # Store in history
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'execution_time': execution_time,
                'pnl': pnl,
                'slippage': slippage
            }
            self.trade_history.append(trade_record)

            logger.debug(f"Recorded trade: {symbol} {side} {quantity}@{price}")

        except Exception as e:
            logger.error(f"Error recording trade: {e}")

    def update_position(self, symbol: str, size: float):
        """Update position size"""
        try:
            self.metric_registry.set_gauge("position_size", size, labels={"symbol": symbol})
        except Exception as e:
            logger.error(f"Error updating position: {e}")

    def update_portfolio_value(self, value: float):
        """Update portfolio value"""
        try:
            self.metric_registry.set_gauge("portfolio_value", value)
        except Exception as e:
            logger.error(f"Error updating portfolio value: {e}")

    def update_risk_score(self, score: float):
        """Update risk score"""
        try:
            self.metric_registry.set_gauge("risk_score", score)
        except Exception as e:
            logger.error(f"Error updating risk score: {e}")

    def record_signal_confidence(self, confidence: float):
        """Record trading signal confidence"""
        try:
            self.metric_registry.observe_histogram("signal_confidence", confidence)
        except Exception as e:
            logger.error(f"Error recording signal confidence: {e}")

    def record_latency(self, component: str, latency: float):
        """Record system latency for a component"""
        try:
            self.metric_registry.observe_histogram("latency", latency, labels={"component": component})
        except Exception as e:
            logger.error(f"Error recording latency: {e}")

    def get_trading_summary(self) -> Dict[str, Any]:
        """Get summary of trading metrics"""
        if not self.trade_history:
            return {}

        recent_trades = list(self.trade_history)[-100:]  # Last 100 trades

        total_trades = len(recent_trades)
        profitable_trades = len([t for t in recent_trades if t['pnl'] > 0])
        total_pnl = sum(t['pnl'] for t in recent_trades)
        avg_execution_time = sum(t['execution_time'] for t in recent_trades) / total_trades
        avg_slippage = sum(t['slippage'] for t in recent_trades) / total_trades

        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': profitable_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_execution_time': avg_execution_time,
            'avg_slippage': avg_slippage,
            'last_trade_time': recent_trades[-1]['timestamp'] if recent_trades else None
        }


class AlertManager:
    """Alert management system"""

    def __init__(self, metric_registry: MetricRegistry):
        self.metric_registry = metric_registry
        self.alerts: Dict[str, AlertConfig] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_callbacks: List[Callable] = []

        # Create alert metrics
        alert_metrics = [
            MetricConfig("alerts_total", "Total number of alerts", "counter", ["severity", "alert_name"]),
            MetricConfig("alert_cooldown_active", "Number of alerts in cooldown", "gauge")
        ]

        for metric_config in alert_metrics:
            self.metric_registry.create_metric(metric_config)

    def add_alert(self, alert_config: AlertConfig):
        """Add a new alert configuration"""
        self.alerts[alert_config.name] = alert_config
        logger.info(f"Added alert: {alert_config.name}")

    def remove_alert(self, name: str):
        """Remove an alert configuration"""
        if name in self.alerts:
            del self.alerts[name]
            logger.info(f"Removed alert: {name}")

    def check_alerts(self):
        """Check all alert conditions"""
        current_time = datetime.now()

        for alert_name, alert_config in self.alerts.items():
            if not alert_config.enabled:
                continue

            # Check cooldown
            if alert_name in self.alert_cooldowns:
                if (current_time - self.alert_cooldowns[alert_name]).total_seconds() < alert_config.cooldown:
                    continue
                else:
                    del self.alert_cooldowns[alert_name]

            try:
                triggered = self._evaluate_alert_condition(alert_config)
                if triggered:
                    self._trigger_alert(alert_config, current_time)
            except Exception as e:
                logger.error(f"Error checking alert {alert_name}: {e}")

    def _evaluate_alert_condition(self, alert_config: AlertConfig) -> bool:
        """Evaluate alert condition (simplified implementation)"""
        # This is a simplified implementation
        # In production, you'd want to use PromQL or similar query language

        # For now, just check if a metric exceeds threshold
        metric_name = alert_config.condition
        current_value = self.metric_registry.get_metric_value(metric_name)

        if current_value is None:
            return False

        if alert_config.operator == ">":
            return current_value > alert_config.threshold
        elif alert_config.operator == "<":
            return current_value < alert_config.threshold
        elif alert_config.operator == ">=":
            return current_value >= alert_config.threshold
        elif alert_config.operator == "<=":
            return current_value <= alert_config.threshold
        elif alert_config.operator == "==":
            return current_value == alert_config.threshold
        else:
            logger.warning(f"Unsupported operator: {alert_config.operator}")
            return False

    def _trigger_alert(self, alert_config: AlertConfig, timestamp: datetime):
        """Trigger an alert"""
        alert_record = {
            'name': alert_config.name,
            'severity': alert_config.severity,
            'message': alert_config.message,
            'timestamp': timestamp,
            'condition': alert_config.condition,
            'threshold': alert_config.threshold
        }

        self.alert_history.append(alert_record)
        self.alert_cooldowns[alert_config.name] = timestamp

        # Update metrics
        self.metric_registry.increment_counter(
            "alerts_total",
            labels={"severity": alert_config.severity, "alert_name": alert_config.name}
        )

        # Log alert
        log_level = {
            'critical': logging.ERROR,
            'warning': logging.WARNING,
            'info': logging.INFO
        }.get(alert_config.severity, logging.INFO)

        logger.log(log_level, f"ALERT: {alert_config.message}")

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_record)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def add_alert_callback(self, callback: Callable):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts (recent ones)"""
        current_time = datetime.now()
        active_alerts = []

        for alert in self.alert_history:
            # Consider alerts from last hour as "active"
            if (current_time - alert['timestamp']).total_seconds() < 3600:
                active_alerts.append(alert)

        return active_alerts


class HealthChecker:
    """Health check system"""

    def __init__(self, metric_registry: MetricRegistry):
        self.metric_registry = metric_registry
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}

        # Create health metrics
        health_metrics = [
            MetricConfig("health_check_status", "Health check status", "gauge", ["check_name"]),
            MetricConfig("health_check_duration", "Health check duration", "histogram", ["check_name"]),
            MetricConfig("health_checks_total", "Total health checks", "counter", ["status", "check_name"])
        ]

        for metric_config in health_metrics:
            self.metric_registry.create_metric(metric_config)

    def add_health_check(self, health_check: HealthCheck):
        """Add a health check"""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")

    def remove_health_check(self, name: str):
        """Remove a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Removed health check: {name}")

    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'overall_status': 'healthy',
            'timestamp': datetime.now(),
            'checks': {}
        }

        overall_healthy = True

        for check_name, health_check in self.health_checks.items():
            start_time = time.time()
            status = False
            error = None

            try:
                # Run health check with timeout
                if asyncio.iscoroutinefunction(health_check.check_func):
                    # Async health check
                    status = asyncio.run(health_check.check_func())
                else:
                    # Sync health check
                    status = health_check.check_func()

            except Exception as e:
                error = str(e)
                status = False
                logger.error(f"Health check {check_name} failed: {e}")

            duration = time.time() - start_time

            # Store result
            check_result = {
                'status': 'healthy' if status else 'unhealthy',
                'duration': duration,
                'error': error,
                'critical': health_check.critical,
                'timestamp': datetime.now()
            }

            results['checks'][check_name] = check_result
            self.last_check_results[check_name] = check_result

            # Update metrics
            self.metric_registry.set_gauge(
                "health_check_status",
                1 if status else 0,
                labels={"check_name": check_name}
            )
            self.metric_registry.observe_histogram(
                "health_check_duration",
                duration,
                labels={"check_name": check_name}
            )
            self.metric_registry.increment_counter(
                "health_checks_total",
                labels={"status": "healthy" if status else "unhealthy", "check_name": check_name}
            )

            # Update overall status
            if not status and health_check.critical:
                overall_healthy = False

        results['overall_status'] = 'healthy' if overall_healthy else 'unhealthy'

        return results

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        if not self.last_check_results:
            return self.run_health_checks()

        critical_failures = [
            name for name, result in self.last_check_results.items()
            if not result['status'] == 'healthy' and result['critical']
        ]

        all_healthy = all(
            result['status'] == 'healthy' for result in self.last_check_results.values()
        )

        return {
            'overall_status': 'healthy' if all_healthy else 'unhealthy',
            'critical_failures': critical_failures,
            'last_check_time': max(
                result['timestamp'] for result in self.last_check_results.values()
            ),
            'total_checks': len(self.last_check_results),
            'healthy_checks': len([
                r for r in self.last_check_results.values() if r['status'] == 'healthy'
            ])
        }


class EnhancedMonitoringSystem:
    """Main enhanced monitoring system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False

        # Initialize components
        self.metric_registry = MetricRegistry()
        self.system_monitor = SystemMonitor(self.metric_registry)
        self.business_metrics = BusinessMetricsCollector(self.metric_registry)
        self.alert_manager = AlertManager(self.metric_registry)
        self.health_checker = HealthChecker(self.metric_registry)

        # Monitoring thread
        self.monitor_thread = None
        self.monitor_interval = config.get('metrics_collection_interval', 60)

        # HTTP server for Prometheus metrics
        self.prometheus_port = config.get('prometheus_port', 8000)
        self.http_server = None

        # Setup default alerts and health checks
        self._setup_default_alerts()
        self._setup_default_health_checks()

    def _setup_default_alerts(self):
        """Setup default alert configurations"""
        default_alerts = [
            AlertConfig(
                name="high_cpu_usage",
                condition="system_cpu_usage",
                threshold=80.0,
                operator=">",
                severity="warning",
                message="High CPU usage detected: {:.1f}%",
                cooldown=300
            ),
            AlertConfig(
                name="high_memory_usage",
                condition="system_memory_usage",
                threshold=85.0,
                operator=">",
                severity="warning",
                message="High memory usage detected: {:.1f}%",
                cooldown=300
            ),
            AlertConfig(
                name="low_portfolio_value",
                condition="portfolio_value",
                threshold=10000.0,
                operator="<",
                severity="critical",
                message="Portfolio value below threshold: ${:.2f}",
                cooldown=600
            ),
            AlertConfig(
                name="high_risk_score",
                condition="risk_score",
                threshold=0.8,
                operator=">",
                severity="warning",
                message="High risk score detected: {:.2f}",
                cooldown=180
            ),
            AlertConfig(
                name="slow_execution",
                condition="trade_execution_time",
                threshold=1.0,
                operator=">",
                severity="warning",
                message="Slow trade execution detected: {:.3f}s",
                cooldown=120
            )
        ]

        for alert in default_alerts:
            self.alert_manager.add_alert(alert)

    def _setup_default_health_checks(self):
        """Setup default health checks"""
        def check_database_connection():
            # Mock database health check
            return True

        def check_redis_connection():
            # Mock Redis health check
            return True

        def check_exchange_connectivity():
            # Mock exchange connectivity check
            return True

        def check_system_resources():
            # Check if system resources are adequate
            cpu_ok = psutil.cpu_percent() < 90
            memory_ok = psutil.virtual_memory().percent < 90
            return cpu_ok and memory_ok

        default_checks = [
            HealthCheck("database", check_database_connection, critical=True),
            HealthCheck("redis", check_redis_connection, critical=True),
            HealthCheck("exchanges", check_exchange_connectivity, critical=True),
            HealthCheck("system_resources", check_system_resources, critical=True)
        ]

        for check in default_checks:
            self.health_checker.add_health_check(check)

    def start(self):
        """Start the monitoring system"""
        if self.running:
            logger.warning("Monitoring system already running")
            return

        try:
            # Start system monitoring
            self.system_monitor.start_monitoring()

            # Start Prometheus HTTP server
            if PROMETHEUS_AVAILABLE:
                start_http_server(self.prometheus_port, registry=self.metric_registry.registry)
                logger.info(f"Prometheus metrics server started on port {self.prometheus_port}")

            # Start main monitoring loop
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()

            logger.info("Enhanced monitoring system started successfully")

        except Exception as e:
            logger.error(f"Failed to start monitoring system: {e}")
            self.stop()

    def stop(self):
        """Stop the monitoring system"""
        self.running = False

        # Stop system monitoring
        self.system_monitor.stop_monitoring()

        # Stop monitoring thread
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Enhanced monitoring system stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Check alerts
                self.alert_manager.check_alerts()

                # Run health checks periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    self.health_checker.run_health_checks()

                time.sleep(self.monitor_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    # Business metrics methods
    def record_trade(self, symbol: str, side: str, quantity: float, price: float,
                     execution_time: float, pnl: float = 0.0, slippage: float = 0.0):
        """Record a trade execution"""
        self.business_metrics.record_trade(symbol, side, quantity, price, execution_time, pnl, slippage)

    def update_portfolio_value(self, value: float):
        """Update portfolio value"""
        self.business_metrics.update_portfolio_value(value)

    def update_risk_score(self, score: float):
        """Update risk score"""
        self.business_metrics.update_risk_score(score)

    def record_latency(self, component: str, latency: float):
        """Record system latency"""
        self.business_metrics.record_latency(component, latency)

    # Health and status methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self.health_checker.get_system_health()

    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading metrics summary"""
        return self.business_metrics.get_trading_summary()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return self.alert_manager.get_active_alerts()

    def get_metrics_output(self) -> str:
        """Get metrics output for Prometheus"""
        return self.metric_registry.generate_metrics_output()


# Decorator for measuring function performance
def monitor_performance(component_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Record latency if monitoring system is available
                try:
                    from .enhanced_monitoring import get_monitoring_system
                    monitoring = get_monitoring_system()
                    if monitoring:
                        monitoring.record_latency(
                            component_name or func.__name__,
                            execution_time
                        )
                except ImportError:
                    pass

                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
                raise

        return wrapper
    return decorator


# Global monitoring system instance
_monitoring_system: Optional[EnhancedMonitoringSystem] = None


def get_monitoring_system() -> Optional[EnhancedMonitoringSystem]:
    """Get global monitoring system instance"""
    return _monitoring_system


def initialize_monitoring(config: Dict[str, Any]) -> EnhancedMonitoringSystem:
    """Initialize global monitoring system"""
    global _monitoring_system
    _monitoring_system = EnhancedMonitoringSystem(config)
    return _monitoring_system


if __name__ == "__main__":
    # Example usage
    config = {
        'metrics_collection_interval': 30,
        'prometheus_port': 8000
    }

    monitoring = initialize_monitoring(config)
    monitoring.start()

    try:
        # Record some example metrics
        monitoring.record_trade("BTC/USDT", "buy", 1.0, 50000.0, 0.05, 100.0, 0.001)
        monitoring.update_portfolio_value(10100.0)
        monitoring.update_risk_score(0.3)
        monitoring.record_latency("smc_detector", 0.025)

        # Print health status
        health = monitoring.get_health_status()
        print(f"System Health: {health}")

        # Print trading summary
        summary = monitoring.get_trading_summary()
        print(f"Trading Summary: {summary}")

        # Keep running
        time.sleep(60)

    finally:
        monitoring.stop()