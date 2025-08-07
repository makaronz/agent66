"""
Data validation utilities for SMC Trading Agent.

This module provides comprehensive data validation using Pydantic models for:
- Market data validation and quality checks
- Trade signal validation
- Configuration validation
- Data integrity verification
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum

from .error_handlers import DataValidationError, ErrorSeverity


class DataQualityLevel(Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class MarketDataModel(BaseModel):
    """Pydantic model for market data validation."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    timestamp: pd.Timestamp
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    
    @validator('high')
    def high_must_be_highest(cls, v, values):
        """Ensure high is the highest value."""
        if 'open' in values and 'close' in values and 'low' in values:
            if v < max(values['open'], values['close']):
                raise ValueError('High must be the highest value')
        return v
    
    @validator('low')
    def low_must_be_lowest(cls, v, values):
        """Ensure low is the lowest value."""
        if 'open' in values and 'close' in values and 'high' in values:
            if v > min(values['open'], values['close']):
                raise ValueError('Low must be the lowest value')
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is not too old."""
        if pd.Timestamp.now() - v > timedelta(hours=24):
            raise ValueError('Market data timestamp is too old (more than 24 hours)')
        return v


class TradeSignalModel(BaseModel):
    """Pydantic model for trade signal validation."""
    
    action: str = Field(..., pattern='^(BUY|SELL)$')
    symbol: str = Field(..., min_length=1)
    entry_price: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    timestamp: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @validator('entry_price')
    def validate_entry_price(cls, v):
        """Validate entry price is reasonable."""
        if v <= 0 or v > 1000000:  # Reasonable price range
            raise ValueError('Entry price must be positive and reasonable')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence is in reasonable range."""
        if v < 0.1:  # Minimum confidence threshold
            raise ValueError('Confidence too low for trading')
        return v
    
    @model_validator(mode='after')
    def validate_stop_loss_take_profit(self):
        """Validate stop loss and take profit relationships."""
        if self.action == 'BUY' and self.stop_loss and self.take_profit:
            if self.stop_loss >= self.entry_price:
                raise ValueError('Stop loss must be below entry price for BUY orders')
            if self.take_profit <= self.entry_price:
                raise ValueError('Take profit must be above entry price for BUY orders')
        elif self.action == 'SELL' and self.stop_loss and self.take_profit:
            if self.stop_loss <= self.entry_price:
                raise ValueError('Stop loss must be above entry price for SELL orders')
            if self.take_profit >= self.entry_price:
                raise ValueError('Take profit must be below entry price for SELL orders')
        
        return self


class OrderBlockModel(BaseModel):
    """Pydantic model for order block validation."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    timestamp: pd.Timestamp
    type: str = Field(..., pattern='^(bullish|bearish)$')
    price_level: Tuple[float, float]
    strength_volume: float = Field(..., ge=0)
    bos_confirmed_at: Optional[pd.Timestamp] = None
    
    @validator('price_level')
    def validate_price_level(cls, v):
        """Validate price level tuple."""
        if len(v) != 2:
            raise ValueError('Price level must be a tuple of (high, low)')
        if v[0] <= v[1]:
            raise ValueError('Price level high must be greater than low')
        return v
    
    @validator('strength_volume')
    def validate_volume(cls, v):
        """Validate volume is reasonable."""
        if v <= 0 or v > 1000000:  # Reasonable volume range
            raise ValueError('Volume must be positive and reasonable')
        return v


class DataValidator:
    """Comprehensive data validation and quality assessment."""
    
    def __init__(self):
        self.quality_thresholds = {
            'missing_data_threshold': 0.05,  # 5% missing data allowed
            'outlier_threshold': 3.0,  # 3 standard deviations
            'stale_data_threshold': 300,  # 5 minutes
            'volume_spike_threshold': 5.0,  # 5x average volume
            'price_change_threshold': 0.1  # 10% price change
        }
    
    def validate_market_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate market data DataFrame for quality and integrity.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        if errors:
            return False, errors
        
        # Check data types
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            errors.append("Timestamp column must be datetime type")
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append(f"Column {col} must be numeric type")
        
        if errors:
            return False, errors
        
        # Check for missing values
        missing_counts = df[required_columns].isnull().sum()
        total_rows = len(df)
        for col, missing_count in missing_counts.items():
            if missing_count / total_rows > self.quality_thresholds['missing_data_threshold']:
                errors.append(f"Too many missing values in {col}: {missing_count}/{total_rows}")
        
        # Check for negative values
        for col in ['open', 'high', 'low', 'close']:
            if (df[col] <= 0).any():
                errors.append(f"Negative or zero values found in {col}")
        
        if (df['volume'] < 0).any():
            errors.append("Negative volume values found")
        
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
        
        # Check for stale data
        if len(df) > 0:
            latest_timestamp = df['timestamp'].max()
            if pd.Timestamp.now() - latest_timestamp > timedelta(seconds=self.quality_thresholds['stale_data_threshold']):
                errors.append(f"Data is stale. Latest timestamp: {latest_timestamp}")
        
        # Check for volume spikes
        if len(df) > 1:
            volume_mean = df['volume'].mean()
            volume_spikes = df['volume'] > volume_mean * self.quality_thresholds['volume_spike_threshold']
            if volume_spikes.sum() > len(df) * 0.1:  # More than 10% spikes
                errors.append("Excessive volume spikes detected")
        
        # Check for extreme price changes
        if len(df) > 1:
            price_changes = abs(df['close'].pct_change()).dropna()
            extreme_changes = price_changes > self.quality_thresholds['price_change_threshold']
            if extreme_changes.sum() > len(price_changes) * 0.05:  # More than 5% extreme changes
                errors.append("Excessive price changes detected")
        
        return len(errors) == 0, errors
    
    def assess_data_quality(self, df: pd.DataFrame) -> DataQualityLevel:
        """
        Assess overall data quality level.
        
        Returns:
            DataQualityLevel enum value
        """
        is_valid, errors = self.validate_market_data(df)
        
        if not is_valid:
            error_count = len(errors)
            if error_count > 10:
                return DataQualityLevel.UNUSABLE
            elif error_count > 5:
                return DataQualityLevel.POOR
            elif error_count > 2:
                return DataQualityLevel.FAIR
            else:
                return DataQualityLevel.GOOD
        
        # Additional quality checks for valid data
        quality_score = 100
        
        # Check data freshness
        if len(df) > 0:
            latest_timestamp = df['timestamp'].max()
            age_minutes = (pd.Timestamp.now() - latest_timestamp).total_seconds() / 60
            if age_minutes > 10:
                quality_score -= 20
            elif age_minutes > 5:
                quality_score -= 10
        
        # Check data completeness
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        quality_score -= missing_ratio * 50
        
        # Check data consistency
        if len(df) > 1:
            price_volatility = df['close'].std() / df['close'].mean()
            if price_volatility > 0.1:  # High volatility
                quality_score -= 10
        
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
    
    def validate_market_data_row(self, row: pd.Series) -> MarketDataModel:
        """
        Validate a single market data row.
        
        Returns:
            Validated MarketDataModel instance
            
        Raises:
            DataValidationError: If validation fails
        """
        try:
            data = {
                'timestamp': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            }
            return MarketDataModel(**data)
        except Exception as e:
            raise DataValidationError(
                f"Market data row validation failed: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                component="market_data_validation",
                context={"row": row.to_dict(), "validation_error": str(e)}
            )
    
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
        
        # Check for price inconsistencies
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_high = df['high'] < df[['open', 'close']].max(axis=1)
            invalid_low = df['low'] > df[['open', 'close']].min(axis=1)
            
            if invalid_high.any():
                anomalies['inconsistencies']['invalid_high'] = invalid_high.sum()
            if invalid_low.any():
                anomalies['inconsistencies']['invalid_low'] = invalid_low.sum()
        
        return anomalies


# Global validator instance
data_validator = DataValidator()
