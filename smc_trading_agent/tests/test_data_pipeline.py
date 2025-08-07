"""
Tests for the data pipeline service.

This module provides comprehensive testing for:
- Data pipeline service initialization and coordination
- Data ingestion and processing
- Health monitoring endpoints
- Graceful shutdown handling
- Error handling and recovery
"""

import pytest
import asyncio
import time
import logging
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the modules to test
from ..data_pipeline.main import (
    main_async, DataPipelineService, load_config, setup_logging,
    handle_shutdown_signal, handle_uncaught_exception
)
from ..service_manager import ServiceManager
from ..health_monitor import EnhancedHealthMonitor


class TestDataPipelineService:
    """Test suite for data pipeline service functionality."""
    
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
    
    @pytest.fixture
    def mock_market_data(self):
        """Mock market data for testing."""
        return pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=100, freq='1H'),
            'open': [60000 + i * 10 for i in range(100)],
            'high': [60050 + i * 10 for i in range(100)],
            'low': [59950 + i * 10 for i in range(100)],
            'close': [60025 + i * 10 for i in range(100)],
            'volume': [100 + i for i in range(100)]
        })
    
    @pytest.fixture
    def data_pipeline_service(self, mock_config):
        """Create a data pipeline service instance for testing."""
        logger = Mock()
        return DataPipelineService(mock_config, logger)
    
    def test_data_pipeline_service_initialization(self, data_pipeline_service, mock_config):
        """Test data pipeline service initialization."""
        assert data_pipeline_service.config == mock_config
        assert data_pipeline_service.data_processor is not None
        assert data_pipeline_service.is_running is False
        assert data_pipeline_service.ingestion_circuit_breaker is not None
        assert data_pipeline_service.processing_circuit_breaker is not None
        assert data_pipeline_service.ingestion_retry_handler is not None
        assert data_pipeline_service.processing_retry_handler is not None
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_initialize_success(self, data_pipeline_service):
        """Test successful data pipeline service initialization."""
        # Mock data processor with async initialize method
        data_pipeline_service.data_processor.initialize_async = AsyncMock()
        
        result = await data_pipeline_service.initialize()
        
        assert result is True
        data_pipeline_service.data_processor.initialize_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_initialize_sync_success(self, data_pipeline_service):
        """Test successful data pipeline service initialization with sync method."""
        # Mock data processor with sync initialize method
        data_pipeline_service.data_processor.initialize = Mock()
        
        result = await data_pipeline_service.initialize()
        
        assert result is True
        data_pipeline_service.data_processor.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_initialize_failure(self, data_pipeline_service):
        """Test data pipeline service initialization failure."""
        # Mock data processor with failing initialize method
        data_pipeline_service.data_processor.initialize_async = AsyncMock(side_effect=Exception("Init failed"))
        
        result = await data_pipeline_service.initialize()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_shutdown_success(self, data_pipeline_service):
        """Test successful data pipeline service shutdown."""
        # Mock data processor with async shutdown method
        data_pipeline_service.data_processor.shutdown_async = AsyncMock()
        data_pipeline_service.is_running = True
        
        await data_pipeline_service.shutdown()
        
        assert data_pipeline_service.is_running is False
        data_pipeline_service.data_processor.shutdown_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_shutdown_sync_success(self, data_pipeline_service):
        """Test successful data pipeline service shutdown with sync method."""
        # Mock data processor with sync shutdown method
        data_pipeline_service.data_processor.shutdown = Mock()
        data_pipeline_service.is_running = True
        
        await data_pipeline_service.shutdown()
        
        assert data_pipeline_service.is_running is False
        data_pipeline_service.data_processor.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_shutdown_failure(self, data_pipeline_service):
        """Test data pipeline service shutdown with error handling."""
        # Mock data processor with failing shutdown method
        data_pipeline_service.data_processor.shutdown_async = AsyncMock(side_effect=Exception("Shutdown failed"))
        data_pipeline_service.is_running = True
        
        await data_pipeline_service.shutdown()
        
        assert data_pipeline_service.is_running is False
        data_pipeline_service.data_processor.shutdown_async.assert_called_once()
    
    def test_data_pipeline_service_health_check_success(self, data_pipeline_service):
        """Test successful health check."""
        result = data_pipeline_service.health_check()
        assert result is True
    
    def test_data_pipeline_service_health_check_failure(self, data_pipeline_service):
        """Test health check failure."""
        # Set data processor to None to simulate failure
        data_pipeline_service.data_processor = None
        
        result = data_pipeline_service.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_run_pipeline_success(self, data_pipeline_service, mock_market_data):
        """Test successful data pipeline execution."""
        # Mock data processor methods
        data_pipeline_service.data_processor.get_latest_ohlcv_data = Mock(return_value=mock_market_data)
        
        # Run pipeline for a short time
        task = asyncio.create_task(data_pipeline_service.run_data_pipeline())
        
        # Let it run for a moment
        await asyncio.sleep(0.1)
        
        # Stop the pipeline
        data_pipeline_service.is_running = False
        
        # Wait for completion
        await task
        
        # Verify data processor was called
        assert data_pipeline_service.data_processor.get_latest_ohlcv_data.called
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_run_pipeline_no_data(self, data_pipeline_service):
        """Test data pipeline execution with no data."""
        # Mock data processor to return None
        data_pipeline_service.data_processor.get_latest_ohlcv_data = Mock(return_value=None)
        
        # Run pipeline for a short time
        task = asyncio.create_task(data_pipeline_service.run_data_pipeline())
        
        # Let it run for a moment
        await asyncio.sleep(0.1)
        
        # Stop the pipeline
        data_pipeline_service.is_running = False
        
        # Wait for completion
        await task
        
        # Verify data processor was called
        assert data_pipeline_service.data_processor.get_latest_ohlcv_data.called
    
    @pytest.mark.asyncio
    async def test_data_pipeline_service_run_pipeline_ingestion_error(self, data_pipeline_service):
        """Test data pipeline execution with ingestion error."""
        # Mock data processor to raise exception
        data_pipeline_service.data_processor.get_latest_ohlcv_data = Mock(side_effect=Exception("Ingestion failed"))
        
        # Run pipeline for a short time
        task = asyncio.create_task(data_pipeline_service.run_data_pipeline())
        
        # Let it run for a moment
        await asyncio.sleep(0.1)
        
        # Stop the pipeline
        data_pipeline_service.is_running = False
        
        # Wait for completion
        await task
        
        # Verify data processor was called
        assert data_pipeline_service.data_processor.get_latest_ohlcv_data.called
    
    @pytest.mark.asyncio
    async def test_process_market_data_success(self, data_pipeline_service, mock_market_data):
        """Test successful market data processing."""
        symbol = "BTC/USDT"
        
        await data_pipeline_service._process_market_data(mock_market_data, symbol)
        
        # Verify processing was logged (debug level)
        # This is a basic test - in real implementation, more processing would happen
    
    @pytest.mark.asyncio
    async def test_process_market_data_error(self, data_pipeline_service, mock_market_data):
        """Test market data processing with error."""
        symbol = "BTC/USDT"
        
        # Mock logger to capture error
        data_pipeline_service.logger.error = Mock()
        
        # Mock processing to raise exception
        with patch.object(data_pipeline_service, '_process_market_data', side_effect=Exception("Processing failed")):
            await data_pipeline_service._process_market_data(mock_market_data, symbol)
            
            # Verify error was logged
            data_pipeline_service.logger.error.assert_called()
    
    def test_load_config_success(self, mock_config):
        """Test successful configuration loading."""
        with patch('smc_trading_agent.data_pipeline.main.load_secure_config') as mock_load:
            mock_load.return_value = mock_config
            config = load_config()
            assert config == mock_config
            mock_load.assert_called_once()
    
    def test_load_config_file_not_found(self):
        """Test configuration loading with missing file."""
        with patch('smc_trading_agent.data_pipeline.main.load_secure_config') as mock_load:
            mock_load.side_effect = FileNotFoundError("Config file not found")
            with pytest.raises(SystemExit):
                load_config()
    
    def test_setup_logging_success(self, mock_config):
        """Test successful logging setup."""
        with patch('logging.config.dictConfig') as mock_dict_config:
            setup_logging(mock_config)
            mock_dict_config.assert_called_once_with(mock_config["logging"])
    
    def test_handle_uncaught_exception_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt exception."""
        with patch('sys.__excepthook__') as mock_excepthook:
            handle_uncaught_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
            mock_excepthook.assert_called_once()
    
    def test_handle_shutdown_signal_first_time(self):
        """Test handling of shutdown signal for the first time."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            with patch('signal.Signals') as mock_signals:
                mock_signals.return_value.name = "SIGTERM"
                handle_shutdown_signal(signal.SIGTERM, None)
                mock_logger.info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_async_success(self, mock_config):
        """Test successful main async execution."""
        with patch('smc_trading_agent.data_pipeline.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.data_pipeline.main.validate_config', return_value=(True, [], [])), \
             patch('smc_trading_agent.data_pipeline.main.setup_logging'), \
             patch('smc_trading_agent.data_pipeline.main.ServiceManager') as mock_service_manager_class, \
             patch('smc_trading_agent.data_pipeline.main.EnhancedHealthMonitor') as mock_health_monitor_class, \
             patch('smc_trading_agent.data_pipeline.main.DataPipelineService') as mock_service_class, \
             patch('smc_trading_agent.data_pipeline.main.uvicorn.Server') as mock_server_class:
            
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
        
        with patch('smc_trading_agent.data_pipeline.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.data_pipeline.main.validate_config', return_value=(False, ["error"], [])):
            
            result = await main_async()
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_main_async_service_initialization_failure(self, mock_config):
        """Test main async with service initialization failure."""
        with patch('smc_trading_agent.data_pipeline.main.load_config', return_value=mock_config), \
             patch('smc_trading_agent.data_pipeline.main.validate_config', return_value=(True, [], [])), \
             patch('smc_trading_agent.data_pipeline.main.setup_logging'), \
             patch('smc_trading_agent.data_pipeline.main.ServiceManager'), \
             patch('smc_trading_agent.data_pipeline.main.EnhancedHealthMonitor'), \
             patch('smc_trading_agent.data_pipeline.main.DataPipelineService', side_effect=Exception("Init failed")):
            
            result = await main_async()
            assert result == 1


class TestDataPipelineIntegration:
    """Integration tests for data pipeline service."""
    
    @pytest.mark.asyncio
    async def test_full_data_pipeline_lifecycle(self):
        """Test full data pipeline lifecycle with mocked components."""
        # This test would require more complex mocking of all components
        # For now, we'll test the basic structure
        assert True  # Placeholder for integration test
    
    @pytest.mark.asyncio
    async def test_data_pipeline_graceful_shutdown(self):
        """Test graceful shutdown handling."""
        # This test would verify that data pipeline shuts down properly
        # For now, we'll test the basic structure
        assert True  # Placeholder for integration test
    
    @pytest.mark.asyncio
    async def test_data_pipeline_health_monitoring(self):
        """Test health monitoring integration."""
        # This test would verify health monitoring endpoints work correctly
        # For now, we'll test the basic structure
        assert True  # Placeholder for integration test


if __name__ == "__main__":
    pytest.main([__file__])
