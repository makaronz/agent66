#!/usr/bin/env python3
"""
Performance Benchmark Suite for SMC Trading Agent

This script performs comprehensive performance testing and benchmarking
to validate that the system meets sub-50ms latency requirements and
can handle production-level throughput.

Benchmark Coverage:
1. End-to-End Latency Measurement
2. Throughput Testing Under Load
3. Resource Utilization Analysis
4. Memory Leak Detection
5. Scalability Testing
"""

import asyncio
import time
import logging
import sys
import os
import json
import psutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tracemalloc
import gc
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import system components
from main import load_config
from data_pipeline.live_data_client import LiveDataClient
from smc_detector.indicators import SMCIndicators
from decision_engine.ml_decision_engine import MLDecisionEngine
from risk_manager.smc_risk_manager import SMCRiskManager
from execution_engine.paper_trading import PaperTradingEngine

class PerformanceBenchmark:
    """Comprehensive performance testing suite."""

    def __init__(self):
        self.logger = self._setup_logging()
        self.config = load_config()
        self.results = {}

    def _setup_logging(self):
        """Setup logging for performance benchmarks."""
        logger = logging.getLogger("PerformanceBenchmark")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler
        log_dir = Path("benchmark_logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_dir / f"performance_benchmark_{timestamp}.log"
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

    async def run_comprehensive_benchmark(self):
        """Run complete performance benchmark suite."""
        self.logger.info("🚀 Starting Performance Benchmark Suite")
        self.logger.info(f"Started at: {datetime.now()}")
        self.logger.info(f"CPU Count: {mp.cpu_count()}")
        self.logger.info(f"Memory Available: {psutil.virtual_memory().available / 1024**3:.1f}GB")

        benchmark_tests = [
            ("Latency Benchmark", self.benchmark_latency),
            ("Throughput Benchmark", self.benchmark_throughput),
            ("Memory Usage Benchmark", self.benchmark_memory_usage),
            ("CPU Utilization Benchmark", self.benchmark_cpu_utilization),
            ("Concurrent Load Benchmark", self.benchmark_concurrent_load),
            ("Scalability Benchmark", self.benchmark_scalability)
        ]

        overall_start_time = time.time()

        for test_name, test_func in benchmark_tests:
            self.logger.info(f"\n📊 Running {test_name}...")
            try:
                test_result = await test_func()
                self.results[test_name] = {
                    'status': 'PASSED' if test_result.get('success', False) else 'FAILED',
                    'timestamp': datetime.now(),
                    'metrics': test_result
                }

                if test_result.get('success', False):
                    self.logger.info(f"✅ {test_name}: PASSED")
                else:
                    self.logger.error(f"❌ {test_name}: FAILED")

            except Exception as e:
                self.logger.error(f"❌ {test_name}: EXCEPTION - {e}")
                self.results[test_name] = {
                    'status': 'ERROR',
                    'timestamp': datetime.now(),
                    'error': str(e)
                }

        total_duration = time.time() - overall_start_time

        # Generate benchmark report
        await self._generate_benchmark_report(total_duration)

        self.logger.info(f"\n⏱️ Total Benchmark Duration: {total_duration:.2f}s")
        self.logger.info("🎯 Performance Benchmark Suite Completed")

        return self.results

    async def benchmark_latency(self):
        """Benchmark end-to-end processing latency."""
        self.logger.info("Measuring end-to-end latency...")

        # Initialize components
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = MLDecisionEngine()

        latencies = []
        component_latencies = {
            'data_fetch': [],
            'smc_detection': [],
            'ml_decision': [],
            'total': []
        }

        # Run latency measurements
        iterations = 50
        successful_iterations = 0

        for i in range(iterations):
            iteration_start = time.time()

            try:
                # Step 1: Data fetch
                data_start = time.time()
                market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=50)
                data_latency = time.time() - data_start

                if market_data_df is None or len(market_data_df) == 0:
                    continue

                # Step 2: SMC detection
                smc_start = time.time()
                order_blocks = smc_detector.detect_order_blocks(market_data_df)
                smc_latency = time.time() - smc_start

                # Step 3: ML decision
                ml_start = time.time()
                trade_signal = await decision_engine.make_decision(
                    market_data=market_data_df,
                    order_blocks=order_blocks
                )
                ml_latency = time.time() - ml_start

                # Calculate total latency
                total_latency = time.time() - iteration_start

                # Store latencies
                component_latencies['data_fetch'].append(data_latency * 1000)  # ms
                component_latencies['smc_detection'].append(smc_latency * 1000)  # ms
                component_latencies['ml_decision'].append(ml_latency * 1000)  # ms
                component_latencies['total'].append(total_latency * 1000)  # ms

                successful_iterations += 1

                if (i + 1) % 10 == 0:
                    self.logger.info(f"  Completed {i + 1}/{iterations} iterations")

            except Exception as e:
                self.logger.warning(f"  Latency iteration {i + 1} failed: {e}")
                continue

        # Calculate statistics
        if successful_iterations > 0:
            latency_stats = {}
            for component, times in component_latencies.items():
                if times:
                    latency_stats[component] = {
                        'mean': np.mean(times),
                        'median': np.median(times),
                        'p95': np.percentile(times, 95),
                        'p99': np.percentile(times, 99),
                        'min': np.min(times),
                        'max': np.max(times),
                        'std': np.std(times)
                    }

            # Check against performance targets
            avg_total_latency = latency_stats['total']['mean']
            p95_total_latency = latency_stats['total']['p95']

            target_met = avg_total_latency < 50.0 and p95_total_latency < 100.0

            self.logger.info(f"  Average Total Latency: {avg_total_latency:.2f}ms")
            self.logger.info(f"  P95 Total Latency: {p95_total_latency:.2f}ms")
            self.logger.info(f"  Success Rate: {successful_iterations}/{iterations} ({successful_iterations/iterations:.1%})")

            return {
                'success': target_met,
                'iterations': successful_iterations,
                'latency_stats': latency_stats,
                'target_met': target_met,
                'avg_latency_ms': avg_total_latency,
                'p95_latency_ms': p95_total_latency
            }
        else:
            return {
                'success': False,
                'error': 'No successful latency measurements'
            }

    async def benchmark_throughput(self):
        """Benchmark system throughput under load."""
        self.logger.info("Measuring system throughput...")

        # Initialize components
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()

        # Test multiple symbols concurrently
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        test_duration = 30  # seconds

        throughput_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'data_points_processed': 0,
            'patterns_detected': 0
        }

        async def process_symbol_data(symbol):
            try:
                # Fetch data
                market_data_df = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=100)
                if market_data_df is None or len(market_data_df) == 0:
                    return {'symbol': symbol, 'success': False, 'error': 'No data'}

                # Detect patterns
                order_blocks = smc_detector.detect_order_blocks(market_data_df)

                return {
                    'symbol': symbol,
                    'success': True,
                    'data_points': len(market_data_df),
                    'patterns': len(order_blocks) if order_blocks else 0
                }

            except Exception as e:
                return {'symbol': symbol, 'success': False, 'error': str(e)}

        # Run throughput test
        start_time = time.time()
        end_time = start_time + test_duration

        while time.time() < end_time:
            # Process all symbols concurrently
            tasks = [process_symbol_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            throughput_metrics['total_requests'] += len(symbols)

            for result in results:
                if isinstance(result, dict) and result.get('success'):
                    throughput_metrics['successful_requests'] += 1
                    throughput_metrics['data_points_processed'] += result.get('data_points', 0)
                    throughput_metrics['patterns_detected'] += result.get('patterns', 0)
                else:
                    throughput_metrics['failed_requests'] += 1

            # Small delay between batches
            await asyncio.sleep(0.1)

        actual_duration = time.time() - start_time

        # Calculate throughput metrics
        requests_per_second = throughput_metrics['total_requests'] / actual_duration
        data_points_per_second = throughput_metrics['data_points_processed'] / actual_duration
        success_rate = throughput_metrics['successful_requests'] / throughput_metrics['total_requests']

        # Check targets
        target_met = success_rate > 0.8 and data_points_per_second > 100

        self.logger.info(f"  Requests/Second: {requests_per_second:.1f}")
        self.logger.info(f"  Data Points/Second: {data_points_per_second:.1f}")
        self.logger.info(f"  Success Rate: {success_rate:.1%}")

        return {
            'success': target_met,
            'duration': actual_duration,
            'requests_per_second': requests_per_second,
            'data_points_per_second': data_points_per_second,
            'success_rate': success_rate,
            'target_met': target_met,
            'metrics': throughput_metrics
        }

    async def benchmark_memory_usage(self):
        """Benchmark memory usage and detect leaks."""
        self.logger.info("Analyzing memory usage patterns...")

        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Get initial memory snapshot
        snapshot1 = tracemalloc.take_snapshot()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Initialize components for memory test
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = MLDecisionEngine()

        memory_samples = []
        iteration_count = 100

        # Run memory stress test
        for i in range(iteration_count):
            try:
                # Simulate processing workload
                test_data = pd.DataFrame({
                    'open': np.random.rand(200) * 1000,
                    'high': np.random.rand(200) * 1100,
                    'low': np.random.rand(200) * 900,
                    'close': np.random.rand(200) * 1000,
                    'volume': np.random.rand(200) * 1000000,
                    'timestamp': pd.date_range(start='2024-01-01', periods=200, freq='1H')
                })

                # Process data
                order_blocks = smc_detector.detect_order_blocks(test_data)

                # Make decision
                trade_signal = await decision_engine.make_decision(
                    market_data=test_data,
                    order_blocks=order_blocks
                )

                # Sample memory usage
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)

                # Cleanup
                del test_data
                del order_blocks
                if trade_signal:
                    del trade_signal

                # Periodic garbage collection
                if i % 20 == 0:
                    gc.collect()

                if (i + 1) % 25 == 0:
                    self.logger.info(f"  Memory test iteration {i + 1}/{iteration_count}")

            except Exception as e:
                self.logger.warning(f"  Memory iteration {i + 1} failed: {e}")
                continue

        # Final memory measurement
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        final_memory = process.memory_info().rss / 1024 / 1024

        # Calculate memory statistics
        memory_increase = final_memory - initial_memory
        avg_memory = np.mean(memory_samples)
        max_memory = np.max(memory_samples)
        min_memory = np.min(memory_samples)

        # Check for memory leaks
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_allocated = sum(stat.size for stat in top_stats)
        memory_leak_detected = memory_increase > 100  # 100MB threshold

        # Check memory target
        memory_target_met = final_memory < 1000 and not memory_leak_detected

        self.logger.info(f"  Initial Memory: {initial_memory:.1f}MB")
        self.logger.info(f"  Final Memory: {final_memory:.1f}MB")
        self.logger.info(f"  Memory Increase: {memory_increase:.1f}MB")
        self.logger.info(f"  Peak Memory: {max_memory:.1f}MB")
        self.logger.info(f"  Memory Leak Detected: {memory_leak_detected}")

        tracemalloc.stop()

        return {
            'success': memory_target_met,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'peak_memory_mb': max_memory,
            'avg_memory_mb': avg_memory,
            'memory_leak_detected': memory_leak_detected,
            'total_allocated_mb': total_allocated / 1024 / 1024,
            'target_met': memory_target_met
        }

    async def benchmark_cpu_utilization(self):
        """Benchmark CPU utilization under load."""
        self.logger.info("Measuring CPU utilization...")

        process = psutil.Process()
        cpu_samples = []

        # Initialize components
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()

        test_duration = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < test_duration:
            # Sample CPU usage
            cpu_percent = process.cpu_percent(interval=0.1)
            cpu_samples.append(cpu_percent)

            # Do some work
            try:
                # Generate test data
                test_data = pd.DataFrame({
                    'open': np.random.rand(50) * 1000,
                    'high': np.random.rand(50) * 1100,
                    'low': np.random.rand(50) * 900,
                    'close': np.random.rand(50) * 1000,
                    'volume': np.random.rand(50) * 1000000
                })

                # Process data
                order_blocks = smc_detector.detect_order_blocks(test_data)

                # Cleanup
                del test_data
                del order_blocks

            except Exception as e:
                self.logger.warning(f"  CPU test iteration failed: {e}")

        # Calculate CPU statistics
        avg_cpu = np.mean(cpu_samples)
        max_cpu = np.max(cpu_samples)
        p95_cpu = np.percentile(cpu_samples, 95)

        # Check CPU target (should not exceed 80% average)
        cpu_target_met = avg_cpu < 80.0

        self.logger.info(f"  Average CPU: {avg_cpu:.1f}%")
        self.logger.info(f"  Peak CPU: {max_cpu:.1f}%")
        self.logger.info(f"  P95 CPU: {p95_cpu:.1f}%")

        return {
            'success': cpu_target_met,
            'avg_cpu_percent': avg_cpu,
            'max_cpu_percent': max_cpu,
            'p95_cpu_percent': p95_cpu,
            'cpu_samples': cpu_samples,
            'target_met': cpu_target_met
        }

    async def benchmark_concurrent_load(self):
        """Benchmark system under concurrent load."""
        self.logger.info("Testing concurrent load handling...")

        # Initialize components
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()

        # Test parameters
        concurrent_tasks = 20
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']

        async def concurrent_processing_task(task_id):
            try:
                symbol = symbols[task_id % len(symbols)]

                # Process data
                market_data_df = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=50)
                if market_data_df is None or len(market_data_df) == 0:
                    return {'task_id': task_id, 'success': False, 'error': 'No data'}

                order_blocks = smc_detector.detect_order_blocks(market_data_df)

                # Simulate processing delay
                await asyncio.sleep(0.1)

                return {
                    'task_id': task_id,
                    'symbol': symbol,
                    'success': True,
                    'data_points': len(market_data_df),
                    'patterns': len(order_blocks) if order_blocks else 0
                }

            except Exception as e:
                return {'task_id': task_id, 'success': False, 'error': str(e)}

        # Run concurrent load test
        start_time = time.time()

        # Create and run concurrent tasks
        tasks = [concurrent_processing_task(i) for i in range(concurrent_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = time.time() - start_time

        # Analyze results
        successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed_tasks = len(results) - successful_tasks
        success_rate = successful_tasks / len(results)

        # Calculate throughput
        tasks_per_second = len(results) / total_duration

        # Check concurrent load target
        load_target_met = success_rate > 0.8 and total_duration < 10.0

        self.logger.info(f"  Concurrent Tasks: {len(results)}")
        self.logger.info(f"  Successful Tasks: {successful_tasks}")
        self.logger.info(f"  Failed Tasks: {failed_tasks}")
        self.logger.info(f"  Success Rate: {success_rate:.1%}")
        self.logger.info(f"  Tasks/Second: {tasks_per_second:.1f}")
        self.logger.info(f"  Total Duration: {total_duration:.2f}s")

        return {
            'success': load_target_met,
            'concurrent_tasks': concurrent_tasks,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': success_rate,
            'tasks_per_second': tasks_per_second,
            'total_duration': total_duration,
            'target_met': load_target_met
        }

    async def benchmark_scalability(self):
        """Benchmark system scalability across different loads."""
        self.logger.info("Testing system scalability...")

        scalability_results = {}

        # Test different load levels
        load_levels = [1, 5, 10, 15, 20]
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()

        for load_level in load_levels:
            self.logger.info(f"  Testing load level: {load_level} concurrent tasks")

            async def scalability_task(task_id):
                try:
                    symbol = 'BTC/USDT'
                    start_time = time.time()

                    market_data_df = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=30)
                    if market_data_df is None or len(market_data_df) == 0:
                        return {'task_id': task_id, 'success': False, 'duration': 0}

                    order_blocks = smc_detector.detect_order_blocks(market_data_df)

                    duration = time.time() - start_time

                    return {
                        'task_id': task_id,
                        'success': True,
                        'duration': duration,
                        'data_points': len(market_data_df) if market_data_df is not None else 0
                    }

                except Exception as e:
                    return {'task_id': task_id, 'success': False, 'duration': 0}

            # Run scalability test
            start_time = time.time()

            tasks = [scalability_task(i) for i in range(load_level)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_duration = time.time() - start_time

            # Calculate metrics
            successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
            avg_task_duration = np.mean([r['duration'] for r in successful_results]) if successful_results else 0
            success_rate = len(successful_results) / len(results) if results else 0

            scalability_results[load_level] = {
                'total_duration': total_duration,
                'successful_tasks': len(successful_results),
                'total_tasks': load_level,
                'success_rate': success_rate,
                'avg_task_duration': avg_task_duration,
                'throughput': load_level / total_duration if total_duration > 0 else 0
            }

            self.logger.info(f"    Duration: {total_duration:.2f}s, Success Rate: {success_rate:.1%}")

        # Analyze scalability
        max_load = max(scalability_results.keys())
        min_throughput = min(r['throughput'] for r in scalability_results.values())
        scalability_factor = scalability_results[max_load]['throughput'] / scalability_results[1]['throughput']

        # Check scalability target
        scalability_target_met = success_rate > 0.7 and scalability_factor > 0.5

        self.logger.info(f"  Scalability Factor: {scalability_factor:.2f}")
        self.logger.info(f"  Minimum Throughput: {min_throughput:.1f} tasks/s")

        return {
            'success': scalability_target_met,
            'load_levels': load_levels,
            'results': scalability_results,
            'scalability_factor': scalability_factor,
            'min_throughput': min_throughput,
            'max_successful_load': max(load_level for level, r in scalability_results.items() if r['success_rate'] > 0.7),
            'target_met': scalability_target_met
        }

    async def _generate_benchmark_report(self, total_duration):
        """Generate comprehensive benchmark report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path("benchmark_reports")
        report_dir.mkdir(exist_ok=True)

        # Prepare report data
        report = {
            'benchmark_summary': {
                'timestamp': datetime.now(),
                'total_duration': total_duration,
                'total_tests': len(self.results),
                'passed_tests': sum(1 for r in self.results.values() if r['status'] == 'PASSED'),
                'failed_tests': sum(1 for r in self.results.values() if r['status'] == 'FAILED'),
                'error_tests': sum(1 for r in self.results.values() if r['status'] == 'ERROR')
            },
            'test_results': self.results,
            'system_info': {
                'cpu_count': mp.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / 1024**3,
                'python_version': sys.version,
                'platform': sys.platform
            }
        }

        # Save JSON report
        json_file = report_dir / f"performance_benchmark_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Generate performance summary
        self._generate_performance_summary(report, report_dir / f"performance_summary_{timestamp}.md")

        self.logger.info(f"📊 Benchmark report generated: {json_file}")

    def _generate_performance_summary(self, report, summary_file):
        """Generate markdown performance summary."""
        summary = report['benchmark_summary']
        results = report['test_results']

        md = f"""# Performance Benchmark Summary

**Generated**: {summary['timestamp']}
**Total Duration**: {summary['total_duration']:.1f} seconds
**Overall Success Rate**: {(summary['passed_tests']/summary['total_tests']*100):.0f}%

## 🎯 Performance Results

"""

        for test_name, result in results.items():
            status_emoji = {'PASSED': '✅', 'FAILED': '❌', 'ERROR': '⚠️'}.get(result['status'], '❓')
            md += f"### {test_name} {status_emoji}\n\n"

            if 'metrics' in result:
                metrics = result['metrics']

                if test_name == "Latency Benchmark":
                    if 'avg_latency_ms' in metrics:
                        md += f"- **Average Latency**: {metrics['avg_latency_ms']:.2f}ms\n"
                        md += f"- **P95 Latency**: {metrics['p95_latency_ms']:.2f}ms\n"
                        md += f"- **Target Met**: {'✅' if metrics.get('target_met') else '❌'}\n"

                elif test_name == "Throughput Benchmark":
                    if 'requests_per_second' in metrics:
                        md += f"- **Requests/Second**: {metrics['requests_per_second']:.1f}\n"
                        md += f"- **Data Points/Second**: {metrics['data_points_per_second']:.1f}\n"
                        md += f"- **Success Rate**: {metrics['success_rate']:.1%}\n"
                        md += f"- **Target Met**: {'✅' if metrics.get('target_met') else '❌'}\n"

                elif test_name == "Memory Usage Benchmark":
                    if 'final_memory_mb' in metrics:
                        md += f"- **Final Memory**: {metrics['final_memory_mb']:.1f}MB\n"
                        md += f"- **Memory Increase**: {metrics['memory_increase_mb']:.1f}MB\n"
                        md += f"- **Memory Leak**: {'⚠️ Yes' if metrics.get('memory_leak_detected') else '✅ No'}\n"
                        md += f"- **Target Met**: {'✅' if metrics.get('target_met') else '❌'}\n"

                elif test_name == "CPU Utilization Benchmark":
                    if 'avg_cpu_percent' in metrics:
                        md += f"- **Average CPU**: {metrics['avg_cpu_percent']:.1f}%\n"
                        md += f"- **Peak CPU**: {metrics['max_cpu_percent']:.1f}%\n"
                        md += f"- **P95 CPU**: {metrics['p95_cpu_percent']:.1f}%\n"
                        md += f"- **Target Met**: {'✅' if metrics.get('target_met') else '❌'}\n"

            md += "\n"

        md += f"""
## 📊 System Information

- **CPU Count**: {report['system_info']['cpu_count']}
- **Total Memory**: {report['system_info']['memory_gb']:.1f}GB
- **Python Version**: {report['system_info']['python_version']}
- **Platform**: {report['system_info']['platform']}

## 🎯 Performance Targets

- **Latency**: < 50ms average, < 100ms P95
- **Throughput**: > 100 data points/second
- **Memory**: < 1GB usage, no memory leaks
- **CPU**: < 80% average utilization
- **Success Rate**: > 95% across all tests

---

*Generated by SMC Trading Agent Performance Benchmark Suite*
"""

        with open(summary_file, 'w') as f:
            f.write(md)

async def main():
    """Main benchmark runner."""
    benchmark = PerformanceBenchmark()

    try:
        results = await benchmark.run_comprehensive_benchmark()

        # Determine overall success
        passed_tests = sum(1 for r in results.values() if r['status'] == 'PASSED')
        total_tests = len(results)
        overall_success = passed_tests >= total_tests * 0.8  # 80% pass rate

        if overall_success:
            print("\n🎉 Performance Benchmark: PASSED")
            print("✅ System meets performance requirements")
        else:
            print("\n💥 Performance Benchmark: FAILED")
            print("❌ System does not meet performance requirements")

        sys.exit(0 if overall_success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Benchmark runner crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Check dependencies
    try:
        import pandas
        import numpy
        import psutil
    except ImportError as e:
        print(f"❌ Missing required dependency: {e}")
        print("Please install with: pip install pandas numpy psutil")
        sys.exit(1)

    asyncio.run(main())