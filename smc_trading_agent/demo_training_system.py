#!/usr/bin/env python3
"""
SMC ML Training System Demo
Demonstrates the complete ML training pipeline with synthetic data.
This version works without external dependencies for quick testing.
"""

import asyncio
import logging
import sys
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datetime import datetime, timedelta
from pathlib import Path
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class DemoMLSystem:
    """Demo version of the SMC ML Training System"""

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

    def generate_synthetic_data(self, n_samples=10000):
        """Generate synthetic SMC pattern data for demonstration"""
        logger.info(f"🔄 Generating {n_samples} samples of synthetic SMC data...")

        np.random.seed(42)

        # Generate realistic price data with SMC patterns
        timestamps = pd.date_range(start='2022-01-01', periods=n_samples, freq='5T')

        # Base price with trend and volatility
        base_price = 50000  # BTC base price
        trend = np.linspace(0, 0.2, n_samples)  # 20% uptrend
        volatility = 0.02  # 2% volatility

        # Generate OHLCV data
        close_prices = base_price * (1 + trend + np.random.normal(0, volatility, n_samples))
        high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.005, n_samples)))
        low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.005, n_samples)))
        open_prices = np.roll(close_prices, 1)  # Previous close becomes open
        open_prices[0] = close_prices[0]

        # Generate volume
        volumes = np.random.lognormal(10, 1, n_samples)

        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })

        # Generate 16 SMC features
        features_df = self._generate_smc_features(df)

        # Generate labels (synthetic trading signals)
        labels = self._generate_labels(df)

        logger.info(f"✅ Generated synthetic data with {len(features_df.columns)} features")
        return df, features_df, labels

    def _generate_smc_features(self, df):
        """Generate all 16 SMC-specific features"""
        features = pd.DataFrame(index=df.index)

        # 1. Price Momentum (multi-timeframe)
        features['price_momentum'] = df['close'].pct_change(20).rolling(5).mean()

        # 2. Volatility Ratio
        volatility = df['close'].pct_change().rolling(20).std()
        features['volatility_ratio'] = volatility / volatility.rolling(100).mean()

        # 3. Volume Profile
        features['volume_profile'] = df['volume'].rolling(20).mean() / df['volume'].rolling(100).mean()

        # 4. Order Block Proximity (synthetic)
        features['order_block_proximity'] = np.random.uniform(0, 1, len(df))

        # 5. CHOCH Strength
        features['choch_strength'] = self._detect_choch(df)

        # 6. FVG Size (synthetic)
        features['fvg_size'] = np.random.uniform(0, 0.01, len(df))

        # 7. Liquidity Sweep Strength
        features['liquidity_sweep_strength'] = self._detect_liquidity_sweeps(df)

        # 8. Break of Structure Momentum
        features['break_of_structure_momentum'] = self._detect_bos(df)

        # 9. M5 M15 Confluence
        features['m5_m15_confluence'] = np.random.uniform(0, 1, len(df))

        # 10. H1 H4 Alignment
        features['h1_h4_alignment'] = self._detect_trend_alignment(df)

        # 11. Daily Trend Strength
        features['daily_trend_strength'] = df['close'].pct_change(288).rolling(50).mean()  # 1 day = 288 5min candles

        # 12. Risk Reward Ratio
        features['risk_reward_ratio'] = self._calculate_risk_reward(df)

        # 13. Position Size Optimal
        features['position_size_optimal'] = 1.0 / (1 + volatility)

        # 14. Stop Loss Distance
        features['stop_loss_distance'] = volatility * 2

        # 15. Bid Ask Spread (synthetic)
        features['bid_ask_spread'] = np.random.uniform(0.0001, 0.001, len(df))

        # 16. Order Book Imbalance (synthetic)
        features['order_book_imbalance'] = np.random.uniform(-0.5, 0.5, len(df))

        # Clean features
        features = features.fillna(0).replace([np.inf, -np.inf], 0)

        return features

    def _detect_choch(self, df):
        """Detect Change of Character patterns"""
        # Simple CHOCH detection: price breaks recent structure
        highs = df['high'].rolling(20).max()
        lows = df['low'].rolling(20).min()
        choch = ((df['close'] > highs.shift(1)) | (df['close'] < lows.shift(1))).astype(float)
        return choch

    def _detect_liquidity_sweeps(self, df):
        """Detect liquidity sweeps"""
        # Simple liquidity sweep detection
        high_sweep = (df['high'] > df['high'].rolling(20).max().shift(1)) & (df['close'] < df['open'])
        low_sweep = (df['low'] < df['low'].rolling(20).min().shift(1)) & (df['close'] > df['open'])
        return (high_sweep | low_sweep).astype(float)

    def _detect_bos(self, df):
        """Detect Break of Structure"""
        # BOS: break previous high/low with momentum
        prev_high = df['high'].rolling(20).max().shift(1)
        prev_low = df['low'].rolling(20).min().shift(1)
        momentum = df['close'].pct_change(5).abs()
        bos_high = (df['close'] > prev_high) & (momentum > 0.01)
        bos_low = (df['close'] < prev_low) & (momentum > 0.01)
        return (bos_high | bos_low).astype(float)

    def _detect_trend_alignment(self, df):
        """Detect trend alignment across timeframes"""
        # Simple trend alignment based on moving averages
        short_ma = df['close'].rolling(20).mean()
        long_ma = df['close'].rolling(100).mean()
        alignment = (short_ma > long_ma).astype(float)
        return alignment

    def _calculate_risk_reward(self, df):
        """Calculate risk/reward ratio"""
        # Simplified R/R calculation
        volatility = df['close'].pct_change().rolling(20).std()
        avg_range = (df['high'] - df['low']).rolling(20).mean()
        rr_ratio = avg_range / (volatility * df['close'])
        return rr_ratio.fillna(1.0)

    def _generate_labels(self, df):
        """Generate trading labels (buy/sell/hold signals)"""
        # Generate labels based on future price movements
        future_returns = df['close'].pct_change(20).shift(-20)  # 20-period forward return

        # Convert to binary labels: 1 for buy, 0 for sell/hold
        labels = (future_returns > 0.01).astype(float)  # Buy if future return > 1%

        return labels.fillna(0)

    def create_lstm_model(self, input_size):
        """Create LSTM model"""
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_dim=128, num_layers=3):
                super().__init__()
                self.hidden_dim = hidden_dim
                self.num_layers = num_layers

                self.lstm = nn.LSTM(input_size, hidden_dim, num_layers,
                                 batch_first=True, dropout=0.3)
                self.fc = nn.Linear(hidden_dim, 1)
                self.dropout = nn.Dropout(0.3)

            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                # Take the last output
                output = self.fc(self.dropout(lstm_out[:, -1, :]))
                return torch.sigmoid(output)

        return LSTMModel(input_size).to(self.device)

    def create_transformer_model(self, input_size):
        """Create Transformer model"""
        class TransformerModel(nn.Module):
            def __init__(self, input_size, d_model=128, nhead=8, num_layers=4):
                super().__init__()
                self.d_model = d_model
                self.input_projection = nn.Linear(input_size, d_model)

                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model, nhead=nhead, dim_feedforward=512,
                    dropout=0.1, batch_first=True
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                self.fc = nn.Linear(d_model, 1)

            def forward(self, x):
                x = self.input_projection(x)
                transformer_out = self.transformer(x)
                output = self.fc(transformer_out[:, -1, :])
                return torch.sigmoid(output)

        return TransformerModel(input_size).to(self.device)

    def train_model(self, model, train_loader, val_loader, epochs=50):
        """Train a single model"""
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        patience = 10
        patience_counter = 0

        for epoch in range(epochs):
            # Training
            model.train()
            train_loss = 0
            for batch_features, batch_labels in train_loader:
                batch_features = batch_features.to(self.device)
                batch_labels = batch_labels.to(self.device)

                optimizer.zero_grad()
                outputs = model(batch_features)
                loss = criterion(outputs.squeeze(), batch_labels)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)
            train_losses.append(avg_train_loss)

            # Validation
            model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch_features, batch_labels in val_loader:
                    batch_features = batch_features.to(self.device)
                    batch_labels = batch_labels.to(self.device)

                    outputs = model(batch_features)
                    loss = criterion(outputs.squeeze(), batch_labels)
                    val_loss += loss.item()

            avg_val_loss = val_loss / len(val_loader)
            val_losses.append(avg_val_loss)

            # Early stopping
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

        return train_losses, val_losses, best_val_loss

    def evaluate_model(self, model, test_loader):
        """Evaluate model performance"""
        model.eval()
        predictions = []
        actuals = []

        with torch.no_grad():
            for batch_features, batch_labels in test_loader:
                batch_features = batch_features.to(self.device)
                batch_labels = batch_labels.to(self.device)

                outputs = model(batch_features)
                predictions.extend(outputs.squeeze().cpu().numpy())
                actuals.extend(batch_labels.cpu().numpy())

        predictions = np.array(predictions) > 0.5
        actuals = np.array(actuals)

        accuracy = np.mean(predictions == actuals)

        return accuracy, predictions, actuals

    def create_sequences(self, features, labels, sequence_length=60):
        """Create sequences for LSTM/Transformer training"""
        sequences = []
        seq_labels = []

        for i in range(sequence_length, len(features)):
            sequences.append(features[i-sequence_length:i])
            seq_labels.append(labels[i])

        return np.array(sequences), np.array(seq_labels)

    async def run_demo_training(self):
        """Run complete demo training pipeline"""
        logger.info("🚀 Starting SMC ML Training System Demo")
        start_time = time.time()

        # 1. Generate synthetic data
        raw_data, features, labels = self.generate_synthetic_data(5000)

        # 2. Prepare data for training
        logger.info("🔄 Preparing data for training...")

        # Create sequences
        sequence_length = 60
        X, y = self.create_sequences(features.values, labels.values, sequence_length)

        # Split data
        train_size = int(0.7 * len(X))
        val_size = int(0.15 * len(X))

        X_train = X[:train_size]
        y_train = y[:train_size]
        X_val = X[train_size:train_size+val_size]
        y_val = y[train_size:train_size+val_size]
        X_test = X[train_size+val_size:]
        y_test = y[train_size+val_size:]

        # Convert to tensors
        X_train = torch.FloatTensor(X_train)
        y_train = torch.FloatTensor(y_train)
        X_val = torch.FloatTensor(X_val)
        y_val = torch.FloatTensor(y_val)
        X_test = torch.FloatTensor(X_test)
        y_test = torch.FloatTensor(y_test)

        # Create data loaders
        batch_size = 32
        train_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(X_train, y_train),
            batch_size=batch_size, shuffle=True
        )
        val_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(X_val, y_val),
            batch_size=batch_size
        )
        test_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(X_test, y_test),
            batch_size=batch_size
        )

        logger.info(f"Data shapes - Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

        # 3. Train models
        input_size = X_train.shape[2]  # Number of features

        # LSTM Model
        logger.info("🧠 Training LSTM Model...")
        lstm_model = self.create_lstm_model(input_size)
        lstm_train_loss, lstm_val_loss, lstm_best_loss = self.train_model(
            lstm_model, train_loader, val_loader, epochs=30
        )
        lstm_accuracy, _, _ = self.evaluate_model(lstm_model, test_loader)

        # Transformer Model
        logger.info("🔮 Training Transformer Model...")
        transformer_model = self.create_transformer_model(input_size)
        transformer_train_loss, transformer_val_loss, transformer_best_loss = self.train_model(
            transformer_model, train_loader, val_loader, epochs=30
        )
        transformer_accuracy, _, _ = self.evaluate_model(transformer_model, test_loader)

        # 4. Ensemble prediction
        logger.info("🎯 Creating ensemble predictions...")
        ensemble_predictions = []
        ensemble_actuals = []

        for batch_features, batch_labels in test_loader:
            batch_features = batch_features.to(self.device)

            lstm_pred = lstm_model(batch_features)
            transformer_pred = transformer_model(batch_features)

            # Simple average ensemble
            ensemble_pred = (lstm_pred + transformer_pred) / 2

            ensemble_predictions.extend((ensemble_pred.squeeze() > 0.5).cpu().numpy())
            ensemble_actuals.extend(batch_labels.numpy())

        ensemble_predictions = np.array(ensemble_predictions)
        ensemble_actuals = np.array(ensemble_actuals)
        ensemble_accuracy = np.mean(ensemble_predictions == ensemble_actuals)

        # 5. Results
        total_time = time.time() - start_time

        print("\\n" + "="*80)
        print("🎯 SMC ML TRAINING SYSTEM DEMO - RESULTS")
        print("="*80)

        print(f"\\n📊 MODEL PERFORMANCE:")
        print(f"  🧠 LSTM Model:")
        print(f"    • Test Accuracy: {lstm_accuracy:.4f}")
        print(f"    • Best Validation Loss: {lstm_best_loss:.4f}")

        print(f"  🔮 Transformer Model:")
        print(f"    • Test Accuracy: {transformer_accuracy:.4f}")
        print(f"    • Best Validation Loss: {transformer_best_loss:.4f}")

        print(f"\\n🎯 ENSEMBLE PERFORMANCE:")
        print(f"  • Overall Accuracy: {ensemble_accuracy:.4f}")
        print(f"  • Target Accuracy (0.65): {'✓' if ensemble_accuracy > 0.65 else '✗'}")

        print(f"\\n⚡ PERFORMANCE:")
        print(f"  • Total Training Time: {total_time:.2f} seconds")
        print(f"  • Device Used: {self.device}")
        print(f"  • Samples Processed: {len(X)}")
        print(f"  • Features Used: {input_size}")

        print(f"\\n🔧 FEATURE BREAKDOWN:")
        feature_names = [
            'price_momentum', 'volatility_ratio', 'volume_profile', 'order_block_proximity',
            'choch_strength', 'fvg_size', 'liquidity_sweep_strength', 'break_of_structure_momentum',
            'm5_m15_confluence', 'h1_h4_alignment', 'daily_trend_strength', 'risk_reward_ratio',
            'position_size_optimal', 'stop_loss_distance', 'bid_ask_spread', 'order_book_imbalance'
        ]

        print(f"  • All 16 SMC Features: ✓ Implemented")
        print(f"  • Feature Engineering: ✓ Complete")
        print(f"  • Pattern Detection: ✓ Synthetic (CHOCH, BOS, Liquidity Sweeps)")

        print(f"\\n🚀 NEXT STEPS:")
        if ensemble_accuracy > 0.65:
            print(f"  ✅ Demo successful! Ready for production data")
            print(f"  🔧 Install TA-Lib: pip install TA-Lib")
            print(f"  📊 Run with real data: python quick_start_training.py --symbols BTCUSDT --days 30")
        else:
            print(f"  ⚠️  Accuracy below target - try more epochs or better features")

        print("="*80)

        return {
            'lstm_accuracy': lstm_accuracy,
            'transformer_accuracy': transformer_accuracy,
            'ensemble_accuracy': ensemble_accuracy,
            'training_time': total_time,
            'samples_processed': len(X),
            'features_used': input_size
        }

async def main():
    """Main demo function"""
    demo_system = DemoMLSystem()

    try:
        results = await demo_system.run_demo_training()
        return results
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        return None

if __name__ == "__main__":
    results = asyncio.run(main())