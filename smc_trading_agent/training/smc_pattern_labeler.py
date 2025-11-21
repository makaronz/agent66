#!/usr/bin/env python3
"""
SMC Pattern Labeling Engine

This module provides comprehensive SMC pattern detection and labeling for training ML models.
It identifies successful and unsuccessful SMC patterns and creates training labels.

Key Features:
- Order Block detection and outcome tracking
- CHOCH/BOS event labeling with success rates
- Liquidity Sweep identification and subsequent movement tracking
- FVG formation and fill rate analysis
- Multi-timeframe confluence zone labeling
- Binary and multi-class label generation
- Pattern success rate calculation by market conditions
"""

import asyncio
import logging
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import talib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """SMC pattern types for labeling."""
    ORDER_BLOCK = "order_block"
    CHOCH = "choch"  # Change of Character
    BOS = "bos"      # Break of Structure
    LIQUIDITY_SWEEP = "liquidity_sweep"
    FVG = "fvg"      # Fair Value Gap
    MARKUP_MAKEDOWN = "markup_makedown"


class OutcomeType(Enum):
    """Pattern outcome types."""
    SUCCESSFUL = "successful"
    FAILED = "failed"
    NEUTRAL = "neutral"


@dataclass
class PatternLabel:
    """Complete pattern label with outcome tracking."""
    pattern_id: str
    pattern_type: PatternType
    timestamp: datetime
    symbol: str
    timeframe: str

    # Pattern characteristics
    entry_price: float
    direction: str  # 'bullish' or 'bearish'
    strength: float

    # Price levels
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float

    # Outcome tracking
    outcome: OutcomeType
    outcome_timestamp: Optional[datetime]
    max_profit: float
    max_loss: float
    exit_price: float
    holding_period_hours: float

    # Market context
    volatility_at_entry: float
    volume_at_entry: float
    market_regime: str

    # Multi-timeframe confluence
    mtf_confluence_score: float
    higher_timeframe_trend: str

    # Labels for ML training
    binary_label: int  # 1 for profitable, 0 for unprofitable
    multi_class_label: int  # 0: failed, 1: small_profit, 2: good_profit, 3: excellent_profit
    confidence_score: float

    # Additional features
    price_momentum: float
    volume_ratio: float
    rsi_at_entry: float


@dataclass
class LabelingConfig:
    """Configuration for pattern labeling."""

    # Outcome tracking parameters
    min_holding_period_hours: float = 1.0
    max_holding_period_hours: float = 168.0  # 1 week
    profit_threshold_pct: float = 0.5  # 0.5% minimum profit
    loss_threshold_pct: float = 0.3   # 0.3% maximum loss before considering failed

    # Pattern detection parameters
    min_order_block_strength: float = 0.5
    min_liquidity_sweep_ratio: float = 1.5
    min_fvg_size_pct: float = 0.1
    choch_confirmation_candles: int = 3

    # Multi-timeframe analysis
    mtf_timeframes: List[str] = None
    confluence_threshold: float = 0.7

    # Market regime detection
    volatility_window: int = 20
    trend_window: int = 50

    # Data processing
    batch_size: int = 1000
    parallel_processing: bool = True

    def __post_init__(self):
        if self.mtf_timeframes is None:
            self.mtf_timeframes = ['5m', '15m', '1h', '4h', '1d']


class SMCPatternLabeler:
    """
    Advanced SMC pattern detection and labeling engine.

    Identifies SMC patterns in historical data and evaluates their outcomes
    to create high-quality training labels for ML models.
    """

    def __init__(self, config: LabelingConfig):
        """
        Initialize SMC pattern labeler.

        Args:
            config: Labeling configuration
        """
        self.config = config

        # Technical analysis parameters
        self.atr_period = 14
        self.rsi_period = 14
        self.ma_short = 20
        self.ma_long = 50

        # Pattern detection thresholds
        self.swing_point_threshold = 2  # Minimum candles for swing point
        self.structure_break_threshold = 0.001  # 0.1% break confirmation

        # Market regime definitions
        self.regime_thresholds = {
            'trending': {'min_adx': 25, 'min_trend_strength': 0.6},
            'ranging': {'max_adx': 20, 'max_volatility': 0.02},
            'volatile': {'min_volatility': 0.03}
        }

        logger.info("SMC Pattern Labeler initialized")

    async def label_historical_data(self, data: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternLabel]:
        """
        Label SMC patterns in historical data.

        Args:
            data: OHLCV historical data
            symbol: Trading symbol
            timeframe: Data timeframe

        Returns:
            List[PatternLabel]: Labeled patterns with outcomes
        """
        try:
            logger.info(f"Starting pattern labeling for {symbol} {timeframe} ({len(data)} records)")

            # Pre-process data
            data = self._preprocess_data(data)

            # Detect patterns
            patterns = await self._detect_all_patterns(data, symbol, timeframe)

            # Evaluate outcomes
            labeled_patterns = await self._evaluate_pattern_outcomes(patterns, data)

            # Calculate multi-timeframe confluence
            if len(self.config.mtf_timeframes) > 1:
                labeled_patterns = await self._calculate_mtf_confluence(labeled_patterns, symbol)

            # Generate ML labels
            for pattern in labeled_patterns:
                pattern.binary_label = self._calculate_binary_label(pattern)
                pattern.multi_class_label = self._calculate_multi_class_label(pattern)
                pattern.confidence_score = self._calculate_confidence_score(pattern)

            logger.info(f"Pattern labeling completed: {len(labeled_patterns)} patterns labeled")
            return labeled_patterns

        except Exception as e:
            logger.error(f"Pattern labeling failed: {str(e)}")
            return []

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pre-process data for pattern detection."""
        df = data.copy()

        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Calculate technical indicators
        df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=self.atr_period)
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
        df['ma_short'] = talib.SMA(df['close'].values, timeperiod=self.ma_short)
        df['ma_long'] = talib.SMA(df['close'].values, timeperiod=self.ma_long)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'].values, timeperiod=20)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower

        # Volume indicators
        df['volume_ma'] = talib.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Price momentum
        df['price_momentum'] = df['close'].pct_change(periods=5)

        # Market regime indicators
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()

        # ADX for trend strength
        df['adx'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)

        # Fill NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')

        return df

    async def _detect_all_patterns(self, data: pd.DataFrame, symbol: str, timeframe: str) -> List[PatternLabel]:
        """Detect all SMC patterns in the data."""
        patterns = []

        # Detect different pattern types
        order_blocks = self._detect_order_blocks(data)
        coch_patterns = self._detect_choch_patterns(data)
        bos_patterns = self._detect_bos_patterns(data)
        liquidity_sweeps = self._detect_liquidity_sweeps(data)
        fvg_patterns = self._detect_fvg_patterns(data)

        # Convert to PatternLabel objects
        for ob in order_blocks:
            pattern = self._create_pattern_label(ob, PatternType.ORDER_BLOCK, symbol, timeframe, data)
            if pattern:
                patterns.append(pattern)

        for coch in coch_patterns:
            pattern = self._create_pattern_label(coch, PatternType.CHOCH, symbol, timeframe, data)
            if pattern:
                patterns.append(pattern)

        for bos in bos_patterns:
            pattern = self._create_pattern_label(bos, PatternType.BOS, symbol, timeframe, data)
            if pattern:
                patterns.append(pattern)

        for sweep in liquidity_sweeps:
            pattern = self._create_pattern_label(sweep, PatternType.LIQUIDITY_SWEEP, symbol, timeframe, data)
            if pattern:
                patterns.append(pattern)

        for fvg in fvg_patterns:
            pattern = self._create_pattern_label(fvg, PatternType.FVG, symbol, timeframe, data)
            if pattern:
                patterns.append(pattern)

        logger.info(f"Detected patterns: Order Blocks={len(order_blocks)}, CHOCH={len(coch_patterns)}, "
                   f"BOS={len(bos_patterns)}, Sweeps={len(liquidity_sweeps)}, FVG={len(fvg_patterns)}")

        return patterns

    def _detect_order_blocks(self, data: pd.DataFrame) -> List[Dict]:
        """Detect order blocks in the data."""
        order_blocks = []

        if len(data) < 10:
            return order_blocks

        # Find swing highs and swing lows
        swing_highs = self._find_swing_points(data, direction='high')
        swing_lows = self._find_swing_points(data, direction='low')

        # Create order blocks from swing points
        for swing_high in swing_highs:
            # Bearish order block (sell opportunity)
            candle = data.loc[swing_high]
            order_block_high = candle['high']
            order_block_low = candle['low']

            # Validate order block strength
            if self._validate_order_block_strength(data, swing_high, 'bearish'):
                order_blocks.append({
                    'timestamp': swing_high,
                    'type': 'bearish',
                    'price_level': (order_block_low, order_block_high),
                    'strength': self._calculate_order_block_strength(data, swing_high, 'bearish'),
                    'candles_in_block': 1
                })

        for swing_low in swing_lows:
            # Bullish order block (buy opportunity)
            candle = data.loc[swing_low]
            order_block_low = candle['low']
            order_block_high = candle['high']

            # Validate order block strength
            if self._validate_order_block_strength(data, swing_low, 'bullish'):
                order_blocks.append({
                    'timestamp': swing_low,
                    'type': 'bullish',
                    'price_level': (order_block_low, order_block_high),
                    'strength': self._calculate_order_block_strength(data, swing_low, 'bullish'),
                    'candles_in_block': 1
                })

        return order_blocks

    def _find_swing_points(self, data: pd.DataFrame, direction: str = 'high') -> List[datetime]:
        """Find swing high or swing low points."""
        swing_points = []

        if len(data) < self.swing_point_threshold * 2 + 1:
            return swing_points

        window = self.swing_point_threshold

        for i in range(window, len(data) - window):
            if direction == 'high':
                # Check if current high is highest in the window
                current_high = data.iloc[i]['high']
                is_swing_high = all(
                    current_high >= data.iloc[j]['high']
                    for j in range(i - window, i + window + 1)
                )

                if is_swing_high:
                    swing_points.append(data.index[i])

            elif direction == 'low':
                # Check if current low is lowest in the window
                current_low = data.iloc[i]['low']
                is_swing_low = all(
                    current_low <= data.iloc[j]['low']
                    for j in range(i - window, i + window + 1)
                )

                if is_swing_low:
                    swing_points.append(data.index[i])

        return swing_points

    def _validate_order_block_strength(self, data: pd.DataFrame, timestamp: datetime, direction: str) -> bool:
        """Validate if order block has sufficient strength."""
        try:
            idx = data.index.get_loc(timestamp)

            # Get volume around the swing point
            start_idx = max(0, idx - 2)
            end_idx = min(len(data), idx + 3)

            volume_slice = data.iloc[start_idx:end_idx]['volume']
            avg_volume = volume_slice.mean()

            # Get ATR for volatility context
            atr = data.iloc[max(0, idx-20):idx]['atr'].mean() if idx > 20 else data.iloc[:idx]['atr'].mean()

            # Strength criteria
            volume_strength = avg_volume > data['volume'].mean() * 1.5
            price_range = data.iloc[idx]['high'] - data.iloc[idx]['low']
            range_strength = price_range > atr * 0.5

            return volume_strength and range_strength

        except Exception:
            return False

    def _calculate_order_block_strength(self, data: pd.DataFrame, timestamp: datetime, direction: str) -> float:
        """Calculate order block strength score (0-1)."""
        try:
            idx = data.index.get_loc(timestamp)

            # Volume strength (40%)
            volume_slice = data.iloc[max(0, idx-2):min(len(data), idx+3)]['volume']
            volume_strength = min(volume_slice.mean() / data['volume'].mean(), 3.0) / 3.0

            # Price range strength (30%)
            atr = data.iloc[max(0, idx-20):idx]['atr'].mean() if idx > 20 else 1.0
            price_range = data.iloc[idx]['high'] - data.iloc[idx]['low']
            range_strength = min(price_range / atr, 2.0) / 2.0

            # Momentum strength (30%)
            momentum = abs(data.iloc[idx]['price_momentum'])
            momentum_strength = min(momentum * 100, 1.0)

            total_strength = (volume_strength * 0.4 + range_strength * 0.3 + momentum_strength * 0.3)

            return max(0.0, min(1.0, total_strength))

        except Exception:
            return 0.5

    def _detect_choch_patterns(self, data: pd.DataFrame) -> List[Dict]:
        """Detect Change of Character (CHOCH) patterns."""
        coch_patterns = []

        if len(data) < 50:
            return coch_patterns

        # Look for momentum shifts and structure breaks
        for i in range(20, len(data) - 20):
            current_candle = data.iloc[i]

            # Check for strong momentum candle
            body_size = abs(current_candle['close'] - current_candle['open'])
            candle_range = current_candle['high'] - current_candle['low']

            if body_size / candle_range < 0.6:  # Strong momentum candle has large body
                continue

            # Determine direction
            if current_candle['close'] > current_candle['open']:  # Bullish CHOCH
                # Check for breakout above resistance
                resistance = data.iloc[i-20:i]['high'].max()
                if current_candle['close'] > resistance * 1.001:  # 0.1% breakout
                    coch_patterns.append({
                        'timestamp': data.index[i],
                        'type': 'bullish',
                        'price_level': current_candle['close'],
                        'strength': self._calculate_pattern_strength(data, i, 'choch', 'bullish'),
                        'breakout_level': resistance
                    })

            else:  # Bearish CHOCH
                # Check for breakdown below support
                support = data.iloc[i-20:i]['low'].min()
                if current_candle['close'] < support * 0.999:  # 0.1% breakdown
                    coch_patterns.append({
                        'timestamp': data.index[i],
                        'type': 'bearish',
                        'price_level': current_candle['close'],
                        'strength': self._calculate_pattern_strength(data, i, 'choch', 'bearish'),
                        'breakdown_level': support
                    })

        return coch_patterns

    def _detect_bos_patterns(self, data: pd.DataFrame) -> List[Dict]:
        """Detect Break of Structure (BOS) patterns."""
        bos_patterns = []

        if len(data) < 30:
            return bos_patterns

        # Track market structure
        highs = []
        lows = []

        for i in range(len(data)):
            if i >= 2:
                # Lower highs and lower lows = downtrend
                if (data.iloc[i]['high'] < data.iloc[i-2]['high'] and
                    data.iloc[i-1]['high'] < data.iloc[i-3]['high'] if i >= 4 else True):
                    highs.append(data.index[i])

                # Higher highs and higher lows = uptrend
                if (data.iloc[i]['low'] > data.iloc[i-2]['low'] and
                    data.iloc[i-1]['low'] > data.iloc[i-3]['low'] if i >= 4 else True):
                    lows.append(data.index[i])

        # Identify structure breaks
        for i in range(5, len(data)):
            # Check for break of previous structure
            if len(highs) >= 2 and len(lows) >= 2:
                # Break of downtrend structure
                if data.iloc[i]['high'] > data.loc[highs[-2]]['high']:
                    bos_patterns.append({
                        'timestamp': data.index[i],
                        'type': 'bullish',
                        'price_level': data.iloc[i]['high'],
                        'strength': self._calculate_pattern_strength(data, i, 'bos', 'bullish'),
                        'broken_level': data.loc[highs[-2]]['high']
                    })

                # Break of uptrend structure
                if data.iloc[i]['low'] < data.loc[lows[-2]]['low']:
                    bos_patterns.append({
                        'timestamp': data.index[i],
                        'type': 'bearish',
                        'price_level': data.iloc[i]['low'],
                        'strength': self._calculate_pattern_strength(data, i, 'bos', 'bearish'),
                        'broken_level': data.loc[lows[-2]]['low']
                    })

        return bos_patterns

    def _detect_liquidity_sweeps(self, data: pd.DataFrame) -> List[Dict]:
        """Detect liquidity sweep patterns."""
        sweeps = []

        if len(data) < 20:
            return sweeps

        for i in range(10, len(data) - 10):
            current_candle = data.iloc[i]

            # Check for sweep above recent high
            if len(data) >= i + 10:
                recent_high = data.iloc[i-10:i]['high'].max()
                if current_candle['high'] > recent_high * 1.001:  # New high
                    # Check if price quickly reverses
                    if (i + 5 < len(data) and
                        data.iloc[i+1:i+6]['low'].min() < current_candle['low'] * 0.998):
                        sweeps.append({
                            'timestamp': data.index[i],
                            'type': 'bearish',
                            'price_level': current_candle['high'],
                            'strength': self._calculate_pattern_strength(data, i, 'sweep', 'bearish'),
                            'swept_level': recent_high,
                            'reversal_low': data.iloc[i+1:i+6]['low'].min()
                        })

            # Check for sweep below recent low
            if len(data) >= i + 10:
                recent_low = data.iloc[i-10:i]['low'].min()
                if current_candle['low'] < recent_low * 0.999:  # New low
                    # Check if price quickly reverses
                    if (i + 5 < len(data) and
                        data.iloc[i+1:i+6]['high'].max() > current_candle['high'] * 1.002):
                        sweeps.append({
                            'timestamp': data.index[i],
                            'type': 'bullish',
                            'price_level': current_candle['low'],
                            'strength': self._calculate_pattern_strength(data, i, 'sweep', 'bullish'),
                            'swept_level': recent_low,
                            'reversal_high': data.iloc[i+1:i+6]['high'].max()
                        })

        return sweeps

    def _detect_fvg_patterns(self, data: pd.DataFrame) -> List[Dict]:
        """Detect Fair Value Gap (FVG) patterns."""
        fvgs = []

        if len(data) < 3:
            return fvgs

        for i in range(1, len(data) - 1):
            prev_candle = data.iloc[i-1]
            current_candle = data.iloc[i]
            next_candle = data.iloc[i+1]

            # Bullish FVG (gap up)
            if (current_candle['low'] > prev_candle['high'] and
                next_candle['low'] > current_candle['high']):
                gap_size = current_candle['low'] - prev_candle['high']
                gap_ratio = gap_size / prev_candle['close']

                if gap_ratio > self.config.min_fvg_size_pct / 100:
                    fvgs.append({
                        'timestamp': data.index[i],
                        'type': 'bullish',
                        'price_level': (prev_candle['high'], current_candle['low']),
                        'gap_size': gap_size,
                        'gap_ratio': gap_ratio,
                        'strength': min(gap_ratio * 10, 1.0)  # Scale to 0-1
                    })

            # Bearish FVG (gap down)
            elif (current_candle['high'] < prev_candle['low'] and
                  next_candle['high'] < current_candle['low']):
                gap_size = prev_candle['low'] - current_candle['high']
                gap_ratio = gap_size / prev_candle['close']

                if gap_ratio > self.config.min_fvg_size_pct / 100:
                    fvgs.append({
                        'timestamp': data.index[i],
                        'type': 'bearish',
                        'price_level': (current_candle['high'], prev_candle['low']),
                        'gap_size': gap_size,
                        'gap_ratio': gap_ratio,
                        'strength': min(gap_ratio * 10, 1.0)
                    })

        return fvgs

    def _calculate_pattern_strength(self, data: pd.DataFrame, index: int, pattern_type: str, direction: str) -> float:
        """Calculate pattern strength score (0-1)."""
        try:
            candle = data.iloc[index]

            # Volume strength (40%)
            volume_strength = min(candle['volume'] / data['volume'].mean(), 2.0) / 2.0

            # Momentum strength (30%)
            momentum = abs(candle['price_momentum'])
            momentum_strength = min(momentum * 100, 1.0)

            # Pattern-specific strength (30%)
            if pattern_type == 'choch':
                # Strong breakout strength
                atr = candle['atr']
                breakout_size = abs(candle['close'] - candle['open'])
                breakout_strength = min(breakout_size / atr, 1.0)
            elif pattern_type == 'bos':
                # Structure break strength
                breakout_strength = min(candle['adx'] / 50, 1.0)  # Use ADX as proxy
            elif pattern_type == 'sweep':
                # Reversal strength
                reversal_strength = min(abs(candle['rsi'] - 50) / 50, 1.0)
            else:
                breakout_strength = 0.5

            total_strength = (volume_strength * 0.4 + momentum_strength * 0.3 + breakout_strength * 0.3)

            return max(0.0, min(1.0, total_strength))

        except Exception:
            return 0.5

    def _create_pattern_label(self, pattern_data: Dict, pattern_type: PatternType,
                            symbol: str, timeframe: str, data: pd.DataFrame) -> Optional[PatternLabel]:
        """Create PatternLabel from pattern data."""
        try:
            timestamp = pattern_data['timestamp']
            direction = pattern_data['type']
            strength = pattern_data['strength']

            # Get entry price
            if pattern_type == PatternType.ORDER_BLOCK:
                price_level = pattern_data['price_level']
                entry_price = price_level[0] if direction == 'bullish' else price_level[1]
            else:
                entry_price = pattern_data['price_level']

            # Calculate stop loss and take profit
            if direction == 'bullish':
                stop_loss = entry_price * 0.98  # 2% SL
                take_profit = entry_price * 1.04  # 4% TP
            else:
                stop_loss = entry_price * 1.02  # 2% SL
                take_profit = entry_price * 0.96  # 4% TP

            risk_reward_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss)

            # Get market context
            idx = data.index.get_loc(timestamp)
            volatility = data.iloc[idx]['volatility']
            volume = data.iloc[idx]['volume']
            rsi = data.iloc[idx]['rsi']
            momentum = data.iloc[idx]['price_momentum']
            volume_ratio = data.iloc[idx]['volume_ratio']

            market_regime = self._determine_market_regime(data, idx)

            pattern_label = PatternLabel(
                pattern_id=f"{symbol}_{timeframe}_{pattern_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                pattern_type=pattern_type,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                entry_price=entry_price,
                direction=direction,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio,
                outcome=OutcomeType.NEUTRAL,  # Will be determined later
                outcome_timestamp=None,
                max_profit=0.0,
                max_loss=0.0,
                exit_price=0.0,
                holding_period_hours=0.0,
                volatility_at_entry=volatility,
                volume_at_entry=volume,
                market_regime=market_regime,
                mtf_confluence_score=0.5,  # Will be calculated later
                higher_timeframe_trend="neutral",
                binary_label=0,  # Will be calculated later
                multi_class_label=0,  # Will be calculated later
                confidence_score=0.5,  # Will be calculated later
                price_momentum=momentum,
                volume_ratio=volume_ratio,
                rsi_at_entry=rsi
            )

            return pattern_label

        except Exception as e:
            logger.error(f"Failed to create pattern label: {str(e)}")
            return None

    def _determine_market_regime(self, data: pd.DataFrame, index: int) -> str:
        """Determine market regime at given index."""
        try:
            adx = data.iloc[index]['adx']
            volatility = data.iloc[index]['volatility']

            # Trend strength
            if adx > self.regime_thresholds['trending']['min_adx']:
                return 'trending'
            elif volatility > self.regime_thresholds['volatile']['min_volatility']:
                return 'volatile'
            else:
                return 'ranging'

        except Exception:
            return 'neutral'

    async def _evaluate_pattern_outcomes(self, patterns: List[PatternLabel], data: pd.DataFrame) -> List[PatternLabel]:
        """Evaluate outcomes for all patterns."""
        labeled_patterns = []

        for pattern in patterns:
            try:
                outcome_data = self._evaluate_single_pattern_outcome(pattern, data)

                if outcome_data:
                    pattern.outcome = outcome_data['outcome']
                    pattern.outcome_timestamp = outcome_data['outcome_timestamp']
                    pattern.max_profit = outcome_data['max_profit']
                    pattern.max_loss = outcome_data['max_loss']
                    pattern.exit_price = outcome_data['exit_price']
                    pattern.holding_period_hours = outcome_data['holding_period_hours']

                labeled_patterns.append(pattern)

            except Exception as e:
                logger.error(f"Failed to evaluate outcome for pattern {pattern.pattern_id}: {str(e)}")
                labeled_patterns.append(pattern)

        return labeled_patterns

    def _evaluate_single_pattern_outcome(self, pattern: PatternLabel, data: pd.DataFrame) -> Optional[Dict]:
        """Evaluate outcome for a single pattern."""
        try:
            # Get pattern index
            pattern_idx = data.index.get_loc(pattern.timestamp)

            # Calculate outcome window
            max_holding_bars = int(self.config.max_holding_period_hours * 60 / 5)  # Assuming 5-minute candles

            # Slice future data
            future_start = pattern_idx + 1
            future_end = min(pattern_idx + max_holding_bars, len(data))

            if future_start >= len(data):
                return None

            future_data = data.iloc[future_start:future_end]

            if len(future_data) == 0:
                return None

            # Track maximum profit and loss
            max_profit = 0.0
            max_loss = 0.0
            exit_price = 0.0
            exit_timestamp = None
            outcome = OutcomeType.NEUTRAL

            for i, (timestamp, candle) in enumerate(future_data.iterrows()):
                hours_elapsed = (timestamp - pattern.timestamp).total_seconds() / 3600

                # Check if minimum holding period has passed
                if hours_elapsed < self.config.min_holding_period_hours:
                    continue

                # Calculate current profit/loss
                if pattern.direction == 'bullish':
                    current_profit_pct = (candle['high'] - pattern.entry_price) / pattern.entry_price * 100
                    current_loss_pct = (pattern.entry_price - candle['low']) / pattern.entry_price * 100

                    # Check take profit
                    if candle['high'] >= pattern.take_profit:
                        max_profit = max(max_profit, current_profit_pct)
                        if outcome == OutcomeType.NEUTRAL:
                            outcome = OutcomeType.SUCCESSFUL
                            exit_price = pattern.take_profit
                            exit_timestamp = timestamp
                            break

                    # Check stop loss
                    elif candle['low'] <= pattern.stop_loss:
                        max_loss = min(max_loss, -current_loss_pct)
                        if outcome == OutcomeType.NEUTRAL:
                            outcome = OutcomeType.FAILED
                            exit_price = pattern.stop_loss
                            exit_timestamp = timestamp
                            break

                else:  # bearish
                    current_profit_pct = (pattern.entry_price - candle['low']) / pattern.entry_price * 100
                    current_loss_pct = (candle['high'] - pattern.entry_price) / pattern.entry_price * 100

                    # Check take profit
                    if candle['low'] <= pattern.take_profit:
                        max_profit = max(max_profit, current_profit_pct)
                        if outcome == OutcomeType.NEUTRAL:
                            outcome = OutcomeType.SUCCESSFUL
                            exit_price = pattern.take_profit
                            exit_timestamp = timestamp
                            break

                    # Check stop loss
                    elif candle['high'] >= pattern.stop_loss:
                        max_loss = min(max_loss, -current_loss_pct)
                        if outcome == OutcomeType.NEUTRAL:
                            outcome = OutcomeType.FAILED
                            exit_price = pattern.stop_loss
                            exit_timestamp = timestamp
                            break

                # Update running maxima
                max_profit = max(max_profit, current_profit_pct if pattern.direction == 'bullish' else -current_profit_pct)
                max_loss = min(max_loss, current_loss_pct if pattern.direction == 'bearish' else -current_loss_pct)

            # If no definite outcome, use final price
            if outcome == OutcomeType.NEUTRAL:
                final_candle = future_data.iloc[-1]
                if pattern.direction == 'bullish':
                    final_return = (final_candle['close'] - pattern.entry_price) / pattern.entry_price * 100
                else:
                    final_return = (pattern.entry_price - final_candle['close']) / pattern.entry_price * 100

                if final_return > self.config.profit_threshold_pct:
                    outcome = OutcomeType.SUCCESSFUL
                    max_profit = final_return
                elif final_return < -self.config.loss_threshold_pct:
                    outcome = OutcomeType.FAILED
                    max_loss = abs(final_return)

                exit_price = final_candle['close']
                exit_timestamp = final_candle.name

            return {
                'outcome': outcome,
                'outcome_timestamp': exit_timestamp,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'exit_price': exit_price,
                'holding_period_hours': (exit_timestamp - pattern.timestamp).total_seconds() / 3600 if exit_timestamp else 0
            }

        except Exception as e:
            logger.error(f"Failed to evaluate pattern outcome: {str(e)}")
            return None

    async def _calculate_mtf_confluence(self, patterns: List[PatternLabel], symbol: str) -> List[PatternLabel]:
        """Calculate multi-timeframe confluence scores."""
        # For now, return patterns without MTF analysis
        # In a full implementation, you'd load higher timeframe data
        for pattern in patterns:
            pattern.mtf_confluence_score = 0.5  # Default confluence score
            pattern.higher_timeframe_trend = "neutral"

        return patterns

    def _calculate_binary_label(self, pattern: PatternLabel) -> int:
        """Calculate binary label (1 for profitable, 0 for unprofitable)."""
        return 1 if pattern.outcome == OutcomeType.SUCCESSFUL else 0

    def _calculate_multi_class_label(self, pattern: PatternLabel) -> int:
        """Calculate multi-class label based on profit levels."""
        if pattern.outcome == OutcomeType.FAILED:
            return 0  # Failed
        elif pattern.outcome == OutcomeType.NEUTRAL:
            return 1  # Small profit/neutral
        elif pattern.max_profit < 1.0:
            return 1  # Small profit (<1%)
        elif pattern.max_profit < 3.0:
            return 2  # Good profit (1-3%)
        else:
            return 3  # Excellent profit (>3%)

    def _calculate_confidence_score(self, pattern: PatternLabel) -> float:
        """Calculate confidence score for the pattern."""
        # Base confidence from pattern strength
        confidence = pattern.strength * 0.4

        # Market regime adjustment
        if pattern.market_regime == 'trending':
            confidence += 0.3
        elif pattern.market_regime == 'volatile':
            confidence += 0.1

        # Risk-reward ratio adjustment
        if pattern.risk_reward_ratio >= 2.0:
            confidence += 0.2
        elif pattern.risk_reward_ratio >= 1.5:
            confidence += 0.1

        # Volume strength adjustment
        if pattern.volume_ratio > 1.5:
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    def get_pattern_statistics(self, patterns: List[PatternLabel]) -> Dict[str, Any]:
        """Get comprehensive statistics about labeled patterns."""
        if not patterns:
            return {}

        total_patterns = len(patterns)
        successful_patterns = sum(1 for p in patterns if p.outcome == OutcomeType.SUCCESSFUL)
        failed_patterns = sum(1 for p in patterns if p.outcome == OutcomeType.FAILED)
        neutral_patterns = sum(1 for p in patterns if p.outcome == OutcomeType.NEUTRAL)

        # Success rates by pattern type
        pattern_type_stats = {}
        for pattern_type in PatternType:
            type_patterns = [p for p in patterns if p.pattern_type == pattern_type]
            if type_patterns:
                successful_type = sum(1 for p in type_patterns if p.outcome == OutcomeType.SUCCESSFUL)
                pattern_type_stats[pattern_type.value] = {
                    'total': len(type_patterns),
                    'successful': successful_type,
                    'success_rate': successful_type / len(type_patterns) * 100,
                    'avg_profit': np.mean([p.max_profit for p in type_patterns]),
                    'avg_loss': np.mean([p.max_loss for p in type_patterns])
                }

        # Success rates by market regime
        regime_stats = {}
        for regime in ['trending', 'ranging', 'volatile']:
            regime_patterns = [p for p in patterns if p.market_regime == regime]
            if regime_patterns:
                successful_regime = sum(1 for p in regime_patterns if p.outcome == OutcomeType.SUCCESSFUL)
                regime_stats[regime] = {
                    'total': len(regime_patterns),
                    'successful': successful_regime,
                    'success_rate': successful_regime / len(regime_patterns) * 100
                }

        # Performance metrics
        avg_profit = np.mean([p.max_profit for p in patterns])
        avg_loss = np.mean([p.max_loss for p in patterns if p.outcome == OutcomeType.FAILED])
        avg_holding_period = np.mean([p.holding_period_hours for p in patterns])

        return {
            'total_patterns': total_patterns,
            'success_rate': successful_patterns / total_patterns * 100,
            'successful_patterns': successful_patterns,
            'failed_patterns': failed_patterns,
            'neutral_patterns': neutral_patterns,
            'pattern_type_statistics': pattern_type_stats,
            'market_regime_statistics': regime_stats,
            'average_profit_pct': avg_profit,
            'average_loss_pct': avg_loss,
            'average_holding_period_hours': avg_holding_period,
            'profit_factor': (successful_patterns * avg_profit) / max(failed_patterns * avg_loss, 1),
            'max_profit': max([p.max_profit for p in patterns], default=0),
            'max_loss': max([p.max_loss for p in patterns], default=0)
        }


def create_labeling_config(**kwargs) -> LabelingConfig:
    """Create labeling configuration with sensible defaults."""
    return LabelingConfig(**kwargs)


async def main():
    """Example usage of the SMC pattern labeler."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting SMC Pattern Labeling")

    # Load sample data (in practice, you'd load your historical data)
    # For demo purposes, create synthetic data
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='5min')
    np.random.seed(42)

    # Generate synthetic OHLCV data
    close_prices = 50000 + np.cumsum(np.random.randn(len(dates)) * 10)
    high_prices = close_prices * (1 + np.random.uniform(0, 0.005, len(dates)))
    low_prices = close_prices * (1 - np.random.uniform(0, 0.005, len(dates)))
    open_prices = close_prices + np.random.randn(len(dates)) * 5
    volumes = np.random.uniform(1000, 10000, len(dates))

    data = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)

    # Create configuration
    config = create_labeling_config(
        min_holding_period_hours=2.0,
        max_holding_period_hours=48.0,
        profit_threshold_pct=0.3,
        loss_threshold_pct=0.2,
        parallel_processing=True
    )

    # Initialize labeler
    labeler = SMCPatternLabeler(config)

    # Label patterns
    patterns = await labeler.label_historical_data(data, 'BTCUSDT', '5m')

    # Get statistics
    stats = labeler.get_pattern_statistics(patterns)

    print("\n" + "="*80)
    print("PATTERN LABELING RESULTS")
    print("="*80)
    print(f"Total Patterns Detected: {len(patterns)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.2f}%")
    print(f"Average Profit: {stats.get('average_profit_pct', 0):.2f}%")
    print(f"Average Loss: {stats.get('average_loss_pct', 0):.2f}%")
    print(f"Profit Factor: {stats.get('profit_factor', 0):.2f}")

    # Print pattern type statistics
    pattern_stats = stats.get('pattern_type_statistics', {})
    if pattern_stats:
        print(f"\nPattern Type Statistics:")
        for pattern_type, type_stats in pattern_stats.items():
            print(f"  {pattern_type}: {type_stats['total']} patterns, "
                  f"{type_stats['success_rate']:.1f}% success rate")

    # Save labeled patterns (in a real implementation)
    # patterns_df = pd.DataFrame([asdict(p) for p in patterns])
    # patterns_df.to_csv('labeled_patterns.csv', index=False)


if __name__ == "__main__":
    asyncio.run(main())