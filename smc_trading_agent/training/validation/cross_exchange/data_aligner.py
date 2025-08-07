"""
Time Series Data Aligner for Cross-Exchange Validation

This module provides sophisticated time series alignment capabilities for
synchronizing data across multiple exchanges with different timestamp formats
and potential latency differences.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlignmentQualityMetrics:
    """Metrics for data alignment quality assessment."""
    total_data_points: int
    aligned_data_points: int
    alignment_ratio: float
    average_time_gap: float
    max_time_gap: float
    missing_data_percentage: float
    timestamp_consistency_score: float


class TimeSeriesAligner:
    """
    Advanced time series data aligner for cross-exchange validation.
    
    Handles timestamp synchronization, data interpolation, and quality assessment
    for multi-exchange trading data alignment.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize time series aligner.
        
        Args:
            config: Configuration dictionary containing:
                - alignment_tolerance: Maximum time difference in seconds for alignment
                - interpolation_method: Method for handling missing data points
                - min_data_points: Minimum required data points for alignment
                - timestamp_format: Expected timestamp format
        """
        self.config = config
        self.alignment_tolerance = config.get('alignment_tolerance', 30)  # seconds
        self.interpolation_method = config.get('interpolation_method', 'linear')
        self.min_data_points = config.get('min_data_points', 100)
        self.timestamp_format = config.get('timestamp_format', 'auto')
        
        logger.info(f"TimeSeriesAligner initialized with tolerance: {self.alignment_tolerance}s")
    
    async def align_multiple_exchanges(
        self, 
        exchange_data: Dict[str, pd.DataFrame],
        base_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Align data from multiple exchanges to a common timeline.
        
        Args:
            exchange_data: Dictionary of exchange data
            base_data: Optional base data to align against
            
        Returns:
            Dict[str, Any]: Aligned data and quality metrics
        """
        logger.info(f"Aligning data from {len(exchange_data)} exchanges")
        
        try:
            # Prepare and validate input data
            prepared_data = await self._prepare_exchange_data(exchange_data)
            
            if not prepared_data:
                logger.warning("No valid data to align")
                return {
                    'aligned_data': {},
                    'alignment_quality': {},
                    'common_timeline': pd.DatetimeIndex([]),
                    'quality_metrics': {}
                }
            
            # Determine common time range
            common_timeline = await self._create_common_timeline(prepared_data, base_data)
            
            # Align each exchange to the common timeline
            aligned_data = {}
            alignment_quality = {}
            quality_metrics = {}
            
            for exchange, data in prepared_data.items():
                logger.info(f"Aligning {exchange} data to common timeline")
                
                aligned_exchange_data, quality = await self._align_single_exchange(
                    data, common_timeline, exchange
                )
                
                aligned_data[exchange] = aligned_exchange_data
                alignment_quality[exchange] = quality.alignment_ratio
                quality_metrics[exchange] = quality
            
            # Calculate overall alignment statistics
            overall_quality = self._calculate_overall_alignment_quality(quality_metrics)
            
            result = {
                'aligned_data': aligned_data,
                'alignment_quality': alignment_quality,
                'common_timeline': common_timeline,
                'quality_metrics': quality_metrics,
                'overall_quality': overall_quality
            }
            
            logger.info(f"Data alignment completed. Overall quality: {overall_quality:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Data alignment failed: {str(e)}")
            raise
    
    async def _prepare_exchange_data(self, exchange_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Prepare and validate exchange data for alignment.
        
        Args:
            exchange_data: Raw exchange data
            
        Returns:
            Dict[str, pd.DataFrame]: Prepared exchange data
        """
        prepared_data = {}
        
        for exchange, data in exchange_data.items():
            if data.empty:
                logger.warning(f"Empty data for exchange {exchange}")
                continue
            
            # Ensure timestamp column exists and is properly formatted
            prepared_df = await self._standardize_timestamps(data, exchange)
            
            # Filter out invalid data points
            prepared_df = self._filter_invalid_data(prepared_df, exchange)
            
            # Check minimum data requirements
            if len(prepared_df) < self.min_data_points:
                logger.warning(
                    f"Insufficient data points for {exchange}: {len(prepared_df)} < {self.min_data_points}"
                )
                continue
            
            prepared_data[exchange] = prepared_df
            logger.info(f"Prepared {len(prepared_df)} data points for {exchange}")
        
        return prepared_data
    
    async def _standardize_timestamps(self, data: pd.DataFrame, exchange: str) -> pd.DataFrame:
        """
        Standardize timestamp format and set as index.
        
        Args:
            data: Exchange data
            exchange: Exchange name for logging
            
        Returns:
            pd.DataFrame: Data with standardized timestamp index
        """
        df = data.copy()
        
        # Identify timestamp column
        timestamp_col = None
        for col in ['timestamp', 'datetime', 'time', 'date']:
            if col in df.columns:
                timestamp_col = col
                break
        
        if timestamp_col is None:
            # Try to use index if it's datetime-like
            if isinstance(df.index, pd.DatetimeIndex):
                df['timestamp'] = df.index
                timestamp_col = 'timestamp'
            else:
                logger.error(f"No timestamp column found for {exchange}")
                raise ValueError(f"No timestamp column found for {exchange}")
        
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
            try:
                df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            except Exception as e:
                logger.error(f"Failed to convert timestamps for {exchange}: {str(e)}")
                raise
        
        # Set timestamp as index and sort
        df = df.set_index(timestamp_col).sort_index()
        
        # Remove duplicate timestamps
        if df.index.duplicated().any():
            logger.warning(f"Removing {df.index.duplicated().sum()} duplicate timestamps for {exchange}")
            df = df[~df.index.duplicated(keep='first')]
        
        return df
    
    def _filter_invalid_data(self, data: pd.DataFrame, exchange: str) -> pd.DataFrame:
        """
        Filter out invalid data points.
        
        Args:
            data: Exchange data
            exchange: Exchange name for logging
            
        Returns:
            pd.DataFrame: Filtered data
        """
        initial_count = len(data)
        
        # Remove rows with all NaN values
        data = data.dropna(how='all')
        
        # Remove rows with invalid prices (negative or zero)
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in data.columns:
                invalid_mask = (data[col] <= 0) | data[col].isna()
                data = data[~invalid_mask]
        
        # Remove rows with invalid volume (negative)
        if 'volume' in data.columns:
            data = data[data['volume'] >= 0]
        
        filtered_count = len(data)
        if filtered_count < initial_count:
            logger.info(f"Filtered {initial_count - filtered_count} invalid data points for {exchange}")
        
        return data
    
    async def _create_common_timeline(
        self, 
        prepared_data: Dict[str, pd.DataFrame],
        base_data: Optional[pd.DataFrame] = None
    ) -> pd.DatetimeIndex:
        """
        Create a common timeline for all exchanges.
        
        Args:
            prepared_data: Prepared exchange data
            base_data: Optional base data to align against
            
        Returns:
            pd.DatetimeIndex: Common timeline for alignment
        """
        # Collect all timestamps
        all_timestamps = []
        
        if base_data is not None and not base_data.empty:
            if isinstance(base_data.index, pd.DatetimeIndex):
                all_timestamps.append(base_data.index)
            elif 'timestamp' in base_data.columns:
                all_timestamps.append(pd.to_datetime(base_data['timestamp']))
        
        for exchange, data in prepared_data.items():
            all_timestamps.append(data.index)
        
        if not all_timestamps:
            return pd.DatetimeIndex([])
        
        # Find overlapping time range
        start_time = max(ts.min() for ts in all_timestamps)
        end_time = min(ts.max() for ts in all_timestamps)
        
        if start_time >= end_time:
            logger.warning("No overlapping time range found across exchanges")
            return pd.DatetimeIndex([])
        
        # Create uniform timeline with 1-minute intervals
        common_timeline = pd.date_range(
            start=start_time,
            end=end_time,
            freq='1T'  # 1-minute frequency
        )
        
        logger.info(f"Created common timeline: {start_time} to {end_time} ({len(common_timeline)} points)")
        return common_timeline
    
    async def _align_single_exchange(
        self, 
        data: pd.DataFrame, 
        common_timeline: pd.DatetimeIndex,
        exchange: str
    ) -> Tuple[pd.DataFrame, AlignmentQualityMetrics]:
        """
        Align single exchange data to common timeline.
        
        Args:
            data: Exchange data
            common_timeline: Target timeline
            exchange: Exchange name
            
        Returns:
            Tuple[pd.DataFrame, AlignmentQualityMetrics]: Aligned data and quality metrics
        """
        if common_timeline.empty:
            empty_df = pd.DataFrame(index=pd.DatetimeIndex([]))
            empty_metrics = AlignmentQualityMetrics(
                total_data_points=0,
                aligned_data_points=0,
                alignment_ratio=0.0,
                average_time_gap=0.0,
                max_time_gap=0.0,
                missing_data_percentage=100.0,
                timestamp_consistency_score=0.0
            )
            return empty_df, empty_metrics
        
        # Use merge_asof for efficient time-based alignment
        aligned_data = self._merge_asof_alignment(data, common_timeline)
        
        # Apply interpolation for missing values
        if self.interpolation_method != 'none':
            aligned_data = self._apply_interpolation(aligned_data)
        
        # Calculate alignment quality metrics
        quality_metrics = self._calculate_alignment_quality(
            original_data=data,
            aligned_data=aligned_data,
            common_timeline=common_timeline
        )
        
        logger.info(f"Aligned {exchange}: {quality_metrics.alignment_ratio:.3f} alignment ratio")
        
        return aligned_data, quality_metrics
    
    def _merge_asof_alignment(self, data: pd.DataFrame, timeline: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Use pandas merge_asof for efficient time-based alignment.
        
        Args:
            data: Exchange data with datetime index
            timeline: Target timeline
            
        Returns:
            pd.DataFrame: Aligned data
        """
        # Create target DataFrame with timeline
        target_df = pd.DataFrame(index=timeline)
        target_df['target_time'] = timeline
        
        # Prepare source data
        source_df = data.reset_index()
        source_df.columns = [col if col != source_df.columns[0] else 'source_time' for col in source_df.columns]
        
        # Perform merge_asof with tolerance
        tolerance = pd.Timedelta(seconds=self.alignment_tolerance)
        
        aligned = pd.merge_asof(
            target_df.reset_index(),
            source_df,
            left_on='target_time',
            right_on='source_time',
            tolerance=tolerance,
            direction='nearest'
        )
        
        # Set the target timeline as index and remove helper columns
        aligned = aligned.set_index('target_time')
        aligned = aligned.drop(columns=['index', 'source_time'], errors='ignore')
        
        return aligned
    
    def _apply_interpolation(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply interpolation to fill missing values.
        
        Args:
            data: Data with potential missing values
            
        Returns:
            pd.DataFrame: Data with interpolated values
        """
        if self.interpolation_method == 'linear':
            return data.interpolate(method='linear')
        elif self.interpolation_method == 'spline':
            return data.interpolate(method='spline', order=2)
        elif self.interpolation_method == 'forward_fill':
            return data.fillna(method='ffill')
        elif self.interpolation_method == 'backward_fill':
            return data.fillna(method='bfill')
        else:
            return data
    
    def _calculate_alignment_quality(
        self, 
        original_data: pd.DataFrame,
        aligned_data: pd.DataFrame,
        common_timeline: pd.DatetimeIndex
    ) -> AlignmentQualityMetrics:
        """
        Calculate alignment quality metrics.
        
        Args:
            original_data: Original exchange data
            aligned_data: Aligned data
            common_timeline: Target timeline
            
        Returns:
            AlignmentQualityMetrics: Quality assessment
        """
        total_points = len(common_timeline)
        valid_points = aligned_data.dropna().shape[0]
        alignment_ratio = valid_points / total_points if total_points > 0 else 0.0
        
        # Calculate time gaps in original data
        time_diffs = original_data.index.to_series().diff().dropna()
        avg_time_gap = time_diffs.mean().total_seconds() if not time_diffs.empty else 0.0
        max_time_gap = time_diffs.max().total_seconds() if not time_diffs.empty else 0.0
        
        # Calculate missing data percentage
        missing_percentage = (aligned_data.isna().sum().sum() / 
                            (len(aligned_data) * len(aligned_data.columns))) * 100
        
        # Calculate timestamp consistency score
        expected_interval = pd.Timedelta(minutes=1)
        if not time_diffs.empty:
            consistency_score = (time_diffs <= expected_interval * 1.5).mean()
        else:
            consistency_score = 0.0
        
        return AlignmentQualityMetrics(
            total_data_points=len(original_data),
            aligned_data_points=valid_points,
            alignment_ratio=alignment_ratio,
            average_time_gap=avg_time_gap,
            max_time_gap=max_time_gap,
            missing_data_percentage=missing_percentage,
            timestamp_consistency_score=consistency_score
        )
    
    def _calculate_overall_alignment_quality(
        self, 
        quality_metrics: Dict[str, AlignmentQualityMetrics]
    ) -> float:
        """
        Calculate overall alignment quality across all exchanges.
        
        Args:
            quality_metrics: Quality metrics by exchange
            
        Returns:
            float: Overall alignment quality score (0-1)
        """
        if not quality_metrics:
            return 0.0
        
        # Weight different quality aspects
        alignment_scores = [metrics.alignment_ratio for metrics in quality_metrics.values()]
        consistency_scores = [metrics.timestamp_consistency_score for metrics in quality_metrics.values()]
        missing_data_scores = [1.0 - (metrics.missing_data_percentage / 100) 
                              for metrics in quality_metrics.values()]
        
        # Calculate weighted average
        overall_score = (
            np.mean(alignment_scores) * 0.4 +
            np.mean(consistency_scores) * 0.3 +
            np.mean(missing_data_scores) * 0.3
        )
        
        return max(0.0, min(1.0, overall_score))
