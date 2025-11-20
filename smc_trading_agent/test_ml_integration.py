#!/usr/bin/env python3
"""
ML Decision Engine Integration Test

This script tests the complete ML Decision Engine integration with the SMC trading system.
It validates all components including feature engineering, model inference, and decision making.

Usage:
    python test_ml_integration.py [--mode shadow|canary|full] [--symbols BTC/USDT]

Test Coverage:
- Configuration management
- Feature engineering
- Model loading and inference
- Decision engine integration
- Performance monitoring
- A/B testing functionality
"""

import asyncio
import argparse
import logging
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from decision_engine import (
    get_ml_decision_engine,
    get_adaptive_model_selector,
    get_ml_config,
    ModelMode,
    DeploymentStage
)
from decision_engine.ml_config import MLConfigManager
from smc_detector.indicators import SMCIndicators
from decision_engine.ml_decision_engine import FeatureEngineer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test ML Decision Engine Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--mode',
        choices=['shadow', 'canary', 'full'],
        default='shadow',
        help='Deployment mode for testing (default: shadow)'
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['BTC/USDT'],
        help='Trading symbols to test (default: BTC/USDT)'
    )

    parser.add_argument(
        '--samples',
        type=int,
        default=10,
        help='Number of test samples to generate (default: 10)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--performance-test',
        action='store_true',
        help='Run performance benchmark tests'
    )

    return parser.parse_args()


def generate_test_market_data(n_samples: int = 100) -> pd.DataFrame:
    """Generate realistic test market data."""
    np.random.seed(42)  # For reproducible tests

    # Generate timestamps
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(hours=n_samples),
        periods=n_samples,
        freq='1h'
    )

    # Generate realistic price movements
    base_price = 50000.0
    prices = [base_price]

    for i in range(1, n_samples):
        # Add trend and noise
        trend = np.random.normal(0, 0.001)  # Small trend
        noise = np.random.normal(0, 0.01)   # 1% volatility
        price_change = trend + noise
        new_price = prices[-1] * (1 + price_change)
        prices.append(max(new_price, 1000))  # Ensure positive price

    # Generate OHLCV data
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Generate realistic OHLC
        high_noise = abs(np.random.normal(0, 0.005))
        low_noise = abs(np.random.normal(0, 0.005))

        open_price = close * (1 + np.random.normal(0, 0.002))
        high_price = max(open_price, close) * (1 + high_noise)
        low_price = min(open_price, close) * (1 - low_noise)

        # Ensure OHLC relationships
        high_price = max(high_price, open_price, close)
        low_price = min(low_price, open_price, close)

        volume = np.random.lognormal(mean=10, sigma=0.5)

        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close,
            'volume': volume
        })

    return pd.DataFrame(data)


def generate_test_order_blocks(market_data: pd.DataFrame) -> list:
    """Generate test order blocks for testing."""
    order_blocks = []

    # Create a few sample order blocks
    for i in range(2):
        if i < len(market_data) - 10:
            row = market_data.iloc[i * 10]
            order_blocks.append({
                'timestamp': row['timestamp'].isoformat(),
                'type': 'bullish' if i % 2 == 0 else 'bearish',
                'price_level': (row['high'], row['low']),
                'strength_volume': np.random.uniform(0.5, 1.0),
                'strength': np.random.uniform(0.5, 1.0)
            })

    return order_blocks


class MLIntegrationTester:
    """Comprehensive ML integration test suite."""

    def __init__(self, deployment_mode: DeploymentStage):
        self.deployment_mode = deployment_mode
        self.test_results = {}
        self.start_time = datetime.now()

    async def run_all_tests(self, symbols: list, n_samples: int):
        """Run all integration tests."""
        logger.info("=" * 80)
        logger.info("ML Decision Engine Integration Test Suite")
        logger.info("=" * 80)
        logger.info(f"Deployment Mode: {self.deployment_mode.value}")
        logger.info(f"Test Symbols: {symbols}")
        logger.info(f"Test Samples: {n_samples}")

        try:
            # Test 1: Configuration Management
            await self.test_configuration_management()

            # Test 2: Feature Engineering
            await self.test_feature_engineering(symbols, n_samples)

            # Test 3: ML Decision Engine
            await self.test_ml_decision_engine(symbols, n_samples)

            # Test 4: Backward Compatibility
            await self.test_backward_compatibility(symbols, n_samples)

            # Test 5: Performance Monitoring
            await self.test_performance_monitoring()

            # Test 6: A/B Testing
            await self.test_ab_testing()

            # Generate final report
            self.generate_test_report()

            return all(result.get('passed', False) for result in self.test_results.values())

        except Exception as e:
            logger.error(f"Test suite failed: {str(e)}", exc_info=True)
            return False

    async def test_configuration_management(self):
        """Test configuration management."""
        logger.info("\n🔧 Testing Configuration Management...")

        try:
            # Test configuration loading
            ml_config = get_ml_config()
            config = ml_config.get_config()

            # Test deployment stage
            original_stage = config.deployment_stage
            ml_config.set_deployment_stage(self.deployment_mode)

            assert ml_config.config.deployment_stage == self.deployment_mode, \
                f"Failed to set deployment stage to {self.deployment_mode.value}"

            # Test ML enabled status
            is_enabled = ml_config.is_ml_enabled()
            should_use_ml = ml_config.should_use_ml_for_decision()

            logger.info(f"  ✅ ML Enabled: {is_enabled}")
            logger.info(f"  ✅ Should Use ML: {should_use_ml}")

            # Test model weights
            weights = ml_config.get_model_weights()
            logger.info(f"  ✅ Model Weights: {weights}")

            # Test validation
            issues = ml_config.validate_config()
            if issues:
                logger.warning(f"  ⚠️ Configuration issues: {issues}")
            else:
                logger.info("  ✅ Configuration validation passed")

            # Restore original stage
            ml_config.set_deployment_stage(original_stage)

            self.test_results['configuration'] = {
                'passed': True,
                'ml_enabled': is_enabled,
                'should_use_ml': should_use_ml,
                'model_weights': weights,
                'validation_issues': issues
            }

        except Exception as e:
            logger.error(f"  ❌ Configuration test failed: {str(e)}")
            self.test_results['configuration'] = {'passed': False, 'error': str(e)}

    async def test_feature_engineering(self, symbols: list, n_samples: int):
        """Test feature engineering."""
        logger.info("\n⚙️ Testing Feature Engineering...")

        try:
            # Generate test data
            market_data = generate_test_market_data(n_samples)
            order_blocks = generate_test_order_blocks(market_data)

            # Initialize feature engineer
            feature_engineer = FeatureEngineer()

            # Test SMC pattern extraction
            smc_patterns = {
                'order_blocks': order_blocks,
                'coch_patterns': [],
                'bos_patterns': [],
                'liquidity_sweeps': []
            }

            features = feature_engineer.extract_smc_features(market_data, smc_patterns)

            # Validate features
            feature_array = features.to_array()
            assert len(feature_array) == 16, f"Expected 16 features, got {len(feature_array)}"

            # Test individual feature categories
            assert 0 <= features.price_momentum <= 1, "Price momentum out of range"
            assert 0 <= features.volatility <= 1, "Volatility out of range"
            assert 0 <= features.rsi <= 100, "RSI out of range"

            logger.info(f"  ✅ Feature extraction successful")
            logger.info(f"  ✅ Feature vector length: {len(feature_array)}")
            logger.info(f"  ✅ Price Momentum: {features.price_momentum:.4f}")
            logger.info(f"  ✅ Volatility: {features.volatility:.4f}")
            logger.info(f"  ✅ RSI: {features.rsi:.2f}")

            self.test_results['feature_engineering'] = {
                'passed': True,
                'feature_count': len(feature_array),
                'sample_features': {
                    'price_momentum': features.price_momentum,
                    'volatility': features.volatility,
                    'rsi': features.rsi,
                    'order_block_strength': features.order_block_strength
                }
            }

        except Exception as e:
            logger.error(f"  ❌ Feature engineering test failed: {str(e)}")
            self.test_results['feature_engineering'] = {'passed': False, 'error': str(e)}

    async def test_ml_decision_engine(self, symbols: list, n_samples: int):
        """Test ML decision engine."""
        logger.info("\n🤖 Testing ML Decision Engine...")

        try:
            # Generate test data
            market_data = generate_test_market_data(n_samples)
            order_blocks = generate_test_order_blocks(market_data)

            # Initialize ML decision engine
            ml_engine = get_ml_decision_engine()

            # Test decision making
            decision = await ml_engine.make_decision(market_data, order_blocks)

            if decision:
                # Validate decision structure
                required_fields = ['action', 'symbol', 'entry_price', 'confidence', 'decision_method']
                for field in required_fields:
                    assert field in decision, f"Missing required field: {field}"

                # Validate action
                assert decision['action'] in ['BUY', 'SELL'], f"Invalid action: {decision['action']}"
                assert 0 <= decision['confidence'] <= 1, f"Invalid confidence: {decision['confidence']}"

                logger.info(f"  ✅ Decision generated successfully")
                logger.info(f"  ✅ Action: {decision['action']}")
                logger.info(f"  ✅ Entry Price: ${decision['entry_price']:.2f}")
                logger.info(f"  ✅ Confidence: {decision['confidence']:.3f}")
                logger.info(f"  ✅ Decision Method: {decision['decision_method']}")

                # Test ML-specific fields if present
                if 'ml_details' in decision:
                    ml_details = decision['ml_details']
                    logger.info(f"  ✅ ML Details: {ml_details.get('market_conditions', {}).get('regime', 'unknown')} regime")

                self.test_results['ml_decision_engine'] = {
                    'passed': True,
                    'decision_generated': True,
                    'action': decision['action'],
                    'confidence': decision['confidence'],
                    'method': decision['decision_method'],
                    'has_ml_details': 'ml_details' in decision
                }

            else:
                logger.warning("  ⚠️ No decision generated (may be normal if no patterns detected)")
                self.test_results['ml_decision_engine'] = {
                    'passed': True,
                    'decision_generated': False,
                    'reason': 'no_patterns_detected'
                }

            # Test performance monitoring
            perf_summary = ml_engine.get_performance_summary()
            self.test_results['ml_decision_engine']['performance_summary'] = perf_summary

        except Exception as e:
            logger.error(f"  ❌ ML decision engine test failed: {str(e)}")
            self.test_results['ml_decision_engine'] = {'passed': False, 'error': str(e)}

    async def test_backward_compatibility(self, symbols: list, n_samples: int):
        """Test backward compatibility with AdaptiveModelSelector."""
        logger.info("\n🔄 Testing Backward Compatibility...")

        try:
            # Generate test data
            market_data = generate_test_market_data(n_samples)
            order_blocks = generate_test_order_blocks(market_data)

            # Initialize adaptive model selector
            model_selector = get_adaptive_model_selector()

            # Test decision making with backward-compatible interface
            decision = await model_selector.make_decision(order_blocks, market_data)

            if decision:
                # Validate backward-compatible structure
                required_fields = ['action', 'symbol', 'entry_price', 'confidence']
                for field in required_fields:
                    assert field in decision, f"Missing required field: {field}"

                logger.info(f"  ✅ Backward-compatible decision generated")
                logger.info(f"  ✅ Action: {decision['action']}")
                logger.info(f"  ✅ Confidence: {decision['confidence']:.3f}")

                self.test_results['backward_compatibility'] = {
                    'passed': True,
                    'decision_generated': True,
                    'action': decision['action'],
                    'confidence': decision['confidence']
                }

            else:
                logger.warning("  ⚠️ No backward-compatible decision generated")
                self.test_results['backward_compatibility'] = {
                    'passed': True,
                    'decision_generated': False,
                    'reason': 'no_patterns_detected'
                }

        except Exception as e:
            logger.error(f"  ❌ Backward compatibility test failed: {str(e)}")
            self.test_results['backward_compatibility'] = {'passed': False, 'error': str(e)}

    async def test_performance_monitoring(self):
        """Test performance monitoring capabilities."""
        logger.info("\n📊 Testing Performance Monitoring...")

        try:
            ml_config = get_ml_config()
            monitoring_config = ml_config.get_monitoring_config()

            # Test monitoring configuration
            assert monitoring_config is not None, "Monitoring config not found"

            logger.info(f"  ✅ Monitoring Enabled: {monitoring_config.enabled}")
            logger.info(f"  ✅ Inference Time Alert: {monitoring_config.inference_time_alert_ms}ms")
            logger.info(f"  ✅ Accuracy Alert Threshold: {monitoring_config.accuracy_alert_threshold}")

            # Test configuration validation
            config_summary = ml_config.get_config_summary()
            assert 'deployment' in config_summary, "Missing deployment summary"
            assert 'models' in config_summary, "Missing models summary"

            logger.info(f"  ✅ Configuration summary generated")
            logger.info(f"  ✅ Deployment Stage: {config_summary['deployment']['stage']}")
            logger.info(f"  ✅ ML Enabled: {config_summary['deployment']['ml_enabled']}")

            self.test_results['performance_monitoring'] = {
                'passed': True,
                'monitoring_enabled': monitoring_config.enabled,
                'inference_time_alert': monitoring_config.inference_time_alert_ms,
                'accuracy_alert_threshold': monitoring_config.accuracy_alert_threshold
            }

        except Exception as e:
            logger.error(f"  ❌ Performance monitoring test failed: {str(e)}")
            self.test_results['performance_monitoring'] = {'passed': False, 'error': str(e)}

    async def test_ab_testing(self):
        """Test A/B testing functionality."""
        logger.info("\n🧪 Testing A/B Testing...")

        try:
            ml_config = get_ml_config()

            # Test enabling A/B test
            original_ab_config = ml_config.get_ab_test_config()

            ml_config.enable_ab_test("integration_test", duration_days=7)

            ab_config = ml_config.get_ab_test_config()
            assert ab_config is not None, "A/B test config not found after enabling"
            assert ab_config.enabled, "A/B test not enabled"
            assert ab_config.test_name == "integration_test", "A/B test name incorrect"

            logger.info(f"  ✅ A/B test enabled: {ab_config.test_name}")
            logger.info(f"  ✅ Variant A Weight: {ab_config.variant_a_weight}")
            logger.info(f"  ✅ Variant B Weight: {ab_config.variant_b_weight}")

            # Test disabling A/B test
            ml_config.disable_ab_test()

            ab_config_after = ml_config.get_ab_test_config()
            assert ab_config_after is None or not ab_config_after.enabled, "A/B test not properly disabled"

            logger.info(f"  ✅ A/B test disabled successfully")

            # Restore original state
            if original_ab_config and original_ab_config.enabled:
                ml_config.update_config({
                    'ab_test_config': original_ab_config.__dict__
                })

            self.test_results['ab_testing'] = {
                'passed': True,
                'test_enabled': True,
                'test_name': "integration_test",
                'variants_balanced': abs(ab_config.variant_a_weight + ab_config.variant_b_weight - 1.0) < 0.01
            }

        except Exception as e:
            logger.error(f"  ❌ A/B testing test failed: {str(e)}")
            self.test_results['ab_testing'] = {'passed': False, 'error': str(e)}

    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST REPORT SUMMARY")
        logger.info("=" * 80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('passed', False))
        execution_time = (datetime.now() - self.start_time).total_seconds()

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed Tests: {passed_tests}")
        logger.info(f"Failed Tests: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {passed_tests / total_tests * 100:.1f}%")
        logger.info(f"Execution Time: {execution_time:.2f} seconds")

        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result.get('passed', False) else "❌ FAILED"
            logger.info(f"  {test_name.replace('_', ' ').title()}: {status}")

            if not result.get('passed', False) and 'error' in result:
                logger.info(f"    Error: {result['error']}")

        # Overall result
        overall_passed = passed_tests == total_tests
        logger.info(f"\n{'✅ ALL TESTS PASSED' if overall_passed else '❌ SOME TESTS FAILED'}")

        # Save report to file
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'deployment_mode': self.deployment_mode.value,
            'execution_time_seconds': execution_time,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests / total_tests * 100,
            'overall_passed': overall_passed,
            'test_results': self.test_results
        }

        report_path = Path(f"test_report_ml_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        import json
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"📄 Detailed report saved to: {report_path}")


async def run_performance_benchmark():
    """Run performance benchmark tests."""
    logger.info("\n⚡ Running Performance Benchmark...")

    try:
        ml_engine = get_ml_decision_engine()
        market_data = generate_test_market_data(100)
        order_blocks = generate_test_order_blocks(market_data)

        # Benchmark inference time
        inference_times = []
        n_iterations = 10

        for i in range(n_iterations):
            start_time = time.time()
            decision = await ml_engine.make_decision(market_data, order_blocks)
            end_time = time.time()

            if decision:
                inference_times.append((end_time - start_time) * 1000)  # Convert to ms

        if inference_times:
            avg_time = np.mean(inference_times)
            p95_time = np.percentile(inference_times, 95)
            max_time = np.max(inference_times)

            logger.info(f"  ✅ Performance Benchmark Results:")
            logger.info(f"    * Average Inference Time: {avg_time:.2f}ms")
            logger.info(f"    * P95 Inference Time: {p95_time:.2f}ms")
            logger.info(f"    * Max Inference Time: {max_time:.2f}ms")
            logger.info(f"    * Successful Inferences: {len(inference_times)}/{n_iterations}")

            # Check against targets
            target_time = 50.0  # 50ms target
            if avg_time <= target_time:
                logger.info(f"    ✅ Meets target ({target_time}ms)")
            else:
                logger.warning(f"    ⚠️ Exceeds target ({target_time}ms)")

    except Exception as e:
        logger.error(f"  ❌ Performance benchmark failed: {str(e)}")


async def main():
    """Main test function."""
    args = parse_arguments()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Map deployment mode
    mode_mapping = {
        'shadow': DeploymentStage.SHADOW,
        'canary': DeploymentStage.CANARY,
        'full': DeploymentStage.FULL
    }
    deployment_mode = mode_mapping[args.mode]

    # Run integration tests
    tester = MLIntegrationTester(deployment_mode)
    success = await tester.run_all_tests(args.symbols, args.samples)

    # Run performance benchmark if requested
    if args.performance_test:
        await run_performance_benchmark()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)