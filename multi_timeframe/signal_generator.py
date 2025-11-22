"""
Multi-Timeframe Signal Generator

Intelligent signal generation with weighted scoring, confidence calculation,
entry validation, and risk-adjusted position sizing based on confluence strength.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from collections import defaultdict
import json

from .confluence_engine import ConfluenceScore, TrendDirection

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal type enumeration."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT = "exit"

class SignalStrength(Enum):
    """Signal strength enumeration."""
    VERY_WEAK = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5

@dataclass
class TradingSignal:
    """Comprehensive trading signal with full context."""
    signal_type: SignalType
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 to 1.0
    strength: SignalStrength
    position_size: float  # Percentage of capital
    risk_reward_ratio: float
    timeframe_consensus: Dict[str, float]  # Timeframe to weight mapping
    confluence_score: float
    supporting_factors: List[str] = field(default_factory=list)
    opposing_factors: List[str] = field(default_factory=list)
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expiry_time: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

@dataclass
class TimeframeWeight:
    """Weight configuration for each timeframe."""
    name: str
    trend_weight: float
    confluence_weight: float
    volume_weight: float
    structure_weight: float
    overall_weight: float

@dataclass
class PositionSizingConfig:
    """Configuration for position sizing."""
    max_position_size: float  # Maximum position size percentage
    min_position_size: float  # Minimum position size percentage
    confluence_multiplier: float  # Position size multiplier for confluence
    risk_adjustment_factor: float  # Risk adjustment factor
    base_position_size: float  # Base position size percentage

class SignalValidator:
    """Validates trading signals based on multiple criteria."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_confidence = config.get('min_confidence', 0.7)
        self.min_risk_reward = config.get('min_risk_reward', 1.5)
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)  # 2%
        self.max_correlation = config.get('max_correlation', 0.7)

    def validate_signal(self, signal: TradingSignal,
                       market_data: Dict[str, Any],
                       existing_positions: List[Dict[str, Any]]) -> bool:
        """
        Validate a trading signal against multiple criteria.

        Args:
            signal: Trading signal to validate
            market_data: Current market data
            existing_positions: List of existing positions

        Returns:
            True if signal is valid, False otherwise
        """
        try:
            # Check minimum confidence
            if signal.confidence < self.min_confidence:
                logger.info(f"Signal rejected: Confidence {signal.confidence} below minimum {self.min_confidence}")
                return False

            # Check minimum risk/reward ratio
            if signal.risk_reward_ratio < self.min_risk_reward:
                logger.info(f"Signal rejected: Risk/Reward {signal.risk_reward_ratio} below minimum {self.min_risk_reward}")
                return False

            # Check position size limits
            if signal.position_size > self.config.get('max_position_size', 0.05):
                logger.info(f"Signal rejected: Position size {signal.position_size} above maximum")
                return False

            # Check market conditions
            if not self._validate_market_conditions(signal, market_data):
                logger.info("Signal rejected: Unfavorable market conditions")
                return False

            # Check correlation with existing positions
            if not self._validate_correlation(signal, existing_positions):
                logger.info("Signal rejected: High correlation with existing positions")
                return False

            # Check volatility conditions
            if not self._validate_volatility(signal, market_data):
                logger.info("Signal rejected: Unfavorable volatility conditions")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False

    def _validate_market_conditions(self, signal: TradingSignal,
                                  market_data: Dict[str, Any]) -> bool:
        """Validate signal against current market conditions."""
        try:
            # Check if market is open (if applicable)
            if market_data.get('market_closed', False):
                return False

            # Check for high volatility
            volatility = market_data.get('volatility', 0)
            max_volatility = self.config.get('max_volatility', 0.05)
            if volatility > max_volatility:
                return False

            # Check volume conditions
            volume_ratio = market_data.get('volume_ratio', 1.0)
            min_volume = self.config.get('min_volume_ratio', 0.5)
            if volume_ratio < min_volume:
                return False

            # Check spread conditions
            spread = market_data.get('spread', 0)
            max_spread = self.config.get('max_spread', 0.001)
            if spread > max_spread:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating market conditions: {e}")
            return False

    def _validate_correlation(self, signal: TradingSignal,
                            existing_positions: List[Dict[str, Any]]) -> bool:
        """Validate signal correlation with existing positions."""
        try:
            if not existing_positions:
                return True

            # Check exposure to same symbol
            symbol_exposure = sum(pos.get('size', 0) for pos in existing_positions
                                if pos.get('symbol') == signal.symbol)

            max_symbol_exposure = self.config.get('max_symbol_exposure', 0.1)
            if symbol_exposure + signal.position_size > max_symbol_exposure:
                return False

            # Check total exposure
            total_exposure = sum(pos.get('size', 0) for pos in existing_positions)
            max_total_exposure = self.config.get('max_total_exposure', 0.3)

            if total_exposure + signal.position_size > max_total_exposure:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating correlation: {e}")
            return True  # Allow signal if validation fails

    def _validate_volatility(self, signal: TradingSignal,
                           market_data: Dict[str, Any]) -> bool:
        """Validate signal against volatility conditions."""
        try:
            current_volatility = market_data.get('current_volatility', 0.01)
            avg_volatility = market_data.get('avg_volatility', 0.02)

            # Reject if volatility is too high (choppy market)
            max_volatility = self.config.get('max_volatility_multiplier', 2.0) * avg_volatility
            if current_volatility > max_volatility:
                return False

            # Reject if volatility is too low (no movement)
            min_volatility = self.config.get('min_volatility_multiplier', 0.5) * avg_volatility
            if current_volatility < min_volatility:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating volatility: {e}")
            return True

class PositionSizer:
    """Calculates optimal position sizes based on confluence strength and risk parameters."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sizing_config = PositionSizingConfig(
            max_position_size=config.get('max_position_size', 0.05),
            min_position_size=config.get('min_position_size', 0.01),
            confluence_multiplier=config.get('confluence_multiplier', 2.0),
            risk_adjustment_factor=config.get('risk_adjustment_factor', 1.5),
            base_position_size=config.get('base_position_size', 0.02)
        )

    def calculate_position_size(self, signal: TradingSignal,
                               account_balance: float,
                               risk_per_trade: float = 0.02) -> float:
        """
        Calculate optimal position size based on multiple factors.

        Args:
            signal: Trading signal with confidence and confluence data
            account_balance: Current account balance
            risk_per_trade: Risk percentage per trade

        Returns:
            Optimal position size as percentage of account balance
        """
        try:
            # Base position size
            base_size = self.sizing_config.base_position_size

            # Adjust based on confidence
            confidence_adjustment = signal.confidence * self.sizing_config.confluence_multiplier

            # Adjust based on confluence strength
            confluence_adjustment = signal.confluence_score * 0.5

            # Adjust based on risk/reward ratio
            rr_adjustment = min(1.5, signal.risk_reward_ratio / self.sizing_config.risk_adjustment_factor)

            # Adjust based on signal strength
            strength_multiplier = signal.strength.value / 3.0  # Normalize to 0-1

            # Calculate adjusted position size
            adjusted_size = base_size * (
                1.0 + confidence_adjustment +
                confluence_adjustment +
                (rr_adjustment - 1.0) * 0.5 +
                (strength_multiplier - 0.5) * 0.3
            )

            # Apply limits
            final_size = max(
                self.sizing_config.min_position_size,
                min(self.sizing_config.max_position_size, adjusted_size)
            )

            # Further adjust based on account size and risk
            max_risk_amount = account_balance * risk_per_trade
            position_value = account_balance * final_size

            if signal.signal_type == SignalType.BUY:
                risk_amount = position_value * abs(signal.entry_price - signal.stop_loss) / signal.entry_price
            else:
                risk_amount = position_value * abs(signal.stop_loss - signal.entry_price) / signal.entry_price

            if risk_amount > max_risk_amount:
                final_size = max_risk_amount / position_value * final_size

            return min(1.0, final_size)

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.sizing_config.min_position_size

class MultiTimeframeSignalGenerator:
    """
    Main signal generator for multi-timeframe confluence analysis.

    Generates intelligent trading signals based on confluence analysis,
    with confidence scoring, position sizing, and risk management.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validator = SignalValidator(config.get('validation', {}))
        self.position_sizer = PositionSizer(config.get('position_sizing', {}))

        # Timeframe weights for different analysis aspects
        self.timeframe_weights = self._initialize_timeframe_weights()

        # Signal generation parameters
        self.min_confluence_score = config.get('min_confluence_score', 0.6)
        self.signal_expiry_minutes = config.get('signal_expiry_minutes', 30)

        # Performance tracking
        self.signals_generated = []
        self.signal_performance = defaultdict(list)

        logger.info("Multi-timeframe signal generator initialized")

    def _initialize_timeframe_weights(self) -> Dict[str, TimeframeWeight]:
        """Initialize timeframe weights for signal generation."""
        return {
            'M5': TimeframeWeight('M5', 0.05, 0.05, 0.05, 0.05, 0.1),
            'M15': TimeframeWeight('M15', 0.1, 0.1, 0.1, 0.1, 0.15),
            'H1': TimeframeWeight('H1', 0.2, 0.2, 0.2, 0.2, 0.25),
            'H4': TimeframeWeight('H4', 0.3, 0.3, 0.3, 0.3, 0.25),
            'D1': TimeframeWeight('D1', 0.35, 0.35, 0.35, 0.35, 0.25)
        }

    def generate_signals(self, symbol: str,
                        confluence_scores: List[ConfluenceScore],
                        current_price: float,
                        market_data: Dict[str, Any],
                        existing_positions: List[Dict[str, Any]] = None) -> List[TradingSignal]:
        """
        Generate trading signals based on confluence analysis.

        Args:
            symbol: Trading symbol
            confluence_scores: List of confluence scores from analysis engine
            current_price: Current market price
            market_data: Current market data and conditions
            existing_positions: List of existing positions

        Returns:
            List of validated trading signals
        """
        try:
            existing_positions = existing_positions or []
            signals = []

            # Filter for significant confluence levels
            significant_levels = [
                score for score in confluence_scores
                if score.overall_score >= self.min_confluence_score
            ]

            if not significant_levels:
                logger.info(f"No significant confluence levels found for {symbol}")
                return signals

            # Generate signals for each significant level
            for confluence in significant_levels:
                signal = self._generate_signal_for_level(
                    symbol, confluence, current_price, market_data
                )

                if signal and self.validator.validate_signal(signal, market_data, existing_positions):
                    signals.append(signal)
                    logger.info(f"Generated {signal.signal_type.value} signal for {symbol} at {signal.entry_price}")

            # Sort signals by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)

            # Keep only the best signals (limit to avoid overexposure)
            max_signals = self.config.get('max_signals_per_symbol', 2)
            signals = signals[:max_signals]

            # Track generated signals
            self.signals_generated.extend(signals)

            return signals

        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []

    def _generate_signal_for_level(self, symbol: str,
                                 confluence: ConfluenceScore,
                                 current_price: float,
                                 market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate a signal for a specific confluence level."""
        try:
            # Determine signal type and direction
            signal_type, direction = self._determine_signal_direction(
                confluence, current_price
            )

            if signal_type == SignalType.HOLD:
                return None

            # Calculate entry, stop loss, and take profit levels
            entry_price, stop_loss, take_profit = self._calculate_price_levels(
                confluence, current_price, direction
            )

            # Calculate signal strength
            strength = self._calculate_signal_strength(confluence)

            # Calculate confidence
            confidence = self._calculate_signal_confidence(confluence, market_data)

            # Calculate position size
            account_balance = market_data.get('account_balance', 10000)
            position_size = self.position_sizer.calculate_position_size(
                TradingSignal(
                    signal_type=signal_type,
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    strength=strength,
                    position_size=0,  # Will be calculated
                    risk_reward_ratio=0,  # Will be calculated
                    timeframe_consensus={},
                    confluence_score=confluence.overall_score,
                    supporting_factors=confluence.supporting_factors,
                    opposing_factors=confluence.opposing_factors
                ),
                account_balance
            )

            # Calculate risk/reward ratio
            risk_reward_ratio = self._calculate_risk_reward(
                entry_price, stop_loss, take_profit, direction
            )

            # Generate timeframe consensus
            timeframe_consensus = self._generate_timeframe_consensus(confluence)

            # Create entry and exit conditions
            entry_conditions = self._generate_entry_conditions(confluence, market_data)
            exit_conditions = self._generate_exit_conditions(confluence, direction)

            # Calculate expiry time
            expiry_time = datetime.utcnow() + timedelta(minutes=self.signal_expiry_minutes)

            # Generate tags
            tags = self._generate_signal_tags(confluence, strength)

            return TradingSignal(
                signal_type=signal_type,
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                strength=strength,
                position_size=position_size,
                risk_reward_ratio=risk_reward_ratio,
                timeframe_consensus=timeframe_consensus,
                confluence_score=confluence.overall_score,
                supporting_factors=confluence.supporting_factors,
                opposing_factors=confluence.opposing_factors,
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                expiry_time=expiry_time,
                tags=tags
            )

        except Exception as e:
            logger.error(f"Error generating signal for level: {e}")
            return None

    def _determine_signal_direction(self, confluence: ConfluenceScore,
                                  current_price: float) -> Tuple[SignalType, str]:
        """Determine signal type and direction based on confluence analysis."""
        try:
            # Check if price is at or near confluence level
            price_distance = abs(current_price - confluence.price_level) / current_price
            tolerance = 0.01  # 1% tolerance

            if price_distance > tolerance:
                return SignalType.HOLD, "neutral"

            # Analyze supporting vs opposing factors
            support_score = len(confluence.supporting_factors) * 0.1
            opposition_score = len(confluence.opposing_factors) * 0.1

            # Check trend alignment
            trend_score = confluence.trend_alignment

            # Check overall confluence
            confluence_score = confluence.level_confluence

            # Calculate net direction score
            net_score = (support_score + trend_score + confluence_score) - opposition_score

            # Determine signal
            if net_score > 0.3:
                return SignalType.BUY, "bullish"
            elif net_score < -0.3:
                return SignalType.SELL, "bearish"
            else:
                return SignalType.HOLD, "neutral"

        except Exception as e:
            logger.error(f"Error determining signal direction: {e}")
            return SignalType.HOLD, "neutral"

    def _calculate_price_levels(self, confluence: ConfluenceScore,
                               current_price: float,
                               direction: str) -> Tuple[float, float, float]:
        """Calculate entry, stop loss, and take profit levels."""
        try:
            # Entry price
            entry_price = confluence.price_level

            # Calculate ATR-based stops (simplified)
            atr_multiplier = 2.0
            atr_estimate = current_price * 0.02  # Simplified ATR estimate

            if direction == "bullish":
                stop_loss = max(entry_price - atr_estimate * atr_multiplier,
                               confluence.price_level * 0.98)
                take_profit = min(entry_price + atr_estimate * atr_multiplier * 2,
                                confluence.price_level * 1.06)
            else:  # bearish
                stop_loss = min(entry_price + atr_estimate * atr_multiplier,
                               confluence.price_level * 1.02)
                take_profit = max(entry_price - atr_estimate * atr_multiplier * 2,
                                confluence.price_level * 0.94)

            return entry_price, stop_loss, take_profit

        except Exception as e:
            logger.error(f"Error calculating price levels: {e}")
            return current_price, current_price * 0.98, current_price * 1.02

    def _calculate_signal_strength(self, confluence: ConfluenceScore) -> SignalStrength:
        """Calculate signal strength based on confluence analysis."""
        try:
            # Base strength from overall score
            base_strength = confluence.overall_score

            # Adjust based on individual components
            strength_boost = 0
            if confluence.timeframe_agreement > 0.7:
                strength_boost += 1
            if confluence.level_confluence > 0.8:
                strength_boost += 1
            if confluence.volume_confirmation > 0.6:
                strength_boost += 1
            if confluence.trend_alignment > 0.7:
                strength_boost += 1

            # Calculate final strength
            final_strength = base_strength * 5 + strength_boost  # Scale to 1-5
            final_strength = max(1, min(5, int(final_strength)))

            return SignalStrength(final_strength)

        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return SignalStrength.MODERATE

    def _calculate_signal_confidence(self, confluence: ConfluenceScore,
                                   market_data: Dict[str, Any]) -> float:
        """Calculate signal confidence based on multiple factors."""
        try:
            # Base confidence from confluence score
            base_confidence = confluence.confidence

            # Adjust for market conditions
            volatility_factor = 1.0
            if market_data.get('volatility', 0) > 0.03:
                volatility_factor = 0.8  # Reduce confidence in high volatility

            # Adjust for volume confirmation
            volume_factor = min(1.2, market_data.get('volume_ratio', 1.0))

            # Adjust for spread
            spread_factor = 1.0
            if market_data.get('spread', 0) > 0.001:
                spread_factor = 0.9  # Reduce confidence with wide spreads

            # Final confidence calculation
            final_confidence = base_confidence * volatility_factor * volume_factor * spread_factor
            return min(1.0, max(0.0, final_confidence))

        except Exception as e:
            logger.error(f"Error calculating signal confidence: {e}")
            return 0.5

    def _calculate_risk_reward(self, entry_price: float, stop_loss: float,
                             take_profit: float, direction: str) -> float:
        """Calculate risk/reward ratio."""
        try:
            if direction == "bullish":
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
            else:  # bearish
                risk = abs(stop_loss - entry_price)
                reward = abs(entry_price - take_profit)

            if risk <= 0:
                return 1.0

            return reward / risk

        except Exception as e:
            logger.error(f"Error calculating risk/reward: {e}")
            return 1.0

    def _generate_timeframe_consensus(self, confluence: ConfluenceScore) -> Dict[str, float]:
        """Generate consensus scores for each timeframe."""
        try:
            consensus = {}

            # Extract timeframe information from factors
            timeframe_votes = defaultdict(list)

            for factor in confluence.supporting_factors:
                parts = factor.split('_')
                if len(parts) >= 2:
                    timeframe = parts[0]
                    timeframe_votes[timeframe].append(1)

            for factor in confluence.opposing_factors:
                parts = factor.split('_')
                if len(parts) >= 2:
                    timeframe = parts[0]
                    timeframe_votes[timeframe].append(-1)

            # Calculate consensus for each timeframe
            for timeframe, votes in timeframe_votes.items():
                if votes:
                    consensus[timeframe] = sum(votes) / len(votes)

            # Add default values for missing timeframes
            all_timeframes = ['M5', 'M15', 'H1', 'H4', 'D1']
            for tf in all_timeframes:
                if tf not in consensus:
                    consensus[tf] = 0.0

            return consensus

        except Exception as e:
            logger.error(f"Error generating timeframe consensus: {e}")
            return {tf: 0.0 for tf in ['M5', 'M15', 'H1', 'H4', 'D1']}

    def _generate_entry_conditions(self, confluence: ConfluenceScore,
                                  market_data: Dict[str, Any]) -> List[str]:
        """Generate entry conditions for the signal."""
        conditions = []

        try:
            # Price condition
            conditions.append(f"Price within 1% of {confluence.price_level:.2f}")

            # Volume condition
            if confluence.volume_confirmation > 0.5:
                conditions.append("Volume confirmation present")

            # Trend condition
            if confluence.trend_alignment > 0.6:
                conditions.append("Trend alignment confirmed")

            # Timeframe condition
            if confluence.timeframe_agreement > 0.5:
                conditions.append(f"{int(confluence.timeframe_agreement * 100)}% timeframe agreement")

            # Market condition
            if market_data.get('volume_ratio', 1.0) > 1.0:
                conditions.append("Above average volume")

            # Volatility condition
            if market_data.get('volatility', 0.02) < 0.03:
                conditions.append("Acceptable volatility levels")

        except Exception as e:
            logger.error(f"Error generating entry conditions: {e}")

        return conditions

    def _generate_exit_conditions(self, confluence: ConfluenceScore,
                                direction: str) -> List[str]:
        """Generate exit conditions for the signal."""
        conditions = []

        try:
            # Stop loss condition
            conditions.append("Stop loss reached")

            # Take profit condition
            conditions.append("Take profit reached")

            # Signal reversal condition
            if confluence.overall_score > 0.7:
                conditions.append("Strong confluence level reached")

            # Time-based exit
            conditions.append("Signal expiry time reached")

            # Momentum condition
            conditions.append("Momentum reversal detected")

            # Volume condition
            conditions.append("Sudden volume spike against position")

        except Exception as e:
            logger.error(f"Error generating exit conditions: {e}")

        return conditions

    def _generate_signal_tags(self, confluence: ConfluenceScore,
                            strength: SignalStrength) -> List[str]:
        """Generate descriptive tags for the signal."""
        tags = []

        try:
            # Strength tag
            tags.append(strength.name.lower())

            # Confluence tag
            if confluence.overall_score > 0.8:
                tags.append("high-confluence")
            elif confluence.overall_score > 0.6:
                tags.append("medium-confluence")

            # Timeframe tag
            if confluence.timeframe_agreement > 0.7:
                tags.append("multi-timeframe")

            # Volume tag
            if confluence.volume_confirmation > 0.7:
                tags.append("volume-confirmed")

            # Trend tag
            if confluence.trend_alignment > 0.7:
                tags.append("trend-aligned")

        except Exception as e:
            logger.error(f"Error generating signal tags: {e}")

        return tags

    def update_signal_performance(self, signal: TradingSignal, outcome: Dict[str, Any]):
        """Update signal performance tracking."""
        try:
            performance_data = {
                'timestamp': datetime.utcnow(),
                'signal_confidence': signal.confidence,
                'signal_strength': signal.strength.value,
                'confluence_score': signal.confluence_score,
                'outcome': outcome.get('result', 'unknown'),
                'profit_loss': outcome.get('profit_loss', 0),
                'duration_minutes': outcome.get('duration_minutes', 0),
                'exit_reason': outcome.get('exit_reason', 'unknown')
            }

            self.signal_performance[signal.symbol].append(performance_data)

            # Keep only recent performance data (last 100 signals per symbol)
            if len(self.signal_performance[signal.symbol]) > 100:
                self.signal_performance[signal.symbol] = self.signal_performance[signal.symbol][-100:]

        except Exception as e:
            logger.error(f"Error updating signal performance: {e}")

    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal generation and performance statistics."""
        try:
            total_signals = len(self.signals_generated)
            if total_signals == 0:
                return {'total_signals': 0}

            # Calculate overall performance metrics
            total_profit_loss = 0
            winning_signals = 0
            losing_signals = 0

            for symbol_signals in self.signal_performance.values():
                for signal_data in symbol_signals:
                    pnl = signal_data.get('profit_loss', 0)
                    total_profit_loss += pnl
                    if pnl > 0:
                        winning_signals += 1
                    elif pnl < 0:
                        losing_signals += 1

            total_evaluated_signals = winning_signals + losing_signals
            win_rate = winning_signals / max(1, total_evaluated_signals)

            # Average confidence and strength
            avg_confidence = np.mean([s.confidence for s in self.signals_generated[-100:]])
            avg_strength = np.mean([s.strength.value for s in self.signals_generated[-100:]])

            return {
                'total_signals': total_signals,
                'evaluated_signals': total_evaluated_signals,
                'win_rate': win_rate,
                'total_profit_loss': total_profit_loss,
                'average_confidence': avg_confidence,
                'average_strength': avg_strength,
                'signals_per_symbol': {
                    symbol: len(signals) for symbol, signals in self.signal_performance.items()
                }
            }

        except Exception as e:
            logger.error(f"Error getting signal statistics: {e}")
            return {'error': str(e)}

    def export_signals(self, filename: str, limit: int = 100):
        """Export recent signals to file for analysis."""
        try:
            recent_signals = self.signals_generated[-limit:]

            export_data = []
            for signal in recent_signals:
                export_data.append({
                    'timestamp': signal.timestamp.isoformat(),
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type.value,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'confidence': signal.confidence,
                    'strength': signal.strength.name,
                    'position_size': signal.position_size,
                    'risk_reward_ratio': signal.risk_reward_ratio,
                    'confluence_score': signal.confluence_score,
                    'supporting_factors': signal.supporting_factors,
                    'opposing_factors': signal.opposing_factors,
                    'tags': signal.tags
                })

            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported {len(export_data)} signals to {filename}")

        except Exception as e:
            logger.error(f"Error exporting signals: {e}")

    def clear_cache(self):
        """Clear signal cache and performance data."""
        try:
            self.signals_generated.clear()
            self.signal_performance.clear()
            logger.info("Signal cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")