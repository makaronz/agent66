"""
Enhanced ML System Components Tests

Comprehensive test suite for optimized components including:
- Optimized Ensemble Architecture
- Enhanced Trading System Integration
- Performance Validation
- System Health Monitoring

Test Categories:
- Unit Tests: Individual component testing
- Integration Tests: Component interaction testing
- Performance Tests: Latency and resource usage
- End-to-End Tests: Complete system workflow
"""

# Try to import pytest, but provide fallback
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Create simple pytest-like decorators
    def pytest_fixture(func):
        return func

    def pytest_main(args):
        import unittest
        # Run as unittest instead
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(__import__(__name__))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

import numpy as np
import pandas as pd
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# Import the enhanced ML components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from decision_engine.optimized_ensemble import (
    OptimizedEnsemble,
    EnsembleOptimizationConfig,
    OptimizationStrategy,
    PerformanceMetric,
    ModelPerformanceHistory,
    calculate_ensemble_diversity,
    create_optimized_ensemble
)

from decision_engine.enhanced_trading_system import (
    EnhancedSMCTradingSystem,
    EnhancedTradingConfig,
    TradingSignal,
    TradingDecision,
    SystemPerformanceMetrics,
    create_enhanced_trading_system
)

from decision_engine.market_regime_detector import get_market_regime_detector
from decision_engine.sentiment_analyzer import get_sentiment_analyzer
from decision_engine.enhanced_feature_engineer import get_enhanced_feature_engineer
from decision_engine.online_learning_adapter import get_online_learning_adapter


class TestEnsembleOptimizationConfig:
    """Test suite for Ensemble Optimization Configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnsembleOptimizationConfig()

        assert config.optimization_strategy == OptimizationStrategy.BAYESIAN
        assert len(config.objective_metrics) == 3
        assert config.optimization_window == 100
        assert config.validation_window == 50
        assert config.min_model_weight == 0.05
        assert config.max_model_weight == 0.60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EnsembleOptimizationConfig(
            optimization_strategy=OptimizationStrategy.ADAPTIVE,
            optimization_window=50,
            min_model_weight=0.1
        )

        assert config.optimization_strategy == OptimizationStrategy.ADAPTIVE
        assert config.optimization_window == 50
        assert config.min_model_weight == 0.1


class TestModelPerformanceHistory:
    """Test suite for Model Performance History."""

    def test_performance_history_initialization(self):
        """Test performance history initialization."""
        history = ModelPerformanceHistory(model_id='test_model')

        assert history.model_id == 'test_model'
        assert len(history.accuracy_history) == 0
        assert len(history.regime_performance) == 0

    def test_recent_metrics_calculation(self):
        """Test recent metrics calculation."""
        history = ModelPerformanceHistory(model_id='test_model')

        # Add some performance data
        for i in range(25):
            history.accuracy_history.append(0.6 + i * 0.01)
            history.precision_history.append(0.5 + i * 0.01)
            history.f1_history.append(0.4 + i * 0.01)

        metrics = history.get_recent_metrics(20)

        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'f1_score' in metrics
        assert metrics['accuracy'] > 0.7  # Should be average of recent values

    def test_regime_performance_tracking(self):
        """Test regime-specific performance tracking."""
        history = ModelPerformanceHistory(model_id='test_model')

        # Add regime-specific performance
        for i in range(15):
            history.regime_performance.setdefault('trending', deque(maxlen=100)).append(0.6 + i * 0.01)
            history.regime_performance.setdefault('ranging', deque(maxlen=100)).append(0.5 + i * 0.005)

        trending_perf = history.get_regime_performance('trending', 10)
        ranging_perf = history.get_regime_performance('ranging', 10)

        assert trending_perf > ranging_perf
        assert trending_perf > 0.6

    def test_empty_performance_metrics(self):
        """Test handling of empty performance history."""
        history = ModelPerformanceHistory(model_id='test_model')
        metrics = history.get_recent_metrics()

        assert metrics == {}

        regime_perf = history.get_regime_performance('unknown')
        assert regime_perf == 0.0


class TestEnsembleDiversity:
    """Test suite for ensemble diversity calculations."""

    def test_diversity_calculation_single_model(self):
        """Test diversity calculation with single model."""
        predictions = np.array([[0.8, 0.2, 0.7]])  # Single model
        diversity = calculate_ensemble_diversity(predictions)
        assert diversity == 0.0

    def test_diversity_calculation_identical_models(self):
        """Test diversity calculation with identical predictions."""
        predictions = np.array([
            [0.8, 0.2, 0.7],  # Model 1
            [0.8, 0.2, 0.7],  # Model 2 (identical)
            [0.8, 0.2, 0.7]   # Model 3 (identical)
        ])
        diversity = calculate_ensemble_diversity(predictions)
        assert diversity == 0.0  # Perfect correlation, no diversity

    def test_diversity_calculation_opposite_models(self):
        """Test diversity calculation with opposite predictions."""
        predictions = np.array([
            [0.9, 0.1, 0.8],  # Model 1
            [0.1, 0.9, 0.2],  # Model 2 (opposite)
            [0.5, 0.5, 0.5]   # Model 3 (neutral)
        ])
        diversity = calculate_ensemble_diversity(predictions)
        assert diversity > 0.5  # High diversity

    def test_diversity_calculation_moderate(self):
        """Test diversity calculation with moderately correlated models."""
        predictions = np.array([
            [0.8, 0.3, 0.7],  # Model 1
            [0.6, 0.4, 0.5],  # Model 2 (similar but not identical)
            [0.4, 0.7, 0.3]   # Model 3 (different)
        ])
        diversity = calculate_ensemble_diversity(predictions)
        assert 0.2 < diversity < 0.8  # Moderate diversity


class TestOptimizedEnsemble:
    """Test suite for Optimized Ensemble."""

    @pytest_fixture
    def mock_ensemble(self):
        """Create mock base ensemble."""
        mock = Mock()
        mock.models = {
            'lstm': Mock(),
            'transformer': Mock(),
            'ppo': Mock(),
            'random_forest': Mock(),
            'xgboost': Mock()
        }
        return mock

    @pytest_fixture
    def mock_regime_adaptive(self):
        """Create mock regime-adaptive ensemble."""
        return Mock()

    @pytest_fixture
    def config(self):
        """Create test configuration."""
        return EnsembleOptimizationConfig(
            optimization_strategy=OptimizationStrategy.ADAPTIVE,
            optimization_window=20,
            validation_window=10
        )

    def test_ensemble_initialization(self):
        """Test ensemble initialization."""
        # Create test fixtures
        mock_ensemble = Mock()
        mock_ensemble.models = {
            'lstm': Mock(),
            'transformer': Mock(),
            'ppo': Mock(),
            'random_forest': Mock(),
            'xgboost': Mock()
        }
        mock_regime_adaptive = Mock()
        config = EnsembleOptimizationConfig(
            optimization_strategy=OptimizationStrategy.ADAPTIVE,
            optimization_window=20,
            validation_window=10
        )

        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        assert ensemble.base_ensemble == mock_ensemble
        assert ensemble.regime_adaptive == mock_regime_adaptive
        assert ensemble.config == config
        assert len(ensemble.current_weights) == 5  # 5 models
        assert len(ensemble.model_performances) == 5

        if HAS_PYTEST:
            assert sum(ensemble.current_weights.values()) == pytest.approx(1.0, rel=1e-5)
        else:
            assert abs(sum(ensemble.current_weights.values()) - 1.0) < 1e-5

    def test_performance_tracking_update(self, mock_ensemble, mock_regime_adaptive, config):
        """Test model performance tracking update."""
        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        predictions = {
            'lstm': np.array([0.7, 0.3, 0.8, 0.2]),
            'transformer': np.array([0.6, 0.4, 0.7, 0.3])
        }
        true_labels = np.array([1, 0, 1, 0])
        regime = 'trending'

        # Update performance
        ensemble.update_model_performance(predictions, true_labels, regime)

        # Check updates
        lstm_history = ensemble.model_performances['lstm']
        transformer_history = ensemble.model_performances['transformer']

        assert len(lstm_history.accuracy_history) == 4
        assert len(lstm_history.regime_performance['trending']) == 4
        assert len(transformer_history.accuracy_history) == 4

    def test_adaptive_optimization(self, mock_ensemble, mock_regime_adaptive, config):
        """Test adaptive weight optimization."""
        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        # Generate test data
        features_batch = [
            {'features': np.random.randn(10)} for _ in range(30)
        ]
        true_labels_batch = np.random.randint(0, 2, size=(30,))
        regimes_batch = ['trending'] * 15 + ['ranging'] * 15

        # Initialize performance data
        for model_id in ensemble.current_weights.keys():
            perf_history = ensemble.model_performances[model_id]
            for _ in range(25):
                perf_history.accuracy_history.append(np.random.uniform(0.5, 0.8))
                perf_history.f1_history.append(np.random.uniform(0.4, 0.7))
                perf_history.profit_history.append(np.random.uniform(0.8, 1.5))

        # Optimize weights
        new_weights = ensemble.optimize_weights(
            features_batch, true_labels_batch, regimes_batch
        )

        # Verify optimization results
        assert isinstance(new_weights, dict)
        assert len(new_weights) == 5
        assert sum(new_weights.values()) == pytest.approx(1.0, rel=1e-5)

        # Check weight constraints
        for weight in new_weights.values():
            assert config.min_model_weight <= weight <= config.max_model_weight

    def test_prediction_with_weights(self, mock_ensemble, mock_regime_adaptive, config):
        """Test prediction with specific weights."""
        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        # Mock base ensemble prediction
        mock_ensemble.predict_single.return_value = np.array([0.7])

        features = {'test_feature': np.array([1.0, 2.0, 3.0])}
        weights = {'lstm': 0.6, 'transformer': 0.4}

        prediction, returned_weights = ensemble._predict_with_weights(features, weights)

        assert isinstance(prediction, np.ndarray)
        assert returned_weights == weights
        mock_ensemble.predict_single.assert_called()

    def test_optimization_report(self, mock_ensemble, mock_regime_adaptive, config):
        """Test optimization report generation."""
        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        # Add some performance data
        for model_id in ensemble.current_weights.keys():
            perf_history = ensemble.model_performances[model_id]
            for _ in range(25):
                perf_history.accuracy_history.append(np.random.uniform(0.6, 0.8))
                perf_history.f1_history.append(np.random.uniform(0.5, 0.7))

        report = ensemble.get_optimization_report()

        assert isinstance(report, dict)
        assert 'optimization_count' in report
        assert 'current_weights' in report
        assert 'model_performances' in report
        assert 'ensemble_diversity' in report
        assert 'recent_optimizations' in report

    def test_rebalancing_decision(self, mock_ensemble, mock_regime_adaptive, config):
        """Test ensemble rebalancing decision logic."""
        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime_adaptive, config)

        current_performance = {'accuracy': 0.65, 'f1_score': 0.62}

        # Should rebalance initially
        should_rebalance = ensemble.should_rebalance(current_performance)
        assert should_rebalance is True

        # Set recent optimization
        ensemble.last_optimization = datetime.now()

        # Should not rebalance immediately after optimization
        should_rebalance = ensemble.should_rebalance(current_performance)
        assert should_rebalance is False


class TestEnhancedTradingConfig:
    """Test suite for Enhanced Trading Configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnhancedTradingConfig()

        assert config.enable_regime_detection is True
        assert config.enable_sentiment_analysis is True
        assert config.enable_online_learning is True
        assert config.enable_ensemble_optimization is True
        assert config.min_confidence_threshold == 0.65
        assert config.target_accuracy == 0.75
        assert config.target_latency_ms == 50.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EnhancedTradingConfig(
            enable_regime_detection=False,
            min_confidence_threshold=0.7,
            target_accuracy=0.8
        )

        assert config.enable_regime_detection is False
        assert config.min_confidence_threshold == 0.7
        assert config.target_accuracy == 0.8


class TestTradingDecision:
    """Test suite for Trading Decision."""

    def test_trading_decision_creation(self):
        """Test trading decision creation."""
        decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=45200.0,
            stop_loss=44300.0,
            take_profit=46700.0,
            position_size=0.05,
            reasoning={'test': 'data'},
            regime='trending',
            sentiment_score=0.6,
            model_weights={'lstm': 0.6, 'transformer': 0.4},
            prediction_probability=0.75
        )

        assert decision.signal == TradingSignal.BUY
        assert decision.confidence == 0.75
        assert decision.entry_price == 45200.0
        assert decision.stop_loss == 44300.0
        assert decision.take_profit == 46700.0
        assert decision.position_size == 0.05
        assert decision.regime == 'trending'
        assert decision.sentiment_score == 0.6
        assert isinstance(decision.timestamp, datetime)


class TestEnhancedTradingSystem:
    """Test suite for Enhanced Trading System."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return EnhancedTradingConfig(
            enable_regime_detection=True,
            enable_sentiment_analysis=True,
            enable_online_learning=True,
            enable_ensemble_optimization=True,
            min_confidence_threshold=0.6
        )

    @patch('decision_engine.enhanced_trading_system.get_market_regime_detector')
    @patch('decision_engine.enhanced_trading_system.get_sentiment_analyzer')
    @patch('decision_engine.enhanced_trading_system.get_enhanced_feature_engineer')
    @patch('decision_engine.enhanced_trading_system.get_online_learning_adapter')
    @patch('decision_engine.enhanced_trading_system.get_optimized_ensemble')
    @patch('decision_engine.enhanced_trading_system.get_regime_adaptive_ensemble')
    def test_system_initialization(
        self, mock_regime_adaptive, mock_optimized, mock_adapter,
        mock_feature_engineer, mock_sentiment, mock_regime, config
    ):
        """Test system initialization with mocked components."""
        system = EnhancedSMCTradingSystem(config)

        assert system.config == config
        assert system.regime_detector is not None
        assert system.sentiment_analyzer is not None
        assert system.feature_engineer is not None
        assert system.online_adapter is not None
        assert system.optimized_ensemble is not None
        assert system.regime_adaptive is not None

    def test_safe_signal_generation(self, config):
        """Test safe signal generation for fallback cases."""
        system = EnhancedSMCTradingSystem(config)
        market_data = {
            'symbol': 'BTC/USDT',
            'open': 45000.0,
            'high': 45500.0,
            'low': 44500.0,
            'close': 45200.0,
            'volume': 1000.0
        }

        safe_signal = system._get_safe_signal(market_data)

        assert safe_signal.signal == TradingSignal.HOLD
        assert safe_signal.confidence == 0.5
        assert safe_signal.entry_price == 45200.0
        assert 'fallback' in safe_signal.reasoning

    def test_risk_management_long_position(self, config):
        """Test risk management for long positions."""
        system = EnhancedSMCTradingSystem(config)

        base_decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            reasoning={'test': 'data'},
            regime='trending',
            sentiment_score=0.6,
            model_weights={'lstm': 0.4, 'transformer': 0.6},
            prediction_probability=0.75
        )

        market_data = {
            'close': 45200.0,
            'atr': 900.0
        }

        risk_adjusted = system._apply_risk_management(base_decision, market_data)

        assert risk_adjusted.entry_price == 45200.0
        assert risk_adjusted.stop_loss < risk_adjusted.entry_price  # Below entry for long
        assert risk_adjusted.take_profit > risk_adjusted.entry_price  # Above entry for long
        assert risk_adjusted.position_size > 0.0
        assert 'risk_management' in risk_adjusted.reasoning

    def test_risk_management_short_position(self, config):
        """Test risk management for short positions."""
        system = EnhancedSMCTradingSystem(config)

        base_decision = TradingDecision(
            signal=TradingSignal.SELL,
            confidence=0.75,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            reasoning={'test': 'data'},
            regime='trending',
            sentiment_score=-0.6,
            model_weights={'lstm': 0.4, 'transformer': 0.6},
            prediction_probability=0.25
        )

        market_data = {
            'close': 45200.0,
            'atr': 900.0
        }

        risk_adjusted = system._apply_risk_management(base_decision, market_data)

        assert risk_adjusted.entry_price == 45200.0
        assert risk_adjusted.stop_loss > risk_adjusted.entry_price  # Above entry for short
        assert risk_adjusted.take_profit < risk_adjusted.entry_price  # Below entry for short

    def test_confidence_threshold_filtering(self, config):
        """Test confidence threshold filtering."""
        system = EnhancedSMCTradingSystem(config)

        low_confidence_decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.4,  # Below threshold
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            reasoning={},
            regime='trending',
            sentiment_score=0.0,
            model_weights={},
            prediction_probability=0.4
        )

        market_data = {'close': 45200.0}

        filtered_decision = system._apply_risk_management(
            low_confidence_decision, market_data
        )

        assert filtered_decision.signal == TradingSignal.HOLD
        assert 'Below confidence threshold' in filtered_decision.reasoning['risk_adjustment']

    def test_system_performance_calculation(self, config):
        """Test system performance metrics calculation."""
        system = EnhancedSMCTradingSystem(config)

        # Add some performance history
        system.performance_history = [
            {
                'timestamp': datetime.now(),
                'signal_correct': True,
                'profit_loss': 0.05,
                'confidence': 0.75,
                'regime': 'trending',
                'sentiment_score': 0.6
            },
            {
                'timestamp': datetime.now(),
                'signal_correct': False,
                'profit_loss': -0.02,
                'confidence': 0.65,
                'regime': 'ranging',
                'sentiment_score': -0.2
            }
        ]

        performance = system.get_system_performance()

        assert isinstance(performance, SystemPerformanceMetrics)
        assert performance.overall_accuracy == 0.5  # 1 correct out of 2
        assert 'trending' in performance.regime_accuracy
        assert 'ranging' in performance.regime_accuracy
        assert performance.regime_accuracy['trending'] == 1.0
        assert performance.regime_accuracy['ranging'] == 0.0

    def test_empty_system_performance(self, config):
        """Test system performance with no history."""
        system = EnhancedSMCTradingSystem(config)

        performance = system.get_system_performance()

        assert isinstance(performance, SystemPerformanceMetrics)
        assert performance.overall_accuracy == 0.0
        assert performance.adaptation_frequency == 0
        assert performance.last_optimization is None

    def test_system_status(self, config):
        """Test system status reporting."""
        system = EnhancedSMCTradingSystem(config)

        status = system.get_system_status()

        assert isinstance(status, dict)
        assert 'initialized' in status
        assert 'config' in status
        assert 'components' in status
        assert 'performance' in status
        assert 'statistics' in status

    def test_prediction_tracking(self, config):
        """Test prediction tracking functionality."""
        system = EnhancedSMCTradingSystem(config)

        decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=45200.0,
            stop_loss=44300.0,
            take_profit=46700.0,
            position_size=0.05,
            reasoning={},
            regime='trending',
            sentiment_score=0.6,
            model_weights={'lstm': 0.5, 'transformer': 0.5},
            prediction_probability=0.75
        )

        # Update tracking
        system._update_prediction_tracking(decision, 35.0)

        assert len(system.recent_predictions) == 1
        tracking_data = system.recent_predictions[0]
        assert tracking_data['signal'] == 'buy'
        assert tracking_data['confidence'] == 0.75
        assert tracking_data['prediction_latency_ms'] == 35.0
        assert tracking_data['regime'] == 'trending'

    def test_outcome_update_profitable(self, config):
        """Test updating with profitable trade outcomes."""
        system = EnhancedSMCTradingSystem(config)

        decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=45200.0,
            stop_loss=44300.0,
            take_profit=46700.0,
            position_size=0.05,
            reasoning={},
            regime='trending',
            sentiment_score=0.6,
            model_weights={'lstm': 0.5, 'transformer': 0.5},
            prediction_probability=0.75
        )

        # Update with profitable outcome
        system.update_with_actual_outcome(decision, 46000.0)

        assert len(system.performance_history) == 1
        outcome = system.performance_history[0]
        assert outcome['signal_correct'] is True  # Profitable trade
        assert outcome['profit_loss'] > 0

    def test_outcome_update_loss(self, config):
        """Test updating with losing trade outcomes."""
        system = EnhancedSMCTradingSystem(config)

        decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=45200.0,
            stop_loss=44300.0,
            take_profit=46700.0,
            position_size=0.05,
            reasoning={},
            regime='trending',
            sentiment_score=0.6,
            model_weights={'lstm': 0.5, 'transformer': 0.5},
            prediction_probability=0.75
        )

        # Update with losing outcome
        system.update_with_actual_outcome(decision, 44500.0)

        assert len(system.performance_history) == 1
        outcome = system.performance_history[0]
        assert outcome['signal_correct'] is False  # Losing trade
        assert outcome['profit_loss'] < 0

    def test_outcome_update_short_position(self, config):
        """Test updating with short position outcomes."""
        system = EnhancedSMCTradingSystem(config)

        decision = TradingDecision(
            signal=TradingSignal.SELL,
            confidence=0.75,
            entry_price=45200.0,
            stop_loss=46100.0,
            take_profit=43700.0,
            position_size=0.05,
            reasoning={},
            regime='trending',
            sentiment_score=-0.6,
            model_weights={'lstm': 0.5, 'transformer': 0.5},
            prediction_probability=0.25
        )

        # Update with profitable short outcome (price goes down)
        system.update_with_actual_outcome(decision, 44000.0)

        assert len(system.performance_history) == 1
        outcome = system.performance_history[0]
        assert outcome['signal_correct'] is True  # Profitable short trade
        assert outcome['profit_loss'] > 0


class TestFactoryFunctions:
    """Test suite for factory functions."""

    @patch('decision_engine.optimized_ensemble.get_ensemble')
    @patch('decision_engine.optimized_ensemble.get_regime_adaptive_ensemble')
    def test_create_optimized_ensemble(self, mock_regime, mock_base):
        """Test optimized ensemble factory function."""
        config = EnsembleOptimizationConfig()
        ensemble = create_optimized_ensemble(mock_base, mock_regime, config)

        assert isinstance(ensemble, OptimizedEnsemble)
        assert ensemble.config == config

    def test_create_enhanced_trading_system(self):
        """Test enhanced trading system factory function."""
        config = EnhancedTradingConfig()
        system = create_enhanced_trading_system(config)

        assert isinstance(system, EnhancedSMCTradingSystem)
        assert system.config == config


class TestPerformanceValidation:
    """Test suite for performance validation and benchmarks."""

    def test_ensemble_optimization_performance(self):
        """Test ensemble optimization performance benchmarks."""
        config = EnsembleOptimizationConfig(
            optimization_strategy=OptimizationStrategy.ADAPTIVE,
            optimization_window=20
        )

        mock_ensemble = Mock()
        mock_ensemble.models = {'model1': Mock(), 'model2': Mock()}
        mock_regime = Mock()

        ensemble = OptimizedEnsemble(mock_ensemble, mock_regime, config)

        # Performance test
        start_time = time.time()

        # Generate test data
        features_batch = [{'features': np.random.randn(5)} for _ in range(20)]
        true_labels = np.random.randint(0, 2, size=(20,))

        # Initialize some performance data
        for model_id in ensemble.current_weights.keys():
            for _ in range(15):
                ensemble.model_performances[model_id].accuracy_history.append(
                    np.random.uniform(0.5, 0.8)
                )

        # Optimize
        ensemble.optimize_weights(features_batch, true_labels)

        optimization_time = time.time() - start_time

        # Should complete optimization within reasonable time
        assert optimization_time < 5.0  # 5 seconds max

    def test_system_latency_validation(self):
        """Test system latency requirements."""
        config = EnhancedTradingConfig(
            target_latency_ms=50.0,
            max_adaptation_latency_ms=100.0
        )

        system = EnhancedSMCTradingSystem(config)

        # Test safe signal generation latency
        start_time = time.time()
        market_data = {'close': 45200.0}
        system._get_safe_signal(market_data)
        safe_signal_time = (time.time() - start_time) * 1000

        # Should meet latency requirements
        assert safe_signal_time < config.target_latency_ms

        # Test risk management latency
        base_decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.75,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            reasoning={},
            regime='trending',
            sentiment_score=0.6,
            model_weights={},
            prediction_probability=0.75
        )

        start_time = time.time()
        system._apply_risk_management(base_decision, market_data)
        risk_management_time = (time.time() - start_time) * 1000

        assert risk_management_time < config.target_latency_ms


# Test configuration and execution
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])