"""
Pytest configuration and fixtures for the enhanced trading system test suite.
"""

import pytest
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable external library warnings during testing
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration for all components"""
    return {
        'risk_manager': {
            'max_position_size': 1000.0,
            'max_portfolio_risk': 0.02,
            'max_daily_loss': 500.0,
            'max_drawdown': 0.15,
            'min_risk_reward': 1.5,
            'max_leverage': 3.0,
            'var_limit': 0.05,
            'stress_test_loss': 0.10,
            'position_sizing_method': 'adaptive',
            'stop_loss_method': 'adaptive'
        },
        'execution_engine': {
            'max_workers': 4,
            'execution_workers': 2,
            'max_chunk_size': 1000.0,
            'min_chunk_size': 10.0
        },
        'smc_detector': {
            'volume_profile_bins': 50,
            'confidence_threshold': 0.7,
            'max_history_size': 1000
        },
        'error_handler': {
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60.0,
            'retry_max_attempts': 3,
            'retry_base_delay': 1.0,
            'retry_max_delay': 60.0
        },
        'monitoring': {
            'health_check_interval': 30,
            'metrics_collection_interval': 60,
            'alert_error_rate': 0.1,
            'alert_circuit_breaker_rate': 0.2,
            'alert_avg_response_time': 5000,
            'alert_critical_error_rate': 0.05
        }
    }

@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """Generate sample market data for testing"""
    np.random.seed(42)  # For reproducible tests

    # Generate 500 hourly candles
    periods = 500
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='H')

    # Generate realistic price series with trend and volatility
    base_price = 50000.0
    trend_factor = 0.0001  # Slight uptrend
    volatility = 0.002  # 0.2% standard deviation

    # Generate price series
    returns = np.random.normal(trend_factor, volatility, periods)
    prices = [base_price]

    for i in range(1, periods):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)

    prices = np.array(prices)

    # Generate OHLC data
    high_low_range = 0.001  # 0.1% typical range
    candle_range = prices * high_low_range

    opens = prices + np.random.normal(0, candle_range * 0.3, periods)
    highs = prices + np.random.uniform(0, candle_range, periods)
    lows = prices - np.random.uniform(0, candle_range, periods)
    closes = prices

    # Ensure OHLC relationships are maintained
    for i in range(periods):
        highs[i] = max(highs[i], opens[i], closes[i])
        lows[i] = min(lows[i], opens[i], closes[i])

    # Generate volume data with realistic patterns
    base_volume = 1000.0
    volumes = np.random.lognormal(np.log(base_volume), 0.5, periods)

    # Add volume spikes (simulating institutional activity)
    spike_indices = np.random.choice(periods, size=25, replace=False)
    volumes[spike_indices] *= np.random.uniform(3, 10, 25)

    # Add some volume patterns (e.g., increasing volume during trends)
    trend_volume_boost = np.linspace(1.0, 1.5, periods)
    volumes *= trend_volume_boost

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })

@pytest.fixture
def volatile_market_data() -> pd.DataFrame:
    """Generate volatile market data for testing edge cases"""
    np.random.seed(123)  # Different seed for variety

    periods = 200
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='H')

    # High volatility scenario
    base_price = 50000.0
    high_volatility = 0.008  # 0.8% standard deviation

    returns = np.random.normal(0, high_volatility, periods)
    prices = [base_price]

    for i in range(1, periods):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)

    prices = np.array(prices)

    # Wider candle ranges for volatile market
    high_low_range = 0.003  # 0.3% range
    candle_range = prices * high_low_range

    opens = prices + np.random.normal(0, candle_range * 0.5, periods)
    highs = prices + np.random.uniform(0, candle_range * 1.5, periods)
    lows = prices - np.random.uniform(0, candle_range * 1.5, periods)
    closes = prices

    # Maintain OHLC relationships
    for i in range(periods):
        highs[i] = max(highs[i], opens[i], closes[i])
        lows[i] = min(lows[i], opens[i], closes[i])

    # Higher volume in volatile market
    base_volume = 2000.0
    volumes = np.random.lognormal(np.log(base_volume), 0.8, periods)

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })

@pytest.fixture
def illiquid_market_data() -> pd.DataFrame:
    """Generate illiquid market data for testing"""
    np.random.seed(456)

    periods = 100
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='H')

    # Low volatility, low volume scenario
    base_price = 50000.0
    low_volatility = 0.0005  # 0.05% standard deviation

    returns = np.random.normal(0, low_volatility, periods)
    prices = [base_price]

    for i in range(1, periods):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)

    prices = np.array(prices)

    # Very tight candle ranges
    high_low_range = 0.0002  # 0.02% range
    candle_range = prices * high_low_range

    opens = prices + np.random.normal(0, candle_range * 0.2, periods)
    highs = prices + np.random.uniform(0, candle_range, periods)
    lows = prices - np.random.uniform(0, candle_range, periods)
    closes = prices

    # Maintain OHLC relationships
    for i in range(periods):
        highs[i] = max(highs[i], opens[i], closes[i])
        lows[i] = min(lows[i], opens[i], closes[i])

    # Low volume
    base_volume = 200.0
    volumes = np.random.lognormal(np.log(base_volume), 0.3, periods)

    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })

@pytest.fixture
def multi_symbol_data() -> Dict[str, pd.DataFrame]:
    """Generate market data for multiple symbols"""
    symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']

    base_prices = {
        'BTC/USDT': 50000.0,
        'ETH/USDT': 3000.0,
        'ADA/USDT': 0.5
    }

    data = {}
    np.random.seed(789)

    for symbol in symbols:
        periods = 200
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='H')

        base_price = base_prices[symbol]
        volatility = 0.002 if symbol == 'BTC/USDT' else 0.003  # Higher volatility for alts

        returns = np.random.normal(0, volatility, periods)
        prices = [base_price]

        for i in range(1, periods):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(new_price)

        prices = np.array(prices)
        high_low_range = volatility * 2
        candle_range = prices * high_low_range

        opens = prices + np.random.normal(0, candle_range * 0.3, periods)
        highs = prices + np.random.uniform(0, candle_range, periods)
        lows = prices - np.random.uniform(0, candle_range, periods)
        closes = prices

        # Maintain OHLC relationships
        for i in range(periods):
            highs[i] = max(highs[i], opens[i], closes[i])
            lows[i] = min(lows[i], opens[i], closes[i])

        # Volume varies by symbol
        base_volume = {'BTC/USDT': 1000, 'ETH/USDT': 5000, 'ADA/USDT': 100000}[symbol]
        volumes = np.random.lognormal(np.log(base_volume), 0.5, periods)

        data[symbol] = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

    return data

@pytest.fixture
def mock_exchange_api():
    """Mock exchange API for testing"""
    class MockExchangeAPI:
        def __init__(self):
            self.orders = {}
            self.account_balance = 10000.0
            self.positions = {}

        async def submit_order(self, order_request):
            """Mock order submission"""
            order_id = f"order_{datetime.utcnow().timestamp()}"

            # Simulate order processing
            await asyncio.sleep(0.01)  # 10ms processing time

            # Mock fill
            fill_price = order_request.price or 50000.0
            if order_request.side == "buy":
                fill_price *= 1.0001  # Small slippage
            else:
                fill_price *= 0.9999

            self.orders[order_id] = {
                'id': order_id,
                'status': 'filled',
                'filled_quantity': order_request.quantity,
                'average_price': fill_price,
                'timestamp': datetime.utcnow()
            }

            return {
                'orderId': order_id,
                'status': 'filled',
                'filledQty': order_request.quantity,
                'avgPx': fill_price
            }

        async def get_order_status(self, order_id):
            """Mock order status check"""
            return self.orders.get(order_id)

        async def get_account_info(self):
            """Mock account information"""
            return {
                'balance': self.account_balance,
                'positions': self.positions
            }

    return MockExchangeAPI()

@pytest.fixture
def performance_metrics():
    """Performance metrics for testing"""
    return {
        'max_analysis_time': 1.0,  # 1 second max
        'max_risk_calculation_time': 0.5,  # 500ms max
        'max_order_execution_time': 0.05,  # 50ms max
        'max_concurrent_operations': 10,
        'memory_limit_mb': 1000,
        'cpu_limit_percent': 80
    }

@pytest.fixture
def mock_config():
    """Mock configuration for testing (legacy compatibility)."""
    return {
        'max_drawdown': 0.10,
        'max_var': 0.05,
        'max_correlation': 0.70,
        'recovery_timeout': 300,
        'check_interval': 60,
        'var_calculator': {
            'confidence_levels': [0.95, 0.99],
            'lookback_period': 252,
            'monte_carlo_simulations': 10000,
            'correlation_threshold': 0.7,
            'cache_ttl': 300
        },
        'risk_metrics': {
            'thresholds': {
                'market': {'max_drawdown': 0.10, 'max_var': 0.05, 'max_volatility': 0.30},
                'credit': {'max_exposure': 0.20, 'max_default_probability': 0.01},
                'liquidity': {'min_bid_ask_spread': 0.001, 'min_market_depth': 1000000, 'min_trading_volume': 500000},
                'operational': {'max_error_rate': 0.01, 'max_latency': 1000, 'min_data_quality': 0.95},
                'concentration': {'max_position_size': 0.20, 'max_sector_exposure': 0.30},
                'correlation': {'max_correlation': 0.70, 'min_diversification': 0.50}
            },
            'calculation_interval': 60,
            'alert_cooldown': 300
        },
        'position_manager': {
            'max_retry_attempts': 3,
            'retry_delay': 1.0,
            'closure_timeout': 30.0,
            'concurrent_closures': 5
        },
        'notifications': {
            'rate_limits': {
                'email': 100,
                'sms': 50,
                'slack': 200
            },
            'throttle_delay': 1.0,
            'max_retry_attempts': 3,
            'retry_delay': 5.0,
            'recipients': {
                'email': ['test@example.com'],
                'sms': ['+1234567890'],
                'slack': ['#alerts']
            }
        }
    }


@pytest.fixture
def mock_exchange_connectors():
    """Mock exchange connectors for testing (legacy compatibility)."""
    connectors = {}

    # Mock Binance connector
    binance_mock = Mock()
    binance_mock.name = "binance"
    binance_mock.connected = True
    binance_mock.fetch_rest_data = AsyncMock(return_value={
        'positions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'long',
                'size': 1.0,
                'entry_price': 50000,
                'current_price': 51000,
                'unrealized_pnl': 1000
            }
        ]
    })
    connectors['binance'] = binance_mock

    # Mock Bybit connector
    bybit_mock = Mock()
    bybit_mock.name = "bybit"
    bybit_mock.connected = True
    bybit_mock.fetch_rest_data = AsyncMock(return_value={
        'positions': [
            {
                'symbol': 'ETHUSDT',
                'side': 'short',
                'size': 10.0,
                'entry_price': 3000,
                'current_price': 2900,
                'unrealized_pnl': 1000
            }
        ]
    })
    connectors['bybit'] = bybit_mock

    return connectors


@pytest.fixture
def mock_service_manager():
    """Mock service manager for testing (legacy compatibility)."""
    service_manager = Mock()
    service_manager.get_service_health = Mock(return_value={
        'circuit_breaker': {'healthy': True},
        'position_manager': {'healthy': True},
        'notification_service': {'healthy': True}
    })
    return service_manager


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing (legacy compatibility)."""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)

    returns = np.random.normal(0.001, 0.02, 100)
    values = 1000000 * (1 + np.cumsum(returns))

    portfolio_data = pd.DataFrame({
        'timestamp': dates,
        'value': values,
        'returns': returns,
        'BTCUSDT': np.random.normal(0.001, 0.03, 100),
        'ETHUSDT': np.random.normal(0.001, 0.025, 100),
        'ADAUSDT': np.random.normal(0.001, 0.035, 100)
    })

    return portfolio_data


