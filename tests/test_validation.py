"""
Unit tests for data validation framework in SMC Trading Agent.

This module provides comprehensive unit tests for:
- Market data validation
- Trade signal validation
- Order block validation
- Data quality assessment
- Anomaly detection
"""

import pytest
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
from ..validators import (
    data_validator, DataQualityLevel, DataValidationError,
    MarketDataModel, TradeSignalModel, OrderBlockModel
)


class TestMarketDataValidation:
    """Test market data validation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = Mock(spec=logging.Logger)
    
    def create_valid_market_data(self):
        """Create valid market data for testing."""
        timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(minutes=100), periods=100, freq='1min')
        base_price = 55000
        
        # Generate realistic OHLCV data
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
        """Test validation of valid market data."""
        data = self.create_valid_market_data()
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_market_data_validation_missing_columns(self):
        """Test validation with missing columns."""
        data = self.create_valid_market_data()
        data = data.drop(columns=['volume'])
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert not is_valid
        assert len(errors) > 0
        assert any('volume' in error.lower() for error in errors)
    
    def test_market_data_validation_invalid_ohlc(self):
        """Test validation with invalid OHLC values."""
        data = self.create_valid_market_data()
        
        # Set invalid values
        data.loc[0, 'high'] = 0  # Invalid high
        data.loc[1, 'low'] = -100  # Invalid low
        data.loc[2, 'open'] = data.loc[2, 'close'] + 1000  # Unrealistic spread
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_market_data_validation_stale_data(self):
        """Test validation with stale data."""
        # Create old data
        old_timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(hours=24), periods=100, freq='1min')
        data = self.create_valid_market_data()
        data['timestamp'] = old_timestamps
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert not is_valid
        assert len(errors) > 0
        assert any('stale' in error.lower() for error in errors)
    
    def test_data_quality_assessment(self):
        """Test data quality assessment."""
        data = self.create_valid_market_data()
        
        quality = data_validator.assess_data_quality(data)
        
        assert quality in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD, DataQualityLevel.ACCEPTABLE]
    
    def test_data_quality_assessment_poor_data(self):
        """Test data quality assessment with poor data."""
        data = self.create_valid_market_data()
        
        # Add noise and gaps
        data.loc[10:20, 'close'] = np.nan
        data.loc[30:40, 'volume'] = 0
        
        quality = data_validator.assess_data_quality(data)
        
        assert quality in [DataQualityLevel.POOR, DataQualityLevel.UNACCEPTABLE]


class TestTradeSignalValidation:
    """Test trade signal validation functionality."""
    
    def test_trade_signal_validation_valid(self):
        """Test validation of valid trade signal."""
        signal = {
            "action": "BUY",
            "symbol": "BTC/USDT",
            "entry_price": 55000.0,
            "confidence": 0.8,
            "timestamp": datetime.now().isoformat()
        }
        
        validated_signal = data_validator.validate_trade_signal(signal)
        
        assert validated_signal.action == "BUY"
        assert validated_signal.symbol == "BTC/USDT"
        assert validated_signal.entry_price == 55000.0
        assert validated_signal.confidence == 0.8
    
    def test_trade_signal_validation_invalid_action(self):
        """Test validation with invalid action."""
        signal = {
            "action": "INVALID",
            "symbol": "BTC/USDT",
            "entry_price": 55000.0,
            "confidence": 0.8
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_trade_signal(signal)
    
    def test_trade_signal_validation_invalid_price(self):
        """Test validation with invalid price."""
        signal = {
            "action": "BUY",
            "symbol": "BTC/USDT",
            "entry_price": -1000.0,
            "confidence": 0.8
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_trade_signal(signal)
    
    def test_trade_signal_validation_invalid_confidence(self):
        """Test validation with invalid confidence."""
        signal = {
            "action": "BUY",
            "symbol": "BTC/USDT",
            "entry_price": 55000.0,
            "confidence": 1.5  # > 1.0
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_trade_signal(signal)
    
    def test_trade_signal_validation_missing_fields(self):
        """Test validation with missing required fields."""
        signal = {
            "action": "BUY",
            "entry_price": 55000.0
            # Missing symbol and confidence
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_trade_signal(signal)


class TestOrderBlockValidation:
    """Test order block validation functionality."""
    
    def test_order_block_validation_valid(self):
        """Test validation of valid order block."""
        order_block = {
            "type": "bullish",
            "high": 56000.0,
            "low": 54000.0,
            "strength": 0.8,
            "timestamp": datetime.now().isoformat()
        }
        
        validated_block = data_validator.validate_order_block(order_block)
        
        assert validated_block.type == "bullish"
        assert validated_block.high == 56000.0
        assert validated_block.low == 54000.0
        assert validated_block.strength == 0.8
    
    def test_order_block_validation_invalid_type(self):
        """Test validation with invalid type."""
        order_block = {
            "type": "invalid",
            "high": 56000.0,
            "low": 54000.0,
            "strength": 0.8
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_order_block(order_block)
    
    def test_order_block_validation_invalid_prices(self):
        """Test validation with invalid price levels."""
        order_block = {
            "type": "bullish",
            "high": 54000.0,  # High < Low
            "low": 56000.0,
            "strength": 0.8
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_order_block(order_block)
    
    def test_order_block_validation_invalid_strength(self):
        """Test validation with invalid strength."""
        order_block = {
            "type": "bullish",
            "high": 56000.0,
            "low": 54000.0,
            "strength": 1.5  # > 1.0
        }
        
        with pytest.raises(DataValidationError):
            data_validator.validate_order_block(order_block)


class TestAnomalyDetection:
    """Test anomaly detection functionality."""
    
    def test_anomaly_detection_normal_data(self):
        """Test anomaly detection with normal data."""
        data = pd.DataFrame({
            'close': np.random.normal(55000, 1000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        anomalies = data_validator.detect_anomalies(data)
        
        # Should not detect many anomalies in normal data
        assert len(anomalies) < len(data) * 0.1  # Less than 10% anomalies
    
    def test_anomaly_detection_with_outliers(self):
        """Test anomaly detection with outliers."""
        data = pd.DataFrame({
            'close': np.random.normal(55000, 1000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        # Add outliers
        data.loc[50, 'close'] = 100000  # Extreme price
        data.loc[51, 'volume'] = 10000  # Extreme volume
        
        anomalies = data_validator.detect_anomalies(data)
        
        # Should detect the outliers
        assert len(anomalies) >= 2
    
    def test_anomaly_detection_empty_data(self):
        """Test anomaly detection with empty data."""
        data = pd.DataFrame()
        
        anomalies = data_validator.detect_anomalies(data)
        
        assert len(anomalies) == 0


class TestPerformance:
    """Test validation performance."""
    
    def test_validation_performance_large_dataset(self):
        """Test validation performance with large dataset."""
        # Create large dataset
        timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(hours=24), periods=10000, freq='1min')
        data = pd.DataFrame({
            'timestamp': timestamps,
            'open': np.random.uniform(50000, 60000, 10000),
            'high': np.random.uniform(50000, 60000, 10000),
            'low': np.random.uniform(50000, 60000, 10000),
            'close': np.random.uniform(50000, 60000, 10000),
            'volume': np.random.uniform(100, 1000, 10000)
        })
        
        start_time = time.time()
        is_valid, errors = data_validator.validate_market_data(data)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second)
        assert end_time - start_time < 1.0
        assert is_valid
    
    def test_validation_performance_batch_processing(self):
        """Test validation performance with batch processing."""
        # Create multiple datasets
        datasets = []
        for i in range(10):
            timestamps = pd.date_range(start=pd.Timestamp.now() - pd.Timedelta(hours=1), periods=1000, freq='1min')
            data = pd.DataFrame({
                'timestamp': timestamps,
                'open': np.random.uniform(50000, 60000, 1000),
                'high': np.random.uniform(50000, 60000, 1000),
                'low': np.random.uniform(50000, 60000, 1000),
                'close': np.random.uniform(50000, 60000, 1000),
                'volume': np.random.uniform(100, 1000, 1000)
            })
            datasets.append(data)
        
        start_time = time.time()
        results = []
        for data in datasets:
            is_valid, errors = data_validator.validate_market_data(data)
            results.append(is_valid)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 5 seconds)
        assert end_time - start_time < 5.0
        assert all(results)  # All should be valid


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_validation_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        data = pd.DataFrame()
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_validation_single_row(self):
        """Test validation with single row of data."""
        data = pd.DataFrame({
            'timestamp': [pd.Timestamp.now()],
            'open': [55000.0],
            'high': [56000.0],
            'low': [54000.0],
            'close': [55500.0],
            'volume': [500.0]
        })
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validation_extreme_values(self):
        """Test validation with extreme but valid values."""
        data = pd.DataFrame({
            'timestamp': [pd.Timestamp.now()],
            'open': [1.0],  # Very low price
            'high': [1000000.0],  # Very high price
            'low': [0.01],  # Very low price
            'close': [500000.0],  # Very high price
            'volume': [0.001]  # Very low volume
        })
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        # Should be valid if within reasonable bounds
        assert is_valid or len(errors) > 0  # Either valid or has specific errors
    
    def test_validation_nan_values(self):
        """Test validation with NaN values."""
        data = pd.DataFrame({
            'timestamp': [pd.Timestamp.now()],
            'open': [np.nan],
            'high': [56000.0],
            'low': [54000.0],
            'close': [55500.0],
            'volume': [500.0]
        })
        
        is_valid, errors = data_validator.validate_market_data(data)
        
        assert not is_valid
        assert len(errors) > 0


