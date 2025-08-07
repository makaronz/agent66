"""
Diebold-Mariano Test for Forecast Accuracy Comparison

This module implements the Diebold-Mariano test for comparing the accuracy
of forecasts from different models or trading strategies.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass
import scipy.stats as stats

logger = logging.getLogger(__name__)

# Try to import statsmodels, fall back to basic implementation if not available
try:
    from statsmodels.stats.diagnostic import acorr_ljungbox
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available - using basic autocorrelation detection")


@dataclass
class DieboldMarianoResult:
    """Result structure for Diebold-Mariano test."""
    test_name: str
    dm_statistic: float
    p_value: float
    critical_value: float
    is_significant: bool
    significance_level: float
    alternative: str
    loss_function: str
    autocorr_adjustment: bool
    sample_size: int
    degrees_of_freedom: Optional[int]
    interpretation: str
    test_timestamp: datetime


class DieboldMarianoTest:
    """
    Diebold-Mariano Test implementation for forecast accuracy comparison.
    
    Tests whether two forecasting methods have significantly different
    accuracy based on a specified loss function, with proper adjustment
    for autocorrelation in the loss differential series.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Diebold-Mariano test.
        
        Args:
            config: Configuration dictionary containing:
                - significance_level: Statistical significance threshold (default: 0.05)
                - loss_function: Loss function type ('squared', 'absolute', 'quantile', 'custom')
                - alternative: Test alternative ('two-sided', 'less', 'greater')
                - autocorr_adjustment: Apply autocorrelation adjustment (default: True)
                - max_lags: Maximum lags for autocorrelation test (default: 10)
                - min_sample_size: Minimum required sample size (default: 30)
        """
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.loss_function = config.get('loss_function', 'squared')
        self.alternative = config.get('alternative', 'two-sided')
        self.autocorr_adjustment = config.get('autocorr_adjustment', True)
        self.max_lags = config.get('max_lags', 10)
        self.min_sample_size = config.get('min_sample_size', 30)
        
        logger.info(f"DieboldMarianoTest initialized with {self.loss_function} loss function")
    
    async def test(
        self, 
        forecast1: pd.Series, 
        forecast2: pd.Series,
        actual: pd.Series,
        loss_function: Optional[str] = None,
        alternative: Optional[str] = None
    ) -> DieboldMarianoResult:
        """
        Perform Diebold-Mariano test comparing two forecasts.
        
        Args:
            forecast1: First forecast series
            forecast2: Second forecast series
            actual: Actual observed values
            loss_function: Loss function type (overrides default)
            alternative: Test alternative (overrides default)
            
        Returns:
            DieboldMarianoResult: Comprehensive test results
        """
        logger.info("Running Diebold-Mariano test")
        
        try:
            # Use provided parameters or defaults
            loss_func = loss_function or self.loss_function
            test_alternative = alternative or self.alternative
            
            # Prepare and validate data
            f1_clean, f2_clean, actual_clean = await self._prepare_data(
                forecast1, forecast2, actual
            )
            
            # Validate sample size
            self._validate_sample_size(f1_clean)
            
            # Calculate loss differential series
            loss_diff = await self._calculate_loss_differential(
                f1_clean, f2_clean, actual_clean, loss_func
            )
            
            # Calculate Diebold-Mariano statistic
            dm_statistic, degrees_of_freedom = await self._calculate_dm_statistic(
                loss_diff
            )
            
            # Calculate p-value and critical value
            p_value, critical_value = self._calculate_p_value_and_critical(
                dm_statistic, degrees_of_freedom, test_alternative
            )
            
            # Determine statistical significance
            is_significant = p_value < self.significance_level
            
            # Generate interpretation
            interpretation = self._generate_interpretation(
                dm_statistic, p_value, loss_func, test_alternative, is_significant
            )
            
            result = DieboldMarianoResult(
                test_name="Diebold-Mariano Test",
                dm_statistic=dm_statistic,
                p_value=p_value,
                critical_value=critical_value,
                is_significant=is_significant,
                significance_level=self.significance_level,
                alternative=test_alternative,
                loss_function=loss_func,
                autocorr_adjustment=self.autocorr_adjustment,
                sample_size=len(loss_diff),
                degrees_of_freedom=degrees_of_freedom,
                interpretation=interpretation,
                test_timestamp=datetime.now()
            )
            
            logger.info(f"Diebold-Mariano test completed: statistic={dm_statistic:.4f}, p-value={p_value:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Diebold-Mariano test failed: {str(e)}")
            raise
    
    async def _prepare_data(
        self, 
        forecast1: pd.Series, 
        forecast2: pd.Series,
        actual: pd.Series
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare and align forecast and actual data.
        
        Args:
            forecast1: First forecast series
            forecast2: Second forecast series
            actual: Actual observed values
            
        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: Aligned data arrays
        """
        # Create DataFrame for alignment
        data_df = pd.DataFrame({
            'forecast1': forecast1,
            'forecast2': forecast2,
            'actual': actual
        })
        
        # Remove rows with any NaN values
        aligned_data = data_df.dropna()
        
        if len(aligned_data) == 0:
            raise ValueError("No aligned data points found")
        
        # Extract aligned arrays
        f1_clean = aligned_data['forecast1'].values
        f2_clean = aligned_data['forecast2'].values
        actual_clean = aligned_data['actual'].values
        
        # Remove infinite values
        finite_mask = (
            np.isfinite(f1_clean) & 
            np.isfinite(f2_clean) & 
            np.isfinite(actual_clean)
        )
        
        f1_clean = f1_clean[finite_mask]
        f2_clean = f2_clean[finite_mask]
        actual_clean = actual_clean[finite_mask]
        
        logger.info(f"Data prepared: {len(f1_clean)} aligned observations")
        
        return f1_clean, f2_clean, actual_clean
    
    def _validate_sample_size(self, data: np.ndarray):
        """Validate that sample size meets minimum requirements."""
        if len(data) < self.min_sample_size:
            raise ValueError(
                f"Insufficient data: {len(data)} < {self.min_sample_size}"
            )
    
    async def _calculate_loss_differential(
        self, 
        forecast1: np.ndarray, 
        forecast2: np.ndarray,
        actual: np.ndarray,
        loss_function: str
    ) -> np.ndarray:
        """
        Calculate loss differential between two forecasts.
        
        Args:
            forecast1: First forecast array
            forecast2: Second forecast array
            actual: Actual values array
            loss_function: Type of loss function
            
        Returns:
            np.ndarray: Loss differential series
        """
        # Calculate losses for each forecast
        loss1 = self._calculate_loss(forecast1, actual, loss_function)
        loss2 = self._calculate_loss(forecast2, actual, loss_function)
        
        # Loss differential (positive values favor forecast1)
        loss_diff = loss1 - loss2
        
        return loss_diff
    
    def _calculate_loss(
        self, 
        forecast: np.ndarray, 
        actual: np.ndarray, 
        loss_function: str
    ) -> np.ndarray:
        """Calculate loss based on specified loss function."""
        errors = actual - forecast
        
        if loss_function == 'squared':
            # Mean Squared Error
            return errors ** 2
        elif loss_function == 'absolute':
            # Mean Absolute Error
            return np.abs(errors)
        elif loss_function == 'quantile':
            # Quantile loss (asymmetric)
            alpha = self.config.get('quantile_alpha', 0.05)
            return np.where(errors >= 0, alpha * errors, (alpha - 1) * errors)
        elif loss_function == 'log':
            # Logarithmic loss (for positive values)
            return np.log(1 + errors ** 2)
        else:
            raise ValueError(f"Unknown loss function: {loss_function}")
    
    async def _calculate_dm_statistic(self, loss_diff: np.ndarray) -> Tuple[float, Optional[int]]:
        """
        Calculate Diebold-Mariano test statistic.
        
        Args:
            loss_diff: Loss differential series
            
        Returns:
            Tuple[float, Optional[int]]: DM statistic and degrees of freedom
        """
        n = len(loss_diff)
        mean_diff = np.mean(loss_diff)
        
        if self.autocorr_adjustment:
            # Calculate variance with autocorrelation adjustment
            var_diff, degrees_of_freedom = await self._calculate_autocorr_adjusted_variance(
                loss_diff, mean_diff
            )
        else:
            # Simple variance calculation
            var_diff = np.var(loss_diff, ddof=1) / n
            degrees_of_freedom = n - 1
        
        if var_diff <= 0:
            logger.warning("Zero or negative variance in loss differential")
            dm_statistic = 0.0
        else:
            dm_statistic = mean_diff / np.sqrt(var_diff)
        
        return dm_statistic, degrees_of_freedom
    
    async def _calculate_autocorr_adjusted_variance(
        self, 
        loss_diff: np.ndarray, 
        mean_diff: float
    ) -> Tuple[float, int]:
        """
        Calculate variance with autocorrelation adjustment using Newey-West estimator.
        
        Args:
            loss_diff: Loss differential series
            mean_diff: Mean of loss differential
            
        Returns:
            Tuple[float, int]: Adjusted variance and effective degrees of freedom
        """
        n = len(loss_diff)
        centered_diff = loss_diff - mean_diff
        
        # Test for autocorrelation
        try:
            if HAS_STATSMODELS:
                ljung_box_result = acorr_ljungbox(
                    centered_diff, 
                    lags=min(self.max_lags, max(1, n // 4)), 
                    return_df=True
                )
                
                # Check if there's significant autocorrelation
                significant_autocorr = (ljung_box_result['lb_pvalue'] < 0.05).any()
            else:
                # Fallback: simple autocorrelation test
                significant_autocorr = self._simple_autocorr_test(centered_diff)
            
        except Exception as e:
            logger.warning(f"Autocorrelation test failed: {str(e)}")
            significant_autocorr = True  # Assume autocorrelation to be safe
        
        if not significant_autocorr:
            # No significant autocorrelation, use simple variance
            var_diff = np.var(loss_diff, ddof=1) / n
            degrees_of_freedom = n - 1
        else:
            # Apply Newey-West correction
            var_diff, degrees_of_freedom = self._newey_west_variance(centered_diff)
        
        return var_diff, degrees_of_freedom
    
    def _newey_west_variance(self, centered_diff: np.ndarray) -> Tuple[float, int]:
        """Calculate Newey-West autocorrelation-robust variance estimator."""
        n = len(centered_diff)
        
        # Automatic lag selection (Newey-West rule)
        max_lag = min(int(4 * (n / 100) ** (2/9)), n // 4)
        
        # Calculate variance and autocovariances
        gamma_0 = np.mean(centered_diff ** 2)
        
        # Calculate autocovariances up to max_lag
        autocovs = []
        for lag in range(1, max_lag + 1):
            if lag >= n:
                break
            autocov = np.mean(centered_diff[:-lag] * centered_diff[lag:])
            autocovs.append(autocov)
        
        # Newey-West weights (Bartlett kernel)
        nw_variance = gamma_0
        for lag, autocov in enumerate(autocovs, 1):
            weight = 1 - lag / (max_lag + 1)
            nw_variance += 2 * weight * autocov
        
        # Adjust for sample size
        nw_variance = nw_variance / n
        
        # Effective degrees of freedom (conservative estimate)
        effective_n = n / (1 + 2 * sum(autocovs) / gamma_0)
        degrees_of_freedom = max(1, int(effective_n) - 1)
        
        return nw_variance, degrees_of_freedom
    
    def _simple_autocorr_test(self, data: np.ndarray) -> bool:
        """
        Simple autocorrelation test using first-order autocorrelation.
        
        Args:
            data: Time series data
            
        Returns:
            bool: True if significant autocorrelation detected
        """
        try:
            if len(data) < 10:
                return False
                
            # Calculate first-order autocorrelation
            autocorr_1 = np.corrcoef(data[:-1], data[1:])[0, 1]
            
            # Simple test: if |autocorr| > 2/sqrt(n), likely significant
            n = len(data)
            threshold = 2 / np.sqrt(n)
            
            return abs(autocorr_1) > threshold
            
        except Exception:
            return True  # Assume autocorrelation to be safe
    
    def _calculate_p_value_and_critical(
        self, 
        dm_statistic: float, 
        degrees_of_freedom: Optional[int],
        alternative: str
    ) -> Tuple[float, float]:
        """Calculate p-value and critical value for the test."""
        
        if degrees_of_freedom is None or degrees_of_freedom > 30:
            # Use normal distribution for large samples
            if alternative == 'two-sided':
                p_value = 2 * (1 - stats.norm.cdf(abs(dm_statistic)))
                critical_value = stats.norm.ppf(1 - self.significance_level / 2)
            elif alternative == 'greater':
                p_value = 1 - stats.norm.cdf(dm_statistic)
                critical_value = stats.norm.ppf(1 - self.significance_level)
            else:  # 'less'
                p_value = stats.norm.cdf(dm_statistic)
                critical_value = -stats.norm.ppf(1 - self.significance_level)
        else:
            # Use t-distribution for small samples
            if alternative == 'two-sided':
                p_value = 2 * (1 - stats.t.cdf(abs(dm_statistic), degrees_of_freedom))
                critical_value = stats.t.ppf(1 - self.significance_level / 2, degrees_of_freedom)
            elif alternative == 'greater':
                p_value = 1 - stats.t.cdf(dm_statistic, degrees_of_freedom)
                critical_value = stats.t.ppf(1 - self.significance_level, degrees_of_freedom)
            else:  # 'less'
                p_value = stats.t.cdf(dm_statistic, degrees_of_freedom)
                critical_value = -stats.t.ppf(1 - self.significance_level, degrees_of_freedom)
        
        return p_value, critical_value
    
    def _generate_interpretation(
        self, 
        dm_statistic: float, 
        p_value: float,
        loss_function: str,
        alternative: str,
        is_significant: bool
    ) -> str:
        """Generate human-readable interpretation of test results."""
        
        # Direction interpretation
        if dm_statistic > 0:
            direction = "Forecast 1 has higher loss (worse performance) than Forecast 2"
            better_forecast = "Forecast 2"
        elif dm_statistic < 0:
            direction = "Forecast 1 has lower loss (better performance) than Forecast 2"
            better_forecast = "Forecast 1"
        else:
            direction = "No difference in forecast performance"
            better_forecast = "Neither"
        
        # Statistical significance interpretation
        if is_significant:
            significance = f"The difference is statistically significant (p={p_value:.4f} < {self.significance_level})"
        else:
            significance = f"The difference is not statistically significant (p={p_value:.4f} >= {self.significance_level})"
        
        # Loss function context
        loss_context = f"based on {loss_function} loss function"
        
        # Overall interpretation
        if better_forecast != "Neither":
            interpretation = (
                f"{direction} {loss_context}. "
                f"{better_forecast} appears to be the better forecasting method. "
                f"{significance}."
            )
        else:
            interpretation = (
                f"{direction} {loss_context}. "
                f"{significance}."
            )
        
        return interpretation
    
    def get_required_sample_size(
        self, 
        effect_size: float, 
        power: float = 0.8, 
        alpha: float = None
    ) -> int:
        """
        Calculate required sample size for desired power.
        
        Args:
            effect_size: Expected effect size (difference in mean losses)
            power: Desired statistical power (default: 0.8)
            alpha: Significance level (default: uses instance setting)
            
        Returns:
            int: Required sample size
        """
        try:
            alpha = alpha or self.significance_level
            
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = stats.norm.ppf(power)
            
            # Simplified sample size calculation
            # Assumes unit variance in loss differential
            required_n = 2 * (z_alpha + z_beta) ** 2 / (effect_size ** 2)
            
            return max(self.min_sample_size, int(np.ceil(required_n)))
            
        except Exception as e:
            logger.warning(f"Sample size calculation failed: {str(e)}")
            return self.min_sample_size * 2
