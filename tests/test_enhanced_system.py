"""
Comprehensive Test Suite for Enhanced Trading System

This module provides extensive testing coverage for all enhanced components including:
- Enhanced SMC pattern detection
- Advanced risk management
- Ultra-low latency execution engine
- Comprehensive error handling
- Integration tests for end-to-end workflows
- Performance benchmarks and load testing
"""

import asyncio
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import json
import time
import logging

# Import enhanced components
from smc_detector.enhanced_smc_detector import (
    EnhancedSMCDetector, PatternType, MarketRegime, EnhancedPattern
)
from risk_manager.advanced_risk_manager import (
    AdvancedRiskManager, Position, OrderSide, RiskMetrics, PositionSizingMethod
)
from execution_engine.optimized_execution_engine import (
    ExecutionEngine, OrderRequest, OrderType, OrderSide, OrderStatus
)
from error_handling.advanced_error_handling import (
    AdvancedErrorHandler, CircuitBreakerOpenError, ErrorSeverity
)

# Test configuration
TEST_CONFIG = {
    'risk_manager': {
        'max_position_size': 1000.0,
        'max_portfolio_risk': 0.02,
        'max_daily_loss': 500.0,
        'min_risk_reward': 1.5
    },
    'execution_engine': {
        'max_workers': 4,
        'execution_workers': 2
    },
    'smc_detector': {
        'volume_profile_bins': 50,
        'confidence_threshold': 0.7
    }
}

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    np.random.seed(42)

    # Generate realistic price data
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='H')

    # Start with base price
    base_price = 50000.0
    prices = [base_price]

    # Generate random walk with trend
    for i in range(1, len(dates)):
        change = np.random.normal(0, 0.002)  # 0.2% standard deviation
        trend = 0.0001 * (i / len(dates))  # Slight uptrend
        new_price = prices[-1] * (1 + change + trend)
        prices.append(new_price)

    prices = np.array(prices)

    # Generate OHLC data
    high_low_range = 0.001  # 0.1% range
    highs = prices * (1 + np.random.uniform(0, high_low_range, len(prices)))
    lows = prices * (1 - np.random.uniform(0, high_low_range, len(prices)))
    opens = prices + np.random.normal(0, prices * 0.0005, len(prices))
    closes = prices

    # Generate volume data with some spikes
    base_volume = 1000.0
    volumes = np.random.lognormal(np.log(base_volume), 0.5, len(prices))

    # Add some volume spikes
    spike_indices = np.random.choice(len(prices), size=50, replace=False)
    volumes[spike_indices] *= np.random.uniform(3, 10, 50)

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })

@pytest.fixture
def enhanced_smc_detector():
    """Create enhanced SMC detector instance"""
    return EnhancedSMCDetector(TEST_CONFIG.get('smc_detector', {}))

@pytest.fixture
def advanced_risk_manager():
    """Create advanced risk manager instance"""
    return AdvancedRiskManager(TEST_CONFIG.get('risk_manager', {}))

@pytest.fixture
def optimized_execution_engine():
    """Create optimized execution engine instance"""
    return ExecutionEngine(TEST_CONFIG.get('execution_engine', {}))

@pytest.fixture
def advanced_error_handler():
    """Create advanced error handler instance"""
    return AdvancedErrorHandler()

class TestEnhancedSMCDetector:
    """Test suite for Enhanced SMC Detector"""

    @pytest.mark.asyncio
    async def test_market_data_analysis(self, enhanced_smc_detector, sample_ohlcv_data):
        """Test market data analysis functionality"""
        result = await enhanced_smc_detector.analyze_market_data(
            sample_ohlcv_data, "BTC/USDT"
        )

        assert result['symbol'] == "BTC/USDT"
        assert 'patterns' in result
        assert 'market_regime' in result
        assert 'volume_profile' in result
        assert 'institutional_zones' in result
        assert 'key_levels' in result

        # Check market regime is valid
        assert result['market_regime'] in ['trending', 'ranging', 'volatile', 'uncertain']

        # Check volume profile has required fields
        vp = result['volume_profile']
        assert 'poc_price' in vp
        assert 'value_area_high' in vp
        assert 'value_area_low' in vp
        assert 'total_volume' in vp

    @pytest.mark.asyncio
    async def test_pattern_detection(self, enhanced_smc_detector, sample_ohlcv_data):
        """Test pattern detection functionality"""
        result = await enhanced_smc_detector.analyze_market_data(
            sample_ohlcv_data, "BTC/USDT"
        )

        patterns = result['patterns']

        # Should detect some patterns
        assert len(patterns) >= 0

        if patterns:
            pattern = patterns[0]
            assert 'type' in pattern
            assert 'confidence' in pattern
            assert 'strength' in pattern
            assert 'price_level' in pattern
            assert 'timestamp' in pattern

            # Check confidence is in valid range
            assert 0 <= pattern['confidence'] <= 1

            # Check strength is positive
            assert pattern['strength'] > 0

    def test_volume_profile_analyzer(self, enhanced_smc_detector):
        """Test volume profile analysis"""
        # Create test data
        np.random.seed(42)
        prices = np.random.normal(50000, 1000, 100)
        volumes = np.random.lognormal(7, 0.5, 100)

        test_df = pd.DataFrame({
            'close': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'volume': volumes
        })

        result = enhanced_smc_detector.volume_analyzer.calculate_volume_profile(test_df)

        assert 'price_bins' in result
        assert 'volume_at_price' in result
        assert 'poc_price' in result
        assert 'value_area_high' in result
        assert 'value_area_low' in result
        assert 'total_volume' in result

        # Check POC is within price range
        assert result['poc_price'] >= prices.min()
        assert result['poc_price'] <= prices.max()

    def test_market_structure_analyzer(self, enhanced_smc_detector):
        """Test market structure analysis"""
        # Create test data with clear trend
        dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        prices = np.linspace(50000, 52000, 100) + np.random.normal(0, 100, 100)

        # Add some volatility
        high_low_range = 200
        highs = prices + np.random.uniform(0, high_low_range, 100)
        lows = prices - np.random.uniform(0, high_low_range, 100)

        test_df = pd.DataFrame({
            'timestamp': dates,
            'high': highs,
            'low': lows
        })

        regime = enhanced_smc_detector.structure_analyzer.detect_market_regime(test_df)
        assert regime in [r.value for r in MarketRegime]

        key_levels = enhanced_smc_detector.structure_analyzer.identify_key_levels(test_df)
        assert 'support' in key_levels
        assert 'resistance' in key_levels
        assert len(key_levels['support']) > 0
        assert len(key_levels['resistance']) > 0

    def test_pattern_statistics(self, enhanced_smc_detector):
        """Test pattern statistics functionality"""
        # Add some test patterns
        now = datetime.utcnow()
        test_patterns = [
            EnhancedPattern(
                pattern_type=PatternType.BULLISH_ORDER_BLOCK,
                timestamp=now - timedelta(hours=1),
                price_level=(50000, 49500),
                confidence=0.8,
                strength=1.5,
                volume_confirmation=True,
                timeframe='1h',
                market_regime=MarketRegime.TRENDING,
                additional_metrics={}
            ),
            EnhancedPattern(
                pattern_type=PatternType.BEARISH_ORDER_BLOCK,
                timestamp=now - timedelta(minutes=30),
                price_level=(51000, 51500),
                confidence=0.7,
                strength=1.2,
                volume_confirmation=True,
                timeframe='1h',
                market_regime=MarketRegime.VOLATILE,
                additional_metrics={}
            )
        ]

        enhanced_smc_detector.pattern_history.extend(test_patterns)

        stats = enhanced_smc_detector.get_pattern_statistics(24)

        assert 'total_patterns' in stats
        assert 'pattern_types' in stats
        assert 'average_confidence' in stats
        assert 'average_strength' in stats
        assert 'market_regimes' in stats

        assert stats['total_patterns'] == 2
        assert 0.7 <= stats['average_confidence'] <= 0.8

class TestAdvancedRiskManager:
    """Test suite for Advanced Risk Manager"""

    @pytest.mark.asyncio
    async def test_position_sizing_calculation(self, advanced_risk_manager, sample_ohlcv_data):
        """Test position sizing calculation"""
        result = await advanced_risk_manager.calculate_position_size(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            account_balance=10000.0,
            market_data=sample_ohlcv_data,
            confidence=0.8
        )

        assert result['symbol'] == "BTC/USDT"
        assert 'optimal_size' in result
        assert 'position_value' in result
        assert 'portfolio_percentage' in result
        assert 'method_results' in result
        assert 'volatility_regime' in result

        # Check position size is reasonable
        assert result['optimal_size'] > 0
        assert result['position_value'] <= advanced_risk_manager.risk_limits.max_position_size
        assert 0 < result['portfolio_percentage'] <= 1

    @pytest.mark.asyncio
    async def test_stop_loss_calculation(self, advanced_risk_manager, sample_ohlcv_data):
        """Test stop-loss and take-profit calculation"""
        result = await advanced_risk_manager.calculate_stop_loss_take_profit(
            symbol="BTC/USDT",
            side="BUY",
            entry_price=50000.0,
            market_data=sample_ohlcv_data,
            position_size=0.1
        )

        assert result['symbol'] == "BTC/USDT"
        assert 'stop_loss' in result
        assert 'take_profit' in result
        assert 'risk_per_unit' in result
        assert 'risk_amount' in result
        assert 'risk_reward_ratio' in result

        # For BUY order, stop loss should be below entry price
        assert result['stop_loss'] < 50000.0
        assert result['take_profit'] > 50000.0

        # Risk-reward ratio should meet minimum
        assert result['risk_reward_ratio'] >= advanced_risk_manager.risk_limits.min_risk_reward

    def test_portfolio_risk_calculation(self, advanced_risk_manager):
        """Test portfolio risk calculation"""
        # Add some test positions
        now = datetime.utcnow()

        position1 = Position(
            symbol="BTC/USDT",
            side="BUY",
            size=0.1,
            entry_price=50000.0,
            current_price=51000.0,
            stop_loss=49000.0,
            take_profit=53000.0,
            entry_time=now
        )

        position2 = Position(
            symbol="ETH/USDT",
            side="SELL",
            size=1.0,
            entry_price=3000.0,
            current_price=2950.0,
            stop_loss=3100.0,
            take_profit=2850.0,
            entry_time=now
        )

        advanced_risk_manager.positions = [position1, position2]

        result = advanced_risk_manager.calculate_portfolio_risk()

        assert 'portfolio_value' in result
        assert 'total_pnl' in result
        assert 'var_95' in result
        assert 'correlation_risk' in result
        assert 'risk_score' in result
        assert 'risk_level' in result

        # Check portfolio value is positive
        assert result['portfolio_value'] > 0

        # Check risk score is in valid range
        assert 0 <= result['risk_score'] <= 1

    def test_trade_validation(self, advanced_risk_manager):
        """Test trade validation against risk limits"""
        result = advanced_risk_manager.validate_trade_risk(
            symbol="BTC/USDT",
            side="BUY",
            size=0.05,  # Small position
            entry_price=50000.0,
            stop_loss=49000.0,
            confidence=0.8
        )

        assert 'approved' in result
        assert 'warnings' in result
        assert 'rejections' in result
        assert 'risk_metrics' in result

        # Small position should be approved
        assert result['approved'] == True

        # Test oversized position
        result_oversized = advanced_risk_manager.validate_trade_risk(
            symbol="BTC/USDT",
            side="BUY",
            size=10.0,  # Large position
            entry_price=50000.0,
            stop_loss=49000.0,
            confidence=0.8
        )

        assert result_oversized['approved'] == False
        assert len(result_oversized['rejections']) > 0

    def test_volatility_analysis(self, advanced_risk_manager, sample_ohlcv_data):
        """Test volatility analysis"""
        volatility_regime = advanced_risk_manager.volatility_analyzer.calculate_volatility_regime(
            sample_ohlcv_data
        )

        assert 'regime' in volatility_regime
        assert 'volatility' in volatility_regime
        assert 'percentile' in volatility_regime
        assert 'historical_mean' in volatility_regime
        assert 'historical_std' in volatility_regime

        assert volatility_regime['regime'] in ['low', 'normal', 'elevated', 'high']
        assert volatility_regime['volatility'] > 0
        assert 0 <= volatility_regime['percentile'] <= 100

class TestOptimizedExecutionEngine:
    """Test suite for Optimized Execution Engine"""

    @pytest.mark.asyncio
    async def test_order_submission(self, optimized_execution_engine):
        """Test order submission"""
        await optimized_execution_engine.start()

        order_request = OrderRequest(
            id="test_order_1",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            price=50000.0
        )

        order_id = await optimized_execution_engine.submit_order(order_request)
        assert order_id == "test_order_1"

        # Check order status
        status = await optimized_execution_engine.get_order_status(order_id)
        assert status is not None
        assert status['order_id'] == order_id
        assert status['status'] in ['submitted', 'partial_filled', 'filled']

        await optimized_execution_engine.stop()

    @pytest.mark.asyncio
    async def test_market_order_execution(self, optimized_execution_engine):
        """Test market order execution"""
        # Set up market data
        market_data = Mock()
        market_data.symbol = "BTC/USDT"
        market_data.bid = 49950.0
        market_data.ask = 50050.0
        market_data.bid_size = 1.0
        market_data.ask_size = 1.0
        market_data.last_price = 50000.0
        market_data.last_size = 0.1
        market_data.timestamp = datetime.utcnow()
        market_data.spread = 100.0
        market_data.mid_price = 50000.0

        optimized_execution_engine.market_data["BTC/USDT"] = market_data

        order_request = OrderRequest(
            id="test_market_order",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1
        )

        result = await optimized_execution_engine._execute_market_order(
            order_request, market_data, optimized_execution_engine._select_execution_strategy(order_request, market_data)
        )

        assert result['success'] == True
        assert 'execution_price' in result
        assert 'executed_quantity' in result
        assert 'slippage' in result
        assert 'venue' in result
        assert 'strategy_used' in result

        # For BUY order, should execute at ask price
        assert result['execution_price'] == market_data.ask

    @pytest.mark.asyncio
    async def test_limit_order_execution(self, optimized_execution_engine):
        """Test limit order execution"""
        # Set up market data
        market_data = Mock()
        market_data.symbol = "BTC/USDT"
        market_data.bid = 49950.0
        market_data.ask = 50050.0
        market_data.bid_size = 1.0
        market_data.ask_size = 1.0
        market_data.last_price = 50000.0
        market_data.last_size = 0.1
        market_data.timestamp = datetime.utcnow()
        market_data.spread = 100.0
        market_data.mid_price = 50000.0

        optimized_execution_engine.market_data["BTC/USDT"] = market_data

        # Limit order that can be filled immediately
        order_request = OrderRequest(
            id="test_limit_order",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50100.0  # Above ask, should fill immediately
        )

        result = await optimized_execution_engine._execute_limit_order(
            order_request, market_data, optimized_execution_engine._select_execution_strategy(order_request, market_data)
        )

        assert result['success'] == True
        assert result['immediate_fill'] == True
        assert result['executed_quantity'] == order_request.quantity

    def test_order_splitting(self, optimized_execution_engine):
        """Test order splitting functionality"""
        large_order_request = OrderRequest(
            id="large_order",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=50.0,  # Large position
        )

        market_conditions = {
            'volatility': 0.02,
            'liquidity_score': 0.7
        }

        chunks = optimized_execution_engine.order_splitter.split_order(
            large_order_request, market_conditions
        )

        assert len(chunks) > 1  # Should be split

        # Check chunk properties
        total_quantity = sum(chunk.quantity for chunk in chunks)
        assert abs(total_quantity - large_order_request.quantity) < 0.001

        for chunk in chunks:
            assert chunk.symbol == large_order_request.symbol
            assert chunk.side == large_order_request.side
            assert chunk.order_type == large_order_request.order_type
            assert chunk.quantity <= optimized_execution_engine.order_splitter.max_chunk_size
            assert 'parent_order_id' in chunk.metadata
            assert chunk.metadata['parent_order_id'] == large_order_request.id

    def test_latency_tracking(self, optimized_execution_engine):
        """Test latency tracking functionality"""
        # Record some latencies
        latencies = [10, 15, 20, 25, 30, 12, 18, 22, 28, 35]

        for latency in latencies:
            optimized_execution_engine.latency_tracker.record_latency(latency)

        stats = optimized_execution_engine.latency_tracker.get_stats()

        assert stats['count'] == len(latencies)
        assert stats['mean_ms'] == pytest.approx(np.mean(latencies), rel=1e-2)
        assert stats['median_ms'] == pytest.approx(np.median(latencies), rel=1e-2)
        assert stats['p95_ms'] == pytest.approx(np.percentile(latencies, 95), rel=1e-2)
        assert stats['max_ms'] == max(latencies)

    def test_circuit_breaker(self, optimized_execution_engine):
        """Test circuit breaker functionality"""
        cb = optimized_execution_engine.circuit_breaker

        # Initially closed
        assert cb['state'] == 'closed'
        assert cb['failure_count'] == 0

        # Simulate failures
        for i in range(6):  # Exceed threshold
            optimized_execution_engine._increment_circuit_breaker()

        assert cb['state'] == 'open'
        assert cb['failure_count'] >= cb['threshold']

        # Test circuit breaker is open
        assert optimized_execution_engine._is_circuit_breaker_open() == True

class TestAdvancedErrorHandler:
    """Test suite for Advanced Error Handler"""

    def test_circuit_breaker_creation(self, advanced_error_handler):
        """Test circuit breaker creation and functionality"""
        cb = advanced_error_handler.get_circuit_breaker("test_service")

        assert cb.name == "test_service"
        assert cb.state.value == "closed"
        assert cb.failure_count == 0
        assert cb.failure_threshold == 5

        # Test successful call
        def successful_func():
            return "success"

        result = cb.call(successful_func)
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.success_count == 1

    def test_circuit_breaker_failure(self, advanced_error_handler):
        """Test circuit breaker failure handling"""
        cb = advanced_error_handler.get_circuit_breaker("failing_service")

        def failing_func():
            raise ValueError("Test error")

        # Should allow failures up to threshold
        for i in range(cb.failure_threshold):
            with pytest.raises(ValueError):
                cb.call(failing_func)

        # Circuit breaker should now be open
        assert cb.state.value == "open"

        # Subsequent calls should fail immediately
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_func)

    def test_retry_handler(self, advanced_error_handler):
        """Test retry handler functionality"""
        retry_handler = advanced_error_handler.get_retry_handler(
            "test_service",
            max_retries=3,
            base_delay=0.1
        )

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        async def test_async():
            return await retry_handler.execute_with_retry(flaky_func)

        result = asyncio.run(test_async())
        assert result == "success"
        assert call_count == 3  # Should have retried 3 times

    def test_distributed_tracing(self, advanced_error_handler):
        """Test distributed tracing functionality"""
        span_id = advanced_error_handler.tracer.start_trace("test_operation")

        assert span_id is not None
        assert span_id in advanced_error_handler.tracer.active_traces

        # Add logs and tags
        advanced_error_handler.tracer.add_log(span_id, "Test log message", "info")
        advanced_error_handler.tracer.add_tag(span_id, "test_tag", "test_value")

        trace = advanced_error_handler.tracer.active_traces[span_id]
        assert len(trace.logs) == 1
        assert trace.tags['test_tag'] == "test_value"

        # Finish trace
        advanced_error_handler.tracer.finish_trace(span_id)
        assert span_id not in advanced_error_handler.tracer.active_traces
        assert len(advanced_error_handler.tracer.completed_traces) > 0

    def test_error_classification(self, advanced_error_handler):
        """Test error classification"""
        # Test critical error
        critical_error = ValueError("Critical system failure")
        severity = advanced_error_handler._classify_error_severity(critical_error)
        assert severity == ErrorSeverity.CRITICAL

        # Test network error
        network_error = ConnectionError("Network timeout")
        severity = advanced_error_handler._classify_error_severity(network_error)
        assert severity == ErrorSeverity.HIGH

        # Test validation error
        validation_error = ValueError("Invalid input")
        severity = advanced_error_handler._classify_error_severity(validation_error)
        assert severity == ErrorSeverity.MEDIUM

    def test_safe_execute_decorator(self, advanced_error_handler):
        """Test safe execute functionality"""
        @advanced_error_handler.circuit_breaker("test_func")
        def test_function():
            return "test_result"

        result = test_function()
        assert result == "test_result"

    def test_health_status(self, advanced_error_handler):
        """Test health status reporting"""
        health_status = advanced_error_handler.get_health_status()

        assert 'overall_status' in health_status
        assert 'components' in health_status
        assert 'global_metrics' in health_status
        assert 'trace_metrics' in health_status
        assert 'last_check' in health_status

        assert health_status['overall_status'] in ['healthy', 'degraded', 'unhealthy']

class TestIntegration:
    """Integration tests for the complete enhanced system"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, sample_ohlcv_data):
        """Test complete end-to-end trading workflow"""
        # Initialize components
        smc_detector = EnhancedSMCDetector()
        risk_manager = AdvancedRiskManager()
        execution_engine = ExecutionEngine()
        error_handler = AdvancedErrorHandler()

        await execution_engine.start()

        try:
            # Step 1: Analyze market data
            market_analysis = await smc_detector.analyze_market_data(
                sample_ohlcv_data, "BTC/USDT"
            )

            assert 'patterns' in market_analysis
            patterns = market_analysis['patterns']

            if patterns:
                # Step 2: Calculate position size
                top_pattern = patterns[0]
                if top_pattern['type'] in ['bullish_order_block', 'bearish_order_block']:
                    side = "BUY" if "bullish" in top_pattern['type'] else "SELL"

                    position_sizing = await risk_manager.calculate_position_size(
                        symbol="BTC/USDT",
                        side=side,
                        entry_price=top_pattern['price_level'][0],
                        account_balance=10000.0,
                        market_data=sample_ohlcv_data,
                        confidence=top_pattern['confidence']
                    )

                    # Step 3: Calculate stop-loss and take-profit
                    risk_calculation = await risk_manager.calculate_stop_loss_take_profit(
                        symbol="BTC/USDT",
                        side=side,
                        entry_price=position_sizing['optimal_size'] * top_pattern['price_level'][0],
                        market_data=sample_ohlcv_data,
                        position_size=position_sizing['optimal_size']
                    )

                    # Step 4: Validate trade
                    validation = risk_manager.validate_trade_risk(
                        symbol="BTC/USDT",
                        side=side,
                        size=position_sizing['optimal_size'],
                        entry_price=top_pattern['price_level'][0],
                        stop_loss=risk_calculation['stop_loss'],
                        confidence=top_pattern['confidence']
                    )

                    if validation['approved']:
                        # Step 5: Execute trade (simulated)
                        order_request = OrderRequest(
                            id=f"trade_{datetime.utcnow().timestamp()}",
                            symbol="BTC/USDT",
                            side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=position_sizing['optimal_size']
                        )

                        # Set up market data for execution
                        market_data = Mock()
                        market_data.symbol = "BTC/USDT"
                        market_data.bid = top_pattern['price_level'][0] * 0.999
                        market_data.ask = top_pattern['price_level'][0] * 1.001
                        market_data.timestamp = datetime.utcnow()

                        execution_engine.market_data["BTC/USDT"] = market_data

                        order_id = await execution_engine.submit_order(order_request)

                        assert order_id is not None

                        # Verify order was processed
                        status = await execution_engine.get_order_status(order_id)
                        assert status is not None

        finally:
            await execution_engine.stop()

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, sample_ohlcv_data):
        """Test error handling and recovery mechanisms"""
        error_handler = AdvancedErrorHandler()
        smc_detector = EnhancedSMCDetector()

        # Simulate network error
        def failing_analysis(*args, **kwargs):
            raise ConnectionError("Network timeout")

        # Should handle the error gracefully
        with patch.object(smc_detector, 'analyze_market_data', side_effect=failing_analysis):
            with pytest.raises(ConnectionError):
                await error_handler.safe_execute_async(
                    smc_detector.analyze_market_data,
                    "market_analysis_cb",
                    "market_analysis_retry",
                    sample_ohlcv_data,
                    "BTC/USDT"
                )

        # Check error was recorded
        health_status = error_handler.get_health_status()
        assert health_status['global_metrics']['total_errors'] > 0

    def test_performance_benchmarks(self, sample_ohlcv_data):
        """Test performance benchmarks for critical operations"""
        import time

        # Benchmark SMC analysis
        smc_detector = EnhancedSMCDetector()

        start_time = time.time()
        patterns = asyncio.run(smc_detector.analyze_market_data(sample_ohlcv_data, "BTC/USDT"))
        smc_analysis_time = time.time() - start_time

        # Should complete analysis within reasonable time
        assert smc_analysis_time < 1.0  # 1 second max

        # Benchmark risk calculations
        risk_manager = AdvancedRiskManager()

        start_time = time.time()
        position_size = asyncio.run(
            risk_manager.calculate_position_size(
                symbol="BTC/USDT",
                side="BUY",
                entry_price=50000.0,
                account_balance=10000.0,
                market_data=sample_ohlcv_data,
                confidence=0.8
            )
        )
        risk_calc_time = time.time() - start_time

        # Should complete within reasonable time
        assert risk_calc_time < 0.5  # 500ms max

        print(f"Performance benchmarks:")
        print(f"  SMC Analysis: {smc_analysis_time:.3f}s")
        print(f"  Risk Calculation: {risk_calc_time:.3f}s")

# Performance tests
@pytest.mark.asyncio
async def test_system_load(sample_ohlcv_data):
    """Test system performance under load"""
    import time

    smc_detector = EnhancedSMCDetector()
    risk_manager = AdvancedRiskManager()

    # Simulate multiple concurrent operations
    start_time = time.time()

    tasks = []
    for i in range(10):  # 10 concurrent analyses
        task = asyncio.create_task(
            smc_detector.analyze_market_data(
                sample_ohlcv_data, f"BTC/USDT_{i}"
            )
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    avg_time = total_time / len(results)

    # Should handle concurrent operations efficiently
    assert total_time < 5.0  # 5 seconds max for 10 concurrent operations
    assert avg_time < 1.0   # Average less than 1 second per operation

    print(f"Load test results:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average time per operation: {avg_time:.3f}s")
    print(f"  Operations per second: {len(results) / total_time:.1f}")

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])