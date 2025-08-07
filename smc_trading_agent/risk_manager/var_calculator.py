"""
Value at Risk (VaR) Calculator for SMC Trading Agent.

This module provides comprehensive VaR calculation methods including:
- Historical VaR calculation
- Parametric VaR calculation  
- Monte Carlo VaR simulation
- Correlation analysis across portfolio positions
- Real-time monitoring and threshold checking
"""

import numpy as np
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import warnings

logger = logging.getLogger(__name__)


class VaRMethod(Enum):
    """VaR calculation methods."""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


@dataclass
class VaRResult:
    """VaR calculation result."""
    var_value: float
    confidence_level: float
    method: VaRMethod
    calculation_time: float
    data_points: int
    portfolio_value: float
    timestamp: float


@dataclass
class CorrelationResult:
    """Correlation analysis result."""
    correlation_matrix: pd.DataFrame
    max_correlation: float
    min_correlation: float
    avg_correlation: float
    high_correlation_pairs: List[Tuple[str, str, float]]
    calculation_time: float
    timestamp: float


class VaRCalculator:
    """
    Comprehensive VaR calculator with multiple calculation methods.
    
    Supports historical, parametric, and Monte Carlo VaR calculations
    along with correlation analysis for portfolio risk management.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize VaR calculator.
        
        Args:
            config: Configuration dictionary with VaR parameters
        """
        self.config = config
        self.confidence_levels = config.get('confidence_levels', [0.95, 0.99])
        self.lookback_period = config.get('lookback_period', 252)  # Trading days
        self.monte_carlo_simulations = config.get('monte_carlo_simulations', 10000)
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        
        # Cache for expensive calculations
        self._var_cache = {}
        self._correlation_cache = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes
        
        logger.info(f"Initialized VaR calculator with {len(self.confidence_levels)} confidence levels")
    
    async def calculate_var(self, portfolio_data: pd.DataFrame, 
                          method: VaRMethod = VaRMethod.HISTORICAL,
                          confidence_level: float = 0.95) -> VaRResult:
        """
        Calculate Value at Risk using specified method.
        
        Args:
            portfolio_data: Portfolio returns data
            method: VaR calculation method
            confidence_level: Confidence level for VaR calculation
            
        Returns:
            VaRResult: VaR calculation result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check cache first
            cache_key = f"{method.value}_{confidence_level}_{hash(str(portfolio_data.tail(10)))}"
            if cache_key in self._var_cache:
                cached_result = self._var_cache[cache_key]
                if (asyncio.get_event_loop().time() - cached_result.timestamp) < self.cache_ttl:
                    logger.debug(f"Using cached VaR result for {method.value}")
                    return cached_result
            
            # Calculate VaR based on method
            if method == VaRMethod.HISTORICAL:
                var_value = await self._calculate_historical_var(portfolio_data, confidence_level)
            elif method == VaRMethod.PARAMETRIC:
                var_value = await self._calculate_parametric_var(portfolio_data, confidence_level)
            elif method == VaRMethod.MONTE_CARLO:
                var_value = await self._calculate_monte_carlo_var(portfolio_data, confidence_level)
            else:
                raise ValueError(f"Unknown VaR method: {method}")
            
            # Create result
            calculation_time = asyncio.get_event_loop().time() - start_time
            result = VaRResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=method,
                calculation_time=calculation_time,
                data_points=len(portfolio_data),
                portfolio_value=portfolio_data['value'].iloc[-1] if 'value' in portfolio_data.columns else 0,
                timestamp=asyncio.get_event_loop().time()
            )
            
            # Cache result
            self._var_cache[cache_key] = result
            
            logger.info(f"Calculated {method.value} VaR: {var_value:.4f} at {confidence_level:.1%} confidence")
            return result
            
        except Exception as e:
            logger.error(f"VaR calculation failed: {e}")
            raise
    
    async def _calculate_historical_var(self, portfolio_data: pd.DataFrame, 
                                      confidence_level: float) -> float:
        """Calculate historical VaR using empirical distribution."""
        try:
            # Calculate portfolio returns
            if 'returns' in portfolio_data.columns:
                returns = portfolio_data['returns']
            else:
                # Calculate returns from portfolio values
                values = portfolio_data['value'] if 'value' in portfolio_data.columns else portfolio_data.iloc[:, 0]
                returns = values.pct_change().dropna()
            
            # Calculate VaR using empirical percentile
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(returns, var_percentile)
            
            return abs(var_value)
            
        except Exception as e:
            logger.error(f"Historical VaR calculation failed: {e}")
            raise
    
    async def _calculate_parametric_var(self, portfolio_data: pd.DataFrame, 
                                      confidence_level: float) -> float:
        """Calculate parametric VaR using normal distribution assumption."""
        try:
            # Calculate portfolio returns
            if 'returns' in portfolio_data.columns:
                returns = portfolio_data['returns']
            else:
                values = portfolio_data['value'] if 'value' in portfolio_data.columns else portfolio_data.iloc[:, 0]
                returns = values.pct_change().dropna()
            
            # Calculate mean and standard deviation
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Calculate VaR using normal distribution
            from scipy.stats import norm
            z_score = norm.ppf(1 - confidence_level)
            var_value = abs(mean_return + z_score * std_return)
            
            return var_value
            
        except Exception as e:
            logger.error(f"Parametric VaR calculation failed: {e}")
            raise
    
    async def _calculate_monte_carlo_var(self, portfolio_data: pd.DataFrame, 
                                       confidence_level: float) -> float:
        """Calculate Monte Carlo VaR using simulation."""
        try:
            # Calculate portfolio returns
            if 'returns' in portfolio_data.columns:
                returns = portfolio_data['returns']
            else:
                values = portfolio_data['value'] if 'value' in portfolio_data.columns else portfolio_data.iloc[:, 0]
                returns = values.pct_change().dropna()
            
            # Fit distribution to returns (use normal for simplicity)
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate Monte Carlo simulations
            np.random.seed(42)  # For reproducibility
            simulated_returns = np.random.normal(mean_return, std_return, self.monte_carlo_simulations)
            
            # Calculate VaR from simulated distribution
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(simulated_returns, var_percentile)
            
            return abs(var_value)
            
        except Exception as e:
            logger.error(f"Monte Carlo VaR calculation failed: {e}")
            raise
    
    async def calculate_correlation_matrix(self, portfolio_data: pd.DataFrame) -> CorrelationResult:
        """
        Calculate correlation matrix for portfolio positions.
        
        Args:
            portfolio_data: Portfolio data with position returns
            
        Returns:
            CorrelationResult: Correlation analysis result
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check cache first
            cache_key = f"correlation_{hash(str(portfolio_data.tail(10)))}"
            if cache_key in self._correlation_cache:
                cached_result = self._correlation_cache[cache_key]
                if (asyncio.get_event_loop().time() - cached_result.timestamp) < self.cache_ttl:
                    logger.debug("Using cached correlation result")
                    return cached_result
            
            # Calculate returns for each position
            returns_data = {}
            for column in portfolio_data.columns:
                if column not in ['timestamp', 'date', 'time']:
                    if 'returns' in column.lower():
                        returns_data[column] = portfolio_data[column]
                    else:
                        # Calculate returns from position values
                        returns_data[column] = portfolio_data[column].pct_change().dropna()
            
            # Create returns DataFrame
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()
            
            # Calculate correlation statistics
            max_correlation = correlation_matrix.max().max()
            min_correlation = correlation_matrix.min().min()
            avg_correlation = correlation_matrix.mean().mean()
            
            # Find high correlation pairs
            high_correlation_pairs = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) > self.correlation_threshold:
                        high_correlation_pairs.append((
                            correlation_matrix.columns[i],
                            correlation_matrix.columns[j],
                            corr_value
                        ))
            
            # Sort by absolute correlation value
            high_correlation_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            
            # Create result
            calculation_time = asyncio.get_event_loop().time() - start_time
            result = CorrelationResult(
                correlation_matrix=correlation_matrix,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                avg_correlation=avg_correlation,
                high_correlation_pairs=high_correlation_pairs,
                calculation_time=calculation_time,
                timestamp=asyncio.get_event_loop().time()
            )
            
            # Cache result
            self._correlation_cache[cache_key] = result
            
            logger.info(f"Calculated correlation matrix: max={max_correlation:.4f}, "
                       f"avg={avg_correlation:.4f}, {len(high_correlation_pairs)} high correlations")
            return result
            
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            raise
    
    async def check_var_threshold(self, var_result: VaRResult, 
                                threshold: float) -> bool:
        """
        Check if VaR exceeds threshold.
        
        Args:
            var_result: VaR calculation result
            threshold: VaR threshold to check against
            
        Returns:
            bool: True if VaR exceeds threshold, False otherwise
        """
        try:
            exceeds_threshold = var_result.var_value > threshold
            
            if exceeds_threshold:
                logger.warning(f"VaR threshold exceeded: {var_result.var_value:.4f} > {threshold:.4f}")
            else:
                logger.debug(f"VaR within threshold: {var_result.var_value:.4f} <= {threshold:.4f}")
            
            return exceeds_threshold
            
        except Exception as e:
            logger.error(f"VaR threshold check failed: {e}")
            raise
    
    async def check_correlation_threshold(self, correlation_result: CorrelationResult,
                                        threshold: float) -> bool:
        """
        Check if correlation exceeds threshold.
        
        Args:
            correlation_result: Correlation analysis result
            threshold: Correlation threshold to check against
            
        Returns:
            bool: True if correlation exceeds threshold, False otherwise
        """
        try:
            exceeds_threshold = abs(correlation_result.max_correlation) > threshold
            
            if exceeds_threshold:
                logger.warning(f"Correlation threshold exceeded: {correlation_result.max_correlation:.4f} > {threshold:.4f}")
            else:
                logger.debug(f"Correlation within threshold: {correlation_result.max_correlation:.4f} <= {threshold:.4f}")
            
            return exceeds_threshold
            
        except Exception as e:
            logger.error(f"Correlation threshold check failed: {e}")
            raise
    
    async def get_risk_summary(self, portfolio_data: pd.DataFrame) -> Dict:
        """
        Get comprehensive risk summary including VaR and correlation.
        
        Args:
            portfolio_data: Portfolio data
            
        Returns:
            Dict: Risk summary with VaR and correlation metrics
        """
        try:
            # Calculate VaR for all methods and confidence levels
            var_results = {}
            for method in VaRMethod:
                for confidence_level in self.confidence_levels:
                    var_results[f"{method.value}_{confidence_level}"] = await self.calculate_var(
                        portfolio_data, method, confidence_level
                    )
            
            # Calculate correlation matrix
            correlation_result = await self.calculate_correlation_matrix(portfolio_data)
            
            # Create risk summary
            risk_summary = {
                "timestamp": asyncio.get_event_loop().time(),
                "var_results": {
                    key: {
                        "var_value": result.var_value,
                        "confidence_level": result.confidence_level,
                        "method": result.method.value,
                        "calculation_time": result.calculation_time
                    }
                    for key, result in var_results.items()
                },
                "correlation_metrics": {
                    "max_correlation": correlation_result.max_correlation,
                    "min_correlation": correlation_result.min_correlation,
                    "avg_correlation": correlation_result.avg_correlation,
                    "high_correlation_pairs": correlation_result.high_correlation_pairs,
                    "calculation_time": correlation_result.calculation_time
                },
                "portfolio_info": {
                    "data_points": len(portfolio_data),
                    "positions": len(portfolio_data.columns) if len(portfolio_data.columns) > 0 else 0
                }
            }
            
            logger.info("Generated comprehensive risk summary")
            return risk_summary
            
        except Exception as e:
            logger.error(f"Risk summary generation failed: {e}")
            raise
    
    def clear_cache(self):
        """Clear calculation cache."""
        self._var_cache.clear()
        self._correlation_cache.clear()
        logger.info("Cleared VaR and correlation calculation cache")
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "var_cache_size": len(self._var_cache),
            "correlation_cache_size": len(self._correlation_cache),
            "cache_ttl": self.cache_ttl
        }
