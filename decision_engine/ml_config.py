"""
ML Configuration Management for SMC Trading System

This module provides comprehensive configuration management for the ML decision engine,
including model settings, training parameters, inference optimization, and A/B testing
configuration.

Key Features:
- Environment-specific model configurations
- A/B testing and gradual rollout management
- Model versioning and hot-swapping
- Performance monitoring configuration
- Dynamic parameter adjustment
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DeploymentStage(Enum):
    """Deployment stages for ML models."""
    DISABLED = "disabled"  # ML models disabled, heuristic only
    SHADOW = "shadow"  # ML running alongside heuristic (no trading impact)
    CANARY = "canary"  # Small percentage of trades using ML
    GRADUAL = "gradual"  # Gradually increasing ML usage
    FULL = "full"  # Full ML deployment


@dataclass
class ModelConfig:
    """Configuration for individual ML models."""
    enabled: bool = True
    weight: float = 0.33  # Weight in ensemble
    inference_timeout_ms: int = 100  # Timeout for inference
    max_memory_mb: int = 512  # Maximum memory usage
    batch_size: int = 32
    sequence_length: int = 60
    confidence_threshold: float = 0.6


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    enabled: bool = False
    auto_retrain: bool = False
    retrain_interval_hours: int = 168  # Weekly
    min_samples: int = 1000
    validation_split: float = 0.2
    max_epochs: int = 100
    early_stopping_patience: int = 10
    save_best_only: bool = True


@dataclass
class ABTestConfig:
    """A/B testing configuration."""
    enabled: bool = False
    test_name: str = ""
    variant_a_weight: float = 0.5  # Heuristic/control
    variant_b_weight: float = 0.5  # ML model/test
    min_sample_size: int = 100
    test_duration_days: int = 14
    significance_level: float = 0.05
    metrics: List[str] = None  # Metrics to track

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = ["accuracy", "profit_pct", "sharpe_ratio"]


@dataclass
class MonitoringConfig:
    """Configuration for model monitoring."""
    enabled: bool = True
    inference_time_alert_ms: float = 50.0
    accuracy_alert_threshold: float = 0.5
    driftdetection_enabled: bool = True
    performance_window_hours: int = 24
    alert_recipients: List[str] = None

    def __post_init__(self):
        if self.alert_recipients is None:
            self.alert_recipients = []


@dataclass
class MLSystemConfig:
    """Complete ML system configuration."""
    # Deployment settings
    deployment_stage: DeploymentStage = DeploymentStage.SHADOW
    environment: str = "development"  # development, staging, production

    # Model configurations
    lstm_config: ModelConfig = None
    transformer_config: ModelConfig = None
    ppo_config: ModelConfig = None

    # Training configuration
    training_config: TrainingConfig = None

    # A/B testing
    ab_test_config: ABTestConfig = None

    # Monitoring
    monitoring_config: MonitoringConfig = None

    # System settings
    fallback_to_heuristic: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: int = 30
    max_concurrent_inferences: int = 10

    # Performance targets
    target_inference_time_ms: float = 50.0
    target_accuracy: float = 0.65
    max_memory_usage_percent: float = 80.0

    def __post_init__(self):
        if self.lstm_config is None:
            self.lstm_config = ModelConfig()
        if self.transformer_config is None:
            self.transformer_config = ModelConfig()
        if self.ppo_config is None:
            self.ppo_config = ModelConfig()
        if self.training_config is None:
            self.training_config = TrainingConfig()
        if self.ab_test_config is None:
            self.ab_test_config = ABTestConfig()
        if self.monitoring_config is None:
            self.monitoring_config = MonitoringConfig()


class MLConfigManager:
    """Manager for ML system configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "config/ml_config.json"
        self.config = MLSystemConfig()
        self._load_config()
        self._apply_environment_overrides()

    def _load_config(self):
        """Load configuration from file."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

                # Convert string enums to enum objects
                if 'deployment_stage' in config_data:
                    config_data['deployment_stage'] = DeploymentStage(config_data['deployment_stage'])

                # Update configuration
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

                logger.info(f"ML configuration loaded from {self.config_path}")
            else:
                logger.info(f"Configuration file not found, using defaults: {self.config_path}")
                self._save_config()  # Save default configuration

        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            logger.info("Using default configuration")

    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        overrides = {
            'ML_DEPLOYMENT_STAGE': ('deployment_stage', DeploymentStage),
            'ML_ENVIRONMENT': ('environment', str),
            'ML_FALLBACK_ENABLED': ('fallback_to_heuristic', bool),
            'ML_TARGET_INFERENCE_TIME': ('target_inference_time_ms', float),
            'ML_TARGET_ACCURACY': ('target_accuracy', float),
            'ML_CACHE_ENABLED': ('cache_enabled', bool),
            'ML_AB_TEST_ENABLED': ('ab_test_config.enabled', bool),
            'ML_TRAINING_ENABLED': ('training_config.enabled', bool),
            'ML_MONITORING_ENABLED': ('monitoring_config.enabled', bool)
        }

        for env_var, (config_path, value_type) in overrides.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    if value_type == bool:
                        env_value = env_value.lower() in ['true', '1', 'yes', 'on']
                    elif value_type == DeploymentStage:
                        env_value = DeploymentStage(env_value)
                    else:
                        env_value = value_type(env_value)

                    # Handle nested paths like 'ab_test_config.enabled'
                    keys = config_path.split('.')
                    target = self.config
                    for key in keys[:-1]:
                        target = getattr(target, key)
                    setattr(target, keys[-1], env_value)

                    logger.info(f"Applied environment override: {config_path} = {env_value}")

                except (ValueError, AttributeError) as e:
                    logger.error(f"Invalid environment override {env_var}={env_value}: {str(e)}")

    def _save_config(self):
        """Save current configuration to file."""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary with enum handling
            config_dict = asdict(self.config)
            config_dict['deployment_stage'] = self.config.deployment_stage.value

            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)

            logger.info(f"Configuration saved to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")

    def get_config(self) -> MLSystemConfig:
        """Get current configuration."""
        return self.config

    def update_config(self, updates: Dict[str, Any]):
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of configuration updates
        """
        try:
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")

            self._save_config()
            logger.info("Configuration updated successfully")

        except Exception as e:
            logger.error(f"Failed to update configuration: {str(e)}")

    def get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment-specific configuration."""
        return {
            'deployment_stage': self.config.deployment_stage.value,
            'environment': self.config.environment,
            'fallback_to_heuristic': self.config.fallback_to_heuristic,
            'cache_enabled': self.config.cache_enabled,
            'cache_ttl_seconds': self.config.cache_ttl_seconds,
            'max_concurrent_inferences': self.config.max_concurrent_inferences
        }

    def get_model_configs(self) -> Dict[str, ModelConfig]:
        """Get all model configurations."""
        return {
            'lstm': self.config.lstm_config,
            'transformer': self.config.transformer_config,
            'ppo': self.config.ppo_config
        }

    def is_ml_enabled(self) -> bool:
        """Check if ML models are enabled."""
        return (
            self.config.deployment_stage != DeploymentStage.DISABLED and
            (self.config.lstm_config.enabled or
             self.config.transformer_config.enabled or
             self.config.ppo_config.enabled)
        )

    def should_use_ml_for_decision(self) -> bool:
        """Determine if ML should be used for current decision."""
        if not self.is_ml_enabled():
            return False

        stage = self.config.deployment_stage

        if stage == DeploymentStage.SHADOW:
            return False  # ML runs but doesn't affect decisions
        elif stage == DeploymentStage.CANARY:
            # Small percentage of trades use ML
            import random
            return random.random() < 0.1  # 10% of trades
        elif stage == DeploymentStage.GRADUAL:
            # Gradually increasing usage
            # This could be based on time since deployment or performance metrics
            return random.random() < 0.5  # 50% of trades (could be adjusted)
        elif stage == DeploymentStage.FULL:
            return True  # Always use ML
        else:
            return False

    def get_ab_test_config(self) -> Optional[ABTestConfig]:
        """Get A/B test configuration if enabled."""
        if self.config.ab_test_config.enabled:
            return self.config.ab_test_config
        return None

    def get_model_weights(self) -> Dict[str, float]:
        """Get current model weights for ensemble."""
        weights = {}

        if self.config.lstm_config.enabled:
            weights['lstm'] = self.config.lstm_config.weight
        if self.config.transformer_config.enabled:
            weights['transformer'] = self.config.transformer_config.weight
        if self.config.ppo_config.enabled:
            weights['ppo'] = self.config.ppo_config.weight

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def enable_ab_test(self, test_name: str, duration_days: int = 14):
        """Enable A/B testing with specified parameters."""
        self.config.ab_test_config.enabled = True
        self.config.ab_test_config.test_name = test_name
        self.config.ab_test_config.test_duration_days = duration_days
        self.config.ab_test_config.start_time = datetime.now().isoformat()
        self._save_config()

        logger.info(f"A/B test enabled: {test_name} for {duration_days} days")

    def disable_ab_test(self):
        """Disable A/B testing."""
        self.config.ab_test_config.enabled = False
        self._save_config()

        logger.info("A/B test disabled")

    def set_deployment_stage(self, stage: DeploymentStage):
        """Set deployment stage."""
        old_stage = self.config.deployment_stage
        self.config.deployment_stage = stage
        self._save_config()

        logger.info(f"Deployment stage changed: {old_stage.value} → {stage.value}")

    def update_model_performance_targets(self, inference_time_ms: float, accuracy: float):
        """Update performance targets."""
        self.config.target_inference_time_ms = inference_time_ms
        self.config.target_accuracy = accuracy
        self._save_config()

        logger.info(f"Performance targets updated - Inference: {inference_time_ms}ms, Accuracy: {accuracy}")

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.config.monitoring_config

    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check deployment stage
        if self.config.deployment_stage == DeploymentStage.FULL:
            if not self.is_ml_enabled():
                issues.append("Full deployment stage requires at least one ML model enabled")

        # Check model weights
        total_weight = (
            self.config.lstm_config.weight +
            self.config.transformer_config.weight +
            self.config.ppo_config.weight
        )
        if abs(total_weight - 1.0) > 0.01 and self.is_ml_enabled():
            issues.append(f"Model weights sum to {total_weight:.2f}, should sum to 1.0")

        # Check A/B test configuration
        if self.config.ab_test_config.enabled:
            if not self.config.ab_test_config.test_name:
                issues.append("A/B test enabled but no test name specified")
            if abs(self.config.ab_test_config.variant_a_weight + self.config.ab_test_config.variant_b_weight - 1.0) > 0.01:
                issues.append("A/B test variant weights should sum to 1.0")

        # Check performance targets
        if self.config.target_inference_time_ms <= 0:
            issues.append("Target inference time must be positive")
        if not (0 <= self.config.target_accuracy <= 1):
            issues.append("Target accuracy must be between 0 and 1")

        # Check monitoring configuration
        if self.config.monitoring_config.enabled:
            if self.config.monitoring_config.inference_time_alert_ms <= 0:
                issues.append("Inference time alert threshold must be positive")
            if not (0 <= self.config.monitoring_config.accuracy_alert_threshold <= 1):
                issues.append("Accuracy alert threshold must be between 0 and 1")

        return issues

    def get_config_summary(self) -> Dict[str, Any]:
        """Get comprehensive configuration summary."""
        return {
            'deployment': {
                'stage': self.config.deployment_stage.value,
                'environment': self.config.environment,
                'ml_enabled': self.is_ml_enabled(),
                'ml_for_decisions': self.should_use_ml_for_decision()
            },
            'models': {
                name: {
                    'enabled': model.enabled,
                    'weight': model.weight,
                    'confidence_threshold': model.confidence_threshold
                }
                for name, model in self.get_model_configs().items()
            },
            'performance_targets': {
                'inference_time_ms': self.config.target_inference_time_ms,
                'accuracy': self.config.target_accuracy,
                'max_memory_percent': self.config.max_memory_usage_percent
            },
            'ab_testing': {
                'enabled': self.config.ab_test_config.enabled,
                'test_name': self.config.ab_test_config.test_name if self.config.ab_test_config.enabled else None
            },
            'monitoring': {
                'enabled': self.config.monitoring_config.enabled,
                'alerts_enabled': len(self.config.monitoring_config.alert_recipients) > 0
            },
            'validation_issues': self.validate_config()
        }

    def export_config(self, export_path: str):
        """Export configuration to specified path."""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            # Create exportable configuration
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'config': asdict(self.config),
                'config_summary': self.get_config_summary()
            }

            # Handle enum conversion
            export_data['config']['deployment_stage'] = self.config.deployment_stage.value

            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"Configuration exported to {export_path}")

        except Exception as e:
            logger.error(f"Failed to export configuration: {str(e)}")

    def import_config(self, import_path: str):
        """Import configuration from specified path."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {import_path}")

            with open(import_file, 'r') as f:
                import_data = json.load(f)

            if 'config' not in import_data:
                raise ValueError("Invalid configuration file format")

            config_data = import_data['config']

            # Convert string enums to enum objects
            if 'deployment_stage' in config_data:
                config_data['deployment_stage'] = DeploymentStage(config_data['deployment_stage'])

            # Update configuration
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            self._save_config()
            logger.info(f"Configuration imported from {import_path}")

        except Exception as e:
            logger.error(f"Failed to import configuration: {str(e)}")


# Global configuration instance
_config_manager = None


def get_ml_config() -> MLConfigManager:
    """Get global ML configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = MLConfigManager()
    return _config_manager


def reload_ml_config():
    """Reload ML configuration from file."""
    global _config_manager
    _config_manager = MLConfigManager()


# Configuration utility functions
def is_production_environment() -> bool:
    """Check if running in production environment."""
    config = get_ml_config().get_config()
    return config.environment == "production"


def should_enable_monitoring() -> bool:
    """Check if monitoring should be enabled."""
    config = get_ml_config().get_config()
    return config.monitoring_config.enabled


def get_inference_timeout() -> int:
    """Get maximum inference timeout in milliseconds."""
    config = get_ml_config().get_config()
    return max(
        config.lstm_config.inference_timeout_ms,
        config.transformer_config.inference_timeout_ms,
        config.ppo_config.inference_timeout_ms
    )