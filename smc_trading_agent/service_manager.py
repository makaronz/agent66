"""
Service Manager for SMC Trading Agent.

This module provides comprehensive service coordination including:
- Component lifecycle management
- Async service initialization and shutdown
- Health monitoring integration
- Graceful shutdown coordination
- Service dependency management
"""

import asyncio
import logging
import signal
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)


@dataclass
class ServiceInfo:
    """Information about a service component."""
    name: str
    component: Any
    health_check: Callable[[], bool]
    critical: bool = True
    startup_timeout: float = 30.0
    shutdown_timeout: float = 30.0


class ServiceManager:
    """
    Manages the lifecycle of all SMC Trading Agent components.
    
    Provides coordinated initialization, health monitoring, and graceful shutdown.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.services: Dict[str, ServiceInfo] = {}
        self.shutdown_flag = False
        self.startup_time = None
        self.health_check_interval = config.get('monitoring', {}).get('health_check_interval', 30)
        
        # Initialize circuit breakers for service management
        self.service_circuit_breaker = CircuitBreaker(
            name="service_manager",
            failure_threshold=3,
            recovery_timeout=120.0,
            logger=self.logger
        )
        
        # Register shutdown signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
    
    def register_service(self, name: str, component: Any, health_check: Callable[[], bool],
                        critical: bool = True, startup_timeout: float = 30.0,
                        shutdown_timeout: float = 30.0) -> None:
        """Register a service component for lifecycle management."""
        service_info = ServiceInfo(
            name=name,
            component=component,
            health_check=health_check,
            critical=critical,
            startup_timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout
        )
        self.services[name] = service_info
        
        # Register with health monitor
        health_monitor.register_component(name, health_check, critical)
        
        self.logger.info(f"Registered service: {name} (critical: {critical})")
    
    async def initialize_services(self) -> bool:
        """Initialize all registered services with error handling."""
        self.startup_time = time.time()
        self.logger.info("Initializing SMC Trading Agent services...")
        
        initialization_tasks = []
        
        for name, service_info in self.services.items():
            task = self._initialize_service(name, service_info)
            initialization_tasks.append(task)
        
        try:
            # Wait for all services to initialize
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
            
            # Check for initialization failures
            failed_services = []
            for i, (name, result) in enumerate(zip(self.services.keys(), results)):
                if isinstance(result, Exception):
                    failed_services.append((name, result))
                    self.logger.error(f"Service {name} initialization failed: {result}")
                else:
                    self.logger.info(f"Service {name} initialized successfully")
            
            if failed_services:
                self.logger.error(f"Failed to initialize {len(failed_services)} services")
                return False
            
            startup_duration = time.time() - self.startup_time
            self.logger.info(f"All services initialized successfully in {startup_duration:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_service(self, name: str, service_info: ServiceInfo) -> None:
        """Initialize a single service with timeout and error handling."""
        try:
            # Check if service has async initialization method
            if hasattr(service_info.component, 'initialize_async'):
                await asyncio.wait_for(
                    service_info.component.initialize_async(),
                    timeout=service_info.startup_timeout
                )
            elif hasattr(service_info.component, 'initialize'):
                # Run sync initialization in thread pool
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, service_info.component.initialize),
                    timeout=service_info.startup_timeout
                )
            
            self.logger.info(f"Service {name} initialized successfully")
            
        except asyncio.TimeoutError:
            raise ComponentHealthError(
                f"Service {name} initialization timeout after {service_info.startup_timeout}s",
                severity=ErrorSeverity.HIGH,
                component=name
            )
        except Exception as e:
            raise ComponentHealthError(
                f"Service {name} initialization failed: {str(e)}",
                severity=ErrorSeverity.HIGH,
                component=name
            )
    
    async def shutdown_services(self) -> None:
        """Gracefully shutdown all services."""
        self.shutdown_flag = True
        self.logger.info("Initiating graceful shutdown of all services...")
        
        shutdown_tasks = []
        
        for name, service_info in self.services.items():
            task = self._shutdown_service(name, service_info)
            shutdown_tasks.append(task)
        
        try:
            # Wait for all services to shutdown
            results = await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            
            # Log shutdown results
            for i, (name, result) in enumerate(zip(self.services.keys(), results)):
                if isinstance(result, Exception):
                    self.logger.error(f"Service {name} shutdown failed: {result}")
                else:
                    self.logger.info(f"Service {name} shutdown successfully")
            
            self.logger.info("All services shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Service shutdown failed: {e}", exc_info=True)
    
    async def _shutdown_service(self, name: str, service_info: ServiceInfo) -> None:
        """Shutdown a single service with timeout and error handling."""
        try:
            # Check if service has async shutdown method
            if hasattr(service_info.component, 'shutdown_async'):
                await asyncio.wait_for(
                    service_info.component.shutdown_async(),
                    timeout=service_info.shutdown_timeout
                )
            elif hasattr(service_info.component, 'shutdown'):
                # Run sync shutdown in thread pool
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, service_info.component.shutdown),
                    timeout=service_info.shutdown_timeout
                )
            
            self.logger.info(f"Service {name} shutdown successfully")
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Service {name} shutdown timeout after {service_info.shutdown_timeout}s")
        except Exception as e:
            self.logger.error(f"Service {name} shutdown failed: {str(e)}")
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        health_status = {
            "overall_healthy": True,
            "services": {},
            "startup_time": self.startup_time,
            "uptime": time.time() - self.startup_time if self.startup_time else 0,
            "shutdown_flag": self.shutdown_flag
        }
        
        for name, service_info in self.services.items():
            try:
                is_healthy = service_info.health_check()
                health_status["services"][name] = {
                    "healthy": is_healthy,
                    "critical": service_info.critical,
                    "last_check": time.time()
                }
                
                if not is_healthy and service_info.critical:
                    health_status["overall_healthy"] = False
                    
            except Exception as e:
                self.logger.error(f"Health check failed for service {name}: {e}")
                health_status["services"][name] = {
                    "healthy": False,
                    "critical": service_info.critical,
                    "error": str(e),
                    "last_check": time.time()
                }
                if service_info.critical:
                    health_status["overall_healthy"] = False
        
        return health_status
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_flag
    
    def _handle_shutdown_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        if not self.shutdown_flag:
            self.logger.info(f"Received shutdown signal: {signal.Signals(signum).name}. Initiating graceful shutdown...")
            self.shutdown_flag = True
        else:
            self.logger.warning("Received second shutdown signal. Forcing exit.")
            import sys
            sys.exit(1)
    
    @asynccontextmanager
    async def service_lifecycle(self):
        """Context manager for service lifecycle management."""
        try:
            success = await self.initialize_services()
            if not success:
                raise ComponentHealthError("Service initialization failed", severity=ErrorSeverity.CRITICAL)
            yield self
        finally:
            await self.shutdown_services()
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service component."""
        service_info = self.services.get(name)
        return service_info.component if service_info else None
    
    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self.services.keys())
