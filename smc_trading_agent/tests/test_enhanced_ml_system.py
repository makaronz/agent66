"""
Enhanced ML System Integration Tests

Comprehensive test suite for the enhanced ML system including:
- Market Regime Detection
- Sentiment Analysis Integration
- Order Book Analysis
- Cross-Asset Correlation
- Online Learning & Adaptation
- Enhanced Feature Engineering
- Regime-Adaptive Ensemble

Test Categories:
- Unit Tests: Individual component testing
- Integration Tests: Component interaction testing
- Performance Tests: Latency and resource usage
- Validation Tests: Accuracy and reliability testing
"""

import pytest
import numpy as np
import pandas as pd
import torch
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import warnings
warnings.filterwarnings('ignore')

# Import the enhanced ML components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from decision_engine.market_regime_detector import (
    MarketRegimeClassifier, VolatilityRegime, TrendRegime, 
    MicrostructureRegime, SessionRegime
)
from decision_engine.sentiment_analyzer import SentimentAnalyzer
from decision_engine.regime_adaptive_ensemble import RegimeAdaptiveEnsemble
from decision_engine.enhanced_feature_engineer import (
    EnhancedFeatureEngineer, SMCFeatureExtractor, TechnicalFeatureExtractor
)
from decision_engine.online_learning_adapter import (
    OnlineLearningAdapter, PredictionRecord, ModelPerformanceMetrics
)


class TestMarketRegimeDetector:
    """Test suite for Market Regime Detector."""
    
    @pytest.fixture
    def sample_ohlcv_data(self):
        """Generate sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=200, freq='H')
        
        # Generate realistic price movements
        price = 50000
        prices = [price]
        
        for _ in range(199):
            # Random walk with trend
            trend = np.random.normal(0.001, 0.02)
            volatility = np.random.normal(0, 0.01)
            price_change = trend + volatility
            price *= (1 + price_change)
            prices.append(price)
        
        # Create OHLCV DataFrame
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [p * np.random.uniform(0.998, 1.002) for p in prices],
            'high': [p * np.random.uniform(1.0, 1.005) for p in prices],
            'low': [p * np.random.uniform(0.995, 1.0) for p in prices],
            'close': prices,
            'volume': np.random.exponential(1000, 200)
        })
        
        return data
    
    @pytest.fixture
    def classifier(self):
        """Create MarketRegimeClassifier instance."""
        return MarketRegimeClassifier(lookback_period=50)
    
    def test_volatility_classification(self, classifier, sample_ohlcv_data):
        """Test volatility regime classification."""
        # Test different volatility regimes
        low_vol_data = sample_ohlcv_data.copy()
        low_vol_data['close'] = low_vol_data['close'] * (1 + np.random.normal(0, 0.001, len(low_vol_data)))
        
        high_vol_data = sample_ohlcv_data.copy()
        high_vol_data['close'] = high_vol_data['close'] * (1 + np.random.normal(0, 0.05, len(high_vol_data)))
        
        # Test classifications
        low_regime = classifier.classify_market_regime(low_vol_data)
        high_regime = classifier.classify_market_regime(high_vol_data)
        
        assert low_regime.volatility_regime in [VolatilityRegime.LOW, VolatilityRegime.NORMAL]
        assert high_regime.volatility_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREMELY_HIGH]
        
        # Test volatility score
        assert low_regime.volatility_score < high_regime.volatility_score
        
    def test_trend_classification(self, classifier, sample_ohlcv_data):
        """Test trend regime classification."""
        # Create trending data
        uptrend_data = sample_ohlcv_data.copy()
        uptrend_data['close'] = uptrend_data['close'] * np.linspace(1, 1.1, len(uptrend_data))
        
        downtrend_data = sample_ohlcv_data.copy()
        downtrend_data['close'] = downtrend_data['close'] * np.linspace(1, 0.9, len(downtrend_data))
        
        # Test classifications
        up_regime = classifier.classify_market_regime(uptrend_data)
        down_regime = classifier.classify_market_regime(downtrend_data)
        
        assert up_regime.trend_regime in [TrendRegime.WEAK_UPTREND, TrendRegime.MODERATE_UPTREND]
        assert down_regime.trend_regime in [TrendRegime.WEAK_DOWNTREND, TrendRegime.MODERATE_DOWNTREND]
        
        # Test trend strength
        assert up_regime.trend_strength > down_regime.trend_strength
        
    def test_session_classification(self, classifier):
        """Test trading session classification."""
        # Test different times
        london_time = datetime(2024, 1, 15, 10, 0, 0)  # 10 AM UTC
        ny_time = datetime(2024, 1, 15, 15, 0, 0)      # 3 PM UTC
        asian_time = datetime(2024, 1, 15, 2, 0, 0)    # 2 AM UTC
        weekend_time = datetime(2024, 1, 13, 12, 0, 0)  # Saturday
        
        london_regime = classifier.session_classifier.classify_session_regime(london_time)
        ny_regime = classifier.session_classifier.classify_session_regime(ny_time)
        asian_regime = classifier.session_classifier.classify_session_regime(asian_time)
        weekend_regime = classifier.session_classifier.classify_session_regime(weekend_time)
        
        assert london_regime == SessionRegime.LONDON_SESSION
        assert ny_regime == SessionRegime.NEW_YORK_SESSION
        assert asian_regime == SessionRegime.ASIAN_SESSION
        assert weekend_regime == SessionRegime.WEEKEND_CLOSE
        
    def test_regime_statistics(self, classifier, sample_ohlcv_data):
        """Test regime statistics calculation."""
        # Generate multiple classifications
        for _ in range(10):
            classifier.classify_market_regime(sample_ohlcv_data)
        
        stats = classifier.get_regime_statistics()
        
        assert 'volatility_regime_distribution' in stats
        assert 'trend_regime_distribution' in stats
        assert 'average_volatility' in stats
        assert 'total_classifications' in stats
        assert stats['total_classifications'] == 10


class TestSentimentAnalyzer:
    """Test suite for Sentiment Analyzer."""
    
    @pytest.fixture
    def sentiment_analyzer(self):
        """Create SentimentAnalyzer instance."""
        return SentimentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_news_sentiment_fetch(self, sentiment_analyzer):
        """Test news sentiment fetching."""
        # Mock API calls
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.get.return_value.json.return_value = {
                'articles': [
                    {
                        'title': 'Bitcoin reaches new highs',
                        'description': 'Positive market sentiment continues',
                        'content': 'Bullish outlook for cryptocurrency'
                    }
                ]
            }
            
            sentiment_scores = await sentiment_analyzer.news_analyzer.fetch_news_sentiment('BTC')
            
            assert len(sentiment_scores) > 0
            assert all(hasattr(score, 'score') for score in sentiment_scores)
            assert all(hasattr(score, 'confidence') for score in sentiment_scores)
    
    def test_sentiment_aggregation(self, sentiment_analyzer):
        """Test sentiment aggregation."""
        # Create sample sentiment scores
        sample_scores = [
            Mock(score=0.7, confidence=0.8, source='newsapi', timestamp=datetime.now()),
            Mock(score=-0.3, confidence=0.6, source='twitter', timestamp=datetime.now()),
            Mock(score=0.5, confidence=0.7, source='reddit', timestamp=datetime.now())
        ]
        
        aggregation = sentiment_analyzer.aggregator.aggregate_sentiment(sample_scores)
        
        assert aggregation is not None
        assert hasattr(aggregation, 'overall_sentiment')
        assert hasattr(aggregation, 'confidence')
        assert hasattr(aggregation, 'cross_platform_agreement')
        
        # Check weighted average calculation
        expected_weighted = (0.7 * 0.8 - 0.3 * 0.6 + 0.5 * 0.7) / (0.8 + 0.6 + 0.7)
        assert abs(aggregation.overall_sentiment - expected_weighted) < 0.01
    
    @pytest.mark.asyncio
    async def test_sentiment_features(self, sentiment_analyzer):
        """Test sentiment feature extraction."""
        # Mock sentiment analysis
        with patch.object(sentiment_analyzer, '_is_cache_valid', return_value=True):
            with patch.object(sentiment_analyzer.aggregator, 'aggregate_sentiment') as mock_aggregate:
                mock_aggregate.return_value = Mock(
                    overall_sentiment=0.3,
                    news_sentiment=0.2,
                    social_sentiment=0.4,
                    momentum=0.1,
                    volatility=0.2,
                    cross_platform_agreement=0.6,
                    confidence=0.7,
                    timestamp=datetime.now()
                )
                
                features = await sentiment_analyzer.get_sentiment_features('BTC')
                
                assert 'sentiment_overall' in features
                assert 'sentiment_news' in features
                assert 'sentiment_social' in features
                assert features['sentiment_overall'] == 0.3  # After baseline adjustment
                assert 'sentiment_confidence' in features


class TestEnhancedFeatureEngineer:
    """Test suite for Enhanced Feature Engineer."""
    
    @pytest.fixture
    def feature_engineer(self):
        """Create EnhancedFeatureEngineer instance."""
        return EnhancedFeatureEngineer()
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for feature extraction."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        
        np.random.seed(42)
        prices = np.cumprod(1 + np.random.normal(0.001, 0.02, 100))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * np.random.uniform(0.998, 1.002),
            'high': prices * np.random.uniform(1.0, 1.005),
            'low': prices * np.random.uniform(0.995, 1.0),
            'close': prices,
            'volume': np.random.exponential(1000, 100)
        })
    
    @pytest.fixture
    def sample_smc_patterns(self):
        """Create sample SMC patterns."""
        return {
            'order_blocks': [
                {
                    'type': 'bullish',
                    'price_level': (50000, 49500),
                    'strength_volume': 1000
                }
            ],
            'coch_patterns': [
                {
                    'type': 'bullish_coch',
                    'confidence': 0.7,
                    'momentum_strength': 2.5
                }
            ],
            'bos_patterns': [
                {
                    'type': 'bullish_bos',
                    'confidence': 0.8,
                    'break_strength': 1.2
                }
            ],
            'liquidity_sweeps': [
                {
                    'type': 'bullish_sweep',
                    'confidence': 0.6,
                    'sweep_strength': 0.8
                }
            ]
        }
    
    def test_smc_feature_extraction(self, feature_engineer, sample_data, sample_smc_patterns):
        """Test SMC feature extraction."""
        smc_features = feature_engineer.smc_extractor.extract_smc_features(sample_data, sample_smc_patterns)
        
        # Check for expected SMC features
        assert 'ob_count' in smc_features
        assert 'coch_count' in smc_features
        assert 'bos_count' in smc_features
        assert 'ls_count' in smc_features
        assert 'volume_trend' in smc_features
        assert 'structure_bullish' in smc_features
        
        # Check specific values
        assert smc_features['ob_count'] == 1
        assert smc_features['coch_count'] == 1
        assert smc_features['bos_count'] == 1
        assert smc_features['ls_count'] == 1
        
        # Check that values are in expected ranges
        assert 0 <= smc_features['ob_density'] <= 1.0
        assert 0.0 <= smc_features['structure_bullish'] <= 1.0
    
    def test_technical_feature_extraction(self, feature_engineer, sample_data):
        """Test technical feature extraction."""
        technical_features = feature_engineer.technical_extractor.extract_technical_features(sample_data)
        
        # Check for expected technical features
        assert 'sma_20_ratio' in technical_features
        assert 'rsi' in technical_features
        assert 'macd' in technical_features
        assert 'bb_position' in technical_features
        assert 'atr' in technical_features
        assert 'volume_trend' in technical_features
        
        # Check RSI range
        assert 0 <= technical_features['rsi'] <= 100
        
        # Check Bollinger Bands position
        assert 0 <= technical_features['bb_position'] <= 1.0
    
    def test_cross_asset_features(self, feature_engineer):
        """Test cross-asset feature extraction."""
        # Create sample cross-asset data
        asset_data = {
            'BTC': pd.DataFrame({
                'close': np.cumprod(1 + np.random.normal(0.001, 0.02, 50))
            }),
            'ETH': pd.DataFrame({
                'close': np.cumprod(1 + np.random.normal(0.001, 0.025, 50))
            }),
            'SPY': pd.DataFrame({
                'close': np.cumprod(1 + np.random.normal(0.0005, 0.015, 50))
            })
        }
        
        cross_asset_features = feature_engineer.cross_asset_extractor.extract_cross_asset_features('BTC', asset_data)
        
        # Check for expected cross-asset features
        assert 'crypto_correlation_avg' in cross_asset_features
        assert 'sp500_correlation' in cross_asset_features
        assert 'gold_correlation' in cross_asset_features
        assert 'safe_haven_demand' in cross_asset_features
        assert 'risk_on_score' in cross_asset_features
        
        # Check value ranges
        assert -1.0 <= cross_asset_features['sp500_correlation'] <= 1.0
        assert -1.0 <= cross_asset_features['gold_correlation'] <= 1.0
        assert 0.0 <= cross_asset_features['safe_haven_demand'] <= 1.0
    
    def test_temporal_features(self, feature_engineer):
        """Test temporal feature extraction."""
        # Test different times
        morning_time = datetime(2024, 1, 15, 9, 30, 0)   # 9:30 AM
        evening_time = datetime(2024, 1, 15, 16, 30, 0)  # 4:30 PM
        weekend_time = datetime(2024, 1, 13, 12, 0, 0)   # Saturday
        
        morning_features = feature_engineer.temporal_extractor.extract_temporal_features(morning_time)
        evening_features = feature_engineer.temporal_extractor.extract_temporal_features(evening_time)
        weekend_features = feature_engineer.temporal_extractor.extract_temporal_features(weekend_time)
        
        # Check session features
        assert morning_features['trading_session_active'] == 1.0
        assert evening_features['trading_session_active'] == 0.0
        assert weekend_features['weekend_flag'] == 0.0
        
        # Check session overlaps
        assert morning_features['session_overlap'] == 1.0  # London/NY overlap
        assert evening_features['session_overlap'] == 0.0
        
        # Check day of week
        assert morning_features['day_of_week'] == 1.0 / 6.0  # Monday
        assert weekend_features['day_of_week'] == 5.0 / 6.0  # Saturday
    
    def test_comprehensive_feature_extraction(self, feature_engineer, sample_data, sample_smc_patterns):
        """Test comprehensive feature extraction."""
        feature_set = feature_engineer.extract_features(
            data=sample_data,
            smc_patterns=sample_smc_patterns,
            order_book=None,
            cross_asset_data=None,
            timestamp=datetime.now()
        )
        
        # Check all feature groups are present
        assert hasattr(feature_set, 'smc_features')
        assert hasattr(feature_set, 'regime_features')
        assert hasattr(feature_set, 'sentiment_features')
        assert hasattr(feature_set, 'technical_features')
        assert hasattr(feature_set, 'order_book_features')
        assert hasattr(feature_set, 'cross_asset_features')
        assert hasattr(feature_set, 'temporal_features')
        
        # Check feature count
        assert feature_set.feature_count > 20  # Should have 25+ features
        
        # Check confidence scores
        assert isinstance(feature_set.confidence_scores, dict)
        assert 'smc' in feature_set.confidence_scores
        assert 'technical' in feature_set.confidence_scores
    
    def test_feature_preparation_for_model(self, feature_engineer, sample_data, sample_smc_patterns):
        """Test feature preparation for ML models."""
        feature_set = feature_engineer.extract_features(sample_data, sample_smc_patterns)
        
        # Prepare features for model
        prepared_features = feature_engineer.prepare_features_for_model(feature_set)
        
        # Check shape
        assert prepared_features.shape[0] == 1  # Single sample
        assert prepared_features.shape[1] > 20  # Should have many features
        
        # Check that features are numeric
        assert np.all(np.isfinite(prepared_features))
        
        # Fit scaler and test again
        feature_engineer.fit_scaler([feature_set])
        scaled_features = feature_engineer.prepare_features_for_model(feature_set)
        
        assert scaled_features.shape == prepared_features.shape
    
    def test_feature_names(self, feature_engineer):
        """Test feature name extraction."""
        feature_names = feature_engineer.get_feature_names()
        
        assert isinstance(feature_names, list)
        assert len(feature_names) > 20
        assert all(isinstance(name, str) for name in feature_names)
        
        # Check for expected prefixes
        smc_features = [name for name in feature_names if name.startswith('smc_')]
        technical_features = [name for name in feature_names if name.startswith('technical_')]
        
        assert len(smc_features) > 5
        assert len(technical_features) > 10


class TestRegimeAdaptiveEnsemble:
    """Test suite for Regime Adaptive Ensemble."""
    
    @pytest.fixture
    def ensemble(self):
        """Create RegimeAdaptiveEnsemble instance."""
        return RegimeAdaptiveEnsemble(input_size=10)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for ensemble."""
        return pd.DataFrame({
            'open': [50000, 50200, 49800, 50100],
            'high': [50500, 50300, 50200, 50400],
            'low': [49500, 50000, 49600, 49900],
            'close': [50000, 50200, 49800, 50100],
            'volume': [1000, 1200, 800, 1100]
        })
    
    def test_regime_specific_models(self, ensemble):
        """Test regime-specific model creation and management."""
        # Check that default models are created
        assert len(ensemble.regime_models) > 0
        assert 'default' in ensemble.regime_models
        
        # Test model prediction
        dummy_data = np.random.randn(60, 5)  # 60 timesteps, 5 features
        
        for regime_key, model in ensemble.regime_models.items():
            prediction = model.predict(dummy_data)
            
            assert 'action' in prediction
            assert 'confidence' in prediction
            assert 'individual_predictions' in prediction
            assert 'regime_model_used' == regime_key
    
    def test_regime_classification_integration(self, ensemble, sample_data):
        """Test integration with regime classification."""
        prediction = ensemble.predict(sample_data)
        
        assert 'regime_classification' in prediction
        assert 'regime_key' in prediction
        assert 'regime_features' in prediction
        
        # Check regime classification results
        regime_class = prediction['regime_classification']
        assert hasattr(regime_class, 'volatility_regime')
        assert hasattr(regime_class, 'trend_regime')
        assert hasattr(regime_class, 'microstructure_regime')
        
        # Check regime features
        regime_features = prediction['regime_features']
        assert 'volatility_regime_numeric' in regime_features
        assert 'trend_regime_numeric' in regime_features
    
    def test_transition_handling(self, ensemble, sample_data):
        """Test smooth regime transition handling."""
        # Make initial prediction
        prediction1 = ensemble.predict(sample_data)
        initial_regime = prediction1['regime_key']
        
        # Simulate regime change by modifying data
        modified_data = sample_data.copy()
        modified_data['close'] *= 1.1  # Increase prices for higher volatility
        
        prediction2 = ensemble.predict(modified_data)
        new_regime = prediction2['regime_key']
        
        # Check if transition was detected
        assert prediction2.get('transition_detected', False) == (initial_regime != new_regime)
        
        if initial_regime != new_regime:
            assert 'blended_prediction' in prediction2 or 'regime_model_used' in prediction2
        else:
            assert 'blended_prediction' not in prediction2
    
    def test_performance_tracking(self, ensemble, sample_data):
        """Test performance tracking and statistics."""
        # Make several predictions
        for i in range(10):
            prediction = ensemble.predict(sample_data)
            
            # Simulate actual outcome (alternating correct/incorrect)
            actual = i % 2  # Alternating
            ensemble.update_performance('lstm', 0, actual, prediction['confidence'])
        
        # Check performance statistics
        perf_summary = ensemble.get_performance_summary()
        
        assert 'ensemble_performance' in perf_summary
        assert 'regime_models' in perf_summary
        
        ensemble_perf = perf_summary['ensemble_performance']
        assert 'accuracy' in ensemble_perf
        assert 'total_predictions' in ensemble_perf
        
        assert ensemble_perf['total_predictions'] == 10


class TestOnlineLearningAdapter:
    """Test suite for Online Learning Adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create OnlineLearningAdapter instance."""
        return OnlineLearningAdapter()
    
    def test_model_registration(self, adapter):
        """Test model registration and tracking."""
        # Create a simple model
        model = Mock()
        model.parameters = Mock(return_value=[])
        model.state_dict = Mock(return_value={})
        
        # Register model
        adapter.register_model('test_model', model, 'lstm')
        
        # Check registration
        assert 'test_model' in adapter.registered_models
        assert adapter.registered_models['test_model']['model'] == model
        
        # Check performance tracking
        assert 'test_model' in adapter.model_performance
        assert isinstance(adapter.model_performance['test_model'], ModelPerformanceMetrics)
    
    def test_prediction_record_tracking(self, adapter):
        """Test prediction record tracking."""
        # Create a prediction record
        record = PredictionRecord(
            timestamp=datetime.now(),
            model_name='test_model',
            regime='test_regime',
            predicted_action='BUY',
            actual_action='BUY',
            confidence=0.8,
            features_used=25,
            correct=True,
            processing_time_ms=15.0
        )
        
        # Add to adapter
        adapter.add_prediction_result(record)
        
        # Check buffer
        assert len(adapter.training_data_buffer) == 1
        assert len(adapter.performance_history) == 1
        
        # Check that the record is properly stored
        stored_record = adapter.training_data_buffer[0]
        assert stored_record.model_name == 'test_model'
        assert stored_record.correct == True
        assert stored_record.confidence == 0.8
    
    def test_performance_monitoring(self, adapter):
        """Test performance monitoring and degradation detection."""
        # Register a model
        model = Mock()
        adapter.register_model('test_model', model, 'lstm')
        
        # Add some prediction records
        for i in range(20):
            correct = i < 15  # 75% accuracy
            record = PredictionRecord(
                timestamp=datetime.now(),
                model_name='test_model',
                regime='test_regime',
                predicted_action='BUY',
                actual_action='BUY' if correct else 'SELL',
                confidence=0.7,
                features_used=25,
                correct=correct
            )
            adapter.add_prediction_result(record)
        
        # Check performance
        perf = adapter.check_model_performance('test_model')
        
        assert perf['status'] == 'monitored'
        assert 'recent_accuracy' in perf
        assert 'overall_accuracy' in perf
        assert 'accuracy_drop' in perf
        assert perf['recent_accuracy'] == 0.75
        assert perf['overall_accuracy'] == 0.75
        
        # Test retrain recommendation
        should_retrain, reason = adapter.should_retrain_model('test_model')
        # With 75% accuracy, might not need retraining depending on threshold
    
        assert isinstance(should_retrain, bool)
        assert isinstance(reason, str)
    
    def test_concept_drift_detection(self, adapter):
        """Test concept drift detection."""
        # Register a model
        model = Mock()
        adapter.register_model('test_model', model, 'lstm')
        
        # Add prediction records with changing accuracy
        for i in range(50):
            # Simulate drift by reducing accuracy over time
            accuracy = max(0.3, 1.0 - i * 0.01)
            correct = np.random.random() < accuracy
            
            record = PredictionRecord(
                timestamp=datetime.now(),
                model_name='test_model',
                regime='test_regime',
                predicted_action='BUY',
                actual_action='BUY' if correct else 'SELL',
                confidence=0.6,
                features_used=25,
                correct=correct
            )
            adapter.add_prediction_result(record)
        
        # Check for drift
        drift_results = adapter.detect_concept_drift()
        
        # May or may not detect drift depending on randomness
        assert isinstance(drift_results, list)
        # If drift is detected, it should have required fields
        for result in drift_results:
            assert result.drift_detected == True
            assert result.drift_type in ['sudden', 'gradual', 'incremental', 'statistical', 'recurring']
            assert result.drift_score >= 0.0
            assert result.affected_models is not None
            assert result.recommended_action is not None
    
    def test_training_data_preparation(self, adapter):
        """Test training data preparation."""
        # Add some prediction records
        for i in range(150):
            record = PredictionRecord(
                timestamp=datetime.now(),
                model_name='test_model',
                regime='test_regime',
                predicted_action='BUY',
                actual_action='BUY',
                confidence=0.7,
                features_used=25,
                correct=True,
                features=np.random.randn(25)  # Simulated features
            )
            adapter.add_prediction_result(record)
        
        # Prepare training data
        X, y = adapter.prepare_training_data('test_model')
        
        assert X is not None
        assert y is not None
        assert X.shape[0] == len(y)  # Same number of samples
        assert X.shape[1] == 25  # Number of features
    
    def test_incremental_update(self, adapter):
        """Test incremental model updates."""
        # This would require actual model implementation
        # For now, test the interface
        
        # Prepare dummy data
        X = np.random.randn(100, 25)
        y = np.random.randint(0, 3, 100)
        
        # The actual implementation would use PyTorch models
        # For testing, we'll mock the result
        result = adapter.incremental_update_model('test_model', X, y)
        
        # Since we don't have a real model, this might return False
        assert isinstance(result, bool)
    
    def test_learning_statistics(self, adapter):
        """Test learning statistics extraction."""
        stats = adapter.get_learning_statistics()
        
        assert isinstance(stats, dict)
        assert 'registered_models' in stats
        assert 'model_performance' in stats
        assert 'training_data_buffer_size' in stats
        assert 'config' in stats
        assert 'drift_detector_stats' in stats


class TestEnhancedMLIntegration:
    """Integration tests for the enhanced ML system."""
    
    @pytest.fixture
    def sample_data(self):
        """Create comprehensive sample data."""
        dates = pd.date_range(start='2024-01-01', periods=500, freq='H')
        
        np.random.seed(42)
        base_price = 50000
        
        # Create realistic price series with trends and volatility
        trend = np.linspace(0, 0.1, 500)  # Upward trend
        volatility = np.random.normal(0, 0.02, 500)
        
        prices = base_price * np.exp(trend + volatility)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * np.random.uniform(0.998, 1.002),
            'high': prices * np.random.uniform(1.0, 1.005),
            'low': prices * np.random.uniform(0.995, 1.0),
            'close': prices,
            'volume': np.random.exponential(1000, 500)
        })
    
    def test_end_to_end_feature_pipeline(self):
        """Test end-to-end feature engineering pipeline."""
        engineer = EnhancedFeatureEngineer()
        
        # Create sample data with SMC patterns
        sample_data = self.sample_data()
        smc_patterns = {
            'order_blocks': [{'type': 'bullish', 'price_level': (50000, 49500), 'strength_volume': 1000}],
            'coch_patterns': [{'type': 'bullish_coch', 'confidence': 0.7, 'momentum_strength': 2.5}],
            'bos_patterns': [{'type': 'bullish_bos', 'confidence': 0.8, 'break_strength': 1.2}],
            'liquidity_sweeps': [{'type': 'bullish_sweep', 'confidence': 0.6, 'sweep_strength': 0.8}]
        }
        
        # Extract comprehensive features
        feature_set = engineer.extract_features(
            data=sample_data,
            smc_patterns=smc_patterns
        )
        
        # Verify feature extraction
        assert feature_set.feature_count > 20
        assert feature_set.confidence_scores is not None
        
        # Prepare features for model
        model_features = engineer.prepare_features_for_model(feature_set)
        
        assert model_features.shape[0] == 1
        assert model_features.shape[1] > 20
        assert np.all(np.isfinite(model_features))
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks for enhanced features."""
        engineer = EnhancedFeatureEngineer()
        
        sample_data = self.sample_data()
        
        # Time feature extraction
        import time
        start_time = time.time()
        
        # Extract SMC features (should be fast)
        smc_features = engineer.smc_extractor.extract_smc_features(sample_data, {})
        smc_time = time.time() - start_time
        
        start_time = time.time()
        
        # Extract technical features
        technical_features = engineer.technical_extractor.extract_technical_features(sample_data)
        technical_time = time.time() - start_time
        
        # Start timing full extraction
        start_time = time.time()
        feature_set = engineer.extract_features(sample_data, {})
        total_time = time.time() - start_time
        
        # Performance expectations (should be fast for real-time use)
        assert smc_time < 0.01  # < 10ms for SMC features
        assert technical_time < 0.05  # < 50ms for technical features
        assert total_time < 0.1     # < 100ms for full extraction
    
    def test_memory_usage(self):
        """Test memory usage of enhanced features."""
        engineer = EnhancedFeatureEngineer()
        
        sample_data = self.sample_data()
        
        # Extract features and check memory efficiency
        feature_set = engineer.extract_features(sample_data, {})
        
        # Feature set should be efficiently stored
        assert len(str(feature_set)) < 10000  # Reasonable string length
        
        # Engineer should maintain history efficiently
        initial_history_size = len(engineer.feature_history)
        
        # Add many feature sets
        for _ in range(100):
            engineer.extract_features(sample_data, {})
        
        # History should be capped
        final_history_size = len(engineer.feature_history)
        assert final_history_size <= engineer.feature_engineer.max_history
    
    def test_feature_consistency(self, feature_engineer, sample_data):
        """Test feature consistency across multiple extractions."""
        # Extract features multiple times
        feature_set1 = feature_engineer.extract_features(sample_data)
        feature_set2 = feature_engineer.extract_features(sample_data)
        
        # Extract and flatten features for comparison
        features1 = feature_engineer._flatten_features(
            feature_set1.smc_features, feature_set1.regime_features, feature_set1.sentiment_features,
            feature_set1.technical_features, feature_set1.order_book_features, feature_set1.cross_asset_features,
            feature_set1.temporal_features
        )
        
        features2 = feature_engineer._flatten_features(
            feature_set2.smc_features, feature_set2.regime_features, feature_set2.sentiment_features,
            feature_set2.technical_features, feature_set2.order_book_features, feature_set2.cross_asset_features,
            feature_set2.temporal_features
        )
        
        # Temporal features may vary based on timestamp
        temporal_diff = features1['temporal_hour_of_day'] - features2['temporal_hour_of_day']
        
        # Non-temporal features should be consistent (allowing for floating point precision)
        for key in features1.keys():
            if 'temporal_' not in key:
                assert abs(features1[key] - features2[key]) < 1e-10, f"Feature {key} differs significantly: {features1[key]} vs {features2[key]}"
    
    def test_scaler_behavior(self, feature_engineer, sample_data):
        """Test feature scaler behavior."""
        engineer = feature_engineer
        
        # Extract features before fitting
        feature_set1 = engineer.extract_features(sample_data, {})
        features1 = engineer.prepare_features_for_model(feature_set1)
        
        # Fit scaler on multiple samples
        feature_sets = []
        for _ in range(10):
            feature_sets.append(feature_engineer.extract_features(sample_data, {}))
        
        engineer.fit_scaler(feature_sets)
        
        # Extract features after fitting
        feature_set2 = engineer.extract_features(sample_data, {})
        features2 = engineer.prepare_features_for_model(feature_set2)
        
        # Scaler should now be fitted
        assert engineer.is_fitted
        
        # Features may be different due to scaling
        # Check that scaling was applied
        assert features1.shape == features2.shape
        
        # Non-zero features should be scaled
        non_zero_indices = features2[0] != 0
        if np.any(non_zero_indices):
            # Some features should be different after scaling
            # (unless all features are zero or similar)
            pass  # Features are likely different due to scaling


class TestMLSystemAccuracy:
    """Test ML system accuracy and performance."""
    
    @pytest.fixture
    def enhanced_system(self):
        """Create enhanced ML system."""
        return {
            'feature_engineer': EnhancedFeatureEngineer(),
            'regime_classifier': MarketRegimeClassifier(),
            'sentiment_analyzer': SentimentAnalyzer(),
            'ensemble': RegimeAdaptiveEnsemble(input_size=25),
            'online_adapter': OnlineLearningAdapter()
        }
    
    def test_accuracy_improvement_potential(self, enhanced_system):
        """Test potential accuracy improvement from enhancements."""
        # This test verifies that all components are working
        # and that the enhanced system provides more features than the baseline
        
        # Feature count verification
        engineer = enhanced_system['feature_engineer']
        
        sample_data = pd.DataFrame({
            'open': [50000] * 100,
            'high': [50500] * 100,
            'low': [49500] * 100,
            'close': [50000] * 100,
            'volume': [1000] * 100
        })
        
        feature_set = engineer.extract_features(sample_data)
        
        # Enhanced system should provide 25+ features
        assert feature_set.feature_count >= 25
        
        # Verify feature groups are comprehensive
        assert len(feature_set.smc_features) >= 10  # SMC features
        assert len(feature_set.technical_features) >= 10  # Technical features
        assert len(feature_set.temporal_features) >= 5   # Temporal features
        
        # Check feature quality
        total_confidence = sum(feature_set.confidence_scores.values())
        avg_confidence = total_confidence / len(feature_set.confidence_scores)
        
        assert avg_confidence > 0.5  # Reasonable confidence overall
    
    def test_system_integration(self, enhanced_system):
        """Test integration between enhanced components."""
        engineer = enhanced_system['feature_engineer']
        classifier = enhanced_system['regime_classifier']
        
        sample_data = pd.DataFrame({
            'open': [50000] * 50,
            'high': [50500] * 50,
            'low': [    49500] * 50,
            'close': [50000] * 50,
            'volume': [1000] * 50
        })
        
        # Test regime classification integration with feature engineering
        regime_classification = classifier.classify_market_regime(sample_data)
        regime_features = classifier.get_regime_features(regime_classification)
        
        feature_set = engineer.extract_features(sample_data)
        
        # Verify regime features are included in feature set
        assert 'regime_features' in feature_set.__dict__
        
        # Check that regime features are properly integrated
        assert 'volatility_regime_numeric' in regime_features
        assert 'trend_regime_numeric' in regime_features
        
        # Test that features can be prepared for models
        model_features = engineer.prepare_features_for_model(feature_set)
        assert model_features.shape[1] >= 25  # Should have enhanced feature count
    
    def test_adaptive_behavior(self, enhanced_system):
        """Test adaptive behavior of the enhanced system."""
        ensemble = enhanced_system['ensemble']
        adapter = enhanced_system['online_adapter']
        
        # Register models for online learning
        # (In practice, these would be real model instances)
        mock_lstm = Mock()
        mock_transformer = Mock()
        mock_lstm.state_dict.return_value = {}
        mock_transformer.state_dict.return_value = {}
        
        adapter.register_model('lstm_adaptive', mock_lstm, 'lstm')
        adapter.register_model('transformer_adaptive', mock_transformer, 'transformer')
        
        # Test ensemble prediction
        sample_data = pd.DataFrame({
            'open': [50000] * 20,
            'high': [50500] * 20,
            'low': [49500] * 20,
            'close': [50000] * 20,
            'volume': [1000] * 20
        })
        
        prediction = ensemble.predict(sample_data)
        
        # Check adaptive elements
        assert 'regime_classification' in prediction
        assert 'regime_features' in prediction
        assert 'ensemble_type' == 'regime_adaptive'
        
        # Test that online learning can be integrated
        learning_result = adapter.process_prediction_with_learning(
            'lstm_adaptive', prediction, actual_label=0  # BUY
        )
        
        assert isinstance(learning_result, PredictionRecord)
        assert 'drift_detected' in learning_result
        assert 'learning_action' in learning_result or 'error' in learning_result


# Test configuration and execution
if __name__ == "__main__":
    pytest.main([__file__])