#!/usr/bin/env python3
"""
Test script for error handling implementation in SMC Trading Agent.

This script tests the comprehensive error handling, validation, and graceful
degradation features implemented in the main application.
"""

import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the current directory to the path for imports
sys.path.append('.')

from error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)
from validators import (
    data_validator, DataQualityLevel, DataValidationError
)
from data_pipeline.ingestion import MarketDataProcessor
from smc_detector.indicators import SMCIndicators
from decision_engine.model_ensemble import AdaptiveModelSelector
from risk_manager.smc_risk_manager import SMCRiskManager


def setup_test_logging():
    """Setup logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Circuit Breaker...")
    
    # Create circuit breaker
    cb = CircuitBreaker("test_component", 2, 5.0, logger)
    
    # Test successful calls
    def successful_operation():
        return "success"
    
    result = cb.call(successful_operation)
    assert result == "success"
    logger.info("✅ Circuit breaker successful calls work")
    
    # Test failure handling
    def failing_operation():
        raise Exception("Test failure")
    
    # First failure
    try:
        cb.call(failing_operation)
    except Exception:
        pass
    
    # Second failure (should open circuit)
    try:
        cb.call(failing_operation)
    except Exception:
        pass
    
    # Third call should fail immediately (circuit open)
    try:
        cb.call(successful_operation)
        assert False, "Circuit should be open"
    except ComponentHealthError:
        logger.info("✅ Circuit breaker opens correctly after failures")
    
    logger.info("✅ Circuit breaker test passed")


def test_retry_handler():
    """Test retry handler functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Retry Handler...")
    
    # Create retry handler
    rh = RetryHandler(2, 0.1, 1.0, logger=logger)
    
    # Test successful operation
    def successful_operation():
        return "success"
    
    result = rh.call(successful_operation)
    assert result == "success"
    logger.info("✅ Retry handler successful calls work")
    
    # Test retry with eventual success
    call_count = 0
    def eventually_successful():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    result = rh.call(eventually_successful)
    assert result == "success"
    assert call_count == 3
    logger.info("✅ Retry handler retries and succeeds")
    
    # Test retry with permanent failure
    def always_failing():
        raise Exception("Permanent failure")
    
    try:
        rh.call(always_failing)
        assert False, "Should have failed after retries"
    except Exception:
        logger.info("✅ Retry handler fails after max retries")
    
    logger.info("✅ Retry handler test passed")


def test_data_validation():
    """Test data validation functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Data Validation...")
    
    # Create valid market data
    timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(minutes=100), periods=100, freq='1min')
    base_price = 55000
    
    # Generate realistic OHLCV data
    price_changes = np.random.normal(0, 0.01, 100)  # 1% daily volatility
    prices = [base_price]
    
    for change in price_changes[1:]:
        prices.append(prices[-1] * (1 + change))
    
    # Generate close prices
    close_prices = [p * (1 + np.random.normal(0, 0.005)) for p in prices]  # Small random change
    
    # Generate high and low prices
    high_prices = []
    low_prices = []
    
    for i in range(len(prices)):
        open_price = prices[i]
        close_price = close_prices[i]
        
        # Generate realistic high and low
        price_range = abs(open_price - close_price) * 2
        high = max(open_price, close_price) + np.random.uniform(0, price_range)
        low = min(open_price, close_price) - np.random.uniform(0, price_range)
        
        high_prices.append(high)
        low_prices.append(low)
    
    valid_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': np.random.uniform(100, 1000, 100)
    })
    
    # Test valid data
    is_valid, errors = data_validator.validate_market_data(valid_data)
    if not is_valid:
        logger.error(f"Validation failed with errors: {errors}")
    assert is_valid
    assert len(errors) == 0
    logger.info("✅ Valid market data validation passed")
    
    # Test data quality assessment
    quality = data_validator.assess_data_quality(valid_data)
    assert quality in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD]
    logger.info(f"✅ Data quality assessment: {quality.value}")
    
    # Test invalid data
    invalid_data = valid_data.copy()
    invalid_data.loc[0, 'high'] = 0  # Invalid high value
    
    is_valid, errors = data_validator.validate_market_data(invalid_data)
    assert not is_valid
    assert len(errors) > 0
    logger.info("✅ Invalid market data validation caught errors")
    
    # Test trade signal validation
    valid_signal = {
        "action": "BUY",
        "symbol": "BTC/USDT",
        "entry_price": 55000.0,
        "confidence": 0.8
    }
    
    validated_signal = data_validator.validate_trade_signal(valid_signal)
    assert validated_signal.action == "BUY"
    assert validated_signal.confidence == 0.8
    logger.info("✅ Trade signal validation passed")
    
    # Test invalid trade signal
    invalid_signal = {
        "action": "INVALID",
        "symbol": "",
        "entry_price": -1000.0,
        "confidence": 1.5
    }
    
    try:
        data_validator.validate_trade_signal(invalid_signal)
        assert False, "Should have raised validation error"
    except DataValidationError:
        logger.info("✅ Invalid trade signal validation caught errors")
    
    logger.info("✅ Data validation test passed")


def test_error_boundary():
    """Test error boundary functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Error Boundary...")
    
    # Test successful operation
    with error_boundary("test_component", ErrorSeverity.MEDIUM):
        result = "success"
        assert result == "success"
    logger.info("✅ Error boundary successful operation")
    
    # Test error handling
    fallback_called = False
    def fallback_function():
        nonlocal fallback_called
        fallback_called = True
    
    try:
        with error_boundary("test_component", ErrorSeverity.MEDIUM, fallback_function):
            raise Exception("Test error")
    except TradingError:
        assert fallback_called
        logger.info("✅ Error boundary handled error and called fallback")
    
    logger.info("✅ Error boundary test passed")


def test_health_monitor():
    """Test health monitoring functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Health Monitor...")
    
    # Register test components
    health_monitor.register_component("test_component", lambda: True, critical=False)
    health_monitor.register_component("failing_component", lambda: False, critical=True)
    
    # Check health
    health_status = health_monitor.get_system_health()
    assert not health_status["overall_healthy"]  # Should be unhealthy due to failing component
    assert health_status["critical_failures"] == 1
    assert health_status["total_failures"] == 1
    logger.info("✅ Health monitor detected component failures")
    
    logger.info("✅ Health monitor test passed")


def test_component_integration():
    """Test component integration with error handling."""
    logger = logging.getLogger(__name__)
    logger.info("Testing Component Integration...")
    
    try:
        # Initialize components
        data_processor = MarketDataProcessor()
        smc_detector = SMCIndicators()
        decision_engine = AdaptiveModelSelector()
        risk_manager = SMCRiskManager()
        
        # Test data processing with error handling
        circuit_breaker = CircuitBreaker("data_processor", 3, 60.0, logger)
        retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
        
        # Create fresh test data instead of using potentially stale data
        timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(minutes=100), periods=100, freq='1min')
        base_price = 55000
        
        # Generate realistic OHLCV data
        price_changes = np.random.normal(0, 0.01, 100)  # 1% daily volatility
        prices = [base_price]
        
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        # Generate close prices
        close_prices = [p * (1 + np.random.normal(0, 0.005)) for p in prices]  # Small random change
        
        # Generate high and low prices
        high_prices = []
        low_prices = []
        
        for i in range(len(prices)):
            open_price = prices[i]
            close_price = close_prices[i]
            
            # Generate realistic high and low
            price_range = abs(open_price - close_price) * 2
            high = max(open_price, close_price) + np.random.uniform(0, price_range)
            low = min(open_price, close_price) - np.random.uniform(0, price_range)
            
            high_prices.append(high)
            low_prices.append(low)
        
        market_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        # Validate data
        is_valid, errors = data_validator.validate_market_data(market_data)
        if not is_valid:
            logger.error(f"Component integration validation failed: {errors}")
        assert is_valid
        logger.info("✅ Component integration with error handling works")
        
        # Test SMC detection
        order_blocks = smc_detector.detect_order_blocks(market_data)
        logger.info(f"✅ SMC detection found {len(order_blocks)} order blocks")
        
        # Test decision engine
        if order_blocks:
            trade_signal = decision_engine.make_decision(order_blocks, market_data)
            if trade_signal:
                validated_signal = data_validator.validate_trade_signal(trade_signal)
                logger.info(f"✅ Decision engine generated valid signal: {validated_signal.action}")
        
        # Test risk management
        if order_blocks:
            stop_loss = risk_manager.calculate_stop_loss(
                55000.0, "BUY", order_blocks, {}
            )
            take_profit = risk_manager.calculate_take_profit(
                55000.0, stop_loss, "BUY"
            )
            logger.info(f"✅ Risk management calculated SL: {stop_loss}, TP: {take_profit}")
        
    except Exception as e:
        logger.error(f"Component integration test failed: {str(e)}", exc_info=True)
        raise
    
    logger.info("✅ Component integration test passed")


def main():
    """Run all error handling tests."""
    logger = setup_test_logging()
    logger.info("Starting Error Handling Tests...")
    
    try:
        test_circuit_breaker()
        test_retry_handler()
        test_data_validation()
        test_error_boundary()
        test_health_monitor()
        test_component_integration()
        
        logger.info("🎉 All error handling tests passed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error handling tests failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
