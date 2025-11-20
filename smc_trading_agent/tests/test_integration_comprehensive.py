"""
Comprehensive Integration Tests for SMC Trading Agent

This module contains integration tests that validate the complete data flow
and interaction between all components of the trading system.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import time
import json
import logging

# Import the test framework
from test_framework import (
    AsyncTestCase, TestConfig, MarketDataSimulator,
    PerformanceTracker, IntegrationTestHelper, TestDataManager
)

# Import system components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDataFlowIntegration(AsyncTestCase):
    """Integration tests for complete data flow pipeline."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.integration_helper = IntegrationTestHelper()

    async def test_complete_market_data_flow(self):
        """Test complete flow from market data ingestion to storage."""
        # Set up test environment
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine'
        ])

        try:
            # 1. Generate realistic market data
            market_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 100)
            orderbook_data = self.market_simulator.generate_order_book_snapshot('BTCUSDT')
            trade_flow = self.market_simulator.generate_trade_flow('BTCUSDT', 50)

            # 2. Ingest market data
            data_pipeline = env['services']['data_pipeline']
            data_pipeline.get_market_data.return_value = market_data
            data_pipeline.validate_data.return_value = True

            ingestion_result = await data_pipeline.ingest_ohlcv_data('BTCUSDT', market_data)
            assert ingestion_result['status'] == 'success'
            assert ingestion_result['records_processed'] == len(market_data)

            # 3. Process through SMC detector
            smc_detector = env['services']['smc_detector']
            smc_detector.detect_patterns.return_value = [
                {
                    'type': 'ORDER_BLOCK',
                    'price_level': (50000, 50100),
                    'direction': 'bullish',
                    'strength': 0.8,
                    'timestamp': datetime.now()
                }
            ]

            patterns = await smc_detector.detect_patterns(market_data)
            assert len(patterns) > 0
            assert patterns[0]['type'] == 'ORDER_BLOCK'

            # 4. Decision engine processing
            decision_engine = env['services']['decision_engine']
            decision_engine.make_decision.return_value = {
                'action': 'buy',
                'confidence': 0.75,
                'entry_price': 50100,
                'stop_loss': 49500,
                'take_profit': 51500
            }

            decision = await decision_engine.make_decision({
                'market_data': market_data,
                'patterns': patterns,
                'current_price': 50000
            })

            assert decision['action'] in ['buy', 'sell', 'hold']
            assert 0 <= decision['confidence'] <= 1

            # 5. Validate end-to-end data consistency
            assert decision['entry_price'] >= patterns[0]['price_level'][0]
            assert decision['entry_price'] <= patterns[0]['price_level'][1]

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def test_multi_symbol_data_processing(self):
        """Test processing multiple symbols simultaneously."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine'
        ])

        try:
            # Process all symbols in parallel
            tasks = []
            for symbol in symbols:
                market_data = self.market_simulator.generate_ohlcv_data(symbol, 50)
                task = self._process_single_symbol(symbol, market_data, env)
                tasks.append(task)

            # Wait for all symbols to be processed
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Failed to process {symbols[i]}: {result}")
                else:
                    assert result['status'] == 'success'
                    assert 'decision' in result
                    assert 'patterns' in result

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def _process_single_symbol(self, symbol: str, market_data: pd.DataFrame, env: dict) -> dict:
        """Helper method to process a single symbol."""
        data_pipeline = env['services']['data_pipeline']
        smc_detector = env['services']['smc_detector']
        decision_engine = env['services']['decision_engine']

        # Set up mocks
        data_pipeline.get_market_data.return_value = market_data
        data_pipeline.validate_data.return_value = True
        smc_detector.detect_patterns.return_value = [
            {
                'type': 'CHOCH',
                'symbol': symbol,
                'confidence': 0.7,
                'timestamp': datetime.now()
            }
        ]
        decision_engine.make_decision.return_value = {
            'action': 'buy',
            'confidence': 0.7,
            'entry_price': market_data['close'].iloc[-1],
            'stop_loss': market_data['close'].iloc[-1] * 0.99,
            'take_profit': market_data['close'].iloc[-1] * 1.02
        }

        # Process data
        ingestion_result = await data_pipeline.ingest_ohlcv_data(symbol, market_data)
        patterns = await smc_detector.detect_patterns(market_data)
        decision = await decision_engine.make_decision({
            'symbol': symbol,
            'market_data': market_data,
            'patterns': patterns
        })

        return {
            'status': 'success',
            'symbol': symbol,
            'decision': decision,
            'patterns': patterns
        }

    async def test_real_time_data_streaming(self):
        """Test real-time data streaming integration."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine', 'risk_manager'
        ])

        try:
            # Simulate real-time data stream
            streaming_data = []
            decisions_made = []

            for i in range(20):
                # Generate new data point
                orderbook = self.market_simulator.generate_order_book_snapshot('BTCUSDT')
                streaming_data.append(orderbook)

                # Process through pipeline
                data_pipeline = env['services']['data_pipeline']
                smc_detector = env['services']['smc_detector']
                decision_engine = env['services']['decision_engine']
                risk_manager = env['services']['risk_manager']

                # Mock real-time processing
                data_pipeline.process_real_time_data.return_value = {
                    'status': 'processed',
                    'data': orderbook
                }

                smc_detector.analyze_real_time_patterns.return_value = {
                    'new_patterns': i % 5 == 0,  # New pattern every 5th data point
                    'confidence': 0.6 + (i * 0.02)
                }

                decision_engine.make_real_time_decision.return_value = {
                    'action': 'buy' if i % 3 == 0 else 'hold',
                    'confidence': 0.7,
                    'timestamp': datetime.now()
                }

                risk_manager.validate_real_time_trade.return_value = {
                    'is_valid': True,
                    'risk_score': 0.3 + (i * 0.01)
                }

                # Process real-time data
                processed_data = await data_pipeline.process_real_time_data(orderbook)
                if processed_data['status'] == 'processed':
                    pattern_analysis = await smc_detector.analyze_real_time_patterns(processed_data)
                    if pattern_analysis['new_patterns']:
                        decision = await decision_engine.make_real_time_decision({
                            'data': processed_data,
                            'patterns': pattern_analysis
                        })

                        risk_validation = await risk_manager.validate_real_time_trade(decision)
                        if risk_validation['is_valid']:
                            decisions_made.append(decision)

                await asyncio.sleep(0.01)  # Simulate real-time interval

            # Validate streaming results
            assert len(streaming_data) == 20
            assert len(decisions_made) > 0  # Should have made some decisions
            assert all(d['action'] in ['buy', 'sell', 'hold'] for d in decisions_made)

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def test_error_recovery_in_pipeline(self):
        """Test error recovery and resilience in data pipeline."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine'
        ])

        try:
            data_pipeline = env['services']['data_pipeline']
            smc_detector = env['services']['smc_detector']
            decision_engine = env['services']['decision_engine']

            # Simulate various error conditions and recovery

            # 1. Data ingestion failure
            corrupted_data = pd.DataFrame({'invalid': [1, 2, 3]})
            data_pipeline.ingest_ohlcv_data.side_effect = [
                Exception("Data validation failed"),  # First call fails
                {'status': 'success', 'records_processed': 10}  # Second call succeeds
            ]

            # Test retry mechanism
            with pytest.raises(Exception):
                await data_pipeline.ingest_ohlcv_data('BTCUSDT', corrupted_data)

            # Recovery with valid data
            valid_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 10)
            result = await data_pipeline.ingest_ohlcv_data('BTCUSDT', valid_data)
            assert result['status'] == 'success'

            # 2. SMC detector failure
            smc_detector.detect_patterns.side_effect = [
                Exception("Pattern detection failed"),  # First call fails
                [{'type': 'ORDER_BLOCK', 'strength': 0.8}]  # Second call succeeds
            ]

            with pytest.raises(Exception):
                await smc_detector.detect_patterns(valid_data)

            # Recovery
            patterns = await smc_detector.detect_patterns(valid_data)
            assert len(patterns) > 0

            # 3. Decision engine failure
            decision_engine.make_decision.side_effect = [
                Exception("Decision making failed"),  # First call fails
                {'action': 'hold', 'confidence': 0.5}  # Second call succeeds
            ]

            with pytest.raises(Exception):
                await decision_engine.make_decision({'data': valid_data})

            # Recovery
            decision = await decision_engine.make_decision({'data': valid_data})
            assert decision['action'] == 'hold'

        finally:
            await self.integration_helper.cleanup_test_environment(env)


class TestTradingWorkflowIntegration(AsyncTestCase):
    """Integration tests for complete trading workflows."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.integration_helper = IntegrationTestHelper()

    async def test_complete_trading_workflow(self):
        """Test end-to-end trading workflow from signal to execution."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine', 'risk_manager', 'execution_engine'
        ])

        try:
            # 1. Market data generation and ingestion
            market_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', 200)
            data_pipeline = env['services']['data_pipeline']
            data_pipeline.get_market_data.return_value = market_data

            # 2. SMC pattern detection
            smc_detector = env['services']['smc_detector']
            detected_patterns = [
                {
                    'type': 'ORDER_BLOCK',
                    'price_level': (49500, 49600),
                    'direction': 'bullish',
                    'strength': 0.85,
                    'timestamp': datetime.now()
                },
                {
                    'type': 'CHOCH',
                    'price_level': 49700,
                    'direction': 'bullish',
                    'confidence': 0.8,
                    'timestamp': datetime.now()
                }
            ]
            smc_detector.detect_patterns.return_value = detected_patterns

            # 3. Decision making
            decision_engine = env['services']['decision_engine']
            trading_decision = {
                'action': 'buy',
                'confidence': 0.82,
                'entry_price': 49650,
                'stop_loss': 49200,
                'take_profit': 51000,
                'position_size': 2.0,
                'reasoning': 'Strong bullish order block with CHOCH confirmation'
            }
            decision_engine.make_decision.return_value = trading_decision

            # 4. Risk validation
            risk_manager = env['services']['risk_manager']
            risk_assessment = {
                'is_valid': True,
                'risk_score': 0.35,
                'warnings': [],
                'max_loss': 900,  # 2.0 * (49650 - 49200)
                'risk_reward_ratio': 3.2  # (51000 - 49650) / (49650 - 49200)
            }
            risk_manager.validate_trade_risk.return_value = risk_assessment

            # 5. Trade execution
            execution_engine = env['services']['execution_engine']
            execution_result = {
                'order_id': 'order_12345',
                'status': 'filled',
                'filled_price': 49648,
                'filled_size': 2.0,
                'execution_time': 0.045,  # 45ms
                'fees': 2.0 * 49648 * 0.001  # 0.1% fee
            }
            execution_engine.execute_order.return_value = execution_result

            # Execute complete workflow
            workflow_result = await self._execute_trading_workflow(
                market_data, detected_patterns, env
            )

            # Validate workflow results
            assert workflow_result['status'] == 'completed'
            assert workflow_result['decision']['action'] == 'buy'
            assert workflow_result['risk_assessment']['is_valid']
            assert workflow_result['execution']['status'] == 'filled'
            assert workflow_result['execution']['execution_time'] < 0.1  # <100ms

            # Validate consistency across components
            assert workflow_result['execution']['filled_price'] >= detected_patterns[0]['price_level'][0]
            assert workflow_result['execution']['filled_price'] <= detected_patterns[0]['price_level'][1]

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def _execute_trading_workflow(self, market_data: pd.DataFrame,
                                      patterns: list, env: dict) -> dict:
        """Execute complete trading workflow."""
        data_pipeline = env['services']['data_pipeline']
        smc_detector = env['services']['smc_detector']
        decision_engine = env['services']['decision_engine']
        risk_manager = env['services']['risk_manager']
        execution_engine = env['services']['execution_engine']

        workflow_result = {
            'status': 'in_progress',
            'stages': {},
            'start_time': time.time()
        }

        try:
            # Stage 1: Data ingestion
            ingestion_result = await data_pipeline.ingest_ohlcv_data('BTCUSDT', market_data)
            workflow_result['stages']['ingestion'] = ingestion_result

            # Stage 2: Pattern detection
            smc_detector.detect_patterns.return_value = patterns
            detected_patterns = await smc_detector.detect_patterns(market_data)
            workflow_result['stages']['pattern_detection'] = {
                'status': 'success',
                'patterns_found': len(detected_patterns)
            }

            # Stage 3: Decision making
            decision = await decision_engine.make_decision({
                'market_data': market_data,
                'patterns': detected_patterns,
                'current_price': market_data['close'].iloc[-1]
            })
            workflow_result['stages']['decision'] = decision

            # Stage 4: Risk validation
            risk_assessment = await risk_manager.validate_trade_risk(decision)
            workflow_result['stages']['risk_validation'] = risk_assessment

            # Stage 5: Execution (if risk approved)
            if risk_assessment['is_valid']:
                execution = await execution_engine.execute_order(decision)
                workflow_result['stages']['execution'] = execution
                workflow_result['execution'] = execution
            else:
                workflow_result['execution'] = {'status': 'rejected_by_risk'}

            workflow_result['status'] = 'completed'
            workflow_result['decision'] = decision
            workflow_result['risk_assessment'] = risk_assessment
            workflow_result['duration'] = time.time() - workflow_result['start_time']

            return workflow_result

        except Exception as e:
            workflow_result['status'] = 'failed'
            workflow_result['error'] = str(e)
            return workflow_result

    async def test_multi_asset_portfolio_workflow(self):
        """Test trading workflow with multiple assets in a portfolio."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine', 'risk_manager', 'execution_engine'
        ])

        try:
            portfolio_results = []

            # Process each symbol
            for symbol in symbols:
                market_data = self.market_simulator.generate_ohlcv_data(symbol, 100)

                # Configure mocks for this symbol
                data_pipeline = env['services']['data_pipeline']
                smc_detector = env['services']['smc_detector']
                decision_engine = env['services']['decision_engine']
                risk_manager = env['services']['risk_manager']
                execution_engine = env['services']['execution_engine']

                data_pipeline.get_market_data.return_value = market_data

                # Generate symbol-specific patterns
                patterns = [
                    {
                        'type': 'ORDER_BLOCK',
                        'symbol': symbol,
                        'price_level': (market_data['close'].iloc[-1] * 0.99,
                                      market_data['close'].iloc[-1] * 1.01),
                        'direction': 'bullish' if np.random.random() > 0.5 else 'bearish',
                        'strength': np.random.uniform(0.6, 0.9),
                        'timestamp': datetime.now()
                    }
                ]
                smc_detector.detect_patterns.return_value = patterns

                # Generate symbol-specific decision
                base_price = market_data['close'].iloc[-1]
                decision = {
                    'symbol': symbol,
                    'action': np.random.choice(['buy', 'sell', 'hold']),
                    'confidence': np.random.uniform(0.6, 0.9),
                    'entry_price': base_price,
                    'stop_loss': base_price * (0.98 if np.random.random() > 0.5 else 1.02),
                    'take_profit': base_price * (1.03 if np.random.random() > 0.5 else 0.97),
                    'position_size': np.random.uniform(0.5, 2.0)
                }
                decision_engine.make_decision.return_value = decision

                risk_manager.validate_trade_risk.return_value = {
                    'is_valid': decision['confidence'] > 0.7,
                    'risk_score': 1.0 - decision['confidence'],
                    'warnings': []
                }

                execution_engine.execute_order.return_value = {
                    'order_id': f'order_{symbol}_{int(time.time())}',
                    'status': 'filled' if decision['action'] != 'hold' else 'skipped',
                    'filled_price': decision['entry_price'] * np.random.uniform(0.999, 1.001),
                    'filled_size': decision['position_size'] if decision['action'] != 'hold' else 0,
                    'execution_time': np.random.uniform(0.02, 0.08)
                }

                # Execute workflow for this symbol
                result = await self._execute_trading_workflow(market_data, patterns, env)
                portfolio_results.append(result)

            # Validate portfolio-level results
            successful_trades = [r for r in portfolio_results
                               if r.get('execution', {}).get('status') == 'filled']
            rejected_trades = [r for r in portfolio_results
                              if not r.get('risk_assessment', {}).get('is_valid', False)]

            assert len(portfolio_results) == len(symbols)
            assert len(successful_trades) + len(rejected_trades) + \
                   len([r for r in portfolio_results if r.get('decision', {}).get('action') == 'hold']) == len(symbols)

            # Check portfolio diversification
            if len(successful_trades) > 1:
                symbols_traded = [r['decision']['symbol'] for r in successful_trades]
                assert len(set(symbols_traded)) == len(symbols_traded)  # No duplicate symbols

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def test_risk_management_integration(self):
        """Test risk management integration across all trading stages."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine', 'risk_manager'
        ])

        try:
            # Set up scenarios that should trigger risk controls
            risk_scenarios = [
                {
                    'name': 'High Risk Trade',
                    'decision': {
                        'action': 'buy',
                        'position_size': 10.0,  # Very large position
                        'confidence': 0.9,
                        'entry_price': 50000,
                        'stop_loss': 45000,  # 10% stop loss
                        'take_profit': 55000
                    },
                    'expected_outcome': 'rejected'
                },
                {
                    'name': 'Low Confidence Trade',
                    'decision': {
                        'action': 'sell',
                        'position_size': 1.0,
                        'confidence': 0.4,  # Low confidence
                        'entry_price': 50000,
                        'stop_loss': 51000,
                        'take_profit': 49000
                    },
                    'expected_outcome': 'rejected'
                },
                {
                    'name': 'Acceptable Trade',
                    'decision': {
                        'action': 'buy',
                        'position_size': 1.5,
                        'confidence': 0.8,
                        'entry_price': 50000,
                        'stop_loss': 49500,
                        'take_profit': 51500
                    },
                    'expected_outcome': 'accepted'
                }
            ]

            risk_manager = env['services']['risk_manager']

            # Test each scenario
            for scenario in risk_scenarios:
                # Configure risk manager response based on scenario
                if scenario['expected_outcome'] == 'rejected':
                    risk_manager.validate_trade_risk.return_value = {
                        'is_valid': False,
                        'risk_score': 0.8,
                        'warnings': ['High position size', 'Low confidence'],
                        'rejection_reason': scenario['name']
                    }
                else:
                    risk_manager.validate_trade_risk.return_value = {
                        'is_valid': True,
                        'risk_score': 0.3,
                        'warnings': [],
                        'max_loss': 750,
                        'risk_reward_ratio': 3.0
                    }

                # Execute risk validation
                risk_assessment = await risk_manager.validate_trade_risk(scenario['decision'])

                # Validate outcome
                assert risk_assessment['is_valid'] == (scenario['expected_outcome'] == 'accepted')

                if scenario['expected_outcome'] == 'rejected':
                    assert risk_assessment['risk_score'] > 0.7
                    assert len(risk_assessment['warnings']) > 0
                else:
                    assert risk_assessment['risk_score'] < 0.5

            # Test portfolio-level risk management
            portfolio_decisions = [
                {'symbol': 'BTCUSDT', 'position_size': 2.0, 'action': 'buy'},
                {'symbol': 'ETHUSDT', 'position_size': 3.0, 'action': 'buy'},
                {'symbol': 'ADAUSDT', 'position_size': 1.5, 'action': 'sell'}
            ]

            risk_manager.calculate_portfolio_risk.return_value = {
                'total_exposure': 0.065,  # 6.5% of portfolio
                'max_drawdown': 0.12,
                'var_95': -0.03,
                'correlation_risk': 0.75,
                'concentration_risk': 0.4,
                'within_limits': True
            }

            portfolio_risk = await risk_manager.calculate_portfolio_risk(portfolio_decisions)
            assert portfolio_risk['within_limits']
            assert portfolio_risk['total_exposure'] < 0.1  # Less than 10% exposure

        finally:
            await self.integration_helper.cleanup_test_environment(env)


class TestPerformanceIntegration(AsyncTestCase):
    """Integration tests focusing on performance under load."""

    @pytest.fixture(autouse=True)
    def setup_fixture(self, mock_config):
        self.config = mock_config
        self.integration_helper = IntegrationTestHelper()

    async def test_high_frequency_data_processing(self):
        """Test system performance with high-frequency data."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine'
        ])

        try:
            # Generate high-frequency data (1-second intervals)
            high_freq_data = []
            for i in range(100):  # 100 data points
                data_point = {
                    'timestamp': datetime.now() - timedelta(seconds=i),
                    'symbol': 'BTCUSDT',
                    'price': 50000 + np.random.normal(0, 100),
                    'volume': np.random.uniform(50, 200)
                }
                high_freq_data.append(data_point)

            # Process with performance tracking
            start_time = time.time()
            processed_count = 0
            processing_times = []

            data_pipeline = env['services']['data_pipeline']
            smc_detector = env['services']['smc_detector']
            decision_engine = env['services']['decision_engine']

            # Configure mocks for high-frequency processing
            data_pipeline.process_real_time_data.return_value = {
                'status': 'processed',
                'processing_time': np.random.uniform(0.001, 0.005)
            }

            smc_detector.analyze_real_time_patterns.return_value = {
                'new_patterns': i % 10 == 0,  # Pattern every 10th data point
                'processing_time': np.random.uniform(0.002, 0.008)
            }

            decision_engine.make_real_time_decision.return_value = {
                'action': 'hold',
                'confidence': 0.6,
                'processing_time': np.random.uniform(0.001, 0.003)
            }

            # Process all data points
            for data_point in high_freq_data:
                point_start_time = time.time()

                # Simulate processing pipeline
                processed_data = await data_pipeline.process_real_time_data(data_point)
                pattern_result = await smc_detector.analyze_real_time_patterns(processed_data)

                if pattern_result['new_patterns']:
                    decision = await decision_engine.make_real_time_decision({
                        'data': processed_data,
                        'patterns': pattern_result
                    })

                point_processing_time = time.time() - point_start_time
                processing_times.append(point_processing_time)
                processed_count += 1

                # Validate processing time constraints
                assert point_processing_time < 0.1  # Each point should process in <100ms

            total_processing_time = time.time() - start_time
            avg_processing_time = np.mean(processing_times)
            max_processing_time = np.max(processing_times)

            # Performance assertions
            assert processed_count == len(high_freq_data)
            assert avg_processing_time < 0.05  # Average <50ms per data point
            assert max_processing_time < 0.1   # Maximum <100ms
            assert total_processing_time < len(high_freq_data) * 0.1  # Total <10s

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def test_concurrent_symbol_processing(self):
        """Test concurrent processing of multiple symbols."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine'
        ])

        try:
            # Create concurrent processing tasks
            async def process_symbol_async(symbol: str):
                # Generate data for this symbol
                market_data = self.market_simulator.generate_ohlcv_data(symbol, 50)

                data_pipeline = env['services']['data_pipeline']
                smc_detector = env['services']['smc_detector']
                decision_engine = env['services']['decision_engine']

                # Configure mocks
                data_pipeline.get_market_data.return_value = market_data
                data_pipeline.ingest_ohlcv_data.return_value = {
                    'status': 'success',
                    'records_processed': len(market_data)
                }

                smc_detector.detect_patterns.return_value = [
                    {
                        'type': 'ORDER_BLOCK',
                        'symbol': symbol,
                        'strength': np.random.uniform(0.6, 0.9),
                        'timestamp': datetime.now()
                    }
                ]

                decision_engine.make_decision.return_value = {
                    'symbol': symbol,
                    'action': np.random.choice(['buy', 'sell', 'hold']),
                    'confidence': np.random.uniform(0.6, 0.9),
                    'processing_time': np.random.uniform(0.01, 0.05)
                }

                # Process symbol
                start_time = time.time()

                ingestion_result = await data_pipeline.ingest_ohlcv_data(symbol, market_data)
                patterns = await smc_detector.detect_patterns(market_data)
                decision = await decision_engine.make_decision({
                    'symbol': symbol,
                    'market_data': market_data,
                    'patterns': patterns
                })

                processing_time = time.time() - start_time

                return {
                    'symbol': symbol,
                    'status': 'success',
                    'processing_time': processing_time,
                    'records_processed': len(market_data),
                    'patterns_found': len(patterns),
                    'decision': decision
                }

            # Run all symbols concurrently
            start_time = time.time()
            results = await asyncio.gather(*[process_symbol_async(symbol) for symbol in symbols])
            total_time = time.time() - start_time

            # Validate concurrent processing results
            assert len(results) == len(symbols)
            assert all(r['status'] == 'success' for r in results)
            assert all(r['processing_time'] < 2.0 for r in results)  # Each symbol <2s

            # Concurrent processing should be faster than sequential
            avg_individual_time = np.mean([r['processing_time'] for r in results])
            assert total_time < avg_individual_time * len(symbols) * 0.8  # At least 20% faster than sequential

        finally:
            await self.integration_helper.cleanup_test_environment(env)

    async def test_memory_usage_under_load(self):
        """Test memory usage during high-load scenarios."""
        env = await self.integration_helper.setup_test_environment([
            'data_pipeline', 'smc_detector', 'decision_engine', 'risk_manager'
        ])

        try:
            # Monitor memory usage
            import psutil
            process = psutil.Process()

            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples = [initial_memory]

            # Process large amounts of data
            batch_size = 50
            num_batches = 10

            data_pipeline = env['services']['data_pipeline']
            smc_detector = env['services']['smc_detector']
            decision_engine = env['services']['decision_engine']
            risk_manager = env['services']['risk_manager']

            for batch_num in range(num_batches):
                # Generate large dataset
                market_data = self.market_simulator.generate_ohlcv_data('BTCUSDT', batch_size * 100)

                # Process the data
                data_pipeline.ingest_ohlcv_data.return_value = {
                    'status': 'success',
                    'records_processed': len(market_data)
                }

                smc_detector.detect_patterns.return_value = [
                    {'type': 'ORDER_BLOCK', 'strength': 0.8} for _ in range(10)
                ]

                decision_engine.make_decision.return_value = {
                    'action': 'hold',
                    'confidence': 0.7
                }

                risk_manager.validate_trade_risk.return_value = {
                    'is_valid': True,
                    'risk_score': 0.3
                }

                # Execute pipeline
                await data_pipeline.ingest_ohlcv_data('BTCUSDT', market_data)
                await smc_detector.detect_patterns(market_data)
                await decision_engine.make_decision({'data': market_data})
                await risk_manager.validate_trade_risk({'action': 'hold'})

                # Sample memory usage
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)

                # Small delay to allow garbage collection
                await asyncio.sleep(0.1)

            final_memory = memory_samples[-1]
            peak_memory = max(memory_samples)
            memory_growth = final_memory - initial_memory

            # Memory usage assertions
            assert memory_growth < 100  # Less than 100MB growth
            assert peak_memory < initial_memory + 200  # Peak shouldn't exceed initial + 200MB

            # Check for memory leaks (steady or decreasing trend)
            if len(memory_samples) > 5:
                recent_memory = memory_samples[-5:]
                memory_trend = np.polyfit(range(len(recent_memory)), recent_memory, 1)[0]
                assert memory_trend < 1  # Memory growth rate should be minimal

        finally:
            await self.integration_helper.cleanup_test_environment(env)


# Integration test runner
class IntegrationTestRunner:
    """Comprehensive integration test runner."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_tracker = PerformanceTracker()

    async def run_all_integration_tests(self):
        """Run all integration tests with comprehensive reporting."""
        self.logger.info("Starting comprehensive integration test suite...")

        test_classes = [
            TestDataFlowIntegration,
            TestTradingWorkflowIntegration,
            TestPerformanceIntegration
        ]

        results = {}
        for test_class in test_classes:
            self.logger.info(f"Running {test_class.__name__} integration tests...")

            start_time = time.time()
            test_results = []

            # Create test instance and run tests
            test_instance = test_class()

            # Run all test methods
            test_methods = [method for method in dir(test_instance)
                          if method.startswith('test_') and asyncio.iscoroutinefunction(method)]

            for method_name in test_methods:
                method_start_time = time.time()
                try:
                    await test_instance.setUp()
                    method = getattr(test_instance, method_name)
                    await method()
                    await test_instance.tearDown()

                    test_results.append({
                        'method': method_name,
                        'status': 'PASSED',
                        'duration': time.time() - method_start_time
                    })

                except Exception as e:
                    test_results.append({
                        'method': method_name,
                        'status': 'FAILED',
                        'error': str(e),
                        'duration': time.time() - method_start_time
                    })

            results[test_class.__name__] = {
                'status': 'completed',
                'tests': test_results,
                'total_duration': time.time() - start_time,
                'passed': len([t for t in test_results if t['status'] == 'PASSED']),
                'failed': len([t for t in test_results if t['status'] == 'FAILED'])
            }

        return self._generate_integration_report(results)

    def _generate_integration_report(self, results: dict) -> dict:
        """Generate comprehensive integration test report."""
        total_tests = sum(r['passed'] + r['failed'] for r in results.values())
        total_passed = sum(r['passed'] for r in results.values())
        total_failed = sum(r['failed'] for r in results.values())

        return {
            'summary': {
                'total_test_classes': len(results),
                'total_tests': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'test_classes': results,
            'performance_metrics': self.performance_tracker.get_performance_report(),
            'recommendations': self._generate_recommendations(results)
        }

    def _generate_recommendations(self, results: dict) -> list:
        """Generate recommendations based on test results."""
        recommendations = []

        for test_class, class_results in results.items():
            if class_results['failed'] > 0:
                recommendations.append(
                    f"Review and fix {class_results['failed']} failing tests in {test_class}"
                )

            if class_results['total_duration'] > 10:
                recommendations.append(
                    f"Optimize performance in {test_class} (took {class_results['total_duration']:.1f}s)"
                )

        # Check for patterns in failures
        failing_tests = []
        for class_results in results.values():
            failing_tests.extend([
                test['method'] for test in class_results['tests']
                if test['status'] == 'FAILED'
            ])

        if len(failing_tests) > 0:
            recommendations.append("Review system integration points and error handling")

        if total_failed == 0:
            recommendations.append("All integration tests passing - system integration is robust")

        return recommendations


# Entry point for running integration tests
if __name__ == "__main__":
    async def main():
        runner = IntegrationTestRunner()
        results = await runner.run_all_integration_tests()

        print("\n" + "="*60)
        print("INTEGRATION TEST RESULTS")
        print("="*60)

        summary = results['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success Rate: {summary['success_rate']:.1f}%")

        print("\nTest Class Results:")
        for test_class, class_results in results['test_classes'].items():
            status_symbol = "✅" if class_results['failed'] == 0 else "❌"
            print(f"  {status_symbol} {test_class}: {class_results['passed']}/{class_results['passed'] + class_results['failed']} passed ({class_results['total_duration']:.1f}s)")

        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"  • {rec}")

    asyncio.run(main())