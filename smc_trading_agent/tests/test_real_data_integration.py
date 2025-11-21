#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Real Data Integration

Tests the complete flow from real market data through SMC detection
to ML decision making and trade execution.
"""

import asyncio
import pytest
import logging
import time
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_smc_enhanced import (
    RealMarketDataProcessor,
    EnhancedSMCDetector,
    EnhancedDecisionEngine,
    IntegratedRiskManager,
    TradingEngine
)
from monitoring.real_time_dashboard import get_dashboard_manager, initialize_dashboard_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRealDataIntegration:
    """Test suite for real data integration components."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "app": {
                "name": "SMC Trading Agent Test",
                "max_cycles": 5
            },
            "decision_engine": {
                "confidence_threshold": 0.6,
                "min_ml_confidence": 0.5
            },
            "risk_manager": {
                "stop_loss_percent": 2.0,
                "take_profit_ratio": 2.5
            },
            "ml_models": {
                "version": "v1.0",
                "path": "tests/models/",
                "sequence_length": 60
            }
        }

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Generate sample OHLCV data for testing."""
        import numpy as np

        np.random.seed(42)  # For reproducible tests

        dates = pd.date_range(end=datetime.now(), periods=200, freq='5T')
        base_price = 50000

        # Generate realistic price movement
        returns = np.random.normal(0, 0.002, 200)  # 0.2% std
        prices = [base_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        # Create OHLCV DataFrame
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.001))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.001))) for p in prices],
            'close': np.roll(prices, -1),
            'volume': np.random.uniform(1000, 5000, 200)
        }).set_index('timestamp')

        return data

    @pytest.fixture
    async def mock_live_data_client(self):
        """Mock LiveDataClient for testing."""
        mock_client = AsyncMock()

        # Mock successful data response
        sample_data = self.sample_ohlcv_data() if hasattr(self, 'sample_ohlcv_data') else self._generate_test_data()
        mock_client.get_latest_ohlcv_data.return_value = sample_data
        mock_client.get_metrics.return_value = {
            'total_requests': 10,
            'successful_requests': 9,
            'average_latency_ms': 45.2
        }
        mock_client.check_health.return_value = {
            'healthy': True,
            'backend_status': {'status': 'ok'},
            'timestamp': time.time()
        }

        return mock_client

    def _generate_test_data(self):
        """Generate test data when fixture not available."""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5T')
        base_price = 50000

        data = pd.DataFrame({
            'timestamp': dates,
            'open': [base_price] * 100,
            'high': [base_price * 1.01] * 100,
            'low': [base_price * 0.99] * 100,
            'close': [base_price * 1.005] * 100,
            'volume': [1000] * 100
        }).set_index('timestamp')

        return data

    @pytest.mark.asyncio
    async def test_real_market_data_processor(self, mock_live_data_client):
        """Test RealMarketDataProcessor functionality."""
        logger.info("Testing RealMarketDataProcessor...")

        # Patch the LiveDataClient
        with patch('run_smc_enhanced.LiveDataClient', return_value=mock_live_data_client):
            processor = RealMarketDataProcessor()

            # Test data retrieval
            data = await processor.get_latest_ohlcv_data("BTC/USDT", "1h")

            assert data is not None, "Should return data"
            assert not data.empty, "Data should not be empty"
            assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume']), "Should have OHLCV columns"

            # Test health status
            health = await processor.get_health_status()
            assert 'status' in health, "Health status should include status"
            assert 'requests' in health, "Health status should include request count"

            # Test cleanup
            await processor.close()

        logger.info("✅ RealMarketDataProcessor tests passed")

    @pytest.mark.asyncio
    async def test_enhanced_smc_detector(self, sample_ohlcv_data):
        """Test EnhancedSMCDetector functionality."""
        logger.info("Testing EnhancedSMCDetector...")

        detector = EnhancedSMCDetector()

        # Test order block detection
        order_blocks = await detector.detect_order_blocks(sample_ohlcv_data)

        assert isinstance(order_blocks, list), "Should return list of order blocks"

        # Check structure of order blocks
        for block in order_blocks:
            assert 'price_level' in block, "Order block should have price level"
            assert 'direction' in block, "Order block should have direction"
            assert 'strength' in block, "Order block should have strength"
            assert 'confidence' in block, "Order block should have confidence"
            assert 0 <= block['confidence'] <= 1, "Confidence should be between 0 and 1"

        # Test comprehensive pattern detection
        patterns = await detector.detect_all_patterns(sample_ohlcv_data)

        assert 'order_blocks' in patterns, "Should include order blocks"
        assert 'coch_patterns' in patterns, "Should include CHOCH patterns"
        assert 'bos_patterns' in patterns, "Should include BOS patterns"
        assert 'liquidity_sweeps' in patterns, "Should include liquidity sweeps"
        assert 'total_patterns' in patterns, "Should include total pattern count"
        assert 'analysis_time_ms' in patterns, "Should include analysis time"

        # Performance check
        assert patterns['analysis_time_ms'] < 100, f"Analysis should be fast ({patterns['analysis_time_ms']}ms)"

        logger.info(f"✅ EnhancedSMCDetector tests passed (found {patterns['total_patterns']} patterns)")

    @pytest.mark.asyncio
    async def test_enhanced_decision_engine(self, mock_config, sample_ohlcv_data):
        """Test EnhancedDecisionEngine functionality."""
        logger.info("Testing EnhancedDecisionEngine...")

        engine = EnhancedDecisionEngine(mock_config)

        # Create sample SMC patterns
        smc_patterns = {
            'order_blocks': [
                {
                    'price_level': (50000, 49500),
                    'direction': 'bullish',
                    'strength': 0.8,
                    'confidence': 0.75
                }
            ],
            'coch_patterns': [],
            'bos_patterns': [],
            'liquidity_sweeps': [],
            'total_patterns': 1
        }

        # Test decision making
        signal = await engine.make_decision(sample_ohlcv_data, smc_patterns)

        # Signal may be None if confidence is too low, that's valid
        if signal:
            assert 'action' in signal, "Signal should have action"
            assert 'confidence' in signal, "Signal should have confidence"
            assert 'entry_price' in signal, "Signal should have entry price"
            assert 'decision_method' in signal, "Signal should have decision method"
            assert 'smc_context' in signal, "Signal should have SMC context"

            # Check SMC context
            smc_ctx = signal['smc_context']
            assert 'total_patterns' in smc_ctx, "SMC context should have total patterns"
            assert 'order_blocks' in smc_ctx, "SMC context should have order block count"

            logger.info(f"✅ Decision engine generated signal: {signal['action']} @ {signal['entry_price']}")
        else:
            logger.info("✅ Decision engine correctly rejected low-confidence signal")

        # Test performance summary
        perf_summary = await engine.get_performance_summary()
        assert isinstance(perf_summary, dict), "Performance summary should be a dictionary"

        # Test health check
        health = await engine.health_check()
        assert 'overall_healthy' in health, "Health check should return overall status"

        logger.info("✅ EnhancedDecisionEngine tests passed")

    def test_integrated_risk_manager(self, mock_config):
        """Test IntegratedRiskManager functionality."""
        logger.info("Testing IntegratedRiskManager...")

        risk_manager = IntegratedRiskManager(mock_config)

        # Test stop loss calculation
        entry_price = 50000
        action = "BUY"
        order_blocks = [
            {
                'price_level': (49800, 49500),
                'direction': 'bullish'
            }
        ]
        smc_context = {'pattern_strength': 0.8}

        stop_loss = risk_manager.calculate_stop_loss(entry_price, action, order_blocks, smc_context)

        assert stop_loss < entry_price, "Stop loss should be below entry for BUY"
        assert stop_loss > 0, "Stop loss should be positive"

        # Test take profit calculation
        take_profit = risk_manager.calculate_take_profit(entry_price, stop_loss, action)

        assert take_profit > entry_price, "Take profit should be above entry for BUY"
        assert take_profit > stop_loss, "Take profit should be above stop loss"

        # Verify risk/reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        assert reward / risk >= mock_config['risk_manager']['take_profit_ratio'], "Should maintain risk/reward ratio"

        logger.info("✅ IntegratedRiskManager tests passed")

    def test_trading_engine(self, mock_config):
        """Test TradingEngine functionality."""
        logger.info("Testing TradingEngine...")

        trading_engine = TradingEngine(mock_config)

        # Test trade execution
        trade_details = {
            'action': 'BUY',
            'symbol': 'BTC/USDT',
            'entry_price': 50000,
            'confidence': 0.75,
            'decision_method': 'ml_ensemble',
            'stop_loss': 49000,
            'take_profit': 52000,
            'smc_context': {
                'total_patterns': 3,
                'order_blocks': 1
            }
        }

        result = trading_engine.execute_trade(trade_details)

        assert result == True, "Trade execution should succeed"
        assert trading_engine.trades_executed == 1, "Should track executed trades"

        # Check trade history
        history = trading_engine.get_trade_history()
        assert len(history) == 1, "Should have one trade in history"

        executed_trade = history[0]
        assert 'execution_id' in executed_trade, "Trade should have execution ID"
        assert 'executed_at' in executed_trade, "Trade should have execution timestamp"
        assert executed_trade['action'] == 'BUY', "Trade should preserve action"
        assert executed_trade['symbol'] == 'BTC/USDT', "Trade should preserve symbol"

        logger.info("✅ TradingEngine tests passed")

    @pytest.mark.asyncio
    async def test_end_to_end_integration(self, mock_config, mock_live_data_client):
        """Test complete end-to-end integration flow."""
        logger.info("Testing end-to-end integration...")

        # Initialize all components
        with patch('run_smc_enhanced.LiveDataClient', return_value=mock_live_data_client):
            market_processor = RealMarketDataProcessor()
            smc_detector = EnhancedSMCDetector()
            decision_engine = EnhancedDecisionEngine(mock_config)
            risk_manager = IntegratedRiskManager(mock_config)
            trading_engine = TradingEngine(mock_config)

            try:
                # Step 1: Get market data
                logger.info("Step 1: Fetching market data...")
                market_data = await market_processor.get_latest_ohlcv_data("BTC/USDT", "1h")

                assert market_data is not None, "Should get market data"
                assert not market_data.empty, "Market data should not be empty"

                # Step 2: SMC analysis
                logger.info("Step 2: Running SMC analysis...")
                smc_patterns = await smc_detector.detect_all_patterns(market_data)

                assert 'order_blocks' in smc_patterns, "Should detect order blocks"

                # Step 3: Decision making
                logger.info("Step 3: Making trading decision...")
                signal = await decision_engine.make_decision(market_data, smc_patterns)

                if signal:
                    logger.info(f"Step 4: Executing trade - {signal['action']}")

                    # Step 4: Risk management
                    stop_loss = risk_manager.calculate_stop_loss(
                        signal['entry_price'],
                        signal['action'],
                        smc_patterns['order_blocks'],
                        signal.get('smc_context', {})
                    )
                    take_profit = risk_manager.calculate_take_profit(
                        signal['entry_price'],
                        stop_loss,
                        signal['action']
                    )

                    # Step 5: Trade execution
                    final_trade = {
                        **signal,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }

                    success = trading_engine.execute_trade(final_trade)
                    assert success, "Trade execution should succeed"

                    logger.info(f"✅ End-to-end integration successful - Trade executed: {signal['action']}")
                else:
                    logger.info("✅ End-to-end integration successful - No signal generated (valid behavior)")

                # Verify component health
                data_health = await market_processor.get_health_status()
                assert data_health['status'] in ['healthy', 'degraded'], "Data processor should be operational"

                decision_health = await decision_engine.health_check()
                assert 'overall_healthy' in decision_health, "Decision engine should report health status"

            finally:
                await market_processor.close()

        logger.info("✅ End-to-end integration tests passed")

    @pytest.mark.asyncio
    async def test_performance_requirements(self, mock_config, mock_live_data_client):
        """Test that performance requirements are met."""
        logger.info("Testing performance requirements...")

        with patch('run_smc_enhanced.LiveDataClient', return_value=mock_live_data_client):
            # Initialize components
            market_processor = RealMarketDataProcessor()
            smc_detector = EnhancedSMCDetector()
            decision_engine = EnhancedDecisionEngine(mock_config)

            try:
                # Test data retrieval latency (<100ms target)
                start_time = time.time()
                market_data = await market_processor.get_latest_ohlcv_data("BTC/USDT", "1h")
                data_latency = (time.time() - start_time) * 1000

                assert data_latency < 200, f"Data retrieval should be fast ({data_latency:.1f}ms)"
                logger.info(f"✅ Data retrieval latency: {data_latency:.1f}ms")

                # Test SMC analysis latency (<50ms target)
                start_time = time.time()
                smc_patterns = await smc_detector.detect_all_patterns(market_data)
                smc_latency = (time.time() - start_time) * 1000

                assert smc_latency < 100, f"SMC analysis should be fast ({smc_latency:.1f}ms)"
                logger.info(f"✅ SMC analysis latency: {smc_latency:.1f}ms")

                # Test decision engine latency (<100ms target)
                start_time = time.time()
                signal = await decision_engine.make_decision(market_data, smc_patterns)
                decision_latency = (time.time() - start_time) * 1000

                assert decision_latency < 200, f"Decision engine should be fast ({decision_latency:.1f}ms)"
                logger.info(f"✅ Decision engine latency: {decision_latency:.1f}ms")

                # Total processing time
                total_latency = data_latency + smc_latency + decision_latency
                assert total_latency < 300, f"Total processing should be under 300ms ({total_latency:.1f}ms)"
                logger.info(f"✅ Total processing latency: {total_latency:.1f}ms")

                # Test memory usage
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024

                assert memory_mb < 500, f"Memory usage should be reasonable ({memory_mb:.1f}MB)"
                logger.info(f"✅ Memory usage: {memory_mb:.1f}MB")

            finally:
                await market_processor.close()

        logger.info("✅ Performance requirement tests passed")

    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, mock_config):
        """Test error handling and fallback mechanisms."""
        logger.info("Testing error handling and fallbacks...")

        # Test with failing live data client
        failing_client = AsyncMock()
        failing_client.get_latest_ohlcv_data.side_effect = Exception("API Error")

        with patch('run_smc_enhanced.LiveDataClient', return_value=failing_client):
            market_processor = RealMarketDataProcessor()

            try:
                # Should fallback to mock data
                data = await market_processor.get_latest_ohlcv_data("BTC/USDT", "1h")

                assert data is not None, "Should provide fallback data on error"
                assert not data.empty, "Fallback data should not be empty"

                logger.info("✅ Fallback data generation works correctly")

            finally:
                await market_processor.close()

        # Test decision engine with empty patterns
        empty_patterns = {
            'order_blocks': [],
            'coch_patterns': [],
            'bos_patterns': [],
            'liquidity_sweeps': [],
            'total_patterns': 0
        }

        empty_data = pd.DataFrame()  # Empty market data

        decision_engine = EnhancedDecisionEngine(mock_config)
        signal = await decision_engine.make_decision(empty_data, empty_patterns)

        assert signal is None, "Should not generate signal with empty data/patterns"
        logger.info("✅ Decision engine handles empty data correctly")

        logger.info("✅ Error handling and fallback tests passed")

    def test_dashboard_integration(self):
        """Test dashboard integration with real data components."""
        logger.info("Testing dashboard integration...")

        # Initialize dashboard
        dashboard = initialize_dashboard_manager()

        assert dashboard is not None, "Dashboard manager should initialize"

        # Test alert sending
        import asyncio
        from monitoring.real_time_dashboard import send_trading_alert

        async def test_alert():
            await send_trading_alert(
                severity="INFO",
                title="Test Alert",
                message="Integration test alert",
                component="test"
            )

        asyncio.run(test_alert())

        # Test signal sending
        from monitoring.real_time_dashboard import send_trading_signal

        async def test_signal():
            await send_trading_signal(
                symbol="BTC/USDT",
                strategy="SMC",
                signal_type="BUY",
                confidence=0.8,
                entry_price=50000,
                smc_patterns=["order_block", "bullish_coch"]
            )

        asyncio.run(test_signal())

        logger.info("✅ Dashboard integration tests passed")


# Performance benchmark test
@pytest.mark.asyncio
async def benchmark_performance():
    """Benchmark the performance of the integrated system."""
    logger.info("Running performance benchmark...")

    # Mock configuration
    config = {
        "decision_engine": {"confidence_threshold": 0.6},
        "risk_manager": {"stop_loss_percent": 2.0, "take_profit_ratio": 2.5},
        "ml_models": {"path": "tests/models/"}
    }

    # Generate test data
    dates = pd.date_range(end=datetime.now(), periods=500, freq='1T')
    base_price = 50000
    import numpy as np

    returns = np.random.normal(0, 0.001, 500)
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    test_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.0005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.0005))) for p in prices],
        'close': np.roll(prices, -1),
        'volume': np.random.uniform(1000, 3000, 500)
    }).set_index('timestamp')

    # Initialize components
    smc_detector = EnhancedSMCDetector()
    decision_engine = EnhancedDecisionEngine(config)

    # Run benchmark
    iterations = 10
    times = []

    for i in range(iterations):
        start_time = time.time()

        # SMC analysis
        patterns = await smc_detector.detect_all_patterns(test_data)

        # Decision making
        signal = await decision_engine.make_decision(test_data, patterns)

        total_time = (time.time() - start_time) * 1000
        times.append(total_time)

    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    logger.info(f"📊 Benchmark Results ({iterations} iterations):")
    logger.info(f"   • Average time: {avg_time:.1f}ms")
    logger.info(f"   • P95 time: {p95_time:.1f}ms")
    logger.info(f"   • Min time: {min(times):.1f}ms")
    logger.info(f"   • Max time: {max(times):.1f}ms")

    # Performance assertions
    assert avg_time < 200, f"Average processing should be under 200ms (actual: {avg_time:.1f}ms)"
    assert p95_time < 300, f"P95 processing should be under 300ms (actual: {p95_time:.1f}ms)"

    logger.info("✅ Performance benchmark passed")


if __name__ == "__main__":
    # Run a quick integration test
    async def quick_test():
        test = TestRealDataIntegration()

        # Generate test data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5T')
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': [50000] * 100,
            'high': [50200] * 100,
            'low': [49800] * 100,
            'close': [50100] * 100,
            'volume': [1000] * 100
        }).set_index('timestamp')

        print("🧪 Running Quick Integration Test...")

        # Test SMC detector
        detector = EnhancedSMCDetector()
        patterns = await detector.detect_all_patterns(test_data)
        print(f"✅ SMC Detector: Found {patterns['total_patterns']} patterns")

        # Test decision engine
        mock_config = {"decision_engine": {"confidence_threshold": 0.5}}
        engine = EnhancedDecisionEngine(mock_config)
        signal = await engine.make_decision(test_data, patterns)
        print(f"✅ Decision Engine: {'Signal generated' if signal else 'No signal'}")

        # Test risk manager
        risk_manager = IntegratedRiskManager(mock_config)
        stop_loss = risk_manager.calculate_stop_loss(50000, "BUY", [], {})
        take_profit = risk_manager.calculate_take_profit(50000, stop_loss, "BUY")
        print(f"✅ Risk Manager: SL={stop_loss:.0f}, TP={take_profit:.0f}")

        # Test trading engine
        trading_engine = TradingEngine(mock_config)
        if signal:
            trading_engine.execute_trade({
                **signal,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            })
            print(f"✅ Trading Engine: Trade executed")

        print("🎉 Quick Integration Test Complete!")

    asyncio.run(quick_test())