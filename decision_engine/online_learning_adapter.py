"""
Online Learning & Adaptation System

This module implements online learning capabilities with concept drift detection,
automatic model retraining, and continuous model improvement. It enables the ML system
to adapt to changing market conditions and maintain high accuracy over time.

Key Features:
- Real-time model performance monitoring
- Concept drift detection using multiple methods
- Automatic retraining triggers and scheduling
- Incremental learning algorithms
- Model versioning and rollback capabilities
- Performance-based model selection
- Adaptive ensemble weight adjustment
"""

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json
import pickle
import os
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from .model_ensemble import LSTMPredictor, TransformerPredictor
from .regime_adaptive_ensemble import RegimeAdaptiveEnsemble, RegimeSpecificModel
from .enhanced_feature_engineer import EnhancedFeatureEngineer, FeatureSet

logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """Record of a prediction and its outcome."""
    timestamp: datetime
    model_name: str
    regime: str
    predicted_action: str
    actual_action: str
    confidence: float
    features_used: int
    correct: bool = False
    processing_time_ms: float = 0.0


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for a model."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    prediction_count: int = 0
    correct_predictions: int = 0
    avg_confidence: float = 0.0
    avg_processing_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    recent_accuracy_trend: float = 0.0
    performance_variance: float = 0.0


@dataclass
class DriftDetectionResult:
    """Result of concept drift detection."""
    drift_detected: bool
    drift_type: str  # 'sudden', 'gradual', 'incremental', 'recurring'
    drift_score: float  # 0-1, higher = more certain drift
    affected_models: List[str]
    timestamp: datetime
    recommended_action: str
    statistical_significance: float = 0.0


class ConceptDriftDetector:
    """
    Detects concept drift using multiple statistical methods.
    """
    
    def __init__(self, window_size: int = 100, significance_threshold: float = 0.05):
        self.window_size = window_size
        self.significance_threshold = significance_threshold
        
        # Performance tracking windows
        self.performance_history = deque(maxlen=window_size * 2)
        self.accuracy_window = deque(maxlen=window_size)
        
        # Drift detection methods
        self.drift_methods = ['page_hinkley', 'adwin', 'ddm', 'statistical_test']
        
        # Thresholds for different methods
        self.thresholds = {
            'page_hinkley': 0.5,
            'adwin': 0.3,
            'ddm': 0.2,
            'statistical_test': 0.05
        }
        
        logger.info("ConceptDriftDetector initialized")
    
    def add_prediction_result(self, prediction_record: PredictionRecord):
        """Add a prediction result to the tracking history."""
        self.performance_history.append(prediction_record)
        self.accuracy_window.append(1.0 if prediction_record.correct else 0.0)
        
        # Clean up old records
        if len(self.performance_history) > self.window_size * 2:
            while len(self.performance_history) > self.window_size:
                self.performance_history.popleft()
    
    def detect_drift(self, model_name: str) -> Optional[DriftDetectionResult]:
        """Detect concept drift for a specific model."""
        try:
            if len(self.accuracy_window) < self.window_size:
                return None
            
            # Get model-specific predictions
            model_predictions = [p for p in self.performance_history if p.model_name == model_name]
            
            if len(model_predictions) < self.window_size:
                return None
            
            # Run different drift detection methods
            drift_results = []
            
            # Page-Hinkley test
            ph_result = self._page_hinkley_test(model_predictions)
            if ph_result:
                drift_results.append(ph_result)
            
            # ADWIN test
            adwin_result = self._adwin_test(model_predictions)
            if adwin_result:
                drift_results.append(adwin_result)
            
            # DDM (Drift Detection Method)
            ddm_result = self._ddm_test(model_predictions)
            if ddm_result:
                drift_results.append(ddm_result)
            
            # Statistical test
            stat_result = self._statistical_test(model_predictions)
            if stat_result:
                drift_results.append(stat_result)
            
            # Combine results
            if drift_results:
                return self._combine_drift_results(drift_results, model_name)
            
            return None
            
        except Exception as e:
            logger.error(f"Drift detection failed for {model_name}: {str(e)}")
            return None
    
    def _page_hinkley_test(self, predictions: List[PredictionRecord]) -> Optional[DriftDetectionResult]:
        """Page-Hinkley test for change detection."""
        try:
            # Extract accuracy sequence
            accuracies = [1.0 if p.correct else 0.0 for p in predictions[-self.window_size:]]
            
            # Calculate cumulative sum of deviations
            mean_accuracy = np.mean(accuracies)
            deviations = [acc - mean_accuracy for acc in accuracies]
            
            # Page-Hinkley statistic
            mH = 0
            min_mH = 0
            
            for i, dev in enumerate(deviations):
                mH += dev
                if mH < min_mH:
                    min_mH = mH
            
            # Threshold check
            threshold = self.thresholds['page_hinkley']
            ph_score = abs(min_mH) / len(deviations) if len(deviations) > 0 else 0
            
            if ph_score > threshold:
                return DriftDetectionResult(
                    drift_detected=True,
                    drift_type='sudden',
                    drift_score=ph_score,
                    affected_models=[predictions[0].model_name],
                    timestamp=datetime.now(),
                    recommended_action='retrain',
                    statistical_significance=ph_score
                )
            
        except Exception as e:
            logger.warning(f"Page-Hinkley test failed: {str(e)}")
        
        return None
    
    def _adwin_test(self, predictions: List[PredictionRecord]) -> Optional[DriftDetectionResult]:
        """ADWIN (Adaptive Windowing) test for drift detection."""
        try:
            # Extract accuracy sequence
            accuracies = [1.0 if p.correct else 0.0 for p in predictions[-self.window_size:]]
            
            # ADWIN maintains a window of data and detects changes in variance
            window_variances = []
            
            # Test different window sizes
            for window_size in [20, 50, 100]:
                if len(accuracies) >= window_size:
                    recent_window = accuracies[-window_size:]
                    older_window = accuracies[-2*window_size:-window_size] if len(accuracies) >= 2*window_size else accuracies[:-window_size]
                    
                    if len(older_window) > 0:
                        recent_var = np.var(recent_window)
                        older_var = np.var(older_window)
                        
                        # Relative change in variance
                        if older_var > 0:
                            relative_change = abs(recent_var - older_var) / older_var
                            window_variances.append(relative_change)
            
            if window_variances:
                max_change = max(window_variances)
                threshold = self.thresholds['adwin']
                
                if max_change > threshold:
                    return DriftDetectionResult(
                        drift_detected=True,
                        drift_type='gradual',
                        drift_score=max_change,
                        affected_models=[predictions[0].model_name],
                        timestamp=datetime.now(),
                        recommended_action='update_weights',
                        statistical_significance=max_change
                    )
            
        except Exception as e:
            logger.warning(f"ADWIN test failed: {str(e)}")
        
        return None
    
    def _ddm_test(self, predictions: List[PredictionRecord]) -> Optional[DriftDetectionResult]:
        """DDM (Drift Detection Method) test."""
        try:
            # Extract confidence and correctness
            confidences = [p.confidence for p in predictions[-self.window_size:]]
            correct = [1.0 if p.correct else 0.0 for p in predictions[-self.window_size:]]
            
            # DDM monitors error rate and confidence
            error_rates = []
            
            for i, (conf, corr) in enumerate(zip(confidences, correct)):
                # Error rate = 1 - accuracy
                error_rate = 1 - corr
                
                # DDM statistic
                ddm_stat = error_rate + 2 * conf
                
                # Use threshold for detection
                if ddm_stat > 0.8:  # High error rate with high confidence
                    error_rates.append(ddm_stat)
            
            if error_rates:
                max_ddm = max(error_rates)
                threshold = self.thresholds['ddm']
                
                if max_ddm > threshold:
                    return DriftDetectionResult(
                        drift_detected=True,
                        drift_type='incremental',
                        drift_score=max_ddm,
                        affected_models=[predictions[0].model_name],
                        timestamp=datetime.now(),
                        recommended_action='incremental_update',
                        statistical_significance=max_ddm
                    )
            
        except Exception as e:
            logger.warning(f"DDM test failed: {str(e)}")
        
        return None
    
    def _statistical_test(self, predictions: List[PredictionRecord]) -> Optional[DriftDetectionResult]:
        """Statistical test for drift detection."""
        try:
            # Split predictions into two halves
            mid_point = len(predictions) // 2
            first_half = predictions[:mid_point]
            second_half = predictions[mid_point:mid_point*2]
            
            if len(first_half) < 10 or len(second_half) < 10:
                return None
            
            # Calculate accuracy for each half
            first_accuracy = sum(1 for p in first_half if p.correct) / len(first_half)
            second_accuracy = sum(1 for p in second_half if p.correct) / len(second_half)
            
            # Perform statistical test
            # Using proportion test (z-test for proportions)
            p1 = first_accuracy
            p2 = second_accuracy
            n1 = len(first_half)
            n2 = len(second_half)
            
            # Pooled proportion
            p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
            
            # Standard error
            if p_pool > 0 and p_pool < 1:
                se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
                
                if se > 0:
                    z_score = abs(p1 - p2) / se
                    
                    # Two-tailed test
                    p_value = 2 * (1 - stats.norm.cdf(z_score))
                    
                    if p_value < self.significance_threshold:
                        return DriftDetectionResult(
                            drift_detected=True,
                            drift_type='statistical',
                            drift_score=1 - p_value,
                            affected_models=[predictions[0].model_name],
                            timestamp=datetime.now(),
                            recommended_action='retrain',
                            statistical_significance=1 - p_value
                        )
            
        except Exception as e:
            logger.warning(f"Statistical test failed: {str(e)}")
        
        return None
    
    def _combine_drift_results(self, drift_results: List[DriftDetectionResult], model_name: str) -> DriftDetectionResult:
        """Combine multiple drift detection results."""
        # Weight by drift score
        total_score = sum(r.drift_score for r in drift_results)
        avg_score = total_score / len(drift_results)
        
        # Determine dominant drift type
        drift_types = [r.drift_type for r in drift_results]
        drift_type_counts = {dt: drift_types.count(dt) for dt in set(drift_types)}
        dominant_type = max(drift_type_counts, key=drift_type_counts.get)
        
        # Combine affected models
        all_models = set()
        for result in drift_results:
            all_models.update(result.affected_models)
        
        # Determine recommended action based on drift type
        action_map = {
            'sudden': 'immediate_retrain',
            'gradual': 'update_weights',
            'incremental': 'incremental_update',
            'statistical': 'retrain',
            'recurring': 'ensemble_adjustment'
        }
        
        recommended_action = action_map.get(dominant_type, 'monitor')
        
        return DriftDetectionResult(
            drift_detected=True,
            drift_type=dominant_type,
            drift_score=avg_score,
            affected_models=list(all_models),
            timestamp=datetime.now(),
            recommended_action=recommended_action,
            statistical_significance=avg_score
        )
    
    def get_drift_statistics(self) -> Dict[str, Any]:
        """Get drift detection statistics."""
        return {
            'window_size': self.window_size,
            'significance_threshold': self.significance_threshold,
            'total_predictions': len(self.performance_history),
            'current_window_size': len(self.accuracy_window),
            'methods_available': self.drift_methods,
            'thresholds': self.thresholds
        }


class OnlineLearningAdapter:
    """
    Main online learning adapter that coordinates concept drift detection,
    model retraining, and performance monitoring.
    """
    
    def __init__(self, model_save_path: str = "models/online_learning/"):
        self.model_save_path = model_save_path
        self.drift_detector = ConceptDriftDetector()
        self.feature_engineer = EnhancedFeatureEngineer()
        
        # Model performance tracking
        self.model_performance = {}
        self.performance_history = deque(maxlen=1000)
        
        # Training data storage
        self.training_data_buffer = []
        self.max_buffer_size = 10000
        
        # Online learning configuration
        self.learning_config = {
            'batch_size': 32,
            'learning_rate': 0.001,
            'retrain_threshold': 0.1,  # Accuracy drop threshold
            'min_samples_for_retrain': 1000,
            'retrain_interval_hours': 24,
            'max_retrain_frequency_hours': 6,
            'performance_window_size': 100
        }
        
        # Last retraining times
        self.last_retrain_times = {}
        self.last_drift_detection = None
        
        # Model registry
        self.registered_models = {}
        
        # Ensure model directory exists
        os.makedirs(model_save_path, exist_ok=True)
        
        logger.info("OnlineLearningAdapter initialized")
    
    def register_model(self, model_name: str, model: nn.Module, model_type: str = 'lstm'):
        """Register a model for online learning monitoring."""
        self.registered_models[model_name] = {
            'model': model,
            'model_type': model_type,
            'optimizer': optim.Adam(model.parameters(), lr=self.learning_config['learning_rate']),
            'last_trained': datetime.now(),
            'training_count': 0
        }
        
        # Initialize performance tracking
        if model_name not in self.model_performance:
            self.model_performance[model_name] = ModelPerformanceMetrics(model_name=model_name)
        
        logger.info(f"Model {model_name} registered for online learning")
    
    def add_prediction_result(self, prediction_record: PredictionRecord):
        """Add a prediction result for monitoring and learning."""
        # Add to drift detector
        self.drift_detector.add_prediction_result(prediction_record)
        
        # Update model performance
        if prediction_record.model_name in self.model_performance:
            perf = self.model_performance[prediction_record.model_name]
            perf.prediction_count += 1
            perf.correct_predictions += 1 if prediction_record.correct else 0
            perf.accuracy = perf.correct_predictions / perf.prediction_count
            
            # Update other metrics
            confidences = [p.confidence for p in self.performance_history if p.model_name == prediction_record.model_name]
            if confidences:
                perf.avg_confidence = np.mean(confidences[-self.learning_config['performance_window_size']:])
            
            times = [p.processing_time_ms for p in self.performance_history if p.model_name == prediction_record.model_name]
            if times:
                perf.avg_processing_time = np.mean(times[-self.learning_config['performance_window_size']:])
            
            perf.last_updated = datetime.now()
        
        # Add to training data buffer
        if hasattr(prediction_record, 'features') and prediction_record.features:
            self.training_data_buffer.append(prediction_record)
            if len(self.training_data_buffer) > self.max_buffer_size:
                self.training_data_buffer.pop(0)
        
        # Add to performance history
        self.performance_history.append(prediction_record)
        if len(self.performance_history) > 1000:
            self.performance_history.popleft()
    
    def check_model_performance(self, model_name: str) -> Dict[str, Any]:
        """Check model performance and detect degradation."""
        try:
            if model_name not in self.model_performance:
                return {'status': 'not_found'}
            
            perf = self.model_performance[model_name]
            
            # Calculate recent performance metrics
            recent_predictions = [p for p in self.performance_history 
                                 if p.model_name == model_name and 
                                 (datetime.now() - p.timestamp).total_seconds() < 3600]  # Last hour
            
            if len(recent_predictions) < 10:
                return {
                    'status': 'insufficient_data',
                    'message': 'Not enough recent predictions'
                }
            
            # Calculate recent accuracy
            recent_accuracy = sum(1 for p in recent_predictions if p.correct) / len(recent_predictions)
            accuracy_drop = perf.accuracy - recent_accuracy
            
            # Performance trends
            if len(recent_predictions) >= 20:
                recent_accuracies = [1 if p.correct else 0 for p in recent_predictions[-20:]]
                perf.recent_accuracy_trend = np.polyfit(range(len(recent_accuracies)), recent_accuracies, 1)[0]
                
                # Calculate performance variance
                perf.performance_variance = np.var(recent_accuracies)
            
            # Check for performance degradation
            retrain_needed = False
            retrain_reason = None
            
            if accuracy_drop > self.learning_config['retrain_threshold']:
                retrain_needed = True
                retrain_reason = f'accuracy_drop_{accuracy_drop:.3f}'
            
            if recent_accuracy < 0.5 and perf.prediction_count >= 100:
                retrain_needed = True
                retrain_reason = 'low_recent_accuracy'
            
            if perf.prediction_count >= self.learning_config['min_samples_for_retrain'] and perf.accuracy < 0.6:
                retrain_needed = True
                retrain_reason = 'low_overall_accuracy'
            
            return {
                'status': 'monitored',
                'recent_accuracy': recent_accuracy,
                'overall_accuracy': perf.accuracy,
                'accuracy_drop': accuracy_drop,
                'prediction_count': len(recent_predictions),
                'retrain_needed': retrain_needed,
                'retrain_reason': retrain_reason,
                'performance_trend': perf.recent_accuracy_trend,
                'performance_variance': perf.performance_variance,
                'avg_confidence': perf.avg_confidence,
                'avg_processing_time': perf.avg_processing_time
            }
            
        except Exception as e:
            logger.error(f"Performance check failed for {model_name}: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def detect_concept_drift(self) -> List[DriftDetectionResult]:
        """Detect concept drift across all registered models."""
        drift_results = []
        
        for model_name in self.registered_models.keys():
            try:
                drift_result = self.drift_detector.detect_drift(model_name)
                if drift_result:
                    drift_results.append(drift_result)
            except Exception as e:
                logger.error(f"Drift detection failed for {model_name}: {str(e)}")
        
        if drift_results:
            self.last_drift_detection = datetime.now()
            logger.warning(f"Concept drift detected in {len(drift_results)} models")
        
        return drift_results
    
    def should_retrain_model(self, model_name: str) -> Tuple[bool, str]:
        """Determine if a model should be retrained."""
        try:
            # Check time-based retraining
            last_retrain = self.last_retrain_times.get(model_name)
            if last_retrain:
                time_since_retrain = datetime.now() - last_retrain
                min_interval = timedelta(hours=self.learning_config['max_retrain_frequency_hours'])
                
                if time_since_retrain < min_interval:
                    return False, f"too_soon_since_last_retrain"
            
            # Check performance-based retraining
            perf_check = self.check_model_performance(model_name)
            
            if perf_check.get('retrain_needed', False):
                return True, perf_check.get('retrain_reason', 'performance_degradation')
            
            # Check concept drift
            drift_results = self.detect_concept_drift()
            model_drift = next((d for d in drift_results if model_name in d.affected_models), None)
            
            if model_drift:
                return True, f"concept_drift_{model_drift.drift_type}"
            
            return False, "no_retrain_needed"
            
        except Exception as e:
            logger.error(f"Retrain check failed for {model_name}: {str(e)}")
            return False, f"check_failed: {str(e)}"
    
    def prepare_training_data(self, model_name: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Prepare training data for a specific model."""
        try:
            # Get model-specific training data
            model_predictions = [p for p in self.training_data_buffer if p.model_name == model_name]
            
            if len(model_predictions) < self.learning_config['min_samples_for_retrain']:
                return None
            
            # Extract features and labels
            features = []
            labels = []
            
            for prediction in model_predictions:
                if hasattr(prediction, 'features') and prediction.features:
                    features.append(prediction.features)
                    # Convert action to numeric label
                    action_map = {'BUY': 0, 'HOLD': 1, 'SELL': 2}
                    label = action_map.get(prediction.predicted_action, 1)
                    actual_label = action_map.get(prediction.actual_action, 1)
                    
                    # Use actual label for training (if available) otherwise predicted
                    final_label = actual_label if hasattr(prediction, 'actual_action') and prediction.actual_action else label
                    labels.append(final_label)
            
            if len(features) == 0:
                return None
            
            # Convert to numpy arrays
            X = np.array(features)
            y = np.array(labels)
            
            # Shuffle data
            indices = np.random.permutation(len(X))
            X = X[indices]
            y = y[indices]
            
            return X, y
            
        except Exception as e:
            logger.error(f"Training data preparation failed for {model_name}: {str(e)}")
            return None
    
    def incremental_update_model(self, model_name: str, X: np.ndarray, y: np.ndarray) -> bool:
        """Perform incremental update of a model."""
        try:
            if model_name not in self.registered_models:
                logger.error(f"Model {model_name} not registered for online learning")
                return False
            
            model_info = self.registered_models[model_name]
            model = model_info['model']
            
            if len(X) < self.learning_config['batch_size']:
                logger.warning(f"Insufficient data for incremental update of {model_name}")
                return False
            
            # Convert to PyTorch tensors
            if isinstance(model, (LSTMPredictor, TransformerPredictor)):
                # For sequence models, prepare data
                if len(X.shape) == 2:
                    X_tensor = torch.FloatTensor(X).unsqueeze(0)  # Add batch dimension
                else:
                    X_tensor = torch.FloatTensor(X)
                
                y_tensor = torch.LongTensor(y)
                
                # Perform incremental training
                model.train()
                optimizer = model_info['optimizer']
                criterion = nn.CrossEntropyLoss()
                
                # Train on batches
                batch_size = min(self.learning_config['batch_size'], len(X))
                for i in range(0, len(X), batch_size):
                    batch_X = X_tensor[i:i+batch_size]
                    batch_y = y_tensor[i:i+batch_size]
                    
                    optimizer.zero_grad()
                    outputs = model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                
                model.eval()
                
                # Update training metadata
                model_info['last_trained'] = datetime.now()
                model_info['training_count'] += 1
                
                logger.info(f"Incremental update completed for {model_name} with {len(X)} samples")
                return True
            
            else:
                logger.warning(f"Model {model_name} type not supported for incremental learning")
                return False
                
        except Exception as e:
            logger.error(f"Incremental update failed for {model_name}: {str(e)}")
            return False
    
    def full_retrain_model(self, model_name: str, X: np.ndarray, y: np.ndarray, epochs: int = 10) -> bool:
        """Perform full retraining of a model."""
        try:
            if model_name not in self.registered_models:
                logger.error(f"Model {model_name} not registered for online learning")
                return False
            
            model_info = self.registered_models[model_name]
            model = model_info['model']
            
            if len(X) < self.learning_config['batch_size']:
                logger.warning(f"Insufficient data for full retrain of {model_name}")
                return False
            
            # Convert to PyTorch tensors and create dataset
            if isinstance(model, (LSTMPredictor, TransformerPredictor)):
                # For sequence models
                if len(X.shape) == 2:
                    X_tensor = torch.FloatTensor(X).unsqueeze(0)
                else:
                    X_tensor = torch.FloatTensor(X)
                
                y_tensor = torch.LongTensor(y)
                
                # Create data loader
                dataset = torch.utils.data.TensorDataset(X_tensor.squeeze(), y_tensor)
                dataloader = torch.utils.data.DataLoader(dataset, batch_size=self.learning_config['batch_size'], shuffle=True)
                
                # Retrain model
                model.train()
                optimizer = model_info['optimizer']
                criterion = nn.CrossEntropyLoss()
                
                for epoch in range(epochs):
                    total_loss = 0
                    for batch_X, batch_y in dataloader:
                        if len(batch_X.shape) == 1:  # Single sample, add sequence dimension
                            batch_X = batch_X.unsqueeze(0)
                        
                        optimizer.zero_grad()
                        outputs = model(batch_X)
                        loss = criterion(outputs, batch_y)
                        loss.backward()
                        optimizer.step()
                        total_loss += loss.item()
                    
                    if (epoch + 1) % 5 == 0:
                        logger.info(f"Retrain epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.4f}")
                
                model.eval()
                
                # Update training metadata
                model_info['last_trained'] = datetime.now()
                model_info['training_count'] += 1
                self.last_retrain_times[model_name] = datetime.now()
                
                # Save model
                self.save_model(model_name)
                
                logger.info(f"Full retrain completed for {model_name} with {len(X)} samples, {epochs} epochs")
                return True
            
            else:
                logger.warning(f"Model {model_name} type not supported for full retrain")
                return False
                
        except Exception as e:
            logger.error(f"Full retrain failed for {model_name}: {str(e)}")
            return False
    
    def save_model(self, model_name: str):
        """Save a trained model."""
        try:
            if model_name not in self.registered_models:
                logger.error(f"Model {model_name} not found")
                return
            
            model_info = self.registered_models[model_name]
            model = model_info['model']
            
            # Save model state
            model_path = os.path.join(self.model_save_path, f"{model_name}_online.pth")
            torch.save(model.state_dict(), model_path)
            
            # Save metadata
            metadata_path = os.path.join(self.model_save_path, f"{model_name}_metadata.pkl")
            metadata = {
                'last_trained': model_info['last_trained'],
                'training_count': model_info['training_count'],
                'performance_metrics': self.model_performance.get(model_name).__dict__,
                'config': self.learning_config
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Model {model_name} saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Model save failed for {model_name}: {str(e)}")
    
    def load_model(self, model_name: str) -> bool:
        """Load a previously saved model."""
        try:
            if model_name not in self.registered_models:
                logger.error(f"Model {model_name} not registered")
                return False
            
            model_info = self.registered_models[model_name]
            model = model_info['model']
            
            # Load model state
            model_path = os.path.join(self.model_save_path, f"{model_name}_online.pth")
            if os.path.exists(model_path):
                model.load_state_dict(torch.load(model_path, map_location='cpu'))
                
                # Load metadata
                metadata_path = os.path.join(self.model_save_path, f"{model_name}_metadata.pkl")
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                        
                        model_info['last_trained'] = metadata.get('last_trained', datetime.now())
                        model_info['training_count'] = metadata.get('training_count', 0)
                        
                        # Restore performance metrics
                        if 'performance_metrics' in metadata:
                            perf_metrics = metadata['performance_metrics']
                            if model_name not in self.model_performance:
                                self.model_performance[model_name] = ModelPerformanceMetrics()
                            
                            for key, value in perf_metrics.items():
                                if hasattr(self.model_performance[model_name], key):
                                    setattr(self.model_performance[model_name], key, value)
                
                logger.info(f"Model {model_name} loaded from {model_path}")
                return True
            else:
                logger.warning(f"No saved model found for {model_name}")
                return False
                
        except Exception as e:
            logger.error(f"Model load failed for {model_name}: {str(e)}")
            return False
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive online learning statistics."""
        try:
            stats = {
                'registered_models': list(self.registered_models.keys()),
                'model_performance': {},
                'training_data_buffer_size': len(self.training_data_buffer),
                'performance_history_size': len(self.performance_history),
                'config': self.learning_config,
                'last_drift_detection': self.last_drift_detection,
                'drift_detector_stats': self.drift_detector.get_drift_statistics()
            }
            
            # Add performance metrics for each model
            for model_name, perf in self.model_performance.items():
                stats['model_performance'][model_name] = {
                    'accuracy': perf.accuracy,
                    'prediction_count': perf.prediction_count,
                    'avg_confidence': perf.avg_confidence,
                    'avg_processing_time': perf.avg_processing_time,
                    'recent_accuracy_trend': perf.recent_accuracy_trend,
                    'performance_variance': perf.performance_variance,
                    'last_updated': perf.last_updated
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Learning statistics extraction failed: {str(e)}")
            return {'error': str(e)}
    
    def process_prediction_with_learning(self, model_name: str, prediction: Dict[str, Any], 
                                       actual_label: Optional[int] = None) -> Dict[str, Any]:
        """Process a prediction and update learning systems."""
        try:
            # Create prediction record
            prediction_record = PredictionRecord(
                timestamp=datetime.now(),
                model_name=model_name,
                regime=prediction.get('regime', 'unknown'),
                predicted_action=prediction.get('action', 'HOLD'),
                actual_action='',  # Will be set if actual_label is provided
                confidence=prediction.get('confidence', 0.5),
                features_used=prediction.get('features_count', 0),
                correct=False,  # Will be determined
                processing_time_ms=prediction.get('processing_time_ms', 0.0)
            )
            
            # Determine correctness if actual label is provided
            if actual_label is not None:
                action_map = {'BUY': 0, 'HOLD': 1, 'SELL': 2}
                predicted_label = action_map.get(prediction.get('action', 'HOLD'), 1)
                prediction_record.actual_action = prediction.get('action', 'HOLD')
                prediction_record.correct = (predicted_label == actual_label)
            
            # Add to learning systems
            self.add_prediction_result(prediction_record)
            
            # Check for retraining needs
            should_retrain, retrain_reason = self.should_retrain_model(model_name)
            
            # Check for concept drift
            drift_results = self.detect_concept_drift()
            
            # Prepare training data if retraining is needed
            if should_retrain and len(self.training_data_buffer) >= self.learning_config['min_samples_for_retrain']:
                training_data = self.prepare_training_data(model_name)
                if training_data:
                    X, y = training_data
                    
                    # Choose retraining method based on reason
                    if 'incremental' in retrain_reason or 'update_weights' in retrain_reason:
                        success = self.incremental_update_model(model_name, X, y)
                        action_taken = 'incremental_update'
                    else:
                        success = self.full_retrain_model(model_name, X, y)
                        action_taken = 'full_retrain'
                    
                    if success:
                        logger.info(f"Model {model_name} updated via {action_taken} due to {retrain_reason}")
                        prediction_record['learning_action'] = action_taken
                        prediction_record['learning_reason'] = retrain_reason
            
            # Add drift information to prediction
            model_drift = next((d for d in drift_results if model_name in d.affected_models), None)
            if model_drift:
                prediction_record['drift_detected'] = True
                prediction_record['drift_type'] = model_drift.drift_type
                prediction_record['drift_score'] = model_drift.drift_score
            else:
                prediction_record['drift_detected'] = False
                prediction_record['drift_type'] = None
                prediction_record['drift_score'] = 0.0
            
            return prediction_record
            
        except Exception as e:
            logger.error(f"Prediction processing with learning failed: {str(e)}")
            return {'error': str(e)}
    
    def reset_learning_system(self):
        """Reset the online learning system."""
        try:
            # Clear buffers
            self.training_data_buffer.clear()
            self.performance_history.clear()
            self.drift_detector.performance_history.clear()
            self.drift_detector.accuracy_window.clear()
            
            # Reset performance metrics
            for model_name in self.model_performance:
                self.model_performance[model_name] = ModelPerformanceMetrics(model_name=model_name)
            
            # Reset retrain times
            self.last_retrain_times.clear()
            self.last_drift_detection = None
            
            logger.info("Online learning system reset")
            
        except Exception as e:
            logger.error(f"Learning system reset failed: {str(e)}")
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update online learning configuration."""
        try:
            self.learning_config.update(new_config)
            
            # Update drift detector thresholds
            if 'significance_threshold' in new_config:
                self.drift_detector.significance_threshold = new_config['significance_threshold']
            
            if 'window_size' in new_config:
                old_window = self.drift_detector.window_size
                self.drift_detector.window_size = new_config['window_size']
                
                # Adjust history size if needed
                if len(self.drift_detector.accuracy_window) > new_config['window_size']:
                    # Keep only recent data
                    self.drift_detector.accuracy_window = deque(
                        list(self.drift_detector.accuracy_window)[-new_config['window_size']:], 
                        maxlen=new_config['window_size'] * 2
                    )
            
            logger.info("Online learning configuration updated")
            
        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")