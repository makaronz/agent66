"""
Component-focused tests for CircuitBreaker (unit + integration workflows).
"""

import pytest
import pandas as pd
import time
from unittest.mock import Mock, AsyncMock, patch

from ..risk_manager.circuit_breaker import CircuitBreaker, CircuitBreakerState
from ..risk_manager.position_manager import ClosureResult
from ..risk_manager.notification_service import NotificationChannel


class TestCircuitBreaker:
    """Unit tests for circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, mock_config, mock_exchange_connectors, mock_service_manager):
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
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        portfolio_data = {
            'drawdown': 0.05,
            'portfolio_data': sample_portfolio_data
        }

        result = await circuit_breaker.check_risk_limits(portfolio_data)

        assert result is True
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggering(self, mock_config, mock_exchange_connectors, mock_service_manager):
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        portfolio_data = {
            'drawdown': 0.15,
            'portfolio_data': pd.DataFrame({
                'value': [1000000, 1010000, 990000, 1020000, 980000],
                'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
            })
        }

        with patch.object(circuit_breaker, 'send_alert', new_callable=AsyncMock) as mock_alert:
            result = await circuit_breaker.check_risk_limits(portfolio_data)

            assert result is False
            assert circuit_breaker.state == CircuitBreakerState.OPEN
            assert circuit_breaker.trigger_time is not None
            mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_position_closure_integration(self, mock_config, mock_exchange_connectors, mock_service_manager):
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        with patch.object(circuit_breaker.position_manager, 'close_all_positions', new_callable=AsyncMock) as mock_closure:
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
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        with patch.object(circuit_breaker.notification_service, 'send_multi_channel_alert', new_callable=AsyncMock) as mock_alert:
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
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        circuit_breaker.state = CircuitBreakerState.OPEN
        circuit_breaker.trigger_time = time.time() - 400

        with patch.object(circuit_breaker, 'send_alert', new_callable=AsyncMock) as mock_alert:
            await circuit_breaker._attempt_recovery()

            assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, mock_config, mock_exchange_connectors, mock_service_manager):
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        status = await circuit_breaker.get_circuit_breaker_status()

        assert 'timestamp' in status
        assert 'state' in status
        assert 'thresholds' in status
        assert 'events_count' in status
        assert 'components' in status
        assert status['state'] == 'closed'


class TestIntegrationWorkflows:
    """End-to-end integration workflows for circuit breaker."""

    @pytest.mark.asyncio
    async def test_complete_circuit_breaker_workflow(self, mock_config, mock_exchange_connectors, mock_service_manager):
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        with patch.object(circuit_breaker.var_calculator, 'calculate_var', new_callable=AsyncMock) as mock_var:
            mock_var.return_value = Mock(var_value=0.08)

            with patch.object(circuit_breaker.position_manager, 'close_all_positions', new_callable=AsyncMock) as mock_closure:
                mock_closure.return_value = [Mock(success=True)]

                with patch.object(circuit_breaker.notification_service, 'send_multi_channel_alert', new_callable=AsyncMock) as mock_alert:
                    mock_alert.return_value = [Mock(success=True)]

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
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        with patch.object(circuit_breaker, 'close_all_positions', new_callable=AsyncMock) as mock_closure:
            with patch.object(circuit_breaker, 'send_alert', new_callable=AsyncMock) as mock_alert:
                mock_closure.return_value = True

                await circuit_breaker._execute_emergency_procedures("Test emergency")

                mock_closure.assert_called_once()
                mock_alert.assert_called_once()


