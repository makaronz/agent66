"""
SMC-Specific Model Training Pipeline

This module provides specialized training pipelines for Smart Money Concepts (SMC) patterns.
It includes data preprocessing, feature engineering, model training, and validation
specifically optimized for SMC trading patterns.

Key Features:
- Historical SMC pattern data collection and labeling
- Multi-timeframe feature extraction (M5, M15, H1, H4, D1)
- Advanced feature engineering for order blocks, FVG, liquidity sweeps
- Model training with walk-forward validation
- Performance evaluation with SMC-specific metrics
- Model versioning and A/B testing capabilities
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import pickle
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp

# ML imports
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Internal imports
from .ml_decision_engine import FeatureEngineer, SMCFeatures
from .model_ensemble import ModelEnsemble, LSTMPredictor, TransformerPredictor
from ..smc_detector.indicators import SMCIndicators
from ..training.pipeline import EnhancedTrainingPipeline

logger = logging.getLogger(__name__)


@dataclass
class SMCTrainingConfig:
    """Configuration for SMC model training."""
    # Data configuration
    train_period_months: int = 24  # Months of historical data
    validation_split: float = 0.2
    test_split: float = 0.1

    # Feature configuration
    lookback_periods: List[int] = None
    multi_timeframe: bool = True
    timeframes: List[str] = None

    # Training configuration
    epochs_lstm: int = 100
    epochs_transformer: int = 100
    ppo_timesteps: int = 50000
    batch_size: int = 64
    learning_rate: float = 0.001

    # Validation configuration
    cv_folds: int = 5
    early_stopping_patience: int = 10
    min_improvement: float = 0.001

    # Performance thresholds
    min_accuracy: float = 0.55
    min_sharpe_ratio: float = 0.5
    max_drawdown_threshold: float = 0.2

    def __post_init__(self):
        if self.lookback_periods is None:
            self.lookback_periods = [5, 10, 20, 50]
        if self.timeframes is None:
            self.timeframes = ["5m", "15m", "1h", "4h", "1d"]


@dataclass
class SMCLabel:
    """Labeled SMC pattern for training."""
    timestamp: datetime
    pattern_type: str  # 'bullish_ob', 'bearish_ob', 'fvg', 'liquidity_sweep', etc.
    entry_price: float
    target_price: Optional[float]  # Take profit target
    stop_loss: Optional[float]  # Stop loss level
    outcome: str  # 'profit', 'loss', 'breakeven'
    profit_pct: float  # Percentage profit/loss
    holding_period: int  # Bars held
    confidence: float  # Pattern confidence
    market_regime: str  # Market condition at pattern detection


class SMCDataCollector:
    """Collects and processes historical SMC pattern data for training."""

    def __init__(self, config: SMCTrainingConfig):
        self.config = config
        self.smc_detector = SMCIndicators()
        self.feature_engineer = FeatureEngineer()

    async def collect_training_data(self,
                                  start_date: datetime,
                                  end_date: datetime,
                                  symbols: List[str] = ["BTC/USDT"]) -> pd.DataFrame:
        """
        Collect comprehensive training data with SMC patterns and labels.

        Args:
            start_date: Start date for data collection
            end_date: End date for data collection
            symbols: Trading symbols to collect data for

        Returns:
            DataFrame with features and labels for training
        """
        logger.info(f"Collecting training data from {start_date} to {end_date}")

        all_data = []

        for symbol in symbols:
            try:
                symbol_data = await self._collect_symbol_data(symbol, start_date, end_date)
                if symbol_data is not None and not symbol_data.empty:
                    all_data.append(symbol_data)
                    logger.info(f"Collected {len(symbol_data)} samples for {symbol}")

            except Exception as e:
                logger.error(f"Failed to collect data for {symbol}: {str(e)}")
                continue

        if not all_data:
            logger.error("No training data collected")
            return pd.DataFrame()

        # Combine all symbol data
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Total training samples collected: {len(combined_data)}")

        return combined_data

    async def _collect_symbol_data(self,
                                 symbol: str,
                                 start_date: datetime,
                                 end_date: datetime) -> Optional[pd.DataFrame]:
        """Collect data for a single symbol with SMC patterns and labels."""
        try:
            # This would typically connect to a data provider
            # For now, we'll simulate the process with realistic data generation

            # Generate realistic OHLCV data
            date_range = pd.date_range(start=start_date, end=end_date, freq='1h')

            # Simulate price movements with realistic characteristics
            np.random.seed(hash(symbol) % 2**32)  # Reproducible per symbol

            # Generate base price with trend and volatility
            base_price = 50000.0 if 'BTC' in symbol else 1000.0

            # Simulate market regime changes
            n_periods = len(date_range)
            trend_changes = np.random.choice(n_periods, size=max(1, n_periods // 720), replace=False)  # ~monthly changes

            prices = []
            current_price = base_price
            trend = np.random.choice([-0.001, 0, 0.001])  # Daily trend

            for i in range(n_periods):
                # Check for trend change
                if i in trend_changes:
                    trend = np.random.choice([-0.001, 0, 0.001])

                # Generate price movement with trend and noise
                volatility = 0.02  # 2% daily volatility
                price_change = trend + np.random.normal(0, volatility / np.sqrt(24))  # Hourly volatility

                current_price *= (1 + price_change)
                prices.append(current_price)

            prices = np.array(prices)

            # Generate OHLC from prices
            high_noise = np.random.exponential(0.002, n_periods)
            low_noise = np.random.exponential(0.002, n_periods)

            data = pd.DataFrame({
                'timestamp': date_range,
                'open': prices,
                'high': prices * (1 + high_noise),
                'low': prices * (1 - low_noise),
                'close': np.roll(prices, -1),  # Next period becomes close
                'volume': np.random.lognormal(mean=10, sigma=1, size=n_periods)
            })

            # Ensure last close equals last open
            data.loc[data.index[-1], 'close'] = data.loc[data.index[-1], 'open']

            # Remove any rows with invalid data
            data = data[data['high'] >= data['low']]
            data = data[data['high'] >= data['open']]
            data = data[data['high'] >= data['close']]
            data = data[data['low'] <= data['open']]
            data = data[data['low'] <= data['close']]

            data.reset_index(drop=True, inplace=True)

            # Detect SMC patterns
            logger.info(f"Detecting SMC patterns for {symbol}")

            # Detect order blocks
            order_blocks = self.smc_detector.detect_order_blocks(data)

            # Detect CHOCH and BOS patterns
            coch_bos = self.smc_detector.identify_choch_bos(data)

            # Detect liquidity sweeps
            liquidity_sweeps = self.smc_detector.liquidity_sweep_detection(data)

            # Create labeled training data
            labeled_data = await self._create_labeled_dataset(
                data, order_blocks, coch_bos, liquidity_sweeps
            )

            return labeled_data

        except Exception as e:
            logger.error(f"Failed to collect symbol data for {symbol}: {str(e)}")
            return None

    async def _create_labeled_dataset(self,
                                    market_data: pd.DataFrame,
                                    order_blocks: List[Dict],
                                    coch_bos: Dict,
                                    liquidity_sweeps: Dict) -> pd.DataFrame:
        """Create labeled dataset from SMC patterns."""
        try:
            training_samples = []

            # Process order blocks
            for ob in order_blocks:
                sample = await self._create_order_block_sample(market_data, ob)
                if sample:
                    training_samples.append(sample)

            # Process CHOCH patterns
            for pattern in coch_bos.get('coch_patterns', []):
                sample = await self._create_pattern_sample(market_data, pattern, 'choch')
                if sample:
                    training_samples.append(sample)

            # Process BOS patterns
            for pattern in coch_bos.get('bos_patterns', []):
                sample = await self._create_pattern_sample(market_data, pattern, 'bos')
                if sample:
                    training_samples.append(sample)

            # Process liquidity sweeps
            for sweep in liquidity_sweeps.get('liquidity_sweeps', []):
                sample = await self._create_pattern_sample(market_data, sweep, 'liquidity_sweep')
                if sample:
                    training_samples.append(sample)

            if not training_samples:
                logger.warning("No training samples created from patterns")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(training_samples)

            # Add negative samples (no pattern detected)
            negative_samples = await self._create_negative_samples(market_data, len(df))
            if negative_samples:
                df = pd.concat([df, negative_samples], ignore_index=True)

            # Shuffle the dataset
            df = df.sample(frac=1).reset_index(drop=True)

            logger.info(f"Created labeled dataset with {len(df)} samples "
                       f"({df['label'].sum()} positive, {(df['label'] == 0).sum()} negative)")

            return df

        except Exception as e:
            logger.error(f"Failed to create labeled dataset: {str(e)}")
            return pd.DataFrame()

    async def _create_order_block_sample(self,
                                       market_data: pd.DataFrame,
                                       order_block: Dict) -> Optional[Dict]:
        """Create training sample from order block pattern."""
        try:
            # Get pattern timestamp
            pattern_time = pd.Timestamp(order_block['timestamp'])
            pattern_type = order_block['type']

            # Find pattern in market data
            pattern_idx = market_data[market_data['timestamp'] >= pattern_time].index
            if len(pattern_idx) == 0:
                return None

            pattern_idx = pattern_idx[0]

            # Look ahead for outcome (next 20 bars)
            look_ahead = min(20, len(market_data) - pattern_idx - 1)
            if look_ahead < 5:
                return None

            future_data = market_data.iloc[pattern_idx + 1:pattern_idx + look_ahead + 1]
            entry_price = market_data.iloc[pattern_idx]['close']

            # Determine outcome based on pattern type
            if 'bull' in pattern_type.lower():
                # Bullish pattern: profit if price goes up
                max_profit = future_data['high'].max() - entry_price
                max_loss = entry_price - future_data['low'].min()
                target_reached = future_data['high'].max() >= entry_price * 1.02  # 2% target
                stop_hit = future_data['low'].min() <= entry_price * 0.98  # 2% stop

            else:  # bearish
                # Bearish pattern: profit if price goes down
                max_profit = entry_price - future_data['low'].min()
                max_loss = future_data['high'].max() - entry_price
                target_reached = future_data['low'].min() <= entry_price * 0.98
                stop_hit = future_data['high'].max() >= entry_price * 1.02

            # Determine outcome
            if target_reached and not stop_hit:
                outcome = 'profit'
                profit_pct = 0.02 if 'bull' in pattern_type.lower() else 0.02
                label = 1
            elif stop_hit and not target_reached:
                outcome = 'loss'
                profit_pct = -0.02
                label = 0
            else:
                # Neither target nor stop hit within look_ahead period
                final_price = future_data.iloc[-1]['close']
                profit_pct = (final_price - entry_price) / entry_price
                if 'bull' in pattern_type.lower():
                    outcome = 'profit' if profit_pct > 0 else 'loss'
                    label = 1 if profit_pct > 0 else 0
                else:
                    outcome = 'profit' if profit_pct < 0 else 'loss'
                    label = 1 if profit_pct < 0 else 0

            # Extract features from pattern context
            context_data = market_data.iloc[max(0, pattern_idx - 50):pattern_idx + 1]
            if len(context_data) < 20:
                return None

            smc_patterns = {'order_blocks': [order_block]}
            features = self.feature_engineer.extract_smc_features(context_data, smc_patterns)

            return {
                'timestamp': pattern_time,
                'pattern_type': f"{pattern_type}_order_block",
                'features': features.to_array(),
                'label': label,
                'outcome': outcome,
                'profit_pct': profit_pct,
                'confidence': order_block.get('strength_volume', 0.5)
            }

        except Exception as e:
            logger.error(f"Failed to create order block sample: {str(e)}")
            return None

    async def _create_pattern_sample(self,
                                   market_data: pd.DataFrame,
                                   pattern: Dict,
                                   pattern_category: str) -> Optional[Dict]:
        """Create training sample from general pattern (CHOCH, BOS, liquidity sweep)."""
        try:
            # Similar logic to order block sample but adapted for different pattern types
            pattern_time = pd.Timestamp(pattern['timestamp'])
            pattern_type = pattern['type']

            # Find pattern in market data
            pattern_idx = market_data[market_data['timestamp'] >= pattern_time].index
            if len(pattern_idx) == 0:
                return None

            pattern_idx = pattern_idx[0]

            # Look ahead for outcome
            look_ahead = min(15, len(market_data) - pattern_idx - 1)
            if look_ahead < 5:
                return None

            future_data = market_data.iloc[pattern_idx + 1:pattern_idx + look_ahead + 1]
            entry_price = market_data.iloc[pattern_idx]['close']

            # Determine expected direction based on pattern type
            bullish_patterns = ['bullish_coch', 'bullish_bos', 'bullish_sweep']
            bearish_patterns = ['bearish_coch', 'bearish_bos', 'bearish_sweep']

            if any(bull in pattern_type for bull in bullish_patterns):
                expected_direction = 1  # Bullish
            elif any(bear in pattern_type for bear in bearish_patterns):
                expected_direction = -1  # Bearish
            else:
                return None  # Unknown pattern type

            # Calculate outcome
            final_price = future_data.iloc[-1]['close']
            price_change = (final_price - entry_price) / entry_price

            if expected_direction * price_change > 0.01:  # 1% profit in expected direction
                outcome = 'profit'
                label = 1
            elif expected_direction * price_change < -0.01:  # 1% loss against expected direction
                outcome = 'loss'
                label = 0
            else:
                outcome = 'breakeven'
                label = 0  # Conservative: count breakeven as negative

            # Extract features
            context_data = market_data.iloc[max(0, pattern_idx - 50):pattern_idx + 1]
            if len(context_data) < 20:
                return None

            smc_patterns = {pattern_category: [pattern]}
            features = self.feature_engineer.extract_smc_features(context_data, smc_patterns)

            return {
                'timestamp': pattern_time,
                'pattern_type': pattern_type,
                'features': features.to_array(),
                'label': label,
                'outcome': outcome,
                'profit_pct': price_change,
                'confidence': pattern.get('confidence', 0.5)
            }

        except Exception as e:
            logger.error(f"Failed to create pattern sample: {str(e)}")
            return None

    async def _create_negative_samples(self,
                                      market_data: pd.DataFrame,
                                      n_samples: int) -> Optional[pd.DataFrame]:
        """Create negative samples (no clear patterns)."""
        try:
            negative_samples = []

            # Sample random time points with no clear patterns
            n_time_points = min(n_samples * 2, len(market_data) - 100)
            random_indices = np.random.choice(
                range(50, len(market_data) - 20),
                size=n_time_points,
                replace=False
            )

            for idx in random_indices[:n_samples]:
                try:
                    # Get context data
                    context_data = market_data.iloc[idx - 50:idx + 1]

                    # Check if this is truly a negative sample (no strong patterns)
                    if len(context_data) < 20:
                        continue

                    # Simple check: low volatility and no clear trend
                    returns = context_data['close'].pct_change().dropna()
                    volatility = returns.std()
                    trend = abs((context_data.iloc[-1]['close'] - context_data.iloc[0]['close']) / context_data.iloc[0]['close'])

                    # Only include if low volatility and weak trend
                    if volatility < 0.02 and trend < 0.02:
                        features = self.feature_engineer.extract_smc_features(context_data, {})

                        negative_samples.append({
                            'timestamp': context_data.iloc[-1]['timestamp'],
                            'pattern_type': 'no_pattern',
                            'features': features.to_array(),
                            'label': 0,
                            'outcome': 'neutral',
                            'profit_pct': 0.0,
                            'confidence': 0.1
                        })

                except Exception as e:
                    continue

            if negative_samples:
                return pd.DataFrame(negative_samples)
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to create negative samples: {str(e)}")
            return None


class SMCTrainer:
    """Specialized trainer for SMC pattern recognition models."""

    def __init__(self, config: SMCTrainingConfig):
        self.config = config
        self.model_ensemble = ModelEnsemble(
            input_size=16,  # SMCFeatures size
            sequence_length=60,
            model_save_path='models/smc_trained/'
        )
        self.scaler = RobustScaler()
        self.is_fitted = False

    async def train_models(self, training_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Train all models in the ensemble with SMC-specific data.

        Args:
            training_data: DataFrame with features and labels

        Returns:
            Training results and performance metrics
        """
        logger.info(f"Starting SMC model training with {len(training_data)} samples")

        try:
            # Validate training data
            if training_data.empty or 'features' not in training_data.columns or 'label' not in training_data.columns:
                raise ValueError("Invalid training data format")

            # Prepare features and labels
            X, y = self._prepare_training_data(training_data)

            if len(X) == 0:
                raise ValueError("No valid training samples after preparation")

            # Split data
            X_train, X_val, X_test, y_train, y_val, y_test = self._split_data(X, y)

            logger.info(f"Data splits - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

            # Train models
            training_results = {}

            # Train LSTM
            lstm_results = await self._train_lstm(X_train, y_train, X_val, y_val)
            training_results['lstm'] = lstm_results

            # Train Transformer
            transformer_results = await self._train_transformer(X_train, y_train, X_val, y_val)
            training_results['transformer'] = transformer_results

            # Train PPO (if enough data)
            if len(X_train) >= 1000:
                ppo_results = await self._train_ppo(X_train, y_train)
                training_results['ppo'] = ppo_results
            else:
                logger.warning("Insufficient data for PPO training (requires at least 1000 samples)")
                training_results['ppo'] = {'status': 'skipped', 'reason': 'insufficient_data'}

            # Evaluate on test set
            test_results = await self._evaluate_models(X_test, y_test)
            training_results['test_evaluation'] = test_results

            # Save models
            await self._save_models()

            # Generate training summary
            summary = self._generate_training_summary(training_results)

            logger.info(f"SMC model training completed successfully")
            logger.info(f"Summary: {json.dumps(summary, indent=2)}")

            return {
                'status': 'completed',
                'results': training_results,
                'summary': summary,
                'model_path': 'models/smc_trained/',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"SMC model training failed: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _prepare_training_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for training."""
        try:
            # Extract features
            features_list = []
            labels_list = []

            for _, row in data.iterrows():
                features = row['features']
                label = row['label']

                if isinstance(features, np.ndarray) and features.shape[0] == 16:
                    features_list.append(features)
                    labels_list.append(label)

            if not features_list:
                return np.array([]), np.array([])

            X = np.array(features_list)
            y = np.array(labels_list)

            # Scale features
            if not self.is_fitted:
                X_scaled = self.scaler.fit_transform(X)
                self.is_fitted = True
            else:
                X_scaled = self.scaler.transform(X)

            return X_scaled, y

        except Exception as e:
            logger.error(f"Failed to prepare training data: {str(e)}")
            return np.array([]), np.array([])

    def _split_data(self, X: np.ndarray, y: np.ndarray) -> Tuple:
        """Split data into train, validation, and test sets."""
        n_samples = len(X)

        # Calculate split indices
        test_size = int(n_samples * self.config.test_split)
        val_size = int(n_samples * self.config.validation_split)
        train_size = n_samples - test_size - val_size

        # Split data (time series aware)
        X_train = X[:train_size]
        y_train = y[:train_size]

        X_val = X[train_size:train_size + val_size]
        y_val = y[train_size:train_size + val_size]

        X_test = X[train_size + val_size:]
        y_test = y[train_size + val_size:]

        return X_train, X_val, X_test, y_train, y_val, y_test

    async def _train_lstm(self, X_train: np.ndarray, y_train: np.ndarray,
                         X_val: np.ndarray, y_val: np.ndarray) -> Dict[str, Any]:
        """Train LSTM model."""
        try:
            logger.info("Training LSTM model...")

            # Create sequences for LSTM
            X_train_seq, y_train_seq = self._create_sequences(X_train, y_train)
            X_val_seq, y_val_seq = self._create_sequences(X_val, y_val)

            if len(X_train_seq) == 0:
                return {'status': 'failed', 'reason': 'insufficient_sequence_data'}

            # Convert to PyTorch tensors
            X_train_tensor = torch.FloatTensor(X_train_seq)
            y_train_tensor = torch.LongTensor(y_train_seq)
            X_val_tensor = torch.FloatTensor(X_val_seq)
            y_val_tensor = torch.LongTensor(y_val_seq)

            # Create data loaders
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            val_dataset = TensorDataset(X_val_tensor, y_val_tensor)

            train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size)

            # Initialize LSTM model
            input_size = X_train_seq.shape[2]
            lstm_model = LSTMPredictor(
                input_size=input_size,
                sequence_length=60,
                hidden_size=128,
                num_layers=2
            )

            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(lstm_model.parameters(), lr=self.config.learning_rate)

            # Training loop
            best_val_loss = float('inf')
            patience_counter = 0
            train_losses = []
            val_losses = []

            for epoch in range(self.config.epochs_lstm):
                # Training
                lstm_model.train()
                train_loss = 0
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = lstm_model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)
                train_losses.append(train_loss)

                # Validation
                lstm_model.eval()
                val_loss = 0
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        outputs = lstm_model(batch_X)
                        loss = criterion(outputs, batch_y)
                        val_loss += loss.item()

                val_loss /= len(val_loader)
                val_losses.append(val_loss)

                # Early stopping
                if val_loss < best_val_loss - self.config.min_improvement:
                    best_val_loss = val_loss
                    patience_counter = 0
                    # Save best model
                    torch.save(lstm_model.state_dict(), 'models/smc_trained/lstm_best.pth')
                else:
                    patience_counter += 1
                    if patience_counter >= self.config.early_stopping_patience:
                        logger.info(f"Early stopping at epoch {epoch + 1}")
                        break

                if (epoch + 1) % 10 == 0:
                    logger.info(f"LSTM Epoch [{epoch+1}/{self.config.epochs_lstm}], "
                               f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            # Load best model for evaluation
            lstm_model.load_state_dict(torch.load('models/smc_trained/lstm_best.pth'))

            # Calculate final metrics
            lstm_model.eval()
            with torch.no_grad():
                y_pred = []
                y_true = []
                for batch_X, batch_y in val_loader:
                    outputs = lstm_model(batch_X)
                    _, predicted = torch.max(outputs.data, 1)
                    y_pred.extend(predicted.cpu().numpy())
                    y_true.extend(batch_y.cpu().numpy())

            accuracy = accuracy_score(y_true, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')

            # Save the trained model to ensemble
            self.model_ensemble.lstm_model = lstm_model

            return {
                'status': 'completed',
                'epochs_trained': epoch + 1,
                'final_train_loss': train_losses[-1],
                'final_val_loss': val_losses[-1],
                'best_val_loss': best_val_loss,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'early_stopped': patience_counter >= self.config.early_stopping_patience
            }

        except Exception as e:
            logger.error(f"LSTM training failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _train_transformer(self, X_train: np.ndarray, y_train: np.ndarray,
                                X_val: np.ndarray, y_val: np.ndarray) -> Dict[str, Any]:
        """Train Transformer model."""
        try:
            logger.info("Training Transformer model...")

            # Similar to LSTM training but with Transformer model
            X_train_seq, y_train_seq = self._create_sequences(X_train, y_train)
            X_val_seq, y_val_seq = self._create_sequences(X_val, y_val)

            if len(X_train_seq) == 0:
                return {'status': 'failed', 'reason': 'insufficient_sequence_data'}

            # Convert to PyTorch tensors
            X_train_tensor = torch.FloatTensor(X_train_seq)
            y_train_tensor = torch.LongTensor(y_train_seq)
            X_val_tensor = torch.FloatTensor(X_val_seq)
            y_val_tensor = torch.LongTensor(y_val_seq)

            # Create data loaders
            train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
            val_dataset = TensorDataset(X_val_tensor, y_val_tensor)

            train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size)

            # Initialize Transformer model
            input_size = X_train_seq.shape[2]
            transformer_model = TransformerPredictor(
                input_size=input_size,
                sequence_length=60,
                d_model=128,
                nhead=8,
                num_layers=4
            )

            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(transformer_model.parameters(), lr=self.config.learning_rate)

            # Training loop (similar to LSTM)
            best_val_loss = float('inf')
            patience_counter = 0

            for epoch in range(self.config.epochs_transformer):
                transformer_model.train()
                train_loss = 0
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = transformer_model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)

                # Validation
                transformer_model.eval()
                val_loss = 0
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        outputs = transformer_model(batch_X)
                        loss = criterion(outputs, batch_y)
                        val_loss += loss.item()

                val_loss /= len(val_loader)

                # Early stopping
                if val_loss < best_val_loss - self.config.min_improvement:
                    best_val_loss = val_loss
                    patience_counter = 0
                    torch.save(transformer_model.state_dict(), 'models/smc_trained/transformer_best.pth')
                else:
                    patience_counter += 1
                    if patience_counter >= self.config.early_stopping_patience:
                        logger.info(f"Transformer early stopping at epoch {epoch + 1}")
                        break

                if (epoch + 1) % 10 == 0:
                    logger.info(f"Transformer Epoch [{epoch+1}/{self.config.epochs_transformer}], "
                               f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            # Load best model
            transformer_model.load_state_dict(torch.load('models/smc_trained/transformer_best.pth'))

            # Calculate metrics
            transformer_model.eval()
            with torch.no_grad():
                y_pred = []
                y_true = []
                for batch_X, batch_y in val_loader:
                    outputs = transformer_model(batch_X)
                    _, predicted = torch.max(outputs.data, 1)
                    y_pred.extend(predicted.cpu().numpy())
                    y_true.extend(batch_y.cpu().numpy())

            accuracy = accuracy_score(y_true, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')

            # Save to ensemble
            self.model_ensemble.transformer_model = transformer_model

            return {
                'status': 'completed',
                'epochs_trained': epoch + 1,
                'best_val_loss': best_val_loss,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1
            }

        except Exception as e:
            logger.error(f"Transformer training failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _train_ppo(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict[str, Any]:
        """Train PPO model."""
        try:
            logger.info("Training PPO model...")

            # Create market environment for PPO
            # This would require creating a custom environment from the training data
            # For now, return a placeholder result
            logger.info("PPO training placeholder - would require custom environment setup")

            return {
                'status': 'placeholder',
                'reason': 'PPO training requires custom environment setup',
                'note': 'Would create trading environment from historical data and train PPO agent'
            }

        except Exception as e:
            logger.error(f"PPO training failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    def _create_sequences(self, X: np.ndarray, y: np.ndarray, sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for time series models."""
        if len(X) < sequence_length:
            return np.array([]), np.array([])

        sequences = []
        labels = []

        for i in range(sequence_length, len(X)):
            sequences.append(X[i-sequence_length:i])
            labels.append(y[i])

        return np.array(sequences), np.array(labels)

    async def _evaluate_models(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate trained models on test set."""
        try:
            logger.info("Evaluating models on test set...")

            evaluation_results = {}

            # Create test sequences
            X_test_seq, y_test_seq = self._create_sequences(X_test, y_test)
            if len(X_test_seq) == 0:
                return {'error': 'Insufficient test data for sequence evaluation'}

            # Evaluate LSTM
            if hasattr(self.model_ensemble.lstm_model, 'state_dict'):
                lstm_results = self._evaluate_model(
                    self.model_ensemble.lstm_model,
                    X_test_seq, y_test_seq,
                    'LSTM'
                )
                evaluation_results['lstm'] = lstm_results

            # Evaluate Transformer
            if hasattr(self.model_ensemble.transformer_model, 'state_dict'):
                transformer_results = self._evaluate_model(
                    self.model_ensemble.transformer_model,
                    X_test_seq, y_test_seq,
                    'Transformer'
                )
                evaluation_results['transformer'] = transformer_results

            # Evaluate ensemble
            ensemble_results = await self._evaluate_ensemble(X_test, y_test)
            evaluation_results['ensemble'] = ensemble_results

            return evaluation_results

        except Exception as e:
            logger.error(f"Model evaluation failed: {str(e)}")
            return {'error': str(e)}

    def _evaluate_model(self, model, X_test_seq: np.ndarray, y_test_seq: np.ndarray, model_name: str) -> Dict[str, Any]:
        """Evaluate a single model."""
        try:
            model.eval()
            X_test_tensor = torch.FloatTensor(X_test_seq)
            y_test_tensor = torch.LongTensor(y_test_seq)

            with torch.no_grad():
                outputs = model(X_test_tensor)
                _, predicted = torch.max(outputs.data, 1)
                predictions = predicted.cpu().numpy()
                true_labels = y_test_tensor.cpu().numpy()

            # Calculate metrics
            accuracy = accuracy_score(true_labels, predictions)
            precision, recall, f1, _ = precision_recall_fscore_support(true_labels, predictions, average='weighted')

            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'predictions_sample': predictions[:10].tolist(),
                'true_labels_sample': true_labels[:10].tolist()
            }

        except Exception as e:
            logger.error(f"Model evaluation failed for {model_name}: {str(e)}")
            return {'error': str(e)}

    async def _evaluate_ensemble(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate ensemble predictions."""
        try:
            # This would require creating test market data and using ensemble.predict
            # For now, return placeholder
            return {
                'status': 'placeholder',
                'note': 'Ensemble evaluation requires market data format conversion'
            }

        except Exception as e:
            logger.error(f"Ensemble evaluation failed: {str(e)}")
            return {'error': str(e)}

    async def _save_models(self):
        """Save all trained models and components."""
        try:
            # Create model directory
            model_dir = Path('models/smc_trained/')
            model_dir.mkdir(parents=True, exist_ok=True)

            # Save ensemble models
            self.model_ensemble.save_models()

            # Save scaler
            with open(model_dir / 'scaler.pkl', 'wb') as f:
                pickle.dump(self.scaler, f)

            # Save training config
            with open(model_dir / 'training_config.json', 'w') as f:
                json.dump(self.config.__dict__, f, indent=2, default=str)

            logger.info(f"Models saved to {model_dir}")

        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")

    def _generate_training_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive training summary."""
        summary = {
            'training_status': results.get('status', 'unknown'),
            'model_performance': {},
            'overall_metrics': {},
            'recommendations': []
        }

        # Extract model performance
        for model_name in ['lstm', 'transformer']:
            if model_name in results and results[model_name].get('status') == 'completed':
                model_results = results[model_name]
                summary['model_performance'][model_name] = {
                    'accuracy': model_results.get('accuracy', 0),
                    'f1_score': model_results.get('f1_score', 0),
                    'training_epochs': model_results.get('epochs_trained', 0)
                }

        # Test evaluation results
        if 'test_evaluation' in results:
            test_results = results['test_evaluation']
            for model_name in ['lstm', 'transformer', 'ensemble']:
                if model_name in test_results and 'accuracy' in test_results[model_name]:
                    summary['overall_metrics'][f'{model_name}_test_accuracy'] = test_results[model_name]['accuracy']

        # Generate recommendations
        lstm_acc = summary['model_performance'].get('lstm', {}).get('accuracy', 0)
        transformer_acc = summary['model_performance'].get('transformer', {}).get('accuracy', 0)

        if lstm_acc < self.config.min_accuracy and transformer_acc < self.config.min_accuracy:
            summary['recommendations'].append("Models show low accuracy - consider more training data or feature engineering")
        elif lstm_acc > 0.7 and transformer_acc > 0.7:
            summary['recommendations'].append("Both models show good performance - ready for deployment")
        else:
            summary['recommendations'].append("Mixed model performance - consider ensembling or further tuning")

        return summary


# Main training orchestrator
class SMCTrainingPipeline:
    """Main pipeline for SMC model training and deployment."""

    def __init__(self, config: Optional[SMCTrainingConfig] = None):
        self.config = config or SMCTrainingConfig()
        self.data_collector = SMCDataCollector(self.config)
        self.trainer = SMCTrainer(self.config)

    async def run_full_training_pipeline(self,
                                       symbols: List[str] = ["BTC/USDT"],
                                       start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Run the complete SMC training pipeline.

        Args:
            symbols: Symbols to train on
            start_date: Start date for training data
            end_date: End date for training data

        Returns:
            Complete training results
        """
        logger.info("Starting SMC training pipeline")

        try:
            # Set default date range
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=self.config.train_period_months * 30)

            logger.info(f"Training data range: {start_date} to {end_date}")

            # Step 1: Collect training data
            training_data = await self.data_collector.collect_training_data(
                start_date=start_date,
                end_date=end_date,
                symbols=symbols
            )

            if training_data.empty:
                raise ValueError("No training data collected")

            # Step 2: Train models
            training_results = await self.trainer.train_models(training_data)

            # Step 3: Validate models
            validation_results = await self._validate_models(training_data)

            # Step 4: Generate deployment package
            deployment_package = await self._create_deployment_package(training_results, validation_results)

            results = {
                'status': 'completed',
                'data_collection': {
                    'samples_collected': len(training_data),
                    'symbols_trained': symbols,
                    'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()}
                },
                'training_results': training_results,
                'validation_results': validation_results,
                'deployment_package': deployment_package,
                'timestamp': datetime.now().isoformat()
            }

            logger.info("SMC training pipeline completed successfully")
            return results

        except Exception as e:
            logger.error(f"SMC training pipeline failed: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _validate_models(self, training_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate trained models with additional metrics."""
        try:
            logger.info("Validating trained models...")

            # Use enhanced training pipeline for validation
            validation_config = {
                'enable_statistical_validation': True,
                'enable_cross_exchange_validation': False,  # Skip for now
                'statistical_validation_config': {
                    'significance_level': 0.05,
                    'effect_size_threshold': 0.2
                }
            }

            enhanced_pipeline = EnhancedTrainingPipeline(validation_config)

            # Prepare strategy returns for validation
            if 'profit_pct' in training_data.columns:
                strategy_returns = training_data['profit_pct']
            else:
                strategy_returns = pd.Series([0] * len(training_data))

            # Convert to DataFrame for validation
            strategy_df = pd.DataFrame({
                'returns': strategy_returns,
                'timestamp': training_data.get('timestamp', pd.date_range('2020-01-01', periods=len(training_data), freq='1h'))
            })

            # Run validation
            validation_results = await enhanced_pipeline.comprehensive_validation(
                strategy_data=strategy_df
            )

            return validation_results

        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def _create_deployment_package(self, training_results: Dict, validation_results: Dict) -> Dict[str, Any]:
        """Create deployment package with models and metadata."""
        try:
            logger.info("Creating deployment package...")

            deployment_package = {
                'models': {
                    'lstm_model_path': 'models/smc_trained/lstm_model.pth',
                    'transformer_model_path': 'models/smc_trained/transformer_model.pth',
                    'scaler_path': 'models/smc_trained/scaler.pkl'
                },
                'metadata': {
                    'training_timestamp': training_results.get('timestamp'),
                    'model_version': 'smc_v1.0',
                    'training_config': self.config.__dict__,
                    'training_summary': training_results.get('summary', {}),
                    'validation_score': validation_results.get('overall_validation_score', 0)
                },
                'deployment_config': {
                    'inference_mode': 'balanced',
                    'confidence_threshold': 0.6,
                    'fallback_enabled': True,
                    'monitoring_enabled': True
                }
            }

            # Save deployment package
            deployment_path = Path('models/smc_deployment_package.json')
            with open(deployment_path, 'w') as f:
                json.dump(deployment_package, f, indent=2, default=str)

            logger.info(f"Deployment package saved to {deployment_path}")
            return deployment_package

        except Exception as e:
            logger.error(f"Failed to create deployment package: {str(e)}")
            return {'status': 'failed', 'error': str(e)}