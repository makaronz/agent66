"""
Health Monitor for SMC Trading Agent Stream Processor

Provides HTTP endpoints for health checks, readiness probes, and metrics collection.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Callable, Optional
from aiohttp import web, web_request
from aiohttp.web_response import Response

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    HTTP-based health monitoring service.
    
    Provides endpoints for Kubernetes health checks and metrics collection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize health monitor.
        
        Args:
            config: Health monitor configuration
        """
        self.config = config
        self.port = config.get('port', 8081)
        self.metrics_port = config.get('metrics_port', 8080)
        
        self.health_checks = {}
        self.app = None
        self.runner = None
        self.site = None
        self.running = False
        
        self.start_time = time.time()
        
        logger.info(f"Health monitor initialized on port {self.port}")
    
    async def start(self) -> bool:
        """
        Start the health monitor HTTP server.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Create aiohttp application
            self.app = web.Application()
            
            # Register routes
            self.app.router.add_get('/health', self._health_handler)
            self.app.router.add_get('/ready', self._readiness_handler)
            self.app.router.add_get('/metrics', self._metrics_handler)
            self.app.router.add_get('/status', self._status_handler)
            
            # Create runner and start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await self.site.start()
            
            self.running = True
            logger.info(f"Health monitor started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start health monitor: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the health monitor HTTP server.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            self.running = False
            
            if self.site:
                await self.site.stop()
                self.site = None
            
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            self.app = None
            
            logger.info("Health monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop health monitor: {e}")
            return False
    
    def register_health_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """
        Register a health check function.
        
        Args:
            name: Health check name
            check_func: Function that returns health status
        """
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def unregister_health_check(self, name: str):
        """
        Unregister a health check function.
        
        Args:
            name: Health check name
        """
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Unregistered health check: {name}")
    
    async def _health_handler(self, request: web_request.Request) -> Response:
        """Handle health check requests."""
        try:
            health_status = await self._get_health_status()
            
            status_code = 200 if health_status['healthy'] else 503
            
            return web.json_response(
                health_status,
                status=status_code,
                headers={'Content-Type': 'application/json'}
            )
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': time.time()
                },
                status=503
            )
    
    async def _readiness_handler(self, request: web_request.Request) -> Response:
        """Handle readiness probe requests."""
        try:
            # Simple readiness check - server is running
            readiness_status = {
                'ready': self.running,
                'uptime_seconds': time.time() - self.start_time,
                'timestamp': time.time()
            }
            
            status_code = 200 if readiness_status['ready'] else 503
            
            return web.json_response(
                readiness_status,
                status=status_code,
                headers={'Content-Type': 'application/json'}
            )
            
        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            return web.json_response(
                {
                    'ready': False,
                    'error': str(e),
                    'timestamp': time.time()
                },
                status=503
            )
    
    async def _metrics_handler(self, request: web_request.Request) -> Response:
        """Handle metrics requests (Prometheus format)."""
        try:
            metrics = await self._get_metrics()
            
            # Convert to Prometheus format
            prometheus_metrics = self._format_prometheus_metrics(metrics)
            
            return web.Response(
                text=prometheus_metrics,
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
            
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return web.Response(
                text=f"# Error collecting metrics: {e}\n",
                status=500,
                content_type='text/plain'
            )
    
    async def _status_handler(self, request: web_request.Request) -> Response:
        """Handle status requests (detailed JSON)."""
        try:
            status = {
                'service': 'smc-stream-processor',
                'version': '1.0.0',
                'uptime_seconds': time.time() - self.start_time,
                'health': await self._get_health_status(),
                'metrics': await self._get_metrics(),
                'timestamp': time.time()
            }
            
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"Status error: {e}")
            return web.json_response(
                {
                    'error': str(e),
                    'timestamp': time.time()
                },
                status=500
            )
    
    async def _get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        health_results = {}
        overall_healthy = True
        
        # Run all registered health checks
        for name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                health_results[name] = result
                
                if not result.get('healthy', False):
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                health_results[name] = {
                    'healthy': False,
                    'error': str(e)
                }
                overall_healthy = False
        
        return {
            'healthy': overall_healthy,
            'checks': health_results,
            'uptime_seconds': time.time() - self.start_time,
            'timestamp': time.time()
        }
    
    async def _get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        metrics = {
            'uptime_seconds': time.time() - self.start_time,
            'health_checks_total': len(self.health_checks),
            'timestamp': time.time()
        }
        
        # Add health check metrics
        health_status = await self._get_health_status()
        healthy_checks = sum(1 for check in health_status['checks'].values() if check.get('healthy', False))
        
        metrics.update({
            'health_checks_healthy': healthy_checks,
            'health_checks_unhealthy': len(self.health_checks) - healthy_checks,
            'overall_healthy': 1 if health_status['healthy'] else 0
        })
        
        return metrics
    
    def _format_prometheus_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics in Prometheus format."""
        lines = [
            "# HELP smc_stream_processor_uptime_seconds Uptime in seconds",
            "# TYPE smc_stream_processor_uptime_seconds gauge",
            f"smc_stream_processor_uptime_seconds {metrics['uptime_seconds']}",
            "",
            "# HELP smc_stream_processor_health_checks_total Total number of health checks",
            "# TYPE smc_stream_processor_health_checks_total gauge",
            f"smc_stream_processor_health_checks_total {metrics['health_checks_total']}",
            "",
            "# HELP smc_stream_processor_health_checks_healthy Number of healthy checks",
            "# TYPE smc_stream_processor_health_checks_healthy gauge",
            f"smc_stream_processor_health_checks_healthy {metrics['health_checks_healthy']}",
            "",
            "# HELP smc_stream_processor_health_checks_unhealthy Number of unhealthy checks",
            "# TYPE smc_stream_processor_health_checks_unhealthy gauge",
            f"smc_stream_processor_health_checks_unhealthy {metrics['health_checks_unhealthy']}",
            "",
            "# HELP smc_stream_processor_healthy Overall health status (1=healthy, 0=unhealthy)",
            "# TYPE smc_stream_processor_healthy gauge",
            f"smc_stream_processor_healthy {metrics['overall_healthy']}",
            ""
        ]
        
        return "\n".join(lines)