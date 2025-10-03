from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradingRecord:
    """
    Record of a completed trade for Kelly criterion calculation.
    """
    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    win: bool
    risk_amount: float  # Amount risked on the trade
    
    @property
    def return_ratio(self) -> float:
        """
        Calculate return as ratio of PnL to risk amount.
        
        Returns:
            Return ratio (positive for wins, negative for losses)
        """
        if self.risk_amount <= 0:
            return 0.0
        return self.pnl / self.risk_amount


class KellyCriterionCalculator:
    """
    Kelly Criterion calculator for optimal position sizing.
    
    The Kelly Criterion determines the optimal fraction of capital to risk
    on each trade to maximize long-term growth while avoiding ruin.
    
    Formula: f* = (bp - q) / b
    Where:
    - f* = fraction of capital to wager
    - b = odds received on the wager (win/loss ratio)
    - p = probability of winning
    - q = probability of losing (1 - p)
    """
    
    def __init__(self, 
                 lookback_trades: int = 100,
                 min_trades_required: int = 20,
                 scaling_factor: float = 0.25,
                 max_kelly_fraction: float = 0.20,
                 min_kelly_fraction: float = 0.01):
        """
        Initialize Kelly Criterion calculator.
        
        Args:
            lookback_trades: Number of recent trades to analyze
            min_trades_required: Minimum trades needed for calculation
            scaling_factor: Conservative scaling of Kelly percentage (0.25 = 25% of full Kelly)
            max_kelly_fraction: Maximum allowed Kelly fraction
            min_kelly_fraction: Minimum Kelly fraction to prevent zero sizing
        """
        self.lookback_trades = lookback_trades
        self.min_trades_required = min_trades_required
        self.scaling_factor = scaling_factor
        self.max_kelly_fraction = max_kelly_fraction
        self.min_kelly_fraction = min_kelly_fraction
        
    def calculate_kelly_percentage(self, trading_history: List[TradingRecord]) -> Tuple[float, dict]:
        """
        Calculate Kelly percentage based on trading history.
        
        Args:
            trading_history: List of completed trades
            
        Returns:
            Tuple of (kelly_percentage, statistics_dict)
        """
        if len(trading_history) < self.min_trades_required:
            return self.min_kelly_fraction, {
                'status': 'insufficient_data',
                'trades_count': len(trading_history),
                'min_required': self.min_trades_required
            }
        
        # Use most recent trades for calculation
        recent_trades = trading_history[-self.lookback_trades:]
        
        # Calculate win rate and average returns
        wins = [trade for trade in recent_trades if trade.win]
        losses = [trade for trade in recent_trades if not trade.win]
        
        if not wins or not losses:
            # Need both wins and losses for Kelly calculation
            return self.min_kelly_fraction, {
                'status': 'insufficient_variation',
                'wins': len(wins),
                'losses': len(losses)
            }
        
        win_rate = len(wins) / len(recent_trades)
        loss_rate = 1 - win_rate
        
        # Calculate average win and loss amounts (as ratios)
        avg_win_ratio = np.mean([trade.return_ratio for trade in wins])
        avg_loss_ratio = abs(np.mean([trade.return_ratio for trade in losses]))
        
        # Avoid division by zero
        if avg_loss_ratio <= 0:
            return self.min_kelly_fraction, {
                'status': 'invalid_loss_ratio',
                'avg_loss_ratio': avg_loss_ratio
            }
        
        # Kelly formula: f* = (bp - q) / b
        # Where b = avg_win_ratio / avg_loss_ratio
        win_loss_ratio = avg_win_ratio / avg_loss_ratio
        
        kelly_fraction = (win_loss_ratio * win_rate - loss_rate) / win_loss_ratio
        
        # Apply conservative scaling
        scaled_kelly = kelly_fraction * self.scaling_factor
        
        # Apply bounds
        final_kelly = max(self.min_kelly_fraction, 
                         min(self.max_kelly_fraction, scaled_kelly))
        
        statistics = {
            'status': 'calculated',
            'trades_analyzed': len(recent_trades),
            'win_rate': win_rate,
            'loss_rate': loss_rate,
            'avg_win_ratio': avg_win_ratio,
            'avg_loss_ratio': avg_loss_ratio,
            'win_loss_ratio': win_loss_ratio,
            'raw_kelly': kelly_fraction,
            'scaled_kelly': scaled_kelly,
            'final_kelly': final_kelly,
            'scaling_factor': self.scaling_factor
        }
        
        return final_kelly, statistics
    
    def calculate_position_size(self, 
                              account_balance: float,
                              kelly_percentage: float,
                              entry_price: float,
                              stop_loss_price: float,
                              max_position_value: Optional[float] = None) -> Tuple[float, dict]:
        """
        Calculate position size using Kelly criterion.
        
        Args:
            account_balance: Current account balance
            kelly_percentage: Kelly percentage from calculate_kelly_percentage
            entry_price: Planned entry price
            stop_loss_price: Stop loss price
            max_position_value: Optional maximum position value limit
            
        Returns:
            Tuple of (position_size, calculation_details)
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0, {'error': 'Invalid prices'}
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            return 0.0, {'error': 'No risk (entry price equals stop loss)'}
        
        # Calculate Kelly-based risk amount
        kelly_risk_amount = account_balance * kelly_percentage
        
        # Calculate position size based on risk
        position_size = kelly_risk_amount / risk_per_share
        
        # Apply maximum position value limit if specified
        if max_position_value:
            max_shares_by_value = max_position_value / entry_price
            if position_size > max_shares_by_value:
                position_size = max_shares_by_value
        
        calculation_details = {
            'account_balance': account_balance,
            'kelly_percentage': kelly_percentage,
            'kelly_risk_amount': kelly_risk_amount,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'risk_per_share': risk_per_share,
            'calculated_position_size': position_size,
            'position_value': position_size * entry_price,
            'max_position_value': max_position_value
        }
        
        return position_size, calculation_details
    
    def validate_kelly_parameters(self, trading_history: List[TradingRecord]) -> dict:
        """
        Validate if Kelly criterion is appropriate for current trading performance.
        
        Args:
            trading_history: List of completed trades
            
        Returns:
            Dict containing validation results and recommendations
        """
        if len(trading_history) < self.min_trades_required:
            return {
                'valid': False,
                'reason': 'insufficient_data',
                'recommendation': 'Use fixed percentage risk until more trade data available'
            }
        
        recent_trades = trading_history[-self.lookback_trades:]
        
        # Check for positive expectancy
        total_pnl = sum(trade.pnl for trade in recent_trades)
        avg_pnl = total_pnl / len(recent_trades)
        
        if avg_pnl <= 0:
            return {
                'valid': False,
                'reason': 'negative_expectancy',
                'avg_pnl': avg_pnl,
                'recommendation': 'Review strategy - negative expected value detected'
            }
        
        # Check win rate bounds (should be reasonable)
        win_rate = sum(1 for trade in recent_trades if trade.win) / len(recent_trades)
        
        if win_rate < 0.1 or win_rate > 0.9:
            return {
                'valid': False,
                'reason': 'extreme_win_rate',
                'win_rate': win_rate,
                'recommendation': 'Win rate too extreme - may indicate data issues'
            }
        
        # Check for reasonable variance in returns
        returns = [trade.return_ratio for trade in recent_trades]
        return_std = np.std(returns)
        
        if return_std < 0.01:
            return {
                'valid': False,
                'reason': 'low_variance',
                'return_std': return_std,
                'recommendation': 'Returns too consistent - may not benefit from Kelly sizing'
            }
        
        return {
            'valid': True,
            'avg_pnl': avg_pnl,
            'win_rate': win_rate,
            'return_std': return_std,
            'recommendation': 'Kelly criterion appears suitable for this strategy'
        }
    
    def get_kelly_statistics(self, trading_history: List[TradingRecord]) -> dict:
        """
        Get comprehensive Kelly criterion statistics.
        
        Args:
            trading_history: List of completed trades
            
        Returns:
            Dict containing detailed statistics
        """
        kelly_percentage, calc_stats = self.calculate_kelly_percentage(trading_history)
        validation = self.validate_kelly_parameters(trading_history)
        
        return {
            'kelly_percentage': kelly_percentage,
            'calculation_stats': calc_stats,
            'validation': validation,
            'configuration': {
                'lookback_trades': self.lookback_trades,
                'min_trades_required': self.min_trades_required,
                'scaling_factor': self.scaling_factor,
                'max_kelly_fraction': self.max_kelly_fraction,
                'min_kelly_fraction': self.min_kelly_fraction
            }
        }