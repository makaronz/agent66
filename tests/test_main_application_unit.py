"""
Unit tests for main application orchestration logic.
Tests the core application flow, service coordination, and error handling.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np

from main import (
    load_config, 
    run_trading_agent, 
    handle_shutdown_signal,
    setup_logging,
    main_async
)


class TestConfigurationLoading:
    """Test suite for configuration loading functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        return {
            'app': {'name': 'smc-trading-agent', 'version': '1.0.0'},
            'logging': {
                'version': 1,
                'formatters': {
                    'default': {
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'default'
                    }
                },
                'root': {
                    'level': 'INFO',
                    'handlers': ['console']
                }
            },
            'database': {'url': 'postgresql://test:test@localhost/test'},
            'exchanges': {
                'binance': {'api_key': 'test_key', 'api_secret': 'test_secret'},
                'bybit': {'api_key': 'test_key', 'api_secret': 'test_secret'}
            },
            'decision_engine': {'confidence_threshold': 0.7},
            'monitoring': {'port': 8008}
        }
    
    @patch('main.load_secure_config')
    @patch('main.get_vault_client')
    async def test_load_config_success(self, mock_vault_client, mock_load_secure_config, mock_config):
        """Test successful configuration loading."""
        mock_load_secure_config.return_value = mock_config
        
        # Mock vault client
        mock_vault = Mock()
        mock_vault.get_database_config = Mock(return_value={
            'DATABASE_URL': 'postgresql://vault:vault@localhost/vault_db',
            'DATABASE_PASSWORD': 'vault_password'
        })
        mock_vault.get_exchange_config = Mock(return_value={
            'api_key': 'vault_api_key',
            'api_secret': 'vault_api_secret'
        })
        mock_vault.get_jwt_config = Mock(return_value={'jwt_secret': 'vault_jwt_secret'})
        mock_vault.get_redis_config = Mock(return_value={'redis_url': 'redis://vault:6379'})
        mock_vault_client.return_value = mock_vault
        
        config = await load_config('test_config.yaml')
        
        assert isinstance(config, dict)
        assert 'app' in config
        assert 'database' in config
        assert config['database']['url'] == 'postgresql://vault:vault@localhost/vault_db'
    
    @patch('main.load_secure_config')
    async def test_load_config_file_not_found(self, mock_load_secure_config):
        """Test configuration loading with file not found."""
        mock_load_secure_config.side_effect = FileNotFoundError("Config file not found")
        
        with pytest.raises(SystemExit):
            await load_config('nonexistent_config.yaml')
    
    @patch('main.load_secure_config')
    @patch('main.get_vault_client')
    async def test_load_config_vault_fallback(self, mock_vault_client, mock_load_secure_config, mock_config):
        """Test configuration loading with Vault fallback."""
        mock_load_secure_config.return_value = mock_config
        mock_vault_client.side_effect = Exception("Vault connection failed")
        
        # Should not raise exception, should fallback gracefully
        config = await load_config('test_config.yaml')
        
        assert isinstance(config, dict)
        assert config == mock_config  # Should return original config without Vault secrets


class TestApplicationOrchestration:
    """Test suite for main application orchestration logic."""
    
    @pytest.fixture
    def mock_service_manager(self):
        """Create mock service manager for testing."""
        service_manager = Mock()
        service_manager.is_shutdown_requested.return_value = False
        service_manager.get_service_health.return_value = {"overall_healthy": True}
        
        # Mock services
        data_processor = Mock()
        data_processor.get_latest_ohlcv_data = Mock(return_value=pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
            'open': np.random.uniform(49000, 51000, 100),
            'high': np.random.uniform(50000, 52000, 100),
            'low': np.random.uniform(48000, 50000, 100),
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }))
        
        smc_detector = Mock()
        smc_detector.detect_order_blocks = Mock(return_value=[
            {
                'timestamp': datetime.now(),
                'type': 'bullish',
                'price_level': (50000, 49900),
                'strength_volume': 5000
            }
        ])
        
        decision_engine = Mock()
        decision_engine.make_decision = Mock(return_value={
            'action': 'BUY',
            'symbol': 'BTC/USDT',
            'entry_price': 50000,
            'confidence': 0.8
        })
        
        risk_manager = Mock()
        risk_manager.calculate_stop_loss = Mock(return_value=49500)
        risk_manager.calculate_take_profit = Mock(return_value=50500)
        
        execution_engine = Mock()
        execution_engine.execute_trade = Mock(return_value=True)
        
        service_manager.get_service.side_effect = lambda name: {
            'data_processor': data_processor,
            'smc_detector': smc_detector,
            'decision_engine': decision_engine,
            'risk_manager': risk_manager,
            'execution_engine': execution_engine
        }[name]
        
        return service_manager
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        return {
            'decision_engine': {'confidence_threshold': 0.7},
            'app': {'name': 'test-app'}
        }
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger for testing."""
        return Mock(spec=logging.Logger)
    
    @patch('main.data_validator')
    @patch('main.CircuitBreaker')
    @patch('main.RetryHandler')
    async def test_run_trading_agent_successful_cycle(
        self, mock_retry_handler, mock_circuit_breaker, mock_data_validator,
        mock_service_manager, mock_config, mock_logger
    ):
        """Test successful trading agent cycle."""
        # Mock validators
        mock_data_validator.validate_market_data.return_value = (True, [])
        mock_data_validator.assess_data_quality.return_value = Mock(value='GOOD')
        mock_data_validator.validate_order_blocks.return_value = [{'test': 'block'}]
        mock_data_validator.validate_trade_signal.return_value = Mock(
            confidence=0.8, entry_price=50000, action='BUY'
        )
        
        # Mock circuit breakers and retry handlers
        mock_circuit_breaker.return_value.call.side_effect = lambda func: func()
        mock_retry_handler.return_value.call.side_effect = lambda func, *args: func(*args) if args else func()
        
        # Mock service manager to stop after one cycle
        call_count = 0
        def mock_shutdown_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Stop after first cycle
        
        mock_service_manager.is_shutdown_requested.side_effect = mock_shutdown_check
        
        # Run trading agent
        await run_trading_agent(mock_config, mock_service_manager, mock_logger)
        
        # Verify services were called
        data_processor = mock_service_manager.get_service('data_processor')
        smc_detector = mock_service_manager.get_service('smc_detector')
        decision_engine = mock_service_manager.get_service('decision_engine')
        risk_manager = mock_service_manager.get_service('risk_manager')
        execution_engine = mock_service_manager.get_service('execution_engine')
        
        data_processor.get_latest_ohlcv_data.assert_called()
        smc_detector.detect_order_blocks.assert_called()
        decision_engine.make_decision.assert_called()
        risk_manager.calculate_stop_loss.assert_called()
        risk_manager.calculate_take_profit.assert_called()
        execution_engine.execute_trade.assert_called()
    
    @patch('main.data_validator')
    @patch('main.CircuitBreaker')
    async def test_run_trading_agent_unhealthy_system(
        self, mock_circuit_breaker, mock_data_validator,
        mock_service_manager, mock_config, mock_logger
    ):
        """Test trading agent with unhealthy system."""
        # Mock unhealthy system
        mock_service_manager.get_service_health.return_value = {"overall_healthy": False}
        
        # Mock service manager to stop after one cycle
        call_count = 0
        def mock_shutdown_check():
            nonlocal call_count
            call_count += 1
            return call_count > 2  # Allow a few cycles
        
        mock_service_manager.is_shutdown_requested.side_effect = mock_shutdown_check
        
        # Run trading agent
        await run_trading_agent(mock_config, mock_service_manager, mock_logger)
        
        # Verify that data processing was skipped due to unhealthy system
        data_processor = mock_service_manager.get_service('data_processor')
        data_processor.get_latest_ohlcv_data.assert_not_called()
    
    @patch('main.data_validator')
    @patch('main.CircuitBreaker')
    async def test_run_trading_agent_data_validation_failure(
        self, mock_circuit_breaker, mock_data_validator,
        mock_service_manager, mock_config, mock_logger
    ):
        """Test trading agent with data validation failure."""
        # Mock data validation failure
        mock_data_validator.validate_market_data.return_value = (False, ['Invalid data'])
        
        # Mock circuit breaker
        mock_circuit_breaker.return_value.call.side_effect = lambda func: func()
        
        # Mock service manager to stop after one cycle
        call_count = 0
        def mock_shutdown_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1
        
        mock_service_manager.is_shutdown_requested.side_effect = mock_shutdown_check
        
        # Run trading agent
        await run_trading_agent(mock_config, mock_service_manager, mock_logger)
        
        # Verify that SMC detection was skipped due to validation failure
        smc_detector = mock_service_manager.get_service('smc_detector')
        smc_detector.detect_order_blocks.assert_not_called()
    
    @patch('main.data_validator')
    @patch('main.CircuitBreaker')
    async def test_run_trading_agent_low_confidence_signal(
        self, mock_circuit_breaker, mock_data_validator,
        mock_service_manager, mock_config, mock_logger
    ):
        """Test trading agent with low confidence trade signal."""
        # Mock validators
        mock_data_validator.validate_market_data.return_value = (True, [])
        mock_data_validator.assess_data_quality.return_value = Mock(value='GOOD')
        mock_data_validator.validate_order_blocks.return_value = [{'test': 'block'}]
        mock_data_validator.validate_trade_signal.return_value = Mock(
            confidence=0.5, entry_price=50000, action='BUY'  # Low confidence
        )
        
        # Mock circuit breaker
        mock_circuit_breaker.return_value.call.side_effect = lambda func: func()
        
        # Mock service manager to stop after one cycle
        call_count = 0
        def mock_shutdown_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1
        
        mock_service_manager.is_shutdown_requested.side_effect = mock_shutdown_check
        
        # Run trading agent
        await run_trading_agent(mock_config, mock_service_manager, mock_logger)
        
        # Verify that execution was skipped due to low confidence
        execution_engine = mock_service_manager.get_service('execution_engine')
        execution_engine.execute_trade.assert_not_called()
    
    @patch('main.data_validator')
    @patch('main.CircuitBreaker')
    async def test_run_trading_agent_exception_handling(
        self, mock_circuit_breaker, mock_data_validator,
        mock_service_manager, mock_config, mock_logger
    ):
        """Test trading agent exception handling."""
        # Mock data processor to raise exception
        data_processor = mock_service_manager.get_service('data_processor')
        data_processor.get_latest_ohlcv_data.side_effect = Exception("Data processing failed")
        
        # Mock circuit breaker to propagate exception
        mock_circuit_breaker.return_value.call.side_effect = lambda func: func()
        
        # Mock service manager to stop after one cycle
        call_count = 0
        def mock_shutdown_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1
        
        mock_service_manager.is_shutdown_requested.side_effect = mock_shutdown_check
        
        # Run trading agent - should handle exception gracefully
        await run_trading_agent(mock_config, mock_service_manager, mock_logger)
        
        # Verify error was logged
        mock_logger.error.assert_called()


class TestSignalHandling:
    """Test suite for signal handling functionality."""
    
    def test_handle_shutdown_signal_first_call(self):
        """Test first shutdown signal handling."""
        import main
        main.shutdown_flag = False
        
        # Mock signal and frame
        signum = 15  # SIGTERM
        frame = Mock()
        
        handle_shutdown_signal(signum, frame)
        
        assert main.shutdown_flag is True
    
    def test_handle_shutdown_signal_second_call(self):
        """Test second shutdown signal handling."""
        import main
        main.shutdown_flag = True
        
        # Mock signal and frame
        signum = 15  # SIGTERM
        frame = Mock()
        
        with pytest.raises(SystemExit):
            handle_shutdown_signal(signum, frame)


class TestLoggingSetup:
    """Test suite for logging setup functionality."""
    
    def test_setup_logging_success(self):
        """Test successful logging setup."""
        config = {
            'logging': {
                'version': 1,
                'formatters': {
                    'default': {
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'default'
                    }
                },
                'root': {
                    'level': 'INFO',
                    'handlers': ['console']
                }
            }
        }
        
        # Should not raise exception
        setup_logging(config)
        
        # Verify logging is configured
        logger = logging.getLogger('test')
        assert logger.isEnabledFor(logging.INFO)
    
    def test_setup_logging_invalid_config(self):
        """Test logging setup with invalid configuration."""
        invalid_config = {
            'logging': {
                'invalid_key': 'invalid_value'
            }
        }
        
        with pytest.raises(SystemExit):
            setup_logging(invalid_config)


class TestMainAsyncFunction:
    """Test suite for main async function."""
    
    @patch('main.load_config')
    @patch('main.validate_config')
    @patch('main.setup_logging')
    @patch('main.ServiceManager')
    @patch('main.EnhancedHealthMonitor')
    @patch('main.MarketDataProcessor')
    @patch('main.SMCIndicators')
    @patch('main.AdaptiveModelSelector')
    @patch('main.SMCRiskManager')
    @patch('main.ExecutionEngine')
    @patch('main.uvicorn.Server')
    async def test_main_async_success(
        self, mock_server, mock_execution_engine, mock_risk_manager,
        mock_model_selector, mock_smc_indicators, mock_data_processor,
        mock_health_monitor, mock_service_manager, mock_setup_logging,
        mock_validate_config, mock_load_config
    ):
        """Test successful main async execution."""
        # Mock configuration loading
        mock_config = {
            'app': {'name': 'test-app'},
            'monitoring': {'port': 8008}
        }
        mock_load_config.return_value = mock_config
        mock_validate_config.return_value = (True, [], [])
        
        # Mock service manager
        mock_sm_instance = Mock()
        mock_sm_instance.service_lifecycle.return_value.__aenter__ = AsyncMock()
        mock_sm_instance.service_lifecycle.return_value.__aexit__ = AsyncMock()
        mock_service_manager.return_value = mock_sm_instance
        
        # Mock health monitor
        mock_hm_instance = Mock()
        mock_hm_instance.start_background_health_checks = AsyncMock()
        mock_hm_instance.get_fastapi_app.return_value = Mock()
        mock_hm_instance.shutdown = AsyncMock()
        mock_health_monitor.return_value = mock_hm_instance
        
        # Mock server
        mock_server_instance = Mock()
        mock_server_instance.serve = AsyncMock()
        mock_server.return_value = mock_server_instance
        
        # Mock component initialization
        mock_data_processor.return_value = Mock()
        mock_smc_indicators.return_value = Mock()
        mock_model_selector.return_value = Mock()
        mock_risk_manager.return_value = Mock()
        mock_execution_engine.return_value = Mock()
        
        # Mock run_trading_agent to complete quickly
        with patch('main.run_trading_agent', new_callable=AsyncMock) as mock_run_trading:
            mock_run_trading.return_value = None
            
            result = await main_async()
        
        assert result == 0
        mock_load_config.assert_called_once()
        mock_validate_config.assert_called_once()
        mock_setup_logging.assert_called_once()
    
    @patch('main.load_config')
    @patch('main.validate_config')
    async def test_main_async_config_validation_failure(self, mock_validate_config, mock_load_config):
        """Test main async with configuration validation failure."""
        mock_load_config.return_value = {}
        mock_validate_config.return_value = (False, ['Config error'], [])
        
        result = await main_async()
        
        assert result == 1
    
    @patch('main.load_config')
    @patch('main.validate_config')
    @patch('main.setup_logging')
    @patch('main.ServiceManager')
    async def test_main_async_service_initialization_failure(
        self, mock_service_manager, mock_setup_logging, mock_validate_config, mock_load_config
    ):
        """Test main async with service initialization failure."""
        mock_load_config.return_value = {'app': {'name': 'test'}}
        mock_validate_config.return_value = (True, [], [])
        
        # Mock service manager to raise exception during initialization
        mock_service_manager.side_effect = Exception("Service initialization failed")
        
        result = await main_async()
        
        assert result == 1


class TestErrorHandlingIntegration:
    """Integration tests for error handling throughout the application."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components with various failure modes."""
        components = {}
        
        # Data processor with intermittent failures
        data_processor = Mock()
        data_processor.get_latest_ohlcv_data = Mock()
        components['data_processor'] = data_processor
        
        # SMC detector with validation errors
        smc_detector = Mock()
        smc_detector.detect_order_blocks = Mock()
        components['smc_detector'] = smc_detector
        
        # Decision engine with confidence variations
        decision_engine = Mock()
        decision_engine.make_decision = Mock()
        components['decision_engine'] = decision_engine
        
        # Risk manager with calculation errors
        risk_manager = Mock()
        risk_manager.calculate_stop_loss = Mock()
        risk_manager.calculate_take_profit = Mock()
        components['risk_manager'] = risk_manager
        
        # Execution engine with execution failures
        execution_engine = Mock()
        execution_engine.execute_trade = Mock()
        components['execution_engine'] = execution_engine
        
        return components
    
    @patch('main.CircuitBreaker')
    @patch('main.RetryHandler')
    async def test_circuit_breaker_integration(self, mock_retry_handler, mock_circuit_breaker, mock_components):
        """Test circuit breaker integration with component failures."""
        # Mock circuit breaker to track calls
        circuit_breaker_calls = []
        def mock_cb_call(func):
            circuit_breaker_calls.append(func.__name__ if hasattr(func, '__name__') else 'lambda')
            return func()
        
        mock_circuit_breaker.return_value.call.side_effect = mock_cb_call
        mock_retry_handler.return_value.call.side_effect = lambda func, *args: func(*args) if args else func()
        
        # Create service manager mock
        service_manager = Mock()
        service_manager.is_shutdown_requested.side_effect = [False, True]  # One cycle
        service_manager.get_service_health.return_value = {"overall_healthy": True}
        service_manager.get_service.side_effect = lambda name: mock_components[name]
        
        # Mock data validation
        with patch('main.data_validator') as mock_validator:
            mock_validator.validate_market_data.return_value = (True, [])
            mock_validator.assess_data_quality.return_value = Mock(value='GOOD')
            mock_validator.validate_order_blocks.return_value = [{'test': 'block'}]
            mock_validator.validate_trade_signal.return_value = Mock(
                confidence=0.8, entry_price=50000, action='BUY'
            )
            
            # Configure components to return valid data
            mock_components['data_processor'].get_latest_ohlcv_data.return_value = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=10, freq='1H'),
                'open': [50000] * 10,
                'high': [50100] * 10,
                'low': [49900] * 10,
                'close': [50050] * 10,
                'volume': [1000] * 10
            })
            mock_components['smc_detector'].detect_order_blocks.return_value = [{'test': 'block'}]
            mock_components['decision_engine'].make_decision.return_value = {
                'action': 'BUY', 'confidence': 0.8, 'entry_price': 50000
            }
            mock_components['risk_manager'].calculate_stop_loss.return_value = 49500
            mock_components['risk_manager'].calculate_take_profit.return_value = 50500
            
            config = {'decision_engine': {'confidence_threshold': 0.7}}
            logger = Mock()
            
            # Run trading agent
            await run_trading_agent(config, service_manager, logger)
            
            # Verify circuit breakers were used
            assert len(circuit_breaker_calls) > 0
    
    async def test_graceful_degradation(self, mock_components):
        """Test graceful degradation when components fail."""
        # Configure components to fail at different stages
        mock_components['data_processor'].get_latest_ohlcv_data.side_effect = Exception("Data unavailable")
        
        service_manager = Mock()
        service_manager.is_shutdown_requested.side_effect = [False, True]  # One cycle
        service_manager.get_service_health.return_value = {"overall_healthy": True}
        service_manager.get_service.side_effect = lambda name: mock_components[name]
        
        with patch('main.CircuitBreaker') as mock_cb, \
             patch('main.RetryHandler') as mock_rh:
            
            # Circuit breaker propagates exception
            mock_cb.return_value.call.side_effect = lambda func: func()
            mock_rh.return_value.call.side_effect = lambda func, *args: func(*args) if args else func()
            
            config = {'decision_engine': {'confidence_threshold': 0.7}}
            logger = Mock()
            
            # Should handle exception gracefully and continue
            await run_trading_agent(config, service_manager, logger)
            
            # Verify error was logged but application continued
            logger.error.assert_called()
            
            # Verify downstream components were not called due to early failure
            mock_components['smc_detector'].detect_order_blocks.assert_not_called()


@pytest.mark.unit
class TestApplicationLifecycle:
    """Test suite for complete application lifecycle."""
    
    @patch('main.signal.signal')
    @patch('main.asyncio.run')
    def test_main_function_signal_setup(self, mock_asyncio_run, mock_signal):
        """Test main function signal setup."""
        from main import main
        
        mock_asyncio_run.return_value = 0
        
        result = main()
        
        assert result == 0
        # Verify signals were registered
        assert mock_signal.call_count >= 2  # SIGINT and SIGTERM
        mock_asyncio_run.assert_called_once()
    
    @patch('main.signal.signal')
    @patch('main.asyncio.run')
    def test_main_function_keyboard_interrupt(self, mock_asyncio_run, mock_signal):
        """Test main function keyboard interrupt handling."""
        from main import main
        
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        
        result = main()
        
        assert result == 0  # Should handle gracefully
    
    @patch('main.signal.signal')
    @patch('main.asyncio.run')
    def test_main_function_unexpected_exception(self, mock_asyncio_run, mock_signal):
        """Test main function unexpected exception handling."""
        from main import main
        
        mock_asyncio_run.side_effect = Exception("Unexpected error")
        
        result = main()
        
        assert result == 1  # Should return error code