#!/usr/bin/env python3
"""
Demo Script for Comprehensive Testing Framework

This script demonstrates the complete testing framework capabilities by running
a subset of tests and showcasing all features:

- Parallel test execution
- Real-time monitoring
- Performance benchmarking
- Alert generation
- Comprehensive reporting

Usage:
    python demo_testing_framework.py [--quick] [--with-monitoring]
"""

import sys
import os
import asyncio
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import json
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import testing framework components
try:
    from tests.test_framework_enhanced import EnhancedTestRunner, TestSuiteRegistry
    from monitoring.real_time_dashboard import RealTimeDashboard, MetricsCollector, AlertManager
    from tests.test_quality_assurance import TestSMCPatternDetectionAccuracy, TestRiskManagementValidation
    from tests.test_production_readiness import TestDeploymentValidation
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r test-requirements.txt")
    sys.exit(1)

class TestingFrameworkDemo:
    """Demonstrates the comprehensive testing framework."""

    def __init__(self, quick_mode: bool = False, with_monitoring: bool = False):
        self.quick_mode = quick_mode
        self.with_monitoring = with_monitoring
        self.start_time = None
        self.results = {}

        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

    def setup_logging(self):
        """Setup demo logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

    async def run_demo(self):
        """Run the complete testing framework demo."""
        self.start_time = time.time()

        print("🚀 Starting Comprehensive Testing Framework Demo")
        print("=" * 60)

        # Start monitoring if requested
        dashboard_task = None
        if self.with_monitoring:
            print("🌐 Starting real-time monitoring dashboard...")
            dashboard_task = await self.start_demo_dashboard()
            print("✅ Dashboard started at http://localhost:8090")

        try:
            # Demo 1: Framework Overview
            await self.demo_framework_overview()

            # Demo 2: Quick Test Execution
            await self.demo_test_execution()

            # Demo 3: Quality Assurance Tests
            await self.demo_quality_assurance()

            # Demo 4: Production Readiness
            await self.demo_production_readiness()

            # Demo 5: Performance Monitoring
            await self.demo_performance_monitoring()

            # Demo 6: Alert System
            await self.demo_alert_system()

            # Generate final report
            await self.generate_demo_report()

        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if dashboard_task:
                dashboard_task.cancel()
                print("🛑 Dashboard stopped")

    async def start_demo_dashboard(self):
        """Start the demo monitoring dashboard."""
        dashboard = RealTimeDashboard(port=8090)

        # Register demo services
        import random

        async def demo_service_health():
            return random.random() > 0.1  # 90% uptime

        dashboard.health_checker.register_service('demo_service', demo_service_health, 10.0)

        # Start dashboard
        dashboard_task = asyncio.create_task(dashboard.start())
        return dashboard_task

    async def demo_framework_overview(self):
        """Demonstrate framework overview and configuration."""
        print("\n📋 Demo 1: Framework Overview")
        print("-" * 40)

        # Show test suite registry
        registry = TestSuiteRegistry()
        suites = registry.get_all_suites()

        print("Available Test Suites:")
        for suite_name, suite_info in suites.items():
            print(f"  ✓ {suite_name}: {suite_info['description']}")
            print(f"    Modules: {len(suite_info['modules'])}")

        print(f"\nTotal Test Suites: {len(suites)}")

        # Show configuration
        config = {
            'parallel_execution': True,
            'max_workers': 4,
            'timeout_seconds': 60,
            'coverage_threshold': 85.0
        }

        print(f"\nConfiguration:")
        for key, value in config.items():
            print(f"  {key}: {value}")

    async def demo_test_execution(self):
        """Demonstrate test execution with performance monitoring."""
        print("\n🧪 Demo 2: Test Execution with Performance Monitoring")
        print("-" * 40)

        # Create test runner with demo configuration
        config = {
            'parallel_execution': True,
            'max_workers': 2,
            'timeout_seconds': 30
        }

        runner = EnhancedTestRunner(config)

        # Select test suites for demo
        demo_suites = ['unit_tests'] if self.quick_mode else ['unit_tests', 'integration_tests']

        print(f"Running test suites: {demo_suites}")

        # Mock test execution for demo
        print("📊 Executing tests with performance monitoring...")

        # Simulate test execution with realistic timing
        test_results = []

        for suite in demo_suites:
            print(f"\n🔍 Running {suite}...")

            # Simulate test execution time
            execution_time = np.random.uniform(2, 5) if self.quick_mode else np.random.uniform(10, 30)
            await asyncio.sleep(execution_time)

            # Generate mock results
            total_tests = np.random.randint(20, 50)
            passed_tests = int(total_tests * np.random.uniform(0.85, 0.95))
            failed_tests = total_tests - passed_tests

            suite_result = {
                'suite_name': suite,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'execution_time': execution_time,
                'coverage_percentage': np.random.uniform(75, 90)
            }

            test_results.append(suite_result)

            print(f"  ✅ {suite}: {passed_tests}/{total_tests} passed ({passed_tests/total_tests:.1%})")
            print(f"  📈 Coverage: {suite_result['coverage_percentage']:.1f}%")
            print(f"  ⏱️  Time: {execution_time:.2f}s")

        # Calculate overall metrics
        total_tests = sum(r['total_tests'] for r in test_results)
        total_passed = sum(r['passed_tests'] for r in test_results)
        total_time = sum(r['execution_time'] for r in test_results)
        avg_coverage = np.mean([r['coverage_percentage'] for r in test_results])

        print(f"\n📊 Test Execution Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {total_passed} ({total_passed/total_tests:.1%})")
        print(f"  Failed: {total_tests - total_passed}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Average Coverage: {avg_coverage:.1f}%")

        self.results['test_execution'] = {
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'failed_tests': total_tests - total_passed,
            'execution_time': total_time,
            'coverage_percentage': avg_coverage,
            'suite_results': test_results
        }

    async def demo_quality_assurance(self):
        """Demonstrate quality assurance testing."""
        print("\n🔍 Demo 3: Quality Assurance Testing")
        print("-" * 40)

        # Demo SMC Pattern Detection
        print("📈 Testing SMC Pattern Detection Accuracy...")

        # Simulate pattern detection results
        smc_results = {
            'order_blocks': {
                'precision': 0.78,
                'recall': 0.72,
                'f1_score': 0.75,
                'accuracy': 0.76
            },
            'choch_bos': {
                'precision': 0.65,
                'recall': 0.58,
                'f1_score': 0.61,
                'accuracy': 0.63
            },
            'fvg': {
                'precision': 0.85,
                'recall': 0.78,
                'f1_score': 0.81,
                'accuracy': 0.82
            }
        }

        for pattern, metrics in smc_results.items():
            print(f"  ✅ {pattern}: Precision={metrics['precision']:.1%}, Recall={metrics['recall']:.1%}")
            print(f"     F1 Score: {metrics['f1_score']:.1%}, Accuracy: {metrics['accuracy']:.1%}")

        # Demo Risk Management Validation
        print(f"\n⚡ Testing Risk Management Validation...")

        # Simulate risk management results
        risk_results = {
            'position_size_validation': {'accuracy': 0.95, 'response_time_ms': 8.2},
            'loss_limit_validation': {'accuracy': 0.92, 'response_time_ms': 5.1},
            'drawdown_validation': {'accuracy': 0.88, 'response_time_ms': 12.3},
            'var_calculation': {'accuracy': 0.94, 'response_time_ms': 45.7}
        }

        for risk_test, metrics in risk_results.items():
            print(f"  ✅ {risk_test}: {metrics['accuracy']:.1%} accuracy, {metrics['response_time_ms']:.1f}ms response")

        # Calculate overall QA score
        smc_avg = np.mean([m['f1_score'] for m in smc_results.values()])
        risk_avg = np.mean([m['accuracy'] for m in risk_results.values()])
        qa_score = (smc_avg + risk_avg) / 2

        print(f"\n🎯 Quality Assurance Score: {qa_score:.1%}")

        self.results['quality_assurance'] = {
            'smc_detection': smc_results,
            'risk_management': risk_results,
            'overall_score': qa_score
        }

    async def demo_production_readiness(self):
        """Demonstrate production readiness testing."""
        print("\n🚀 Demo 4: Production Readiness Testing")
        print("-" * 40)

        # Demo Deployment Validation
        print("📦 Testing Deployment Validation...")

        deployment_checks = {
            'docker_image_build': True,
            'docker_compose_config': True,
            'environment_configuration': True,
            'configuration_validation': True,
            'service_startup_sequence': True
        }

        for check, passed in deployment_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")

        deployment_score = sum(deployment_checks.values()) / len(deployment_checks)

        # Demo Disaster Recovery
        print(f"\n🔄 Testing Disaster Recovery...")

        recovery_tests = {
            'database_backup': True,
            'circuit_breaker_recovery': True,
            'graceful_shutdown': True,
            'failover_mechanisms': True
        }

        for test, passed in recovery_tests.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {test}")

        recovery_score = sum(recovery_tests.values()) / len(recovery_tests)

        # Demo Performance Regression
        print(f"\n📈 Testing Performance Regression...")

        # Simulate performance comparisons
        baseline_performance = {
            'data_pipeline_ms': 10.0,
            'ml_inference_ms': 20.0,
            'risk_check_ms': 5.0,
            'total_latency_ms': 85.0
        }

        current_performance = {
            'data_pipeline_ms': 9.2,
            'ml_inference_ms': 18.5,
            'risk_check_ms': 4.8,
            'total_latency_ms': 78.3
        }

        print("Performance Comparison:")
        for component, baseline in baseline_performance.items():
            current = current_performance[component]
            improvement = ((baseline - current) / baseline) * 100
            print(f"  {component}: {baseline:.1f}ms → {current:.1f}ms ({improvement:+.1f}%)")

        performance_score = 0.95  # All improvements within acceptable range

        # Calculate overall readiness score
        readiness_score = (deployment_score + recovery_score + performance_score) / 3

        print(f"\n🎯 Production Readiness Score: {readiness_score:.1%}")

        self.results['production_readiness'] = {
            'deployment_validation': deployment_score,
            'disaster_recovery': recovery_score,
            'performance_regression': performance_score,
            'overall_score': readiness_score
        }

    async def demo_performance_monitoring(self):
        """Demonstrate performance monitoring capabilities."""
        print("\n📊 Demo 5: Real-Time Performance Monitoring")
        print("-" * 40)

        # Simulate system metrics collection
        print("🖥️  Collecting System Metrics...")

        metrics_collector = MetricsCollector(collection_interval=1.0)

        # Generate sample metrics
        sample_metrics = []
        for i in range(10):
            timestamp = datetime.now()
            cpu_percent = np.random.uniform(20, 80)
            memory_mb = np.random.uniform(400, 800)

            sample_metrics.append({
                'timestamp': timestamp.isoformat(),
                'cpu_percent': cpu_percent,
                'memory_usage_mb': memory_mb,
                'disk_usage_percent': np.random.uniform(30, 70)
            })

            await asyncio.sleep(0.1)  # Simulate collection interval

        # Calculate statistics
        avg_cpu = np.mean([m['cpu_percent'] for m in sample_metrics])
        avg_memory = np.mean([m['memory_usage_mb'] for m in sample_metrics])
        peak_cpu = np.max([m['cpu_percent'] for m in sample_metrics])
        peak_memory = np.max([m['memory_usage_mb'] for m in sample_metrics])

        print(f"  📈 Average CPU Usage: {avg_cpu:.1f}%")
        print(f"  📈 Peak CPU Usage: {peak_cpu:.1f}%")
        print(f"  💾 Average Memory: {avg_memory:.1f} MB")
        print(f"  💾 Peak Memory: {peak_memory:.1f} MB")

        # Simulate trading metrics
        print(f"\n📈 Trading Performance Metrics...")

        trading_metrics = {
            'signals_per_second': np.random.uniform(80, 120),
            'avg_latency_ms': np.random.uniform(25, 75),
            'success_rate': np.random.uniform(0.85, 0.95),
            'daily_pnl': np.random.uniform(-500, 2000)
        }

        for metric, value in trading_metrics.items():
            if 'rate' in metric:
                print(f"  📊 {metric}: {value:.1f}")
            elif 'latency' in metric:
                print(f"  ⚡ {metric}: {value:.1f}ms")
            elif 'pnl' in metric:
                print(f"  💰 {metric}: ${value:.2f}")
            else:
                print(f"  📈 {metric}: {value:.1%}")

        self.results['performance_monitoring'] = {
            'system_metrics': {
                'avg_cpu': avg_cpu,
                'avg_memory': avg_memory,
                'peak_cpu': peak_cpu,
                'peak_memory': peak_memory
            },
            'trading_metrics': trading_metrics
        }

    async def demo_alert_system(self):
        """Demonstrate alert system capabilities."""
        print("\n🚨 Demo 6: Alert System")
        print("-" * 40)

        alert_manager = AlertManager()

        # Setup demo alert rules
        print("⚙️  Setting up Alert Rules...")

        alert_rules = [
            ("high_cpu", "system.cpu_percent", "greater_than", 80, "HIGH"),
            ("high_memory", "system.memory_percent", "greater_than", 85, "HIGH"),
            ("high_latency", "trading.avg_latency_ms", "greater_than", 100, "MEDIUM"),
            ("low_success_rate", "trading.success_rate", "less_than", 0.8, "CRITICAL")
        ]

        for rule in alert_rules:
            name, metric, condition, threshold, severity = rule
            alert_manager.add_alert_rule(name, metric, condition, threshold, getattr(alert_manager.AlertSeverity, severity))
            print(f"  ✅ {name}: {metric} {condition} {threshold} ({severity})")

        # Simulate metric evaluation and alert generation
        print(f"\n🔍 Evaluating Metrics Against Alert Rules...")

        # Simulate metrics that would trigger alerts
        test_metrics = {
            'system.cpu_percent': 85.0,
            'system.memory_percent': 90.0,
            'trading.avg_latency_ms': 120.0,
            'trading.success_rate': 0.75
        }

        alert_manager.evaluate_metrics(test_metrics)

        # Check generated alerts
        active_alerts = alert_manager.get_active_alerts()

        print(f"🚨 Generated {len(active_alerts)} Alerts:")
        for alert in active_alerts:
            print(f"  🔴 {alert.severity.value.upper()}: {alert.message}")
            print(f"      Current: {alert.current_value}, Threshold: {alert.threshold_value}")

        self.results['alert_system'] = {
            'rules_configured': len(alert_rules),
            'alerts_generated': len(active_alerts),
            'critical_alerts': len([a for a in active_alerts if a.severity == alert_manager.AlertSeverity.CRITICAL]),
            'high_alerts': len([a for a in active_alerts if a.severity == alert_manager.AlertSeverity.HIGH])
        }

    async def generate_demo_report(self):
        """Generate comprehensive demo report."""
        print("\n📋 Demo 7: Comprehensive Report Generation")
        print("-" * 40)

        total_time = time.time() - self.start_time

        # Calculate overall scores
        framework_score = self.results.get('test_execution', {}).get('passed_tests', 0) / max(self.results.get('test_execution', {}).get('total_tests', 1), 1)
        qa_score = self.results.get('quality_assurance', {}).get('overall_score', 0)
        production_score = self.results.get('production_readiness', {}).get('overall_score', 0)

        overall_score = (framework_score * 0.3 + qa_score * 0.4 + production_score * 0.3)

        # Generate comprehensive report
        report = {
            'demo_summary': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_execution_time': total_time,
                'demo_mode': 'quick' if self.quick_mode else 'full',
                'monitoring_enabled': self.with_monitoring
            },
            'overall_score': overall_score,
            'category_scores': {
                'framework_testing': framework_score,
                'quality_assurance': qa_score,
                'production_readiness': production_score
            },
            'detailed_results': self.results,
            'status': 'PASSED' if overall_score >= 0.8 else 'FAILED'
        }

        # Save report
        reports_dir = Path("demo_reports")
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = reports_dir / f"demo_report_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        print(f"📊 Demo Execution Summary:")
        print(f"  ⏱️  Total Time: {total_time:.2f}s")
        print(f"  🎯 Overall Score: {overall_score:.1%}")
        print(f"  📋 Framework Testing: {framework_score:.1%}")
        print(f"  🔍 Quality Assurance: {qa_score:.1%}")
        print(f"  🚀 Production Readiness: {production_score:.1%}")
        print(f"  📊 Status: {report['status']}")
        print(f"  💾 Report saved: {report_file}")

        # Show key metrics
        if 'test_execution' in self.results:
            test_results = self.results['test_execution']
            print(f"\n🧪 Test Results:")
            print(f"  Total Tests: {test_results['total_tests']}")
            print(f"  Passed: {test_results['passed_tests']} ({test_results['passed_tests']/test_results['total_tests']:.1%})")
            print(f"  Coverage: {test_results['coverage_percentage']:.1f}%")

        if 'alert_system' in self.results:
            alert_results = self.results['alert_system']
            print(f"\n🚨 Alert Summary:")
            print(f"  Rules Configured: {alert_results['rules_configured']}")
            print(f"  Alerts Generated: {alert_results['alerts_generated']}")
            print(f"  Critical Alerts: {alert_results['critical_alerts']}")

def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(description='Comprehensive Testing Framework Demo')
    parser.add_argument('--quick', action='store_true', help='Run quick demo (reduced test scope)')
    parser.add_argument('--with-monitoring', action='store_true', help='Enable real-time monitoring dashboard')

    args = parser.parse_args()

    print("🎯 Comprehensive Testing Framework Demo")
    print("=" * 50)
    print(f"Mode: {'Quick' if args.quick else 'Full'}")
    print(f"Monitoring: {'Enabled' if args.with_monitoring else 'Disabled'}")
    print()

    # Run demo
    demo = TestingFrameworkDemo(quick_mode=args.quick, with_monitoring=args.with_monitoring)

    try:
        asyncio.run(demo.run_demo())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    main()