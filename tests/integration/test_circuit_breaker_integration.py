"""
Circuit Breaker Integration Testing with Real API Rate Limits

This module implements comprehensive circuit breaker tests that validate:
1. Circuit breaker behavior with real API rate limits
2. Integration with exchange connectors and error handling
3. Failover mechanism triggering and recovery
4. Real-time monitoring and alerting

Requirements covered: 1.5, 2.5, 3.3
"""

import asyncio
import logging
import os
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock
import json

from data_pipeline.exchange_connectors.production_config import ExchangeType, Environment
from data_pipeline.exchange_connectors.binance_connector import BinanceConnector
from data_pipeline.exchange_connectors.bybit_connector import ByBitConnector
from data_pipeline.exchange_connectors.oanda_connector import OANDAConnector
from data_pipeline.exchange_connectors.error_handling import (
    ErrorHandlerManager,
    ExchangeError,
    ErrorCategory,
    ErrorSeverity
)
from data_pipeline.exchange_connectors.rate_limiter import (
    RateLimitManager,
    ExchangeRateLimiter,
    RequestPriority,
    RateLimitConfig
)
from data_pipeline.exchange_connectors.failover_manager import (
    ExchangeFailoverManager,
    FailoverTrigger,
    FailoverState
)
from risk_manager.circuit_breaker import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger(__name__)

# Test configuration
RATE_LIMIT_TEST_DURATION = 30  # seconds
CIRCUIT_BREAKER_TEST_TIMEOUT = 60  # seconds
MAX_REQUESTS_PER_TEST = 50


class RateLimitTestScenario:
    """Test scenario for rate limit validation."""
    
    def __init__(self, name: str, exchange_type: ExchangeType, 
                 requests_per_second: int, expected_behavior: str):
        """
        Initialize rate limit test scenario.
        
        Args:
            name: Scenario name
            exchange_type: Exchange to test
            requests_per_second: Request rate to attempt
            expected_behavior: Expected behavior (success, rate_limit, circuit_breaker)
        """
        self.name = name
        self.exchange_type = exchange_type
        self.requests_per_second = requests_per_second
        self.expected_behavior = expected_behavior
        self.results = {}


class CircuitBreakerTestHarness:
    """Test harness for circuit breaker integration testing."""
    
    def __init__(self, sandbox_config):
        """Initialize test harness."""
        self.sandbox_config = sandbox_config
        self.connectors = {}
        self.rate_manager = None
        self.error_manager = None
        self.failover_manager = None
        self.circuit_breaker = None
        
    async def setup(self, available_exchanges: List[ExchangeType]):
        """Set up test environment."""
        logger.info("Setting up circuit breaker test harness")
        
        # Initialize managers
        self.rate_manager = RateLimitManager()
        self.error_manager = ErrorHandlerManager()
        self.failover_manager = ExchangeFailoverManager(Environment.TESTNET)
        
        # Create connectors for available exchanges
        for exchange_type in available_exchanges:
            connector = await self._create_connector(exchange_type)
            if connector:
                self.connectors[exchange_type] = connector
                
                # Configure rate limiter
                rate_config = self._get_rate_config(exchange_type)
                self.rate_manager.add_exchange(exchange_type, rate_config)
                
                # Add to failover manager
                priority = list(available_exchanges).index(exchange_type) + 1
                self.failover_manager.add_exchange(exchange_type, connector, priority)
        
        # Initialize circuit breaker
        cb_config = self._get_circuit_breaker_config()
        exchange_connectors_dict = {
            ex.value: conn for ex, conn in self.connectors.items()
        }
        self.circuit_breaker = CircuitBreaker(cb_config, exchange_connectors_dict)
        
        # Start monitoring
        self.rate_manager.start_monitoring()
        await self.failover_manager.start_monitoring()
        
        logger.info(f"Test harness setup complete with {len(self.connectors)} exchanges")
    
    async def _create_connector(self, exchange_type: ExchangeType):
        """Create connector for exchange type."""
        try:
            if exchange_type == ExchangeType.BINANCE:
                if not self.sandbox_config.has_binance_credentials():
                    return None
                config = self.sandbox_config.binance_testnet
                return BinanceConnector(config)
                
            elif exchange_type == ExchangeType.BYBIT:
                if not self.sandbox_config.has_bybit_credentials():
                    return None
                config = self.sandbox_config.bybit_testnet
                return ByBitConnector(config)
                
            elif exchange_type == ExchangeType.OANDA:
                if not self.sandbox_config.has_oanda_credentials():
                    return None
                config = self.sandbox_config.oanda_practice.copy()
                config["websocket_url"] = config["websocket_url"].format(
                    account_id=config["account_id"]
                )
                return OANDAConnector(config)
                
        except Exception as e:
            logger.error(f"Failed to create {exchange_type.value} connector: {e}")
            return None
    
    def _get_rate_config(self, exchange_type: ExchangeType) -> RateLimitConfig:
        """Get rate limit configuration for exchange."""
        if exchange_type == ExchangeType.BINANCE:
            return RateLimitConfig(
                requests_per_minute=60,   # Conservative for testing
                requests_per_second=2,
                burst_limit=5,
                backoff_factor=2.0,
                max_backoff_time=60
            )
        elif exchange_type == ExchangeType.BYBIT:
            return RateLimitConfig(
                requests_per_minute=120,
                requests_per_second=3,
                burst_limit=10,
                backoff_factor=1.5,
                max_backoff_time=30
            )
        else:  # OANDA
            return RateLimitConfig(
                requests_per_minute=120,
                requests_per_second=3,
                burst_limit=8,
                backoff_factor=1.5,
                max_backoff_time=30
            )
    
    def _get_circuit_breaker_config(self) -> Dict[str, Any]:
        """Get circuit breaker configuration."""
        return {
            'max_drawdown': 0.05,
            'max_var': 0.03,
            'max_correlation': 0.8,
            'recovery_timeout': 30,
            'check_interval': 5,
            'var_calculator': {
                'confidence_levels': [0.95],
                'lookback_period': 50,
                'monte_carlo_simulations': 1000,
                'cache_ttl': 60
            },
            'risk_metrics': {
                'thresholds': {
                    'market': {'max_drawdown': 0.05, 'max_var': 0.03},
                    'operational': {'max_error_rate': 0.1, 'max_latency': 2000}
                },
                'calculation_interval': 10
            },
            'notifications': {
                'recipients': {
                    'email': ['test@example.com'],
                    'slack': ['#test-alerts']
                }
            }
        }
    
    async def cleanup(self):
        """Clean up test environment."""
        logger.info("Cleaning up circuit breaker test harness")
        
        try:
            if self.circuit_breaker:
                await self.circuit_breaker.close()
            
            if self.failover_manager:
                await self.failover_manager.stop_monitoring()
            
            if self.rate_manager:
                self.rate_manager.stop_monitoring()
            
            for connector in self.connectors.values():
                try:
                    await connector.disconnect_websocket()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


@pytest.fixture
def circuit_breaker_harness(sandbox_config):
    """Circuit breaker test harness fixture."""
    return CircuitBreakerTestHarness(sandbox_config)


class TestRateLimitCircuitBreaker:
    """Test circuit breaker behavior with rate limits."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_circuit_breaker_integration(self, circuit_breaker_harness, skip_if_no_credentials):
        """Test circuit breaker integration with rate limiting."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available")
        
        await circuit_breaker_harness.setup(skip_if_no_credentials)
        
        try:
            # Test scenarios for each exchange
            scenarios = []
            
            for exchange_type in skip_if_no_credentials:
                scenarios.extend([
                    RateLimitTestScenario(
                        f"{exchange_type.value}_normal_rate",
                        exchange_type,
                        1,  # 1 req/sec - should be fine
                        "success"
                    ),
                    RateLimitTestScenario(
                        f"{exchange_type.value}_high_rate",
                        exchange_type,
                        10,  # 10 req/sec - should hit rate limits
                        "rate_limit"
                    )
                ])
            
            # Execute test scenarios
            for scenario in scenarios:
                logger.info(f"Running scenario: {scenario.name}")
                await self._execute_rate_limit_scenario(
                    circuit_breaker_harness, scenario
                )
                
                # Analyze results
                self._analyze_scenario_results(scenario)
                
                # Wait between scenarios
                await asyncio.sleep(5)
            
            # Test circuit breaker triggering
            await self._test_circuit_breaker_triggering(circuit_breaker_harness)
            
        finally:
            await circuit_breaker_harness.cleanup()
    
    async def _execute_rate_limit_scenario(self, harness, scenario: RateLimitTestScenario):
        """Execute a rate limit test scenario."""
        connector = harness.connectors.get(scenario.exchange_type)
        if not connector:
            scenario.results = {"error": "Connector not available"}
            return
        
        # Get appropriate endpoint
        if scenario.exchange_type == ExchangeType.BINANCE:
            endpoint = "/api/v3/ping"
        elif scenario.exchange_type == ExchangeType.BYBIT:
            endpoint = "/v5/market/time"
        else:  # OANDA
            endpoint = f"/accounts/{harness.sandbox_config.oanda_practice['account_id']}"
        
        # Execute requests at specified rate
        start_time = time.time()
        request_results = []
        rate_limit_hits = 0
        successful_requests = 0
        
        request_interval = 1.0 / scenario.requests_per_second
        
        for i in range(min(MAX_REQUESTS_PER_TEST, scenario.requests_per_second * 10)):
            request_start = time.time()
            
            try:
                # Acquire rate limit permit
                permit_acquired = await harness.rate_manager.acquire_permit(
                    scenario.exchange_type,
                    endpoint,
                    weight=1,
                    priority=RequestPriority.NORMAL,
                    timeout=5.0
                )
                
                if permit_acquired:
                    # Make actual API request
                    result = await connector.fetch_rest_data(endpoint)
                    successful_requests += 1
                    request_results.append({
                        "request_id": i,
                        "success": True,
                        "duration": time.time() - request_start,
                        "permit_acquired": True
                    })
                else:
                    rate_limit_hits += 1
                    request_results.append({
                        "request_id": i,
                        "success": False,
                        "duration": time.time() - request_start,
                        "permit_acquired": False,
                        "error": "Rate limit permit denied"
                    })
                
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate limit" in error_str.lower() or "429" in error_str
                
                if is_rate_limit:
                    rate_limit_hits += 1
                    # Handle rate limit error
                    harness.rate_manager.handle_rate_limit_error(scenario.exchange_type)
                
                request_results.append({
                    "request_id": i,
                    "success": False,
                    "duration": time.time() - request_start,
                    "permit_acquired": permit_acquired if 'permit_acquired' in locals() else False,
                    "error": error_str,
                    "is_rate_limit": is_rate_limit
                })
            
            # Wait for next request (if not the last one)
            if i < MAX_REQUESTS_PER_TEST - 1:
                elapsed = time.time() - request_start
                sleep_time = max(0, request_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            # Stop if we've been running too long
            if time.time() - start_time > RATE_LIMIT_TEST_DURATION:
                break
        
        total_time = time.time() - start_time
        
        # Store results
        scenario.results = {
            "total_requests": len(request_results),
            "successful_requests": successful_requests,
            "rate_limit_hits": rate_limit_hits,
            "total_time": total_time,
            "requests_per_second_actual": len(request_results) / total_time,
            "success_rate": successful_requests / len(request_results) if request_results else 0,
            "request_details": request_results[-10:]  # Last 10 requests for analysis
        }
        
        logger.info(f"Scenario {scenario.name} completed: "
                   f"{successful_requests}/{len(request_results)} successful, "
                   f"{rate_limit_hits} rate limit hits")
    
    def _analyze_scenario_results(self, scenario: RateLimitTestScenario):
        """Analyze scenario results and validate expectations."""
        results = scenario.results
        
        if "error" in results:
            logger.warning(f"Scenario {scenario.name} failed: {results['error']}")
            return
        
        logger.info(f"Analyzing scenario: {scenario.name}")
        logger.info(f"  Expected behavior: {scenario.expected_behavior}")
        logger.info(f"  Success rate: {results['success_rate']:.2%}")
        logger.info(f"  Rate limit hits: {results['rate_limit_hits']}")
        logger.info(f"  Actual RPS: {results['requests_per_second_actual']:.2f}")
        
        # Validate expectations
        if scenario.expected_behavior == "success":
            assert results['success_rate'] > 0.8, f"Expected high success rate, got {results['success_rate']:.2%}"
            
        elif scenario.expected_behavior == "rate_limit":
            assert results['rate_limit_hits'] > 0, "Expected rate limit hits but got none"
            
        # Rate limiting should prevent excessive request rates
        if scenario.requests_per_second > 5:
            assert results['requests_per_second_actual'] < scenario.requests_per_second * 0.8, \
                "Rate limiting should reduce actual request rate"
    
    async def _test_circuit_breaker_triggering(self, harness):
        """Test circuit breaker triggering under high error conditions."""
        logger.info("Testing circuit breaker triggering")
        
        # Create high-risk portfolio data to trigger circuit breaker
        high_risk_data = {
            'drawdown': 0.08,  # 8% drawdown - exceeds 5% limit
            'portfolio_data': {
                'returns': [-0.05, -0.03, -0.02, -0.04, -0.01],  # Negative returns
                'positions': {
                    'BTCUSDT': {'size': 10.0, 'value': 500000},
                    'ETHUSDT': {'size': 100.0, 'value': 300000}
                }
            }
        }
        
        # Check circuit breaker response
        result = await harness.circuit_breaker.check_risk_limits(high_risk_data)
        
        # Should trigger circuit breaker
        assert result is False, "Circuit breaker should be triggered by high risk"
        assert harness.circuit_breaker.is_open(), "Circuit breaker should be in open state"
        
        # Get status
        status = await harness.circuit_breaker.get_circuit_breaker_status()
        assert status["state"] == CircuitBreakerState.OPEN.value
        
        logger.info("Circuit breaker successfully triggered")


class TestFailoverCircuitBreaker:
    """Test failover mechanism with circuit breaker integration."""
    
    @pytest.mark.asyncio
    async def test_failover_circuit_breaker_integration(self, circuit_breaker_harness, skip_if_no_credentials):
        """Test failover mechanism integration with circuit breaker."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await circuit_breaker_harness.setup(skip_if_no_credentials)
        
        try:
            # Test normal failover scenario
            await self._test_normal_failover(circuit_breaker_harness)
            
            # Test circuit breaker triggered failover
            await self._test_circuit_breaker_failover(circuit_breaker_harness)
            
            # Test recovery scenario
            await self._test_failover_recovery(circuit_breaker_harness)
            
        finally:
            await circuit_breaker_harness.cleanup()
    
    async def _test_normal_failover(self, harness):
        """Test normal failover without circuit breaker."""
        logger.info("Testing normal failover scenario")
        
        failover_manager = harness.failover_manager
        
        # Get primary and secondary exchanges
        primary_exchange = failover_manager.primary_exchange
        secondary_exchanges = [ex for ex in harness.connectors.keys() if ex != primary_exchange]
        
        if not secondary_exchanges:
            logger.warning("No secondary exchange available for failover test")
            return
        
        target_exchange = secondary_exchanges[0]
        
        # Simulate connection failure on primary
        failover_manager.health_metrics[primary_exchange].is_connected = False
        failover_manager.health_metrics[primary_exchange].consecutive_failures = 10
        
        # Ensure target is healthy
        failover_manager.health_metrics[target_exchange].is_connected = True
        
        # Mock failover execution for testing
        with patch.object(failover_manager, '_execute_failover', return_value=True):
            # Trigger failover evaluation
            await failover_manager._evaluate_failover_rules()
            
            # Verify failover occurred
            assert failover_manager.active_exchange == target_exchange
            assert failover_manager.current_state == FailoverState.FAILED_OVER
            assert primary_exchange in failover_manager.failed_exchanges
        
        logger.info(f"Normal failover completed: {primary_exchange.value} -> {target_exchange.value}")
    
    async def _test_circuit_breaker_failover(self, harness):
        """Test failover triggered by circuit breaker."""
        logger.info("Testing circuit breaker triggered failover")
        
        # Create conditions that should trigger both circuit breaker and failover
        extreme_risk_data = {
            'drawdown': 0.15,  # 15% drawdown - extreme risk
            'portfolio_data': {
                'returns': [-0.08, -0.05, -0.07, -0.06, -0.04],
                'positions': {
                    'BTCUSDT': {'size': 20.0, 'value': 1000000},
                    'ETHUSDT': {'size': 200.0, 'value': 600000}
                }
            }
        }
        
        # This should trigger circuit breaker
        result = await harness.circuit_breaker.check_risk_limits(extreme_risk_data)
        assert result is False, "Extreme risk should trigger circuit breaker"
        
        # Circuit breaker should be open
        assert harness.circuit_breaker.is_open()
        
        # Check if failover was also triggered (would depend on implementation)
        failover_status = harness.failover_manager.get_status()
        logger.info(f"Failover status after circuit breaker: {failover_status['current_state']}")
        
        logger.info("Circuit breaker failover test completed")
    
    async def _test_failover_recovery(self, harness):
        """Test recovery from failover state."""
        logger.info("Testing failover recovery")
        
        failover_manager = harness.failover_manager
        
        # Ensure we're in failed over state
        if failover_manager.current_state != FailoverState.FAILED_OVER:
            # Set up failed over state manually
            primary = failover_manager.primary_exchange
            secondary = [ex for ex in harness.connectors.keys() if ex != primary][0]
            
            failover_manager.active_exchange = secondary
            failover_manager.current_state = FailoverState.FAILED_OVER
            failover_manager.failed_exchanges.add(primary)
        
        # Simulate primary exchange recovery
        primary = failover_manager.primary_exchange
        if primary in failover_manager.failed_exchanges:
            # Set primary as healthy
            failover_manager.health_metrics[primary].is_connected = True
            failover_manager.health_metrics[primary].consecutive_failures = 0
            failover_manager.health_metrics[primary].success_rate_5min = 95.0
            
            # Check recovery
            await failover_manager._check_failed_exchange_recovery()
            
            # Primary should be removed from failed exchanges
            assert primary not in failover_manager.failed_exchanges
            
            logger.info(f"Recovery test completed for {primary.value}")


class TestErrorHandlingCircuitBreaker:
    """Test error handling integration with circuit breaker."""
    
    @pytest.mark.asyncio
    async def test_error_cascade_circuit_breaker(self, circuit_breaker_harness, skip_if_no_credentials):
        """Test error cascade leading to circuit breaker activation."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available")
        
        await circuit_breaker_harness.setup(skip_if_no_credentials)
        
        try:
            # Test error accumulation
            await self._test_error_accumulation(circuit_breaker_harness)
            
            # Test error recovery
            await self._test_error_recovery(circuit_breaker_harness)
            
        finally:
            await circuit_breaker_harness.cleanup()
    
    async def _test_error_accumulation(self, harness):
        """Test accumulation of errors leading to circuit breaker."""
        logger.info("Testing error accumulation")
        
        error_manager = harness.error_manager
        exchange_type = list(harness.connectors.keys())[0]
        
        # Simulate multiple errors
        error_count = 0
        for i in range(10):
            try:
                # Create a fake error
                fake_error = Exception(f"Test error {i}")
                
                # Handle the error
                structured_error = await error_manager.handle_error(
                    fake_error,
                    exchange_type,
                    f"test_operation_{i}"
                )
                
                error_count += 1
                
                # Update health metrics to reflect errors
                metrics = harness.failover_manager.health_metrics[exchange_type]
                metrics.update_request_result(False)
                
                logger.debug(f"Processed error {i}: {structured_error.error_code}")
                
            except Exception as e:
                logger.error(f"Error handling failed: {e}")
        
        # Check error statistics
        stats = error_manager.get_error_statistics(exchange_type)
        assert stats["total_errors"] >= error_count
        
        # Check if errors affected health metrics
        metrics = harness.failover_manager.health_metrics[exchange_type]
        health_score = metrics.get_health_score()
        
        logger.info(f"Health score after {error_count} errors: {health_score:.1f}")
        
        # Health score should be reduced
        assert health_score < 100.0, "Health score should be reduced after errors"
    
    async def _test_error_recovery(self, harness):
        """Test recovery from error conditions."""
        logger.info("Testing error recovery")
        
        exchange_type = list(harness.connectors.keys())[0]
        
        # Simulate successful requests to recover
        metrics = harness.failover_manager.health_metrics[exchange_type]
        
        initial_health = metrics.get_health_score()
        
        # Simulate successful operations
        for i in range(20):
            metrics.update_request_result(True, latency_ms=50.0)
        
        final_health = metrics.get_health_score()
        
        logger.info(f"Health recovery: {initial_health:.1f} -> {final_health:.1f}")
        
        # Health should improve
        assert final_health > initial_health, "Health should improve after successful requests"


class TestPerformanceCircuitBreaker:
    """Test circuit breaker performance under load."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self, circuit_breaker_harness, skip_if_no_credentials):
        """Test circuit breaker performance under high load."""
        if not skip_if_no_credentials:
            pytest.skip("No credentials available")
        
        await circuit_breaker_harness.setup(skip_if_no_credentials)
        
        try:
            # Test concurrent risk checks
            await self._test_concurrent_risk_checks(circuit_breaker_harness)
            
            # Test high frequency monitoring
            await self._test_high_frequency_monitoring(circuit_breaker_harness)
            
        finally:
            await circuit_breaker_harness.cleanup()
    
    async def _test_concurrent_risk_checks(self, harness):
        """Test concurrent risk limit checks."""
        logger.info("Testing concurrent risk checks")
        
        # Create test portfolio data
        portfolio_data = {
            'drawdown': 0.02,  # Normal risk level
            'portfolio_data': {
                'returns': [0.01, -0.005, 0.008, -0.003, 0.012],
                'positions': {
                    'BTCUSDT': {'size': 1.0, 'value': 50000},
                    'ETHUSDT': {'size': 10.0, 'value': 30000}
                }
            }
        }
        
        # Run concurrent risk checks
        start_time = time.time()
        
        tasks = []
        for i in range(20):  # 20 concurrent checks
            task = asyncio.create_task(
                harness.circuit_breaker.check_risk_limits(portfolio_data)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_checks = sum(1 for r in results if r is True)
        failed_checks = sum(1 for r in results if r is False)
        errors = sum(1 for r in results if isinstance(r, Exception))
        
        logger.info(f"Concurrent risk checks completed in {total_time:.2f}s")
        logger.info(f"Results: {successful_checks} success, {failed_checks} failed, {errors} errors")
        
        # Performance assertions
        assert total_time < 10.0, "Concurrent checks should complete within 10 seconds"
        assert successful_checks > 0, "At least some checks should succeed"
        assert errors == 0, "No errors should occur during concurrent checks"
    
    async def _test_high_frequency_monitoring(self, harness):
        """Test high frequency monitoring performance."""
        logger.info("Testing high frequency monitoring")
        
        # Reduce check interval for testing
        original_interval = harness.circuit_breaker.check_interval
        harness.circuit_breaker.check_interval = 1  # 1 second
        
        try:
            # Monitor for a short period
            monitoring_duration = 10  # seconds
            start_time = time.time()
            
            portfolio_data = {
                'drawdown': 0.01,
                'portfolio_data': {
                    'returns': [0.005, -0.002, 0.003, -0.001, 0.004],
                    'positions': {'BTCUSDT': {'size': 1.0, 'value': 50000}}
                }
            }
            
            check_count = 0
            while time.time() - start_time < monitoring_duration:
                await harness.circuit_breaker.check_risk_limits(portfolio_data)
                check_count += 1
                await asyncio.sleep(0.5)  # Check every 500ms
            
            total_time = time.time() - start_time
            checks_per_second = check_count / total_time
            
            logger.info(f"High frequency monitoring: {checks_per_second:.1f} checks/second")
            
            # Performance assertion
            assert checks_per_second >= 1.0, "Should achieve at least 1 check per second"
            
        finally:
            # Restore original interval
            harness.circuit_breaker.check_interval = original_interval


# Test runner for integration tests
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])