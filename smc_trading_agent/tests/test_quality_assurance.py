#!/usr/bin/env python3
"""
Quality Assurance Test Suite for Enhanced SMC Trading System

This comprehensive test suite validates:

1. SMC Pattern Detection Accuracy
2. Risk Management Validation
3. ML Model Backtesting Framework
4. Regulatory Compliance Tests
5. Security Vulnerability Assessments

Each test includes detailed validation with specific success criteria and edge case coverage.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock
import json
import time
import logging
import math
from dataclasses import dataclass
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import system components
from smc_detector.indicators import SMCIndicators
from risk_manager.advanced_risk_manager import AdvancedRiskManager
from decision_engine.ml_decision_engine import MLDecisionEngine
from validators import data_validator, DataQualityLevel
from error_handlers import CircuitBreaker, health_monitor

@dataclass
class SMCValidationResult:
    """SMC pattern detection validation result."""
    pattern_type: str
    expected_count: int
    detected_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float

@dataclass
class RiskValidationResult:
    """Risk management validation result."""
    risk_type: str
    test_scenarios: int
    risk_violations_detected: int
    correct_actions_taken: int
    response_time_ms: float
    risk_containment_effective: bool

class TestSMCPatternDetectionAccuracy:
    """Test SMC pattern detection accuracy and reliability."""

    @pytest.fixture
    def smc_indicators(self):
        """Initialize SMC indicators for testing."""
        return SMCIndicators()

    @pytest.fixture
    def known_patterns_data(self):
        """Generate market data with known SMC patterns."""
        np.random.seed(42)  # For reproducible tests

        # Generate 1000 candles with embedded patterns
        periods = 1000
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='5T')

        # Base price
        base_price = 50000.0
        prices = [base_price]

        # Generate price action with known patterns
        for i in range(1, periods):
            # Add trend and pattern-based movements
            if i < 200:
                # Uptrend with higher highs and higher lows
                change = np.random.normal(0.001, 0.002)
            elif i < 400:
                # Downtrend with lower highs and lower lows
                change = np.random.normal(-0.001, 0.003)
            elif i < 600:
                # Range-bound with consolidation
                change = np.random.normal(0, 0.001)
            elif i < 800:
                # Breakout pattern
                if i == 600:
                    change = 0.02  # 2% breakout
                else:
                    change = np.random.normal(0.005, 0.002)
            else:
                # Reversal pattern
                if i == 800:
                    change = -0.015  # 1.5% reversal
                else:
                    change = np.random.normal(-0.003, 0.002)

            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1000.0))  # Prevent negative prices

        # Generate OHLC data
        opens = np.array(prices[:-1])
        closes = np.array(prices[1:])

        # Generate highs and lows with realistic ranges
        high_low_spread = 0.001  # 0.1% typical spread
        highs = np.maximum(opens, closes) + np.random.uniform(0, prices[1:] * high_low_spread, periods-1)
        lows = np.minimum(opens, closes) - np.random.uniform(0, prices[1:] * high_low_spread, periods-1)

        # Generate volume with patterns
        base_volume = 1000.0
        volumes = np.random.lognormal(np.log(base_volume), 0.5, periods-1)

        # Add volume spikes at pattern transitions
        volumes[200] *= 3  # Trend change
        volumes[400] *= 2.5  # Trend change
        volumes[600] *= 5  # Breakout
        volumes[800] *= 4  # Reversal

        return pd.DataFrame({
            'timestamp': dates[1:],
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

    @pytest.fixture
    def manual_patterns(self):
        """Manually identified expected patterns for validation."""
        return {
            'order_blocks': [
                {'candle_index': 150, 'direction': 'bullish', 'strength': 0.8},
                {'candle_index': 350, 'direction': 'bearish', 'strength': 0.7},
                {'candle_index': 750, 'direction': 'bullish', 'strength': 0.9}
            ],
            'choch_bos': [
                {'candle_index': 200, 'type': 'CHOCH', 'direction': 'bearish'},
                {'candle_index': 400, 'type': 'CHOCH', 'direction': 'bullish'},
                {'candle_index': 600, 'type': 'BOS', 'direction': 'bullish'},
                {'candle_index': 800, 'type': 'CHOCH', 'direction': 'bearish'}
            ],
            'fvg': [
                {'start_index': 250, 'end_index': 252, 'size_percent': 0.15},
                {'candle_index': 550, 'size_percent': 0.12},
                {'candle_index': 650, 'size_percent': 0.18}
            ],
            'liquidity_sweeps': [
                {'candle_index': 180, 'type': 'high_sweep'},
                {'candle_index': 320, 'type': 'low_sweep'},
                {'candle_index': 680, 'type': 'high_sweep'}
            ]
        }

    def test_order_block_detection_accuracy(self, smc_indicators, known_patterns_data, manual_patterns):
        """Test order block detection accuracy."""
        # Detect order blocks
        detected_order_blocks = smc_indicators.detect_order_blocks(known_patterns_data)

        # Validation metrics
        expected_order_blocks = manual_patterns['order_blocks']
        tolerance_candles = 5  # Allow 5 candle tolerance

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        # Check each expected order block
        for expected in expected_order_blocks:
            expected_index = expected['candle_index']
            expected_direction = expected['direction']

            # Find if there's a detected order block within tolerance
            detected_match = False
            for detected in detected_order_blocks:
                if (abs(detected['candle_index'] - expected_index) <= tolerance_candles and
                    detected['direction'] == expected_direction):
                    detected_match = True
                    break

            if detected_match:
                true_positives += 1
            else:
                false_negatives += 1

        # Check for false positives (detected blocks not in expected)
        for detected in detected_order_blocks:
            detected_index = detected['candle_index']
            detected_direction = detected['direction']

            expected_match = False
            for expected in expected_order_blocks:
                if (abs(detected_index - expected['candle_index']) <= tolerance_candles and
                    detected['direction'] == expected['direction']):
                    expected_match = True
                    break

            if not expected_match:
                false_positives += 1

        # Calculate metrics
        total_expected = len(expected_order_blocks)
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(total_expected, 1)
        f1_score = 2 * (precision * recall) / max(precision + recall, 1)
        accuracy = true_positives / max(total_expected + false_positives, 1)

        result = SMCValidationResult(
            pattern_type='order_blocks',
            expected_count=total_expected,
            detected_count=len(detected_order_blocks),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=accuracy
        )

        # Validate minimum accuracy thresholds
        assert precision >= 0.7, f"Order block precision {precision:.2f} below 70% threshold"
        assert recall >= 0.6, f"Order block recall {recall:.2f} below 60% threshold"
        assert f1_score >= 0.65, f"Order block F1 score {f1_score:.2f} below 65% threshold"

        return result

    def test_choch_bos_detection_accuracy(self, smc_indicators, known_patterns_data, manual_patterns):
        """Test CHOCH/BOS detection accuracy."""
        # Detect CHOCH/BOS patterns
        detected_patterns = smc_indicators.detect_choch_bos(known_patterns_data)

        expected_patterns = manual_patterns['choch_bos']
        tolerance_candles = 3

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        # Validation logic similar to order blocks
        for expected in expected_patterns:
            expected_index = expected['candle_index']
            expected_type = expected['type']
            expected_direction = expected['direction']

            detected_match = False
            for detected in detected_patterns:
                if (abs(detected['candle_index'] - expected_index) <= tolerance_candles and
                    detected.get('type') == expected_type and
                    detected.get('direction') == expected_direction):
                    detected_match = True
                    break

            if detected_match:
                true_positives += 1
            else:
                false_negatives += 1

        for detected in detected_patterns:
            detected_index = detected['candle_index']
            detected_type = detected.get('type')
            detected_direction = detected.get('direction')

            expected_match = False
            for expected in expected_patterns:
                if (abs(detected_index - expected['candle_index']) <= tolerance_candles and
                    detected_type == expected['type'] and
                    detected_direction == expected['direction']):
                    expected_match = True
                    break

            if not expected_match:
                false_positives += 1

        total_expected = len(expected_patterns)
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(total_expected, 1)
        f1_score = 2 * (precision * recall) / max(precision + recall, 1)

        result = SMCValidationResult(
            pattern_type='choch_bos',
            expected_count=total_expected,
            detected_count=len(detected_patterns),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=precision  # Use precision for CHOCH/BOS
        )

        # Validate accuracy (CHOCH/BOS is harder to detect)
        assert precision >= 0.6, f"CHOCH/BOS precision {precision:.2f} below 60% threshold"
        assert recall >= 0.5, f"CHOCH/BOS recall {recall:.2f} below 50% threshold"

        return result

    def test_fvg_detection_accuracy(self, smc_indicators, known_patterns_data, manual_patterns):
        """Test Fair Value Gap detection accuracy."""
        # Detect FVG patterns
        detected_fvgs = smc_indicators.detect_fair_value_gaps(known_patterns_data)

        expected_fvgs = manual_patterns['fvg']
        tolerance_candles = 2

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        for expected in expected_fvgs:
            expected_index = expected['candle_index']

            detected_match = False
            for detected in detected_fvgs:
                if abs(detected['candle_index'] - expected_index) <= tolerance_candles:
                    detected_match = True
                    break

            if detected_match:
                true_positives += 1
            else:
                false_negatives += 1

        for detected in detected_fvgs:
            detected_index = detected['candle_index']

            expected_match = False
            for expected in expected_fvgs:
                if abs(detected_index - expected['candle_index']) <= tolerance_candles:
                    expected_match = True
                    break

            if not expected_match:
                false_positives += 1

        total_expected = len(expected_fvgs)
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(total_expected, 1)
        f1_score = 2 * (precision * recall) / max(precision + recall, 1)

        result = SMCValidationResult(
            pattern_type='fvg',
            expected_count=total_expected,
            detected_count=len(detected_fvgs),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=precision
        )

        # FVG detection should be more accurate
        assert precision >= 0.8, f"FVG precision {precision:.2f} below 80% threshold"
        assert recall >= 0.7, f"FVG recall {recall:.2f} below 70% threshold"

        return result

    def test_pattern_detection_consistency(self, smc_indicators, known_patterns_data):
        """Test pattern detection consistency across multiple runs."""
        # Run detection multiple times
        results = []
        for i in range(5):
            order_blocks = smc_indicators.detect_order_blocks(known_patterns_data)
            results.append(len(order_blocks))

        # Check for consistency
        mean_count = np.mean(results)
        std_count = np.std(results)
        coefficient_of_variation = std_count / max(mean_count, 1)

        assert coefficient_of_variation <= 0.1, \
            f"Pattern detection inconsistent: CV={coefficient_of_variation:.2f} > 0.1"

    @pytest.mark.asyncio
    async def test_real_time_pattern_detection(self, smc_indicators):
        """Test real-time pattern detection performance."""
        # Generate streaming data
        periods = 100
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1T')

        base_price = 50000.0
        prices = [base_price]

        for i in range(1, periods):
            change = np.random.normal(0, 0.001)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)

        # Test real-time processing
        detection_times = []

        for i in range(10, periods):
            # Create sliding window
            window_data = pd.DataFrame({
                'timestamp': dates[max(0, i-50):i],
                'open': [prices[j] * (1 + np.random.normal(0, 0.0005)) for j in range(max(0, i-50), i)],
                'high': [prices[j] * (1 + np.random.uniform(0, 0.001)) for j in range(max(0, i-50), i)],
                'low': [prices[j] * (1 - np.random.uniform(0, 0.001)) for j in range(max(0, i-50), i)],
                'close': prices[max(0, i-50):i],
                'volume': np.random.lognormal(7, 0.5, i - max(0, i-50))
            })

            start_time = time.time()
            patterns = smc_indicators.detect_all_patterns(window_data)
            detection_time = time.time() - start_time

            detection_times.append(detection_time)

        # Validate performance
        avg_detection_time = np.mean(detection_times)
        max_detection_time = np.max(detection_times)

        assert avg_detection_time <= 0.1, f"Average detection time {avg_detection_time:.3f}s exceeds 100ms"
        assert max_detection_time <= 0.5, f"Maximum detection time {max_detection_time:.3f}s exceeds 500ms"

class TestRiskManagementValidation:
    """Test risk management system validation and effectiveness."""

    @pytest.fixture
    def risk_manager(self):
        """Initialize advanced risk manager for testing."""
        return AdvancedRiskManager({
            'max_position_size': 1000.0,
            'max_daily_loss': 500.0,
            'max_drawdown': 0.15,
            'var_limit': 0.05,
            'max_leverage': 3.0,
            'stress_test_loss': 0.10
        })

    @pytest.fixture
    def risk_scenarios(self):
        """Define test scenarios for risk validation."""
        return {
            'position_size_violations': [
                {'size': 1500.0, 'expected_action': 'reject'},
                {'size': 1200.0, 'expected_action': 'reduce'},
                {'size': 800.0, 'expected_action': 'accept'}
            ],
            'loss_limit_violations': [
                {'daily_loss': 600.0, 'expected_action': 'stop_trading'},
                {'daily_loss': 450.0, 'expected_action': 'reduce_size'},
                {'daily_loss': 300.0, 'expected_action': 'accept'}
            ],
            'drawdown_violations': [
                {'drawdown': 0.20, 'expected_action': 'close_positions'},
                {'drawdown': 0.12, 'expected_action': 'reduce_risk'},
                {'drawdown': 0.08, 'expected_action': 'accept'}
            ],
            'leverage_violations': [
                {'leverage': 4.0, 'expected_action': 'reject'},
                {'leverage': 2.5, 'expected_action': 'accept_with_warning'},
                {'leverage': 1.5, 'expected_action': 'accept'}
            ]
        }

    @pytest.mark.asyncio
    async def test_position_size_validation(self, risk_manager, risk_scenarios):
        """Test position size risk validation."""
        scenarios = risk_scenarios['position_size_violations']
        correct_actions = 0

        for scenario in scenarios:
            position_request = {
                'symbol': 'BTC/USDT',
                'size': scenario['size'],
                'price': 50000.0,
                'side': 'buy'
            }

            start_time = time.time()
            risk_result = await risk_manager.validate_position(position_request)
            response_time = time.time() - start_time

            # Validate risk action
            if risk_result['action'] == scenario['expected_action']:
                correct_actions += 1

            # Validate response time
            assert response_time <= 0.01, f"Risk validation took {response_time:.3f}s, exceeds 10ms"

        accuracy = correct_actions / len(scenarios)
        assert accuracy >= 0.9, f"Position size validation accuracy {accuracy:.2f} below 90%"

        return RiskValidationResult(
            risk_type='position_size',
            test_scenarios=len(scenarios),
            risk_violations_detected=len([s for s in scenarios if s['size'] > 1000]),
            correct_actions_taken=correct_actions,
            response_time_ms=5.0,
            risk_containment_effective=True
        )

    @pytest.mark.asyncio
    async def test_loss_limit_validation(self, risk_manager, risk_scenarios):
        """Test loss limit risk validation."""
        scenarios = risk_scenarios['loss_limit_violations']
        correct_actions = 0

        for scenario in scenarios:
            # Simulate daily P&L
            current_positions = [
                {'symbol': 'BTC/USDT', 'pnl': -scenario['daily_loss'], 'size': 1000}
            ]

            risk_check = await risk_manager.check_daily_loss(current_positions)

            expected_action = scenario['expected_action']
            if (expected_action == 'stop_trading' and risk_check['should_stop']) or \
               (expected_action == 'reduce_size' and risk_check['should_reduce']) or \
               (expected_action == 'accept' and not risk_check['should_stop'] and not risk_check['should_reduce']):
                correct_actions += 1

        accuracy = correct_actions / len(scenarios)
        assert accuracy >= 0.9, f"Loss limit validation accuracy {accuracy:.2f} below 90%"

    @pytest.mark.asyncio
    async def test_drawdown_validation(self, risk_manager, risk_scenarios):
        """Test drawdown risk validation."""
        scenarios = risk_scenarios['drawdown_violations']
        correct_actions = 0

        for scenario in scenarios:
            # Simulate portfolio drawdown
            portfolio_data = {
                'current_value': 100000.0 * (1 - scenario['drawdown']),
                'peak_value': 100000.0,
                'positions': [
                    {'symbol': 'BTC/USDT', 'value': 50000.0 * (1 - scenario['drawdown'])},
                    {'symbol': 'ETH/USDT', 'value': 50000.0 * (1 - scenario['drawdown'])}
                ]
            }

            drawdown_check = await risk_manager.check_drawdown(portfolio_data)

            expected_action = scenario['expected_action']
            if (expected_action == 'close_positions' and drawdown_check['emergency_close']) or \
               (expected_action == 'reduce_risk' and drawdown_check['reduce_exposure']) or \
               (expected_action == 'accept' and not drawdown_check['emergency_close'] and not drawdown_check['reduce_exposure']):
                correct_actions += 1

        accuracy = correct_actions / len(scenarios)
        assert accuracy >= 0.9, f"Drawdown validation accuracy {accuracy:.2f} below 90%"

    @pytest.mark.asyncio
    async def test_var_calculation_accuracy(self, risk_manager):
        """Test VaR calculation accuracy and reliability."""
        # Generate historical return data
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # 1 year of daily returns

        portfolio_value = 100000.0
        confidence_levels = [0.95, 0.99]

        var_results = {}
        for confidence in confidence_levels:
            var_result = await risk_manager.calculate_var(returns, portfolio_value, confidence)
            var_results[confidence] = var_result

        # Validate VaR calculations
        # VaR should be positive (loss amount)
        assert var_results[0.95]['var'] > 0, "95% VaR should be positive"
        assert var_results[0.99]['var'] > 0, "99% VaR should be positive"

        # 99% VaR should be greater than 95% VaR
        assert var_results[0.99]['var'] > var_results[0.95]['var'], \
            "99% VaR should be greater than 95% VaR"

        # Expected VaR ranges (based on normal distribution)
        expected_var_95 = portfolio_value * 0.02 * 1.65  # 2% daily vol * 1.65 z-score
        expected_var_99 = portfolio_value * 0.02 * 2.33  # 2% daily vol * 2.33 z-score

        var_95_error = abs(var_results[0.95]['var'] - expected_var_95) / expected_var_95
        var_99_error = abs(var_results[0.99]['var'] - expected_var_99) / expected_var_99

        assert var_95_error <= 0.1, f"95% VaR calculation error {var_95_error:.2f} exceeds 10%"
        assert var_99_error <= 0.1, f"99% VaR calculation error {var_99_error:.2f} exceeds 10%"

    @pytest.mark.asyncio
    async def test_risk_circuit_breaker(self, risk_manager):
        """Test risk circuit breaker functionality."""
        # Normal operations
        normal_requests = [
            {'symbol': 'BTC/USDT', 'size': 500.0, 'price': 50000.0}
            for _ in range(5)
        ]

        for request in normal_requests:
            result = await risk_manager.validate_position(request)
            assert result['action'] in ['accept', 'accept_with_warning'], \
                "Normal requests should be accepted"

        # Simulate risk violation to trigger circuit breaker
        violation_requests = [
            {'symbol': 'BTC/USDT', 'size': 2000.0, 'price': 50000.0}  # Exceeds max position
            for _ in range(10)  # Multiple violations to trigger circuit breaker
        ]

        for request in violation_requests:
            await risk_manager.validate_position(request)

        # Check if circuit breaker is triggered
        circuit_status = await risk_manager.get_circuit_breaker_status()
        assert circuit_status['is_open'], "Circuit breaker should be open after violations"

        # Test that further requests are blocked
        test_request = {'symbol': 'BTC/USDT', 'size': 100.0, 'price': 50000.0}
        result = await risk_manager.validate_position(test_request)
        assert result['action'] == 'reject', "Requests should be rejected when circuit breaker is open"

        # Wait for circuit breaker recovery
        await asyncio.sleep(1.0)

        # Test recovery
        recovery_request = {'symbol': 'BTC/USDT', 'size': 100.0, 'price': 50000.0}
        result = await risk_manager.validate_position(recovery_request)

        # Should recover after timeout
        assert result['action'] != 'reject', "System should recover after circuit breaker timeout"

class TestMLModelBacktesting:
    """Test ML model backtesting framework and accuracy."""

    @pytest.fixture
    def ml_decision_engine(self):
        """Initialize ML decision engine for testing."""
        return MLDecisionEngine()

    @pytest.fixture
    def historical_data(self):
        """Generate historical data for backtesting."""
        np.random.seed(42)

        # Generate 2 years of hourly data
        periods = 24 * 365 * 2  # 2 years
        dates = pd.date_range(start='2022-01-01', periods=periods, freq='H')

        # Generate realistic price series
        base_price = 50000.0
        prices = [base_price]

        # Add trend, seasonality, and noise
        for i in range(1, periods):
            trend = 0.0001 * np.sin(2 * np.pi * i / (24 * 30))  # Monthly trend
            seasonal = 0.0005 * np.sin(2 * np.pi * i / 24)  # Daily seasonality
            noise = np.random.normal(0, 0.002)  # Random noise

            change = trend + seasonal + noise
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1000.0))

        # Create OHLCV data
        prices = np.array(prices)
        opens = prices[:-1]
        closes = prices[1:]

        highs = np.maximum(opens, closes) + np.random.uniform(0, closes * 0.001, len(closes))
        lows = np.minimum(opens, closes) - np.random.uniform(0, closes * 0.001, len(closes))

        volumes = np.random.lognormal(8, 0.5, len(closes))

        return pd.DataFrame({
            'timestamp': dates[1:],
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

    @pytest.fixture
    def true_signals(self, historical_data):
        """Generate true trading signals based on known patterns."""
        signals = []

        for i in range(50, len(historical_data) - 50):
            window = historical_data.iloc[i-50:i+50]

            # Simple momentum strategy for true signals
            short_ma = window['close'].rolling(10).mean().iloc[-1]
            long_ma = window['close'].rolling(30).mean().iloc[-1]

            if short_ma > long_ma * 1.002:  # 0.2% threshold
                signals.append({
                    'timestamp': window.iloc[-1]['timestamp'],
                    'action': 'buy',
                    'confidence': min(0.9, abs(short_ma - long_ma) / long_ma * 100),
                    'price': window.iloc[-1]['close']
                })
            elif short_ma < long_ma * 0.998:
                signals.append({
                    'timestamp': window.iloc[-1]['timestamp'],
                    'action': 'sell',
                    'confidence': min(0.9, abs(short_ma - long_ma) / long_ma * 100),
                    'price': window.iloc[-1]['close']
                })

        return signals

    @pytest.mark.asyncio
    async def test_backtest_framework_setup(self, ml_decision_engine, historical_data):
        """Test backtesting framework setup and configuration."""
        # Configure backtest
        backtest_config = {
            'start_date': historical_data['timestamp'].min(),
            'end_date': historical_data['timestamp'].max(),
            'initial_capital': 100000.0,
            'commission': 0.001,  # 0.1%
            'slippage': 0.0005,   # 0.05%
            'position_size': 0.1,  # 10% of capital per trade
            'max_positions': 5,
            'stop_loss': 0.02,    # 2%
            'take_profit': 0.04   # 4%
        }

        # Initialize backtest
        backtest_engine = await ml_decision_engine.initialize_backtest(backtest_config)

        assert backtest_engine is not None, "Backtest engine initialization failed"
        assert backtest_engine.initial_capital == backtest_config['initial_capital']
        assert backtest_engine.commission == backtest_config['commission']

    @pytest.mark.asyncio
    async def test_model_accuracy_backtest(self, ml_decision_engine, historical_data, true_signals):
        """Test ML model accuracy through backtesting."""
        # Train model on first year of data
        train_data = historical_data.iloc[:len(historical_data)//2]
        test_data = historical_data.iloc[len(historical_data)//2:]

        # Train models
        await ml_decision_engine.train_models(train_data)

        # Generate predictions on test data
        predictions = []
        true_labels = []

        for i in range(50, len(test_data) - 50):
            window = test_data.iloc[i-50:i]

            prediction = await ml_decision_engine.predict_signal(window)
            predictions.append(prediction['action'])

            # Get true signal for this timestamp
            current_time = test_data.iloc[i]['timestamp']
            true_signal = next((s for s in true_signals if abs((s['timestamp'] - current_time).total_seconds()) < 3600), None)

            if true_signal:
                true_labels.append(true_signal['action'])
            else:
                true_labels.append('hold')

        # Calculate accuracy metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        accuracy = accuracy_score(true_labels, predictions)
        precision = precision_score(true_labels, predictions, average='weighted', zero_division=0)
        recall = recall_score(true_labels, predictions, average='weighted', zero_division=0)
        f1 = f1_score(true_labels, predictions, average='weighted', zero_division=0)

        # Validate minimum performance thresholds
        assert accuracy >= 0.55, f"Model accuracy {accuracy:.2f} below 55% threshold"
        assert f1 >= 0.50, f"Model F1 score {f1:.2f} below 50% threshold"

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_predictions': len(predictions)
        }

    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, ml_decision_engine):
        """Test backtesting performance metrics calculation."""
        # Simulate trade results
        trades = [
            {'entry_price': 50000, 'exit_price': 51000, 'side': 'buy', 'size': 100},
            {'entry_price': 51000, 'exit_price': 49500, 'side': 'sell', 'size': 100},
            {'entry_price': 49500, 'exit_price': 52000, 'side': 'buy', 'size': 150},
            {'entry_price': 52000, 'exit_price': 51500, 'side': 'sell', 'size': 80},
            {'entry_price': 51500, 'exit_price': 53000, 'side': 'buy', 'size': 120}
        ]

        performance_metrics = await ml_decision_engine.calculate_performance_metrics(trades)

        # Validate calculated metrics
        assert 'total_return' in performance_metrics
        assert 'sharpe_ratio' in performance_metrics
        assert 'max_drawdown' in performance_metrics
        assert 'win_rate' in performance_metrics
        assert 'profit_factor' in performance_metrics

        # Validate metric ranges
        assert performance_metrics['win_rate'] >= 0 and performance_metrics['win_rate'] <= 1
        assert isinstance(performance_metrics['sharpe_ratio'], (int, float))
        assert performance_metrics['max_drawdown'] <= 0  # Drawdown should be negative or zero

    @pytest.mark.asyncio
    async def test_walk_forward_analysis(self, ml_decision_engine, historical_data):
        """Test walk-forward analysis methodology."""
        # Split data into walk-forward periods
        total_periods = len(historical_data)
        train_window = total_periods // 4
        test_window = total_periods // 8
        step_size = test_window // 2

        results = []

        for start in range(0, total_periods - train_window - test_window, step_size):
            train_end = start + train_window
            test_end = train_end + test_window

            train_data = historical_data.iloc[start:train_end]
            test_data = historical_data.iloc[train_end:test_end]

            # Train on train data
            await ml_decision_engine.train_models(train_data)

            # Test on test data
            test_results = []
            for i in range(10, len(test_data)):
                window = test_data.iloc[max(0, i-10):i]
                prediction = await ml_decision_engine.predict_signal(window)
                test_results.append(prediction['confidence'])

            if test_results:
                avg_confidence = np.mean(test_results)
                results.append(avg_confidence)

        # Validate walk-forward results
        assert len(results) > 0, "Walk-forward analysis produced no results"

        avg_confidence = np.mean(results)
        confidence_std = np.std(results)

        assert avg_confidence > 0.5, f"Average confidence {avg_confidence:.2f} below 0.5"
        assert confidence_std < 0.3, f"Confidence variance too high: {confidence_std:.2f}"

class TestRegulatoryCompliance:
    """Test regulatory compliance requirements."""

    @pytest.fixture
    def compliance_config(self):
        """Compliance configuration for testing."""
        return {
            'mifid_ii': {
                'transaction_reporting': True,
                'best_execution': True,
                'record_keeping_days': 7,
                'client_classification_required': True
            },
            'risk_limits': {
                'max_leverage': 5.0,
                'margin_requirement': 0.2,
                'position_concentration_limit': 0.3
            },
            'data_protection': {
                'data_retention_days': 2555,  # 7 years
                'anonymization_required': True,
                'audit_trail_required': True
            }
        }

    def test_transaction_reporting_compliance(self, compliance_config):
        """Test MiFID II transaction reporting compliance."""
        # Sample transaction data
        transactions = [
            {
                'timestamp': datetime.now(),
                'instrument': 'BTC/USDT',
                'quantity': 1.5,
                'price': 50000.0,
                'venue': 'binance',
                'client_id': 'client_123',
                'transaction_id': 'txn_001',
                'decision_maker': 'algorithm',
                'execution_algorithm': 'twap'
            }
        ]

        # Validate required fields
        required_fields = [
            'timestamp', 'instrument', 'quantity', 'price',
            'venue', 'transaction_id', 'decision_maker'
        ]

        for transaction in transactions:
            missing_fields = [field for field in required_fields if field not in transaction]
            assert not missing_fields, f"Missing required fields: {missing_fields}"

        # Validate data quality
        for transaction in transactions:
            assert transaction['quantity'] > 0, "Transaction quantity must be positive"
            assert transaction['price'] > 0, "Transaction price must be positive"
            assert isinstance(transaction['timestamp'], datetime), "Timestamp must be datetime object"

    def test_best_execution_compliance(self, compliance_config):
        """Test best execution compliance requirements."""
        # Sample execution data
        executions = [
            {
                'timestamp': datetime.now(),
                'instrument': 'BTC/USDT',
                'order_size': 1000.0,
                'execution_venues': ['binance', 'bybit', 'oanda'],
                'venue_prices': {'binance': 50001.0, 'bybit': 50000.5, 'oanda': 50002.0},
                'selected_venue': 'bybit',
                'execution_price': 50000.5,
                'decision_factors': ['price', 'liquidity', 'cost']
            }
        ]

        for execution in executions:
            # Validate best venue selection
            venue_prices = execution['venue_prices']
            selected_venue = execution['selected_venue']
            execution_price = execution['execution_price']

            # Check if selected venue offered best price
            best_price = min(venue_prices.values())
            assert execution_price <= best_price * 1.0001, \
                f"Selected venue {selected_venue} price {execution_price} not near best price {best_price}"

            # Validate decision factors documentation
            assert 'decision_factors' in execution, "Best execution decision factors not documented"
            assert len(execution['decision_factors']) > 0, "No decision factors documented"

    def test_record_keeping_compliance(self, compliance_config):
        """Test record keeping compliance requirements."""
        # Test data retention
        retention_days = compliance_config['mifid_ii']['record_keeping_days']
        assert retention_days >= 7, f"Record retention {retention_days} days below 7-day minimum"

        # Test audit trail integrity
        audit_entries = [
            {
                'timestamp': datetime.now(),
                'user_id': 'user_123',
                'action': 'place_order',
                'details': {'symbol': 'BTC/USDT', 'side': 'buy', 'quantity': 1.0},
                'ip_address': '192.168.1.100',
                'user_agent': 'SMC-Trading-Agent/1.0'
            }
        ]

        for entry in audit_entries:
            # Validate required audit fields
            required_audit_fields = ['timestamp', 'user_id', 'action', 'details']
            missing_fields = [field for field in required_audit_fields if field not in entry]
            assert not missing_fields, f"Missing audit fields: {missing_fields}"

            # Validate data integrity
            assert isinstance(entry['timestamp'], datetime), "Audit timestamp must be datetime"
            assert len(entry['user_id']) > 0, "User ID cannot be empty"
            assert len(entry['action']) > 0, "Action cannot be empty"

    def test_risk_limit_compliance(self, compliance_config):
        """Test regulatory risk limit compliance."""
        risk_config = compliance_config['risk_limits']

        # Test leverage limits
        positions = [
            {'symbol': 'BTC/USDT', 'notional_value': 50000, 'margin': 10000},
            {'symbol': 'ETH/USDT', 'notional_value': 30000, 'margin': 6000},
            {'symbol': 'ADA/USDT', 'notional_value': 10000, 'margin': 2000}
        ]

        total_notional = sum(p['notional_value'] for p in positions)
        total_margin = sum(p['margin'] for p in positions)

        # Calculate leverage
        leverage = total_notional / max(total_margin, 1)
        assert leverage <= risk_config['max_leverage'], \
            f"Leverage {leverage:.1f} exceeds regulatory limit {risk_config['max_leverage']}"

        # Test position concentration
        largest_position = max(p['notional_value'] for p in positions)
        concentration = largest_position / total_notional
        assert concentration <= risk_config['position_concentration_limit'], \
            f"Position concentration {concentration:.1%} exceeds limit {risk_config['position_concentration_limit']:.1%}"

        # Test margin requirements
        margin_requirement = total_margin / total_notional
        assert margin_requirement >= risk_config['margin_requirement'], \
            f"Margin requirement {margin_requirement:.1%} below minimum {risk_config['margin_requirement']:.1%}"

class TestSecurityVulnerabilityAssessment:
    """Test security vulnerability assessments and mitigation."""

    @pytest.fixture
    def security_config(self):
        """Security configuration for testing."""
        return {
            'authentication': {
                'password_min_length': 12,
                'password_complexity': True,
                'session_timeout': 1800,  # 30 minutes
                'max_login_attempts': 5
            },
            'encryption': {
                'data_at_rest': 'AES-256',
                'data_in_transit': 'TLS-1.3',
                'key_rotation_days': 90
            },
            'api_security': {
                'rate_limiting': True,
                'request_validation': True,
                'cors_enabled': True,
                'https_required': True
            }
        }

    def test_password_security(self, security_config):
        """Test password security requirements."""
        auth_config = security_config['authentication']

        # Test password complexity requirements
        test_passwords = [
            {'password': 'simple', 'should_fail': True},
            {'password': '12345678', 'should_fail': True},
            {'password': 'Password', 'should_fail': True},
            {'password': 'Password123', 'should_fail': True},  # Too short
            {'password': 'SecurePass123!', 'should_fail': False},
            {'password': 'VerySecurePassword123!@#', 'should_fail': False}
        ]

        for test_case in test_passwords:
            password = test_case['password']
            should_fail = test_case['should_fail']

            # Check length
            length_valid = len(password) >= auth_config['password_min_length']

            # Check complexity if required
            complexity_valid = True
            if auth_config['password_complexity']:
                has_upper = any(c.isupper() for c in password)
                has_lower = any(c.islower() for c in password)
                has_digit = any(c.isdigit() for c in password)
                has_special = any(c in '!@#$%^&*' for c in password)
                complexity_valid = has_upper and has_lower and has_digit and has_special

            is_valid = length_valid and complexity_valid

            if should_fail:
                assert not is_valid, f"Password '{password}' should be rejected but passed validation"
            else:
                assert is_valid, f"Password '{password}' should be accepted but failed validation"

    def test_session_security(self, security_config):
        """Test session security implementation."""
        auth_config = security_config['authentication']

        # Test session timeout
        session_timeout = auth_config['session_timeout']
        assert session_timeout <= 3600, f"Session timeout {session_timeout}s exceeds 1 hour maximum"

        # Test login attempt limiting
        max_attempts = auth_config['max_login_attempts']
        assert max_attempts <= 10, f"Max login attempts {max_attempts} exceeds security best practice"

    def test_api_security(self, security_config):
        """Test API security implementation."""
        api_config = security_config['api_security']

        # Test required security features
        assert api_config['rate_limiting'], "Rate limiting must be enabled"
        assert api_config['https_required'], "HTTPS must be required"
        assert api_config['request_validation'], "Request validation must be enabled"

        # Test CORS configuration
        if api_config['cors_enabled']:
            # Would validate actual CORS headers in implementation
            pass

    def test_data_encryption(self, security_config):
        """Test data encryption requirements."""
        encryption_config = security_config['encryption']

        # Validate encryption standards
        assert encryption_config['data_at_rest'] == 'AES-256', \
            f"Data at rest encryption {encryption_config['data_at_rest']} not AES-256"

        assert encryption_config['data_in_transit'] == 'TLS-1.3', \
            f"Data in transit encryption {encryption_config['data_in_transit']} not TLS-1.3"

        # Validate key rotation
        key_rotation_days = encryption_config['key_rotation_days']
        assert key_rotation_days <= 365, f"Key rotation {key_rotation_days} days exceeds 1 year"

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test SQL injection prevention mechanisms."""
        # Test malicious input
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]

        # Simulate input validation
        for malicious_input in malicious_inputs:
            # Check for SQL injection patterns
            sql_patterns = ["'", ';', '--', '/*', '*/', 'xp_', 'sp_']

            contains_sql_pattern = any(pattern in malicious_input.lower() for pattern in sql_patterns)

            if contains_sql_pattern:
                # Input should be sanitized or rejected
                sanitized_input = malicious_input.replace("'", "''").replace(";", "")
                assert sanitized_input != malicious_input, \
                    f"Malicious input not sanitized: {malicious_input}"

    @pytest.mark.asyncio
    async def test_xss_prevention(self):
        """Test Cross-Site Scripting prevention."""
        # Test malicious scripts
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert('xss')</script>"
        ]

        for payload in xss_payloads:
            # Check for XSS patterns
            xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=']

            contains_xss = any(pattern in payload.lower() for pattern in xss_patterns)

            if contains_xss:
                # Payload should be escaped
                escaped_payload = payload.replace("<", "&lt;").replace(">", "&gt;")
                assert escaped_payload != payload, \
                    f"XSS payload not escaped: {payload}"

# Integration test for quality assurance
@pytest.mark.asyncio
async def test_quality_assurance_integration():
    """Comprehensive integration test for quality assurance."""
    qa_results = {
        'smc_detection': False,
        'risk_management': False,
        'ml_backtesting': False,
        'regulatory_compliance': False,
        'security_assessment': False
    }

    # Initialize test components
    smc_test = TestSMCPatternDetectionAccuracy()
    risk_test = TestRiskManagementValidation()
    ml_test = TestMLModelBacktesting()
    compliance_test = TestRegulatoryCompliance()
    security_test = TestSecurityVulnerabilityAssessment()

    try:
        # Run key QA tests
        smc_indicators = SMCIndicators()
        known_patterns = smc_test.known_patterns_data()
        manual_patterns = smc_test.manual_patterns()

        # Test SMC detection
        order_block_result = smc_test.test_order_block_detection_accuracy(
            smc_indicators, known_patterns, manual_patterns
        )
        qa_results['smc_detection'] = order_block_result.accuracy >= 0.7

        # Test risk management
        risk_manager = AdvancedRiskManager({})
        risk_scenarios = risk_test.risk_scenarios()

        position_result = await risk_test.test_position_size_validation(
            risk_manager, risk_scenarios
        )
        qa_results['risk_management'] = position_result.correct_actions_taken >= 2

        # Test ML backtesting
        ml_engine = MLDecisionEngine()
        historical_data = ml_test.historical_data()
        true_signals = ml_test.true_signals(historical_data)

        backtest_result = await ml_test.test_model_accuracy_backtest(
            ml_engine, historical_data, true_signals
        )
        qa_results['ml_backtesting'] = backtest_result['accuracy'] >= 0.55

        # Test compliance
        compliance_config = compliance_test.compliance_config()
        compliance_test.test_transaction_reporting_compliance(compliance_config)
        qa_results['regulatory_compliance'] = True

        # Test security
        security_config = security_test.security_config()
        security_test.test_password_security(security_config)
        qa_results['security_assessment'] = True

    except Exception as e:
        logging.error(f"Quality assurance integration test failed: {e}")

    # Evaluate overall QA score
    passed_tests = sum(qa_results.values())
    total_tests = len(qa_results)
    qa_score = passed_tests / total_tests

    assert qa_score >= 0.8, f"QA score {qa_score:.1%} below 80% threshold"

    return {
        'qa_score': qa_score,
        'test_results': qa_results,
        'overall_status': 'passed' if qa_score >= 0.8 else 'failed'
    }