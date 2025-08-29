"""
SMC Trading Agent - Model Ensemble Implementation

This module implements a comprehensive ensemble architecture with LSTM, Transformer, and PPO models,
plus adaptive selection logic based on market volatility and trend strength calculations.

Key Features:
- LSTM for time series prediction
- Transformer for sequence modeling with attention mechanisms
- PPO (Proximal Policy Optimization) for reinforcement learning
- Adaptive model selection based on market conditions
- Market volatility and trend strength calculations
- Ensemble weighting and confidence scoring
"""

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import tensorflow as tf
import keras
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv
import gymnasium as gym
from gymnasium import spaces
from typing import List, Dict, Any, Tuple, Optional, Union
import pickle
import os
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger(__name__)


class MarketEnvironment(gym.Env):
    """
    Custom Gymnasium environment for PPO training on SMC trading.
    """
    def __init__(self, market_data: pd.DataFrame, initial_balance: float = 10000.0):
        super().__init__()
        self.market_data = market_data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0.0  # Current position size (-1 to 1)
        self.entry_price = None
        
        # Define action and observation spaces
        self.action_space = spaces.Box(low=-1, high=1, shape=(1,), dtype=np.float32)
        
        # Observation: OHLCV + technical indicators
        n_features = len(market_data.columns)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_features,), dtype=np.float32
        )
        
    def reset(self, seed=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = None
        return self._get_observation(), {}
        
    def step(self, action):
        if self.current_step >= len(self.market_data) - 1:
            return self._get_observation(), 0, True, True, {}
            
        current_price = self.market_data.iloc[self.current_step]['close']
        action_value = action[0]
        
        # Calculate reward
        reward = 0.0
        
        # If we have a position, calculate unrealized P&L
        if self.position != 0 and self.entry_price is not None:
            price_change = (current_price - self.entry_price) / self.entry_price
            position_pnl = self.position * price_change * 100  # Scale for better reward signal
            reward += position_pnl * 0.1  # Weight the reward
            
        # Position management
        if abs(action_value) > 0.5:  # Significant action
            if self.position == 0:  # Enter position
                self.position = np.sign(action_value)
                self.entry_price = current_price
            elif np.sign(action_value) != np.sign(self.position):  # Reverse position
                # Close current and open new
                if self.entry_price:
                    price_change = (current_price - self.entry_price) / self.entry_price
                    realized_pnl = self.position * price_change * 100
                    reward += realized_pnl
                    self.balance += realized_pnl
                    
                self.position = np.sign(action_value)
                self.entry_price = current_price
        else:  # Close position
            if self.position != 0 and self.entry_price:
                price_change = (current_price - self.entry_price) / self.entry_price
                realized_pnl = self.position * price_change * 100
                reward += realized_pnl
                self.balance += realized_pnl
                self.position = 0.0
                self.entry_price = None
                
        # Penalize excessive risk
        if abs(self.position) > 1:
            reward -= 10
            
        self.current_step += 1
        done = self.current_step >= len(self.market_data) - 1
        truncated = False
        
        return self._get_observation(), reward, done, truncated, {}
        
    def _get_observation(self):
        if self.current_step >= len(self.market_data):
            return np.zeros(self.observation_space.shape[0], dtype=np.float32)
        return self.market_data.iloc[self.current_step].values.astype(np.float32)


class LSTMPredictor(nn.Module):
    """
    LSTM model for time series prediction of price movements.
    """
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2, 
                 dropout: float = 0.2, sequence_length: int = 60):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=8, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc2 = nn.Linear(hidden_size // 2, 3)  # Buy, Hold, Sell
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        lstm_out, _ = self.lstm(x)
        
        # Apply attention
        lstm_out_transposed = lstm_out.transpose(0, 1)  # (seq_len, batch, hidden)
        attn_out, _ = self.attention(lstm_out_transposed, lstm_out_transposed, lstm_out_transposed)
        attn_out = attn_out.transpose(0, 1)  # Back to (batch, seq_len, hidden)
        
        # Use last timestep
        out = attn_out[:, -1, :]
        out = self.dropout(out)
        out = self.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        
        return self.softmax(out)
    
    def predict_direction(self, x):
        """Predict price direction with confidence."""
        with torch.no_grad():
            self.eval()
            probs = self.forward(x)
            predictions = torch.argmax(probs, dim=1)
            confidences = torch.max(probs, dim=1)[0]
            return predictions, confidences


class TransformerPredictor(nn.Module):
    """
    Transformer model for sequence modeling with attention mechanisms.
    """
    def __init__(self, input_size: int, d_model: int = 128, nhead: int = 8, 
                 num_layers: int = 4, sequence_length: int = 60):
        super().__init__()
        self.input_size = input_size
        self.d_model = d_model
        self.sequence_length = sequence_length
        
        self.input_projection = nn.Linear(input_size, d_model)
        self.positional_encoding = nn.Parameter(torch.randn(sequence_length, d_model))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc1 = nn.Linear(d_model, d_model // 2)
        self.fc2 = nn.Linear(d_model // 2, 3)  # Buy, Hold, Sell
        self.dropout = nn.Dropout(0.1)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        x = self.input_projection(x)
        
        # Add positional encoding
        x = x + self.positional_encoding.unsqueeze(0)
        
        # Apply transformer
        transformer_out = self.transformer(x)
        
        # Global average pooling
        out = transformer_out.mean(dim=1)
        
        out = self.dropout(out)
        out = self.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        
        return self.softmax(out)
    
    def predict_direction(self, x):
        """Predict price direction with confidence."""
        with torch.no_grad():
            self.eval()
            probs = self.forward(x)
            predictions = torch.argmax(probs, dim=1)
            confidences = torch.max(probs, dim=1)[0]
            return predictions, confidences


class MarketConditionAnalyzer:
    """
    Analyzes market conditions to determine volatility and trend strength.
    """
    def __init__(self, volatility_window: int = 20, trend_window: int = 14):
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        
    def calculate_volatility(self, prices: pd.Series) -> float:
        """Calculate realized volatility using rolling standard deviation."""
        if len(prices) < self.volatility_window:
            return 0.0
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=self.volatility_window).std().iloc[-1]
        return volatility * np.sqrt(252) if not np.isnan(volatility) else 0.0
    
    def calculate_trend_strength(self, prices: pd.Series) -> Tuple[float, str]:
        """Calculate trend strength using ADX-like calculation."""
        if len(prices) < self.trend_window + 1:
            return 0.0, "sideways"
            
        high = prices.rolling(window=2).max()
        low = prices.rolling(window=2).min()
        
        plus_dm = np.where(
            (high.diff() > low.diff().abs()) & (high.diff() > 0),
            high.diff(), 0
        )
        minus_dm = np.where(
            (low.diff().abs() > high.diff()) & (low.diff() < 0),
            low.diff().abs(), 0
        )
        
        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - prices.shift(1)),
                np.abs(low - prices.shift(1))
            )
        )
        
        plus_di = 100 * pd.Series(plus_dm).rolling(self.trend_window).mean() / pd.Series(tr).rolling(self.trend_window).mean()
        minus_di = 100 * pd.Series(minus_dm).rolling(self.trend_window).mean() / pd.Series(tr).rolling(self.trend_window).mean()
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(self.trend_window).mean().iloc[-1]
        
        if np.isnan(adx):
            return 0.0, "sideways"
            
        # Determine trend direction
        if plus_di.iloc[-1] > minus_di.iloc[-1]:
            trend_direction = "uptrend"
        else:
            trend_direction = "downtrend"
            
        return adx, trend_direction
    
    def get_market_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Determine current market regime."""
        if 'close' not in data.columns:
            return {"volatility": 0.0, "trend_strength": 0.0, "trend_direction": "sideways", "regime": "low_vol_sideways"}
            
        prices = data['close']
        volatility = self.calculate_volatility(prices)
        trend_strength, trend_direction = self.calculate_trend_strength(prices)
        
        # Define regimes
        if volatility > 0.25:  # High volatility
            if trend_strength > 25:
                regime = f"high_vol_{trend_direction}"
            else:
                regime = "high_vol_sideways"
        else:  # Low volatility
            if trend_strength > 25:
                regime = f"low_vol_{trend_direction}"
            else:
                regime = "low_vol_sideways"
                
        return {
            "volatility": volatility,
            "trend_strength": trend_strength,
            "trend_direction": trend_direction,
            "regime": regime
        }


class ModelEnsemble:
    """
    Main ensemble class that orchestrates LSTM, Transformer, and PPO models
    with adaptive selection based on market conditions.
    """
    def __init__(self, input_size: int, sequence_length: int = 60, model_save_path: str = "models/"):
        self.input_size = input_size
        self.sequence_length = sequence_length
        self.model_save_path = model_save_path
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # Ensure model directory exists
        os.makedirs(model_save_path, exist_ok=True)
        
        # Initialize models
        self.lstm_model = LSTMPredictor(input_size, sequence_length=sequence_length)
        self.transformer_model = TransformerPredictor(input_size, sequence_length=sequence_length)
        self.ppo_model = None  # Will be initialized during training
        
        # Model optimizers
        self.lstm_optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.001)
        self.transformer_optimizer = optim.Adam(self.transformer_model.parameters(), lr=0.001)
        
        # Market condition analyzer
        self.market_analyzer = MarketConditionAnalyzer()
        
        # Model performance tracking
        self.model_performance = {
            "lstm": {"accuracy": 0.5, "last_updated": datetime.now()},
            "transformer": {"accuracy": 0.5, "last_updated": datetime.now()},
            "ppo": {"return": 0.0, "last_updated": datetime.now()}
        }
        
        logger.info("ModelEnsemble initialized with LSTM, Transformer, and PPO models")
    
    def prepare_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for LSTM and Transformer training."""
        if len(data) < self.sequence_length + 1:
            return np.array([]), np.array([])
            
        # Scale features
        if not self.is_fitted:
            scaled_data = self.scaler.fit_transform(data.iloc[:, :-1])  # Exclude target
            self.is_fitted = True
        else:
            scaled_data = self.scaler.transform(data.iloc[:, :-1])
            
        X, y = [], []
        
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            # Assuming last column is target (price direction)
            y.append(data.iloc[i, -1])
            
        return np.array(X), np.array(y)
    
    def train_lstm(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        """Train the LSTM model."""
        logger.info("Training LSTM model...")
        
        X, y = self.prepare_sequences(data)
        if len(X) == 0:
            logger.warning("Insufficient data for LSTM training")
            return
            
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.LongTensor(y)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        criterion = nn.CrossEntropyLoss()
        
        self.lstm_model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                self.lstm_optimizer.zero_grad()
                outputs = self.lstm_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                self.lstm_optimizer.step()
                total_loss += loss.item()
                
            if (epoch + 1) % 10 == 0:
                logger.info(f"LSTM Epoch [{epoch+1}/{epochs}], Loss: {total_loss/len(dataloader):.4f}")
        
        # Update performance
        self.lstm_model.eval()
        with torch.no_grad():
            predictions, _ = self.lstm_model.predict_direction(X_tensor)
            accuracy = accuracy_score(y, predictions.numpy())
            self.model_performance["lstm"]["accuracy"] = accuracy
            self.model_performance["lstm"]["last_updated"] = datetime.now()
            
        logger.info(f"LSTM training completed. Accuracy: {accuracy:.4f}")
    
    def train_transformer(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        """Train the Transformer model."""
        logger.info("Training Transformer model...")
        
        X, y = self.prepare_sequences(data)
        if len(X) == 0:
            logger.warning("Insufficient data for Transformer training")
            return
            
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.LongTensor(y)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        criterion = nn.CrossEntropyLoss()
        
        self.transformer_model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                self.transformer_optimizer.zero_grad()
                outputs = self.transformer_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                self.transformer_optimizer.step()
                total_loss += loss.item()
                
            if (epoch + 1) % 10 == 0:
                logger.info(f"Transformer Epoch [{epoch+1}/{epochs}], Loss: {total_loss/len(dataloader):.4f}")
        
        # Update performance
        self.transformer_model.eval()
        with torch.no_grad():
            predictions, _ = self.transformer_model.predict_direction(X_tensor)
            accuracy = accuracy_score(y, predictions.numpy())
            self.model_performance["transformer"]["accuracy"] = accuracy
            self.model_performance["transformer"]["last_updated"] = datetime.now()
            
        logger.info(f"Transformer training completed. Accuracy: {accuracy:.4f}")
    
    def train_ppo(self, data: pd.DataFrame, total_timesteps: int = 10000):
        """Train the PPO reinforcement learning model."""
        logger.info("Training PPO model...")
        
        try:
            # Create environment
            def make_env():
                return MarketEnvironment(data)
            
            env = DummyVecEnv([make_env])
            
            # Initialize PPO
            self.ppo_model = PPO(
                "MlpPolicy",
                env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                verbose=1
            )
            
            # Train
            self.ppo_model.learn(total_timesteps=total_timesteps)
            
            # Evaluate performance
            obs = env.reset()
            total_reward = 0
            done = False
            
            for _ in range(len(data) - 1):
                if done:
                    break
                action, _ = self.ppo_model.predict(obs, deterministic=True)
                obs, reward, done, info = env.step(action)
                total_reward += reward[0]
            
            self.model_performance["ppo"]["return"] = total_reward
            self.model_performance["ppo"]["last_updated"] = datetime.now()
            
            logger.info(f"PPO training completed. Total return: {total_reward:.4f}")
            
        except Exception as e:
            logger.error(f"PPO training failed: {str(e)}")
            self.ppo_model = None
    
    def get_model_weights(self, market_conditions: Dict[str, Any]) -> Dict[str, float]:
        """
        Determine model weights based on market conditions and performance.
        """
        regime = market_conditions.get("regime", "low_vol_sideways")
        volatility = market_conditions.get("volatility", 0.0)
        trend_strength = market_conditions.get("trend_strength", 0.0)
        
        # Base weights on market conditions
        weights = {"lstm": 0.33, "transformer": 0.33, "ppo": 0.34}
        
        # Adjust based on market regime
        if "high_vol" in regime:
            # In high volatility, favor PPO (RL) and Transformer
            weights["ppo"] += 0.2
            weights["transformer"] += 0.1
            weights["lstm"] -= 0.3
        elif "sideways" in regime:
            # In sideways markets, favor LSTM (good for mean reversion)
            weights["lstm"] += 0.2
            weights["ppo"] += 0.1
            weights["transformer"] -= 0.3
        else:  # Trending markets
            # In trending markets, favor Transformer and PPO
            weights["transformer"] += 0.2
            weights["ppo"] += 0.1
            weights["lstm"] -= 0.3
        
        # Adjust based on recent performance
        total_perf = (
            self.model_performance["lstm"]["accuracy"] +
            self.model_performance["transformer"]["accuracy"] +
            max(0, self.model_performance["ppo"]["return"] / 100 + 0.5)  # Normalize return to 0-1
        )
        
        if total_perf > 0:
            lstm_perf_weight = self.model_performance["lstm"]["accuracy"] / total_perf
            transformer_perf_weight = self.model_performance["transformer"]["accuracy"] / total_perf
            ppo_perf_weight = max(0, self.model_performance["ppo"]["return"] / 100 + 0.5) / total_perf
            
            # Blend with performance weights
            weights["lstm"] = 0.7 * weights["lstm"] + 0.3 * lstm_perf_weight
            weights["transformer"] = 0.7 * weights["transformer"] + 0.3 * transformer_perf_weight
            weights["ppo"] = 0.7 * weights["ppo"] + 0.3 * ppo_perf_weight
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Ensure minimum weight
        for model in weights:
            weights[model] = max(0.1, weights[model])
            
        # Renormalize after minimum constraint
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def predict(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate ensemble prediction with confidence scoring.
        """
        try:
            # Analyze market conditions
            market_conditions = self.market_analyzer.get_market_regime(data)
            
            # Get model weights
            weights = self.get_model_weights(market_conditions)
            
            # Prepare data for predictions
            recent_data = data.tail(self.sequence_length)
            if len(recent_data) < self.sequence_length:
                logger.warning("Insufficient data for prediction")
                return {
                    "action": "HOLD",
                    "confidence": 0.0,
                    "market_conditions": market_conditions,
                    "model_weights": weights
                }
            
            predictions = {}
            confidences = {}
            
            # LSTM prediction
            if self.is_fitted:
                try:
                    scaled_recent = self.scaler.transform(recent_data.iloc[:, :-1] if recent_data.shape[1] > self.input_size else recent_data)
                    X_recent = torch.FloatTensor(scaled_recent[-self.sequence_length:]).unsqueeze(0)
                    
                    pred, conf = self.lstm_model.predict_direction(X_recent)
                    predictions["lstm"] = pred.item()
                    confidences["lstm"] = conf.item()
                except Exception as e:
                    logger.warning(f"LSTM prediction failed: {str(e)}")
                    predictions["lstm"] = 1  # Hold
                    confidences["lstm"] = 0.5
            else:
                predictions["lstm"] = 1
                confidences["lstm"] = 0.5
            
            # Transformer prediction
            try:
                if self.is_fitted:
                    pred, conf = self.transformer_model.predict_direction(X_recent)
                    predictions["transformer"] = pred.item()
                    confidences["transformer"] = conf.item()
                else:
                    predictions["transformer"] = 1
                    confidences["transformer"] = 0.5
            except Exception as e:
                logger.warning(f"Transformer prediction failed: {str(e)}")
                predictions["transformer"] = 1
                confidences["transformer"] = 0.5
            
            # PPO prediction
            if self.ppo_model is not None:
                try:
                    obs = recent_data.iloc[-1].values.astype(np.float32)
                    action, _ = self.ppo_model.predict(obs, deterministic=True)
                    # Convert continuous action to discrete
                    if action[0] > 0.5:
                        predictions["ppo"] = 0  # Buy
                    elif action[0] < -0.5:
                        predictions["ppo"] = 2  # Sell
                    else:
                        predictions["ppo"] = 1  # Hold
                    confidences["ppo"] = abs(action[0])
                except Exception as e:
                    logger.warning(f"PPO prediction failed: {str(e)}")
                    predictions["ppo"] = 1
                    confidences["ppo"] = 0.5
            else:
                predictions["ppo"] = 1
                confidences["ppo"] = 0.5
            
            # Ensemble prediction
            weighted_pred = 0
            weighted_conf = 0
            
            for model in ["lstm", "transformer", "ppo"]:
                weighted_pred += weights[model] * predictions[model]
                weighted_conf += weights[model] * confidences[model]
            
            # Convert to action
            if weighted_pred < 0.5:
                action = "BUY"
            elif weighted_pred > 1.5:
                action = "SELL"
            else:
                action = "HOLD"
            
            result = {
                "action": action,
                "confidence": weighted_conf,
                "market_conditions": market_conditions,
                "model_weights": weights,
                "individual_predictions": predictions,
                "individual_confidences": confidences,
                "ensemble_score": weighted_pred
            }
            
            logger.info(f"Ensemble prediction: {action} (confidence: {weighted_conf:.4f})")
            return result
            
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {str(e)}")
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "market_conditions": {"regime": "unknown"},
                "model_weights": {"lstm": 0.33, "transformer": 0.33, "ppo": 0.34},
                "error": str(e)
            }
    
    def save_models(self):
        """Save all trained models."""
        try:
            # Save PyTorch models
            torch.save(self.lstm_model.state_dict(), os.path.join(self.model_save_path, "lstm_model.pth"))
            torch.save(self.transformer_model.state_dict(), os.path.join(self.model_save_path, "transformer_model.pth"))
            
            # Save PPO model
            if self.ppo_model is not None:
                self.ppo_model.save(os.path.join(self.model_save_path, "ppo_model"))
            
            # Save scaler
            with open(os.path.join(self.model_save_path, "scaler.pkl"), "wb") as f:
                pickle.dump(self.scaler, f)
            
            # Save performance metrics
            with open(os.path.join(self.model_save_path, "performance.pkl"), "wb") as f:
                pickle.dump(self.model_performance, f)
                
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
    
    def load_models(self):
        """Load previously trained models."""
        try:
            # Load PyTorch models
            lstm_path = os.path.join(self.model_save_path, "lstm_model.pth")
            transformer_path = os.path.join(self.model_save_path, "transformer_model.pth")
            
            if os.path.exists(lstm_path):
                self.lstm_model.load_state_dict(torch.load(lstm_path))
                logger.info("LSTM model loaded")
            
            if os.path.exists(transformer_path):
                self.transformer_model.load_state_dict(torch.load(transformer_path))
                logger.info("Transformer model loaded")
            
            # Load PPO model
            ppo_path = os.path.join(self.model_save_path, "ppo_model")
            if os.path.exists(ppo_path + ".zip"):
                self.ppo_model = PPO.load(ppo_path)
                logger.info("PPO model loaded")
            
            # Load scaler
            scaler_path = os.path.join(self.model_save_path, "scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                self.is_fitted = True
                logger.info("Scaler loaded")
            
            # Load performance metrics
            perf_path = os.path.join(self.model_save_path, "performance.pkl")
            if os.path.exists(perf_path):
                with open(perf_path, "rb") as f:
                    self.model_performance = pickle.dump(f)
                logger.info("Performance metrics loaded")
                
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")


class AdaptiveModelSelector:
    """
    Backward compatible wrapper for the ensemble system.
    Maintains the original interface while providing enhanced functionality.
    """
    def __init__(self, input_size: int = 10):
        self.ensemble = ModelEnsemble(input_size=input_size)
        self.logger = logging.getLogger(__name__)
        self.logger.info("AdaptiveModelSelector initialized with ModelEnsemble")
    
    def make_decision(self, order_blocks: List[Dict[str, Any]], market_conditions: Any = None) -> Optional[Dict[str, Any]]:
        """
        Make trading decision based on detected SMC patterns.
        Enhanced version using ensemble predictions.
        """
        if not order_blocks:
            return None
        
        try:
            # Convert order blocks to DataFrame format for ensemble
            # This is a simplified conversion - in practice, you'd want more comprehensive data
            if isinstance(market_conditions, pd.DataFrame) and not market_conditions.empty:
                prediction = self.ensemble.predict(market_conditions)
                
                # Map ensemble action to original format
                action_mapping = {"BUY": "BUY", "SELL": "SELL", "HOLD": None}
                mapped_action = action_mapping.get(prediction["action"])
                
                if mapped_action:
                    # Use the latest order block for entry price
                    latest_ob = order_blocks[0]
                    
                    signal = {
                        "action": mapped_action,
                        "symbol": "BTC/USDT",  # Default symbol
                        "entry_price": latest_ob['price_level'][0] if mapped_action == "BUY" else latest_ob['price_level'][1],
                        "confidence": prediction["confidence"],
                        "market_regime": prediction["market_conditions"]["regime"],
                        "ensemble_details": prediction
                    }
                    
                    self.logger.info(f"Generated {mapped_action} signal with confidence {prediction['confidence']:.3f}")
                    return signal
            else:
                # Fallback to original logic if no market data available
                latest_ob = order_blocks[0]
                self.logger.info("Using fallback decision logic")
                
                if latest_ob.get('type') == 'bullish' or latest_ob.get('direction') == 'bullish':
                    return {
                        "action": "BUY",
                        "symbol": "BTC/USDT",
                        "entry_price": latest_ob['price_level'][0],
                        "confidence": 0.75
                    }
                elif latest_ob.get('type') == 'bearish' or latest_ob.get('direction') == 'bearish':
                    return {
                        "action": "SELL",
                        "symbol": "BTC/USDT",
                        "entry_price": latest_ob['price_level'][1],
                        "confidence": 0.75
                    }
        
        except Exception as e:
            self.logger.error(f"Decision making failed: {str(e)}")
            
        return None
    
    def train_models(self, training_data: pd.DataFrame, epochs: int = 50):
        """Train all models in the ensemble."""
        self.ensemble.train_lstm(training_data, epochs=epochs)
        self.ensemble.train_transformer(training_data, epochs=epochs)
        self.ensemble.train_ppo(training_data, total_timesteps=10000)
        
    def save_models(self):
        """Save trained models."""
        self.ensemble.save_models()
        
    def load_models(self):
        """Load previously trained models."""
        self.ensemble.load_models()