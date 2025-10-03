"""
Service Manager for SMC Trading Agent

Provides a small lifecycle manager used by main.py and tests.
This version aligns the API used across the codebase: constructor
accepts (config, logger), exposes register_service(name, component,
health_check, critical), get_service(name), initialize_services(),
and shutdown().
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable


@dataclass
class ServiceInfo:
    name: str
    component: Any
    status: str = "registered"
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    critical: bool = False
    health_check: Optional[Callable] = None


class ServiceManager:
    """Service lifecycle manager with a stable, test-friendly API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.services: Dict[str, ServiceInfo] = {}
        self.running = False
        self._ready = False
        self.logger.info("Service manager initialized")

    def register_service(self, name: str, component: Any, health_check: Optional[Callable] = None, critical: bool = False) -> bool:
        """Register a service for management (synchronous for simplicity)."""
        try:
            if name in self.services:
                self.logger.warning(f"Service '{name}' already registered")
                return False

            self.services[name] = ServiceInfo(
                name=name,
                component=component,
                critical=critical,
                health_check=health_check,
            )
            self.logger.info(f"Registered service: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register service '{name}': {e}")
            return False

    async def start_service(self, name: str) -> bool:
        """Start a single service if it exposes a start() method."""
        try:
            if name not in self.services:
                self.logger.error(f"Service '{name}' not registered")
                return False

            svc = self.services[name]
            if svc.status == "running":
                return True

            comp = svc.component
            if hasattr(comp, 'start'):
                if asyncio.iscoroutinefunction(comp.start):
                    result = await comp.start()
                else:
                    result = comp.start()
                if result is False:
                    self.logger.error(f"Failed to start service: {name}")
                    return False
            svc.status = 'running'
            svc.start_time = asyncio.get_event_loop().time()
            self.logger.info(f"Started service: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error starting service '{name}': {e}")
            return False

    async def stop_service(self, name: str) -> bool:
        """Stop a single service if it exposes a stop() method."""
        try:
            if name not in self.services:
                return False
            svc = self.services[name]
            if svc.status != 'running':
                return True
            comp = svc.component
            if hasattr(comp, 'stop'):
                if asyncio.iscoroutinefunction(comp.stop):
                    await comp.stop()
                else:
                    comp.stop()
            svc.status = 'stopped'
            svc.stop_time = asyncio.get_event_loop().time()
            self.logger.info(f"Stopped service: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping service '{name}': {e}")
            return False

    async def start_all_services(self) -> bool:
        self.logger.info("Starting all services...")
        ok = True
        for name in list(self.services.keys()):
            if not await self.start_service(name):
                ok = False
        self.running = ok
        return ok

    async def stop_all_services(self) -> bool:
        self.logger.info("Stopping all services...")
        ok = True
        for name in reversed(list(self.services.keys())):
            if not await self.stop_service(name):
                ok = False
        self.running = False
        return ok

    def get_service(self, name: str) -> Optional[Any]:
        """Return the underlying component by name."""
        info = self.services.get(name)
        return info.component if info else None

    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        info = self.services.get(name)
        if not info:
            return None
        return {
            'name': info.name,
            'status': info.status,
            'critical': info.critical,
            'start_time': info.start_time,
            'stop_time': info.stop_time,
        }

    def get_all_services_status(self) -> Dict[str, Any]:
        return {
            'manager_running': self.running,
            'total_services': len(self.services),
            'services': {n: self.get_service_status(n) for n in self.services}
        }

    async def initialize_services(self, use_mock: bool = False) -> bool:
        """Compatibility shim used by main(); no-op aside from marking running."""
        try:
            # Wire default mock providers if requested (keeps main() path working)
            if use_mock:
                from providers.mock import (
                    MockDataFeed, MockAnalyzer, MockDecisionEngine, MockExecutorClient, MockRiskManager
                )
                self.register_service("data_feed", MockDataFeed())
                self.register_service("analyzer", MockAnalyzer())
                self.register_service("decision_engine", MockDecisionEngine())
                self.register_service("executor", MockExecutorClient())
                self.register_service("risk_manager", MockRiskManager())

            # Load secrets/env if needed here (placeholder)
            # Warm-up models/components if necessary (best-effort)
            analyzer = self.get_service("analyzer")
            if analyzer and hasattr(analyzer, "warm_up"):
                try:
                    res = analyzer.warm_up()  # sync or async
                    if hasattr(res, "__await__"):
                        await res
                except Exception as e:
                    self.logger.debug(f"Analyzer warm-up skipped: {e}")
            self.running = True
            self._ready = True
            return True
        except Exception as e:
            self.logger.error(f"initialize_services failed: {e}")
            self._ready = False
            return False

    async def shutdown(self) -> None:
        await self.stop_all_services()

    # Readiness helpers
    def is_ready(self) -> bool:
        return self._ready and self.running
