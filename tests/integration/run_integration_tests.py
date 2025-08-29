"""
Integration Test Runner

Comprehensive test runner for exchange API integration tests.
Provides different test suites and configuration options.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.integration.conftest import SandboxTestConfig, print_env_var_help


class IntegrationTestRunner:
    """Integration test runner with various test suites."""
    
    def __init__(self):
        """Initialize test runner."""
        self.config = SandboxTestConfig()
        self.test_results = {}
        
    def check_credentials(self) -> Dict[str, bool]:
        """Check which exchange credentials are available."""
        return {
            "binance": self.config.has_binance_credentials(),
            "bybit": self.config.has_bybit_credentials(),
            "oanda": self.config.has_oanda_credentials()
        }
    
    def print_status(self):
        """Print current test environment status."""
        print("\n" + "=" * 80)
        print("SMC Trading Agent - Integration Test Runner")
        print("=" * 80)
        
        credentials = self.check_credentials()
        available_exchanges = self.config.get_available_exchanges()
        
        print(f"\nAvailable Exchanges: {len(available_exchanges)}")
        for exchange, available in credentials.items():
            status = "✓ Available" if available else "✗ Not Available"
            print(f"  {exchange.upper():<10} {status}")
        
        if not available_exchanges:
            print("\n⚠️  WARNING: No exchange credentials available!")
            print("   Integration tests will be skipped.")
            print("   Set environment variables to enable testing.")
        
        print("\nTest Suites Available:")
        print("  1. Basic Connection Tests")
        print("  2. Rate Limiting Tests") 
        print("  3. Error Handling Tests")
        print("  4. Circuit Breaker Tests")
        print("  5. Failover Mechanism Tests")
        print("  6. Full Integration Suite")
        print("=" * 80)
    
    def run_basic_tests(self) -> int:
        """Run basic connection tests."""
        print("\n🔍 Running Basic Connection Tests...")
        
        args = [
            "tests/integration/test_sandbox_integration.py::TestSandboxConfiguration",
            "tests/integration/test_sandbox_integration.py::TestBinanceTestnetIntegration::test_binance_testnet_connection",
            "tests/integration/test_sandbox_integration.py::TestBybitTestnetIntegration::test_bybit_testnet_connection", 
            "tests/integration/test_sandbox_integration.py::TestOandaPracticeIntegration::test_oanda_practice_connection",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_rate_limiting_tests(self) -> int:
        """Run rate limiting tests."""
        print("\n⏱️  Running Rate Limiting Tests...")
        
        args = [
            "tests/integration/test_sandbox_integration.py",
            "-k", "rate_limiting",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_error_handling_tests(self) -> int:
        """Run error handling tests."""
        print("\n🚨 Running Error Handling Tests...")
        
        args = [
            "tests/integration/test_sandbox_integration.py::TestErrorHandlingIntegration",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_circuit_breaker_tests(self) -> int:
        """Run circuit breaker tests."""
        print("\n🔌 Running Circuit Breaker Tests...")
        
        args = [
            "tests/integration/test_circuit_breaker_integration.py",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_failover_tests(self) -> int:
        """Run failover mechanism tests."""
        print("\n🔄 Running Failover Mechanism Tests...")
        
        args = [
            "tests/integration/test_failover_integration.py",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_full_suite(self) -> int:
        """Run full integration test suite."""
        print("\n🚀 Running Full Integration Test Suite...")
        
        args = [
            "tests/integration/",
            "-v", "-s", "--tb=short",
            "--maxfail=5"  # Stop after 5 failures
        ]
        
        return pytest.main(args)
    
    def run_performance_tests(self) -> int:
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")
        
        args = [
            "tests/integration/",
            "-m", "slow",
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)
    
    def run_custom_tests(self, test_pattern: str) -> int:
        """Run custom test pattern."""
        print(f"\n🎯 Running Custom Tests: {test_pattern}")
        
        args = [
            "tests/integration/",
            "-k", test_pattern,
            "-v", "-s", "--tb=short"
        ]
        
        return pytest.main(args)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="SMC Trading Agent Integration Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_integration_tests.py --suite basic
  python run_integration_tests.py --suite full
  python run_integration_tests.py --custom "binance and connection"
  python run_integration_tests.py --check-env
        """
    )
    
    parser.add_argument(
        "--suite",
        choices=["basic", "rate-limiting", "error-handling", "circuit-breaker", "failover", "full", "performance"],
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--custom",
        type=str,
        help="Custom test pattern to run (pytest -k syntax)"
    )
    
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment variables and exit"
    )
    
    parser.add_argument(
        "--list-tests",
        action="store_true", 
        help="List available tests without running them"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    runner = IntegrationTestRunner()
    
    # Always show status
    runner.print_status()
    
    # Check environment variables
    if args.check_env:
        print("\n")
        print_env_var_help()
        return 0
    
    # List tests
    if args.list_tests:
        print("\n📋 Listing Available Tests...")
        pytest_args = [
            "tests/integration/",
            "--collect-only",
            "-q"
        ]
        return pytest.main(pytest_args)
    
    # Check if any credentials are available
    available_exchanges = runner.config.get_available_exchanges()
    if not available_exchanges:
        print("\n❌ No exchange credentials available!")
        print("   Set environment variables to run integration tests.")
        print("   Use --check-env to see required variables.")
        return 1
    
    # Run tests based on arguments
    start_time = time.time()
    
    try:
        if args.suite == "basic":
            result = runner.run_basic_tests()
        elif args.suite == "rate-limiting":
            result = runner.run_rate_limiting_tests()
        elif args.suite == "error-handling":
            result = runner.run_error_handling_tests()
        elif args.suite == "circuit-breaker":
            result = runner.run_circuit_breaker_tests()
        elif args.suite == "failover":
            result = runner.run_failover_tests()
        elif args.suite == "full":
            result = runner.run_full_suite()
        elif args.suite == "performance":
            result = runner.run_performance_tests()
        elif args.custom:
            result = runner.run_custom_tests(args.custom)
        else:
            # Interactive mode
            result = runner.run_interactive_mode()
        
        duration = time.time() - start_time
        
        print(f"\n" + "=" * 80)
        print(f"Test execution completed in {duration:.2f} seconds")
        
        if result == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with exit code: {result}")
        
        print("=" * 80)
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1
    
    def run_interactive_mode(self) -> int:
        """Run interactive test selection mode."""
        print("\n🎮 Interactive Test Selection")
        print("=" * 40)
        
        options = {
            "1": ("Basic Connection Tests", self.run_basic_tests),
            "2": ("Rate Limiting Tests", self.run_rate_limiting_tests),
            "3": ("Error Handling Tests", self.run_error_handling_tests),
            "4": ("Circuit Breaker Tests", self.run_circuit_breaker_tests),
            "5": ("Failover Mechanism Tests", self.run_failover_tests),
            "6": ("Full Integration Suite", self.run_full_suite),
            "7": ("Performance Tests", self.run_performance_tests),
            "q": ("Quit", lambda: 0)
        }
        
        while True:
            print("\nSelect test suite to run:")
            for key, (description, _) in options.items():
                print(f"  {key}. {description}")
            
            choice = input("\nEnter your choice (1-7, q): ").strip().lower()
            
            if choice in options:
                description, func = options[choice]
                if choice == "q":
                    print("Goodbye!")
                    return 0
                
                print(f"\nRunning: {description}")
                result = func()
                
                if result == 0:
                    print(f"✅ {description} completed successfully!")
                else:
                    print(f"❌ {description} failed with exit code: {result}")
                
                continue_choice = input("\nRun another test suite? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    return result
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    sys.exit(main())