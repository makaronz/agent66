#!/usr/bin/env python3
"""
Ultra-Low Latency Performance Validation Script

Validates that the SMC trading agent meets performance targets:
- Data Pipeline: <10ms
- ML Inference: <20ms
- Risk Checks: <5ms
- Total System: <50ms

Usage:
    python validate_latency.py --target-ms 50 --iterations 100
"""

import asyncio
import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LatencyValidator:
    """Ultra-low latency performance validator"""

    def __init__(self, base_url: str = "http://localhost:8008"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

        # Performance targets (ms)
        self.targets = {
            'total_system_ms': 50,
            'data_pipeline_ms': 10,
            'ml_inference_ms': 20,
            'risk_check_ms': 5,
            'execution_ms': 15
        }

        # Results storage
        self.results: List[Dict[str, Any]] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10.0),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def validate_latency(self, iterations: int = 100) -> Dict[str, Any]:
        """Run comprehensive latency validation"""

        logger.info(f"Starting latency validation with {iterations} iterations")
        logger.info(f"Target latencies: {self.targets}")

        # Wait for system to be ready
        await self._wait_for_system_ready()

        # Run latency tests
        await self._run_latency_tests(iterations)

        # Analyze results
        analysis = self._analyze_results()

        # Generate report
        self._generate_report(analysis)

        return analysis

    async def _wait_for_system_ready(self):
        """Wait for system to be ready for testing"""
        max_wait = 60  # seconds
        wait_interval = 2

        for i in range(max_wait // wait_interval):
            try:
                async with self.session.get(f"{self.base_url}/api/python/health") as response:
                    if response.status == 200:
                        logger.info("System is ready for latency testing")
                        return
            except Exception:
                pass

            logger.info(f"Waiting for system to be ready... ({i + 1}/{max_wait // wait_interval})")
            await asyncio.sleep(wait_interval)

        raise RuntimeError("System not ready after maximum wait time")

    async def _run_latency_tests(self, iterations: int):
        """Run latency test iterations"""
        logger.info("Running latency tests...")

        for i in range(iterations):
            try:
                result = await self._single_latency_test()
                self.results.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(f"Completed {i + 1}/{iterations} iterations")

                # Small delay between tests
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in iteration {i + 1}: {e}")

        logger.info(f"Completed {len(self.results)} successful iterations")

    async def _single_latency_test(self) -> Dict[str, Any]:
        """Run single latency test and capture detailed metrics"""

        start_time = time.time()

        # Trigger a trading cycle and measure detailed latency
        async with self.session.post(
            f"{self.base_url}/api/test/trigger-trading-cycle",
            json={"symbol": "BTCUSDT", "force_cycle": True}
        ) as response:

            if response.status != 200:
                raise RuntimeError(f"Failed to trigger trading cycle: {response.status}")

            cycle_data = await response.json()

        total_time = (time.time() - start_time) * 1000  # Convert to ms

        # Extract detailed latency breakdown
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_latency_ms': total_time,
            'data_pipeline_ms': cycle_data.get('data_pipeline_latency_ms', 0),
            'ml_inference_ms': cycle_data.get('ml_inference_latency_ms', 0),
            'risk_check_ms': cycle_data.get('risk_check_latency_ms', 0),
            'execution_ms': cycle_data.get('execution_latency_ms', 0),
            'cache_hit_rate': cycle_data.get('cache_hit_rate', 0),
            'circuit_breaker_status': cycle_data.get('circuit_breaker_status', 'closed'),
            'signal_generated': cycle_data.get('signal_generated', False),
            'system_health': cycle_data.get('system_health', 'unknown')
        }

        return result

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze latency test results"""

        if not self.results:
            raise RuntimeError("No results to analyze")

        # Extract latency data
        total_latencies = [r['total_latency_ms'] for r in self.results]
        data_latencies = [r['data_pipeline_ms'] for r in self.results]
        ml_latencies = [r['ml_inference_ms'] for r in self.results]
        risk_latencies = [r['risk_check_ms'] for r in self.results]

        # Calculate statistics
        analysis = {
            'summary': {
                'total_tests': len(self.results),
                'success_rate': len([r for r in self.results if r['system_health'] == 'healthy']) / len(self.results),
                'signal_generation_rate': len([r for r in self.results if r['signal_generated']]) / len(self.results),
                'avg_cache_hit_rate': statistics.mean([r['cache_hit_rate'] for r in self.results])
            },
            'total_latency': {
                'mean_ms': statistics.mean(total_latencies),
                'median_ms': statistics.median(total_latencies),
                'p95_ms': np.percentile(total_latencies, 95),
                'p99_ms': np.percentile(total_latencies, 99),
                'max_ms': max(total_latencies),
                'min_ms': min(total_latencies),
                'std_ms': statistics.stdev(total_latencies)
            },
            'component_latency': {
                'data_pipeline': {
                    'mean_ms': statistics.mean(data_latencies),
                    'p95_ms': np.percentile(data_latencies, 95),
                    'target_ms': self.targets['data_pipeline_ms']
                },
                'ml_inference': {
                    'mean_ms': statistics.mean(ml_latencies),
                    'p95_ms': np.percentile(ml_latencies, 95),
                    'target_ms': self.targets['ml_inference_ms']
                },
                'risk_check': {
                    'mean_ms': statistics.mean(risk_latencies),
                    'p95_ms': np.percentile(risk_latencies, 95),
                    'target_ms': self.targets['risk_check_ms']
                }
            },
            'performance_against_targets': self._calculate_performance_scores(total_latencies, data_latencies, ml_latencies, risk_latencies),
            'outliers': self._identify_outliers(total_latencies),
            'trend_analysis': self._analyze_trends(total_latencies)
        }

        return analysis

    def _calculate_performance_scores(self, total_latencies, data_latencies, ml_latencies, risk_latencies) -> Dict[str, Any]:
        """Calculate performance scores against targets"""

        # Calculate percentage of tests meeting targets
        total_target_met = len([t for t in total_latencies if t <= self.targets['total_system_ms']])
        data_target_met = len([t for t in data_latencies if t <= self.targets['data_pipeline_ms']])
        ml_target_met = len([t for t in ml_latencies if t <= self.targets['ml_inference_ms']])
        risk_target_met = len([t for t in risk_latencies if t <= self.targets['risk_check_ms']])

        total_tests = len(total_latencies)

        return {
            'overall_score': (total_target_met / total_tests) * 100,
            'component_scores': {
                'data_pipeline': (data_target_met / total_tests) * 100,
                'ml_inference': (ml_target_met / total_tests) * 100,
                'risk_check': (risk_target_met / total_tests) * 100
            },
            'target_achievement_rates': {
                'total_system': f"{(total_target_met / total_tests) * 100:.1f}%",
                'data_pipeline': f"{(data_target_met / total_tests) * 100:.1f}%",
                'ml_inference': f"{(ml_target_met / total_tests) * 100:.1f}%",
                'risk_check': f"{(risk_target_met / total_tests) * 100:.1f}%"
            }
        }

    def _identify_outliers(self, latencies: List[float]) -> Dict[str, Any]:
        """Identify performance outliers"""

        latencies_array = np.array(latencies)
        q1, q3 = np.percentile(latencies_array, [25, 75])
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [l for l in latencies if l < lower_bound or l > upper_bound]

        return {
            'count': len(outliers),
            'percentage': (len(outliers) / len(latencies)) * 100,
            'values': outliers,
            'bounds': {'lower': lower_bound, 'upper': upper_bound}
        }

    def _analyze_trends(self, latencies: List[float]) -> Dict[str, Any]:
        """Analyze performance trends over time"""

        # Simple trend analysis - compare first half vs second half
        mid_point = len(latencies) // 2
        first_half = latencies[:mid_point]
        second_half = latencies[mid_point:]

        first_mean = statistics.mean(first_half)
        second_mean = statistics.mean(second_half)

        trend = "stable"
        if second_mean > first_mean * 1.05:
            trend = "degrading"
        elif second_mean < first_mean * 0.95:
            trend = "improving"

        return {
            'trend': trend,
            'first_half_mean': first_mean,
            'second_half_mean': second_mean,
            'percent_change': ((second_mean - first_mean) / first_mean) * 100
        }

    def _generate_report(self, analysis: Dict[str, Any]):
        """Generate comprehensive performance report"""

        # Console report
        self._print_console_report(analysis)

        # JSON report
        self._save_json_report(analysis)

        # Visual report
        self._generate_visualizations(analysis)

    def _print_console_report(self, analysis: Dict[str, Any]):
        """Print performance summary to console"""

        print("\n" + "="*60)
        print("ULTRA-LOW LATENCY PERFORMANCE VALIDATION REPORT")
        print("="*60)

        # Summary
        summary = analysis['summary']
        total_latency = analysis['total_latency']
        performance = analysis['performance_against_targets']

        print(f"\nSUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"  Signal Generation Rate: {summary['signal_generation_rate']*100:.1f}%")
        print(f"  Avg Cache Hit Rate: {summary['avg_cache_hit_rate']*100:.1f}%")

        print(f"\nTOTAL LATENCY PERFORMANCE:")
        print(f"  Target: <{self.targets['total_system_ms']}ms")
        print(f"  Mean: {total_latency['mean_ms']:.2f}ms")
        print(f"  Median: {total_latency['median_ms']:.2f}ms")
        print(f"  P95: {total_latency['p95_ms']:.2f}ms")
        print(f"  P99: {total_latency['p99_ms']:.2f}ms")
        print(f"  Max: {total_latency['max_ms']:.2f}ms")
        print(f"  Std Dev: {total_latency['std_ms']:.2f}ms")

        print(f"\nCOMPONENT PERFORMANCE:")
        for component, data in analysis['component_latency'].items():
            print(f"  {component.replace('_', ' ').title()}:")
            print(f"    Mean: {data['mean_ms']:.2f}ms (target: <{data['target_ms']}ms)")
            print(f"    P95: {data['p95_ms']:.2f}ms")

        print(f"\nTARGET ACHIEVEMENT:")
        print(f"  Overall Score: {performance['overall_score']:.1f}%")
        for metric, rate in performance['target_achievement_rates'].items():
            print(f"  {metric.replace('_', ' ').title()}: {rate}")

        # Outliers
        outliers = analysis['outliers']
        if outliers['count'] > 0:
            print(f"\nOUTLIERS:")
            print(f"  Count: {outliers['count']} ({outliers['percentage']:.1f}%)")
            print(f"  Range: {min(outliers['values']):.2f}ms - {max(outliers['values']):.2f}ms")

        # Trends
        trends = analysis['trend_analysis']
        print(f"\nTREND ANALYSIS:")
        print(f"  Trend: {trends['trend']}")
        print(f"  Change: {trends['percent_change']:+.2f}%")

        # Overall assessment
        overall_score = performance['overall_score']
        if overall_score >= 95:
            status = "🟢 EXCELLENT"
        elif overall_score >= 85:
            status = "🟡 GOOD"
        elif overall_score >= 70:
            status = "🟠 ACCEPTABLE"
        else:
            status = "🔴 NEEDS IMPROVEMENT"

        print(f"\nOVERALL ASSESSMENT: {status} ({overall_score:.1f}%)")
        print("="*60)

    def _save_json_report(self, analysis: Dict[str, Any]):
        """Save detailed JSON report"""

        report_data = {
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'validator_version': '1.0.0',
                'targets': self.targets,
                'test_parameters': {
                    'iterations': len(self.results),
                    'base_url': self.base_url
                }
            },
            'results': self.results,
            'analysis': analysis
        }

        report_file = f"latency_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"JSON report saved to: {report_file}")

    def _generate_visualizations(self, analysis: Dict[str, Any]):
        """Generate performance visualization charts"""

        try:
            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Ultra-Low Latency Performance Validation', fontsize=16, fontweight='bold')

            # 1. Total latency distribution
            total_latencies = [r['total_latency_ms'] for r in self.results]
            axes[0, 0].hist(total_latencies, bins=30, alpha=0.7, color='blue', edgecolor='black')
            axes[0, 0].axvline(self.targets['total_system_ms'], color='red', linestyle='--', label=f'Target: {self.targets["total_system_ms"]}ms')
            axes[0, 0].set_title('Total Latency Distribution')
            axes[0, 0].set_xlabel('Latency (ms)')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

            # 2. Component latency comparison
            components = ['Data Pipeline', 'ML Inference', 'Risk Check']
            means = [
                analysis['component_latency']['data_pipeline']['mean_ms'],
                analysis['component_latency']['ml_inference']['mean_ms'],
                analysis['component_latency']['risk_check']['mean_ms']
            ]
            targets = [
                self.targets['data_pipeline_ms'],
                self.targets['ml_inference_ms'],
                self.targets['risk_check_ms']
            ]

            x = np.arange(len(components))
            width = 0.35

            axes[0, 1].bar(x - width/2, means, width, label='Actual', alpha=0.7, color='blue')
            axes[0, 1].bar(x + width/2, targets, width, label='Target', alpha=0.7, color='red')
            axes[0, 1].set_title('Component Latency Comparison')
            axes[0, 1].set_xlabel('Component')
            axes[0, 1].set_ylabel('Latency (ms)')
            axes[0, 1].set_xticks(x)
            axes[0, 1].set_xticklabels(components)
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)

            # 3. Latency over time (trend)
            axes[1, 0].plot(total_latencies, alpha=0.7, color='green')
            axes[1, 0].axhline(self.targets['total_system_ms'], color='red', linestyle='--', label='Target')
            axes[1, 0].set_title('Latency Trend Over Time')
            axes[1, 0].set_xlabel('Test Iteration')
            axes[1, 0].set_ylabel('Latency (ms)')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)

            # 4. Performance score gauge
            score = analysis['performance_against_targets']['overall_score']
            colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
            axes[1, 1].barh(['Performance Score'], [score], color=colors[3] if score >= 85 else colors[2] if score >= 70 else colors[1])
            axes[1, 1].set_xlim(0, 100)
            axes[1, 1].set_title(f'Overall Performance Score: {score:.1f}%')
            axes[1, 1].set_xlabel('Score (%)')

            plt.tight_layout()

            chart_file = f"latency_validation_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"Performance charts saved to: {chart_file}")

        except Exception as e:
            logger.warning(f"Failed to generate visualizations: {e}")


async def main():
    """Main function"""

    parser = argparse.ArgumentParser(description='Validate ultra-low latency performance')
    parser.add_argument('--url', default='http://localhost:8008', help='Base URL for the trading agent')
    parser.add_argument('--target-ms', type=int, default=50, help='Target total latency in milliseconds')
    parser.add_argument('--iterations', type=int, default=100, help='Number of test iterations')
    parser.add_argument('--output-dir', default='.', help='Output directory for reports')

    args = parser.parse_args()

    # Update targets if custom target specified
    validator = LatencyValidator(args.url)
    if args.target_ms != 50:
        validator.targets['total_system_ms'] = args.target_ms

    async with validator:
        try:
            analysis = await validator.validate_latency(args.iterations)

            # Determine exit code based on performance
            overall_score = analysis['performance_against_targets']['overall_score']
            if overall_score >= 85:
                exit_code = 0  # Success
            elif overall_score >= 70:
                exit_code = 1  # Warning
            else:
                exit_code = 2  # Failure

            return exit_code

        except Exception as e:
            logger.error(f"Latency validation failed: {e}")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)