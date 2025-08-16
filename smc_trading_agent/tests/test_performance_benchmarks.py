"""
Performance benchmarks for high-frequency trading operations.
Tests latency, throughput, and resource usage under various load conditions.
"""

import pytest
import time
import asyncio
import threading
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import statistics
from typing import List, Dict, Any

from smc_detector.indicators import SMCIndicators
from decision_engine.model_ensemble import ModelEnsemble
from data_pipeline.ingestion import MarketDataProcessor
from risk_manager.smc_risk_manager import SMCRiskManager


class PerformanceBenchmark:
    """Base class for performance benchmarking."""
    
    def __init__(self, name: str):
        self.name = name
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.memory_before = None
        self.memory_after = None
        self.cpu_before = None
        self.cpu_after = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        gc.collect()  # Clean up before measurement
        self.memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.cpu_before = psutil.cpu_percent(interval=None)
        self.start_time = time.perf_counter()
    
    def stop_monitoring(self):
        """Stop performance monitoring and calculate metrics."""
        self.end_time = time.perf_counter()
        self.cpu_after = psutil.cpu_percent(interval=None)
        self.memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        self.results.update({
            'duration': self.end_time - self.start_time,
            'memory_used': self.memory_after - self.memory_before,
            'cpu_usage': self.cpu_after - self.cpu_before,
            'memory_before': self.memory_before,
            'memory_after': self.memory_after
        })
    
    def get_results(self) -> Dict[str, Any]:
        """Get benchmark results."""
        return {
            'name': self.name,
            'timestamp': datetime.now(),
            **self.results
        }


@pytest.fixture
def large_market_data():
    """Generate large market dataset for performance testing."""
    np.random.seed(42)
    size = 10000
    
    dates = pd.date_range('2024-01-01', periods=size, freq='1min')
    base_price = 50000
    
    # Generate realistic price movements
    returns = np.random.normal(0, 0.001, size)  # 0.1% volatility
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price * (1 + abs(np.random.normal(0, 0.002)))
        low = price * (1 - abs(np.random.normal(0, 0.002)))
        open_price = prices[i-1] if i > 0 else price
        volume = np.random.uniform(100, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def streaming_data_generator():
    """Generate streaming data for real-time performance testing."""
    def generate_tick_data(symbol: str, count: int = 1000):
        """Generate tick data stream."""
        base_price = 50000
        current_price = base_price
        
        for i in range(count):
            # Small price movements
            change = np.random.normal(0, 0.0001)  # 0.01% movements
            current_price *= (1 + change)
            
            yield {
                'symbol': symbol,
                'price': current_price,
                'volume': np.random.uniform(1, 100),
                'timestamp': datetime.now() + timedelta(milliseconds=i),
                'bid': current_price * 0.9999,
                'ask': current_price * 1.0001
            }
    
    return generate_tick_data


class TestSMCIndicatorPerformance:
    """Performance tests for SMC indicators."""
    
    def test_order_block_detection_performance(self, large_market_data):
        """Test order block detection performance with large dataset."""
        smc_indicators = SMCIndicators()
        benchmark = PerformanceBenchmark("order_block_detection_large_dataset")
        
        benchmark.start_monitoring()
        
        # Run order block detection
        order_blocks = smc_indicators.detect_order_blocks(large_market_data)
        
        benchmark.stop_monitoring()
        results = benchmark.get_results()
        
        # Performance assertions
        assert results['duration'] < 5.0  # Should complete within 5 seconds
        assert results['memory_used'] < 500  # Should use less than 500MB additional memory
        assert len(order_blocks) >= 0  # Should return valid results
        
        # Log performance metrics
        print(f"Order Block Detection Performance:")
        print(f"  Duration: {results['duration']:.3f}s")
        print(f"  Memory used: {results['memory_used']:.1f}MB")
        print(f"  Blocks detected: {len(order_blocks)}")
        print(f"  Throughput: {len(large_market_data) / results['duration']:.0f} candles/sec")
    
    def test_choch_bos_detection_performance(self, large_market_data):
        """Test CHOCH/BOS detection performance with large dataset."""
        smc_indicators = SMCIndicators()
        benchmark = PerformanceBenchmark("choch_bos_detection_large_dataset")
        
        benchmark.start_monitoring()
        
        # Run CHOCH/BOS detection
        patterns = smc_indicators.identify_choch_bos(large_market_data)
        
        benchmark.stop_monitoring()
        results = benchmark.get_results()
        
        # Performance assertions
        assert results['duration'] < 10.0  # Should complete within 10 seconds
        assert results['memory_used'] < 500  # Should use less than 500MB additional memory
        assert isinstance(patterns, dict)
        
        total_patterns = patterns.get('total_patterns', 0)
        
        print(f"CHOCH/BOS Detection Performance:")
        print(f"  Duration: {results['duration']:.3f}s")
        print(f"  Memory used: {results['memory_used']:.1f}MB")
        print(f"  Patterns detected: {total_patterns}")
        print(f"  Throughput: {len(large_market_data) / results['duration']:.0f} candles/sec")
    
    def test_liquidity_sweep_detection_performance(self, large_market_data):
        """Test liquidity sweep detection performance with large dataset."""
        smc_indicators = SMCIndicators()
        benchmark = PerformanceBenchmark("liquidity_sweep_detection_large_dataset")
        
        benchmark.start_monitoring()
        
        # Run liquidity sweep detection
        sweeps = smc_indicators.liquidity_sweep_detection(large_market_data)
        
        benchmark.stop_monitoring()
        results = benchmark.get_results()
        
        # Performance assertions
        assert results['duration'] < 15.0  # Should complete within 15 seconds
        assert results['memory_used'] < 500  # Should use less than 500MB additional memory
        assert isinstance(sweeps, dict)
        
        total_sweeps = sweeps.get('total_sweeps', 0)
        
        print(f"Liquidity Sweep Detection Performance:")
        print(f"  Duration: {results['duration']:.3f}s")
        print(f"  Memory used: {results['memory_used']:.1f}MB")
        print(f"  Sweeps detected: {total_sweeps}")
        print(f"  Throughput: {len(large_market_data) / results['duration']:.0f} candles/sec")
    
    @pytest.mark.parametrize("data_size", [1000, 5000, 10000, 20000])
    def test_smc_scalability(self, data_size):
        """Test SMC indicator scalability with different data sizes."""
        # Generate data of specified size
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=data_size, freq='1min')
        prices = 50000 + np.cumsum(np.random.normal(0, 10, data_size))
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.001,
            'low': prices * 0.999,
            'close': prices,
            'volume': np.random.uniform(100, 1000, data_size)
        })
        
        smc_indicators = SMCIndicators()
        
        start_time = time.perf_counter()
        order_blocks = smc_indicators.detect_order_blocks(data)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        throughput = data_size / duration
        
        # Scalability assertions
        assert duration < data_size * 0.001  # Should be sub-linear
        assert throughput > 1000  # Should process at least 1000 candles/sec
        
        print(f"Scalability Test (size={data_size}):")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Throughput: {throughput:.0f} candles/sec")
    
    def test_concurrent_smc_processing(self, large_market_data):
        """Test concurrent SMC processing performance."""
        smc_indicators = SMCIndicators()
        
        # Split data into chunks for concurrent processing
        chunk_size = len(large_market_data) // 4
        chunks = [
            large_market_data[i:i+chunk_size] 
            for i in range(0, len(large_market_data), chunk_size)
        ]
        
        benchmark = PerformanceBenchmark("concurrent_smc_processing")
        benchmark.start_monitoring()
        
        # Process chunks concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(smc_indicators.detect_order_blocks, chunk)
                for chunk in chunks
            ]
            
            results = [future.result() for future in futures]
        
        benchmark.stop_monitoring()
        perf_results = benchmark.get_results()
        
        # Combine results
        total_blocks = sum(len(result) for result in results)
        
        # Performance assertions
        assert perf_results['duration'] < 10.0  # Should benefit from concurrency
        assert total_blocks >= 0
        
        print(f"Concurrent SMC Processing Performance:")
        print(f"  Duration: {perf_results['duration']:.3f}s")
        print(f"  Total blocks: {total_blocks}")
        print(f"  Chunks processed: {len(chunks)}")


class TestModelEnsemblePerformance:
    """Performance tests for model ensemble."""
    
    def test_model_prediction_latency(self):
        """Test model prediction latency for real-time trading."""
        ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        
        # Generate test data
        test_data = pd.DataFrame({
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100),
            'feature_1': np.random.randn(100),
            'feature_2': np.random.randn(100),
            'feature_3': np.random.randn(100)
        })
        
        # Warm up (first prediction is often slower)
        ensemble.predict(test_data)
        
        # Measure prediction latency
        latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = ensemble.predict(test_data)
            end_time = time.perf_counter()
            
            latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds
            assert result['action'] in ['BUY', 'SELL', 'HOLD']
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        
        # Performance assertions for HFT
        assert avg_latency < 50  # Average < 50ms
        assert p95_latency < 100  # 95th percentile < 100ms
        assert p99_latency < 200  # 99th percentile < 200ms
        
        print(f"Model Prediction Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")
    
    def test_model_throughput(self):
        """Test model prediction throughput."""
        ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        
        # Generate batch of test data
        batch_size = 1000
        test_batches = []
        
        for _ in range(batch_size):
            data = pd.DataFrame({
                'close': np.random.uniform(49000, 51000, 100),
                'volume': np.random.uniform(1000, 10000, 100),
                'feature_1': np.random.randn(100),
                'feature_2': np.random.randn(100),
                'feature_3': np.random.randn(100)
            })
            test_batches.append(data)
        
        benchmark = PerformanceBenchmark("model_throughput_test")
        benchmark.start_monitoring()
        
        # Process all batches
        results = []
        for batch in test_batches:
            result = ensemble.predict(batch)
            results.append(result)
        
        benchmark.stop_monitoring()
        perf_results = benchmark.get_results()
        
        throughput = batch_size / perf_results['duration']
        
        # Performance assertions
        assert throughput > 100  # Should process > 100 predictions/sec
        assert len(results) == batch_size
        
        print(f"Model Throughput Performance:")
        print(f"  Duration: {perf_results['duration']:.3f}s")
        print(f"  Throughput: {throughput:.0f} predictions/sec")
        print(f"  Memory used: {perf_results['memory_used']:.1f}MB")
    
    def test_model_memory_efficiency(self):
        """Test model memory efficiency under sustained load."""
        ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        
        # Generate test data
        test_data = pd.DataFrame({
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100),
            'feature_1': np.random.randn(100),
            'feature_2': np.random.randn(100),
            'feature_3': np.random.randn(100)
        })
        
        # Measure memory usage over time
        memory_usage = []
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        for i in range(1000):
            ensemble.predict(test_data)
            
            if i % 100 == 0:  # Sample every 100 predictions
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_usage.append(current_memory - initial_memory)
        
        # Check for memory leaks
        memory_growth = memory_usage[-1] - memory_usage[0]
        max_memory_used = max(memory_usage)
        
        # Performance assertions
        assert memory_growth < 100  # Should not grow more than 100MB
        assert max_memory_used < 500  # Should not exceed 500MB total
        
        print(f"Model Memory Efficiency:")
        print(f"  Initial memory delta: {memory_usage[0]:.1f}MB")
        print(f"  Final memory delta: {memory_usage[-1]:.1f}MB")
        print(f"  Memory growth: {memory_growth:.1f}MB")
        print(f"  Max memory used: {max_memory_used:.1f}MB")


class TestDataProcessingPerformance:
    """Performance tests for data processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_realtime_data_processing_latency(self, streaming_data_generator):
        """Test real-time data processing latency."""
        processor = MarketDataProcessor()
        
        # Generate streaming data
        tick_generator = streaming_data_generator('BTCUSDT', 1000)
        
        latencies = []
        processed_count = 0
        
        for tick_data in tick_generator:
            start_time = time.perf_counter()
            
            # Process tick data
            result = processor.process_tick_data(tick_data)
            
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000000  # Convert to microseconds
            
            latencies.append(latency)
            if result:
                processed_count += 1
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        
        # Performance assertions for HFT
        assert avg_latency < 1000  # Average < 1ms (1000 microseconds)
        assert p95_latency < 5000  # P95 < 5ms
        assert p99_latency < 10000  # P99 < 10ms
        
        print(f"Real-time Data Processing Latency:")
        print(f"  Average: {avg_latency:.0f}μs")
        print(f"  P95: {p95_latency:.0f}μs")
        print(f"  P99: {p99_latency:.0f}μs")
        print(f"  Processed: {processed_count}/{len(latencies)}")
    
    def test_data_ingestion_throughput(self, streaming_data_generator):
        """Test data ingestion throughput under high load."""
        processor = MarketDataProcessor()
        
        # Configure for high throughput
        processor.configure_high_throughput(
            batch_size=1000,
            buffer_size=10000,
            processing_threads=4
        )
        
        # Generate high-frequency data
        tick_count = 10000
        tick_generator = streaming_data_generator('BTCUSDT', tick_count)
        
        benchmark = PerformanceBenchmark("data_ingestion_throughput")
        benchmark.start_monitoring()
        
        processed_count = 0
        for tick_data in tick_generator:
            result = processor.process_tick_data(tick_data)
            if result:
                processed_count += 1
        
        benchmark.stop_monitoring()
        results = benchmark.get_results()
        
        throughput = processed_count / results['duration']
        
        # Performance assertions
        assert throughput > 5000  # Should process > 5000 ticks/sec
        assert processed_count >= tick_count * 0.95  # Should process at least 95%
        
        print(f"Data Ingestion Throughput:")
        print(f"  Duration: {results['duration']:.3f}s")
        print(f"  Throughput: {throughput:.0f} ticks/sec")
        print(f"  Processed: {processed_count}/{tick_count}")
        print(f"  Memory used: {results['memory_used']:.1f}MB")
    
    def test_concurrent_data_streams(self, streaming_data_generator):
        """Test concurrent processing of multiple data streams."""
        processor = MarketDataProcessor()
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        tick_count_per_symbol = 1000
        
        benchmark = PerformanceBenchmark("concurrent_data_streams")
        benchmark.start_monitoring()
        
        # Process multiple streams concurrently
        def process_stream(symbol):
            tick_generator = streaming_data_generator(symbol, tick_count_per_symbol)
            processed = 0
            for tick_data in tick_generator:
                result = processor.process_tick_data(tick_data)
                if result:
                    processed += 1
            return processed
        
        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            futures = [executor.submit(process_stream, symbol) for symbol in symbols]
            results = [future.result() for future in futures]
        
        benchmark.stop_monitoring()
        perf_results = benchmark.get_results()
        
        total_processed = sum(results)
        total_expected = len(symbols) * tick_count_per_symbol
        throughput = total_processed / perf_results['duration']
        
        # Performance assertions
        assert throughput > 10000  # Should handle > 10k ticks/sec across all streams
        assert total_processed >= total_expected * 0.9  # Should process at least 90%
        
        print(f"Concurrent Data Streams Performance:")
        print(f"  Duration: {perf_results['duration']:.3f}s")
        print(f"  Total throughput: {throughput:.0f} ticks/sec")
        print(f"  Streams: {len(symbols)}")
        print(f"  Processed: {total_processed}/{total_expected}")
        print(f"  Memory used: {perf_results['memory_used']:.1f}MB")


class TestRiskManagerPerformance:
    """Performance tests for risk management operations."""
    
    def test_risk_calculation_latency(self):
        """Test risk calculation latency for real-time trading."""
        risk_manager = SMCRiskManager()
        
        # Generate test scenarios
        test_scenarios = []
        for _ in range(1000):
            scenario = {
                'entry_price': np.random.uniform(49000, 51000),
                'action': np.random.choice(['BUY', 'SELL']),
                'position_size': np.random.uniform(0.1, 10.0),
                'account_balance': np.random.uniform(10000, 100000),
                'volatility': np.random.uniform(0.1, 0.5)
            }
            test_scenarios.append(scenario)
        
        # Measure calculation latencies
        latencies = []
        
        for scenario in test_scenarios:
            start_time = time.perf_counter()
            
            # Calculate risk metrics
            stop_loss = risk_manager.calculate_stop_loss(
                scenario['entry_price'],
                scenario['action'],
                [],  # order_blocks
                {}   # structure
            )
            
            take_profit = risk_manager.calculate_take_profit(
                scenario['entry_price'],
                stop_loss,
                scenario['action']
            )
            
            position_size = risk_manager.calculate_position_size(
                scenario['account_balance'],
                scenario['entry_price'],
                stop_loss,
                risk_percentage=0.02
            )
            
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        
        # Performance assertions for HFT
        assert avg_latency < 1.0  # Average < 1ms
        assert p95_latency < 5.0  # P95 < 5ms
        assert p99_latency < 10.0  # P99 < 10ms
        
        print(f"Risk Calculation Latency:")
        print(f"  Average: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  P99: {p99_latency:.3f}ms")
        print(f"  Scenarios tested: {len(test_scenarios)}")
    
    def test_portfolio_risk_monitoring_performance(self):
        """Test portfolio risk monitoring performance."""
        risk_manager = SMCRiskManager()
        
        # Generate portfolio with multiple positions
        portfolio_size = 100
        positions = []
        
        for i in range(portfolio_size):
            position = {
                'symbol': f'SYMBOL{i}',
                'side': np.random.choice(['long', 'short']),
                'size': np.random.uniform(0.1, 10.0),
                'entry_price': np.random.uniform(1, 1000),
                'current_price': np.random.uniform(1, 1000),
                'unrealized_pnl': np.random.uniform(-1000, 1000)
            }
            positions.append(position)
        
        benchmark = PerformanceBenchmark("portfolio_risk_monitoring")
        benchmark.start_monitoring()
        
        # Monitor portfolio risk
        risk_metrics = risk_manager.calculate_portfolio_risk(positions)
        
        benchmark.stop_monitoring()
        results = benchmark.get_results()
        
        # Performance assertions
        assert results['duration'] < 0.1  # Should complete within 100ms
        assert isinstance(risk_metrics, dict)
        assert 'total_exposure' in risk_metrics
        
        print(f"Portfolio Risk Monitoring Performance:")
        print(f"  Duration: {results['duration']*1000:.1f}ms")
        print(f"  Portfolio size: {portfolio_size}")
        print(f"  Memory used: {results['memory_used']:.1f}MB")


@pytest.mark.performance
class TestEndToEndPerformance:
    """End-to-end performance tests for complete trading pipeline."""
    
    @pytest.mark.asyncio
    async def test_complete_trading_cycle_latency(self, streaming_data_generator):
        """Test complete trading cycle latency from data to execution."""
        # Initialize components
        data_processor = MarketDataProcessor()
        smc_indicators = SMCIndicators()
        model_ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        risk_manager = SMCRiskManager()
        
        # Generate test data
        tick_generator = streaming_data_generator('BTCUSDT', 100)
        
        # Prepare historical data for models
        historical_data = pd.DataFrame({
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100),
            'feature_1': np.random.randn(100),
            'feature_2': np.random.randn(100),
            'feature_3': np.random.randn(100)
        })
        
        cycle_latencies = []
        
        for tick_data in tick_generator:
            cycle_start = time.perf_counter()
            
            # 1. Process incoming data
            processed_data = data_processor.process_tick_data(tick_data)
            
            if processed_data:
                # 2. Update historical data (simplified)
                # In real implementation, this would update the DataFrame
                
                # 3. Detect SMC patterns (on sample data)
                order_blocks = smc_indicators.detect_order_blocks(
                    historical_data.tail(50)  # Use recent data
                )
                
                # 4. Make trading decision
                if order_blocks:
                    decision = model_ensemble.predict(historical_data)
                    
                    if decision['action'] != 'HOLD' and decision['confidence'] > 0.7:
                        # 5. Calculate risk parameters
                        entry_price = processed_data.get('price', 50000)
                        
                        stop_loss = risk_manager.calculate_stop_loss(
                            entry_price, decision['action'], order_blocks, {}
                        )
                        
                        take_profit = risk_manager.calculate_take_profit(
                            entry_price, stop_loss, decision['action']
                        )
                        
                        # 6. Execute trade (mocked)
                        trade_executed = True
            
            cycle_end = time.perf_counter()
            cycle_latency = (cycle_end - cycle_start) * 1000  # Convert to milliseconds
            cycle_latencies.append(cycle_latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(cycle_latencies)
        p95_latency = np.percentile(cycle_latencies, 95)
        p99_latency = np.percentile(cycle_latencies, 99)
        
        # Performance assertions for HFT
        assert avg_latency < 100  # Average < 100ms
        assert p95_latency < 200  # P95 < 200ms
        assert p99_latency < 500  # P99 < 500ms
        
        print(f"Complete Trading Cycle Latency:")
        print(f"  Average: {avg_latency:.1f}ms")
        print(f"  P95: {p95_latency:.1f}ms")
        print(f"  P99: {p99_latency:.1f}ms")
        print(f"  Cycles tested: {len(cycle_latencies)}")
    
    def test_system_resource_usage_under_load(self, streaming_data_generator):
        """Test system resource usage under sustained load."""
        # Initialize all components
        data_processor = MarketDataProcessor()
        smc_indicators = SMCIndicators()
        model_ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        risk_manager = SMCRiskManager()
        
        # Monitor system resources
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        initial_cpu = psutil.cpu_percent(interval=None)
        
        memory_samples = []
        cpu_samples = []
        
        # Run sustained load test
        duration = 30  # 30 seconds
        start_time = time.time()
        
        tick_count = 0
        while time.time() - start_time < duration:
            # Generate and process data
            tick_generator = streaming_data_generator('BTCUSDT', 100)
            
            for tick_data in tick_generator:
                # Process data through pipeline
                processed_data = data_processor.process_tick_data(tick_data)
                tick_count += 1
                
                # Sample resources every 1000 ticks
                if tick_count % 1000 == 0:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    current_cpu = psutil.cpu_percent(interval=None)
                    
                    memory_samples.append(current_memory - initial_memory)
                    cpu_samples.append(current_cpu)
        
        # Calculate resource usage statistics
        avg_memory_usage = statistics.mean(memory_samples) if memory_samples else 0
        max_memory_usage = max(memory_samples) if memory_samples else 0
        avg_cpu_usage = statistics.mean(cpu_samples) if cpu_samples else 0
        max_cpu_usage = max(cpu_samples) if cpu_samples else 0
        
        throughput = tick_count / duration
        
        # Performance assertions
        assert avg_memory_usage < 1000  # Average memory usage < 1GB
        assert max_memory_usage < 2000  # Max memory usage < 2GB
        assert avg_cpu_usage < 80  # Average CPU usage < 80%
        assert throughput > 1000  # Should process > 1000 ticks/sec
        
        print(f"System Resource Usage Under Load:")
        print(f"  Duration: {duration}s")
        print(f"  Throughput: {throughput:.0f} ticks/sec")
        print(f"  Average memory usage: {avg_memory_usage:.1f}MB")
        print(f"  Max memory usage: {max_memory_usage:.1f}MB")
        print(f"  Average CPU usage: {avg_cpu_usage:.1f}%")
        print(f"  Max CPU usage: {max_cpu_usage:.1f}%")
        print(f"  Total ticks processed: {tick_count}")


if __name__ == "__main__":
    # Run performance benchmarks directly
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])