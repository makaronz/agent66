"""
Cross-Exchange Validator - Main coordination class for cross-exchange validation

This module implements the main CrossExchangeValidator class that coordinates
multi-exchange data fetching, alignment, and validation for trading strategies.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .data_aligner import TimeSeriesAligner
from .correlation_analyzer import CorrelationAnalyzer
from ...data_pipeline.exchange_connectors import get_exchange_connector

logger = logging.getLogger(__name__)


@dataclass
class ExchangeValidationResult:
    """Result structure for cross-exchange validation."""
    exchange: str
    data_quality_score: float
    correlation_with_base: float
    performance_metrics: Dict[str, float]
    data_points: int
    timestamp_range: Tuple[datetime, datetime]
    errors: List[str]


@dataclass
class CrossExchangeValidationResults:
    """Comprehensive cross-exchange validation results."""
    base_exchange: str
    validation_exchanges: List[str]
    overall_correlation: float
    correlation_significance: float
    performance_consistency: float
    data_quality_score: float
    exchange_results: Dict[str, ExchangeValidationResult]
    alignment_quality: Dict[str, float]
    recommendations: List[str]
    execution_time: float
    timestamp: datetime


class CrossExchangeValidator:
    """
    Main cross-exchange validation coordinator.
    
    Handles multi-exchange data fetching, alignment, correlation analysis,
    and performance consistency validation for trading strategies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cross-exchange validator.
        
        Args:
            config: Configuration dictionary containing:
                - exchanges: List of exchange names to validate against
                - base_exchange: Primary exchange for comparison
                - symbols: List of trading symbols to validate
                - alignment_tolerance: Time alignment tolerance in seconds
                - correlation_threshold: Minimum correlation threshold
                - data_quality_threshold: Minimum data quality score
        """
        self.config = config
        self.exchanges = config.get('exchanges', ['binance', 'bybit'])
        self.base_exchange = config.get('base_exchange', 'binance')
        self.symbols = config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
        self.alignment_tolerance = config.get('alignment_tolerance', 30)  # seconds
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        self.data_quality_threshold = config.get('data_quality_threshold', 0.8)
        
        # Initialize components
        self.data_aligner = TimeSeriesAligner(config)
        self.correlation_analyzer = CorrelationAnalyzer(config)
        
        # Exchange connectors cache
        self._exchange_connectors = {}
        
        logger.info(f"CrossExchangeValidator initialized for exchanges: {self.exchanges}")
    
    async def validate_across_exchanges(
        self, 
        base_data: pd.DataFrame,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> CrossExchangeValidationResults:
        """
        Perform comprehensive cross-exchange validation.
        
        Args:
            base_data: Primary strategy data for validation
            start_time: Start time for validation period
            end_time: End time for validation period
            
        Returns:
            CrossExchangeValidationResults: Comprehensive validation results
        """
        start_validation = datetime.now()
        logger.info(f"Starting cross-exchange validation for {len(self.exchanges)} exchanges")
        
        try:
            # Determine validation time range
            if start_time is None:
                start_time = base_data.index.min() if hasattr(base_data.index, 'min') else datetime.now() - timedelta(days=30)
            if end_time is None:
                end_time = base_data.index.max() if hasattr(base_data.index, 'max') else datetime.now()
            
            # Fetch data from all exchanges concurrently
            exchange_data = await self._fetch_all_exchange_data(start_time, end_time)
            
            # Validate data quality for each exchange
            data_quality_results = await self._validate_data_quality(exchange_data)
            
            # Align data across exchanges
            aligned_data = await self._align_exchange_data(exchange_data, base_data)
            
            # Perform correlation analysis
            correlation_results = await self._analyze_correlations(aligned_data)
            
            # Calculate performance consistency
            performance_results = await self._analyze_performance_consistency(aligned_data)
            
            # Generate validation results for each exchange
            exchange_results = {}
            for exchange in self.exchanges:
                if exchange != self.base_exchange and exchange in exchange_data:
                    exchange_results[exchange] = ExchangeValidationResult(
                        exchange=exchange,
                        data_quality_score=data_quality_results.get(exchange, 0.0),
                        correlation_with_base=correlation_results.get(f"{self.base_exchange}_{exchange}", 0.0),
                        performance_metrics=performance_results.get(exchange, {}),
                        data_points=len(exchange_data.get(exchange, pd.DataFrame())),
                        timestamp_range=(start_time, end_time),
                        errors=[]
                    )
            
            # Calculate overall metrics
            overall_correlation = np.mean([
                result.correlation_with_base for result in exchange_results.values()
            ]) if exchange_results else 0.0
            
            performance_consistency = self._calculate_performance_consistency(performance_results)
            
            overall_data_quality = np.mean([
                result.data_quality_score for result in exchange_results.values()
            ]) if exchange_results else 0.0
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                exchange_results, overall_correlation, performance_consistency, overall_data_quality
            )
            
            execution_time = (datetime.now() - start_validation).total_seconds()
            
            results = CrossExchangeValidationResults(
                base_exchange=self.base_exchange,
                validation_exchanges=[ex for ex in self.exchanges if ex != self.base_exchange],
                overall_correlation=overall_correlation,
                correlation_significance=correlation_results.get('significance', 0.0),
                performance_consistency=performance_consistency,
                data_quality_score=overall_data_quality,
                exchange_results=exchange_results,
                alignment_quality=aligned_data.get('alignment_quality', {}),
                recommendations=recommendations,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
            logger.info(f"Cross-exchange validation completed in {execution_time:.2f}s")
            logger.info(f"Overall correlation: {overall_correlation:.3f}, Consistency: {performance_consistency:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Cross-exchange validation failed: {str(e)}")
            raise
    
    async def _fetch_all_exchange_data(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data from all configured exchanges concurrently.
        
        Args:
            start_time: Start time for data fetching
            end_time: End time for data fetching
            
        Returns:
            Dict[str, pd.DataFrame]: Exchange data mapped by exchange name
        """
        logger.info(f"Fetching data from {len(self.exchanges)} exchanges")
        
        # Create tasks for concurrent data fetching
        fetch_tasks = []
        for exchange in self.exchanges:
            for symbol in self.symbols:
                task = self._fetch_exchange_symbol_data(exchange, symbol, start_time, end_time)
                fetch_tasks.append(task)
        
        # Execute all fetch tasks concurrently
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # Organize results by exchange
        exchange_data = {exchange: pd.DataFrame() for exchange in self.exchanges}
        
        task_index = 0
        for exchange in self.exchanges:
            exchange_symbol_data = []
            for symbol in self.symbols:
                result = fetch_results[task_index]
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch {symbol} from {exchange}: {str(result)}")
                else:
                    if not result.empty:
                        result['symbol'] = symbol
                        exchange_symbol_data.append(result)
                task_index += 1
            
            # Combine symbol data for exchange
            if exchange_symbol_data:
                exchange_data[exchange] = pd.concat(exchange_symbol_data, ignore_index=True)
                logger.info(f"Fetched {len(exchange_data[exchange])} data points from {exchange}")
        
        return exchange_data
    
    async def _fetch_exchange_symbol_data(
        self, 
        exchange: str, 
        symbol: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Fetch data for a specific symbol from a specific exchange.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            start_time: Start time for data
            end_time: End time for data
            
        Returns:
            pd.DataFrame: OHLCV data for the symbol
        """
        try:
            # Get or create exchange connector
            if exchange not in self._exchange_connectors:
                self._exchange_connectors[exchange] = get_exchange_connector(exchange)
            
            connector = self._exchange_connectors[exchange]
            
            # Fetch OHLCV data
            data = await connector.fetch_ohlcv_async(
                symbol=symbol,
                timeframe='1m',  # Use 1-minute data for high precision
                start_time=start_time,
                end_time=end_time
            )
            
            if data is not None and not data.empty:
                data['exchange'] = exchange
                return data
            else:
                logger.warning(f"No data received for {symbol} from {exchange}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching {symbol} from {exchange}: {str(e)}")
            return pd.DataFrame()
    
    async def _validate_data_quality(self, exchange_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Validate data quality for each exchange.
        
        Args:
            exchange_data: Data from all exchanges
            
        Returns:
            Dict[str, float]: Data quality scores by exchange
        """
        quality_scores = {}
        
        for exchange, data in exchange_data.items():
            if data.empty:
                quality_scores[exchange] = 0.0
                continue
                
            # Check data completeness
            completeness_score = 1.0 - (data.isnull().sum().sum() / (len(data) * len(data.columns)))
            
            # Check timestamp consistency (no large gaps)
            if 'timestamp' in data.columns:
                time_diffs = data['timestamp'].diff().dropna()
                expected_interval = time_diffs.mode().iloc[0] if not time_diffs.empty else pd.Timedelta(minutes=1)
                large_gaps = (time_diffs > expected_interval * 2).sum()
                timestamp_score = 1.0 - (large_gaps / len(time_diffs))
            else:
                timestamp_score = 0.5  # Partial score if no timestamp
            
            # Check price reasonableness (no extreme outliers)
            if 'close' in data.columns:
                price_changes = data['close'].pct_change().dropna()
                outliers = (np.abs(price_changes) > 0.1).sum()  # 10% price changes considered outliers
                price_score = 1.0 - (outliers / len(price_changes))
            else:
                price_score = 0.0
            
            # Calculate overall quality score
            overall_score = (completeness_score * 0.4 + timestamp_score * 0.3 + price_score * 0.3)
            quality_scores[exchange] = max(0.0, min(1.0, overall_score))
            
            logger.info(f"Data quality for {exchange}: {overall_score:.3f}")
        
        return quality_scores
    
    async def _align_exchange_data(
        self, 
        exchange_data: Dict[str, pd.DataFrame], 
        base_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Align data across exchanges using the data aligner.
        
        Args:
            exchange_data: Data from all exchanges
            base_data: Base strategy data
            
        Returns:
            Dict[str, Any]: Aligned data and alignment quality metrics
        """
        logger.info("Aligning data across exchanges")
        
        # Use the TimeSeriesAligner to align data
        aligned_result = await self.data_aligner.align_multiple_exchanges(exchange_data, base_data)
        
        return aligned_result
    
    async def _analyze_correlations(self, aligned_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Analyze correlations between exchanges.
        
        Args:
            aligned_data: Aligned exchange data
            
        Returns:
            Dict[str, float]: Correlation analysis results
        """
        logger.info("Analyzing cross-exchange correlations")
        
        # Use the CorrelationAnalyzer to perform correlation analysis
        correlation_results = await self.correlation_analyzer.analyze_cross_exchange_correlations(aligned_data)
        
        return correlation_results
    
    async def _analyze_performance_consistency(self, aligned_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Analyze performance consistency across exchanges.
        
        Args:
            aligned_data: Aligned exchange data
            
        Returns:
            Dict[str, Dict[str, float]]: Performance metrics by exchange
        """
        logger.info("Analyzing performance consistency")
        
        performance_results = {}
        
        # Extract aligned data for each exchange
        for exchange, data in aligned_data.get('aligned_data', {}).items():
            if data.empty:
                continue
                
            # Calculate basic performance metrics
            if 'close' in data.columns:
                returns = data['close'].pct_change().dropna()
                
                performance_metrics = {
                    'mean_return': returns.mean(),
                    'volatility': returns.std(),
                    'sharpe_ratio': returns.mean() / returns.std() if returns.std() > 0 else 0,
                    'max_drawdown': self._calculate_max_drawdown(data['close']),
                    'total_return': (data['close'].iloc[-1] / data['close'].iloc[0] - 1) if len(data) > 1 else 0
                }
                
                performance_results[exchange] = performance_metrics
        
        return performance_results
    
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown from price series."""
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return drawdown.min()
    
    def _calculate_performance_consistency(self, performance_results: Dict[str, Dict[str, float]]) -> float:
        """
        Calculate overall performance consistency across exchanges.
        
        Args:
            performance_results: Performance metrics by exchange
            
        Returns:
            float: Performance consistency score (0-1)
        """
        if len(performance_results) < 2:
            return 1.0
        
        # Calculate coefficient of variation for key metrics
        metrics_to_compare = ['mean_return', 'volatility', 'sharpe_ratio']
        consistency_scores = []
        
        for metric in metrics_to_compare:
            values = [results.get(metric, 0) for results in performance_results.values()]
            if len(values) > 1 and np.std(values) > 0:
                cv = np.std(values) / np.abs(np.mean(values)) if np.mean(values) != 0 else float('inf')
                consistency_score = max(0, 1 - min(cv, 1))  # Convert CV to consistency score
                consistency_scores.append(consistency_score)
        
        return np.mean(consistency_scores) if consistency_scores else 0.0
    
    def _generate_recommendations(
        self, 
        exchange_results: Dict[str, ExchangeValidationResult],
        overall_correlation: float,
        performance_consistency: float,
        overall_data_quality: float
    ) -> List[str]:
        """
        Generate recommendations based on validation results.
        
        Args:
            exchange_results: Validation results by exchange
            overall_correlation: Overall correlation score
            performance_consistency: Performance consistency score
            overall_data_quality: Overall data quality score
            
        Returns:
            List[str]: List of recommendations
        """
        recommendations = []
        
        # Correlation recommendations
        if overall_correlation < self.correlation_threshold:
            recommendations.append(
                f"LOW CORRELATION WARNING: Overall correlation ({overall_correlation:.3f}) "
                f"is below threshold ({self.correlation_threshold}). Strategy may not be robust across exchanges."
            )
        
        # Performance consistency recommendations
        if performance_consistency < 0.7:
            recommendations.append(
                f"PERFORMANCE INCONSISTENCY: Performance varies significantly across exchanges "
                f"(consistency: {performance_consistency:.3f}). Consider exchange-specific optimizations."
            )
        
        # Data quality recommendations
        if overall_data_quality < self.data_quality_threshold:
            recommendations.append(
                f"DATA QUALITY CONCERN: Overall data quality ({overall_data_quality:.3f}) "
                f"is below threshold ({self.data_quality_threshold}). Verify data sources."
            )
        
        # Exchange-specific recommendations
        for exchange, result in exchange_results.items():
            if result.data_quality_score < 0.6:
                recommendations.append(
                    f"EXCHANGE DATA ISSUE: {exchange} has low data quality "
                    f"({result.data_quality_score:.3f}). Consider excluding from analysis."
                )
            
            if result.correlation_with_base < 0.5:
                recommendations.append(
                    f"EXCHANGE CORRELATION ISSUE: {exchange} shows low correlation "
                    f"({result.correlation_with_base:.3f}) with {self.base_exchange}."
                )
        
        # Positive recommendations
        if overall_correlation >= self.correlation_threshold and performance_consistency >= 0.8:
            recommendations.append(
                "VALIDATION PASSED: Strategy shows good consistency and correlation across exchanges."
            )
        
        return recommendations
