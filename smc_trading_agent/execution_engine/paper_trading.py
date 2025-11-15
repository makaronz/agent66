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
                self.logger.warning(f"Max positions ({self.max_positions}) reached, cannot open new position")
                return None
            
            # Calculate position value
            position_value = size * price
            
            # Check if we have sufficient balance (margin check)
            required_margin = position_value * 0.1  # Assume 10x leverage
            if required_margin > self.balance:
                self.logger.warning(
                    f"Insufficient balance for position: "
                    f"Required ${required_margin:.2f}, Available ${self.balance:.2f}"
                )
                return None
            
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

