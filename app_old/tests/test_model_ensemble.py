"""
Test suite for the Model Ensemble system.

Tests all components of the ensemble architecture including LSTM, Transformer, PPO models,
market condition analysis, and adaptive selection logic.
"""

import pytest
import numpy as np
import pandas as pd
import torch
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime, timedelta

from smc_trading_agent.decision_engine.model_ensemble import (
    ModelEnsemble,
    AdaptiveModelSelector,
    MarketConditionAnalyzer,
    LSTMPredictor,
    TransformerPredictor,
    MarketEnvironment
)


class TestMarketConditionAnalyzer:
    """Test market condition analysis functionality."""
    
    def setup_method(self):
        self.analyzer = MarketConditionAnalyzer()
        
    def create_sample_data(self, n_samples=100, volatility_type="low", trend_type="sideways"):
        """Create sample market data for testing."""
        np.random.seed(42)
        
        if trend_type == "uptrend":
            trend = np.linspace(100, 120, n_samples)
        elif trend_type == "downtrend":
            trend = np.linspace(120, 100, n_samples)
        else:  # sideways
            trend = np.ones(n_samples) * 110
            
        if volatility_type == "high":
            noise = np.random.normal(0, 5, n_samples)
        else:  # low
            noise = np.random.normal(0, 1, n_samples)
            
        prices = trend + noise
        dates = pd.date_range('2023-01-01', periods=n_samples, freq='1H')
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 0.1, n_samples),
            'high': prices + np.abs(np.random.normal(0, 0.5, n_samples)),
            'low': prices - np.abs(np.random.normal(0, 0.5, n_samples)),
            'close': prices,
            'volume': np.random.uniform(1000, 10000, n_samples)
        })
    
    def test_calculate_volatility_low_vol(self):
        """Test volatility calculation for low volatility scenario."""
        data = self.create_sample_data(volatility_type="low")
        volatility = self.analyzer.calculate_volatility(data['close'])
        assert 0.0 <= volatility <= 0.3  # Low volatility expected
        
    def test_calculate_volatility_high_vol(self):
        """Test volatility calculation for high volatility scenario."""
        data = self.create_sample_data(volatility_type="high")
        volatility = self.analyzer.calculate_volatility(data['close'])
        assert volatility > 0.3  # High volatility expected
        
    def test_calculate_trend_strength_uptrend(self):
        """Test trend strength calculation for uptrend."""
        data = self.create_sample_data(trend_type="uptrend")
        strength, direction = self.analyzer.calculate_trend_strength(data['close'])
        assert strength > 0
        assert direction in ["uptrend", "downtrend", "sideways"]
        
    def test_calculate_trend_strength_sideways(self):
        """Test trend strength calculation for sideways market."""
        data = self.create_sample_data(trend_type="sideways")
        strength, direction = self.analyzer.calculate_trend_strength(data['close'])
        assert 0 <= strength <= 50  # Lower trend strength expected for sideways
        
    def test_get_market_regime_combinations(self):
        """Test market regime identification for various combinations."""
        # High vol uptrend
        data = self.create_sample_data(volatility_type="high", trend_type="uptrend")
        regime = self.analyzer.get_market_regime(data)
        assert "volatility" in regime
        assert "trend_strength" in regime
        assert "trend_direction" in regime
        assert "regime" in regime
        
        # Low vol sideways
        data = self.create_sample_data(volatility_type="low", trend_type="sideways")
        regime = self.analyzer.get_market_regime(data)
        assert regime["regime"] == "low_vol_sideways"
        
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        short_data = pd.DataFrame({'close': [100, 101, 102]})
        volatility = self.analyzer.calculate_volatility(short_data['close'])
        assert volatility == 0.0
        
        strength, direction = self.analyzer.calculate_trend_strength(short_data['close'])
        assert strength == 0.0
        assert direction == "sideways"


class TestLSTMPredictor:
    """Test LSTM model functionality."""
    
    def setup_method(self):
        self.input_size = 5
        self.model = LSTMPredictor(self.input_size, hidden_size=32, num_layers=1)
        
    def test_model_initialization(self):
        """Test LSTM model initialization."""
        assert self.model.input_size == self.input_size
        assert self.model.hidden_size == 32
        assert self.model.num_layers == 1
        assert isinstance(self.model.lstm, torch.nn.LSTM)
        
    def test_forward_pass(self):
        """Test forward pass through LSTM."""
        batch_size = 2
        sequence_length = 10
        x = torch.randn(batch_size, sequence_length, self.input_size)
        output = self.model(x)
        
        assert output.shape == (batch_size, 3)  # Buy, Hold, Sell
        assert torch.allclose(output.sum(dim=1), torch.ones(batch_size))  # Softmax output
        
    def test_predict_direction(self):
        """Test direction prediction."""
        x = torch.randn(1, 10, self.input_size)
        predictions, confidences = self.model.predict_direction(x)
        
        assert predictions.shape == (1,)
        assert confidences.shape == (1,)
        assert 0 <= predictions.item() <= 2
        assert 0 <= confidences.item() <= 1


class TestTransformerPredictor:
    """Test Transformer model functionality."""
    
    def setup_method(self):
        self.input_size = 5
        self.model = TransformerPredictor(self.input_size, d_model=32, nhead=4, num_layers=2)
        
    def test_model_initialization(self):
        """Test Transformer model initialization."""
        assert self.model.input_size == self.input_size
        assert self.model.d_model == 32
        assert isinstance(self.model.transformer, torch.nn.TransformerEncoder)
        
    def test_forward_pass(self):
        """Test forward pass through Transformer."""
        batch_size = 2
        sequence_length = 10
        x = torch.randn(batch_size, sequence_length, self.input_size)
        output = self.model(x)
        
        assert output.shape == (batch_size, 3)  # Buy, Hold, Sell
        assert torch.allclose(output.sum(dim=1), torch.ones(batch_size))  # Softmax output
        
    def test_predict_direction(self):
        """Test direction prediction."""
        x = torch.randn(1, 10, self.input_size)
        predictions, confidences = self.model.predict_direction(x)
        
        assert predictions.shape == (1,)
        assert confidences.shape == (1,)
        assert 0 <= predictions.item() <= 2
        assert 0 <= confidences.item() <= 1


class TestMarketEnvironment:
    """Test PPO market environment."""
    
    def setup_method(self):
        # Create sample market data
        np.random.seed(42)
        n_samples = 100
        data = pd.DataFrame({
            'open': np.random.uniform(100, 200, n_samples),
            'high': np.random.uniform(150, 250, n_samples),
            'low': np.random.uniform(50, 150, n_samples),
            'close': np.random.uniform(100, 200, n_samples),
            'volume': np.random.uniform(1000, 10000, n_samples)
        })
        self.env = MarketEnvironment(data)
        
    def test_environment_initialization(self):
        """Test environment initialization."""
        assert self.env.initial_balance == 10000.0
        assert self.env.current_step == 0
        assert self.env.balance == 10000.0
        assert self.env.position == 0.0
        
    def test_reset(self):
        """Test environment reset."""
        # Change some state
        self.env.current_step = 10
        self.env.balance = 5000
        self.env.position = 1.0
        
        obs, info = self.env.reset()
        assert self.env.current_step == 0
        assert self.env.balance == 10000.0
        assert self.env.position == 0.0
        assert isinstance(obs, np.ndarray)
        
    def test_step(self):
        """Test environment step."""
        obs, info = self.env.reset()
        action = np.array([0.8])  # Buy action
        
        next_obs, reward, done, truncated, info = self.env.step(action)
        
        assert isinstance(next_obs, np.ndarray)
        assert isinstance(reward, (int, float))
        assert isinstance(done, bool)
        assert isinstance(truncated, bool)
        assert self.env.current_step == 1


class TestModelEnsemble:
    """Test the main ensemble functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_size = 5
        self.ensemble = ModelEnsemble(
            input_size=self.input_size,
            sequence_length=20,
            model_save_path=self.temp_dir
        )
        
    def teardown_method(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_training_data(self, n_samples=100):
        """Create sample training data."""
        np.random.seed(42)
        
        # Create features
        features = np.random.randn(n_samples, self.input_size)
        
        # Create target (price direction: 0=Buy, 1=Hold, 2=Sell)
        target = np.random.choice([0, 1, 2], n_samples)
        
        # Combine into DataFrame
        feature_cols = [f'feature_{i}' for i in range(self.input_size)]
        data = pd.DataFrame(features, columns=feature_cols)
        data['close'] = np.random.uniform(100, 200, n_samples)
        data['target'] = target
        
        return data
        
    def test_ensemble_initialization(self):
        """Test ensemble initialization."""
        assert self.ensemble.input_size == self.input_size
        assert self.ensemble.sequence_length == 20
        assert isinstance(self.ensemble.lstm_model, LSTMPredictor)
        assert isinstance(self.ensemble.transformer_model, TransformerPredictor)
        assert isinstance(self.ensemble.market_analyzer, MarketConditionAnalyzer)
        
    def test_prepare_sequences(self):
        """Test sequence preparation for training."""
        data = self.create_training_data(n_samples=50)
        X, y = self.ensemble.prepare_sequences(data)
        
        expected_sequences = len(data) - self.ensemble.sequence_length
        if expected_sequences > 0:
            assert X.shape[0] == expected_sequences
            assert X.shape[1] == self.ensemble.sequence_length
            assert X.shape[2] == self.input_size
            assert len(y) == expected_sequences
            
    def test_insufficient_data_for_sequences(self):
        """Test behavior with insufficient data for sequences."""
        data = self.create_training_data(n_samples=10)  # Less than sequence_length
        X, y = self.ensemble.prepare_sequences(data)
        
        assert len(X) == 0
        assert len(y) == 0
        
    @patch('smc_trading_agent.decision_engine.model_ensemble.PPO')
    def test_train_lstm(self, mock_ppo):
        """Test LSTM training."""
        data = self.create_training_data(n_samples=100)
        
        # Mock training to avoid actual training time
        with patch.object(self.ensemble.lstm_model, 'train'):
            with patch.object(self.ensemble, 'prepare_sequences') as mock_prepare:
                # Mock sufficient data
                mock_prepare.return_value = (
                    np.random.randn(50, 20, self.input_size),
                    np.random.choice([0, 1, 2], 50)
                )
                
                self.ensemble.train_lstm(data, epochs=2, batch_size=4)
                
                # Check that performance was updated
                assert "lstm" in self.ensemble.model_performance
                assert "accuracy" in self.ensemble.model_performance["lstm"]
                
    @patch('smc_trading_agent.decision_engine.model_ensemble.PPO')
    def test_train_transformer(self, mock_ppo):
        """Test Transformer training."""
        data = self.create_training_data(n_samples=100)
        
        with patch.object(self.ensemble.transformer_model, 'train'):
            with patch.object(self.ensemble, 'prepare_sequences') as mock_prepare:
                mock_prepare.return_value = (
                    np.random.randn(50, 20, self.input_size),
                    np.random.choice([0, 1, 2], 50)
                )
                
                self.ensemble.train_transformer(data, epochs=2, batch_size=4)
                
                assert "transformer" in self.ensemble.model_performance
                assert "accuracy" in self.ensemble.model_performance["transformer"]
                
    @patch('smc_trading_agent.decision_engine.model_ensemble.PPO')
    @patch('smc_trading_agent.decision_engine.model_ensemble.DummyVecEnv')
    def test_train_ppo(self, mock_vec_env, mock_ppo_class):
        """Test PPO training."""
        data = self.create_training_data(n_samples=100)
        
        # Mock PPO model
        mock_ppo_instance = Mock()
        mock_ppo_instance.learn = Mock()
        mock_ppo_instance.predict = Mock(return_value=(np.array([0.5]), None))
        mock_ppo_class.return_value = mock_ppo_instance
        
        # Mock environment
        mock_env = Mock()
        mock_env.reset = Mock(return_value=np.zeros(self.input_size))
        mock_env.step = Mock(return_value=(np.zeros(self.input_size), 0.1, True, {}))
        mock_vec_env.return_value = mock_env
        
        self.ensemble.train_ppo(data, total_timesteps=100)
        
        assert self.ensemble.ppo_model is not None
        assert "ppo" in self.ensemble.model_performance
        
    def test_get_model_weights_high_volatility(self):
        """Test model weight calculation for high volatility."""
        market_conditions = {
            "volatility": 0.4,
            "trend_strength": 30,
            "trend_direction": "uptrend",
            "regime": "high_vol_uptrend"
        }
        
        weights = self.ensemble.get_model_weights(market_conditions)
        
        assert "lstm" in weights
        assert "transformer" in weights
        assert "ppo" in weights
        assert abs(sum(weights.values()) - 1.0) < 1e-6  # Weights sum to 1
        assert all(w >= 0.1 for w in weights.values())  # Minimum weight constraint
        
    def test_get_model_weights_sideways_market(self):
        """Test model weight calculation for sideways market."""
        market_conditions = {
            "volatility": 0.1,
            "trend_strength": 10,
            "trend_direction": "sideways",
            "regime": "low_vol_sideways"
        }
        
        weights = self.ensemble.get_model_weights(market_conditions)
        
        # In sideways markets, LSTM should get higher weight
        assert weights["lstm"] > weights["transformer"]
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        
    def test_predict_with_insufficient_data(self):
        """Test prediction with insufficient data."""
        short_data = pd.DataFrame({
            'close': [100, 101, 102],
            'feature_0': [1, 2, 3]
        })
        
        result = self.ensemble.predict(short_data)
        
        assert result["action"] == "HOLD"
        assert result["confidence"] == 0.0
        assert "market_conditions" in result
        assert "model_weights" in result
        
    def test_predict_with_sufficient_data(self):
        """Test prediction with sufficient data."""
        data = self.create_training_data(n_samples=100)
        
        # Mock the individual model predictions
        with patch.object(self.ensemble.lstm_model, 'predict_direction') as mock_lstm:
            with patch.object(self.ensemble.transformer_model, 'predict_direction') as mock_transformer:
                mock_lstm.return_value = (torch.tensor([0]), torch.tensor([0.8]))  # Buy with confidence
                mock_transformer.return_value = (torch.tensor([1]), torch.tensor([0.7]))  # Hold with confidence
                
                # Fit the scaler first
                self.ensemble.is_fitted = True
                
                result = self.ensemble.predict(data)
                
                assert result["action"] in ["BUY", "SELL", "HOLD"]
                assert 0 <= result["confidence"] <= 1
                assert "market_conditions" in result
                assert "model_weights" in result
                assert "individual_predictions" in result
                
    def test_save_and_load_models(self):
        """Test model saving and loading."""
        # Save models
        self.ensemble.save_models()
        
        # Verify files were created
        assert os.path.exists(os.path.join(self.temp_dir, "lstm_model.pth"))
        assert os.path.exists(os.path.join(self.temp_dir, "transformer_model.pth"))
        assert os.path.exists(os.path.join(self.temp_dir, "scaler.pkl"))
        assert os.path.exists(os.path.join(self.temp_dir, "performance.pkl"))
        
        # Create new ensemble and load models
        new_ensemble = ModelEnsemble(
            input_size=self.input_size,
            model_save_path=self.temp_dir
        )
        new_ensemble.load_models()
        
        # Verify scaler was loaded
        if self.ensemble.is_fitted:
            assert new_ensemble.is_fitted


class TestAdaptiveModelSelector:
    """Test the backward compatible wrapper."""
    
    def setup_method(self):
        """Setup test environment."""
        self.selector = AdaptiveModelSelector(input_size=5)
        
    def test_initialization(self):
        """Test selector initialization."""
        assert isinstance(self.selector.ensemble, ModelEnsemble)
        
    def test_make_decision_no_order_blocks(self):
        """Test decision making with no order blocks."""
        result = self.selector.make_decision([])
        assert result is None
        
    def test_make_decision_with_order_blocks_no_market_data(self):
        """Test decision making with order blocks but no market data."""
        order_blocks = [{
            'type': 'bullish',
            'price_level': (110, 100),
            'strength': 0.8,
            'timestamp': datetime.now()
        }]
        
        result = self.selector.make_decision(order_blocks)
        
        assert result is not None
        assert result["action"] == "BUY"
        assert result["symbol"] == "BTC/USDT"
        assert result["entry_price"] == 110
        assert result["confidence"] == 0.75
        
    def test_make_decision_with_market_data(self):
        """Test decision making with market data."""
        order_blocks = [{
            'type': 'bearish',
            'price_level': (110, 100),
            'strength': 0.8,
            'timestamp': datetime.now()
        }]
        
        # Create mock market data
        market_data = pd.DataFrame({
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        })
        
        # Mock ensemble prediction
        with patch.object(self.selector.ensemble, 'predict') as mock_predict:
            mock_predict.return_value = {
                "action": "SELL",
                "confidence": 0.85,
                "market_conditions": {"regime": "high_vol_downtrend"},
                "model_weights": {"lstm": 0.3, "transformer": 0.4, "ppo": 0.3}
            }
            
            result = self.selector.make_decision(order_blocks, market_data)
            
            assert result is not None
            assert result["action"] == "SELL"
            assert result["confidence"] == 0.85
            assert "market_regime" in result
            assert "ensemble_details" in result
            
    def test_train_models_interface(self):
        """Test training interface."""
        training_data = pd.DataFrame({
            'feature_0': np.random.randn(100),
            'feature_1': np.random.randn(100),
            'target': np.random.choice([0, 1, 2], 100)
        })
        
        # Mock the training methods to avoid actual training
        with patch.object(self.selector.ensemble, 'train_lstm') as mock_lstm:
            with patch.object(self.selector.ensemble, 'train_transformer') as mock_transformer:
                with patch.object(self.selector.ensemble, 'train_ppo') as mock_ppo:
                    
                    self.selector.train_models(training_data, epochs=2)
                    
                    mock_lstm.assert_called_once_with(training_data, epochs=2)
                    mock_transformer.assert_called_once_with(training_data, epochs=2)
                    mock_ppo.assert_called_once_with(training_data, total_timesteps=10000)
                    
    def test_save_load_models_interface(self):
        """Test save/load interface."""
        with patch.object(self.selector.ensemble, 'save_models') as mock_save:
            with patch.object(self.selector.ensemble, 'load_models') as mock_load:
                
                self.selector.save_models()
                self.selector.load_models()
                
                mock_save.assert_called_once()
                mock_load.assert_called_once()


class TestIntegrationScenarios:
    """Integration tests for complete ensemble workflows."""
    
    def setup_method(self):
        """Setup integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.ensemble = ModelEnsemble(
            input_size=6,
            sequence_length=30,
            model_save_path=self.temp_dir
        )
        
    def teardown_method(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_realistic_market_data(self, n_samples=200):
        """Create more realistic market data for integration testing."""
        np.random.seed(42)
        
        # Generate realistic OHLCV data
        base_price = 100
        prices = [base_price]
        
        for i in range(1, n_samples):
            # Random walk with slight upward bias
            change = np.random.normal(0.001, 0.02)  # 0.1% daily drift, 2% volatility
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1))  # Prevent negative prices
            
        prices = np.array(prices)
        
        # Create OHLC from close prices
        opens = prices + np.random.normal(0, 0.001, n_samples) * prices
        highs = np.maximum(opens, prices) + np.abs(np.random.normal(0, 0.005, n_samples)) * prices
        lows = np.minimum(opens, prices) - np.abs(np.random.normal(0, 0.005, n_samples)) * prices
        volumes = np.random.lognormal(10, 0.5, n_samples)
        
        # Add some technical indicators
        sma_20 = pd.Series(prices).rolling(20).mean().fillna(prices[0])
        rsi = self._calculate_rsi(pd.Series(prices))
        
        return pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=n_samples, freq='1H'),
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volumes,
            'sma_20': sma_20,
            'rsi': rsi
        })
        
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI for more realistic data."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    def test_full_ensemble_workflow(self):
        """Test complete ensemble workflow from data to prediction."""
        # Create realistic market data
        market_data = self.create_realistic_market_data(n_samples=150)
        
        # Add target labels (simplified momentum strategy)
        market_data['returns'] = market_data['close'].pct_change()
        market_data['target'] = 1  # Default to hold
        
        # Simple labeling: buy if next return > 1%, sell if < -1%
        future_returns = market_data['returns'].shift(-1)
        market_data.loc[future_returns > 0.01, 'target'] = 0  # Buy
        market_data.loc[future_returns < -0.01, 'target'] = 2  # Sell
        
        market_data = market_data.dropna()
        
        # Test market condition analysis
        market_conditions = self.ensemble.market_analyzer.get_market_regime(market_data)
        assert "regime" in market_conditions
        assert "volatility" in market_conditions
        assert "trend_strength" in market_conditions
        
        # Test prediction on unseen data (without training for speed)
        prediction = self.ensemble.predict(market_data)
        
        assert prediction["action"] in ["BUY", "SELL", "HOLD"]
        assert 0 <= prediction["confidence"] <= 1
        assert "market_conditions" in prediction
        assert "model_weights" in prediction
        
    def test_ensemble_with_different_market_regimes(self):
        """Test ensemble behavior across different market regimes."""
        # Test high volatility scenario
        high_vol_data = self.create_realistic_market_data(n_samples=100)
        # Artificially increase volatility
        high_vol_data['close'] *= (1 + np.random.normal(0, 0.1, len(high_vol_data)))
        
        high_vol_prediction = self.ensemble.predict(high_vol_data)
        high_vol_weights = high_vol_prediction["model_weights"]
        
        # Test low volatility scenario  
        low_vol_data = self.create_realistic_market_data(n_samples=100)
        # Reduce volatility
        low_vol_data['close'] = low_vol_data['close'].rolling(5).mean().fillna(low_vol_data['close'])
        
        low_vol_prediction = self.ensemble.predict(low_vol_data)
        low_vol_weights = low_vol_prediction["model_weights"]
        
        # Weights should be different between regimes
        assert high_vol_weights != low_vol_weights
        
        # Both predictions should be valid
        for pred in [high_vol_prediction, low_vol_prediction]:
            assert pred["action"] in ["BUY", "SELL", "HOLD"]
            assert 0 <= pred["confidence"] <= 1
            
    def test_performance_tracking_updates(self):
        """Test that performance metrics are properly tracked."""
        initial_performance = self.ensemble.model_performance.copy()
        
        # Simulate some predictions and updates
        market_data = self.create_realistic_market_data(n_samples=100)
        
        # Mock some training to update performance
        with patch.object(self.ensemble, 'prepare_sequences') as mock_prepare:
            mock_prepare.return_value = (
                np.random.randn(50, 30, 6),
                np.random.choice([0, 1, 2], 50)
            )
            
            # Mock successful training
            with patch('torch.save'):  # Prevent actual file I/O in test
                self.ensemble.train_lstm(market_data, epochs=1)
                
        # Performance should be updated
        updated_performance = self.ensemble.model_performance
        assert updated_performance["lstm"]["last_updated"] >= initial_performance["lstm"]["last_updated"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])