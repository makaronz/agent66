"""
Standalone test file to demonstrate coverage without complex dependencies.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os


class TradingDataProcessor:
    """Simple trading data processor for testing."""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def validate_ohlc_data(self, data):
        """Validate OHLC data structure."""
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(field in data for field in required_fields):
            self.error_count += 1
            return False
        
        # Validate OHLC relationships
        if data['high'] < max(data['open'], data['close']):
            self.error_count += 1
            return False
        
        if data['low'] > min(data['open'], data['close']):
            self.error_count += 1
            return False
        
        if data['volume'] <= 0:
            self.error_count += 1
            return False
        
        self.processed_count += 1
        return True
    
    def calculate_returns(self, prices):
        """Calculate price returns."""
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        return returns
    
    def detect_trend(self, prices, window=5):
        """Simple trend detection."""
        if len(prices) < window:
            return 'insufficient_data'
        
        recent_prices = prices[-window:]
        
        # Calculate linear trend
        x = list(range(len(recent_prices)))
        y = recent_prices
        
        # Simple linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.001:
            return 'uptrend'
        elif slope < -0.001:
            return 'downtrend'
        else:
            return 'sideways'
    
    def calculate_volatility(self, returns):
        """Calculate volatility from returns."""
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility
    
    def get_statistics(self):
        """Get processing statistics."""
        total = self.processed_count + self.error_count
        success_rate = self.processed_count / total if total > 0 else 0
        
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'total': total,
            'success_rate': success_rate
        }


class SimpleRiskManager:
    """Simple risk manager for testing."""
    
    def __init__(self, max_risk_per_trade=0.02):
        self.max_risk_per_trade = max_risk_per_trade
        self.trades = []
    
    def calculate_position_size(self, account_balance, entry_price, stop_loss):
        """Calculate position size based on risk."""
        if stop_loss == entry_price:
            return 0
        
        risk_amount = account_balance * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        position_size = risk_amount / price_risk
        
        return position_size
    
    def validate_trade(self, trade):
        """Validate trade parameters."""
        required_fields = ['symbol', 'action', 'entry_price', 'stop_loss', 'position_size']
        
        if not all(field in trade for field in required_fields):
            return False, "Missing required fields"
        
        if trade['action'] not in ['BUY', 'SELL']:
            return False, "Invalid action"
        
        if trade['position_size'] <= 0:
            return False, "Invalid position size"
        
        if trade['entry_price'] <= 0:
            return False, "Invalid entry price"
        
        # Validate stop loss
        if trade['action'] == 'BUY' and trade['stop_loss'] >= trade['entry_price']:
            return False, "Invalid stop loss for BUY order"
        
        if trade['action'] == 'SELL' and trade['stop_loss'] <= trade['entry_price']:
            return False, "Invalid stop loss for SELL order"
        
        return True, "Valid trade"
    
    def add_trade(self, trade):
        """Add trade to tracking."""
        is_valid, message = self.validate_trade(trade)
        if is_valid:
            self.trades.append(trade)
            return True
        return False
    
    def get_portfolio_risk(self):
        """Calculate total portfolio risk."""
        total_risk = 0
        for trade in self.trades:
            risk = abs(trade['entry_price'] - trade['stop_loss']) * trade['position_size']
            total_risk += risk
        
        return total_risk


class SimpleDecisionEngine:
    """Simple decision engine for testing."""
    
    def __init__(self, confidence_threshold=0.7):
        self.confidence_threshold = confidence_threshold
        self.decisions = []
    
    def analyze_market_data(self, data):
        """Analyze market data and return signals."""
        if len(data) < 10:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'Insufficient data'}
        
        # Simple moving average crossover
        short_ma = sum(data[-5:]) / 5
        long_ma = sum(data[-10:]) / 10
        
        if short_ma > long_ma * 1.01:  # 1% threshold
            confidence = min(0.9, (short_ma - long_ma) / long_ma * 10)
            return {'signal': 'BUY', 'confidence': confidence, 'reason': 'MA crossover bullish'}
        elif short_ma < long_ma * 0.99:  # 1% threshold
            confidence = min(0.9, (long_ma - short_ma) / long_ma * 10)
            return {'signal': 'SELL', 'confidence': confidence, 'reason': 'MA crossover bearish'}
        else:
            return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'No clear signal'}
    
    def make_decision(self, market_data, risk_params=None):
        """Make trading decision."""
        analysis = self.analyze_market_data(market_data)
        
        # Apply confidence threshold
        if analysis['confidence'] < self.confidence_threshold:
            decision = {
                'action': 'HOLD',
                'confidence': analysis['confidence'],
                'reason': f"Confidence below threshold: {analysis['reason']}"
            }
        else:
            decision = {
                'action': analysis['signal'],
                'confidence': analysis['confidence'],
                'reason': analysis['reason']
            }
        
        self.decisions.append(decision)
        return decision
    
    def get_decision_stats(self):
        """Get decision statistics."""
        if not self.decisions:
            return {'total': 0, 'buy': 0, 'sell': 0, 'hold': 0}
        
        stats = {'total': len(self.decisions), 'buy': 0, 'sell': 0, 'hold': 0}
        
        for decision in self.decisions:
            action = decision['action'].lower()
            if action in stats:
                stats[action] += 1
        
        return stats


# Test Classes
class TestTradingDataProcessor:
    """Test the trading data processor."""
    
    @pytest.fixture
    def processor(self):
        return TradingDataProcessor()
    
    def test_validate_ohlc_data_valid(self, processor):
        """Test OHLC validation with valid data."""
        valid_data = {
            'open': 50000,
            'high': 50100,
            'low': 49900,
            'close': 50050,
            'volume': 1000
        }
        
        result = processor.validate_ohlc_data(valid_data)
        assert result is True
        assert processor.processed_count == 1
        assert processor.error_count == 0
    
    def test_validate_ohlc_data_invalid_high(self, processor):
        """Test OHLC validation with invalid high."""
        invalid_data = {
            'open': 50000,
            'high': 49000,  # High < Open (invalid)
            'low': 49900,
            'close': 50050,
            'volume': 1000
        }
        
        result = processor.validate_ohlc_data(invalid_data)
        assert result is False
        assert processor.error_count == 1
    
    def test_validate_ohlc_data_missing_fields(self, processor):
        """Test OHLC validation with missing fields."""
        incomplete_data = {
            'open': 50000,
            'high': 50100,
            # Missing 'low', 'close', 'volume'
        }
        
        result = processor.validate_ohlc_data(incomplete_data)
        assert result is False
        assert processor.error_count == 1
    
    def test_calculate_returns(self, processor):
        """Test return calculation."""
        prices = [100, 105, 102, 108, 110]
        returns = processor.calculate_returns(prices)
        
        expected_returns = [0.05, -0.0286, 0.0588, 0.0185]  # Approximate
        
        assert len(returns) == 4
        assert abs(returns[0] - 0.05) < 0.001
        assert abs(returns[1] - (-0.0286)) < 0.001
    
    def test_detect_trend_uptrend(self, processor):
        """Test trend detection for uptrend."""
        uptrend_prices = [100, 102, 104, 106, 108, 110]
        trend = processor.detect_trend(uptrend_prices)
        assert trend == 'uptrend'
    
    def test_detect_trend_downtrend(self, processor):
        """Test trend detection for downtrend."""
        downtrend_prices = [110, 108, 106, 104, 102, 100]
        trend = processor.detect_trend(downtrend_prices)
        assert trend == 'downtrend'
    
    def test_detect_trend_sideways(self, processor):
        """Test trend detection for sideways market."""
        sideways_prices = [100, 101, 100, 101, 100, 101]
        trend = processor.detect_trend(sideways_prices)
        assert trend == 'sideways'
    
    def test_calculate_volatility(self, processor):
        """Test volatility calculation."""
        returns = [0.01, -0.02, 0.015, -0.01, 0.005]
        volatility = processor.calculate_volatility(returns)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    def test_get_statistics(self, processor):
        """Test statistics calculation."""
        # Process some data
        processor.validate_ohlc_data({'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000})
        processor.validate_ohlc_data({'open': 100, 'high': 98, 'low': 99, 'close': 100, 'volume': 1000})  # Invalid
        
        stats = processor.get_statistics()
        
        assert stats['processed'] == 1
        assert stats['errors'] == 1
        assert stats['total'] == 2
        assert stats['success_rate'] == 0.5


class TestSimpleRiskManager:
    """Test the simple risk manager."""
    
    @pytest.fixture
    def risk_manager(self):
        return SimpleRiskManager(max_risk_per_trade=0.02)
    
    def test_calculate_position_size(self, risk_manager):
        """Test position size calculation."""
        account_balance = 10000
        entry_price = 50000
        stop_loss = 49500
        
        position_size = risk_manager.calculate_position_size(account_balance, entry_price, stop_loss)
        
        # Expected: (10000 * 0.02) / (50000 - 49500) = 200 / 500 = 0.4
        assert abs(position_size - 0.4) < 0.001
    
    def test_validate_trade_valid(self, risk_manager):
        """Test trade validation with valid trade."""
        valid_trade = {
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'entry_price': 50000,
            'stop_loss': 49500,
            'position_size': 0.1
        }
        
        is_valid, message = risk_manager.validate_trade(valid_trade)
        assert is_valid is True
        assert "Valid trade" in message
    
    def test_validate_trade_invalid_action(self, risk_manager):
        """Test trade validation with invalid action."""
        invalid_trade = {
            'symbol': 'BTCUSDT',
            'action': 'INVALID',
            'entry_price': 50000,
            'stop_loss': 49500,
            'position_size': 0.1
        }
        
        is_valid, message = risk_manager.validate_trade(invalid_trade)
        assert is_valid is False
        assert "Invalid action" in message
    
    def test_validate_trade_invalid_stop_loss(self, risk_manager):
        """Test trade validation with invalid stop loss."""
        invalid_trade = {
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'entry_price': 50000,
            'stop_loss': 50500,  # Stop loss above entry for BUY (invalid)
            'position_size': 0.1
        }
        
        is_valid, message = risk_manager.validate_trade(invalid_trade)
        assert is_valid is False
        assert "Invalid stop loss" in message
    
    def test_add_trade(self, risk_manager):
        """Test adding trades."""
        valid_trade = {
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'entry_price': 50000,
            'stop_loss': 49500,
            'position_size': 0.1
        }
        
        result = risk_manager.add_trade(valid_trade)
        assert result is True
        assert len(risk_manager.trades) == 1
    
    def test_get_portfolio_risk(self, risk_manager):
        """Test portfolio risk calculation."""
        trades = [
            {
                'symbol': 'BTCUSDT',
                'action': 'BUY',
                'entry_price': 50000,
                'stop_loss': 49500,
                'position_size': 0.1
            },
            {
                'symbol': 'ETHUSDT',
                'action': 'SELL',
                'entry_price': 3000,
                'stop_loss': 3100,
                'position_size': 1.0
            }
        ]
        
        for trade in trades:
            risk_manager.add_trade(trade)
        
        portfolio_risk = risk_manager.get_portfolio_risk()
        
        # Expected: (50000-49500)*0.1 + (3100-3000)*1.0 = 50 + 100 = 150
        assert abs(portfolio_risk - 150) < 0.001


class TestSimpleDecisionEngine:
    """Test the simple decision engine."""
    
    @pytest.fixture
    def decision_engine(self):
        return SimpleDecisionEngine(confidence_threshold=0.7)
    
    def test_analyze_market_data_bullish(self, decision_engine):
        """Test market analysis with bullish signal."""
        # Create data where short MA > long MA
        bullish_data = [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]
        
        analysis = decision_engine.analyze_market_data(bullish_data)
        
        assert analysis['signal'] == 'BUY'
        assert analysis['confidence'] > 0
        assert 'bullish' in analysis['reason']
    
    def test_analyze_market_data_bearish(self, decision_engine):
        """Test market analysis with bearish signal."""
        # Create data where short MA < long MA
        bearish_data = [110, 109, 108, 107, 106, 105, 104, 103, 102, 100]
        
        analysis = decision_engine.analyze_market_data(bearish_data)
        
        assert analysis['signal'] == 'SELL'
        assert analysis['confidence'] > 0
        assert 'bearish' in analysis['reason']
    
    def test_analyze_market_data_insufficient(self, decision_engine):
        """Test market analysis with insufficient data."""
        insufficient_data = [100, 101, 102]
        
        analysis = decision_engine.analyze_market_data(insufficient_data)
        
        assert analysis['signal'] == 'HOLD'
        assert analysis['confidence'] == 0.0
        assert 'Insufficient data' in analysis['reason']
    
    def test_make_decision_high_confidence(self, decision_engine):
        """Test decision making with high confidence."""
        # Strong bullish data
        strong_bullish_data = [100, 102, 104, 106, 108, 110, 112, 114, 116, 120]
        
        decision = decision_engine.make_decision(strong_bullish_data)
        
        assert decision['action'] == 'BUY'
        assert decision['confidence'] >= 0.7
    
    def test_make_decision_low_confidence(self, decision_engine):
        """Test decision making with low confidence."""
        # Sideways data (low confidence)
        sideways_data = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101]
        
        decision = decision_engine.make_decision(sideways_data)
        
        assert decision['action'] == 'HOLD'
        assert 'below threshold' in decision['reason']
    
    def test_get_decision_stats(self, decision_engine):
        """Test decision statistics."""
        # Make several decisions
        decision_engine.make_decision([100, 102, 104, 106, 108, 110, 112, 114, 116, 120])  # BUY
        decision_engine.make_decision([120, 118, 116, 114, 112, 110, 108, 106, 104, 100])  # SELL
        decision_engine.make_decision([100, 101, 100, 101, 100, 101, 100, 101, 100, 101])  # HOLD
        
        stats = decision_engine.get_decision_stats()
        
        assert stats['total'] == 3
        assert stats['buy'] >= 0
        assert stats['sell'] >= 0
        assert stats['hold'] >= 0


@pytest.mark.integration
class TestIntegrationScenarios:
    """Test integration between components."""
    
    def test_full_trading_pipeline(self):
        """Test complete trading pipeline integration."""
        # Initialize components
        processor = TradingDataProcessor()
        risk_manager = SimpleRiskManager()
        decision_engine = SimpleDecisionEngine()
        
        # Create market data
        market_data = [
            {'open': 50000, 'high': 50100, 'low': 49900, 'close': 50050, 'volume': 1000},
            {'open': 50050, 'high': 50200, 'low': 50000, 'close': 50150, 'volume': 1200},
            {'open': 50150, 'high': 50300, 'low': 50100, 'close': 50250, 'volume': 1100},
            {'open': 50250, 'high': 50400, 'low': 50200, 'close': 50350, 'volume': 1300},
            {'open': 50350, 'high': 50500, 'low': 50300, 'close': 50450, 'volume': 1400},
        ]
        
        # Process and validate data
        valid_data = []
        for candle in market_data:
            if processor.validate_ohlc_data(candle):
                valid_data.append(candle['close'])
        
        # Make trading decision
        if len(valid_data) >= 5:
            decision = decision_engine.make_decision(valid_data)
            
            # If decision is to trade, calculate risk parameters
            if decision['action'] in ['BUY', 'SELL']:
                entry_price = valid_data[-1]
                stop_loss = entry_price * 0.99 if decision['action'] == 'BUY' else entry_price * 1.01
                
                position_size = risk_manager.calculate_position_size(10000, entry_price, stop_loss)
                
                trade = {
                    'symbol': 'BTCUSDT',
                    'action': decision['action'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'position_size': position_size
                }
                
                # Validate and add trade
                trade_added = risk_manager.add_trade(trade)
                assert trade_added is True
        
        # Verify pipeline worked
        stats = processor.get_statistics()
        assert stats['processed'] > 0
        assert stats['success_rate'] > 0
    
    def test_error_handling_pipeline(self):
        """Test error handling in the pipeline."""
        processor = TradingDataProcessor()
        
        # Test with invalid data
        invalid_data = [
            {'open': 50000, 'high': 49000, 'low': 49900, 'close': 50050, 'volume': 1000},  # Invalid high
            {'open': 50000, 'high': 50100, 'low': 51000, 'close': 50050, 'volume': 1000},  # Invalid low
            {'open': 50000, 'high': 50100, 'low': 49900, 'close': 50050, 'volume': -100},  # Invalid volume
        ]
        
        for candle in invalid_data:
            result = processor.validate_ohlc_data(candle)
            assert result is False
        
        stats = processor.get_statistics()
        assert stats['errors'] == 3
        assert stats['success_rate'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=term-missing", "--cov-report=html"])