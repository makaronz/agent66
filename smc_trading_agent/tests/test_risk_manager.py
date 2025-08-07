import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from smc_trading_agent.risk_manager.circuit_breaker import CircuitBreaker
from smc_trading_agent.risk_manager.smc_risk_manager import SMCRiskManager

class TestCircuitBreaker:
    @pytest.fixture
    def circuit_breaker(self):
        return CircuitBreaker(max_drawdown=0.08, max_var=0.05)
        
    @pytest.mark.asyncio
    async def test_drawdown_trigger(self, circuit_breaker):
        # Test circuit breaker triggers on max drawdown
        portfolio_metrics = {'drawdown': 0.10}  # 10% > 8% limit
        
        # Mock the async method that would be called
        circuit_breaker.trigger_circuit_breaker = AsyncMock()
        
        result = await circuit_breaker.check_risk_limits(portfolio_metrics)
        
        assert result is False
        circuit_breaker.trigger_circuit_breaker.assert_called_once()
        
    def test_smc_stop_loss_calculation(self):
        # Test SMC-specific stop loss calculation
        smc_rm = SMCRiskManager()
        
        # Updated to use standardized price_level tuple format
        order_blocks = [{
            'type': 'bullish',
            'price_level': (29145.67, 29134.22),  # (high, low) tuple format
            'strength_volume': 0.78,
            'timestamp': '2023-10-27T10:00:00Z',
            'bos_confirmed_at': '2023-10-27T10:05:00Z'
        }]
        
        sl_price = smc_rm.calculate_stop_loss(
            entry_price=29140.0,
            direction="BUY",  # Updated to match risk manager expectation
            order_blocks=order_blocks,
            structure={'swing_low': 29120.0}
        )
        
        # Updated expected calculation to match risk manager logic
        # Risk manager uses price_level[1] * 0.998 for bullish order blocks
        expected_sl = 29134.22 * 0.998  # 0.2% buffer below the low
        assert abs(sl_price - expected_sl) < 0.01

    def test_smc_stop_loss_calculation_bearish(self):
        # Test SMC-specific stop loss calculation for bearish order blocks
        smc_rm = SMCRiskManager()
        
        # Bearish order block test data
        order_blocks = [{
            'type': 'bearish',
            'price_level': (29150.00, 29140.00),  # (high, low) tuple format
            'strength_volume': 0.85,
            'timestamp': '2023-10-27T10:00:00Z',
            'bos_confirmed_at': '2023-10-27T10:05:00Z'
        }]
        
        sl_price = smc_rm.calculate_stop_loss(
            entry_price=29145.0,
            direction="SELL",  # Short position
            order_blocks=order_blocks,
            structure={'swing_high': 29160.0}
        )
        
        # Risk manager uses price_level[0] * 1.002 for bearish order blocks
        expected_sl = 29150.00 * 1.002  # 0.2% buffer above the high
        assert abs(sl_price - expected_sl) < 0.01

    def test_smc_stop_loss_fallback(self):
        # Test fallback stop loss when no relevant order block is found
        smc_rm = SMCRiskManager()
        
        # Empty order blocks list
        order_blocks = []
        
        sl_price = smc_rm.calculate_stop_loss(
            entry_price=29140.0,
            direction="BUY",
            order_blocks=order_blocks,
            structure={'swing_low': 29120.0}
        )
        
        # Fallback should be 2% below entry price
        expected_sl = 29140.0 * 0.98
        assert abs(sl_price - expected_sl) < 0.01

