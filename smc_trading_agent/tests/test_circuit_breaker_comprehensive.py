"""
Comprehensive Circuit Breaker Tests for SMC Trading Agent.

This module provides comprehensive testing for the complete circuit breaker system including:
- Unit tests for all components
- Integration tests for end-to-end workflows
- Performance tests for critical operations
- Validation tests for risk calculations
- Mock services for external dependencies
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from ..risk_manager.circuit_breaker import CircuitBreaker, CircuitBreakerState
from ..risk_manager.var_calculator import VaRCalculator, VaRMethod
from ..risk_manager.risk_metrics import RiskMetricsMonitor, RiskCategory, RiskSeverity
from ..risk_manager.position_manager import PositionManager, Position, ClosureResult
from ..risk_manager.notification_service import NotificationService, NotificationChannel, NotificationPriority


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        'max_drawdown': 0.10,
        'max_var': 0.05,
        'max_correlation': 0.70,
        'recovery_timeout': 300,
        'check_interval': 60,
        'var_calculator': {
            'confidence_levels': [0.95, 0.99],
            'lookback_period': 252,
            'monte_carlo_simulations': 10000,
            'correlation_threshold': 0.7,
            'cache_ttl': 300
        },
        'risk_metrics': {
            'thresholds': {
                'market': {'max_drawdown': 0.10, 'max_var': 0.05, 'max_volatility': 0.30},
                'credit': {'max_exposure': 0.20, 'max_default_probability': 0.01},
                'liquidity': {'min_bid_ask_spread': 0.001, 'min_market_depth': 1000000, 'min_trading_volume': 500000},
                'operational': {'max_error_rate': 0.01, 'max_latency': 1000, 'min_data_quality': 0.95},
                'concentration': {'max_position_size': 0.20, 'max_sector_exposure': 0.30},
                'correlation': {'max_correlation': 0.70, 'min_diversification': 0.50}
            },
            'calculation_interval': 60,
            'alert_cooldown': 300
        },
        'position_manager': {
            'max_retry_attempts': 3,
            'retry_delay': 1.0,
            'closure_timeout': 30.0,
            'concurrent_closures': 5
        },
        'notifications': {
            'rate_limits': {
                'email': 100,
                'sms': 50,
                'slack': 200
            },
            'throttle_delay': 1.0,
            'max_retry_attempts': 3,
            'retry_delay': 5.0,
            'recipients': {
                'email': ['test@example.com'],
                'sms': ['+1234567890'],
                'slack': ['#alerts']
            }
        }
    }


@pytest.fixture
def mock_exchange_connectors():
    """Mock exchange connectors for testing."""
    connectors = {}
    
    # Mock Binance connector
    binance_mock = Mock()
    binance_mock.name = "binance"
    binance_mock.connected = True
    binance_mock.fetch_rest_data = AsyncMock(return_value={
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'long',
                'size': 1.0,
                'entry_price': 50000,
                'current_price': 51000,
                'unrealized_pnl': 1000
            }
        ]
    })
    connectors['binance'] = binance_mock
    
    # Mock Bybit connector
    bybit_mock = Mock()
    bybit_mock.name = "bybit"
    bybit_mock.connected = True
    bybit_mock.fetch_rest_data = AsyncMock(return_value={
        'positions': [
            {
                'symbol': 'ETHUSDT',
                'side': 'short',
                'size': 10.0,
                'entry_price': 3000,
                'current_price': 2900,
                'unrealized_pnl': 1000
            }
        ]
    })
    connectors['bybit'] = bybit_mock
    
    return connectors


@pytest.fixture
def mock_service_manager():
    """Mock service manager for testing."""
    service_manager = Mock()
    service_manager.get_service_health = Mock(return_value={
        'circuit_breaker': {'healthy': True},
        'position_manager': {'healthy': True},
        'notification_service': {'healthy': True}
    })
    return service_manager


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing."""
    # Create sample portfolio data
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # Generate sample returns
    returns = np.random.normal(0.001, 0.02, 100)
    values = 1000000 * (1 + np.cumsum(returns))
    
    portfolio_data = pd.DataFrame({
        'timestamp': dates,
        'value': values,
        'returns': returns,
        'BTCUSDT': np.random.normal(0.001, 0.03, 100),
        'ETHUSDT': np.random.normal(0.001, 0.025, 100),
        'ADAUSDT': np.random.normal(0.001, 0.035, 100)
    })
    
    return portfolio_data


class TestVaRCalculator:
    """Test VaR calculator functionality."""
    
    @pytest.mark.asyncio
    async def test_historical_var_calculation(self, mock_config):
        """Test historical VaR calculation."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        # Create test data
        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })
        
        result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)
        
        assert result.var_value > 0
        assert result.confidence_level == 0.95
        assert result.method == VaRMethod.HISTORICAL
        assert result.data_points == 5
    
    @pytest.mark.asyncio
    async def test_parametric_var_calculation(self, mock_config):
        """Test parametric VaR calculation."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })
        
        result = await calculator.calculate_var(portfolio_data, VaRMethod.PARAMETRIC, 0.95)
        
        assert result.var_value > 0
        assert result.confidence_level == 0.95
        assert result.method == VaRMethod.PARAMETRIC
    
    @pytest.mark.asyncio
    async def test_correlation_matrix_calculation(self, mock_config):
        """Test correlation matrix calculation."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        portfolio_data = pd.DataFrame({
            'BTCUSDT': np.random.normal(0.001, 0.03, 100),
            'ETHUSDT': np.random.normal(0.001, 0.025, 100),
            'ADAUSDT': np.random.normal(0.001, 0.035, 100)
        })
        
        result = await calculator.calculate_correlation_matrix(portfolio_data)
        
        assert result.correlation_matrix is not None
        assert result.max_correlation >= result.min_correlation
        assert result.avg_correlation >= -1 and result.avg_correlation <= 1
    
    @pytest.mark.asyncio
    async def test_var_threshold_checking(self, mock_config):
        """Test VaR threshold checking."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })
        
        var_result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)
        
        # Test threshold checking
        threshold_exceeded = await calculator.check_var_threshold(var_result, 0.01)
        assert isinstance(threshold_exceeded, bool)


class TestRiskMetricsMonitor:
    """Test risk metrics monitor functionality."""
    
    @pytest.mark.asyncio
    async def test_market_risk_calculation(self, mock_config):
        """Test market risk calculation."""
        monitor = RiskMetricsMonitor(mock_config['risk_metrics'])
        
        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })
        
        metrics = await monitor.calculate_market_risk(portfolio_data)
        
        assert 'drawdown' in metrics or 'var' in metrics or 'volatility' in metrics
        for metric in metrics.values():
            assert metric.category == RiskCategory.MARKET
            assert metric.value >= 0
    
    @pytest.mark.asyncio
    async def test_all_risk_metrics_calculation(self, mock_config):
        """Test calculation of all risk metrics."""
        monitor = RiskMetricsMonitor(mock_config['risk_metrics'])
        
        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02],
            'BTCUSDT': [50000, 51000, 49000, 52000, 48000]
        })
        
        all_metrics = await monitor.calculate_all_risk_metrics(portfolio_data)
        
        assert len(all_metrics) > 0
        for metric in all_metrics.values():
            assert metric.category in RiskCategory
            assert metric.severity in RiskSeverity
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, mock_config):
        """Test alert generation for threshold violations."""
        monitor = RiskMetricsMonitor(mock_config['risk_metrics'])
        
        # Create metrics that exceed thresholds
        metrics = {
            'test_metric': monitor._create_test_metric(
                name='test_metric',
                value=0.15,  # Exceeds threshold
                threshold=0.10,
                category=RiskCategory.MARKET,
                severity=RiskSeverity.HIGH
            )
        }
        
        alerts = await monitor.check_thresholds_and_generate_alerts(metrics)
        
        assert len(alerts) > 0
        for alert in alerts:
            assert alert.category == RiskCategory.MARKET
            assert alert.severity == RiskSeverity.HIGH


class TestPositionManager:
    """Test position manager functionality."""
    
    @pytest.mark.asyncio
    async def test_position_discovery(self, mock_config, mock_exchange_connectors):
        """Test position discovery across exchanges."""
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)
        
        positions = await manager.discover_all_positions()
        
        assert len(positions) > 0
        for position_id, position in positions.items():
            assert isinstance(position, Position)
            assert position.exchange in ['binance', 'bybit']
            assert position.size > 0
    
    @pytest.mark.asyncio
    async def test_position_closure(self, mock_config, mock_exchange_connectors):
        """Test position closure functionality."""
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)
        
        # Mock successful closure
        with patch.object(manager, '_execute_position_closure') as mock_closure:
            mock_closure.return_value = ClosureResult(
                exchange='binance',
                symbol='BTCUSDT',
                success=True,
                closed_size=1.0,
                closure_price=51000,
                timestamp=time.time()
            )
            
            closure_results = await manager.close_all_positions("Test closure")
            
            assert len(closure_results) > 0
            for result in closure_results:
                assert isinstance(result, ClosureResult)
    
    @pytest.mark.asyncio
    async def test_closure_validation(self, mock_config, mock_exchange_connectors):
        """Test position closure validation."""
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)
        
        # Test successful closure validation
        successful_results = [
            ClosureResult(
                exchange='binance',
                symbol='BTCUSDT',
                success=True,
                closed_size=1.0,
                closure_price=51000,
                timestamp=time.time()
            )
        ]
        
        is_valid = await manager.validate_position_closure(successful_results)
        assert is_valid is True


class TestNotificationService:
    """Test notification service functionality."""
    
    @pytest.mark.asyncio
    async def test_email_notification(self, mock_config):
        """Test email notification sending."""
        service = NotificationService(mock_config['notifications'])
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 202
            
            result = await service.send_alert(
                channel=NotificationChannel.EMAIL,
                priority=NotificationPriority.HIGH,
                subject="Test Alert",
                message="Test message",
                recipients=["test@example.com"]
            )
            
            assert result.success is True
            assert result.channel == NotificationChannel.EMAIL
    
    @pytest.mark.asyncio
    async def test_slack_notification(self, mock_config):
        """Test Slack notification sending."""
        service = NotificationService(mock_config['notifications'])
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await service.send_alert(
                channel=NotificationChannel.SLACK,
                priority=NotificationPriority.CRITICAL,
                subject="Test Alert",
                message="Test message",
                recipients=["#alerts"]
            )
            
            assert result.success is True
            assert result.channel == NotificationChannel.SLACK
    
    @pytest.mark.asyncio
    async def test_multi_channel_notification(self, mock_config):
        """Test multi-channel notification sending."""
        service = NotificationService(mock_config['notifications'])
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            
            results = await service.send_multi_channel_alert(
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                priority=NotificationPriority.HIGH,
                subject="Test Alert",
                message="Test message",
                recipients={
                    NotificationChannel.EMAIL: ["test@example.com"],
                    NotificationChannel.SLACK: ["#alerts"]
                }
            )
            
            assert len(results) == 2
            for result in results:
                assert result.success is True


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test circuit breaker initialization."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.max_drawdown == 0.10
        assert circuit_breaker.max_var == 0.05
        assert circuit_breaker.max_correlation == 0.70
        assert circuit_breaker.var_calculator is not None
        assert circuit_breaker.risk_monitor is not None
        assert circuit_breaker.position_manager is not None
        assert circuit_breaker.notification_service is not None
    
    @pytest.mark.asyncio
    async def test_risk_limit_checking_normal_conditions(self, mock_config, mock_exchange_connectors, mock_service_manager, sample_portfolio_data):
        """Test risk limit checking under normal conditions."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        portfolio_data = {
            'drawdown': 0.05,  # Within limits
            'portfolio_data': sample_portfolio_data
        }
        
        result = await circuit_breaker.check_risk_limits(portfolio_data)
        
        assert result is True
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_triggering(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test circuit breaker triggering."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        # Create portfolio data that exceeds limits
        portfolio_data = {
            'drawdown': 0.15,  # Exceeds max_drawdown of 0.10
            'portfolio_data': pd.DataFrame({
                'value': [1000000, 1010000, 990000, 1020000, 980000],
                'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
            })
        }
        
        with patch.object(circuit_breaker, 'send_alert') as mock_alert:
            result = await circuit_breaker.check_risk_limits(portfolio_data)
            
            assert result is False
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            assert circuit_breaker.trigger_time is not None
            mock_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_position_closure_integration(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test position closure integration."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        with patch.object(circuit_breaker.position_manager, 'close_all_positions') as mock_closure:
            mock_closure.return_value = [
                ClosureResult(
                    exchange='binance',
                    symbol='BTCUSDT',
                    success=True,
                    closed_size=1.0,
                    closure_price=51000,
                    timestamp=time.time()
                )
            ]
            
            success = await circuit_breaker.close_all_positions()
            
            assert success is True
            mock_closure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_sending_integration(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test alert sending integration."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        with patch.object(circuit_breaker.notification_service, 'send_multi_channel_alert') as mock_alert:
            mock_alert.return_value = [
                Mock(success=True, channel=NotificationChannel.EMAIL),
                Mock(success=True, channel=NotificationChannel.SLACK)
            ]
            
            await circuit_breaker.send_alert("Test alert message")
            
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            assert call_args[1]['subject'] == "🚨 CIRCUIT BREAKER TRIGGERED"
    
    @pytest.mark.asyncio
    async def test_recovery_mechanism(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test circuit breaker recovery mechanism."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        # Set circuit breaker to open state
        circuit_breaker.state = CircuitBreakerState.OPEN
        circuit_breaker.trigger_time = time.time() - 400  # Past recovery timeout
        
        with patch.object(circuit_breaker, 'send_alert') as mock_alert:
            await circuit_breaker._attempt_recovery()
            
            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            mock_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test circuit breaker status reporting."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        status = await circuit_breaker.get_circuit_breaker_status()
        
        assert 'timestamp' in status
        assert 'state' in status
        assert 'thresholds' in status
        assert 'events_count' in status
        assert 'components' in status
        assert status['state'] == 'closed'


class TestIntegrationWorkflows:
    """Test end-to-end integration workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_circuit_breaker_workflow(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test complete circuit breaker workflow from trigger to recovery."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        # Mock all components for successful workflow
        with patch.object(circuit_breaker.var_calculator, 'calculate_var') as mock_var:
            mock_var.return_value = Mock(var_value=0.08)  # Exceeds threshold
            
            with patch.object(circuit_breaker.position_manager, 'close_all_positions') as mock_closure:
                mock_closure.return_value = [Mock(success=True)]
                
                with patch.object(circuit_breaker.notification_service, 'send_multi_channel_alert') as mock_alert:
                    mock_alert.return_value = [Mock(success=True)]
                    
                    # Trigger circuit breaker
                    portfolio_data = {
                        'drawdown': 0.05,
                        'portfolio_data': pd.DataFrame({'value': [1000000], 'returns': [0.01]})
                    }
                    
                    result = await circuit_breaker.check_risk_limits(portfolio_data)
                    
                    assert result is False
                    assert circuit_breaker.state == CircuitBreakerState.OPEN
                    mock_closure.assert_called_once()
                    mock_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_emergency_procedures_execution(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test emergency procedures execution."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        with patch.object(circuit_breaker, 'close_all_positions') as mock_closure:
            with patch.object(circuit_breaker, 'send_alert') as mock_alert:
                mock_closure.return_value = True
                
                await circuit_breaker._execute_emergency_procedures("Test emergency")
                
                mock_closure.assert_called_once()
                mock_alert.assert_called_once()


class TestPerformanceTests:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_var_calculation_performance(self, mock_config):
        """Test VaR calculation performance."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        # Create large dataset
        portfolio_data = pd.DataFrame({
            'value': np.random.normal(1000000, 50000, 1000),
            'returns': np.random.normal(0.001, 0.02, 1000)
        })
        
        start_time = time.time()
        result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)
        end_time = time.time()
        
        calculation_time = end_time - start_time
        
        assert calculation_time < 1.0  # Should complete within 1 second
        assert result.var_value > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_response_time(self, mock_config, mock_exchange_connectors, mock_service_manager):
        """Test circuit breaker response time."""
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)
        
        portfolio_data = {
            'drawdown': 0.05,
            'portfolio_data': pd.DataFrame({'value': [1000000], 'returns': [0.01]})
        }
        
        start_time = time.time()
        result = await circuit_breaker.check_risk_limits(portfolio_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response_time < 2.0  # Should respond within 2 seconds
        assert isinstance(result, bool)


class TestValidationTests:
    """Test validation of calculations and results."""
    
    @pytest.mark.asyncio
    async def test_var_calculation_validation(self, mock_config):
        """Test VaR calculation validation against known results."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        # Create dataset with known properties
        returns = np.array([-0.02, -0.01, 0.01, 0.02, -0.03, 0.01, -0.01, 0.02, -0.02, 0.01])
        portfolio_data = pd.DataFrame({
            'value': 1000000 * (1 + np.cumsum(returns)),
            'returns': returns
        })
        
        # Calculate VaR
        var_result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)
        
        # Validate results
        assert var_result.var_value > 0
        assert var_result.var_value <= 0.1  # Should not exceed 10% for this dataset
        assert var_result.data_points == 10
    
    @pytest.mark.asyncio
    async def test_correlation_validation(self, mock_config):
        """Test correlation calculation validation."""
        calculator = VaRCalculator(mock_config['var_calculator'])
        
        # Create correlated data
        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = 0.7 * x + 0.3 * np.random.normal(0, 1, 100)  # Correlation ~0.7
        
        portfolio_data = pd.DataFrame({
            'asset1': x,
            'asset2': y
        })
        
        correlation_result = await calculator.calculate_correlation_matrix(portfolio_data)
        
        # Validate correlation
        assert abs(correlation_result.max_correlation) > 0.6  # Should detect high correlation
        assert correlation_result.max_correlation <= 1.0
        assert correlation_result.min_correlation >= -1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
