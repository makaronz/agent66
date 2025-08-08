import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
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
    """Mock exchange connectors for testing."""
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
    """Mock service manager for testing."""
    service_manager = Mock()
    service_manager.get_service_health = Mock(return_value={
        'circuit_breaker': {'healthy': True},
        'position_manager': {'healthy': True},
        'notification_service': {'healthy': True}
    })
    return service_manager


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing."""
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


