# Enhanced SMCTradingEnv Architecture Design

> Author: AI Assistant  •  Date: 2025-08-07  •  File: `docs/rl_env_design.md`

---

## 1. Architecture Overview

The enhanced `SMCTradingEnv` follows a modular, layered architecture that maintains backward compatibility while adding sophisticated SMC features, multi-timeframe observations, realistic cost modeling, and advanced reward shaping.

### Core Design Principles

- **Separation of Concerns**: Each enhancement in separate, testable modules
- **Backward Compatibility**: Existing training scripts continue to work
- **Performance**: Vectorized operations, avoid loops over timeframes  
- **Extensibility**: Easy to add new SMC patterns or timeframes
- **Clean Interfaces**: Maintain Gymnasium API compatibility

---

## 2. Component Architecture

### 2.1 Data Pipeline Layer

```python
# training/data_pipeline/multi_tf_aligner.py
class MultiTimeframeAligner:
    """Aligns data across multiple timeframes for feature extraction"""
    
    def __init__(self, timeframes=['1m', '5m', '15m', '1h']):
        self.timeframes = timeframes
        
    def align_data(self, ohlcv_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Resample and align data to target timeframes"""
        # Implementation: resample, forward-fill, align timestamps
```

### 2.2 Feature Extraction Layer

```python
# training/features/smc_features.py
class SMCFeatureExtractor:
    """Extracts SMC patterns across multiple timeframes"""
    
    def __init__(self, timeframes=['1m', '5m', '15m', '1h']):
        self.timeframes = timeframes
        self.detectors = {
            'order_blocks': OrderBlockDetector(),
            'choch_bos': CHOCHBOSDetector(), 
            'fvg': FairValueGapDetector(),
            'liquidity_sweeps': LiquiditySweepDetector()
        }
    
    def extract_features(self, aligned_data: Dict[str, pd.DataFrame]) -> np.ndarray:
        """Extract SMC features for all timeframes"""
        # Implementation: vectorized feature extraction
```

### 2.3 Market Analysis Layer

```python
# training/analysis/market_regime.py
class MarketRegimeDetector:
    """Detects market regimes using clustering on volatility and trend metrics"""
    
    def __init__(self, n_regimes=3, window=100):
        self.n_regimes = n_regimes
        self.window = window
        self.kmeans = KMeans(n_clusters=n_regimes)
        
    def detect_regime(self, features: np.ndarray) -> int:
        """Returns regime label (0=trend, 1=range, 2=high_vol)"""
        # Implementation: clustering on vol + trend features

# training/analysis/confluence.py
class ConfluenceCalculator:
    """Calculates SMC pattern confluence scores"""
    
    def calculate_confluence(self, smc_features: np.ndarray) -> float:
        """Returns confluence score 0.0-1.0 based on pattern confirmations"""
        # Implementation: weighted sum of confirmed patterns

# training/analysis/position_sizing.py
class KellyPositionSizer:
    """Implements Kelly criterion for position sizing"""
    
    def __init__(self, risk_limit=0.02, lookback=252):
        self.risk_limit = risk_limit
        self.lookback = lookback
        
    def calculate_size(self, sharpe_ratio: float, equity: float) -> float:
        """Returns position size based on Kelly fraction"""
        # Implementation: Kelly = Sharpe / Volatility, clamped to risk limit
```

### 2.4 Cost & Slippage Layer

```python
# training/costs/slippage_model.py
class SlippageModel:
    """Models realistic slippage based on market conditions"""
    
    def __init__(self, base_slippage=0.0001, vol_multiplier=2.0):
        self.base_slippage = base_slippage
        self.vol_multiplier = vol_multiplier
        
    def calculate_slippage(self, volatility: float, position_size: float) -> float:
        """Returns slippage cost: N(0, base_slippage * vol_multiplier * volatility)"""
        # Implementation: volatility-scaled normal distribution

# training/costs/spread_model.py
class VariableSpreadModel:
    """Models variable spreads based on market conditions"""
    
    def __init__(self, base_spread=0.0002, atr_multiplier=0.5):
        self.base_spread = base_spread
        self.atr_multiplier = atr_multiplier
        
    def calculate_spread(self, atr: float) -> float:
        """Returns dynamic spread: base_spread + atr_multiplier * ATR"""
        # Implementation: ATR-based dynamic spread
```

### 2.5 Enhanced Environment

```python
# training/rl_environment.py (Enhanced)
class EnhancedSMCTradingEnv(gym.Env):
    """Enhanced SMCTradingEnv with SMC features, multi-TF, realistic costs"""
    
    def __init__(self, ohlcv_data, smc_features=None, transaction_cost=0.001):
        super().__init__()
        
        # Core components
        self.data_aligner = MultiTimeframeAligner()
        self.feature_extractor = SMCFeatureExtractor()
        self.regime_detector = MarketRegimeDetector()
        self.confluence_calc = ConfluenceCalculator()
        self.kelly_sizer = KellyPositionSizer()
        self.slippage_model = SlippageModel()
        self.spread_model = VariableSpreadModel()
        
        # Enhanced observation space
        self.observation_space = self._build_observation_space()
        
        # State tracking
        self.position = 0.0
        self.equity = 10000.0
        self.returns_history = []
        
    def _build_observation_space(self) -> gym.spaces.Box:
        """Builds concatenated multi-TF observation space"""
        # Implementation: concatenate features from all timeframes
        
    def step(self, action):
        """Enhanced step with realistic costs and advanced reward"""
        # Implementation: position management, cost calculation, reward shaping
```

---

## 3. Data Flow Architecture

### 3.1 Observation Space Design

```
Observation Vector Structure:
[
    # 1m Features (25 dims)
    smc_1m_order_blocks_bullish,     # 0-1
    smc_1m_order_blocks_bearish,     # 0-1  
    smc_1m_choch_bullish,           # 0-1
    smc_1m_choch_bearish,           # 0-1
    smc_1m_fvg_bullish,             # 0-1
    smc_1m_fvg_bearish,             # 0-1
    smc_1m_liquidity_sweeps,        # 0-1
    price_1m_open, high, low, close, volume,  # 5 dims
    technical_1m_rsi, macd, bbands, atr,      # 4 dims
    
    # 5m Features (25 dims) - same structure
    smc_5m_*, price_5m_*, technical_5m_*,     # 25 dims
    
    # 15m Features (25 dims) - same structure  
    smc_15m_*, price_15m_*, technical_15m_*,  # 25 dims
    
    # 1h Features (25 dims) - same structure
    smc_1h_*, price_1h_*, technical_1h_*,     # 25 dims
    
    # Market Context (10 dims)
    market_regime,                  # 0-2 (one-hot encoded)
    confluence_score,              # 0-1
    volatility_ratio,              # current_vol / avg_vol
    trend_strength,                # -1 to 1
    position_size,                 # current position
    equity,                        # current equity
    sharpe_ratio,                  # rolling Sharpe
    max_drawdown,                  # current max DD
    risk_metrics_1, risk_metrics_2 # additional risk measures
    
    # Total: 130 dimensions
]
```

### 3.2 Reward Function Design

```python
def calculate_reward(self, action, next_price, current_price):
    """Enhanced reward with multiple components"""
    
    # 1. Base PnL
    price_change = (next_price - current_price) / current_price
    base_pnl = self.position * price_change
    
    # 2. Transaction Costs
    spread_cost = self.spread_model.calculate_spread(self.current_atr)
    slippage_cost = self.slippage_model.calculate_slippage(
        self.current_volatility, abs(action)
    )
    commission_cost = abs(action) * self.transaction_cost
    total_cost = spread_cost + slippage_cost + commission_cost
    
    # 3. Confluence Bonus
    confluence_score = self.confluence_calc.calculate_confluence(
        self.current_smc_features
    )
    confluence_bonus = 0.1 * confluence_score if action != 0 else 0
    
    # 4. Regime Multiplier
    regime = self.regime_detector.detect_regime(self.current_features)
    regime_multipliers = {0: 1.0, 1: 0.8, 2: 1.2}  # trend, range, high_vol
    regime_multiplier = regime_multipliers[regime]
    
    # 5. Risk Adjustment
    sharpe_ratio = self.calculate_rolling_sharpe()
    risk_adjustment = max(0.5, min(2.0, sharpe_ratio + 1))
    
    # Final Reward
    reward = (base_pnl - total_cost + confluence_bonus) * regime_multiplier * risk_adjustment
    
    return reward
```

---

## 4. Integration Points

### 4.1 Backward Compatibility

```python
# Maintain existing interface
def reset(self, seed=None, options=None):
    """Enhanced reset maintaining Gymnasium compatibility"""
    super().reset(seed=seed)
    # Initialize all components
    return self._get_observation(), {}

def step(self, action):
    """Enhanced step maintaining Gymnasium compatibility"""
    # Enhanced implementation
    return observation, reward, done, truncated, info
```

### 4.2 Training Pipeline Integration

```python
# training/pipeline.py (Enhanced)
def create_enhanced_env(ohlcv_data, config):
    """Creates enhanced environment with all features"""
    env = EnhancedSMCTradingEnv(
        ohlcv_data=ohlcv_data,
        transaction_cost=config.get('transaction_cost', 0.001)
    )
    return env
```

---

## 5. Performance Considerations

### 5.1 Vectorization Strategy

- **Feature Extraction**: Use pandas-ta and smartmoneyconcepts for vectorized operations
- **Multi-TF Processing**: Pre-compute features for all timeframes, cache results
- **Reward Calculation**: Vectorize cost and reward calculations across batch

### 5.2 Memory Management

- **Observation Caching**: Cache computed features to avoid recalculation
- **History Management**: Limit return history to prevent memory bloat
- **Lazy Loading**: Load SMC features on-demand if not pre-computed

### 5.3 Computational Complexity

- **Feature Extraction**: O(n) where n = number of candles
- **Regime Detection**: O(k * m) where k = clusters, m = features  
- **Reward Calculation**: O(1) per step
- **Total**: Linear complexity with data size

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_enhanced_rl_env.py
def test_observation_space_dimensions():
    """Test observation space has correct dimensions"""
    
def test_reward_calculation():
    """Test reward function components"""
    
def test_cost_modeling():
    """Test slippage and spread models"""
    
def test_backward_compatibility():
    """Test existing training scripts still work"""
```

### 6.2 Integration Tests

```python
# tests/test_integration.py
def test_full_training_loop():
    """Test complete training pipeline with enhanced env"""
    
def test_multi_timeframe_alignment():
    """Test data alignment across timeframes"""
    
def test_smc_feature_extraction():
    """Test SMC pattern detection accuracy"""
```

---

## 7. Migration Plan

### Phase 1: Core Infrastructure
1. Implement `MultiTimeframeAligner`
2. Create `SMCFeatureExtractor` with smartmoneyconcepts
3. Build basic `EnhancedSMCTradingEnv` skeleton

### Phase 2: Advanced Features  
1. Implement `MarketRegimeDetector`
2. Add `ConfluenceCalculator`
3. Create `KellyPositionSizer`

### Phase 3: Cost Modeling
1. Implement `SlippageModel`
2. Add `VariableSpreadModel`
3. Integrate cost calculation into reward

### Phase 4: Testing & Optimization
1. Comprehensive unit and integration tests
2. Performance benchmarking
3. Backward compatibility validation

---

## 8. Dependencies

### Required Libraries
```yaml
smartmoneyconcepts: ^1.4.0
pandas-ta: ^0.3.14b
scikit-learn: ^1.3.0
numpy: ^1.24.0
gymnasium: ^0.29.0
```

### Optional Libraries
```yaml
ta-lib: ^0.4.28  # For performance-critical indicators
```

---

*This design document serves as the blueprint for implementing tasks T-125 through T-127.*
