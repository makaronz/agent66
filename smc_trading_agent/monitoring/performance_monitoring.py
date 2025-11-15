"""
Comprehensive Performance Monitoring for SMC Trading Agent

Real-time monitoring of all system components with:
- Prometheus metrics
- Grafana dashboard integration
- Alerting for performance degradation
- Latency tracking across all components
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta
import psutil
import threading

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, push_to_gateway
import aiohttp
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """System components being monitored."""
    DATA_PIPELINE = "data_pipeline"
    ML_ENSEMBLE = "ml_ensemble"
    EXECUTION_ENGINE = "execution_engine"
    RISK_MANAGER = "risk_manager"
    CIRCUIT_BREAKER = "circuit_breaker"
    DATABASE = "database"
    KAFKA_PRODUCER = "kafka_producer"
    ORDER_ROUTER = "order_router"


@dataclass
class PerformanceThresholds:
    """Performance thresholds for alerting."""
    max_latency_ms: float = 50.0  # Target latency
    warning_latency_ms: float = 30.0
    max_error_rate: float = 0.05  # 5%
    max_cpu_usage: float = 0.80   # 80%
    max_memory_usage: float = 0.85  # 85%
    min_cache_hit_rate: float = 0.70  # 70%
    max_queue_size: int = 1000


class ComponentMetrics:
    """Metrics collector for a specific component."""
    
    def __init__(self, component_type: ComponentType, registry: CollectorRegistry):
        self.component_type = component_type
        self.registry = registry
        
        # Latency metrics
        self.latency_histogram = Histogram(
            f'smc_{component_type.value}_latency_seconds',
            f'Latency for {component_type.value}',
            ['operation'],
            registry=registry
        )
        
        # Throughput metrics
        self.requests_total = Counter(
            f'smc_{component_type.value}_requests_total',
            f'Total requests for {component_type.value}',
            ['operation', 'status'],
            registry=registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            f'smc_{component_type.value}_errors_total',
            f'Total errors for {component_type.value}',
            ['error_type'],
            registry=registry
        )
        
        # Performance gauges
        self.active_connections = Gauge(
            f'smc_{component_type.value}_active_connections',
            f'Active connections for {component_type.value}',
            registry=registry
        )
        
        self.queue_size = Gauge(
            f'smc_{component_type.value}_queue_size',
            f'Queue size for {component_type.value}',
            registry=registry
        )
        
        self.cache_hit_rate = Gauge(
            f'smc_{component_type.value}_cache_hit_rate',
            f'Cache hit rate for {component_type.value}',
            registry=registry
        )
        
        # Component-specific metrics
        self.custom_metrics = {}
        
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency."""
        self.latency_histogram.labels(operation=operation).observe(latency_ms / 1000)
        
    def record_request(self, operation: str, status: str = 'success') -> None:
        """Record a request."""
        self.requests_total.labels(operation=operation, status=status).inc()
        
    def record_error(self, error_type: str) -> None:
        """Record an error."""
        self.errors_total.labels(error_type=error_type).inc()
        self.requests_total.labels(operation='unknown', status='error').inc()
        
    def set_active_connections(self, count: int) -> None:
        """Set active connections count."""
        self.active_connections.set(count)
        
    def set_queue_size(self, size: int) -> None:
        """Set queue size."""
        self.queue_size.set(size)
        
    def set_cache_hit_rate(self, rate: float) -> None:
        """Set cache hit rate."""
        self.cache_hit_rate.set(rate)
        
    def add_custom_metric(self, name: str, metric_type: str, **kwargs) -> None:
        """Add custom metric."""
        if name not in self.custom_metrics:
            if metric_type == 'gauge':
                self.custom_metrics[name] = Gauge(
                    f'smc_{self.component_type.value}_{name}',
                    kwargs.get('description', ''),
                    registry=self.registry
                )


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Features:
    - Real-time metrics collection
    - Performance threshold monitoring
    - Automatic alerting
    - Historical data analysis
    - Health status reporting
    """
    
    def __init__(
        self,
        thresholds: PerformanceThresholds = None,
        prometheus_gateway: str = "localhost:9091",
        redis_url: str = "redis://localhost:6379"
    ):
        self.thresholds = thresholds or PerformanceThresholds()
        self.prometheus_gateway = prometheus_gateway
        self.redis_url = redis_url
        
        # Prometheus registry
        self.registry = CollectorRegistry()
        
        # System-wide metrics
        self.system_metrics = {
            'cpu_usage': Gauge('smc_system_cpu_usage', 'System CPU usage', registry=self.registry),
            'memory_usage': Gauge('smc_system_memory_usage', 'System memory usage', registry=self.registry),
            'disk_usage': Gauge('smc_system_disk_usage', 'System disk usage', registry=self.registry),
            'network_io': Gauge('smc_system_network_io', 'System network I/O', registry=self.registry)
        }
        
        # Component metrics
        self.component_metrics = {}
        
        # Alert state
        self.alerts = {}
        self.alert_callbacks = []
        
        # Monitoring state
        self.is_running = False
        self.monitor_task = None
        self.redis_client = None
        
        # Performance history
        self.performance_history = {}
        self.max_history_size = 1000
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize metrics for all components."""
        for component_type in ComponentType:
            self.component_metrics[component_type] = ComponentMetrics(component_type, self.registry)
            
    async def initialize(self) -> None:
        """Initialize monitoring system."""
        try:
            # Connect to Redis for distributed metrics
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Start background monitoring
            await self.start_monitoring()
            
            logger.info("Performance Monitor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize performance monitor: {e}")
            raise
            
    async def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Performance monitoring started")
        
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self.is_running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Performance monitoring stopped")
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Check performance thresholds
                await self._check_thresholds()
                
                # Push metrics to Prometheus
                await self._push_metrics()
                
                # Store performance history
                await self._store_performance_history()
                
                # Sleep between iterations
                await asyncio.sleep(5)  # 5 second monitoring interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # Wait before retrying
                
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_metrics['cpu_usage'].set(cpu_percent / 100)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_metrics['memory_usage'].set(memory.percent / 100)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.system_metrics['disk_usage'].set(disk_percent / 100)
            
            # Network I/O
            network = psutil.net_io_counters()
            if network:
                bytes_sent = network.bytes_sent
                bytes_recv = network.bytes_recv
                # Store as a combined metric (simplified)
                self.system_metrics['network_io'].set((bytes_sent + bytes_recv) / 1e9)  # GB
                
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            
    async def _check_thresholds(self) -> None:
        """Check performance thresholds and trigger alerts."""
        current_time = time.time()
        
        # Check system thresholds
        try:
            # CPU usage
            cpu_usage = self.system_metrics['cpu_usage']._value._value
            if cpu_usage > self.thresholds.max_cpu_usage:
                await self._trigger_alert('high_cpu', f'High CPU usage: {cpu_usage:.1%}')
                
            # Memory usage
            memory_usage = self.system_metrics['memory_usage']._value._value
            if memory_usage > self.thresholds.max_memory_usage:
                await self._trigger_alert('high_memory', f'High memory usage: {memory_usage:.1%}')
                
        except Exception as e:
            logger.warning(f"Threshold check error: {e}")
            
        # Check component thresholds
        for component_type, metrics in self.component_metrics.items():
            try:
                await self._check_component_thresholds(component_type, metrics)
            except Exception as e:
                logger.warning(f"Component threshold check error for {component_type}: {e}")
                
    async def _check_component_thresholds(
        self,
        component_type: ComponentType,
        metrics: ComponentMetrics
    ) -> None:
        """Check thresholds for a specific component."""
        # Check queue size
        if metrics.queue_size._value:
            queue_size = metrics.queue_size._value._value
            if queue_size > self.thresholds.max_queue_size:
                await self._trigger_alert(
                    f'{component_type.value}_high_queue',
                    f'High queue size for {component_type.value}: {queue_size}'
                )
                
        # Check cache hit rate
        if metrics.cache_hit_rate._value:
            cache_rate = metrics.cache_hit_rate._value._value
            if cache_rate < self.thresholds.min_cache_hit_rate:
                await self._trigger_alert(
                    f'{component_type.value}_low_cache_hit_rate',
                    f'Low cache hit rate for {component_type.value}: {cache_rate:.1%}'
                )
                
    async def _push_metrics(self) -> None:
        """Push metrics to Prometheus gateway."""
        try:
            push_to_gateway(
                self.prometheus_gateway,
                job='smc_trading_agent',
                registry=self.registry
            )
        except Exception as e:
            logger.warning(f"Failed to push metrics to Prometheus: {e}")
            
    async def _store_performance_history(self) -> None:
        """Store performance history in Redis."""
        if not self.redis_client:
            return
            
        try:
            current_time = datetime.now().isoformat()
            
            # Collect key performance indicators
            kpis = {
                'timestamp': current_time,
                'system': {
                    'cpu_usage': self.system_metrics['cpu_usage']._value._value,
                    'memory_usage': self.system_metrics['memory_usage']._value._value
                },
                'components': {}
            }
            
            for component_type, metrics in self.component_metrics.items():
                component_kpis = {
                    'active_connections': metrics.active_connections._value._value if metrics.active_connections._value else 0,
                    'queue_size': metrics.queue_size._value._value if metrics.queue_size._value else 0,
                    'cache_hit_rate': metrics.cache_hit_rate._value._value if metrics.cache_hit_rate._value else 0
                }
                kpis['components'][component_type.value] = component_kpis
                
            # Store in Redis with TTL
            await self.redis_client.setex(
                f'smc:kpis:{current_time}',
                3600,  # 1 hour TTL
                json.dumps(kpis)
            )
            
        except Exception as e:
            logger.warning(f"Failed to store performance history: {e}")
            
    async def _trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger an alert."""
        current_time = time.time()
        
        # Check if this alert was recently triggered (avoid spam)
        if alert_type in self.alerts:
            last_time = self.alerts[alert_type]['timestamp']
            if current_time - last_time < 300:  # 5 minute cooldown
                return
                
        # Record alert
        self.alerts[alert_type] = {
            'timestamp': current_time,
            'message': message,
            'resolved': False
        }
        
        logger.warning(f"ALERT: {message}")
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert_type, message)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
                
    def add_alert_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add alert callback function."""
        self.alert_callbacks.append(callback)
        
    # Component-specific methods
    
    def record_component_latency(
        self,
        component_type: ComponentType,
        operation: str,
        latency_ms: float
    ) -> None:
        """Record latency for a component."""
        if component_type in self.component_metrics:
            self.component_metrics[component_type].record_latency(operation, latency_ms)
            
            # Check latency threshold
            if latency_ms > self.thresholds.max_latency_ms:
                asyncio.create_task(self._trigger_alert(
                    f'{component_type.value}_high_latency',
                    f'High latency for {component_type.value}.{operation}: {latency_ms:.1f}ms'
                ))
                
    def record_component_request(
        self,
        component_type: ComponentType,
        operation: str,
        status: str = 'success'
    ) -> None:
        """Record request for a component."""
        if component_type in self.component_metrics:
            self.component_metrics[component_type].record_request(operation, status)
            
    def record_component_error(
        self,
        component_type: ComponentType,
        error_type: str
    ) -> None:
        """Record error for a component."""
        if component_type in self.component_metrics:
            self.component_metrics[component_type].record_error(error_type)
            
    def update_component_metrics(
        self,
        component_type: ComponentType,
        metrics: Dict[str, Any]
    ) -> None:
        """Update component-specific metrics."""
        if component_type not in self.component_metrics:
            return
            
        component_metrics = self.component_metrics[component_type]
        
        if 'active_connections' in metrics:
            component_metrics.set_active_connections(metrics['active_connections'])
            
        if 'queue_size' in metrics:
            component_metrics.set_queue_size(metrics['queue_size'])
            
        if 'cache_hit_rate' in metrics:
            component_metrics.set_cache_hit_rate(metrics['cache_hit_rate'])
            
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_usage': self.system_metrics['cpu_usage']._value._value,
                'memory_usage': self.system_metrics['memory_usage']._value._value,
                'disk_usage': self.system_metrics['disk_usage']._value._value
            },
            'components': {},
            'alerts': {
                'active_count': len([a for a in self.alerts.values() if not a['resolved']]),
                'total_count': len(self.alerts)
            }
        }
        
        # Add component summaries
        for component_type, metrics in self.component_metrics.items():
            component_summary = {
                'active_connections': metrics.active_connections._value._value if metrics.active_connections._value else 0,
                'queue_size': metrics.queue_size._value._value if metrics.queue_size._value else 0,
                'cache_hit_rate': metrics.cache_hit_rate._value._value if metrics.cache_hit_rate._value else 0,
                'requests_total': metrics.requests_total._value._value if metrics.requests_total._value else 0,
                'errors_total': metrics.errors_total._value._value if metrics.errors_total._value else 0
            }
            summary['components'][component_type.value] = component_summary
            
        return summary
        
    async def get_historical_performance(
        self,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical performance data."""
        if not self.redis_client:
            return []
            
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # Get performance data from Redis
            performance_data = []
            
            # This is a simplified implementation - in practice you'd want
            # more sophisticated time-series querying
            current_time = start_time
            while current_time <= end_time:
                key = f'smc:kpis:{current_time.strftime("%Y-%m-%dT%H:%M:%S")}'
                data = await self.redis_client.get(key)
                
                if data:
                    performance_data.append(json.loads(data))
                    
                current_time += timedelta(minutes=5)  # 5-minute intervals
                
            return performance_data
            
        except Exception as e:
            logger.error(f"Failed to get historical performance: {e}")
            return []


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


async def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        await _performance_monitor.initialize()
        
    return _performance_monitor


# Decorators for automatic performance tracking

def track_performance(component_type: ComponentType, operation: str = "default"):
    """Decorator to automatically track performance of functions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            monitor = await get_performance_monitor()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                
                monitor.record_component_latency(component_type, operation, latency_ms)
                monitor.record_component_request(component_type, operation, 'success')
                
                return result
                
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                
                monitor.record_component_latency(component_type, operation, latency_ms)
                monitor.record_component_error(component_type, type(e).__name__)
                raise
                
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            return asyncio.run(async_wrapper(*args, **kwargs))
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# Example alert callback
async def log_alert_callback(alert_type: str, message: str) -> None:
    """Default alert callback that logs alerts."""
    logger.warning(f"PERFORMANCE ALERT [{alert_type}]: {message}")


# Factory function
async def create_performance_monitor(
    thresholds: PerformanceThresholds = None,
    prometheus_gateway: str = "localhost:9091",
    redis_url: str = "redis://localhost:6379"
) -> PerformanceMonitor:
    """Create and initialize performance monitor."""
    monitor = PerformanceMonitor(thresholds, prometheus_gateway, redis_url)
    monitor.add_alert_callback(log_alert_callback)
    await monitor.initialize()
    return monitor