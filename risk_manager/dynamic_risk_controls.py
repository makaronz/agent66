"""
Dynamic Risk Controls with Adaptive Position Sizing

This module implements sophisticated risk management with:
- Adaptive position sizing based on volatility and market conditions
- Kelly Criterion implementation with fractional Kelly approach
- Time-varying risk limits based on market regimes
- Market regime-aware risk adjustments
- Real-time risk monitoring and dynamic rebalancing
- Risk-adjusted performance optimization
"""

import numpy as np
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from scipy import stats, optimize
from scipy.optimize import minimize
import json
from collections import deque
import warnings

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications."""
    BULL_VOLATILE = "bull_volatile"
    BULL_STABLE = "bull_stable"
    BEAR_VOLATILE = "bear_volatile"
    BEAR_STABLE = "bear_stable"
    SIDEWAYS_LOW_VOL = "sideways_low_vol"
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"
    TRANSITION = "transition"
    CRISIS = "crisis"

class PositionSizingMethod(Enum):
    """Position sizing methodologies."""
    FIXED_FRACTIONAL = "fixed_fractional"
    KELLY_CRITERION = "kelly_criterion"
    FRACTIONAL_KELLY = "fractional_kelly"
    VOLATILITY_TARGETED = "volatility_targeted"
    RISK_PARITY = "risk_parity"
    ADAPTIVE_AUM = "adaptive_aum"
    CONFIDENCE_WEIGHTED = "confidence_weighted"

class RiskAdjustmentFactor(Enum):
    """Risk adjustment factor types."""
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    LIQUIDITY = "liquidity"
    DRAWDOWN = "drawdown"
    REGIME = "regime"
    SEASONAL = "seasonal"

@dataclass
class MarketRegimeDetection:
    """Market regime detection results."""
    current_regime: MarketRegime
    regime_probability: float
    transition_probability: Dict[MarketRegime, float]
    market_volatility: float
    trend_strength: float
    momentum: float
    regime_duration: int
    confidence: float
    timestamp: datetime

@dataclass
class KellyCalculation:
    """Kelly Criterion calculation results."""
    optimal_fraction: float
    expected_return: float
    win_probability: float
    average_win: float
    average_loss: float
    sharpe_ratio: float
    max_drawdown_estimate: float
    recommended_fraction: float  # After safety adjustments
    safety_multiplier: float
    timestamp: datetime

@dataclass
class RiskLimits:
    """Dynamic risk limits."""
    max_position_size: float
    max_portfolio_risk: float
    max_daily_loss: float
    max_drawdown: float
    var_limit: float
    leverage_limit: float
    correlation_limit: float
    concentration_limit: float
    regime_adjusted: bool
    timestamp: datetime

@dataclass
class PositionSizeRecommendation:
    """Position sizing recommendation."""
    symbol: str
    recommended_size: float
    method: PositionSizingMethod
    risk_amount: float
    confidence: float
    adjustment_factors: Dict[str, float]
    safety_buffers: Dict[str, float]
    expected_return: float
    risk_adjusted_return: float
    priority: int
    timestamp: datetime

class DynamicRiskControls:
    """
    Dynamic risk management system with adaptive controls.

    Provides sophisticated position sizing, Kelly Criterion implementation,
    and market regime-aware risk adjustments.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Dynamic Risk Controls.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Base risk parameters
        self.base_risk_limits = {
            'max_position_size': self.config.get('max_position_size', 0.05),  # 5% of portfolio
            'max_portfolio_risk': self.config.get('max_portfolio_risk', 0.02),  # 2% daily
            'max_daily_loss': self.config.get('max_daily_loss', 0.03),  # 3% daily
            'max_drawdown': self.config.get('max_drawdown', 0.15),  # 15% max
            'var_limit': self.config.get('var_limit', 0.025),  # 2.5% VaR
            'leverage_limit': self.config.get('leverage_limit', 2.0),  # 2x leverage
            'correlation_limit': self.config.get('correlation_limit', 0.7),
            'concentration_limit': self.config.get('concentration_limit', 0.15)
        }

        # Kelly Criterion parameters
        self.kelly_config = {
            'max_kelly_fraction': self.config.get('max_kelly_fraction', 0.25),  # Max 25%
            'kelly_safety_multiplier': self.config.get('kelly_safety_multiplier', 0.5),  # Fractional Kelly
            'min_win_probability': self.config.get('min_win_probability', 0.55),
            'min_trades_for_kelly': self.config.get('min_trades_for_kelly', 30),
            'lookback_period': self.config.get('kelly_lookback', 100)
        }

        # Volatility targeting
        self.volatility_target = self.config.get('volatility_target', 0.12)  # 12% annual
        self.volatility_lookback = self.config.get('volatility_lookback', 60)

        # Market regime detection
        self.regime_detection_config = {
            'lookback_period': self.config.get('regime_lookback', 252),
            'trend_period': self.config.get('trend_period', 50),
            'volatility_window': self.config.get('volatility_window', 20),
            'regime_persistence': self.config.get('regime_persistence', 10)  # Minimum days
        }

        # Position sizing methods
        self.position_sizing_method = PositionSizingMethod(
            self.config.get('position_sizing_method', 'adaptive_aum')
        )

        # State tracking
        self.current_regime: MarketRegime = MarketRegime.BULL_STABLE
        self.regime_history: deque = deque(maxlen=100)
        self.performance_history: deque = deque(maxlen=1000)
        self.risk_adjustments: Dict[str, float] = {}

        # Real-time monitoring
        self.monitoring_interval = self.config.get('monitoring_interval', 300)  # 5 minutes
        self.last_update = datetime.utcnow()

        logger.info("Dynamic Risk Controls initialized with adaptive features")

    async def detect_market_regime(self, market_data: pd.DataFrame,
                                  additional_indicators: Optional[Dict[str, pd.Series]] = None) -> MarketRegimeDetection:
        """
        Detect current market regime using multiple indicators.

        Args:
            market_data: Market price data
            additional_indicators: Additional market indicators

        Returns:
            MarketRegimeDetection: Market regime analysis
        """
        try:
            if len(market_data) < self.regime_detection_config['lookback_period']:
                return MarketRegimeDetection(
                    current_regime=MarketRegime.TRANSITION,
                    regime_probability=0.5,
                    transition_probability={},
                    market_volatility=0.0,
                    trend_strength=0.0,
                    momentum=0.0,
                    regime_duration=0,
                    confidence=0.0,
                    timestamp=datetime.utcnow()
                )

            # Calculate market indicators
            prices = market_data['close']
            returns = prices.pct_change().dropna()

            # Trend analysis
            trend_period = self.regime_detection_config['trend_period']
            short_ma = prices.rolling(trend_period).mean()
            long_ma = prices.rolling(trend_period * 2).mean()
            trend_strength = (short_ma.iloc[-1] - long_ma.iloc[-1]) / long_ma.iloc[-1]

            # Volatility analysis
            volatility_window = self.regime_detection_config['volatility_window']
            volatility = returns.rolling(volatility_window).std().iloc[-1] * np.sqrt(252)

            # Momentum indicators
            momentum_20 = prices.pct_change(20).iloc[-1]
            momentum_60 = prices.pct_change(60).iloc[-1]

            # Determine regime based on indicators
            regime_probabilities = self._calculate_regime_probabilities(
                trend_strength, volatility, momentum_20, momentum_60
            )

            # Select most probable regime
            current_regime = max(regime_probabilities.items(), key=lambda x: x[1])[0]

            # Calculate transition probabilities
            transition_probabilities = self._calculate_transition_probabilities(current_regime)

            # Determine confidence
            max_prob = max(regime_probabilities.values())
            confidence = (max_prob - 1/len(regime_probabilities)) / (1 - 1/len(regime_probabilities))

            # Calculate regime duration
            regime_duration = self._calculate_regime_duration(current_regime)

            result = MarketRegimeDetection(
                current_regime=current_regime,
                regime_probability=regime_probabilities[current_regime],
                transition_probability=transition_probabilities,
                market_volatility=volatility,
                trend_strength=trend_strength,
                momentum=momentum_20,
                regime_duration=regime_duration,
                confidence=confidence,
                timestamp=datetime.utcnow()
            )

            # Update state
            self.current_regime = current_regime
            self.regime_history.append(result)

            logger.info(f"Market regime detected: {current_regime.value} (confidence: {confidence:.2f})")
            return result

        except Exception as e:
            logger.error(f"Market regime detection failed: {e}")
            raise

    async def calculate_kelly_criterion(self, trade_history: pd.DataFrame,
                                      symbol: Optional[str] = None) -> KellyCalculation:
        """
        Calculate Kelly Criterion for position sizing.

        Args:
            trade_history: Historical trade data with returns
            symbol: Specific symbol (if None, use all trades)

        Returns:
            KellyCalculation: Kelly Criterion results
        """
        try:
            # Filter trades for symbol if specified
            if symbol and 'symbol' in trade_history.columns:
                symbol_trades = trade_history[trade_history['symbol'] == symbol]
            else:
                symbol_trades = trade_history

            if len(symbol_trades) < self.kelly_config['min_trades_for_kelly']:
                # Not enough data for reliable Kelly calculation
                return KellyCalculation(
                    optimal_fraction=0.0,
                    expected_return=0.0,
                    win_probability=0.5,
                    average_win=0.0,
                    average_loss=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown_estimate=0.0,
                    recommended_fraction=0.01,  # Conservative default
                    safety_multiplier=self.kelly_config['kelly_safety_multiplier'],
                    timestamp=datetime.utcnow()
                )

            # Extract returns and outcomes
            if 'return' in symbol_trades.columns:
                returns = symbol_trades['return']
            elif 'pnl' in symbol_trades.columns and 'entry_price' in symbol_trades.columns:
                # Calculate returns from PnL
                returns = symbol_trades['pnl'] / symbol_trades['entry_price']
            else:
                # Assume first numeric column is returns
                numeric_columns = symbol_trades.select_dtypes(include=[np.number]).columns
                if len(numeric_columns) > 0:
                    returns = symbol_trades[numeric_columns[0]]
                else:
                    raise ValueError("No return data found in trade history")

            # Calculate Kelly parameters
            wins = returns[returns > 0]
            losses = returns[returns < 0]

            win_probability = len(wins) / len(returns) if len(returns) > 0 else 0
            average_win = wins.mean() if len(wins) > 0 else 0
            average_loss = abs(losses.mean()) if len(losses) > 0 else 0

            # Calculate expected return and variance
            expected_return = returns.mean()
            return_variance = returns.var()

            # Calculate Sharpe ratio
            sharpe_ratio = expected_return / np.sqrt(return_variance) if return_variance > 0 else 0

            # Calculate Kelly fraction
            if win_probability > 0 and average_loss > 0:
                win_loss_ratio = average_win / average_loss
                kelly_fraction = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio
                kelly_fraction = max(0, kelly_fraction)  # Ensure non-negative
            else:
                kelly_fraction = 0.0

            # Apply safety constraints
            max_kelly = self.kelly_config['max_kelly_fraction']
            safety_multiplier = self.kelly_config['kelly_safety_multiplier']
            recommended_fraction = min(kelly_fraction * safety_multiplier, max_kelly)

            # Estimate maximum drawdown (simplified)
            max_drawdown_estimate = self._estimate_max_drawdown(kelly_fraction, returns.std())

            result = KellyCalculation(
                optimal_fraction=kelly_fraction,
                expected_return=expected_return,
                win_probability=win_probability,
                average_win=average_win,
                average_loss=average_loss,
                sharpe_ratio=sharpe_ratio,
                max_drawdown_estimate=max_drawdown_estimate,
                recommended_fraction=recommended_fraction,
                safety_multiplier=safety_multiplier,
                timestamp=datetime.utcnow()
            )

            logger.info(f"Kelly calculation for {symbol or 'portfolio'}: "
                       f"f={kelly_fraction:.3f}, recommended={recommended_fraction:.3f}")

            return result

        except Exception as e:
            logger.error(f"Kelly calculation failed: {e}")
            raise

    async def calculate_adaptive_position_size(self,
                                             symbol: str,
                                             account_balance: float,
                                             market_data: pd.DataFrame,
                                             trade_history: Optional[pd.DataFrame] = None,
                                             confidence: float = 0.7,
                                             current_positions: Optional[Dict[str, float]] = None) -> PositionSizeRecommendation:
        """
        Calculate adaptive position size based on multiple factors.

        Args:
            symbol: Trading symbol
            account_balance: Account balance
            market_data: Market data for analysis
            trade_history: Historical trade data
            confidence: Trade confidence score
            current_positions: Current positions and sizes

        Returns:
            PositionSizeRecommendation: Position sizing recommendation
        """
        try:
            # Initialize adjustment factors
            adjustment_factors = {}
            safety_buffers = {}

            # Base position size calculation
            if self.position_sizing_method == PositionSizingMethod.FIXED_FRACTIONAL:
                base_size = self._calculate_fixed_fractional_size(account_balance, confidence)
            elif self.position_sizing_method == PositionSizingMethod.KELLY_CRITERION:
                kelly_result = await self.calculate_kelly_criterion(trade_history, symbol)
                base_size = kelly_result.recommended_fraction * account_balance
            elif self.position_sizing_method == PositionSizingMethod.VOLATILITY_TARGETED:
                base_size = await self._calculate_volatility_targeted_size(
                    symbol, account_balance, market_data
                )
            elif self.position_sizing_method == PositionSizingMethod.RISK_PARITY:
                base_size = await self._calculate_risk_parity_size(
                    symbol, account_balance, market_data, current_positions
                )
            elif self.position_sizing_method == PositionSizingMethod.CONFIDENCE_WEIGHTED:
                base_size = self._calculate_confidence_weighted_size(account_balance, confidence)
            else:  # Default to adaptive AUM
                base_size = await self._calculate_adaptive_aum_size(
                    symbol, account_balance, market_data, confidence
                )

            # Apply market regime adjustments
            regime_adjustment = await self._get_regime_adjustment(market_data)
            adjustment_factors['regime'] = regime_adjustment

            # Apply volatility adjustments
            volatility_adjustment = await self._get_volatility_adjustment(market_data)
            adjustment_factors['volatility'] = volatility_adjustment

            # Apply correlation adjustments
            if current_positions:
                correlation_adjustment = await self._get_correlation_adjustment(
                    symbol, market_data, current_positions
                )
                adjustment_factors['correlation'] = correlation_adjustment

            # Apply concentration adjustments
            if current_positions:
                concentration_adjustment = await self._get_concentration_adjustment(
                    symbol, current_positions
                )
                adjustment_factors['concentration'] = concentration_adjustment

            # Apply liquidity adjustments
            liquidity_adjustment = await self._get_liquidity_adjustment(market_data)
            adjustment_factors['liquidity'] = liquidity_adjustment

            # Apply drawdown adjustments
            drawdown_adjustment = await self._get_drawdown_adjustment(account_balance)
            adjustment_factors['drawdown'] = drawdown_adjustment

            # Calculate final adjusted size
            total_adjustment = np.prod(list(adjustment_factors.values()))
            adjusted_size = base_size * total_adjustment

            # Apply safety buffers
            safety_buffers['max_position'] = self.base_risk_limits['max_position_size'] * account_balance
            safety_buffers['min_position'] = 0.01 * account_balance  # Minimum 1% position
            safety_buffers['kelly_limit'] = self.kelly_config['max_kelly_fraction'] * account_balance

            # Apply final safety constraints
            final_size = min(adjusted_size, safety_buffers['max_position'])
            final_size = min(final_size, safety_buffers['kelly_limit'])
            final_size = max(final_size, safety_buffers['min_position'])

            # Calculate risk metrics
            current_price = market_data['close'].iloc[-1]
            position_size = final_size / current_price
            risk_amount = final_size * 0.02  # Assume 2% risk

            # Calculate expected returns (simplified)
            expected_return = self._estimate_expected_return(market_data, confidence)
            risk_adjusted_return = expected_return / (market_data['close'].pct_change().std() * np.sqrt(252))

            # Determine priority
            priority = self._calculate_position_priority(
                symbol, confidence, adjustment_factors, expected_return
            )

            result = PositionSizeRecommendation(
                symbol=symbol,
                recommended_size=position_size,
                method=self.position_sizing_method,
                risk_amount=risk_amount,
                confidence=confidence,
                adjustment_factors=adjustment_factors,
                safety_buffers=safety_buffers,
                expected_return=expected_return,
                risk_adjusted_return=risk_adjusted_return,
                priority=priority,
                timestamp=datetime.utcnow()
            )

            logger.info(f"Adaptive position size for {symbol}: {position_size:.4f} "
                       f"(base: {base_size/current_price:.4f}, adjustment: {total_adjustment:.3f})")

            return result

        except Exception as e:
            logger.error(f"Adaptive position sizing failed for {symbol}: {e}")
            raise

    async def update_dynamic_risk_limits(self, market_data: pd.DataFrame,
                                       portfolio_data: Optional[pd.DataFrame] = None) -> RiskLimits:
        """
        Update dynamic risk limits based on market conditions.

        Args:
            market_data: Market data
            portfolio_data: Portfolio performance data

        Returns:
            RiskLimits: Updated risk limits
        """
        try:
            # Detect market regime
            regime_detection = await self.detect_market_regime(market_data)

            # Calculate regime adjustments
            regime_adjustments = self._get_regime_risk_adjustments(regime_detection.current_regime)

            # Update risk limits with regime adjustments
            adjusted_limits = {}
            for limit_name, base_value in self.base_risk_limits.items():
                adjustment_factor = regime_adjustments.get(limit_name, 1.0)
                adjusted_limits[limit_name] = base_value * adjustment_factor

            # Apply additional adjustments based on portfolio performance
            if portfolio_data is not None and len(portfolio_data) > 0:
                performance_adjustments = await self._calculate_performance_adjustments(portfolio_data)
                for limit_name, adjustment in performance_adjustments.items():
                    adjusted_limits[limit_name] *= adjustment

            # Ensure limits stay within reasonable bounds
            for limit_name in adjusted_limits:
                if limit_name == 'leverage_limit':
                    adjusted_limits[limit_name] = max(0.5, min(adjusted_limits[limit_name], 3.0))
                elif 'max_' in limit_name and limit_name != 'max_position_size':
                    adjusted_limits[limit_name] = max(0.005, min(adjusted_limits[limit_name], 0.1))

            result = RiskLimits(
                max_position_size=adjusted_limits['max_position_size'],
                max_portfolio_risk=adjusted_limits['max_portfolio_risk'],
                max_daily_loss=adjusted_limits['max_daily_loss'],
                max_drawdown=adjusted_limits['max_drawdown'],
                var_limit=adjusted_limits['var_limit'],
                leverage_limit=adjusted_limits['leverage_limit'],
                correlation_limit=adjusted_limits['correlation_limit'],
                concentration_limit=adjusted_limits['concentration_limit'],
                regime_adjusted=True,
                timestamp=datetime.utcnow()
            )

            self.last_update = datetime.utcnow()
            logger.info(f"Risk limits updated for {regime_detection.current_regime.value} regime")

            return result

        except Exception as e:
            logger.error(f"Risk limits update failed: {e}")
            raise

    # Private implementation methods

    def _calculate_regime_probabilities(self, trend_strength: float, volatility: float,
                                      momentum_20: float, momentum_60: float) -> Dict[MarketRegime, float]:
        """Calculate probabilities for each market regime."""
        probabilities = {}

        # Bull stable: positive trend, low volatility
        if trend_strength > 0.05 and volatility < 0.15:
            probabilities[MarketRegime.BULL_STABLE] = 0.8
            probabilities[MarketRegime.BULL_VOLATILE] = 0.2
        # Bull volatile: positive trend, high volatility
        elif trend_strength > 0.05 and volatility >= 0.15:
            probabilities[MarketRegime.BULL_VOLATILE] = 0.7
            probabilities[MarketRegime.BULL_STABLE] = 0.2
            probabilities[MarketRegime.TRANSITION] = 0.1
        # Bear stable: negative trend, low volatility
        elif trend_strength < -0.05 and volatility < 0.15:
            probabilities[MarketRegime.BEAR_STABLE] = 0.8
            probabilities[MarketRegime.BEAR_VOLATILE] = 0.2
        # Bear volatile: negative trend, high volatility
        elif trend_strength < -0.05 and volatility >= 0.15:
            probabilities[MarketRegime.BEAR_VOLATILE] = 0.7
            probabilities[MarketRegime.BEAR_STABLE] = 0.2
            probabilities[MarketRegime.CRISIS] = 0.1 if volatility > 0.3 else 0.0
        # Sideways markets
        elif abs(trend_strength) <= 0.05:
            if volatility < 0.1:
                probabilities[MarketRegime.SIDEWAYS_LOW_VOL] = 0.8
                probabilities[MarketRegime.SIDEWAYS_HIGH_VOL] = 0.2
            else:
                probabilities[MarketRegime.SIDEWAYS_HIGH_VOL] = 0.7
                probabilities[MarketRegime.SIDEWAYS_LOW_VOL] = 0.3
        else:
            # Transition state
            probabilities[MarketRegime.TRANSITION] = 0.6
            # Distribute remaining probability based on trend
            if trend_strength > 0:
                probabilities[MarketRegime.BULL_STABLE] = 0.2
                probabilities[MarketRegime.BEAR_STABLE] = 0.1
            else:
                probabilities[MarketRegime.BEAR_STABLE] = 0.2
                probabilities[MarketRegime.BULL_STABLE] = 0.1

        return probabilities

    def _calculate_transition_probabilities(self, current_regime: MarketRegime) -> Dict[MarketRegime, float]:
        """Calculate transition probabilities between regimes."""
        # Simplified transition matrix
        transition_matrix = {
            MarketRegime.BULL_STABLE: {
                MarketRegime.BULL_STABLE: 0.7,
                MarketRegime.BULL_VOLATILE: 0.15,
                MarketRegime.TRANSITION: 0.1,
                MarketRegime.SIDEWAYS_LOW_VOL: 0.05
            },
            MarketRegime.BULL_VOLATILE: {
                MarketRegime.BULL_VOLATILE: 0.6,
                MarketRegime.BULL_STABLE: 0.2,
                MarketRegime.TRANSITION: 0.15,
                MarketRegime.CRISIS: 0.05
            },
            MarketRegime.BEAR_STABLE: {
                MarketRegime.BEAR_STABLE: 0.7,
                MarketRegime.BEAR_VOLATILE: 0.15,
                MarketRegime.TRANSITION: 0.1,
                MarketRegime.SIDEWAYS_LOW_VOL: 0.05
            },
            MarketRegime.BEAR_VOLATILE: {
                MarketRegime.BEAR_VOLATILE: 0.6,
                MarketRegime.BEAR_STABLE: 0.2,
                MarketRegime.TRANSITION: 0.15,
                MarketRegime.CRISIS: 0.05
            },
            MarketRegime.SIDEWAYS_LOW_VOL: {
                MarketRegime.SIDEWAYS_LOW_VOL: 0.6,
                MarketRegime.TRANSITION: 0.2,
                MarketRegime.BULL_STABLE: 0.1,
                MarketRegime.BEAR_STABLE: 0.1
            },
            MarketRegime.SIDEWAYS_HIGH_VOL: {
                MarketRegime.SIDEWAYS_HIGH_VOL: 0.5,
                MarketRegime.TRANSITION: 0.3,
                MarketRegime.BULL_VOLATILE: 0.1,
                MarketRegime.BEAR_VOLATILE: 0.1
            },
            MarketRegime.TRANSITION: {
                MarketRegime.TRANSITION: 0.4,
                MarketRegime.BULL_STABLE: 0.2,
                MarketRegime.BEAR_STABLE: 0.2,
                MarketRegime.SIDEWAYS_LOW_VOL: 0.2
            },
            MarketRegime.CRISIS: {
                MarketRegime.CRISIS: 0.7,
                MarketRegime.BEAR_VOLATILE: 0.2,
                MarketRegime.TRANSITION: 0.1
            }
        }

        return transition_matrix.get(current_regime, {current_regime: 1.0})

    def _calculate_regime_duration(self, current_regime: MarketRegime) -> int:
        """Calculate duration of current regime."""
        if not self.regime_history:
            return 0

        duration = 0
        for detection in reversed(self.regime_history):
            if detection.current_regime == current_regime:
                duration += 1
            else:
                break

        return duration

    def _estimate_max_drawdown(self, kelly_fraction: float, volatility: float) -> float:
        """Estimate maximum drawdown for given Kelly fraction and volatility."""
        # Simplified drawdown estimation using Kelly properties
        # The expected maximum drawdown is approximately ln(1/kelly_fraction)
        if kelly_fraction > 0:
            estimated_dd = -np.log(1 - kelly_fraction) if kelly_fraction < 1 else 0.5
        else:
            estimated_dd = 0

        # Adjust for volatility
        volatility_adjustment = volatility / 0.15  # Normalize to 15% volatility
        return min(estimated_dd * volatility_adjustment, 0.5)  # Cap at 50%

    def _calculate_fixed_fractional_size(self, account_balance: float, confidence: float) -> float:
        """Calculate fixed fractional position size."""
        base_fraction = 0.02  # 2% base position
        confidence_adjustment = confidence  # Scale by confidence
        return account_balance * base_fraction * confidence_adjustment

    async def _calculate_volatility_targeted_size(self, symbol: str, account_balance: float,
                                                market_data: pd.DataFrame) -> float:
        """Calculate volatility-targeted position size."""
        # Calculate current volatility
        returns = market_data['close'].pct_change().dropna()
        current_vol = returns.tail(self.volatility_lookback).std() * np.sqrt(252)

        if current_vol == 0:
            return 0.0

        # Target constant volatility exposure
        target_vol_exposure = account_balance * 0.015  # 1.5% volatility exposure
        position_size = target_vol_exposure / (current_vol * 2)  # Use 2x vol as risk estimate

        return position_size

    async def _calculate_risk_parity_size(self, symbol: str, account_balance: float,
                                        market_data: pd.DataFrame,
                                        current_positions: Optional[Dict[str, float]]) -> float:
        """Calculate risk parity position size."""
        # Calculate position volatility
        returns = market_data['close'].pct_change().dropna()
        position_vol = returns.tail(60).std() * np.sqrt(252)

        if position_vol == 0:
            return 0.0

        # Target equal risk contribution
        target_risk_contribution = 0.1  # 10% risk per position
        portfolio_size = account_balance * len(current_positions) if current_positions else account_balance

        position_size = (portfolio_size * target_risk_contribution) / (position_vol * 2)
        return position_size

    def _calculate_confidence_weighted_size(self, account_balance: float, confidence: float) -> float:
        """Calculate confidence-weighted position size."""
        base_size = account_balance * 0.03  # 3% base position
        confidence_weight = (confidence - 0.5) * 2  # Scale to 0-1 range
        return base_size * confidence_weight

    async def _calculate_adaptive_aum_size(self, symbol: str, account_balance: float,
                                         market_data: pd.DataFrame, confidence: float) -> float:
        """Calculate adaptive AUM-based position size."""
        # Calculate base size as percentage of AUM
        base_size = account_balance * 0.025  # 2.5% of AUM

        # Adjust based on market conditions
        market_adjustment = await self._get_regime_adjustment(market_data)
        volatility_adjustment = await self._get_volatility_adjustment(market_data)

        # Apply confidence scaling
        confidence_adjustment = 0.5 + confidence * 0.5  # Scale between 0.5 and 1.0

        return base_size * market_adjustment * volatility_adjustment * confidence_adjustment

    async def _get_regime_adjustment(self, market_data: pd.DataFrame) -> float:
        """Get market regime adjustment factor."""
        try:
            regime_detection = await self.detect_market_regime(market_data)
            regime_adjustments = {
                MarketRegime.BULL_STABLE: 1.2,
                MarketRegime.BULL_VOLATILE: 0.8,
                MarketRegime.BEAR_STABLE: 0.7,
                MarketRegime.BEAR_VOLATILE: 0.5,
                MarketRegime.SIDEWAYS_LOW_VOL: 0.9,
                MarketRegime.SIDEWAYS_HIGH_VOL: 0.6,
                MarketRegime.TRANSITION: 0.7,
                MarketRegime.CRISIS: 0.3
            }

            return regime_adjustments.get(regime_detection.current_regime, 1.0)
        except:
            return 1.0

    async def _get_volatility_adjustment(self, market_data: pd.DataFrame) -> float:
        """Get volatility-based adjustment factor."""
        try:
            returns = market_data['close'].pct_change().dropna()
            current_vol = returns.tail(60).std()
            historical_vol = returns.std()

            if historical_vol == 0:
                return 1.0

            vol_ratio = current_vol / historical_vol

            # Adjust position size inversely to volatility
            if vol_ratio < 0.5:  # Low volatility
                return 1.3
            elif vol_ratio < 1.0:  # Normal to low volatility
                return 1.1
            elif vol_ratio < 1.5:  # Normal to high volatility
                return 0.9
            else:  # High volatility
                return 0.7
        except:
            return 1.0

    async def _get_correlation_adjustment(self, symbol: str, market_data: pd.DataFrame,
                                        current_positions: Dict[str, float]) -> float:
        """Get correlation-based adjustment factor."""
        # Simplified correlation adjustment
        # In practice, this would calculate actual correlations with existing positions
        num_positions = len(current_positions)

        if num_positions == 0:
            return 1.0

        # Reduce position size as portfolio gets more crowded
        if num_positions < 3:
            return 1.1
        elif num_positions < 5:
            return 1.0
        elif num_positions < 10:
            return 0.9
        else:
            return 0.8

    async def _get_concentration_adjustment(self, symbol: str, current_positions: Dict[str, float]) -> float:
        """Get concentration-based adjustment factor."""
        if symbol in current_positions:
            current_weight = current_positions[symbol]
            max_concentration = self.base_risk_limits['concentration_limit']

            if current_weight > max_concentration * 0.8:
                return 0.5  # Heavily reduce if near limit
            elif current_weight > max_concentration * 0.6:
                return 0.7
            elif current_weight > max_concentration * 0.4:
                return 0.9
            else:
                return 1.0

        return 1.0

    async def _get_liquidity_adjustment(self, market_data: pd.DataFrame) -> float:
        """Get liquidity-based adjustment factor."""
        # Simplified liquidity analysis using volume
        if 'volume' in market_data.columns:
            recent_volume = market_data['volume'].tail(20).mean()
            historical_volume = market_data['volume'].mean()

            if historical_volume > 0:
                volume_ratio = recent_volume / historical_volume

                if volume_ratio > 1.5:  # High liquidity
                    return 1.2
                elif volume_ratio > 1.0:  # Normal liquidity
                    return 1.0
                elif volume_ratio > 0.5:  # Low liquidity
                    return 0.8
                else:  # Very low liquidity
                    return 0.6

        return 1.0

    async def _get_drawdown_adjustment(self, account_balance: float) -> float:
        """Get drawdown-based adjustment factor."""
        # This would typically use historical drawdown data
        # For now, return a neutral adjustment
        return 1.0

    def _estimate_expected_return(self, market_data: pd.DataFrame, confidence: float) -> float:
        """Estimate expected return for the position."""
        # Simple momentum-based return estimation
        returns = market_data['close'].pct_change().dropna()
        recent_return = returns.tail(20).mean()

        # Adjust by confidence and annualize
        expected_return = recent_return * confidence * 252
        return expected_return

    def _calculate_position_priority(self, symbol: str, confidence: float,
                                   adjustment_factors: Dict[str, float],
                                   expected_return: float) -> int:
        """Calculate priority for position sizing."""
        # Base priority from confidence
        base_priority = int(confidence * 10)

        # Adjust for expected return
        if expected_return > 0.15:  # 15% annual return
            return min(base_priority - 2, 1)  # Higher priority
        elif expected_return < 0.05:  # 5% annual return
            return max(base_priority + 3, 10)  # Lower priority

        return min(max(base_priority, 1), 10)

    def _get_regime_risk_adjustments(self, regime: MarketRegime) -> Dict[str, float]:
        """Get risk limit adjustments for market regime."""
        regime_adjustments = {
            MarketRegime.BULL_STABLE: {
                'max_position_size': 1.2,
                'max_portfolio_risk': 1.1,
                'max_daily_loss': 1.1,
                'leverage_limit': 1.2
            },
            MarketRegime.BULL_VOLATILE: {
                'max_position_size': 0.8,
                'max_portfolio_risk': 0.9,
                'max_daily_loss': 0.9,
                'leverage_limit': 0.9
            },
            MarketRegime.BEAR_STABLE: {
                'max_position_size': 0.7,
                'max_portfolio_risk': 0.8,
                'max_daily_loss': 0.8,
                'leverage_limit': 0.8
            },
            MarketRegime.BEAR_VOLATILE: {
                'max_position_size': 0.5,
                'max_portfolio_risk': 0.6,
                'max_daily_loss': 0.7,
                'leverage_limit': 0.7
            },
            MarketRegime.SIDEWAYS_LOW_VOL: {
                'max_position_size': 0.9,
                'max_portfolio_risk': 1.0,
                'max_daily_loss': 1.0,
                'leverage_limit': 1.0
            },
            MarketRegime.SIDEWAYS_HIGH_VOL: {
                'max_position_size': 0.7,
                'max_portfolio_risk': 0.8,
                'max_daily_loss': 0.9,
                'leverage_limit': 0.8
            },
            MarketRegime.TRANSITION: {
                'max_position_size': 0.8,
                'max_portfolio_risk': 0.9,
                'max_daily_loss': 0.9,
                'leverage_limit': 0.9
            },
            MarketRegime.CRISIS: {
                'max_position_size': 0.3,
                'max_portfolio_risk': 0.5,
                'max_daily_loss': 0.6,
                'leverage_limit': 0.6
            }
        }

        return regime_adjustments.get(regime, {k: 1.0 for k in regime_adjustments[MarketRegime.BULL_STABLE].keys()})

    async def _calculate_performance_adjustments(self, portfolio_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate risk limit adjustments based on performance."""
        if len(portfolio_data) < 30:
            return {k: 1.0 for k in self.base_risk_limits.keys()}

        returns = portfolio_data.pct_change().dropna()
        current_drawdown = self._calculate_current_drawdown(portfolio_data)
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

        adjustments = {}

        # Reduce limits if in significant drawdown
        if current_drawdown > 0.10:  # 10% drawdown
            adjustments['max_position_size'] = 0.8
            adjustments['max_portfolio_risk'] = 0.9
        elif current_drawdown > 0.05:  # 5% drawdown
            adjustments['max_position_size'] = 0.9

        # Adjust based on Sharpe ratio
        if sharpe_ratio > 1.5:  # Excellent performance
            adjustments['leverage_limit'] = 1.1
        elif sharpe_ratio < 0.5:  # Poor performance
            adjustments['leverage_limit'] = 0.9
            adjustments['max_daily_loss'] = 0.9

        return adjustments

    def _calculate_current_drawdown(self, portfolio_data: pd.DataFrame) -> float:
        """Calculate current drawdown from portfolio data."""
        cumulative = (1 + portfolio_data.pct_change().fillna(0)).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return abs(drawdown.iloc[-1])

# Factory function for easy instantiation
def create_dynamic_risk_controls(config: Optional[Dict[str, Any]] = None) -> DynamicRiskControls:
    """Create dynamic risk controls instance."""
    return DynamicRiskControls(config)