"""
Comprehensive test suite for exchange failover functionality.

Tests failover logic, health monitoring, recovery strategies, and integration
with the production exchange factory.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from data_pipeline.exchange_connectors.production_config import ExchangeType, Environment
from data_pipeline.exchange_connectors.failover_manager import (
    ExchangeFailoverManager,
    FailoverTrigger,
    FailoverState,
    FailoverRule,
    ExchangeHealthMetrics,
    FailoverEvent
)
from data_pipeline.exchange_connectors.failover_integration import (
    ProductionFailoverFactory,
    FailoverEnabledExchangeConnector,
    FailoverAwareDataPipeline
)
from data_pipeline.exchange_connectors.error_handling import ExchangeError, ErrorCategory, ErrorSeverity


class TestExchangeHealthMetrics:
    """Test exchange health metrics functionality."""
    
    def test_health_metrics_initialization(self):
        """Test health metrics initialization."""
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        
        assert metrics.exchange_type == ExchangeType.BINANCE
        assert not metrics.is_connected
        assert metrics.consecutive_failures == 0
        assert metrics.success_rate_1min == 100.0
        assert metrics.get_health_score() == 0.0  # Not connected
    
    def test_update_request_result_success(self):
        """Test updating metrics with successful request."""
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        metrics.is_connected = True
        
        metrics.update_request_result(True, 50.0)
        
        assert metrics.successful_requests == 1
        assert metrics.total_requests == 1
        assert metrics.consecutive_failures == 0
        assert metrics.average_latency_ms == 50.0
        assert metrics.get_health_score() > 80.0  # Should be high
    
    def test_update_request_result_failure(self):
        """Test updating metrics with failed request."""
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        metrics.is_connected = True
        
        metrics.update_request_result(False)
        
        assert metrics.failed_requests == 1
        assert metrics.total_requests == 1
        assert metrics.consecutive_failures == 1
        assert metrics.get_health_score() < 100.0  # Should be reduced
    
    def test_health_score_calculation(self):
        """Test health score calculation with various conditions."""
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        
        # Disconnected should give 0 score
        assert metrics.get_health_score() == 0.0
        
        # Connected with good metrics
        metrics.is_connected = True
        metrics.success_rate_5min = 95.0
        metrics.average_latency_ms = 100.0
        metrics.data_quality_score = 90.0
        
        score = metrics.get_health_score()
        assert 80.0 <= score <= 100.0
        
        # High latency should reduce score
        metrics.average_latency_ms = 2000.0
        score_high_latency = metrics.get_health_score()
        assert score_high_latency < score
        
        # Consecutive failures should reduce score
        metrics.consecutive_failures = 5
        score_with_failures = metrics.get_health_score()
        assert score_with_failures < score_high_latency


class TestFailoverRules:
    """Test failover rule functionality."""
    
    def test_connection_failure_rule(self):
        """Test connection failure rule triggering."""
        rule = FailoverRule(
            trigger=FailoverTrigger.CONNECTION_FAILURE,
            threshold=1
        )
        
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        
        # Should not trigger when connected
        metrics.is_connected = True
        assert not rule.should_trigger(metrics)
        
        # Should trigger when disconnected
        metrics.is_connected = False
        assert rule.should_trigger(metrics)
    
    def test_high_latency_rule(self):
        """Test high latency rule triggering."""
        rule = FailoverRule(
            trigger=FailoverTrigger.HIGH_LATENCY,
            threshold=1000.0
        )
        
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        
        # Should not trigger with low latency
        metrics.average_latency_ms = 100.0
        assert not rule.should_trigger(metrics)
        
        # Should trigger with high latency
        metrics.average_latency_ms = 1500.0
        assert rule.should_trigger(metrics)
    
    def test_api_error_rule(self):
        """Test API error rule triggering."""
        rule = FailoverRule(
            trigger=FailoverTrigger.API_ERROR,
            threshold=5
        )
        
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        
        # Should not trigger with few failures
        metrics.consecutive_failures = 3
        assert not rule.should_trigger(metrics)
        
        # Should trigger with many failures
        metrics.consecutive_failures = 6
        assert rule.should_trigger(metrics)
    
    def test_disabled_rule(self):
        """Test that disabled rules don't trigger."""
        rule = FailoverRule(
            trigger=FailoverTrigger.CONNECTION_FAILURE,
            threshold=1,
            enabled=False
        )
        
        metrics = ExchangeHealthMetrics(ExchangeType.BINANCE)
        metrics.is_connected = False
        
        assert not rule.should_trigger(metrics)


class TestExchangeFailoverManager:
    """Test exchange failover manager functionality."""
    
    @pytest.fixture
    def failover_manager(self):
        """Create failover manager for testing."""
        return ExchangeFailoverManager(Environment.TESTNET)
    
    @pytest.fixture
    def mock_connector(self):
        """Create mock connector for testing."""
        connector = Mock()
        connector.get_health_status = AsyncMock(return_value={
            "connected": True,
            "websocket_connected": True,
            "rest_api_healthy": True
        })
        connector.connect_websocket = AsyncMock(return_value=True)
        connector.disconnect_websocket = AsyncMock(return_value=True)
        connector.start = AsyncMock(return_value=True)
        connector.stop = AsyncMock(return_value=True)
        return connector
    
    def test_add_exchange(self, failover_manager, mock_connector):
        """Test adding exchange to failover management."""
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=1)
        
        assert ExchangeType.BINANCE in failover_manager.exchanges
        assert ExchangeType.BINANCE in failover_manager.health_metrics
        assert failover_manager.exchange_priorities[ExchangeType.BINANCE] == 1
        assert failover_manager.primary_exchange == ExchangeType.BINANCE
        assert failover_manager.active_exchange == ExchangeType.BINANCE
    
    def test_exchange_priority_management(self, failover_manager, mock_connector):
        """Test exchange priority management."""
        # Add exchanges with different priorities
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=2)
        failover_manager.add_exchange(ExchangeType.BYBIT, mock_connector, priority=1)
        
        # Lower number should be primary (higher priority)
        assert failover_manager.primary_exchange == ExchangeType.BYBIT
        
        # Update priority
        failover_manager.set_exchange_priority(ExchangeType.BINANCE, 0)
        assert failover_manager.primary_exchange == ExchangeType.BINANCE
    
    def test_select_best_exchange(self, failover_manager, mock_connector):
        """Test best exchange selection logic."""
        # Add multiple exchanges
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=2)
        failover_manager.add_exchange(ExchangeType.BYBIT, mock_connector, priority=1)
        
        # Set health metrics
        failover_manager.health_metrics[ExchangeType.BINANCE].is_connected = True
        failover_manager.health_metrics[ExchangeType.BYBIT].is_connected = True
        
        # Should select based on priority and health
        best = failover_manager._select_best_exchange()
        assert best == ExchangeType.BYBIT  # Higher priority
        
        # Exclude BYBIT, should select BINANCE
        best_excluded = failover_manager._select_best_exchange(exclude={ExchangeType.BYBIT})
        assert best_excluded == ExchangeType.BINANCE
    
    @pytest.mark.asyncio
    async def test_health_check_loop(self, failover_manager, mock_connector):
        """Test health check loop functionality."""
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=1)
        
        # Perform single health check
        await failover_manager._perform_health_checks()
        
        # Verify health status was updated
        metrics = failover_manager.health_metrics[ExchangeType.BINANCE]
        assert metrics.last_health_check > 0
        assert mock_connector.get_health_status.called
    
    @pytest.mark.asyncio
    async def test_manual_failover(self, failover_manager, mock_connector):
        """Test manual failover functionality."""
        # Add two exchanges
        mock_connector2 = Mock()
        mock_connector2.get_health_status = AsyncMock(return_value={"connected": True})
        mock_connector2.start = AsyncMock(return_value=True)
        mock_connector2.stop = AsyncMock(return_value=True)
        
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=1)
        failover_manager.add_exchange(ExchangeType.BYBIT, mock_connector2, priority=2)
        
        # Set both as connected
        failover_manager.health_metrics[ExchangeType.BINANCE].is_connected = True
        failover_manager.health_metrics[ExchangeType.BYBIT].is_connected = True
        
        # Perform manual failover
        with patch.object(failover_manager, '_execute_failover', return_value=True):
            success = await failover_manager.manual_failover(ExchangeType.BYBIT)
        
        assert success
        assert failover_manager.active_exchange == ExchangeType.BYBIT
        assert failover_manager.current_state == FailoverState.FAILED_OVER
        assert ExchangeType.BINANCE in failover_manager.failed_exchanges
    
    @pytest.mark.asyncio
    async def test_failover_rule_evaluation(self, failover_manager, mock_connector):
        """Test failover rule evaluation."""
        # Add exchanges
        mock_connector2 = Mock()
        mock_connector2.get_health_status = AsyncMock(return_value={"connected": True})
        mock_connector2.start = AsyncMock(return_value=True)
        
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=1)
        failover_manager.add_exchange(ExchangeType.BYBIT, mock_connector2, priority=2)
        
        # Set BYBIT as connected, BINANCE as disconnected
        failover_manager.health_metrics[ExchangeType.BINANCE].is_connected = False
        failover_manager.health_metrics[ExchangeType.BYBIT].is_connected = True
        
        # Mock failover execution
        with patch.object(failover_manager, '_trigger_failover', return_value=True) as mock_trigger:
            await failover_manager._evaluate_failover_rules()
            
            # Should trigger failover due to connection failure
            mock_trigger.assert_called_once()
    
    def test_get_status(self, failover_manager, mock_connector):
        """Test status reporting."""
        failover_manager.add_exchange(ExchangeType.BINANCE, mock_connector, priority=1)
        
        status = failover_manager.get_status()
        
        assert status["environment"] == Environment.TESTNET.value
        assert status["current_state"] == FailoverState.NORMAL.value
        assert status["primary_exchange"] == ExchangeType.BINANCE.value
        assert status["active_exchange"] == ExchangeType.BINANCE.value
        assert ExchangeType.BINANCE.value in status["exchange_health"]
        assert len(status["failover_rules"]) > 0


class TestProductionFailoverFactory:
    """Test production failover factory functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create production failover factory for testing."""
        return ProductionFailoverFactory(Environment.TESTNET)
    
    @patch('data_pipeline.exchange_connectors.failover_integration.BinanceConnector')
    def test_create_failover_connector(self, mock_binance_class, factory):
        """Test creating failover-enabled connector."""
        # Mock the configuration manager
        mock_config = Mock()
        mock_config.exchange_type = ExchangeType.BINANCE
        mock_config.testnet = True
        mock_config.credentials.api_key = "test_key"
        mock_config.credentials.api_secret = "test_secret"
        mock_config.endpoints.get_rest_url.return_value = "https://testnet.binance.vision"
        mock_config.endpoints.get_websocket_url.return_value = "wss://testnet.binance.vision/ws"
        mock_config.rate_limits.requests_per_minute = 1200
        
        factory.config_manager.get_config = Mock(return_value=mock_config)
        factory.config_manager.validate_configuration = Mock(return_value={"valid": True})
        factory.config_manager.is_exchange_enabled = Mock(return_value=True)
        
        # Mock the base connector
        mock_base_connector = Mock()
        mock_binance_class.return_value = mock_base_connector
        
        # Create connector
        connector = factory.create_connector(ExchangeType.BINANCE)
        
        assert connector is not None
        assert isinstance(connector, FailoverEnabledExchangeConnector)
        assert ExchangeType.BINANCE in factory.failover_manager.exchanges
    
    @pytest.mark.asyncio
    async def test_managed_failover_connectors(self, factory):
        """Test managed failover connectors context manager."""
        # Mock configuration and connectors
        with patch.object(factory, 'create_all_connectors') as mock_create:
            mock_connector = Mock()
            mock_connector.start = AsyncMock(return_value=True)
            mock_connector.stop = AsyncMock(return_value=True)
            
            mock_create.return_value = {ExchangeType.BINANCE: mock_connector}
            
            async with factory.managed_failover_connectors() as context:
                assert "connectors" in context
                assert "failover_manager" in context
                assert "get_active_connector" in context
                assert ExchangeType.BINANCE in context["connectors"]
            
            # Verify connector was stopped
            mock_connector.stop.assert_called_once()


class TestFailoverAwareDataPipeline:
    """Test failover-aware data pipeline functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create mock factory for testing."""
        factory = Mock()
        factory.failover_manager = Mock()
        factory.failover_manager.active_exchange = ExchangeType.BINANCE
        factory.failover_manager.current_state = FailoverState.NORMAL
        factory.failover_manager.add_failover_callback = Mock()
        return factory
    
    @pytest.fixture
    def pipeline(self, factory):
        """Create data pipeline for testing."""
        return FailoverAwareDataPipeline(factory)
    
    def test_pipeline_initialization(self, pipeline, factory):
        """Test pipeline initialization."""
        assert pipeline.factory == factory
        assert pipeline.failover_manager == factory.failover_manager
        assert not pipeline.is_running
        
        # Verify callback was registered
        factory.failover_manager.add_failover_callback.assert_called_once()
    
    def test_add_data_callback(self, pipeline):
        """Test adding data callbacks."""
        callback = Mock()
        pipeline.add_data_callback(callback)
        
        assert callback in pipeline.data_callbacks
    
    @pytest.mark.asyncio
    async def test_data_processing(self, pipeline):
        """Test data processing with callbacks."""
        # Add test callback
        received_data = []
        pipeline.add_data_callback(lambda data: received_data.append(data))
        
        # Process test data
        test_data = {"symbol": "BTCUSDT", "price": 50000}
        await pipeline._process_data(test_data)
        
        assert len(received_data) == 1
        assert received_data[0]["symbol"] == "BTCUSDT"
        assert "source_exchange" in received_data[0]
        assert "failover_state" in received_data[0]
    
    @pytest.mark.asyncio
    async def test_failover_event_handling(self, pipeline):
        """Test handling of failover events."""
        event = FailoverEvent(
            timestamp=time.time(),
            from_exchange=ExchangeType.BINANCE,
            to_exchange=ExchangeType.BYBIT,
            trigger=FailoverTrigger.CONNECTION_FAILURE,
            trigger_value=1.0,
            success=True
        )
        
        # Should not raise exception
        await pipeline._handle_failover_event(event)


class TestFailoverIntegration:
    """Test integration between all failover components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_failover_scenario(self):
        """Test complete failover scenario from error to recovery."""
        # This would be a comprehensive integration test
        # For now, we'll test the basic flow
        
        # Create failover manager
        manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Add mock exchanges
        mock_connector1 = Mock()
        mock_connector1.get_health_status = AsyncMock(return_value={"connected": True})
        mock_connector1.start = AsyncMock(return_value=True)
        mock_connector1.stop = AsyncMock(return_value=True)
        
        mock_connector2 = Mock()
        mock_connector2.get_health_status = AsyncMock(return_value={"connected": True})
        mock_connector2.start = AsyncMock(return_value=True)
        mock_connector2.stop = AsyncMock(return_value=True)
        
        manager.add_exchange(ExchangeType.BINANCE, mock_connector1, priority=1)
        manager.add_exchange(ExchangeType.BYBIT, mock_connector2, priority=2)
        
        # Simulate connection failure on primary
        manager.health_metrics[ExchangeType.BINANCE].is_connected = False
        manager.health_metrics[ExchangeType.BYBIT].is_connected = True
        
        # Mock failover execution
        with patch.object(manager, '_execute_failover', return_value=True):
            # Trigger failover evaluation
            await manager._evaluate_failover_rules()
            
            # Verify failover occurred
            assert manager.active_exchange == ExchangeType.BYBIT
            assert manager.current_state == FailoverState.FAILED_OVER
            assert ExchangeType.BINANCE in manager.failed_exchanges
    
    @pytest.mark.asyncio
    async def test_recovery_scenario(self):
        """Test recovery of failed exchange."""
        manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Add exchanges
        mock_connector1 = Mock()
        mock_connector1.get_health_status = AsyncMock(return_value={"connected": True})
        
        mock_connector2 = Mock()
        mock_connector2.get_health_status = AsyncMock(return_value={"connected": True})
        
        manager.add_exchange(ExchangeType.BINANCE, mock_connector1, priority=1)
        manager.add_exchange(ExchangeType.BYBIT, mock_connector2, priority=2)
        
        # Simulate failover state
        manager.active_exchange = ExchangeType.BYBIT
        manager.current_state = FailoverState.FAILED_OVER
        manager.failed_exchanges.add(ExchangeType.BINANCE)
        
        # Set BINANCE as recovered
        manager.health_metrics[ExchangeType.BINANCE].is_connected = True
        manager.health_metrics[ExchangeType.BINANCE].success_rate_5min = 95.0
        
        # Check recovery
        await manager._check_failed_exchange_recovery()
        
        # BINANCE should be removed from failed exchanges
        assert ExchangeType.BINANCE not in manager.failed_exchanges


# Performance and stress tests
class TestFailoverPerformance:
    """Test failover performance and stress scenarios."""
    
    @pytest.mark.asyncio
    async def test_failover_speed(self):
        """Test failover execution speed."""
        manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Add mock exchanges
        mock_connector1 = Mock()
        mock_connector1.get_health_status = AsyncMock(return_value={"connected": False})
        mock_connector1.stop = AsyncMock(return_value=True)
        
        mock_connector2 = Mock()
        mock_connector2.get_health_status = AsyncMock(return_value={"connected": True})
        mock_connector2.start = AsyncMock(return_value=True)
        
        manager.add_exchange(ExchangeType.BINANCE, mock_connector1, priority=1)
        manager.add_exchange(ExchangeType.BYBIT, mock_connector2, priority=2)
        
        # Set health states
        manager.health_metrics[ExchangeType.BINANCE].is_connected = False
        manager.health_metrics[ExchangeType.BYBIT].is_connected = True
        
        # Measure failover time
        start_time = time.time()
        
        with patch.object(manager, '_execute_failover', return_value=True):
            success = await manager._trigger_failover(
                ExchangeType.BYBIT,
                FailoverTrigger.CONNECTION_FAILURE,
                1.0
            )
        
        failover_time = time.time() - start_time
        
        assert success
        assert failover_time < 1.0  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_multiple_rapid_failovers(self):
        """Test handling of multiple rapid failover attempts."""
        manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Add mock exchanges
        for i, exchange_type in enumerate([ExchangeType.BINANCE, ExchangeType.BYBIT]):
            mock_connector = Mock()
            mock_connector.get_health_status = AsyncMock(return_value={"connected": True})
            mock_connector.start = AsyncMock(return_value=True)
            mock_connector.stop = AsyncMock(return_value=True)
            
            manager.add_exchange(exchange_type, mock_connector, priority=i+1)
            manager.health_metrics[exchange_type].is_connected = True
        
        # Attempt multiple rapid failovers
        with patch.object(manager, '_execute_failover', return_value=True):
            tasks = []
            for _ in range(5):
                task = asyncio.create_task(
                    manager.manual_failover(ExchangeType.BYBIT)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Only one should succeed, others should be rejected or handled gracefully
            successful = sum(1 for r in results if r is True)
            assert successful <= 1  # At most one should succeed


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])