"""
Training Module

Handles model training, backtesting, and validation for the SMC Trading Agent.
Includes training pipelines, reinforcement learning environments, and evaluation metrics.
"""

__all__ = []

def get_training_pipeline():
    """Get training pipeline functions."""
    from . import pipeline
    return pipeline

def get_rl_environment():
    """Get RL environment functions."""
    from . import rl_environment
    return rl_environment
