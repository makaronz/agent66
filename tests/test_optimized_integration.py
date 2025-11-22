#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Optimized SMC Trading System

Tests the ultra-low latency integration of all optimized components:
- Optimized Kafka producer performance
- Parallel ML ensemble with caching
- Advanced risk management with circuit breakers
- Ultra-low latency execution engine
- End-to-end system latency (<50ms target)
"""

import asyncio
import pytest
import time
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import numpy as np

# Test fixtures and helpers
@pytest.fixture
async def mock_redis():
    """Mock Redis for testing"""
    class MockRedis:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def setex(self, key, ttl, value):
            self.data[key] = value

        async def ping(self):
            return True

        async def close(self):
            pass

    return MockRedis()

@pytest.fixture
async def mock_kafka_producer():
    """Mock optimized Kafka producer"""
    from data_pipeline.kafka_producer_optimized import OptimizedKafkaProducer, KafkaConfig

    config = KafkaConfig(
        bootstrap_servers=['localhost:9092'],
        batch_size=100,
        linger_ms=5
    )

    producer = OptimizedKafkaProducer(config)

    # Mock the actual Kafka operations
    producer.producer = AsyncMock()
    producer.producer.send_and_wait = AsyncMock(return_value=Mock(offset=0, partition=0))

    return producer

@pytest.fixture
def mock_ml_models():
    """Mock ML models for testing"""
    class MockModel:
        def __init__(self):
            self.device = 'cpu'

        def to(self, device):
            self.device = device
            return self

        def eval(self):
            return self

        def predict_direction(self, x):
            return Mock(), Mock()

    return {
        'lstm': MockModel(),
        'transformer': MockModel(),
        'ppo': Mock()
    }

@pytest.fixture
async def optimized_ml_ensemble(mock_ml_models, mock_redis):
    """Create optimized ML ensemble for testing"""
    from decision_engine.model_ensemble_optimized import OptimizedModelEnsemble, ModelConfig
    from sklearn.preprocessing import StandardScaler

    config = ModelConfig(
        cache_ttl_seconds=60,
        parallel_execution=True,
        max_workers=2
    )

    ensemble = OptimizedModelEnsemble(
        lstm_model=mock_ml_models['lstm'],
        transformer_model=mock_ml_models['transformer'],
        ppo_model=mock_ml_models['ppo'],
        scaler=StandardScaler(),
        config=config,
        redis_url="redis://localhost:6379"
    )

    # Mock Redis connection
    ensemble.cache._redis = mock_redis

    return ensemble

@pytest.fixture
async def optimized_circuit_breaker():
    """Create optimized circuit breaker for testing"""
    from risk_manager.circuit_breaker_optimized import OptimizedCircuitBreaker, RiskConfig

    config = RiskConfig(
        max_drawdown=0.05,
        max_var=0.02,
        parallel_calculation=True,
        max_workers=2,
        redis_url="redis://localhost:6379"
    )

    breaker = OptimizedCircuitBreaker(config)

    # Mock database connection
    breaker.db_pool = AsyncMock()

    return breaker

@pytest.fixture
async def optimized_execution_engine():
    """Create optimized execution engine for testing"""
    from execution_engine.optimized_execution_engine import create_optimized_execution_engine

    config = {
        'max_chunk_size': 1000.0,
        'execution_workers': 2,
        'latency_target_ms': 30
    }

    engine = create_optimized_execution_engine(config)
    await engine.start()

    yield engine

    await engine.stop()


class TestOptimizedKafkaProducer:
    """Test optimized Kafka producer performance"""

    @pytest.mark.asyncio
    async def test_batch_processing_latency(self, mock_kafka_producer):
        """Test that batch processing meets latency targets"""
        start_time = time.time()

        # Send multiple messages rapidly
        messages = []
        for i in range(100):
            success = await mock_kafka_producer.send_market_data(
                exchange="binance",
                symbol="BTCUSDT",
                data_type="kline",
                data={'price': 50000.0, 'volume': 1.0}
            )
            messages.append(success)

        # Flush to ensure all messages are sent
        await mock_kafka_producer.flush()

        latency = (time.time() - start_time) * 1000  # Convert to ms

        # Should process 100 messages in under 100ms (1ms per message)
        assert latency < 100, f"Batch processing took {latency:.2f}ms, target <100ms"
        assert all(messages), "All messages should be sent successfully"

    @pytest.mark.asyncio
    async def test_message_queue_performance(self, mock_kafka_producer):
        """Test message queue performance under load"""
        messages_per_batch = 1000
        start_time = time.time()

        # Send large batch of messages
        tasks = []
        for i in range(messages_per_batch):
            task = mock_kafka_producer.send_market_data(
                exchange="binance",
                symbol=f"SYMBOL{i%10}",
                data_type="trade",
                data={'price': 50000.0 + i, 'volume': 1.0}
            )
            tasks.append(task)

        # Wait for all messages to be queued
        await asyncio.gather(*tasks)
        await mock_kafka_producer.flush()

        total_time = (time.time() - start_time) * 1000
        avg_latency = total_time / messages_per_batch

        # Should achieve sub-1ms average per message
        assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms per message, target <1ms"

    def test_metrics_tracking(self, mock_kafka_producer):
        """Test that metrics are tracked correctly"""
        initial_count = mock_kafka_producer.messages_sent
        initial_errors = mock_kafka_producer.error_count

        # These should be updated when messages are sent
        assert hasattr(mock_kafka_producer, 'get_metrics')
        metrics = mock_kafka_producer.get_metrics()

        assert 'messages_sent' in metrics
        assert 'error_count' in metrics
        assert 'avg_latency_ms' in metrics


class TestOptimizedMLEnsemble:
    """Test optimized ML ensemble performance"""

    @pytest.mark.asyncio
    async def test_parallel_inference_latency(self, optimized_ml_ensemble):
        """Test that parallel ML inference meets latency targets"""
        # Create test data
        test_data = np.random.randn(100, 2)  # 100 samples, 2 features (price, volume)

        # Measure inference time
        start_time = time.time()

        action, confidence, metadata = await optimized_ml_ensemble.predict_parallel(
            test_data, sequence_length=60
        )

        inference_time = (time.time() - start_time) * 1000  # Convert to ms

        # Should complete inference in under 20ms
        assert inference_time < 20, f"Inference took {inference_time:.2f}ms, target <20ms"
        assert 'inference_time_ms' in metadata
        assert 'source' in metadata
        assert action in [0, 1, 2]  # Valid actions: buy(0), hold(1), sell(2)
        assert 0 <= confidence <= 1

    @pytest.mark.asyncio
    async def test_cache_performance(self, optimized_ml_ensemble):
        """Test that caching improves performance"""
        test_data = np.random.randn(60, 2)  # Exactly 60 samples

        # First inference (should miss cache)
        start_time = time.time()
        action1, confidence1, metadata1 = await optimized_ml_ensemble.predict_parallel(test_data)
        first_time = (time.time() - start_time) * 1000

        # Second inference with same data (should hit cache)
        start_time = time.time()
        action2, confidence2, metadata2 = await optimized_ml_ensemble.predict_parallel(test_data)
        second_time = (time.time() - start_time) * 1000

        # Results should be identical
        assert action1 == action2
        assert confidence1 == confidence2
        assert metadata1['source'] == 'inference'
        assert metadata2['source'] == 'cache'

        # Cache hit should be significantly faster
        assert second_time < first_time * 0.5, "Cache hit should be at least 50% faster"

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_performance(self, optimized_ml_ensemble):
        """Test that parallel execution is faster than sequential"""
        test_data = np.random.randn(60, 2)

        # Force parallel execution
        optimized_ml_ensemble.config.parallel_execution = True
        start_time = time.time()
        action_parallel, _, _ = await optimized_ml_ensemble.predict_parallel(test_data)
        parallel_time = (time.time() - start_time) * 1000

        # Force sequential execution
        optimized_ml_ensemble.config.parallel_execution = False
        start_time = time.time()
        action_sequential, _, _ = await optimized_ml_ensemble.predict_parallel(test_data)
        sequential_time = (time.time() - start_time) * 1000

        # Results should be the same but parallel should be faster
        assert action_parallel == action_sequential
        assert parallel_time < sequential_time, "Parallel execution should be faster than sequential"

    def test_performance_metrics(self, optimized_ml_ensemble):
        """Test that performance metrics are tracked"""
        metrics = optimized_ml_ensemble.get_performance_metrics()

        assert 'inference_times' in metrics
        assert 'cache_performance' in metrics
        assert 'model_performance' in metrics
        assert 'parallel_execution' in metrics


class TestOptimizedCircuitBreaker:
    """Test optimized circuit breaker performance"""

    @pytest.mark.asyncio
    async def test_parallel_risk_checks_latency(self, optimized_circuit_breaker):
        """Test that parallel risk checks meet latency targets"""
        # Test portfolio data
        portfolio_data = {
            'positions': {'BTCUSDT': 0.1},
            'balance': 10000.0,
            'drawdown': 0.02,
            'leverage': 1.5,
            'returns': np.random.randn(100).tolist(),
            'returns_matrix': np.random.randn(10, 5).tolist()
        }

        # Test trade details
        trade_details = {
            'symbol': 'BTCUSDT',
            'quantity': 0.01,
            'price': 50000.0,
            'side': 'buy'
        }

        # Measure risk check time
        start_time = time.time()

        is_safe, violations, metadata = await optimized_circuit_breaker.check_risk_limits(
            portfolio_data, trade_details
        )

        risk_check_time = (time.time() - start_time) * 1000

        # Should complete risk checks in under 5ms
        assert risk_check_time < 5, f"Risk check took {risk_check_time:.2f}ms, target <5ms"
        assert isinstance(is_safe, bool)
        assert isinstance(violations, list)
        assert 'check_time_ms' in metadata
        assert 'parallel_checks' in metadata

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, optimized_circuit_breaker):
        """Test circuit breaker opens and closes correctly"""
        portfolio_data = {
            'positions': {},
            'balance': 10000.0,
            'drawdown': 0.15,  # High drawdown to trigger circuit
            'leverage': 1.0,
            'returns': [],
            'returns_matrix': []
        }

        trade_details = {
            'symbol': 'BTCUSDT',
            'quantity': 0.01,
            'price': 50000.0,
            'side': 'buy'
        }

        # First check should fail due to high drawdown
        is_safe1, violations1, metadata1 = await optimized_circuit_breaker.check_risk_limits(
            portfolio_data, trade_details
        )

        # Second check should be blocked by circuit breaker after enough failures
        for i in range(5):
            await optimized_circuit_breaker.check_risk_limits(portfolio_data, trade_details)

        is_safe2, violations2, metadata2 = await optimized_circuit_breaker.check_risk_limits(
            portfolio_data, trade_details
        )

        assert not is_safe1
        assert not is_safe2  # Should be blocked by circuit breaker
        assert metadata1['circuit_state'] == 'closed'
        assert metadata2['circuit_state'] == 'open'

    def test_performance_metrics(self, optimized_circuit_breaker):
        """Test that performance metrics are tracked"""
        metrics = optimized_circuit_breaker.get_performance_metrics()

        assert 'state' in metrics
        assert 'failure_count' in metrics
        assert 'performance' in metrics
        assert 'metrics' in metrics


class TestOptimizedExecutionEngine:
    """Test optimized execution engine performance"""

    @pytest.mark.asyncio
    async def test_order_submission_latency(self, optimized_execution_engine):
        """Test that order submission meets latency targets"""
        from execution_engine.optimized_execution_engine import OrderRequest, OrderSide, OrderType, ExecutionStrategy

        # Create test order
        order_request = OrderRequest(
            id="test-order-1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            strategy=ExecutionStrategy.LATENCY_OPTIMIZED
        )

        # Measure submission time
        start_time = time.time()

        order_id = await optimized_execution_engine.submit_order(order_request)

        submission_time = (time.time() - start_time) * 1000

        # Should submit order in under 10ms
        assert submission_time < 10, f"Order submission took {submission_time:.2f}ms, target <10ms"
        assert order_id == "test-order-1"

    @pytest.mark.asyncio
    async def test_order_execution_latency(self, optimized_execution_engine):
        """Test that order execution meets latency targets"""
        from execution_engine.optimized_execution_engine import OrderRequest, OrderSide, OrderType, ExecutionStrategy

        # Create and submit order
        order_request = OrderRequest(
            id="test-order-execution",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
            strategy=ExecutionStrategy.LATENCY_OPTIMIZED
        )

        await optimized_execution_engine.submit_order(order_request)

        # Wait for execution (with timeout)
        max_wait_time = 1.0  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            order_status = await optimized_execution_engine.get_order_status("test-order-execution")
            if order_status and order_status['status'] == 'filled':
                execution_time = (time.time() - start_time) * 1000
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail("Order execution timed out")

        # Should execute order in under 50ms (target for ultra-low latency)
        assert execution_time < 50, f"Order execution took {execution_time:.2f}ms, target <50ms"

    def test_performance_metrics(self, optimized_execution_engine):
        """Test that performance metrics are tracked"""
        metrics = optimized_execution_engine.get_performance_metrics()

        assert 'latency_stats' in metrics
        assert 'execution_stats' in metrics
        assert 'circuit_breaker' in metrics
        assert 'active_orders' in metrics


class TestEndToEndIntegration:
    """Test end-to-end integration performance"""

    @pytest.mark.asyncio
    async def test_complete_trading_cycle_latency(self, mock_kafka_producer, optimized_ml_ensemble, optimized_circuit_breaker):
        """Test complete trading cycle meets sub-50ms target"""

        # Simulate market data
        market_data = {
            'symbol': 'BTCUSDT',
            'price': 50000.0,
            'volume': 1.5,
            'timestamp': time.time()
        }

        cycle_start_time = time.time()

        # 1. Data pipeline (send to Kafka) - Target: <10ms
        data_start = time.time()
        await mock_kafka_producer.send_market_data(
            exchange="binance",
            symbol="BTCUSDT",
            data_type="trade",
            data=market_data
        )
        data_time = (time.time() - data_start) * 1000

        # 2. ML inference - Target: <20ms
        ml_start = time.time()
        test_data = np.random.randn(60, 2)
        action, confidence, ml_metadata = await optimized_ml_ensemble.predict_parallel(test_data)
        ml_time = (time.time() - ml_start) * 1000

        # 3. Risk management - Target: <5ms
        risk_start = time.time()
        portfolio_data = {'balance': 10000.0, 'positions': {}, 'drawdown': 0.01}
        trade_details = {'symbol': 'BTCUSDT', 'quantity': 0.01, 'price': 50000.0, 'side': 'buy'}
        is_safe, violations, risk_metadata = await optimized_circuit_breaker.check_risk_limits(
            portfolio_data, trade_details
        )
        risk_time = (time.time() - risk_start) * 1000

        total_cycle_time = (time.time() - cycle_start_time) * 1000

        # Validate individual component performance
        assert data_time < 10, f"Data pipeline took {data_time:.2f}ms, target <10ms"
        assert ml_time < 20, f"ML inference took {ml_time:.2f}ms, target <20ms"
        assert risk_time < 5, f"Risk check took {risk_time:.2f}ms, target <5ms"

        # Validate overall performance
        assert total_cycle_time < 50, f"Complete cycle took {total_cycle_time:.2f}ms, target <50ms"

        # Validate results
        assert action in [0, 1, 2]
        assert 0 <= confidence <= 1
        assert isinstance(is_safe, bool)

    @pytest.mark.asyncio
    async def test_system_under_load(self, mock_kafka_producer, optimized_ml_ensemble, optimized_circuit_breaker):
        """Test system performance under concurrent load"""

        concurrent_cycles = 10
        cycle_latencies = []

        async def single_cycle():
            cycle_start = time.time()

            # Simulate complete trading cycle
            await mock_kafka_producer.send_market_data(
                exchange="binance",
                symbol="BTCUSDT",
                data_type="trade",
                data={'price': 50000.0, 'volume': 1.0}
            )

            test_data = np.random.randn(60, 2)
            await optimized_ml_ensemble.predict_parallel(test_data)

            portfolio_data = {'balance': 10000.0}
            trade_details = {'symbol': 'BTCUSDT', 'quantity': 0.01, 'price': 50000.0}
            await optimized_circuit_breaker.check_risk_limits(portfolio_data, trade_details)

            return (time.time() - cycle_start) * 1000

        # Run concurrent cycles
        tasks = [single_cycle() for _ in range(concurrent_cycles)]
        cycle_latencies = await asyncio.gather(*tasks)

        # Analyze performance under load
        avg_latency = sum(cycle_latencies) / len(cycle_latencies)
        p95_latency = sorted(cycle_latencies)[int(len(cycle_latencies) * 0.95)]

        # Should maintain performance under concurrent load
        assert avg_latency < 50, f"Average latency under load: {avg_latency:.2f}ms, target <50ms"
        assert p95_latency < 75, f"P95 latency under load: {p95_latency:.2f}ms, target <75ms"

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_kafka_producer, optimized_ml_ensemble, optimized_circuit_breaker):
        """Test system resilience and error recovery"""

        # Test 1: Kafka failure handling
        mock_kafka_producer.producer.send_and_wait.side_effect = Exception("Kafka error")

        try:
            await mock_kafka_producer.send_market_data(
                exchange="binance",
                symbol="BTCUSDT",
                data_type="trade",
                data={'price': 50000.0}
            )
        except Exception:
            pass  # Expected

        # Test 2: Circuit breaker should handle errors gracefully
        portfolio_data = {'balance': -1000.0}  # Invalid data
        trade_details = {'symbol': 'BTCUSDT', 'quantity': 0.01}

        is_safe, violations, metadata = await optimized_circuit_breaker.check_risk_limits(
            portfolio_data, trade_details
        )

        assert not is_safe
        assert len(violations) > 0

        # Test 3: System should recover from errors
        mock_kafka_producer.producer.send_and_wait.side_effect = None

        success = await mock_kafka_producer.send_market_data(
            exchange="binance",
            symbol="BTCUSDT",
            data_type="trade",
            data={'price': 50000.0}
        )

        assert success, "System should recover from Kafka errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])