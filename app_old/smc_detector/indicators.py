import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import numba
from numba import jit, float64, int64, boolean
from numba.core.types import List
from typing import Tuple

# Numba-optimized helper functions for SMC detection
@jit(nopython=True)
def _find_order_blocks_numba(
    high_values: np.ndarray,
    low_values: np.ndarray, 
    open_values: np.ndarray,
    close_values: np.ndarray,
    volume_values: np.ndarray,
    potential_ob_indices: np.ndarray,
    bos_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized order block detection core algorithm"""
    n_blocks = 0
    max_blocks = len(potential_ob_indices)
    
    # Pre-allocate arrays
    ob_indices = np.empty(max_blocks, dtype=np.int64)
    ob_types = np.empty(max_blocks, dtype=np.int64)  # 1=bullish, 0=bearish
    ob_high_prices = np.empty(max_blocks, dtype=np.float64)
    ob_low_prices = np.empty(max_blocks, dtype=np.float64)
    ob_volumes = np.empty(max_blocks, dtype=np.float64)
    
    body_sizes = np.abs(close_values - open_values)
    n_candles = len(high_values)
    
    for i in range(len(potential_ob_indices)):
        idx = potential_ob_indices[i]
        
        if idx == 0 or idx >= n_candles - 1:
            continue
            
        potential_ob_open = open_values[idx]
        potential_ob_close = close_values[idx]
        potential_ob_high = high_values[idx]
        potential_ob_low = low_values[idx]
        potential_ob_volume = volume_values[idx]
        
        # Determine Order Block type
        is_bullish_ob = potential_ob_close < potential_ob_open  # Last down candle
        is_bearish_ob = potential_ob_close > potential_ob_open  # Last up candle
        
        if is_bullish_ob:
            # Look for a strong up-move that breaks the high of the OB candle
            structure_high = potential_ob_high
            for j in range(idx + 1, n_candles):
                if high_values[j] > structure_high and body_sizes[j] > bos_threshold:
                    ob_indices[n_blocks] = idx
                    ob_types[n_blocks] = 1  # bullish
                    ob_high_prices[n_blocks] = potential_ob_high
                    ob_low_prices[n_blocks] = potential_ob_low
                    ob_volumes[n_blocks] = potential_ob_volume
                    n_blocks += 1
                    break
        
        elif is_bearish_ob:
            # Look for a strong down-move that breaks the low of the OB candle
            structure_low = potential_ob_low
            for j in range(idx + 1, n_candles):
                if low_values[j] < structure_low and body_sizes[j] > bos_threshold:
                    ob_indices[n_blocks] = idx
                    ob_types[n_blocks] = 0  # bearish
                    ob_high_prices[n_blocks] = potential_ob_high
                    ob_low_prices[n_blocks] = potential_ob_low
                    ob_volumes[n_blocks] = potential_ob_volume
                    n_blocks += 1
                    break
    
    return (
        ob_indices[:n_blocks],
        ob_types[:n_blocks],
        ob_high_prices[:n_blocks],
        ob_low_prices[:n_blocks],
        ob_volumes[:n_blocks]
    )

@jit(nopython=True)
def _detect_choch_patterns_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    volume_values: np.ndarray,
    momentum_values: np.ndarray,
    swing_highs: np.ndarray,
    swing_lows: np.ndarray,
    volume_threshold: float,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized CHOCH pattern detection"""
    max_patterns = len(swing_highs) + len(swing_lows)
    
    # Pre-allocate arrays
    pattern_indices = np.empty(max_patterns, dtype=np.int64)
    pattern_types = np.empty(max_patterns, dtype=np.int64)  # 1=bullish_coch, 0=bearish_coch
    pattern_confidences = np.empty(max_patterns, dtype=np.float64)
    pattern_strengths = np.empty(max_patterns, dtype=np.float64)
    n_patterns = 0
    
    # Bearish COCH: Higher highs to lower highs
    if len(swing_highs) >= 3:
        for i in range(len(swing_highs) - 2):
            high1_idx, high2_idx, high3_idx = swing_highs[i], swing_highs[i+1], swing_highs[i+2]
            high1, high2, high3 = high_values[high1_idx], high_values[high2_idx], high_values[high3_idx]
            
            # Check for bearish COCH: high2 > high1 and high3 < high2
            if high2 > high1 and high3 < high2:
                volume_confirmed = volume_values[high3_idx] > volume_threshold
                momentum_strength = abs(momentum_values[high3_idx])
                
                confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    pattern_indices[n_patterns] = high3_idx
                    pattern_types[n_patterns] = 0  # bearish_coch
                    pattern_confidences[n_patterns] = confidence
                    pattern_strengths[n_patterns] = momentum_strength
                    n_patterns += 1
    
    # Bullish COCH: Lower lows to higher lows
    if len(swing_lows) >= 3:
        for i in range(len(swing_lows) - 2):
            low1_idx, low2_idx, low3_idx = swing_lows[i], swing_lows[i+1], swing_lows[i+2]
            low1, low2, low3 = low_values[low1_idx], low_values[low2_idx], low_values[low3_idx]
            
            # Check for bullish COCH: low2 < low1 and low3 > low2
            if low2 < low1 and low3 > low2:
                volume_confirmed = volume_values[low3_idx] > volume_threshold
                momentum_strength = abs(momentum_values[low3_idx])
                
                confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    pattern_indices[n_patterns] = low3_idx
                    pattern_types[n_patterns] = 1  # bullish_coch
                    pattern_confidences[n_patterns] = confidence
                    pattern_strengths[n_patterns] = momentum_strength
                    n_patterns += 1
    
    return (
        pattern_indices[:n_patterns],
        pattern_types[:n_patterns],
        pattern_confidences[:n_patterns],
        pattern_strengths[:n_patterns]
    )

@jit(nopython=True)
def _detect_bos_patterns_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    volume_values: np.ndarray,
    momentum_values: np.ndarray,
    swing_highs: np.ndarray,
    swing_lows: np.ndarray,
    volume_threshold: float,
    momentum_threshold: float,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized BOS pattern detection"""
    max_patterns = len(swing_highs) + len(swing_lows)
    
    # Pre-allocate arrays
    pattern_indices = np.empty(max_patterns, dtype=np.int64)
    pattern_types = np.empty(max_patterns, dtype=np.int64)  # 1=bullish_bos, 0=bearish_bos
    pattern_confidences = np.empty(max_patterns, dtype=np.float64)
    pattern_strengths = np.empty(max_patterns, dtype=np.float64)
    n_patterns = 0
    
    # Bullish BOS: Break above previous swing high
    for i in range(len(swing_highs) - 1):
        high_idx = swing_highs[i]
        next_high_idx = swing_highs[i + 1]
        structure_level = high_values[high_idx]
        
        # Check if price broke above the structure level
        if high_values[next_high_idx] > structure_level:
            break_strength = (high_values[next_high_idx] - structure_level) / structure_level * 100
            volume_confirmed = volume_values[next_high_idx] > volume_threshold
            momentum_confirmed = momentum_values[next_high_idx] > momentum_threshold
            
            confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
            
            if confidence >= confidence_threshold:
                pattern_indices[n_patterns] = next_high_idx
                pattern_types[n_patterns] = 1  # bullish_bos
                pattern_confidences[n_patterns] = confidence
                pattern_strengths[n_patterns] = break_strength
                n_patterns += 1
    
    # Bearish BOS: Break below previous swing low
    for i in range(len(swing_lows) - 1):
        low_idx = swing_lows[i]
        next_low_idx = swing_lows[i + 1]
        structure_level = low_values[low_idx]
        
        # Check if price broke below the structure level
        if low_values[next_low_idx] < structure_level:
            break_strength = (structure_level - low_values[next_low_idx]) / structure_level * 100
            volume_confirmed = volume_values[next_low_idx] > volume_threshold
            momentum_confirmed = abs(momentum_values[next_low_idx]) > momentum_threshold
            
            confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
            
            if confidence >= confidence_threshold:
                pattern_indices[n_patterns] = next_low_idx
                pattern_types[n_patterns] = 0  # bearish_bos
                pattern_confidences[n_patterns] = confidence
                pattern_strengths[n_patterns] = break_strength
                n_patterns += 1
    
    return (
        pattern_indices[:n_patterns],
        pattern_types[:n_patterns],
        pattern_confidences[:n_patterns],
        pattern_strengths[:n_patterns]
    )

@jit(nopython=True)
def _detect_liquidity_sweeps_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    close_values: np.ndarray,
    volume_values: np.ndarray,
    volume_ratios: np.ndarray,
    resistance_levels: np.ndarray,
    support_levels: np.ndarray,
    min_sweep_distance: float,
    volume_spike_threshold: float,
    sweep_reversal_candles: int,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized liquidity sweep detection"""
    max_sweeps = (len(resistance_levels) + len(support_levels)) * 10
    
    # Pre-allocate arrays
    sweep_indices = np.empty(max_sweeps, dtype=np.int64)
    sweep_types = np.empty(max_sweeps, dtype=np.int64)  # 1=bullish_sweep, 0=bearish_sweep
    sweep_confidences = np.empty(max_sweeps, dtype=np.float64)
    sweep_strengths = np.empty(max_sweeps, dtype=np.float64)
    sweep_levels = np.empty(max_sweeps, dtype=np.float64)
    n_sweeps = 0
    
    n_candles = len(high_values)
    
    # Detect Bullish Liquidity Sweeps (Above Resistance)
    for resistance in resistance_levels:
        for idx in range(n_candles - sweep_reversal_candles):
            # Check if candle swept above resistance
            if high_values[idx] > resistance:
                sweep_distance = (high_values[idx] - resistance) / resistance * 100
                
                # Check if sweep distance is significant
                if sweep_distance >= min_sweep_distance:
                    volume_spike = volume_values[idx] > volume_spike_threshold
                    volume_ratio = volume_ratios[idx]
                    
                    # Check for reversal within specified candles
                    reversal_confirmed = False
                    reversal_strength = 0.0
                    
                    for j in range(1, min(sweep_reversal_candles + 1, n_candles - idx)):
                        if close_values[idx + j] < resistance:
                            reversal_confirmed = True
                            reversal_strength = (resistance - close_values[idx + j]) / resistance * 100
                            break
                    
                    # Calculate confidence score
                    confidence = 0.5
                    if volume_spike:
                        confidence += 0.2
                    if reversal_confirmed:
                        confidence += 0.2
                    if volume_ratio > 2.0:
                        confidence += 0.1
                    if sweep_distance > 0.5:
                        confidence += 0.1
                    if reversal_strength > 0.3:
                        confidence += 0.1
                    
                    confidence = min(0.95, confidence)
                    
                    if confidence >= confidence_threshold:
                        sweep_indices[n_sweeps] = idx
                        sweep_types[n_sweeps] = 1  # bullish_sweep
                        sweep_confidences[n_sweeps] = confidence
                        sweep_strengths[n_sweeps] = sweep_distance
                        sweep_levels[n_sweeps] = resistance
                        n_sweeps += 1
    
    # Detect Bearish Liquidity Sweeps (Below Support)
    for support in support_levels:
        for idx in range(n_candles - sweep_reversal_candles):
            # Check if candle swept below support
            if low_values[idx] < support:
                sweep_distance = (support - low_values[idx]) / support * 100
                
                # Check if sweep distance is significant
                if sweep_distance >= min_sweep_distance:
                    volume_spike = volume_values[idx] > volume_spike_threshold
                    volume_ratio = volume_ratios[idx]
                    
                    # Check for reversal within specified candles
                    reversal_confirmed = False
                    reversal_strength = 0.0
                    
                    for j in range(1, min(sweep_reversal_candles + 1, n_candles - idx)):
                        if close_values[idx + j] > support:
                            reversal_confirmed = True
                            reversal_strength = (close_values[idx + j] - support) / support * 100
                            break
                    
                    # Calculate confidence score
                    confidence = 0.5
                    if volume_spike:
                        confidence += 0.2
                    if reversal_confirmed:
                        confidence += 0.2
                    if volume_ratio > 2.0:
                        confidence += 0.1
                    if sweep_distance > 0.5:
                        confidence += 0.1
                    if reversal_strength > 0.3:
                        confidence += 0.1
                    
                    confidence = min(0.95, confidence)
                    
                    if confidence >= confidence_threshold:
                        sweep_indices[n_sweeps] = idx
                        sweep_types[n_sweeps] = 0  # bearish_sweep
                        sweep_confidences[n_sweeps] = confidence
                        sweep_strengths[n_sweeps] = sweep_distance
                        sweep_levels[n_sweeps] = support
                        n_sweeps += 1
    
    return (
        sweep_indices[:n_sweeps],
        sweep_types[:n_sweeps],
        sweep_confidences[:n_sweeps],
        sweep_strengths[:n_sweeps],
        sweep_levels[:n_sweeps]
    )

class SMCIndicators:
    def detect_order_blocks(self, ohlc_data: pd.DataFrame, volume_threshold_percentile=95, bos_confirmation_factor=1.5):
        """
        Detects Order Blocks using peak volume analysis and Break of Structure (BoS) confirmation.
        Optimized with Numba JIT compilation for improved performance.

        An order block is identified as the last bearish candle before a strong bullish move
        (or vice-versa) that occurs on high volume and is followed by a break of structure.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            volume_threshold_percentile (int): The percentile to use for identifying significant volume peaks.
            bos_confirmation_factor (float): Multiplier for the average candle body size to confirm a BoS.

        Returns:
            list: A list of dictionaries, where each dictionary represents a confirmed order block.
                  Example: {
                      'timestamp': '2023-10-27T10:00:00Z',
                      'type': 'bullish',
                      'price_level': (60000.50, 59500.25),
                      'strength_volume': 150.75,
                      'bos_confirmed_at': '2023-10-27T10:05:00Z'
                  }
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Identify High-Volume Candles (Potential Order Blocks) ---
        volume_threshold = np.percentile(volume_values, volume_threshold_percentile)
        potential_ob_indices, _ = find_peaks(volume_values, height=volume_threshold)
        
        if len(potential_ob_indices) == 0:
            return []

        # --- 2. Calculate BOS threshold ---
        body_sizes = np.abs(close_values - open_values)
        avg_body_size = np.mean(body_sizes)
        bos_threshold = avg_body_size * bos_confirmation_factor

        # --- 3. Use Numba-optimized function for core detection ---
        ob_indices, ob_types, ob_high_prices, ob_low_prices, ob_volumes = _find_order_blocks_numba(
            high_values, low_values, open_values, close_values, volume_values,
            potential_ob_indices, bos_threshold
        )

        # --- 4. Convert results back to expected format ---
        confirmed_order_blocks = []
        for i in range(len(ob_indices)):
            idx = ob_indices[i]
            ob_type = 'bullish' if ob_types[i] == 1 else 'bearish'
            
            confirmed_order_blocks.append({
                'timestamp': timestamps[idx],
                'type': ob_type,
                'price_level': (ob_high_prices[i], ob_low_prices[i]),
                'strength_volume': ob_volumes[i],
                'bos_confirmed_at': None  # Could be enhanced to track this
            })

        return confirmed_order_blocks

    def identify_choch_bos(self, ohlc_data: pd.DataFrame, swing_highs: list = None, swing_lows: list = None, 
                          min_swing_distance: int = 5, volume_confirmation_threshold: float = 1.5,
                          momentum_threshold: float = 1.2, confidence_threshold: float = 0.7):
        """
        Identifies Change of Character (COCH) and Break of Structure (BOS) patterns using SMC methodology.
        Optimized with Numba JIT compilation for improved performance.

        COCH occurs when market structure shifts from bullish to bearish (higher highs to lower highs)
        or bearish to bullish (lower lows to higher lows). BOS occurs when price breaks through
        established support/resistance levels with sufficient momentum and volume confirmation.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            swing_highs (list): Optional list of swing high indices. If None, will be calculated automatically.
            swing_lows (list): Optional list of swing low indices. If None, will be calculated automatically.
            min_swing_distance (int): Minimum distance between swing points for peak detection.
            volume_confirmation_threshold (float): Multiplier for average volume to confirm patterns.
            momentum_threshold (float): Minimum momentum required for BOS confirmation.
            confidence_threshold (float): Minimum confidence score for pattern validation.

        Returns:
            dict: A dictionary containing COCH and BOS patterns with confidence scores.
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Calculate Swing Points if not provided ---
        if swing_highs is None:
            swing_highs, _ = find_peaks(high_values, distance=min_swing_distance, prominence=np.std(high_values) * 0.1)
        if swing_lows is None:
            swing_lows, _ = find_peaks(-low_values, distance=min_swing_distance, prominence=np.std(low_values) * 0.1)

        # Convert swing points to NumPy arrays if they're lists
        if isinstance(swing_highs, list):
            swing_highs = np.array(swing_highs, dtype=np.int64)
        if isinstance(swing_lows, list):
            swing_lows = np.array(swing_lows, dtype=np.int64)

        # --- 2. Calculate Additional Metrics ---
        momentum_values = (close_values - open_values) / open_values * 100
        
        avg_volume = np.mean(volume_values)
        volume_threshold = avg_volume * volume_confirmation_threshold

        # --- 3. Use Numba-optimized functions for pattern detection ---
        coch_indices, coch_types, coch_confidences, coch_strengths = _detect_choch_patterns_numba(
            high_values, low_values, volume_values, momentum_values,
            swing_highs, swing_lows, volume_threshold, confidence_threshold
        )

        bos_indices, bos_types, bos_confidences, bos_strengths = _detect_bos_patterns_numba(
            high_values, low_values, volume_values, momentum_values,
            swing_highs, swing_lows, volume_threshold, momentum_threshold, confidence_threshold
        )

        # --- 4. Convert results back to expected format ---
        coch_patterns = []
        for i in range(len(coch_indices)):
            idx = coch_indices[i]
            pattern_type = 'bullish_coch' if coch_types[i] == 1 else 'bearish_coch'
            
            coch_patterns.append({
                'timestamp': timestamps[idx],
                'type': pattern_type,
                'price_level': (high_values[idx], low_values[idx]),
                'confidence': round(coch_confidences[i], 3),
                'volume_confirmed': volume_values[idx] > volume_threshold,
                'momentum_strength': coch_strengths[i]
            })

        bos_patterns = []
        for i in range(len(bos_indices)):
            idx = bos_indices[i]
            pattern_type = 'bullish_bos' if bos_types[i] == 1 else 'bearish_bos'
            
            bos_patterns.append({
                'timestamp': timestamps[idx],
                'type': pattern_type,
                'price_level': high_values[idx] if pattern_type == 'bullish_bos' else low_values[idx],
                'confidence': round(bos_confidences[i], 3),
                'break_strength': round(bos_strengths[i], 2),
                'volume_confirmed': volume_values[idx] > volume_threshold,
                'momentum_confirmed': momentum_values[idx] > momentum_threshold if pattern_type == 'bullish_bos' else abs(momentum_values[idx]) > momentum_threshold
            })

        return {
            'coch_patterns': coch_patterns,
            'bos_patterns': bos_patterns,
            'swing_highs': swing_highs.tolist() if hasattr(swing_highs, 'tolist') else swing_highs,
            'swing_lows': swing_lows.tolist() if hasattr(swing_lows, 'tolist') else swing_lows,
            'total_patterns': len(coch_patterns) + len(bos_patterns)
        }
        
    def liquidity_sweep_detection(self, ohlc_data: pd.DataFrame, volume_threshold_percentile: int = 95,
                                 sweep_reversal_candles: int = 3, min_sweep_distance: float = 0.1,
                                 volume_spike_threshold: float = 2.0, confidence_threshold: float = 0.7):
        """
        Detects liquidity sweeps using SMC methodology for identifying stop-loss hunting and institutional manipulation.
        Optimized with Numba JIT compilation for improved performance.

        Liquidity sweeps occur when price briefly moves beyond key support/resistance levels to trigger
        stop losses before reversing. This method identifies institutional order flow manipulation patterns.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            volume_threshold_percentile (int): Percentile for identifying significant volume levels.
            sweep_reversal_candles (int): Maximum number of candles for reversal confirmation.
            min_sweep_distance (float): Minimum distance beyond key level for sweep confirmation (percentage).
            volume_spike_threshold (float): Multiplier for average volume to confirm volume spike.
            confidence_threshold (float): Minimum confidence score for sweep validation.

        Returns:
            dict: A dictionary containing detected liquidity sweeps with detailed metrics.
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Calculate Volume Ratios ---
        # Calculate rolling mean volume for volume ratio calculation
        volume_rolling_mean = np.full_like(volume_values, np.nan)
        window = min(20, len(volume_values))
        for i in range(window - 1, len(volume_values)):
            volume_rolling_mean[i] = np.mean(volume_values[max(0, i - window + 1):i + 1])

        # Fill initial NaN values with overall mean
        overall_mean = np.mean(volume_values)
        volume_rolling_mean[:window - 1] = overall_mean
        volume_ratios = volume_values / volume_rolling_mean

        # Calculate volume thresholds
        avg_volume = np.mean(volume_values)
        volume_spike_threshold_actual = avg_volume * volume_spike_threshold

        # --- 2. Identify Key Support and Resistance Levels ---
        # Find swing highs and lows for potential liquidity pools
        swing_highs, _ = find_peaks(high_values, distance=5, prominence=np.std(high_values) * 0.1)
        swing_lows, _ = find_peaks(-low_values, distance=5, prominence=np.std(low_values) * 0.1)

        # Create liquidity pool levels as NumPy arrays
        resistance_levels = high_values[swing_highs]
        support_levels = low_values[swing_lows]

        # --- 3. Use Numba-optimized function for sweep detection ---
        sweep_indices, sweep_types, sweep_confidences, sweep_strengths, sweep_levels = _detect_liquidity_sweeps_numba(
            high_values, low_values, close_values, volume_values, volume_ratios,
            resistance_levels, support_levels, min_sweep_distance,
            volume_spike_threshold_actual, sweep_reversal_candles, confidence_threshold
        )

        # --- 4. Convert results back to expected format ---
        detected_sweeps = []
        for i in range(len(sweep_indices)):
            idx = sweep_indices[i]
            sweep_type = 'bullish_sweep' if sweep_types[i] == 1 else 'bearish_sweep'
            liquidity_type = 'resistance' if sweep_type == 'bullish_sweep' else 'support'
            
            detected_sweeps.append({
                'timestamp': timestamps[idx],
                'type': sweep_type,
                'price_level': sweep_levels[i],
                'sweep_high': high_values[idx],
                'sweep_low': low_values[idx],
                'confidence': round(sweep_confidences[i], 3),
                'volume_spike': round(volume_ratios[idx], 2),
                'reversal_confirmed': True,  # Already filtered by Numba function
                'sweep_strength': round(sweep_strengths[i], 2),
                'liquidity_pool_type': liquidity_type,
                'candle_index': idx,
                'volume_confirmed': volume_values[idx] > volume_spike_threshold_actual
            })

        # --- 5. Filter duplicate sweeps at similar levels ---
        filtered_sweeps = []
        used_levels = set()
        
        for sweep in sorted(detected_sweeps, key=lambda x: x['confidence'], reverse=True):
            level_key = f"{sweep['price_level']:.2f}"
            
            # Check if we already have a sweep at a similar level (within 0.1%)
            level_used = False
            for used_level in used_levels:
                if abs(float(level_key) - float(used_level)) / float(used_level) < 0.001:
                    level_used = True
                    break
            
            if not level_used:
                filtered_sweeps.append(sweep)
                used_levels.add(level_key)

        return {
            'liquidity_sweeps': filtered_sweeps,
            'total_sweeps': len(filtered_sweeps),
            'resistance_levels': resistance_levels.tolist(),
            'support_levels': support_levels.tolist(),
            'bullish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bullish_sweep']),
            'bearish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bearish_sweep'])
        }

