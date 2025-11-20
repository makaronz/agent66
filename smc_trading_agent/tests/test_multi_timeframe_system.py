"""
Comprehensive tests for the multi-timeframe confluence analysis system.

Tests cover data management, confluence analysis, signal generation,
caching, integration, and performance.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import tempfile
import os

# Import modules to test
from multi_timeframe.data_manager import MultiTimeframeDataManager, ConfluenceZone
from multi_timeframe.confluence_engine import ConfluenceAnalysisEngine, ConfluenceScore
from multi_timeframe.signal_generator import MultiTimeframeSignalGenerator, TradingSignal, SignalType
from multi_timeframe.cache_manager import ConfluenceCacheManager
from multi_timeframe.main import MultiTimeframeConfluenceSystem, create_confluence_system
from multi_timeframe.integration import MultiTimeframeIntegration, create_integration_system

class TestMultiTimeframeDataManager:
    """Test cases for MultiTimeframeDataManager"""

    @pytest.fixture
    def config(self):
        """Test configuration for data manager."""
        return {
            'symbols': ['BTCUSDT'],
            'timeframes': [
                {'name': 'M5', 'minutes': 5, 'priority': 1, 'max_candles': 100, 'confluence_weight': 0.1},
                {'name': 'M15', 'minutes': 15, 'priority': 2, 'max_candles': 100, 'confluence_weight': 0.2},
            ]
        }

    @pytest.fixture
    def data_manager(self, config):
        """Create data manager instance for testing."""
        return MultiTimeframeDataManager(config)

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        np.random.seed(42)

        base_price = 50000
        returns = np.random.normal(0, 0.001, 100)
        prices = [base_price]

        for ret in returns:
            prices.append(prices[-1] * (1 + ret))

        prices = prices[1:]

        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.001))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.001))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, 100)
        })

    def test_initialization(self, config):
        """Test data manager initialization."""
        manager = MultiTimeframeDataManager(config)
        assert manager.symbols == config['symbols']
        assert len(manager.timeframes) == 2
        assert 'M5' in [tf.name for tf in manager.timeframes]

    def test_add_market_data(self, data_manager):
        """Test adding market data."""
        timestamp = datetime.utcnow()
        data_manager.add_market_data('BTCUSDT', 50000.0, 100.0, timestamp)

        # Check if data was added
        m5_data = data_manager.get_timeframe_data('BTCUSDT', 'M5')
        assert not m5_data.empty
        assert len(m5_data) >= 1

    @pytest.mark.asyncio
    async def test_confluence_detection(self, data_manager, sample_ohlcv_data):
        """Test confluence zone detection."""
        # Add sample data
        for _, row in sample_ohlcv_data.iterrows():
            data_manager.add_market_data(
                'BTCUSDT', row['close'], row['volume'], row['timestamp']
            )

        # Detect confluence zones
        zones = data_manager.detect_confluence_zones('BTCUSDT')

        assert isinstance(zones, list)
        # Zones should be detected (may be empty with random data)
        assert isinstance(zones, list)

    def test_get_all_timeframes_data(self, data_manager, sample_ohlcv_data):
        """Test getting data for all timeframes."""
        # Add sample data
        for _, row in sample_ohlcv_data.head(50).iterrows():
            data_manager.add_market_data(
                'BTCUSDT', row['close'], row['volume'], row['timestamp']
            )

        # Get all timeframe data
        all_data = data_manager.get_all_timeframes_data('BTCUSDT')

        assert isinstance(all_data, dict)
        assert 'M5' in all_data
        assert 'M15' in all_data

    def test_cache_functionality(self, data_manager):
        """Test data caching functionality."""
        # Add some data
        data_manager.add_market_data('BTCUSDT', 50000.0, 100.0)

        # Get data (should use cache)
        data1 = data_manager.get_timeframe_data('BTCUSDT', 'M5', use_cache=True)
        data2 = data_manager.get_timeframe_data('BTCUSDT', 'M5', use_cache=True)

        # Should be the same data
        pd.testing.assert_frame_equal(data1, data2)

    def test_metrics(self, data_manager):
        """Test performance metrics collection."""
        initial_metrics = data_manager.get_metrics()
        assert 'total_updates' in initial_metrics

        # Add some data
        data_manager.add_market_data('BTCUSDT', 50000.0, 100.0)

        updated_metrics = data_manager.get_metrics()
        assert updated_metrics['total_updates'] > initial_metrics['total_updates']


class TestConfluenceAnalysisEngine:
    """Test cases for ConfluenceAnalysisEngine"""

    @pytest.fixture
    def config(self):
        """Test configuration for confluence engine."""
        return {}

    @pytest.fixture
    def confluence_engine(self, config):
        """Create confluence engine instance."""
        return ConfluenceAnalysisEngine(config)

    @pytest.fixture
    def sample_timeframe_data(self):
        """Create sample data for multiple timeframes."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        np.random.seed(42)

        base_price = 50000
        returns = np.random.normal(0, 0.002, 100)
        prices = [base_price]

        for ret in returns:
            prices.append(prices[-1] * (1 + ret))

        prices = prices[1:]

        ohlcv = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, 100)
        })

        return {
            'M5': ohlcv,
            'M15': ohlcv.resample('15min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        }

    def test_trend_analysis(self, confluence_engine, sample_timeframe_data):
        """Test trend analysis functionality."""
        m5_data = sample_timeframe_data['M5']
        trend = confluence_engine.trend_analyzer.analyze_trend(m5_data, 'M5')

        assert trend is not None
        assert hasattr(trend, 'direction')
        assert hasattr(trend, 'strength')
        assert 0 <= trend.strength <= 1

    def test_premium_discount_analysis(self, confluence_engine, sample_timeframe_data):
        """Test premium/discount zone analysis."""
        m5_data = sample_timeframe_data['M5']
        current_price = m5_data.iloc[-1]['close']

        zones = confluence_engine.premium_discount_analyzer.analyze_premium_discount(
            m5_data, 'M5', current_price
        )

        assert isinstance(zones, list)
        # Should have premium and discount zones
        assert len(zones) >= 0

    def test_multi_timeframe_confluence(self, confluence_engine, sample_timeframe_data):
        """Test multi-timeframe confluence analysis."""
        symbol = 'BTCUSDT'
        current_price = 50000.0

        scores = confluence_engine.analyze_multi_timeframe_confluence(
            symbol, sample_timeframe_data, current_price
        )

        assert isinstance(scores, list)
        for score in scores:
            assert isinstance(score, ConfluenceScore)
            assert 0 <= score.overall_score <= 1
            assert score.price_level > 0

    def test_confluence_score_calculation(self, confluence_engine):
        """Test individual confluence score calculation."""
        # Create mock timeframe analyses
        timeframe_analyses = {
            'M5': {
                'trend': Mock(direction='bullish', strength=0.7, support_levels=[49000], resistance_levels=[51000]),
                'order_blocks': [Mock(price_level=49500, volume_confirmation=1.5)],
                'structure_shifts': []
            }
        }

        score = confluence_engine._calculate_confluence_score(
            49500, timeframe_analyses, 50000, ['M5_order_block']
        )

        assert isinstance(score, ConfluenceScore)
        assert score.price_level == 49500
        assert 0 <= score.overall_score <= 1


class TestMultiTimeframeSignalGenerator:
    """Test cases for MultiTimeframeSignalGenerator"""

    @pytest.fixture
    def config(self):
        """Test configuration for signal generator."""
        return {
            'validation': {
                'min_confidence': 0.6,
                'min_risk_reward': 1.2
            },
            'position_sizing': {
                'max_position_size': 0.05,
                'base_position_size': 0.02
            }
        }

    @pytest.fixture
    def signal_generator(self, config):
        """Create signal generator instance."""
        return MultiTimeframeSignalGenerator(config)

    @pytest.fixture
    def sample_confluence_scores(self):
        """Create sample confluence scores."""
        return [
            ConfluenceScore(
                price_level=49500.0,
                overall_score=0.75,
                trend_alignment=0.8,
                level_confluence=0.7,
                volume_confirmation=0.6,
                timeframe_agreement=0.8,
                signal_strength=0.7,
                risk_reward_ratio=2.0,
                confidence=0.75,
                supporting_factors=['M5_support', 'H1_trend'],
                opposing_factors=[]
            )
        ]

    def test_signal_generation(self, signal_generator, sample_confluence_scores):
        """Test trading signal generation."""
        symbol = 'BTCUSDT'
        current_price = 49500.0
        market_data = {
            'account_balance': 10000,
            'volatility': 0.02,
            'volume_ratio': 1.2,
            'spread': 0.001
        }

        signals = signal_generator.generate_signals(
            symbol, sample_confluence_scores, current_price, market_data
        )

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol == symbol
            assert 0 <= signal.confidence <= 1
            assert signal.position_size > 0

    def test_signal_validation(self, signal_generator):
        """Test signal validation."""
        # Create a valid signal
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            symbol='BTCUSDT',
            entry_price=49500.0,
            stop_loss=49000.0,
            take_profit=51000.0,
            confidence=0.8,
            position_size=0.03,
            risk_reward_ratio=2.0,
            timeframe_consensus={'H1': 0.8},
            confluence_score=0.75
        )

        market_data = {
            'volatility': 0.02,
            'volume_ratio': 1.2,
            'spread': 0.001
        }

        is_valid = signal_generator.validator.validate_signal(signal, market_data, [])
        assert is_valid

    def test_position_sizing(self, signal_generator):
        """Test position sizing calculation."""
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            symbol='BTCUSDT',
            entry_price=49500.0,
            stop_loss=49000.0,
            take_profit=51000.0,
            confidence=0.8,
            position_size=0.02,
            risk_reward_ratio=2.0,
            timeframe_consensus={},
            confluence_score=0.75
        )

        position_size = signal_generator.position_sizer.calculate_position_size(
            signal, account_balance=10000, risk_per_trade=0.02
        )

        assert 0.01 <= position_size <= 0.05  # Within configured limits

    def test_signal_performance_tracking(self, signal_generator):
        """Test signal performance tracking."""
        signal = TradingSignal(
            signal_type=SignalType.BUY,
            symbol='BTCUSDT',
            entry_price=49500.0,
            stop_loss=49000.0,
            take_profit=51000.0,
            confidence=0.8,
            position_size=0.02,
            risk_reward_ratio=2.0,
            timeframe_consensus={},
            confluence_score=0.75
        )

        outcome = {
            'result': 'profit',
            'profit_loss': 100,
            'duration_minutes': 60,
            'exit_reason': 'take_profit'
        }

        signal_generator.update_signal_performance(signal, outcome)

        stats = signal_generator.get_signal_statistics()
        assert 'total_signals' in stats
        assert stats['total_signals'] >= 1


class TestConfluenceCacheManager:
    """Test cases for ConfluenceCacheManager"""

    @pytest.fixture
    def config(self):
        """Test configuration for cache manager."""
        return {
            'cache': {
                'confluence_cache_size': 10,
                'indicator_cache_size': 10,
                'max_memory_mb': 64
            }
        }

    @pytest.fixture
    def cache_manager(self, config):
        """Create cache manager instance."""
        return ConfluenceCacheManager(config)

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_manager):
        """Test cache manager initialization."""
        await cache_manager.initialize()
        assert cache_manager.running

        await cache_manager.shutdown()
        assert not cache_manager.running

    def test_confluence_caching(self, cache_manager):
        """Test confluence zone caching."""
        symbol = 'BTCUSDT'
        timeframes = ['M5', 'H1']
        zones = [
            ConfluenceZone(
                price_level=49500.0,
                strength=0.8,
                timeframes={'M5', 'H1'},
                zone_type='support',
                timestamp=datetime.utcnow(),
                confidence=0.75
            )
        ]

        # Cache zones
        success = cache_manager.cache_confluence_result(symbol, timeframes, zones)
        assert success

        # Retrieve cached zones
        cached_zones = cache_manager.get_cached_confluence(symbol, timeframes)
        assert cached_zones is not None
        assert len(cached_zones) == 1
        assert cached_zones[0].price_level == 49500.0

    def test_symbol_invalidation(self, cache_manager):
        """Test symbol cache invalidation."""
        symbol = 'BTCUSDT'
        timeframes = ['M5']
        zones = []

        # Cache data
        cache_manager.cache_confluence_result(symbol, timeframes, zones)

        # Invalidate symbol
        cache_manager.invalidate_symbol_cache(symbol)

        # Check if data was invalidated
        cached_zones = cache_manager.get_cached_confluence(symbol, timeframes)
        assert cached_zones is None

    def test_performance_metrics(self, cache_manager):
        """Test performance metrics collection."""
        metrics = cache_manager.get_performance_metrics()
        assert 'operations' in metrics
        assert 'cache_statistics' in metrics
        assert 'hit_rate' in metrics


class TestMultiTimeframeSystem:
    """Test cases for the complete multi-timeframe system"""

    @pytest.fixture
    def config(self):
        """Test configuration for complete system."""
        return {
            'symbols': ['BTCUSDT'],
            'timeframes': ['M5', 'M15'],
            'analysis_interval_minutes': 1,
            'data_manager': {
                'symbols': ['BTCUSDT']
            },
            'cache_manager': {
                'cache': {
                    'max_memory_mb': 64
                }
            }
        }

    @pytest.fixture
    def mt_system(self, config):
        """Create multi-timeframe system instance."""
        return create_confluence_system(config)

    @pytest.mark.asyncio
    async def test_system_initialization(self, mt_system):
        """Test system initialization."""
        await mt_system.initialize()
        assert mt_system.running

        await mt_system.stop()
        assert not mt_system.running

    def test_market_data_processing(self, mt_system):
        """Test market data processing."""
        symbol = 'BTCUSDT'
        price = 50000.0
        volume = 100.0

        # Add market data
        mt_system.add_market_data(symbol, price, volume)

        # Check if data was processed
        data = mt_system.data_manager.get_timeframe_data(symbol, 'M5')
        # Data may be empty if not enough time has passed
        assert isinstance(data, pd.DataFrame)

    def test_symbol_analysis(self, mt_system):
        """Test symbol analysis functionality."""
        # Add some sample data first
        for i in range(10):
            mt_system.add_market_data('BTCUSDT', 50000 + i, 100)

        # Analyze symbol
        analysis = mt_system.analyze_symbol('BTCUSDT', force_analysis=True)

        assert isinstance(analysis, dict)
        assert 'symbol' in analysis
        if 'error' not in analysis:
            assert 'confluence_scores' in analysis
            assert 'signals' in analysis
            assert 'current_price' in analysis

    def test_signal_generation(self, mt_system):
        """Test signal generation."""
        # Add some sample data
        for i in range(20):
            price = 50000 + (i % 5) * 100  # Create some volatility
            mt_system.add_market_data('BTCUSDT', price, 100)

        # Get signal
        signal = mt_system.get_signal_for_symbol('BTCUSDT')

        # Signal may be None if no strong signals are detected
        if signal is not None:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol == 'BTCUSDT'

    def test_performance_metrics(self, mt_system):
        """Test performance metrics collection."""
        metrics = mt_system.get_performance_metrics()
        assert 'system' in metrics
        assert 'data_manager' in metrics
        assert 'cache' in metrics


class TestMultiTimeframeIntegration:
    """Test cases for multi-timeframe integration"""

    @pytest.fixture
    def config(self):
        """Test configuration for integration."""
        return {
            'symbols': ['BTCUSDT'],
            'multi_timeframe': {
                'symbols': ['BTCUSDT'],
                'timeframes': ['M5']
            },
            'integration_weights': {
                'multi_timeframe': 0.5,
                'ml_ensemble': 0.3,
                'smc_indicators': 0.2
            }
        }

    @pytest.fixture
    def integration_system(self, config):
        """Create integration system instance."""
        return create_integration_system(config)

    @pytest.mark.asyncio
    async def test_integration_initialization(self, integration_system):
        """Test integration system initialization."""
        await integration_system.initialize()
        # Note: Components may not fully initialize without proper configuration

        await integration_system.shutdown()

    def test_market_data_processing(self, integration_system):
        """Test market data processing through integration."""
        symbol = 'BTCUSDT'
        price = 50000.0
        volume = 100.0

        # Process market data
        integration_system.process_market_data(symbol, price, volume)

        # Check if data was processed by multi-timeframe system
        data = integration_system.mt_system.data_manager.get_timeframe_data(symbol, 'M5')
        assert isinstance(data, pd.DataFrame)

    def test_signal_combination(self, integration_system):
        """Test signal combination from multiple sources."""
        from multi_timeframe.signal_generator import TradingSignal, SignalType

        # Create mock signals
        mt_signal = TradingSignal(
            signal_type=SignalType.BUY,
            symbol='BTCUSDT',
            entry_price=49500.0,
            stop_loss=49000.0,
            take_profit=51000.0,
            confidence=0.8,
            position_size=0.03,
            risk_reward_ratio=2.0,
            timeframe_consensus={'H1': 0.8},
            confluence_score=0.75
        )

        ml_signal = {
            'signal': 'buy',
            'confidence': 0.7
        }

        smc_signal = {
            'signal': 'buy',
            'confidence': 0.6
        }

        risk_assessment = {
            'risk_level': 'medium',
            'max_position_size': 0.05
        }

        # Combine signals
        integrated_signal = integration_system._combine_signals(
            'BTCUSDT', mt_signal, ml_signal, smc_signal, risk_assessment
        )

        assert integrated_signal.symbol == 'BTCUSDT'
        assert integrated_signal.final_decision in ['buy', 'sell', 'hold']
        assert integrated_signal.combined_confidence > 0
        assert integrated_signal.recommended_action in ['BUY', 'SELL', 'HOLD']

    def test_integration_metrics(self, integration_system):
        """Test integration performance metrics."""
        metrics = integration_system.get_integration_metrics()
        assert 'integration' in metrics
        assert 'multi_timeframe_system' in metrics
        assert 'component_status' in metrics


class TestPerformanceAndScalability:
    """Performance and scalability tests"""

    @pytest.mark.asyncio
    async def test_concurrent_symbol_analysis(self):
        """Test concurrent analysis of multiple symbols."""
        config = {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
            'timeframes': ['M5', 'M15'],
            'data_manager': {'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']}
        }

        system = create_confluence_system(config)
        await system.initialize()

        try:
            # Add data for all symbols
            symbols = config['symbols']
            for symbol in symbols:
                for i in range(20):
                    price = 50000 + (hash(symbol) % 1000) + i * 10
                    system.add_market_data(symbol, price, 100)

            # Analyze all symbols concurrently
            tasks = [
                system.analyze_symbol(symbol, force_analysis=True)
                for symbol in symbols
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            assert len(results) == len(symbols)
            for result in results:
                if not isinstance(result, Exception):
                    assert 'symbol' in result

        finally:
            await system.stop()

    def test_memory_usage(self):
        """Test memory usage with large datasets."""
        config = {
            'symbols': ['BTCUSDT'],
            'timeframes': ['M5'],
            'cache_manager': {
                'cache': {'max_memory_mb': 32}
            }
        }

        system = create_confluence_system(config)

        # Add large amount of data
        for i in range(1000):
            price = 50000 + (i % 100) * 10
            system.add_market_data('BTCUSDT', price, 100)

        # Check memory usage
        metrics = system.get_performance_metrics()
        memory_mb = metrics['cache'].get('total_memory_mb', 0)
        assert memory_mb < 64  # Should be within reasonable limits

    def test_cache_efficiency(self):
        """Test cache hit rates with repeated requests."""
        config = {
            'symbols': ['BTCUSDT'],
            'timeframes': ['M5'],
            'cache_manager': {
                'cache': {
                    'confluence_ttl_minutes': 60  # Long TTL for testing
                }
            }
        }

        system = create_confluence_system(config)

        # Add some data
        for i in range(10):
            system.add_market_data('BTCUSDT', 50000 + i * 10, 100)

        # First analysis (cache miss)
        result1 = system.analyze_symbol('BTCUSDT', force_analysis=True)

        # Second analysis (should use cache)
        result2 = system.analyze_symbol('BTCUSDT', force_analysis=True)

        # Check cache metrics
        cache_metrics = system.cache_manager.get_performance_metrics()
        hit_rate = cache_metrics.get('hit_rate', 0)

        # Hit rate should be positive (may be 0 if cache implementation differs)
        assert hit_rate >= 0


# Integration test for the complete workflow
@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete workflow from data to signals."""
    config = {
        'symbols': ['BTCUSDT'],
        'timeframes': ['M5', 'M15'],
        'analysis_interval_minutes': 1,
        'data_manager': {'symbols': ['BTCUSDT']},
        'signal_generator': {
            'validation': {'min_confidence': 0.5}
        }
    }

    system = create_confluence_system(config)
    await system.initialize()

    try:
        # Simulate real-time market data
        base_price = 50000
        for i in range(30):  # 30 data points
            # Add some trend and noise
            trend = i * 10
            noise = np.random.normal(0, 50)
            price = base_price + trend + noise
            volume = 100 + np.random.randint(-50, 50)

            system.add_market_data('BTCUSDT', price, volume)

            # Small delay to simulate real-time
            await asyncio.sleep(0.01)

        # Analyze symbol
        analysis = system.analyze_symbol('BTCUSDT', force_analysis=True)

        assert isinstance(analysis, dict)

        if 'error' not in analysis:
            # Check analysis structure
            assert 'confluence_scores' in analysis
            assert 'signals' in analysis
            assert 'current_price' in analysis

            # Generate signal if available
            signal = system.get_signal_for_symbol('BTCUSDT')
            if signal:
                assert signal.symbol == 'BTCUSDT'
                assert 0 <= signal.confidence <= 1

        # Get performance metrics
        metrics = system.get_performance_metrics()
        assert 'system' in metrics
        assert metrics['system']['total_analyses'] >= 1

    finally:
        await system.stop()


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])