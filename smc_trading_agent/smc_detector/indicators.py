import pandas as pd
import numpy as np
from scipy.signal import find_peaks

class SMCIndicators:
    def detect_order_blocks(self, ohlc_data: pd.DataFrame, volume_threshold_percentile=95, bos_confirmation_factor=1.5):
        """
        Detects Order Blocks using peak volume analysis and Break of Structure (BoS) confirmation.

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
                      'price_level': 60000.50,
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

        confirmed_order_blocks = []

        # --- 1. Identify High-Volume Candles (Potential Order Blocks) ---
        volume_threshold = np.percentile(df['volume'], volume_threshold_percentile)
        potential_ob_indices, _ = find_peaks(df['volume'], height=volume_threshold)
        
        if not potential_ob_indices.any():
            return []

        # --- 2. Confirm with Break of Structure (BoS) ---
        df['body_size'] = abs(df['close'] - df['open'])
        avg_body_size = df['body_size'].mean()
        bos_threshold = avg_body_size * bos_confirmation_factor

        for idx in potential_ob_indices:
            if idx == 0 or idx >= len(df) - 1:
                continue

            potential_ob = df.iloc[idx]
            
            # Determine Order Block type
            is_bullish_ob = potential_ob['close'] < potential_ob['open'] # Last down candle
            is_bearish_ob = potential_ob['close'] > potential_ob['open'] # Last up candle

            # Look for Break of Structure after the OB
            subsequent_candles = df.iloc[idx + 1:]
            
            if is_bullish_ob:
                # Look for a strong up-move that breaks the high of the OB candle
                structure_high = potential_ob['high']
                for i, candle in subsequent_candles.iterrows():
                    if candle['high'] > structure_high and candle['body_size'] > bos_threshold:
                        confirmed_order_blocks.append({
                            'timestamp': potential_ob['timestamp'],
                            'type': 'bullish',
                            'price_level': (potential_ob['high'], potential_ob['low']), # OB is the full candle range
                            'strength_volume': potential_ob['volume'],
                            'bos_confirmed_at': candle['timestamp']
                        })
                        break # Move to next potential OB
            
            elif is_bearish_ob:
                # Look for a strong down-move that breaks the low of the OB candle
                structure_low = potential_ob['low']
                for i, candle in subsequent_candles.iterrows():
                    if candle['low'] < structure_low and candle['body_size'] > bos_threshold:
                        confirmed_order_blocks.append({
                            'timestamp': potential_ob['timestamp'],
                            'type': 'bearish',
                            'price_level': (potential_ob['high'], potential_ob['low']),
                            'strength_volume': potential_ob['volume'],
                            'bos_confirmed_at': candle['timestamp']
                        })
                        break # Move to next potential OB

        return confirmed_order_blocks

    def identify_choch_bos(self, ohlc_data: pd.DataFrame, swing_highs: list = None, swing_lows: list = None, 
                          min_swing_distance: int = 5, volume_confirmation_threshold: float = 1.5,
                          momentum_threshold: float = 1.2, confidence_threshold: float = 0.7):
        """
        Identifies Change of Character (COCH) and Break of Structure (BOS) patterns using SMC methodology.

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
                  Example: {
                      'coch_patterns': [
                          {
                              'timestamp': '2023-10-27T10:00:00Z',
                              'type': 'bearish_coch',
                              'price_level': (60000.50, 59500.25),
                              'confidence': 0.85,
                              'swing_points': [(100, 60000.50), (150, 59800.25)],
                              'volume_confirmed': True
                          }
                      ],
                      'bos_patterns': [
                          {
                              'timestamp': '2023-10-27T10:05:00Z',
                              'type': 'bullish_bos',
                              'price_level': 60500.75,
                              'confidence': 0.92,
                              'break_strength': 1.8,
                              'volume_confirmed': True
                          }
                      ]
                  }
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # --- 1. Calculate Swing Points if not provided ---
        if swing_highs is None:
            swing_highs, _ = find_peaks(df['high'], distance=min_swing_distance, prominence=df['high'].std() * 0.1)
        if swing_lows is None:
            swing_lows, _ = find_peaks(-df['low'], distance=min_swing_distance, prominence=df['low'].std() * 0.1)

        # --- 2. Calculate Additional Metrics ---
        df['body_size'] = abs(df['close'] - df['open'])
        df['momentum'] = (df['close'] - df['open']) / df['open'] * 100
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        avg_volume = df['volume'].mean()
        volume_threshold = avg_volume * volume_confirmation_threshold

        # --- 3. Detect Change of Character (COCH) Patterns ---
        coch_patterns = []
        
        # Bearish COCH: Higher highs to lower highs
        if len(swing_highs) >= 3:
            for i in range(len(swing_highs) - 2):
                high1_idx, high2_idx, high3_idx = swing_highs[i], swing_highs[i+1], swing_highs[i+2]
                high1, high2, high3 = df.iloc[high1_idx]['high'], df.iloc[high2_idx]['high'], df.iloc[high3_idx]['high']
                
                # Check for bearish COCH: high2 > high1 and high3 < high2
                if high2 > high1 and high3 < high2:
                    # Calculate confidence based on volume and momentum
                    volume_confirmed = df.iloc[high3_idx]['volume'] > volume_threshold
                    momentum_strength = abs(df.iloc[high3_idx]['momentum'])
                    
                    confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                    
                    if confidence >= confidence_threshold:
                        coch_patterns.append({
                            'timestamp': df.iloc[high3_idx]['timestamp'],
                            'type': 'bearish_coch',
                            'price_level': (high2, high3),
                            'confidence': round(confidence, 3),
                            'swing_points': [(high1_idx, high1), (high2_idx, high2), (high3_idx, high3)],
                            'volume_confirmed': volume_confirmed,
                            'momentum_strength': momentum_strength
                        })

        # Bullish COCH: Lower lows to higher lows
        if len(swing_lows) >= 3:
            for i in range(len(swing_lows) - 2):
                low1_idx, low2_idx, low3_idx = swing_lows[i], swing_lows[i+1], swing_lows[i+2]
                low1, low2, low3 = df.iloc[low1_idx]['low'], df.iloc[low2_idx]['low'], df.iloc[low3_idx]['low']
                
                # Check for bullish COCH: low2 < low1 and low3 > low2
                if low2 < low1 and low3 > low2:
                    # Calculate confidence based on volume and momentum
                    volume_confirmed = df.iloc[low3_idx]['volume'] > volume_threshold
                    momentum_strength = abs(df.iloc[low3_idx]['momentum'])
                    
                    confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                    
                    if confidence >= confidence_threshold:
                        coch_patterns.append({
                            'timestamp': df.iloc[low3_idx]['timestamp'],
                            'type': 'bullish_coch',
                            'price_level': (low2, low3),
                            'confidence': round(confidence, 3),
                            'swing_points': [(low1_idx, low1), (low2_idx, low2), (low3_idx, low3)],
                            'volume_confirmed': volume_confirmed,
                            'momentum_strength': momentum_strength
                        })

        # --- 4. Detect Break of Structure (BOS) Patterns ---
        bos_patterns = []
        
        # Bullish BOS: Break above previous swing high
        for i, high_idx in enumerate(swing_highs[:-1]):
            structure_level = df.iloc[high_idx]['high']
            next_high_idx = swing_highs[i + 1]
            
            # Check if price broke above the structure level
            if df.iloc[next_high_idx]['high'] > structure_level:
                # Calculate break strength and confirmation
                break_strength = (df.iloc[next_high_idx]['high'] - structure_level) / structure_level * 100
                volume_confirmed = df.iloc[next_high_idx]['volume'] > volume_threshold
                momentum_confirmed = df.iloc[next_high_idx]['momentum'] > momentum_threshold
                
                confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    bos_patterns.append({
                        'timestamp': df.iloc[next_high_idx]['timestamp'],
                        'type': 'bullish_bos',
                        'price_level': structure_level,
                        'confidence': round(confidence, 3),
                        'break_strength': round(break_strength, 2),
                        'volume_confirmed': volume_confirmed,
                        'momentum_confirmed': momentum_confirmed,
                        'structure_high_idx': high_idx,
                        'break_high_idx': next_high_idx
                    })

        # Bearish BOS: Break below previous swing low
        for i, low_idx in enumerate(swing_lows[:-1]):
            structure_level = df.iloc[low_idx]['low']
            next_low_idx = swing_lows[i + 1]
            
            # Check if price broke below the structure level
            if df.iloc[next_low_idx]['low'] < structure_level:
                # Calculate break strength and confirmation
                break_strength = (structure_level - df.iloc[next_low_idx]['low']) / structure_level * 100
                volume_confirmed = df.iloc[next_low_idx]['volume'] > volume_threshold
                momentum_confirmed = abs(df.iloc[next_low_idx]['momentum']) > momentum_threshold
                
                confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    bos_patterns.append({
                        'timestamp': df.iloc[next_low_idx]['timestamp'],
                        'type': 'bearish_bos',
                        'price_level': structure_level,
                        'confidence': round(confidence, 3),
                        'break_strength': round(break_strength, 2),
                        'volume_confirmed': volume_confirmed,
                        'momentum_confirmed': momentum_confirmed,
                        'structure_low_idx': low_idx,
                        'break_low_idx': next_low_idx
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
                  Example: {
                      'liquidity_sweeps': [
                          {
                              'timestamp': '2023-10-27T10:00:00Z',
                              'type': 'bullish_sweep',
                              'price_level': 60500.75,
                              'sweep_high': 60650.25,
                              'sweep_low': 60400.50,
                              'confidence': 0.88,
                              'volume_spike': 2.5,
                              'reversal_confirmed': True,
                              'sweep_strength': 1.8,
                              'liquidity_pool_type': 'resistance'
                          }
                      ],
                      'total_sweeps': 5,
                      'bullish_sweeps': 3,
                      'bearish_sweeps': 2
                  }
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # --- 1. Calculate Additional Metrics ---
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        # Calculate volume thresholds
        volume_threshold = np.percentile(df['volume'], volume_threshold_percentile)
        avg_volume = df['volume'].mean()
        volume_spike_threshold_actual = avg_volume * volume_spike_threshold

        # --- 2. Identify Key Support and Resistance Levels ---
        # Find swing highs and lows for potential liquidity pools
        swing_highs, _ = find_peaks(df['high'], distance=5, prominence=df['high'].std() * 0.1)
        swing_lows, _ = find_peaks(-df['low'], distance=5, prominence=df['low'].std() * 0.1)

        # Create liquidity pool levels
        resistance_levels = df.iloc[swing_highs]['high'].tolist()
        support_levels = df.iloc[swing_lows]['low'].tolist()

        detected_sweeps = []

        # --- 3. Detect Bullish Liquidity Sweeps (Above Resistance) ---
        for i, resistance in enumerate(resistance_levels):
            # Look for candles that sweep above resistance
            for idx in range(len(df) - sweep_reversal_candles):
                candle = df.iloc[idx]
                
                # Check if candle swept above resistance
                if candle['high'] > resistance:
                    sweep_distance = (candle['high'] - resistance) / resistance * 100
                    
                    # Check if sweep distance is significant
                    if sweep_distance >= min_sweep_distance:
                        # Check for volume spike
                        volume_spike = candle['volume'] > volume_spike_threshold_actual
                        volume_ratio = candle['volume_ratio']
                        
                        # Check for reversal within specified candles
                        reversal_confirmed = False
                        reversal_strength = 0
                        
                        for j in range(1, min(sweep_reversal_candles + 1, len(df) - idx)):
                            next_candle = df.iloc[idx + j]
                            
                            # Check if price reversed below resistance
                            if next_candle['close'] < resistance:
                                reversal_confirmed = True
                                reversal_strength = (resistance - next_candle['close']) / resistance * 100
                                break
                        
                        # Calculate confidence score
                        confidence = 0.5  # Base confidence
                        
                        if volume_spike:
                            confidence += 0.2
                        if reversal_confirmed:
                            confidence += 0.2
                        if volume_ratio > 2.0:
                            confidence += 0.1
                        if sweep_distance > 0.5:  # Stronger sweep
                            confidence += 0.1
                        if reversal_strength > 0.3:  # Strong reversal
                            confidence += 0.1
                        
                        confidence = min(0.95, confidence)
                        
                        if confidence >= confidence_threshold:
                            detected_sweeps.append({
                                'timestamp': candle['timestamp'],
                                'type': 'bullish_sweep',
                                'price_level': resistance,
                                'sweep_high': candle['high'],
                                'sweep_low': candle['low'],
                                'confidence': round(confidence, 3),
                                'volume_spike': round(volume_ratio, 2),
                                'reversal_confirmed': reversal_confirmed,
                                'sweep_strength': round(sweep_distance, 2),
                                'reversal_strength': round(reversal_strength, 2),
                                'liquidity_pool_type': 'resistance',
                                'candle_index': idx,
                                'volume_confirmed': volume_spike
                            })

        # --- 4. Detect Bearish Liquidity Sweeps (Below Support) ---
        for i, support in enumerate(support_levels):
            # Look for candles that sweep below support
            for idx in range(len(df) - sweep_reversal_candles):
                candle = df.iloc[idx]
                
                # Check if candle swept below support
                if candle['low'] < support:
                    sweep_distance = (support - candle['low']) / support * 100
                    
                    # Check if sweep distance is significant
                    if sweep_distance >= min_sweep_distance:
                        # Check for volume spike
                        volume_spike = candle['volume'] > volume_spike_threshold_actual
                        volume_ratio = candle['volume_ratio']
                        
                        # Check for reversal within specified candles
                        reversal_confirmed = False
                        reversal_strength = 0
                        
                        for j in range(1, min(sweep_reversal_candles + 1, len(df) - idx)):
                            next_candle = df.iloc[idx + j]
                            
                            # Check if price reversed above support
                            if next_candle['close'] > support:
                                reversal_confirmed = True
                                reversal_strength = (next_candle['close'] - support) / support * 100
                                break
                        
                        # Calculate confidence score
                        confidence = 0.5  # Base confidence
                        
                        if volume_spike:
                            confidence += 0.2
                        if reversal_confirmed:
                            confidence += 0.2
                        if volume_ratio > 2.0:
                            confidence += 0.1
                        if sweep_distance > 0.5:  # Stronger sweep
                            confidence += 0.1
                        if reversal_strength > 0.3:  # Strong reversal
                            confidence += 0.1
                        
                        confidence = min(0.95, confidence)
                        
                        if confidence >= confidence_threshold:
                            detected_sweeps.append({
                                'timestamp': candle['timestamp'],
                                'type': 'bearish_sweep',
                                'price_level': support,
                                'sweep_high': candle['high'],
                                'sweep_low': candle['low'],
                                'confidence': round(confidence, 3),
                                'volume_spike': round(volume_ratio, 2),
                                'reversal_confirmed': reversal_confirmed,
                                'sweep_strength': round(sweep_distance, 2),
                                'reversal_strength': round(reversal_strength, 2),
                                'liquidity_pool_type': 'support',
                                'candle_index': idx,
                                'volume_confirmed': volume_spike
                            })

        # --- 5. Filter and Sort Results ---
        # Remove duplicate sweeps at similar levels
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
            'resistance_levels': resistance_levels,
            'support_levels': support_levels,
            'bullish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bullish_sweep']),
            'bearish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bearish_sweep'])
        }

