"""
Unit tests for error handling implementation in SMC Trading Agent.

This module provides comprehensive unit tests for:
- Circuit breaker functionality
- Retry handler mechanisms
- Data validation framework
- Error boundary patterns
- Health monitoring system
"""

import pytest
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity,
    CircuitBreakerState
)
from validators import (
    data_validator, DataQualityLevel, DataValidationError,
    MarketDataModel, TradeSignalModel, OrderBlockModel
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = Mock(spec=logging.Logger)
        self.cb = CircuitBreaker("test_component", 2, 5.0, self.logger)
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        assert self.cb.state.state == "CLOSED"
        assert self.cb.state.failure_count == 0
        assert self.cb.state.last_failure_time is None
    
    def test_circuit_breaker_successful_calls(self):
        """Test circuit breaker with successful calls."""
        def successful_operation():
            return "success"
        
        result = self.cb.call(successful_operation)
        assert result == "success"
        assert self.cb.state.state == "CLOSED"
        assert self.cb.state.failure_count == 0
    
    def test_circuit_breaker_failure_handling(self):
        """Test circuit breaker failure handling."""
        def failing_operation():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            self.cb.call(failing_operation)
        
        assert self.cb.state.failure_count == 1
        assert self.cb.state.state == "CLOSED"
        
        # Second failure (should open circuit)
        with pytest.raises(Exception):
            self.cb.call(failing_operation)
        
        assert self.cb.state.failure_count == 2
        assert self.cb.state.state == "OPEN"
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        # Open the circuit
        self.cb.state.state = "OPEN"
        self.cb.state.last_failure_time = time.time()
        
        def successful_operation():
            return "success"
        
        # Should raise ComponentHealthError
        with pytest.raises(ComponentHealthError):
            self.cb.call(successful_operation)
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        # Open the circuit
        self.cb.state.state = "OPEN"
        self.cb.state.last_failure_time = time.time() - 10  # 10 seconds ago
        
        def successful_operation():
            return "success"
        
        # Should transition to HALF_OPEN and then CLOSED
        result = self.cb.call(successful_operation)
        assert result == "success"
        assert self.cb.state.state == "CLOSED"
        assert self.cb.state.failure_count == 0


class TestRetryHandler:
    """Test retry handler functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = Mock(spec=logging.Logger)
        self.rh = RetryHandler(2, 0.1, 1.0, logger=self.logger)
    
    def test_retry_handler_successful_calls(self):
        """Test retry handler with successful calls."""
        def successful_operation():
            return "success"
        
        result = self.rh.call(successful_operation)
        assert result == "success"
    
    def test_retry_handler_retry_success(self):
        """Test retry handler with eventual success."""
        call_count = 0
        
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = self.rh.call(eventually_successful)
        assert result == "success"
        assert call_count == 3
    
    def test_retry_handler_max_retries_exceeded(self):
        """Test retry handler when max retries are exceeded."""
        def always_failing():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            self.rh.call(always_failing)
    
    def test_retry_handler_exponential_backoff(self):
        """Test retry handler exponential backoff."""
        call_times = []
        
        def failing_operation():
            call_times.append(time.time())
            raise Exception("Failure")
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            self.rh.call(failing_operation)
        
        # Should have 3 calls (initial + 2 retries)
        assert len(call_times) == 3
        
        # Check that delays increase exponentially
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        assert delay2 > delay1  # Exponential backoff


class TestDataValidation:
    """Test data validation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = data_validator
    
    def create_valid_market_data(self):
        """Create valid market data for testing."""
        timestamps = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(minutes=100), 
            periods=100, 
            freq='1min'
        )
        
        base_price = 55000
        price_changes = np.random.normal(0, 0.01, 100)
        prices = [base_price]
        
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        close_prices = [p * (1 + np.random.normal(0, 0.005)) for p in prices]
        
        high_prices = []
        low_prices = []
        
        for i in range(len(prices)):
            open_price = prices[i]
            close_price = close_prices[i]
            price_range = abs(open_price - close_price) * 2
            high = max(open_price, close_price) + np.random.uniform(0, price_range)
            low = min(open_price, close_price) - np.random.uniform(0, price_range)
            high_prices.append(high)
            low_prices.append(low)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(100, 1000, 100)
        })
    
    def test_market_data_validation_valid(self):
        """Test market data validation with valid data."""
        df = self.create_valid_market_data()
        is_valid, errors = self.validator.validate_market_data(df)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_market_data_validation_missing_columns(self):
        """Test market data validation with missing columns."""
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1h'),
            'open': np.random.uniform(50000, 60000, 10)
        })
        
        is_valid, errors = self.validator.validate_market_data(df)
        
        assert not is_valid
        assert any("Missing required columns" in error for error in errors)
    
    def test_market_data_validation_invalid_ohlc(self):
        """Test market data validation with invalid OHLC relationships."""
        df = self.create_valid_market_data()
        df.loc[0, 'high'] = 0  # Invalid high value
        
        is_valid, errors = self.validator.validate_market_data(df)
        
        assert not is_valid
        assert any("High values are not the highest" in error for error in errors)
    
    def test_market_data_validation_stale_data(self):
        """Test market data validation with stale data."""
        df = self.create_valid_market_data()
        # Make data stale by setting old timestamps
        df['timestamp'] = pd.date_range(start='2020-01-01', periods=100, freq='1h')
        
        is_valid, errors = self.validator.validate_market_data(df)
        
        assert not is_valid
        assert any("Data is stale" in error for error in errors)
    
    def test_data_quality_assessment(self):
        """Test data quality assessment."""
        df = self.create_valid_market_data()
        quality = self.validator.assess_data_quality(df)
        
        assert quality in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD]
    
    def test_trade_signal_validation_valid(self):
        """Test trade signal validation with valid data."""
        signal = {
            "action": "BUY",
            "symbol": "BTC/USDT",
            "entry_price": 55000.0,
            "confidence": 0.8
        }
        
        validated = self.validator.validate_trade_signal(signal)
        assert validated.action == "BUY"
        assert validated.confidence == 0.8
    
    def test_trade_signal_validation_invalid(self):
        """Test trade signal validation with invalid data."""
        signal = {
            "action": "INVALID",
            "symbol": "",
            "entry_price": -1000.0,
            "confidence": 1.5
        }
        
        with pytest.raises(DataValidationError):
            self.validator.validate_trade_signal(signal)
    
    def test_order_block_validation_valid(self):
        """Test order block validation with valid data."""
        order_block = {
            "timestamp": pd.Timestamp.now(),
            "type": "bullish",
            "price_level": (60000.0, 59000.0),
            "strength_volume": 150.0
        }
        
        validated = self.validator.validate_order_blocks([order_block])
        assert len(validated) == 1
        assert validated[0].type == "bullish"
    
    def test_order_block_validation_invalid(self):
        """Test order block validation with invalid data."""
        order_block = {
            "timestamp": pd.Timestamp.now(),
            "type": "invalid",
            "price_level": (59000.0, 60000.0),  # Low > High
            "strength_volume": -100.0
        }
        
        with pytest.raises(DataValidationError):
            self.validator.validate_order_blocks([order_block])
    
    def test_anomaly_detection(self):
        """Test anomaly detection functionality."""
        df = self.create_valid_market_data()
        anomalies = self.validator.detect_data_anomalies(df)
        
        assert isinstance(anomalies, dict)
        assert 'missing_data' in anomalies
        assert 'outliers' in anomalies
        assert 'duplicates' in anomalies
        assert 'inconsistencies' in anomalies
        assert 'timing_issues' in anomalies


class TestErrorBoundary:
    """Test error boundary functionality."""
    
    def test_error_boundary_successful_operation(self):
        """Test error boundary with successful operation."""
        with error_boundary("test_component", ErrorSeverity.MEDIUM):
            result = "success"
            assert result == "success"
    
    def test_error_boundary_error_handling(self):
        """Test error boundary error handling."""
        fallback_called = False
        
        def fallback_function():
            nonlocal fallback_called
            fallback_called = True
        
        with pytest.raises(TradingError):
            with error_boundary("test_component", ErrorSeverity.MEDIUM, fallback_function):
                raise Exception("Test error")
        
        assert fallback_called
    
    def test_error_boundary_fallback_failure(self):
        """Test error boundary when fallback also fails."""
        def failing_fallback():
            raise Exception("Fallback failure")
        
        with pytest.raises(TradingError):
            with error_boundary("test_component", ErrorSeverity.MEDIUM, failing_fallback):
                raise Exception("Test error")
    
    def test_safe_execute_decorator(self):
        """Test safe_execute decorator."""
        @safe_execute("test_component", ErrorSeverity.HIGH)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_safe_execute_decorator_with_error(self):
        """Test safe_execute decorator with error."""
        @safe_execute("test_component", ErrorSeverity.HIGH)
        def failing_function():
            raise Exception("Test error")
        
        with pytest.raises(TradingError):
            failing_function()


class TestHealthMonitor:
    """Test health monitoring functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.monitor = health_monitor
        self.monitor.components.clear()  # Reset for each test
    
    def test_health_monitor_registration(self):
        """Test component registration."""
        def health_check():
            return True
        
        self.monitor.register_component("test_component", health_check, critical=True)
        
        assert "test_component" in self.monitor.components
        assert self.monitor.components["test_component"]["critical"] is True
    
    def test_health_monitor_health_check(self):
        """Test health check functionality."""
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        self.monitor.register_component("healthy", healthy_check, critical=False)
        self.monitor.register_component("unhealthy", unhealthy_check, critical=True)
        
        # Check individual components
        assert self.monitor.check_health("healthy") is True
        assert self.monitor.check_health("unhealthy") is False
    
    def test_health_monitor_system_health(self):
        """Test system health reporting."""
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        self.monitor.register_component("healthy", healthy_check, critical=False)
        self.monitor.register_component("unhealthy", unhealthy_check, critical=True)
        
        health_status = self.monitor.get_system_health()
        
        assert health_status["overall_healthy"] is False
        assert health_status["critical_failures"] == 1
        assert health_status["total_failures"] == 1
        assert "healthy" in health_status["components"]
        assert "unhealthy" in health_status["components"]
    
    def test_health_monitor_error_handling(self):
        """Test health monitor error handling."""
        def failing_health_check():
            raise Exception("Health check failure")
        
        self.monitor.register_component("failing", failing_health_check, critical=True)
        
        # Should handle the exception and mark as unhealthy
        assert self.monitor.check_health("failing") is False


class TestIntegration:
    """Integration tests for error handling components."""
    
    def test_circuit_breaker_with_retry_handler(self):
        """Test circuit breaker combined with retry handler."""
        logger = Mock(spec=logging.Logger)
        cb = CircuitBreaker("test", 2, 5.0, logger)
        rh = RetryHandler(1, 0.1, 1.0, logger=logger)
        
        call_count = 0
        
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        # Use retry handler inside circuit breaker
        result = cb.call(lambda: rh.call(operation))
        
        assert result == "success"
        assert call_count == 3
    
    def test_error_boundary_with_validation(self):
        """Test error boundary with data validation."""
        def operation_with_validation():
            # Simulate data validation
            data = {"invalid": "data"}
            validated = data_validator.validate_trade_signal(data)
            return validated
        
        with pytest.raises(TradingError):
            with error_boundary("validation_test", ErrorSeverity.HIGH):
                operation_with_validation()
    
    def test_health_monitor_with_circuit_breaker(self):
        """Test health monitor with circuit breaker integration."""
        monitor = health_monitor
        monitor.components.clear()
        
        def health_check():
            # Simulate checking if circuit breaker is healthy
            return True
        
        monitor.register_component("circuit_breaker", health_check, critical=True)
        
        health_status = monitor.get_system_health()
        assert health_status["overall_healthy"] is True


class TestPerformance:
    """Performance tests for error handling components."""
    
    def test_validation_performance(self):
        """Test data validation performance."""
        # Create large dataset
        timestamps = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=1000), 
            periods=10000, 
            freq='1min'
        )
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': np.random.uniform(50000, 60000, 10000),
            'high': np.random.uniform(60000, 70000, 10000),
            'low': np.random.uniform(40000, 50000, 10000),
            'close': np.random.uniform(50000, 60000, 10000),
            'volume': np.random.uniform(100, 1000, 10000)
        })
        
        # Ensure OHLC relationships
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)
        
        start_time = time.time()
        is_valid, errors = data_validator.validate_market_data(df)
        validation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert validation_time < 5.0  # 5 seconds
        assert is_valid
    
    def test_circuit_breaker_performance(self):
        """Test circuit breaker performance."""
        logger = Mock(spec=logging.Logger)
        cb = CircuitBreaker("perf_test", 5, 10.0, logger)
        
        def fast_operation():
            return "success"
        
        start_time = time.time()
        for _ in range(1000):
            cb.call(fast_operation)
        total_time = time.time() - start_time
        
        # Should handle 1000 calls quickly
        assert total_time < 1.0  # 1 second
        assert cb.state.state == "CLOSED"


if __name__ == "__main__":
    pytest.main([__file__])
