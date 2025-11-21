"""
Regime-Adaptive Ensemble System

This module implements a sophisticated ensemble system that adapts model selection
and weighting based on current market regimes. It combines regime-specific models
with dynamic model selection for optimal performance across different market conditions.

Key Features:
- Regime-specific model specialization
- Dynamic model weighting based on regime
- Smooth regime transition handling
- Performance-based model adaptation
- Confidence-weighted voting
- Model retirement and replacement
"""

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
import pickle
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from .market_regime_detector import MarketRegimeClassifier, RegimeClassification, VolatilityRegime, TrendRegime, MicrostructureRegime
from .model_ensemble import LSTMPredictor, TransformerPredictor, MarketEnvironment

logger = logging.getLogger(__name__)


@dataclass
class RegimeModelConfig:
    """Configuration for regime-specific models."""
    regime_key: str
    lstm_config: Dict[str, Any]
    transformer_config: Dict[str, Any]
    ppo_config: Dict[str, Any]
    ensemble_weights: Dict[str, float]
    confidence_threshold: float
    performance_window: int  # Number of recent predictions to evaluate


@dataclass
class ModelPerformance:
    """Model performance tracking data."""
    model_name: str
    regime: str
    accuracy: float
    precision: float
    recall: float
    confidence_avg: float
    prediction_count: int
    last_updated: datetime
    recent_predictions: List[Dict[str, Any]]


class RegimeSpecificModel:
    """
    Specialized model for specific market regimes with optimized parameters.
    """
    
    def __init__(self, regime_key: str, config: RegimeModelConfig, input_size: int):
        self.regime_key = regime_key
        self.config = config
        self.input_size = input_size
        
        # Initialize models with regime-specific configurations
        self.lstm_model = self._create_lstm_model(config.lstm_config)
        self.transformer_model = self._create_transformer_model(config.transformer_config)
        self.ppo_model = None  # PPO model initialized separately
        
        # Performance tracking
        self.performance = {
            'lstm': ModelPerformance('lstm', regime_key, 0.5, 0.5, 0.5, 0.5, 0, datetime.now(), []),
            'transformer': ModelPerformance('transformer', regime_key, 0.5, 0.5, 0.5, 0.5, 0, datetime.now(), []),
            'ppo': ModelPerformance('ppo', regime_key, 0.0, 0.0, 0.0, 0.5, 0, datetime.now(), [])
        }
        
        # Model weights for ensemble
        self.ensemble_weights = config.ensemble_weights.copy()
        
        logger.info(f"RegimeSpecificModel created for regime: {regime_key}")
    
    def _create_lstm_model(self, config: Dict[str, Any]) -> LSTMPredictor:
        """Create LSTM model with regime-specific configuration."""
        return LSTMPredictor(
            input_size=self.input_size,
            hidden_size=config.get('hidden_size', 128),
            num_layers=config.get('num_layers', 2),
            dropout=config.get('dropout', 0.2),
            sequence_length=config.get('sequence_length', 60)
        )
    
    def _create_transformer_model(self, config: Dict[str, Any]) -> TransformerPredictor:
        """Create Transformer model with regime-specific configuration."""
        return TransformerPredictor(
            input_size=self.input_size,
            d_model=config.get('d_model', 128),
            nhead=config.get('nhead', 8),
            num_layers=config.get('num_layers', 4),
            sequence_length=config.get('sequence_length', 60)
        )
    
    def predict(self, data: np.ndarray) -> Dict[str, Any]:
        """Generate prediction using regime-specific ensemble."""
        predictions = {}
        confidences = {}
        
        try:
            # LSTM prediction
            if len(data.shape) == 2:  # Single sample
                data_tensor = torch.FloatTensor(data).unsqueeze(0)
            else:
                data_tensor = torch.FloatTensor(data)
            
            with torch.no_grad():
                self.lstm_model.eval()
                lstm_probs = self.lstm_model(data_tensor)
                lstm_pred = torch.argmax(lstm_probs, dim=1).item()
                lstm_conf = torch.max(lstm_probs, dim=1)[0].item()
                
                predictions['lstm'] = lstm_pred
                confidences['lstm'] = lstm_conf
            
            # Transformer prediction
            with torch.no_grad():
                self.transformer_model.eval()
                transformer_probs = self.transformer_model(data_tensor)
                transformer_pred = torch.argmax(transformer_probs, dim=1).item()
                transformer_conf = torch.max(transformer_probs, dim=1)[0].item()
                
                predictions['transformer'] = transformer_pred
                confidences['transformer'] = transformer_conf
            
            # PPO prediction (if available)
            if self.ppo_model is not None:
                try:
                    obs = data[-1] if len(data.shape) == 2 else data
                    action, _ = self.ppo_model.predict(obs, deterministic=True)
                    
                    if action[0] > 0.5:
                        ppo_pred = 0  # Buy
                    elif action[0] < -0.5:
                        ppo_pred = 2  # Sell
                    else:
                        ppo_pred = 1  # Hold
                    
                    ppo_conf = abs(action[0])
                    
                    predictions['ppo'] = ppo_pred
                    confidences['ppo'] = ppo_conf
                except Exception as e:
                    logger.warning(f"PPO prediction failed for regime {self.regime_key}: {str(e)}")
                    predictions['ppo'] = 1  # Hold
                    confidences['ppo'] = 0.5
            else:
                predictions['ppo'] = 1
                confidences['ppo'] = 0.5
            
            # Ensemble prediction using regime-specific weights
            weighted_pred = 0
            weighted_conf = 0
            
            for model in ['lstm', 'transformer', 'ppo']:
                weight = self.ensemble_weights.get(model, 0.33)
                weighted_pred += weight * predictions[model]
                weighted_conf += weight * confidences[model]
            
            # Convert to action
            if weighted_pred < 0.5:
                action = "BUY"
            elif weighted_pred > 1.5:
                action = "SELL"
            else:
                action = "HOLD"
            
            return {
                'action': action,
                'confidence': weighted_conf,
                'individual_predictions': predictions,
                'individual_confidences': confidences,
                'ensemble_score': weighted_pred,
                'regime_specific_weights': self.ensemble_weights.copy()
            }
            
        except Exception as e:
            logger.error(f"Prediction failed for regime {self.regime_key}: {str(e)}")
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'individual_predictions': {'lstm': 1, 'transformer': 1, 'ppo': 1},
                'individual_confidences': {'lstm': 0.5, 'transformer': 0.5, 'ppo': 0.5},
                'ensemble_score': 1.0,
                'regime_specific_weights': self.ensemble_weights.copy(),
                'error': str(e)
            }
    
    def update_performance(self, model_name: str, prediction: int, actual: int, confidence: float):
        """Update performance metrics for a specific model."""
        if model_name not in self.performance:
            return
        
        perf = self.performance[model_name]
        perf.recent_predictions.append({
            'prediction': prediction,
            'actual': actual,
            'confidence': confidence,
            'timestamp': datetime.now()
        })
        
        # Keep only recent predictions for performance evaluation
        if len(perf.recent_predictions) > self.config.performance_window:
            perf.recent_predictions = perf.recent_predictions[-self.config.performance_window:]
        
        # Update metrics
        if len(perf.recent_predictions) >= 10:
            predictions = [p['prediction'] for p in perf.recent_predictions]
            actuals = [p['actual'] for p in perf.recent_predictions]
            
            perf.accuracy = accuracy_score(actuals, predictions)
            perf.precision = precision_score(actuals, predictions, average='weighted', zero_division=0)
            perf.recall = recall_score(actuals, predictions, average='weighted', zero_division=0)
            perf.confidence_avg = np.mean([p['confidence'] for p in perf.recent_predictions])
        
        perf.prediction_count += 1
        perf.last_updated = datetime.now()
    
    def adapt_weights(self):
        """Adapt ensemble weights based on recent performance."""
        total_performance = 0
        performance_scores = {}
        
        # Calculate performance scores for each model
        for model_name, perf in self.performance.items():
            if perf.prediction_count >= 10:  # Only consider models with sufficient data
                # Combine accuracy and confidence for performance score
                performance_scores[model_name] = perf.accuracy * perf.confidence_avg
                total_performance += performance_scores[model_name]
        
        if total_performance > 0:
            # Update weights based on performance
            new_weights = {}
            for model_name in ['lstm', 'transformer', 'ppo']:
                if model_name in performance_scores:
                    new_weights[model_name] = performance_scores[model_name] / total_performance
                else:
                    # Default weight for models with insufficient data
                    new_weights[model_name] = 1.0 / 3.0
            
            # Smooth weight adaptation to avoid drastic changes
            alpha = 0.3  # Adaptation rate
            for model_name in new_weights:
                old_weight = self.ensemble_weights.get(model_name, 1.0 / 3.0)
                self.ensemble_weights[model_name] = alpha * new_weights[model_name] + (1 - alpha) * old_weight
            
            # Normalize weights
            total_weight = sum(self.ensemble_weights.values())
            if total_weight > 0:
                self.ensemble_weights = {k: v / total_weight for k, v in self.ensemble_weights.items()}
            
            logger.info(f"Adapted weights for regime {self.regime_key}: {self.ensemble_weights}")
    
    def save_model(self, save_path: str):
        """Save regime-specific model to disk."""
        try:
            regime_dir = os.path.join(save_path, self.regime_key)
            os.makedirs(regime_dir, exist_ok=True)
            
            # Save neural network models
            torch.save(self.lstm_model.state_dict(), os.path.join(regime_dir, 'lstm_model.pth'))
            torch.save(self.transformer_model.state_dict(), os.path.join(regime_dir, 'transformer_model.pth'))
            
            # Save PPO model if available
            if self.ppo_model is not None:
                self.ppo_model.save(os.path.join(regime_dir, 'ppo_model'))
            
            # Save configuration and performance
            with open(os.path.join(regime_dir, 'config.pkl'), 'wb') as f:
                pickle.dump(self.config, f)
            
            with open(os.path.join(regime_dir, 'performance.pkl'), 'wb') as f:
                pickle.dump(self.performance, f)
            
            with open(os.path.join(regime_dir, 'ensemble_weights.json'), 'w') as f:
                json.dump(self.ensemble_weights, f)
            
            logger.info(f"Regime-specific model saved for {self.regime_key}")
            
        except Exception as e:
            logger.error(f"Failed to save regime model {self.regime_key}: {str(e)}")
    
    def load_model(self, save_path: str):
        """Load regime-specific model from disk."""
        try:
            regime_dir = os.path.join(save_path, self.regime_key)
            
            if not os.path.exists(regime_dir):
                logger.warning(f"No saved model found for regime {self.regime_key}")
                return False
            
            # Load neural network models
            lstm_path = os.path.join(regime_dir, 'lstm_model.pth')
            if os.path.exists(lstm_path):
                self.lstm_model.load_state_dict(torch.load(lstm_path, map_location='cpu'))
            
            transformer_path = os.path.join(regime_dir, 'transformer_model.pth')
            if os.path.exists(transformer_path):
                self.transformer_model.load_state_dict(torch.load(transformer_path, map_location='cpu'))
            
            # Load PPO model if available
            ppo_path = os.path.join(regime_dir, 'ppo_model')
            if os.path.exists(ppo_path + '.zip'):
                from stable_baselines3 import PPO
                self.ppo_model = PPO.load(ppo_path)
            
            # Load configuration and performance
            config_path = os.path.join(regime_dir, 'config.pkl')
            if os.path.exists(config_path):
                with open(config_path, 'rb') as f:
                    self.config = pickle.load(f)
            
            perf_path = os.path.join(regime_dir, 'performance.pkl')
            if os.path.exists(perf_path):
                with open(perf_path, 'rb') as f:
                    self.performance = pickle.load(f)
            
            weights_path = os.path.join(regime_dir, 'ensemble_weights.json')
            if os.path.exists(weights_path):
                with open(weights_path, 'r') as f:
                    self.ensemble_weights = json.load(f)
            
            logger.info(f"Regime-specific model loaded for {self.regime_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load regime model {self.regime_key}: {str(e)}")
            return False


class RegimeAdaptiveEnsemble:
    """
    Main regime-adaptive ensemble system that coordinates multiple regime-specific models
    and provides seamless predictions across market regime transitions.
    """
    
    def __init__(self, input_size: int, model_save_path: str = "models/regime_adaptive/"):
        self.input_size = input_size
        self.model_save_path = model_save_path
        
        # Initialize components
        self.regime_classifier = MarketRegimeClassifier()
        self.regime_models = {}
        self.current_regime = None
        self.last_regime = None
        
        # Model configuration for different regimes
        self.regime_configs = self._initialize_regime_configs()
        
        # Transition handling
        self.transition_threshold = 0.7  # Confidence threshold for regime transitions
        self.transition_buffer = []  # Buffer for handling regime transitions
        self.transition_buffer_size = 5
        
        # Performance tracking
        self.ensemble_performance = {
            'total_predictions': 0,
            'accurate_predictions': 0,
            'regime_transitions': 0,
            'average_confidence': 0.0,
            'last_updated': datetime.now()
        }
        
        # Ensure model directory exists
        os.makedirs(model_save_path, exist_ok=True)
        
        # Initialize regime models
        self._initialize_regime_models()
        
        logger.info("RegimeAdaptiveEnsemble initialized")
    
    def _initialize_regime_configs(self) -> Dict[str, RegimeModelConfig]:
        """Initialize configurations for different market regimes."""
        configs = {}
        
        # High volatility trending regimes
        configs['high_vol_uptrend'] = RegimeModelConfig(
            regime_key='high_vol_uptrend',
            lstm_config={'hidden_size': 256, 'num_layers': 3, 'dropout': 0.3, 'sequence_length': 30},
            transformer_config={'d_model': 256, 'nhead': 16, 'num_layers': 6, 'sequence_length': 30},
            ppo_config={'learning_rate': 1e-4, 'n_steps': 1024},
            ensemble_weights={'lstm': 0.2, 'transformer': 0.5, 'ppo': 0.3},
            confidence_threshold=0.7,
            performance_window=50
        )
        
        configs['high_vol_downtrend'] = RegimeModelConfig(
            regime_key='high_vol_downtrend',
            lstm_config={'hidden_size': 256, 'num_layers': 3, 'dropout': 0.3, 'sequence_length': 30},
            transformer_config={'d_model': 256, 'nhead': 16, 'num_layers': 6, 'sequence_length': 30},
            ppo_config={'learning_rate': 1e-4, 'n_steps': 1024},
            ensemble_weights={'lstm': 0.3, 'transformer': 0.4, 'ppo': 0.3},
            confidence_threshold=0.7,
            performance_window=50
        )
        
        # Low volatility regimes
        configs['low_vol_sideways'] = RegimeModelConfig(
            regime_key='low_vol_sideways',
            lstm_config={'hidden_size': 128, 'num_layers': 2, 'dropout': 0.1, 'sequence_length': 120},
            transformer_config={'d_model': 128, 'nhead': 8, 'num_layers': 4, 'sequence_length': 120},
            ppo_config={'learning_rate': 3e-4, 'n_steps': 2048},
            ensemble_weights={'lstm': 0.5, 'transformer': 0.2, 'ppo': 0.3},
            confidence_threshold=0.6,
            performance_window=100
        )
        
        # Normal volatility regimes
        configs['normal_uptrend'] = RegimeModelConfig(
            regime_key='normal_uptrend',
            lstm_config={'hidden_size': 192, 'num_layers': 2, 'dropout': 0.2, 'sequence_length': 60},
            transformer_config={'d_model': 192, 'nhead': 12, 'num_layers': 5, 'sequence_length': 60},
            ppo_config={'learning_rate': 2e-4, 'n_steps': 2048},
            ensemble_weights={'lstm': 0.3, 'transformer': 0.4, 'ppo': 0.3},
            confidence_threshold=0.65,
            performance_window=75
        )
        
        configs['normal_downtrend'] = RegimeModelConfig(
            regime_key='normal_downtrend',
            lstm_config={'hidden_size': 192, 'num_layers': 2, 'dropout': 0.2, 'sequence_length': 60},
            transformer_config={'d_model': 192, 'nhead': 12, 'num_layers': 5, 'sequence_length': 60},
            ppo_config={'learning_rate': 2e-4, 'n_steps': 2048},
            ensemble_weights={'lstm': 0.4, 'transformer': 0.3, 'ppo': 0.3},
            confidence_threshold=0.65,
            performance_window=75
        )
        
        # Default config for unknown regimes
        configs['default'] = RegimeModelConfig(
            regime_key='default',
            lstm_config={'hidden_size': 128, 'num_layers': 2, 'dropout': 0.2, 'sequence_length': 60},
            transformer_config={'d_model': 128, 'nhead': 8, 'num_layers': 4, 'sequence_length': 60},
            ppo_config={'learning_rate': 3e-4, 'n_steps': 2048},
            ensemble_weights={'lstm': 0.34, 'transformer': 0.33, 'ppo': 0.33},
            confidence_threshold=0.6,
            performance_window=100
        )
        
        return configs
    
    def _initialize_regime_models(self):
        """Initialize regime-specific models."""
        for regime_key, config in self.regime_configs.items():
            try:
                model = RegimeSpecificModel(regime_key, config, self.input_size)
                # Try to load existing model
                if not model.load_model(self.model_save_path):
                    logger.info(f"Created new regime model for {regime_key}")
                else:
                    logger.info(f"Loaded existing regime model for {regime_key}")
                
                self.regime_models[regime_key] = model
                
            except Exception as e:
                logger.error(f"Failed to initialize regime model {regime_key}: {str(e)}")
    
    def predict(self, data: pd.DataFrame, actual_label: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate prediction using regime-adaptive ensemble.
        
        Args:
            data: Market data DataFrame
            actual_label: Optional actual label for performance tracking
            
        Returns:
            Dictionary with prediction and metadata
        """
        try:
            # Classify current market regime
            regime_classification = self.regime_classifier.classify_market_regime(data)
            self.current_regime = regime_classification
            
            # Determine regime key for model selection
            regime_key = self._get_regime_key(regime_classification)
            
            # Handle regime transitions
            prediction_result = self._handle_regime_transition(data, regime_classification, regime_key)
            
            # Update performance tracking
            if actual_label is not None:
                self._update_performance(prediction_result, actual_label, regime_key)
            
            # Add regime information to prediction result
            prediction_result.update({
                'regime_classification': regime_classification,
                'regime_key': regime_key,
                'regime_features': self.regime_classifier.get_regime_features(regime_classification),
                'ensemble_type': 'regime_adaptive',
                'transition_detected': self.last_regime != regime_key and self.last_regime is not None
            })
            
            self.last_regime = regime_key
            self.ensemble_performance['total_predictions'] += 1
            self.ensemble_performance['last_updated'] = datetime.now()
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Regime-adaptive prediction failed: {str(e)}")
            return self._fallback_prediction()
    
    def _get_regime_key(self, classification: RegimeClassification) -> str:
        """Map regime classification to model configuration key."""
        vol_regime = classification.volatility_regime.value
        trend_regime = classification.trend_regime.value
        
        # Create regime key based on volatility and trend
        if 'high' in vol_regime or 'extremely' in vol_regime:
            if 'uptrend' in trend_regime:
                return 'high_vol_uptrend'
            elif 'downtrend' in trend_regime:
                return 'high_vol_downtrend'
        elif 'low' in vol_regime:
            if 'sideways' in trend_regime:
                return 'low_vol_sideways'
        elif 'normal' in vol_regime or 'elevated' in vol_regime:
            if 'uptrend' in trend_regime:
                return 'normal_uptrend'
            elif 'downtrend' in trend_regime:
                return 'normal_downtrend'
        
        # Default fallback
        return 'default'
    
    def _handle_regime_transition(self, data: pd.DataFrame, classification: RegimeClassification, 
                                regime_key: str) -> Dict[str, Any]:
        """Handle regime transitions with smooth blending."""
        # Check if this is a regime transition
        if self.last_regime and self.last_regime != regime_key:
            self.ensemble_performance['regime_transitions'] += 1
            logger.info(f"Regime transition detected: {self.last_regime} -> {regime_key}")
            
            # Add to transition buffer
            self.transition_buffer.append({
                'from_regime': self.last_regime,
                'to_regime': regime_key,
                'timestamp': datetime.now(),
                'confidence': classification.confidence
            })
            
            if len(self.transition_buffer) > self.transition_buffer_size:
                self.transition_buffer.pop(0)
            
            # Use transition blending if confidence is moderate
            if classification.confidence < self.transition_threshold:
                return self._blend_regime_predictions(data, self.last_regime, regime_key, classification.confidence)
        
        # Get regime-specific model
        if regime_key in self.regime_models:
            model = self.regime_models[regime_key]
            
            # Prepare data for prediction
            prepared_data = self._prepare_prediction_data(data)
            
            # Generate prediction
            prediction = model.predict(prepared_data)
            prediction['regime_model_used'] = regime_key
            prediction['prediction_confidence'] = classification.confidence
            
            return prediction
        else:
            logger.warning(f"Regime model not found for {regime_key}, using default")
            if 'default' in self.regime_models:
                model = self.regime_models['default']
                prepared_data = self._prepare_prediction_data(data)
                prediction = model.predict(prepared_data)
                prediction['regime_model_used'] = 'default'
                prediction['prediction_confidence'] = classification.confidence
                return prediction
            else:
                return self._fallback_prediction()
    
    def _blend_regime_predictions(self, data: pd.DataFrame, old_regime: str, new_regime: str, 
                                 confidence: float) -> Dict[str, Any]:
        """Blend predictions from old and new regime models during transitions."""
        prepared_data = self._prepare_prediction_data(data)
        
        predictions = {}
        
        # Get prediction from old regime model
        if old_regime in self.regime_models:
            old_prediction = self.regime_models[old_regime].predict(prepared_data)
            predictions['old_regime'] = old_prediction
        else:
            predictions['old_regime'] = {'action': 'HOLD', 'confidence': 0.5}
        
        # Get prediction from new regime model
        if new_regime in self.regime_models:
            new_prediction = self.regime_models[new_regime].predict(prepared_data)
            predictions['new_regime'] = new_prediction
        else:
            predictions['new_regime'] = {'action': 'HOLD', 'confidence': 0.5}
        
        # Blend predictions based on confidence
        blend_weight = confidence  # Higher confidence = more weight to new regime
        
        # Action blending
        old_action_score = self._action_to_score(predictions['old_regime']['action'])
        new_action_score = self._action_to_score(predictions['new_regime']['action'])
        
        blended_score = (1 - blend_weight) * old_action_score + blend_weight * new_action_score
        blended_action = self._score_to_action(blended_score)
        
        # Confidence blending
        blended_confidence = (1 - blend_weight) * predictions['old_regime']['confidence'] + \
                           blend_weight * predictions['new_regime']['confidence']
        
        return {
            'action': blended_action,
            'confidence': blended_confidence,
            'blended_prediction': True,
            'blend_weight': blend_weight,
            'old_regime_prediction': predictions['old_regime'],
            'new_regime_prediction': predictions['new_regime'],
            'regime_model_used': f"blended_{old_regime}_{new_regime}",
            'prediction_confidence': confidence
        }
    
    def _action_to_score(self, action: str) -> float:
        """Convert action to numeric score."""
        action_map = {'BUY': 0.0, 'HOLD': 1.0, 'SELL': 2.0}
        return action_map.get(action, 1.0)
    
    def _score_to_action(self, score: float) -> str:
        """Convert numeric score to action."""
        if score < 0.5:
            return 'BUY'
        elif score > 1.5:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _prepare_prediction_data(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare data for model prediction."""
        # Get recent data for sequence prediction
        recent_data = data.tail(120)  # Use up to 120 recent candles
        
        # Select numeric features
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        available_columns = [col for col in numeric_columns if col in data.columns]
        
        if len(available_columns) == 0:
            logger.warning("No numeric columns found for prediction")
            return np.zeros((60, 5))  # Return default data
        
        feature_data = recent_data[available_columns].values
        
        # Normalize to sequence length
        if len(feature_data) > 60:
            feature_data = feature_data[-60:]
        elif len(feature_data) < 60:
            # Pad with last values if needed
            padding_size = 60 - len(feature_data)
            if len(feature_data) > 0:
                last_row = feature_data[-1:]
                padding = np.tile(last_row, (padding_size, 1))
                feature_data = np.vstack([padding, feature_data])
            else:
                feature_data = np.zeros((60, len(available_columns)))
        
        return feature_data
    
    def _update_performance(self, prediction_result: Dict[str, Any], actual_label: int, regime_key: str):
        """Update performance tracking."""
        try:
            # Convert action to numeric label
            action_map = {'BUY': 0, 'HOLD': 1, 'SELL': 2}
            predicted_label = action_map.get(prediction_result.get('action', 'HOLD'), 1)
            
            # Update ensemble performance
            if predicted_label == actual_label:
                self.ensemble_performance['accurate_predictions'] += 1
            
            # Update regime-specific model performance
            if regime_key in self.regime_models:
                model = self.regime_models[regime_key]
                confidence = prediction_result.get('confidence', 0.5)
                
                # Update individual model performances
                if 'individual_predictions' in prediction_result:
                    for model_name, pred in prediction_result['individual_predictions'].items():
                        conf = prediction_result['individual_confidences'].get(model_name, 0.5)
                        model.update_performance(model_name, pred, actual_label, conf)
                
                # Periodically adapt weights
                if self.ensemble_performance['total_predictions'] % 20 == 0:
                    model.adapt_weights()
            
            # Update average confidence
            total_preds = self.ensemble_performance['total_predictions']
            current_conf = prediction_result.get('confidence', 0.5)
            avg_conf = self.ensemble_performance.get('average_confidence', 0.5)
            self.ensemble_performance['average_confidence'] = (avg_conf * (total_preds - 1) + current_conf) / total_preds
            
        except Exception as e:
            logger.error(f"Performance update failed: {str(e)}")
    
    def _fallback_prediction(self) -> Dict[str, Any]:
        """Provide fallback prediction when ensemble fails."""
        return {
            'action': 'HOLD',
            'confidence': 0.5,
            'fallback': True,
            'regime_model_used': 'fallback',
            'prediction_confidence': 0.1,
            'error': 'Ensemble prediction failed, using fallback'
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        accuracy = 0.0
        if self.ensemble_performance['total_predictions'] > 0:
            accuracy = self.ensemble_performance['accurate_predictions'] / self.ensemble_performance['total_predictions']
        
        return {
            'ensemble_performance': {
                'accuracy': accuracy,
                'total_predictions': self.ensemble_performance['total_predictions'],
                'average_confidence': self.ensemble_performance.get('average_confidence', 0.0),
                'regime_transitions': self.ensemble_performance['regime_transitions'],
                'last_updated': self.ensemble_performance['last_updated']
            },
            'regime_models': {
                regime_key: {
                    'lstm_performance': {
                        'accuracy': model.performance['lstm'].accuracy,
                        'prediction_count': model.performance['lstm'].prediction_count,
                        'recent_predictions': len(model.performance['lstm'].recent_predictions)
                    },
                    'transformer_performance': {
                        'accuracy': model.performance['transformer'].accuracy,
                        'prediction_count': model.performance['transformer'].prediction_count,
                        'recent_predictions': len(model.performance['transformer'].recent_predictions)
                    },
                    'ppo_performance': {
                        'accuracy': model.performance['ppo'].accuracy,
                        'prediction_count': model.performance['ppo'].prediction_count,
                        'recent_predictions': len(model.performance['ppo'].recent_predictions)
                    },
                    'ensemble_weights': model.ensemble_weights
                }
                for regime_key, model in self.regime_models.items()
            },
            'regime_classifier_stats': self.regime_classifier.get_regime_statistics(),
            'recent_transitions': self.transition_buffer[-5:] if self.transition_buffer else []
        }
    
    def save_models(self):
        """Save all regime-specific models."""
        for regime_key, model in self.regime_models.items():
            model.save_model(self.model_save_path)
        
        # Save ensemble metadata
        metadata = {
            'last_updated': datetime.now(),
            'total_predictions': self.ensemble_performance['total_predictions'],
            'current_regime': self.current_regime,
            'last_regime': self.last_regime
        }
        
        with open(os.path.join(self.model_save_path, 'ensemble_metadata.json'), 'w') as f:
            json.dump(metadata, f, default=str)
        
        logger.info("All regime-adaptive models saved")
    
    def load_models(self):
        """Load all regime-specific models."""
        success_count = 0
        for regime_key, model in self.regime_models.items():
            if model.load_model(self.model_save_path):
                success_count += 1
        
        # Load ensemble metadata
        metadata_path = os.path.join(self.model_save_path, 'ensemble_metadata.json')
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.ensemble_performance['total_predictions'] = metadata.get('total_predictions', 0)
                    self.last_regime = metadata.get('last_regime')
            except Exception as e:
                logger.warning(f"Failed to load ensemble metadata: {str(e)}")
        
        logger.info(f"Loaded {success_count}/{len(self.regime_models)} regime-specific models")
        return success_count > 0
    
    def reset_models(self):
        """Reset all models to initial state."""
        self.regime_models.clear()
        self._initialize_regime_models()
        self.transition_buffer.clear()
        self.last_regime = None
        self.current_regime = None
        logger.info("Regime-adaptive ensemble models reset")