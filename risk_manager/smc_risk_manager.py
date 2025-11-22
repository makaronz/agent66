import logging
from typing import Dict, Any, Optional


class RiskViolationError(Exception):
    """Raised when a risk limit is violated."""
    pass


class SMCRiskManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Risk limits from config
        self.max_position_size = self.config.get('max_position_size', 1000)  # USD
        self.max_daily_loss = self.config.get('max_daily_loss', 500)  # USD
        self.max_drawdown = self.config.get('max_drawdown', 0.10)  # 10%
        self.stop_loss_percent = self.config.get('stop_loss_percent', 2.0)  # %
        self.take_profit_ratio = self.config.get('take_profit_ratio', 3.0)  # R:R
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        self.logger.info(
            f"Risk Manager initialized - "
            f"Max Position: ${self.max_position_size}, "
            f"Max Daily Loss: ${self.max_daily_loss}, "
            f"Max Drawdown: {self.max_drawdown:.1%}"
        )

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

    def find_nearest_bearish_ob(self, entry_price, order_blocks):
        # Finds the closest bearish order block above the entry price
        # For a bearish order block, we want the high to be above entry price for stop loss placement
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish' and ob['price_level'][0] > entry_price]
        if not bearish_obs:
            return None
        return min(bearish_obs, key=lambda ob: ob['price_level'][0] - entry_price)
    
    def validate_position_size(
        self,
        symbol: str,
        size: float,
        price: float,
        balance: float,
        max_risk_percent: float = 0.02
    ) -> Dict[str, Any]:
        """
        Validate that position size doesn't exceed risk limits.
        
        Args:
            symbol: Trading symbol
            size: Position size
            price: Entry price
            balance: Account balance
            max_risk_percent: Maximum risk per trade as % of balance
        
        Returns:
            Dict with validation result and adjusted size if needed
        
        Raises:
            RiskViolationError: If position violates hard limits
        """
        position_value = size * price
        
        # Check absolute position size limit
        if position_value > self.max_position_size:
            self.logger.warning(
                f"Position value ${position_value:.2f} exceeds max ${self.max_position_size:.2f}"
            )
            # Adjust size to max allowed
            adjusted_size = self.max_position_size / price
            return {
                'valid': False,
                'adjusted': True,
                'original_size': size,
                'adjusted_size': adjusted_size,
                'reason': f'Reduced to max position size ${self.max_position_size}'
            }
        
        # Check percentage of balance
        max_position_value = balance * max_risk_percent
        if position_value > max_position_value:
            self.logger.warning(
                f"Position value ${position_value:.2f} exceeds {max_risk_percent:.1%} "
                f"of balance (${max_position_value:.2f})"
            )
            # Adjust size
            adjusted_size = max_position_value / price
            return {
                'valid': False,
                'adjusted': True,
                'original_size': size,
                'adjusted_size': adjusted_size,
                'reason': f'Reduced to {max_risk_percent:.1%} of balance'
            }
        
        # Position size is valid
        return {
            'valid': True,
            'adjusted': False,
            'size': size,
            'position_value': position_value
        }
    
    def check_daily_loss_limit(self, current_pnl: float) -> bool:
        """
        Check if daily loss limit has been reached.
        
        Args:
            current_pnl: Current day's total P&L
        
        Returns:
            True if trading should continue, False if limit reached
        """
        if current_pnl < -self.max_daily_loss:
            self.logger.critical(
                f"🚨 DAILY LOSS LIMIT REACHED: ${current_pnl:.2f} < -${self.max_daily_loss:.2f}"
            )
            return False
        
        if current_pnl < -self.max_daily_loss * 0.8:
            self.logger.warning(
                f"⚠️ Approaching daily loss limit: ${current_pnl:.2f} "
                f"(limit: -${self.max_daily_loss:.2f})"
            )
        
        return True
    
    def update_daily_pnl(self, trade_pnl: float):
        """Update daily P&L tracking."""
        self.daily_pnl += trade_pnl
        self.daily_trades += 1
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new trading day)."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.logger.info("Daily metrics reset")
