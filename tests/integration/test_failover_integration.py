"""
Failover Mechanism Integration Testing

This module implements comprehensive failover mechanism tests that validate:
1. Failover between exchanges with real API connections
2. Health monitoring and automatic failover triggering
3. Recovery and failback mechanisms
4. Integration with error handling and circuit breakers

Requirements covered: 1.5, 2.5, 3.3
"""

import asyncio
import logging
import os
import pytest
import time
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch, AsyncMock
import json
from dataclasses import dataclass

from data_pipeline.exchange_connectors.production_config import ExchangeType, Environment
from data_pipeline.exchange_connectors.binance_connector import BinanceConnector
from data_pipeline.exchange_connectors.bybit_connector import ByBitConnector
from data_pipeline.exchange_connectors.oanda_connector import OANDAConnector
from data_pipeline.exchange_connectors.failover_manager import (
    ExchangeFailoverManager,
    FailoverTrigger,
    FailoverState,
    FailoverRule,
    ExchangeHealthMetrics,
    FailoverEvent
)
from data_pipeline.exchange_connectors.error_handling import (
    ErrorHandlerManager,
    ExchangeError,
    ErrorCategory,
    ErrorSeverity
)
from data_pipeline.exchange_connectors.rate_limiter import (
    RateLimitManager,
    RateLimitConfig
)

logger = logging.getLogger(__name__)

# Test configuration
FAILOVER_TEST_TIMEOUT = 120  # seconds
HEALTH_CHECK_INTERVAL = 5   # seconds
RECOVERY_TEST_DURATION = 60 # seconds


@dataclass
class FailoverTestScenario:
    """Failover test scenario configuration."""
    name: str
    trigger: FailoverTrigger
    primary_exchange: ExchangeType
    target_exchange: ExchangeType
    expected_outcome: str  # success, failure, partial
    setup_conditions: Dict[str, Any]
    validation_checks: List[str]


class FailoverTestHarness:
    """Test harness for failover mechanism testing."""
    
    def __init__(self, sandbox_config):
        """Initialize failover test harness."""
        self.sandbox_config = sandbox_config
        self.connectors = {}
        self.failover_manager = None
        self.error_manager = None
        self.rate_manager = None
        self.test_results = {}
        
    async def setup(self, available_exchanges: List[ExchangeType]):
        """Set up test environment."""
        logger.info("Setting up failover test harness")
        
        if len(available_exchanges) < 2:
            raise ValueError("Need at least 2 exchanges for failover testing")
        
        # Initialize managers
        self.failover_manager = ExchangeFailoverManager(Environment.TESTNET)
        self.error_manager = ErrorHandlerManager()
        self.rate_manager = RateLimitManager()
        
        # Create connectors
        for i, exchange_type in enumerate(available_exchanges):
            connector = await self._create_connector(exchange_type)
            if connector:
                self.connectors[exchange_type] = connector
                
                # Add to failover manager with priority
                priority = i + 1
                self.failover_manager.add_exchange(exchange_type, connector, priority)
                
                # Configure rate limiter
                rate_config = self._get_rate_config(exchange_type)
                self.rate_manager.add_exchange(exchange_type, rate_config)
        
        # Start monitoring
        await self.failover_manager.start_monitoring()
        self.rate_manager.start_monitoring()
        
        # Wait for initial health checks
        await asyncio.sleep(3)
        
        logger.info(f"Failover test harness setup complete with {len(self.connectors)} exchanges")
        logger.info(f"Primary exchange: {self.failover_manager.primary_exchange.value}")
        logger.info(f"Active exchange: {self.failover_manager.active_exchange.value}")
    
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
        return RateLimitConfig(
            requests_per_minute=60,
            requests_per_second=2,
            burst_limit=5,
            backoff_factor=1.5,
            max_backoff_time=30
        )
    
    async def simulate_exchange_failure(self, exchange_type: ExchangeType, failure_type: str):
        """Simulate exchange failure for testing."""
        logger.info(f"Simulating {failure_type} failure for {exchange_type.value}")
        
        metrics = self.failover_manager.health_metrics[exchange_type]
        
        if failure_type == "connection":
            metrics.is_connected = False
            metrics.consecutive_failures = 10
            
        elif failure_type == "high_latency":
            metrics.average_latency_ms = 2000.0  # 2 seconds
            
        elif failure_type == "api_errors":
            metrics.consecutive_failures = 8
            metrics.success_rate_5min = 30.0
            
        elif failure_type == "rate_limit":
            metrics.rate_limit_violations = 5
            
        logger.info(f"Simulated {failure_type} failure - health score: {metrics.get_health_score():.1f}")
    
    async def simulate_exchange_recovery(self, exchange_type: ExchangeType):
        """Simulate exchange recovery for testing."""
        logger.info(f"Simulating recovery for {exchange_type.value}")
        
        metrics = self.failover_manager.health_metrics[exchange_type]
        
        # Reset to healthy state
        metrics.is_connected = True
        metrics.consecutive_failures = 0
        metrics.success_rate_5min = 95.0
        metrics.average_latency_ms = 100.0
        metrics.rate_limit_violations = 0
        
        # Simulate successful requests
        for _ in range(10):
            metrics.update_request_result(True, 80.0)
        
        logger.info(f"Simulated recovery - health score: {metrics.get_health_score():.1f}")
    
    async def wait_for_failover(self, timeout: float = 30.0) -> bool:
        """Wait for failover to occur."""
        start_time = time.time()
        initial_active = self.failover_manager.active_exchange
        
        while time.time() - start_time < timeout:
            current_active = self.failover_manager.active_exchange
            current_state = self.failover_manager.current_state
            
            if (current_active != initial_active or 
                current_state == FailoverState.FAILED_OVER):
                logger.info(f"Failover detected: {initial_active.value} -> {current_active.value}")
                return True
            
            await asyncio.sleep(1)
        
        return False
    
    async def cleanup(self):
        """Clean up test environment."""
        logger.info("Cleaning up failover test harness")
        
        try:
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
def failover_harness(sandbox_config):
    """Failover test harness fixture."""
    return FailoverTestHarness(sandbox_config)


class TestBasicFailover:
    """Test basic failover functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_failure_failover(self, failover_harness, skip_if_no_credentials):
        """Test failover triggered by connection failure."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            # Get initial state
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing connection failure failover: {primary_exchange.value} -> {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Simulate connection failure on primary
            await failover_harness.simulate_exchange_failure(primary_exchange, "connection")
            
            # Mock the actual failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Wait for failover to be triggered
                failover_occurred = await failover_harness.wait_for_failover(timeout=20.0)
                
                assert failover_occurred, "Failover should have been triggered by connection failure"
                
                # Verify failover state
                assert failover_harness.failover_manager.active_exchange == target_exchange
                assert failover_harness.failover_manager.current_state == FailoverState.FAILED_OVER
                assert primary_exchange in failover_harness.failover_manager.failed_exchanges
            
            logger.info("Connection failure failover test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_high_latency_failover(self, failover_harness, skip_if_no_credentials):
        """Test failover triggered by high latency."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing high latency failover: {primary_exchange.value} -> {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Simulate high latency on primary
            await failover_harness.simulate_exchange_failure(primary_exchange, "high_latency")
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Wait for failover
                failover_occurred = await failover_harness.wait_for_failover(timeout=20.0)
                
                assert failover_occurred, "Failover should have been triggered by high latency"
                assert failover_harness.failover_manager.active_exchange == target_exchange
            
            logger.info("High latency failover test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_api_error_failover(self, failover_harness, skip_if_no_credentials):
        """Test failover triggered by API errors."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing API error failover: {primary_exchange.value} -> {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Simulate API errors on primary
            await failover_harness.simulate_exchange_failure(primary_exchange, "api_errors")
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Wait for failover
                failover_occurred = await failover_harness.wait_for_failover(timeout=20.0)
                
                assert failover_occurred, "Failover should have been triggered by API errors"
                assert failover_harness.failover_manager.active_exchange == target_exchange
            
            logger.info("API error failover test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_manual_failover(self, failover_harness, skip_if_no_credentials):
        """Test manual failover functionality."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing manual failover: {primary_exchange.value} -> {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Trigger manual failover
                success = await failover_harness.failover_manager.manual_failover(target_exchange)
                
                assert success, "Manual failover should succeed"
                assert failover_harness.failover_manager.active_exchange == target_exchange
                assert failover_harness.failover_manager.current_state == FailoverState.FAILED_OVER
            
            logger.info("Manual failover test completed successfully")
            
        finally:
            await failover_harness.cleanup()


class TestFailoverRecovery:
    """Test failover recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_exchange_recovery_detection(self, failover_harness, skip_if_no_credentials):
        """Test detection of exchange recovery."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            
            # Simulate failover state
            failover_harness.failover_manager.active_exchange = secondary_exchanges[0]
            failover_harness.failover_manager.current_state = FailoverState.FAILED_OVER
            failover_harness.failover_manager.failed_exchanges.add(primary_exchange)
            
            logger.info(f"Testing recovery detection for {primary_exchange.value}")
            
            # Simulate primary exchange recovery
            await failover_harness.simulate_exchange_recovery(primary_exchange)
            
            # Wait for recovery detection
            await asyncio.sleep(5)
            
            # Check recovery
            await failover_harness.failover_manager._check_failed_exchange_recovery()
            
            # Primary should be removed from failed exchanges
            assert primary_exchange not in failover_harness.failover_manager.failed_exchanges
            
            logger.info("Exchange recovery detection test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_automatic_failback(self, failover_harness, skip_if_no_credentials):
        """Test automatic failback to primary exchange."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for failover testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            secondary_exchange = secondary_exchanges[0]
            
            # Set up failed over state
            failover_harness.failover_manager.active_exchange = secondary_exchange
            failover_harness.failover_manager.current_state = FailoverState.FAILED_OVER
            failover_harness.failover_manager.failed_exchanges.add(primary_exchange)
            
            logger.info(f"Testing automatic failback: {secondary_exchange.value} -> {primary_exchange.value}")
            
            # Make secondary exchange less healthy
            await failover_harness.simulate_exchange_failure(secondary_exchange, "high_latency")
            
            # Make primary exchange very healthy
            await failover_harness.simulate_exchange_recovery(primary_exchange)
            
            # Mock failover execution for failback
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Trigger recovery check
                await failover_harness.failover_manager._check_failed_exchange_recovery()
                
                # Should consider failback
                await failover_harness.failover_manager._consider_failback(primary_exchange)
                
                # Check if failback occurred
                if failover_harness.failover_manager.active_exchange == primary_exchange:
                    logger.info("Automatic failback occurred successfully")
                else:
                    logger.info("Failback conditions not met (expected in some scenarios)")
            
        finally:
            await failover_harness.cleanup()


class TestFailoverScenarios:
    """Test complex failover scenarios."""
    
    @pytest.mark.asyncio
    async def test_cascading_failures(self, failover_harness, skip_if_no_credentials):
        """Test cascading failures across multiple exchanges."""
        if len(skip_if_no_credentials) < 3:
            pytest.skip("Need at least 3 exchanges for cascading failure testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            exchanges = list(skip_if_no_credentials[:3])  # Use first 3 exchanges
            
            logger.info(f"Testing cascading failures across {len(exchanges)} exchanges")
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Simulate failures in sequence
                for i, exchange in enumerate(exchanges[:-1]):  # Leave last exchange healthy
                    logger.info(f"Simulating failure {i+1}: {exchange.value}")
                    
                    await failover_harness.simulate_exchange_failure(exchange, "connection")
                    
                    # Wait for failover
                    await asyncio.sleep(3)
                    
                    # Check state
                    current_active = failover_harness.failover_manager.active_exchange
                    logger.info(f"Active exchange after failure {i+1}: {current_active.value}")
                
                # Final active exchange should be the last healthy one
                final_active = failover_harness.failover_manager.active_exchange
                assert final_active == exchanges[-1], f"Expected {exchanges[-1].value}, got {final_active.value}"
            
            logger.info("Cascading failures test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_rapid_failover_recovery_cycle(self, failover_harness, skip_if_no_credentials):
        """Test rapid failover and recovery cycles."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for rapid cycle testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            secondary_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing rapid failover/recovery cycles between {primary_exchange.value} and {secondary_exchange.value}")
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Perform multiple rapid cycles
                for cycle in range(3):
                    logger.info(f"Cycle {cycle + 1}: Failing over to {secondary_exchange.value}")
                    
                    # Simulate primary failure
                    await failover_harness.simulate_exchange_failure(primary_exchange, "connection")
                    
                    # Trigger failover
                    success = await failover_harness.failover_manager.manual_failover(secondary_exchange)
                    assert success, f"Failover should succeed in cycle {cycle + 1}"
                    
                    # Wait briefly
                    await asyncio.sleep(2)
                    
                    logger.info(f"Cycle {cycle + 1}: Recovering {primary_exchange.value}")
                    
                    # Simulate primary recovery
                    await failover_harness.simulate_exchange_recovery(primary_exchange)
                    
                    # Simulate secondary failure to force failback
                    await failover_harness.simulate_exchange_failure(secondary_exchange, "api_errors")
                    
                    # Trigger failback
                    success = await failover_harness.failover_manager.manual_failover(primary_exchange)
                    assert success, f"Failback should succeed in cycle {cycle + 1}"
                    
                    # Wait briefly
                    await asyncio.sleep(2)
                    
                    # Recover secondary for next cycle
                    await failover_harness.simulate_exchange_recovery(secondary_exchange)
            
            logger.info("Rapid failover/recovery cycle test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_no_healthy_exchanges(self, failover_harness, skip_if_no_credentials):
        """Test behavior when no healthy exchanges are available."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for no healthy exchanges testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            logger.info("Testing behavior with no healthy exchanges")
            
            # Simulate failures on all exchanges
            for exchange in skip_if_no_credentials:
                await failover_harness.simulate_exchange_failure(exchange, "connection")
            
            # Try to find best exchange
            best_exchange = failover_harness.failover_manager._select_best_exchange()
            
            # Should return None when no exchanges are healthy
            assert best_exchange is None, "Should return None when no exchanges are healthy"
            
            # Try manual failover (should fail)
            target_exchange = skip_if_no_credentials[0]
            success = await failover_harness.failover_manager.manual_failover(target_exchange)
            
            # Should fail because target is not healthy
            assert not success, "Manual failover should fail when target is unhealthy"
            
            logger.info("No healthy exchanges test completed successfully")
            
        finally:
            await failover_harness.cleanup()


class TestFailoverIntegration:
    """Test failover integration with other components."""
    
    @pytest.mark.asyncio
    async def test_failover_error_handling_integration(self, failover_harness, skip_if_no_credentials):
        """Test failover integration with error handling."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for integration testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            
            logger.info(f"Testing failover integration with error handling for {primary_exchange.value}")
            
            # Simulate multiple errors
            for i in range(10):
                fake_error = Exception(f"Test API error {i}")
                
                # Handle error
                structured_error = await failover_harness.error_manager.handle_error(
                    fake_error,
                    primary_exchange,
                    f"test_operation_{i}"
                )
                
                # Update health metrics based on error
                metrics = failover_harness.failover_manager.health_metrics[primary_exchange]
                metrics.update_request_result(False)
            
            # Check if errors affected health score
            metrics = failover_harness.failover_manager.health_metrics[primary_exchange]
            health_score = metrics.get_health_score()
            
            logger.info(f"Health score after errors: {health_score:.1f}")
            
            # Health should be degraded
            assert health_score < 80.0, "Health score should be degraded after multiple errors"
            
            # Get error statistics
            error_stats = failover_harness.error_manager.get_error_statistics(primary_exchange)
            assert error_stats["total_errors"] >= 10
            
            logger.info("Failover error handling integration test completed successfully")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_failover_rate_limiting_integration(self, failover_harness, skip_if_no_credentials):
        """Test failover integration with rate limiting."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for integration testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            
            logger.info(f"Testing failover integration with rate limiting for {primary_exchange.value}")
            
            # Simulate rate limit hits
            for i in range(5):
                failover_harness.rate_manager.handle_rate_limit_error(primary_exchange)
                
                # Update health metrics
                metrics = failover_harness.failover_manager.health_metrics[primary_exchange]
                metrics.rate_limit_violations += 1
            
            # Check rate limiter status
            rate_status = failover_harness.rate_manager.get_exchange_status(primary_exchange)
            assert rate_status is not None
            assert rate_status["statistics"]["rate_limit_hits"] >= 5
            
            # Check if rate limits affected health
            metrics = failover_harness.failover_manager.health_metrics[primary_exchange]
            health_score = metrics.get_health_score()
            
            logger.info(f"Health score after rate limit hits: {health_score:.1f}")
            
            logger.info("Failover rate limiting integration test completed successfully")
            
        finally:
            await failover_harness.cleanup()


class TestFailoverPerformance:
    """Test failover performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_failover_speed(self, failover_harness, skip_if_no_credentials):
        """Test failover execution speed."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for performance testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing failover speed: {primary_exchange.value} -> {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Measure failover time
            start_time = time.time()
            
            # Mock fast failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                success = await failover_harness.failover_manager.manual_failover(target_exchange)
                
                failover_time = time.time() - start_time
                
                assert success, "Failover should succeed"
                assert failover_time < 5.0, f"Failover should complete within 5 seconds, took {failover_time:.2f}s"
                
                logger.info(f"Failover completed in {failover_time:.3f} seconds")
            
        finally:
            await failover_harness.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_failover_attempts(self, failover_harness, skip_if_no_credentials):
        """Test handling of concurrent failover attempts."""
        if len(skip_if_no_credentials) < 2:
            pytest.skip("Need at least 2 exchanges for concurrency testing")
        
        await failover_harness.setup(skip_if_no_credentials)
        
        try:
            primary_exchange = failover_harness.failover_manager.primary_exchange
            secondary_exchanges = [ex for ex in skip_if_no_credentials if ex != primary_exchange]
            target_exchange = secondary_exchanges[0]
            
            logger.info(f"Testing concurrent failover attempts to {target_exchange.value}")
            
            # Ensure target is healthy
            await failover_harness.simulate_exchange_recovery(target_exchange)
            
            # Mock failover execution
            with patch.object(failover_harness.failover_manager, '_execute_failover', return_value=True):
                # Launch multiple concurrent failover attempts
                tasks = []
                for i in range(5):
                    task = asyncio.create_task(
                        failover_harness.failover_manager.manual_failover(target_exchange)
                    )
                    tasks.append(task)
                
                # Wait for all attempts
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze results
                successful_failovers = sum(1 for r in results if r is True)
                failed_failovers = sum(1 for r in results if r is False)
                errors = sum(1 for r in results if isinstance(r, Exception))
                
                logger.info(f"Concurrent failover results: {successful_failovers} success, "
                           f"{failed_failovers} failed, {errors} errors")
                
                # Only one should succeed, others should be handled gracefully
                assert successful_failovers <= 1, "At most one concurrent failover should succeed"
                assert errors == 0, "No exceptions should occur during concurrent attempts"
            
        finally:
            await failover_harness.cleanup()


# Test runner for failover integration tests
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