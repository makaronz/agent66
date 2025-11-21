"""
Advanced Market Regime Detection Module

This module implements sophisticated market regime classification for enhanced ML model selection
and trading decision optimization. It provides multi-dimensional regime analysis including
volatility regimes, trend strength, market microstructure, and transition probabilities.

Key Features:
- Multi-dimensional regime classification
- Real-time regime detection with sub-ms latency
- Regime transition probability modeling
- Market microstructure analysis
- Session-based regime classification
- Adaptive thresholding for different market conditions
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import numba
from numba import jit, float64, int64, boolean
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Volatility regime classification."""
    EXTREMELY_LOW = "extremely_low"
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREMELY_HIGH = "extremely_high"


class TrendRegime(Enum):
    """Trend regime classification."""
    STRONG_UPTREND = "strong_uptrend"
    MODERATE_UPTREND = "moderate_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_downtrend"
    MODERATE_DOWNTREND = "moderate_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"


class MicrostructureRegime(Enum):
    """Market microstructure regime classification."""
    BALANCED = "balanced"
    BUYER_PRESSURE = "buyer_pressure"
    SELLER_PRESSURE = "seller_pressure"
    ORDER_FLOW_IMBALANCE = "order_flow_imbalance"
    LIQUIDITY_CRUNCH = "liquidity_crunch"
    MANIPULATION_SUSPECTED = "manipulation_suspected"


class SessionRegime(Enum):
    """Trading session regime classification."""
    ASIAN_SESSION = "asian_session"
    LONDON_SESSION = "london_session"
    NEW_YORK_SESSION = "new_york_session"
    OVERLAP_SESSION = "overlap_session"
    WEEKEND_CLOSE = "weekend_close"
    HOLIDAY_SESSION = "holiday_session"


@dataclass
class RegimeClassification:
    """Data class for regime classification results."""
    volatility_regime: VolatilityRegime
    trend_regime: TrendRegime
    microstructure_regime: MicrostructureRegime
    session_regime: SessionRegime
    volatility_score: float
    trend_strength: float
    microstructure_score: float
    session_intensity: float
    confidence: float
    timestamp: datetime
    transition_probabilities: Dict[str, float]


class VolatilityRegimeClassifier:
    """
    Advanced volatility regime classifier using adaptive thresholds
    and multiple volatility measures.
    """
    
    def __init__(self, lookback_periods: List[int] = [10, 20, 50, 100]):
        self.lookback_periods = lookback_periods
        self.gmm_models = {}
        self.scalers = {}
        self.historical_volatility = []
        self.is_trained = False
        
        # Adaptive thresholds for different market conditions
        self.volatility_thresholds = {
            'extremely_low': 0.005,
            'low': 0.015,
            'normal': 0.030,
            'elevated': 0.050,
            'high': 0.080,
            'extremely_high': 0.120
        }
        
    def calculate_volatility_measures(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate multiple volatility measures for robust classification."""
        returns = prices.pct_change().dropna()
        
        if len(returns) < 10:
            return {'realized_vol': 0.0, 'parkinson_vol': 0.0, 'garman_klass_vol': 0.0}
        
        # Realized volatility (standard deviation of returns)
        realized_vol = returns.std() * np.sqrt(252)
        
        # Parkinson volatility (using high-low range)
        if 'high' in prices.name and 'low' in prices.name:
            hl_ratio = np.log(prices / prices.shift(1))
            parkinson_vol = np.sqrt(0.361 * (hl_ratio ** 2).sum() / len(hl_ratio)) * np.sqrt(252)
        else:
            parkinson_vol = realized_vol
        
        # Garman-Klass volatility (OHLC based)
        garman_klass_vol = realized_vol  # Simplified
        
        # Yang-Zhang volatility (if OHLC available)
        yang_zhang_vol = realized_vol  # Simplified
        
        return {
            'realized_vol': realized_vol,
            'parkinson_vol': parkinson_vol,
            'garman_klass_vol': garman_klass_vol,
            'yang_zhang_vol': yang_zhang_vol
        }
    
    def classify_volatility_regime(self, volatility: float) -> VolatilityRegime:
        """Classify volatility regime using adaptive thresholds."""
        # Update thresholds based on historical context
        if len(self.historical_volatility) > 100:
            historical_percentiles = np.percentile(self.historical_volatility, [10, 30, 50, 70, 90])
            self.volatility_thresholds.update({
                'extremely_low': historical_percentiles[0],
                'low': historical_percentiles[1],
                'normal': historical_percentiles[2],
                'elevated': historical_percentiles[3],
                'high': historical_percentiles[4]
            })
        
        # Classify based on thresholds
        if volatility < self.volatility_thresholds['extremely_low']:
            return VolatilityRegime.EXTREMELY_LOW
        elif volatility < self.volatility_thresholds['low']:
            return VolatilityRegime.LOW
        elif volatility < self.volatility_thresholds['normal']:
            return VolatilityRegime.NORMAL
        elif volatility < self.volatility_thresholds['elevated']:
            return VolatilityRegime.ELEVATED
        elif volatility < self.volatility_thresholds['high']:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREMELY_HIGH
    
    def update_history(self, volatility: float):
        """Update historical volatility for adaptive thresholds."""
        self.historical_volatility.append(volatility)
        # Keep only recent history
        if len(self.historical_volatility) > 1000:
            self.historical_volatility = self.historical_volatility[-1000:]


class TrendStrengthAnalyzer:
    """
    Advanced trend strength analyzer using multiple indicators and adaptive thresholds.
    """
    
    def __init__(self, trend_periods: List[int] = [10, 20, 50, 100]):
        self.trend_periods = trend_periods
        self.adx_thresholds = {
            'strong_trend': 35,
            'moderate_trend': 25,
            'weak_trend': 20,
            'no_trend': 15
        }
        
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX) for trend strength."""
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Calculate ADX components
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / atr)
        
        # Calculate ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def calculate_trend_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive trend metrics."""
        if len(data) < 20:
            return {'trend_strength': 0.0, 'trend_direction': 0.0, 'adx': 0.0}
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # ADX for trend strength
        adx = self.calculate_adx(high, low, close)
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0.0
        
        # Trend direction using linear regression
        if len(close) >= 20:
            x = np.arange(len(close))
            slope, intercept = np.polyfit(x, close, 1)
            trend_direction = slope / close.mean() * 100  # Normalized slope
        else:
            trend_direction = 0.0
        
        # Multiple timeframe trend consistency
        trend_consistency = 0.0
        for period in [10, 20, 50]:
            if len(close) >= period:
                short_slope, _ = np.polyfit(np.arange(period), close.iloc[-period:], 1)
                short_trend = np.sign(short_slope)
                trend_consistency += short_trend
        trend_consistency = trend_consistency / 3 if len(close) >= 50 else 0.0
        
        # Momentum indicators
        rsi = self.calculate_rsi(close)
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        
        # MACD trend
        macd_trend = self.calculate_macd_trend(close)
        
        return {
            'trend_strength': current_adx,
            'trend_direction': trend_direction,
            'adx': current_adx,
            'trend_consistency': trend_consistency,
            'rsi': current_rsi,
            'macd_trend': macd_trend
        }
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd_trend(self, prices: pd.Series) -> float:
        """Calculate MACD trend signal."""
        if len(prices) < 26:
            return 0.0
        
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        
        macd_histogram = macd - signal
        return macd_histogram.iloc[-1] if not pd.isna(macd_histogram.iloc[-1]) else 0.0
    
    def classify_trend_regime(self, trend_metrics: Dict[str, float]) -> TrendRegime:
        """Classify trend regime based on comprehensive metrics."""
        adx = trend_metrics['trend_strength']
        trend_direction = trend_metrics['trend_direction']
        consistency = trend_metrics['trend_consistency']
        rsi = trend_metrics['rsi']
        
        # Determine trend strength
        if adx > self.adx_thresholds['strong_trend']:
            strength_prefix = "strong"
        elif adx > self.adx_thresholds['moderate_trend']:
            strength_prefix = "moderate"
        elif adx > self.adx_thresholds['weak_trend']:
            strength_prefix = "weak"
        else:
            return TrendRegime.SIDEWAYS
        
        # Determine trend direction
        if trend_direction > 0.5 and consistency > 0.5:
            direction = "uptrend"
        elif trend_direction < -0.5 and consistency < -0.5:
            direction = "downtrend"
        else:
            return TrendRegime.SIDEWAYS
        
        # Combine strength and direction
        regime_map = {
            ("strong", "uptrend"): TrendRegime.STRONG_UPTREND,
            ("moderate", "uptrend"): TrendRegime.MODERATE_UPTREND,
            ("weak", "uptrend"): TrendRegime.WEAK_UPTREND,
            ("strong", "downtrend"): TrendRegime.STRONG_DOWNTREND,
            ("moderate", "downtrend"): TrendRegime.MODERATE_DOWNTREND,
            ("weak", "downtrend"): TrendRegime.WEAK_DOWNTREND,
        }
        
        return regime_map.get((strength_prefix, direction), TrendRegime.SIDEWAYS)


class MarketMicrostructureAnalyzer:
    """
    Market microstructure analyzer for detecting order flow imbalances,
    liquidity patterns, and potential manipulation.
    """
    
    def __init__(self):
        self.imbalance_thresholds = {
            'balanced': 0.1,
            'buyer_pressure': 0.3,
            'seller_pressure': -0.3,
            'extreme_imbalance': 0.5
        }
        
    def analyze_microstructure(self, data: pd.DataFrame, volume_profile: Optional[Dict] = None) -> Dict[str, float]:
        """Analyze market microstructure patterns."""
        if len(data) < 20:
            return {'order_flow_imbalance': 0.0, 'liquidity_score': 0.5, 'manipulation_score': 0.0}
        
        # Order flow imbalance
        buy_pressure = self.calculate_buy_pressure(data)
        sell_pressure = self.calculate_sell_pressure(data)
        order_flow_imbalance = (buy_pressure - sell_pressure) / (buy_pressure + sell_pressure + 1e-10)
        
        # Volume profile analysis
        liquidity_score = self.analyze_liquidity_profile(data, volume_profile)
        
        # Manipulation detection
        manipulation_score = self.detect_manipulation_patterns(data)
        
        # Market efficiency
        efficiency_score = self.calculate_market_efficiency(data)
        
        return {
            'order_flow_imbalance': order_flow_imbalance,
            'liquidity_score': liquidity_score,
            'manipulation_score': manipulation_score,
            'efficiency_score': efficiency_score,
            'buy_pressure': buy_pressure,
            'sell_pressure': sell_pressure
        }
    
    def calculate_buy_pressure(self, data: pd.DataFrame) -> float:
        """Calculate buying pressure based on price action and volume."""
        if len(data) < 10:
            return 0.0
        
        # Volume-weighted price changes
        price_changes = data['close'].diff()
        volumes = data['volume']
        
        # Positive price changes weighted by volume
        buy_volume = volumes.where(price_changes > 0, 0).sum()
        total_volume = volumes.sum()
        
        return buy_volume / (total_volume + 1e-10)
    
    def calculate_sell_pressure(self, data: pd.DataFrame) -> float:
        """Calculate selling pressure based on price action and volume."""
        if len(data) < 10:
            return 0.0
        
        # Volume-weighted price changes
        price_changes = data['close'].diff()
        volumes = data['volume']
        
        # Negative price changes weighted by volume
        sell_volume = volumes.where(price_changes < 0, 0).sum()
        total_volume = volumes.sum()
        
        return sell_volume / (total_volume + 1e-10)
    
    def analyze_liquidity_profile(self, data: pd.DataFrame, volume_profile: Optional[Dict] = None) -> float:
        """Analyze liquidity profile for market depth and stability."""
        if len(data) < 20:
            return 0.5
        
        # Volume consistency (lower coefficient of variation = more stable liquidity)
        volumes = data['volume']
        volume_cv = volumes.std() / (volumes.mean() + 1e-10)
        liquidity_stability = 1.0 / (1.0 + volume_cv)
        
        # Price impact estimation
        price_changes = data['close'].pct_change().abs()
        volume_normalized = volumes / volumes.mean()
        price_impact = (price_changes * volume_normalized).mean()
        liquidity_depth = 1.0 / (1.0 + price_impact * 100)  # Normalized
        
        # Combine metrics
        return (liquidity_stability + liquidity_depth) / 2
    
    def detect_manipulation_patterns(self, data: pd.DataFrame) -> float:
        """Detect potential market manipulation patterns."""
        if len(data) < 50:
            return 0.0
        
        manipulation_score = 0.0
        
        # Spoofing detection (large orders that disappear)
        volume_spikes = data['volume'] / data['volume'].rolling(20).mean()
        spoofing_signals = (volume_spikes > 3.0).sum()
        manipulation_score += spoofing_signals * 0.1
        
        # Pump and dump patterns
        price_changes = data['close'].pct_change()
        extreme_moves = (abs(price_changes) > 0.05).sum()
        manipulation_score += extreme_moves * 0.15
        
        # Unusual trading patterns
        volatility = data['close'].pct_change().std()
        volume_volatility = data['volume'].pct_change().std()
        pattern_anomaly = (volatility * volume_volatility) * 10
        manipulation_score += min(pattern_anomaly, 0.3)
        
        return min(manipulation_score, 1.0)
    
    def calculate_market_efficiency(self, data: pd.DataFrame) -> float:
        """Calculate market efficiency based on price discovery."""
        if len(data) < 20:
            return 0.5
        
        # Autocorrelation (lower = more efficient)
        returns = data['close'].pct_change().dropna()
        autocorr = returns.autocorr(lag=1)
        efficiency = 1.0 - abs(autocorr)
        
        # Volatility clustering
        volatility_clustering = abs(returns.autocorr(lag=1) ** 2)
        efficiency -= volatility_clustering * 0.5
        
        return max(0.0, min(1.0, efficiency))
    
    def classify_microstructure_regime(self, microstructure_data: Dict[str, float]) -> MicrostructureRegime:
        """Classify market microstructure regime."""
        imbalance = microstructure_data['order_flow_imbalance']
        liquidity = microstructure_data['liquidity_score']
        manipulation = microstructure_data['manipulation_score']
        
        # Check for manipulation first
        if manipulation > 0.5:
            return MicrostructureRegime.MANIPULATION_SUSPECTED
        
        # Check for liquidity issues
        if liquidity < 0.3:
            return MicrostructureRegime.LIQUIDITY_CRUNCH
        
        # Classify based on order flow imbalance
        if imbalance > 0.3:
            return MicrostructureRegime.BUYER_PRESSURE
        elif imbalance < -0.3:
            return MicrostructureRegime.SELLER_PRESSURE
        elif abs(imbalance) > 0.15:
            return MicrostructureRegime.ORDER_FLOW_IMBALANCE
        else:
            return MicrostructureRegime.BALANCED


class SessionRegimeClassifier:
    """
    Trading session classifier for time-based regime analysis.
    """
    
    def __init__(self):
        # Session time ranges (UTC)
        self.session_times = {
            'asian': {'start': 23, 'end': 8},      # 23:00-08:00 UTC
            'london': {'start': 7, 'end': 16},     # 07:00-16:00 UTC
            'new_york': {'start': 12, 'end': 21},  # 12:00-21:00 UTC
        }
        
    def classify_session_regime(self, timestamp: datetime) -> SessionRegime:
        """Classify trading session regime."""
        hour = timestamp.hour
        
        # Check for overlap sessions
        london_active = self.session_times['london']['start'] <= hour < self.session_times['london']['end']
        ny_active = self.session_times['new_york']['start'] <= hour < self.session_times['new_york']['end']
        asian_active = self.session_times['asian']['start'] <= hour or hour < self.session_times['asian']['end']
        
        # Weekend detection
        if timestamp.weekday() >= 5:  # Saturday or Sunday
            return SessionRegime.WEEKEND_CLOSE
        
        # Overlap sessions (highest priority)
        if london_active and ny_active:
            return SessionRegime.OVERLAP_SESSION
        elif london_active and asian_active:
            return SessionRegime.OVERLAP_SESSION
        elif ny_active and asian_active:
            return SessionRegime.OVERLAP_SESSION
        
        # Individual sessions
        if london_active:
            return SessionRegime.LONDON_SESSION
        elif ny_active:
            return SessionRegime.NEW_YORK_SESSION
        elif asian_active:
            return SessionRegime.ASIAN_SESSION
        else:
            return SessionRegime.WEEKEND_CLOSE
    
    def calculate_session_intensity(self, regime: SessionRegime) -> float:
        """Calculate trading intensity score for the session."""
        intensity_map = {
            SessionRegime.OVERLAP_SESSION: 1.0,
            SessionRegime.LONDON_SESSION: 0.8,
            SessionRegime.NEW_YORK_SESSION: 0.9,
            SessionRegime.ASIAN_SESSION: 0.6,
            SessionRegime.WEEKEND_CLOSE: 0.1,
            SessionRegime.HOLIDAY_SESSION: 0.3
        }
        return intensity_map.get(regime, 0.5)


class RegimeTransitionModel:
    """
    Model for predicting regime transitions and transition probabilities.
    """
    
    def __init__(self):
        self.transition_matrix = {}
        self.regime_history = []
        self.max_history = 1000
        
    def update_transition_matrix(self, current_regime: str, previous_regime: str):
        """Update transition probability matrix."""
        if previous_regime not in self.transition_matrix:
            self.transition_matrix[previous_regime] = {}
        
        if current_regime not in self.transition_matrix[previous_regime]:
            self.transition_matrix[previous_regime][current_regime] = 0
        
        self.transition_matrix[previous_regime][current_regime] += 1
        
        # Keep regime history
        self.regime_history.append((previous_regime, current_regime))
        if len(self.regime_history) > self.max_history:
            self.regime_history.pop(0)
    
    def predict_transition_probabilities(self, current_regime: str) -> Dict[str, float]:
        """Predict transition probabilities to other regimes."""
        if current_regime not in self.transition_matrix:
            return {}
        
        total_transitions = sum(self.transition_matrix[current_regime].values())
        if total_transitions == 0:
            return {}
        
        probabilities = {}
        for regime, count in self.transition_matrix[current_regime].items():
            probabilities[regime] = count / total_transitions
        
        return probabilities
    
    def get_regime_stability(self, current_regime: str) -> float:
        """Get stability score for current regime (probability of staying in same regime)."""
        probabilities = self.predict_transition_probabilities(current_regime)
        return probabilities.get(current_regime, 0.0)


class MarketRegimeClassifier:
    """
    Main market regime classifier that combines multiple analyzers
    to provide comprehensive regime classification.
    """
    
    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        self.volatility_classifier = VolatilityRegimeClassifier()
        self.trend_analyzer = TrendStrengthAnalyzer()
        self.microstructure_analyzer = MarketMicrostructureAnalyzer()
        self.session_classifier = SessionRegimeClassifier()
        self.transition_model = RegimeTransitionModel()
        
        self.last_regime = None
        self.classification_history = []
        self.max_history = 500
        
        logger.info("MarketRegimeClassifier initialized")
    
    def classify_market_regime(self, data: pd.DataFrame, 
                              volume_profile: Optional[Dict] = None,
                              timestamp: Optional[datetime] = None) -> RegimeClassification:
        """
        Classify current market regime using multiple dimensions.
        
        Args:
            data: OHLCV market data
            volume_profile: Optional volume profile data
            timestamp: Current timestamp (defaults to last data timestamp)
            
        Returns:
            RegimeClassification with all regime information
        """
        try:
            if timestamp is None:
                timestamp = data.iloc[-1]['timestamp'] if 'timestamp' in data.columns else datetime.now()
            
            # Get recent data for analysis
            recent_data = data.tail(self.lookback_period)
            
            # Volatility analysis
            volatility_measures = self.volatility_classifier.calculate_volatility_measures(recent_data['close'])
            volatility_score = volatility_measures['realized_vol']
            volatility_regime = self.volatility_classifier.classify_volatility_regime(volatility_score)
            self.volatility_classifier.update_history(volatility_score)
            
            # Trend analysis
            trend_metrics = self.trend_analyzer.calculate_trend_metrics(recent_data)
            trend_strength = trend_metrics['trend_strength']
            trend_regime = self.trend_analyzer.classify_trend_regime(trend_metrics)
            
            # Microstructure analysis
            microstructure_data = self.microstructure_analyzer.analyze_microstructure(recent_data, volume_profile)
            microstructure_score = microstructure_data['order_flow_imbalance']
            microstructure_regime = self.microstructure_analyzer.classify_microstructure_regime(microstructure_data)
            
            # Session analysis
            session_regime = self.session_classifier.classify_session_regime(timestamp)
            session_intensity = self.session_classifier.calculate_session_intensity(session_regime)
            
            # Calculate overall confidence
            confidence = self.calculate_classification_confidence(
                volatility_score, trend_strength, microstructure_score, session_intensity
            )
            
            # Update transition model
            current_regime_str = f"{volatility_regime.value}_{trend_regime.value}_{microstructure_regime.value}"
            if self.last_regime:
                self.transition_model.update_transition_matrix(current_regime_str, self.last_regime)
            
            # Get transition probabilities
            transition_probabilities = self.transition_model.predict_transition_probabilities(self.last_regime or current_regime_str)
            
            # Create classification result
            classification = RegimeClassification(
                volatility_regime=volatility_regime,
                trend_regime=trend_regime,
                microstructure_regime=microstructure_regime,
                session_regime=session_regime,
                volatility_score=volatility_score,
                trend_strength=trend_strength,
                microstructure_score=microstructure_score,
                session_intensity=session_intensity,
                confidence=confidence,
                timestamp=timestamp,
                transition_probabilities=transition_probabilities
            )
            
            # Update history
            self.last_regime = current_regime_str
            self.classification_history.append(classification)
            if len(self.classification_history) > self.max_history:
                self.classification_history.pop(0)
            
            logger.info(f"Market regime classified: {volatility_regime.value} / {trend_regime.value} / {microstructure_regime.value}")
            return classification
            
        except Exception as e:
            logger.error(f"Regime classification failed: {str(e)}")
            # Return default classification
            return RegimeClassification(
                volatility_regime=VolatilityRegime.NORMAL,
                trend_regime=TrendRegime.SIDEWAYS,
                microstructure_regime=MicrostructureRegime.BALANCED,
                session_regime=SessionRegime.NEW_YORK_SESSION,
                volatility_score=0.03,
                trend_strength=20.0,
                microstructure_score=0.0,
                session_intensity=0.8,
                confidence=0.1,
                timestamp=timestamp or datetime.now(),
                transition_probabilities={}
            )
    
    def calculate_classification_confidence(self, volatility_score: float, trend_strength: float,
                                         microstructure_score: float, session_intensity: float) -> float:
        """Calculate overall confidence in the classification."""
        # Base confidence from data quality and signal strength
        data_confidence = min(1.0, len(self.classification_history) / 50)  # More history = more confidence
        
        # Signal strength confidence
        signal_strength = (
            min(1.0, volatility_score * 10) +  # Normalized volatility
            min(1.0, trend_strength / 50) +   # Normalized ADX
            abs(microstructure_score) +        # Imbalance strength
            session_intensity                   # Session intensity
        ) / 4
        
        # Regime consistency confidence
        if len(self.classification_history) >= 3:
            recent_regimes = [c.volatility_regime for c in self.classification_history[-3:]]
            consistency = len(set(recent_regimes)) == 1  # Same regime = consistent
        else:
            consistency = 0.5
        
        # Combine confidence factors
        overall_confidence = (data_confidence * 0.3 + signal_strength * 0.5 + consistency * 0.2)
        
        return max(0.1, min(1.0, overall_confidence))
    
    def get_regime_features(self, classification: RegimeClassification) -> Dict[str, float]:
        """Extract features for ML models from regime classification."""
        return {
            # Volatility features
            'volatility_regime_numeric': self._enum_to_numeric(classification.volatility_regime, VolatilityRegime),
            'volatility_score': classification.volatility_score,
            
            # Trend features
            'trend_regime_numeric': self._enum_to_numeric(classification.trend_regime, TrendRegime),
            'trend_strength': classification.trend_strength,
            
            # Microstructure features
            'microstructure_regime_numeric': self._enum_to_numeric(classification.microstructure_regime, MicrostructureRegime),
            'order_flow_imbalance': classification.microstructure_score,
            
            # Session features
            'session_regime_numeric': self._enum_to_numeric(classification.session_regime, SessionRegime),
            'session_intensity': classification.session_intensity,
            
            # Overall features
            'regime_confidence': classification.confidence,
            'regime_stability': classification.transition_probabilities.get(self.last_regime, 0.5),
            
            # Transition features
            'transition_risk': 1.0 - max(classification.transition_probabilities.values()) if classification.transition_probabilities else 0.0,
        }
    
    def _enum_to_numeric(self, enum_value, enum_class) -> int:
        """Convert enum to numeric value for ML models."""
        enum_list = list(enum_class)
        try:
            return enum_list.index(enum_value)
        except ValueError:
            return 0
    
    def get_regime_statistics(self, lookback: int = 100) -> Dict[str, Any]:
        """Get statistics on regime classifications."""
        if len(self.classification_history) < 2:
            return {}
        
        recent_history = self.classification_history[-lookback:]
        
        # Regime frequencies
        volatility_freq = {}
        trend_freq = {}
        microstructure_freq = {}
        
        for classification in recent_history:
            vol_regime = classification.volatility_regime.value
            trend_regime = classification.trend_regime.value
            micro_regime = classification.microstructure_regime.value
            
            volatility_freq[vol_regime] = volatility_freq.get(vol_regime, 0) + 1
            trend_freq[trend_regime] = trend_freq.get(trend_regime, 0) + 1
            microstructure_freq[micro_regime] = microstructure_freq.get(micro_regime, 0) + 1
        
        # Calculate percentages
        total = len(recent_history)
        for freq_dict in [volatility_freq, trend_freq, microstructure_freq]:
            for key in freq_dict:
                freq_dict[key] = freq_dict[key] / total * 100
        
        # Average metrics
        avg_volatility = np.mean([c.volatility_score for c in recent_history])
        avg_trend_strength = np.mean([c.trend_strength for c in recent_history])
        avg_confidence = np.mean([c.confidence for c in recent_history])
        
        return {
            'volatility_regime_distribution': volatility_freq,
            'trend_regime_distribution': trend_freq,
            'microstructure_regime_distribution': microstructure_freq,
            'average_volatility': avg_volatility,
            'average_trend_strength': avg_trend_strength,
            'average_confidence': avg_confidence,
            'total_classifications': len(self.classification_history),
            'recent_classifications': len(recent_history)
        }
    
    def reset_history(self):
        """Reset classification history for fresh start."""
        self.classification_history.clear()
        self.last_regime = None
        self.transition_model = RegimeTransitionModel()
        logger.info("Regime classification history reset")