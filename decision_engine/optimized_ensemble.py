#!/usr/bin/env python3
"""
Optimized Model Ensemble for SMC Trading System

Implements dynamic ensemble optimization with:
- Performance-based model selection
- Dynamic weight adjustment
- Meta-learning for ensemble optimization
- Adaptive model combination
- Real-time performance tracking
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import json
try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

try:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.preprocessing import MinMaxScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
import numba as nb
import warnings
warnings.filterwarnings('ignore')

# Import existing ensemble components
from .model_ensemble import (
    ModelEnsemble,
    EnsemblePrediction,
    ModelState,
    ModelMetrics,
    get_ensemble
)

# Import regime-adaptive components
from .regime_adaptive_ensemble import RegimeAdaptiveEnsemble

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies for ensemble weights."""
    GRID_SEARCH = "grid_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    REINFORCEMENT = "reinforcement"
    ADAPTIVE = "adaptive"


class PerformanceMetric(Enum):
    """Performance metrics for optimization."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    REGIME_ADAPTATION = "regime_adaptation"


@dataclass
class EnsembleOptimizationConfig:
    """Configuration for ensemble optimization."""
    optimization_strategy: OptimizationStrategy = OptimizationStrategy.BAYESIAN
    objective_metrics: List[PerformanceMetric] = field(default_factory=lambda: [
        PerformanceMetric.ACCURACY,
        PerformanceMetric.F1_SCORE,
        PerformanceMetric.PROFIT_FACTOR
    ])
    optimization_window: int = 100  # samples for optimization
    validation_window: int = 50  # samples for validation
    rebalance_frequency: int = 20  # epochs between rebalancing
    min_model_weight: float = 0.05
    max_model_weight: float = 0.60
    performance_decay: float = 0.95  # decay factor for historical performance
    adaptive_threshold: float = 0.02  # threshold for adaptive rebalancing
    ensemble_diversity_bonus: float = 0.1  # bonus for model diversity


@dataclass
class ModelPerformanceHistory:
    """Historical performance tracking for each model."""
    model_id: str
    accuracy_history: deque = field(default_factory=lambda: deque(maxlen=200))
    precision_history: deque = field(default_factory=lambda: deque(maxlen=200))
    recall_history: deque = field(default_factory=lambda: deque(maxlen=200))
    f1_history: deque = field(default_factory=lambda: deque(maxlen=200))
    profit_history: deque = field(default_factory=lambda: deque(maxlen=200))
    regime_performance: Dict[str, deque] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

    def get_recent_metrics(self, window: int = 20) -> Dict[str, float]:
        """Get recent performance metrics."""
        recent_window = min(window, len(self.accuracy_history))

        if recent_window == 0:
            return {}

        return {
            'accuracy': np.mean(list(self.accuracy_history)[-recent_window:]),
            'precision': np.mean(list(self.precision_history)[-recent_window:]),
            'recall': np.mean(list(self.recall_history)[-recent_window:]),
            'f1_score': np.mean(list(self.f1_history)[-recent_window:]),
            'profit_factor': np.mean(list(self.profit_history)[-recent_window:])
        }

    def get_regime_performance(self, regime: str, window: int = 20) -> float:
        """Get regime-specific performance."""
        if regime not in self.regime_performance:
            return 0.0

        regime_hist = self.regime_performance[regime]
        recent_window = min(window, len(regime_hist))

        if recent_window == 0:
            return 0.0

        return np.mean(list(regime_hist)[-recent_window:])


@nb.jit(nopython=True)
def calculate_ensemble_diversity(predictions: np.ndarray) -> float:
    """Calculate ensemble diversity using correlation matrix."""
    if predictions.shape[1] < 2:
        return 0.0

    # Calculate correlation matrix
    corr_matrix = np.corrcoef(predictions.T)

    # Get upper triangle (excluding diagonal)
    upper_triangle = corr_matrix[np.triu_indices_from(corr_matrix, k=1)]

    # Diversity = 1 - average correlation
    avg_correlation = np.mean(np.abs(upper_triangle))
    return 1.0 - avg_correlation


class OptimizedEnsemble:
    """
    Optimized ensemble with dynamic weight adjustment and meta-learning.
    """

    def __init__(
        self,
        base_ensemble: ModelEnsemble,
        regime_adaptive: RegimeAdaptiveEnsemble,
        config: EnsembleOptimizationConfig
    ):
        self.base_ensemble = base_ensemble
        self.regime_adaptive = regime_adaptive
        self.config = config
        self.optimization_history: List[Dict] = []
        self.model_performances: Dict[str, ModelPerformanceHistory] = {}
        self.current_weights: Dict[str, float] = {}
        self.performance_predictions: Dict[str, float] = {}
        self.diversity_metrics: deque = deque(maxlen=50)
        self.optimization_count = 0
        self.last_optimization = None

        # Initialize performance tracking
        self._initialize_performance_tracking()

        # Setup meta-learner
        self._setup_meta_learner()

        logger.info("Initialized OptimizedEnsemble with dynamic optimization")

    def _initialize_performance_tracking(self):
        """Initialize performance tracking for all models."""
        # Get model IDs from base ensemble
        if hasattr(self.base_ensemble, 'models'):
            model_ids = list(self.base_ensemble.models.keys())
        else:
            model_ids = ['lstm', 'transformer', 'ppo', 'random_forest', 'xgboost']

        # Initialize performance tracking
        for model_id in model_ids:
            self.model_performances[model_id] = ModelPerformanceHistory(model_id=model_id)

            # Initialize with equal weights
            self.current_weights[model_id] = 1.0 / len(model_ids)

    def _setup_meta_learner(self):
        """Setup meta-learner for weight optimization."""
        # Simple weight normalization
        if HAS_SKLEARN:
            self.weight_scaler = MinMaxScaler(feature_range=(self.config.min_model_weight, self.config.max_model_weight))
        else:
            self.weight_scaler = None

    def update_model_performance(
        self,
        predictions: Dict[str, np.ndarray],
        true_labels: np.ndarray,
        regime: Optional[str] = None,
        profits: Optional[np.ndarray] = None
    ):
        """Update performance metrics for all models."""
        for model_id, pred in predictions.items():
            if model_id not in self.model_performances:
                continue

            perf_history = self.model_performances[model_id]

            # Convert predictions to binary for classification metrics
            pred_binary = (pred > 0.5).astype(int)
            true_binary = (true_labels > 0.5).astype(int)

            # Calculate metrics
            if HAS_SKLEARN:
                accuracy = accuracy_score(true_binary, pred_binary)
                precision = precision_score(true_binary, pred_binary, zero_division=0)
                recall = recall_score(true_binary, pred_binary, zero_division=0)
                f1 = f1_score(true_binary, pred_binary, zero_division=0)
            else:
                # Fallback calculations without sklearn
                accuracy = np.mean(pred_binary == true_binary)
                precision = self._calculate_precision(true_binary, pred_binary)
                recall = self._calculate_recall(true_binary, pred_binary)
                f1 = self._calculate_f1_score(precision, recall)

            # Calculate profit factor if provided
            profit_factor = 0.0
            if profits is not None:
                winning_profits = profits[pred_binary == 1]
                losing_profits = profits[pred_binary == 0]

                if len(losing_profits) > 0:
                    profit_factor = abs(np.sum(winning_profits)) / abs(np.sum(losing_profits))
                elif len(winning_profits) > 0:
                    profit_factor = 2.0  # Perfect performance

            # Update performance history
            perf_history.accuracy_history.append(accuracy)
            perf_history.precision_history.append(precision)
            perf_history.recall_history.append(recall)
            perf_history.f1_history.append(f1)
            perf_history.profit_history.append(profit_factor)

            # Update regime-specific performance
            if regime:
                if regime not in perf_history.regime_performance:
                    perf_history.regime_performance[regime] = deque(maxlen=100)
                perf_history.regime_performance[regime].append(f1)

            perf_history.last_updated = datetime.now()

    def _calculate_precision(self, y_true, y_pred):
        """Calculate precision without sklearn."""
        true_positives = np.sum((y_true == 1) & (y_pred == 1))
        predicted_positives = np.sum(y_pred == 1)

        if predicted_positives == 0:
            return 0.0
        return true_positives / predicted_positives

    def _calculate_recall(self, y_true, y_pred):
        """Calculate recall without sklearn."""
        true_positives = np.sum((y_true == 1) & (y_pred == 1))
        actual_positives = np.sum(y_true == 1)

        if actual_positives == 0:
            return 0.0
        return true_positives / actual_positives

    def _calculate_f1_score(self, precision, recall):
        """Calculate F1 score from precision and recall."""
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def predict(
        self,
        features: Dict[str, np.ndarray],
        regime: Optional[str] = None,
        return_weights: bool = False
    ) -> Tuple[np.ndarray, Optional[Dict[str, float]]]:
        """Make optimized ensemble prediction."""

        # Get base predictions
        base_predictions = {}
        for model_id in self.current_weights.keys():
            if hasattr(self.base_ensemble, 'predict_single'):
                pred = self.base_ensemble.predict_single(model_id, features)
            else:
                # Fallback to regime-adaptive ensemble
                pred = self.regime_adaptive.predict(features, regime)

            base_predictions[model_id] = pred

        # Get predictions array for diversity calculation
        pred_array = np.column_stack(list(base_predictions.values()))

        # Calculate ensemble diversity
        diversity = calculate_ensemble_diversity(pred_array)
        self.diversity_metrics.append(diversity)

        # Apply optimized weights
        weighted_prediction = np.zeros_like(pred_array[:, 0])
        for i, (model_id, pred) in enumerate(base_predictions.items()):
            weight = self.current_weights[model_id]
            weighted_prediction += weight * pred

        # Apply diversity bonus to weights
        if diversity > 0.5:  # Good diversity
            diversity_adjustment = 1.0 + self.config.ensemble_diversity_bonus * diversity
        else:  # Poor diversity, favor better models
            diversity_adjustment = 1.0 - (1.0 - diversity) * 0.2

        weighted_prediction *= diversity_adjustment

        if return_weights:
            return weighted_prediction, self.current_weights.copy()

        return weighted_prediction, None

    def optimize_weights(
        self,
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Optimize ensemble weights using configured strategy."""

        logger.info(f"Starting ensemble weight optimization (strategy: {self.config.optimization_strategy.value})")

        if self.config.optimization_strategy == OptimizationStrategy.BAYESIAN:
            optimal_weights = self._bayesian_optimization(features_batch, true_labels_batch, regimes_batch, profits_batch)
        elif self.config.optimization_strategy == OptimizationStrategy.ADAPTIVE:
            optimal_weights = self._adaptive_optimization(features_batch, true_labels_batch, regimes_batch, profits_batch)
        elif self.config.optimization_strategy == OptimizationStrategy.GRID_SEARCH:
            optimal_weights = self._grid_search_optimization(features_batch, true_labels_batch, regimes_batch, profits_batch)
        else:
            optimal_weights = self._performance_based_optimization(features_batch, true_labels_batch, regimes_batch, profits_batch)

        # Update current weights
        self.current_weights = optimal_weights
        self.last_optimization = datetime.now()
        self.optimization_count += 1

        # Log optimization results
        logger.info(f"Optimized ensemble weights: {optimal_weights}")

        return optimal_weights

    def _bayesian_optimization(
        self,
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Bayesian optimization using Optuna."""

        if not HAS_OPTUNA:
            logger.warning("Optuna not available, falling back to adaptive optimization")
            return self._adaptive_optimization(features_batch, true_labels_batch, regimes_batch, profits_batch)

        def objective(trial):
            # Suggest weights for each model
            weights = {}
            model_ids = list(self.current_weights.keys())

            for i, model_id in enumerate(model_ids):
                weights[model_id] = trial.suggest_float(f'weight_{model_id}', 0.0, 1.0)

            # Normalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}

            # Evaluate weights
            score = self._evaluate_weights(weights, features_batch, true_labels_batch, regimes_batch, profits_batch)

            return score

        # Create study
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=50)

        # Get best weights
        best_params = study.best_params
        best_weights = {}
        model_ids = list(self.current_weights.keys())

        for model_id in model_ids:
            best_weights[model_id] = best_params.get(f'weight_{model_id}', 0.0)

        # Normalize best weights
        total_weight = sum(best_weights.values())
        if total_weight > 0:
            best_weights = {k: v / total_weight for k, v in best_weights.items()}

        return best_weights

    def _adaptive_optimization(
        self,
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Adaptive optimization based on recent performance trends."""

        new_weights = {}

        for model_id in self.current_weights.keys():
            perf_history = self.model_performances[model_id]

            # Get recent performance
            recent_metrics = perf_history.get_recent_metrics(self.config.optimization_window // 2)

            if not recent_metrics:
                # No performance history, keep current weight
                new_weights[model_id] = self.current_weights[model_id]
                continue

            # Calculate adaptive score
            score = 0.0
            metric_weights = {
                'accuracy': 0.3,
                'precision': 0.2,
                'recall': 0.2,
                'f1_score': 0.2,
                'profit_factor': 0.1
            }

            for metric, weight in metric_weights.items():
                if metric in recent_metrics:
                    score += recent_metrics[metric] * weight

            # Apply regime-specific bonus
            if regimes_batch:
                regime_counts = {}
                for regime in regimes_batch:
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1

                regime_bonus = 0.0
                total_samples = len(regimes_batch)

                for regime, count in regime_counts.items():
                    regime_weight = count / total_samples
                    regime_perf = perf_history.get_regime_performance(regime)
                    regime_bonus += regime_weight * regime_perf * 0.1

                score += regime_bonus

            # Convert score to weight adjustment
            current_weight = self.current_weights[model_id]

            # Adaptive adjustment
            if score > 0.6:  # Good performance
                adjustment = 1.0 + (score - 0.6) * 0.5
            elif score < 0.4:  # Poor performance
                adjustment = 1.0 - (0.4 - score) * 0.5
            else:
                adjustment = 1.0

            new_weight = current_weight * adjustment

            # Apply constraints
            new_weight = max(self.config.min_model_weight,
                           min(self.config.max_model_weight, new_weight))

            new_weights[model_id] = new_weight

        # Normalize weights
        total_weight = sum(new_weights.values())
        if total_weight > 0:
            new_weights = {k: v / total_weight for k, v in new_weights.items()}

        return new_weights

    def _grid_search_optimization(
        self,
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Grid search optimization for weight combinations."""

        model_ids = list(self.current_weights.keys())
        n_models = len(model_ids)

        # Generate weight combinations (simple grid)
        weight_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        best_score = -float('inf')
        best_weights = self.current_weights.copy()

        # Simple iterative search (for computational efficiency)
        for i in range(20):  # Limited iterations for speed
            weights = {}

            for model_id in model_ids:
                weights[model_id] = np.random.choice(weight_values)

            # Normalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}

            # Evaluate weights
            score = self._evaluate_weights(weights, features_batch, true_labels_batch, regimes_batch, profits_batch)

            if score > best_score:
                best_score = score
                best_weights = weights

        return best_weights

    def _performance_based_optimization(
        self,
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Performance-based optimization using historical metrics."""

        weights = {}

        for model_id in self.current_weights.keys():
            perf_history = self.model_performances[model_id]
            recent_metrics = perf_history.get_recent_metrics(self.config.optimization_window)

            if not recent_metrics:
                weights[model_id] = 1.0 / len(self.current_weights)
                continue

            # Calculate composite performance score
            score = 0.0

            # Accuracy and F1 are most important
            if 'accuracy' in recent_metrics:
                score += recent_metrics['accuracy'] * 0.4

            if 'f1_score' in recent_metrics:
                score += recent_metrics['f1_score'] * 0.3

            # Profit factor is secondary
            if 'profit_factor' in recent_metrics and recent_metrics['profit_factor'] > 0:
                # Log transform profit factor to reduce extreme values
                profit_score = min(np.log(recent_metrics['profit_factor'] + 1) / 2.0, 1.0)
                score += profit_score * 0.2

            # Add regime-specific performance
            if regimes_batch:
                most_common_regime = max(set(regimes_batch), key=regimes_batch.count)
                regime_perf = perf_history.get_regime_performance(most_common_regime)
                score += regime_perf * 0.1

            weights[model_id] = max(score, 0.01)  # Minimum score

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def _evaluate_weights(
        self,
        weights: Dict[str, float],
        features_batch: List[Dict[str, np.ndarray]],
        true_labels_batch: np.ndarray,
        regimes_batch: Optional[List[str]] = None,
        profits_batch: Optional[np.ndarray] = None
    ) -> float:
        """Evaluate weight configuration on validation data."""

        predictions = []

        for features in features_batch:
            # Get weighted prediction
            pred, _ = self._predict_with_weights(features, weights)
            predictions.append(pred)

        predictions = np.array(predictions)

        # Convert to binary for evaluation
        pred_binary = (predictions > 0.5).astype(int)
        true_binary = (true_labels_batch > 0.5).astype(int)

        # Calculate evaluation metrics
        if HAS_SKLEARN:
            accuracy = accuracy_score(true_binary, pred_binary)
            f1 = f1_score(true_binary, pred_binary, zero_division=0)
        else:
            accuracy = np.mean(pred_binary == true_binary)
            precision = self._calculate_precision(true_binary, pred_binary)
            recall = self._calculate_recall(true_binary, pred_binary)
            f1 = self._calculate_f1_score(precision, recall)

        # Calculate profit factor if available
        profit_factor = 1.0
        if profits_batch is not None:
            winning_profits = profits_batch[pred_binary == 1]
            losing_profits = profits_batch[pred_binary == 0]

            if len(losing_profits) > 0:
                profit_factor = abs(np.sum(winning_profits)) / abs(np.sum(losing_profits))
            elif len(winning_profits) > 0:
                profit_factor = 2.0

        # Composite score
        score = accuracy * 0.4 + f1 * 0.4 + min(profit_factor, 2.0) / 2.0 * 0.2

        return score

    def _predict_with_weights(
        self,
        features: Dict[str, np.ndarray],
        weights: Dict[str, float]
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """Predict with specific weights."""

        # Get predictions from each model
        predictions = {}
        for model_id in weights.keys():
            if hasattr(self.base_ensemble, 'predict_single'):
                pred = self.base_ensemble.predict_single(model_id, features)
            else:
                pred = self.regime_adaptive.predict(features)

            predictions[model_id] = pred

        # Apply weights
        weighted_prediction = np.zeros_like(list(predictions.values())[0])
        for model_id, pred in predictions.items():
            weighted_prediction += weights[model_id] * pred

        return weighted_prediction, weights

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""

        report = {
            'optimization_count': self.optimization_count,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'current_weights': self.current_weights,
            'optimization_strategy': self.config.optimization_strategy.value,
            'model_performances': {},
            'ensemble_diversity': {
                'current': np.mean(list(self.diversity_metrics)) if self.diversity_metrics else 0.0,
                'trend': list(self.diversity_metrics)[-10:] if len(self.diversity_metrics) >= 10 else list(self.diversity_metrics)
            },
            'recent_optimizations': self.optimization_history[-5:] if self.optimization_history else []
        }

        # Add model performance summaries
        for model_id, perf_history in self.model_performances.items():
            recent_metrics = perf_history.get_recent_metrics(20)
            report['model_performances'][model_id] = {
                'recent_metrics': recent_metrics,
                'regime_performances': {regime: float(np.mean(list(perf)[-10:]))
                                      for regime, perf in perf_history.regime_performance.items()
                                      if len(perf) >= 10},
                'last_updated': perf_history.last_updated.isoformat()
            }

        return report

    def should_rebalance(self, current_performance: Dict[str, float]) -> bool:
        """Determine if ensemble should be rebalanced."""

        # Check if enough time has passed since last optimization
        if self.last_optimization:
            time_since_opt = datetime.now() - self.last_optimization
            if time_since_opt < timedelta(minutes=self.config.rebalance_frequency):
                return False

        # Check performance degradation
        if not self.optimization_history:
            return True

        last_optimization_score = self.optimization_history[-1].get('score', 0.0)
        current_score = np.mean(list(current_performance.values()))

        performance_drop = last_optimization_score - current_score

        return performance_drop > self.config.adaptive_threshold


# Factory function for optimized ensemble
def create_optimized_ensemble(
    base_ensemble: ModelEnsemble,
    regime_adaptive: RegimeAdaptiveEnsemble,
    config: Optional[EnsembleOptimizationConfig] = None
) -> OptimizedEnsemble:
    """Factory function to create optimized ensemble."""

    if config is None:
        config = EnsembleOptimizationConfig()

    return OptimizedEnsemble(base_ensemble, regime_adaptive, config)


# Singleton instance
_optimized_ensemble = None


def get_optimized_ensemble() -> OptimizedEnsemble:
    """Get global optimized ensemble instance."""
    global _optimized_ensemble

    if _optimized_ensemble is None:
        # Initialize with default components
        base_ensemble = get_ensemble()
        regime_adaptive = RegimeAdaptiveEnsemble(base_ensemble, {})
        config = EnsembleOptimizationConfig()

        _optimized_ensemble = create_optimized_ensemble(base_ensemble, regime_adaptive, config)

    return _optimized_ensemble


if __name__ == "__main__":
    # Test the optimized ensemble
    ensemble = get_optimized_ensemble()

    # Generate test data
    features_batch = [
        {'smc_features': np.random.randn(16), 'technical_features': np.random.randn(8)}
        for _ in range(50)
    ]
    true_labels_batch = np.random.randint(0, 2, size=(50,))
    regimes_batch = ['trending' if i % 2 == 0 else 'ranging' for i in range(50)]

    # Test optimization
    print("Testing ensemble optimization...")

    # Update model performance with dummy data
    dummy_predictions = {
        'lstm': np.random.rand(len(true_labels_batch)),
        'transformer': np.random.rand(len(true_labels_batch)),
        'ppo': np.random.rand(len(true_labels_batch)),
        'random_forest': np.random.rand(len(true_labels_batch)),
        'xgboost': np.random.rand(len(true_labels_batch))
    }

    ensemble.update_model_performance(dummy_predictions, true_labels_batch, regimes_batch)

    # Optimize weights
    optimal_weights = ensemble.optimize_weights(features_batch, true_labels_batch, regimes_batch)

    print(f"Optimal weights: {optimal_weights}")

    # Get optimization report
    report = ensemble.get_optimization_report()
    print(f"Optimization report: {report}")