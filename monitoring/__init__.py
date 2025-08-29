"""
Monitoring Module - System Observability and Health Monitoring

Provides comprehensive monitoring, logging, and observability features for the SMC Trading Agent.
Includes health monitoring, Grafana dashboards, system metrics collection, and performance tracking.

Key Features:
- Real-time system health monitoring and alerts
- Grafana dashboard integration for visualization
- Comprehensive metrics collection and analysis
- Performance monitoring and optimization tracking
- Log aggregation and centralized logging
- Alert management and notification systems
- System diagnostics and troubleshooting tools

Usage:
    from smc_trading_agent.monitoring import EnhancedHealthMonitor, HealthMonitor
    
    # Enhanced health monitor (main package)
    enhanced_monitor = EnhancedHealthMonitor()
    health_status = await enhanced_monitor.get_system_health()
    
    # Local health monitor (monitoring package)
    local_monitor = HealthMonitor()
    service_status = await local_monitor.perform_health_checks()
"""

__version__ = "1.0.0"
__description__ = "System monitoring and observability features"
__keywords__ = ["monitoring", "observability", "health-check", "metrics", "grafana"]

# Import monitoring components
from .health_monitor import HealthMonitor

# Package-level exports
__all__ = [
    'HealthMonitor',
    '__version__',
    '__description__'
]
