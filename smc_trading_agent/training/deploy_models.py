#!/usr/bin/env python3
"""
SMC Model Deployment Script

This script handles the deployment of trained SMC ML models to production.
It loads models, validates them, and prepares them for real-time inference.

Key Features:
- Model loading and validation
- Performance benchmarking
- Configuration setup for production
- Health checks and monitoring setup
- Model versioning and rollback capability
"""

import asyncio
import logging
import sys
import time
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import torch
import torch.nn as nn
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our models and components
from smc_training_pipeline import LSTMModel, TransformerModel, PPOAgent
from smc_feature_engineer import SMCFeatureEngineer, FeatureConfig

logger = logging.getLogger(__name__)


class ModelDeployer:
    """Handles deployment of trained SMC models to production."""

    def __init__(self, model_dir: str = "./models", config_file: str = "deployment_config.json"):
        """
        Initialize model deployer.

        Args:
            model_dir: Directory containing trained models
            config_file: Deployment configuration file
        """
        self.model_dir = Path(model_dir)
        self.config_file = Path(config_file)
        self.config = self._load_deployment_config()

        # Models storage
        self.models = {}
        self.scaler = None
        self.feature_engineer = None

        # Performance tracking
        self.performance_stats = {
            'load_time': {},
            'inference_time': {},
            'memory_usage': {},
            'accuracy': {},
            'last_validation': None
        }

        # Device setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Model Deployer initialized (device: {self.device})")

    def _load_deployment_config(self) -> Dict[str, Any]:
        """Load deployment configuration."""
        default_config = {
            "model_paths": {
                "lstm": "lstm_model.pth",
                "transformer": "transformer_model.pth",
                "ppo": "ppo_agent.pkl",
                "scaler": "feature_scaler.pkl",
                "ensemble_weights": "ensemble_weights.json"
            },
            "model_settings": {
                "sequence_length": 60,
                "batch_size": 1,  # For real-time inference
                "confidence_threshold": 0.6,
                "max_inference_time_ms": 20.0
            },
            "feature_settings": {
                "scaling_method": "standard",
                "feature_count": 16,
                "remove_correlated": True
            },
            "ensemble_weights": {
                "lstm": 0.4,
                "transformer": 0.4,
                "ppo": 0.2
            },
            "monitoring": {
                "enable_drift_detection": True,
                "performance_window": 1000,
                "drift_threshold": 0.1
            },
            "version": "1.0.0",
            "deployment_timestamp": datetime.now().isoformat()
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                logger.info(f"Loaded deployment config from {self.config_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config file, using defaults: {str(e)}")

        return default_config

    async def load_models(self) -> Dict[str, bool]:
        """Load all trained models."""
        logger.info("Loading trained models for deployment")
        results = {}

        try:
            # Load feature scaler
            scaler_path = self.model_dir / self.config["model_paths"]["scaler"]
            if scaler_path.exists():
                start_time = time.time()
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                load_time = time.time() - start_time
                self.performance_stats['load_time']['scaler'] = load_time
                results['scaler'] = True
                logger.info(f"Feature scaler loaded in {load_time:.3f}s")
            else:
                logger.warning(f"Feature scaler not found at {scaler_path}")
                results['scaler'] = False

            # Initialize feature engineer
            feature_config = FeatureConfig(
                scaling_method=self.config["feature_settings"]["scaling_method"],
                remove_correlated=self.config["feature_settings"]["remove_correlated"]
            )
            self.feature_engineer = SMCFeatureEngineer(feature_config)
            self.feature_engineer.scaler = self.scaler

            # Load LSTM model
            lstm_path = self.model_dir / self.config["model_paths"]["lstm"]
            if lstm_path.exists():
                start_time = time.time()
                self.models['lstm'] = await self._load_lstm_model(lstm_path)
                load_time = time.time() - start_time
                self.performance_stats['load_time']['lstm'] = load_time
                results['lstm'] = True
                logger.info(f"LSTM model loaded in {load_time:.3f}s")
            else:
                logger.warning(f"LSTM model not found at {lstm_path}")
                results['lstm'] = False

            # Load Transformer model
            transformer_path = self.model_dir / self.config["model_paths"]["transformer"]
            if transformer_path.exists():
                start_time = time.time()
                self.models['transformer'] = await self._load_transformer_model(transformer_path)
                load_time = time.time() - start_time
                self.performance_stats['load_time']['transformer'] = load_time
                results['transformer'] = True
                logger.info(f"Transformer model loaded in {load_time:.3f}s")
            else:
                logger.warning(f"Transformer model not found at {transformer_path}")
                results['transformer'] = False

            # Load PPO agent
            ppo_path = self.model_dir / self.config["model_paths"]["ppo"]
            if ppo_path.exists():
                start_time = time.time()
                self.models['ppo'] = await self._load_ppo_agent(ppo_path)
                load_time = time.time() - start_time
                self.performance_stats['load_time']['ppo'] = load_time
                results['ppo'] = True
                logger.info(f"PPO agent loaded in {load_time:.3f}s")
            else:
                logger.warning(f"PPO agent not found at {ppo_path}")
                results['ppo'] = False

            # Load ensemble weights
            weights_path = self.model_dir / self.config["model_paths"]["ensemble_weights"]
            if weights_path.exists():
                with open(weights_path, 'r') as f:
                    self.config["ensemble_weights"] = json.load(f)
                logger.info("Ensemble weights loaded")
            else:
                logger.warning("Ensemble weights not found, using defaults")

            # Validate loaded models
            validation_results = await self._validate_loaded_models()
            self.performance_stats['last_validation'] = validation_results

            success_count = sum(1 for v in results.values() if v)
            logger.info(f"Model loading completed: {success_count}/{len(results)} models loaded successfully")

            return results

        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            return {'error': str(e)}

    async def _load_lstm_model(self, model_path: Path) -> nn.Module:
        """Load LSTM model from file."""
        # Determine model architecture (would need to store this during training)
        # For now, assume standard architecture
        input_size = self.config["feature_settings"]["feature_count"]
        hidden_dims = [128, 128, 128]

        model = LSTMModel(
            input_size=input_size,
            hidden_dims=hidden_dims,
            output_size=3,
            dropout=0.3
        ).to(self.device)

        # Load state dict
        state_dict = torch.load(model_path, map_location=self.device)
        model.load_state_dict(state_dict)
        model.eval()

        return model

    async def _load_transformer_model(self, model_path: Path) -> nn.Module:
        """Load Transformer model from file."""
        # Determine model architecture
        input_size = self.config["feature_settings"]["feature_count"]
        d_model = self.config["model_settings"].get("d_model", 256)
        num_heads = self.config["model_settings"].get("num_heads", 8)
        num_layers = self.config["model_settings"].get("num_layers", 4)
        max_sequence_length = self.config["model_settings"].get("sequence_length", 60)

        model = TransformerModel(
            input_size=input_size,
            d_model=d_model,
            num_heads=num_heads,
            num_layers=num_layers,
            output_size=3,
            dropout=0.1,
            max_sequence_length=max_sequence_length
        ).to(self.device)

        # Load state dict
        state_dict = torch.load(model_path, map_location=self.device)
        model.load_state_dict(state_dict)
        model.eval()

        return model

    async def _load_ppo_agent(self, model_path: Path) -> PPOAgent:
        """Load PPO agent from file."""
        with open(model_path, 'rb') as f:
            agent = pickle.load(f)

        # Move to device if needed
        if hasattr(agent, 'actor') and hasattr(agent, 'critic'):
            agent.actor.to(self.device)
            agent.critic.to(self.device)

        return agent

    async def _validate_loaded_models(self) -> Dict[str, Any]:
        """Validate loaded models with test data."""
        logger.info("Validating loaded models")
        validation_results = {}

        try:
            # Create test data
            test_data = self._create_test_data()

            if not test_data:
                logger.warning("No test data available for validation")
                return validation_results

            # Validate each model
            for model_name, model in self.models.items():
                if model_name == 'ppo':
                    validation_results[model_name] = await self._validate_ppo_model(model, test_data)
                else:
                    validation_results[model_name] = await self._validate_neural_model(model, test_data, model_name)

            return validation_results

        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return {'error': str(e)}

    def _create_test_data(self) -> Optional[torch.Tensor]:
        """Create test data for model validation."""
        try:
            # Create synthetic test data
            feature_count = self.config["feature_settings"]["feature_count"]
            sequence_length = self.config["model_settings"]["sequence_length"]
            batch_size = 10

            # Generate random test features
            test_data = torch.randn(batch_size, sequence_length, feature_count)

            # Apply scaling if available
            if self.scaler is not None:
                # Flatten for scaling, then reshape back
                original_shape = test_data.shape
                test_data_flat = test_data.view(-1, feature_count)
                test_data_scaled = self.scaler.transform(test_data_flat.cpu().numpy())
                test_data = torch.tensor(test_data_scaled, dtype=torch.float32).view(original_shape)

            return test_data.to(self.device)

        except Exception as e:
            logger.error(f"Failed to create test data: {str(e)}")
            return None

    async def _validate_neural_model(self, model: nn.Module, test_data: torch.Tensor, model_name: str) -> Dict[str, Any]:
        """Validate neural network model."""
        try:
            start_time = time.time()
            with torch.no_grad():
                outputs = model(test_data)
            inference_time = time.time() - start_time

            # Basic validation checks
            output_shape = outputs.shape
            expected_output_shape = (test_data.shape[0], 3)  # batch_size, num_classes

            is_valid = (
                len(output_shape) == 2 and
                output_shape[0] == expected_output_shape[0] and
                output_shape[1] == expected_output_shape[1]
            )

            # Check for NaN or infinite values
            has_nan = torch.isnan(outputs).any().item()
            has_inf = torch.isinf(outputs).any().item()

            return {
                'valid': is_valid and not has_nan and not has_inf,
                'output_shape': list(output_shape),
                'inference_time_ms': inference_time * 1000,
                'has_nan': has_nan,
                'has_inf': has_inf
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    async def _validate_ppo_model(self, agent: PPOAgent, test_data: torch.Tensor) -> Dict[str, Any]:
        """Validate PPO agent."""
        try:
            start_time = time.time()

            # Test action selection
            actions = []
            for i in range(test_data.shape[0]):
                state = test_data[i, -1, :].cpu().numpy()  # Take last timestep
                action, _, _ = agent.get_action(state)
                actions.append(action)

            inference_time = time.time() - start_time

            # Basic validation
            actions_valid = all(0 <= a < 3 for a in actions)  # Valid action range

            return {
                'valid': actions_valid,
                'num_actions': len(actions),
                'action_range': [min(actions), max(actions)],
                'inference_time_ms': inference_time * 1000
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    async def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Make prediction using ensemble of loaded models.

        Args:
            features: Feature DataFrame for prediction

        Returns:
            Dict[str, Any]: Prediction results
        """
        try:
            start_time = time.time()

            # Validate input
            if features.empty:
                return {'error': 'Empty features provided', 'prediction': None}

            # Preprocess features
            features_processed = self._preprocess_features(features)
            if features_processed is None:
                return {'error': 'Feature preprocessing failed', 'prediction': None}

            # Convert to tensor
            features_tensor = torch.FloatTensor(features_processed).to(self.device)

            # Reshape for sequence models if needed
            if features_tensor.dim() == 2:
                features_tensor = features_tensor.unsqueeze(0)  # Add batch dimension

            # Get predictions from each model
            predictions = {}
            confidences = {}

            for model_name, model in self.models.items():
                if model_name == 'ppo':
                    # PPO prediction
                    pred, confidence = self._ppo_predict(model, features_tensor)
                    predictions[model_name] = pred
                    confidences[model_name] = confidence
                else:
                    # Neural network prediction
                    with torch.no_grad():
                        outputs = model(features_tensor)
                        probs = torch.softmax(outputs, dim=-1)
                        pred = torch.argmax(probs, dim=-1).item()
                        confidence = probs.max().item()
                        predictions[model_name] = pred
                        confidences[model_name] = confidence

            # Ensemble prediction
            ensemble_prediction = self._ensemble_predict(predictions, confidences)

            inference_time = (time.time() - start_time) * 1000

            result = {
                'prediction': ensemble_prediction,
                'individual_predictions': predictions,
                'confidences': confidences,
                'ensemble_weights': self.config["ensemble_weights"],
                'inference_time_ms': inference_time,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

            # Update performance stats
            self._update_performance_stats(result)

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {
                'error': str(e),
                'prediction': None,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _preprocess_features(self, features: pd.DataFrame) -> Optional[np.ndarray]:
        """Preprocess features for model input."""
        try:
            # Validate feature count
            expected_features = self.config["feature_settings"]["feature_count"]
            if features.shape[1] != expected_features:
                logger.warning(f"Feature count mismatch: expected {expected_features}, got {features.shape[1]}")
                # Pad or truncate as needed
                if features.shape[1] < expected_features:
                    # Pad with zeros
                    padding = expected_features - features.shape[1]
                    features = pd.concat([features, pd.DataFrame(0, index=features.index, columns=range(features.shape[1], features.shape[1] + padding))], axis=1)
                else:
                    # Truncate
                    features = features.iloc[:, :expected_features]

            # Apply scaling
            if self.scaler is not None:
                features_scaled = self.scaler.transform(features)
                return features_scaled
            else:
                logger.warning("No scaler available, using raw features")
                return features.values

        except Exception as e:
            logger.error(f"Feature preprocessing failed: {str(e)}")
            return None

    def _ppo_predict(self, agent: PPOAgent, features: torch.Tensor) -> Tuple[int, float]:
        """Get PPO prediction."""
        # Take last timestep for sequence data
        if features.dim() == 3:
            features = features[:, -1, :]  # (batch, features)
        else:
            features = features.squeeze(0)  # (features,)

        # Use first sample in batch
        state = features[0].cpu().numpy()
        action, _, _ = agent.get_action(state)

        # Calculate confidence (simplified)
        confidence = 0.5  # PPO doesn't naturally provide confidence scores

        return action, confidence

    def _ensemble_predict(self, predictions: Dict[str, int], confidences: Dict[str, float]) -> int:
        """Combine predictions using ensemble weights."""
        try:
            weighted_prediction = 0
            total_weight = 0

            for model_name, pred in predictions.items():
                weight = self.config["ensemble_weights"].get(model_name, 0)
                confidence = confidences.get(model_name, 0.5)

                # Weight by both ensemble weight and confidence
                combined_weight = weight * confidence
                weighted_prediction += pred * combined_weight
                total_weight += combined_weight

            if total_weight > 0:
                return int(round(weighted_prediction / total_weight))
            else:
                # Fallback to majority vote
                return max(set(predictions.values()), key=list(predictions.values()).count)

        except Exception as e:
            logger.error(f"Ensemble prediction failed: {str(e)}")
            return 1  # Default to neutral/buy

    def _update_performance_stats(self, result: Dict[str, Any]):
        """Update performance statistics."""
        try:
            inference_time = result.get('inference_time_ms', 0)
            self.performance_stats['inference_time'].setdefault('recent', [])
            self.performance_stats['inference_time']['recent'].append(inference_time)

            # Keep only recent measurements
            if len(self.performance_stats['inference_time']['recent']) > 1000:
                self.performance_stats['inference_time']['recent'] = self.performance_stats['inference_time']['recent'][-1000:]

            # Update accuracy if we had ground truth (not available in real deployment)
            # self.performance_stats['accuracy'].setdefault('recent', [])

        except Exception as e:
            logger.error(f"Failed to update performance stats: {str(e)}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            summary = {
                'model_status': {
                    'models_loaded': list(self.models.keys()),
                    'scaler_loaded': self.scaler is not None,
                    'feature_engineer_loaded': self.feature_engineer is not None
                },
                'load_times': self.performance_stats.get('load_time', {}),
                'inference_performance': {},
                'last_validation': self.performance_stats.get('last_validation', {}),
                'config': self.config
            }

            # Calculate inference statistics
            if 'recent' in self.performance_stats.get('inference_time', {}):
                recent_times = self.performance_stats['inference_time']['recent']
                if recent_times:
                    summary['inference_performance'] = {
                        'avg_inference_time_ms': np.mean(recent_times),
                        'p95_inference_time_ms': np.percentile(recent_times, 95),
                        'max_inference_time_ms': np.max(recent_times),
                        'min_inference_time_ms': np.min(recent_times),
                        'total_predictions': len(recent_times)
                    }

            return summary

        except Exception as e:
            logger.error(f"Failed to generate performance summary: {str(e)}")
            return {'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            health = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {}
            }

            # Check models
            models_check = {
                'loaded': len(self.models) > 0,
                'models': list(self.models.keys()),
                'count': len(self.models)
            }
            health['checks']['models'] = models_check

            # Check scaler
            scaler_check = {
                'loaded': self.scaler is not None
            }
            health['checks']['scaler'] = scaler_check

            # Check device
            device_check = {
                'device': str(self.device),
                'cuda_available': torch.cuda.is_available(),
                'cuda_memory_allocated': torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
            }
            health['checks']['device'] = device_check

            # Check performance
            performance = self.get_performance_summary()
            health['checks']['performance'] = performance.get('inference_performance', {})

            # Check files
            model_dir_exists = self.model_dir.exists()
            config_file_exists = self.config_file.exists()

            health['checks']['files'] = {
                'model_directory_exists': model_dir_exists,
                'config_file_exists': config_file_exists,
                'model_files_found': len(list(self.model_dir.glob("*.pth"))) + len(list(self.model_dir.glob("*.pkl"))))
            }

            # Overall health determination
            all_healthy = (
                models_check['loaded'] and
                scaler_check['loaded'] and
                model_dir_exists and
                config_file_exists
            )

            health['status'] = 'healthy' if all_healthy else 'unhealthy'

            return health

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def benchmark_performance(self, num_runs: int = 1000) -> Dict[str, Any]:
        """Benchmark model performance."""
        logger.info(f"Running performance benchmark with {num_runs} runs")

        try:
            # Create test data
            test_data = self._create_test_data()

            if not test_data:
                return {'error': 'No test data available for benchmarking'}

            results = {}

            for model_name, model in self.models.items():
                if model_name == 'ppo':
                    continue  # PPO handled differently

                # Warm up
                for _ in range(10):
                    with torch.no_grad():
                        model(test_data)

                # Benchmark
                times = []
                for _ in range(num_runs):
                    start_time = time.time()
                    with torch.no_grad():
                        _ = model(test_data)
                    times.append(time.time() - start_time)

                results[model_name] = {
                    'avg_time_s': np.mean(times),
                    'min_time_s': np.min(times),
                    'max_time_s': np.max(times),
                    'p95_time_s': np.percentile(times, 95),
                    'p99_time_s': np.percentile(times, 99),
                    'throughput_per_second': num_runs / np.sum(times)
                }

                logger.info(f"{model_name} benchmark: "
                           f"Avg={results[model_name]['avg_time_s']*1000:.2f}ms, "
                           f"P95={results[model_name]['p95_time_s']*1000:.2f}ms, "
                           f"Throughput={results[model_name]['throughput_per_second']:.1f} pred/s")

            return results

        except Exception as e:
            logger.error(f"Benchmarking failed: {str(e)}")
            return {'error': str(e)}


async def main():
    """Example usage of the model deployer."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting SMC Model Deployment")

    # Initialize deployer
    deployer = ModelDeployer(
        model_dir="./models",
        config_file="deployment_config.json"
    )

    # Load models
    load_results = await deployer.load_models()
    print(f"Model loading results: {load_results}")

    # Perform health check
    health = deployer.health_check()
    print(f"Health check: {health}")

    # Get performance summary
    performance = deployer.get_performance_summary()
    print(f"Performance summary: {performance}")

    # Run benchmark
    benchmark = await deployer.benchmark_performance(num_runs=100)
    print(f"Benchmark results: {benchmark}")


if __name__ == "__main__":
    asyncio.run(main())