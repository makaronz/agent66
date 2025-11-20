"""
Decision Engine Module - Enhanced ML Trading Decision Logic

Implements advanced trading decision logic and ML ensemble for the SMC Trading Agent.
Includes adaptive model selection, real-time inference, A/B testing, and comprehensive monitoring.

Key Features:
- Enhanced ML Decision Engine with LSTM, Transformer, and PPO models
- Advanced feature engineering for SMC patterns
- Real-time inference with sub-50ms latency
- A/B testing and gradual rollout capability
- Comprehensive performance monitoring and alerting
- Fallback mechanisms for robustness
- Model versioning and hot-swapping
- Configuration management for deployment stages

Usage:
    from smc_trading_agent.decision_engine import get_ml_decision_engine, get_adaptive_model_selector

    # Enhanced ML Engine
    ml_engine = get_ml_decision_engine()
    decision = await ml_engine.make_decision(market_data, order_blocks)

    # Backward compatible interface
    model_selector = get_adaptive_model_selector()
    decision = await model_selector.make_decision(order_blocks, market_data)
"""

__version__ = "2.0.0"
__description__ = "Enhanced ML trading decision logic and ensemble"
__keywords__ = ["decision-engine", "ml-ensemble", "smc-patterns", "real-time-inference", "ab-testing"]

# Package-level exports
__all__ = [
    # Enhanced ML components
    'MLDecisionEngine',
    'SMCTrainingPipeline',
    'MLConfigManager',
    'FeatureEngineer',

    # Configuration and enums
    'ModelMode',
    'InferenceMode',
    'DeploymentStage',

    # Backward compatibility
    'AdaptiveModelSelector',
    'get_ml_decision_engine',
    'get_adaptive_model_selector',
    'get_ml_config',

    # Metadata
    '__version__',
    '__description__'
]

def get_ml_decision_engine(config=None):
    """Get enhanced ML Decision Engine instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        MLDecisionEngine: Configured instance for ML-based trading decisions

    Example:
        ml_engine = get_ml_decision_engine()
        decision = await ml_engine.make_decision(market_data, order_blocks)
    """
    from .ml_decision_engine import MLDecisionEngine
    from .ml_config import get_ml_config

    if config is None:
        config = get_ml_config().get_config().__dict__

    return MLDecisionEngine(config=config)


def get_adaptive_model_selector():
    """Get AdaptiveModelSelector instance for backward compatibility.

    Returns:
        AdaptiveModelSelector: Enhanced instance with ML integration

    Example:
        model_selector = get_adaptive_model_selector()
        decision = await model_selector.make_decision(order_blocks, market_data)
    """
    from .ml_decision_engine import AdaptiveModelSelector
    return AdaptiveModelSelector()


def get_ml_config():
    """Get ML configuration manager.

    Returns:
        MLConfigManager: Configuration manager for ML system

    Example:
        config = get_ml_config()
        is_ml_enabled = config.is_ml_enabled()
    """
    from .ml_config import get_ml_config as _get_ml_config
    return _get_ml_config()


def get_smc_training_pipeline(config=None):
    """Get SMC training pipeline instance.

    Args:
        config: Optional training configuration

    Returns:
        SMCTrainingPipeline: Configured training pipeline

    Example:
        pipeline = get_smc_training_pipeline()
        results = await pipeline.run_full_training_pipeline()
    """
    from .smc_training_pipeline import SMCTrainingPipeline, SMCTrainingConfig

    if config is None:
        config = SMCTrainingConfig()

    return SMCTrainingPipeline(config=config)
