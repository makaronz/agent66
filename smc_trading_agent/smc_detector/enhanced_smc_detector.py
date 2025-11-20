"""
Enhanced SMC Pattern Detection with Advanced Market Structure Analysis

This module implements sophisticated Smart Money Concepts pattern detection
incorporating advanced market structure analysis, volume profile analysis,
and institutional order flow detection as outlined in traderule.md.

Key Features:
- Advanced market structure analysis with multi-timeframe support
- Volume profile analysis and Point of Control (POC) detection
- Liquidity zone identification and smart money tracking
- Institutional order block detection with confirmation algorithms
- Real-time pattern scoring and confidence weighting
- Market regime detection and adaptive sensitivity
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
from scipy import stats
from scipy.signal import find_peaks
import numba
from numba import jit, float64, int64, boolean
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classification for adaptive sensitivity"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNCERTAIN = "uncertain"

class PatternType(Enum):
    """SMC pattern types with enhanced classification"""
    BULLISH_ORDER_BLOCK = "bullish_order_block"
    BEARISH_ORDER_BLOCK = "bearish_order_block"
    BULLISH_BREAK_OF_STRUCTURE = "bullish_bos"
    BEARISH_BREAK_OF_STRUCTURE = "bearish_bos"
    CHANGE_OF_CHARACTER = "change_of_character"
    FAIR_VALUE_GAP = "fair_value_gap"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    SMART_MONEY_ENTRY = "smart_money_entry"
    INSTITUTIONAL_ZONE = "institutional_zone"

@dataclass
class EnhancedPattern:
    """Enhanced pattern structure with comprehensive metadata"""
    pattern_type: PatternType
    timestamp: datetime
    price_level: Tuple[float, float]
    confidence: float
    strength: float
    volume_confirmation: bool
    timeframe: str
    market_regime: MarketRegime
    additional_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API compatibility"""
        return {
            'type': self.pattern_type.value,
            'timestamp': self.timestamp.isoformat(),
            'price_level': self.price_level,
            'confidence': self.confidence,
            'strength': self.strength,
            'volume_confirmed': self.volume_confirmation,
            'timeframe': self.timeframe,
            'market_regime': self.market_regime.value,
            'additional_metrics': self.additional_metrics
        }

class VolumeProfileAnalyzer:
    """Advanced volume profile analysis for identifying institutional activity"""

    def __init__(self, price_bins: int = 100):
        self.price_bins = price_bins

    def calculate_volume_profile(self, df: pd.DataFrame, lookback: int = 1000) -> Dict[str, np.ndarray]:
        """
        Calculate comprehensive volume profile analysis

        Args:
            df: OHLCV DataFrame
            lookback: Number of candles to analyze

        Returns:
            Dictionary containing volume profile data
        """
        if len(df) < lookback:
            lookback = len(df)

        recent_data = df.tail(lookback)

        # Create price bins
        price_min = recent_data['low'].min()
        price_max = recent_data['high'].max()
        price_bins = np.linspace(price_min, price_max, self.price_bins)

        # Calculate volume at each price level
        volume_at_price = np.zeros(len(price_bins) - 1)

        for _, candle in recent_data.iterrows():
            high_idx = np.searchsorted(price_bins, candle['high']) - 1
            low_idx = np.searchsorted(price_bins, candle['low'])

            if high_idx >= low_idx and high_idx < len(volume_at_price):
                volume_at_price[low_idx:min(high_idx + 1, len(volume_at_price))] += candle['volume']

        # Find Point of Control (POC) - highest volume level
        poc_idx = np.argmax(volume_at_price)
        poc_price = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2

        # Calculate Value Area (70% of volume)
        total_volume = volume_at_price.sum()
        cumulative_volume = np.cumsum(volume_at_price[volume_at_price.argsort()[::-1]])
        va_volume_threshold = total_volume * 0.7

        sorted_indices = volume_at_price.argsort()[::-1]
        va_indices = sorted_indices[cumulative_volume <= va_volume_threshold]

        if len(va_indices) > 0:
            va_high = price_bins[va_indices.min() + 1]
            va_low = price_bins[va_indices.max()]
        else:
            va_high = va_low = poc_price

        return {
            'price_bins': price_bins,
            'volume_at_price': volume_at_price,
            'poc_price': poc_price,
            'poc_volume': volume_at_price[poc_idx],
            'value_area_high': va_high,
            'value_area_low': va_low,
            'total_volume': total_volume
        }

    def detect_institutional_zones(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect institutional trading zones using volume profile anomalies"""
        volume_profile = self.calculate_volume_profile(df)

        # Identify high volume nodes (potential institutional zones)
        volume_threshold = np.percentile(volume_profile['volume_at_price'], 80)
        high_volume_indices = np.where(volume_profile['volume_at_price'] > volume_threshold)[0]

        institutional_zones = []

        for idx in high_volume_indices:
            zone_price = (volume_profile['price_bins'][idx] + volume_profile['price_bins'][idx + 1]) / 2
            zone_volume = volume_profile['volume_at_price'][idx]

            institutional_zones.append({
                'price_level': zone_price,
                'volume': zone_volume,
                'significance': zone_volume / volume_profile['poc_volume'],
                'type': 'support' if zone_price < volume_profile['poc_price'] else 'resistance'
            })

        return sorted(institutional_zones, key=lambda x: x['volume'], reverse=True)

class MarketStructureAnalyzer:
    """Advanced market structure analysis for trend and range detection"""

    @staticmethod
    @jit(nopython=True)
    def _detect_market_structure_numba(highs: np.ndarray, lows: np.ndarray,
                                       swing_length: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Numba-optimized market structure detection

        Args:
            highs: Array of high prices
            lows: Array of low prices
            swing_length: Minimum distance between swing points

        Returns:
            Tuple of (swing_highs_indices, swing_lows_indices)
        """
        swing_highs = []
        swing_lows = []
        n = len(highs)

        for i in range(swing_length, n - swing_length):
            # Check for swing high
            is_swing_high = True
            current_high = highs[i]
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and highs[j] >= current_high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append(i)

            # Check for swing low
            is_swing_low = True
            current_low = lows[i]
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and lows[j] <= current_low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append(i)

        return np.array(swing_highs), np.array(swing_lows)

    def detect_market_regime(self, df: pd.DataFrame, lookback: int = 200) -> MarketRegime:
        """
        Detect current market regime using multiple indicators

        Args:
            df: OHLCV DataFrame
            lookback: Number of candles to analyze

        Returns:
            Current market regime
        """
        if len(df) < lookback:
            lookback = len(df)

        recent_data = df.tail(lookback)

        # Calculate trend strength
        swing_highs, swing_lows = self._detect_market_structure_numba(
            recent_data['high'].values, recent_data['low'].values
        )

        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Calculate trend lines
            highs_slope = np.polyfit(swing_highs, recent_data['high'].iloc[swing_highs], 1)[0]
            lows_slope = np.polyfit(swing_lows, recent_data['low'].iloc[swing_lows], 1)[0]

            # Calculate volatility
            returns = recent_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)

            # Determine regime
            if abs(highs_slope) > 0.001 and abs(lows_slope) > 0.001:
                if highs_slope > 0 and lows_slope > 0:
                    return MarketRegime.TRENDING
                elif highs_slope < 0 and lows_slope < 0:
                    return MarketRegime.TRENDING
                else:
                    return MarketRegime.UNCERTAIN
            else:
                if volatility > 0.3:
                    return MarketRegime.VOLATILE
                else:
                    return MarketRegime.RANGING
        else:
            return MarketRegime.UNCERTAIN

    def identify_key_levels(self, df: pd.DataFrame, lookback: int = 500) -> Dict[str, List[float]]:
        """
        Identify key support and resistance levels using multiple methods

        Args:
            df: OHLCV DataFrame
            lookback: Number of candles to analyze

        Returns:
            Dictionary containing support and resistance levels
        """
        if len(df) < lookback:
            lookback = len(df)

        recent_data = df.tail(lookback)

        # Method 1: Swing points
        swing_highs, swing_lows = self._detect_market_structure_numba(
            recent_data['high'].values, recent_data['low'].values
        )

        support_levels = []
        resistance_levels = []

        if len(swing_lows) > 0:
            support_levels = recent_data['low'].iloc[swing_lows].tolist()
        if len(swing_highs) > 0:
            resistance_levels = recent_data['high'].iloc[swing_highs].tolist()

        # Method 2: Volume profile POC and VA
        volume_analyzer = VolumeProfileAnalyzer()
        volume_profile = volume_analyzer.calculate_volume_profile(recent_data)

        support_levels.append(volume_profile['value_area_low'])
        resistance_levels.append(volume_profile['value_area_high'])

        # Method 3: Fibonacci levels
        max_high = recent_data['high'].max()
        min_low = recent_data['low'].min()

        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        for fib in fib_levels:
            level = min_low + (max_high - min_low) * fib
            if level > recent_data['close'].iloc[-1]:
                resistance_levels.append(level)
            else:
                support_levels.append(level)

        # Remove duplicates and sort
        support_levels = sorted(list(set(support_levels)))
        resistance_levels = sorted(list(set(resistance_levels)), reverse=True)

        return {
            'support': support_levels[:10],  # Top 10 levels
            'resistance': resistance_levels[:10]
        }

class SmartMoneyDetector:
    """Detect smart money activity using advanced pattern recognition"""

    def __init__(self):
        self.volume_analyzer = VolumeProfileAnalyzer()
        self.structure_analyzer = MarketStructureAnalyzer()

    @staticmethod
    @jit(nopython=True)
    def _detect_order_blocks_numba(highs: np.ndarray, lows: np.ndarray,
                                  opens: np.ndarray, closes: np.ndarray,
                                  volumes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Numba-optimized order block detection

        Args:
            highs, lows, opens, closes, volumes: OHLCV arrays

        Returns:
            Tuple of (indices, types, strengths)
        """
        n = len(highs)
        max_blocks = n // 10  # Estimate maximum number of order blocks
        indices = np.zeros(max_blocks, dtype=np.int64)
        types = np.zeros(max_blocks, dtype=np.int64)  # 1=bullish, 0=bearish
        strengths = np.zeros(max_blocks, dtype=np.float64)
        count = 0

        # Find potential order blocks
        for i in range(1, n - 1):
            # Bullish order block: Strong down candle before strong up move
            if (closes[i] < opens[i] and  # Down candle
                volumes[i] > np.mean(volumes[max(0, i-20):i+1])):  # High volume

                # Check for subsequent up move
                for j in range(i + 1, min(i + 10, n)):
                    if (closes[j] > opens[j] and  # Up candle
                        closes[j] > highs[i] and  # Breaks high
                        volumes[j] > volumes[i]):  # Even higher volume
                        indices[count] = i
                        types[count] = 1  # Bullish
                        strengths[count] = volumes[i] / np.mean(volumes[max(0, i-20):i+1])
                        count += 1
                        break

            # Bearish order block: Strong up candle before strong down move
            elif (closes[i] > opens[i] and  # Up candle
                  volumes[i] > np.mean(volumes[max(0, i-20):i+1])):  # High volume

                # Check for subsequent down move
                for j in range(i + 1, min(i + 10, n)):
                    if (closes[j] < opens[j] and  # Down candle
                        closes[j] < lows[i] and  # Breaks low
                        volumes[j] > volumes[i]):  # Even higher volume
                        indices[count] = i
                        types[count] = 0  # Bearish
                        strengths[count] = volumes[i] / np.mean(volumes[max(0, i-20):i+1])
                        count += 1
                        break

        return indices[:count], types[:count], strengths[:count]

    def detect_smart_money_patterns(self, df: pd.DataFrame,
                                   market_regime: MarketRegime) -> List[EnhancedPattern]:
        """
        Detect comprehensive smart money patterns

        Args:
            df: OHLCV DataFrame
            market_regime: Current market regime

        Returns:
            List of enhanced patterns
        """
        patterns = []

        # Detect order blocks
        ob_indices, ob_types, ob_strengths = self._detect_order_blocks_numba(
            df['high'].values, df['low'].values, df['open'].values,
            df['close'].values, df['volume'].values
        )

        for i, idx in enumerate(ob_indices):
            if idx < len(df):
                pattern_type = PatternType.BULLISH_ORDER_BLOCK if ob_types[i] == 1 else PatternType.BEARISH_ORDER_BLOCK

                pattern = EnhancedPattern(
                    pattern_type=pattern_type,
                    timestamp=df['timestamp'].iloc[idx],
                    price_level=(df['high'].iloc[idx], df['low'].iloc[idx]),
                    confidence=min(0.95, 0.6 + ob_strengths[i] * 0.2),
                    strength=ob_strengths[i],
                    volume_confirmation=True,
                    timeframe='1h',  # Default timeframe
                    market_regime=market_regime,
                    additional_metrics={
                        'volume_ratio': ob_strengths[i],
                        'price_move': abs(df['close'].iloc[idx] - df['open'].iloc[idx]) / df['open'].iloc[idx]
                    }
                )
                patterns.append(pattern)

        # Detect fair value gaps
        fvg_patterns = self._detect_fair_value_gaps(df, market_regime)
        patterns.extend(fvg_patterns)

        # Detect liquidity sweeps
        sweep_patterns = self._detect_liquidity_sweeps(df, market_regime)
        patterns.extend(sweep_patterns)

        # Sort by confidence and strength
        patterns.sort(key=lambda x: x.confidence * x.strength, reverse=True)

        return patterns[:20]  # Return top 20 patterns

    def _detect_fair_value_gaps(self, df: pd.DataFrame,
                               market_regime: MarketRegime) -> List[EnhancedPattern]:
        """Detect Fair Value Gaps (FVG) - 3-candle patterns"""
        patterns = []

        for i in range(2, len(df)):
            # Bullish FVG: Gap between high of first candle and low of third candle
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                avg_candle_range = (df['high'].iloc[i-2:i+1] - df['low'].iloc[i-2:i+1]).mean()

                if gap_size > avg_candle_range * 0.5:  # Significant gap
                    pattern = EnhancedPattern(
                        pattern_type=PatternType.FAIR_VALUE_GAP,
                        timestamp=df['timestamp'].iloc[i],
                        price_level=(df['high'].iloc[i-2], df['low'].iloc[i]),
                        confidence=min(0.9, 0.6 + gap_size / avg_candle_range * 0.3),
                        strength=gap_size / df['close'].iloc[i],
                        volume_confirmation=df['volume'].iloc[i] > df['volume'].iloc[i-1],
                        timeframe='1h',
                        market_regime=market_regime,
                        additional_metrics={
                            'gap_size': gap_size,
                            'gap_percentage': gap_size / df['close'].iloc[i] * 100
                        }
                    )
                    patterns.append(pattern)

            # Bearish FVG: Gap between low of first candle and high of third candle
            elif df['low'].iloc[i-2] > df['high'].iloc[i]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                avg_candle_range = (df['high'].iloc[i-2:i+1] - df['low'].iloc[i-2:i+1]).mean()

                if gap_size > avg_candle_range * 0.5:  # Significant gap
                    pattern = EnhancedPattern(
                        pattern_type=PatternType.FAIR_VALUE_GAP,
                        timestamp=df['timestamp'].iloc[i],
                        price_level=(df['low'].iloc[i-2], df['high'].iloc[i]),
                        confidence=min(0.9, 0.6 + gap_size / avg_candle_range * 0.3),
                        strength=gap_size / df['close'].iloc[i],
                        volume_confirmation=df['volume'].iloc[i] > df['volume'].iloc[i-1],
                        timeframe='1h',
                        market_regime=market_regime,
                        additional_metrics={
                            'gap_size': gap_size,
                            'gap_percentage': gap_size / df['close'].iloc[i] * 100
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def _detect_liquidity_sweeps(self, df: pd.DataFrame,
                                market_regime: MarketRegime) -> List[EnhancedPattern]:
        """Detect liquidity sweeps - price moves beyond key levels with quick reversal"""
        patterns = []

        key_levels = self.structure_analyzer.identify_key_levels(df)

        for i in range(5, len(df) - 5):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]

            # Check for sweep above resistance
            for resistance in key_levels['resistance'][:5]:  # Top 5 resistance levels
                if current_high > resistance:
                    sweep_distance = (current_high - resistance) / resistance

                    # Check for quick reversal within next 5 candles
                    reversal_found = False
                    reversal_strength = 0

                    for j in range(1, 6):
                        if i + j < len(df) and df['close'].iloc[i + j] < resistance:
                            reversal_found = True
                            reversal_strength = (resistance - df['close'].iloc[i + j]) / resistance
                            break

                    if reversal_found and sweep_distance > 0.001:  # 0.1% minimum sweep
                        pattern = EnhancedPattern(
                            pattern_type=PatternType.LIQUIDITY_SWEEP,
                            timestamp=df['timestamp'].iloc[i],
                            price_level=(current_high, current_low),
                            confidence=min(0.9, 0.5 + sweep_distance * 50 + reversal_strength * 30),
                            strength=sweep_distance * 100,
                            volume_confirmation=df['volume'].iloc[i] > df['volume'].iloc[i-1],
                            timeframe='1h',
                            market_regime=market_regime,
                            additional_metrics={
                                'sweep_distance': sweep_distance,
                                'reversal_strength': reversal_strength,
                                'level_type': 'resistance'
                            }
                        )
                        patterns.append(pattern)

            # Check for sweep below support
            for support in key_levels['support'][:5]:  # Top 5 support levels
                if current_low < support:
                    sweep_distance = (support - current_low) / support

                    # Check for quick reversal within next 5 candles
                    reversal_found = False
                    reversal_strength = 0

                    for j in range(1, 6):
                        if i + j < len(df) and df['close'].iloc[i + j] > support:
                            reversal_found = True
                            reversal_strength = (df['close'].iloc[i + j] - support) / support
                            break

                    if reversal_found and sweep_distance > 0.001:  # 0.1% minimum sweep
                        pattern = EnhancedPattern(
                            pattern_type=PatternType.LIQUIDITY_SWEEP,
                            timestamp=df['timestamp'].iloc[i],
                            price_level=(current_high, current_low),
                            confidence=min(0.9, 0.5 + sweep_distance * 50 + reversal_strength * 30),
                            strength=sweep_distance * 100,
                            volume_confirmation=df['volume'].iloc[i] > df['volume'].iloc[i-1],
                            timeframe='1h',
                            market_regime=market_regime,
                            additional_metrics={
                                'sweep_distance': sweep_distance,
                                'reversal_strength': reversal_strength,
                                'level_type': 'support'
                            }
                        )
                        patterns.append(pattern)

        return patterns

class EnhancedSMCDetector:
    """
    Main enhanced SMC detector with comprehensive pattern analysis
    and real-time market structure detection
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.volume_analyzer = VolumeProfileAnalyzer(
            price_bins=self.config.get('volume_profile_bins', 100)
        )
        self.structure_analyzer = MarketStructureAnalyzer()
        self.smart_money_detector = SmartMoneyDetector()

        # Pattern history for trend analysis
        self.pattern_history: List[EnhancedPattern] = []
        self.max_history_size = 1000

        # Performance optimization
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Adaptive sensitivity based on market regime
        self.confidence_thresholds = {
            MarketRegime.TRENDING: 0.65,
            MarketRegime.RANGING: 0.75,
            MarketRegime.VOLATILE: 0.60,
            MarketRegime.UNCERTAIN: 0.80
        }

        self.logger.info("Enhanced SMC Detector initialized with advanced pattern recognition")

    async def analyze_market_data(self, df: pd.DataFrame,
                                 symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        Comprehensive market analysis with enhanced SMC patterns

        Args:
            df: OHLCV DataFrame
            symbol: Trading symbol

        Returns:
            Comprehensive analysis results
        """
        try:
            if df.empty or len(df) < 50:
                self.logger.warning(f"Insufficient data for {symbol}")
                return {'patterns': [], 'market_regime': 'unknown', 'analysis': {}}

            # Ensure proper data types
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)

            # Detect market regime
            market_regime = self.structure_analyzer.detect_market_regime(df)

            # Run analyses in parallel
            loop = asyncio.get_event_loop()

            # Pattern detection
            patterns_future = loop.run_in_executor(
                self.executor,
                self.smart_money_detector.detect_smart_money_patterns,
                df,
                market_regime
            )

            # Volume profile analysis
            volume_profile_future = loop.run_in_executor(
                self.executor,
                self.volume_analyzer.calculate_volume_profile,
                df
            )

            # Institutional zones
            institutional_zones_future = loop.run_in_executor(
                self.executor,
                self.volume_analyzer.detect_institutional_zones,
                df
            )

            # Key levels
            key_levels_future = loop.run_in_executor(
                self.executor,
                self.structure_analyzer.identify_key_levels,
                df
            )

            # Wait for all analyses
            patterns = await patterns_future
            volume_profile = await volume_profile_future
            institutional_zones = await institutional_zones_future
            key_levels = await key_levels_future

            # Filter patterns by confidence threshold
            confidence_threshold = self.confidence_thresholds.get(market_regime, 0.7)
            filtered_patterns = [p for p in patterns if p.confidence >= confidence_threshold]

            # Update pattern history
            self.pattern_history.extend(filtered_patterns)
            if len(self.pattern_history) > self.max_history_size:
                self.pattern_history = self.pattern_history[-self.max_history_size:]

            # Prepare results
            analysis_results = {
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat(),
                'market_regime': market_regime.value,
                'patterns': [p.to_dict() for p in filtered_patterns[:10]],  # Top 10 patterns
                'volume_profile': {
                    'poc_price': float(volume_profile['poc_price']),
                    'value_area_high': float(volume_profile['value_area_high']),
                    'value_area_low': float(volume_profile['value_area_low']),
                    'total_volume': float(volume_profile['total_volume'])
                },
                'institutional_zones': institutional_zones[:5],  # Top 5 zones
                'key_levels': key_levels,
                'pattern_summary': {
                    'total_patterns': len(filtered_patterns),
                    'bullish_patterns': len([p for p in filtered_patterns if 'bullish' in p.pattern_type.value]),
                    'bearish_patterns': len([p for p in filtered_patterns if 'bearish' in p.pattern_type.value]),
                    'high_confidence_patterns': len([p for p in filtered_patterns if p.confidence >= 0.8])
                }
            }

            self.logger.info(
                f"Enhanced SMC analysis completed for {symbol}",
                extra={
                    'symbol': symbol,
                    'market_regime': market_regime.value,
                    'patterns_found': len(filtered_patterns),
                    'confidence_threshold': confidence_threshold
                }
            )

            return analysis_results

        except Exception as e:
            self.logger.error(f"Enhanced SMC analysis failed for {symbol}: {str(e)}", exc_info=True)
            return {
                'symbol': symbol,
                'patterns': [],
                'market_regime': 'error',
                'error': str(e),
                'analysis': {}
            }

    def get_pattern_statistics(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Get pattern statistics for performance analysis

        Args:
            lookback_hours: Hours to look back for pattern analysis

        Returns:
            Pattern statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent_patterns = [p for p in self.pattern_history if p.timestamp > cutoff_time]

        if not recent_patterns:
            return {'message': 'No recent patterns found'}

        # Pattern type distribution
        pattern_types = {}
        for pattern in recent_patterns:
            pattern_type = pattern.pattern_type.value
            if pattern_type not in pattern_types:
                pattern_types[pattern_type] = []
            pattern_types[pattern_type].append(pattern.confidence)

        # Calculate statistics
        stats = {
            'total_patterns': len(recent_patterns),
            'pattern_types': {},
            'average_confidence': np.mean([p.confidence for p in recent_patterns]),
            'average_strength': np.mean([p.strength for p in recent_patterns]),
            'market_regimes': {},
            'timeframe': f'{lookback_hours}h'
        }

        # Pattern type statistics
        for pattern_type, confidences in pattern_types.items():
            stats['pattern_types'][pattern_type] = {
                'count': len(confidences),
                'avg_confidence': np.mean(confidences),
                'max_confidence': max(confidences)
            }

        # Market regime distribution
        for pattern in recent_patterns:
            regime = pattern.market_regime.value
            if regime not in stats['market_regimes']:
                stats['market_regimes'][regime] = 0
            stats['market_regimes'][regime] += 1

        return stats

    def cleanup(self):
        """Cleanup resources"""
        self.executor.shutdown(wait=True)
        self.logger.info("Enhanced SMC Detector cleaned up")

# Factory function for backward compatibility
def create_enhanced_smc_detector(config: Optional[Dict[str, Any]] = None) -> EnhancedSMCDetector:
    """Create enhanced SMC detector instance"""
    return EnhancedSMCDetector(config)