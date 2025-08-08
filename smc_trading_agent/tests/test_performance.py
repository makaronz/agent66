"""
Performance-focused tests split from the comprehensive module.
"""

import pytest
import pandas as pd
import numpy as np
import time

from ..risk_manager.var_calculator import VaRCalculator, VaRMethod
from ..risk_manager.circuit_breaker import CircuitBreaker


class TestPerformanceTests:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_var_calculation_performance(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

        np.random.seed(42)
        portfolio_data = pd.DataFrame({
            'value': np.random.normal(1000000, 50000, 1000),
            'returns': np.random.normal(0.001, 0.02, 1000)
        })

        start_time = time.time()
        result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)
        end_time = time.time()

        calculation_time = end_time - start_time

        assert calculation_time < 1.0
        assert result.var_value > 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_response_time(self, mock_config, mock_exchange_connectors, mock_service_manager):
        circuit_breaker = CircuitBreaker(mock_config, mock_exchange_connectors, mock_service_manager)

        portfolio_data = {
            'drawdown': 0.05,
            'portfolio_data': pd.DataFrame({'value': [1000000], 'returns': [0.01]})
        }

        start_time = time.time()
        result = await circuit_breaker.check_risk_limits(portfolio_data)
        end_time = time.time()

        response_time = end_time - start_time

        assert response_time < 2.0
        assert isinstance(result, bool)


