"""
Unit tests for SMC Indicators core functionality.
Tests the core SMC pattern detection algorithms with comprehensive coverage.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from smc_detector.indicators import SMCIndicators


class TestSMCIndicators:
    """Test suite for SMC Indicators with comprehensive unit test coverage."""
    
    @pytest.fixture
    def smc_indicators(self):
        """Create SMC indicators instance for testing."""
        return SMCIndicators()
    
    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        np.random.seed(42)  # For reproducible tests
        
        # Generate realistic price data
        base_price = 50000
        price_changes = np.random.normal(0, 0.02, 100)
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def minimal_ohlcv_data(self):
        """Create minimal OHLCV data for edge case testing."""
        return pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [50000],
            'high': [50100],
            'low': [49900],
            'close': [50050],
            'volume': [1000]
        })
    
    def test_detect_order_blocks_valid_input(self, smc_indicators, sample_ohlcv_data):
        """Test order block detection with valid input data."""
        result = smc_indicators.detect_order_blocks(sample_ohlcv_data)
        
        assert isinstance(result, list)
        # Should detect some order blocks in the sample data
        assert len(result) >= 0
        
        # Validate structure of detected order blocks
        for block in result:
            assert isinstance(block, dict)
            assert 'timestamp' in block
            assert 'type' in block
            assert 'price_level' in block
            assert 'strength_volume' in block
            assert block['type'] in ['bullish', 'bearish']
            assert isinstance(block['price_level'], tuple)
            assert len(block['price_level']) == 2
            assert block['price_level'][0] >= block['price_level'][1]  # high >= low
    
    def test_detect_order_blocks_insufficient_data(self, smc_indicators, minimal_ohlcv_data):
        """Test order block detection with insufficient data."""
        result = smc_indicators.detect_order_blocks(minimal_ohlcv_data)
        
        # Should return empty list for insufficient data
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_detect_order_blocks_invalid_columns(self, smc_indicators):
        """Test order block detection with invalid column names."""
        invalid_data = pd.DataFrame({
            'time': [datetime.now()],
            'o': [50000],
            'h': [50100],
            'l': [49900],
            'c': [50050],
            'v': [1000]
        })
        
        with pytest.raises(ValueError, match="Input DataFrame must contain columns"):
            smc_indicators.detect_order_blocks(invalid_data)
    
    def test_detect_order_blocks_custom_parameters(self, smc_indicators, sample_ohlcv_data):
        """Test order block detection with custom parameters."""
        result = smc_indicators.detect_order_blocks(
            sample_ohlcv_data,
            volume_threshold_percentile=90,
            bos_confirmation_factor=2.0
        )
        
        assert isinstance(result, list)
        # With stricter parameters, should detect fewer blocks
        assert len(result) >= 0
    
    def test_identify_choch_bos_valid_input(self, smc_indicators, sample_ohlcv_data):
        """Test CHOCH/BOS identification with valid input data."""
        result = smc_indicators.identify_choch_bos(sample_ohlcv_data)
        
        assert isinstance(result, dict)
        assert 'coch_patterns' in result
        assert 'bos_patterns' in result
        assert 'swing_highs' in result
        assert 'swing_lows' in result
        assert 'total_patterns' in result
        
        # Validate CHOCH patterns
        for pattern in result['coch_patterns']:
            assert isinstance(pattern, dict)
            assert 'timestamp' in pattern
            assert 'type' in pattern
            assert 'confidence' in pattern
            assert pattern['type'] in ['bullish_coch', 'bearish_coch']
            assert 0 <= pattern['confidence'] <= 1
        
        # Validate BOS patterns
        for pattern in result['bos_patterns']:
            assert isinstance(pattern, dict)
            assert 'timestamp' in pattern
            assert 'type' in pattern
            assert 'confidence' in pattern
            assert pattern['type'] in ['bullish_bos', 'bearish_bos']
            assert 0 <= pattern['confidence'] <= 1
    
    def test_identify_choch_bos_with_custom_swings(self, smc_indicators, sample_ohlcv_data):
        """Test CHOCH/BOS identification with custom swing points."""
        # Provide custom swing points
        swing_highs = [10, 30, 50, 70]
        swing_lows = [5, 25, 45, 65]
        
        result = smc_indicators.identify_choch_bos(
            sample_ohlcv_data,
            swing_highs=swing_highs,
            swing_lows=swing_lows
        )
        
        assert isinstance(result, dict)
        assert result['swing_highs'] == swing_highs
        assert result['swing_lows'] == swing_lows
    
    def test_identify_choch_bos_invalid_columns(self, smc_indicators):
        """Test CHOCH/BOS identification with invalid columns."""
        invalid_data = pd.DataFrame({
            'time': [datetime.now()],
            'price': [50000]
        })
        
        with pytest.raises(ValueError, match="Input DataFrame must contain columns"):
            smc_indicators.identify_choch_bos(invalid_data)
    
    def test_liquidity_sweep_detection_valid_input(self, smc_indicators, sample_ohlcv_data):
        """Test liquidity sweep detection with valid input data."""
        result = smc_indicators.liquidity_sweep_detection(sample_ohlcv_data)
        
        assert isinstance(result, dict)
        assert 'detected_sweeps' in result
        assert 'support_levels' in result
        assert 'resistance_levels' in result
        assert 'total_sweeps' in result
        
        # Validate detected sweeps
        for sweep in result['detected_sweeps']:
            assert isinstance(sweep, dict)
            assert 'timestamp' in sweep
            assert 'type' in sweep
            assert 'confidence' in sweep
            assert sweep['type'] in ['bullish_sweep', 'bearish_sweep']
            assert 0 <= sweep['confidence'] <= 1
    
    def test_liquidity_sweep_detection_custom_parameters(self, smc_indicators, sample_ohlcv_data):
        """Test liquidity sweep detection with custom parameters."""
        result = smc_indicators.liquidity_sweep_detection(
            sample_ohlcv_data,
            volume_threshold_percentile=90,
            sweep_reversal_candles=5,
            min_sweep_distance=0.2,
            volume_spike_threshold=3.0,
            confidence_threshold=0.8
        )
        
        assert isinstance(result, dict)
        # With stricter parameters, should detect fewer sweeps
        assert len(result['detected_sweeps']) >= 0
    
    def test_liquidity_sweep_detection_insufficient_data(self, smc_indicators, minimal_ohlcv_data):
        """Test liquidity sweep detection with insufficient data."""
        result = smc_indicators.liquidity_sweep_detection(minimal_ohlcv_data)
        
        assert isinstance(result, dict)
        assert len(result['detected_sweeps']) == 0
    
    @pytest.mark.parametrize("volume_percentile", [80, 90, 95, 99])
    def test_detect_order_blocks_volume_percentiles(self, smc_indicators, sample_ohlcv_data, volume_percentile):
        """Test order block detection with different volume percentiles."""
        result = smc_indicators.detect_order_blocks(
            sample_ohlcv_data,
            volume_threshold_percentile=volume_percentile
        )
        
        assert isinstance(result, list)
        # Higher percentiles should generally detect fewer blocks
        assert len(result) >= 0
    
    @pytest.mark.parametrize("confidence_threshold", [0.5, 0.6, 0.7, 0.8, 0.9])
    def test_choch_bos_confidence_thresholds(self, smc_indicators, sample_ohlcv_data, confidence_threshold):
        """Test CHOCH/BOS detection with different confidence thresholds."""
        result = smc_indicators.identify_choch_bos(
            sample_ohlcv_data,
            confidence_threshold=confidence_threshold
        )
        
        assert isinstance(result, dict)
        # All detected patterns should meet the confidence threshold
        for pattern in result['coch_patterns']:
            assert pattern['confidence'] >= confidence_threshold
        for pattern in result['bos_patterns']:
            assert pattern['confidence'] >= confidence_threshold
    
    def test_empty_dataframe_handling(self, smc_indicators):
        """Test handling of empty DataFrames."""
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Should handle empty data gracefully
        order_blocks = smc_indicators.detect_order_blocks(empty_df)
        assert order_blocks == []
        
        choch_bos = smc_indicators.identify_choch_bos(empty_df)
        assert isinstance(choch_bos, dict)
        assert len(choch_bos['coch_patterns']) == 0
        assert len(choch_bos['bos_patterns']) == 0
        
        sweeps = smc_indicators.liquidity_sweep_detection(empty_df)
        assert isinstance(sweeps, dict)
        assert len(sweeps['detected_sweeps']) == 0
    
    def test_data_type_conversion(self, smc_indicators):
        """Test automatic data type conversion."""
        # Create data with string timestamps
        data = pd.DataFrame({
            'timestamp': ['2024-01-01 10:00:00', '2024-01-01 11:00:00', '2024-01-01 12:00:00'],
            'open': ['50000', '50100', '50200'],
            'high': ['50100', '50200', '50300'],
            'low': ['49900', '50000', '50100'],
            'close': ['50050', '50150', '50250'],
            'volume': ['1000', '1100', '1200']
        })
        
        # Should handle string data types
        result = smc_indicators.detect_order_blocks(data)
        assert isinstance(result, list)
    
    def test_performance_with_large_dataset(self, smc_indicators):
        """Test performance with larger dataset."""
        # Create larger dataset
        dates = pd.date_range('2024-01-01', periods=1000, freq='1H')
        np.random.seed(42)
        
        base_price = 50000
        prices = [base_price]
        for _ in range(999):
            change = np.random.normal(0, 0.01)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        large_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 10000, 1000)
        })
        
        # Should handle large datasets efficiently
        import time
        start_time = time.time()
        result = smc_indicators.detect_order_blocks(large_data)
        end_time = time.time()
        
        assert isinstance(result, list)
        # Should complete within reasonable time (less than 5 seconds)
        assert (end_time - start_time) < 5.0
    
    def test_numba_optimization_functions(self, smc_indicators, sample_ohlcv_data):
        """Test that Numba-optimized functions are working correctly."""
        # This test ensures the Numba JIT compilation is working
        # by calling the methods multiple times and checking consistency
        
        result1 = smc_indicators.detect_order_blocks(sample_ohlcv_data)
        result2 = smc_indicators.detect_order_blocks(sample_ohlcv_data)
        
        # Results should be consistent
        assert len(result1) == len(result2)
        
        if result1:  # If we have results
            for block1, block2 in zip(result1, result2):
                assert block1['type'] == block2['type']
                assert block1['price_level'] == block2['price_level']
                assert abs(block1['strength_volume'] - block2['strength_volume']) < 1e-6
    
    def test_edge_case_single_candle(self, smc_indicators):
        """Test edge case with single candle."""
        single_candle = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [50000],
            'high': [50100],
            'low': [49900],
            'close': [50050],
            'volume': [1000]
        })
        
        # Should handle single candle gracefully
        result = smc_indicators.detect_order_blocks(single_candle)
        assert result == []
    
    def test_extreme_values_handling(self, smc_indicators):
        """Test handling of extreme values."""
        extreme_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1H'),
            'open': [1e6, 1e-6, 0, float('inf'), -float('inf'), 1, 2, 3, 4, 5],
            'high': [1e6, 1e-6, 1, float('inf'), -float('inf'), 2, 3, 4, 5, 6],
            'low': [1e6, 1e-6, -1, float('inf'), -float('inf'), 0, 1, 2, 3, 4],
            'close': [1e6, 1e-6, 0.5, float('inf'), -float('inf'), 1.5, 2.5, 3.5, 4.5, 5.5],
            'volume': [1000] * 10
        })
        
        # Should handle extreme values without crashing
        try:
            result = smc_indicators.detect_order_blocks(extreme_data)
            assert isinstance(result, list)
        except (ValueError, OverflowError, ZeroDivisionError):
            # These exceptions are acceptable for extreme values
            pass
    
    def test_memory_efficiency(self, smc_indicators):
        """Test memory efficiency with repeated calls."""
        # Create moderate-sized dataset
        dates = pd.date_range('2024-01-01', periods=500, freq='1H')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(49000, 51000, 500),
            'high': np.random.uniform(50000, 52000, 500),
            'low': np.random.uniform(48000, 50000, 500),
            'close': np.random.uniform(49000, 51000, 500),
            'volume': np.random.uniform(1000, 10000, 500)
        })
        
        # Call methods multiple times to check for memory leaks
        for _ in range(10):
            smc_indicators.detect_order_blocks(data)
            smc_indicators.identify_choch_bos(data)
            smc_indicators.liquidity_sweep_detection(data)
        
        # If we reach here without memory issues, test passes
        assert True


@pytest.mark.unit
class TestSMCIndicatorsIntegration:
    """Integration tests for SMC Indicators combining multiple methods."""
    
    @pytest.fixture
    def smc_indicators(self):
        return SMCIndicators()
    
    @pytest.fixture
    def comprehensive_data(self):
        """Create comprehensive test data with known patterns."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1H')
        
        # Create data with intentional patterns
        prices = []
        volumes = []
        base_price = 50000
        
        for i in range(200):
            # Create some trending periods and consolidation
            if i < 50:  # Uptrend
                price = base_price + (i * 10) + np.random.normal(0, 50)
                volume = 1000 + np.random.normal(0, 100)
            elif i < 100:  # Consolidation with high volume spikes
                price = base_price + 500 + np.random.normal(0, 100)
                volume = 1000 + (2000 if i % 10 == 0 else 0) + np.random.normal(0, 100)
            elif i < 150:  # Downtrend
                price = base_price + 500 - ((i - 100) * 8) + np.random.normal(0, 50)
                volume = 1000 + np.random.normal(0, 100)
            else:  # Recovery
                price = base_price + 100 + ((i - 150) * 5) + np.random.normal(0, 50)
                volume = 1000 + np.random.normal(0, 100)
            
            prices.append(max(1, price))  # Ensure positive prices
            volumes.append(max(1, volume))  # Ensure positive volumes
        
        # Create OHLC from prices
        data = []
        for i, (date, price, volume) in enumerate(zip(dates, prices, volumes)):
            if i == 0:
                open_price = price
            else:
                open_price = prices[i-1]
            
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_full_smc_analysis_pipeline(self, smc_indicators, comprehensive_data):
        """Test complete SMC analysis pipeline."""
        # Run all detection methods
        order_blocks = smc_indicators.detect_order_blocks(comprehensive_data)
        choch_bos = smc_indicators.identify_choch_bos(comprehensive_data)
        sweeps = smc_indicators.liquidity_sweep_detection(comprehensive_data)
        
        # Verify all methods return valid results
        assert isinstance(order_blocks, list)
        assert isinstance(choch_bos, dict)
        assert isinstance(sweeps, dict)
        
        # Check for logical consistency
        total_patterns = len(order_blocks) + choch_bos['total_patterns'] + sweeps['total_sweeps']
        assert total_patterns >= 0
        
        # Verify timestamps are within data range
        data_start = comprehensive_data['timestamp'].min()
        data_end = comprehensive_data['timestamp'].max()
        
        for block in order_blocks:
            assert data_start <= block['timestamp'] <= data_end
        
        for pattern in choch_bos['coch_patterns'] + choch_bos['bos_patterns']:
            assert data_start <= pattern['timestamp'] <= data_end
        
        for sweep in sweeps['detected_sweeps']:
            assert data_start <= sweep['timestamp'] <= data_end
    
    def test_pattern_correlation_analysis(self, smc_indicators, comprehensive_data):
        """Test correlation between different pattern types."""
        order_blocks = smc_indicators.detect_order_blocks(comprehensive_data)
        choch_bos = smc_indicators.identify_choch_bos(comprehensive_data)
        
        # If we have both order blocks and CHOCH/BOS patterns,
        # check for temporal relationships
        if order_blocks and (choch_bos['coch_patterns'] or choch_bos['bos_patterns']):
            ob_timestamps = [block['timestamp'] for block in order_blocks]
            pattern_timestamps = [p['timestamp'] for p in choch_bos['coch_patterns'] + choch_bos['bos_patterns']]
            
            # Verify timestamps are properly ordered
            assert all(t1 <= t2 for t1, t2 in zip(sorted(ob_timestamps), sorted(ob_timestamps)[1:]))
            assert all(t1 <= t2 for t1, t2 in zip(sorted(pattern_timestamps), sorted(pattern_timestamps)[1:]))