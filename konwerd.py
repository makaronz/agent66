Powiedziałeś(-aś):
przesylam Ci pliki z kodem mojej aplikacji, przenalizuj je, napisz prompt na baze powyzszego ktory bedie zawieral dokladni to co powyzszy prompt oraz instrukcje jak zmienic apliakcje i jej logike, co dodac, aby byla naprawdew funkcjonalna
Powiedziałeś(-aś):
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
Powiedziałeś(-aś):
"""
Paper Trading Engine for SMC Trading Agent

Simulates order execution with live market prices without risking real capital.
Tracks positions, P&L, and maintains trading history.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"  # Alias for BUY
    SHORT = "SHORT"  # Alias for SELL


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class Trade:
    """Represents a single trade (order execution)."""
    id: str
    symbol: str
    side: str  # BUY, SELL, LONG, SHORT
    size: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    exit_timestamp: Optional[float] = None
    status: str = "OPEN"
    pnl: float = 0.0
    pnl_percent: float = 0.0
    reason: str = ""
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'timestamp': self.timestamp,
            'exit_timestamp': self.exit_timestamp,
            'status': self.status,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'reason': self.reason,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }


@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    side: str  # LONG or SHORT
    size: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    entry_timestamp: float = field(default_factory=time.time)
    trade_id: str = ""
    
    def update_pnl(self, current_price: float):
        """Update unrealized P&L based on current price."""
        self.current_price = current_price
        
        if self.side in ['LONG', 'BUY']:
            price_diff = current_price - self.entry_price
        else:  # SHORT or SELL
            price_diff = self.entry_price - current_price
        
        self.unrealized_pnl = price_diff * self.size
        if self.entry_price > 0:
            self.unrealized_pnl_percent = (price_diff / self.entry_price) * 100
    
    def check_stop_loss(self) -> bool:
        """Check if stop loss is triggered."""
        if self.stop_loss is None:
            return False
        
        if self.side in ['LONG', 'BUY']:
            return self.current_price <= self.stop_loss
        else:  # SHORT or SELL
            return self.current_price >= self.stop_loss
    
    def check_take_profit(self) -> bool:
        """Check if take profit is triggered."""
        if self.take_profit is None:
            return False
        
        if self.side in ['LONG', 'BUY']:
            return self.current_price >= self.take_profit
        else:  # SHORT or SELL
            return self.current_price <= self.take_profit
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_percent': self.unrealized_pnl_percent,
            'entry_timestamp': self.entry_timestamp,
            'trade_id': self.trade_id,
            'entry_datetime': datetime.fromtimestamp(self.entry_timestamp).isoformat()
        }


class PaperTradingEngine:
    """
    Paper trading engine for simulating trades with live market prices.
    
    Features:
    - Simulates order execution at live prices
    - Tracks open positions and P&L
    - Enforces stop loss and take profit
    - Maintains trade history
    - Provides account summary
    """
    
    def __init__(self, initial_balance: float = 10000.0, max_positions: int = 5):
        """
        Initialize paper trading engine.
        
        Args:
            initial_balance: Starting balance in USD
            max_positions: Maximum number of concurrent positions
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.max_positions = max_positions
        
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.trades_history: List[Trade] = []
        
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Paper Trading Engine initialized with ${initial_balance:.2f} balance")
    
    def execute_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reason: str = "Manual trade"
    ) -> Optional[Trade]:
        """
        Execute a paper trade order.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            side: Order side ('BUY', 'SELL', 'LONG', 'SHORT')
            size: Position size
            price: Entry price
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            reason: Reason for trade (for logging)
        
        Returns:
            Trade object if successful, None if rejected
        """
        try:
            # Normalize side
            side = side.upper()
            if side == 'BUY':
                side = 'LONG'
            elif side == 'SELL':
                side = 'SHORT'
            
            # Check if position already exists
            if symbol in self.positions:
                self.logger.warning(f"Position already exists for {symbol}, closing first")
                self.close_position(symbol, price, "Replacing existing position")
            
            # Check max positions
            if len(self.positions) >= self.max_positions:
                error_msg = f"Max positions ({self.max_positions}) reached, cannot open new position"
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Calculate position value
            position_value = size * price
            
            # Check if we have sufficient balance (margin check)
            required_margin = position_value * 0.1  # Assume 10x leverage
            if required_margin > self.balance:
                error_msg = (
                    f"Insufficient balance for position: "
                    f"Required ${required_margin:.2f}, Available ${self.balance:.2f}. "
                    f"Position value: ${position_value:.2f} (size: {size}, price: ${price:.2f})"
                )
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # Create trade
            trade_id = f"paper_{int(time.time() * 1000)}"
            trade = Trade(
                id=trade_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=reason,
                status="OPEN"
            )
            
            # Create position
            position = Position(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=price,
                current_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trade_id=trade_id
            )
            
            # Add to positions
            self.positions[symbol] = position
            self.trades_history.append(trade)
            self.total_trades += 1
            
            # Reserve margin
            self.balance -= required_margin
            
            self.logger.info(
                f"📈 PAPER ORDER EXECUTED: {side} {size} {symbol} @ ${price:.2f}"
                f" | SL: ${stop_loss:.2f if stop_loss else 'None'}"
                f" | TP: ${take_profit:.2f if take_profit else 'None'}"
                f" | Reason: {reason}"
            )
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Failed to execute paper order: {str(e)}", exc_info=True)
            return None
    
    def update_positions(self, live_prices: Dict[str, float]):
        """
        Update all positions with live prices and check SL/TP.
        
        Args:
            live_prices: Dictionary of symbol -> current_price
        """
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            if symbol not in live_prices:
                continue
            
            current_price = live_prices[symbol]
            position.update_pnl(current_price)
            
            # Check stop loss
            if position.check_stop_loss():
                positions_to_close.append((symbol, current_price, "Stop loss triggered"))
            
            # Check take profit
            elif position.check_take_profit():
                positions_to_close.append((symbol, current_price, "Take profit triggered"))
        
        # Close triggered positions
        for symbol, price, reason in positions_to_close:
            self.close_position(symbol, price, reason)
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "Manual close"
    ) -> Optional[Trade]:
        """
        Close an open position.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            reason: Reason for closing
        
        Returns:
            Updated Trade object if successful, None otherwise
        """
        if symbol not in self.positions:
            self.logger.warning(f"No open position for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate realized P&L
        if position.side in ['LONG', 'BUY']:
            pnl = (exit_price - position.entry_price) * position.size
        else:  # SHORT or SELL
            pnl = (position.entry_price - exit_price) * position.size
        
        pnl_percent = (pnl / (position.entry_price * position.size)) * 100
        
        # Update balance
        position_value = position.size * position.entry_price
        required_margin = position_value * 0.1
        self.balance += required_margin + pnl  # Return margin + profit/loss
        
        # Update totals
        self.total_pnl += pnl
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Find and update trade in history
        for trade in self.trades_history:
            if trade.id == position.trade_id:
                trade.exit_price = exit_price
                trade.exit_timestamp = time.time()
                trade.status = "CLOSED"
                trade.pnl = pnl
                trade.pnl_percent = pnl_percent
                
                self.logger.info(
                    f"📉 POSITION CLOSED: {position.side} {position.size} {symbol}"
                    f" | Entry: ${position.entry_price:.2f}"
                    f" | Exit: ${exit_price:.2f}"
                    f" | P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)"
                    f" | Reason: {reason}"
                )
                
                # Remove from open positions
                del self.positions[symbol]
                
                return trade
        
        return None
    
    def close_all_positions(self, live_prices: Dict[str, float], reason: str = "Close all"):
        """Close all open positions at current market prices."""
        symbols_to_close = list(self.positions.keys())
        
        for symbol in symbols_to_close:
            if symbol in live_prices:
                self.close_position(symbol, live_prices[symbol], reason)
            else:
                self.logger.warning(f"No live price for {symbol}, cannot close position")
    
    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary with balance, positions, and performance metrics.
        
        Returns:
            Dictionary with account information
        """
        # Calculate total unrealized P&L
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Calculate equity
        equity = self.balance + total_unrealized_pnl
        
        # Calculate used margin
        used_margin = sum(
            (pos.size * pos.entry_price * 0.1) for pos in self.positions.values()
        )
        
        # Win rate
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'balance': self.balance,
            'equity': equity,
            'initial_balance': self.initial_balance,
            'total_pnl': self.total_pnl,
            'total_pnl_percent': (self.total_pnl / self.initial_balance * 100),
            'unrealized_pnl': total_unrealized_pnl,
            'used_margin': used_margin,
            'free_margin': self.balance - used_margin,
            'margin_level': (equity / used_margin * 100) if used_margin > 0 else float('inf'),
            'open_positions': len(self.positions),
            'max_positions': self.max_positions,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate
        }
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of all open positions."""
        return [pos.dict() for pos in self.positions.values()]
    
    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history."""
        return [trade.dict() for trade in self.trades_history[-limit:]]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate detailed performance metrics."""
        if self.total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        wins = [t.pnl for t in self.trades_history if t.status == 'CLOSED' and t.pnl > 0]
        losses = [t.pnl for t in self.trades_history if t.status == 'CLOSED' and t.pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Simple Sharpe ratio approximation
        returns = [t.pnl_percent for t in self.trades_history if t.status == 'CLOSED']
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max drawdown (simplified)
        equity_curve = [self.initial_balance]
        running_balance = self.initial_balance
        for trade in self.trades_history:
            if trade.status == 'CLOSED':
                running_balance += trade.pnl
                equity_curve.append(running_balance)
        
        max_drawdown = 0
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_pnl': self.total_pnl
        }

Powiedziałeś(-aś):
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import numba
from numba import jit, float64, int64, boolean
from numba.typed import List
from typing import Tuple

# Numba-optimized helper functions for SMC detection
@jit(nopython=True)
def _find_order_blocks_numba(
    high_values: np.ndarray,
    low_values: np.ndarray, 
    open_values: np.ndarray,
    close_values: np.ndarray,
    volume_values: np.ndarray,
    potential_ob_indices: np.ndarray,
    bos_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized order block detection core algorithm"""
    n_blocks = 0
    max_blocks = len(potential_ob_indices)
    
    # Pre-allocate arrays
    ob_indices = np.empty(max_blocks, dtype=np.int64)
    ob_types = np.empty(max_blocks, dtype=np.int64)  # 1=bullish, 0=bearish
    ob_high_prices = np.empty(max_blocks, dtype=np.float64)
    ob_low_prices = np.empty(max_blocks, dtype=np.float64)
    ob_volumes = np.empty(max_blocks, dtype=np.float64)
    
    body_sizes = np.abs(close_values - open_values)
    n_candles = len(high_values)
    
    for i in range(len(potential_ob_indices)):
        idx = potential_ob_indices[i]
        
        if idx == 0 or idx >= n_candles - 1:
            continue
            
        potential_ob_open = open_values[idx]
        potential_ob_close = close_values[idx]
        potential_ob_high = high_values[idx]
        potential_ob_low = low_values[idx]
        potential_ob_volume = volume_values[idx]
        
        # Determine Order Block type
        is_bullish_ob = potential_ob_close < potential_ob_open  # Last down candle
        is_bearish_ob = potential_ob_close > potential_ob_open  # Last up candle
        
        if is_bullish_ob:
            # Look for a strong up-move that breaks the high of the OB candle
            structure_high = potential_ob_high
            for j in range(idx + 1, n_candles):
                if high_values[j] > structure_high and body_sizes[j] > bos_threshold:
                    ob_indices[n_blocks] = idx
                    ob_types[n_blocks] = 1  # bullish
                    ob_high_prices[n_blocks] = potential_ob_high
                    ob_low_prices[n_blocks] = potential_ob_low
                    ob_volumes[n_blocks] = potential_ob_volume
                    n_blocks += 1
                    break
        
        elif is_bearish_ob:
            # Look for a strong down-move that breaks the low of the OB candle
            structure_low = potential_ob_low
            for j in range(idx + 1, n_candles):
                if low_values[j] < structure_low and body_sizes[j] > bos_threshold:
                    ob_indices[n_blocks] = idx
                    ob_types[n_blocks] = 0  # bearish
                    ob_high_prices[n_blocks] = potential_ob_high
                    ob_low_prices[n_blocks] = potential_ob_low
                    ob_volumes[n_blocks] = potential_ob_volume
                    n_blocks += 1
                    break
    
    return (
        ob_indices[:n_blocks],
        ob_types[:n_blocks],
        ob_high_prices[:n_blocks],
        ob_low_prices[:n_blocks],
        ob_volumes[:n_blocks]
    )

@jit(nopython=True)
def _detect_choch_patterns_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    volume_values: np.ndarray,
    momentum_values: np.ndarray,
    swing_highs: np.ndarray,
    swing_lows: np.ndarray,
    volume_threshold: float,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized CHOCH pattern detection"""
    max_patterns = len(swing_highs) + len(swing_lows)
    
    # Pre-allocate arrays
    pattern_indices = np.empty(max_patterns, dtype=np.int64)
    pattern_types = np.empty(max_patterns, dtype=np.int64)  # 1=bullish_coch, 0=bearish_coch
    pattern_confidences = np.empty(max_patterns, dtype=np.float64)
    pattern_strengths = np.empty(max_patterns, dtype=np.float64)
    n_patterns = 0
    
    # Bearish COCH: Higher highs to lower highs
    if len(swing_highs) >= 3:
        for i in range(len(swing_highs) - 2):
            high1_idx, high2_idx, high3_idx = swing_highs[i], swing_highs[i+1], swing_highs[i+2]
            high1, high2, high3 = high_values[high1_idx], high_values[high2_idx], high_values[high3_idx]
            
            # Check for bearish COCH: high2 > high1 and high3 < high2
            if high2 > high1 and high3 < high2:
                volume_confirmed = volume_values[high3_idx] > volume_threshold
                momentum_strength = abs(momentum_values[high3_idx])
                
                confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    pattern_indices[n_patterns] = high3_idx
                    pattern_types[n_patterns] = 0  # bearish_coch
                    pattern_confidences[n_patterns] = confidence
                    pattern_strengths[n_patterns] = momentum_strength
                    n_patterns += 1
    
    # Bullish COCH: Lower lows to higher lows
    if len(swing_lows) >= 3:
        for i in range(len(swing_lows) - 2):
            low1_idx, low2_idx, low3_idx = swing_lows[i], swing_lows[i+1], swing_lows[i+2]
            low1, low2, low3 = low_values[low1_idx], low_values[low2_idx], low_values[low3_idx]
            
            # Check for bullish COCH: low2 < low1 and low3 > low2
            if low2 < low1 and low3 > low2:
                volume_confirmed = volume_values[low3_idx] > volume_threshold
                momentum_strength = abs(momentum_values[low3_idx])
                
                confidence = min(0.9, 0.5 + (momentum_strength / 10) + (0.2 if volume_confirmed else 0))
                
                if confidence >= confidence_threshold:
                    pattern_indices[n_patterns] = low3_idx
                    pattern_types[n_patterns] = 1  # bullish_coch
                    pattern_confidences[n_patterns] = confidence
                    pattern_strengths[n_patterns] = momentum_strength
                    n_patterns += 1
    
    return (
        pattern_indices[:n_patterns],
        pattern_types[:n_patterns],
        pattern_confidences[:n_patterns],
        pattern_strengths[:n_patterns]
    )

@jit(nopython=True)
def _detect_bos_patterns_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    volume_values: np.ndarray,
    momentum_values: np.ndarray,
    swing_highs: np.ndarray,
    swing_lows: np.ndarray,
    volume_threshold: float,
    momentum_threshold: float,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized BOS pattern detection"""
    max_patterns = len(swing_highs) + len(swing_lows)
    
    # Pre-allocate arrays
    pattern_indices = np.empty(max_patterns, dtype=np.int64)
    pattern_types = np.empty(max_patterns, dtype=np.int64)  # 1=bullish_bos, 0=bearish_bos
    pattern_confidences = np.empty(max_patterns, dtype=np.float64)
    pattern_strengths = np.empty(max_patterns, dtype=np.float64)
    n_patterns = 0
    
    # Bullish BOS: Break above previous swing high
    for i in range(len(swing_highs) - 1):
        high_idx = swing_highs[i]
        next_high_idx = swing_highs[i + 1]
        structure_level = high_values[high_idx]
        
        # Check if price broke above the structure level
        if high_values[next_high_idx] > structure_level:
            break_strength = (high_values[next_high_idx] - structure_level) / structure_level * 100
            volume_confirmed = volume_values[next_high_idx] > volume_threshold
            momentum_confirmed = momentum_values[next_high_idx] > momentum_threshold
            
            confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
            
            if confidence >= confidence_threshold:
                pattern_indices[n_patterns] = next_high_idx
                pattern_types[n_patterns] = 1  # bullish_bos
                pattern_confidences[n_patterns] = confidence
                pattern_strengths[n_patterns] = break_strength
                n_patterns += 1
    
    # Bearish BOS: Break below previous swing low
    for i in range(len(swing_lows) - 1):
        low_idx = swing_lows[i]
        next_low_idx = swing_lows[i + 1]
        structure_level = low_values[low_idx]
        
        # Check if price broke below the structure level
        if low_values[next_low_idx] < structure_level:
            break_strength = (structure_level - low_values[next_low_idx]) / structure_level * 100
            volume_confirmed = volume_values[next_low_idx] > volume_threshold
            momentum_confirmed = abs(momentum_values[next_low_idx]) > momentum_threshold
            
            confidence = min(0.95, 0.6 + (break_strength / 20) + (0.2 if volume_confirmed else 0) + (0.15 if momentum_confirmed else 0))
            
            if confidence >= confidence_threshold:
                pattern_indices[n_patterns] = next_low_idx
                pattern_types[n_patterns] = 0  # bearish_bos
                pattern_confidences[n_patterns] = confidence
                pattern_strengths[n_patterns] = break_strength
                n_patterns += 1
    
    return (
        pattern_indices[:n_patterns],
        pattern_types[:n_patterns],
        pattern_confidences[:n_patterns],
        pattern_strengths[:n_patterns]
    )

@jit(nopython=True)
def _detect_liquidity_sweeps_numba(
    high_values: np.ndarray,
    low_values: np.ndarray,
    close_values: np.ndarray,
    volume_values: np.ndarray,
    volume_ratios: np.ndarray,
    resistance_levels: np.ndarray,
    support_levels: np.ndarray,
    min_sweep_distance: float,
    volume_spike_threshold: float,
    sweep_reversal_candles: int,
    confidence_threshold: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-optimized liquidity sweep detection"""
    max_sweeps = (len(resistance_levels) + len(support_levels)) * 10
    
    # Pre-allocate arrays
    sweep_indices = np.empty(max_sweeps, dtype=np.int64)
    sweep_types = np.empty(max_sweeps, dtype=np.int64)  # 1=bullish_sweep, 0=bearish_sweep
    sweep_confidences = np.empty(max_sweeps, dtype=np.float64)
    sweep_strengths = np.empty(max_sweeps, dtype=np.float64)
    sweep_levels = np.empty(max_sweeps, dtype=np.float64)
    n_sweeps = 0
    
    n_candles = len(high_values)
    
    # Detect Bullish Liquidity Sweeps (Above Resistance)
    for resistance in resistance_levels:
        for idx in range(n_candles - sweep_reversal_candles):
            # Check if candle swept above resistance
            if high_values[idx] > resistance:
                sweep_distance = (high_values[idx] - resistance) / resistance * 100
                
                # Check if sweep distance is significant
                if sweep_distance >= min_sweep_distance:
                    volume_spike = volume_values[idx] > volume_spike_threshold
                    volume_ratio = volume_ratios[idx]
                    
                    # Check for reversal within specified candles
                    reversal_confirmed = False
                    reversal_strength = 0.0
                    
                    for j in range(1, min(sweep_reversal_candles + 1, n_candles - idx)):
                        if close_values[idx + j] < resistance:
                            reversal_confirmed = True
                            reversal_strength = (resistance - close_values[idx + j]) / resistance * 100
                            break
                    
                    # Calculate confidence score
                    confidence = 0.5
                    if volume_spike:
                        confidence += 0.2
                    if reversal_confirmed:
                        confidence += 0.2
                    if volume_ratio > 2.0:
                        confidence += 0.1
                    if sweep_distance > 0.5:
                        confidence += 0.1
                    if reversal_strength > 0.3:
                        confidence += 0.1
                    
                    confidence = min(0.95, confidence)
                    
                    if confidence >= confidence_threshold:
                        sweep_indices[n_sweeps] = idx
                        sweep_types[n_sweeps] = 1  # bullish_sweep
                        sweep_confidences[n_sweeps] = confidence
                        sweep_strengths[n_sweeps] = sweep_distance
                        sweep_levels[n_sweeps] = resistance
                        n_sweeps += 1
    
    # Detect Bearish Liquidity Sweeps (Below Support)
    for support in support_levels:
        for idx in range(n_candles - sweep_reversal_candles):
            # Check if candle swept below support
            if low_values[idx] < support:
                sweep_distance = (support - low_values[idx]) / support * 100
                
                # Check if sweep distance is significant
                if sweep_distance >= min_sweep_distance:
                    volume_spike = volume_values[idx] > volume_spike_threshold
                    volume_ratio = volume_ratios[idx]
                    
                    # Check for reversal within specified candles
                    reversal_confirmed = False
                    reversal_strength = 0.0
                    
                    for j in range(1, min(sweep_reversal_candles + 1, n_candles - idx)):
                        if close_values[idx + j] > support:
                            reversal_confirmed = True
                            reversal_strength = (close_values[idx + j] - support) / support * 100
                            break
                    
                    # Calculate confidence score
                    confidence = 0.5
                    if volume_spike:
                        confidence += 0.2
                    if reversal_confirmed:
                        confidence += 0.2
                    if volume_ratio > 2.0:
                        confidence += 0.1
                    if sweep_distance > 0.5:
                        confidence += 0.1
                    if reversal_strength > 0.3:
                        confidence += 0.1
                    
                    confidence = min(0.95, confidence)
                    
                    if confidence >= confidence_threshold:
                        sweep_indices[n_sweeps] = idx
                        sweep_types[n_sweeps] = 0  # bearish_sweep
                        sweep_confidences[n_sweeps] = confidence
                        sweep_strengths[n_sweeps] = sweep_distance
                        sweep_levels[n_sweeps] = support
                        n_sweeps += 1
    
    return (
        sweep_indices[:n_sweeps],
        sweep_types[:n_sweeps],
        sweep_confidences[:n_sweeps],
        sweep_strengths[:n_sweeps],
        sweep_levels[:n_sweeps]
    )

class SMCIndicators:
    def detect_order_blocks(self, ohlc_data: pd.DataFrame, volume_threshold_percentile=95, bos_confirmation_factor=1.5):
        """
        Detects Order Blocks using peak volume analysis and Break of Structure (BoS) confirmation.
        Optimized with Numba JIT compilation for improved performance.

        An order block is identified as the last bearish candle before a strong bullish move
        (or vice-versa) that occurs on high volume and is followed by a break of structure.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            volume_threshold_percentile (int): The percentile to use for identifying significant volume peaks.
            bos_confirmation_factor (float): Multiplier for the average candle body size to confirm a BoS.

        Returns:
            list: A list of dictionaries, where each dictionary represents a confirmed order block.
                  Example: {
                      'timestamp': '2023-10-27T10:00:00Z',
                      'type': 'bullish',
                      'price_level': (60000.50, 59500.25),
                      'strength_volume': 150.75,
                      'bos_confirmed_at': '2023-10-27T10:05:00Z'
                  }
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Identify High-Volume Candles (Potential Order Blocks) ---
        volume_threshold = np.percentile(volume_values, volume_threshold_percentile)
        potential_ob_indices, _ = find_peaks(volume_values, height=volume_threshold)
        
        if len(potential_ob_indices) == 0:
            return []

        # --- 2. Calculate BOS threshold ---
        body_sizes = np.abs(close_values - open_values)
        avg_body_size = np.mean(body_sizes)
        bos_threshold = avg_body_size * bos_confirmation_factor

        # --- 3. Use Numba-optimized function for core detection ---
        ob_indices, ob_types, ob_high_prices, ob_low_prices, ob_volumes = _find_order_blocks_numba(
            high_values, low_values, open_values, close_values, volume_values,
            potential_ob_indices, bos_threshold
        )

        # --- 4. Convert results back to expected format ---
        confirmed_order_blocks = []
        for i in range(len(ob_indices)):
            idx = ob_indices[i]
            ob_type = 'bullish' if ob_types[i] == 1 else 'bearish'
            
            confirmed_order_blocks.append({
                'timestamp': timestamps[idx],
                'type': ob_type,
                'price_level': (ob_high_prices[i], ob_low_prices[i]),
                'strength_volume': ob_volumes[i],
                'bos_confirmed_at': None  # Could be enhanced to track this
            })

        return confirmed_order_blocks

    def identify_choch_bos(self, ohlc_data: pd.DataFrame, swing_highs: list = None, swing_lows: list = None, 
                          min_swing_distance: int = 5, volume_confirmation_threshold: float = 1.5,
                          momentum_threshold: float = 1.2, confidence_threshold: float = 0.7):
        """
        Identifies Change of Character (COCH) and Break of Structure (BOS) patterns using SMC methodology.
        Optimized with Numba JIT compilation for improved performance.

        COCH occurs when market structure shifts from bullish to bearish (higher highs to lower highs)
        or bearish to bullish (lower lows to higher lows). BOS occurs when price breaks through
        established support/resistance levels with sufficient momentum and volume confirmation.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            swing_highs (list): Optional list of swing high indices. If None, will be calculated automatically.
            swing_lows (list): Optional list of swing low indices. If None, will be calculated automatically.
            min_swing_distance (int): Minimum distance between swing points for peak detection.
            volume_confirmation_threshold (float): Multiplier for average volume to confirm patterns.
            momentum_threshold (float): Minimum momentum required for BOS confirmation.
            confidence_threshold (float): Minimum confidence score for pattern validation.

        Returns:
            dict: A dictionary containing COCH and BOS patterns with confidence scores.
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Calculate Swing Points if not provided ---
        if swing_highs is None:
            swing_highs, _ = find_peaks(high_values, distance=min_swing_distance, prominence=np.std(high_values) * 0.1)
        if swing_lows is None:
            swing_lows, _ = find_peaks(-low_values, distance=min_swing_distance, prominence=np.std(low_values) * 0.1)

        # Convert swing points to NumPy arrays if they're lists
        if isinstance(swing_highs, list):
            swing_highs = np.array(swing_highs, dtype=np.int64)
        if isinstance(swing_lows, list):
            swing_lows = np.array(swing_lows, dtype=np.int64)

        # --- 2. Calculate Additional Metrics ---
        momentum_values = (close_values - open_values) / open_values * 100
        
        avg_volume = np.mean(volume_values)
        volume_threshold = avg_volume * volume_confirmation_threshold

        # --- 3. Use Numba-optimized functions for pattern detection ---
        coch_indices, coch_types, coch_confidences, coch_strengths = _detect_choch_patterns_numba(
            high_values, low_values, volume_values, momentum_values,
            swing_highs, swing_lows, volume_threshold, confidence_threshold
        )

        bos_indices, bos_types, bos_confidences, bos_strengths = _detect_bos_patterns_numba(
            high_values, low_values, volume_values, momentum_values,
            swing_highs, swing_lows, volume_threshold, momentum_threshold, confidence_threshold
        )

        # --- 4. Convert results back to expected format ---
        coch_patterns = []
        for i in range(len(coch_indices)):
            idx = coch_indices[i]
            pattern_type = 'bullish_coch' if coch_types[i] == 1 else 'bearish_coch'
            
            coch_patterns.append({
                'timestamp': timestamps[idx],
                'type': pattern_type,
                'price_level': (high_values[idx], low_values[idx]),
                'confidence': round(coch_confidences[i], 3),
                'volume_confirmed': volume_values[idx] > volume_threshold,
                'momentum_strength': coch_strengths[i]
            })

        bos_patterns = []
        for i in range(len(bos_indices)):
            idx = bos_indices[i]
            pattern_type = 'bullish_bos' if bos_types[i] == 1 else 'bearish_bos'
            
            bos_patterns.append({
                'timestamp': timestamps[idx],
                'type': pattern_type,
                'price_level': high_values[idx] if pattern_type == 'bullish_bos' else low_values[idx],
                'confidence': round(bos_confidences[i], 3),
                'break_strength': round(bos_strengths[i], 2),
                'volume_confirmed': volume_values[idx] > volume_threshold,
                'momentum_confirmed': momentum_values[idx] > momentum_threshold if pattern_type == 'bullish_bos' else abs(momentum_values[idx]) > momentum_threshold
            })

        return {
            'coch_patterns': coch_patterns,
            'bos_patterns': bos_patterns,
            'swing_highs': swing_highs.tolist() if hasattr(swing_highs, 'tolist') else swing_highs,
            'swing_lows': swing_lows.tolist() if hasattr(swing_lows, 'tolist') else swing_lows,
            'total_patterns': len(coch_patterns) + len(bos_patterns)
        }
        
    def liquidity_sweep_detection(self, ohlc_data: pd.DataFrame, volume_threshold_percentile: int = 95,
                                 sweep_reversal_candles: int = 3, min_sweep_distance: float = 0.1,
                                 volume_spike_threshold: float = 2.0, confidence_threshold: float = 0.7):
        """
        Detects liquidity sweeps using SMC methodology for identifying stop-loss hunting and institutional manipulation.
        Optimized with Numba JIT compilation for improved performance.

        Liquidity sweeps occur when price briefly moves beyond key support/resistance levels to trigger
        stop losses before reversing. This method identifies institutional order flow manipulation patterns.

        Args:
            ohlc_data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            volume_threshold_percentile (int): Percentile for identifying significant volume levels.
            sweep_reversal_candles (int): Maximum number of candles for reversal confirmation.
            min_sweep_distance (float): Minimum distance beyond key level for sweep confirmation (percentage).
            volume_spike_threshold (float): Multiplier for average volume to confirm volume spike.
            confidence_threshold (float): Minimum confidence score for sweep validation.

        Returns:
            dict: A dictionary containing detected liquidity sweeps with detailed metrics.
        """
        # --- Input Validation ---
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlc_data.columns for col in required_columns):
            raise ValueError(f"Input DataFrame must contain columns: {required_columns}")

        df = ohlc_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Convert to NumPy arrays for Numba optimization
        high_values = df['high'].values
        low_values = df['low'].values
        open_values = df['open'].values
        close_values = df['close'].values
        volume_values = df['volume'].values
        timestamps = df['timestamp'].values

        # --- 1. Calculate Volume Ratios ---
        # Calculate rolling mean volume for volume ratio calculation
        volume_rolling_mean = np.full_like(volume_values, np.nan)
        window = min(20, len(volume_values))
        for i in range(window - 1, len(volume_values)):
            volume_rolling_mean[i] = np.mean(volume_values[max(0, i - window + 1):i + 1])

        # Fill initial NaN values with overall mean
        overall_mean = np.mean(volume_values)
        volume_rolling_mean[:window - 1] = overall_mean
        volume_ratios = volume_values / volume_rolling_mean

        # Calculate volume thresholds
        avg_volume = np.mean(volume_values)
        volume_spike_threshold_actual = avg_volume * volume_spike_threshold

        # --- 2. Identify Key Support and Resistance Levels ---
        # Find swing highs and lows for potential liquidity pools
        swing_highs, _ = find_peaks(high_values, distance=5, prominence=np.std(high_values) * 0.1)
        swing_lows, _ = find_peaks(-low_values, distance=5, prominence=np.std(low_values) * 0.1)

        # Create liquidity pool levels as NumPy arrays
        resistance_levels = high_values[swing_highs]
        support_levels = low_values[swing_lows]

        # --- 3. Use Numba-optimized function for sweep detection ---
        sweep_indices, sweep_types, sweep_confidences, sweep_strengths, sweep_levels = _detect_liquidity_sweeps_numba(
            high_values, low_values, close_values, volume_values, volume_ratios,
            resistance_levels, support_levels, min_sweep_distance,
            volume_spike_threshold_actual, sweep_reversal_candles, confidence_threshold
        )

        # --- 4. Convert results back to expected format ---
        detected_sweeps = []
        for i in range(len(sweep_indices)):
            idx = sweep_indices[i]
            sweep_type = 'bullish_sweep' if sweep_types[i] == 1 else 'bearish_sweep'
            liquidity_type = 'resistance' if sweep_type == 'bullish_sweep' else 'support'
            
            detected_sweeps.append({
                'timestamp': timestamps[idx],
                'type': sweep_type,
                'price_level': sweep_levels[i],
                'sweep_high': high_values[idx],
                'sweep_low': low_values[idx],
                'confidence': round(sweep_confidences[i], 3),
                'volume_spike': round(volume_ratios[idx], 2),
                'reversal_confirmed': True,  # Already filtered by Numba function
                'sweep_strength': round(sweep_strengths[i], 2),
                'liquidity_pool_type': liquidity_type,
                'candle_index': idx,
                'volume_confirmed': volume_values[idx] > volume_spike_threshold_actual
            })

        # --- 5. Filter duplicate sweeps at similar levels ---
        filtered_sweeps = []
        used_levels = set()
        
        for sweep in sorted(detected_sweeps, key=lambda x: x['confidence'], reverse=True):
            level_key = f"{sweep['price_level']:.2f}"
            
            # Check if we already have a sweep at a similar level (within 0.1%)
            level_used = False
            for used_level in used_levels:
                if abs(float(level_key) - float(used_level)) / float(used_level) < 0.001:
                    level_used = True
                    break
            
            if not level_used:
                filtered_sweeps.append(sweep)
                used_levels.add(level_key)

        return {
            'liquidity_sweeps': filtered_sweeps,
            'total_sweeps': len(filtered_sweeps),
            'resistance_levels': resistance_levels.tolist(),
            'support_levels': support_levels.tolist(),
            'bullish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bullish_sweep']),
            'bearish_sweeps': len([s for s in filtered_sweeps if s['type'] == 'bearish_sweep'])
        }



    