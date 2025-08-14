"""
Service Manager for SMC Trading Agent Stream Processor

Manages the lifecycle of various services and components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Service lifecycle manager.
    
    Manages starting, stopping, and monitoring of various services.
    """
    
    def __init__(self):
        """Initialize service manager."""
        self.services = {}
        self.running = False
        
        logger.info("Service manager initialized")
    
    async def register_service(self, name: str, service: Any) -> bool:
        """
        Register a service for management.
        
        Args:
            name: Service name
            service: Service instance
            
        Returns:
            bool: True if registered successfully, False otherwise
        """
        try:
            if name in self.services:
                logger.warning(f"Service '{name}' already registered")
                return False
            
            self.services[name] = {
                'instance': service,
                'status': 'registered',
                'start_time': None,
                'stop_time': None
            }
            
            logger.info(f"Registered service: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service '{name}': {e}")
            return False
    
    async def start_service(self, name: str) -> bool:
        """
        Start a specific service.
        
        Args:
            name: Service name
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            if name not in self.services:
                logger.error(f"Service '{name}' not registered")
                return False
            
            service_info = self.services[name]
            service = service_info['instance']
            
            if service_info['status'] == 'running':
                logger.warning(f"Service '{name}' already running")
                return True
            
            # Start the service
            if hasattr(service, 'start'):
                if asyncio.iscoroutinefunction(service.start):
                    result = await service.start()
                else:
                    result = service.start()
                
                if result:
                    service_info['status'] = 'running'
                    service_info['start_time'] = asyncio.get_event_loop().time()
                    logger.info(f"Started service: {name}")
                    return True
                else:
                    logger.error(f"Failed to start service: {name}")
                    return False
            else:
                logger.warning(f"Service '{name}' has no start method")
                return False
                
        except Exception as e:
            logger.error(f"Error starting service '{name}': {e}")
            return False
    
    async def stop_service(self, name: str) -> bool:
        """
        Stop a specific service.
        
        Args:
            name: Service name
            
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            if name not in self.services:
                logger.error(f"Service '{name}' not registered")
                return False
            
            service_info = self.services[name]
            service = service_info['instance']
            
            if service_info['status'] != 'running':
                logger.warning(f"Service '{name}' not running")
                return True
            
            # Stop the service
            if hasattr(service, 'stop'):
                if asyncio.iscoroutinefunction(service.stop):
                    result = await service.stop()
                else:
                    result = service.stop()
                
                if result:
                    service_info['status'] = 'stopped'
                    service_info['stop_time'] = asyncio.get_event_loop().time()
                    logger.info(f"Stopped service: {name}")
                    return True
                else:
                    logger.error(f"Failed to stop service: {name}")
                    return False
            else:
                logger.warning(f"Service '{name}' has no stop method")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping service '{name}': {e}")
            return False
    
    async def start_all_services(self) -> bool:
        """
        Start all registered services.
        
        Returns:
            bool: True if all services started successfully, False otherwise
        """
        logger.info("Starting all services...")
        
        success = True
        for name in self.services.keys():
            if not await self.start_service(name):
                success = False
        
        if success:
            self.running = True
            logger.info("All services started successfully")
        else:
            logger.error("Some services failed to start")
        
        return success
    
    async def stop_all_services(self) -> bool:
        """
        Stop all running services.
        
        Returns:
            bool: True if all services stopped successfully, False otherwise
        """
        logger.info("Stopping all services...")
        
        success = True
        # Stop services in reverse order
        for name in reversed(list(self.services.keys())):
            if not await self.stop_service(name):
                success = False
        
        self.running = False
        
        if success:
            logger.info("All services stopped successfully")
        else:
            logger.error("Some services failed to stop")
        
        return success
    
    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific service.
        
        Args:
            name: Service name
            
        Returns:
            Dict containing service status information, None if not found
        """
        if name in self.services:
            return self.services[name].copy()
        return None
    
    def get_all_services_status(self) -> Dict[str, Any]:
        """
        Get status of all services.
        
        Returns:
            Dict containing status of all services
        """
        return {
            'manager_running': self.running,
            'total_services': len(self.services),
            'services': {name: info.copy() for name, info in self.services.items()}
        }
    
    def is_service_running(self, name: str) -> bool:
        """
        Check if a service is running.
        
        Args:
            name: Service name
            
        Returns:
            bool: True if service is running, False otherwise
        """
        if name in self.services:
            return self.services[name]['status'] == 'running'
        return False
    
    def get_running_services(self) -> List[str]:
        """
        Get list of running services.
        
        Returns:
            List of running service names
        """
        return [
            name for name, info in self.services.items()
            if info['status'] == 'running'
        ]