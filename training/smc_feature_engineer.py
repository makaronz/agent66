#!/usr/bin/env python3
"""
SMC Feature Engineering Pipeline

This module provides comprehensive feature engineering for SMC-based ML training.
Implements the 16 SMC-specific features identified in the system requirements.

Features:
1. Price Action Features
   - price_momentum: Multi-timeframe price momentum
   - volatility_ratio: Current volatility relative to historical average
   - volume_profile: Volume distribution and analysis

2. SMC Pattern Features
   - order_block_proximity: Distance to nearest order blocks
   - choch_strength: Change of Character pattern strength
   - fvg_size: Fair Value Gap size and intensity
   - liquidity_sweep_strength: Liquidity sweep detection and strength
   - break_of_structure_momentum: BOS pattern momentum

3. Multi-timeframe Features
   - m5_m15_confluence: Confluence between 5m and 15m timeframes
   - h1_h4_alignment: Alignment between 1h and 4h trends
   - daily_trend_strength: Overall daily trend momentum

4. Risk Management Features
   - risk_reward_ratio: Calculated risk-reward for potential trades
   - position_size_optimal: Optimal position sizing based on volatility
   - stop_loss_distance: Optimal stop loss distance

5. Market Microstructure Features
   - bid_ask_spread: Market liquidity indicator
   - order_book_imbalance: Order flow analysis
   - market_depth: Market depth and liquidity analysis
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
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class SMCDataset:
    """Complete SMC dataset with features and labels."""
    features: pd.DataFrame
    labels: pd.Series
    timestamps: pd.DatetimeIndex
    symbol: str
    timeframe: str

    # Metadata
    feature_names: List[str]
    label_type: str  # 'binary', 'multiclass', 'regression'
    created_at: datetime

    # Scaling information
    scaler: Any
    feature_statistics: Dict[str, Dict[str, float]]


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""

    # Price action features
    momentum_periods: List[int] = None
    volatility_windows: List[int] = None
    volume_profile_lookback: int = 100

    # Pattern features
    order_block_lookback: int = 50
    choch_confirmation_candles: int = 3
    fvg_min_size: float = 0.001
    liquidity_sweep_threshold: float = 1.5

    # Multi-timeframe analysis
    mtf_timeframes: List[str] = None
    confluence_threshold: float = 0.7

    # Risk management
    max_risk_per_trade: float = 0.02  # 2%
    atr_multiplier: float = 2.0
    position_sizing_method: str = 'kelly'  # 'kelly', 'fixed', 'volatility'

    # Market microstructure
    order_book_depth: int = 10
    spread_threshold: float = 0.001

    # Feature processing
    scaling_method: str = 'standard'  # 'standard', 'minmax', 'robust'
    pca_components: Optional[int] = None
    remove_correlated: bool = True
    correlation_threshold: float = 0.95

    # Data processing
    batch_size: int = 5000
    handle_missing: str = 'forward_fill'  # 'forward_fill', 'interpolate', 'drop'
    outlier_method: str = 'iqr'  # 'iqr', 'zscore', 'isolation'

    def __post_init__(self):
        if self.momentum_periods is None:
            self.momentum_periods = [5, 10, 20, 50]
        if self.volatility_windows is None:
            self.volatility_windows = [10, 20, 50]
        if self.mtf_timeframes is None:
            self.mtf_timeframes = ['5m', '15m', '1h', '4h', '1d']


class SMCFeatureEngineer:
    """
    Advanced feature engineering for SMC trading patterns.

    Implements comprehensive feature extraction with 16 SMC-specific features,
    multi-timeframe analysis, and advanced preprocessing.
    """

    def __init__(self, config: FeatureConfig):
        """
        Initialize SMC feature engineer.

        Args:
            config: Feature engineering configuration
        """
        self.config = config

        # Initialize scalers
        if config.scaling_method == 'standard':
            self.scaler = StandardScaler()
        elif config.scaling_method == 'minmax':
            self.scaler = MinMaxScaler()
        else:  # robust
            self.scaler = RobustScaler()

        # Technical analysis parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2

        # Feature cache for optimization
        self.feature_cache = {}
        self.feature_statistics = {}

        logger.info(f"SMC Feature Engineer initialized with {len(self.config.mtf_timeframes)} timeframes")

    async def engineer_features(self, data: pd.DataFrame, symbol: str, timeframe: str,
                              patterns: Dict[str, List[Dict]] = None) -> SMCDataset:
        """
        Engineer comprehensive SMC features from market data.

        Args:
            data: OHLCV market data
            symbol: Trading symbol
            timeframe: Data timeframe
            patterns: Optional detected SMC patterns

        Returns:
            SMCDataset: Complete dataset with features and metadata
        """
        try:
            logger.info(f"Starting feature engineering for {symbol} {timeframe} ({len(data)} records)")

            # Preprocess data
            data = self._preprocess_data(data)

            # Extract feature categories
            features = {}

            # 1. Price Action Features (3 features)
            price_features = self._extract_price_features(data)
            features.update(price_features)

            # 2. SMC Pattern Features (5 features)
            pattern_features = self._extract_pattern_features(data, patterns or {})
            features.update(pattern_features)

            # 3. Multi-timeframe Features (3 features)
            mtf_features = await self._extract_mtf_features(data, symbol, timeframe)
            features.update(mtf_features)

            # 4. Risk Management Features (3 features)
            risk_features = self._extract_risk_features(data)
            features.update(risk_features)

            # 5. Market Microstructure Features (2 features)
            microstructure_features = self._extract_microstructure_features(data)
            features.update(microstructure_features)

            # Combine all features
            features_df = pd.DataFrame(features, index=data.index)

            # Clean and validate features
            features_df = self._clean_features(features_df)

            # Apply scaling
            features_scaled = self._apply_scaling(features_df)

            # Generate labels (if patterns provided)
            labels = self._generate_labels(data, patterns or {}) if patterns else pd.Series(0, index=data.index)

            # Create dataset
            dataset = SMCDataset(
                features=features_scaled,
                labels=labels,
                timestamps=data.index,
                symbol=symbol,
                timeframe=timeframe,
                feature_names=list(features_scaled.columns),
                label_type='binary',
                created_at=datetime.now(),
                scaler=self.scaler,
                feature_statistics=self.feature_statistics
            )

            logger.info(f"Feature engineering completed: {len(dataset.feature_names)} features created")
            return dataset

        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            raise

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Preprocess raw market data."""
        df = data.copy()

        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Handle missing data
        if self.config.handle_missing == 'forward_fill':
            df = df.fillna(method='ffill').fillna(method='bfill')
        elif self.config.handle_missing == 'interpolate':
            df = df.interpolate(method='linear')
        else:  # drop
            df = df.dropna()

        # Remove outliers
        if self.config.outlier_method != 'none':
            df = self._remove_outliers(df)

        # Calculate basic technical indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

        # Additional indicators
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
        df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)

        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            df['close'].values, fastperiod=self.macd_fast,
            slowperiod=self.macd_slow, signalperiod=self.macd_signal
        )
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_histogram'] = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'].values, timeperiod=self.bb_period, nbdevup=self.bb_std)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Volume indicators
        df['volume_ma'] = talib.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Fill any remaining NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')

        return df

    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove outliers from price and volume data."""
        if self.config.outlier_method == 'zscore':
            # Z-score method
            from scipy import stats
            z_scores = stats.zscore(df[['open', 'high', 'low', 'close', 'volume']])
            abs_z_scores = np.abs(z_scores)
            filtered_entries = (abs_z_scores < 3).all(axis=1)
            return df[filtered_entries]

        elif self.config.outlier_method == 'iqr':
            # IQR method
            for col in ['open', 'high', 'low', 'close', 'volume']:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

            return df

        else:  # isolation forest or none
            return df

    def _extract_price_features(self, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract price action features (3 features)."""
        features = {}

        # 1. Price momentum - multi-timeframe momentum analysis
        momentum_values = []
        for period in self.config.momentum_periods:
            if len(data) > period:
                momentum = (data['close'] / data['close'].shift(period) - 1).fillna(0)
                momentum_values.append(momentum)
            else:
                momentum_values.append(pd.Series(0, index=data.index))

        # Combine multiple momentum periods with weights
        weights = [0.4, 0.3, 0.2, 0.1]  # More weight to recent periods
        combined_momentum = sum(m * w for m, w in zip(momentum_values[:len(weights)], weights))
        features['price_momentum'] = combined_momentum.values

        # 2. Volatility ratio - current volatility relative to historical average
        volatility_ratios = []
        for window in self.config.volatility_windows:
            if len(data) > window:
                current_vol = data['returns'].rolling(window=20).std().iloc[-1]
                historical_vol = data['returns'].rolling(window=window).std().mean()
                ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
                volatility_ratios.append(ratio)
            else:
                volatility_ratios.append(1.0)

        features['volatility_ratio'] = np.full(len(data), np.mean(volatility_ratios))

        # 3. Volume profile - volume distribution analysis
        # Calculate volume-weighted price and volume deviation
        if len(data) > self.config.volume_profile_lookback:
            vwap = (data['close'] * data['volume']).rolling(window=self.config.volume_profile_lookback).sum() / \
                   data['volume'].rolling(window=self.config.volume_profile_lookback).sum()
            volume_profile = (data['close'] - vwap) / vwap
            features['volume_profile'] = volume_profile.fillna(0).values
        else:
            features['volume_profile'] = np.zeros(len(data))

        return features

    def _extract_pattern_features(self, data: pd.DataFrame, patterns: Dict) -> Dict[str, np.ndarray]:
        """Extract SMC pattern features (5 features)."""
        features = {}

        # Initialize arrays
        n = len(data)
        features['order_block_proximity'] = np.zeros(n)
        features['choch_strength'] = np.zeros(n)
        features['fvg_size'] = np.zeros(n)
        features['liquidity_sweep_strength'] = np.zeros(n)
        features['break_of_structure_momentum'] = np.zeros(n)

        # Order block proximity
        order_blocks = patterns.get('order_blocks', [])
        if order_blocks:
            for i, timestamp in enumerate(data.index):
                min_distance = float('inf')
                max_strength = 0.0

                for ob in order_blocks:
                    ob_timestamp = pd.Timestamp(ob.get('timestamp', '1970-01-01'))
                    time_diff = abs((timestamp - ob_timestamp).total_seconds() / 3600)  # hours

                    if time_diff < 24:  # Only consider order blocks within 24 hours
                        strength = ob.get('strength', 0.5)
                        proximity_score = strength / (1 + time_diff / 6)  # Decay over 6 hours

                        if proximity_score > max_strength:
                            max_strength = proximity_score

                features['order_block_proximity'][i] = max_strength

        # CHOCH strength
        coch_patterns = patterns.get('coch_patterns', [])
        if coch_patterns:
            for i, timestamp in enumerate(data.index):
                max_choch_strength = 0.0

                for coch in coch_patterns:
                    coch_timestamp = pd.Timestamp(coch.get('timestamp', '1970-01-01'))
                    time_diff = abs((timestamp - coch_timestamp).total_seconds() / 3600)

                    if time_diff < 12:  # Within 12 hours
                        strength = coch.get('strength', 0.5)
                        decayed_strength = strength * np.exp(-time_diff / 6)  # Exponential decay
                        max_choch_strength = max(max_choch_strength, decayed_strength)

                features['choch_strength'][i] = max_choch_strength

        # FVG size
        fvg_patterns = patterns.get('fvg_patterns', [])
        if fvg_patterns:
            for i, timestamp in enumerate(data.index):
                max_fvg_size = 0.0

                for fvg in fvg_patterns:
                    fvg_timestamp = pd.Timestamp(fvg.get('timestamp', '1970-01-01'))
                    time_diff = abs((timestamp - fvg_timestamp).total_seconds() / 3600)

                    if time_diff < 8:  # Within 8 hours
                        gap_ratio = fvg.get('gap_ratio', 0.001)
                        decayed_size = gap_ratio * np.exp(-time_diff / 4)
                        max_fvg_size = max(max_fvg_size, decayed_size)

                features['fvg_size'][i] = min(max_fvg_size * 100, 1.0)  # Scale and cap

        # Liquidity sweep strength
        liquidity_sweeps = patterns.get('liquidity_sweeps', [])
        if liquidity_sweeps:
            for i, timestamp in enumerate(data.index):
                max_sweep_strength = 0.0

                for sweep in liquidity_sweeps:
                    sweep_timestamp = pd.Timestamp(sweep.get('timestamp', '1970-01-01'))
                    time_diff = abs((timestamp - sweep_timestamp).total_seconds() / 3600)

                    if time_diff < 6:  # Within 6 hours
                        strength = sweep.get('strength', 0.5)
                        decayed_strength = strength * np.exp(-time_diff / 3)
                        max_sweep_strength = max(max_sweep_strength, decayed_strength)

                features['liquidity_sweep_strength'][i] = max_sweep_strength

        # Break of structure momentum
        bos_patterns = patterns.get('bos_patterns', [])
        if bos_patterns:
            for i, timestamp in enumerate(data.index):
                max_bos_momentum = 0.0

                for bos in bos_patterns:
                    bos_timestamp = pd.Timestamp(bos.get('timestamp', '1970-01-01'))
                    time_diff = abs((timestamp - bos_timestamp).total_seconds() / 3600)

                    if time_diff < 10:  # Within 10 hours
                        strength = bos.get('strength', 0.5)
                        momentum = strength * np.exp(-time_diff / 5)
                        max_bos_momentum = max(max_bos_momentum, momentum)

                features['break_of_structure_momentum'][i] = max_bos_momentum

        return features

    async def _extract_mtf_features(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, np.ndarray]:
        """Extract multi-timeframe features (3 features)."""
        features = {}
        n = len(data)

        # Initialize with default values
        features['m5_m15_confluence'] = np.full(n, 0.5)
        features['h1_h4_alignment'] = np.full(n, 0.5)
        features['daily_trend_strength'] = np.full(n, 0.0)

        # In a real implementation, you would load higher timeframe data
        # For now, simulate MTF features using the existing data with different windows

        try:
            # 1. M5-M15 confluence (confluence between short timeframes)
            short_momentum = data['close'].pct_change(periods=5).fillna(0)
            medium_momentum = data['close'].pct_change(periods=15).fillna(0)

            # Calculate correlation-based confluence
            rolling_correlation = short_momentum.rolling(window=20).corr(medium_momentum)
            confluence_score = (rolling_correlation + 1) / 2  # Scale to 0-1
            features['m5_m15_confluence'] = confluence_score.fillna(0.5).values

            # 2. H1-H4 alignment (trend alignment between medium timeframes)
            short_trend = data['close'].rolling(window=50).mean()
            long_trend = data['close'].rolling(window=200).mean()

            trend_alignment = np.where(short_trend > long_trend, 1.0, 0.0)
            smooth_alignment = pd.Series(trend_alignment).rolling(window=20).mean()
            features['h1_h4_alignment'] = smooth_alignment.fillna(0.5).values

            # 3. Daily trend strength (overall trend momentum)
            # Use ADX and directional movement for trend strength
            adx = talib.ADX(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
            plus_di = talib.PLUS_DI(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
            minus_di = talib.MINUS_DI(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)

            # Normalize ADX to 0-1 range (typical range 0-100)
            normalized_adx = np.minimum(adx / 50, 1.0)

            # Apply directional bias
            directional_bias = (plus_di - minus_di) / 100  # Normalize to -1 to 1
            trend_strength = normalized_adx * np.abs(directional_bias)

            features['daily_trend_strength'] = np.nan_to_num(trend_strength, nan=0.0)

        except Exception as e:
            logger.warning(f"MTF feature calculation failed: {str(e)}")
            # Keep default values if calculation fails

        return features

    def _extract_risk_features(self, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract risk management features (3 features)."""
        features = {}

        # 1. Risk-reward ratio (based on ATR and recent price ranges)
        atr = data['atr'].fillna(method='ffill').fillna(1.0)
        avg_range = (data['high'] - data['low']).rolling(window=20).mean()

        # Calculate potential risk-reward based on volatility
        risk_reward = avg_range / (atr * 2)  # Target: 2x ATR, Risk: ATR
        features['risk_reward_ratio'] = np.minimum(risk_reward.fillna(2.0), 5.0).values  # Cap at 5:1

        # 2. Optimal position size (Kelly criterion or volatility-based)
        returns = data['returns'].fillna(0)

        if self.config.position_sizing_method == 'kelly':
            # Kelly criterion: f = (bp - q) / b where b=odds, p=win_rate, q=loss_rate
            win_rate = (returns > 0).rolling(window=100).mean()
            avg_win = returns[returns > 0].rolling(window=100).mean()
            avg_loss = returns[returns < 0].rolling(window=100).mean().abs()

            # Simplified Kelly fraction
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = np.nan_to_num(kelly_fraction, nan=0.01, posinf=0.25, neginf=0.01)
            kelly_fraction = np.clip(kelly_fraction, 0.01, 0.25)  # 1% to 25% of capital

            features['position_size_optimal'] = kelly_fraction.values
        else:
            # Volatility-based position sizing
            volatility = returns.rolling(window=20).std()
            base_size = 0.02  # 2% base position
            vol_adj_size = base_size / (volatility * np.sqrt(252) + 0.01)  # Adjust for volatility
            features['position_size_optimal'] = np.clip(vol_adj_size.fillna(0.02), 0.005, 0.1).values

        # 3. Stop loss distance (ATR-based with volatility adjustment)
        # Base stop loss at 2x ATR, adjusted for market conditions
        base_stop_distance = atr * self.config.atr_multiplier

        # Adjust based on volatility (tighter stops in low volatility, wider in high volatility)
        vol_adjustment = data['volatility'] / data['volatility'].rolling(window=50).mean()
        adjusted_stop_distance = base_stop_distance * (1 + vol_adjustment)

        # Normalize as percentage of price
        stop_distance_pct = adjusted_stop_distance / data['close']
        features['stop_loss_distance'] = np.clip(stop_distance_pct.fillna(0.02), 0.005, 0.1).values

        return features

    def _extract_microstructure_features(self, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract market microstructure features (2 features)."""
        features = {}

        # 1. Bid-ask spread estimation (using price range as proxy)
        # In real implementation, you'd use order book data
        high_low_spread = (data['high'] - data['low']) / data['close']

        # Smooth the spread estimate
        spread_ma = high_low_spread.rolling(window=10).mean()
        spread_volatility = high_low_spread.rolling(window=20).std()

        # Normalize spread (typical spread should be 0.1-0.5% for liquid assets)
        spread_estimate = (spread_ma + spread_volatility * 0.5) * 100  # Convert to percentage
        features['bid_ask_spread'] = np.clip(spread_estimate.fillna(0.2), 0.01, 2.0).values

        # 2. Order book imbalance estimation (using volume and price action)
        # In real implementation, you'd use actual order book data
        volume_ratio = data['volume'] / data['volume'].rolling(window=20).mean()

        # Price pressure indicator
        price_change = data['close'].pct_change()
        volume_price_correlation = price_change.rolling(window=10).corr(volume_ratio)

        # Imbalance score (positive = buying pressure, negative = selling pressure)
        imbalance_score = volume_price_correlation * volume_ratio
        features['order_book_imbalance'] = np.clip(imbalance_score.fillna(0), -2.0, 2.0).values

        return features

    def _clean_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate features."""
        # Remove infinite values
        features_df = features_df.replace([np.inf, -np.inf], np.nan)

        # Handle missing values
        features_df = features_df.fillna(method='ffill').fillna(method='bfill').fillna(0)

        # Remove highly correlated features if enabled
        if self.config.remove_correlated:
            features_df = self._remove_correlated_features(features_df)

        return features_df

    def _remove_correlated_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Remove highly correlated features."""
        if len(features_df.columns) <= 1:
            return features_df

        # Calculate correlation matrix
        corr_matrix = features_df.corr().abs()

        # Find highly correlated pairs
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # Find features to remove
        to_remove = [column for column in upper_triangle.columns
                    if any(upper_triangle[column] > self.config.correlation_threshold)]

        # Remove correlated features
        if to_remove:
            logger.info(f"Removing {len(to_remove)} highly correlated features: {to_remove}")
            features_df = features_df.drop(columns=to_remove)

        return features_df

    def _apply_scaling(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Apply scaling to features."""
        # Fit scaler if not already fitted
        if not hasattr(self.scaler, 'mean_'):
            scaled_features = self.scaler.fit_transform(features_df)
        else:
            scaled_features = self.scaler.transform(features_df)

        # Create DataFrame with scaled features
        scaled_df = pd.DataFrame(
            scaled_features,
            index=features_df.index,
            columns=features_df.columns
        )

        # Store feature statistics
        self.feature_statistics = {
            'mean': features_df.mean().to_dict(),
            'std': features_df.std().to_dict(),
            'min': features_df.min().to_dict(),
            'max': features_df.max().to_dict()
        }

        return scaled_df

    def _generate_labels(self, data: pd.DataFrame, patterns: Dict) -> pd.Series:
        """Generate labels from patterns."""
        labels = pd.Series(0, index=data.index)  # Default to neutral

        try:
            # Process pattern outcomes to generate labels
            all_patterns = []
            for pattern_list in patterns.values():
                all_patterns.extend(pattern_list)

            for pattern in all_patterns:
                try:
                    pattern_time = pd.Timestamp(pattern.get('timestamp', '1970-01-01'))

                    # Find the closest data point
                    closest_idx = data.index.get_indexer([pattern_time], method='nearest')[0]
                    if closest_idx >= 0 and closest_idx < len(data):
                        # Generate label based on pattern outcome
                        outcome = pattern.get('outcome', 'neutral')
                        if outcome == 'successful':
                            labels.iloc[closest_idx] = 1
                        elif outcome == 'failed':
                            labels.iloc[closest_idx] = 0
                        else:  # neutral
                            labels.iloc[closest_idx] = 0.5

                except Exception as e:
                    logger.debug(f"Failed to process pattern for labeling: {str(e)}")
                    continue

        except Exception as e:
            logger.warning(f"Label generation failed: {str(e)}")

        return labels

    def apply_pca(self, dataset: SMCDataset, n_components: int = None) -> SMCDataset:
        """Apply Principal Component Analysis for dimensionality reduction."""
        if n_components is None:
            n_components = self.config.pca_components

        if n_components is None or n_components >= len(dataset.feature_names):
            return dataset

        try:
            # Apply PCA
            pca = PCA(n_components=n_components)
            features_pca = pca.fit_transform(dataset.features)

            # Create new feature names
            pca_feature_names = [f'pc_{i+1}' for i in range(n_components)]

            # Create new dataset
            pca_dataset = SMCDataset(
                features=pd.DataFrame(features_pca, index=dataset.timestamps, columns=pca_feature_names),
                labels=dataset.labels,
                timestamps=dataset.timestamps,
                symbol=dataset.symbol,
                timeframe=dataset.timeframe,
                feature_names=pca_feature_names,
                label_type=dataset.label_type,
                created_at=dataset.created_at,
                scaler=dataset.scaler,
                feature_statistics=dataset.feature_statistics
            )

            # Store PCA model
            pca_dataset.pca_model = pca
            pca_dataset.explained_variance_ratio = pca.explained_variance_ratio_

            logger.info(f"PCA applied: {len(pca_feature_names)} components explain {pca.explained_variance_ratio_.sum():.3f} of variance")

            return pca_dataset

        except Exception as e:
            logger.error(f"PCA application failed: {str(e)}")
            return dataset

    def get_feature_importance(self, dataset: SMCDataset, target_column: Optional[str] = None) -> Dict[str, float]:
        """Calculate feature importance using correlation with target."""
        try:
            if target_column is None:
                # Use labels as target if available
                target = dataset.labels
            else:
                target = dataset.features[target_column]

            importance = {}
            for feature_name in dataset.feature_names:
                correlation = dataset.features[feature_name].corr(target)
                importance[feature_name] = abs(correlation) if not np.isnan(correlation) else 0.0

            # Sort by importance
            sorted_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

            return sorted_importance

        except Exception as e:
            logger.error(f"Feature importance calculation failed: {str(e)}")
            return {}

    def get_feature_summary(self, dataset: SMCDataset) -> Dict[str, Any]:
        """Get comprehensive feature summary statistics."""
        try:
            summary = {
                'dataset_info': {
                    'symbol': dataset.symbol,
                    'timeframe': dataset.timeframe,
                    'total_samples': len(dataset.features),
                    'feature_count': len(dataset.feature_names),
                    'label_type': dataset.label_type,
                    'created_at': dataset.created_at.isoformat()
                },
                'feature_statistics': {},
                'label_distribution': {},
                'data_quality': {}
            }

            # Feature statistics
            if len(dataset.features) > 0:
                summary['feature_statistics'] = {
                    'mean_values': dataset.features.mean().to_dict(),
                    'std_values': dataset.features.std().to_dict(),
                    'missing_values': dataset.features.isnull().sum().to_dict(),
                    'zero_values': (dataset.features == 0).sum().to_dict()
                }

            # Label distribution
            if hasattr(dataset.labels, 'value_counts'):
                summary['label_distribution'] = dataset.labels.value_counts().to_dict()

            # Data quality metrics
            summary['data_quality'] = {
                'completeness': (1 - dataset.features.isnull().sum().sum() / dataset.features.size) * 100,
                'duplicate_rows': dataset.features.index.duplicated().sum(),
                'feature_correlation_matrix': dataset.features.corr().to_dict(),
                'outlier_count': self._count_outliers(dataset.features)
            }

            return summary

        except Exception as e:
            logger.error(f"Feature summary generation failed: {str(e)}")
            return {}

    def _count_outliers(self, features_df: pd.DataFrame) -> Dict[str, int]:
        """Count outliers in features using IQR method."""
        outlier_counts = {}

        for column in features_df.columns:
            Q1 = features_df[column].quantile(0.25)
            Q3 = features_df[column].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = ((features_df[column] < lower_bound) | (features_df[column] > upper_bound)).sum()
            outlier_counts[column] = int(outliers)

        return outlier_counts

    def save_dataset(self, dataset: SMCDataset, filepath: Union[str, Path]) -> bool:
        """Save dataset to disk."""
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for saving
            save_data = {
                'metadata': {
                    'symbol': dataset.symbol,
                    'timeframe': dataset.timeframe,
                    'feature_names': dataset.feature_names,
                    'label_type': dataset.label_type,
                    'created_at': dataset.created_at.isoformat(),
                    'feature_statistics': dataset.feature_statistics
                },
                'features': dataset.features.to_dict(),
                'labels': dataset.labels.to_dict(),
                'timestamps': dataset.timestamps.tolist()
            }

            # Save to JSON
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)

            # Also save as separate CSV files for easy access
            dataset.features.to_csv(filepath.with_suffix('.features.csv'))
            dataset.labels.to_csv(filepath.with_suffix('.labels.csv'))

            logger.info(f"Dataset saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save dataset: {str(e)}")
            return False

    def load_dataset(self, filepath: Union[str, Path]) -> Optional[SMCDataset]:
        """Load dataset from disk."""
        try:
            filepath = Path(filepath)

            # Load from JSON
            with open(filepath, 'r') as f:
                save_data = json.load(f)

            # Reconstruct dataset
            features_df = pd.DataFrame(save_data['features'])
            labels_series = pd.Series(save_data['labels'])
            timestamps = pd.to_datetime(save_data['timestamps'])

            features_df.index = timestamps
            labels_series.index = timestamps

            dataset = SMCDataset(
                features=features_df,
                labels=labels_series,
                timestamps=timestamps,
                symbol=save_data['metadata']['symbol'],
                timeframe=save_data['metadata']['timeframe'],
                feature_names=save_data['metadata']['feature_names'],
                label_type=save_data['metadata']['label_type'],
                created_at=datetime.fromisoformat(save_data['metadata']['created_at']),
                scaler=self.scaler,
                feature_statistics=save_data['metadata']['feature_statistics']
            )

            logger.info(f"Dataset loaded from {filepath}")
            return dataset

        except Exception as e:
            logger.error(f"Failed to load dataset: {str(e)}")
            return None


def create_feature_config(**kwargs) -> FeatureConfig:
    """Create feature engineering configuration."""
    return FeatureConfig(**kwargs)


async def main():
    """Example usage of the SMC feature engineer."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting SMC Feature Engineering")

    # Create synthetic data for demonstration
    dates = pd.date_range(start='2023-01-01', end='2023-03-31', freq='5min')
    np.random.seed(42)

    # Generate realistic OHLCV data
    price_base = 50000
    returns = np.random.normal(0, 0.0002, len(dates))  # 0.02% daily volatility
    prices = price_base * np.cumprod(1 + returns)

    # Create OHLCV data
    high_noise = np.random.uniform(1, 1.005, len(dates))
    low_noise = np.random.uniform(0.995, 1, len(dates))

    data = pd.DataFrame({
        'open': prices,
        'high': prices * high_noise,
        'low': prices * low_noise,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, len(dates))
    }, index=dates)

    # Create configuration
    config = create_feature_config(
        momentum_periods=[5, 10, 20],
        volatility_windows=[10, 20],
        scaling_method='standard',
        remove_correlated=True,
        pca_components=10
    )

    # Initialize feature engineer
    engineer = SMCFeatureEngineer(config)

    # Create some synthetic patterns for demonstration
    synthetic_patterns = {
        'order_blocks': [
            {
                'timestamp': '2023-01-15 10:00:00',
                'strength': 0.8,
                'type': 'bullish'
            }
        ],
        'coch_patterns': [
            {
                'timestamp': '2023-01-20 14:30:00',
                'strength': 0.7,
                'type': 'bearish'
            }
        ]
    }

    # Engineer features
    dataset = await engineer.engineer_features(data, 'BTCUSDT', '5m', synthetic_patterns)

    # Get feature summary
    summary = engineer.get_feature_summary(dataset)

    # Apply PCA
    dataset_pca = engineer.apply_pca(dataset, n_components=8)

    # Get feature importance
    importance = engineer.get_feature_importance(dataset)

    print("\n" + "="*80)
    print("FEATURE ENGINEERING RESULTS")
    print("="*80)
    print(f"Dataset: {dataset.symbol} {dataset.timeframe}")
    print(f"Total Samples: {len(dataset.features)}")
    print(f"Feature Count: {len(dataset.feature_names)}")
    print(f"Label Distribution: {summary.get('label_distribution', {})}")
    print(f"Data Quality: {summary.get('data_quality', {}).get('completeness', 0):.1f}% complete")

    print(f"\nTop 10 Features by Importance:")
    for feature, score in list(importance.items())[:10]:
        print(f"  {feature}: {score:.3f}")

    # Save dataset
    engineer.save_dataset(dataset, 'smc_features_demo.json')


if __name__ == "__main__":
    asyncio.run(main())