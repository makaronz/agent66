# SMC Trading Agent ML Training System Documentation

## Overview

This document provides comprehensive documentation for the Machine Learning training system designed for Smart Money Concepts (SMC) trading patterns. The system implements end-to-end ML workflows from data collection to model deployment.

## Architecture

The ML training system consists of the following key components:

### 1. Data Collection & Validation
- **Historical Data Collector**: Multi-exchange data acquisition (Binance, ByBit, OANDA)
- **Data Quality Validation**: Comprehensive data cleaning and gap filling
- **Multi-timeframe Support**: 5m, 15m, 1h, 4h, 1d timeframes
- **Storage Format**: Efficient Parquet storage with metadata tracking

### 2. SMC Pattern Detection & Labeling
- **Pattern Types**: Order Blocks, CHOCH, BOS, Liquidity Sweeps, FVG
- **Outcome Tracking**: Success/failure analysis with risk-reward calculation
- **Multi-timeframe Confluence**: Pattern strength across different timeframes
- **Label Generation**: Binary and multi-class labels for ML training

### 3. Feature Engineering Pipeline
- **16 SMC-Specific Features**:
  1. `price_momentum`: Multi-timeframe price momentum
  2. `volatility_ratio`: Current volatility relative to historical average
  3. `volume_profile`: Volume distribution analysis
  4. `order_block_proximity`: Distance to nearest order blocks
  5. `choch_strength`: Change of Character pattern strength
  6. `fvg_size`: Fair Value Gap size and intensity
  7. `liquidity_sweep_strength`: Liquidity sweep detection strength
  8. `break_of_structure_momentum`: BOS pattern momentum
  9. `m5_m15_confluence`: Confluence between 5m and 15m timeframes
 10. `h1_h4_alignment`: Alignment between 1h and 4h trends
  11. `daily_trend_strength`: Overall daily trend momentum
  12. `risk_reward_ratio`: Calculated risk-reward for potential trades
  13. `position_size_optimal`: Optimal position sizing based on volatility
 14. `stop_loss_distance`: Optimal stop loss distance
 15. `bid_ask_spread`: Market liquidity indicator
  16. `order_book_imbalance`: Order flow analysis

### 4. Model Training Architecture

#### LSTM Model
- **Architecture**: 3-layer LSTM with 128 hidden units each
- **Sequence Length**: 60 timesteps (5 hours of M5 data)
- **Regularization**: 30% dropout, L2 regularization
- **Optimization**: Adam with learning rate scheduling

#### Transformer Model
- **Architecture**: 4-layer Transformer with 8 attention heads
- **Sequence Length**: 120 timesteps for broader context
- **Positional Encoding**: Learnable embeddings
- **Multi-head Attention**: Capture complex feature interactions

#### PPO Agent
- **Environment**: Custom trading environment with SMC patterns
- **State Space**: 16 features + market context
- **Action Space**: {buy, sell, hold} with position sizing
- **Training**: Proximal Policy Optimization with KL penalty

### 5. Ensemble Optimization
- **Weight Optimization**: Performance-based dynamic weighting
- **Confidence Intervals**: Model uncertainty quantification
- **Meta-learning**: Adaptive model selection
- **Blending Strategies**: Multiple ensemble combination methods

## Installation & Setup

### Prerequisites
```bash
# Python dependencies
pip install torch torchvision scikit-learn pandas numpy
pip install talib matplotlib seaborn
pip install asyncio aiofiles aiohttp

# System requirements
Python 3.8+
16GB+ RAM for training
GPU support recommended (CUDA 11.0+)
```

### Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd smc_trading_agent

# Create environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Data Collection
```python
from training.historical_data_collector import create_data_collection_config, HistoricalDataCollector

# Configure data collection
config = create_data_collection_config(
    exchanges=['binance', 'bybit'],
    symbols=['BTCUSDT', 'ETHUSDT'],
    timeframes=['5m', '15m', '1h', '4h'],
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2024, 1, 1),
    data_dir='./historical_data',
    validate_data=True
)

# Initialize collector
collector = HistoricalDataCollector(config)

# Collect data
results = await collector.collect_all_historical_data()
```

### 2. Pattern Labeling
```python
from training.smc_pattern_labeler import create_labeling_config, SMCPatternLabeler

# Configure labeling
label_config = create_labeling_config(
    min_holding_period_hours=2.0,
    max_holding_period_hours=48.0,
    profit_threshold_pct=0.3
)

# Initialize labeler
labeler = SMCPatternLabeler(label_config)

# Load your data
data = pd.read_parquet('historical_data/binance/BTCUSDT_5m.parquet')

# Label patterns
patterns = await labeler.label_historical_data(data, 'BTCUSDT', '5m')
```

### 3. Feature Engineering
```python
from training.smc_feature_engineer import create_feature_config, SMCFeatureEngineer

# Configure feature engineering
feature_config = create_feature_config(
    scaling_method='standard',
    remove_correlated=True,
    pca_components=None
)

# Initialize engineer
engineer = SMCFeatureEngineer(feature_config)

# Engineer features
dataset = await engineer.engineer_features(data, 'BTCUSDT', '5m', patterns)
```

### 4. Complete Training Pipeline
```python
from training.smc_training_pipeline import create_training_config, SMCTrainingPipeline

# Configure training
training_config = create_training_config(
    symbols=['BTCUSDT'],
    exchanges=['binance'],
    timeframes=['5m', '15m', '1h'],
    epochs=100,
    batch_size=512,
    learning_rate=0.001,
    device='cuda'  # or 'cpu'
)

# Initialize pipeline
pipeline = SMCTrainingPipeline(training_config)

# Run complete pipeline
results = await pipeline.run_complete_pipeline()
```

### 5. Model Deployment
```python
from training.deploy_models import ModelDeployer

# Initialize deployer
deployer = ModelDeployer(
    model_dir='./models',
    config_file='deployment_config.json'
)

# Load trained models
await deployer.load_models()

# Make prediction
features = pd.DataFrame(...)  # Your feature data
prediction = await deployer.predict(features)
```

## Configuration

### Training Configuration
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "exchanges": ["binance", "bybit"],
  "timeframes": ["5m", "15m", "1h", "4h"],
  "start_date": "2022-01-01T00:00:00",
  "end_date": "2024-01-01T00:00:00",
  "data_dir": "./training_data",
  "test_size": 0.2,
  "validation_size": 0.2,
  "batch_size": 512,
  "learning_rate": 0.001,
  "epochs": 100,
  "early_stopping_patience": 15,
  "min_accuracy": 0.65,
  "device": "auto",
  "model_dir": "./models"
}
```

### Feature Engineering Configuration
```json
{
  "momentum_periods": [5, 10, 20, 50],
  "volatility_windows": [10, 20, 50],
  "volume_profile_lookback": 100,
  "order_block_lookback": 50,
  "choch_confirmation_candles": 3,
  "fvg_min_size": 0.001,
  "liquidity_sweep_threshold": 1.5,
  "mtf_timeframes": ["5m", "15m", "1h", "4h", "1d"],
  "confluence_threshold": 0.7,
  "max_risk_per_trade": 0.02,
  "atr_multiplier": 2.0,
  "position_sizing_method": "kelly",
  "scaling_method": "standard",
  "remove_correlated": true,
  "correlation_threshold": 0.95
}
```

## Performance Targets

### Model Performance
- **Ensemble Accuracy**: >70% on test set
- **LSTM Accuracy**: >65% with <15ms inference
- **Transformer Accuracy**: >68% with <18ms inference
- **PPO Win Rate**: >62% with <12ms inference
- **Total Inference**: <20ms for ensemble prediction

### System Requirements
- **Memory**: 16GB+ RAM for training
- **GPU**: CUDA-compatible GPU recommended
- **Storage**: 100GB+ for 2+ years of historical data
- **Network**: Stable internet connection for data collection

## Model Monitoring

### Performance Metrics
```python
# Get performance summary
summary = deployer.get_performance_summary()

# Monitor drift
performance_stats = deployer.performance_stats
```

### Health Checks
```python
# Comprehensive health check
health = deployer.health_check()

# Specific checks
- Model loading status
- Feature preprocessing validation
- Inference latency monitoring
- Data quality checks
```

## Troubleshooting

### Common Issues

#### 1. Model Loading Errors
```python
# Check model files exist
import os
model_dir = Path("./models")
print("Model files:", list(model_dir.glob("*")))

# Verify model architecture
# Ensure input_size matches feature count
```

#### 2. Feature Mismatches
```python
# Check feature count
expected_features = 16
actual_features = features.shape[1]
print(f"Expected: {expected_features}, Actual: {actual_features}")

# Apply correct scaling
features_scaled = engineer.scaler.transform(features)
```

#### 3. Memory Issues
```python
# Reduce batch size
training_config.batch_size = 256  # From 512

# Use gradient accumulation if needed
# Implement gradient checkpointing
```

#### 4. GPU Memory
```python
# Enable mixed precision
scaler = torch.cuda.amp.GradScaler()

# Reduce model size
training_config.lstm_hidden_dims = [64, 64, 64]  # From [128, 128, 128]
```

## Best Practices

### Data Quality
1. **Always validate data** before training
2. **Handle missing values** appropriately
3. **Check for outliers** and anomalies
4. **Ensure timestamp consistency** across exchanges

### Model Training
1. **Use early stopping** to prevent overfitting
2. **Monitor validation loss** closely
3. **Save model checkpoints** regularly
4. **Use appropriate batch sizes** for your hardware

### Feature Engineering
1. **Normalize features** consistently
2. **Remove highly correlated** features
3. **Validate feature importance** regularly
4. **Monitor feature drift** in production

### Production Deployment
1. **Monitor model performance** continuously
2. **Implement fallback mechanisms** for model failures
3. **Log all predictions** for analysis
4. **Regular model retraining** schedule

## Extensions

### Additional Pattern Types
- Market Structure Shift detection
- Support and Resistance identification
- Volume Profile analysis
- Market Microstructure patterns

### Advanced Models
- Graph Neural Networks for pattern relationships
- Temporal Fusion Networks for multi-timeframe analysis
- Attention mechanisms with learnable patterns
- Custom loss functions for trading objectives

### Ensemble Methods
- Stacking with meta-learners
- Bayesian Model Averaging
- Dynamic ensemble selection
- Multi-objective optimization

## API Reference

### HistoricalDataCollector
```python
class HistoricalDataCollector:
    def __init__(config: DataCollectionConfig)
    async def collect_all_historical_data(self) -> Dict[str, Any]
    def get_collection_summary(self) -> Dict[str, Any]
```

### SMCPatternLabeler
```python
class SMCPatternLabeler:
    def __init__(config: LabelingConfig)
    async def label_historical_data(self, data, symbol, timeframe) -> List[PatternLabel]
    def get_pattern_statistics(self, patterns: List[PatternLabel]) -> Dict[str, Any]
```

### SMCFeatureEngineer
```python
class SMCFeatureEngineer:
    def __init__(config: FeatureConfig)
    async def engineer_features(self, data, symbol, timeframe, patterns) -> SMCDataset
    def apply_pca(self, dataset, n_components: int) -> SMCDataset
    def get_feature_importance(self, dataset, target_column=None) -> Dict[str, float]
```

### SMCTrainingPipeline
```python
class SMCTrainingPipeline:
    def __init__(config: TrainingConfig)
    async def run_complete_pipeline(self) -> Dict[str, Any]
```

### ModelDeployer
```python
class ModelDeployer:
    def __init__(model_dir: str, config_file: str)
    async def load_models(self) -> Dict[str, bool]
    async def predict(self, features: pd.DataFrame) -> Dict[str, Any]
    def health_check(self) -> Dict[str, Any]
```

## Contributing

### Development Guidelines
1. **Follow PEP 8** style guidelines
2. **Add comprehensive tests** for new features
3. **Document all changes** thoroughly
4. **Update configuration** schemas as needed
5. **Maintain backward compatibility**

### Testing
```bash
# Run all tests
pytest training/tests/

# Run specific test modules
pytest training/tests/test_data_collector.py
pytest training/tests/test_feature_engineer.py
```

### Documentation
- Update this README for new features
- Add inline documentation to code
- Include usage examples
- Maintain API reference documentation

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For questions, issues, or contributions, please contact the development team or open an issue on the project repository.

---

**Last Updated**: December 2024
**Version**: 1.0.0