import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class TradingRecord:
    """Trading record for Kelly criterion calculation."""
    profit_loss: float
    win: bool
    timestamp: datetime
    trade_size: float

class SMCRiskManager:
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Kelly criterion settings
        self.kelly_lookback_trades = self.config.get('kelly_lookback_trades', 50)
        self.kelly_scaling_factor = self.config.get('kelly_scaling_factor', 0.75)  # Conservative scaling
        self.max_position_size_pct = self.config.get('max_position_size_pct', 0.25)  # 25% max
        self.min_position_size_pct = self.config.get('min_position_size_pct', 0.01)  # 1% min
        
        # Risk management settings
        self.max_risk_per_trade_pct = self.config.get('max_risk_per_trade_pct', 0.02)  # 2% max risk
        self.max_daily_risk_pct = self.config.get('max_daily_risk_pct', 0.06)  # 6% daily risk
        
        # Trading history for Kelly calculation
        self.trading_history: List[TradingRecord] = []
        
        self.logger.info("Enhanced SMC Risk Manager initialized with Kelly criterion support.")

    def calculate_stop_loss(self, entry_price: float, direction: str, order_blocks: list, structure: dict) -> float:
        """
        Calculates the stop-loss price based on the nearest relevant structure.
        """
        if direction == "BUY":
            # For a long, SL is below the low of the bullish order block
            relevant_ob = self.find_nearest_bullish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['price_level'][1] * 0.998  # 0.2% buffer below the low
                self.logger.info("Calculated SL based on bullish order block.", extra={'sl_price': sl_price})
                return sl_price
            else:
                # Fallback to a generic percentage
                sl_price = entry_price * 0.98 # 2% stop loss
                self.logger.warning("No relevant OB for SL calculation, using fallback.", extra={'sl_price': sl_price})
                return sl_price
        else: # SELL
            # For a short, SL is above the high of the bearish order block
            relevant_ob = self.find_nearest_bearish_ob(entry_price, order_blocks)
            if relevant_ob:
                sl_price = relevant_ob['price_level'][0] * 1.002 # 0.2% buffer above the high
                self.logger.info("Calculated SL based on bearish order block.", extra={'sl_price': sl_price})
                return sl_price
            else:
                sl_price = entry_price * 1.02 # 2% stop loss
                self.logger.warning("No relevant OB for SL calculation, using fallback.", extra={'sl_price': sl_price})
                return sl_price

    def calculate_take_profit(self, entry_price: float, stop_loss_price: float, direction: str, risk_reward_ratio: float = 3.0) -> float:
        """
        Calculates the take-profit price based on a fixed risk/reward ratio.
        """
        risk_per_share = abs(entry_price - stop_loss_price)
        if direction == "BUY":
            tp_price = entry_price + (risk_per_share * risk_reward_ratio)
        else: # SELL
            tp_price = entry_price - (risk_per_share * risk_reward_ratio)
        
        self.logger.info(f"Calculated TP for {risk_reward_ratio}:1 R/R.", extra={'tp_price': tp_price})
        return tp_price

    def find_nearest_bullish_ob(self, entry_price, order_blocks):
        # Finds the closest bullish order block below the entry price
        # For a bullish order block, we want the low to be below entry price for stop loss placement
        bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish' and ob['price_level'][1] < entry_price]
        if not bullish_obs:
            return None
        return min(bullish_obs, key=lambda ob: entry_price - ob['price_level'][1])

    def calculate_kelly_criterion(self) -> float:
        """
        Calculate Kelly criterion percentage based on recent trading history.
        
        Returns:
            float: Kelly percentage (0.0 to 1.0), scaled by safety factor
        """
        if len(self.trading_history) < 10:
            self.logger.warning("Insufficient trading history for Kelly calculation, using conservative 2%")
            return 0.02
        
        # Use recent trades for calculation
        recent_trades = self.trading_history[-self.kelly_lookback_trades:]
        
        wins = [trade for trade in recent_trades if trade.win]
        losses = [trade for trade in recent_trades if not trade.win]
        
        if not wins or not losses:
            self.logger.warning("No wins or losses in history, using conservative sizing")
            return 0.02
        
        # Calculate win probability
        win_probability = len(wins) / len(recent_trades)
        
        # Calculate average win/loss ratio
        avg_win = np.mean([trade.profit_loss for trade in wins])
        avg_loss = abs(np.mean([trade.profit_loss for trade in losses]))
        
        if avg_loss == 0:
            return 0.02
        
        win_loss_ratio = avg_win / avg_loss
        
        # Kelly formula: f = (bp - q) / b
        # where b = win_loss_ratio, p = win_probability, q = loss_probability
        kelly_pct = (win_loss_ratio * win_probability - (1 - win_probability)) / win_loss_ratio
        
        # Apply scaling factor for safety
        kelly_pct *= self.kelly_scaling_factor
        
        # Clamp to reasonable bounds
        kelly_pct = max(self.min_position_size_pct, min(kelly_pct, self.max_position_size_pct))
        
        self.logger.info(f"Kelly criterion calculated: {kelly_pct:.3f} (win_rate: {win_probability:.3f}, win/loss: {win_loss_ratio:.2f})")
        return kelly_pct
    
    def calculate_position_size(self, account_balance: float, entry_price: float, 
                              stop_loss_price: float, use_kelly: bool = True) -> float:
        """
        Calculate position size using Kelly criterion or percentage risk method.
        
        Args:
            account_balance: Total account balance
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price
            use_kelly: Whether to use Kelly criterion (default) or percentage risk
        
        Returns:
            float: Position size in base currency
        """
        if use_kelly and len(self.trading_history) >= 10:
            # Kelly criterion method
            kelly_pct = self.calculate_kelly_criterion()
            position_value = account_balance * kelly_pct
            
            # Calculate position size based on risk
            risk_per_share = abs(entry_price - stop_loss_price)
            if risk_per_share > 0:
                max_shares_by_risk = (account_balance * self.max_risk_per_trade_pct) / risk_per_share
                shares_by_kelly = position_value / entry_price
                position_size = min(max_shares_by_risk, shares_by_kelly)
            else:
                position_size = position_value / entry_price
        else:
            # Percentage risk method
            risk_amount = account_balance * self.max_risk_per_trade_pct
            risk_per_share = abs(entry_price - stop_loss_price)
            
            if risk_per_share > 0:
                position_size = risk_amount / risk_per_share
            else:
                # Fallback to 2% of account
                position_size = (account_balance * 0.02) / entry_price
        
        # Final position value check
        position_value = position_size * entry_price
        max_position_value = account_balance * self.max_position_size_pct
        
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            self.logger.info(f"Position size capped at {self.max_position_size_pct*100}% of account")
        
        self.logger.info(f"Calculated position size: {position_size:.4f} (value: ${position_value:.2f})")
        return position_size
    
    def add_trading_record(self, profit_loss: float, entry_price: float, exit_price: float, 
                          position_size: float, trade_timestamp: Optional[datetime] = None):
        """
        Add a completed trade to the trading history for Kelly criterion calculation.
        
        Args:
            profit_loss: Profit or loss amount
            entry_price: Entry price of the trade
            exit_price: Exit price of the trade
            position_size: Size of the position
            trade_timestamp: Timestamp of the trade completion
        """
        if trade_timestamp is None:
            trade_timestamp = datetime.now()
        
        record = TradingRecord(
            profit_loss=profit_loss,
            win=profit_loss > 0,
            timestamp=trade_timestamp,
            trade_size=position_size
        )
        
        self.trading_history.append(record)
        
        # Keep only recent history to avoid memory bloat
        max_history = self.kelly_lookback_trades * 2
        if len(self.trading_history) > max_history:
            self.trading_history = self.trading_history[-max_history:]
        
        self.logger.info(f"Added trading record: P&L ${profit_loss:.2f}, Win: {record.win}")
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """
        Get current risk metrics and statistics.
        
        Returns:
            Dict containing various risk metrics
        """
        if not self.trading_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'kelly_percentage': 0.02
            }
        
        recent_trades = self.trading_history[-self.kelly_lookback_trades:]
        wins = [trade for trade in recent_trades if trade.win]
        losses = [trade for trade in recent_trades if not trade.win]
        
        win_rate = len(wins) / len(recent_trades) if recent_trades else 0
        avg_win = np.mean([trade.profit_loss for trade in wins]) if wins else 0
        avg_loss = abs(np.mean([trade.profit_loss for trade in losses])) if losses else 0
        
        total_wins = sum(trade.profit_loss for trade in wins)
        total_losses = abs(sum(trade.profit_loss for trade in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'total_trades': len(recent_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'kelly_percentage': self.calculate_kelly_criterion()
        }

    def find_nearest_bearish_ob(self, entry_price, order_blocks):
        # Finds the closest bearish order block below the entry price
        # For a bearish order block, we want the high to be above entry price for stop loss placement
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['price_level'][0] > entry_price]
        if not bearish_obs:
            return None
        return min(bearish_obs, key=lambda ob: ob['price_level'][0] - entry_price)
