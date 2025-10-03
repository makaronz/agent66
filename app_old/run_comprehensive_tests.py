#!/usr/bin/env python3
"""
Comprehensive test runner for SMC Trading Agent error handling and validation.

This script runs all tests and generates a comprehensive report covering:
- Error handling functionality
- Data validation framework
- System degradation and recovery
- Performance testing
- Integration testing
"""

import sys
import os
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Tuple

# Add current directory to path
sys.path.append('.')

# Import test modules
from test_error_handling import main as run_error_handling_tests
from tests.test_error_handling import (
    TestCircuitBreaker, TestRetryHandler, TestDataValidation,
    TestErrorBoundary, TestHealthMonitor, TestIntegration, TestPerformance
)
from tests.test_validation import (
    TestMarketDataValidation, TestTradeSignalValidation,
    TestOrderBlockValidation, TestAnomalyDetection,
    TestPerformance as TestValidationPerformance, TestEdgeCases
)
from tests.test_degradation import (
    TestGracefulDegradation, TestRecoveryMechanisms,
    TestStressTesting, TestPerformanceDegradation, TestEdgeCaseDegradation
)


class TestRunner:
    """Comprehensive test runner with reporting."""
    
    def __init__(self):
        """Initialize test runner."""
        self.setup_logging()
        self.results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'test_details': [],
            'start_time': None,
            'end_time': None
        }
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('test_results.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_test_method(self, test_class, method_name: str) -> Dict:
        """Run a single test method and return results."""
        test_instance = test_class()
        test_instance.setup_method()
        
        start_time = time.time()
        result = {
            'test_name': f"{test_class.__name__}.{method_name}",
            'status': 'PASSED',
            'error': None,
            'duration': 0,
            'details': ''
        }
        
        try:
            method = getattr(test_instance, method_name)
            method()
            result['status'] = 'PASSED'
            result['details'] = 'Test completed successfully'
        except Exception as e:
            result['status'] = 'FAILED'
            result['error'] = str(e)
            result['details'] = traceback.format_exc()
        
        result['duration'] = time.time() - start_time
        return result
    
    def run_test_class(self, test_class) -> List[Dict]:
        """Run all test methods in a test class."""
        results = []
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        self.logger.info(f"Running {len(test_methods)} tests from {test_class.__name__}")
        
        for method_name in test_methods:
            result = self.run_test_method(test_class, method_name)
            results.append(result)
            
            if result['status'] == 'PASSED':
                self.logger.info(f"✅ {result['test_name']} - {result['duration']:.3f}s")
            else:
                self.logger.error(f"❌ {result['test_name']} - {result['error']}")
        
        return results
    
    def run_integration_tests(self) -> List[Dict]:
        """Run integration tests."""
        self.logger.info("Running Integration Tests...")
        
        try:
            # Run the main error handling test script
            start_time = time.time()
            exit_code = run_error_handling_tests()
            duration = time.time() - start_time
            
            result = {
                'test_name': 'Integration.ErrorHandlingMain',
                'status': 'PASSED' if exit_code == 0 else 'FAILED',
                'error': None if exit_code == 0 else f"Exit code: {exit_code}",
                'duration': duration,
                'details': 'Main error handling integration test'
            }
            
            if result['status'] == 'PASSED':
                self.logger.info(f"✅ {result['test_name']} - {result['duration']:.3f}s")
            else:
                self.logger.error(f"❌ {result['test_name']} - {result['error']}")
            
            return [result]
            
        except Exception as e:
            result = {
                'test_name': 'Integration.ErrorHandlingMain',
                'status': 'FAILED',
                'error': str(e),
                'duration': 0,
                'details': traceback.format_exc()
            }
            self.logger.error(f"❌ {result['test_name']} - {result['error']}")
            return [result]
    
    def run_all_tests(self):
        """Run all test suites."""
        self.results['start_time'] = datetime.now()
        self.logger.info("🚀 Starting Comprehensive Test Suite...")
        
        # Test classes to run
        test_classes = [
            # Error handling tests
            TestCircuitBreaker,
            TestRetryHandler,
            TestDataValidation,
            TestErrorBoundary,
            TestHealthMonitor,
            TestPerformance,
            
            # Validation tests
            TestMarketDataValidation,
            TestTradeSignalValidation,
            TestOrderBlockValidation,
            TestAnomalyDetection,
            TestValidationPerformance,
            TestEdgeCases,
            
            # Degradation tests
            TestGracefulDegradation,
            TestRecoveryMechanisms,
            TestStressTesting,
            TestPerformanceDegradation,
            TestEdgeCaseDegradation,
        ]
        
        # Run unit tests
        for test_class in test_classes:
            try:
                class_results = self.run_test_class(test_class)
                self.results['test_details'].extend(class_results)
            except Exception as e:
                self.logger.error(f"Failed to run test class {test_class.__name__}: {e}")
        
        # Run integration tests
        integration_results = self.run_integration_tests()
        self.results['test_details'].extend(integration_results)
        
        # Calculate statistics
        self.calculate_statistics()
        
        self.results['end_time'] = datetime.now()
        self.logger.info("🏁 Test Suite Completed!")
    
    def calculate_statistics(self):
        """Calculate test statistics."""
        for result in self.results['test_details']:
            self.results['total_tests'] += 1
            
            if result['status'] == 'PASSED':
                self.results['passed_tests'] += 1
            elif result['status'] == 'FAILED':
                self.results['failed_tests'] += 1
            else:
                self.results['skipped_tests'] += 1
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        report = f"""
# SMC Trading Agent - Comprehensive Test Report

## Test Summary
- **Total Tests**: {self.results['total_tests']}
- **Passed**: {self.results['passed_tests']} ✅
- **Failed**: {self.results['failed_tests']} ❌
- **Skipped**: {self.results['skipped_tests']} ⏭️
- **Success Rate**: {(self.results['passed_tests'] / self.results['total_tests'] * 100):.1f}%
- **Duration**: {duration:.2f} seconds

## Test Categories

### Error Handling Tests
- Circuit Breaker: {self.count_tests_by_category('TestCircuitBreaker')}
- Retry Handler: {self.count_tests_by_category('TestRetryHandler')}
- Data Validation: {self.count_tests_by_category('TestDataValidation')}
- Error Boundary: {self.count_tests_by_category('TestErrorBoundary')}
- Health Monitor: {self.count_tests_by_category('TestHealthMonitor')}
- Performance: {self.count_tests_by_category('TestPerformance')}

### Validation Tests
- Market Data Validation: {self.count_tests_by_category('TestMarketDataValidation')}
- Trade Signal Validation: {self.count_tests_by_category('TestTradeSignalValidation')}
- Order Block Validation: {self.count_tests_by_category('TestOrderBlockValidation')}
- Anomaly Detection: {self.count_tests_by_category('TestAnomalyDetection')}
- Validation Performance: {self.count_tests_by_category('TestValidationPerformance')}
- Edge Cases: {self.count_tests_by_category('TestEdgeCases')}

### Degradation Tests
- Graceful Degradation: {self.count_tests_by_category('TestGracefulDegradation')}
- Recovery Mechanisms: {self.count_tests_by_category('TestRecoveryMechanisms')}
- Stress Testing: {self.count_tests_by_category('TestStressTesting')}
- Performance Degradation: {self.count_tests_by_category('TestPerformanceDegradation')}
- Edge Case Degradation: {self.count_tests_by_category('TestEdgeCaseDegradation')}

## Failed Tests
"""
        
        failed_tests = [r for r in self.results['test_details'] if r['status'] == 'FAILED']
        if failed_tests:
            for test in failed_tests:
                report += f"""
### {test['test_name']}
- **Error**: {test['error']}
- **Duration**: {test['duration']:.3f}s
- **Details**: {test['details']}
"""
        else:
            report += "\n🎉 No failed tests!\n"
        
        report += f"""
## Performance Summary
- **Average Test Duration**: {self.calculate_average_duration():.3f}s
- **Longest Test**: {self.find_longest_test()}
- **Shortest Test**: {self.find_shortest_test()}

## Recommendations
"""
        
        if self.results['failed_tests'] > 0:
            report += "- Investigate and fix failed tests\n"
        else:
            report += "- All tests passing! System is robust and reliable\n"
        
        if self.calculate_average_duration() > 1.0:
            report += "- Consider optimizing slow tests\n"
        
        report += "- Continue monitoring system performance in production\n"
        report += "- Regular test execution recommended\n"
        
        return report
    
    def count_tests_by_category(self, category: str) -> str:
        """Count tests by category."""
        category_tests = [r for r in self.results['test_details'] if category in r['test_name']]
        passed = len([r for r in category_tests if r['status'] == 'PASSED'])
        total = len(category_tests)
        return f"{passed}/{total} passed"
    
    def calculate_average_duration(self) -> float:
        """Calculate average test duration."""
        if not self.results['test_details']:
            return 0.0
        total_duration = sum(r['duration'] for r in self.results['test_details'])
        return total_duration / len(self.results['test_details'])
    
    def find_longest_test(self) -> str:
        """Find the longest running test."""
        if not self.results['test_details']:
            return "N/A"
        longest = max(self.results['test_details'], key=lambda x: x['duration'])
        return f"{longest['test_name']} ({longest['duration']:.3f}s)"
    
    def find_shortest_test(self) -> str:
        """Find the shortest running test."""
        if not self.results['test_details']:
            return "N/A"
        shortest = min(self.results['test_details'], key=lambda x: x['duration'])
        return f"{shortest['test_name']} ({shortest['duration']:.3f}s)"
    
    def save_report(self, report: str):
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_report_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        self.logger.info(f"📄 Test report saved to: {filename}")
    
    def run(self):
        """Run the complete test suite."""
        try:
            self.run_all_tests()
            report = self.generate_report()
            print(report)
            self.save_report(report)
            
            # Return exit code based on test results
            return 0 if self.results['failed_tests'] == 0 else 1
            
        except Exception as e:
            self.logger.error(f"Test runner failed: {e}")
            return 1


def main():
    """Main entry point."""
    runner = TestRunner()
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())


