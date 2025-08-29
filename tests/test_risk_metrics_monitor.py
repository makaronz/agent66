"""
Component-focused tests for RiskMetricsMonitor.
"""

import pytest
import pandas as pd

from ..risk_manager.risk_metrics import RiskMetricsMonitor, RiskCategory, RiskSeverity


class TestRiskMetricsMonitor:
    """Test risk metrics monitor functionality."""

    @pytest.mark.asyncio
    async def test_market_risk_calculation(self, mock_config):
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
        monitor = RiskMetricsMonitor(mock_config['risk_metrics'])

        metrics = {
            'test_metric': monitor._create_test_metric(
                name='test_metric',
                value=0.15,
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


    @pytest.mark.asyncio
    async def test_no_alert_when_below_threshold(self, mock_config):
        """Ensure no alert is generated when metric value is strictly below its threshold."""
        monitor = RiskMetricsMonitor(mock_config['risk_metrics'])

        metrics = {
            'test_metric': monitor._create_test_metric(
                name='test_metric',
                value=0.05,  # below threshold
                threshold=0.10,
                category=RiskCategory.MARKET,
                severity=RiskSeverity.LOW
            )
        }

        alerts = await monitor.check_thresholds_and_generate_alerts(metrics)

        assert alerts == []

