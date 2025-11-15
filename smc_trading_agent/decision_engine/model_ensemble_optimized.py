"""
Optimized ML Model Ensemble with Parallel Inference and Caching

Implements ultra-low latency ML inference with:
- Parallel model execution
- Pre-loaded models
- Result caching with Redis
- Adaptive model selection
- <20ms inference latency target
"""

import asyncio
import json
import time
import logging
import hashlib
import pickle
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import asynccontextmanager

import numpy as np
import torch
import torch.nn as nn
from redis.asyncio import Redis, ConnectionPool
from stable_baselines3 import PPO
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for model optimization."""
    cache_ttl_seconds: int = 60
    cache_prefix: str = "smc_model_cache"
    parallel_execution: bool = True
    max_workers: int = 4
    model_timeout_ms: int = 50
    confidence_threshold: float = 0.6
    adaptive_selection: bool = True
    preload_models: bool = True


class ModelCache:
    """High-performance caching for model results."""
    
    def __init__(self, redis_url: str, config: ModelConfig):
        self.config = config
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Initialize Redis connection pool
        self.redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            retry_on_timeout=True,
            decode_responses=False  # Keep binary data
        )
        self._redis = None
        
    async def initialize(self):
        """Initialize Redis connection."""
        self._redis = Redis(connection_pool=self.redis_pool)
        await self._redis.ping()
        logger.info("Model cache initialized with Redis")
        
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached prediction result."""
        if not self._redis:
            return None
            
        try:
            data = await self._redis.getex(
                f"{self.config.cache_prefix}:{cache_key}",
                ex=self.config.cache_ttl_seconds
            )
            
            if data:
                self._cache_hits += 1
                return pickle.loads(data)
            else:
                self._cache_misses += 1
                return None
                
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self._cache_misses += 1
            return None
    
    async def set(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache prediction result."""
        if not self._redis:
            return
            
        try:
            data = pickle.dumps(result)
            await self._redis.setex(
                f"{self.config.cache_prefix}:{cache_key}",
                self.config.cache_ttl_seconds,
                data
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(1, total_requests)
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


class OptimizedModelEnsemble:
    """
    Optimized ML ensemble with parallel inference and caching.
    
    Key optimizations:
    - Pre-loaded models in memory
    - Parallel model execution
    - Result caching with Redis
    - Adaptive model selection
    - Timeout protection
    - Performance monitoring
    """
    
    def __init__(
        self,
        lstm_model: nn.Module,
        transformer_model: nn.Module,
        ppo_model: PPO,
        scaler: StandardScaler,
        config: ModelConfig,
        redis_url: str = "redis://localhost:6379"
    ):
        self.config = config
        self.scaler = scaler
        
        # Cache setup
        self.cache = ModelCache(redis_url, config)
        
        # Models (will be pre-loaded)
        self.lstm_model = lstm_model
        self.transformer_model = transformer_model
        self.ppo_model = ppo_model
        
        # Performance tracking
        self.inference_times = []
        self.model_performance = {
            'lstm': {'accuracy': 0.5, 'count': 0, 'errors': 0},
            'transformer': {'accuracy': 0.5, 'count': 0, 'errors': 0},
            'ppo': {'accuracy': 0.5, 'count': 0, 'errors': 0}
        }
        
        # Thread pool for model execution
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # Model state
        self._models_loaded = False
        self._model_lock = threading.Lock()
        
        logger.info("Optimized Model Ensemble initialized")

    async def initialize(self) -> None:
        """Initialize models and cache."""
        try:
            # Initialize cache
            await self.cache.initialize()
            
            # Pre-load models
            if self.config.preload_models:
                await self._preload_models()
                
            logger.info("Optimized Model Ensemble fully initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ensemble: {e}")
            raise

    async def _preload_models(self) -> None:
        """Pre-load models into memory for fast inference."""
        try:
            with self._model_lock:
                if self._models_loaded:
                    return
                    
                logger.info("Pre-loading models for inference...")
                
                # Move models to appropriate device and set to eval mode
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                
                if self.lstm_model:
                    self.lstm_model = self.lstm_model.to(device)
                    self.lstm_model.eval()
                    
                if self.transformer_model:
                    self.transformer_model = self.transformer_model.to(device)
                    self.transformer_model.eval()
                
                self._models_loaded = True
                logger.info(f"Models pre-loaded on device: {device}")
                
        except Exception as e:
            logger.error(f"Failed to pre-load models: {e}")

    def _generate_cache_key(self, recent_data: np.ndarray, sequence_length: int) -> str:
        """Generate cache key based on input data hash."""
        # Create a deterministic hash of the input data
        data_str = json.dumps(recent_data[-sequence_length:].tolist(), sort_keys=True)
        cache_key = hashlib.md5(data_str.encode()).hexdigest()[:16]
        return cache_key

    async def predict_parallel(
        self,
        recent_data: np.ndarray,
        sequence_length: int = 60,
        timeout_ms: Optional[int] = None
    ) -> Tuple[int, float, Dict[str, Any]]:
        """
        Make parallel predictions from all models with caching.
        
        Args:
            recent_data: Recent market data
            sequence_length: Length of input sequence
            timeout_ms: Timeout for model inference
            
        Returns:
            Tuple of (action, confidence, metadata)
        """
        start_time = time.time()
        timeout_ms = timeout_ms or self.config.model_timeout_ms
        
        # Check cache first
        cache_key = self._generate_cache_key(recent_data, sequence_length)
        cached_result = await self.cache.get(cache_key)
        
        if cached_result:
            inference_time = (time.time() - start_time) * 1000
            metadata = {
                'source': 'cache',
                'inference_time_ms': inference_time,
                'cache_stats': self.cache.get_cache_stats(),
                'model_predictions': cached_result['predictions']
            }
            return cached_result['action'], cached_result['confidence'], metadata
        
        # Prepare input data
        try:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            # Scale input data
            scaled_recent = self.scaler.transform(recent_data)
            X_recent = torch.FloatTensor(scaled_recent[-sequence_length:]).unsqueeze(0).to(device)
            obs = recent_data[-1].astype(np.float32)
            
        except Exception as e:
            logger.error(f"Data preparation failed: {e}")
            return 1, 0.5, {'error': str(e), 'source': 'error'}
        
        # Run predictions in parallel
        if self.config.parallel_execution:
            predictions = await self._parallel_predict(X_recent, obs, timeout_ms)
        else:
            predictions = await self._sequential_predict(X_recent, obs, timeout_ms)
        
        # Adaptive model selection
        action, confidence = self._adaptive_ensemble_selection(predictions)
        
        # Cache result
        result_to_cache = {
            'action': action,
            'confidence': confidence,
            'predictions': predictions
        }
        await self.cache.set(cache_key, result_to_cache)
        
        # Performance tracking
        inference_time = (time.time() - start_time) * 1000
        self.inference_times.append(inference_time)
        
        # Keep only recent samples
        if len(self.inference_times) > 1000:
            self.inference_times.pop(0)
        
        metadata = {
            'source': 'inference',
            'inference_time_ms': inference_time,
            'predictions': predictions,
            'cache_stats': self.cache.get_cache_stats(),
            'parallel_execution': self.config.parallel_execution,
            'device': str(device)
        }
        
        return action, confidence, metadata

    async def _parallel_predict(
        self,
        X_recent: torch.Tensor,
        obs: np.ndarray,
        timeout_ms: int
    ) -> Dict[str, Tuple[int, float]]:
        """Execute model predictions in parallel."""
        loop = asyncio.get_event_loop()
        
        # Create prediction tasks
        tasks = [
            loop.run_in_executor(
                self.executor,
                self._predict_lstm,
                X_recent
            ),
            loop.run_in_executor(
                self.executor,
                self._predict_transformer,
                X_recent
            ),
            loop.run_in_executor(
                self.executor,
                self._predict_ppo,
                obs
            )
        ]
        
        # Wait for all predictions with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_ms / 1000
            )
            
            predictions = {}
            model_names = ['lstm', 'transformer', 'ppo']
            
            for i, result in enumerate(results):
                model_name = model_names[i]
                
                if isinstance(result, Exception):
                    logger.warning(f"{model_name} prediction failed: {result}")
                    predictions[model_name] = (1, 0.5)  # Hold with low confidence
                    self.model_performance[model_name]['errors'] += 1
                else:
                    predictions[model_name] = result
                    self.model_performance[model_name]['count'] += 1
            
            return predictions
            
        except asyncio.TimeoutError:
            logger.error("Model inference timeout")
            # Return default predictions
            return {
                'lstm': (1, 0.5),
                'transformer': (1, 0.5),
                'ppo': (1, 0.5)
            }

    async def _sequential_predict(
        self,
        X_recent: torch.Tensor,
        obs: np.ndarray,
        timeout_ms: int
    ) -> Dict[str, Tuple[int, float]]:
        """Execute model predictions sequentially (fallback)."""
        predictions = {}
        
        try:
            predictions['lstm'] = self._predict_lstm(X_recent)
        except Exception as e:
            logger.warning(f"LSTM prediction failed: {e}")
            predictions['lstm'] = (1, 0.5)
            
        try:
            predictions['transformer'] = self._predict_transformer(X_recent)
        except Exception as e:
            logger.warning(f"Transformer prediction failed: {e}")
            predictions['transformer'] = (1, 0.5)
            
        try:
            predictions['ppo'] = self._predict_ppo(obs)
        except Exception as e:
            logger.warning(f"PPO prediction failed: {e}")
            predictions['ppo'] = (1, 0.5)
            
        return predictions

    def _predict_lstm(self, X_recent: torch.Tensor) -> Tuple[int, float]:
        """LSTM model prediction (thread-safe)."""
        try:
            with torch.no_grad():
                if self.lstm_model and self._models_loaded:
                    pred, conf = self.lstm_model.predict_direction(X_recent)
                    return pred.item(), conf.item()
        except Exception:
            pass
        return 1, 0.5  # Hold with low confidence

    def _predict_transformer(self, X_recent: torch.Tensor) -> Tuple[int, float]:
        """Transformer model prediction (thread-safe)."""
        try:
            with torch.no_grad():
                if self.transformer_model and self._models_loaded:
                    pred, conf = self.transformer_model.predict_direction(X_recent)
                    return pred.item(), conf.item()
        except Exception:
            pass
        return 1, 0.5  # Hold with low confidence

    def _predict_ppo(self, obs: np.ndarray) -> Tuple[int, float]:
        """PPO model prediction (thread-safe)."""
        try:
            if self.ppo_model:
                action, _ = self.ppo_model.predict(obs, deterministic=True)
                
                # Convert continuous action to discrete
                if action[0] > 0.5:
                    pred = 0  # Buy
                elif action[0] < -0.5:
                    pred = 2  # Sell
                else:
                    pred = 1  # Hold
                    
                confidence = abs(action[0])
                return pred, confidence
        except Exception:
            pass
        return 1, 0.5  # Hold with low confidence

    def _adaptive_ensemble_selection(
        self,
        predictions: Dict[str, Tuple[int, float]]
    ) -> Tuple[int, float]:
        """
        Adaptive ensemble selection based on model performance and confidence.
        """
        if not self.config.adaptive_selection:
            # Simple weighted average
            actions = [pred[0] for pred in predictions.values()]
            confidences = [pred[1] for pred in predictions.values()]
            
            # Weight by confidence
            if sum(confidences) > 0:
                weighted_action = sum(a * c for a, c in zip(actions, confidences)) / sum(confidences)
            else:
                weighted_action = 1  # Hold
                
            return int(round(weighted_action)), sum(confidences) / len(confidences)
        
        # Adaptive selection based on recent performance
        model_scores = {}
        total_score = 0
        
        for model_name, (action, confidence) in predictions.items():
            perf = self.model_performance[model_name]
            
            # Score combines recent accuracy and current confidence
            score = perf['accuracy'] * confidence
            model_scores[model_name] = score
            total_score += score
        
        # Weighted voting
        if total_score > 0:
            weighted_action = sum(
                predictions[model][0] * score
                for model, score in model_scores.items()
            ) / total_score
            
            weighted_confidence = total_score / len(predictions)
        else:
            weighted_action = 1  # Hold
            weighted_confidence = 0.5
        
        return int(round(weighted_action)), weighted_confidence

    def update_model_performance(
        self,
        model_name: str,
        predicted_action: int,
        actual_action: int,
        confidence: float
    ) -> None:
        """Update model performance tracking."""
        if model_name in self.model_performance:
            perf = self.model_performance[model_name]
            
            # Update running accuracy (exponential moving average)
            alpha = 0.1  # Learning rate
            correct = int(predicted_action == actual_action)
            new_accuracy = alpha * correct + (1 - alpha) * perf['accuracy']
            
            perf['accuracy'] = new_accuracy

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        if self.inference_times:
            avg_inference_time = np.mean(self.inference_times) * 1000
            p95_inference_time = np.percentile(self.inference_times, 95) * 1000
            p99_inference_time = np.percentile(self.inference_times, 99) * 1000
        else:
            avg_inference_time = p95_inference_time = p99_inference_time = 0
        
        return {
            'inference_times': {
                'avg_ms': avg_inference_time,
                'p95_ms': p95_inference_time,
                'p99_ms': p99_inference_time
            },
            'cache_performance': self.cache.get_cache_stats(),
            'model_performance': self.model_performance.copy(),
            'models_loaded': self._models_loaded,
            'parallel_execution': self.config.parallel_execution
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.executor.shutdown(wait=True)
            
            if hasattr(self.cache, '_redis') and self.cache._redis:
                await self.cache._redis.close()
                
            logger.info("Optimized Model Ensemble cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Factory function for easy instantiation
async def create_optimized_ensemble(
    lstm_model: nn.Module,
    transformer_model: nn.Module,
    ppo_model: PPO,
    scaler: StandardScaler,
    redis_url: str = "redis://localhost:6379",
    **kwargs
) -> OptimizedModelEnsemble:
    """
    Create and initialize optimized model ensemble.
    
    Args:
        lstm_model: LSTM neural network model
        transformer_model: Transformer neural network model
        ppo_model: PPO reinforcement learning model
        scaler: Data scaler for preprocessing
        redis_url: Redis connection URL
        **kwargs: Additional configuration options
        
    Returns:
        OptimizedModelEnsemble: Initialized ensemble
    """
    config = ModelConfig(**kwargs)
    ensemble = OptimizedModelEnsemble(
        lstm_model, transformer_model, ppo_model, scaler, config, redis_url
    )
    
    await ensemble.initialize()
    return ensemble