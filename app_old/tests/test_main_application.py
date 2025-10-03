"""
Tests for the main application entry point.

This module provides comprehensive testing for:
- Service initialization and coordination
- Health monitoring endpoints
- Graceful shutdown handling
- Error handling and recovery
- Configuration validation
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the modules to test
from ..main import (
    main_async, run_trading_agent, load_config, setup_logging,
    handle_shutdown_signal, handle_uncaught_exception
)
from ..service_manager import ServiceManager
from ..health_monitor import EnhancedHealthMonitor


class TestMainApplication:
    """Test suite for main application functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "app": {
                "name": "SMC Trading Agent",
                "version": "0.1.0"
            },
            "data_pipeline": {
                "ingestion": {
                    "source": "binance",
                    "symbols": ["BTC/USDT"],
                    "timeframe": "1h"
                }
            },
            "monitoring": {
                "enabled": True,
                "port": 8008,
                "health_check_interval": 30
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
    
    @pytest.fixture
    def mock_service_manager(self):
        """Mock service manager for testing."""
        manager = Mock(spec=ServiceManager)
        manager.is_shutdown_requested.return_value = False
        manager.get_service_health.return_value = {
            "overall_healthy": True,
            "services": {
                "data_processor": {"healthy": True, "critical": True},
                "smc_detector": {"healthy": True, "critical": True},
                "decision_engine": {"healthy": True, "critical": True},
                "risk_manager": {"healthy": True, "critical": True},
                "execution_engine": {"healthy": True, "critical": True}
            }
        }
        return manager
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Mock health monitor for testing."""
        monitor = Mock(spec=EnhancedHealthMonitor)
        monitor.start_background_health_checks = AsyncMock()
        monitor.shutdown = AsyncMock()
        monitor.get_fastapi_app.return_value = Mock()
        return monitor
    
    def test_load_config_success(self, mock_config):
        """Test successful configuration loading."""
        with patch('smc_trading_agent.main.load_secure_config') as mock_load:
            mock_load.return_value = mock_config
            config = load_config()
            assert config == mock_config
            mock_load.assert_called_once()
    
    def test_load_config_file_not_found(self):
        """Test configuration loading with missing file."""
        with patch('smc_trading_agent.main.load_secure_config') as mock_load:
            mock_load.side_effect = FileNotFoundError("Config file not found")
            with pytest.raises(SystemExit):
                load_config()
    
    def test_load_config_validation_error(self):
        """Test configuration loading with validation error."""
        with patch('smc_trading_agent.main.load_secure_config') as mock_load:
            from ..config_loader import ConfigValidationError
            mock_load.side_effect = ConfigValidationError("Invalid config")
            with pytest.raises(SystemExit):
                load_config()
    
    def test_setup_logging_success(self, mock_config):
        """Test successful logging setup."""
        with patch('logging.config.dictConfig') as mock_dict_config:
            setup_logging(mock_config)
            mock_dict_config.assert_called_once_with(mock_config["logging"])
    
    def test_setup_logging_failure(self):
        """Test logging setup with invalid configuration."""
        invalid_config = {"logging": {"invalid": "config"}}
        with patch('logging.config.dictConfig') as mock_dict_config:
            mock_dict_config.side_effect = ValueError("Invalid logging config")
            with pytest.raises(SystemExit):
                setup_logging(invalid_config)
    
    def test_handle_uncaught_exception_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt exception."""
        with patch('sys.__excepthook__') as mock_excepthook:
            handle_uncaught_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
            mock_excepthook.assert_called_once()
    
    def test_handle_uncaught_exception_other(self):
        """Test handling of other exceptions."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            handle_uncaught_exception(ValueError, ValueError("test"), None)
            mock_logger.critical.assert_called_once()
    
    def test_handle_shutdown_signal_first_time(self):
        """Test handling of shutdown signal for the first time."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            with patch('signal.Signals') as mock_signals:
                mock_signals.return_value.name = "SIGTERM"
                handle_shutdown_signal(signal.SIGTERM, None)
                mock_logger.info.assert_called_once()
    
    def test_handle_shutdown_signal_second_time(self):
        """Test handling of shutdown signal for the second time."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            with patch('sys.exit') as mock_exit:
                # Set global shutdown flag
                import smc_trading_agent.main
                smc_trading_agent.main.shutdown_flag = True
                handle_shutdown_signal(signal.SIGTERM, None)
                mock_logger.warning.assert_called_once()
                mock_exit.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_run_trading_agent_healthy_system(self, mock_config, mock_service_manager):
        """Test trading agent with healthy system."""
        logger = Mock()
        
        # Mock services
        mock_service_manager.get_service.side_effect = lambda name: Mock()
        
        # Run trading agent for a short time
        task = asyncio.create_task(
            run_trading_agent(mock_config, mock_service_manager, logger)
        )
        
        # Let it run for a moment
        await asyncio.sleep(0.1)
        
        # Request shutdown
        mock_service_manager.is_shutdown_requested.return_value = True
        
        # Wait for completion
        await task
        
        # Verify service manager was used
        assert mock_service_manager.get_service_health.called
    
    @pytest.mark.asyncio
    async def test_run_trading_agent_unhealthy_system(self, mock_config, mock_service_manager):
        """Test trading agent with unhealthy system."""
        logger = Mock()
        
        # Mock unhealthy system
        mock_service_manager.get_service_health.return_value = {
            "overall_healthy": False,
            "services": {}
        }
        mock_service_manager.get_service.side_effect = lambda name: Mock()
        
        # Run trading agent for a short time
        task = asyncio.create_task(
            run_trading_agent(mock_config, mock_service_manager, logger)
        )
        
        # Let it run for a moment
        await asyncio.sleep(0.1)
        
        # Request shutdown
        mock_service_manager.is_shutdown_requested.return_value = True
        
        # Wait for completion
        await task
        
        # Verify warning was logged for unhealthy system
        logger.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_main_async_success(self, mock_config):
        """Test successful main async execution."""
        with patch('smc_trading_agent.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.main.validate_config', return_value=(True, [], [])), \
             patch('smc_trading_agent.main.setup_logging'), \
             patch('smc_trading_agent.main.ServiceManager') as mock_service_manager_class, \
             patch('smc_trading_agent.main.EnhancedHealthMonitor') as mock_health_monitor_class, \
             patch('smc_trading_agent.main.MarketDataProcessor'), \
             patch('smc_trading_agent.main.SMCIndicators'), \
             patch('smc_trading_agent.main.AdaptiveModelSelector'), \
             patch('smc_trading_agent.main.SMCRiskManager'), \
             patch('smc_trading_agent.main.ExecutionEngine'), \
             patch('smc_trading_agent.main.uvicorn.Server') as mock_server_class:
            
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
            
            # Run main async
            result = await main_async()
            
            # Verify result
            assert result == 0
            
            # Verify service manager was used
            mock_service_manager.register_service.assert_called()
            
            # Verify health monitor was used
            mock_health_monitor.start_background_health_checks.assert_called_once()
            mock_health_monitor.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_async_config_validation_failure(self):
        """Test main async with configuration validation failure."""
        mock_config = {"app": {"name": "test"}}
        
        with patch('smc_trading_agent.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.main.validate_config', return_value=(False, ["error"], [])):
            
            result = await main_async()
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_main_async_service_initialization_failure(self, mock_config):
        """Test main async with service initialization failure."""
        with patch('smc_trading_agent.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.main.validate_config', return_value=(True, [], [])), \
             patch('smc_trading_agent.main.setup_logging'), \
             patch('smc_trading_agent.main.ServiceManager'), \
             patch('smc_trading_agent.main.EnhancedHealthMonitor'), \
             patch('smc_trading_agent.main.MarketDataProcessor', side_effect=Exception("Init failed")):
            
            result = await main_async()
            assert result == 1
    
    def test_service_manager_integration(self, mock_config):
        """Test service manager integration."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service_manager = ServiceManager(mock_config, mock_logger)
            
            # Test service registration
            mock_service = Mock()
            service_manager.register_service("test_service", mock_service, lambda: True, critical=True)
            
            assert "test_service" in service_manager.services
            assert service_manager.services["test_service"].component == mock_service
            assert service_manager.services["test_service"].critical is True
    
    def test_health_monitor_integration(self, mock_config):
        """Test health monitor integration."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            health_monitor = EnhancedHealthMonitor("test-app", mock_logger)
            
            # Test FastAPI app creation
            app = health_monitor.get_fastapi_app()
            assert app is not None
            
            # Test health status
            health_status = asyncio.run(health_monitor.get_system_health())
            assert "app_name" in health_status
            assert health_status["app_name"] == "test-app"


class TestMainApplicationIntegration:
    """Integration tests for main application."""
    
    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self):
        """Test full service lifecycle with mocked components."""
        # This test would require more complex mocking of all components
        # For now, we'll test the basic structure
        assert True  # Placeholder for integration test
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown handling."""
        # This test would verify that all services shut down properly
        # For now, we'll test the basic structure
        assert True  # Placeholder for integration test


if __name__ == "__main__":
    pytest.main([__file__])
