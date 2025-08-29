"""
Integration Test Configuration

Provides fixtures and configuration for integration tests with real exchange APIs.
"""

import os
import pytest
import logging
from typing import List, Dict, Any

from data_pipeline.exchange_connectors.production_config import ExchangeType


class SandboxTestConfig:
    """Configuration for sandbox testing."""
    
    def __init__(self):
        """Initialize sandbox test configuration."""
        self.binance_testnet = {
            "api_key": os.getenv("BINANCE_TESTNET_API_KEY"),
            "api_secret": os.getenv("BINANCE_TESTNET_API_SECRET"),
            "rest_url": "https://testnet.binance.vision",
            "websocket_url": "wss://testnet.binance.vision/ws/",
            "rate_limit": 1200
        }
        
        self.bybit_testnet = {
            "api_key": os.getenv("BYBIT_TESTNET_API_KEY"),
            "api_secret": os.getenv("BYBIT_TESTNET_API_SECRET"),
            "rest_url": "https://api-testnet.bybit.com",
            "websocket_url": "wss://stream-testnet.bybit.com/v5/public/spot",
            "rate_limit": 120
        }
        
        self.oanda_practice = {
            "api_key": os.getenv("OANDA_PRACTICE_API_KEY"),
            "api_secret": os.getenv("OANDA_PRACTICE_API_SECRET"),
            "account_id": os.getenv("OANDA_PRACTICE_ACCOUNT_ID"),
            "rest_url": "https://api-fxpractice.oanda.com/v3",
            "websocket_url": "wss://stream-fxpractice.oanda.com/v3/accounts/{account_id}/pricing/stream",
            "rate_limit": 120
        }
    
    def has_binance_credentials(self) -> bool:
        """Check if Binance testnet credentials are available."""
        return bool(self.binance_testnet["api_key"] and self.binance_testnet["api_secret"])
    
    def has_bybit_credentials(self) -> bool:
        """Check if Bybit testnet credentials are available."""
        return bool(self.bybit_testnet["api_key"] and self.bybit_testnet["api_secret"])
    
    def has_oanda_credentials(self) -> bool:
        """Check if Oanda practice credentials are available."""
        return bool(
            self.oanda_practice["api_key"] and 
            self.oanda_practice["api_secret"] and 
            self.oanda_practice["account_id"]
        )
    
    def get_available_exchanges(self) -> List[ExchangeType]:
        """Get list of exchanges with available credentials."""
        available = []
        if self.has_binance_credentials():
            available.append(ExchangeType.BINANCE)
        if self.has_bybit_credentials():
            available.append(ExchangeType.BYBIT)
        if self.has_oanda_credentials():
            available.append(ExchangeType.OANDA)
        return available


@pytest.fixture(scope="session")
def sandbox_config():
    """Sandbox configuration fixture."""
    return SandboxTestConfig()


@pytest.fixture(scope="session")
def skip_if_no_credentials():
    """Skip test if no credentials available."""
    config = SandboxTestConfig()
    available = config.get_available_exchanges()
    
    if not available:
        pytest.skip("No sandbox/testnet credentials available. Set environment variables:\n"
                   "BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET\n"
                   "BYBIT_TESTNET_API_KEY, BYBIT_TESTNET_API_SECRET\n"
                   "OANDA_PRACTICE_API_KEY, OANDA_PRACTICE_API_SECRET, OANDA_PRACTICE_ACCOUNT_ID")
    
    return available


@pytest.fixture(scope="session", autouse=True)
def setup_integration_logging():
    """Set up logging for integration tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Reduce noise from some loggers
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)


def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring real API credentials"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add integration marker to all tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests that might take a while
        if any(keyword in item.name.lower() for keyword in ["performance", "stress", "load", "cascade"]):
            item.add_marker(pytest.mark.slow)


# Environment variable documentation
REQUIRED_ENV_VARS = {
    "BINANCE_TESTNET_API_KEY": "Binance testnet API key for integration testing",
    "BINANCE_TESTNET_API_SECRET": "Binance testnet API secret for integration testing",
    "BYBIT_TESTNET_API_KEY": "Bybit testnet API key for integration testing", 
    "BYBIT_TESTNET_API_SECRET": "Bybit testnet API secret for integration testing",
    "OANDA_PRACTICE_API_KEY": "Oanda practice API key for integration testing",
    "OANDA_PRACTICE_API_SECRET": "Oanda practice API secret for integration testing",
    "OANDA_PRACTICE_ACCOUNT_ID": "Oanda practice account ID for integration testing"
}


def print_env_var_help():
    """Print help for required environment variables."""
    print("\nRequired Environment Variables for Integration Tests:")
    print("=" * 60)
    for var, description in REQUIRED_ENV_VARS.items():
        status = "✓ SET" if os.getenv(var) else "✗ NOT SET"
        print(f"{var:<30} {status:<10} {description}")
    print("=" * 60)


if __name__ == "__main__":
    print_env_var_help()