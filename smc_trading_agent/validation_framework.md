# SMC Trading Agent - Validation Framework

## Overview

This document outlines the comprehensive validation framework for the SMC Trading Agent, designed to ensure data integrity, quality, and reliability throughout the trading pipeline.

## 1. Validation Architecture

### 1.1 Validation Layers

```
┌─────────────────────────────────────┐
│           Application Layer         │
├─────────────────────────────────────┤
│         Business Logic Layer        │
├─────────────────────────────────────┤
│           Data Model Layer          │
├─────────────────────────────────────┤
│           Input Validation          │
└─────────────────────────────────────┘
```

### 1.2 Validation Flow

1. **Input Validation**: Validate all incoming data
2. **Model Validation**: Validate data against Pydantic models
3. **Business Logic Validation**: Validate trading-specific rules
4. **Output Validation**: Validate results before use

## 2. Data Models

### 2.1 Market Data Model

```python
class MarketDataModel(BaseModel):
    timestamp: pd.Timestamp
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    
    @validator('high')
    def high_must_be_highest(cls, v, values):
        if 'open' in values and 'close' in values and 'low' in values:
            if v < max(values['open'], values['close']):
                raise ValueError('High must be the highest value')
        return v
    
    @validator('low')
    def low_must_be_lowest(cls, v, values):
        if 'open' in values and 'close' in values and 'high' in values:
            if v > min(values['open'], values['close']):
                raise ValueError('Low must be the lowest value')
        return v
```

**Validation Rules:**
- All price fields must be positive
- High must be the highest value
- Low must be the lowest value
- Volume must be non-negative
- Timestamp must not be too old

### 2.2 Trade Signal Model

```python
class TradeSignalModel(BaseModel):
    action: str = Field(..., regex='^(BUY|SELL)$')
    symbol: str = Field(..., min_length=1)
    entry_price: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    timestamp: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @validator('entry_price')
    def validate_entry_price(cls, v):
        if v <= 0 or v > 1000000:
            raise ValueError('Entry price must be positive and reasonable')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.1:
            raise ValueError('Confidence too low for trading')
        return v
```

**Validation Rules:**
- Action must be BUY or SELL
- Symbol must not be empty
- Entry price must be positive and reasonable
- Confidence must be between 0.1 and 1.0
- Stop loss and take profit relationships must be valid

### 2.3 Order Block Model

```python
class OrderBlockModel(BaseModel):
    timestamp: pd.Timestamp
    type: str = Field(..., regex='^(bullish|bearish)$')
    price_level: Tuple[float, float]
    strength_volume: float = Field(..., ge=0)
    bos_confirmed_at: Optional[pd.Timestamp] = None
    
    @validator('price_level')
    def validate_price_level(cls, v):
        if len(v) != 2:
            raise ValueError('Price level must be a tuple of (high, low)')
        if v[0] <= v[1]:
            raise ValueError('Price level high must be greater than low')
        return v
```

**Validation Rules:**
- Type must be bullish or bearish
- Price level must be a tuple of (high, low)
- High must be greater than low
- Volume must be positive

## 3. Data Quality Assessment

### 3.1 Quality Levels

```python
class DataQualityLevel(Enum):
    EXCELLENT = "excellent"  # High-quality data, safe for trading
    GOOD = "good"           # Good quality, minor issues acceptable
    FAIR = "fair"           # Moderate quality, use with caution
    POOR = "poor"           # Low quality, avoid trading
    UNUSABLE = "unusable"   # Data quality too poor for any use
```

### 3.2 Quality Assessment Criteria

#### 3.2.1 Data Completeness
- **Missing Data Threshold**: 5% maximum missing values
- **Required Columns**: All OHLCV columns must be present
- **Data Types**: Correct data types for all columns

#### 3.2.2 Data Consistency
- **OHLC Relationships**: High ≥ max(Open, Close) ≥ min(Open, Close) ≥ Low
- **Price Continuity**: No extreme price gaps
- **Volume Consistency**: No negative or zero volumes

#### 3.2.3 Data Freshness
- **Stale Data Threshold**: 5 minutes maximum age
- **Update Frequency**: Regular data updates
- **Timestamp Consistency**: Monotonic timestamps

#### 3.2.4 Data Accuracy
- **Outlier Detection**: 3 standard deviations threshold
- **Volume Spikes**: 5x average volume threshold
- **Price Changes**: 10% maximum price change

### 3.3 Quality Scoring Algorithm

```python
def assess_data_quality(self, df: pd.DataFrame) -> DataQualityLevel:
    quality_score = 100
    
    # Data freshness (20 points)
    if age_minutes > 10:
        quality_score -= 20
    elif age_minutes > 5:
        quality_score -= 10
    
    # Data completeness (30 points)
    missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
    quality_score -= missing_ratio * 50
    
    # Data consistency (25 points)
    if price_volatility > 0.1:
        quality_score -= 10
    if has_outliers:
        quality_score -= 15
    
    # Data accuracy (25 points)
    if has_volume_spikes:
        quality_score -= 10
    if has_extreme_changes:
        quality_score -= 15
    
    # Determine quality level
    if quality_score >= 90:
        return DataQualityLevel.EXCELLENT
    elif quality_score >= 75:
        return DataQualityLevel.GOOD
    elif quality_score >= 60:
        return DataQualityLevel.FAIR
    elif quality_score >= 40:
        return DataQualityLevel.POOR
    else:
        return DataQualityLevel.UNUSABLE
```

## 4. Validation Framework

### 4.1 DataValidator Class

```python
class DataValidator:
    def __init__(self):
        self.quality_thresholds = {
            'missing_data_threshold': 0.05,
            'outlier_threshold': 3.0,
            'stale_data_threshold': 300,
            'volume_spike_threshold': 5.0,
            'price_change_threshold': 0.1
        }
```

### 4.2 Validation Methods

#### 4.2.1 Market Data Validation

```python
def validate_market_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Comprehensive market data validation.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required columns
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    # Check data types
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        errors.append("Timestamp column must be datetime type")
    
    # Check for missing values
    missing_counts = df[required_columns].isnull().sum()
    total_rows = len(df)
    for col, missing_count in missing_counts.items():
        if missing_count / total_rows > self.quality_thresholds['missing_data_threshold']:
            errors.append(f"Too many missing values in {col}: {missing_count}/{total_rows}")
    
    # Check OHLC relationships
    invalid_high = df['high'] < df[['open', 'close']].max(axis=1)
    if invalid_high.any():
        errors.append("High values are not the highest in some rows")
    
    invalid_low = df['low'] > df[['open', 'close']].min(axis=1)
    if invalid_low.any():
        errors.append("Low values are not the lowest in some rows")
    
    # Check for outliers
    for col in ['open', 'high', 'low', 'close']:
        z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
        outliers = z_scores > self.quality_thresholds['outlier_threshold']
        if outliers.sum() > 0:
            errors.append(f"Outliers detected in {col}: {outliers.sum()} values")
    
    return len(errors) == 0, errors
```

#### 4.2.2 Trade Signal Validation

```python
def validate_trade_signal(self, signal: Dict[str, Any]) -> TradeSignalModel:
    """
    Validate trade signal data.
    
    Returns:
        Validated TradeSignalModel instance
        
    Raises:
        DataValidationError: If validation fails
    """
    try:
        return TradeSignalModel(**signal)
    except Exception as e:
        raise DataValidationError(
            f"Trade signal validation failed: {str(e)}",
            severity=ErrorSeverity.HIGH,
            component="trade_signal_validation",
            context={"signal": signal, "validation_error": str(e)}
        )
```

#### 4.2.3 Order Block Validation

```python
def validate_order_blocks(self, order_blocks: List[Dict[str, Any]]) -> List[OrderBlockModel]:
    """
    Validate order blocks data.
    
    Returns:
        List of validated OrderBlockModel instances
        
    Raises:
        DataValidationError: If validation fails
    """
    validated_blocks = []
    
    for i, block in enumerate(order_blocks):
        try:
            validated_block = OrderBlockModel(**block)
            validated_blocks.append(validated_block)
        except Exception as e:
            raise DataValidationError(
                f"Order block validation failed at index {i}: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                component="order_block_validation",
                context={"block_index": i, "block": block, "validation_error": str(e)}
            )
    
    return validated_blocks
```

### 4.3 Anomaly Detection

```python
def detect_data_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect various types of data anomalies.
    
    Returns:
        Dictionary containing detected anomalies
    """
    anomalies = {
        'missing_data': {},
        'outliers': {},
        'duplicates': {},
        'inconsistencies': {},
        'timing_issues': {}
    }
    
    # Check for missing data
    missing_data = df.isnull().sum()
    for col, missing_count in missing_data.items():
        if missing_count > 0:
            anomalies['missing_data'][col] = missing_count
    
    # Check for outliers using IQR method
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            if len(outliers) > 0:
                anomalies['outliers'][col] = len(outliers)
    
    # Check for duplicates
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        anomalies['duplicates']['total'] = duplicates
    
    # Check for timing inconsistencies
    if 'timestamp' in df.columns and len(df) > 1:
        time_diffs = df['timestamp'].diff().dropna()
        irregular_intervals = time_diffs[time_diffs != time_diffs.mode().iloc[0]]
        if len(irregular_intervals) > 0:
            anomalies['timing_issues']['irregular_intervals'] = len(irregular_intervals)
    
    return anomalies
```

## 5. Validation Integration

### 5.1 Main Application Integration

```python
# Market data validation in main loop
try:
    market_data_df = data_circuit_breaker.call(
        lambda: data_retry_handler.call(
            data_processor.get_latest_ohlcv_data, "BTC/USDT", "1h"
        )
    )
    
    # Validate market data quality
    is_valid, validation_errors = data_validator.validate_market_data(market_data_df)
    if not is_valid:
        logger.error("Market data validation failed", extra={"errors": validation_errors})
        continue
    
    quality_level = data_validator.assess_data_quality(market_data_df)
    if quality_level in [DataQualityLevel.POOR, DataQualityLevel.UNUSABLE]:
        logger.warning(f"Market data quality is {quality_level.value}, skipping cycle")
        continue
    
except Exception as e:
    logger.error(f"Failed to get market data: {str(e)}", exc_info=True)
    continue
```

### 5.2 Component Integration

```python
# Trade signal validation
if trade_signal:
    try:
        validated_signal = data_validator.validate_trade_signal(trade_signal)
        
        if validated_signal.confidence > config.get('decision_engine', {}).get('confidence_threshold', 0.7):
            # Proceed with validated signal
            pass
            
    except DataValidationError as e:
        logger.error(f"Trade signal validation failed: {str(e)}", exc_info=True)
        continue
```

## 6. Configuration

### 6.1 Validation Configuration

```yaml
validation:
  quality_thresholds:
    missing_data_threshold: 0.05
    outlier_threshold: 3.0
    stale_data_threshold: 300
    volume_spike_threshold: 5.0
    price_change_threshold: 0.1
  
  data_models:
    market_data:
      max_age_hours: 24
      min_volume: 0
      max_price: 1000000
    
    trade_signal:
      min_confidence: 0.1
      max_confidence: 1.0
      min_price: 0
      max_price: 1000000
    
    order_block:
      min_volume: 0
      max_volume: 1000000
      price_level_tolerance: 0.001
```

### 6.2 Quality Assessment Configuration

```yaml
quality_assessment:
  scoring:
    freshness_weight: 0.2
    completeness_weight: 0.3
    consistency_weight: 0.25
    accuracy_weight: 0.25
  
  thresholds:
    excellent_score: 90
    good_score: 75
    fair_score: 60
    poor_score: 40
```

## 7. Testing Strategy

### 7.1 Unit Tests

```python
def test_market_data_validation():
    # Test valid data
    valid_df = create_valid_market_data()
    is_valid, errors = data_validator.validate_market_data(valid_df)
    assert is_valid
    assert len(errors) == 0
    
    # Test invalid data
    invalid_df = create_invalid_market_data()
    is_valid, errors = data_validator.validate_market_data(invalid_df)
    assert not is_valid
    assert len(errors) > 0

def test_trade_signal_validation():
    # Test valid signal
    valid_signal = {
        "action": "BUY",
        "symbol": "BTC/USDT",
        "entry_price": 50000.0,
        "confidence": 0.8
    }
    validated = data_validator.validate_trade_signal(valid_signal)
    assert validated.action == "BUY"
    assert validated.confidence == 0.8
    
    # Test invalid signal
    invalid_signal = {
        "action": "INVALID",
        "symbol": "",
        "entry_price": -1000.0,
        "confidence": 1.5
    }
    with pytest.raises(DataValidationError):
        data_validator.validate_trade_signal(invalid_signal)
```

### 7.2 Integration Tests

```python
def test_validation_integration():
    # Test validation in main loop
    market_data = create_test_market_data()
    
    # Validate data
    is_valid, errors = data_validator.validate_market_data(market_data)
    assert is_valid
    
    # Assess quality
    quality = data_validator.assess_data_quality(market_data)
    assert quality in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD]
    
    # Detect anomalies
    anomalies = data_validator.detect_data_anomalies(market_data)
    assert len(anomalies['missing_data']) == 0
    assert len(anomalies['outliers']) == 0
```

### 7.3 Performance Tests

```python
def test_validation_performance():
    # Test validation performance with large datasets
    large_df = create_large_market_dataset(10000)
    
    start_time = time.time()
    is_valid, errors = data_validator.validate_market_data(large_df)
    validation_time = time.time() - start_time
    
    assert validation_time < 1.0  # Should complete within 1 second
    assert is_valid
```

## 8. Monitoring and Metrics

### 8.1 Validation Metrics

- **Validation Success Rate**: Percentage of successful validations
- **Data Quality Distribution**: Distribution of quality levels
- **Anomaly Detection Rate**: Frequency of detected anomalies
- **Validation Performance**: Time taken for validation operations

### 8.2 Alerting

- **High Anomaly Rate**: Alert when anomaly rate exceeds threshold
- **Poor Data Quality**: Alert when data quality is consistently poor
- **Validation Failures**: Alert when validation fails repeatedly
- **Performance Degradation**: Alert when validation performance degrades

## 9. Best Practices

### 9.1 Validation Best Practices

1. **Validate Early**: Validate data as soon as it enters the system
2. **Validate Often**: Validate at multiple points in the pipeline
3. **Fail Fast**: Fail quickly when validation fails
4. **Provide Context**: Include context in validation errors
5. **Log Everything**: Log all validation results for monitoring

### 9.2 Performance Best Practices

1. **Efficient Validation**: Use vectorized operations where possible
2. **Caching**: Cache validation results when appropriate
3. **Parallel Processing**: Use parallel processing for large datasets
4. **Incremental Validation**: Validate only changed data when possible

### 9.3 Error Handling Best Practices

1. **Specific Exceptions**: Use specific exception types for different validation failures
2. **Error Context**: Include context information in error messages
3. **Graceful Degradation**: Degrade gracefully when validation fails
4. **Recovery Strategies**: Implement recovery strategies for validation failures

## 10. Future Enhancements

### 10.1 Advanced Validation

- **Machine Learning Validation**: Use ML models for anomaly detection
- **Adaptive Thresholds**: Adjust validation thresholds based on market conditions
- **Real-time Validation**: Implement real-time validation for streaming data
- **Cross-validation**: Validate data across multiple sources

### 10.2 Performance Enhancements

- **Validation Caching**: Cache validation results for improved performance
- **Parallel Validation**: Implement parallel validation for large datasets
- **Incremental Validation**: Validate only changed data
- **Validation Optimization**: Optimize validation algorithms

### 10.3 Monitoring Enhancements

- **Real-time Dashboards**: Create real-time validation dashboards
- **Predictive Analytics**: Implement predictive analytics for data quality
- **Automated Alerts**: Implement automated alerting for validation issues
- **Performance Monitoring**: Monitor validation performance metrics

---

*This validation framework should be reviewed and updated regularly as the system evolves and new validation requirements are identified.*
