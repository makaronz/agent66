"""
Pytest-compatible test for trading system with coverage.
"""

import pytest


class TradingSystem:
    def __init__(self):
        self.balance = 10000
        self.positions = {}
        self.trades = []
    
    def calculate_sma(self, prices, period):
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def detect_crossover(self, short_sma, long_sma, prev_short, prev_long):
        """Detect moving average crossover."""
        if not all([short_sma, long_sma, prev_short, prev_long]):
            return None
        
        # Bullish crossover: short MA crosses above long MA
        if prev_short <= prev_long and short_sma > long_sma:
            return "BUY"
        
        # Bearish crossover: short MA crosses below long MA
        if prev_short >= prev_long and short_sma < long_sma:
            return "SELL"
        
        return "HOLD"
    
    def calculate_position_size(self, price, stop_loss, risk_percent=2):
        """Calculate position size based on risk management."""
        if price <= 0 or stop_loss <= 0:
            return 0
        
        risk_amount = self.balance * (risk_percent / 100)
        price_risk = abs(price - stop_loss)
        
        if price_risk == 0:
            return 0
        
        return risk_amount / price_risk
    
    def execute_trade(self, symbol, action, price, quantity):
        """Execute a trade."""
        if action == "BUY":
            cost = price * quantity
            if cost <= self.balance:
                self.balance -= cost
                self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                self.trades.append({
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'quantity': quantity,
                    'timestamp': 'now'
                })
                return True
        elif action == "SELL":
            if self.positions.get(symbol, 0) >= quantity:
                revenue = price * quantity
                self.balance += revenue
                self.positions[symbol] -= quantity
                self.trades.append({
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'quantity': quantity,
                    'timestamp': 'now'
                })
                return True
        
        return False
    
    def get_portfolio_value(self, current_prices):
        """Calculate total portfolio value."""
        total_value = self.balance
        
        for symbol, quantity in self.positions.items():
            if symbol in current_prices:
                total_value += quantity * current_prices[symbol]
        
        return total_value
    
    def get_statistics(self):
        """Get trading statistics."""
        total_trades = len(self.trades)
        buy_trades = sum(1 for trade in self.trades if trade['action'] == 'BUY')
        sell_trades = sum(1 for trade in self.trades if trade['action'] == 'SELL')
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'balance': self.balance,
            'positions': dict(self.positions)
        }


class TestTradingSystem:
    """Test suite for TradingSystem."""
    
    @pytest.fixture
    def trading_system(self):
        """Create a fresh trading system for each test."""
        return TradingSystem()
    
    def test_sma_calculation(self, trading_system):
        """Test SMA calculation."""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        
        sma_5 = trading_system.calculate_sma(prices, 5)
        sma_10 = trading_system.calculate_sma(prices, 10)
        
        assert sma_5 == 114.0
        assert sma_10 == 109.0
    
    def test_sma_insufficient_data(self, trading_system):
        """Test SMA with insufficient data."""
        prices = [100, 102, 104]
        sma_5 = trading_system.calculate_sma(prices, 5)
        assert sma_5 is None
    
    def test_crossover_detection_bullish(self, trading_system):
        """Test bullish crossover detection."""
        signal = trading_system.detect_crossover(115, 110, 109, 111)
        assert signal == "BUY"
    
    def test_crossover_detection_bearish(self, trading_system):
        """Test bearish crossover detection."""
        signal = trading_system.detect_crossover(109, 111, 115, 110)
        assert signal == "SELL"
    
    def test_crossover_detection_hold(self, trading_system):
        """Test no crossover (hold signal)."""
        signal = trading_system.detect_crossover(115, 110, 114, 109)
        assert signal == "HOLD"
    
    def test_crossover_detection_none_values(self, trading_system):
        """Test crossover detection with None values."""
        signal = trading_system.detect_crossover(None, 110, 114, 109)
        assert signal is None
    
    def test_position_sizing(self, trading_system):
        """Test position size calculation."""
        position_size = trading_system.calculate_position_size(50000, 49000, 2)
        expected_size = (10000 * 0.02) / (50000 - 49000)  # 200 / 1000 = 0.2
        assert abs(position_size - expected_size) < 0.001
    
    def test_position_sizing_invalid_price(self, trading_system):
        """Test position sizing with invalid price."""
        position_size = trading_system.calculate_position_size(0, 49000, 2)
        assert position_size == 0
    
    def test_position_sizing_zero_risk(self, trading_system):
        """Test position sizing with zero risk."""
        position_size = trading_system.calculate_position_size(50000, 50000, 2)
        assert position_size == 0
    
    def test_execute_buy_trade_success(self, trading_system):
        """Test successful buy trade execution."""
        success = trading_system.execute_trade("BTCUSDT", "BUY", 50000, 0.1)
        
        assert success is True
        assert trading_system.balance == 5000
        assert trading_system.positions["BTCUSDT"] == 0.1
        assert len(trading_system.trades) == 1
    
    def test_execute_buy_trade_insufficient_balance(self, trading_system):
        """Test buy trade with insufficient balance."""
        success = trading_system.execute_trade("BTCUSDT", "BUY", 50000, 1.0)
        
        assert success is False
        assert trading_system.balance == 10000  # Unchanged
        assert "BTCUSDT" not in trading_system.positions
    
    def test_execute_sell_trade_success(self, trading_system):
        """Test successful sell trade execution."""
        # First buy some
        trading_system.execute_trade("BTCUSDT", "BUY", 50000, 0.1)
        
        # Then sell
        success = trading_system.execute_trade("BTCUSDT", "SELL", 52000, 0.05)
        
        assert success is True
        assert trading_system.balance == 5000 + (52000 * 0.05)  # 5000 + 2600 = 7600
        assert trading_system.positions["BTCUSDT"] == 0.05
        assert len(trading_system.trades) == 2
    
    def test_execute_sell_trade_insufficient_position(self, trading_system):
        """Test sell trade with insufficient position."""
        success = trading_system.execute_trade("BTCUSDT", "SELL", 50000, 0.1)
        
        assert success is False
        assert trading_system.balance == 10000  # Unchanged
    
    def test_portfolio_value_calculation(self, trading_system):
        """Test portfolio value calculation."""
        # Execute a trade
        trading_system.execute_trade("BTCUSDT", "BUY", 50000, 0.1)
        
        # Calculate portfolio value
        current_prices = {"BTCUSDT": 52000}
        portfolio_value = trading_system.get_portfolio_value(current_prices)
        
        expected_value = 5000 + (0.1 * 52000)  # 5000 + 5200 = 10200
        assert portfolio_value == expected_value
    
    def test_portfolio_value_no_positions(self, trading_system):
        """Test portfolio value with no positions."""
        current_prices = {"BTCUSDT": 52000}
        portfolio_value = trading_system.get_portfolio_value(current_prices)
        
        assert portfolio_value == 10000  # Just the balance
    
    def test_get_statistics(self, trading_system):
        """Test statistics calculation."""
        # Execute some trades
        trading_system.execute_trade("BTCUSDT", "BUY", 50000, 0.1)
        trading_system.execute_trade("ETHUSDT", "BUY", 3000, 1.0)
        trading_system.execute_trade("BTCUSDT", "SELL", 52000, 0.05)
        
        stats = trading_system.get_statistics()
        
        assert stats['total_trades'] == 3
        assert stats['buy_trades'] == 2
        assert stats['sell_trades'] == 1
        assert stats['balance'] == 4600  # 10000 - 5000 - 3000 + 2600
        assert 'positions' in stats
    
    def test_get_statistics_no_trades(self, trading_system):
        """Test statistics with no trades."""
        stats = trading_system.get_statistics()
        
        assert stats['total_trades'] == 0
        assert stats['buy_trades'] == 0
        assert stats['sell_trades'] == 0
        assert stats['balance'] == 10000
        assert stats['positions'] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=test_trading_system", "--cov-report=term-missing", "--cov-report=html"])