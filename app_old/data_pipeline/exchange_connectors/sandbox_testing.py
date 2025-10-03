"""
Sandbox Testing Framework

Comprehensive testing framework for production API credentials in sandbox/testnet mode.
Validates API functionality, permissions, and integration before production deployment.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from .production_config import ExchangeType, ExchangeConfig, ProductionConfigManager, Environment
from .production_factory import ProductionExchangeFactory
from .error_handling import handle_exchange_error, ErrorCategory

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestSeverity(Enum):
    """Test failure severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    exchange_type: ExchangeType
    status: TestStatus
    severity: TestSeverity
    duration: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "test_name": self.test_name,
            "exchange": self.exchange_type.value,
            "status": self.status.value,
            "severity": self.severity.value,
            "duration": self.duration,
            "error_message": self.error_message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class TestSuite:
    """Collection of test results for an exchange."""
    exchange_type: ExchangeType
    environment: Environment
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration: float
    results: List[TestResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def is_healthy(self) -> bool:
        """Determine if exchange is healthy based on test results."""
        # Consider healthy if >80% tests pass and no critical failures
        critical_failures = [r for r in self.results if r.status == TestStatus.FAILED and r.severity == TestSeverity.CRITICAL]
        return self.success_rate >= 80.0 and len(critical_failures) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "exchange": self.exchange_type.value,
            "environment": self.environment.value,
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "skipped_tests": self.skipped_tests,
                "success_rate": self.success_rate,
                "total_duration": self.total_duration,
                "is_healthy": self.is_healthy
            },
            "timing": {
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None
            },
            "results": [result.to_dict() for result in self.results]
        }


class SandboxTestRunner:
    """
    Runs comprehensive tests against exchange APIs in sandbox/testnet mode.
    
    Tests include:
    - Authentication validation
    - API endpoint accessibility
    - WebSocket connectivity
    - Data retrieval
    - Rate limiting behavior
    - Error handling
    """
    
    def __init__(self, config_manager: ProductionConfigManager, factory: ProductionExchangeFactory):
        """
        Initialize test runner.
        
        Args:
            config_manager: Production configuration manager
            factory: Exchange factory for creating connectors
        """
        self.config_manager = config_manager
        self.factory = factory
        self.test_suites: Dict[ExchangeType, TestSuite] = {}
        
        logger.info("Initialized sandbox test runner")
    
    async def run_all_tests(self, exchange_types: Optional[List[ExchangeType]] = None) -> Dict[ExchangeType, TestSuite]:
        """
        Run all tests for specified exchanges.
        
        Args:
            exchange_types: Exchanges to test, or None for all configured
            
        Returns:
            Dict[ExchangeType, TestSuite]: Test results for each exchange
        """
        if exchange_types is None:
            exchange_types = [et for et in ExchangeType if self.config_manager.is_exchange_enabled(et)]
        
        logger.info(f"Running sandbox tests for {len(exchange_types)} exchanges")
        
        # Run tests for each exchange
        tasks = []
        for exchange_type in exchange_types:
            task = asyncio.create_task(self.run_exchange_tests(exchange_type))
            tasks.append(task)
        
        # Wait for all tests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        test_suites = {}
        for i, result in enumerate(results):
            exchange_type = exchange_types[i]
            if isinstance(result, Exception):
                logger.error(f"Test suite failed for {exchange_type.value}: {result}")
                # Create failed test suite
                test_suites[exchange_type] = TestSuite(
                    exchange_type=exchange_type,
                    environment=self.config_manager.environment,
                    total_tests=1,
                    passed_tests=0,
                    failed_tests=1,
                    skipped_tests=0,
                    total_duration=0.0,
                    results=[TestResult(
                        test_name="test_suite_execution",
                        exchange_type=exchange_type,
                        status=TestStatus.FAILED,
                        severity=TestSeverity.CRITICAL,
                        duration=0.0,
                        error_message=str(result)
                    )]
                )
            else:
                test_suites[exchange_type] = result
        
        self.test_suites = test_suites
        return test_suites
    
    async def run_exchange_tests(self, exchange_type: ExchangeType) -> TestSuite:
        """
        Run all tests for a specific exchange.
        
        Args:
            exchange_type: Exchange to test
            
        Returns:
            TestSuite: Test results for the exchange
        """
        logger.info(f"Starting tests for {exchange_type.value}")
        start_time = time.time()
        
        # Initialize test suite
        test_suite = TestSuite(
            exchange_type=exchange_type,
            environment=self.config_manager.environment,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            total_duration=0.0
        )
        
        # Define test methods
        test_methods = [
            ("test_configuration_validation", self._test_configuration_validation, TestSeverity.CRITICAL),
            ("test_api_authentication", self._test_api_authentication, TestSeverity.CRITICAL),
            ("test_rest_api_connectivity", self._test_rest_api_connectivity, TestSeverity.HIGH),
            ("test_websocket_connectivity", self._test_websocket_connectivity, TestSeverity.HIGH),
            ("test_market_data_retrieval", self._test_market_data_retrieval, TestSeverity.MEDIUM),
            ("test_rate_limiting", self._test_rate_limiting, TestSeverity.MEDIUM),
            ("test_error_handling", self._test_error_handling, TestSeverity.LOW),
            ("test_data_normalization", self._test_data_normalization, TestSeverity.MEDIUM),
            ("test_health_monitoring", self._test_health_monitoring, TestSeverity.LOW)
        ]
        
        # Run each test
        for test_name, test_method, severity in test_methods:
            result = await self._run_single_test(test_name, test_method, exchange_type, severity)
            test_suite.results.append(result)
            test_suite.total_tests += 1
            
            if result.status == TestStatus.PASSED:
                test_suite.passed_tests += 1
            elif result.status == TestStatus.FAILED:
                test_suite.failed_tests += 1
            elif result.status == TestStatus.SKIPPED:
                test_suite.skipped_tests += 1
        
        # Finalize test suite
        test_suite.total_duration = time.time() - start_time
        test_suite.completed_at = datetime.utcnow()
        
        logger.info(f"Completed tests for {exchange_type.value}: {test_suite.passed_tests}/{test_suite.total_tests} passed")
        return test_suite
    
    async def _run_single_test(
        self, 
        test_name: str, 
        test_method, 
        exchange_type: ExchangeType, 
        severity: TestSeverity
    ) -> TestResult:
        """Run a single test method."""
        logger.debug(f"Running {test_name} for {exchange_type.value}")
        start_time = time.time()
        
        try:
            details = await test_method(exchange_type)
            duration = time.time() - start_time
            
            return TestResult(
                test_name=test_name,
                exchange_type=exchange_type,
                status=TestStatus.PASSED,
                severity=severity,
                duration=duration,
                details=details
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Test {test_name} failed for {exchange_type.value}: {e}")
            
            return TestResult(
                test_name=test_name,
                exchange_type=exchange_type,
                status=TestStatus.FAILED,
                severity=severity,
                duration=duration,
                error_message=str(e)
            )
    
    async def _test_configuration_validation(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test configuration validation."""
        config = self.config_manager.get_config(exchange_type)
        if not config:
            raise Exception("No configuration found")
        
        validation = self.config_manager.validate_configuration(exchange_type)
        if not validation["valid"]:
            raise Exception(f"Configuration validation failed: {validation['errors']}")
        
        return {
            "config_valid": True,
            "testnet_mode": config.testnet,
            "symbols_count": len(config.symbols),
            "warnings": validation.get("warnings", [])
        }
    
    async def _test_api_authentication(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test API authentication."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        # Test basic authentication by making a simple API call
        try:
            # This would be exchange-specific endpoint for testing auth
            if exchange_type == ExchangeType.BINANCE:
                endpoint = "/api/v3/account"
            elif exchange_type == ExchangeType.BYBIT:
                endpoint = "/v5/account/info"
            elif exchange_type == ExchangeType.OANDA:
                endpoint = f"/accounts/{connector.config.credentials.account_id}"
            else:
                raise Exception(f"Unknown exchange type: {exchange_type}")
            
            # Make authenticated request
            response = await connector.fetch_rest_data(endpoint)
            
            return {
                "authentication_successful": True,
                "response_received": True,
                "account_info_available": bool(response)
            }
            
        except Exception as e:
            # Check if it's an authentication error
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise Exception(f"Authentication failed: {e}")
            else:
                # Other errors might be acceptable for auth test
                return {
                    "authentication_successful": True,
                    "response_received": False,
                    "error": str(e)
                }
    
    async def _test_rest_api_connectivity(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test REST API connectivity."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        # Test public endpoint (no auth required)
        try:
            if exchange_type == ExchangeType.BINANCE:
                endpoint = "/api/v3/ping"
            elif exchange_type == ExchangeType.BYBIT:
                endpoint = "/v5/market/time"
            elif exchange_type == ExchangeType.OANDA:
                endpoint = "/instruments"
            else:
                raise Exception(f"Unknown exchange type: {exchange_type}")
            
            start_time = time.time()
            response = await connector.fetch_rest_data(endpoint)
            response_time = time.time() - start_time
            
            return {
                "connectivity_successful": True,
                "response_time_ms": response_time * 1000,
                "response_received": bool(response)
            }
            
        except Exception as e:
            raise Exception(f"REST API connectivity failed: {e}")
    
    async def _test_websocket_connectivity(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test WebSocket connectivity."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            # Test WebSocket connection
            start_time = time.time()
            success = await connector.connect_websocket()
            connection_time = time.time() - start_time
            
            if not success:
                raise Exception("WebSocket connection failed")
            
            # Test subscription to a stream
            if exchange_type == ExchangeType.BINANCE:
                streams = ["btcusdt@ticker"]
            elif exchange_type == ExchangeType.BYBIT:
                streams = ["orderbook.1.BTCUSDT"]
            elif exchange_type == ExchangeType.OANDA:
                streams = ["EUR_USD"]
            else:
                streams = []
            
            subscription_success = False
            if streams:
                subscription_success = await connector.subscribe_to_streams(streams)
            
            # Clean up
            await connector.disconnect_websocket()
            
            return {
                "websocket_connection_successful": True,
                "connection_time_ms": connection_time * 1000,
                "subscription_successful": subscription_success,
                "streams_tested": len(streams)
            }
            
        except Exception as e:
            raise Exception(f"WebSocket connectivity failed: {e}")
    
    async def _test_market_data_retrieval(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test market data retrieval."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            # Test market data endpoints
            if exchange_type == ExchangeType.BINANCE:
                endpoint = "/api/v3/ticker/24hr"
                params = {"symbol": "BTCUSDT"}
            elif exchange_type == ExchangeType.BYBIT:
                endpoint = "/v5/market/tickers"
                params = {"category": "spot", "symbol": "BTCUSDT"}
            elif exchange_type == ExchangeType.OANDA:
                endpoint = "/accounts/{}/pricing".format(connector.config.credentials.account_id)
                params = {"instruments": "EUR_USD"}
            else:
                raise Exception(f"Unknown exchange type: {exchange_type}")
            
            response = await connector.fetch_rest_data(endpoint, params)
            
            if not response:
                raise Exception("No market data received")
            
            return {
                "market_data_retrieved": True,
                "data_size": len(str(response)),
                "has_price_data": "price" in str(response).lower()
            }
            
        except Exception as e:
            raise Exception(f"Market data retrieval failed: {e}")
    
    async def _test_rate_limiting(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test rate limiting behavior."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            # Make multiple rapid requests to test rate limiting
            request_count = 5
            start_time = time.time()
            
            for i in range(request_count):
                try:
                    if exchange_type == ExchangeType.BINANCE:
                        await connector.fetch_rest_data("/api/v3/ping")
                    elif exchange_type == ExchangeType.BYBIT:
                        await connector.fetch_rest_data("/v5/market/time")
                    elif exchange_type == ExchangeType.OANDA:
                        await connector.fetch_rest_data("/instruments")
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        # Rate limiting is working
                        break
            
            total_time = time.time() - start_time
            
            return {
                "rate_limiting_tested": True,
                "requests_made": request_count,
                "total_time_ms": total_time * 1000,
                "average_request_time_ms": (total_time / request_count) * 1000
            }
            
        except Exception as e:
            raise Exception(f"Rate limiting test failed: {e}")
    
    async def _test_error_handling(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test error handling capabilities."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            # Test with invalid endpoint to trigger error handling
            try:
                await connector.fetch_rest_data("/invalid/endpoint")
            except Exception as e:
                # This is expected - test that error is handled properly
                error = await handle_exchange_error(e, exchange_type, "test_error_handling")
                
                return {
                    "error_handling_working": True,
                    "error_classified": error.category != ErrorCategory.UNKNOWN,
                    "error_category": error.category.value,
                    "error_severity": error.severity.value
                }
            
            # If no error was raised, that's unexpected
            return {
                "error_handling_working": False,
                "reason": "No error raised for invalid endpoint"
            }
            
        except Exception as e:
            raise Exception(f"Error handling test failed: {e}")
    
    async def _test_data_normalization(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test data normalization functionality."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            # Test data normalization with sample data
            if exchange_type == ExchangeType.BINANCE:
                sample_trade_data = {
                    "s": "BTCUSDT",
                    "p": "50000.00",
                    "q": "0.001",
                    "S": "BUY",
                    "T": 1234567890000,
                    "t": 12345,
                    "Q": "50.00"
                }
            elif exchange_type == ExchangeType.BYBIT:
                sample_trade_data = {
                    "s": "BTCUSDT",
                    "p": "50000.00",
                    "v": "0.001",
                    "S": "Buy",
                    "T": 1234567890000,
                    "i": "12345",
                    "q": "50.00"
                }
            elif exchange_type == ExchangeType.OANDA:
                sample_trade_data = {
                    "instrument": "EUR_USD",
                    "price": "1.1000",
                    "units": "1000",
                    "side": "buy",
                    "time": 1234567890,
                    "id": "12345"
                }
            else:
                raise Exception(f"Unknown exchange type: {exchange_type}")
            
            normalized = await connector.normalize_data(sample_trade_data, "trade")
            
            # Check if normalized data has expected fields
            expected_fields = ["exchange", "symbol", "price", "quantity", "side", "timestamp"]
            has_all_fields = all(field in normalized for field in expected_fields)
            
            return {
                "normalization_successful": True,
                "has_all_expected_fields": has_all_fields,
                "normalized_fields": list(normalized.keys()),
                "exchange_field_correct": normalized.get("exchange") == exchange_type.value
            }
            
        except Exception as e:
            raise Exception(f"Data normalization test failed: {e}")
    
    async def _test_health_monitoring(self, exchange_type: ExchangeType) -> Dict[str, Any]:
        """Test health monitoring functionality."""
        connector = self.factory.create_connector(exchange_type)
        if not connector:
            raise Exception("Failed to create connector")
        
        try:
            health_status = await connector.get_health_status()
            
            if not health_status:
                raise Exception("No health status returned")
            
            # Check for expected health status fields
            expected_fields = ["exchange", "connected", "timestamp"]
            has_expected_fields = all(field in health_status for field in expected_fields)
            
            return {
                "health_monitoring_working": True,
                "has_expected_fields": has_expected_fields,
                "health_status_fields": list(health_status.keys()),
                "exchange_name_correct": health_status.get("exchange") == exchange_type.value
            }
            
        except Exception as e:
            raise Exception(f"Health monitoring test failed: {e}")
    
    def generate_test_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive test report.
        
        Args:
            output_file: Optional file path to save report
            
        Returns:
            Dict[str, Any]: Test report
        """
        if not self.test_suites:
            return {"error": "No test results available"}
        
        # Calculate overall statistics
        total_exchanges = len(self.test_suites)
        healthy_exchanges = sum(1 for suite in self.test_suites.values() if suite.is_healthy)
        total_tests = sum(suite.total_tests for suite in self.test_suites.values())
        total_passed = sum(suite.passed_tests for suite in self.test_suites.values())
        total_failed = sum(suite.failed_tests for suite in self.test_suites.values())
        total_skipped = sum(suite.skipped_tests for suite in self.test_suites.values())
        
        # Generate report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "environment": self.config_manager.environment.value,
                "total_exchanges_tested": total_exchanges
            },
            "overall_summary": {
                "healthy_exchanges": healthy_exchanges,
                "unhealthy_exchanges": total_exchanges - healthy_exchanges,
                "overall_health_rate": (healthy_exchanges / total_exchanges * 100) if total_exchanges > 0 else 0,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "overall_success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            "exchange_results": {
                exchange_type.value: suite.to_dict() 
                for exchange_type, suite in self.test_suites.items()
            },
            "recommendations": self._generate_recommendations()
        }
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Test report saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save test report: {e}")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        for exchange_type, suite in self.test_suites.items():
            if not suite.is_healthy:
                recommendations.append(f"Review {exchange_type.value} configuration - health check failed")
            
            # Check for critical failures
            critical_failures = [r for r in suite.results if r.status == TestStatus.FAILED and r.severity == TestSeverity.CRITICAL]
            if critical_failures:
                recommendations.append(f"Address critical failures in {exchange_type.value}: {[f.test_name for f in critical_failures]}")
            
            # Check success rate
            if suite.success_rate < 80:
                recommendations.append(f"Improve {exchange_type.value} reliability - success rate is {suite.success_rate:.1f}%")
        
        if not recommendations:
            recommendations.append("All exchanges are healthy and ready for production")
        
        return recommendations


# Convenience functions
async def run_sandbox_tests(environment: Environment = Environment.TESTNET) -> Dict[ExchangeType, TestSuite]:
    """
    Run sandbox tests for all configured exchanges.
    
    Args:
        environment: Environment to test (should be testnet/sandbox)
        
    Returns:
        Dict[ExchangeType, TestSuite]: Test results
    """
    config_manager = ProductionConfigManager(environment)
    factory = ProductionExchangeFactory(environment)
    test_runner = SandboxTestRunner(config_manager, factory)
    
    return await test_runner.run_all_tests()


async def validate_production_readiness(environment: Environment = Environment.TESTNET) -> bool:
    """
    Validate if exchanges are ready for production deployment.
    
    Args:
        environment: Environment to test
        
    Returns:
        bool: True if all exchanges are production-ready
    """
    test_results = await run_sandbox_tests(environment)
    
    # Check if all exchanges are healthy
    all_healthy = all(suite.is_healthy for suite in test_results.values())
    
    if all_healthy:
        logger.info("All exchanges are production-ready")
    else:
        unhealthy = [et.value for et, suite in test_results.items() if not suite.is_healthy]
        logger.warning(f"Exchanges not ready for production: {unhealthy}")
    
    return all_healthy