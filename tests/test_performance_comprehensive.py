"""
Comprehensive Performance and Load Testing for SMC Trading Agent

This module contains performance tests, load tests, and stress tests to ensure
the system meets performance requirements under various conditions.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import time
import psutil
import threading
import concurrent.futures
from typing import Dict, List, Any
import json
import logging

# Import the test framework
from test_framework import (
    AsyncTestCase, TestConfig, MarketDataSimulator,
    PerformanceTracker, TestDataManager
)

# Import system components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSystemPerformance(AsyncTestCase):
    """Test system performance under various conditions."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.performance_tracker = PerformanceTracker()
        self.market_simulator = MarketDataSimulator()

    async def test_data_pipeline_throughput(self):
        """Test data pipeline throughput with large datasets."""
        from data_pipeline.ingestion import MarketDataIngestion

        # Create ingestion instance
        ingestion = MarketDataIngestion(self.config)

        # Test with different data sizes
        test_sizes = [1000, 5000, 10000, 50000]
        throughput_results = {}

        for size in test_sizes:
            # Generate test data
            test_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', size)

            # Measure throughput
            start_time = time.time()
            result = await ingestion.ingest_ohlcv_data('BTCUSDT', test_data)
            end_time = time.time()

            duration = end_time - start_time
            throughput = size / duration  # records per second

            throughput_results[size] = {
                'duration': duration,
                'throughput': throughput,
                'memory_usage': self._get_memory_usage()
            }

            # Performance assertions
            assert result['status'] == 'success'
            assert duration < 10.0  # Should complete within 10 seconds
            assert throughput > 100  # Minimum 100 records/second

        # Analyze throughput scalability
        throughputs = [result['throughput'] for result in throughput_results.values()]
        assert throughputs[0] / throughputs[-1] < 5  # Performance shouldn't degrade more than 5x

    async def test_smc_detector_latency(self):
        """Test SMC pattern detection latency."""
        from smc_detector.patterns import OrderBlockDetector

        detector = OrderBlockDetector(self.config)

        # Test with different data complexities
        test_scenarios = [
            {'size': 100, 'volatility': 0.02, 'name': 'Low Volatility'},
            {'size': 500, 'volatility': 0.03, 'name': 'Medium Volatility'},
            {'size': 1000, 'volatility': 0.05, 'name': 'High Volatility'},
            {'size': 2000, 'volatility': 0.08, 'name': 'Extreme Volatility'}
        ]

        latency_results = {}

        for scenario in test_scenarios:
            # Generate test data with specified characteristics
            test_data = self._generate_data_with_characteristics(
                scenario['size'], scenario['volatility']
            )

            # Measure detection latency
            latencies = []
            for _ in range(10):  # Run multiple times for statistical significance
                start_time = time.time()
                order_blocks = await detector.detect_order_blocks(test_data)
                end_time = time.time()

                latencies.append(end_time - start_time)

            avg_latency = np.mean(latencies)
            max_latency = np.max(latencies)
            p95_latency = np.percentile(latencies, 95)

            latency_results[scenario['name']] = {
                'avg_latency': avg_latency,
                'max_latency': max_latency,
                'p95_latency': p95_latency,
                'patterns_found': len(order_blocks)
            }

            # Latency assertions
            assert avg_latency < 1.0  # Average latency < 1 second
            assert max_latency < 2.0  # Maximum latency < 2 seconds
            assert p95_latency < 1.5   # 95th percentile < 1.5 seconds

        # Validate latency consistency
        avg_latencies = [result['avg_latency'] for result in latency_results.values()]
        assert np.std(avg_latencies) / np.mean(avg_latencies) < 0.5  # Coefficient of variation < 50%

    async def test_decision_engine_response_time(self):
        """Test decision engine response time under various conditions."""
        from decision_engine.models import ModelEnsemble

        ensemble = ModelEnsemble(self.config)

        # Test with different feature complexities
        complexity_levels = [
            {'features': 10, 'samples': 100, 'name': 'Simple'},
            {'features': 50, 'samples': 500, 'name': 'Moderate'},
            {'features': 100, 'samples': 1000, 'name': 'Complex'},
            {'features': 200, 'samples': 2000, 'name': 'Very Complex'}
        ]

        response_times = {}

        for level in complexity_levels:
            # Generate test features
            test_features = self._generate_test_features(
                level['samples'], level['features']
            )

            # Measure response time
            times = []
            for _ in range(5):  # Multiple runs for consistency
                start_time = time.time()
                predictions = await ensemble.get_predictions(test_features)
                end_time = time.time()

                times.append(end_time - start_time)

            response_times[level['name']] = {
                'avg_time': np.mean(times),
                'max_time': np.max(times),
                'min_time': np.min(times),
                'std_time': np.std(times)
            }

            # Response time assertions
            assert response_times[level['name']]['avg_time'] < 2.0  # Average < 2 seconds
            assert response_times[level['name']]['max_time'] < 5.0  # Maximum < 5 seconds

        # Check scalability
        simple_time = response_times['Simple']['avg_time']
        complex_time = response_times['Very Complex']['avg_time']
        assert complex_time / simple_time < 10  # Complex tasks shouldn't take more than 10x longer

    async def test_risk_manager_performance(self):
        """Test risk manager calculation performance."""
        from risk_manager.var_calculator import VaRCalculator
        from risk_manager.position_sizer import PositionSizer

        var_calculator = VaRCalculator(self.config)
        position_sizer = PositionSizer(self.config)

        # Test VaR calculation performance
        portfolio_sizes = [100, 500, 1000, 2000]  # Number of assets/positions

        for size in portfolio_sizes:
            # Generate test portfolio
            returns = np.random.normal(0, 0.02, (252, size))  # 1 year of daily returns

            # Measure VaR calculation time
            start_time = time.time()
            var_95 = await var_calculator.calculate_var(returns, confidence_level=0.95)
            var_99 = await var_calculator.calculate_var(returns, confidence_level=0.99)
            end_time = time.time()

            calculation_time = end_time - start_time

            # Performance assertions
            assert calculation_time < 1.0  # Should complete within 1 second
            assert var_95 is not None
            assert var_99 is not None

        # Test position sizing performance
        sizing_scenarios = [
            {'positions': 10, 'complexity': 'simple'},
            {'positions': 50, 'complexity': 'moderate'},
            {'positions': 100, 'complexity': 'complex'}
        ]

        for scenario in sizing_scenarios:
            start_time = time.time()

            for i in range(scenario['positions']):
                position_size = await position_sizer.calculate_position_size(
                    account_balance=100000,
                    risk_per_trade=0.02,
                    entry_price=50000 + i,
                    stop_loss=49500 + i
                )

            end_time = time.time()
            total_time = end_time - start_time
            avg_time_per_position = total_time / scenario['positions']

            # Performance assertions
            assert avg_time_per_position < 0.01  # <10ms per position
            assert total_time < scenario['positions'] * 0.05  # Total <50ms per position

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def _generate_data_with_characteristics(self, size: int, volatility: float) -> pd.DataFrame:
        """Generate market data with specific characteristics."""
        dates = pd.date_range(
            start=datetime.now() - timedelta(minutes=size),
            periods=size,
            freq='1min'
        )

        # Generate price series with specified volatility
        returns = np.random.normal(0, volatility, size)
        base_price = 50000
        prices = [base_price]

        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)

        data = []
        for i, (timestamp, close_price) in enumerate(zip(dates, prices[1:])):
            high_noise = np.random.uniform(0, 0.002)
            low_noise = np.random.uniform(-0.002, 0)

            data.append({
                'timestamp': timestamp,
                'open': prices[i],
                'high': close_price * (1 + high_noise),
                'low': close_price * (1 + low_noise),
                'close': close_price,
                'volume': np.random.uniform(100, 1000)
            })

        return pd.DataFrame(data)

    def _generate_test_features(self, n_samples: int, n_features: int) -> pd.DataFrame:
        """Generate test features for ML models."""
        feature_names = [f'feature_{i}' for i in range(n_features)]
        data = np.random.normal(0, 1, (n_samples, n_features))

        return pd.DataFrame(data, columns=feature_names)


class TestLoadTesting(AsyncTestCase):
    """Load testing to verify system performance under expected load."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.performance_tracker = PerformanceTracker()
        self.market_simulator = MarketDataSimulator()

    async def test_concurrent_market_data_processing(self):
        """Test concurrent processing of multiple market data streams."""
        from data_pipeline.ingestion import MarketDataIngestion
        from smc_detector.patterns import OrderBlockDetector

        ingestion = MarketDataIngestion(self.config)
        detector = OrderBlockDetector(self.config)

        # Simulate multiple concurrent data streams
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        concurrent_streams = 10  # Multiple streams per symbol

        async def process_data_stream(symbol: str, stream_id: int):
            """Process a single data stream."""
            # Generate unique data for this stream
            data = self.market_simulator.generate_ohlcv_data(symbol, 100)

            # Add stream identifier to ensure uniqueness
            data['stream_id'] = stream_id

            # Process through pipeline
            start_time = time.time()

            ingestion_result = await ingestion.ingest_ohlcv_data(f"{symbol}_stream_{stream_id}", data)
            patterns = await detector.detect_order_blocks(data)

            end_time = time.time()

            return {
                'symbol': symbol,
                'stream_id': stream_id,
                'duration': end_time - start_time,
                'records_processed': len(data),
                'patterns_found': len(patterns),
                'success': ingestion_result['status'] == 'success'
            }

        # Execute all streams concurrently
        start_time = time.time()
        tasks = []

        for symbol in symbols:
            for stream_id in range(concurrent_streams):
                task = process_data_stream(symbol, stream_id)
                tasks.append(task)

        # Wait for all streams to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception) and r['success']]
        failed_results = [r for r in results if isinstance(r, Exception) or not r['success']]

        # Load testing assertions
        assert len(successful_results) == len(symbols) * concurrent_streams
        assert len(failed_results) == 0

        # Performance assertions
        avg_stream_time = np.mean([r['duration'] for r in successful_results])
        max_stream_time = np.max([r['duration'] for r in successful_results])

        assert avg_stream_time < 5.0  # Average stream processing < 5 seconds
        assert max_stream_time < 10.0  # Maximum stream processing < 10 seconds
        assert total_time < avg_stream_time * 2  # Concurrent processing should be efficient

        # Throughput assertions
        total_records = sum(r['records_processed'] for r in successful_results)
        throughput = total_records / total_time  # records per second

        assert throughput > 1000  # Minimum throughput

    async def test_high_frequency_trading_decisions(self):
        """Test system performance under high-frequency trading scenarios."""
        from decision_engine.models import ModelEnsemble
        from risk_manager.smc_risk_manager import SMCRiskManager

        ensemble = ModelEnsemble(self.config)
        risk_manager = SMCRiskManager(self.config)

        # Simulate high-frequency decision making
        decision_frequency = 100  # Decisions per second
        test_duration = 10  # Seconds
        total_decisions = decision_frequency * test_duration

        decision_times = []
        successful_decisions = 0
        failed_decisions = 0

        async def make_trading_decision(decision_id: int):
            """Make a single trading decision."""
            try:
                # Generate test features
                features = pd.DataFrame({
                    'price_change': [np.random.normal(0, 0.02)],
                    'volume_change': [np.random.normal(0, 0.3)],
                    'rsi': [np.random.uniform(20, 80)],
                    'macd': [np.random.normal(0, 0.001)],
                    'confidence': [np.random.uniform(0.6, 0.9)]
                })

                start_time = time.time()

                # Get prediction from ensemble
                prediction = await ensemble.get_predictions(features)

                # Validate with risk manager
                trade = {
                    'action': prediction['ensemble']['action'],
                    'confidence': prediction['ensemble']['confidence'],
                    'position_size': 1.0,
                    'entry_price': 50000,
                    'stop_loss': 49500
                }

                risk_validation = await risk_manager.validate_trade_risk(trade)

                end_time = time.time()
                decision_time = end_time - start_time

                return {
                    'decision_id': decision_id,
                    'decision_time': decision_time,
                    'success': True,
                    'action': prediction['ensemble']['action'],
                    'risk_approved': risk_validation['is_valid']
                }

            except Exception as e:
                return {
                    'decision_id': decision_id,
                    'decision_time': 0,
                    'success': False,
                    'error': str(e),
                    'risk_approved': False
                }

        # Execute high-frequency decisions
        start_time = time.time()
        tasks = []

        for i in range(total_decisions):
            # Schedule decisions at the target frequency
            delay = i / decision_frequency
            task = asyncio.create_task(
                self._delayed_execute(make_trading_decision, i, delay)
            )
            tasks.append(task)

        # Wait for all decisions to complete
        results = await asyncio.gather(*tasks)
        actual_duration = time.time() - start_time

        # Analyze results
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        successful_decisions = len(successful_results)
        failed_decisions = len(failed_results)

        decision_times = [r['decision_time'] for r in successful_results]

        # High-frequency trading assertions
        assert successful_decisions / total_decisions > 0.95  # >95% success rate
        assert np.mean(decision_times) < 0.01  # Average decision time < 10ms
        assert np.percentile(decision_times, 95) < 0.02  # 95th percentile < 20ms

        # Frequency assertions
        actual_frequency = successful_decisions / actual_duration
        assert actual_frequency >= decision_frequency * 0.8  # Maintain at least 80% of target frequency

    async def _delayed_execute(self, func, *args, delay: float):
        """Execute a function after a specified delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        return await func(*args)

    async def test_memory_usage_under_load(self):
        """Test memory usage patterns under sustained load."""
        import gc
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()

        memory_samples = []
        cpu_samples = []

        # Generate sustained load
        load_duration = 30  # seconds
        sampling_interval = 1  # second

        async def generate_load():
            """Generate sustained system load."""
            from data_pipeline.ingestion import MarketDataIngestion
            from smc_detector.patterns import OrderBlockDetector
            from decision_engine.models import ModelEnsemble

            ingestion = MarketDataIngestion(self.config)
            detector = OrderBlockDetector(self.config)
            ensemble = ModelEnsemble(self.config)

            end_time = time.time() + load_duration

            while time.time() < end_time:
                # Generate and process data
                data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 50)

                # Process through components
                await ingestion.ingest_ohlcv_data('BTCUSDT', data)
                await detector.detect_order_blocks(data)

                # Generate features and get predictions
                features = pd.DataFrame(np.random.normal(0, 1, (10, 5)))
                await ensemble.get_predictions(features)

                await asyncio.sleep(0.1)  # Small delay to prevent 100% CPU usage

        # Start load generation and monitoring
        load_task = asyncio.create_task(generate_load())
        monitoring_task = asyncio.create_task(
            self._monitor_system_resources(memory_samples, cpu_samples, load_duration, sampling_interval)
        )

        # Wait for completion
        await load_task
        await monitoring_task

        # Analyze memory usage
        initial_memory = memory_samples[0]
        peak_memory = max(memory_samples)
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory

        # Analyze CPU usage
        avg_cpu = np.mean(cpu_samples)
        max_cpu = max(cpu_samples)

        # Memory assertions
        assert memory_growth < 200  # Memory growth should be < 200MB
        assert peak_memory - initial_memory < 300  # Peak usage should be < 300MB above initial

        # Check for memory leaks
        if len(memory_samples) > 10:
            recent_memory = memory_samples[-10:]
            memory_trend = np.polyfit(range(len(recent_memory)), recent_memory, 1)[0]
            assert memory_trend < 5  # Memory growth rate should be minimal

        # CPU assertions
        assert avg_cpu < 80  # Average CPU usage should be < 80%
        assert max_cpu < 95  # Peak CPU usage should be < 95%

        # Get tracemalloc statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 500 * 1024 * 1024  # Peak memory < 500MB (from tracemalloc)

    async def _monitor_system_resources(self, memory_samples: list, cpu_samples: list,
                                       duration: int, interval: float):
        """Monitor system resources during load testing."""
        process = psutil.Process()

        for _ in range(int(duration / interval)):
            # Sample memory usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)

            # Sample CPU usage
            cpu_percent = process.cpu_percent()
            cpu_samples.append(cpu_percent)

            await asyncio.sleep(interval)


class TestStressTesting(AsyncTestCase):
    """Stress testing to find system limits and breaking points."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.performance_tracker = PerformanceTracker()
        self.market_simulator = MarketDataSimulator()

    async def test_maximum_data_ingestion_rate(self):
        """Test maximum data ingestion rate before system degradation."""
        from data_pipeline.ingestion import MarketDataIngestion

        ingestion = MarketDataIngestion(self.config)

        # Test with progressively higher ingestion rates
        ingestion_rates = [100, 500, 1000, 2000, 5000]  # records per second
        max_sustainable_rate = 0

        for rate in ingestion_rates:
            # Generate test data
            test_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', rate)

            # Measure ingestion performance
            start_time = time.time()
            memory_before = self._get_memory_usage()
            cpu_before = self._get_cpu_usage()

            result = await ingestion.ingest_ohlcv_data('BTCUSDT', test_data)

            end_time = time.time()
            memory_after = self._get_memory_usage()
            cpu_after = self._get_cpu_usage()

            duration = end_time - start_time
            actual_rate = len(test_data) / duration
            memory_delta = memory_after - memory_before
            cpu_peak = max(cpu_before, cpu_after)

            # Check for system degradation
            if (duration > 10.0 or  # Taking too long
                memory_delta > 100 or  # Excessive memory usage
                cpu_peak > 90):  # Excessive CPU usage
                break

            max_sustainable_rate = rate
            assert result['status'] == 'success'
            assert actual_rate >= rate * 0.8  # Should achieve at least 80% of target rate

        # Validate minimum sustainable rate
        assert max_sustainable_rate >= 1000  # Should handle at least 1000 records/second

    async def test_concurrent_user_simulation(self):
        """Test system behavior with multiple concurrent users."""
        from decision_engine.models import ModelEnsemble
        from risk_manager.smc_risk_manager import SMCRiskManager

        ensemble = ModelEnsemble(self.config)
        risk_manager = SMCRiskManager(self.config)

        # Simulate multiple concurrent users
        user_counts = [10, 50, 100, 200, 500]
        max_concurrent_users = 0

        for user_count in user_counts:
            async def simulate_user(user_id: int):
                """Simulate a single user's trading activity."""
                try:
                    # User generates multiple trading requests
                    requests_per_user = 5
                    successful_requests = 0

                    for req_id in range(requests_per_user):
                        # Generate trading request
                        features = pd.DataFrame({
                            'price_change': [np.random.normal(0, 0.02)],
                            'volume_change': [np.random.normal(0, 0.3)],
                            'rsi': [np.random.uniform(20, 80)],
                            'user_id': [user_id],
                            'request_id': [req_id]
                        })

                        start_time = time.time()

                        # Get trading decision
                        prediction = await ensemble.get_predictions(features)

                        # Validate trade
                        trade = {
                            'user_id': user_id,
                            'action': prediction['ensemble']['action'],
                            'confidence': prediction['ensemble']['confidence'],
                            'position_size': 1.0,
                            'entry_price': 50000,
                            'stop_loss': 49500
                        }

                        risk_validation = await risk_manager.validate_trade_risk(trade)

                        end_time = time.time()

                        if risk_validation['is_valid']:
                            successful_requests += 1

                        # Rate limiting per user
                        await asyncio.sleep(0.1)

                    return {
                        'user_id': user_id,
                        'successful_requests': successful_requests,
                        'total_requests': requests_per_user,
                        'success_rate': successful_requests / requests_per_user
                    }

                except Exception as e:
                    return {
                        'user_id': user_id,
                        'successful_requests': 0,
                        'total_requests': 5,
                        'success_rate': 0,
                        'error': str(e)
                    }

            # Execute all users concurrently
            start_time = time.time()
            tasks = [simulate_user(user_id) for user_id in range(user_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            # Analyze results
            successful_users = [r for r in results if not isinstance(r, Exception)]
            failed_users = [r for r in results if isinstance(r, Exception)]

            if len(failed_users) > len(successful_users) * 0.1:  # More than 10% failures
                break

            avg_success_rate = np.mean([u['success_rate'] for u in successful_users])
            avg_response_time = total_time / user_count

            # Check for performance degradation
            if (avg_success_rate < 0.8 or  # Less than 80% success rate
                avg_response_time > 5.0 or  # Average response time > 5 seconds
                total_time > user_count * 2):  # Total time > 2s per user
                break

            max_concurrent_users = user_count
            assert len(successful_users) >= user_count * 0.9  # At least 90% of users successful
            assert avg_success_rate >= 0.8  # Average success rate >= 80%

        # Validate minimum concurrent user capacity
        assert max_concurrent_users >= 100  # Should handle at least 100 concurrent users

    async def test_extreme_market_volatility_handling(self):
        """Test system performance during extreme market volatility."""
        from data_pipeline.ingestion import MarketDataIngestion
        from smc_detector.patterns import OrderBlockDetector
        from decision_engine.models import ModelEnsemble

        ingestion = MarketDataIngestion(self.config)
        detector = OrderBlockDetector(self.config)
        ensemble = ModelEnsemble(self.config)

        # Simulate extreme market conditions
        volatility_scenarios = [
            {'volatility': 0.05, 'name': 'High Volatility'},
            {'volatility': 0.10, 'name': 'Very High Volatility'},
            {'volatility': 0.20, 'name': 'Extreme Volatility'},
            {'volatility': 0.30, 'name': 'Market Crash Scenario'}
        ]

        for scenario in volatility_scenarios:
            # Generate high volatility data
            volatile_data = self._generate_volatile_data(
                size=1000,
                volatility=scenario['volatility']
            )

            # Measure system performance under stress
            start_time = time.time()
            memory_before = self._get_memory_usage()

            # Process through pipeline
            ingestion_result = await ingestion.ingest_ohlcv_data('BTCUSDT', volatile_data)
            patterns = await detector.detect_order_blocks(volatile_data)

            # Generate features under stress
            features = self._extract_features_from_volatile_data(volatile_data)
            predictions = await ensemble.get_predictions(features)

            end_time = time.time()
            memory_after = self._get_memory_usage()

            processing_time = end_time - start_time
            memory_delta = memory_after - memory_before

            # Stress testing assertions
            assert ingestion_result['status'] == 'success'
            assert processing_time < 20.0  # Should complete within 20 seconds even under stress
            assert memory_delta < 500  # Memory usage should remain reasonable

            # System should remain functional
            assert len(patterns) >= 0  # Pattern detection should not crash
            assert predictions is not None  # Decision making should not crash

            # Validate data quality handling
            assert not volatile_data.isnull().any().any()  # No NaN values in processed data
            assert (volatile_data['close'] > 0).all()  # All prices should be positive

    async def test_system_recovery_after_failure(self):
        """Test system recovery after various failure scenarios."""
        from data_pipeline.ingestion import MarketDataIngestion
        from smc_detector.patterns import OrderBlockDetector

        ingestion = MarketDataIngestion(self.config)
        detector = OrderBlockDetector(self.config)

        # Test different failure scenarios
        failure_scenarios = [
            {
                'name': 'Memory Pressure',
                'simulate': self._simulate_memory_pressure,
                'recovery_test': self._test_memory_recovery
            },
            {
                'name': 'High CPU Load',
                'simulate': self._simulate_cpu_pressure,
                'recovery_test': self._test_cpu_recovery
            },
            {
                'name': 'Network Latency',
                'simulate': self._simulate_network_latency,
                'recovery_test': self._test_network_recovery
            }
        ]

        for scenario in failure_scenarios:
            # Measure baseline performance
            baseline_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)
            baseline_time = time.time()
            baseline_result = await ingestion.ingest_ohlcv_data('BTCUSDT', baseline_data)
            baseline_duration = time.time() - baseline_time

            # Simulate failure condition
            await scenario['simulate'](duration=5)

            # Test system is degraded
            degraded_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)
            degraded_time = time.time()
            degraded_result = await ingestion.ingest_ohlcv_data('BTCUSDT', degraded_data)
            degraded_duration = time.time() - degraded_time

            # Allow recovery period
            await asyncio.sleep(2)

            # Test recovery
            recovery_success = await scenario['recovery_test'](
                ingestion, detector, baseline_duration * 2
            )

            # Recovery assertions
            assert baseline_result['status'] == 'success'
            assert degraded_result['status'] == 'success'  # System should still function
            assert recovery_success  # System should recover to acceptable performance

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent()

    def _generate_volatile_data(self, size: int, volatility: float) -> pd.DataFrame:
        """Generate highly volatile market data."""
        dates = pd.date_range(
            start=datetime.now() - timedelta(minutes=size),
            periods=size,
            freq='1min'
        )

        # Generate extreme price movements
        returns = np.random.normal(0, volatility, size)

        # Add occasional extreme moves
        extreme_moves = np.random.choice(size, size=int(size * 0.05), replace=False)
        returns[extreme_moves] *= np.random.uniform(3, 10)  # 3-10x normal moves

        base_price = 50000
        prices = [base_price]

        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            # Ensure prices stay positive
            new_price = max(new_price, base_price * 0.1)
            prices.append(new_price)

        data = []
        for i, (timestamp, close_price) in enumerate(zip(dates, prices[1:])):
            data.append({
                'timestamp': timestamp,
                'open': prices[i],
                'high': close_price * np.random.uniform(1.0, 1.01),
                'low': close_price * np.random.uniform(0.99, 1.0),
                'close': close_price,
                'volume': np.random.uniform(100, 5000)  # Higher volume in volatile markets
            })

        return pd.DataFrame(data)

    def _extract_features_from_volatile_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from volatile market data."""
        features = pd.DataFrame()

        # Calculate returns
        features['returns'] = data['close'].pct_change()
        features['volume_change'] = data['volume'].pct_change()
        features['volatility'] = features['returns'].rolling(20).std()
        features['rsi'] = self._calculate_rsi(data['close'])
        features['price_range'] = (data['high'] - data['low']) / data['close']

        # Fill NaN values
        features = features.fillna(0)

        return features.dropna()

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    async def _simulate_memory_pressure(self, duration: int):
        """Simulate memory pressure on the system."""
        # Allocate large amounts of memory
        memory_hogs = []
        try:
            for _ in range(10):
                # Allocate 50MB chunks
                chunk = np.random.random((50 * 1024 * 1024 // 8,))
                memory_hogs.append(chunk)
                await asyncio.sleep(0.5)
        finally:
            # Clean up memory
            memory_hogs.clear()

    async def _simulate_cpu_pressure(self, duration: int):
        """Simulate CPU pressure on the system."""
        end_time = time.time() + duration

        async def cpu_intensive_task():
            while time.time() < end_time:
                # CPU intensive computation
                _ = sum(i * i for i in range(1000))
                await asyncio.sleep(0.01)

        # Run multiple CPU intensive tasks
        tasks = [cpu_intensive_task() for _ in range(4)]
        await asyncio.gather(*tasks)

    async def _simulate_network_latency(self, duration: int):
        """Simulate network latency conditions."""
        # This would typically involve mocking network calls with delays
        # For now, we'll simulate with artificial delays
        end_time = time.time() + duration

        while time.time() < end_time:
            # Simulate network latency
            await asyncio.sleep(0.1)
            # Simulate network packet loss recovery
            if np.random.random() < 0.05:  # 5% packet loss
                await asyncio.sleep(0.5)  # Recovery delay

    async def _test_memory_recovery(self, ingestion, detector, max_acceptable_time: float) -> bool:
        """Test system recovery after memory pressure."""
        test_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)

        start_time = time.time()
        result = await ingestion.ingest_ohlcv_data('BTCUSDT', test_data)
        duration = time.time() - start_time

        return result['status'] == 'success' and duration < max_acceptable_time

    async def _test_cpu_recovery(self, ingestion, detector, max_acceptable_time: float) -> bool:
        """Test system recovery after CPU pressure."""
        test_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)

        start_time = time.time()
        result = await ingestion.ingest_ohlcv_data('BTCUSDT', test_data)
        duration = time.time() - start_time

        return result['status'] == 'success' and duration < max_acceptable_time

    async def _test_network_recovery(self, ingestion, detector, max_acceptable_time: float) -> bool:
        """Test system recovery after network issues."""
        test_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)

        start_time = time.time()
        result = await ingestion.ingest_ohlcv_data('BTCUSDT', test_data)
        duration = time.time() - start_time

        return result['status'] == 'success' and duration < max_acceptable_time


class PerformanceTestRunner:
    """Comprehensive performance test runner."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def run_all_performance_tests(self):
        """Run all performance tests and generate comprehensive report."""
        self.logger.info("Starting comprehensive performance test suite...")

        test_classes = [
            TestSystemPerformance,
            TestLoadTesting,
            TestStressTesting
        ]

        results = {}
        performance_metrics = {}

        for test_class in test_classes:
            self.logger.info(f"Running {test_class.__name__} performance tests...")

            # Create test instance
            test_instance = test_class()

            # Run tests
            start_time = time.time()
            test_results = await self._run_performance_tests(test_instance)
            total_time = time.time() - start_time

            # Collect performance metrics
            metrics = self._collect_performance_metrics(test_instance)

            results[test_class.__name__] = {
                'tests': test_results,
                'total_time': total_time,
                'performance_metrics': metrics
            }

        return self._generate_performance_report(results)

    async def _run_performance_tests(self, test_instance):
        """Run all performance test methods in a test class."""
        test_methods = [method for method in dir(test_instance)
                       if method.startswith('test_') and asyncio.iscoroutinefunction(method)]

        results = []
        for method_name in test_methods:
            try:
                method = getattr(test_instance, method_name)
                await method()
                results.append({
                    'method': method_name,
                    'status': 'PASSED'
                })
            except Exception as e:
                results.append({
                    'method': method_name,
                    'status': 'FAILED',
                    'error': str(e)
                })

        return results

    def _collect_performance_metrics(self, test_instance):
        """Collect performance metrics from test instance."""
        metrics = {}

        if hasattr(test_instance, 'performance_tracker'):
            metrics.update(test_instance.performance_tracker.get_performance_report())

        # Add system metrics
        metrics['system'] = {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
            'memory_available': psutil.virtual_memory().available / 1024 / 1024 / 1024  # GB
        }

        return metrics

    def _generate_performance_report(self, results: dict) -> dict:
        """Generate comprehensive performance test report."""
        total_tests = sum(len(r['tests']) for r in results.values())
        passed_tests = sum(len([t for t in r['tests'] if t['status'] == 'PASSED']) for r in results.values())
        failed_tests = sum(len([t for t in r['tests'] if t['status'] == 'FAILED']) for r in results.values())

        return {
            'summary': {
                'total_test_classes': len(results),
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_classes': results,
            'recommendations': self._generate_performance_recommendations(results),
            'benchmarks': self._extract_benchmarks(results)
        }

    def _generate_performance_recommendations(self, results: dict) -> list:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Analyze test results for performance issues
        for test_class, class_results in results.items():
            failed_tests = [t for t in class_results['tests'] if t['status'] == 'FAILED']
            if failed_tests:
                recommendations.append(
                    f"Address {len(failed_tests)} performance test failures in {test_class}"
                )

            # Check for slow test execution
            if class_results['total_time'] > 30:
                recommendations.append(
                    f"Optimize {test_class} performance (took {class_results['total_time']:.1f}s)"
                )

        # System-level recommendations
        recommendations.extend([
            "Monitor system resources during peak trading hours",
            "Implement performance monitoring in production",
            "Consider horizontal scaling for high-load scenarios",
            "Regular performance testing and benchmarking"
        ])

        return recommendations

    def _extract_benchmarks(self, results: dict) -> dict:
        """Extract performance benchmarks from test results."""
        benchmarks = {}

        for test_class, class_results in results.items():
            if 'performance_metrics' in class_results:
                benchmarks[test_class] = class_results['performance_metrics']

        return benchmarks


# Entry point for running performance tests
if __name__ == "__main__":
    async def main():
        runner = PerformanceTestRunner()
        results = await runner.run_all_performance_tests()

        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS")
        print("="*60)

        summary = results['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success Rate: {summary['success_rate']:.1f}%")

        print("\nTest Class Results:")
        for test_class, class_results in results['test_classes'].items():
            passed = len([t for t in class_results['tests'] if t['status'] == 'PASSED'])
            total = len(class_results['tests'])
            status_symbol = "✅" if passed == total else "❌"
            print(f"  {status_symbol} {test_class}: {passed}/{total} passed ({class_results['total_time']:.1f}s)")

        print("\nPerformance Recommendations:")
        for rec in results['recommendations']:
            print(f"  • {rec}")

        if 'benchmarks' in results:
            print("\nPerformance Benchmarks:")
            for test_class, benchmarks in results['benchmarks'].items():
                print(f"  {test_class}:")
                if 'summary' in benchmarks:
                    summary = benchmarks['summary']
                    print(f"    Average Duration: {summary.get('average_duration', 'N/A'):.3f}s")
                    print(f"    Total Duration: {summary.get('total_duration', 'N/A'):.3f}s")

    asyncio.run(main())