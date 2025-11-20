"""
Comprehensive tests for the Institutional Risk Management System.

Tests all components including:
- Enhanced VaR calculator with multiple methods
- Portfolio risk management with correlation analysis
- Dynamic risk controls with Kelly Criterion
- Regulatory compliance with MiFID II features
- Real-time risk dashboard functionality
- System integration and performance
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json
import tempfile
import os

# Import the risk management components
from risk_manager.enhanced_var_calculator import (
    EnhancedVaRCalculator, VaRMethod, StressScenario, VaRResult
)
from risk_manager.portfolio_risk_manager import (
    PortfolioRiskManager, ConcentrationMetric, CorrelationAnalysis
)
from risk_manager.dynamic_risk_controls import (
    DynamicRiskControls, MarketRegime, PositionSizingMethod
)
from risk_manager.enhanced_compliance_engine import (
    EnhancedComplianceEngine, ComplianceStatus, ReportType
)
from risk_manager.realtime_risk_dashboard import (
    RealTimeRiskDashboard, AlertSeverity, RiskMetricType
)
from risk_manager.institutional_risk_system import (
    InstitutionalRiskSystem, RiskDecision, RiskSystemMode
)


class TestEnhancedVaRCalculator:
    """Test cases for Enhanced VaR Calculator."""

    @pytest.fixture
    def var_calculator(self):
        """Create VaR calculator instance for testing."""
        config = {
            'confidence_levels': [0.95, 0.99],
            'time_horizons': [1, 5, 10],
            'monte_carlo_simulations': 1000,  # Reduced for testing
            'lookback_period': 100
        }
        return EnhancedVaRCalculator(config)

    @pytest.fixture
    def sample_portfolio_data(self):
        """Create sample portfolio data for testing."""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.utcnow(), periods=200, freq='D')

        # Generate realistic returns with some volatility clustering
        returns = np.random.normal(0.001, 0.02, 200)
        values = 1000000 * (1 + np.cumsum(returns))

        return pd.DataFrame({
            'value': values,
            'returns': returns
        }, index=dates)

    @pytest.mark.asyncio
    async def test_historical_var_calculation(self, var_calculator, sample_portfolio_data):
        """Test historical VaR calculation."""
        result = await var_calculator.calculate_enhanced_var(
            sample_portfolio_data, VaRMethod.HISTORICAL, 0.95, 1
        )

        assert isinstance(result, VaRResult)
        assert result.var_value > 0
        assert result.confidence_level == 0.95
        assert result.time_horizon == 1
        assert result.method == VaRMethod.HISTORICAL
        assert len(result.additional_metrics) > 0

    @pytest.mark.asyncio
    async def test_monte_carlo_var_calculation(self, var_calculator, sample_portfolio_data):
        """Test Monte Carlo VaR calculation."""
        result = await var_calculator.calculate_enhanced_var(
            sample_portfolio_data, VaRMethod.MONTE_CARLO, 0.99, 5
        )

        assert isinstance(result, VaRResult)
        assert result.var_value > 0
        assert result.confidence_level == 0.99
        assert result.time_horizon == 5
        assert result.method == VaRMethod.MONTE_CARLO

    @pytest.mark.asyncio
    async def test_cvar_calculation(self, var_calculator, sample_portfolio_data):
        """Test Conditional VaR calculation."""
        cvar_result = await var_calculator.calculate_cvar(
            sample_portfolio_data, VaRMethod.HISTORICAL, 0.95
        )

        assert cvar_result.cvar_value > 0
        assert cvar_result.var_value > 0
        assert cvar_result.expected_shortfall == cvar_result.cvar_value
        assert cvar_result.confidence_level == 0.95

    @pytest.mark.asyncio
    async def test_stress_testing(self, var_calculator, sample_portfolio_data):
        """Test stress testing functionality."""
        stress_result = await var_calculator.run_stress_test(
            sample_portfolio_data, StressScenario.MARKET_CRASH
        )

        assert stress_result.scenario == StressScenario.MARKET_CRASH
        assert stress_result.stressed_var > 0
        assert stress_result.percentage_loss < 0  # Should be a loss
        assert 'market_shock' in stress_result.scenario_params

    @pytest.mark.asyncio
    async def test_var_backtesting(self, var_calculator):
        """Test VaR backtesting."""
        # Generate test returns
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 500))

        backtest_result = await var_calculator.run_backtest(returns, VaRMethod.HISTORICAL, 0.95)

        assert backtest_result.method == VaRMethod.HISTORICAL
        assert backtest_result.confidence_level == 0.95
        assert backtest_result.total_observations > 0
        assert isinstance(backtest_result.passed_kupiec, bool)
        assert isinstance(backtest_result.passed_christoffersen, bool)


class TestPortfolioRiskManager:
    """Test cases for Portfolio Risk Manager."""

    @pytest.fixture
    def portfolio_manager(self):
        """Create portfolio manager instance for testing."""
        config = {
            'max_concentration': 0.20,
            'max_sector_exposure': 0.30,
            'correlation_threshold': 0.7
        }
        return PortfolioRiskManager(config)

    @pytest.fixture
    def sample_returns_data(self):
        """Create sample returns data for testing."""
        np.random.seed(42)
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='D')

        data = {}
        for symbol in symbols:
            # Create correlated returns with some unique characteristics
            base_returns = np.random.normal(0.001, 0.02, 100)
            if symbol == 'BTCUSDT':
                base_returns += np.random.normal(0.0005, 0.01, 100)  # Slight drift
            data[symbol] = base_returns

        return pd.DataFrame(data, index=dates)

    @pytest.fixture
    def sample_positions(self):
        """Create sample positions for testing."""
        return {
            'BTCUSDT': 50000,
            'ETHUSDT': 30000,
            'ADAUSDT': 15000,
            'DOTUSDT': 5000
        }

    @pytest.mark.asyncio
    async def test_correlation_analysis(self, portfolio_manager, sample_returns_data):
        """Test correlation analysis functionality."""
        result = await portfolio_manager.analyze_correlation_matrix(sample_returns_data)

        assert isinstance(result, CorrelationAnalysis)
        assert result.correlation_matrix.shape == (3, 3)  # 3 symbols
        assert len(result.eigenvalues) == 3
        assert result.maximum_correlation >= 0
        assert result.maximum_correlation <= 1
        assert result.systemic_risk_score >= 0
        assert result.systemic_risk_score <= 1

    @pytest.mark.asyncio
    async def test_concentration_risk_analysis(self, portfolio_manager, sample_positions):
        """Test concentration risk analysis."""
        sectors = {
            'BTCUSDT': 'Cryptocurrency',
            'ETHUSDT': 'Cryptocurrency',
            'ADAUSDT': 'Cryptocurrency',
            'DOTUSDT': 'Cryptocurrency'
        }

        result = await portfolio_manager.analyze_concentration_risk(sample_positions, sectors)

        assert result.metric == ConcentrationMetric.HERFINDAHL_INDEX
        assert result.value > 0
        assert result.risk_level in ['LOW', 'MEDIUM', 'HIGH']
        assert len(result.top_positions) > 0
        assert result.sector_concentration['Cryptocurrency'] > 0

    @pytest.mark.asyncio
    async def test_diversification_metrics(self, portfolio_manager):
        """Test diversification metrics calculation."""
        # Create sample data
        dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='D')
        portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)

        position_returns = pd.DataFrame({
            'asset1': np.random.normal(0.001, 0.02, 100),
            'asset2': np.random.normal(0.001, 0.015, 100),
            'asset3': np.random.normal(0.0005, 0.025, 100)
        }, index=dates)

        position_weights = {'asset1': 0.4, 'asset2': 0.3, 'asset3': 0.3}

        result = await portfolio_manager.calculate_diversification_metrics(
            portfolio_returns, position_returns, position_weights
        )

        assert result.diversification_ratio > 0
        assert result.effective_number_bets > 0
        assert result.systematic_risk >= 0
        assert result.specific_risk >= 0
        assert abs(result.systematic_risk + result.specific_risk - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_rebalance_recommendations(self, portfolio_manager, sample_positions):
        """Test rebalancing recommendation generation."""
        # Create target weights that differ from current
        target_weights = {'BTCUSDT': 0.3, 'ETHUSDT': 0.3, 'ADAUSDT': 0.2, 'DOTUSDT': 0.2}

        recommendations = await portfolio_manager.generate_rebalance_recommendations(
            sample_positions, target_weights
        )

        assert len(recommendations) > 0
        for rec in recommendations:
            assert rec.current_weight >= 0
            assert rec.target_weight >= 0
            assert rec.priority >= 1
            assert rec.priority <= 10


class TestDynamicRiskControls:
    """Test cases for Dynamic Risk Controls."""

    @pytest.fixture
    def dynamic_controls(self):
        """Create dynamic controls instance for testing."""
        config = {
            'max_position_size': 0.05,
            'volatility_target': 0.12,
            'kelly_safety_multiplier': 0.5,
            'max_kelly_fraction': 0.25
        }
        return DynamicRiskControls(config)

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='D')

        # Generate price series with trend and volatility
        initial_price = 50000
        returns = np.random.normal(0.001, 0.02, 100)
        prices = initial_price * (1 + np.cumsum(returns))

        return pd.DataFrame({
            'open': prices * np.random.uniform(0.99, 1.01, 100),
            'high': prices * np.random.uniform(1.00, 1.05, 100),
            'low': prices * np.random.uniform(0.95, 1.00, 100),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)

    @pytest.mark.asyncio
    async def test_market_regime_detection(self, dynamic_controls, sample_market_data):
        """Test market regime detection."""
        result = await dynamic_controls.detect_market_regime(sample_market_data)

        assert isinstance(result.current_regime, MarketRegime)
        assert 0 <= result.regime_probability <= 1
        assert result.market_volatility >= 0
        assert -1 <= result.trend_strength <= 1
        assert result.regime_duration >= 0
        assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_kelly_criterion_calculation(self, dynamic_controls):
        """Test Kelly Criterion calculation."""
        # Create sample trade history with known characteristics
        np.random.seed(42)
        trade_count = 100
        returns = np.random.normal(0.02, 0.05, trade_count)  # Positive expectancy
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        trade_history = pd.DataFrame({
            'return': returns,
            'pnl': returns * 1000  # Assume $1000 base position
        })

        result = await dynamic_controls.calculate_kelly_criterion(trade_history)

        assert result.optimal_fraction >= 0
        assert result.recommended_fraction >= 0
        assert result.recommended_fraction <= dynamic_controls.kelly_config['max_kelly_fraction']
        assert 0 <= result.win_probability <= 1
        assert result.average_win > 0 if len(wins) > 0 else True
        assert result.average_loss > 0 if len(losses) > 0 else True

    @pytest.mark.asyncio
    async def test_adaptive_position_sizing(self, dynamic_controls, sample_market_data):
        """Test adaptive position sizing."""
        symbol = 'BTCUSDT'
        account_balance = 100000
        confidence = 0.8

        result = await dynamic_controls.calculate_adaptive_position_size(
            symbol, account_balance, sample_market_data, confidence
        )

        assert result.symbol == symbol
        assert result.recommended_size > 0
        assert result.confidence == confidence
        assert len(result.adjustment_factors) > 0
        assert len(result.safety_buffers) > 0
        assert 1 <= result.priority <= 10

    @pytest.mark.asyncio
    async def test_dynamic_risk_limits_update(self, dynamic_controls, sample_market_data):
        """Test dynamic risk limits updates."""
        result = await dynamic_controls.update_dynamic_risk_limits(sample_market_data)

        assert result.regime_adjusted
        assert result.max_position_size > 0
        assert result.max_portfolio_risk > 0
        assert result.max_drawdown > 0
        assert result.leverage_limit > 0


class TestEnhancedComplianceEngine:
    """Test cases for Enhanced Compliance Engine."""

    @pytest.fixture
    def compliance_engine(self):
        """Create compliance engine instance for testing."""
        # Use temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        config = {
            'db_path': db_path,
            'max_position_size_pct': 0.25,
            'max_daily_trades': 100,
            'record_retention_years': 1  # Reduced for testing
        }

        engine = EnhancedComplianceEngine(config)
        yield engine

        # Cleanup
        engine._init_database()  # Close connections
        os.unlink(db_path)

    @pytest.fixture
    def sample_order(self):
        """Create sample order for testing."""
        return {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 1.0,
            'price': 50000,
            'client_id': 'client_001',
            'venue': 'regulated_market'
        }

    @pytest.mark.asyncio
    async def test_pre_trade_compliance_check(self, compliance_engine, sample_order):
        """Test pre-trade compliance checking."""
        checks = await compliance_engine.comprehensive_pre_trade_compliance_check(sample_order)

        assert len(checks) > 0
        for check in checks:
            assert check.check_type
            assert check.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING,
                                 ComplianceStatus.NON_COMPLIANT]
            assert check.severity in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            assert check.recommendation
            assert check.regulatory_reference

    @pytest.mark.asyncio
    async def test_trade_capture(self, compliance_engine):
        """Test trade capture functionality."""
        trade_data = {
            'instrument_id': 'BTCUSDT',
            'venue': 'regulated_market',
            'execution_time': datetime.utcnow(),
            'price': 50000,
            'quantity': 1.0,
            'side': 'BUY',
            'counterparty': 'exchange_001',
            'client_id': 'client_001',
            'order_id': 'order_001'
        }

        result = await compliance_engine.capture_trade(trade_data)

        assert result.trade_id
        assert result.instrument_id == 'BTCUSDT'
        assert result.price == 50000
        assert result.quantity == 1.0
        assert result.side == 'BUY'

    @pytest.mark.asyncio
    async def test_best_execution_analysis(self, compliance_engine):
        """Test best execution analysis."""
        instrument_id = 'BTCUSDT'
        trade_data = {
            'price': 50000,
            'quantity': 1.0,
            'timing_cost': 10,
            'market_impact': 50
        }

        venue_data = {
            'venue_1': {
                'fees': 5,
                'commission': 10,
                'spread': 20,
                'price': 50010
            },
            'venue_2': {
                'fees': 3,
                'commission': 15,
                'spread': 15,
                'price': 50005
            }
        }

        result = await compliance_engine.perform_best_execution_analysis(
            instrument_id, trade_data, venue_data
        )

        assert result.instrument_id == instrument_id
        assert len(result.venues_analyzed) == 2
        assert result.selected_venue in ['venue_1', 'venue_2']
        assert 0 <= result.execution_quality_score <= 100
        assert result.justification

    @pytest.mark.asyncio
    async def test_regulatory_report_generation(self, compliance_engine):
        """Test regulatory report generation."""
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()

        # Test different report types
        for report_type in [ReportType.DAILY_SUMMARY, ReportType.TRANSACTION_REPORT,
                          ReportType.BEST_EXECUTION_REPORT]:
            result = await compliance_engine.generate_regulatory_report(
                report_type, start_date, end_date
            )

            assert result['report_type'] == report_type.value
            assert 'reporting_period' in result
            assert 'generated_at' in result
            assert 'compliance_engine_version' in result


class TestRealTimeRiskDashboard:
    """Test cases for Real-Time Risk Dashboard."""

    @pytest.fixture
    def risk_dashboard(self):
        """Create risk dashboard instance for testing."""
        config = {
            'update_interval': 1,  # 1 second for testing
            'max_data_points': 100,
            'enable_alerts': True,
            'websocket_enabled': False  # Disable for testing
        }
        return RealTimeRiskDashboard(config)

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.utcnow(), periods=50, freq='D')
        prices = 50000 * (1 + np.cumsum(np.random.normal(0, 0.02, 50)))

        return pd.DataFrame({
            'open': prices * np.random.uniform(0.99, 1.01, 50),
            'high': prices * np.random.uniform(1.00, 1.05, 50),
            'low': prices * np.random.uniform(0.95, 1.00, 50),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 50)
        }, index=dates)

    @pytest.mark.asyncio
    async def test_market_data_update(self, risk_dashboard, sample_market_data):
        """Test market data update functionality."""
        symbol = 'BTCUSDT'
        await risk_dashboard.update_market_data(symbol, sample_market_data)

        assert symbol in risk_dashboard.market_data_stream
        assert len(risk_dashboard.market_data_stream[symbol]) == 50

    @pytest.mark.asyncio
    async def test_alert_creation(self, risk_dashboard):
        """Test alert creation and management."""
        # Create a test alert
        await risk_dashboard._create_alert(
            RiskMetricType.PORTFOLIO_VAR,
            AlertSeverity.HIGH,
            "High VaR Alert",
            "Portfolio VaR exceeds threshold",
            0.05,
            0.03
        )

        assert len(risk_dashboard.active_alerts) == 1
        assert len(risk_dashboard.alert_history) == 1

        alert = list(risk_dashboard.active_alerts.values())[0]
        assert alert.metric_type == RiskMetricType.PORTFOLIO_VAR
        assert alert.severity == AlertSeverity.HIGH
        assert alert.current_value == 0.05
        assert alert.threshold_value == 0.03

    @pytest.mark.asyncio
    async def test_dashboard_visualizations(self, risk_dashboard, sample_market_data):
        """Test dashboard visualization generation."""
        # Update market data first
        await risk_dashboard.update_market_data('BTCUSDT', sample_market_data)
        await risk_dashboard.update_market_data('ETHUSDT', sample_market_data)

        # Generate visualizations
        visualizations = await risk_dashboard.generate_dashboard_visualizations()

        assert len(visualizations) > 0

        # Check specific visualizations
        assert 'risk_metrics_overview' in visualizations
        assert 'alerts_panel' in visualizations
        assert 'portfolio_composition' in visualizations

        # Verify visualization structure
        for viz_name, viz_data in visualizations.items():
            assert 'type' in viz_data
            if viz_name != 'alerts_panel':  # Alerts panel returns data, not chart
                assert 'chart' in viz_data

    def test_alert_threshold_initialization(self, risk_dashboard):
        """Test alert threshold initialization."""
        thresholds = risk_dashboard.dashboard_config.alert_thresholds

        assert RiskMetricType.PORTFOLIO_VAR in thresholds
        assert RiskMetricType.MAX_DRAWDOWN in thresholds
        assert RiskMetricType.VOLATILITY in thresholds

        for metric_type, threshold_config in thresholds.items():
            assert 'warning' in threshold_config
            assert 'critical' in threshold_config
            assert threshold_config['warning'] < threshold_config['critical']


class TestInstitutionalRiskSystemIntegration:
    """Integration tests for the complete Institutional Risk System."""

    @pytest.fixture
    def risk_system(self):
        """Create risk system instance for testing."""
        config = {
            'mode': 'simulation',
            'auto_approve_threshold': 0.8,
            'auto_reject_threshold': 0.3,
            'enable_real_time_monitoring': False,  # Disable for testing
            'var_config': {'monte_carlo_simulations': 500},  # Reduced for testing
            'compliance_config': {
                'max_daily_trades': 50,
                'record_retention_years': 1
            }
        }
        return InstitutionalRiskSystem(config)

    @pytest.mark.asyncio
    async def test_system_initialization(self, risk_system):
        """Test system initialization."""
        await risk_system.initialize()

        assert risk_system.system_status.is_healthy
        assert risk_system.system_status.mode == RiskSystemMode.SIMULATION
        assert len(risk_system.system_status.components_status) == 5
        assert all(risk_system.system_status.components_status.values())

    @pytest.mark.asyncio
    async def test_comprehensive_risk_assessment(self, risk_system):
        """Test comprehensive risk assessment workflow."""
        await risk_system.initialize()

        # Create test trade request
        trade_request = {
            'trade_id': 'test_trade_001',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 1.0,
            'price': 50000,
            'confidence': 0.8,
            'client_id': 'client_001',
            'venue': 'regulated_market'
        }

        # Perform risk assessment
        assessment = await risk_system.comprehensive_risk_assessment(trade_request)

        assert assessment.trade_id == 'test_trade_001'
        assert assessment.symbol == 'BTCUSDT'
        assert assessment.side == 'BUY'
        assert assessment.quantity == 1.0
        assert assessment.price == 50000
        assert assessment.decision in [RiskDecision.APPROVED, RiskDecision.REJECTED,
                                    RiskDecision.MODIFIED, RiskDecision.DEFERRED]
        assert 0 <= assessment.risk_score <= 100
        assert 0 <= assessment.confidence <= 1
        assert assessment.compliance_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING,
                                              ComplianceStatus.NON_COMPLIANT]

    @pytest.mark.asyncio
    async def test_parallel_assessments(self, risk_system):
        """Test parallel risk assessment processing."""
        await risk_system.initialize()

        # Create multiple trade requests
        trade_requests = [
            {
                'trade_id': f'test_trade_{i:03d}',
                'symbol': 'BTCUSDT',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'quantity': 0.1 + i * 0.01,
                'price': 50000 + i * 100,
                'confidence': 0.7 + (i % 3) * 0.1
            }
            for i in range(10)
        ]

        # Process assessments in parallel
        assessments = await asyncio.gather(*[
            risk_system.comprehensive_risk_assessment(trade_request)
            for trade_request in trade_requests
        ])

        assert len(assessments) == 10
        for i, assessment in enumerate(assessments):
            assert assessment.trade_id == f'test_trade_{i:03d}'
            assert assessment.decision in [RiskDecision.APPROVED, RiskDecision.REJECTED,
                                        RiskDecision.MODIFIED, RiskDecision.DEFERRED]

    @pytest.mark.asyncio
    async def test_system_report_generation(self, risk_system):
        """Test system report generation."""
        await risk_system.initialize()

        # Perform a few assessments to generate data
        for i in range(3):
            trade_request = {
                'trade_id': f'report_test_{i}',
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'quantity': 0.5,
                'price': 50000,
                'confidence': 0.8
            }
            await risk_system.comprehensive_risk_assessment(trade_request)

        # Generate system report
        report = await risk_system.generate_system_report()

        assert 'report_timestamp' in report
        assert 'system_status' in report
        assert 'performance_metrics' in report
        assert 'risk_metrics' in report
        assert 'data_quality' in report

        # Check system status
        assert report['system_status']['is_healthy']
        assert report['system_status']['uptime_seconds'] > 0

        # Check performance metrics
        assert report['performance_metrics']['total_assessments'] == 3
        assert report['performance_metrics']['avg_assessment_time'] >= 0
        assert 0 <= report['performance_metrics']['approval_rate'] <= 1

    @pytest.mark.asyncio
    async def test_system_shutdown(self, risk_system):
        """Test system shutdown process."""
        await risk_system.initialize()

        # Verify system is running
        assert risk_system.system_status.is_healthy

        # Shutdown system
        await risk_system.shutdown()

        # Verify system is shut down gracefully
        assert not risk_system.system_config['enable_real_time_monitoring']


class TestPerformanceAndScalability:
    """Performance and scalability tests."""

    @pytest.mark.asyncio
    async def test_var_calculation_performance(self):
        """Test VaR calculation performance with different data sizes."""
        config = {'monte_carlo_simulations': 1000}
        var_calculator = EnhancedVaRCalculator(config)

        data_sizes = [100, 500, 1000, 5000]
        performance_results = {}

        for size in data_sizes:
            np.random.seed(42)
            data = pd.DataFrame({
                'returns': np.random.normal(0.001, 0.02, size)
            })

            start_time = asyncio.get_event_loop().time()
            result = await var_calculator.calculate_enhanced_var(
                data, VaRMethod.HISTORICAL, 0.95, 1
            )
            end_time = asyncio.get_event_loop().time()

            performance_results[size] = end_time - start_time
            assert result.var_value > 0

        # Performance should scale reasonably
        for size in data_sizes[1:]:
            assert performance_results[size] < 10.0  # Should complete within 10 seconds

    @pytest.mark.asyncio
    async def test_concurrent_risk_assessments(self):
        """Test concurrent risk assessment processing."""
        config = {
            'mode': 'simulation',
            'enable_real_time_monitoring': False,
            'max_parallel_assessments': 20
        }
        risk_system = InstitutionalRiskSystem(config)
        await risk_system.initialize()

        try:
            # Create many trade requests
            num_trades = 50
            trade_requests = [
                {
                    'trade_id': f'concurrent_test_{i:03d}',
                    'symbol': 'BTCUSDT',
                    'side': 'BUY' if i % 2 == 0 else 'SELL',
                    'quantity': 0.1,
                    'price': 50000,
                    'confidence': 0.8
                }
                for i in range(num_trades)
            ]

            # Process all assessments concurrently
            start_time = asyncio.get_event_loop().time()
            assessments = await asyncio.gather(*[
                risk_system.comprehensive_risk_assessment(trade_request)
                for trade_request in trade_requests
            ])
            end_time = asyncio.get_event_loop().time()

            # Verify all assessments completed
            assert len(assessments) == num_trades
            for assessment in assessments:
                assert assessment.decision in [RiskDecision.APPROVED, RiskDecision.REJECTED,
                                            RiskDecision.MODIFIED, RiskDecision.DEFERRED]

            # Check performance
            total_time = end_time - start_time
            avg_time_per_assessment = total_time / num_trades
            assert avg_time_per_assessment < 5.0  # Should average less than 5 seconds per assessment

        finally:
            await risk_system.shutdown()

    def test_memory_usage(self):
        """Test memory usage patterns."""
        # This would typically use memory profiling tools
        # For now, we'll just test that components don't grow unbounded

        config = {'max_data_points': 100}  # Limit data points for testing
        dashboard = RealTimeRiskDashboard(config)

        # Add many metrics
        for i in range(200):  # More than the max_data_points
            metric_type = RiskMetricType.PORTFOLIO_VAR
            metric = dashboard.risk_metrics[metric_type]

            # Mock metric
            mock_metric = Mock()
            mock_metric.value = 0.02 + i * 0.001
            mock_metric.timestamp = datetime.utcnow()
            mock_metric.status = 'normal'

            metric.append(mock_metric)

        # Should not exceed max_data_points
        assert len(dashboard.risk_metrics[RiskMetricType.PORTFOLIO_VAR]) <= 100


# Test data utilities and helpers

def create_comprehensive_test_data():
    """Create comprehensive test data for all components."""
    np.random.seed(42)

    # Market data for multiple symbols
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
    market_data = {}

    for symbol in symbols:
        dates = pd.date_range(end=datetime.utcnow(), periods=252, freq='D')

        # Generate realistic price data with trends and volatility
        initial_prices = {'BTCUSDT': 50000, 'ETHUSDT': 3000, 'ADAUSDT': 1.0,
                         'DOTUSDT': 20, 'LINKUSDT': 15}

        initial_price = initial_prices.get(symbol, 100)
        returns = np.random.normal(0.001, 0.02, 252)

        # Add some symbol-specific characteristics
        if symbol == 'BTCUSDT':
            returns += np.random.normal(0.0005, 0.01, 252)  # Slight uptrend
        elif symbol == 'ETHUSDT':
            returns += np.random.normal(0.0003, 0.015, 252)

        prices = initial_price * (1 + np.cumsum(returns))

        market_data[symbol] = pd.DataFrame({
            'open': prices * np.random.uniform(0.99, 1.01, 252),
            'high': prices * np.random.uniform(1.00, 1.05, 252),
            'low': prices * np.random.uniform(0.95, 1.00, 252),
            'close': prices,
            'volume': np.random.randint(1000000, 50000000, 252)
        }, index=dates)

    return market_data


def create_test_trade_history(num_trades=100):
    """Create test trade history with realistic characteristics."""
    np.random.seed(42)

    trades = []
    for i in range(num_trades):
        # Simulate realistic trade returns with positive expectancy
        base_return = 0.02
        volatility = 0.05
        trade_return = np.random.normal(base_return, volatility)

        trade = {
            'trade_id': f'trade_{i:04d}',
            'symbol': np.random.choice(['BTCUSDT', 'ETHUSDT', 'ADAUSDT']),
            'side': np.random.choice(['BUY', 'SELL']),
            'quantity': np.random.uniform(0.1, 2.0),
            'entry_price': 50000 * (1 + np.random.normal(0, 0.1)),
            'exit_price': None,  # Will be calculated based on return
            'return': trade_return,
            'pnl': trade_return * 10000,  # Assume $10k base position
            'entry_time': datetime.utcnow() - timedelta(days=np.random.randint(1, 30)),
            'exit_time': datetime.utcnow() - timedelta(days=np.random.randint(0, 30))
        }

        # Calculate exit price based on return
        if trade['return'] != 0:
            trade['exit_price'] = trade['entry_price'] * (1 + trade['return'])
        else:
            trade['exit_price'] = trade['entry_price']

        trades.append(trade)

    return pd.DataFrame(trades)


# pytest configuration and fixtures

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment for all tests."""
    # Set warning filters
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

    # Set random seed for reproducible tests
    np.random.seed(42)

    yield

    # Cleanup
    warnings.resetwarnings()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])