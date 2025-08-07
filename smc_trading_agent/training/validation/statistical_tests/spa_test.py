"""
Superior Predictive Ability (SPA) Test for Trading Strategy Validation

This module implements the Superior Predictive Ability test introduced by Hansen (2005)
for comparing multiple trading strategies with bootstrap methodology to account for
data snooping bias and multiple comparison issues.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import scipy.stats as stats
from concurrent.futures import ThreadPoolExecutor
import warnings

logger = logging.getLogger(__name__)


@dataclass
class SPAResult:
    """Result structure for Superior Predictive Ability test."""
    test_name: str
    spa_statistic: float
    p_value: float
    confidence_set: List[str]
    confidence_level: float
    best_strategy: str
    benchmark_strategy: str
    strategy_performance: Dict[str, float]
    bootstrap_samples: int
    is_significant: bool
    significance_level: float
    loss_function: str
    interpretation: str
    test_timestamp: datetime


class SPATest:
    """
    Superior Predictive Ability (SPA) Test implementation.
    
    Tests whether any strategy in a given set significantly outperforms
    a benchmark strategy, accounting for data snooping bias through
    bootstrap methodology.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SPA test.
        
        Args:
            config: Configuration dictionary containing:
                - significance_level: Statistical significance threshold (default: 0.05)
                - bootstrap_samples: Number of bootstrap samples (default: 10000)
                - block_size: Block size for bootstrap (default: None, auto-selected)
                - loss_function: Loss function type ('squared', 'absolute', 'quantile')
                - confidence_level: Confidence level for confidence set (default: 0.95)
                - parallel_processing: Use parallel processing for bootstrap (default: True)
                - max_workers: Maximum number of worker threads (default: None)
        """
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.bootstrap_samples = config.get('bootstrap_samples', 10000)
        self.block_size = config.get('block_size', None)
        self.loss_function = config.get('loss_function', 'squared')
        self.confidence_level = config.get('confidence_level', 0.95)
        self.parallel_processing = config.get('parallel_processing', True)
        self.max_workers = config.get('max_workers', None)
        
        logger.info(f"SPATest initialized with {self.bootstrap_samples} bootstrap samples")
    
    async def test(
        self, 
        strategy_returns: Dict[str, pd.Series], 
        benchmark_name: str,
        loss_function: Optional[str] = None
    ) -> SPAResult:
        """
        Perform Superior Predictive Ability test.
        
        Args:
            strategy_returns: Dictionary mapping strategy names to return series
            benchmark_name: Name of the benchmark strategy
            loss_function: Loss function to use ('squared', 'absolute', 'quantile')
            
        Returns:
            SPAResult: Comprehensive SPA test results
        """
        logger.info(f"Running SPA test with {len(strategy_returns)} strategies")
        
        try:
            # Use provided loss function or default
            loss_func = loss_function or self.loss_function
            
            # Validate inputs
            self._validate_inputs(strategy_returns, benchmark_name)
            
            # Prepare data
            aligned_returns = await self._prepare_data(strategy_returns)
            
            # Calculate loss differences
            loss_differences = await self._calculate_loss_differences(
                aligned_returns, benchmark_name, loss_func
            )
            
            # Calculate SPA statistic
            spa_statistic = np.max(np.mean(loss_differences, axis=0))
            
            # Perform bootstrap test
            p_value = await self._bootstrap_test(
                loss_differences, spa_statistic
            )
            
            # Construct confidence set
            confidence_set = await self._construct_confidence_set(
                loss_differences, aligned_returns.columns.tolist()
            )
            
            # Identify best strategy
            mean_losses = np.mean(loss_differences, axis=0)
            strategy_names = [col for col in aligned_returns.columns if col != benchmark_name]
            best_idx = np.argmax(mean_losses)
            best_strategy = strategy_names[best_idx]
            
            # Calculate strategy performance metrics
            strategy_performance = await self._calculate_strategy_performance(
                aligned_returns, benchmark_name
            )
            
            # Determine statistical significance
            is_significant = p_value < self.significance_level
            
            # Generate interpretation
            interpretation = self._generate_interpretation(
                spa_statistic, p_value, confidence_set, best_strategy, 
                benchmark_name, is_significant
            )
            
            result = SPAResult(
                test_name="Superior Predictive Ability (SPA) Test",
                spa_statistic=spa_statistic,
                p_value=p_value,
                confidence_set=confidence_set,
                confidence_level=self.confidence_level,
                best_strategy=best_strategy,
                benchmark_strategy=benchmark_name,
                strategy_performance=strategy_performance,
                bootstrap_samples=self.bootstrap_samples,
                is_significant=is_significant,
                significance_level=self.significance_level,
                loss_function=loss_func,
                interpretation=interpretation,
                test_timestamp=datetime.now()
            )
            
            logger.info(f"SPA test completed: statistic={spa_statistic:.4f}, p-value={p_value:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"SPA test failed: {str(e)}")
            raise
    
    def _validate_inputs(self, strategy_returns: Dict[str, pd.Series], benchmark_name: str):
        """Validate input data."""
        if not strategy_returns:
            raise ValueError("Strategy returns dictionary cannot be empty")
        
        if benchmark_name not in strategy_returns:
            raise ValueError(f"Benchmark strategy '{benchmark_name}' not found in strategy returns")
        
        if len(strategy_returns) < 2:
            raise ValueError("At least 2 strategies (including benchmark) are required")
        
        # Check for minimum data requirements
        min_observations = 50
        for name, returns in strategy_returns.items():
            if len(returns.dropna()) < min_observations:
                raise ValueError(f"Insufficient data for strategy '{name}': {len(returns.dropna())} < {min_observations}")
    
    async def _prepare_data(self, strategy_returns: Dict[str, pd.Series]) -> pd.DataFrame:
        """Prepare and align strategy return data."""
        # Create DataFrame from strategy returns
        returns_df = pd.DataFrame(strategy_returns)
        
        # Remove rows with any NaN values (align all series)
        aligned_returns = returns_df.dropna()
        
        if len(aligned_returns) == 0:
            raise ValueError("No overlapping data found across all strategies")
        
        logger.info(f"Data aligned: {len(aligned_returns)} observations across {len(aligned_returns.columns)} strategies")
        
        return aligned_returns
    
    async def _calculate_loss_differences(
        self, 
        aligned_returns: pd.DataFrame, 
        benchmark_name: str,
        loss_function: str
    ) -> np.ndarray:
        """
        Calculate loss differences between strategies and benchmark.
        
        Args:
            aligned_returns: Aligned return data
            benchmark_name: Name of benchmark strategy
            loss_function: Type of loss function
            
        Returns:
            np.ndarray: Loss differences (observations x strategies)
        """
        benchmark_returns = aligned_returns[benchmark_name].values
        
        # Calculate losses for benchmark
        benchmark_losses = self._calculate_losses(benchmark_returns, loss_function)
        
        # Calculate loss differences for each strategy
        loss_differences = []
        
        for col in aligned_returns.columns:
            if col != benchmark_name:
                strategy_returns = aligned_returns[col].values
                strategy_losses = self._calculate_losses(strategy_returns, loss_function)
                
                # Loss difference = benchmark loss - strategy loss
                # Positive values indicate strategy outperforms benchmark
                loss_diff = benchmark_losses - strategy_losses
                loss_differences.append(loss_diff)
        
        return np.column_stack(loss_differences)
    
    def _calculate_losses(self, returns: np.ndarray, loss_function: str) -> np.ndarray:
        """Calculate losses based on specified loss function."""
        if loss_function == 'squared':
            # Squared loss (penalizes large negative returns more)
            return -returns ** 2
        elif loss_function == 'absolute':
            # Absolute loss
            return -np.abs(returns)
        elif loss_function == 'quantile':
            # Quantile loss (focuses on downside risk)
            alpha = self.config.get('quantile_alpha', 0.05)
            return np.where(returns < 0, -returns * alpha, -returns * (1 - alpha))
        else:
            raise ValueError(f"Unknown loss function: {loss_function}")
    
    async def _bootstrap_test(
        self, 
        loss_differences: np.ndarray, 
        spa_statistic: float
    ) -> float:
        """
        Perform bootstrap test to calculate p-value.
        
        Args:
            loss_differences: Original loss differences
            spa_statistic: Original SPA statistic
            
        Returns:
            float: Bootstrap p-value
        """
        if self.parallel_processing:
            return await self._bootstrap_test_parallel(loss_differences, spa_statistic)
        else:
            return await self._bootstrap_test_sequential(loss_differences, spa_statistic)
    
    async def _bootstrap_test_parallel(
        self, 
        loss_differences: np.ndarray, 
        spa_statistic: float
    ) -> float:
        """Perform bootstrap test with parallel processing."""
        def bootstrap_worker(n_samples: int) -> List[float]:
            """Worker function for parallel bootstrap."""
            bootstrap_statistics = []
            n_obs, n_strategies = loss_differences.shape
            
            for _ in range(n_samples):
                # Generate bootstrap sample
                if self.block_size is None:
                    # Simple bootstrap
                    boot_indices = np.random.randint(0, n_obs, n_obs)
                else:
                    # Block bootstrap for time series
                    boot_indices = self._block_bootstrap_indices(n_obs, self.block_size)
                
                boot_loss_diff = loss_differences[boot_indices]
                
                # Center the bootstrap sample
                boot_loss_diff_centered = boot_loss_diff - np.mean(loss_differences, axis=0)
                
                # Calculate bootstrap SPA statistic
                boot_spa_stat = np.max(np.mean(boot_loss_diff_centered, axis=0))
                bootstrap_statistics.append(boot_spa_stat)
            
            return bootstrap_statistics
        
        # Split bootstrap samples across workers
        n_workers = self.max_workers or min(4, self.bootstrap_samples // 1000)
        samples_per_worker = self.bootstrap_samples // n_workers
        
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [
                executor.submit(bootstrap_worker, samples_per_worker)
                for _ in range(n_workers)
            ]
            
            bootstrap_results = []
            for future in futures:
                bootstrap_results.extend(future.result())
        
        # Calculate p-value
        bootstrap_statistics = np.array(bootstrap_results)
        p_value = np.mean(bootstrap_statistics >= spa_statistic)
        
        return p_value
    
    async def _bootstrap_test_sequential(
        self, 
        loss_differences: np.ndarray, 
        spa_statistic: float
    ) -> float:
        """Perform bootstrap test sequentially."""
        bootstrap_statistics = []
        n_obs, n_strategies = loss_differences.shape
        
        for i in range(self.bootstrap_samples):
            if i % 1000 == 0:
                logger.info(f"Bootstrap progress: {i}/{self.bootstrap_samples}")
            
            # Generate bootstrap sample
            if self.block_size is None:
                # Simple bootstrap
                boot_indices = np.random.randint(0, n_obs, n_obs)
            else:
                # Block bootstrap for time series
                boot_indices = self._block_bootstrap_indices(n_obs, self.block_size)
            
            boot_loss_diff = loss_differences[boot_indices]
            
            # Center the bootstrap sample
            boot_loss_diff_centered = boot_loss_diff - np.mean(loss_differences, axis=0)
            
            # Calculate bootstrap SPA statistic
            boot_spa_stat = np.max(np.mean(boot_loss_diff_centered, axis=0))
            bootstrap_statistics.append(boot_spa_stat)
        
        # Calculate p-value
        bootstrap_statistics = np.array(bootstrap_statistics)
        p_value = np.mean(bootstrap_statistics >= spa_statistic)
        
        return p_value
    
    def _block_bootstrap_indices(self, n_obs: int, block_size: int) -> np.ndarray:
        """Generate block bootstrap indices for time series data."""
        if block_size is None:
            block_size = max(1, int(np.sqrt(n_obs)))
        
        n_blocks = int(np.ceil(n_obs / block_size))
        indices = []
        
        for _ in range(n_blocks):
            start_idx = np.random.randint(0, n_obs - block_size + 1)
            block_indices = np.arange(start_idx, min(start_idx + block_size, n_obs))
            indices.extend(block_indices)
        
        return np.array(indices[:n_obs])
    
    async def _construct_confidence_set(
        self, 
        loss_differences: np.ndarray, 
        strategy_names: List[str]
    ) -> List[str]:
        """
        Construct confidence set of strategies that are not significantly worse than the best.
        
        Args:
            loss_differences: Loss differences matrix
            strategy_names: List of strategy names
            
        Returns:
            List[str]: Strategies in the confidence set
        """
        # Remove benchmark from strategy names for confidence set
        benchmark_name = self.config.get('benchmark_name', strategy_names[0])
        strategy_names_filtered = [name for name in strategy_names if name != benchmark_name]
        
        mean_losses = np.mean(loss_differences, axis=0)
        max_mean_loss = np.max(mean_losses)
        
        # Critical value for confidence set construction
        alpha = 1 - self.confidence_level
        critical_value = stats.norm.ppf(1 - alpha / 2)
        
        confidence_set = []
        
        for i, strategy_name in enumerate(strategy_names_filtered):
            # Test if strategy is significantly worse than the best
            loss_diff_from_best = mean_losses[i] - max_mean_loss
            se_diff = np.std(loss_differences[:, i] - loss_differences[:, np.argmax(mean_losses)]) / np.sqrt(len(loss_differences))
            
            t_stat = loss_diff_from_best / (se_diff + 1e-10)  # Add small constant to avoid division by zero
            
            # Include in confidence set if not significantly worse
            if t_stat >= -critical_value:
                confidence_set.append(strategy_name)
        
        return confidence_set
    
    async def _calculate_strategy_performance(
        self, 
        aligned_returns: pd.DataFrame, 
        benchmark_name: str
    ) -> Dict[str, float]:
        """Calculate performance metrics for each strategy."""
        performance = {}
        
        for col in aligned_returns.columns:
            returns = aligned_returns[col]
            
            # Calculate basic performance metrics
            mean_return = returns.mean()
            volatility = returns.std()
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0
            
            # Calculate relative performance vs benchmark if not benchmark itself
            if col != benchmark_name:
                benchmark_returns = aligned_returns[benchmark_name]
                excess_returns = returns - benchmark_returns
                information_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
            else:
                information_ratio = 0
            
            performance[col] = {
                'mean_return': mean_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'information_ratio': information_ratio
            }
        
        return performance
    
    def _generate_interpretation(
        self, 
        spa_statistic: float, 
        p_value: float, 
        confidence_set: List[str],
        best_strategy: str,
        benchmark_name: str,
        is_significant: bool
    ) -> str:
        """Generate human-readable interpretation of SPA test results."""
        
        if is_significant:
            significance_msg = f"There is statistically significant evidence (p={p_value:.4f}) that at least one strategy outperforms the benchmark '{benchmark_name}'"
        else:
            significance_msg = f"No statistically significant evidence (p={p_value:.4f}) that any strategy outperforms the benchmark '{benchmark_name}'"
        
        best_strategy_msg = f"The best performing strategy is '{best_strategy}'"
        
        if len(confidence_set) == 1:
            confidence_msg = f"Only '{confidence_set[0]}' is in the {self.confidence_level*100:.0f}% confidence set"
        elif len(confidence_set) > 1:
            confidence_msg = f"{len(confidence_set)} strategies are in the {self.confidence_level*100:.0f}% confidence set: {', '.join(confidence_set)}"
        else:
            confidence_msg = f"No strategies are in the {self.confidence_level*100:.0f}% confidence set"
        
        interpretation = f"{significance_msg}. {best_strategy_msg}. {confidence_msg}."
        
        return interpretation
