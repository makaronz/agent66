"""
Enhanced Health Monitoring for SMC Trading Agent.

This module provides comprehensive health monitoring including:
- FastAPI health check endpoints
- Prometheus metrics collection
- Docker-compatible health checks
- Service health status tracking
- Health check coordination
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .error_handlers import health_monitor as base_health_monitor


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service: str
    healthy: bool
    latency_ms: float
    error_message: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class EnhancedHealthMonitor:
    """
    Enhanced health monitoring with FastAPI endpoints and Prometheus metrics.
    """
    
    def __init__(self, app_name: str = "smc-trading-agent", logger: Optional[logging.Logger] = None):
        self.app_name = app_name
        self.logger = logger or logging.getLogger(__name__)
        self.startup_time = time.time()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=f"{app_name} Health Monitor",
            description="Health monitoring endpoints for SMC Trading Agent",
            version="1.0.0"
        )
        
        # Prometheus metrics
        self.health_check_counter = Counter(
            'health_check_total',
            'Total number of health checks',
            ['service', 'status']
        )
        
        self.health_check_duration = Histogram(
            'health_check_duration_seconds',
            'Health check duration in seconds',
            ['service']
        )
        
        self.service_health_gauge = Gauge(
            'service_health_status',
            'Service health status (1=healthy, 0=unhealthy)',
            ['service']
        )
        
        self.system_uptime_gauge = Gauge(
            'system_uptime_seconds',
            'System uptime in seconds'
        )
        
        # Register FastAPI routes
        self._register_routes()
        
        # Background health check task
        self.health_check_task: Optional[asyncio.Task] = None
        self.health_check_interval = 30  # seconds
        
    def _register_routes(self):
        """Register FastAPI routes for health monitoring."""
        
        @self.app.get("/health")
        async def health_check():
            """Basic health check endpoint."""
            try:
                health_status = await self.get_system_health()
                status_code = 200 if health_status["overall_healthy"] else 503
                
                return JSONResponse(
                    content=health_status,
                    status_code=status_code
                )
            except Exception as e:
                self.logger.error(f"Health check failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Health check failed")
        
        @self.app.get("/health/ready")
        async def readiness_check():
            """Readiness check endpoint for Kubernetes/Docker."""
            try:
                health_status = await self.get_system_health()
                
                # Check if all critical services are healthy
                critical_services_healthy = all(
                    service_info.get("healthy", False)
                    for service_info in health_status["services"].values()
                    if service_info.get("critical", False)
                )
                
                if critical_services_healthy:
                    return JSONResponse(
                        content={"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()},
                        status_code=200
                    )
                else:
                    return JSONResponse(
                        content={"status": "not ready", "timestamp": datetime.now(timezone.utc).isoformat()},
                        status_code=503
                    )
            except Exception as e:
                self.logger.error(f"Readiness check failed: {e}", exc_info=True)
                return JSONResponse(
                    content={"status": "not ready", "error": str(e)},
                    status_code=503
                )
        
        @self.app.get("/health/live")
        async def liveness_check():
            """Liveness check endpoint for Kubernetes/Docker."""
            try:
                # Simple liveness check - just verify the service is responding
                uptime = time.time() - self.startup_time
                
                return JSONResponse(
                    content={
                        "status": "alive",
                        "uptime_seconds": uptime,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    status_code=200
                )
            except Exception as e:
                self.logger.error(f"Liveness check failed: {e}", exc_info=True)
                return JSONResponse(
                    content={"status": "not alive", "error": str(e)},
                    status_code=503
                )
        
        @self.app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint."""
            try:
                # Update uptime metric
                self.system_uptime_gauge.set(time.time() - self.startup_time)
                
                # Update service health metrics
                health_status = await self.get_system_health()
                for service_name, service_info in health_status["services"].items():
                    self.service_health_gauge.labels(service=service_name).set(
                        1 if service_info.get("healthy", False) else 0
                    )
                
                return Response(
                    content=generate_latest(),
                    media_type=CONTENT_TYPE_LATEST
                )
            except Exception as e:
                self.logger.error(f"Metrics generation failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Metrics generation failed")
        
        @self.app.get("/health/detailed")
        async def detailed_health_check():
            """Detailed health check with service-specific information."""
            try:
                health_status = await self.get_detailed_health()
                status_code = 200 if health_status["overall_healthy"] else 503
                
                return JSONResponse(
                    content=health_status,
                    status_code=status_code
                )
            except Exception as e:
                self.logger.error(f"Detailed health check failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Detailed health check failed")
    
    async def start_background_health_checks(self):
        """Start background health check task."""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._background_health_checks())
            self.logger.info("Background health checks started")
    
    async def stop_background_health_checks(self):
        """Stop background health check task."""
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Background health checks stopped")
    
    async def _background_health_checks(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Background health check failed: {e}", exc_info=True)
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks for all registered components."""
        try:
            # Get base health monitor status
            base_health = base_health_monitor.get_system_health()
            
            # Update Prometheus metrics
            for component_name, component_info in base_health.get("components", {}).items():
                is_healthy = component_info.get("healthy", False)
                self.service_health_gauge.labels(service=component_name).set(1 if is_healthy else 0)
                
                # Increment health check counter
                status = "healthy" if is_healthy else "unhealthy"
                self.health_check_counter.labels(service=component_name, status=status).inc()
            
            self.logger.debug("Background health checks completed")
            
        except Exception as e:
            self.logger.error(f"Background health checks failed: {e}", exc_info=True)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            # Get base health monitor status
            base_health = base_health_monitor.get_system_health()
            
            # Enhance with additional information
            health_status = {
                "app_name": self.app_name,
                "overall_healthy": base_health.get("overall_healthy", False),
                "startup_time": self.startup_time,
                "uptime_seconds": time.time() - self.startup_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": base_health.get("components", {}),
                "version": "1.0.0"
            }
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"System health check failed: {e}", exc_info=True)
            return {
                "app_name": self.app_name,
                "overall_healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0"
            }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status with service-specific information."""
        try:
            base_health = base_health_monitor.get_system_health()
            
            detailed_health = {
                "app_name": self.app_name,
                "overall_healthy": base_health.get("overall_healthy", False),
                "startup_time": self.startup_time,
                "uptime_seconds": time.time() - self.startup_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "services": {}
            }
            
            # Add detailed service information
            for component_name, component_info in base_health.get("components", {}).items():
                service_health = await self._check_service_health(component_name)
                detailed_health["services"][component_name] = {
                    **component_info,
                    **service_health
                }
            
            return detailed_health
            
        except Exception as e:
            self.logger.error(f"Detailed health check failed: {e}", exc_info=True)
            return {
                "app_name": self.app_name,
                "overall_healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0"
            }
    
    async def _check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service with timing."""
        start_time = time.time()
        
        try:
            # Get health check from base health monitor
            is_healthy = base_health_monitor.check_health(service_name)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.health_check_duration.labels(service=service_name).observe(
                (time.time() - start_time)
            )
            
            return {
                "healthy": is_healthy,
                "latency_ms": latency_ms,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed for {service_name}: {e}")
            
            return {
                "healthy": False,
                "latency_ms": latency_ms,
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
    
    def get_fastapi_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app
    
    async def shutdown(self):
        """Shutdown the health monitor."""
        await self.stop_background_health_checks()
        self.logger.info("Health monitor shutdown completed")
