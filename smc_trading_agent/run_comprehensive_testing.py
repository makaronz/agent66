#!/usr/bin/env python3
"""
Comprehensive Testing Runner for Enhanced SMC Trading System

This script orchestrates the complete testing framework including:

1. Automated Testing Framework
2. Quality Assurance Tests
3. Real-Time Monitoring
4. Production Readiness Tests

Features:
- Parallel test execution
- Real-time progress monitoring
- Comprehensive reporting
- Integration with CI/CD pipelines
- Performance benchmarking
"""

import sys
import os
import asyncio
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import threading
import websockets
import aiohttp
from aiohttp import web
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test framework components
from tests.test_framework_enhanced import EnhancedTestRunner, FrameworkReport, TestSuiteRegistry
from tests.test_production_readiness import test_production_readiness_integration
from tests.test_quality_assurance import test_quality_assurance_integration

# Import monitoring components
from monitoring.real_time_dashboard import RealTimeDashboard, MetricsCollector, AlertManager

class ComprehensiveTestOrchestrator:
    """Orchestrates comprehensive testing with real-time monitoring."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.test_runner = EnhancedTestRunner()
        self.metrics_collector = MetricsCollector(collection_interval=2.0)
        self.alert_manager = AlertManager()
        self.dashboard = None
        self.test_results = {}
        self.start_time = None
        self.websocket_connections = set()

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup comprehensive logging."""
        log_dir = Path("test_logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)

    async def start_monitoring_dashboard(self, port: int = 8090):
        """Start the real-time monitoring dashboard for testing."""
        self.dashboard = RealTimeDashboard(port=port)

        # Setup test-specific monitoring
        await self._setup_test_monitoring()

        # Start dashboard in background
        dashboard_task = asyncio.create_task(self._run_dashboard())

        self.logger.info(f"Test monitoring dashboard started on port {port}")
        return dashboard_task

    async def _setup_test_monitoring(self):
        """Setup test-specific monitoring and alerts."""
        # Add test-specific alert rules
        self.alert_manager.add_alert_rule(
            "test_failure_rate", "test.failure_rate", "greater_than", 0.1,
            self.alert_manager.AlertSeverity.HIGH
        )
        self.alert_manager.add_alert_rule(
            "test_execution_time", "test.execution_time", "greater_than", 300,
            self.alert_manager.AlertSeverity.MEDIUM
        )
        self.alert_manager.add_alert_rule(
            "memory_usage", "system.memory_percent", "greater_than", 80,
            self.alert_manager.AlertSeverity.HIGH
        )

    async def _run_dashboard(self):
        """Run the monitoring dashboard."""
        await self.dashboard.start()

    async def run_comprehensive_tests(self,
                                    include_unit: bool = True,
                                    include_integration: bool = True,
                                    include_e2e: bool = True,
                                    include_performance: bool = True,
                                    include_quality: bool = True,
                                    include_production: bool = True,
                                    parallel: bool = True) -> Dict[str, Any]:
        """Run comprehensive test suite with monitoring."""
        self.start_time = time.time()
        self.logger.info("Starting comprehensive test execution")

        # Start monitoring
        await self.metrics_collector.start_collection()

        # Determine which test suites to run
        test_suites = []
        if include_unit:
            test_suites.append('unit_tests')
        if include_integration:
            test_suites.append('integration_tests')
        if include_e2e:
            test_suites.append('end_to_end_tests')
        if include_performance:
            test_suites.append('performance_tests')

        # Run framework tests
        framework_report = await self._run_framework_tests(test_suites, parallel)
        self.test_results['framework'] = framework_report

        # Run quality assurance tests
        if include_quality:
            qa_report = await self._run_quality_assurance_tests()
            self.test_results['quality_assurance'] = qa_report

        # Run production readiness tests
        if include_production:
            production_report = await self._run_production_readiness_tests()
            self.test_results['production_readiness'] = production_report

        # Generate comprehensive report
        comprehensive_report = await self._generate_comprehensive_report()

        # Stop monitoring
        self.metrics_collector.stop_collection()

        self.logger.info(f"Comprehensive testing completed in {time.time() - self.start_time:.2f}s")

        return comprehensive_report

    async def _run_framework_tests(self, test_suites: List[str], parallel: bool) -> FrameworkReport:
        """Run the enhanced test framework."""
        self.logger.info(f"Running framework test suites: {test_suites}")

        # Update test runner config
        config = self.test_runner.config.copy()
        config['parallel_execution'] = parallel

        self.test_runner = EnhancedTestRunner(config)

        # Run tests
        report = self.test_runner.run_all_tests(test_suites)

        # Broadcast results to dashboard
        if self.dashboard:
            await self._broadcast_test_results('framework', report)

        return report

    async def _run_quality_assurance_tests(self) -> Dict[str, Any]:
        """Run quality assurance tests."""
        self.logger.info("Running quality assurance tests")

        try:
            qa_result = await test_quality_assurance_integration()

            # Broadcast results to dashboard
            if self.dashboard:
                await self._broadcast_test_results('quality_assurance', qa_result)

            return qa_result

        except Exception as e:
            self.logger.error(f"Quality assurance tests failed: {e}")
            return {
                'qa_score': 0.0,
                'test_results': {},
                'overall_status': 'failed',
                'error': str(e)
            }

    async def _run_production_readiness_tests(self) -> Dict[str, Any]:
        """Run production readiness tests."""
        self.logger.info("Running production readiness tests")

        try:
            production_result = await test_production_readiness_integration()

            # Broadcast results to dashboard
            if self.dashboard:
                await self._broadcast_test_results('production_readiness', production_result)

            return production_result

        except Exception as e:
            self.logger.error(f"Production readiness tests failed: {e}")
            return {
                'readiness_score': 0.0,
                'test_results': {},
                'overall_status': 'not_ready',
                'error': str(e)
            }

    async def _broadcast_test_results(self, test_type: str, results: Dict[str, Any]):
        """Broadcast test results to monitoring dashboard."""
        if not self.dashboard:
            return

        await self.dashboard.broadcast_update({
            'type': 'test_results',
            'test_type': test_type,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    async def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive testing report."""
        total_execution_time = time.time() - self.start_time

        # Calculate overall scores
        framework_score = 0.0
        if 'framework' in self.test_results:
            framework = self.test_results['framework']
            framework_score = framework.passed_tests / max(framework.total_tests, 1)

        qa_score = self.test_results.get('quality_assurance', {}).get('qa_score', 0.0)
        production_score = self.test_results.get('production_readiness', {}).get('readiness_score', 0.0)

        overall_score = (framework_score * 0.4 + qa_score * 0.3 + production_score * 0.3)

        # Generate recommendations
        recommendations = self._generate_recommendations()

        # Get performance metrics
        performance_metrics = self._get_performance_metrics()

        comprehensive_report = {
            'execution_summary': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_execution_time': total_execution_time,
                'overall_score': overall_score,
                'status': 'passed' if overall_score >= 0.8 else 'failed'
            },
            'test_results': self.test_results,
            'scores': {
                'framework': framework_score,
                'quality_assurance': qa_score,
                'production_readiness': production_score,
                'overall': overall_score
            },
            'performance_metrics': performance_metrics,
            'recommendations': recommendations,
            'alert_summary': {
                'total_alerts': len(self.alert_manager.get_active_alerts()),
                'critical_alerts': len([a for a in self.alert_manager.get_active_alerts() if a.severity == self.alert_manager.AlertSeverity.CRITICAL]),
                'high_alerts': len([a for a in self.alert_manager.get_active_alerts() if a.severity == self.alert_manager.AlertSeverity.HIGH])
            }
        }

        # Save comprehensive report
        await self._save_comprehensive_report(comprehensive_report)

        return comprehensive_report

    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations based on test results."""
        recommendations = []

        # Framework recommendations
        if 'framework' in self.test_results:
            framework = self.test_results['framework']
            if framework.overall_coverage < 85:
                recommendations.append(f"Increase test coverage from {framework.overall_coverage:.1f}% to 85%+")

            failed_suites = [sr.suite_name for sr in framework.suite_results if sr.failed_tests > 0]
            if failed_suites:
                recommendations.append(f"Address test failures in: {', '.join(failed_suites)}")

        # Quality assurance recommendations
        qa_score = self.test_results.get('quality_assurance', {}).get('qa_score', 0.0)
        if qa_score < 0.8:
            recommendations.append(f"Improve quality assurance score from {qa_score:.1%} to 80%+")

        # Production readiness recommendations
        prod_score = self.test_results.get('production_readiness', {}).get('readiness_score', 0.0)
        if prod_score < 0.8:
            recommendations.append(f"Enhance production readiness from {prod_score:.1%} to 80%+")

        # Performance recommendations
        system_metrics = list(self.metrics_collector.metrics_history['system'])
        if system_metrics:
            avg_memory = np.mean([m.memory_percent for m in system_metrics])
            if avg_memory > 70:
                recommendations.append(f"Optimize memory usage (average: {avg_memory:.1f}%)")

        return recommendations

    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from the testing session."""
        system_metrics = list(self.metrics_collector.metrics_history['system'])

        if not system_metrics:
            return {}

        return {
            'peak_memory_mb': max(m.memory_usage_mb for m in system_metrics),
            'avg_memory_percent': np.mean([m.memory_percent for m in system_metrics]),
            'peak_cpu_percent': max(m.cpu_percent for m in system_metrics),
            'avg_cpu_percent': np.mean([m.cpu_percent for m in system_metrics]),
            'total_data_points': len(system_metrics),
            'collection_duration': (system_metrics[-1].timestamp - system_metrics[0].timestamp).total_seconds() if len(system_metrics) > 1 else 0
        }

    async def _save_comprehensive_report(self, report: Dict[str, Any]):
        """Save comprehensive report to files."""
        reports_dir = Path("test_reports")
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON report
        json_file = reports_dir / f"comprehensive_test_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save HTML report
        html_file = reports_dir / f"comprehensive_test_report_{timestamp}.html"
        html_content = self._generate_html_report(report)
        with open(html_file, 'w') as f:
            f.write(html_content)

        # Save summary
        summary_file = reports_dir / f"test_summary_{timestamp}.txt"
        summary_content = self._generate_text_summary(report)
        with open(summary_file, 'w') as f:
            f.write(summary_content)

        self.logger.info(f"Comprehensive report saved to {reports_dir}")

    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML version of the comprehensive report."""
        execution_summary = report['execution_summary']
        scores = report['scores']
        recommendations = report['recommendations']

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Test Report - SMC Trading System</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .status-{{execution_summary['status']}} {{ color: {'green' if execution_summary['status'] == 'passed' else 'red'} }; font-size: 24px; font-weight: bold; }}
        .score-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
        .score-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .score-value {{ font-size: 36px; font-weight: bold; color: #2196f3; }}
        .score-label {{ color: #666; margin-top: 5px; }}
        .section {{ margin: 30px 0; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #2196f3; padding-bottom: 10px; }}
        .recommendations {{ background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; }}
        .recommendations ul {{ margin: 0; padding-left: 20px; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .metrics-table th, .metrics-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        .metrics-table th {{ background: #f8f9fa; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Comprehensive Test Report</h1>
            <h2>SMC Trading System - Enhanced Version</h2>
            <p class="status-{execution_summary['status']}">
                {execution_summary['status'].upper()}
            </p>
            <p>Overall Score: {scores['overall']:.1%}</p>
        </div>

        <div class="section">
            <h2>Execution Summary</h2>
            <table class="metrics-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Start Time</td>
                    <td>{execution_summary['start_time']}</td>
                </tr>
                <tr>
                    <td>End Time</td>
                    <td>{execution_summary['end_time']}</td>
                </tr>
                <tr>
                    <td>Total Execution Time</td>
                    <td>{execution_summary['total_execution_time']:.2f} seconds</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Test Scores</h2>
            <div class="score-grid">
                <div class="score-card">
                    <div class="score-value">{scores['framework']:.1%}</div>
                    <div class="score-label">Framework Tests</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{scores['quality_assurance']:.1%}</div>
                    <div class="score-label">Quality Assurance</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{scores['production_readiness']:.1%}</div>
                    <div class="score-label">Production Readiness</div>
                </div>
                <div class="score-card">
                    <div class="score-value">{scores['overall']:.1%}</div>
                    <div class="score-label">Overall Score</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Performance Metrics</h2>
            <table class="metrics-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Peak Memory Usage</td>
                    <td>{report['performance_metrics'].get('peak_memory_mb', 0):.1f} MB</td>
                </tr>
                <tr>
                    <td>Average Memory Usage</td>
                    <td>{report['performance_metrics'].get('avg_memory_percent', 0):.1f}%</td>
                </tr>
                <tr>
                    <td>Peak CPU Usage</td>
                    <td>{report['performance_metrics'].get('peak_cpu_percent', 0):.1f}%</td>
                </tr>
                <tr>
                    <td>Average CPU Usage</td>
                    <td>{report['performance_metrics'].get('avg_cpu_percent', 0):.1f}%</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <div class="recommendations">
                {'<ul>' + ''.join(f'<li>{rec}</li>' for rec in recommendations) + '</ul>' if recommendations else '<p>No recommendations - All tests passed!</p>'}
            </div>
        </div>

        <div class="section">
            <h2>Alert Summary</h2>
            <table class="metrics-table">
                <tr>
                    <th>Alert Type</th>
                    <th>Count</th>
                </tr>
                <tr>
                    <td>Total Alerts</td>
                    <td>{report['alert_summary']['total_alerts']}</td>
                </tr>
                <tr>
                    <td>Critical Alerts</td>
                    <td>{report['alert_summary']['critical_alerts']}</td>
                </tr>
                <tr>
                    <td>High Priority Alerts</td>
                    <td>{report['alert_summary']['high_alerts']}</td>
                </tr>
            </table>
        </div>
    </div>
</body>
</html>
        """

    def _generate_text_summary(self, report: Dict[str, Any]) -> str:
        """Generate text summary of the comprehensive report."""
        execution_summary = report['execution_summary']
        scores = report['scores']

        summary = f"""
COMPREHENSIVE TEST REPORT SUMMARY
================================

Execution Status: {execution_summary['status'].upper()}
Overall Score: {scores['overall']:.1%}
Execution Time: {execution_summary['total_execution_time']:.2f} seconds

TEST SCORES
-----------
Framework Tests: {scores['framework']:.1%}
Quality Assurance: {scores['quality_assurance']:.1%}
Production Readiness: {scores['production_readiness']:.1%}

PERFORMANCE METRICS
------------------
Peak Memory: {report['performance_metrics'].get('peak_memory_mb', 0):.1f} MB
Average CPU: {report['performance_metrics'].get('avg_cpu_percent', 0):.1f}%
Peak CPU: {report['performance_metrics'].get('peak_cpu_percent', 0):.1f}%

ALERT SUMMARY
-------------
Total Alerts: {report['alert_summary']['total_alerts']}
Critical: {report['alert_summary']['critical_alerts']}
High: {report['alert_summary']['high_alerts']}

RECOMMENDATIONS
---------------
{chr(10).join(f'- {rec}' for rec in report['recommendations']) if report['recommendations'] else 'No recommendations - All tests passed!'}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        return summary.strip()

def main():
    """Main entry point for comprehensive testing."""
    parser = argparse.ArgumentParser(description='Comprehensive Testing for Enhanced SMC Trading System')

    parser.add_argument('--include-unit', action='store_true', default=True, help='Include unit tests')
    parser.add_argument('--exclude-unit', action='store_true', help='Exclude unit tests')
    parser.add_argument('--include-integration', action='store_true', default=True, help='Include integration tests')
    parser.add_argument('--exclude-integration', action='store_true', help='Exclude integration tests')
    parser.add_argument('--include-e2e', action='store_true', default=True, help='Include end-to-end tests')
    parser.add_argument('--exclude-e2e', action='store_true', help='Exclude end-to-end tests')
    parser.add_argument('--include-performance', action='store_true', default=True, help='Include performance tests')
    parser.add_argument('--exclude-performance', action='store_true', help='Exclude performance tests')
    parser.add_argument('--include-quality', action='store_true', default=True, help='Include quality assurance tests')
    parser.add_argument('--exclude-quality', action='store_true', help='Exclude quality assurance tests')
    parser.add_argument('--include-production', action='store_true', default=True, help='Include production readiness tests')
    parser.add_argument('--exclude-production', action='store_true', help='Exclude production readiness tests')
    parser.add_argument('--parallel', action='store_true', default=True, help='Enable parallel test execution')
    parser.add_argument('--no-parallel', action='store_true', help='Disable parallel test execution')
    parser.add_argument('--dashboard-port', type=int, default=8090, help='Dashboard port (0 to disable)')
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')

    args = parser.parse_args()

    # Resolve test inclusion flags
    include_unit = args.include_unit and not args.exclude_unit
    include_integration = args.include_integration and not args.exclude_integration
    include_e2e = args.include_e2e and not args.exclude_e2e
    include_performance = args.include_performance and not args.exclude_performance
    include_quality = args.include_quality and not args.exclude_quality
    include_production = args.include_production and not args.exclude_production
    parallel = args.parallel and not args.no_parallel

    # Print configuration
    print("=" * 80)
    print("COMPREHENSIVE TESTING CONFIGURATION")
    print("=" * 80)
    print(f"Unit Tests: {'✓' if include_unit else '✗'}")
    print(f"Integration Tests: {'✓' if include_integration else '✗'}")
    print(f"End-to-End Tests: {'✓' if include_e2e else '✗'}")
    print(f"Performance Tests: {'✓' if include_performance else '✗'}")
    print(f"Quality Assurance: {'✓' if include_quality else '✗'}")
    print(f"Production Readiness: {'✓' if include_production else '✗'}")
    print(f"Parallel Execution: {'✓' if parallel else '✗'}")
    print(f"Dashboard Port: {args.dashboard_port if args.dashboard_port > 0 else 'Disabled'}")
    print(f"Workers: {args.workers if parallel else 1}")
    print("=" * 80)

    # Run comprehensive testing
    async def run_tests():
        orchestrator = ComprehensiveTestOrchestrator()

        # Start dashboard if requested
        dashboard_task = None
        if args.dashboard_port > 0:
            dashboard_task = await orchestrator.start_monitoring_dashboard(args.dashboard_port)
            print(f"🌐 Real-time monitoring dashboard: http://localhost:{args.dashboard_port}")

        try:
            # Run tests
            print("\n🚀 Starting comprehensive test execution...\n")

            report = await orchestrator.run_comprehensive_tests(
                include_unit=include_unit,
                include_integration=include_integration,
                include_e2e=include_e2e,
                include_performance=include_performance,
                include_quality=include_quality,
                include_production=include_production,
                parallel=parallel
            )

            # Print summary
            print("\n" + "=" * 80)
            print("COMPREHENSIVE TESTING RESULTS")
            print("=" * 80)
            print(f"Overall Status: {report['execution_summary']['status'].upper()}")
            print(f"Overall Score: {report['scores']['overall']:.1%}")
            print(f"Execution Time: {report['execution_summary']['total_execution_time']:.2f}s")

            print("\nTest Scores:")
            print(f"  Framework: {report['scores']['framework']:.1%}")
            print(f"  Quality Assurance: {report['scores']['quality_assurance']:.1%}")
            print(f"  Production Readiness: {report['scores']['production_readiness']:.1%}")

            print(f"\nRecommendations: {len(report['recommendations'])}")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")

            print(f"\nReports saved to: test_reports/")
            print(f"Dashboard: http://localhost:{args.dashboard_port}" if args.dashboard_port > 0 else "Dashboard: Disabled")

            # Determine exit code
            exit_code = 0 if report['execution_summary']['status'] == 'passed' else 1
            return exit_code

        except Exception as e:
            print(f"\n❌ Comprehensive testing failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            if dashboard_task:
                dashboard_task.cancel()

    # Run the async function
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)

if __name__ == "__main__":
    main()