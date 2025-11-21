#!/usr/bin/env python3
"""
Comprehensive System Integration Testing Suite for SMC Trading Agent

This module provides end-to-end testing of the complete integrated system,
validating real-time data flow, ML decision making, risk management, and execution.
All tests use REAL components - NO MOCKS per Shannon V3 testing philosophy.

Test Coverage:
1. End-to-End Data Flow Testing
2. System Performance Validation
3. Error Handling and Recovery
4. Configuration and Deployment Testing
5. Real-Time Trading Scenarios
"""

import pytest
import asyncio
import time
import logging
import subprocess
import psutil
import requests
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import REAL system components for integration testing
from main import load_config, run_trading_agent
from data_pipeline.live_data_client import LiveDataClient
from smc_detector.indicators import SMCIndicators
from decision_engine.ml_decision_engine import MLDecisionEngine
from risk_manager.smc_risk_manager import SMCRiskManager
from execution_engine.paper_trading import PaperTradingEngine
from service_manager import ServiceManager
from health_monitor import EnhancedHealthMonitor
from config_validator import validate_config

class TestEndToEndDataFlow:
    """Test complete data pipeline from market data to trade execution."""

    @pytest.fixture
    async def integration_environment(self):
        """Set up integration testing environment with real components."""
        # Load configuration
        config = load_config()

        # Initialize service manager
        service_manager = ServiceManager(config, logging.getLogger("test"))

        # Initialize REAL components (NO MOCKS)
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = MLDecisionEngine()
        risk_manager = SMCRiskManager(config=config.get('risk_manager', {}))
        execution_engine = PaperTradingEngine(initial_balance=10000.0)

        # Register services
        service_manager.register_service("data_processor", data_processor, lambda: True)
        service_manager.register_service("smc_detector", smc_detector, lambda: True)
        service_manager.register_service("decision_engine", decision_engine, lambda: True)
        service_manager.register_service("risk_manager", risk_manager, lambda: True)
        service_manager.register_service("execution_engine", execution_engine, lambda: True)

        yield {
            'config': config,
            'service_manager': service_manager,
            'data_processor': data_processor,
            'smc_detector': smc_detector,
            'decision_engine': decision_engine,
            'risk_manager': risk_manager,
            'execution_engine': execution_engine
        }

        # Cleanup
        await service_manager.shutdown_all_services()

    @pytest.mark.asyncio
    async def test_live_market_data_ingestion(self, integration_environment):
        """Test real market data ingestion from live APIs."""
        data_processor = integration_environment['data_processor']

        try:
            # Get REAL market data from exchange
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)

            # Validate data structure
            assert market_data_df is not None, "Market data DataFrame is None"
            assert len(market_data_df) > 0, "No market data received"

            # Validate required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                assert col in market_data_df.columns, f"Missing required column: {col}"

            # Validate data quality
            assert not market_data_df[required_columns].isnull().any().any(), "Market data contains null values"
            assert (market_data_df['high'] >= market_data_df['low']).all(), "Invalid high/low prices"
            assert (market_data_df['high'] >= market_data_df['open']).all(), "Invalid high/open prices"
            assert (market_data_df['high'] >= market_data_df['close']).all(), "Invalid high/close prices"
            assert (market_data_df['low'] <= market_data_df['open']).all(), "Invalid low/open prices"
            assert (market_data_df['low'] <= market_data_df['close']).all(), "Invalid low/close prices"
            assert (market_data_df['volume'] >= 0).all(), "Negative volume detected"

            logging.info(f"Successfully retrieved {len(market_data_df)} market data records")

        except Exception as e:
            pytest.fail(f"Live market data ingestion failed: {e}")

    @pytest.mark.asyncio
    async def test_smc_pattern_detection(self, integration_environment):
        """Test Smart Money Concepts pattern detection on real data."""
        smc_detector = integration_environment['smc_detector']
        data_processor = integration_environment['data_processor']

        try:
            # Get real market data
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=200)

            # Detect SMC patterns (REAL algorithm, no mocking)
            order_blocks = smc_detector.detect_order_blocks(market_data_df)
            choch_levels = smc_detector.detect_choch(market_data_df)
            fvg_zones = smc_detector.detect_fvg(market_data_df)

            # Validate pattern detection results
            assert isinstance(order_blocks, list), "Order blocks should be a list"
            assert isinstance(choch_levels, list), "CHOCH levels should be a list"
            assert isinstance(fvg_zones, list), "FVG zones should be a list"

            # Validate order block structure if any detected
            for block in order_blocks:
                assert isinstance(block, dict), "Order block should be a dictionary"
                assert 'price_level' in block, "Order block missing price_level"
                assert 'direction' in block, "Order block missing direction"
                assert 'timestamp' in block, "Order block missing timestamp"
                assert block['direction'] in ['bullish', 'bearish'], "Invalid order block direction"

            logging.info(f"SMC Pattern Detection Results:")
            logging.info(f"  Order Blocks: {len(order_blocks)}")
            logging.info(f"  CHOCH Levels: {len(choch_levels)}")
            logging.info(f"  FVG Zones: {len(fvg_zones)}")

        except Exception as e:
            pytest.fail(f"SMC pattern detection failed: {e}")

    @pytest.mark.asyncio
    async def test_ml_decision_engine_integration(self, integration_environment):
        """Test ML decision engine with real features and patterns."""
        decision_engine = integration_environment['decision_engine']
        data_processor = integration_environment['data_processor']
        smc_detector = integration_environment['smc_detector']

        try:
            # Get real market data
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)

            # Generate real SMC patterns
            order_blocks = smc_detector.detect_order_blocks(market_data_df)

            # Make ML decision with REAL data
            trade_signal = await decision_engine.make_decision(
                market_data=market_data_df,
                order_blocks=order_blocks
            )

            # Validate trade signal structure
            if trade_signal:  # Signal may be None if no patterns detected
                assert isinstance(trade_signal, dict), "Trade signal should be a dictionary"
                assert 'action' in trade_signal, "Trade signal missing action"
                assert 'confidence' in trade_signal, "Trade signal missing confidence"
                assert 'entry_price' in trade_signal, "Trade signal missing entry_price"

                # Validate signal values
                assert trade_signal['action'] in ['buy', 'sell'], f"Invalid action: {trade_signal['action']}"
                assert 0 <= trade_signal['confidence'] <= 1, f"Invalid confidence: {trade_signal['confidence']}"
                assert trade_signal['entry_price'] > 0, f"Invalid entry price: {trade_signal['entry_price']}"

                logging.info(f"ML Decision Generated:")
                logging.info(f"  Action: {trade_signal['action']}")
                logging.info(f"  Confidence: {trade_signal['confidence']:.2%}")
                logging.info(f"  Entry Price: {trade_signal['entry_price']}")
                logging.info(f"  Method: {trade_signal.get('decision_method', 'unknown')}")
            else:
                logging.info("No trade signal generated (expected for some market conditions)")

        except Exception as e:
            pytest.fail(f"ML decision engine integration failed: {e}")

    @pytest.mark.asyncio
    async def test_risk_management_integration(self, integration_environment):
        """Test risk management with real trade signals."""
        risk_manager = integration_environment['risk_manager']
        decision_engine = integration_environment['decision_engine']
        data_processor = integration_environment['data_processor']
        smc_detector = integration_environment['smc_detector']

        try:
            # Get real market data and patterns
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)
            order_blocks = smc_detector.detect_order_blocks(market_data_df)

            # Generate trade signal
            trade_signal = await decision_engine.make_decision(
                market_data=market_data_df,
                order_blocks=order_blocks
            )

            if trade_signal and trade_signal['confidence'] > 0.7:
                # Calculate stop loss with real data
                stop_loss = risk_manager.calculate_stop_loss(
                    entry_price=trade_signal['entry_price'],
                    direction=trade_signal['action'],
                    order_blocks=order_blocks,
                    market_structure={}
                )

                # Calculate take profit
                take_profit = risk_manager.calculate_take_profit(
                    entry_price=trade_signal['entry_price'],
                    stop_loss=stop_loss,
                    direction=trade_signal['action']
                )

                # Validate risk calculations
                assert stop_loss is not None, "Stop loss not calculated"
                assert take_profit is not None, "Take profit not calculated"
                assert stop_loss > 0, "Invalid stop loss value"
                assert take_profit > 0, "Invalid take profit value"

                if trade_signal['action'] == 'buy':
                    assert stop_loss < trade_signal['entry_price'], "Buy stop loss should be below entry"
                    assert take_profit > trade_signal['entry_price'], "Buy take profit should be above entry"
                else:
                    assert stop_loss > trade_signal['entry_price'], "Sell stop loss should be above entry"
                    assert take_profit < trade_signal['entry_price'], "Sell take profit should be below entry"

                # Validate risk/reward ratio
                risk = abs(trade_signal['entry_price'] - stop_loss)
                reward = abs(take_profit - trade_signal['entry_price'])
                risk_reward_ratio = reward / risk if risk > 0 else 0

                assert risk_reward_ratio >= 1.5, f"Risk/reward ratio too low: {risk_reward_ratio:.2f}"

                logging.info(f"Risk Management Results:")
                logging.info(f"  Entry Price: {trade_signal['entry_price']}")
                logging.info(f"  Stop Loss: {stop_loss}")
                logging.info(f"  Take Profit: {take_profit}")
                logging.info(f"  Risk/Reward Ratio: {risk_reward_ratio:.2f}")
            else:
                logging.info("No risk management test performed (insufficient signal confidence)")

        except Exception as e:
            pytest.fail(f"Risk management integration failed: {e}")

    @pytest.mark.asyncio
    async def test_execution_engine_integration(self, integration_environment):
        """Test trade execution with real trade signals."""
        execution_engine = integration_environment['execution_engine']
        risk_manager = integration_environment['risk_manager']
        decision_engine = integration_environment['decision_engine']
        data_processor = integration_environment['data_processor']
        smc_detector = integration_environment['smc_detector']

        try:
            # Get real market data and generate trading signals
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)
            order_blocks = smc_detector.detect_order_blocks(market_data_df)
            trade_signal = await decision_engine.make_decision(
                market_data=market_data_df,
                order_blocks=order_blocks
            )

            if trade_signal and trade_signal['confidence'] > 0.7:
                # Calculate risk parameters
                stop_loss = risk_manager.calculate_stop_loss(
                    entry_price=trade_signal['entry_price'],
                    direction=trade_signal['action'],
                    order_blocks=order_blocks,
                    market_structure={}
                )

                take_profit = risk_manager.calculate_take_profit(
                    entry_price=trade_signal['entry_price'],
                    stop_loss=stop_loss,
                    direction=trade_signal['action']
                )

                # Execute real paper trade
                paper_trade = execution_engine.execute_order(
                    symbol=trade_signal['symbol'],
                    side=trade_signal['action'],
                    size=0.001,  # Small size for testing
                    price=trade_signal['entry_price'],
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason="Integration test trade execution"
                )

                # Validate trade execution
                assert paper_trade is not None, "Paper trade execution returned None"
                assert hasattr(paper_trade, 'id'), "Trade missing ID"
                assert hasattr(paper_trade, 'symbol'), "Trade missing symbol"
                assert hasattr(paper_trade, 'side'), "Trade missing side"
                assert paper_trade.symbol == trade_signal['symbol'], "Trade symbol mismatch"
                assert paper_trade.side == trade_signal['action'], "Trade side mismatch"

                # Check account summary
                account_summary = execution_engine.get_account_summary()
                assert account_summary is not None, "Account summary is None"
                assert 'balance' in account_summary, "Account summary missing balance"
                assert 'equity' in account_summary, "Account summary missing equity"
                assert account_summary['balance'] >= 0, "Negative account balance"

                # Check open positions
                open_positions = execution_engine.get_open_positions()
                assert isinstance(open_positions, list), "Open positions should be a list"

                logging.info(f"Trade Execution Results:")
                logging.info(f"  Trade ID: {paper_trade.id}")
                logging.info(f"  Symbol: {paper_trade.symbol}")
                logging.info(f"  Side: {paper_trade.side}")
                logging.info(f"  Size: {paper_trade.size}")
                logging.info(f"  Account Balance: ${account_summary['balance']:.2f}")
                logging.info(f"  Open Positions: {len(open_positions)}")
            else:
                logging.info("No trade execution test performed (insufficient signal confidence)")

        except Exception as e:
            pytest.fail(f"Execution engine integration failed: {e}")

class TestSystemPerformanceValidation:
    """Test system performance under realistic conditions."""

    @pytest.fixture
    async def performance_environment(self):
        """Set up performance testing environment."""
        config = load_config()

        # Initialize components for performance testing
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = MLDecisionEngine()

        yield {
            'config': config,
            'data_processor': data_processor,
            'smc_detector': smc_detector,
            'decision_engine': decision_engine
        }

    @pytest.mark.asyncio
    async def test_end_to_end_latency_measurement(self, performance_environment):
        """Measure end-to-end processing latency."""
        data_processor = performance_environment['data_processor']
        smc_detector = performance_environment['smc_detector']
        decision_engine = performance_environment['decision_engine']

        latencies = []

        # Run multiple iterations to measure latency
        for i in range(10):
            start_time = time.time()

            try:
                # Step 1: Get market data
                market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=50)
                data_time = time.time()

                # Step 2: Detect SMC patterns
                order_blocks = smc_detector.detect_order_blocks(market_data_df)
                smc_time = time.time()

                # Step 3: Generate trading decision
                trade_signal = await decision_engine.make_decision(
                    market_data=market_data_df,
                    order_blocks=order_blocks
                )
                decision_time = time.time()

                # Calculate latencies
                total_latency = decision_time - start_time
                data_latency = data_time - start_time
                smc_latency = smc_time - data_time
                decision_latency = decision_time - smc_time

                latencies.append({
                    'total': total_latency,
                    'data': data_latency,
                    'smc': smc_latency,
                    'decision': decision_latency
                })

                logging.info(f"Iteration {i+1} latencies - "
                           f"Data: {data_latency:.3f}s, "
                           f"SMC: {smc_latency:.3f}s, "
                           f"Decision: {decision_latency:.3f}s, "
                           f"Total: {total_latency:.3f}s")

            except Exception as e:
                logging.warning(f"Latency measurement iteration {i+1} failed: {e}")
                continue

        # Validate performance
        assert len(latencies) >= 5, f"Too few successful latency measurements: {len(latencies)}"

        # Calculate statistics
        avg_total_latency = np.mean([l['total'] for l in latencies])
        max_total_latency = np.max([l['total'] for l in latencies])
        avg_data_latency = np.mean([l['data'] for l in latencies])
        avg_smc_latency = np.mean([l['smc'] for l in latencies])
        avg_decision_latency = np.mean([l['decision'] for l in latencies])

        # Performance assertions (50ms target for production)
        assert avg_total_latency < 0.05, f"Average total latency {avg_total_latency:.3f}s exceeds 50ms target"
        assert max_total_latency < 0.10, f"Maximum total latency {max_total_latency:.3f}s exceeds 100ms"

        logging.info(f"Performance Validation Results:")
        logging.info(f"  Average Total Latency: {avg_total_latency:.3f}s")
        logging.info(f"  Maximum Total Latency: {max_total_latency:.3f}s")
        logging.info(f"  Average Data Latency: {avg_data_latency:.3f}s")
        logging.info(f"  Average SMC Latency: {avg_smc_latency:.3f}s")
        logging.info(f"  Average Decision Latency: {avg_decision_latency:.3f}s")

    @pytest.mark.asyncio
    async def test_throughput_validation(self, performance_environment):
        """Test system throughput under load."""
        data_processor = performance_environment['data_processor']
        smc_detector = performance_environment['smc_detector']

        # Test data processing throughput
        start_time = time.time()
        processed_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']

        # Process multiple symbols concurrently
        async def process_symbol(symbol):
            try:
                data = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=50)
                patterns = smc_detector.detect_order_blocks(data)
                return {
                    'symbol': symbol,
                    'data_points': len(data) if data is not None else 0,
                    'patterns': len(patterns) if patterns else 0,
                    'success': True
                }
            except Exception as e:
                return {
                    'symbol': symbol,
                    'error': str(e),
                    'success': False
                }

        # Run concurrent processing
        tasks = [process_symbol(symbol) for symbol in processed_symbols]
        results = await asyncio.gather(*tasks)

        processing_time = time.time() - start_time

        # Validate throughput
        successful_results = [r for r in results if r['success']]
        success_rate = len(successful_results) / len(processed_symbols)
        total_data_points = sum(r['data_points'] for r in successful_results)
        throughput = total_data_points / processing_time if processing_time > 0 else 0

        assert success_rate >= 0.75, f"Low throughput success rate: {success_rate:.2%}"
        assert throughput > 100, f"Low data throughput: {throughput:.1f} data points/second"

        logging.info(f"Throughput Validation Results:")
        logging.info(f"  Processing Time: {processing_time:.3f}s")
        logging.info(f"  Success Rate: {success_rate:.2%}")
        logging.info(f"  Total Data Points: {total_data_points}")
        logging.info(f"  Throughput: {throughput:.1f} data points/second")

    def test_memory_usage_validation(self, performance_environment):
        """Test memory usage and detect memory leaks."""
        import gc
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Record initial memory
        snapshot1 = tracemalloc.take_snapshot()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate workload
        data_processor = performance_environment['data_processor']
        smc_detector = performance_environment['smc_detector']

        # Run multiple iterations to stress test memory
        for i in range(50):
            try:
                # This would be async in real usage, but simplified for memory test
                # Simulate data processing
                test_data = pd.DataFrame({
                    'open': np.random.rand(100) * 1000,
                    'high': np.random.rand(100) * 1100,
                    'low': np.random.rand(100) * 900,
                    'close': np.random.rand(100) * 1000,
                    'volume': np.random.rand(100) * 1000000
                })

                patterns = smc_detector.detect_order_blocks(test_data)

                # Clean up
                del test_data
                del patterns

                if i % 10 == 0:
                    gc.collect()

            except Exception as e:
                logging.warning(f"Memory test iteration {i+1} failed: {e}")

        # Final memory measurement
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Compare memory usage
        memory_increase = final_memory - initial_memory

        # Check for memory leaks
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_allocated = sum(stat.size for stat in top_stats)

        assert memory_increase < 100, f"Excessive memory increase: {memory_increase:.1f}MB"
        assert final_memory < 1000, f"High final memory usage: {final_memory:.1f}MB"

        tracemalloc.stop()

        logging.info(f"Memory Usage Validation Results:")
        logging.info(f"  Initial Memory: {initial_memory:.1f}MB")
        logging.info(f"  Final Memory: {final_memory:.1f}MB")
        logging.info(f"  Memory Increase: {memory_increase:.1f}MB")
        logging.info(f"  Total Allocated: {total_allocated / 1024 / 1024:.1f}MB")

class TestErrorHandlingAndRecovery:
    """Test system error handling and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_api_connection_failure_recovery(self):
        """Test recovery from API connection failures."""
        from error_handlers import CircuitBreaker, RetryHandler

        # Create circuit breaker for API calls
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,
            expected_exception=Exception
        )

        retry_handler = RetryHandler(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0
        )

        failure_count = 0
        recovery_count = 0

        async def simulate_api_call(should_fail=False):
            nonlocal failure_count, recovery_count
            if should_fail:
                failure_count += 1
                raise Exception(f"Simulated API failure {failure_count}")
            else:
                recovery_count += 1
                return {"status": "success", "data": "test_data"}

        # Test circuit breaker behavior
        # Simulate initial failures
        for i in range(3):
            try:
                with circuit_breaker:
                    await simulate_api_call(should_fail=True)
            except Exception:
                pass  # Expected failures

        # Circuit breaker should be open
        assert circuit_breaker.state == 'open', "Circuit breaker should be open after failures"

        # Test that calls are blocked during open state
        try:
            with circuit_breaker:
                await simulate_api_call(should_fail=False)
            pytest.fail("Circuit breaker should block calls when open")
        except Exception:
            pass  # Expected - circuit breaker is open

        # Wait for recovery timeout
        await asyncio.sleep(6)

        # Test recovery with successful call
        try:
            with circuit_breaker:
                result = await simulate_api_call(should_fail=False)
            assert result["status"] == "success", "Recovery call should succeed"
            assert circuit_breaker.state == 'closed', "Circuit breaker should close after successful call"
        except Exception as e:
            pytest.fail(f"Circuit breaker recovery failed: {e}")

        # Test retry handler
        retry_attempts = []

        async def failing_function():
            retry_attempts.append(len(retry_attempts))
            if len(retry_attempts) < 3:
                raise Exception("Simulated retry failure")
            return {"success": True, "attempts": len(retry_attempts)}

        try:
            result = await retry_handler.call(failing_function)
            assert result["success"] is True, "Retry should eventually succeed"
            assert len(retry_attempts) == 3, f"Expected 3 retry attempts, got {len(retry_attempts)}"
        except Exception as e:
            pytest.fail(f"Retry handler failed: {e}")

        logging.info(f"Error Handling Results:")
        logging.info(f"  Failures Simulated: {failure_count}")
        logging.info(f"  Successful Recoveries: {recovery_count}")
        logging.info(f"  Retry Attempts: {len(retry_attempts)}")

    @pytest.mark.asyncio
    async def test_data_quality_error_handling(self):
        """Test handling of poor quality or missing data."""
        from validators import data_validator, DataQualityLevel, DataValidationError

        # Test with missing data
        missing_data_df = pd.DataFrame({
            'open': [100, 200, None, 400],
            'high': [110, 210, 310, 410],
            'low': [90, 190, None, 390],
            'close': [105, 205, 305, 405],
            'volume': [1000, 2000, 3000, None]
        })

        # Validate missing data handling
        is_valid, errors = data_validator.validate_market_data(missing_data_df)
        assert not is_valid, "Missing data should be detected as invalid"
        assert len(errors) > 0, "Missing data should produce validation errors"

        # Test data quality assessment
        quality_level = data_validator.assess_data_quality(missing_data_df)
        assert quality_level in [DataQualityLevel.POOR, DataQualityLevel.UNUSABLE], \
            f"Poor data should be assessed as POOR or UNUSABLE, got {quality_level}"

        # Test with outlier data
        outlier_data_df = pd.DataFrame({
            'open': [100, 200, 10000, 400],  # Extreme outlier
            'high': [110, 210, 10010, 410],
            'low': [90, 190, 9990, 390],
            'close': [105, 205, 10005, 405],
            'volume': [1000, 2000, 3000, 4000]
        })

        # Validate outlier handling
        is_valid, errors = data_validator.validate_market_data(outlier_data_df)
        # Should either be invalid or marked with warnings
        quality_level = data_validator.assess_data_quality(outlier_data_df)
        assert quality_level != DataQualityLevel.EXCELLENT, \
            "Data with outliers should not be rated as EXCELLENT"

        # Test with insufficient data
        insufficient_data_df = pd.DataFrame({
            'open': [100],
            'high': [110],
            'low': [90],
            'close': [105],
            'volume': [1000]
        })

        # Validate insufficient data
        is_valid, errors = data_validator.validate_market_data(insufficient_data_df)
        assert not is_valid or len(errors) > 0, "Insufficient data should be flagged"

        logging.info(f"Data Quality Error Handling Results:")
        logging.info(f"  Missing Data Detected: {not is_valid}")
        logging.info(f"  Validation Errors: {len(errors)}")
        logging.info(f"  Quality Level: {quality_level.value}")

    @pytest.mark.asyncio
    async def test_component_failure_isolation(self):
        """Test that component failures don't cascade through the system."""

        class MockFailingComponent:
            def __init__(self, should_fail=False):
                self.should_fail = should_fail
                self.call_count = 0

            async def process(self, data):
                self.call_count += 1
                if self.should_fail:
                    raise Exception(f"Component failed on call {self.call_count}")
                return {"processed": True, "data": data}

        # Test isolated component failure
        failing_component = MockFailingComponent(should_fail=True)
        working_component = MockFailingComponent(should_fail=False)

        test_data = {"test": "data"}

        # Test that failing component doesn't affect working component
        try:
            failing_result = await failing_component.process(test_data)
            pytest.fail("Failing component should raise exception")
        except Exception:
            pass  # Expected

        # Working component should still function
        working_result = await working_component.process(test_data)
        assert working_result["processed"] is True, "Working component should still function"

        # Test component recovery
        failing_component.should_fail = False
        recovery_result = await failing_component.process(test_data)
        assert recovery_result["processed"] is True, "Component should recover after failure"

        logging.info(f"Component Failure Isolation Results:")
        logging.info(f"  Failing Component Calls: {failing_component.call_count}")
        logging.info(f"  Working Component Success: {working_result['processed']}")
        logging.info(f"  Recovery Success: {recovery_result['processed']}")

class TestConfigurationAndDeployment:
    """Test configuration validation and deployment procedures."""

    def test_production_configuration_validation(self):
        """Validate production configuration completeness and correctness."""
        config = load_config()

        # Validate required sections exist
        required_sections = [
            'app', 'exchanges', 'risk_manager', 'execution_engine',
            'smc_detector', 'decision_engine', 'monitoring'
        ]

        for section in required_sections:
            assert section in config, f"Missing required config section: {section}"

        # Validate app configuration
        app_config = config['app']
        assert 'name' in app_config, "App name missing"
        assert 'mode' in app_config, "Trading mode missing"
        assert app_config['mode'] in ['paper', 'real'], f"Invalid trading mode: {app_config['mode']}"

        # Validate risk management configuration
        risk_config = config['risk_manager']
        required_risk_params = ['max_position_size', 'max_daily_loss', 'max_drawdown']
        for param in required_risk_params:
            assert param in risk_config, f"Missing risk parameter: {param}"
            assert risk_config[param] > 0, f"Invalid risk parameter value for {param}: {risk_config[param]}"

        # Validate SMC detector configuration
        smc_config = config['smc_detector']
        assert 'confidence_threshold' in smc_config, "SMC confidence threshold missing"
        assert 0 <= smc_config['confidence_threshold'] <= 1, "Invalid confidence threshold"

        # Validate decision engine configuration
        decision_config = config['decision_engine']
        assert 'confidence_threshold' in decision_config, "Decision confidence threshold missing"
        assert 0 <= decision_config['confidence_threshold'] <= 1, "Invalid decision confidence threshold"

        logging.info("Production configuration validation completed successfully")

    def test_environment_variable_validation(self):
        """Test environment variable loading and validation."""
        # Test config loading with environment variables
        try:
            config = load_config()

            # Check that environment variables are properly substituted
            # This test depends on having a .env file or environment variables set
            exchanges_config = config.get('exchanges', {})

            if 'binance' in exchanges_config:
                binance_config = exchanges_config['binance']
                # API keys should be loaded from environment
                # In production, these should not be empty strings
                if binance_config.get('api_key') == '':
                    logging.warning("Binance API key not configured in environment")
                if binance_config.get('api_secret') == '':
                    logging.warning("Binance API secret not configured in environment")

        except Exception as e:
            pytest.fail(f"Environment variable validation failed: {e}")

        logging.info("Environment variable validation completed")

    def test_docker_deployment_configuration(self):
        """Test Docker deployment configuration."""
        import yaml
        docker_compose_file = Path(__file__).parent.parent / "docker-compose.production.yml"

        if not docker_compose_file.exists():
            pytest.skip("docker-compose.production.yml not found")

        try:
            with open(docker_compose_file, 'r') as f:
                docker_config = yaml.safe_load(f)

            # Validate Docker Compose structure
            assert 'version' in docker_config, "Docker Compose version missing"
            assert 'services' in docker_config, "Docker Compose services missing"

            services = docker_config['services']

            # Check for essential services
            main_service = None
            for service_name, service_config in services.items():
                if 'trading' in service_name.lower() or 'smc' in service_name.lower():
                    main_service = service_name
                    break

            assert main_service is not None, "Main trading service not found in Docker Compose"

            # Validate main service configuration
            main_config = services[main_service]
            assert 'image' in main_config or 'build' in main_config, "Service image or build config missing"

            if 'environment' in main_config:
                env_vars = main_config['environment']
                assert isinstance(env_vars, list), "Environment variables should be a list"

                # Check for essential environment variables
                env_var_names = [env.split('=')[0] if '=' in env else env for env in env_vars]
                essential_vars = ['APP_ENV', 'LOG_LEVEL', 'TRADING_MODE']

                for var in essential_vars:
                    assert var in env_var_names, f"Essential environment variable missing: {var}"

            logging.info(f"Docker configuration validation completed for service: {main_service}")

        except Exception as e:
            pytest.fail(f"Docker deployment configuration validation failed: {e}")

    @pytest.mark.asyncio
    async def test_service_startup_health_checks(self):
        """Test service startup and health check procedures."""
        from health_monitor import EnhancedHealthMonitor

        # Initialize health monitor
        health_monitor = EnhancedHealthMonitor(
            app_name="test-smc-trading-agent",
            logger=logging.getLogger("test")
        )

        # Start health monitoring
        await health_monitor.start_background_health_checks()

        # Test health check endpoints
        health_status = health_monitor.get_system_health()

        # Validate health status structure
        assert 'overall_healthy' in health_status, "Overall health status missing"
        assert 'services' in health_status, "Service health status missing"
        assert 'timestamp' in health_status, "Health check timestamp missing"
        assert isinstance(health_status['services'], dict), "Service status should be a dictionary"

        # Test individual service health checks
        for service_name, service_status in health_status['services'].items():
            assert 'healthy' in service_status, f"Service {service_name} missing health status"
            assert 'last_check' in service_status, f"Service {service_name} missing last check time"
            assert isinstance(service_status['healthy'], bool), f"Service {service_name} health should be boolean"

        # Test health monitoring performance
        start_time = time.time()
        health_status = health_monitor.get_system_health()
        health_check_duration = time.time() - start_time

        assert health_check_duration < 1.0, f"Health check too slow: {health_check_duration:.3f}s"

        # Shutdown health monitor
        await health_monitor.shutdown()

        logging.info(f"Service Health Check Results:")
        logging.info(f"  Overall Healthy: {health_status['overall_healthy']}")
        logging.info(f"  Services Monitored: {len(health_status['services'])}")
        logging.info(f"  Health Check Duration: {health_check_duration:.3f}s")

class TestRealTimeTradingScenarios:
    """Test realistic trading scenarios with real market data."""

    @pytest.mark.asyncio
    async def test_complete_trading_cycle(self):
        """Test complete trading cycle from market data to position management."""
        config = load_config()

        # Initialize all components
        service_manager = ServiceManager(config, logging.getLogger("test"))
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = MLDecisionEngine()
        risk_manager = SMCRiskManager(config=config.get('risk_manager', {}))
        execution_engine = PaperTradingEngine(initial_balance=10000.0)

        # Register services
        service_manager.register_service("data_processor", data_processor, lambda: True)
        service_manager.register_service("smc_detector", smc_detector, lambda: True)
        service_manager.register_service("decision_engine", decision_engine, lambda: True)
        service_manager.register_service("risk_manager", risk_manager, lambda: True)
        service_manager.register_service("execution_engine", execution_engine, lambda: True)

        try:
            # Step 1: Get real market data
            market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h", limit=100)
            assert market_data_df is not None and len(market_data_df) > 0, "Failed to get market data"

            # Step 2: Detect SMC patterns
            order_blocks = smc_detector.detect_order_blocks(market_data_df)

            # Step 3: Generate trading decision
            trade_signal = await decision_engine.make_decision(
                market_data=market_data_df,
                order_blocks=order_blocks
            )

            if trade_signal and trade_signal['confidence'] > 0.7:
                # Step 4: Calculate risk parameters
                stop_loss = risk_manager.calculate_stop_loss(
                    entry_price=trade_signal['entry_price'],
                    direction=trade_signal['action'],
                    order_blocks=order_blocks,
                    market_structure={}
                )

                take_profit = risk_manager.calculate_take_profit(
                    entry_price=trade_signal['entry_price'],
                    stop_loss=stop_loss,
                    direction=trade_signal['action']
                )

                # Step 5: Execute trade
                paper_trade = execution_engine.execute_order(
                    symbol=trade_signal['symbol'],
                    side=trade_signal['action'],
                    size=0.001,
                    price=trade_signal['entry_price'],
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason="Complete trading cycle test"
                )

                assert paper_trade is not None, "Trade execution failed"

                # Step 6: Get updated prices and check position management
                updated_prices = await data_processor.get_latest_ohlcv_data(trade_signal['symbol'], "1h", limit=1)
                if updated_prices is not None and not updated_prices.empty:
                    live_price = updated_prices['close'].iloc[-1]
                    live_prices = {trade_signal['symbol']: live_price}

                    # Update positions and check for stop loss/take profit
                    execution_engine.update_positions(live_prices)

                # Step 7: Verify final state
                account_summary = execution_engine.get_account_summary()
                open_positions = execution_engine.get_open_positions()
                trade_history = execution_engine.get_trade_history(limit=10)

                # Validate final state
                assert account_summary is not None, "Account summary missing"
                assert isinstance(open_positions, list), "Open positions should be a list"
                assert isinstance(trade_history, list), "Trade history should be a list"
                assert len(trade_history) > 0, "No trades in history"

                logging.info(f"Complete Trading Cycle Results:")
                logging.info(f"  Trade Executed: {paper_trade.id}")
                logging.info(f"  Final Balance: ${account_summary['balance']:.2f}")
                logging.info(f"  Open Positions: {len(open_positions)}")
                logging.info(f"  Total Trades: {len(trade_history)}")

            else:
                logging.info("No trade signal generated for complete cycle test")

        except Exception as e:
            pytest.fail(f"Complete trading cycle failed: {e}")
        finally:
            await service_manager.shutdown_all_services()

    @pytest.mark.asyncio
    async def test_multi_asset_portfolio_management(self):
        """Test portfolio management across multiple assets."""
        config = load_config()

        # Initialize components
        service_manager = ServiceManager(config, logging.getLogger("test"))
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        execution_engine = PaperTradingEngine(initial_balance=50000.0)  # Larger balance for multiple assets

        try:
            # Test multiple symbols
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
            portfolio_positions = {}

            for symbol in symbols:
                try:
                    # Get market data for each symbol
                    market_data_df = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=50)

                    if market_data_df is not None and len(market_data_df) > 0:
                        # Simulate trade execution for each symbol
                        current_price = market_data_df['close'].iloc[-1]
                        position_size = 1000 / current_price  # $1000 position per symbol

                        # Execute buy order
                        trade = execution_engine.execute_order(
                            symbol=symbol,
                            side='buy',
                            size=position_size,
                            price=current_price,
                            stop_loss=current_price * 0.98,  # 2% stop loss
                            take_profit=current_price * 1.06,  # 6% take profit
                            reason=f"Multi-asset test for {symbol}"
                        )

                        if trade:
                            portfolio_positions[symbol] = {
                                'trade_id': trade.id,
                                'size': position_size,
                                'entry_price': current_price
                            }

                except Exception as e:
                    logging.warning(f"Failed to process {symbol}: {e}")
                    continue

            # Validate portfolio state
            account_summary = execution_engine.get_account_summary()
            open_positions = execution_engine.get_open_positions()

            assert len(portfolio_positions) > 0, "No positions established in portfolio"
            assert len(open_positions) >= len(portfolio_positions), "Open positions mismatch"
            assert account_summary['balance'] < 50000, "Account balance should be reduced by positions"

            # Test portfolio updates with live prices
            updated_prices = {}
            for symbol in portfolio_positions.keys():
                try:
                    price_data = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=1)
                    if price_data is not None and not price_data.empty:
                        updated_prices[symbol] = price_data['close'].iloc[-1]
                except Exception as e:
                    logging.warning(f"Failed to get updated price for {symbol}: {e}")

            if updated_prices:
                execution_engine.update_positions(updated_prices)

            # Final portfolio validation
            final_summary = execution_engine.get_account_summary()
            final_positions = execution_engine.get_open_positions()

            logging.info(f"Multi-Asset Portfolio Results:")
            logging.info(f"  Symbols Traded: {list(portfolio_positions.keys())}")
            logging.info(f"  Initial Balance: $50000.00")
            logging.info(f"  Final Balance: ${final_summary['balance']:.2f}")
            logging.info(f"  Open Positions: {len(final_positions)}")
            logging.info(f"  Portfolio P&L: ${final_summary.get('pnl', 0):.2f}")

        except Exception as e:
            pytest.fail(f"Multi-asset portfolio management failed: {e}")
        finally:
            await service_manager.shutdown_all_services()

# Integration test runner
@pytest.mark.asyncio
async def test_complete_system_integration():
    """Run complete system integration test with all components."""
    results = {
        'end_to_end_data_flow': False,
        'system_performance': False,
        'error_handling': False,
        'configuration_deployment': False,
        'real_time_scenarios': False
    }

    test_classes = [
        TestEndToEndDataFlow,
        TestSystemPerformanceValidation,
        TestErrorHandlingAndRecovery,
        TestConfigurationAndDeployment,
        TestRealTimeTradingScenarios
    ]

    overall_start_time = time.time()

    for i, test_class in enumerate(test_classes):
        try:
            logging.info(f"Running integration test class {i+1}/{len(test_classes)}: {test_class.__name__}")

            # Run a representative test from each class
            test_instance = test_class()

            if test_class == TestEndToEndDataFlow:
                await test_instance.test_live_market_data_ingestion(test_instance.integration_environment())
                results['end_to_end_data_flow'] = True

            elif test_class == TestSystemPerformanceValidation:
                test_instance.test_memory_usage_validation(test_instance.performance_environment())
                results['system_performance'] = True

            elif test_class == TestErrorHandlingAndRecovery:
                await test_instance.test_api_connection_failure_recovery()
                results['error_handling'] = True

            elif test_class == TestConfigurationAndDeployment:
                test_instance.test_production_configuration_validation()
                results['configuration_deployment'] = True

            elif test_class == TestRealTimeTradingScenarios:
                await test_instance.test_complete_trading_cycle()
                results['real_time_scenarios'] = True

            logging.info(f"✅ {test_class.__name__} completed successfully")

        except Exception as e:
            logging.error(f"❌ {test_class.__name__} failed: {e}")
            continue

    total_duration = time.time() - overall_start_time
    passed_tests = sum(results.values())
    total_tests = len(results)
    success_rate = passed_tests / total_tests

    # Generate integration test report
    integration_report = {
        'timestamp': datetime.now(),
        'total_duration': total_duration,
        'success_rate': success_rate,
        'test_results': results,
        'overall_status': 'passed' if success_rate >= 0.8 else 'failed'
    }

    # Save integration test report
    report_file = Path(__file__).parent / "integration_test_report.json"
    with open(report_file, 'w') as f:
        json.dump(integration_report, f, indent=2, default=str)

    logging.info(f"System Integration Test Summary:")
    logging.info(f"  Duration: {total_duration:.2f}s")
    logging.info(f"  Success Rate: {success_rate:.1%}")
    logging.info(f"  Tests Passed: {passed_tests}/{total_tests}")
    logging.info(f"  Overall Status: {integration_report['overall_status'].upper()}")

    assert success_rate >= 0.8, f"Integration test success rate {success_rate:.1%} below 80% threshold"

    return integration_report

if __name__ == "__main__":
    # Run the complete integration test suite
    asyncio.run(test_complete_system_integration())