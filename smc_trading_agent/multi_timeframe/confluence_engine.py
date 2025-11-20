"""
Multi-Timeframe Confluence Analysis Engine

Advanced confluence detection algorithms including HTF trend analysis,
premium/discount zone mapping, order block confluence, and market structure
shift pattern recognition with intelligent scoring systems.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Set

# Try to import talib, provide fallback if not available
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("Warning: talib not available, using fallback implementations")
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class TrendDirection(Enum):
    """Trend direction enumeration."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNCERTAIN = "uncertain"

class MarketStructurePhase(Enum):
    """Market structure phase enumeration."""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    TRANSITION = "transition"

@dataclass
class TrendAnalysis:
    """Trend analysis results for a timeframe."""
    direction: TrendDirection
    strength: float  # 0.0 to 1.0
    momentum: float
    volatility: float
    phase: MarketStructurePhase
    confidence: float
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    key_levels: List[float] = field(default_factory=list)

@dataclass
class PremiumDiscountZone:
    """Premium or discount zone analysis."""
    zone_type: str  # 'premium' or 'discount'
    price_range: Tuple[float, float]
    strength: float
    timeframe: str
    confidence: float
    fair_value: float
    deviation_percent: float

@dataclass
class OrderBlockConfluence:
    """Order block confluence across timeframes."""
    price_level: float
    order_blocks: List[Dict[str, Any]]
    timeframes: Set[str]
    confluence_strength: float
    type: str  # 'bullish' or 'bearish'
    freshness_score: float
    volume_confirmation: float

@dataclass
class MarketStructureShift:
    """Market structure shift pattern."""
    shift_type: str  # 'CHOCH', 'BOS', 'MSS'
    direction: str  # 'bullish' or 'bearish'
    price_level: float
    timeframes: Set[str]
    confidence: float
    strength: float
    timestamp: datetime

@dataclass
class ConfluenceScore:
    """Overall confluence score for a price level."""
    price_level: float
    overall_score: float
    trend_alignment: float
    level_confluence: float
    volume_confirmation: float
    timeframe_agreement: float
    signal_strength: float
    risk_reward_ratio: float
    confidence: float
    supporting_factors: List[str] = field(default_factory=list)
    opposing_factors: List[str] = field(default_factory=list)

class TrendAnalyzer:
    """Analyzes trends across multiple timeframes."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    def analyze_trend(self, df: pd.DataFrame, timeframe: str) -> TrendAnalysis:
        """
        Comprehensive trend analysis for a single timeframe.

        Args:
            df: OHLCV DataFrame
            timeframe: Timeframe identifier

        Returns:
            TrendAnalysis object with comprehensive trend information
        """
        try:
            if df.empty or len(df) < 20:
                return TrendAnalysis(
                    direction=TrendDirection.UNCERTAIN,
                    strength=0.0,
                    momentum=0.0,
                    volatility=0.0,
                    phase=MarketStructurePhase.TRANSITION,
                    confidence=0.0
                )

            # Calculate technical indicators
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values

            # Moving averages for trend direction
            if TALIB_AVAILABLE:
                ma_20 = talib.SMA(close, timeperiod=20)
                ma_50 = talib.SMA(close, timeperiod=50)
                ma_200 = talib.SMA(close, timeperiod=200) if len(close) >= 200 else None

                # Momentum indicators
                rsi = talib.RSI(close, timeperiod=14)
                macd, macd_signal, macd_hist = talib.MACD(close)
                adx = talib.ADX(high, low, close, timeperiod=14)

                # Volatility
                atr = talib.ATR(high, low, close, timeperiod=14)
                bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20)
            else:
                # Fallback implementations
                ma_20 = self._fallback_sma(close, 20)
                ma_50 = self._fallback_sma(close, 50)
                ma_200 = self._fallback_sma(close, 200) if len(close) >= 200 else None

                # Simple fallback momentum indicators
                rsi = self._fallback_rsi(close, 14)
                macd, macd_signal, macd_hist = self._fallback_macd(close)
                adx = self._fallback_adx(high, low, close, 14)
                atr = self._fallback_atr(high, low, close, 14)
                bb_upper, bb_middle, bb_lower = self._fallback_bollinger_bands(close, 20)

            # Determine trend direction
            current_price = close[-1]
            current_ma_20 = ma_20[-1] if not np.isnan(ma_20[-1]) else current_price
            current_ma_50 = ma_50[-1] if not np.isnan(ma_50[-1]) else current_price

            # Trend direction logic
            if ma_200 is not None and not np.isnan(ma_200[-1]):
                current_ma_200 = ma_200[-1]
                if current_price > current_ma_200 > current_ma_50 > current_ma_20:
                    direction = TrendDirection.BULLISH
                elif current_price < current_ma_200 < current_ma_50 < current_ma_20:
                    direction = TrendDirection.BEARISH
                else:
                    direction = TrendDirection.SIDEWAYS
            else:
                if current_price > current_ma_20 > current_ma_50:
                    direction = TrendDirection.BULLISH
                elif current_price < current_ma_20 < current_ma_50:
                    direction = TrendDirection.BEARISH
                else:
                    direction = TrendDirection.SIDEWAYS

            # Calculate trend strength
            ma_alignment = self._calculate_ma_alignment(ma_20, ma_50, ma_200)
            momentum_strength = self._calculate_momentum_strength(rsi, macd_hist, adx)
            volatility_normalized = min(1.0, np.mean(atr[-20:]) / current_price * 100)

            strength = (ma_alignment * 0.4 + momentum_strength * 0.4 + (1 - volatility_normalized) * 0.2)

            # Determine market structure phase
            phase = self._determine_market_phase(df, direction)

            # Calculate confidence
            confidence = min(1.0, strength * (1 - volatility_normalized * 0.3))

            # Find key levels
            support_levels, resistance_levels, key_levels = self._find_key_levels(df)

            return TrendAnalysis(
                direction=direction,
                strength=min(1.0, strength),
                momentum=momentum_strength,
                volatility=volatility_normalized,
                phase=phase,
                confidence=confidence,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                key_levels=key_levels
            )

        except Exception as e:
            logger.error(f"Error analyzing trend for {timeframe}: {e}")
            return TrendAnalysis(
                direction=TrendDirection.UNCERTAIN,
                strength=0.0,
                momentum=0.0,
                volatility=0.0,
                phase=MarketStructurePhase.TRANSITION,
                confidence=0.0
            )

    def _calculate_ma_alignment(self, ma_20: np.ndarray, ma_50: np.ndarray,
                               ma_200: Optional[np.ndarray]) -> float:
        """Calculate moving average alignment score."""
        try:
            if ma_200 is None:
                # Simple alignment between MA20 and MA50
                alignment = np.corrcoef(ma_20[~np.isnan(ma_20)], ma_50[~np.isnan(ma_50)])[0, 1]
                return max(0, alignment)

            # Full alignment across all MAs
            valid_indices = ~(np.isnan(ma_20) | np.isnan(ma_50) | np.isnan(ma_200))
            if not np.any(valid_indices):
                return 0.0

            ma_20_valid = ma_20[valid_indices]
            ma_50_valid = ma_50[valid_indices]
            ma_200_valid = ma_200[valid_indices]

            # Check if they're in correct order and trending together
            alignment_score = 0.0

            # Bullish alignment
            bullish_alignment = np.mean((ma_20_valid > ma_50_valid) & (ma_50_valid > ma_200_valid))
            # Bearish alignment
            bearish_alignment = np.mean((ma_20_valid < ma_50_valid) & (ma_50_valid < ma_200_valid))

            alignment_score = max(bullish_alignment, bearish_alignment)
            return alignment_score

        except Exception as e:
            logger.error(f"Error calculating MA alignment: {e}")
            return 0.0

    def _calculate_momentum_strength(self, rsi: np.ndarray, macd_hist: np.ndarray,
                                   adx: np.ndarray) -> float:
        """Calculate momentum strength score."""
        try:
            # RSI momentum
            rsi_current = rsi[-1] if not np.isnan(rsi[-1]) else 50
            rsi_strength = abs(rsi_current - 50) / 50

            # MACD momentum
            macd_strength = 0.0
            if len(macd_hist) >= 10:
                recent_macd = macd_hist[-10:]
                macd_trend = np.polyfit(range(len(recent_macd)), recent_macd, 1)[0]
                macd_strength = min(1.0, abs(macd_trend) * 1000)

            # ADX strength
            adx_current = adx[-1] if not np.isnan(adx[-1]) else 25
            adx_strength = min(1.0, adx_current / 50)

            # Combined momentum strength
            momentum = (rsi_strength * 0.3 + macd_strength * 0.4 + adx_strength * 0.3)
            return min(1.0, momentum)

        except Exception as e:
            logger.error(f"Error calculating momentum strength: {e}")
            return 0.0

    def _determine_market_phase(self, df: pd.DataFrame, direction: TrendDirection) -> MarketStructurePhase:
        """Determine current market structure phase."""
        try:
            close = df['close'].values
            volume = df['volume'].values

            # Price and volume characteristics
            price_volatility = np.std(close[-20:]) / np.mean(close[-20:])
            volume_ratio = np.mean(volume[-10:]) / np.mean(volume[:-10])

            # Phase determination logic
            if direction == TrendDirection.BULLISH:
                if volume_ratio > 1.2 and price_volatility < 0.02:
                    return MarketStructurePhase.MARKUP
                elif price_volatility > 0.03:
                    return MarketStructurePhase.TRANSITION
                else:
                    return MarketStructurePhase.ACCUMULATION
            elif direction == TrendDirection.BEARISH:
                if volume_ratio > 1.2 and price_volatility < 0.02:
                    return MarketStructurePhase.MARKDOWN
                elif price_volatility > 0.03:
                    return MarketStructurePhase.TRANSITION
                else:
                    return MarketStructurePhase.DISTRIBUTION
            else:
                return MarketStructurePhase.TRANSITION

        except Exception as e:
            logger.error(f"Error determining market phase: {e}")
            return MarketStructurePhase.TRANSITION

    def _find_key_levels(self, df: pd.DataFrame) -> Tuple[List[float], List[float], List[float]]:
        """Find key support, resistance, and overall levels."""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            # Find swing highs and lows
            swing_highs = self._find_swing_points(high, 'high')
            swing_lows = self._find_swing_points(low, 'low')

            support_levels = [low[i] for i in swing_lows[-10:]]  # Last 10 swing lows
            resistance_levels = [high[i] for i in swing_highs[-10:]]  # Last 10 swing highs

            # Combine all key levels
            key_levels = list(set(support_levels + resistance_levels))
            key_levels.sort()

            return support_levels, resistance_levels, key_levels

        except Exception as e:
            logger.error(f"Error finding key levels: {e}")
            return [], [], []

    def _fallback_sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Fallback Simple Moving Average implementation."""
        if len(data) < period:
            return np.full(len(data), np.nan)

        cumsum = np.cumsum(np.insert(data, 0, 0))
        return (cumsum[period:] - cumsum[:-period]) / float(period)

    def _fallback_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Fallback RSI implementation."""
        delta = np.diff(data)
        gain = (delta > 0) * delta
        loss = (delta < 0) * -delta

        avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')

        rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
        rsi = 100 - (100 / (1 + rs))

        # Pad with NaN to match original length
        rsi = np.concatenate([np.full(period, np.nan), rsi])
        return rsi

    def _fallback_macd(self, data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """Fallback MACD implementation."""
        ema_fast = self._fallback_ema(data, fast)
        ema_slow = self._fallback_ema(data, slow)
        macd = ema_fast - ema_slow
        signal_line = self._fallback_ema(macd, signal)
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _fallback_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Fallback Exponential Moving Average implementation."""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]

        return ema

    def _fallback_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14):
        """Fallback Average True Range implementation."""
        tr = np.zeros(len(close))

        for i in range(1, len(close)):
            high_low = high[i] - low[i]
            high_close = abs(high[i] - close[i-1])
            low_close = abs(low[i] - close[i-1])
            tr[i] = max(high_low, high_close, low_close)

        return self._fallback_sma(tr, period)

    def _fallback_bollinger_bands(self, data: np.ndarray, period: int = 20, std_dev: float = 2):
        """Fallback Bollinger Bands implementation."""
        sma = self._fallback_sma(data, period)
        std = np.full(len(data), np.nan)

        for i in range(period-1, len(data)):
            std[i] = np.std(data[i-period+1:i+1])

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return upper, sma, lower

    def _fallback_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14):
        """Fallback ADX implementation (simplified)."""
        # This is a very simplified ADX implementation
        tr = self._fallback_atr(high, low, close, 1)
        plus_dm = np.zeros(len(high))
        minus_dm = np.zeros(len(high))

        for i in range(1, len(high)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]

            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            elif down_move > up_move and down_move > 0:
                minus_dm[i] = down_move

        # Simplified ADX calculation
        adx = np.full(len(close), 25.0)  # Default middle value
        return adx

    def _find_swing_points(self, values: np.ndarray, point_type: str,
                          distance: int = 5) -> List[int]:
        """Find swing points using peak detection."""
        try:
            from scipy.signal import find_peaks

            prominence = np.std(values) * 0.1

            if point_type == 'high':
                peaks, _ = find_peaks(values, distance=distance, prominence=prominence)
            else:  # low
                peaks, _ = find_peaks(-values, distance=distance, prominence=prominence)

            return peaks.tolist()

        except Exception as e:
            logger.error(f"Error finding swing points: {e}")
            return []

class PremiumDiscountAnalyzer:
    """Analyzes premium and discount zones across timeframes."""

    def analyze_premium_discount(self, df: pd.DataFrame, timeframe: str,
                                current_price: float) -> List[PremiumDiscountZone]:
        """
        Analyze premium and discount zones.

        Args:
            df: OHLCV DataFrame
            timeframe: Timeframe identifier
            current_price: Current price level

        Returns:
            List of premium/discount zones
        """
        try:
            zones = []

            if df.empty or len(df) < 50:
                return zones

            # Calculate value area using volume profile concept
            value_area = self._calculate_value_area(df)
            fair_value = value_area['poc']  # Point of Control

            # Define premium and discount zones
            zone_range = value_area['vah'] - value_area['val']  # Value area high - low
            zone_extension = zone_range * 0.5  # 50% extension beyond value area

            # Premium zone (above value area)
            premium_zone = PremiumDiscountZone(
                zone_type='premium',
                price_range=(value_area['vah'], value_area['vah'] + zone_extension),
                strength=self._calculate_zone_strength(df, value_area['vah'], 'premium'),
                timeframe=timeframe,
                confidence=min(1.0, value_area['volume_ratio']),
                fair_value=fair_value,
                deviation_percent=(current_price - fair_value) / fair_value * 100
            )
            zones.append(premium_zone)

            # Discount zone (below value area)
            discount_zone = PremiumDiscountZone(
                zone_type='discount',
                price_range=(value_area['val'] - zone_extension, value_area['val']),
                strength=self._calculate_zone_strength(df, value_area['val'], 'discount'),
                timeframe=timeframe,
                confidence=min(1.0, value_area['volume_ratio']),
                fair_value=fair_value,
                deviation_percent=(current_price - fair_value) / fair_value * 100
            )
            zones.append(discount_zone)

            return zones

        except Exception as e:
            logger.error(f"Error analyzing premium/discount for {timeframe}: {e}")
            return []

    def _calculate_value_area(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate value area (simplified volume profile)."""
        try:
            # Use price levels and volume to find value area
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values

            # Create price bins
            price_range = np.max(high) - np.min(low)
            num_bins = min(100, len(df) // 2)
            bin_size = price_range / num_bins

            # Calculate volume at each price level
            price_volume_map = defaultdict(float)

            for i in range(len(df)):
                # Distribute volume across the candle's price range
                price_levels = np.linspace(low[i], high[i], 5)
                candle_volume = volume[i] / len(price_levels)

                for price in price_levels:
                    price_bin = round(price / bin_size) * bin_size
                    price_volume_map[price_bin] += candle_volume

            if not price_volume_map:
                return {'poc': close[-1], 'vah': close[-1], 'val': close[-1], 'volume_ratio': 0.5}

            # Find Point of Control (highest volume)
            poc = max(price_volume_map.keys(), key=lambda k: price_volume_map[k])

            # Calculate value area (70% of total volume)
            total_volume = sum(price_volume_map.values())
            target_volume = total_volume * 0.7

            # Build value area around POC
            sorted_prices = sorted(price_volume_map.keys())
            poc_index = sorted_prices.index(poc)

            vah, val = poc, poc
            accumulated_volume = price_volume_map[poc]

            # Expand outward from POC
            up_index, down_index = poc_index + 1, poc_index - 1

            while accumulated_volume < target_volume:
                added_volume = 0

                # Check upward
                if up_index < len(sorted_prices):
                    up_price = sorted_prices[up_index]
                    up_volume = price_volume_map[up_price]
                    if up_index - poc_index <= down_index - poc_index or down_index < 0:
                        accumulated_volume += up_volume
                        vah = up_price
                        up_index += 1
                        added_volume += up_volume

                # Check downward
                if down_index >= 0 and accumulated_volume < target_volume:
                    down_price = sorted_prices[down_index]
                    down_volume = price_volume_map[down_price]
                    if down_index >= 0:
                        accumulated_volume += down_volume
                        val = down_price
                        down_index -= 1
                        added_volume += down_volume

                if not added_volume:
                    break

            return {
                'poc': poc,
                'vah': vah,
                'val': val,
                'volume_ratio': min(1.0, accumulated_volume / total_volume)
            }

        except Exception as e:
            logger.error(f"Error calculating value area: {e}")
            return {'poc': df['close'].iloc[-1], 'vah': df['close'].iloc[-1],
                   'val': df['close'].iloc[-1], 'volume_ratio': 0.5}

    def _calculate_zone_strength(self, df: pd.DataFrame, level: float,
                                zone_type: str) -> float:
        """Calculate strength of a premium/discount zone."""
        try:
            # Count historical reactions at this level
            reactions = 0
            total_touches = 0

            for _, candle in df.iterrows():
                if zone_type == 'premium':
                    if candle['high'] >= level:
                        total_touches += 1
                        if candle['close'] < candle['open']:  # Rejection
                            reactions += 1
                else:  # discount
                    if candle['low'] <= level:
                        total_touches += 1
                        if candle['close'] > candle['open']:  # Bounce
                            reactions += 1

            if total_touches == 0:
                return 0.0

            return min(1.0, reactions / total_touches)

        except Exception as e:
            logger.error(f"Error calculating zone strength: {e}")
            return 0.0

class ConfluenceAnalysisEngine:
    """
    Main confluence analysis engine.

    Integrates trend analysis, premium/discount zones, order block confluence,
    and market structure shifts to generate comprehensive confluence scores.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.trend_analyzer = TrendAnalyzer()
        self.premium_discount_analyzer = PremiumDiscountAnalyzer()
        self.executor = ThreadPoolExecutor(max_workers=8)

        # Cache for storing analysis results
        self.trend_cache: Dict[str, Dict[str, TrendAnalysis]] = {}
        self.confluence_cache: Dict[str, List[ConfluenceScore]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}

        logger.info("Confluence analysis engine initialized")

    def analyze_multi_timeframe_confluence(self, symbol: str,
                                         timeframe_data: Dict[str, pd.DataFrame],
                                         current_price: float) -> List[ConfluenceScore]:
        """
        Analyze confluence across all timeframes for a symbol.

        Args:
            symbol: Trading symbol
            timeframe_data: Dictionary mapping timeframes to OHLCV DataFrames
            current_price: Current price level

        Returns:
            List of confluence scores sorted by strength
        """
        try:
            # Analyze each timeframe in parallel
            analysis_futures = {}
            for timeframe, df in timeframe_data.items():
                if not df.empty and len(df) >= 20:
                    future = self.executor.submit(
                        self._analyze_single_timeframe, timeframe, df, current_price
                    )
                    analysis_futures[timeframe] = future

            # Collect analyses
            timeframe_analyses = {}
            for timeframe, future in analysis_futures.items():
                try:
                    analysis = future.result(timeout=10)
                    timeframe_analyses[timeframe] = analysis
                except Exception as e:
                    logger.error(f"Error analyzing {timeframe}: {e}")

            # Generate confluence scores
            confluence_scores = self._generate_confluence_scores(
                symbol, timeframe_analyses, current_price
            )

            # Cache results
            self.confluence_cache[symbol] = confluence_scores
            self.cache_timestamps[symbol] = datetime.utcnow()

            # Sort by overall score
            confluence_scores.sort(key=lambda x: x.overall_score, reverse=True)

            return confluence_scores

        except Exception as e:
            logger.error(f"Error analyzing multi-timeframe confluence for {symbol}: {e}")
            return []

    def _analyze_single_timeframe(self, timeframe: str, df: pd.DataFrame,
                                current_price: float) -> Dict[str, Any]:
        """Analyze a single timeframe for confluence factors."""
        try:
            # Trend analysis
            trend_analysis = self.trend_analyzer.analyze_trend(df, timeframe)

            # Premium/Discount analysis
            premium_discount_zones = self.premium_discount_analyzer.analyze_premium_discount(
                df, timeframe, current_price
            )

            # Order block detection (simplified)
            order_blocks = self._detect_order_blocks(df, timeframe)

            # Market structure shifts
            structure_shifts = self._detect_structure_shifts(df, timeframe)

            return {
                'trend': trend_analysis,
                'premium_discount_zones': premium_discount_zones,
                'order_blocks': order_blocks,
                'structure_shifts': structure_shifts
            }

        except Exception as e:
            logger.error(f"Error analyzing single timeframe {timeframe}: {e}")
            return {}

    def _detect_order_blocks(self, df: pd.DataFrame, timeframe: str) -> List[OrderBlockConfluence]:
        """Detect order blocks for confluence analysis."""
        try:
            order_blocks = []

            if df.empty or len(df) < 20:
                return order_blocks

            # Simple order block detection (can be enhanced with existing SMC indicators)
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values

            # Find strong momentum candles (potential order blocks)
            body_threshold = np.mean(np.abs(close[1:] - close[:-1])) * 2

            for i in range(2, len(df) - 1):
                # Check for strong down candle (bullish order block)
                if close[i] < close[i-1] and (close[i-1] - close[i]) > body_threshold:
                    # Look for reversal in next candle
                    if close[i+1] > close[i] and volume[i] > np.percentile(volume, 80):
                        order_blocks.append(OrderBlockConfluence(
                            price_level=low[i],
                            order_blocks=[{
                                'timestamp': df.index[i],
                                'high': high[i],
                                'low': low[i],
                                'close': close[i],
                                'volume': volume[i]
                            }],
                            timeframes={timeframe},
                            confluence_strength=volume[i] / np.mean(volume),
                            type='bullish',
                            freshness_score=1.0 - (len(df) - i) / len(df),
                            volume_confirmation=volume[i] / np.mean(volume)
                        ))

                # Check for strong up candle (bearish order block)
                elif close[i] > close[i-1] and (close[i] - close[i-1]) > body_threshold:
                    # Look for reversal in next candle
                    if close[i+1] < close[i] and volume[i] > np.percentile(volume, 80):
                        order_blocks.append(OrderBlockConfluence(
                            price_level=high[i],
                            order_blocks=[{
                                'timestamp': df.index[i],
                                'high': high[i],
                                'low': low[i],
                                'close': close[i],
                                'volume': volume[i]
                            }],
                            timeframes={timeframe},
                            confluence_strength=volume[i] / np.mean(volume),
                            type='bearish',
                            freshness_score=1.0 - (len(df) - i) / len(df),
                            volume_confirmation=volume[i] / np.mean(volume)
                        ))

            return order_blocks

        except Exception as e:
            logger.error(f"Error detecting order blocks for {timeframe}: {e}")
            return []

    def _detect_structure_shifts(self, df: pd.DataFrame, timeframe: str) -> List[MarketStructureShift]:
        """Detect market structure shifts (CHOCH, BOS, MSS)."""
        try:
            shifts = []

            if df.empty or len(df) < 30:
                return shifts

            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            # Find swing points
            swing_highs = self.trend_analyzer._find_swing_points(high, 'high')
            swing_lows = self.trend_analyzer._find_swing_points(low, 'low')

            # Detect CHOCH (Change of Character)
            if len(swing_highs) >= 3:
                for i in range(len(swing_highs) - 2):
                    h1, h2, h3 = swing_highs[i], swing_highs[i+1], swing_highs[i+2]
                    if high[h2] > high[h1] and high[h3] < high[h2]:
                        shifts.append(MarketStructureShift(
                            shift_type='CHOCH',
                            direction='bearish',
                            price_level=high[h2],
                            timeframes={timeframe},
                            confidence=0.7,
                            strength=abs(high[h2] - high[h3]) / high[h2],
                            timestamp=df.index[h3]
                        ))

            if len(swing_lows) >= 3:
                for i in range(len(swing_lows) - 2):
                    l1, l2, l3 = swing_lows[i], swing_lows[i+1], swing_lows[i+2]
                    if low[l2] < low[l1] and low[l3] > low[l2]:
                        shifts.append(MarketStructureShift(
                            shift_type='CHOCH',
                            direction='bullish',
                            price_level=low[l2],
                            timeframes={timeframe},
                            confidence=0.7,
                            strength=abs(low[l3] - low[l2]) / low[l2],
                            timestamp=df.index[l3]
                        ))

            return shifts

        except Exception as e:
            logger.error(f"Error detecting structure shifts for {timeframe}: {e}")
            return []

    def _generate_confluence_scores(self, symbol: str,
                                  timeframe_analyses: Dict[str, Any],
                                  current_price: float) -> List[ConfluenceScore]:
        """Generate confluence scores for key price levels."""
        confluence_scores = []

        try:
            # Collect all key price levels from all timeframes
            all_levels = set()
            level_sources = defaultdict(list)

            for timeframe, analysis in timeframe_analyses.items():
                if not analysis:
                    continue

                trend = analysis.get('trend')
                if trend:
                    for level in trend.support_levels + trend.resistance_levels:
                        all_levels.add(round(level, 2))
                        level_sources[round(level, 2)].append(f"{timeframe}_trend")

                # Add order block levels
                for ob in analysis.get('order_blocks', []):
                    level = round(ob.price_level, 2)
                    all_levels.add(level)
                    level_sources[level].append(f"{timeframe}_order_block")

                # Add structure shift levels
                for shift in analysis.get('structure_shifts', []):
                    level = round(shift.price_level, 2)
                    all_levels.add(level)
                    level_sources[level].append(f"{timeframe}_structure_shift")

            # Generate confluence scores for each level
            for level in all_levels:
                score = self._calculate_confluence_score(
                    level, timeframe_analyses, current_price, level_sources[level]
                )
                if score.overall_score > 0.3:  # Only include significant confluence
                    confluence_scores.append(score)

            # Add current price level
            current_score = self._calculate_confluence_score(
                current_price, timeframe_analyses, current_price, ['current_price']
            )
            if current_score.overall_score > 0.2:
                confluence_scores.append(current_score)

        except Exception as e:
            logger.error(f"Error generating confluence scores: {e}")

        return confluence_scores

    def _calculate_confluence_score(self, price_level: float,
                                  timeframe_analyses: Dict[str, Any],
                                  current_price: float,
                                  sources: List[str]) -> ConfluenceScore:
        """Calculate comprehensive confluence score for a price level."""
        try:
            # Initialize score components
            trend_alignment = 0.0
            level_confluence = 0.0
            volume_confirmation = 0.0
            timeframe_agreement = 0.0
            signal_strength = 0.0

            supporting_factors = []
            opposing_factors = []

            # Analyze each timeframe's contribution
            agreeing_timeframes = 0
            total_timeframes = len(timeframe_analyses)

            for timeframe, analysis in timeframe_analyses.items():
                if not analysis:
                    continue

                trend = analysis.get('trend')
                if trend:
                    # Check trend alignment
                    if price_level in trend.support_levels:
                        if trend.direction == TrendDirection.BULLISH:
                            trend_alignment += 0.2
                            supporting_factors.append(f"{timeframe}_support_bullish")
                        else:
                            opposing_factors.append(f"{timeframe}_support_bearish")
                        level_confluence += 0.15
                        agreeing_timeframes += 1

                    elif price_level in trend.resistance_levels:
                        if trend.direction == TrendDirection.BEARISH:
                            trend_alignment += 0.2
                            supporting_factors.append(f"{timeframe}_resistance_bearish")
                        else:
                            opposing_factors.append(f"{timeframe}_resistance_bullish")
                        level_confluence += 0.15
                        agreeing_timeframes += 1

                # Check order blocks
                for ob in analysis.get('order_blocks', []):
                    if abs(ob.price_level - price_level) / price_level < 0.005:  # 0.5% tolerance
                        level_confluence += 0.25
                        volume_confirmation += ob.volume_confirmation * 0.2
                        supporting_factors.append(f"{timeframe}_order_block")

                # Check structure shifts
                for shift in analysis.get('structure_shifts', []):
                    if abs(shift.price_level - price_level) / price_level < 0.005:
                        signal_strength += shift.confidence * 0.3
                        supporting_factors.append(f"{timeframe}_{shift.shift_type}")

            # Calculate timeframe agreement
            if total_timeframes > 0:
                timeframe_agreement = agreeing_timeframes / total_timeframes

            # Calculate overall score
            overall_score = (
                trend_alignment * 0.3 +
                level_confluence * 0.3 +
                volume_confirmation * 0.2 +
                timeframe_agreement * 0.1 +
                signal_strength * 0.1
            )

            # Calculate risk/reward ratio (simplified)
            risk_reward = self._calculate_risk_reward(price_level, current_price, timeframe_analyses)

            # Calculate confidence
            confidence = min(1.0, overall_score * timeframe_agreement)

            return ConfluenceScore(
                price_level=price_level,
                overall_score=min(1.0, overall_score),
                trend_alignment=min(1.0, trend_alignment),
                level_confluence=min(1.0, level_confluence),
                volume_confirmation=min(1.0, volume_confirmation),
                timeframe_agreement=timeframe_agreement,
                signal_strength=min(1.0, signal_strength),
                risk_reward_ratio=risk_reward,
                confidence=confidence,
                supporting_factors=supporting_factors,
                opposing_factors=opposing_factors
            )

        except Exception as e:
            logger.error(f"Error calculating confluence score: {e}")
            return ConfluenceScore(
                price_level=price_level,
                overall_score=0.0,
                trend_alignment=0.0,
                level_confluence=0.0,
                volume_confirmation=0.0,
                timeframe_agreement=0.0,
                signal_strength=0.0,
                risk_reward_ratio=1.0,
                confidence=0.0,
                supporting_factors=[],
                opposing_factors=[]
            )

    def _calculate_risk_reward(self, price_level: float, current_price: float,
                             timeframe_analyses: Dict[str, Any]) -> float:
        """Calculate risk/reward ratio for a price level."""
        try:
            # Simplified risk/reward calculation
            distance_to_level = abs(current_price - price_level) / current_price

            # Find nearest opposite level for stop loss/target
            all_levels = []
            for analysis in timeframe_analyses.values():
                if not analysis:
                    continue
                trend = analysis.get('trend')
                if trend:
                    all_levels.extend(trend.support_levels)
                    all_levels.extend(trend.resistance_levels)

            if not all_levels:
                return 1.0

            # Find nearest opposite level
            opposite_levels = [level for level in all_levels
                             if abs(level - price_level) / price_level > 0.01]

            if not opposite_levels:
                return 1.0

            nearest_opposite = min(opposite_levels, key=lambda x: abs(x - price_level))
            potential_move = abs(nearest_opposite - price_level) / price_level

            if potential_move > 0:
                return min(5.0, potential_move / max(0.001, distance_to_level))

            return 1.0

        except Exception as e:
            logger.error(f"Error calculating risk/reward: {e}")
            return 1.0

    def get_cached_analysis(self, symbol: str, max_age_minutes: int = 5) -> Optional[List[ConfluenceScore]]:
        """Get cached confluence analysis if available and fresh."""
        try:
            if symbol not in self.confluence_cache:
                return None

            cache_time = self.cache_timestamps.get(symbol)
            if not cache_time:
                return None

            age = (datetime.utcnow() - cache_time).total_seconds() / 60
            if age > max_age_minutes:
                return None

            return self.confluence_cache[symbol].copy()

        except Exception as e:
            logger.error(f"Error getting cached analysis: {e}")
            return None

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached analysis data."""
        try:
            if symbol:
                if symbol in self.confluence_cache:
                    del self.confluence_cache[symbol]
                if symbol in self.cache_timestamps:
                    del self.cache_timestamps[symbol]
            else:
                self.confluence_cache.clear()
                self.cache_timestamps.clear()

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance and analysis metrics."""
        return {
            'cached_symbols': list(self.confluence_cache.keys()),
            'total_cached_analyses': sum(len(scores) for scores in self.confluence_cache.values()),
            'cache_timestamps': {k: v.isoformat() for k, v in self.cache_timestamps.items()}
        }