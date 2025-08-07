import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ..smc_detector.indicators import SMCIndicators


class TestSMCIndicators:
    """Test suite for SMC Indicators implementation."""
    
    @pytest.fixture
    def indicators(self):
        """Create SMCIndicators instance for testing."""
        return SMCIndicators()
    
    @pytest.fixture
    def sample_ohlc_data(self):
        """Create sample OHLCV data for testing."""
        # Create realistic market data with known patterns
        dates = pd.date_range(start='2023-10-01', periods=100, freq='1H')
        
        # Create price data with some volatility
        np.random.seed(42)  # For reproducible tests
        base_price = 50000
        returns = np.random.normal(0, 0.02, 100)  # 2% volatility
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Add some volatility within each candle
            volatility = price * 0.01  # 1% intra-candle volatility
            open_price = price
            high_price = price + np.random.uniform(0, volatility)
            low_price = price - np.random.uniform(0, volatility)
            close_price = price + np.random.uniform(-volatility/2, volatility/2)
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def coch_test_data(self):
        """Create test data with known COCH patterns."""
        dates = pd.date_range(start='2023-10-01', periods=50, freq='1H')
        
        # Create bearish COCH pattern: higher highs to lower highs
        data = []
        base_price = 50000
        
        # First swing high
        for i in range(10):
            data.append({
                'timestamp': dates[i],
                'open': base_price + i * 10,
                'high': base_price + i * 10 + 50,
                'low': base_price + i * 10 - 20,
                'close': base_price + i * 10 + 30,
                'volume': 500 + i * 10
            })
        
        # Second swing high (higher)
        for i in range(10, 20):
            data.append({
                'timestamp': dates[i],
                'open': base_price + 100 + i * 15,
                'high': base_price + 100 + i * 15 + 60,
                'low': base_price + 100 + i * 15 - 25,
                'close': base_price + 100 + i * 15 + 35,
                'volume': 600 + i * 15
            })
        
        # Third swing high (lower - COCH)
        for i in range(20, 30):
            data.append({
                'timestamp': dates[i],
                'open': base_price + 200 + i * 5,
                'high': base_price + 200 + i * 5 + 40,
                'low': base_price + 200 + i * 5 - 30,
                'close': base_price + 200 + i * 5 + 20,
                'volume': 800 + i * 20  # High volume for confirmation
            })
        
        # Continue with normal data
        for i in range(30, 50):
            data.append({
                'timestamp': dates[i],
                'open': base_price + 250 + i * 8,
                'high': base_price + 250 + i * 8 + 45,
                'low': base_price + 250 + i * 8 - 20,
                'close': base_price + 250 + i * 8 + 25,
                'volume': 400 + i * 10
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def liquidity_sweep_test_data(self):
        """Create test data with known liquidity sweep patterns."""
        dates = pd.date_range(start='2023-10-01', periods=40, freq='1H')
        
        # Create resistance level at 50500
        resistance_level = 50500
        data = []
        base_price = 50000
        
        # Build up to resistance
        for i in range(15):
            data.append({
                'timestamp': dates[i],
                'open': base_price + i * 30,
                'high': base_price + i * 30 + 40,
                'low': base_price + i * 30 - 20,
                'close': base_price + i * 30 + 20,
                'volume': 400 + i * 20
            })
        
        # Liquidity sweep above resistance
        data.append({
            'timestamp': dates[15],
            'open': resistance_level - 50,
            'high': resistance_level + 100,  # Sweep above resistance
            'low': resistance_level - 80,
            'close': resistance_level - 60,  # Close below resistance
            'volume': 1500  # High volume spike
        })
        
        # Reversal candle
        data.append({
            'timestamp': dates[16],
            'open': resistance_level - 60,
            'high': resistance_level - 40,
            'low': resistance_level - 120,
            'close': resistance_level - 100,  # Strong reversal
            'volume': 800
        })
        
        # Continue with normal data
        for i in range(17, 40):
            data.append({
                'timestamp': dates[i],
                'open': resistance_level - 100 + i * 5,
                'high': resistance_level - 100 + i * 5 + 30,
                'low': resistance_level - 100 + i * 5 - 15,
                'close': resistance_level - 100 + i * 5 + 15,
                'volume': 400 + i * 10
            })
        
        return pd.DataFrame(data)

    def test_identify_choch_bos_input_validation(self, indicators):
        """Test input validation for identify_choch_bos method."""
        # Test with missing columns
        invalid_data = pd.DataFrame({'timestamp': [datetime.now()], 'open': [100]})
        
        with pytest.raises(ValueError, match="Input DataFrame must contain columns"):
            indicators.identify_choch_bos(invalid_data)
    
    def test_identify_choch_bos_basic_functionality(self, indicators, sample_ohlc_data):
        """Test basic functionality of identify_choch_bos method."""
        result = indicators.identify_choch_bos(sample_ohlc_data)
        
        # Check return structure
        assert isinstance(result, dict)
        assert 'coch_patterns' in result
        assert 'bos_patterns' in result
        assert 'swing_highs' in result
        assert 'swing_lows' in result
        assert 'total_patterns' in result
        
        # Check data types
        assert isinstance(result['coch_patterns'], list)
        assert isinstance(result['bos_patterns'], list)
        assert isinstance(result['total_patterns'], int)
    
    def test_identify_choch_bos_coch_detection(self, indicators, coch_test_data):
        """Test COCH pattern detection with known patterns."""
        result = indicators.identify_choch_bos(coch_test_data, confidence_threshold=0.6)
        
        # Should detect at least one COCH pattern
        assert len(result['coch_patterns']) > 0
        
        # Check COCH pattern structure
        coch_pattern = result['coch_patterns'][0]
        assert 'timestamp' in coch_pattern
        assert 'type' in coch_pattern
        assert 'price_level' in coch_pattern
        assert 'confidence' in coch_pattern
        assert 'swing_points' in coch_pattern
        assert 'volume_confirmed' in coch_pattern
        assert 'momentum_strength' in coch_pattern
        
        # Check pattern type
        assert coch_pattern['type'] in ['bearish_coch', 'bullish_coch']
        assert coch_pattern['confidence'] >= 0.6
    
    def test_identify_choch_bos_bos_detection(self, indicators, sample_ohlc_data):
        """Test BOS pattern detection."""
        result = indicators.identify_choch_bos(sample_ohlc_data, confidence_threshold=0.5)
        
        # Check BOS pattern structure if any found
        if result['bos_patterns']:
            bos_pattern = result['bos_patterns'][0]
            assert 'timestamp' in bos_pattern
            assert 'type' in bos_pattern
            assert 'price_level' in bos_pattern
            assert 'confidence' in bos_pattern
            assert 'break_strength' in bos_pattern
            assert 'volume_confirmed' in bos_pattern
            assert 'momentum_confirmed' in bos_pattern
            
            # Check pattern type
            assert bos_pattern['type'] in ['bullish_bos', 'bearish_bos']
            assert bos_pattern['confidence'] >= 0.5
    
    def test_liquidity_sweep_detection_input_validation(self, indicators):
        """Test input validation for liquidity_sweep_detection method."""
        # Test with missing columns
        invalid_data = pd.DataFrame({'timestamp': [datetime.now()], 'open': [100]})
        
        with pytest.raises(ValueError, match="Input DataFrame must contain columns"):
            indicators.liquidity_sweep_detection(invalid_data)
    
    def test_liquidity_sweep_detection_basic_functionality(self, indicators, sample_ohlc_data):
        """Test basic functionality of liquidity_sweep_detection method."""
        result = indicators.liquidity_sweep_detection(sample_ohlc_data)
        
        # Check return structure
        assert isinstance(result, dict)
        assert 'liquidity_sweeps' in result
        assert 'total_sweeps' in result
        assert 'resistance_levels' in result
        assert 'support_levels' in result
        assert 'bullish_sweeps' in result
        assert 'bearish_sweeps' in result
        
        # Check data types
        assert isinstance(result['liquidity_sweeps'], list)
        assert isinstance(result['total_sweeps'], int)
        assert isinstance(result['resistance_levels'], list)
        assert isinstance(result['support_levels'], list)
        assert isinstance(result['bullish_sweeps'], int)
        assert isinstance(result['bearish_sweeps'], int)
    
    def test_liquidity_sweep_detection_sweep_detection(self, indicators, liquidity_sweep_test_data):
        """Test liquidity sweep detection with known patterns."""
        result = indicators.liquidity_sweep_detection(liquidity_sweep_test_data, confidence_threshold=0.6)
        
        # Should detect at least one liquidity sweep
        assert len(result['liquidity_sweeps']) > 0
        
        # Check sweep pattern structure
        sweep = result['liquidity_sweeps'][0]
        assert 'timestamp' in sweep
        assert 'type' in sweep
        assert 'price_level' in sweep
        assert 'sweep_high' in sweep
        assert 'sweep_low' in sweep
        assert 'confidence' in sweep
        assert 'volume_spike' in sweep
        assert 'reversal_confirmed' in sweep
        assert 'sweep_strength' in sweep
        assert 'reversal_strength' in sweep
        assert 'liquidity_pool_type' in sweep
        assert 'candle_index' in sweep
        assert 'volume_confirmed' in sweep
        
        # Check pattern type
        assert sweep['type'] in ['bullish_sweep', 'bearish_sweep']
        assert sweep['confidence'] >= 0.6
        assert sweep['liquidity_pool_type'] in ['resistance', 'support']
    
    def test_liquidity_sweep_detection_parameters(self, indicators, sample_ohlc_data):
        """Test liquidity sweep detection with different parameters."""
        # Test with different confidence thresholds
        result_low = indicators.liquidity_sweep_detection(sample_ohlc_data, confidence_threshold=0.3)
        result_high = indicators.liquidity_sweep_detection(sample_ohlc_data, confidence_threshold=0.8)
        
        # Lower threshold should detect more sweeps
        assert result_low['total_sweeps'] >= result_high['total_sweeps']
        
        # Test with different volume spike thresholds
        result_vol_low = indicators.liquidity_sweep_detection(sample_ohlc_data, volume_spike_threshold=1.5)
        result_vol_high = indicators.liquidity_sweep_detection(sample_ohlc_data, volume_spike_threshold=3.0)
        
        # Lower volume threshold should detect more sweeps
        assert result_vol_low['total_sweeps'] >= result_vol_high['total_sweeps']
    
    def test_integration_with_existing_methods(self, indicators, sample_ohlc_data):
        """Test integration between different SMC indicator methods."""
        # Test order blocks detection
        order_blocks = indicators.detect_order_blocks(sample_ohlc_data)
        
        # Test COCH/BOS detection
        coch_bos = indicators.identify_choch_bos(sample_ohlc_data)
        
        # Test liquidity sweep detection
        liquidity_sweeps = indicators.liquidity_sweep_detection(sample_ohlc_data)
        
        # All methods should work together without conflicts
        assert isinstance(order_blocks, list)
        assert isinstance(coch_bos, dict)
        assert isinstance(liquidity_sweeps, dict)
        
        # Check that all methods return consistent data structures
        assert 'timestamp' in coch_bos['coch_patterns'][0] if coch_bos['coch_patterns'] else True
        assert 'timestamp' in liquidity_sweeps['liquidity_sweeps'][0] if liquidity_sweeps['liquidity_sweeps'] else True
    
    def test_edge_cases(self, indicators):
        """Test edge cases and error conditions."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        result_coch = indicators.identify_choch_bos(empty_df)
        result_sweep = indicators.liquidity_sweep_detection(empty_df)
        
        assert result_coch['total_patterns'] == 0
        assert result_sweep['total_sweeps'] == 0
        
        # Test with single row DataFrame
        single_row = pd.DataFrame([{
            'timestamp': datetime.now(),
            'open': 100,
            'high': 105,
            'low': 95,
            'close': 102,
            'volume': 500
        }])
        
        result_coch = indicators.identify_choch_bos(single_row)
        result_sweep = indicators.liquidity_sweep_detection(single_row)
        
        assert result_coch['total_patterns'] == 0  # Need at least 3 swing points
        assert result_sweep['total_sweeps'] == 0  # Need multiple candles for sweep detection
    
    def test_performance_benchmark(self, indicators, sample_ohlc_data):
        """Test performance of SMC indicator methods."""
        import time
        
        # Benchmark COCH/BOS detection
        start_time = time.time()
        result_coch = indicators.identify_choch_bos(sample_ohlc_data)
        coch_time = time.time() - start_time
        
        # Benchmark liquidity sweep detection
        start_time = time.time()
        result_sweep = indicators.liquidity_sweep_detection(sample_ohlc_data)
        sweep_time = time.time() - start_time
        
        # Performance should be reasonable for real-time processing
        assert coch_time < 1.0  # Should complete within 1 second
        assert sweep_time < 1.0  # Should complete within 1 second
        
        # Both methods should return results
        assert isinstance(result_coch, dict)
        assert isinstance(result_sweep, dict)


if __name__ == "__main__":
    pytest.main([__file__])

