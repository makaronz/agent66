"""
Unit tests for Model Ensemble core functionality.
Tests the ensemble decision-making, model training, and market condition analysis.
"""

import pytest
import pandas as pd
import numpy as np
import torch
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from decision_engine.model_ensemble import (
    ModelEnsemble, 
    MarketConditionAnalyzer, 
    LSTMPredictor, 
    TransformerPredictor,
    MarketEnvironment
)


class TestMarketConditionAnalyzer:
    """Test suite for Market Condition Analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create market condition analyzer for testing."""
        return MarketConditionAnalyzer(volatility_window=20, trend_window=14)
    
    @pytest.fixture
    def sample_prices(self):
        """Create sample price series for testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        base_price = 50000
        
        # Generate trending price series
        trend = np.linspace(0, 0.1, 100)  # 10% uptrend
        noise = np.random.normal(0, 0.02, 100)
        returns = trend + noise
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.Series(prices, index=dates)
    
    @pytest.fixture
    def volatile_prices(self):
        """Create volatile price series for testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        base_price = 50000
        
        # Generate high volatility series
        returns = np.random.normal(0, 0.05, 100)  # High volatility
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.Series(prices, index=dates)
    
    def test_calculate_volatility_normal_data(self, analyzer, sample_prices):
        """Test volatility calculation with normal data."""
        volatility = analyzer.calculate_volatility(sample_prices)
        
        assert isinstance(volatility, float)
        assert volatility >= 0
        assert not np.isnan(volatility)
        assert not np.isinf(volatility)
    
    def test_calculate_volatility_insufficient_data(self, analyzer):
        """Test volatility calculation with insufficient data."""
        short_prices = pd.Series([50000, 50100, 50200])
        volatility = analyzer.calculate_volatility(short_prices)
        
        assert volatility == 0.0
    
    def test_calculate_volatility_high_vol_data(self, analyzer, volatile_prices):
        """Test volatility calculation with high volatility data."""
        volatility = analyzer.calculate_volatility(volatile_prices)
        
        assert isinstance(volatility, float)
        assert volatility > 0.1  # Should detect high volatility
    
    def test_calculate_trend_strength_trending_data(self, analyzer, sample_prices):
        """Test trend strength calculation with trending data."""
        trend_strength, trend_direction = analyzer.calculate_trend_strength(sample_prices)
        
        assert isinstance(trend_strength, float)
        assert isinstance(trend_direction, str)
        assert trend_strength >= 0
        assert trend_direction in ['uptrend', 'downtrend', 'sideways']
        assert not np.isnan(trend_strength)
    
    def test_calculate_trend_strength_insufficient_data(self, analyzer):
        """Test trend strength calculation with insufficient data."""
        short_prices = pd.Series([50000, 50100])
        trend_strength, trend_direction = analyzer.calculate_trend_strength(short_prices)
        
        assert trend_strength == 0.0
        assert trend_direction == "sideways"
    
    def test_get_market_regime_complete_data(self, analyzer):
        """Test market regime identification with complete data."""
        # Create comprehensive market data
        data = pd.DataFrame({
            'close': np.random.uniform(49000, 51000, 50),
            'volume': np.random.uniform(1000, 10000, 50)
        })
        
        regime = analyzer.get_market_regime(data)
        
        assert isinstance(regime, dict)
        assert 'volatility' in regime
        assert 'trend_strength' in regime
        assert 'trend_direction' in regime
        assert 'regime' in regime
        
        assert isinstance(regime['volatility'], float)
        assert isinstance(regime['trend_strength'], float)
        assert regime['trend_direction'] in ['uptrend', 'downtrend', 'sideways']
        assert 'vol' in regime['regime']
    
    def test_get_market_regime_missing_close_column(self, analyzer):
        """Test market regime identification with missing close column."""
        data = pd.DataFrame({
            'open': [50000, 50100, 50200],
            'high': [50100, 50200, 50300],
            'low': [49900, 50000, 50100]
        })
        
        regime = analyzer.get_market_regime(data)
        
        assert regime['volatility'] == 0.0
        assert regime['trend_strength'] == 0.0
        assert regime['trend_direction'] == "sideways"
        assert regime['regime'] == "low_vol_sideways"
    
    @pytest.mark.parametrize("volatility_window,trend_window", [
        (10, 7),
        (20, 14),
        (30, 21),
        (50, 30)
    ])
    def test_analyzer_different_windows(self, volatility_window, trend_window, sample_prices):
        """Test analyzer with different window sizes."""
        analyzer = MarketConditionAnalyzer(volatility_window, trend_window)
        
        volatility = analyzer.calculate_volatility(sample_prices)
        trend_strength, trend_direction = analyzer.calculate_trend_strength(sample_prices)
        
        assert isinstance(volatility, float)
        assert isinstance(trend_strength, float)
        assert isinstance(trend_direction, str)


class TestMarketEnvironment:
    """Test suite for Market Environment (RL environment)."""
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for environment testing."""
        return pd.DataFrame({
            'open': np.random.uniform(49000, 51000, 100),
            'high': np.random.uniform(50000, 52000, 100),
            'low': np.random.uniform(48000, 50000, 100),
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        })
    
    @pytest.fixture
    def market_env(self, sample_market_data):
        """Create market environment for testing."""
        return MarketEnvironment(sample_market_data, initial_balance=10000.0)
    
    def test_environment_initialization(self, market_env, sample_market_data):
        """Test market environment initialization."""
        assert market_env.initial_balance == 10000.0
        assert market_env.balance == 10000.0
        assert market_env.current_step == 0
        assert market_env.position == 0.0
        assert market_env.entry_price is None
        assert len(market_env.market_data) == len(sample_market_data)
    
    def test_environment_reset(self, market_env):
        """Test environment reset functionality."""
        # Modify environment state
        market_env.current_step = 50
        market_env.balance = 5000
        market_env.position = 0.5
        market_env.entry_price = 50000
        
        obs, info = market_env.reset()
        
        assert market_env.current_step == 0
        assert market_env.balance == 10000.0
        assert market_env.position == 0.0
        assert market_env.entry_price is None
        assert isinstance(obs, np.ndarray)
        assert isinstance(info, dict)
    
    def test_environment_step_buy_action(self, market_env):
        """Test environment step with buy action."""
        obs, info = market_env.reset()
        
        # Take buy action
        action = np.array([0.8])  # Strong buy signal
        obs, reward, done, truncated, info = market_env.step(action)
        
        assert market_env.position == 1.0  # Long position
        assert market_env.entry_price is not None
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(truncated, bool)
        assert isinstance(obs, np.ndarray)
    
    def test_environment_step_sell_action(self, market_env):
        """Test environment step with sell action."""
        obs, info = market_env.reset()
        
        # Take sell action
        action = np.array([-0.8])  # Strong sell signal
        obs, reward, done, truncated, info = market_env.step(action)
        
        assert market_env.position == -1.0  # Short position
        assert market_env.entry_price is not None
    
    def test_environment_step_hold_action(self, market_env):
        """Test environment step with hold action."""
        obs, info = market_env.reset()
        
        # Take hold action
        action = np.array([0.2])  # Weak signal (hold)
        obs, reward, done, truncated, info = market_env.step(action)
        
        assert market_env.position == 0.0  # No position
        assert market_env.entry_price is None
    
    def test_environment_position_reversal(self, market_env):
        """Test position reversal in environment."""
        obs, info = market_env.reset()
        
        # First take long position
        action = np.array([0.8])
        market_env.step(action)
        assert market_env.position == 1.0
        
        # Then reverse to short
        action = np.array([-0.8])
        obs, reward, done, truncated, info = market_env.step(action)
        assert market_env.position == -1.0
    
    def test_environment_episode_completion(self, market_env):
        """Test environment episode completion."""
        obs, info = market_env.reset()
        
        # Run through entire episode
        done = False
        step_count = 0
        while not done and step_count < len(market_env.market_data):
            action = np.array([np.random.uniform(-1, 1)])
            obs, reward, done, truncated, info = market_env.step(action)
            step_count += 1
        
        assert done or step_count >= len(market_env.market_data) - 1


class TestLSTMPredictor:
    """Test suite for LSTM Predictor model."""
    
    @pytest.fixture
    def lstm_model(self):
        """Create LSTM model for testing."""
        return LSTMPredictor(input_size=5, hidden_size=64, num_layers=2, sequence_length=30)
    
    @pytest.fixture
    def sample_input(self):
        """Create sample input tensor for testing."""
        return torch.randn(32, 30, 5)  # batch_size=32, seq_len=30, input_size=5
    
    def test_lstm_initialization(self, lstm_model):
        """Test LSTM model initialization."""
        assert lstm_model.input_size == 5
        assert lstm_model.hidden_size == 64
        assert lstm_model.num_layers == 2
        assert lstm_model.sequence_length == 30
        
        # Check model components
        assert hasattr(lstm_model, 'lstm')
        assert hasattr(lstm_model, 'attention')
        assert hasattr(lstm_model, 'fc1')
        assert hasattr(lstm_model, 'fc2')
    
    def test_lstm_forward_pass(self, lstm_model, sample_input):
        """Test LSTM forward pass."""
        lstm_model.eval()
        with torch.no_grad():
            output = lstm_model(sample_input)
        
        assert output.shape == (32, 3)  # batch_size=32, num_classes=3
        assert torch.allclose(output.sum(dim=1), torch.ones(32), atol=1e-6)  # Softmax sums to 1
    
    def test_lstm_predict_direction(self, lstm_model, sample_input):
        """Test LSTM prediction method."""
        predictions, confidences = lstm_model.predict_direction(sample_input)
        
        assert predictions.shape == (32,)
        assert confidences.shape == (32,)
        assert torch.all(predictions >= 0) and torch.all(predictions <= 2)
        assert torch.all(confidences >= 0) and torch.all(confidences <= 1)
    
    def test_lstm_training_mode(self, lstm_model, sample_input):
        """Test LSTM in training mode."""
        lstm_model.train()
        output = lstm_model(sample_input)
        
        assert output.shape == (32, 3)
        assert output.requires_grad  # Should require gradients in training mode


class TestTransformerPredictor:
    """Test suite for Transformer Predictor model."""
    
    @pytest.fixture
    def transformer_model(self):
        """Create Transformer model for testing."""
        return TransformerPredictor(input_size=5, d_model=64, nhead=8, num_layers=4, sequence_length=30)
    
    @pytest.fixture
    def sample_input(self):
        """Create sample input tensor for testing."""
        return torch.randn(32, 30, 5)  # batch_size=32, seq_len=30, input_size=5
    
    def test_transformer_initialization(self, transformer_model):
        """Test Transformer model initialization."""
        assert transformer_model.input_size == 5
        assert transformer_model.d_model == 64
        assert transformer_model.sequence_length == 30
        
        # Check model components
        assert hasattr(transformer_model, 'input_projection')
        assert hasattr(transformer_model, 'positional_encoding')
        assert hasattr(transformer_model, 'transformer')
        assert hasattr(transformer_model, 'fc1')
        assert hasattr(transformer_model, 'fc2')
    
    def test_transformer_forward_pass(self, transformer_model, sample_input):
        """Test Transformer forward pass."""
        transformer_model.eval()
        with torch.no_grad():
            output = transformer_model(sample_input)
        
        assert output.shape == (32, 3)  # batch_size=32, num_classes=3
        assert torch.allclose(output.sum(dim=1), torch.ones(32), atol=1e-6)  # Softmax sums to 1
    
    def test_transformer_predict_direction(self, transformer_model, sample_input):
        """Test Transformer prediction method."""
        predictions, confidences = transformer_model.predict_direction(sample_input)
        
        assert predictions.shape == (32,)
        assert confidences.shape == (32,)
        assert torch.all(predictions >= 0) and torch.all(predictions <= 2)
        assert torch.all(confidences >= 0) and torch.all(confidences <= 1)


class TestModelEnsemble:
    """Test suite for Model Ensemble."""
    
    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1H')
        
        # Create features
        features = np.random.randn(200, 5)  # 5 features
        
        # Create target (price direction: 0=sell, 1=hold, 2=buy)
        targets = np.random.choice([0, 1, 2], size=200, p=[0.3, 0.4, 0.3])
        
        # Combine features and targets
        data = pd.DataFrame(features, columns=[f'feature_{i}' for i in range(5)])
        data['target'] = targets
        
        return data
    
    @pytest.fixture
    def model_ensemble(self):
        """Create model ensemble for testing."""
        return ModelEnsemble(input_size=5, sequence_length=60, model_save_path="test_models/")
    
    def test_ensemble_initialization(self, model_ensemble):
        """Test model ensemble initialization."""
        assert model_ensemble.input_size == 5
        assert model_ensemble.sequence_length == 60
        assert model_ensemble.model_save_path == "test_models/"
        assert not model_ensemble.is_fitted
        
        # Check model components
        assert hasattr(model_ensemble, 'lstm_model')
        assert hasattr(model_ensemble, 'transformer_model')
        assert hasattr(model_ensemble, 'market_analyzer')
        assert hasattr(model_ensemble, 'model_performance')
    
    def test_prepare_sequences_sufficient_data(self, model_ensemble, sample_training_data):
        """Test sequence preparation with sufficient data."""
        X, y = model_ensemble.prepare_sequences(sample_training_data)
        
        expected_samples = len(sample_training_data) - model_ensemble.sequence_length
        assert X.shape == (expected_samples, model_ensemble.sequence_length, 5)
        assert y.shape == (expected_samples,)
        assert model_ensemble.is_fitted  # Scaler should be fitted
    
    def test_prepare_sequences_insufficient_data(self, model_ensemble):
        """Test sequence preparation with insufficient data."""
        small_data = pd.DataFrame({
            'feature_0': [1, 2, 3],
            'feature_1': [4, 5, 6],
            'target': [0, 1, 2]
        })
        
        X, y = model_ensemble.prepare_sequences(small_data)
        
        assert X.shape == (0,)
        assert y.shape == (0,)
    
    @patch('decision_engine.model_ensemble.DataLoader')
    def test_train_lstm_success(self, mock_dataloader, model_ensemble, sample_training_data):
        """Test LSTM training success."""
        # Mock DataLoader to avoid actual training
        mock_dataloader.return_value = []
        
        # This should not raise an exception
        model_ensemble.train_lstm(sample_training_data, epochs=1, batch_size=32)
        
        # Performance should be updated
        assert 'lstm' in model_ensemble.model_performance
        assert 'accuracy' in model_ensemble.model_performance['lstm']
    
    @patch('decision_engine.model_ensemble.DataLoader')
    def test_train_transformer_success(self, mock_dataloader, model_ensemble, sample_training_data):
        """Test Transformer training success."""
        # Mock DataLoader to avoid actual training
        mock_dataloader.return_value = []
        
        # This should not raise an exception
        model_ensemble.train_transformer(sample_training_data, epochs=1, batch_size=32)
        
        # Performance should be updated
        assert 'transformer' in model_ensemble.model_performance
        assert 'accuracy' in model_ensemble.model_performance['transformer']
    
    @patch('decision_engine.model_ensemble.PPO')
    @patch('decision_engine.model_ensemble.DummyVecEnv')
    def test_train_ppo_success(self, mock_vec_env, mock_ppo, model_ensemble, sample_training_data):
        """Test PPO training success."""
        # Mock PPO and environment
        mock_ppo_instance = Mock()
        mock_ppo_instance.learn = Mock()
        mock_ppo_instance.predict = Mock(return_value=(np.array([0.5]), None))
        mock_ppo.return_value = mock_ppo_instance
        
        mock_env = Mock()
        mock_env.reset = Mock(return_value=np.zeros(5))
        mock_env.step = Mock(return_value=(np.zeros(5), 0.0, True, {}))
        mock_vec_env.return_value = mock_env
        
        # This should not raise an exception
        model_ensemble.train_ppo(sample_training_data, total_timesteps=100)
        
        # PPO model should be set
        assert model_ensemble.ppo_model is not None
    
    def test_get_model_weights_high_volatility(self, model_ensemble):
        """Test model weight calculation for high volatility regime."""
        market_conditions = {
            "regime": "high_vol_uptrend",
            "volatility": 0.3,
            "trend_strength": 30
        }
        
        weights = model_ensemble.get_model_weights(market_conditions)
        
        assert isinstance(weights, dict)
        assert 'lstm' in weights
        assert 'transformer' in weights
        assert 'ppo' in weights
        assert abs(sum(weights.values()) - 1.0) < 1e-6  # Should sum to 1
        assert all(w >= 0.1 for w in weights.values())  # Minimum weight constraint
    
    def test_get_model_weights_sideways_market(self, model_ensemble):
        """Test model weight calculation for sideways market."""
        market_conditions = {
            "regime": "low_vol_sideways",
            "volatility": 0.1,
            "trend_strength": 10
        }
        
        weights = model_ensemble.get_model_weights(market_conditions)
        
        assert isinstance(weights, dict)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        # In sideways markets, LSTM should get higher weight
        assert weights['lstm'] >= weights['transformer']
        assert weights['lstm'] >= weights['ppo']
    
    def test_predict_insufficient_data(self, model_ensemble):
        """Test prediction with insufficient data."""
        small_data = pd.DataFrame({
            'close': [50000, 50100, 50200],
            'volume': [1000, 1100, 1200]
        })
        
        result = model_ensemble.predict(small_data)
        
        assert isinstance(result, dict)
        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0.0
    
    def test_predict_with_sufficient_data(self, model_ensemble):
        """Test prediction with sufficient data."""
        # Create data with enough samples
        np.random.seed(42)
        data = pd.DataFrame({
            'close': np.random.uniform(49000, 51000, 100),
            'volume': np.random.uniform(1000, 10000, 100),
            'feature_1': np.random.randn(100),
            'feature_2': np.random.randn(100),
            'feature_3': np.random.randn(100)
        })
        
        result = model_ensemble.predict(data)
        
        assert isinstance(result, dict)
        assert 'action' in result
        assert 'confidence' in result
        assert 'market_conditions' in result
        assert 'model_weights' in result
        assert result['action'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= result['confidence'] <= 1
    
    @patch('os.path.exists')
    @patch('torch.save')
    @patch('pickle.dump')
    def test_save_models(self, mock_pickle_dump, mock_torch_save, mock_exists, model_ensemble):
        """Test model saving functionality."""
        mock_exists.return_value = True
        
        # This should not raise an exception
        model_ensemble.save_models()
        
        # Verify save methods were called
        assert mock_torch_save.call_count >= 2  # LSTM and Transformer
        assert mock_pickle_dump.call_count >= 2  # Scaler and performance
    
    @patch('os.path.exists')
    @patch('torch.load')
    @patch('pickle.load')
    def test_load_models(self, mock_pickle_load, mock_torch_load, mock_exists, model_ensemble):
        """Test model loading functionality."""
        mock_exists.return_value = True
        mock_torch_load.return_value = {}
        mock_pickle_load.return_value = Mock()
        
        # This should not raise an exception
        model_ensemble.load_models()
        
        # Verify load methods were called
        assert mock_torch_load.call_count >= 2  # LSTM and Transformer
        assert mock_pickle_load.call_count >= 1  # Scaler
    
    def test_model_performance_tracking(self, model_ensemble):
        """Test model performance tracking."""
        initial_performance = model_ensemble.model_performance.copy()
        
        # Update LSTM performance
        model_ensemble.model_performance['lstm']['accuracy'] = 0.85
        
        assert model_ensemble.model_performance['lstm']['accuracy'] == 0.85
        assert model_ensemble.model_performance['lstm']['accuracy'] != initial_performance['lstm']['accuracy']
    
    @pytest.mark.parametrize("regime,expected_weights", [
        ("high_vol_uptrend", {"ppo": "higher"}),
        ("low_vol_sideways", {"lstm": "higher"}),
        ("low_vol_uptrend", {"transformer": "higher"})
    ])
    def test_adaptive_model_selection(self, model_ensemble, regime, expected_weights):
        """Test adaptive model selection based on market regime."""
        market_conditions = {"regime": regime, "volatility": 0.2, "trend_strength": 25}
        weights = model_ensemble.get_model_weights(market_conditions)
        
        # Check that expected model gets higher weight
        for model, expectation in expected_weights.items():
            if expectation == "higher":
                other_models = [m for m in weights.keys() if m != model]
                assert any(weights[model] >= weights[other] for other in other_models)


@pytest.mark.unit
class TestModelEnsembleIntegration:
    """Integration tests for Model Ensemble combining multiple components."""
    
    @pytest.fixture
    def comprehensive_data(self):
        """Create comprehensive training data."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=500, freq='1H')
        
        # Create realistic market features
        returns = np.random.normal(0, 0.02, 500)
        prices = [50000]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        volumes = np.random.uniform(1000, 10000, 500)
        
        # Technical indicators
        rsi = np.random.uniform(20, 80, 500)
        macd = np.random.normal(0, 10, 500)
        bb_position = np.random.uniform(0, 1, 500)
        
        # Target: price direction
        targets = []
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1] * 1.001:  # >0.1% increase
                targets.append(2)  # Buy
            elif prices[i] < prices[i-1] * 0.999:  # >0.1% decrease
                targets.append(0)  # Sell
            else:
                targets.append(1)  # Hold
        targets.insert(0, 1)  # First target
        
        return pd.DataFrame({
            'close': prices,
            'volume': volumes,
            'rsi': rsi,
            'macd': macd,
            'bb_position': bb_position,
            'target': targets
        })
    
    def test_full_ensemble_pipeline(self, comprehensive_data):
        """Test complete ensemble training and prediction pipeline."""
        ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        
        # Test sequence preparation
        X, y = ensemble.prepare_sequences(comprehensive_data)
        assert len(X) > 0
        assert len(y) > 0
        
        # Test market condition analysis
        market_conditions = ensemble.market_analyzer.get_market_regime(comprehensive_data)
        assert isinstance(market_conditions, dict)
        
        # Test prediction (without training)
        result = ensemble.predict(comprehensive_data)
        assert isinstance(result, dict)
        assert result['action'] in ['BUY', 'SELL', 'HOLD']
    
    def test_ensemble_consistency(self, comprehensive_data):
        """Test ensemble prediction consistency."""
        ensemble = ModelEnsemble(input_size=5, sequence_length=60)
        
        # Make multiple predictions with same data
        result1 = ensemble.predict(comprehensive_data)
        result2 = ensemble.predict(comprehensive_data)
        
        # Results should be consistent (same model weights, same market conditions)
        assert result1['market_conditions']['regime'] == result2['market_conditions']['regime']
        assert result1['model_weights'] == result2['model_weights']
    
    def test_ensemble_robustness(self):
        """Test ensemble robustness with various data conditions."""
        ensemble = ModelEnsemble(input_size=3, sequence_length=30)
        
        # Test with different data scenarios
        scenarios = [
            # Trending up
            pd.DataFrame({
                'close': np.linspace(50000, 55000, 100),
                'volume': np.random.uniform(1000, 5000, 100),
                'feature': np.random.randn(100)
            }),
            # Trending down
            pd.DataFrame({
                'close': np.linspace(55000, 50000, 100),
                'volume': np.random.uniform(1000, 5000, 100),
                'feature': np.random.randn(100)
            }),
            # Sideways
            pd.DataFrame({
                'close': 50000 + np.random.normal(0, 100, 100),
                'volume': np.random.uniform(1000, 5000, 100),
                'feature': np.random.randn(100)
            })
        ]
        
        for i, scenario_data in enumerate(scenarios):
            result = ensemble.predict(scenario_data)
            assert isinstance(result, dict)
            assert result['action'] in ['BUY', 'SELL', 'HOLD']
            assert 0 <= result['confidence'] <= 1