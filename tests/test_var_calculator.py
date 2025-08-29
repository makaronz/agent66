"""
Component-focused tests for VaRCalculator (VaR and correlation + validations).
"""

import pytest
import pandas as pd
import numpy as np

from ..risk_manager.var_calculator import VaRCalculator, VaRMethod


class TestVaRCalculator:
    """Test VaR calculator functionality."""

    @pytest.mark.asyncio
    async def test_historical_var_calculation(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

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
        calculator = VaRCalculator(mock_config['var_calculator'])

        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })

        result = await calculator.calculate_var(portfolio_data, VaRMethod.PARAMETRIC, 0.95)

        assert result.var_value > 0
        assert result.confidence_level == 0.95
        assert result.method == VaRMethod.PARAMETRIC
        assert result.data_points == len(portfolio_data)

    @pytest.mark.asyncio
    async def test_correlation_matrix_calculation(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

        np.random.seed(42)
        portfolio_data = pd.DataFrame({
            'BTCUSDT': np.random.normal(0.001, 0.03, 100),
            'ETHUSDT': np.random.normal(0.001, 0.025, 100),
            'ADAUSDT': np.random.normal(0.001, 0.035, 100)
        })

        result = await calculator.calculate_correlation_matrix(portfolio_data)

        assert result.correlation_matrix is not None
        assert result.max_correlation >= result.min_correlation
        assert -1 <= result.avg_correlation <= 1

    @pytest.mark.asyncio
    async def test_var_threshold_checking(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

        portfolio_data = pd.DataFrame({
            'value': [1000000, 1010000, 990000, 1020000, 980000],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })

        var_result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)

        threshold_exceeded = await calculator.check_var_threshold(var_result, 0.01)
        assert isinstance(threshold_exceeded, bool)


class TestValidationTests:
    """Validation of VaR and correlation calculations."""

    @pytest.mark.asyncio
    async def test_var_calculation_validation(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

        returns = np.array([-0.02, -0.01, 0.01, 0.02, -0.03, 0.01, -0.01, 0.02, -0.02, 0.01])
        portfolio_data = pd.DataFrame({
            'value': 1000000 * (1 + np.cumsum(returns)),
            'returns': returns
        })

        var_result = await calculator.calculate_var(portfolio_data, VaRMethod.HISTORICAL, 0.95)

        assert var_result.var_value > 0
        assert var_result.var_value <= 0.1
        assert var_result.data_points == 10

    @pytest.mark.asyncio
    async def test_correlation_validation(self, mock_config):
        calculator = VaRCalculator(mock_config['var_calculator'])

        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = 0.7 * x + 0.3 * np.random.normal(0, 1, 100)

        portfolio_data = pd.DataFrame({
            'asset1': x,
            'asset2': y
        })

        correlation_result = await calculator.calculate_correlation_matrix(portfolio_data)

        assert abs(correlation_result.max_correlation) > 0.6
        assert correlation_result.max_correlation <= 1.0
        assert correlation_result.min_correlation >= -1.0


