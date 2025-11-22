"""
Integration tests for SMC Trading Agent services.

This module provides comprehensive integration testing for:
- Service coordination between main application and data pipeline
- Health monitoring integration
- Graceful shutdown coordination
- Error handling and recovery across services
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the modules to test
from ..main import main_async as main_app_async
from ..data_pipeline.main import main_async as data_pipeline_async
from ..service_manager import ServiceManager
from ..health_monitor import EnhancedHealthMonitor


class TestServiceIntegration:
    """Integration tests for service coordination."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for integration testing."""
        return {
            "app": {
                "name": "SMC Trading Agent",
                "version": "0.1.0"
            },
            "data_pipeline": {
                "ingestion": {
                    "source": "binance",
                    "symbols": ["BTC/USDT", "ETH/USDT"],
                    "timeframe": "1h",
                    "batch_size": 100,
                    "retry_attempts": 3,
                    "retry_delay": 5.0
                },
                "processing": {
                    "enable_real_time": True,
                    "processing_interval": 60,
                    "max_processing_time": 30.0
                },
                "storage": {
                    "database_url": "postgresql://test:test@localhost/test",
                    "enable_caching": True,
                    "cache_ttl": 300
                }
            },
            "monitoring": {
                "enabled": True,
                "port": 8008,
                "health_check_interval": 30,
                "data_pipeline": {
                    "port": 8009,
                    "health_check_interval": 30,
                    "metrics_enabled": True
                }
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "json_formatter": {
                        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                        "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "json_formatter",
                        "level": "INFO",
                        "stream": "ext://sys.stdout"
                    }
                },
                "root": {
                    "handlers": ["console"],
                    "level": "INFO"
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_service_manager_lifecycle(self, mock_config):
        """Test service manager lifecycle with multiple services."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            
            # Register multiple services
            mock_service1 = Mock()
            mock_service2 = Mock()
            
            service_manager.register_service("service1", mock_service1, lambda: True, critical=True)
            service_manager.register_service("service2", mock_service2, lambda: True, critical=False)
            
            # Test service registration
            assert len(service_manager.services) == 2
            assert "service1" in service_manager.services
            assert "service2" in service_manager.services
            assert service_manager.services["service1"].critical is True
            assert service_manager.services["service2"].critical is False
            
            # Test service retrieval
            assert service_manager.get_service("service1") == mock_service1
            assert service_manager.get_service("service2") == mock_service2
            assert service_manager.get_service("nonexistent") is None
            
            # Test service listing
            services = service_manager.list_services()
            assert "service1" in services
            assert "service2" in services
            assert len(services) == 2
    
    @pytest.mark.asyncio
    async def test_health_monitor_integration(self, mock_config):
        """Test health monitor integration with service manager."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            health_monitor = EnhancedHealthMonitor("test-app", mock_logger)
            
            # Test health status
            health_status = await health_monitor.get_system_health()
            assert "app_name" in health_status
            assert health_status["app_name"] == "test-app"
            assert "overall_healthy" in health_status
            assert "services" in health_status
            
            # Test detailed health
            detailed_health = await health_monitor.get_detailed_health()
            assert "app_name" in detailed_health
            assert "services" in detailed_health
    
    @pytest.mark.asyncio
    async def test_service_coordination_initialization(self, mock_config):
        """Test service coordination during initialization."""
        with patch('main.load_config', return_value=mock_config), \
             patch('main.validate_config', return_value=(True, [], [])), \
             patch('main.setup_logging'), \
             patch('main.ServiceManager') as mock_service_manager_class, \
             patch('main.EnhancedHealthMonitor') as mock_health_monitor_class, \
             patch('main.MarketDataProcessor'), \
             patch('main.SMCIndicators'), \
             patch('main.AdaptiveModelSelector'), \
             patch('main.SMCRiskManager'), \
             patch('main.ExecutionEngine'), \
             patch('main.uvicorn.Server') as mock_server_class:
            
            # Mock service manager
            mock_service_manager = Mock()
            mock_service_manager_class.return_value = mock_service_manager
            mock_service_manager.service_lifecycle.return_value.__aenter__ = AsyncMock()
            mock_service_manager.service_lifecycle.return_value.__aexit__ = AsyncMock()
            
            # Mock health monitor
            mock_health_monitor = Mock()
            mock_health_monitor_class.return_value = mock_health_monitor
            mock_health_monitor.start_background_health_checks = AsyncMock()
            mock_health_monitor.shutdown = AsyncMock()
            mock_health_monitor.get_fastapi_app.return_value = Mock()
            
            # Mock server
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.serve = AsyncMock()
            
            # Run main application
            result = await main_app_async()
            
            # Verify coordination
            assert result == 0
            mock_service_manager.register_service.assert_called()
            mock_health_monitor.start_background_health_checks.assert_called_once()
            mock_health_monitor.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_pipeline_coordination(self, mock_config):
        """Test data pipeline service coordination."""
        with patch('data_pipeline.main.load_config', return_value=mock_config), \
             patch('data_pipeline.main.validate_config', return_value=(True, [], [])), \
             patch('data_pipeline.main.setup_logging'), \
             patch('data_pipeline.main.ServiceManager') as mock_service_manager_class, \
             patch('data_pipeline.main.EnhancedHealthMonitor') as mock_health_monitor_class, \
             patch('data_pipeline.main.DataPipelineService') as mock_service_class, \
             patch('data_pipeline.main.uvicorn.Server') as mock_server_class:
            
            # Mock service manager
            mock_service_manager = Mock()
            mock_service_manager_class.return_value = mock_service_manager
            mock_service_manager.service_lifecycle.return_value.__aenter__ = AsyncMock()
            mock_service_manager.service_lifecycle.return_value.__aexit__ = AsyncMock()
            
            # Mock health monitor
            mock_health_monitor = Mock()
            mock_health_monitor_class.return_value = mock_health_monitor
            mock_health_monitor.start_background_health_checks = AsyncMock()
            mock_health_monitor.shutdown = AsyncMock()
            mock_health_monitor.get_fastapi_app.return_value = Mock()
            
            # Mock data pipeline service
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock server
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            mock_server.serve = AsyncMock()
            
            # Run data pipeline
            result = await data_pipeline_async()
            
            # Verify coordination
            assert result == 0
            mock_service_manager.register_service.assert_called()
            mock_health_monitor.start_background_health_checks.assert_called_once()
            mock_health_monitor.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_coordination(self, mock_config):
        """Test graceful shutdown coordination between services."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            
            # Register services with shutdown methods
            mock_service1 = Mock()
            mock_service1.shutdown_async = AsyncMock()
            mock_service2 = Mock()
            mock_service2.shutdown = Mock()
            
            service_manager.register_service("service1", mock_service1, lambda: True, critical=True)
            service_manager.register_service("service2", mock_service2, lambda: True, critical=False)
            
            # Test graceful shutdown
            await service_manager.shutdown_services()
            
            # Verify services were shut down
            mock_service1.shutdown_async.assert_called_once()
            mock_service2.shutdown.assert_called_once()
            assert service_manager.is_shutdown_requested() is True
    
    @pytest.mark.asyncio
    async def test_health_monitoring_coordination(self, mock_config):
        """Test health monitoring coordination across services."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            health_monitor = EnhancedHealthMonitor("test-app", mock_logger)
            
            # Register services
            mock_service1 = Mock()
            mock_service2 = Mock()
            
            service_manager.register_service("service1", mock_service1, lambda: True, critical=True)
            service_manager.register_service("service2", mock_service2, lambda: False, critical=False)
            
            # Test health status
            health_status = service_manager.get_service_health()
            assert "overall_healthy" in health_status
            assert "services" in health_status
            assert "service1" in health_status["services"]
            assert "service2" in health_status["services"]
            
            # Test system health
            system_health = await health_monitor.get_system_health()
            assert "app_name" in system_health
            assert "overall_healthy" in system_health
    
    @pytest.mark.asyncio
    async def test_error_handling_coordination(self, mock_config):
        """Test error handling coordination across services."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            
            # Register service with failing health check
            mock_service = Mock()
            failing_health_check = Mock(side_effect=Exception("Health check failed"))
            
            service_manager.register_service("failing_service", mock_service, failing_health_check, critical=True)
            
            # Test health status with failing service
            health_status = service_manager.get_service_health()
            assert health_status["overall_healthy"] is False
            assert "failing_service" in health_status["services"]
            assert health_status["services"]["failing_service"]["healthy"] is False
            assert "error" in health_status["services"]["failing_service"]
    
    @pytest.mark.asyncio
    async def test_service_dependency_management(self, mock_config):
        """Test service dependency management."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            
            # Register services with different timeouts
            mock_service1 = Mock()
            mock_service2 = Mock()
            
            service_manager.register_service(
                "service1", mock_service1, lambda: True, 
                critical=True, startup_timeout=10.0, shutdown_timeout=5.0
            )
            service_manager.register_service(
                "service2", mock_service2, lambda: True, 
                critical=False, startup_timeout=30.0, shutdown_timeout=15.0
            )
            
            # Verify timeout configuration
            assert service_manager.services["service1"].startup_timeout == 10.0
            assert service_manager.services["service1"].shutdown_timeout == 5.0
            assert service_manager.services["service2"].startup_timeout == 30.0
            assert service_manager.services["service2"].shutdown_timeout == 15.0


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self):
        """Test full service lifecycle with all components."""
        # This test would require running actual services
        # For now, we'll test the basic structure
        assert True  # Placeholder for end-to-end test
    
    @pytest.mark.asyncio
    async def test_service_communication(self):
        """Test communication between services."""
        # This test would verify inter-service communication
        # For now, we'll test the basic structure
        assert True  # Placeholder for communication test
    
    @pytest.mark.asyncio
    async def test_fault_tolerance(self):
        """Test fault tolerance across services."""
        # This test would verify fault tolerance mechanisms
        # For now, we'll test the basic structure
        assert True  # Placeholder for fault tolerance test


if __name__ == "__main__":
    pytest.main([__file__])
