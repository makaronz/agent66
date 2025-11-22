"""
Cross-Exchange Correlation Analyzer

This module provides comprehensive correlation analysis capabilities for
cross-exchange validation, including statistical significance testing
and various correlation measures.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result structure for correlation analysis."""
    exchange_pair: str
    pearson_correlation: float
    pearson_p_value: float
    spearman_correlation: float
    spearman_p_value: float
    kendall_correlation: float
    kendall_p_value: float
    rolling_correlation_mean: float
    rolling_correlation_std: float
    correlation_stability: float
    significance_level: float
    is_significant: bool


@dataclass
class CrossExchangeCorrelationResults:
    """Comprehensive cross-exchange correlation results."""
    base_exchange: str
    correlation_pairs: Dict[str, CorrelationResult]
    overall_correlation: float
    correlation_matrix: pd.DataFrame
    significance_summary: Dict[str, bool]
    stability_scores: Dict[str, float]
    recommendations: List[str]
    analysis_timestamp: datetime


class CorrelationAnalyzer:
    """
    Advanced correlation analyzer for cross-exchange validation.
    
    Provides multiple correlation measures, statistical significance testing,
    and temporal stability analysis for trading strategy validation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize correlation analyzer.
        
        Args:
            config: Configuration dictionary containing:
                - significance_level: Statistical significance threshold (default: 0.05)
                - rolling_window: Window size for rolling correlation (default: 100)
                - min_periods: Minimum periods for correlation calculation (default: 30)
                - correlation_methods: List of correlation methods to use
        """
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.rolling_window = config.get('rolling_window', 100)
        self.min_periods = config.get('min_periods', 30)
        self.correlation_methods = config.get('correlation_methods', ['pearson', 'spearman', 'kendall'])
        
        logger.info(f"CorrelationAnalyzer initialized with significance level: {self.significance_level}")
    
    async def analyze_cross_exchange_correlations(
        self, 
        aligned_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Perform comprehensive cross-exchange correlation analysis.
        
        Args:
            aligned_data: Aligned exchange data from TimeSeriesAligner
            
        Returns:
            Dict[str, float]: Correlation analysis results
        """
        logger.info("Starting cross-exchange correlation analysis")
        
        try:
            exchange_data = aligned_data.get('aligned_data', {})
            
            if len(exchange_data) < 2:
                logger.warning("Insufficient exchanges for correlation analysis")
                return {'significance': 0.0}
            
            # Prepare data for correlation analysis
            prepared_data = await self._prepare_correlation_data(exchange_data)
            
            # Calculate pairwise correlations
            correlation_pairs = await self._calculate_pairwise_correlations(prepared_data)
            
            # Calculate correlation matrix
            correlation_matrix = await self._create_correlation_matrix(prepared_data)
            
            # Analyze correlation stability
            stability_scores = await self._analyze_correlation_stability(prepared_data)
            
            # Calculate overall correlation metrics
            overall_correlation = self._calculate_overall_correlation(correlation_pairs)
            
            # Assess statistical significance
            significance_summary = self._assess_statistical_significance(correlation_pairs)
            
            # Generate recommendations
            recommendations = self._generate_correlation_recommendations(
                correlation_pairs, significance_summary, stability_scores
            )
            
            # Create comprehensive results
            results = CrossExchangeCorrelationResults(
                base_exchange=list(exchange_data.keys())[0] if exchange_data else 'unknown',
                correlation_pairs=correlation_pairs,
                overall_correlation=overall_correlation,
                correlation_matrix=correlation_matrix,
                significance_summary=significance_summary,
                stability_scores=stability_scores,
                recommendations=recommendations,
                analysis_timestamp=datetime.now()
            )
            
            logger.info(f"Correlation analysis completed. Overall correlation: {overall_correlation:.3f}")
            
            # Return simplified results for compatibility
            return {
                'overall_correlation': overall_correlation,
                'significance': np.mean(list(significance_summary.values())) if significance_summary else 0.0,
                **{f"{pair}_correlation": result.pearson_correlation 
                   for pair, result in correlation_pairs.items()}
            }
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {str(e)}")
            return {'significance': 0.0}
    
    async def _prepare_correlation_data(self, exchange_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """
        Prepare data for correlation analysis.
        
        Args:
            exchange_data: Aligned exchange data
            
        Returns:
            Dict[str, pd.Series]: Prepared return series for each exchange
        """
        prepared_data = {}
        
        for exchange, data in exchange_data.items():
            if data.empty:
                continue
            
            # Use closing prices for correlation analysis
            if 'close' in data.columns:
                prices = data['close'].dropna()
                
                # Calculate returns
                returns = prices.pct_change().dropna()
                
                # Filter out extreme outliers (beyond 3 standard deviations)
                returns_std = returns.std()
                returns_mean = returns.mean()
                outlier_mask = np.abs(returns - returns_mean) <= 3 * returns_std
                returns = returns[outlier_mask]
                
                if len(returns) >= self.min_periods:
                    prepared_data[exchange] = returns
                    logger.info(f"Prepared {len(returns)} return observations for {exchange}")
                else:
                    logger.warning(f"Insufficient data for {exchange}: {len(returns)} < {self.min_periods}")
        
        return prepared_data
    
    async def _calculate_pairwise_correlations(
        self, 
        prepared_data: Dict[str, pd.Series]
    ) -> Dict[str, CorrelationResult]:
        """
        Calculate pairwise correlations between all exchange pairs.
        
        Args:
            prepared_data: Prepared return series
            
        Returns:
            Dict[str, CorrelationResult]: Correlation results for each pair
        """
        correlation_pairs = {}
        exchanges = list(prepared_data.keys())
        
        for i, exchange1 in enumerate(exchanges):
            for j, exchange2 in enumerate(exchanges[i+1:], i+1):
                pair_name = f"{exchange1}_{exchange2}"
                
                # Align data for the pair
                series1 = prepared_data[exchange1]
                series2 = prepared_data[exchange2]
                
                # Find common time range
                aligned_data = pd.DataFrame({'ex1': series1, 'ex2': series2}).dropna()
                
                if len(aligned_data) < self.min_periods:
                    logger.warning(f"Insufficient aligned data for {pair_name}")
                    continue
                
                # Calculate correlations
                correlation_result = await self._calculate_correlation_metrics(
                    aligned_data['ex1'], aligned_data['ex2'], pair_name
                )
                
                correlation_pairs[pair_name] = correlation_result
                logger.info(f"Calculated correlations for {pair_name}: {correlation_result.pearson_correlation:.3f}")
        
        return correlation_pairs
    
    async def _calculate_correlation_metrics(
        self, 
        series1: pd.Series, 
        series2: pd.Series, 
        pair_name: str
    ) -> CorrelationResult:
        """
        Calculate comprehensive correlation metrics for a pair of series.
        
        Args:
            series1: First return series
            series2: Second return series
            pair_name: Name of the exchange pair
            
        Returns:
            CorrelationResult: Comprehensive correlation metrics
        """
        # Pearson correlation
        pearson_corr, pearson_p = stats.pearsonr(series1, series2)
        
        # Spearman correlation
        spearman_corr, spearman_p = stats.spearmanr(series1, series2)
        
        # Kendall's tau correlation
        kendall_corr, kendall_p = stats.kendalltau(series1, series2)
        
        # Rolling correlation analysis
        rolling_corr = series1.rolling(window=self.rolling_window, min_periods=self.min_periods).corr(series2)
        rolling_corr = rolling_corr.dropna()
        
        rolling_mean = rolling_corr.mean() if not rolling_corr.empty else 0.0
        rolling_std = rolling_corr.std() if not rolling_corr.empty else 0.0
        
        # Correlation stability (inverse of coefficient of variation)
        if rolling_std > 0 and abs(rolling_mean) > 0:
            correlation_stability = 1.0 - (rolling_std / abs(rolling_mean))
        else:
            correlation_stability = 0.0
        
        # Statistical significance assessment
        is_significant = (pearson_p < self.significance_level and 
                         spearman_p < self.significance_level)
        
        return CorrelationResult(
            exchange_pair=pair_name,
            pearson_correlation=pearson_corr,
            pearson_p_value=pearson_p,
            spearman_correlation=spearman_corr,
            spearman_p_value=spearman_p,
            kendall_correlation=kendall_corr,
            kendall_p_value=kendall_p,
            rolling_correlation_mean=rolling_mean,
            rolling_correlation_std=rolling_std,
            correlation_stability=max(0.0, min(1.0, correlation_stability)),
            significance_level=self.significance_level,
            is_significant=is_significant
        )
    
    async def _create_correlation_matrix(self, prepared_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Create correlation matrix for all exchanges.
        
        Args:
            prepared_data: Prepared return series
            
        Returns:
            pd.DataFrame: Correlation matrix
        """
        if len(prepared_data) < 2:
            return pd.DataFrame()
        
        # Combine all series into a DataFrame
        combined_data = pd.DataFrame(prepared_data)
        
        # Calculate correlation matrix
        correlation_matrix = combined_data.corr(method='pearson')
        
        return correlation_matrix
    
    async def _analyze_correlation_stability(
        self, 
        prepared_data: Dict[str, pd.Series]
    ) -> Dict[str, float]:
        """
        Analyze temporal stability of correlations.
        
        Args:
            prepared_data: Prepared return series
            
        Returns:
            Dict[str, float]: Stability scores for each exchange pair
        """
        stability_scores = {}
        exchanges = list(prepared_data.keys())
        
        for i, exchange1 in enumerate(exchanges):
            for j, exchange2 in enumerate(exchanges[i+1:], i+1):
                pair_name = f"{exchange1}_{exchange2}"
                
                # Align data
                series1 = prepared_data[exchange1]
                series2 = prepared_data[exchange2]
                aligned_data = pd.DataFrame({'ex1': series1, 'ex2': series2}).dropna()
                
                if len(aligned_data) < self.rolling_window:
                    stability_scores[pair_name] = 0.0
                    continue
                
                # Calculate rolling correlations
                rolling_corr = aligned_data['ex1'].rolling(
                    window=self.rolling_window, 
                    min_periods=self.min_periods
                ).corr(aligned_data['ex2']).dropna()
                
                if len(rolling_corr) == 0:
                    stability_scores[pair_name] = 0.0
                    continue
                
                # Calculate stability as inverse of coefficient of variation
                corr_mean = rolling_corr.mean()
                corr_std = rolling_corr.std()
                
                if corr_std > 0 and abs(corr_mean) > 0:
                    cv = corr_std / abs(corr_mean)
                    stability = max(0.0, 1.0 - min(cv, 1.0))
                else:
                    stability = 1.0 if corr_std == 0 else 0.0
                
                stability_scores[pair_name] = stability
        
        return stability_scores
    
    def _calculate_overall_correlation(self, correlation_pairs: Dict[str, CorrelationResult]) -> float:
        """
        Calculate overall correlation score across all pairs.
        
        Args:
            correlation_pairs: Correlation results for all pairs
            
        Returns:
            float: Overall correlation score
        """
        if not correlation_pairs:
            return 0.0
        
        # Use absolute values and weight by significance
        correlations = []
        weights = []
        
        for result in correlation_pairs.values():
            # Use Pearson correlation as primary measure
            abs_correlation = abs(result.pearson_correlation)
            
            # Weight by statistical significance and stability
            weight = (1.0 if result.is_significant else 0.5) * (result.correlation_stability + 0.1)
            
            correlations.append(abs_correlation)
            weights.append(weight)
        
        # Calculate weighted average
        if sum(weights) > 0:
            overall_correlation = np.average(correlations, weights=weights)
        else:
            overall_correlation = np.mean(correlations)
        
        return overall_correlation
    
    def _assess_statistical_significance(
        self, 
        correlation_pairs: Dict[str, CorrelationResult]
    ) -> Dict[str, bool]:
        """
        Assess statistical significance of correlations.
        
        Args:
            correlation_pairs: Correlation results for all pairs
            
        Returns:
            Dict[str, bool]: Significance assessment for each pair
        """
        significance_summary = {}
        
        for pair_name, result in correlation_pairs.items():
            significance_summary[pair_name] = result.is_significant
        
        return significance_summary
    
    def _generate_correlation_recommendations(
        self,
        correlation_pairs: Dict[str, CorrelationResult],
        significance_summary: Dict[str, bool],
        stability_scores: Dict[str, float]
    ) -> List[str]:
        """
        Generate recommendations based on correlation analysis.
        
        Args:
            correlation_pairs: Correlation results
            significance_summary: Statistical significance results
            stability_scores: Correlation stability scores
            
        Returns:
            List[str]: List of recommendations
        """
        recommendations = []
        
        if not correlation_pairs:
            recommendations.append("No correlation data available for analysis.")
            return recommendations
        
        # Overall correlation assessment
        overall_corr = self._calculate_overall_correlation(correlation_pairs)
        
        if overall_corr >= 0.8:
            recommendations.append(
                f"EXCELLENT: High correlation ({overall_corr:.3f}) across exchanges indicates robust strategy."
            )
        elif overall_corr >= 0.6:
            recommendations.append(
                f"GOOD: Moderate correlation ({overall_corr:.3f}) suggests reasonable strategy consistency."
            )
        elif overall_corr >= 0.3:
            recommendations.append(
                f"CAUTION: Low correlation ({overall_corr:.3f}) indicates potential strategy inconsistency."
            )
        else:
            recommendations.append(
                f"WARNING: Very low correlation ({overall_corr:.3f}) suggests poor strategy generalization."
            )
        
        # Significance assessment
        significant_pairs = sum(significance_summary.values())
        total_pairs = len(significance_summary)
        
        if total_pairs > 0:
            significance_ratio = significant_pairs / total_pairs
            if significance_ratio < 0.5:
                recommendations.append(
                    f"STATISTICAL CONCERN: Only {significant_pairs}/{total_pairs} correlations are statistically significant."
                )
        
        # Stability assessment
        if stability_scores:
            avg_stability = np.mean(list(stability_scores.values()))
            if avg_stability < 0.5:
                recommendations.append(
                    f"STABILITY CONCERN: Average correlation stability ({avg_stability:.3f}) is low."
                )
        
        # Pair-specific recommendations
        for pair_name, result in correlation_pairs.items():
            if not result.is_significant:
                recommendations.append(
                    f"PAIR CONCERN: {pair_name} correlation ({result.pearson_correlation:.3f}) is not statistically significant."
                )
            
            if result.correlation_stability < 0.3:
                recommendations.append(
                    f"STABILITY ISSUE: {pair_name} correlation is unstable (stability: {result.correlation_stability:.3f})."
                )
        
        return recommendations
