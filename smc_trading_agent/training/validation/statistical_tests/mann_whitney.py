"""
Mann-Whitney U Test for Trading Strategy Validation

This module implements the Mann-Whitney U test for non-parametric comparison
of return distributions between trading strategies and benchmarks.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import scipy.stats as stats

logger = logging.getLogger(__name__)


@dataclass
class MannWhitneyResult:
    """Result structure for Mann-Whitney U test."""
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    alternative: str
    is_significant: bool
    significance_level: float
    sample_sizes: Tuple[int, int]
    interpretation: str
    test_timestamp: datetime


class MannWhitneyTest:
    """
    Mann-Whitney U Test implementation for trading strategy validation.
    
    Performs non-parametric comparison of return distributions between
    a trading strategy and benchmark to determine if there are statistically
    significant differences in performance.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Mann-Whitney U test.
        
        Args:
            config: Configuration dictionary containing:
                - significance_level: Statistical significance threshold (default: 0.05)
                - alternative: Test alternative ('two-sided', 'less', 'greater')
                - confidence_level: Confidence level for effect size CI (default: 0.95)
                - min_sample_size: Minimum required sample size (default: 30)
        """
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.alternative = config.get('alternative', 'two-sided')
        self.confidence_level = config.get('confidence_level', 0.95)
        self.min_sample_size = config.get('min_sample_size', 30)
        
        logger.info(f"MannWhitneyTest initialized with significance level: {self.significance_level}")
    
    async def test(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series,
        alternative: Optional[str] = None
    ) -> MannWhitneyResult:
        """
        Perform Mann-Whitney U test comparing strategy and benchmark returns.
        
        Args:
            strategy_returns: Strategy return series
            benchmark_returns: Benchmark return series
            alternative: Test alternative ('two-sided', 'less', 'greater')
            
        Returns:
            MannWhitneyResult: Comprehensive test results
        """
        logger.info("Running Mann-Whitney U test")
        
        try:
            # Use provided alternative or default
            test_alternative = alternative or self.alternative
            
            # Prepare and validate data
            strategy_clean, benchmark_clean = await self._prepare_data(
                strategy_returns, benchmark_returns
            )
            
            # Validate sample sizes
            self._validate_sample_sizes(strategy_clean, benchmark_clean)
            
            # Perform Mann-Whitney U test
            statistic, p_value = stats.mannwhitneyu(
                strategy_clean, 
                benchmark_clean, 
                alternative=test_alternative
            )
            
            # Calculate effect size (rank-biserial correlation)
            effect_size = await self._calculate_effect_size(strategy_clean, benchmark_clean)
            
            # Calculate confidence interval for effect size
            confidence_interval = await self._calculate_confidence_interval(
                strategy_clean, benchmark_clean, effect_size
            )
            
            # Determine statistical significance
            is_significant = p_value < self.significance_level
            
            # Generate interpretation
            interpretation = self._generate_interpretation(
                statistic, p_value, effect_size, test_alternative, is_significant
            )
            
            result = MannWhitneyResult(
                test_name="Mann-Whitney U Test",
                statistic=statistic,
                p_value=p_value,
                effect_size=effect_size,
                confidence_interval=confidence_interval,
                alternative=test_alternative,
                is_significant=is_significant,
                significance_level=self.significance_level,
                sample_sizes=(len(strategy_clean), len(benchmark_clean)),
                interpretation=interpretation,
                test_timestamp=datetime.now()
            )
            
            logger.info(f"Mann-Whitney U test completed: statistic={statistic:.4f}, p-value={p_value:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Mann-Whitney U test failed: {str(e)}")
            raise
    
    async def _prepare_data(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare and clean data for statistical testing.
        
        Args:
            strategy_returns: Strategy return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Cleaned strategy and benchmark returns
        """
        # Remove NaN values
        strategy_clean = strategy_returns.dropna().values
        benchmark_clean = benchmark_returns.dropna().values
        
        # Remove infinite values
        strategy_clean = strategy_clean[np.isfinite(strategy_clean)]
        benchmark_clean = benchmark_clean[np.isfinite(benchmark_clean)]
        
        # Remove extreme outliers (beyond 5 standard deviations)
        strategy_clean = self._remove_extreme_outliers(strategy_clean)
        benchmark_clean = self._remove_extreme_outliers(benchmark_clean)
        
        logger.info(f"Data prepared: strategy={len(strategy_clean)}, benchmark={len(benchmark_clean)} observations")
        
        return strategy_clean, benchmark_clean
    
    def _remove_extreme_outliers(self, data: np.ndarray, threshold: float = 5.0) -> np.ndarray:
        """Remove extreme outliers beyond threshold standard deviations."""
        if len(data) == 0:
            return data
            
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return data
            
        outlier_mask = np.abs(data - mean) <= threshold * std
        return data[outlier_mask]
    
    def _validate_sample_sizes(self, strategy_data: np.ndarray, benchmark_data: np.ndarray):
        """Validate that sample sizes meet minimum requirements."""
        if len(strategy_data) < self.min_sample_size:
            raise ValueError(
                f"Insufficient strategy data: {len(strategy_data)} < {self.min_sample_size}"
            )
        
        if len(benchmark_data) < self.min_sample_size:
            raise ValueError(
                f"Insufficient benchmark data: {len(benchmark_data)} < {self.min_sample_size}"
            )
    
    async def _calculate_effect_size(
        self, 
        strategy_data: np.ndarray, 
        benchmark_data: np.ndarray
    ) -> float:
        """
        Calculate effect size (rank-biserial correlation) for Mann-Whitney test.
        
        Args:
            strategy_data: Strategy return data
            benchmark_data: Benchmark return data
            
        Returns:
            float: Effect size (rank-biserial correlation)
        """
        try:
            n1, n2 = len(strategy_data), len(benchmark_data)
            
            # Calculate U statistic manually for effect size calculation
            combined = np.concatenate([strategy_data, benchmark_data])
            ranks = stats.rankdata(combined)
            
            # Sum of ranks for strategy data
            R1 = np.sum(ranks[:n1])
            
            # Calculate U1 statistic
            U1 = R1 - n1 * (n1 + 1) / 2
            
            # Calculate effect size (rank-biserial correlation)
            effect_size = 1 - (2 * U1) / (n1 * n2)
            
            return effect_size
            
        except Exception as e:
            logger.warning(f"Effect size calculation failed: {str(e)}")
            return 0.0
    
    async def _calculate_confidence_interval(
        self, 
        strategy_data: np.ndarray, 
        benchmark_data: np.ndarray,
        effect_size: float
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for effect size using bootstrap.
        
        Args:
            strategy_data: Strategy return data
            benchmark_data: Benchmark return data
            effect_size: Calculated effect size
            
        Returns:
            Tuple[float, float]: Lower and upper bounds of confidence interval
        """
        try:
            n_bootstrap = self.config.get('bootstrap_samples', 1000)
            bootstrap_effects = []
            
            for _ in range(n_bootstrap):
                # Bootstrap samples
                strategy_boot = np.random.choice(strategy_data, size=len(strategy_data), replace=True)
                benchmark_boot = np.random.choice(benchmark_data, size=len(benchmark_data), replace=True)
                
                # Calculate bootstrap effect size
                boot_effect = await self._calculate_effect_size(strategy_boot, benchmark_boot)
                bootstrap_effects.append(boot_effect)
            
            # Calculate confidence interval
            alpha = 1 - self.confidence_level
            lower_percentile = (alpha / 2) * 100
            upper_percentile = (1 - alpha / 2) * 100
            
            lower_bound = np.percentile(bootstrap_effects, lower_percentile)
            upper_bound = np.percentile(bootstrap_effects, upper_percentile)
            
            return (lower_bound, upper_bound)
            
        except Exception as e:
            logger.warning(f"Confidence interval calculation failed: {str(e)}")
            # Return effect size ± 0.1 as fallback
            return (effect_size - 0.1, effect_size + 0.1)
    
    def _generate_interpretation(
        self, 
        statistic: float, 
        p_value: float, 
        effect_size: float,
        alternative: str,
        is_significant: bool
    ) -> str:
        """
        Generate human-readable interpretation of test results.
        
        Args:
            statistic: Test statistic
            p_value: P-value
            effect_size: Effect size
            alternative: Test alternative
            is_significant: Whether result is statistically significant
            
        Returns:
            str: Human-readable interpretation
        """
        # Effect size interpretation
        if abs(effect_size) < 0.1:
            effect_magnitude = "negligible"
        elif abs(effect_size) < 0.3:
            effect_magnitude = "small"
        elif abs(effect_size) < 0.5:
            effect_magnitude = "medium"
        else:
            effect_magnitude = "large"
        
        # Direction interpretation
        if effect_size > 0:
            direction = "Strategy returns tend to be higher than benchmark returns"
        elif effect_size < 0:
            direction = "Strategy returns tend to be lower than benchmark returns"
        else:
            direction = "No difference between strategy and benchmark returns"
        
        # Statistical significance interpretation
        if is_significant:
            significance = f"The difference is statistically significant (p={p_value:.4f} < {self.significance_level})"
        else:
            significance = f"The difference is not statistically significant (p={p_value:.4f} >= {self.significance_level})"
        
        # Overall interpretation
        interpretation = (
            f"{direction}. "
            f"Effect size is {effect_magnitude} ({effect_size:.3f}). "
            f"{significance}."
        )
        
        return interpretation
    
    def get_test_power(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series,
        effect_size: float
    ) -> float:
        """
        Calculate statistical power of the test.
        
        Args:
            strategy_returns: Strategy return series
            benchmark_returns: Benchmark return series
            effect_size: Expected effect size
            
        Returns:
            float: Statistical power (0-1)
        """
        try:
            # Simplified power calculation based on sample sizes and effect size
            n1, n2 = len(strategy_returns.dropna()), len(benchmark_returns.dropna())
            
            # Use approximation for Mann-Whitney power
            # This is a simplified calculation - for precise power analysis,
            # Monte Carlo simulation would be needed
            
            harmonic_mean_n = 2 * n1 * n2 / (n1 + n2)
            z_alpha = stats.norm.ppf(1 - self.significance_level / 2)
            z_beta = abs(effect_size) * np.sqrt(harmonic_mean_n / 12) - z_alpha
            
            power = 1 - stats.norm.cdf(z_beta)
            
            return max(0.0, min(1.0, power))
            
        except Exception as e:
            logger.warning(f"Power calculation failed: {str(e)}")
            return 0.5  # Return moderate power as fallback
    
    def get_required_sample_size(
        self, 
        effect_size: float, 
        power: float = 0.8, 
        alpha: float = None
    ) -> int:
        """
        Calculate required sample size for desired power.
        
        Args:
            effect_size: Expected effect size
            power: Desired statistical power (default: 0.8)
            alpha: Significance level (default: uses instance setting)
            
        Returns:
            int: Required sample size per group
        """
        try:
            alpha = alpha or self.significance_level
            
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = stats.norm.ppf(power)
            
            # Simplified sample size calculation for Mann-Whitney test
            required_n = 12 * (z_alpha + z_beta) ** 2 / (effect_size ** 2)
            
            return max(self.min_sample_size, int(np.ceil(required_n)))
            
        except Exception as e:
            logger.warning(f"Sample size calculation failed: {str(e)}")
            return self.min_sample_size * 2  # Return conservative estimate
