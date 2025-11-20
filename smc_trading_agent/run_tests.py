#!/usr/bin/env python3
"""
SMC Trading Agent - Comprehensive Test Runner

This script provides a convenient interface for running all types of tests
for the SMC Trading Agent system with comprehensive reporting and CI/CD integration.
"""

import asyncio
import argparse
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test automation components
from tests.test_automation_suite import TestAutomationOrchestrator, CICDIntegration


def setup_logging(verbose: bool = False):
    """Set up logging for the test runner."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_runner.log')
        ]
    )


async def run_tests(categories: list = None, config: str = None, verbose: bool = False):
    """Run tests with specified categories."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting SMC Trading Agent Test Suite")
    logger.info(f"Categories: {categories or 'all'}")
    logger.info(f"Config: {config or 'default'}")

    # Initialize orchestrator
    orchestrator = TestAutomationOrchestrator(config or "test_config.yaml")

    try:
        # Run comprehensive test suite
        results = await orchestrator.run_comprehensive_test_suite(categories)

        # Display results summary
        display_results(results)

        # Return exit code based on results
        failed_tests = results['summary']['failed_tests']
        return 0 if failed_tests == 0 else 1

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return 1


def display_results(results: dict):
    """Display test results in a user-friendly format."""
    print("\n" + "="*70)
    print("🧪 SMC TRADING AGENT - TEST RESULTS")
    print("="*70)

    summary = results['summary']

    # Overall status
    total_tests = summary['total_tests']
    passed_tests = summary['passed_tests']
    failed_tests = summary['failed_tests']
    success_rate = summary['success_rate']

    if failed_tests == 0:
        status_emoji = "✅"
        status_text = "ALL TESTS PASSED"
    elif success_rate >= 80:
        status_emoji = "⚠️"
        status_text = "MOSTLY PASSED"
    else:
        status_emoji = "❌"
        status_text = "TESTS FAILED"

    print(f"\n{status_emoji} {status_text}")
    print(f"📊 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    print(f"⏱️  Duration: {results.get('total_duration', 0):.2f} seconds")

    # Category results
    print(f"\n📋 Category Results:")
    for category, result in results['results'].items():
        status = result.get('status', 'unknown')
        duration = result.get('duration', 0)

        if status == 'passed':
            emoji = "✅"
        elif status == 'failed':
            emoji = "❌"
        else:
            emoji = "⚠️"

        print(f"  {emoji} {category.title():<15} {status.upper():<10} ({duration:6.2f}s)")

        # Add category-specific details
        if category == 'unit' and 'coverage' in result:
            coverage = result['coverage']
            if 'overall' in coverage:
                line_cov = coverage['overall'].get('line_coverage', 0)
                branch_cov = coverage['overall'].get('branch_coverage', 0)
                print(f"      📊 Coverage: {line_cov:.1f}% lines, {branch_cov:.1f}% branches")

        elif 'test_results' in result and 'summary' in result['test_results']:
            test_summary = result['test_results']['summary']
            passed = test_summary.get('passed', 0)
            total = test_summary.get('total_tests', 0)
            print(f"      📊 Tests: {passed}/{total} passed")

    # Warnings
    if 'warnings' in results and results['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in results['warnings']:
            print(f"  • {warning}")

    # Artifacts
    if results.get('artifacts'):
        print(f"\n📁 Generated Artifacts:")
        for artifact in results['artifacts']:
            artifact_name = Path(artifact).name
            print(f"  • {artifact_name}")

    print("\n" + "="*70)


async def run_ci_tests(platform: str, event_type: str = None, build_type: str = None):
    """Run tests for CI/CD platforms."""
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 Running tests for {platform} CI/CD")

    cicd = CICDIntegration()

    try:
        if platform == "github":
            results = await cicd.run_github_actions_workflow(
                event_type or "push",
                {"repository": "smc_trading_agent", "branch": "main"}
            )
        elif platform == "gitlab":
            results = await cicd.run_gitlab_ci_pipeline(build_type or "test")
        elif platform == "jenkins":
            results = await cicd.run_jenkins_pipeline(build_type or "full")
        else:
            raise ValueError(f"Unknown CI/CD platform: {platform}")

        # Display CI results
        display_ci_results(results, platform)

        return results.get('exit_code', 0)

    except Exception as e:
        logger.error(f"❌ CI/CD test execution failed: {e}")
        return 1


def display_ci_results(results: dict, platform: str):
    """Display CI/CD test results."""
    print(f"\n🔄 {platform.upper()} CI/CD TEST RESULTS")
    print("="*50)

    test_results = results.get('results', {})
    summary = test_results.get('summary', {})

    print(f"📊 Total Tests: {summary.get('total_tests', 0)}")
    print(f"✅ Passed: {summary.get('passed_tests', 0)}")
    print(f"❌ Failed: {summary.get('failed_tests', 0)}")
    print(f"📈 Success Rate: {summary.get('success_rate', 0):.1f}%")
    print(f"🏗️  Build Status: {results.get('build_status', 'UNKNOWN')}")

    if results.get('artifacts'):
        print(f"\n📁 Build Artifacts:")
        for artifact in results['artifacts']:
            print(f"  • {artifact}")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="SMC Trading Agent - Comprehensive Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py

  # Run specific test categories
  python run_tests.py --categories unit integration

  # Run with custom configuration
  python run_tests.py --config custom_config.yaml

  # Run in CI/CD mode
  python run_tests.py --ci github --event-type push

  # Run with verbose output
  python run_tests.py --verbose
        """
    )

    # Test execution options
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        choices=["unit", "integration", "performance", "e2e"],
        help="Test categories to run (default: all)"
    )

    parser.add_argument(
        "--config", "-f",
        default="test_config.yaml",
        help="Path to test configuration file"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    # CI/CD options
    parser.add_argument(
        "--ci",
        choices=["github", "gitlab", "jenkins"],
        help="Run in CI/CD mode"
    )

    parser.add_argument(
        "--event-type",
        choices=["push", "pull_request", "schedule"],
        help="CI/CD event type"
    )

    parser.add_argument(
        "--build-type",
        choices=["test", "performance", "e2e", "full", "quick", "release"],
        help="Build type for CI/CD"
    )

    # Utility options
    parser.add_argument(
        "--version",
        action="version",
        version="SMC Trading Agent Test Runner v1.0.0"
    )

    args = parser.parse_args()

    # Run based on mode
    if args.ci:
        # CI/CD mode
        exit_code = asyncio.run(run_ci_tests(
            platform=args.ci,
            event_type=args.event_type,
            build_type=args.build_type
        ))
    else:
        # Standard test mode
        exit_code = asyncio.run(run_tests(
            categories=args.categories,
            config=args.config,
            verbose=args.verbose
        ))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()