"""
Comprehensive Test Automation Suite for SMC Trading Agent

This module provides automated test execution, reporting, and CI/CD integration
for the complete trading system testing framework.
"""

import pytest
import asyncio
import subprocess
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import yaml
import requests
from pathlib import Path

# Import test modules
from test_unit_comprehensive import TestRunner as UnitTestRunner
from test_integration_comprehensive import IntegrationTestRunner
from test_performance_comprehensive import PerformanceTestRunner
from test_e2e_comprehensive import EndToEndTestRunner


@dataclass
class TestConfiguration:
    """Configuration for test automation."""
    test_categories: List[str]
    parallel_execution: bool
    timeout_seconds: int
    generate_reports: bool
    notify_on_failure: bool
    artifact_retention_days: int
    performance_thresholds: Dict[str, float]
    coverage_thresholds: Dict[str, float]


@dataclass
class TestExecution:
    """Test execution metadata and results."""
    execution_id: str
    timestamp: datetime
    test_category: str
    status: str
    duration: float
    results: Dict
    artifacts: List[str]
    performance_metrics: Dict
    coverage_metrics: Dict


class TestAutomationOrchestrator:
    """Orchestrates comprehensive test automation across all test categories."""

    def __init__(self, config_path: str = "test_config.yaml"):
        self.logger = self._setup_logging()
        self.config = self._load_configuration(config_path)
        self.execution_history: List[TestExecution] = []
        self.artifacts_dir = Path("test_artifacts")
        self.artifacts_dir.mkdir(exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """Set up comprehensive logging for test automation."""
        logger = logging.getLogger("TestAutomation")
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler("test_automation.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def _load_configuration(self, config_path: str) -> TestConfiguration:
        """Load test automation configuration."""
        default_config = {
            'test_categories': ['unit', 'integration', 'performance', 'e2e'],
            'parallel_execution': True,
            'timeout_seconds': 3600,
            'generate_reports': True,
            'notify_on_failure': True,
            'artifact_retention_days': 30,
            'performance_thresholds': {
                'max_test_duration': 600,
                'max_memory_usage': 1024,
                'min_throughput': 100
            },
            'coverage_thresholds': {
                'min_line_coverage': 80,
                'min_branch_coverage': 75,
                'min_function_coverage': 80
            }
        }

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)

        return TestConfiguration(**default_config)

    async def run_comprehensive_test_suite(self, categories: List[str] = None) -> Dict:
        """Run comprehensive test suite across specified categories."""
        if categories is None:
            categories = self.config.test_categories

        self.logger.info(f"Starting comprehensive test suite for categories: {categories}")

        execution_id = f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = time.time()

        execution_results = {
            'execution_id': execution_id,
            'start_time': datetime.now(),
            'categories': categories,
            'results': {},
            'summary': {},
            'artifacts': [],
            'status': 'running'
        }

        try:
            # Run tests for each category
            for category in categories:
                self.logger.info(f"Running {category} tests...")
                category_start_time = time.time()

                try:
                    if category == 'unit':
                        result = await self._run_unit_tests()
                    elif category == 'integration':
                        result = await self._run_integration_tests()
                    elif category == 'performance':
                        result = await self._run_performance_tests()
                    elif category == 'e2e':
                        result = await self._run_e2e_tests()
                    else:
                        raise ValueError(f"Unknown test category: {category}")

                    category_duration = time.time() - category_start_time
                    result['duration'] = category_duration

                    execution_results['results'][category] = result
                    self.logger.info(f"Completed {category} tests in {category_duration:.2f}s")

                except Exception as e:
                    self.logger.error(f"Failed to run {category} tests: {e}")
                    execution_results['results'][category] = {
                        'status': 'failed',
                        'error': str(e),
                        'duration': time.time() - category_start_time
                    }

            # Calculate summary
            execution_results['summary'] = self._calculate_execution_summary(execution_results['results'])
            execution_results['status'] = 'completed'

            # Generate reports and artifacts
            if self.config.generate_reports:
                artifacts = await self._generate_test_reports(execution_results)
                execution_results['artifacts'] = artifacts

            # Check performance and coverage thresholds
            self._validate_thresholds(execution_results)

            total_duration = time.time() - start_time
            execution_results['total_duration'] = total_duration

            self.logger.info(f"Test suite completed in {total_duration:.2f}s")
            self._log_execution_summary(execution_results)

            # Store execution history
            self._store_execution(execution_results)

            # Send notifications if needed
            if self.config.notify_on_failure and execution_results['summary']['failed_tests'] > 0:
                await self._send_failure_notification(execution_results)

            return execution_results

        except Exception as e:
            execution_results['status'] = 'failed'
            execution_results['error'] = str(e)
            self.logger.error(f"Test suite failed: {e}")
            raise

    async def _run_unit_tests(self) -> Dict:
        """Run unit tests with coverage."""
        self.logger.info("Running unit tests with coverage...")

        # Run pytest with coverage
        cmd = [
            "python", "-m", "pytest",
            "--cov=.",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--junit-xml=test_artifacts/unit_test_results.xml",
            "tests/test_unit_comprehensive.py",
            "-v"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Parse results
        if process.returncode == 0:
            # Parse coverage report
            coverage_data = self._parse_coverage_report()
            return {
                'status': 'passed',
                'coverage': coverage_data,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            }
        else:
            return {
                'status': 'failed',
                'return_code': process.returncode,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            }

    async def _run_integration_tests(self) -> Dict:
        """Run integration tests."""
        self.logger.info("Running integration tests...")

        runner = IntegrationTestRunner()
        result = await runner.run_all_integration_tests()

        # Generate JUnit XML report
        self._generate_junit_report(result, "integration")

        return {
            'status': 'passed',
            'test_results': result,
            'junit_report': 'test_artifacts/integration_test_results.xml'
        }

    async def _run_performance_tests(self) -> Dict:
        """Run performance tests."""
        self.logger.info("Running performance tests...")

        runner = PerformanceTestRunner()
        result = await runner.run_all_performance_tests()

        # Validate performance thresholds
        performance_issues = self._validate_performance_thresholds(result)

        return {
            'status': 'passed' if not performance_issues else 'warning',
            'test_results': result,
            'performance_issues': performance_issues
        }

    async def _run_e2e_tests(self) -> Dict:
        """Run end-to-end tests."""
        self.logger.info("Running end-to-end tests...")

        runner = EndToEndTestRunner()
        result = await runner.run_all_e2e_tests()

        # Validate production readiness
        readiness_score = result['production_readiness']['success_rate']

        return {
            'status': 'passed' if readiness_score >= 80 else 'warning',
            'test_results': result,
            'production_readiness': result['production_readiness']
        }

    def _parse_coverage_report(self) -> Dict:
        """Parse coverage report from XML file."""
        coverage_file = Path("test_artifacts/coverage.xml")
        if not coverage_file.exists():
            return {}

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(coverage_file)
            root = tree.getroot()

            coverage_data = {}
            for package in root.findall(".//package"):
                name = package.get('name')
                line_rate = float(package.get('line-rate', 0))
                branch_rate = float(package.get('branch-rate', 0))

                coverage_data[name] = {
                    'line_coverage': line_rate * 100,
                    'branch_coverage': branch_rate * 100
                }

            # Calculate overall coverage
            if root.findall(".//coverage"):
                coverage = root.find(".//coverage")
                overall = {
                    'line_coverage': float(coverage.get('line-rate', 0)) * 100,
                    'branch_coverage': float(coverage.get('branch-rate', 0)) * 100
                }
                coverage_data['overall'] = overall

            return coverage_data

        except Exception as e:
            self.logger.error(f"Failed to parse coverage report: {e}")
            return {}

    def _generate_junit_report(self, test_results: Dict, test_type: str):
        """Generate JUnit XML report for test results."""
        junit_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{test_type}_tests" tests="{test_results['summary']['total_tests']}"
           failures="{test_results['summary']['failed']}" time="{test_results.get('total_duration', 0)}">
"""

        for test_class, class_results in test_results.get('test_classes', {}).items():
            for test in class_results.get('tests', []):
                status = "passed" if test['status'] == 'PASSED' else "failed"
                junit_xml += f"""
    <testcase classname="{test_class}" name="{test['method']}" time="{test.get('duration', 0)}">
"""
                if test['status'] == 'FAILED':
                    junit_xml += f"""
        <failure message="{test.get('error', 'Test failed')}">
            {test.get('error', 'Unknown error')}
        </failure>
"""
                junit_xml += """
    </testcase>
"""

        junit_xml += "</testsuite>"

        # Write to file
        output_file = self.artifacts_dir / f"{test_type}_test_results.xml"
        with open(output_file, 'w') as f:
            f.write(junit_xml)

    def _validate_performance_thresholds(self, results: Dict) -> List[str]:
        """Validate performance against configured thresholds."""
        issues = []

        for category, result in results.items():
            if 'test_results' in result and 'performance_metrics' in result['test_results']:
                metrics = result['test_results']['performance_metrics']

                # Check test duration
                if 'summary' in metrics:
                    total_duration = metrics['summary'].get('total_duration', 0)
                    if total_duration > self.config.performance_thresholds['max_test_duration']:
                        issues.append(f"{category} tests exceeded duration threshold: {total_duration:.2f}s")

                # Check memory usage
                if 'system' in metrics:
                    memory_usage = metrics['system'].get('memory_total', 0)
                    if memory_usage > self.config.performance_thresholds['max_memory_usage']:
                        issues.append(f"{category} tests exceeded memory threshold: {memory_usage:.1f}MB")

        return issues

    def _validate_thresholds(self, execution_results: Dict):
        """Validate all thresholds and add warnings to results."""
        warnings = []

        # Check coverage thresholds
        if 'unit' in execution_results['results']:
            unit_result = execution_results['results']['unit']
            if 'coverage' in unit_result:
                coverage = unit_result['coverage']
                if 'overall' in coverage:
                    line_coverage = coverage['overall'].get('line_coverage', 0)
                    if line_coverage < self.config.coverage_thresholds['min_line_coverage']:
                        warnings.append(f"Line coverage {line_coverage:.1f}% below threshold {self.config.coverage_thresholds['min_line_coverage']}%")

        # Check performance thresholds
        performance_issues = self._validate_performance_thresholds(execution_results['results'])
        warnings.extend(performance_issues)

        if warnings:
            execution_results['warnings'] = warnings
            self.logger.warning("Threshold validation warnings:")
            for warning in warnings:
                self.logger.warning(f"  - {warning}")

    def _calculate_execution_summary(self, results: Dict) -> Dict:
        """Calculate comprehensive execution summary."""
        summary = {
            'total_categories': len(results),
            'passed_categories': 0,
            'failed_categories': 0,
            'warning_categories': 0,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'total_duration': 0
        }

        for category, result in results.items():
            status = result.get('status', 'unknown')

            if status == 'passed':
                summary['passed_categories'] += 1
            elif status == 'failed':
                summary['failed_categories'] += 1
            elif status == 'warning':
                summary['warning_categories'] += 1

            # Count tests if available
            if 'test_results' in result and 'summary' in result['test_results']:
                test_summary = result['test_results']['summary']
                summary['total_tests'] += test_summary.get('total_tests', 0)
                summary['passed_tests'] += test_summary.get('passed', 0)
                summary['failed_tests'] += test_summary.get('failed', 0)

            # Add duration
            summary['total_duration'] += result.get('duration', 0)

        # Calculate success rate
        if summary['total_tests'] > 0:
            summary['success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        else:
            summary['success_rate'] = 0

        return summary

    async def _generate_test_reports(self, execution_results: Dict) -> List[str]:
        """Generate comprehensive test reports."""
        artifacts = []

        # Generate HTML report
        html_report = await self._generate_html_report(execution_results)
        html_file = self.artifacts_dir / f"test_report_{execution_results['execution_id']}.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        artifacts.append(str(html_file))

        # Generate JSON report
        json_file = self.artifacts_dir / f"test_results_{execution_results['execution_id']}.json"
        with open(json_file, 'w') as f:
            json.dump(execution_results, f, indent=2, default=str)
        artifacts.append(str(json_file))

        # Generate summary markdown
        markdown_report = self._generate_markdown_report(execution_results)
        markdown_file = self.artifacts_dir / f"test_summary_{execution_results['execution_id']}.md"
        with open(markdown_file, 'w') as f:
            f.write(markdown_report)
        artifacts.append(str(markdown_file))

        return artifacts

    async def _generate_html_report(self, execution_results: Dict) -> str:
        """Generate comprehensive HTML test report."""
        summary = execution_results['summary']

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SMC Trading Agent - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .category {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; }}
        .failed {{ background-color: #f8d7da; }}
        .warning {{ background-color: #fff3cd; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .status-pass {{ color: green; font-weight: bold; }}
        .status-fail {{ color: red; font-weight: bold; }}
        .status-warning {{ color: orange; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SMC Trading Agent - Test Report</h1>
        <p><strong>Execution ID:</strong> {execution_results['execution_id']}</p>
        <p><strong>Start Time:</strong> {execution_results['start_time']}</p>
        <p><strong>Total Duration:</strong> {execution_results.get('total_duration', 0):.2f} seconds</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Categories</td><td>{summary['total_categories']}</td></tr>
            <tr><td>Passed Categories</td><td>{summary['passed_categories']}</td></tr>
            <tr><td>Failed Categories</td><td>{summary['failed_categories']}</td></tr>
            <tr><td>Warning Categories</td><td>{summary['warning_categories']}</td></tr>
            <tr><td>Total Tests</td><td>{summary['total_tests']}</td></tr>
            <tr><td>Passed Tests</td><td>{summary['passed_tests']}</td></tr>
            <tr><td>Failed Tests</td><td>{summary['failed_tests']}</td></tr>
            <tr><td>Success Rate</td><td>{summary['success_rate']:.1f}%</td></tr>
        </table>
    </div>

    <h2>Category Results</h2>
"""

        for category, result in execution_results['results'].items():
            status = result.get('status', 'unknown')
            css_class = status.replace('unknown', 'warning')

            html += f"""
    <div class="category {css_class}">
        <h3>{category.title()} Tests</h3>
        <p><strong>Status:</strong> <span class="status-{status}">{status.upper()}</span></p>
        <p><strong>Duration:</strong> {result.get('duration', 0):.2f} seconds</p>
"""

            # Add category-specific details
            if category == 'unit' and 'coverage' in result:
                coverage = result['coverage']
                if 'overall' in coverage:
                    html += f"""
        <p><strong>Line Coverage:</strong> {coverage['overall'].get('line_coverage', 0):.1f}%</p>
        <p><strong>Branch Coverage:</strong> {coverage['overall'].get('branch_coverage', 0):.1f}%</p>
"""

            elif 'test_results' in result and 'summary' in result['test_results']:
                test_summary = result['test_results']['summary']
                html += f"""
        <p><strong>Tests Passed:</strong> {test_summary.get('passed', 0)}/{test_summary.get('total_tests', 0)}</p>
"""

            html += """
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def _generate_markdown_report(self, execution_results: Dict) -> str:
        """Generate markdown test report."""
        summary = execution_results['summary']

        markdown = f"""# SMC Trading Agent - Test Report

**Execution ID:** {execution_results['execution_id']}
**Start Time:** {execution_results['start_time']}
**Total Duration:** {execution_results.get('total_duration', 0):.2f} seconds

## Summary

| Metric | Value |
|--------|-------|
| Total Categories | {summary['total_categories']} |
| Passed Categories | {summary['passed_categories']} |
| Failed Categories | {summary['failed_categories']} |
| Warning Categories | {summary['warning_categories']} |
| Total Tests | {summary['total_tests']} |
| Passed Tests | {summary['passed_tests']} |
| Failed Tests | {summary['failed_tests']} |
| Success Rate | {summary['success_rate']:.1f}% |

## Category Results

"""

        for category, result in execution_results['results'].items():
            status = result.get('status', 'unknown')
            duration = result.get('duration', 0)

            markdown += f"""
### {category.title()} Tests

**Status:** {status.upper()}
**Duration:** {duration:.2f} seconds

"""

            # Add category-specific details
            if category == 'unit' and 'coverage' in result:
                coverage = result['coverage']
                if 'overall' in coverage:
                    markdown += f"""
**Line Coverage:** {coverage['overall'].get('line_coverage', 0):.1f}%
**Branch Coverage:** {coverage['overall'].get('branch_coverage', 0):.1f}%

"""

            elif 'test_results' in result and 'summary' in result['test_results']:
                test_summary = result['test_results']['summary']
                markdown += f"""
**Tests Passed:** {test_summary.get('passed', 0)}/{test_summary.get('total_tests', 0)}

"""

        # Add warnings if any
        if 'warnings' in execution_results:
            markdown += """
## Warnings

"""
            for warning in execution_results['warnings']:
                markdown += f"- {warning}\n"

        markdown += """
## Artifacts

"""
        for artifact in execution_results.get('artifacts', []):
            artifact_name = Path(artifact).name
            markdown += f"- [{artifact_name}](./{artifact_name})\n"

        return markdown

    def _log_execution_summary(self, execution_results: Dict):
        """Log execution summary to console."""
        summary = execution_results['summary']

        self.logger.info("=" * 60)
        self.logger.info("TEST EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Execution ID: {execution_results['execution_id']}")
        self.logger.info(f"Total Categories: {summary['total_categories']}")
        self.logger.info(f"Passed Categories: {summary['passed_categories']}")
        self.logger.info(f"Failed Categories: {summary['failed_categories']}")
        self.logger.info(f"Warning Categories: {summary['warning_categories']}")
        self.logger.info(f"Total Tests: {summary['total_tests']}")
        self.logger.info(f"Passed Tests: {summary['passed_tests']}")
        self.logger.info(f"Failed Tests: {summary['failed_tests']}")
        self.logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
        self.logger.info(f"Total Duration: {execution_results.get('total_duration', 0):.2f}s")

        if 'warnings' in execution_results:
            self.logger.warning("WARNINGS:")
            for warning in execution_results['warnings']:
                self.logger.warning(f"  - {warning}")

        self.logger.info("=" * 60)

    def _store_execution(self, execution_results: Dict):
        """Store execution results in history."""
        execution = TestExecution(
            execution_id=execution_results['execution_id'],
            timestamp=execution_results['start_time'],
            test_category="comprehensive",
            status=execution_results['status'],
            duration=execution_results.get('total_duration', 0),
            results=execution_results,
            artifacts=execution_results.get('artifacts', []),
            performance_metrics={},
            coverage_metrics={}
        )

        self.execution_history.append(execution)

        # Keep only recent executions
        cutoff_date = datetime.now() - timedelta(days=self.config.artifact_retention_days)
        self.execution_history = [
            exec for exec in self.execution_history
            if exec.timestamp > cutoff_date
        ]

    async def _send_failure_notification(self, execution_results: Dict):
        """Send notification on test failure."""
        # This would integrate with your notification system
        # (Slack, email, Teams, etc.)
        summary = execution_results['summary']

        message = f"""
🚨 **Test Suite Failed** 🚨

**Execution ID:** {execution_results['execution_id']}
**Failed Tests:** {summary['failed_tests']}/{summary['total_tests']}
**Success Rate:** {summary['success_rate']:.1f}%

**Failed Categories:**
"""

        for category, result in execution_results['results'].items():
            if result.get('status') == 'failed':
                message += f"- {category.title()}: {result.get('error', 'Unknown error')}\n"

        self.logger.error("Test failure notification:")
        self.logger.error(message)

        # Here you would send the actual notification
        # await self._send_slack_notification(message)
        # await self._send_email_notification(message)


class CICDIntegration:
    """CI/CD pipeline integration for automated testing."""

    def __init__(self):
        self.logger = logging.getLogger("CICDIntegration")

    async def run_github_actions_workflow(self, event_type: str, payload: Dict) -> Dict:
        """Run tests as part of GitHub Actions workflow."""
        self.logger.info(f"Running GitHub Actions workflow for event: {event_type}")

        # Determine test categories based on event
        if event_type == 'push':
            # Full test suite for main branch pushes
            categories = ['unit', 'integration', 'performance']
        elif event_type == 'pull_request':
            # Core tests for pull requests
            categories = ['unit', 'integration']
        else:
            # Default test categories
            categories = ['unit', 'integration']

        # Run tests
        orchestrator = TestAutomationOrchestrator()
        results = await orchestrator.run_comprehensive_test_suite(categories)

        # Generate GitHub Actions output
        github_output = self._generate_github_actions_output(results)

        # Set exit code based on results
        exit_code = 0 if results['summary']['failed_tests'] == 0 else 1

        return {
            'exit_code': exit_code,
            'results': results,
            'github_output': github_output
        }

    def _generate_github_actions_output(self, results: Dict) -> str:
        """Generate GitHub Actions output format."""
        summary = results['summary']

        output = f"""
## Test Results Summary

- **Total Tests:** {summary['total_tests']}
- **Passed:** {summary['passed_tests']} ✅
- **Failed:** {summary['failed_tests']} ❌
- **Success Rate:** {summary['success_rate']:.1f}%
- **Duration:** {results.get('total_duration', 0):.2f}s

### Category Results

"""

        for category, result in results['results'].items():
            status = result.get('status', 'unknown')
            duration = result.get('duration', 0)
            status_emoji = "✅" if status == 'passed' else "❌" if status == 'failed' else "⚠️"

            output += f"- **{category.title()}:** {status_emoji} {status.upper()} ({duration:.2f}s)\n"

        # Add artifacts
        if results.get('artifacts'):
            output += "\n### Artifacts\n"
            for artifact in results['artifacts']:
                artifact_name = Path(artifact).name
                output += f"- [{artifact_name}](artifact://{artifact})\n"

        return output

    async def run_gitlab_ci_pipeline(self, stage: str) -> Dict:
        """Run tests as part of GitLab CI pipeline."""
        self.logger.info(f"Running GitLab CI pipeline for stage: {stage}")

        # Determine test categories based on pipeline stage
        if stage == 'test':
            categories = ['unit', 'integration']
        elif stage == 'performance':
            categories = ['performance']
        elif stage == 'e2e':
            categories = ['e2e']
        else:
            categories = ['unit']

        # Run tests
        orchestrator = TestAutomationOrchestrator()
        results = await orchestrator.run_comprehensive_test_suite(categories)

        # Generate GitLab CI artifacts
        gitlab_artifacts = self._generate_gitlab_artifacts(results)

        return {
            'results': results,
            'artifacts': gitlab_artifacts,
            'exit_code': 0 if results['summary']['failed_tests'] == 0 else 1
        }

    def _generate_gitlab_artifacts(self, results: Dict) -> Dict:
        """Generate GitLab CI artifacts."""
        artifacts = {
            'reports': {
                'junit': 'test_artifacts/junit.xml'
            },
            'test_reports': results.get('artifacts', [])
        }

        # Add coverage report if available
        if 'unit' in results['results'] and 'coverage' in results['results']['unit']:
            artifacts['coverage'] = {
                'coverage_report': 'htmlcov/index.html',
                'coverage_xml': 'coverage.xml'
            }

        return artifacts

    async def run_jenkins_pipeline(self, build_type: str) -> Dict:
        """Run tests as part of Jenkins pipeline."""
        self.logger.info(f"Running Jenkins pipeline for build type: {build_type}")

        # Determine test categories based on build type
        if build_type == 'full':
            categories = ['unit', 'integration', 'performance', 'e2e']
        elif build_type == 'quick':
            categories = ['unit']
        elif build_type == 'release':
            categories = ['unit', 'integration', 'performance', 'e2e']
        else:
            categories = ['unit', 'integration']

        # Run tests
        orchestrator = TestAutomationOrchestrator()
        results = await orchestrator.run_comprehensive_test_suite(categories)

        # Generate Jenkins test results
        jenkins_results = self._generate_jenkins_results(results)

        return {
            'results': results,
            'jenkins_results': jenkins_results,
            'build_status': 'SUCCESS' if results['summary']['failed_tests'] == 0 else 'FAILURE'
        }

    def _generate_jenkins_results(self, results: Dict) -> Dict:
        """Generate Jenkins-compatible test results."""
        summary = results['summary']

        return {
            'total': summary['total_tests'],
            'passed': summary['passed_tests'],
            'failed': summary['failed_tests'],
            'skipped': 0,
            'failures': [
                {
                    'test': f"{category}_{test['method']}",
                    'error': test.get('error', 'Test failed')
                }
                for category, result in results['results'].items()
                if 'test_results' in result
                for test_class in result['test_results'].get('test_classes', {}).values()
                for test in test_class.get('tests', [])
                if test['status'] == 'FAILED'
            ]
        }


# Main execution functions
async def main():
    """Main function for running test automation."""
    import argparse

    parser = argparse.ArgumentParser(description="SMC Trading Agent Test Automation")
    parser.add_argument("--config", default="test_config.yaml", help="Configuration file path")
    parser.add_argument("--categories", nargs="+", help="Test categories to run")
    parser.add_argument("--ci-platform", choices=["github", "gitlab", "jenkins"], help="CI/CD platform")
    parser.add_argument("--event-type", help="CI/CD event type")
    parser.add_argument("--build-type", help="Build type for CI/CD")

    args = parser.parse_args()

    if args.ci_platform:
        # Run in CI/CD mode
        cicd = CICDIntegration()

        if args.ci_platform == "github":
            results = await cicd.run_github_actions_workflow(
                args.event_type or "push",
                {"repository": "smc_trading_agent", "branch": "main"}
            )
        elif args.ci_platform == "gitlab":
            results = await cicd.run_gitlab_ci_pipeline(args.build_type or "test")
        elif args.ci_platform == "jenkins":
            results = await cicd.run_jenkins_pipeline(args.build_type or "full")

        # Exit with appropriate code
        exit_code = results.get('exit_code', 0)
        sys.exit(exit_code)

    else:
        # Run standalone test automation
        orchestrator = TestAutomationOrchestrator(args.config)
        results = await orchestrator.run_comprehensive_test_suite(args.categories)

        # Exit with appropriate code
        exit_code = 0 if results['summary']['failed_tests'] == 0 else 1
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())