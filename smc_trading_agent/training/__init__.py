"""
Training Module - Model Training and Validation Pipeline

Handles comprehensive model training, backtesting, and validation for the SMC Trading Agent.
Includes training pipelines, reinforcement learning environments, evaluation metrics, and model optimization.

Key Features:
- Automated model training and optimization pipelines
- Reinforcement learning environment for strategy development
- Comprehensive backtesting and validation frameworks
- Model performance evaluation and metrics tracking
- Hyperparameter optimization and model selection
- Training data management and preprocessing
- Model versioning and deployment management

Usage:
    from smc_trading_agent.training import get_training_pipeline, get_rl_environment
    
    pipeline = get_training_pipeline()
    rl_env = get_rl_environment()
    
    # Train model using pipeline
    model = pipeline.train_model(training_data)
    
    # Test strategy in RL environment
    performance = rl_env.evaluate_strategy(strategy)
"""

__version__ = "1.0.0"
__description__ = "Model training and validation pipeline"
__keywords__ = ["training", "machine-learning", "reinforcement-learning", "backtesting", "validation"]

# Package-level exports
__all__ = [
    'get_training_pipeline',
    'get_rl_environment',
    '__version__',
    '__description__',
    # SMC ML Training Components
    'HistoricalDataCollector',
    'DataCollectionConfig',
    'create_data_collection_config',
    'SMCPatternLabeler',
    'LabelingConfig',
    'create_labeling_config',
    'SMCFeatureEngineer',
    'FeatureConfig',
    'create_feature_config',
    'SMCTrainingPipeline',
    'create_training_config'
]

def get_training_pipeline():
    """Get training pipeline functions for model development.
    
    Returns:
        module: Training pipeline module with model training functions
        
    Example:
        pipeline = get_training_pipeline()
        model = pipeline.train_model(training_data)
    """
    from . import pipeline
    return pipeline

def get_rl_environment():
    """Get RL environment functions for strategy evaluation.
    
    Returns:
        module: Reinforcement learning environment module
        
    Example:
        rl_env = get_rl_environment()
        performance = rl_env.evaluate_strategy(strategy)
    """
    from . import rl_environment
    return rl_environment
