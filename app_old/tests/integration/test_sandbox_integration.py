"""
Real Exchange API Integration Testing - Sandbox/Testnet Environment

This module implements comprehensive integration tests for real exchange APIs
using sandbox/testnet environments. Tests validate:

1. Sandbox/testnet configuration for Binance, Bybit, and Oanda
2. Real API integration with proper rate limiting validation
3. Comprehensive error handling tests for exchange failures
4. Circuit breaker testing with real API rate limits
5. Failover mechanism testing between exchanges

Requirements covered: 1.5, 2.5, 3.3
"""

import asyncio
import logging
import os
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch
import json

from data_pipeline.exchange_connectors.production_config import (
    ProductionConfigManager, 
    ExchangeType, 
    Environment,
    ExchangeCredentials,
    RateLimitConfig
)
from data_pipeline.exchange_connectors.production_factory import (
    ProductionExchangeFactory,
    test_exchange_connections
)
from data_pipeline.exchange_connectors.binance_connector import BinanceConnector
from data_pipeline.exchange_connectors.bybit_connector import ByBitConnector
from data_pipeline.exchange_connectors.oanda_connector import OANDAConnector
from data_pipeline.exchange_connectors.error_handling import (
    ErrorHandlerManager,
    ExchangeError,
    ErrorCategory,
    ErrorSeverity,
    handle_exchange_error,
    execute_with_error_handling
)
from data_pipeline.exchange_connectors.rate_limiter import (
    RateLimitManager,
    ExchangeRateLimiter,
    RequestPriority,
    rate_limited
)
from data_pipeline.exchange_connectors.failover_manager import (
    ExchangeFailoverManager,
    FailoverTrigger,
    FailoverState
)
from risk_manager.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger(__name__)

# Test configuration constants
TESTNET_TIMEOUT = 30.0
MAX_RETRY_ATTEMPTS = 3
RATE_LIMIT_TEST_REQUESTS = 10


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


class TestSandboxConfiguration:
    """Test sandbox/testnet configuration setup."""
    
    def test_sandbox_config_initialization(self, sandbox_config):
        """Test sandbox configuration initialization."""
        assert isinstance(sandbox_config, SandboxTestConfig)
        
        # Test configuration structure
        assert "api_key" in sandbox_config.binance_testnet
        assert "rest_url" in sandbox_config.binance_testnet
        assert "websocket_url" in sandbox_config.binance_testnet
        
        assert "api_key" in sandbox_config.bybit_testnet
        assert "rest_url" in sandbox_config.bybit_testnet
        
        assert "api_key" in sandbox_config.oanda_practice
        assert "account_id" in sandbox_config.oanda_practice
    
    def test_credential_detection(self, sandbox_config):
        """Test credential detection methods."""
        # These should not raise exceptions
        binance_available = sandbox_config.has_binance_credentials()
        bybit_available = sandbox_config.has_bybit_credentials()
        oanda_available = sandbox_config.has_oanda_credentials()
        
        assert isinstance(binance_available, bool)
        assert isinstance(bybit_available, bool)
        assert isinstance(oanda_available, bool)
        
        available_exchanges = sandbox_config.get_available_exchanges()
        assert isinstance(available_exchanges, list)
        assert all(isinstance(ex, ExchangeType) for ex in available_exchanges)
    
    @pytest.mark.asyncio
    async def test_production_config_manager_testnet(self):
        """Test production config manager with testnet environment."""
        # Set test environment variables
        test_env = {
            "BINANCE_API_KEY": "test_key",
            "BINANCE_API_SECRET": "test_secret",
            "BYBIT_API_KEY": "test_key",
            "BYBIT_API_SECRET": "test_secret",
            "OANDA_API_KEY": "test_key",
            "OANDA_API_SECRET": "test_secret",
            "OANDA_ACCOUNT_ID": "test_account"
        }
        
        with patch.dict(os.environ, test_env):
            config_manager = ProductionConfigManager(Environment.TESTNET)
            
            # Test configuration loading
            assert config_manager.environment == Environment.TESTNET
            
            # Test validation
            for exchange_type in ExchangeType:
                if config_manager.is_exchange_enabled(exchange_type):
                    validation = config_manager.validate_configuration(exchange_type)
                    assert isinstance(validation, dict)
                    assert "valid" in validation
                    assert "errors" in validation
                    assert "warnings" in validation


class TestBinanceTestnetIntegration:
    """Test Binance testnet integration."""
    
    @pytest.mark.asyncio
    async def test_binance_testnet_connection(self, sandbox_config, skip_if_no_credentials):
        """Test Binance testnet WebSocket and REST connection."""
        if ExchangeType.BINANCE not in skip_if_no_credentials:
            pytest.skip("Binance testnet credentials not available")
        
        connector = BinanceConnector(sandbox_config.binance_testnet)
        
        try:
            # Test WebSocket connection
            logger.info("Testing Binance testnet WebSocket connection")
            success = await connector.connect_websocket()
            assert success, "Failed to connect to Binance testnet WebSocket"
            
            # Test subscription
            streams = ["btcusdt@trade", "btcusdt@depth5"]
            success = await connector.subscribe_to_streams(streams)
            assert success, "Failed to subscribe to Binance testnet streams"
            
            # Test REST API
            logger.info("Testing Binance testnet REST API")
            ping_data = await connector.fetch_rest_data("/api/v3/ping")
            assert ping_data is not None, "Binance testnet ping failed"
            
            # Test server time
            time_data = await connector.fetch_rest_data("/api/v3/time")
            assert "serverTime" in time_data, "Binance testnet time endpoint failed"
            
            # Test exchange info
            exchange_info = await connector.fetch_rest_data("/api/v3/exchangeInfo")
            assert "symbols" in exchange_info, "Binance testnet exchange info failed"
            
            # Test health status
            health = await connector.get_health_status()
            assert health["exchange"] == "binance"
            assert health["connected"] is True
            
        finally:
            # Cleanup
            await connector.disconnect_websocket()
    
    @pytest.mark.asyncio
    async def test_binance_testnet_rate_limiting(self, sandbox_config, skip_if_no_credentials):
        """Test Binance testnet rate limiting behavior."""
        if ExchangeType.BINANCE not in skip_if_no_credentials:
            pytest.skip("Binance testnet credentials not available")
        
        connector = BinanceConnector(sandbox_config.binance_testnet)
        
        try:
            # Test rate limiting with multiple requests
            logger.info("Testing Binance testnet rate limiting")
            
            start_time = time.time()
            request_times = []
            
            for i in range(RATE_LIMIT_TEST_REQUESTS):
                request_start = time.time()
                try:
                    await connector.fetch_rest_data("/api/v3/ping")
                    request_times.append(time.time() - request_start)
                except Exception as e:
                    logger.warning(f"Request {i} failed: {e}")
                    # Rate limit errors are expected in this test
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        logger.info(f"Rate limit hit at request {i}")
                        break
            
            total_time = time.time() - start_time
            
            # Verify rate limiting behavior
            assert len(request_times) > 0, "No successful requests made"
            
            # Calculate average request time
            avg_request_time = sum(request_times) / len(request_times)
            logger.info(f"Average request time: {avg_request_time:.3f}s")
            logger.info(f"Total test time: {total_time:.3f}s")
            
            # Rate limiting should introduce delays
            if len(request_times) == RATE_LIMIT_TEST_REQUESTS:
                # If all requests succeeded, they should have reasonable timing
                assert avg_request_time < 2.0, "Requests taking too long"
            
        finally:
            await connector.disconnect_websocket()
    
    @pytest.mark.asyncio
    async def test_binance_testnet_error_handling(self, sandbox_config, skip_if_no_credentials):
        """Test Binance testnet error handling."""
        if ExchangeType.BINANCE not in skip_if_no_credentials:
            pytest.skip("Binance testnet credentials not available")
        
        connector = BinanceConnector(sandbox_config.binance_testnet)
        
        try:
            # Test invalid endpoint
            logger.info("Testing Binance testnet error handling")
            
            with pytest.raises(Exception):
                await connector.fetch_rest_data("/api/v3/invalid_endpoint")
            
            # Test invalid parameters
            with pytest.raises(Exception):
                await connector.fetch_rest_data("/api/v3/ticker/24hr", {"symbol": "INVALID"})
            
            # Test data normalization errors
            with pytest.raises(Exception):
                await connector.normalize_data({}, "invalid_type")
            
        finally:
            await connector.disconnect_websocket()


class TestBybitTestnetIntegration:
    """Test Bybit testnet integration."""
    
    @pytest.mark.asyncio
    async def test_bybit_testnet_connection(self, sandbox_config, skip_if_no_credentials):
        """Test Bybit testnet WebSocket and REST connection."""
        if ExchangeType.BYBIT not in skip_if_no_credentials:
            pytest.skip("Bybit testnet credentials not available")
        
        connector = ByBitConnector(sandbox_config.bybit_testnet)
        
        try:
            # Test WebSocket connection
            logger.info("Testing Bybit testnet WebSocket connection")
            success = await connector.connect_websocket()
            assert success, "Failed to connect to Bybit testnet WebSocket"
            
            # Test subscription
            streams = ["publicTrade.BTCUSDT", "orderbook.1.BTCUSDT"]
            success = await connector.subscribe_to_streams(streams)
            assert success, "Failed to subscribe to Bybit testnet streams"
            
            # Test REST API
            logger.info("Testing Bybit testnet REST API")
            time_data = await connector.fetch_rest_data("/v5/market/time")
            assert "result" in time_data, "Bybit testnet time endpoint failed"
            
            # Test market data
            tickers_data = await connector.fetch_rest_data("/v5/market/tickers", {"category": "spot"})
            assert "result" in tickers_data, "Bybit testnet tickers endpoint failed"
            
            # Test health status
            health = await connector.get_health_status()
            assert health["exchange"] == "bybit"
            assert health["connected"] is True
            
        finally:
            await connector.disconnect_websocket()
    
    @pytest.mark.asyncio
    async def test_bybit_testnet_rate_limiting(self, sandbox_config, skip_if_no_credentials):
        """Test Bybit testnet rate limiting behavior."""
        if ExchangeType.BYBIT not in skip_if_no_credentials:
            pytest.skip("Bybit testnet credentials not available")
        
        connector = ByBitConnector(sandbox_config.bybit_testnet)
        
        try:
            # Test rate limiting with multiple requests
            logger.info("Testing Bybit testnet rate limiting")
            
            start_time = time.time()
            request_times = []
            
            for i in range(RATE_LIMIT_TEST_REQUESTS):
                request_start = time.time()
                try:
                    await connector.fetch_rest_data("/v5/market/time")
                    request_times.append(time.time() - request_start)
                except Exception as e:
                    logger.warning(f"Request {i} failed: {e}")
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        logger.info(f"Rate limit hit at request {i}")
                        break
            
            total_time = time.time() - start_time
            
            # Verify rate limiting behavior
            assert len(request_times) > 0, "No successful requests made"
            
            avg_request_time = sum(request_times) / len(request_times)
            logger.info(f"Average request time: {avg_request_time:.3f}s")
            logger.info(f"Total test time: {total_time:.3f}s")
            
        finally:
            await connector.disconnect_websocket()


class TestOandaPracticeIntegration:
    """Test Oanda practice account integration."""
    
    @pytest.mark.asyncio
    async def test_oanda_practice_connection(self, sandbox_config, skip_if_no_credentials):
        """Test Oanda practice WebSocket and REST connection."""
        if ExchangeType.OANDA not in skip_if_no_credentials:
            pytest.skip("Oanda practice credentials not available")
        
        # Format WebSocket URL with account ID
        config = sandbox_config.oanda_practice.copy()
        config["websocket_url"] = config["websocket_url"].format(
            account_id=config["account_id"]
        )
        
        connector = OANDAConnector(config)
        
        try:
            # Test WebSocket connection
            logger.info("Testing Oanda practice WebSocket connection")
            success = await connector.connect_websocket()
            assert success, "Failed to connect to Oanda practice WebSocket"
            
            # Test subscription
            instruments = ["EUR_USD", "GBP_USD"]
            success = await connector.subscribe_to_streams(instruments)
            assert success, "Failed to subscribe to Oanda practice streams"
            
            # Test REST API
            logger.info("Testing Oanda practice REST API")
            account_data = await connector.fetch_rest_data(f"/accounts/{config['account_id']}")
            assert "account" in account_data, "Oanda practice account endpoint failed"
            
            # Test instruments
            instruments_data = await connector.fetch_rest_data(f"/accounts/{config['account_id']}/instruments")
            assert "instruments" in instruments_data, "Oanda practice instruments endpoint failed"
            
            # Test health status
            health = await connector.get_health_status()
            assert health["exchange"] == "oanda"
            assert health["connected"] is True
            
        finally:
            await connector.disconnect_websocket()
    
    @pytest.mark.asyncio
    async def test_oanda_practice_rate_limiting(self, sandbox_config, skip_if_no_credentials):
        """Test Oanda practice rate limiting behavior."""
        if ExchangeType.OANDA not in skip_if_no_credentials:
            pytest.skip("Oanda practice credentials not available")
        
        config = sandbox_config.oanda_practice.copy()
        connector = OANDAConnector(config)
        
        try:
            # Test rate limiting with multiple requests
            logger.info("Testing Oanda practice rate limiting")
            
            start_time = time.time()
            request_times = []
            
            for i in range(RATE_LIMIT_TEST_REQUESTS):
                request_start = time.time()
                try:
                    await connector.fetch_rest_data(f"/accounts/{config['account_id']}")
                    request_times.append(time.time() - request_start)
                except Exception as e:
                    logger.warning(f"Request {i} failed: {e}")
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        logger.info(f"Rate limit hit at request {i}")
                        break
            
            total_time = time.time() - start_time
            
            # Verify rate limiting behavior
            assert len(request_times) > 0, "No successful requests made"
            
            avg_request_time = sum(request_times) / len(request_times)
            logger.info(f"Average request time: {avg_request_time:.3f}s")
            logger.info(f"Total test time: {total_time:.3f}s")
            
        finally:
            await connector.disconnect_websocket()


class TestErrorHandlingIntegration:
    """Test comprehensive error handling with real APIs."""
    
    @pytest.mark.asyncio
    async def test_error_handler_with_real_apis(self, sandbox_config, skip_if_no_credentials):
        """Test error handler with real API errors."""
        error_manager = ErrorHandlerManager()
        
        for exchange_type in skip_if_no_credentials:
            logger.info(f"Testing error handling for {exchange_type.value}")
            
            # Get appropriate config
            if exchange_type == ExchangeType.BINANCE:
                config = sandbox_config.binance_testnet
                connector_class = BinanceConnector
            elif exchange_type == ExchangeType.BYBIT:
                config = sandbox_config.bybit_testnet
                connector_class = ByBitConnector
            elif exchange_type == ExchangeType.OANDA:
                config = sandbox_config.oanda_practice.copy()
                if "account_id" in config:
                    config["websocket_url"] = config["websocket_url"].format(
                        account_id=config["account_id"]
                    )
                connector_class = OANDAConnector
            else:
                continue
            
            connector = connector_class(config)
            
            try:
                # Test invalid endpoint error
                try:
                    await connector.fetch_rest_data("/invalid/endpoint")
                except Exception as e:
                    error = await error_manager.handle_error(
                        e, exchange_type, "test_invalid_endpoint"
                    )
                    
                    assert isinstance(error, ExchangeError)
                    assert error.exchange_type == exchange_type
                    assert error.category in [ErrorCategory.API_ERROR, ErrorCategory.NETWORK]
                
                # Test rate limit handling (if we can trigger it)
                try:
                    # Make rapid requests to potentially trigger rate limit
                    for _ in range(20):
                        await connector.fetch_rest_data("/api/v3/ping" if exchange_type == ExchangeType.BINANCE else "/v5/market/time")
                except Exception as e:
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        error = await error_manager.handle_error(
                            e, exchange_type, "test_rate_limit"
                        )
                        
                        assert error.category == ErrorCategory.RATE_LIMIT
                        assert error.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
                
            finally:
                await connector.disconnect_websocket()
    
    @pytest.mark.asyncio
    async def test_execute_with_error_handling(self, sandbox_config, skip_if_no_credentials):
        """Test execute_with_error_handling function with real APIs."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available for error handling test")
        
        exchange_type = skip_if_no_credentials[0]  # Use first available exchange
        
        # Get appropriate config
        if exchange_type == ExchangeType.BINANCE:
            config = sandbox_config.binance_testnet
            connector_class = BinanceConnector
            valid_endpoint = "/api/v3/ping"
            invalid_endpoint = "/api/v3/invalid"
        elif exchange_type == ExchangeType.BYBIT:
            config = sandbox_config.bybit_testnet
            connector_class = ByBitConnector
            valid_endpoint = "/v5/market/time"
            invalid_endpoint = "/v5/invalid"
        else:
            pytest.skip(f"Error handling test not implemented for {exchange_type.value}")
        
        connector = connector_class(config)
        
        try:
            # Test successful execution
            async def successful_operation():
                return await connector.fetch_rest_data(valid_endpoint)
            
            result = await execute_with_error_handling(
                successful_operation,
                exchange_type,
                "test_successful_operation",
                max_retries=2
            )
            
            assert result is not None
            
            # Test failed operation with retries
            async def failing_operation():
                return await connector.fetch_rest_data(invalid_endpoint)
            
            with pytest.raises(Exception):
                await execute_with_error_handling(
                    failing_operation,
                    exchange_type,
                    "test_failing_operation",
                    max_retries=2
                )
            
        finally:
            await connector.disconnect_websocket()


class TestRateLimitingIntegration:
    """Test rate limiting integration with real APIs."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_real_apis(self, sandbox_config, skip_if_no_credentials):
        """Test rate limiter with real API calls."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available for rate limiting test")
        
        rate_manager = RateLimitManager()
        
        for exchange_type in skip_if_no_credentials:
            logger.info(f"Testing rate limiting for {exchange_type.value}")
            
            # Configure rate limiter
            if exchange_type == ExchangeType.BINANCE:
                rate_config = RateLimitConfig(
                    requests_per_minute=60,  # Conservative for testing
                    requests_per_second=2,
                    burst_limit=5
                )
            else:
                rate_config = RateLimitConfig(
                    requests_per_minute=60,
                    requests_per_second=2,
                    burst_limit=5
                )
            
            rate_manager.add_exchange(exchange_type, rate_config)
            
            # Test permit acquisition
            start_time = time.time()
            successful_requests = 0
            
            for i in range(10):
                permit_acquired = await rate_manager.acquire_permit(
                    exchange_type,
                    f"test_endpoint_{i}",
                    weight=1,
                    priority=RequestPriority.NORMAL,
                    timeout=5.0
                )
                
                if permit_acquired:
                    successful_requests += 1
                    logger.debug(f"Permit {i} acquired")
                else:
                    logger.warning(f"Permit {i} denied")
            
            total_time = time.time() - start_time
            
            # Verify rate limiting worked
            assert successful_requests > 0, "No permits were acquired"
            logger.info(f"Acquired {successful_requests}/10 permits in {total_time:.2f}s")
            
            # Get status
            status = rate_manager.get_exchange_status(exchange_type)
            assert status is not None
            assert status["exchange"] == exchange_type.value
            
        # Cleanup
        rate_manager.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_rate_limited_decorator(self, sandbox_config, skip_if_no_credentials):
        """Test rate_limited decorator with real API calls."""
        if ExchangeType.BINANCE not in skip_if_no_credentials:
            pytest.skip("Binance testnet credentials not available")
        
        rate_manager = RateLimitManager()
        rate_config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_second=1,
            burst_limit=3
        )
        rate_manager.add_exchange(ExchangeType.BINANCE, rate_config)
        
        connector = BinanceConnector(sandbox_config.binance_testnet)
        
        @rate_limited(
            ExchangeType.BINANCE,
            "/api/v3/ping",
            weight=1,
            priority=RequestPriority.NORMAL,
            timeout=10.0
        )
        async def rate_limited_ping():
            return await connector.fetch_rest_data("/api/v3/ping")
        
        try:
            # Test decorated function
            start_time = time.time()
            
            for i in range(5):
                result = await rate_limited_ping()
                assert result is not None
                logger.debug(f"Rate limited request {i} completed")
            
            total_time = time.time() - start_time
            logger.info(f"Completed 5 rate limited requests in {total_time:.2f}s")
            
            # Should take at least 4 seconds due to rate limiting (1 req/sec after burst)
            assert total_time >= 2.0, "Rate limiting not working properly"
            
        finally:
            await connector.disconnect_websocket()
            rate_manager.stop_monitoring()


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with real APIs."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_real_connectors(self, sandbox_config, skip_if_no_credentials):
        """Test circuit breaker with real exchange connectors."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available for circuit breaker test")
        
        # Create mock exchange connectors dict for circuit breaker
        exchange_connectors = {}
        
        for exchange_type in skip_if_no_credentials:
            if exchange_type == ExchangeType.BINANCE:
                config = sandbox_config.binance_testnet
                connector = BinanceConnector(config)
            elif exchange_type == ExchangeType.BYBIT:
                config = sandbox_config.bybit_testnet
                connector = ByBitConnector(config)
            elif exchange_type == ExchangeType.OANDA:
                config = sandbox_config.oanda_practice.copy()
                if "account_id" in config:
                    config["websocket_url"] = config["websocket_url"].format(
                        account_id=config["account_id"]
                    )
                connector = OANDAConnector(config)
            else:
                continue
            
            exchange_connectors[exchange_type.value] = connector
        
        # Circuit breaker configuration
        cb_config = {
            'max_drawdown': 0.05,  # 5% max drawdown
            'max_var': 0.03,       # 3% max VaR
            'max_correlation': 0.8, # 80% max correlation
            'recovery_timeout': 60,  # 1 minute recovery
            'check_interval': 10,    # 10 second checks
            'notifications': {
                'recipients': {
                    'email': ['test@example.com'],
                    'slack': ['#test-alerts']
                }
            }
        }
        
        circuit_breaker = CircuitBreaker(cb_config, exchange_connectors)
        
        try:
            # Test normal operation
            portfolio_data = {
                'drawdown': 0.02,  # 2% drawdown - within limits
                'portfolio_data': {
                    'returns': [0.01, -0.005, 0.008, -0.003, 0.012],
                    'positions': {
                        'BTCUSDT': {'size': 1.0, 'value': 50000},
                        'ETHUSDT': {'size': 10.0, 'value': 30000}
                    }
                }
            }
            
            # Should pass risk checks
            result = await circuit_breaker.check_risk_limits(portfolio_data)
            assert result is True, "Risk limits should pass with normal data"
            assert circuit_breaker.is_closed(), "Circuit breaker should be closed"
            
            # Test circuit breaker trigger
            high_risk_data = {
                'drawdown': 0.08,  # 8% drawdown - exceeds 5% limit
                'portfolio_data': portfolio_data['portfolio_data']
            }
            
            # Should trigger circuit breaker
            result = await circuit_breaker.check_risk_limits(high_risk_data)
            assert result is False, "Risk limits should fail with high risk data"
            assert circuit_breaker.is_open(), "Circuit breaker should be open"
            
            # Test status reporting
            status = await circuit_breaker.get_circuit_breaker_status()
            assert status["state"] == CircuitBreakerState.OPEN.value
            assert status["trigger_time"] is not None
            
        finally:
            # Cleanup
            await circuit_breaker.close()
            for connector in exchange_connectors.values():
                try:
                    await connector.disconnect_websocket()
                except:
                    pass


class TestFailoverIntegration:
    """Test failover mechanism integration with real APIs."""
    
    @pytest.mark.asyncio
    async def test_failover_with_real_connectors(self, sandbox_config, skip_if_no_credentials):
        """Test failover mechanism with real exchange connectors."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        failover_manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Add available exchanges
        connectors = {}
        for i, exchange_type in enumerate(skip_if_no_credentials[:2]):  # Use first 2 exchanges
            if exchange_type == ExchangeType.BINANCE:
                config = sandbox_config.binance_testnet
                connector = BinanceConnector(config)
            elif exchange_type == ExchangeType.BYBIT:
                config = sandbox_config.bybit_testnet
                connector = ByBitConnector(config)
            elif exchange_type == ExchangeType.OANDA:
                config = sandbox_config.oanda_practice.copy()
                if "account_id" in config:
                    config["websocket_url"] = config["websocket_url"].format(
                        account_id=config["account_id"]
                    )
                connector = OANDAConnector(config)
            else:
                continue
            
            connectors[exchange_type] = connector
            failover_manager.add_exchange(exchange_type, connector, priority=i+1)
        
        try:
            # Start monitoring
            await failover_manager.start_monitoring()
            
            # Wait for initial health checks
            await asyncio.sleep(2)
            
            # Test health status
            for exchange_type in connectors.keys():
                metrics = failover_manager.health_metrics[exchange_type]
                logger.info(f"{exchange_type.value} health score: {metrics.get_health_score():.1f}")
            
            # Test manual failover
            primary_exchange = failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in connectors.keys() if ex != primary_exchange]
            
            if secondary_exchanges:
                target_exchange = secondary_exchanges[0]
                logger.info(f"Testing manual failover: {primary_exchange.value} -> {target_exchange.value}")
                
                # Mock the failover execution for testing
                with patch.object(failover_manager, '_execute_failover', return_value=True):
                    success = await failover_manager.manual_failover(target_exchange)
                    assert success, "Manual failover should succeed"
                    assert failover_manager.active_exchange == target_exchange
                    assert failover_manager.current_state == FailoverState.FAILED_OVER
            
            # Test status reporting
            status = failover_manager.get_status()
            assert status["environment"] == Environment.TESTNET.value
            assert len(status["exchange_health"]) >= 2
            
        finally:
            # Cleanup
            await failover_manager.stop_monitoring()
            for connector in connectors.values():
                try:
                    await connector.disconnect_websocket()
                except:
                    pass


class TestProductionFactoryIntegration:
    """Test production factory integration with sandbox environments."""
    
    @pytest.mark.asyncio
    async def test_production_factory_testnet(self, sandbox_config, skip_if_no_credentials):
        """Test production factory with testnet environment."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available for factory test")
        
        # Set up environment variables for testing
        test_env = {}
        
        if ExchangeType.BINANCE in skip_if_no_credentials:
            test_env.update({
                "BINANCE_API_KEY": sandbox_config.binance_testnet["api_key"],
                "BINANCE_API_SECRET": sandbox_config.binance_testnet["api_secret"]
            })
        
        if ExchangeType.BYBIT in skip_if_no_credentials:
            test_env.update({
                "BYBIT_API_KEY": sandbox_config.bybit_testnet["api_key"],
                "BYBIT_API_SECRET": sandbox_config.bybit_testnet["api_secret"]
            })
        
        if ExchangeType.OANDA in skip_if_no_credentials:
            test_env.update({
                "OANDA_API_KEY": sandbox_config.oanda_practice["api_key"],
                "OANDA_API_SECRET": sandbox_config.oanda_practice["api_secret"],
                "OANDA_ACCOUNT_ID": sandbox_config.oanda_practice["account_id"]
            })
        
        with patch.dict(os.environ, test_env):
            factory = ProductionExchangeFactory(Environment.TESTNET)
            
            try:
                # Test connector creation
                created_connectors = factory.create_all_connectors()
                assert len(created_connectors) > 0, "No connectors were created"
                
                # Test connection testing
                connection_results = await test_exchange_connections(Environment.TESTNET)
                
                for exchange_name, result in connection_results.items():
                    logger.info(f"{exchange_name} connection test: {result}")
                    assert isinstance(result, dict)
                    assert "connected" in result
                    assert "environment" in result
                    assert result["environment"] == Environment.TESTNET.value
                
                # Test managed connectors context
                async with factory.managed_connectors() as connectors:
                    assert len(connectors) > 0, "No active connectors in context"
                    
                    # Test health status for each connector
                    for exchange_type, connector in connectors.items():
                        health = await connector.get_health_status()
                        assert health["exchange"] == exchange_type.value
                        logger.info(f"{exchange_type.value} health: {health}")
                
            finally:
                # Cleanup
                await factory.stop_all_connectors()


# Integration test runner
if __name__ == "__main__":
    # Configure logging for integration tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-k", "not test_failover_with_real_connectors"  # Skip heavy tests by default
    ])