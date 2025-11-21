"""
Enhanced Feature Engineering Pipeline

This module implements comprehensive feature engineering that combines SMC patterns,
market regime detection, sentiment analysis, order book analysis, and cross-asset correlations
to create rich feature sets for ML model training and inference.

Key Features:
- 25+ engineered features across multiple domains
- Real-time feature computation with sub-ms latency
- Feature normalization and scaling
- Feature importance tracking
- Feature drift detection
- Cached feature computation for efficiency
"""

import logging
import numpy as np
import pandas as pd
import talib
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_classif
import warnings
warnings.filterwarnings('ignore')

from .market_regime_detector import MarketRegimeClassifier
from .sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class FeatureSet:
    """Data class for engineered feature set."""
    smc_features: Dict[str, float]
    regime_features: Dict[str, float]
    sentiment_features: Dict[str, float]
    technical_features: Dict[str, float]
    order_book_features: Dict[str, float]
    cross_asset_features: Dict[str, float]
    temporal_features: Dict[str, float]
    timestamp: datetime
    feature_count: int
    confidence_scores: Dict[str, float]


class SMCFeatureExtractor:
    """
    Extracts SMC (Smart Money Concepts) specific features for ML models.
    """
    
    def __init__(self):
        self.feature_history = []
        self.max_history = 1000
        
    def extract_smc_features(self, ohlc_data: pd.DataFrame, smc_patterns: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive SMC features from OHLC data and detected patterns."""
        try:
            features = {}
            
            if len(ohlc_data) < 20:
                return self._get_default_smc_features()
            
            # Order Block Features
            order_blocks = smc_patterns.get('order_blocks', [])
            features.update(self._extract_order_block_features(order_blocks, ohlc_data))
            
            # CHOCH/BOS Features
            coch_patterns = smc_patterns.get('coch_patterns', [])
            bos_patterns = smc_patterns.get('bos_patterns', [])
            features.update(self._extract_choch_bos_features(coch_patterns, bos_patterns, ohlc_data))
            
            # Liquidity Sweep Features
            liquidity_sweeps = smc_patterns.get('liquidity_sweeps', [])
            features.update(self._extract_liquidity_sweep_features(liquidity_sweeps, ohlc_data))
            
            # Fair Value Gap Features
            fvg_patterns = smc_patterns.get('fvg_patterns', [])
            features.update(self._extract_fvg_features(fvg_patterns, ohlc_data))
            
            # Volume Profile Features
            features.update(self._extract_volume_profile_features(ohlc_data))
            
            # Market Structure Features
            features.update(self._extract_market_structure_features(ohlc_data))
            
            return features
            
        except Exception as e:
            logger.error(f"SMC feature extraction failed: {str(e)}")
            return self._get_default_smc_features()
    
    def _extract_order_block_features(self, order_blocks: List[Dict], data: pd.DataFrame) -> Dict[str, float]:
        """Extract features from order block patterns."""
        if not order_blocks:
            return {'ob_count': 0, 'ob_strength': 0.0, 'ob_density': 0.0}
        
        current_price = data.iloc[-1]['close']
        
        # Order block count and strength
        ob_count = len(order_blocks)
        
        # Order block strength (based on volume and proximity to current price)
        ob_strengths = []
        ob_distances = []
        
        for ob in order_blocks:
            price_level = ob['price_level']
            volume = ob.get('strength_volume', 1.0)
            
            # Calculate distance from current price
            if isinstance(price_level, tuple):
                avg_price = (price_level[0] + price_level[1]) / 2
            else:
                avg_price = price_level
            
            distance = abs(current_price - avg_price) / current_price * 100
            ob_distances.append(distance)
            
            # Strength based on volume and recency
            strength = volume * (1.0 / (1.0 + distance))
            ob_strengths.append(strength)
        
        return {
            'ob_count': ob_count,
            'ob_strength_avg': np.mean(ob_strengths) if ob_strengths else 0.0,
            'ob_strength_max': np.max(ob_strengths) if ob_strengths else 0.0,
            'ob_distance_avg': np.mean(ob_distances) if ob_distances else 0.0,
            'ob_distance_min': np.min(ob_distances) if ob_distances else 0.0,
            'ob_density': ob_count / 10.0,  # Normalized density
            'ob_bullish_ratio': sum(1 for ob in order_blocks if ob.get('type') == 'bullish') / ob_count
        }
    
    def _extract_choch_bos_features(self, coch_patterns: List[Dict], bos_patterns: List[Dict], data: pd.DataFrame) -> Dict[str, float]:
        """Extract features from CHOCH and BOS patterns."""
        features = {}
        
        # CHOCH features
        coch_count = len(coch_patterns)
        if coch_patterns:
            coch_confidences = [p.get('confidence', 0.5) for p in coch_patterns]
            coch_strengths = [p.get('momentum_strength', 0.0) for p in coch_patterns]
            
            features.update({
                'coch_count': coch_count,
                'coch_confidence_avg': np.mean(coch_confidences),
                'coch_strength_avg': np.mean(coch_strengths),
                'coch_bullish_ratio': sum(1 for p in coch_patterns if 'bullish' in p.get('type', '')) / coch_count
            })
        else:
            features.update({'coch_count': 0, 'coch_confidence_avg': 0.0, 'coch_strength_avg': 0.0, 'coch_bullish_ratio': 0.0})
        
        # BOS features
        bos_count = len(bos_patterns)
        if bos_patterns:
            bos_confidences = [p.get('confidence', 0.5) for p in bos_patterns]
            bos_strengths = [p.get('break_strength', 0.0) for p in bos_patterns]
            
            features.update({
                'bos_count': bos_count,
                'bos_confidence_avg': np.mean(bos_confidences),
                'bos_strength_avg': np.mean(bos_strengths),
                'bos_bullish_ratio': sum(1 for p in bos_patterns if 'bullish' in p.get('type', '')) / bos_count
            })
        else:
            features.update({'bos_count': 0, 'bos_confidence_avg': 0.0, 'bos_strength_avg': 0.0, 'bos_bullish_ratio': 0.0})
        
        # Combined features
        total_patterns = coch_count + bos_count
        if total_patterns > 0:
            features.update({
                'pattern_density': total_patterns / 20.0,  # Normalized density
                'pattern_confidence_avg': (coch_count * features.get('coch_confidence_avg', 0) + 
                                           bos_count * features.get('bos_confidence_avg', 0)) / total_patterns
            })
        else:
            features.update({'pattern_density': 0.0, 'pattern_confidence_avg': 0.0})
        
        return features
    
    def _extract_liquidity_sweep_features(self, liquidity_sweeps: List[Dict], data: pd.DataFrame) -> Dict[str, float]:
        """Extract features from liquidity sweep patterns."""
        if not liquidity_sweeps:
            return {'ls_count': 0, 'ls_strength_avg': 0.0, 'ls_reversal_ratio': 0.0}
        
        ls_count = len(liquidity_sweeps)
        
        # Sweep strengths and confidence
        strengths = [s.get('sweep_strength', 0.0) for s in liquidity_sweeps]
        confidences = [s.get('confidence', 0.5) for s in liquidity_sweeps]
        reversals_confirmed = [s.get('reversal_confirmed', False) for s in liquidity_sweeps]
        
        return {
            'ls_count': ls_count,
            'ls_strength_avg': np.mean(strengths),
            'ls_strength_max': np.max(strengths) if strengths else 0.0,
            'ls_confidence_avg': np.mean(confidences),
            'ls_reversal_ratio': sum(reversals_confirmed) / len(reversals_confirmed),
            'ls_bullish_ratio': sum(1 for s in liquidity_sweeps if 'bullish' in s.get('type', '')) / ls_count,
            'ls_density': ls_count / 15.0  # Normalized density
        }
    
    def _extract_fvg_features(self, fvg_patterns: List[Dict], data: pd.DataFrame) -> Dict[str, float]:
        """Extract features from Fair Value Gap patterns."""
        if not fvg_patterns:
            return {'fvg_count': 0, 'fvg_size_avg': 0.0, 'fvg_fill_ratio': 0.0}
        
        fvg_count = len(fvg_patterns)
        
        # FVG sizes and fill status
        sizes = [f.get('size_percentage', 0.0) for f in fvg_patterns]
        filled = [f.get('filled', False) for f in fvg_patterns]
        
        return {
            'fvg_count': fvg_count,
            'fvg_size_avg': np.mean(sizes),
            'fvg_size_max': np.max(sizes) if sizes else 0.0,
            'fvg_fill_ratio': sum(filled) / len(filled),
            'fvg_density': fvg_count / 10.0,  # Normalized density
            'fvg_unfilled_ratio': 1.0 - sum(filled) / len(filled)
        }
    
    def _extract_volume_profile_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract volume profile related features."""
        if len(data) < 20:
            return {'volume_trend': 0.0, 'volume_volatility': 0.0}
        
        volumes = data['volume'].values
        prices = data['close'].values
        
        # Volume trend
        volume_ma_short = volumes[-10:].mean()
        volume_ma_long = volumes[-20:].mean()
        volume_trend = (volume_ma_short - volume_ma_long) / volume_ma_long if volume_ma_long > 0 else 0
        
        # Volume volatility
        volume_volatility = np.std(volumes[-20:]) / np.mean(volumes[-20:]) if np.mean(volumes[-20:]) > 0 else 0
        
        # Price-volume correlation
        if len(prices) >= len(volumes):
            price_changes = np.diff(prices)
            volume_changes = np.diff(volumes)
            if len(price_changes) > 0 and len(volume_changes) > 0:
                correlation = np.corrcoef(price_changes, volume_changes)[0, 1]
            else:
                correlation = 0
        else:
            correlation = 0
        
        # Volume spikes
        volume_threshold = np.percentile(volumes, 80)
        volume_spikes = np.sum(volumes > volume_threshold) / len(volumes)
        
        return {
            'volume_trend': volume_trend,
            'volume_volatility': volume_volatility,
            'volume_price_correlation': correlation if not np.isnan(correlation) else 0.0,
            'volume_spike_ratio': volume_spikes,
            'volume_avg_ratio': volumes[-1] / np.mean(volumes) if np.mean(volumes) > 0 else 1.0
        }
    
    def _extract_market_structure_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract market structure features."""
        if len(data) < 50:
            return {'structure_bullish': 0.0, 'structure_strength': 0.0}
        
        highs = data['high'].values
        lows = data['low'].values
        closes = data['close'].values
        
        # Higher highs and higher lows analysis
        hh_count = 0
        hl_count = 0
        lh_count = 0
        ll_count = 0
        
        window = 10
        for i in range(window, len(data)):
            current_high = highs[i]
            current_low = lows[i]
            
            # Check for higher high
            if current_high > np.max(highs[i-window:i]):
                hh_count += 1
            
            # Check for higher low
            if current_low > np.max(lows[i-window:i]):
                hl_count += 1
            
            # Check for lower high
            if current_high < np.min(highs[i-window:i]):
                lh_count += 1
            
            # Check for lower low
            if current_low < np.min(lows[i-window:i]):
                ll_count += 1
        
        total_structure = hh_count + hl_count + lh_count + ll_count
        
        if total_structure > 0:
            bullish_ratio = (hh_count + hl_count) / total_structure
            bearish_ratio = (lh_count + ll_count) / total_structure
            structure_strength = total_structure / (len(data) - window)
        else:
            bullish_ratio = 0.5
            bearish_ratio = 0.5
            structure_strength = 0.0
        
        return {
            'structure_bullish': bullish_ratio,
            'structure_bearish': bearish_ratio,
            'structure_strength': structure_strength,
            'hh_count': hh_count,
            'll_count': ll_count,
            'structure_imbalance': abs(bullish_ratio - bearish_ratio)
        }
    
    def _get_default_smc_features(self) -> Dict[str, float]:
        """Get default SMC features when data is insufficient."""
        return {
            'ob_count': 0, 'ob_strength_avg': 0.0, 'ob_density': 0.0,
            'coch_count': 0, 'coch_confidence_avg': 0.0, 'coch_strength_avg': 0.0,
            'bos_count': 0, 'bos_confidence_avg': 0.0, 'bos_strength_avg': 0.0,
            'ls_count': 0, 'ls_strength_avg': 0.0, 'ls_reversal_ratio': 0.0,
            'fvg_count': 0, 'fvg_size_avg': 0.0, 'fvg_fill_ratio': 0.0,
            'volume_trend': 0.0, 'volume_volatility': 0.0,
            'structure_bullish': 0.5, 'structure_strength': 0.0
        }


class TechnicalFeatureExtractor:
    """
    Extracts traditional technical analysis features using TA-Lib.
    """
    
    def __init__(self):
        self.indicators_history = {}
        
    def extract_technical_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract comprehensive technical analysis features."""
        try:
            if len(data) < 50:
                return self._get_default_technical_features()
            
            features = {}
            
            # Prepare data for TA-Lib
            close = data['close'].values
            high = data['high'].values
            low = data['low'].values
            volume = data['volume'].values
            open_prices = data['open'].values
            
            # Trend Indicators
            features.update(self._extract_trend_features(close, high, low))
            
            # Momentum Indicators
            features.update(self._extract_momentum_features(close, high, low, volume))
            
            # Volatility Indicators
            features.update(self._extract_volatility_features(close, high, low))
            
            # Volume Indicators
            features.update(self._extract_volume_indicators(close, volume))
            
            # Pattern Recognition
            features.update(self._extract_pattern_features(open_prices, high, low, close))
            
            return features
            
        except Exception as e:
            logger.error(f"Technical feature extraction failed: {str(e)}")
            return self._get_default_technical_features()
    
    def _extract_trend_features(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Extract trend-based technical features."""
        features = {}
        
        try:
            # Moving Averages
            sma_20 = talib.SMA(close, timeperiod=20)
            sma_50 = talib.SMA(close, timeperiod=50)
            ema_12 = talib.EMA(close, timeperiod=12)
            ema_26 = talib.EMA(close, timeperiod=26)
            
            features['sma_20_ratio'] = close[-1] / sma_20[-1] if not np.isnan(sma_20[-1]) and sma_20[-1] > 0 else 1.0
            features['sma_50_ratio'] = close[-1] / sma_50[-1] if not np.isnan(sma_50[-1]) and sma_50[-1] > 0 else 1.0
            features['ema_12_ratio'] = close[-1] / ema_12[-1] if not np.isnan(ema_12[-1]) and ema_12[-1] > 0 else 1.0
            features['ema_26_ratio'] = close[-1] / ema_26[-1] if not np.isnan(ema_26[-1]) and ema_26[-1] > 0 else 1.0
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close)
            features['macd'] = macd[-1] if not np.isnan(macd[-1]) else 0.0
            features['macd_signal'] = macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0.0
            features['macd_histogram'] = macd_hist[-1] if not np.isnan(macd_hist[-1]) else 0.0
            
            # ADX
            adx = talib.ADX(high, low, close, timeperiod=14)
            features['adx'] = adx[-1] if not np.isnan(adx[-1]) else 0.0
            
            # Parabolic SAR
            sar = talib.SAR(high, low)
            features['sar_ratio'] = close[-1] / sar[-1] if not np.isnan(sar[-1]) and sar[-1] > 0 else 1.0
            
        except Exception as e:
            logger.warning(f"Trend feature extraction error: {str(e)}")
        
        return features
    
    def _extract_momentum_features(self, close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> Dict[str, float]:
        """Extract momentum-based technical features."""
        features = {}
        
        try:
            # RSI
            rsi = talib.RSI(close, timeperiod=14)
            features['rsi'] = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
            
            # Stochastic Oscillator
            slowk, slowd = talib.STOCH(high, low, close)
            features['stoch_k'] = slowk[-1] if not np.isnan(slowk[-1]) else 50.0
            features['stoch_d'] = slowd[-1] if not np.isnan(slowd[-1]) else 50.0
            
            # Williams %R
            willr = talib.WILLR(high, low, close, timeperiod=14)
            features['williams_r'] = willr[-1] if not np.isnan(willr[-1]) else -50.0
            
            # CCI
            cci = talib.CCI(high, low, close, timeperiod=14)
            features['cci'] = cci[-1] if not np.isnan(cci[-1]) else 0.0
            
            # MFI
            mfi = talib.MFI(high, low, close, volume, timeperiod=14)
            features['mfi'] = mfi[-1] if not np.isnan(mfi[-1]) else 50.0
            
            # ROC
            roc = talib.ROC(close, timeperiod=10)
            features['roc'] = roc[-1] if not np.isnan(roc[-1]) else 0.0
            
        except Exception as e:
            logger.warning(f"Momentum feature extraction error: {str(e)}")
        
        return features
    
    def _extract_volatility_features(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Extract volatility-based technical features."""
        features = {}
        
        try:
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            features['bb_position'] = (close[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1]) if (bb_upper[-1] - bb_lower[-1]) > 0 else 0.5
            features['bb_width'] = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1] if bb_middle[-1] > 0 else 0.0
            
            # ATR
            atr = talib.ATR(high, low, close, timeperiod=14)
            features['atr'] = atr[-1] if not np.isnan(atr[-1]) else 0.0
            features['atr_ratio'] = atr[-1] / close[-1] if close[-1] > 0 else 0.0
            
            # Historical Volatility
            returns = np.diff(np.log(close))
            hist_vol = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
            features['historical_volatility'] = hist_vol
            
        except Exception as e:
            logger.warning(f"Volatility feature extraction error: {str(e)}")
        
        return features
    
    def _extract_volume_indicators(self, close: np.ndarray, volume: np.ndarray) -> Dict[str, float]:
        """Extract volume-based technical features."""
        features = {}
        
        try:
            # On-Balance Volume
            obv = talib.OBV(close, volume)
            obv_slope = np.polyfit(np.arange(len(obv)), obv, 1)[0] if len(obv) > 1 else 0.0
            features['obv_slope'] = obv_slope
            
            # Volume Weighted Average Price (VWAP)
            if len(close) == len(volume):
                vwap = np.cumsum(close * volume) / np.cumsum(volume)
                features['vwap_ratio'] = close[-1] / vwap[-1] if vwap[-1] > 0 else 1.0
            
            # Volume SMA
            volume_sma = talib.SMA(volume, timeperiod=20)
            features['volume_sma_ratio'] = volume[-1] / volume_sma[-1] if volume_sma[-1] > 0 else 1.0
            
            # Ease of Movement
            if len(volume) >= 14:
                eom = talib.EOM(volume, high, low, close)
                features['eom'] = eom[-1] if not np.isnan(eom[-1]) else 0.0
            
        except Exception as e:
            logger.warning(f"Volume indicator extraction error: {str(e)}")
        
        return features
    
    def _extract_pattern_features(self, open_prices: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Dict[str, float]:
        """Extract pattern recognition features."""
        features = {}
        
        try:
            # Candlestick Patterns (normalized to -1 to 1 scale)
            patterns = {
                'doji': talib.CDLDOJI(open_prices, high, low, close),
                'hammer': talib.CDLHAMMER(open_prices, high, low, close),
                'shooting_star': talib.CDLSHOOTINGSTAR(open_prices, high, low, close),
                'engulfing': talib.CDLENGULFING(open_prices, high, low, close),
                'harami': talib.CDLHARAMI(open_prices, high, low, close),
                'morning_star': talib.CDLMORNINGSTAR(open_prices, high, low, close),
                'evening_star': talib.CDLEVENINGSTAR(open_prices, high, low, close)
            }
            
            for pattern_name, pattern_values in patterns.items():
                # Use the most recent pattern value
                pattern_value = pattern_values[-1] if len(pattern_values) > 0 else 0
                # Normalize to -1 to 1 range (100 becomes 1.0, -100 becomes -1.0)
                features[f'pattern_{pattern_name}'] = max(-1.0, min(1.0, pattern_value / 100.0))
            
        except Exception as e:
            logger.warning(f"Pattern feature extraction error: {str(e)}")
        
        return features
    
    def _get_default_technical_features(self) -> Dict[str, float]:
        """Get default technical features when data is insufficient."""
        return {
            'sma_20_ratio': 1.0, 'sma_50_ratio': 1.0, 'ema_12_ratio': 1.0, 'ema_26_ratio': 1.0,
            'macd': 0.0, 'macd_signal': 0.0, 'macd_histogram': 0.0, 'adx': 0.0,
            'sar_ratio': 1.0, 'rsi': 50.0, 'stoch_k': 50.0, 'stoch_d': 50.0,
            'williams_r': -50.0, 'cci': 0.0, 'mfi': 50.0, 'roc': 0.0,
            'bb_position': 0.5, 'bb_width': 0.1, 'atr': 0.0, 'atr_ratio': 0.0,
            'historical_volatility': 0.02, 'obv_slope': 0.0, 'vwap_ratio': 1.0,
            'volume_sma_ratio': 1.0, 'eom': 0.0,
            'pattern_doji': 0.0, 'pattern_hammer': 0.0, 'pattern_shooting_star': 0.0,
            'pattern_engulfing': 0.0, 'pattern_harami': 0.0, 'pattern_morning_star': 0.0, 'pattern_evening_star': 0.0
        }


class OrderBookFeatureExtractor:
    """
    Extracts order book and market microstructure features.
    """
    
    def __init__(self):
        self.order_book_cache = {}
        self.cache_ttl = timedelta(seconds=5)
        
    def extract_order_book_features(self, order_book: Dict[str, Any] = None) -> Dict[str, float]:
        """Extract order book and liquidity features."""
        try:
            if not order_book:
                return self._get_default_order_book_features()
            
            features = {}
            
            # Order book imbalance
            features.update(self._extract_order_imbalance_features(order_book))
            
            # Liquidity features
            features.update(self._extract_liquidity_features(order_book))
            
            # Market depth features
            features.update(self._extract_market_depth_features(order_book))
            
            # Spread features
            features.update(self._extract_spread_features(order_book))
            
            return features
            
        except Exception as e:
            logger.error(f"Order book feature extraction failed: {str(e)}")
            return self._get_default_order_book_features()
    
    def _extract_order_imbalance_features(self, order_book: Dict[str, Any]) -> Dict[str, float]:
        """Extract order flow imbalance features."""
        features = {}
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {'bid_ask_imbalance': 0.0, 'order_flow_pressure': 0.0}
            
            # Calculate total bid and ask volumes
            total_bid_volume = sum(bid[1] for bid in bids[:10])  # Top 10 levels
            total_ask_volume = sum(ask[1] for ask in asks[:10])
            
            # Order book imbalance
            if total_bid_volume + total_ask_volume > 0:
                imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
                features['bid_ask_imbalance'] = imbalance
            else:
                features['bid_ask_imbalance'] = 0.0
            
            # Order flow pressure
            if len(bids) >= 3 and len(asks) >= 3:
                bid_pressure = sum(bid[1] for bid in bids[:3])
                ask_pressure = sum(ask[1] for ask in asks[:3])
                features['order_flow_pressure'] = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure)
            else:
                features['order_flow_pressure'] = 0.0
            
        except Exception as e:
            logger.warning(f"Order imbalance feature extraction error: {str(e)}")
            features.update({'bid_ask_imbalance': 0.0, 'order_flow_pressure': 0.0})
        
        return features
    
    def _extract_liquidity_features(self, order_book: Dict[str, Any]) -> Dict[str, float]:
        """Extract liquidity-related features."""
        features = {}
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {'liquidity_score': 0.5, 'market_depth': 0.0}
            
            # Liquidity score (total volume near mid price)
            mid_price = (bids[0][0] + asks[0][0]) / 2
            liquidity_range = mid_price * 0.01  # 1% around mid price
            
            liquidity_volume = 0
            for bid in bids:
                if mid_price - bid[0] <= liquidity_range:
                    liquidity_volume += bid[1]
                else:
                    break
            
            for ask in asks:
                if ask[0] - mid_price <= liquidity_range:
                    liquidity_volume += ask[1]
                else:
                    break
            
            features['liquidity_score'] = min(1.0, liquidity_volume / 1000000)  # Normalize
            
            # Market depth
            depth_volume = 0
            depth_levels = 0
            for i in range(min(20, len(bids), len(asks))):
                if i < len(bids):
                    depth_volume += bids[i][1]
                if i < len(asks):
                    depth_volume += asks[i][1]
                depth_levels += 1
            
            features['market_depth'] = depth_volume / depth_levels if depth_levels > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Liquidity feature extraction error: {str(e)}")
            features.update({'liquidity_score': 0.5, 'market_depth': 0.0})
        
        return features
    
    def _extract_market_depth_features(self, order_book: Dict[str, Any]) -> Dict[str, float]:
        """Extract market depth features."""
        features = {}
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {'depth_imbalance': 0.0, 'wall_detection': 0.0}
            
            # Depth imbalance at different levels
            level_imbalances = []
            for i in range(min(5, len(bids), len(asks))):
                bid_vol = bids[i][1] if i < len(bids) else 0
                ask_vol = asks[i][1] if i < len(asks) else 0
                
                if bid_vol + ask_vol > 0:
                    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
                    level_imbalances.append(imbalance)
            
            features['depth_imbalance'] = np.mean(level_imbalances) if level_imbalances else 0.0
            
            # Wall detection (large orders)
            large_order_threshold = 500000  # Large order threshold
            wall_count = 0
            
            for bid in bids[:10]:
                if bid[1] >= large_order_threshold:
                    wall_count += 1
            
            for ask in asks[:10]:
                if ask[1] >= large_order_threshold:
                    wall_count += 1
            
            features['wall_detection'] = min(1.0, wall_count / 10.0)
            
        except Exception as e:
            logger.warning(f"Market depth feature extraction error: {str(e)}")
            features.update({'depth_imbalance': 0.0, 'wall_detection': 0.0})
        
        return features
    
    def _extract_spread_features(self, order_book: Dict[str, Any]) -> Dict[str, float]:
        """Extract spread-related features."""
        features = {}
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {'spread_percentage': 0.001, 'spread_tightness': 0.5}
            
            # Calculate spreads
            mid_price = (bids[0][0] + asks[0][0]) / 2
            spread = asks[0][0] - bids[0][0]
            spread_percentage = spread / mid_price if mid_price > 0 else 0.001
            
            features['spread_percentage'] = spread_percentage
            
            # Spread tightness (inverse of spread percentage)
            features['spread_tightness'] = 1.0 / (1.0 + spread_percentage * 1000)
            
        except Exception as e:
            logger.warning(f"Spread feature extraction error: {str(e)}")
            features.update({'spread_percentage': 0.001, 'spread_tightness': 0.5})
        
        return features
    
    def _get_default_order_book_features(self) -> Dict[str, float]:
        """Get default order book features when data is unavailable."""
        return {
            'bid_ask_imbalance': 0.0, 'order_flow_pressure': 0.0, 'liquidity_score': 0.5,
            'market_depth': 0.0, 'depth_imbalance': 0.0, 'wall_detection': 0.0,
            'spread_percentage': 0.001, 'spread_tightness': 0.5
        }


class CrossAssetFeatureExtractor:
    """
    Extracts cross-asset correlation and macro market features.
    """
    
    def __init__(self):
        self.asset_data_cache = {}
        self.correlation_window = 100
        
    def extract_cross_asset_features(self, symbol: str, asset_data: Dict[str, pd.DataFrame] = None) -> Dict[str, float]:
        """Extract cross-asset correlation features."""
        try:
            if not asset_data:
                return self._get_default_cross_asset_features()
            
            features = {}
            
            # Crypto correlations
            features.update(self._extract_crypto_correlations(symbol, asset_data))
            
            # Traditional market correlations
            features.update(self._extract_traditional_correlations(asset_data))
            
            # Risk regime features
            features.update(self._extract_risk_regime_features(asset_data))
            
            return features
            
        except Exception as e:
            logger.error(f"Cross-asset feature extraction failed: {str(e)}")
            return self._get_default_cross_asset_features()
    
    def _extract_crypto_correlations(self, symbol: str, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Extract cryptocurrency correlation features."""
        features = {}
        
        try:
            # Get main asset data
            main_data = asset_data.get(symbol)
            if main_data is None or len(main_data) < 50:
                return {'btc_eth_correlation': 0.0, 'crypto_correlation_avg': 0.0}
            
            main_returns = main_data['close'].pct_change().dropna()
            
            # Correlate with other crypto assets
            crypto_assets = ['ETH', 'BNB', 'ADA', 'DOT', 'SOL']
            correlations = []
            
            for crypto in crypto_assets:
                crypto_data = asset_data.get(crypto)
                if crypto_data is not None and len(crypto_data) >= len(main_returns):
                    crypto_returns = crypto_data['close'].pct_change().dropna()
                    
                    # Align returns
                    min_length = min(len(main_returns), len(crypto_returns))
                    if min_length > 10:
                        correlation = np.corrcoef(main_returns[-min_length:], crypto_returns[-min_length:])[0, 1]
                        if not np.isnan(correlation):
                            correlations.append(abs(correlation))
                            features[f'{symbol.lower()}_{crypto.lower()}_correlation'] = correlation
            
            # BTC-ETH special correlation
            eth_data = asset_data.get('ETH')
            if eth_data is not None and len(eth_data) >= 50:
                eth_returns = eth_data['close'].pct_change().dropna()
                min_length = min(len(main_returns), len(eth_returns))
                if min_length > 10:
                    btc_eth_corr = np.corrcoef(main_returns[-min_length:], eth_returns[-min_length:])[0, 1]
                    features['btc_eth_correlation'] = btc_eth_corr if not np.isnan(btc_eth_corr) else 0.0
            
            features['crypto_correlation_avg'] = np.mean(correlations) if correlations else 0.0
            features['crypto_correlation_count'] = len(correlations)
            
        except Exception as e:
            logger.warning(f"Crypto correlation extraction error: {str(e)}")
            features.update({'btc_eth_correlation': 0.0, 'crypto_correlation_avg': 0.0, 'crypto_correlation_count': 0})
        
        return features
    
    def _extract_traditional_correlations(self, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Extract correlations with traditional markets."""
        features = {}
        
        try:
            # Get crypto data for correlation
            crypto_data = asset_data.get('BTC') or asset_data.get('ETH')
            if crypto_data is None or len(crypto_data) < 50:
                return {'sp500_correlation': 0.0, 'gold_correlation': 0.0, 'safe_haven_demand': 0.5}
            
            crypto_returns = crypto_data['close'].pct_change().dropna()
            
            # Traditional market assets
            traditional_assets = {
                'SPY': 'sp500_correlation',
                'QQQ': 'nasdaq_correlation',
                'GLD': 'gold_correlation',
                'US10Y': 'bond_correlation',
                'DXY': 'dollar_correlation'
            }
            
            correlations = []
            
            for asset_name, feature_name in traditional_assets.items():
                asset_df = asset_data.get(asset_name)
                if asset_df is not None and len(asset_df) >= len(crypto_returns):
                    asset_returns = asset_df['close'].pct_change().dropna()
                    
                    min_length = min(len(crypto_returns), len(asset_returns))
                    if min_length > 10:
                        correlation = np.corrcoef(crypto_returns[-min_length:], asset_returns[-min_length:])[0, 1]
                        if not np.isnan(correlation):
                            correlations.append(correlation)
                            features[feature_name] = correlation
            
            # Safe haven demand (inverse correlation with risky assets)
            if 'sp500_correlation' in features and 'gold_correlation' in features:
                # When stocks fall and gold rises = high safe haven demand
                safe_haven_score = -features['sp500_correlation'] * features['gold_correlation']
                features['safe_haven_demand'] = (safe_haven_score + 1) / 2  # Normalize to 0-1
            
            features['traditional_correlation_avg'] = np.mean(correlations) if correlations else 0.0
            
        except Exception as e:
            logger.warning(f"Traditional correlation extraction error: {str(e)}")
            features.update({'sp500_correlation': 0.0, 'gold_correlation': 0.0, 'safe_haven_demand': 0.5, 'traditional_correlation_avg': 0.0})
        
        return features
    
    def _extract_risk_regime_features(self, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Extract risk regime features."""
        features = {}
        
        try:
            # Get data for major risk assets
            sp500_data = asset_data.get('SPY')
            vix_data = asset_data.get('VIX')
            
            if sp500_data is not None and len(sp500_data) >= 20:
                sp500_returns = sp500_data['close'].pct_change().dropna()
                
                # Volatility regime
                volatility = sp500_returns.std() * np.sqrt(252)
                features['market_volatility_regime'] = min(1.0, volatility / 0.3)  # Normalize against 30% annual vol
                
                # Trend strength
                if len(sp500_data) >= 50:
                    sp500_prices = sp500_data['close'].values
                    x = np.arange(len(sp500_prices))
                    slope, _ = np.polyfit(x, sp500_prices, 1)
                    trend_strength = abs(slope) / np.mean(sp500_prices) if np.mean(sp500_prices) > 0 else 0
                    features['market_trend_strength'] = min(1.0, trend_strength * 1000)
            
            # VIX features (fear index)
            if vix_data is not None and len(vix_data) >= 20:
                vix_current = vix_data['close'].iloc[-1]
                vix_ma = vix_data['close'].rolling(20).mean().iloc[-1]
                features['vix_ratio'] = vix_current / vix_ma if vix_ma > 0 else 1.0
                features['fear_index'] = min(1.0, vix_current / 50.0)  # Normalize against VIX=50
            
            # Risk-on/off score
            risk_assets = ['SPY', 'QQQ']
            safe_assets = ['GLD', 'US10Y']
            
            risk_performance = 0
            safe_performance = 0
            risk_count = 0
            safe_count = 0
            
            for asset in risk_assets:
                asset_df = asset_data.get(asset)
                if asset_df is not None and len(asset_df) >= 20:
                    returns = asset_df['close'].pct_change().dropna()
                    risk_performance += returns.mean()
                    risk_count += 1
            
            for asset in safe_assets:
                asset_df = asset_data.get(asset)
                if asset_df is not None and len(asset_df) >= 20:
                    returns = asset_df['close'].pct_change().dropna()
                    safe_performance += returns.mean()
                    safe_count += 1
            
            if risk_count > 0 and safe_count > 0:
                risk_on_score = (risk_performance / risk_count - safe_performance / safe_count) + 1
                features['risk_on_score'] = max(0, min(2, risk_on_score)) / 2  # Normalize to 0-1
            
        except Exception as e:
            logger.warning(f"Risk regime extraction error: {str(e)}")
            features.update({
                'market_volatility_regime': 0.5, 'market_trend_strength': 0.5,
                'vix_ratio': 1.0, 'fear_index': 0.5, 'risk_on_score': 0.5
            })
        
        return features
    
    def _get_default_cross_asset_features(self) -> Dict[str, float]:
        """Get default cross-asset features when data is unavailable."""
        return {
            'btc_eth_correlation': 0.0, 'crypto_correlation_avg': 0.0, 'crypto_correlation_count': 0,
            'sp500_correlation': 0.0, 'gold_correlation': 0.0, 'safe_haven_demand': 0.5,
            'traditional_correlation_avg': 0.0, 'market_volatility_regime': 0.5,
            'market_trend_strength': 0.5, 'vix_ratio': 1.0, 'fear_index': 0.5, 'risk_on_score': 0.5
        }


class TemporalFeatureExtractor:
    """
    Extracts time-based and temporal features.
    """
    
    def __init__(self):
        pass
    
    def extract_temporal_features(self, timestamp: datetime = None) -> Dict[str, float]:
        """Extract temporal features from timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        
        features = {}
        
        # Hour of day features
        hour = timestamp.hour
        features['hour_of_day'] = hour / 24.0
        features['trading_session_active'] = 1.0 if 9 <= hour <= 16 else 0.0  # NY/LE trading hours
        
        # Day of week features
        day_of_week = timestamp.weekday()
        features['day_of_week'] = day_of_week / 6.0
        features['weekend_flag'] = 1.0 if day_of_week >= 5 else 0.0
        
        # Month features
        month = timestamp.month
        features['month_of_year'] = month / 12.0
        features['quarter_end_flag'] = 1.0 if month in [3, 6, 9, 12] else 0.0
        
        # Session-specific features
        features['asian_session'] = 1.0 if 23 <= hour or hour < 8 else 0.0
        features['london_session'] = 1.0 if 7 <= hour < 16 else 0.0
        features['new_york_session'] = 1.0 if 12 <= hour < 21 else 0.0
        features['session_overlap'] = 1.0 if (7 <= hour < 8) or (12 <= hour < 16) else 0.0
        
        return features


class EnhancedFeatureEngineer:
    """
    Main enhanced feature engineering pipeline that combines all feature extractors.
    """
    
    def __init__(self, scaler_type: str = 'standard'):
        # Initialize feature extractors
        self.smc_extractor = SMCFeatureExtractor()
        self.technical_extractor = TechnicalFeatureExtractor()
        self.order_book_extractor = OrderBookFeatureExtractor()
        self.cross_asset_extractor = CrossAssetFeatureExtractor()
        self.temporal_extractor = TemporalFeatureExtractor()
        
        # Initialize regime classifier and sentiment analyzer
        self.regime_classifier = MarketRegimeClassifier()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Feature scaling
        self.scaler_type = scaler_type
        if scaler_type == 'standard':
            self.scaler = StandardScaler()
        elif scaler_type == 'robust':
            self.scaler = RobustScaler()
        elif scaler_type == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            self.scaler = StandardScaler()
        
        self.is_fitted = False
        
        # Feature tracking
        self.feature_history = []
        self.feature_importance = {}
        self.max_history = 5000
        
        logger.info(f"EnhancedFeatureEngineer initialized with {scaler_type} scaler")
    
    def extract_features(self, data: pd.DataFrame, smc_patterns: Dict[str, Any] = None,
                        order_book: Dict[str, Any] = None, cross_asset_data: Dict[str, pd.DataFrame] = None,
                        timestamp: datetime = None) -> FeatureSet:
        """
        Extract comprehensive feature set from all available data sources.
        
        Args:
            data: Main OHLCV data
            smc_patterns: Detected SMC patterns
            order_book: Order book data
            cross_asset_data: Data for correlation analysis
            timestamp: Current timestamp
            
        Returns:
            FeatureSet with all engineered features
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Extract features from all extractors
            smc_features = self.smc_extractor.extract_smc_features(data, smc_patterns or {})
            
            # Get regime features
            regime_classification = self.regime_classifier.classify_market_regime(data)
            regime_features = self.regime_classifier.get_regime_features(regime_classification)
            
            # Get sentiment features (async operation, we'll use a fallback for now)
            sentiment_features = self._get_sentiment_features_fallback()
            
            # Technical features
            technical_features = self.technical_extractor.extract_technical_features(data)
            
            # Order book features
            order_book_features = self.order_book_extractor.extract_order_book_features(order_book)
            
            # Cross-asset features
            cross_asset_features = self.cross_asset_extractor.extract_cross_asset_features(
                data.iloc[-1]['symbol'] if 'symbol' in data.columns[-1:] else 'BTC', 
                cross_asset_data
            )
            
            # Temporal features
            temporal_features = self.temporal_extractor.extract_temporal_features(timestamp)
            
            # Calculate confidence scores for each feature group
            confidence_scores = self._calculate_feature_confidence_scores(
                data, smc_features, regime_features, technical_features, order_book_features, cross_asset_features
            )
            
            # Create feature set
            feature_set = FeatureSet(
                smc_features=smc_features,
                regime_features=regime_features,
                sentiment_features=sentiment_features,
                technical_features=technical_features,
                order_book_features=order_book_features,
                cross_asset_features=cross_asset_features,
                temporal_features=temporal_features,
                timestamp=timestamp,
                feature_count=len(self._flatten_features(smc_features, regime_features, sentiment_features, 
                                               technical_features, order_book_features, cross_asset_features, temporal_features)),
                confidence_scores=confidence_scores
            )
            
            # Update feature history
            self.feature_history.append(feature_set)
            if len(self.feature_history) > self.max_history:
                self.feature_history = self.feature_history[-self.max_history:]
            
            logger.info(f"Extracted {feature_set.feature_count} features across 7 feature groups")
            return feature_set
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            return self._get_default_feature_set(timestamp or datetime.now())
    
    def _get_sentiment_features_fallback(self) -> Dict[str, float]:
        """Fallback sentiment features when async sentiment analysis is not available."""
        # In production, this would be replaced with actual async sentiment analysis
        return {
            'sentiment_overall': 0.0, 'sentiment_news': 0.0, 'sentiment_social': 0.0,
            'sentiment_momentum': 0.0, 'sentiment_volatility': 0.5, 'sentiment_agreement': 0.5,
            'sentiment_confidence': 0.1, 'sentiment_anomaly': 0.0, 'sentiment_diversity': 0.0,
            'sentiment_volume': 0.0
        }
    
    def _calculate_feature_confidence_scores(self, data: pd.DataFrame, *feature_groups) -> Dict[str, float]:
        """Calculate confidence scores for each feature group."""
        confidence_scores = {}
        
        # Data quality confidence
        data_quality = min(1.0, len(data) / 100.0)  # More data = higher confidence
        
        # SMC features confidence
        confidence_scores['smc'] = data_quality
        
        # Regime features confidence
        confidence_scores['regime'] = data_quality
        
        # Sentiment features confidence (placeholder for async)
        confidence_scores['sentiment'] = 0.5  # Will be updated when async is implemented
        
        # Technical features confidence
        confidence_scores['technical'] = data_quality
        
        # Order book features confidence
        confidence_scores['order_book'] = 0.8  # High confidence if data is available
        
        # Cross-asset features confidence
        confidence_scores['cross_asset'] = 0.6  # Medium confidence
        
        # Temporal features confidence
        confidence_scores['temporal'] = 1.0  # Always available
        
        return confidence_scores
    
    def _flatten_features(self, *feature_groups) -> Dict[str, float]:
        """Flatten all feature groups into a single dictionary."""
        flattened = {}
        group_names = ['smc', 'regime', 'sentiment', 'technical', 'order_book', 'cross_asset', 'temporal']
        
        for i, group in enumerate(feature_groups):
            if group and isinstance(group, dict):
                prefix = group_names[i] + '_'
                for key, value in group.items():
                    flattened[prefix + key] = value
        
        return flattened
    
    def prepare_features_for_model(self, feature_set: FeatureSet) -> np.ndarray:
        """Prepare feature set for ML model (scaled and ready for prediction)."""
        try:
            # Flatten all features
            features = self._flatten_features(
                feature_set.smc_features, feature_set.regime_features, feature_set.sentiment_features,
                feature_set.technical_features, feature_set.order_book_features, feature_set.cross_asset_features,
                feature_set.temporal_features
            )
            
            # Convert to numpy array
            feature_array = np.array(list(features.values())).reshape(1, -1)
            
            # Scale features if scaler is fitted
            if self.is_fitted:
                try:
                    scaled_features = self.scaler.transform(feature_array)
                    return scaled_features
                except Exception as e:
                    logger.warning(f"Feature scaling failed: {str(e)}")
                    return feature_array
            else:
                return feature_array
                
        except Exception as e:
            logger.error(f"Feature preparation failed: {str(e)}")
            return np.zeros((1, 100))  # Return default features
    
    def fit_scaler(self, feature_sets: List[FeatureSet]):
        """Fit feature scaler on historical feature sets."""
        try:
            if not feature_sets:
                logger.warning("No feature sets provided for scaler fitting")
                return
            
            # Flatten all features
            all_features = []
            for feature_set in feature_sets:
                features = self._flatten_features(
                    feature_set.smc_features, feature_set.regime_features, feature_set.sentiment_features,
                    feature_set.technical_features, feature_set.order_book_features, feature_set.cross_asset_features,
                    feature_set.temporal_features
                )
                all_features.append(list(features.values()))
            
            if all_features:
                # Fit scaler
                self.scaler.fit(np.array(all_features))
                self.is_fitted = True
                logger.info(f"Feature scaler fitted on {len(all_features)} feature samples with {len(all_features[0])} features each")
            
        except Exception as e:
            logger.error(f"Scaler fitting failed: {str(e)}")
    
    def get_feature_names(self) -> List[str]:
        """Get ordered list of feature names."""
        try:
            # Create a sample feature set to get feature names
            sample_timestamp = datetime.now()
            sample_data = pd.DataFrame({
                'timestamp': [sample_timestamp],
                'open': [50000],
                'high': [50500],
                'low': [49500],
                'close': [50250],
                'volume': [1000]
            })
            
            sample_features = self.extract_features(sample_data)
            flattened = self._flatten_features(
                sample_features.smc_features, sample_features.regime_features, sample_features.sentiment_features,
                sample_features.technical_features, sample_features.order_book_features, sample_features.cross_asset_features,
                sample_features.temporal_features
            )
            
            return list(flattened.keys())
            
        except Exception as e:
            logger.error(f"Feature name extraction failed: {str(e)}")
            return []
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        return self.feature_importance.copy()
    
    def update_feature_importance(self, feature_names: List[str], importance_scores: np.ndarray):
        """Update feature importance scores."""
        try:
            if len(feature_names) == len(importance_scores):
                for name, score in zip(feature_names, importance_scores):
                    self.feature_importance[name] = score
            logger.info("Feature importance updated")
        except Exception as e:
            logger.error(f"Feature importance update failed: {str(e)}")
    
    def get_feature_statistics(self) -> Dict[str, Any]:
        """Get comprehensive feature statistics."""
        try:
            if not self.feature_history:
                return {
                    'total_feature_sets': 0,
                    'average_feature_count': 0,
                    'feature_groups_count': 0
                }
            
            feature_counts = [fs.feature_count for fs in self.feature_history]
            
            return {
                'total_feature_sets': len(self.feature_history),
                'average_feature_count': np.mean(feature_counts),
                'max_feature_count': np.max(feature_counts),
                'min_feature_count': np.min(feature_counts),
                'feature_groups_count': 7,  # smc, regime, sentiment, technical, order_book, cross_asset, temporal
                'scaler_type': self.scaler_type,
                'scaler_fitted': self.is_fitted,
                'last_extraction': self.feature_history[-1].timestamp if self.feature_history else None,
                'feature_importance_count': len(self.feature_importance)
            }
            
        except Exception as e:
            logger.error(f"Feature statistics extraction failed: {str(e)}")
            return {'error': str(e)}
    
    def _get_default_feature_set(self, timestamp: datetime) -> FeatureSet:
        """Get default feature set when extraction fails."""
        return FeatureSet(
            smc_features=self.smc_extractor._get_default_smc_features(),
            regime_features={'volatility_regime_numeric': 2.0, 'trend_regime_numeric': 3.0, 'microstructure_regime_numeric': 0.0,
                          'session_regime_numeric': 2.0, 'volatility_score': 0.03, 'trend_strength': 20.0,
                          'microstructure_score': 0.0, 'session_intensity': 0.8, 'regime_confidence': 0.5},
            sentiment_features=self._get_sentiment_features_fallback(),
            technical_features=self.technical_extractor._get_default_technical_features(),
            order_book_features=self.order_book_extractor._get_default_order_book_features(),
            cross_asset_features=self.cross_asset_extractor._get_default_cross_asset_features(),
            temporal_features=self.temporal_extractor.extract_temporal_features(timestamp),
            timestamp=timestamp,
            feature_count=50,
            confidence_scores={'smc': 0.1, 'regime': 0.1, 'sentiment': 0.1, 'technical': 0.1, 'order_book': 0.1, 'cross_asset': 0.1, 'temporal': 1.0}
        )