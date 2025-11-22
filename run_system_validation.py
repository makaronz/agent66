#!/usr/bin/env python3
"""
System Validation Runner for SMC Trading Agent

This script executes comprehensive system integration testing to validate
production readiness, ensuring all components work together seamlessly.

Validation Coverage:
1. Component Integration Testing
2. Performance Benchmarking
3. Error Handling Validation
4. Configuration Verification
5. Production Readiness Assessment
"""

import asyncio
import logging
import sys
import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test modules
from system_integration_tests import (
    TestEndToEndDataFlow,
    TestSystemPerformanceValidation,
    TestErrorHandlingAndRecovery,
    TestConfigurationAndDeployment,
    TestRealTimeTradingScenarios,
    test_complete_system_integration
)
from tests.test_production_readiness import test_production_readiness_integration

class SystemValidator:
    """Comprehensive system validation coordinator."""

    def __init__(self):
        self.logger = self._setup_logging()
        self.validation_results = {}
        self.start_time = None

    def _setup_logging(self):
        """Setup comprehensive logging for validation."""
        logger = logging.getLogger("SystemValidator")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler
        log_dir = Path("validation_logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_dir / f"system_validation_{timestamp}.log"
        )
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    async def run_comprehensive_validation(self):
        """Run complete system validation suite."""
        self.start_time = time.time()

        self.logger.info("=" * 80)
        self.logger.info("🚀 SMC TRADING AGENT - SYSTEM VALIDATION STARTED")
        self.logger.info("=" * 80)
        self.logger.info(f"Started at: {datetime.now()}")
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Working directory: {os.getcwd()}")

        validation_phases = [
            ("Component Integration", self._validate_component_integration),
            ("System Performance", self._validate_system_performance),
            ("Error Handling", self._validate_error_handling),
            ("Configuration", self._validate_configuration),
            ("Real-Time Scenarios", self._validate_real_time_scenarios),
            ("Production Readiness", self._validate_production_readiness)
        ]

        overall_success = True

        for phase_name, phase_func in validation_phases:
            self.logger.info(f"\n📋 Running {phase_name} Validation...")
            try:
                phase_result = await phase_func()
                self.validation_results[phase_name] = {
                    'status': 'PASSED' if phase_result else 'FAILED',
                    'timestamp': datetime.now(),
                    'details': phase_result if isinstance(phase_result, dict) else {}
                }

                if phase_result:
                    self.logger.info(f"✅ {phase_name} Validation: PASSED")
                else:
                    self.logger.error(f"❌ {phase_name} Validation: FAILED")
                    overall_success = False

            except Exception as e:
                self.logger.error(f"❌ {phase_name} Validation: EXCEPTION - {e}")
                self.logger.debug(traceback.format_exc())
                self.validation_results[phase_name] = {
                    'status': 'ERROR',
                    'timestamp': datetime.now(),
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                overall_success = False

        # Generate final report
        await self._generate_validation_report(overall_success)

        total_duration = time.time() - self.start_time
        self.logger.info(f"\n⏱️ Total Validation Duration: {total_duration:.2f}s")

        if overall_success:
            self.logger.info("\n🎉 SYSTEM VALIDATION: ALL TESTS PASSED")
            self.logger.info("✅ System is ready for production deployment")
        else:
            self.logger.error("\n💥 SYSTEM VALIDATION: FAILED")
            self.logger.error("❌ System requires fixes before production deployment")

        self.logger.info("=" * 80)

        return overall_success

    async def _validate_component_integration(self):
        """Validate component integration and data flow."""
        try:
            self.logger.info("Testing end-to-end data flow...")

            # Initialize test environment
            test_instance = TestEndToEndDataFlow()

            # Run key integration tests
            integration_env = await test_instance.integration_environment().__anext__()

            # Test market data ingestion
            await test_instance.test_live_market_data_ingestion(integration_env)
            self.logger.info("  ✅ Live market data ingestion")

            # Test SMC pattern detection
            await test_instance.test_smc_pattern_detection(integration_env)
            self.logger.info("  ✅ SMC pattern detection")

            # Test ML decision engine
            await test_instance.test_ml_decision_engine_integration(integration_env)
            self.logger.info("  ✅ ML decision engine integration")

            # Test risk management
            await test_instance.test_risk_management_integration(integration_env)
            self.logger.info("  ✅ Risk management integration")

            # Test execution engine
            await test_instance.test_execution_engine_integration(integration_env)
            self.logger.info("  ✅ Execution engine integration")

            return True

        except Exception as e:
            self.logger.error(f"Component integration validation failed: {e}")
            return False

    async def _validate_system_performance(self):
        """Validate system performance characteristics."""
        try:
            self.logger.info("Testing system performance...")

            test_instance = TestSystemPerformanceValidation()
            perf_env = await test_instance.performance_environment().__anext__()

            # Test latency measurement
            await test_instance.test_end_to_end_latency_measurement(perf_env)
            self.logger.info("  ✅ End-to-end latency measurement")

            # Test throughput validation
            await test_instance.test_throughput_validation(perf_env)
            self.logger.info("  ✅ Throughput validation")

            # Test memory usage
            test_instance.test_memory_usage_validation(perf_env)
            self.logger.info("  ✅ Memory usage validation")

            return True

        except Exception as e:
            self.logger.error(f"System performance validation failed: {e}")
            return False

    async def _validate_error_handling(self):
        """Validate error handling and recovery mechanisms."""
        try:
            self.logger.info("Testing error handling...")

            test_instance = TestErrorHandlingAndRecovery()

            # Test API connection failure recovery
            await test_instance.test_api_connection_failure_recovery()
            self.logger.info("  ✅ API connection failure recovery")

            # Test data quality error handling
            await test_instance.test_data_quality_error_handling()
            self.logger.info("  ✅ Data quality error handling")

            # Test component failure isolation
            await test_instance.test_component_failure_isolation()
            self.logger.info("  ✅ Component failure isolation")

            return True

        except Exception as e:
            self.logger.error(f"Error handling validation failed: {e}")
            return False

    async def _validate_configuration(self):
        """Validate configuration and deployment setup."""
        try:
            self.logger.info("Testing configuration...")

            test_instance = TestConfigurationAndDeployment()

            # Test production configuration
            test_instance.test_production_configuration_validation()
            self.logger.info("  ✅ Production configuration validation")

            # Test environment variables
            test_instance.test_environment_variable_validation()
            self.logger.info("  ✅ Environment variable validation")

            # Test Docker configuration
            test_instance.test_docker_deployment_configuration()
            self.logger.info("  ✅ Docker deployment configuration")

            # Test service health checks
            await test_instance.test_service_startup_health_checks()
            self.logger.info("  ✅ Service startup health checks")

            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    async def _validate_real_time_scenarios(self):
        """Validate real-time trading scenarios."""
        try:
            self.logger.info("Testing real-time trading scenarios...")

            test_instance = TestRealTimeTradingScenarios()

            # Test complete trading cycle
            await test_instance.test_complete_trading_cycle()
            self.logger.info("  ✅ Complete trading cycle")

            # Test multi-asset portfolio management
            await test_instance.test_multi_asset_portfolio_management()
            self.logger.info("  ✅ Multi-asset portfolio management")

            return True

        except Exception as e:
            self.logger.error(f"Real-time scenarios validation failed: {e}")
            return False

    async def _validate_production_readiness(self):
        """Validate overall production readiness."""
        try:
            self.logger.info("Testing production readiness...")

            # Run production readiness integration test
            readiness_result = await test_production_readiness_integration()

            if readiness_result['overall_status'] == 'ready':
                self.logger.info(f"  ✅ Production readiness score: {readiness_result['readiness_score']:.1%}")
                return True
            else:
                self.logger.error(f"  ❌ Production readiness score: {readiness_result['readiness_score']:.1%}")
                return False

        except Exception as e:
            self.logger.error(f"Production readiness validation failed: {e}")
            return False

    async def _generate_validation_report(self, overall_success):
        """Generate comprehensive validation report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path("validation_reports") / f"system_validation_report_{timestamp}.json"
        report_file.parent.mkdir(exist_ok=True)

        # Prepare report data
        report = {
            'validation_summary': {
                'timestamp': datetime.now(),
                'total_duration': time.time() - self.start_time,
                'overall_success': overall_success,
                'total_phases': len(self.validation_results),
                'passed_phases': sum(1 for r in self.validation_results.values() if r['status'] == 'PASSED'),
                'failed_phases': sum(1 for r in self.validation_results.values() if r['status'] == 'FAILED'),
                'error_phases': sum(1 for r in self.validation_results.values() if r['status'] == 'ERROR')
            },
            'phase_results': self.validation_results,
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'working_directory': os.getcwd(),
                'environment': os.getenv('ENVIRONMENT', 'development')
            }
        }

        # Save JSON report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Generate HTML report
        html_report_file = report_file.with_suffix('.html')
        html_content = self._generate_html_report(report)
        with open(html_report_file, 'w') as f:
            f.write(html_content)

        # Generate markdown summary
        md_report_file = report_file.with_suffix('.md')
        md_content = self._generate_markdown_report(report)
        with open(md_report_file, 'w') as f:
            f.write(md_content)

        self.logger.info(f"📊 Validation reports generated:")
        self.logger.info(f"  JSON: {report_file}")
        self.logger.info(f"  HTML: {html_report_file}")
        self.logger.info(f"  Markdown: {md_report_file}")

    def _generate_html_report(self, report):
        """Generate HTML validation report."""
        summary = report['validation_summary']
        status_color = '#28a745' if summary['overall_success'] else '#dc3545'

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SMC Trading Agent - System Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status {{ font-size: 24px; font-weight: bold; color: {status_color}; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric-value {{ font-size: 28px; font-weight: bold; display: block; }}
        .metric-label {{ color: #666; font-size: 14px; }}
        .phase {{ border: 1px solid #ddd; margin: 15px 0; border-radius: 6px; }}
        .phase-header {{ padding: 15px; font-weight: bold; font-size: 18px; }}
        .phase-details {{ padding: 15px; }}
        .passed {{ border-left: 5px solid #28a745; }}
        .failed {{ border-left: 5px solid #dc3545; }}
        .error {{ border-left: 5px solid #ffc107; }}
        .timestamp {{ color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SMC Trading Agent</h1>
            <h2>System Validation Report</h2>
            <div class="status">{'✅ VALIDATION PASSED' if summary['overall_success'] else '❌ VALIDATION FAILED'}</div>
            <div class="timestamp">Generated: {summary['timestamp']}</div>
        </div>

        <div class="summary">
            <h3>📊 Validation Summary</h3>
            <div class="metric">
                <span class="metric-value">{summary['total_duration']:.1f}s</span>
                <span class="metric-label">Duration</span>
            </div>
            <div class="metric">
                <span class="metric-value">{summary['passed_phases']}/{summary['total_phases']}</span>
                <span class="metric-label">Phases Passed</span>
            </div>
            <div class="metric">
                <span class="metric-value">{(summary['passed_phases']/summary['total_phases']*100):.0f}%</span>
                <span class="metric-label">Success Rate</span>
            </div>
        </div>

        <h3>🔍 Phase Results</h3>
"""

        for phase_name, result in report['phase_results'].items():
            status_class = result['status'].lower()
            html += f"""
        <div class="phase {status_class}">
            <div class="phase-header">
                {phase_name} - {result['status']}
            </div>
            <div class="phase-details">
                <div class="timestamp">Time: {result['timestamp']}</div>
"""

            if 'error' in result:
                html += f'<div style="color: #dc3545; margin-top: 10px;"><strong>Error:</strong> {result["error"]}</div>'

            html += '</div></div>'

        html += """
        <div style="margin-top: 40px; text-align: center; color: #666; font-size: 12px;">
            <p>Generated by SMC Trading Agent System Validator</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_markdown_report(self, report):
        """Generate markdown validation report."""
        summary = report['validation_summary']
        status_emoji = '✅' if summary['overall_success'] else '❌'

        md = f"""# SMC Trading Agent - System Validation Report

{status_emoji} **Overall Status**: {'VALIDATION PASSED' if summary['overall_success'] else 'VALIDATION FAILED'}

**Generated**: {summary['timestamp']}
**Duration**: {summary['total_duration']:.1f} seconds
**Success Rate**: {(summary['passed_phases']/summary['total_phases']*100):.0f}% ({summary['passed_phases']}/{summary['total_phases']} phases)

## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Phases | {summary['total_phases']} |
| Passed Phases | {summary['passed_phases']} |
| Failed Phases | {summary['failed_phases']} |
| Error Phases | {summary['error_phases']} |

## 🔍 Phase Results

"""

        for phase_name, result in report['phase_results'].items():
            status_emoji = {'PASSED': '✅', 'FAILED': '❌', 'ERROR': '⚠️'}.get(result['status'], '❓')
            md += f"### {phase_name} - {result['status']} {status_emoji}\n\n"
            md += f"**Time**: {result['timestamp']}\n\n"

            if 'error' in result:
                md += f"**Error**: `{result['error']}`\n\n"

            if 'details' in result and result['details']:
                md += f"**Details**: {json.dumps(result['details'], indent=2)}\n\n"

        md += """
---

*Generated by SMC Trading Agent System Validator*
"""
        return md

async def main():
    """Main validation runner."""
    validator = SystemValidator()

    try:
        success = await validator.run_comprehensive_validation()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation runner crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Check if required dependencies are available
    try:
        import pandas
        import numpy
        import pytest
    except ImportError as e:
        print(f"❌ Missing required dependency: {e}")
        print("Please install required packages with: pip install -r requirements.txt")
        sys.exit(1)

    # Run validation
    asyncio.run(main())