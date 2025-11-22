"""
Enhanced Monitoring and Metrics System for SMC Trading Agent

Provides comprehensive monitoring with:
- Prometheus metrics collection and integration
- Grafana dashboard configuration and management
- Real-time performance monitoring and alerting
- System health checks and diagnostics
- Business metrics for trading operations
- Distributed tracing and latency analysis
"""

__version__ = "2.0.0"
__description__ = "Enhanced monitoring and metrics system with Prometheus/Grafana integration"
__keywords__ = ["monitoring", "metrics", "prometheus", "grafana", "trading", "performance"]

# Import enhanced monitoring components
from .enhanced_monitoring import (
    EnhancedMonitoringSystem,
    MetricRegistry,
    SystemMonitor,
    BusinessMetricsCollector,
    AlertManager,
    HealthChecker,
    MetricConfig,
    AlertConfig,
    HealthCheck,
    monitor_performance,
    get_monitoring_system,
    initialize_monitoring
)

from .grafana_dashboards import (
    GrafanaDashboardManager,
    DashboardConfig,
    GrafanaConfig,
    DashboardTemplates,
    DashboardSetup
)

# Legacy imports for backward compatibility
from .health_monitor import HealthMonitor
from ..health_monitor import EnhancedHealthMonitor

# Package-level exports
__all__ = [
    # Enhanced monitoring system
    "EnhancedMonitoringSystem",
    "MetricRegistry",
    "SystemMonitor",
    "BusinessMetricsCollector",
    "AlertManager",
    "HealthChecker",

    # Configuration classes
    "MetricConfig",
    "AlertConfig",
    "HealthCheck",
    "DashboardConfig",
    "GrafanaConfig",
    "DashboardTemplates",
    "DashboardSetup",

    # Grafana integration
    "GrafanaDashboardManager",

    # Utility functions
    "monitor_performance",
    "get_monitoring_system",
    "initialize_monitoring",

    # Legacy compatibility
    "HealthMonitor",
    "EnhancedHealthMonitor",

    # Metadata
    "__version__",
    "__description__"
]
