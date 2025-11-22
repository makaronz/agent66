"""
Enhanced Value at Risk (VaR) Calculator with Institutional-Grade Features

This module provides comprehensive VaR calculation methods including:
- Historical VaR with multiple time horizons (1-day, 5-day, 10-day)
- Monte Carlo VaR simulation with advanced distributions
- Conditional VaR (CVaR/Expected Shortfall) calculations
- Stress testing scenarios and scenario analysis
- Backtesting with Kupiec test and Christoffersen test
- Risk metrics aggregation and decomposition
"""

import numpy as np
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from scipy import stats
from scipy.optimize import minimize
import warnings

logger = logging.getLogger(__name__)

class VaRMethod(Enum):
    """VaR calculation methods."""
    HISTORICAL = "historical"
    PARAMETRIC_NORMAL = "parametric_normal"
    PARAMETRIC_T = "parametric_t"
    MONTE_CARLO = "monte_carlo"
    EXTREME_VALUE = "extreme_value"

class DistributionType(Enum):
    """Distribution types for Monte Carlo simulation."""
    NORMAL = "normal"
    STUDENT_T = "student_t"
    SKEWED_T = "skewed_t"
    GENERALIZED_ERROR = "generalized_error"

class StressScenario(Enum):
    """Predefined stress scenarios."""
    MARKET_CRASH = "market_crash"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    INTEREST_RATE_SHOCK = "interest_rate_shock"
    CUSTOM = "custom"

@dataclass
class VaRResult:
    """Enhanced VaR calculation result."""
    var_value: float
    confidence_level: float
    time_horizon: int  # days
    method: VaRMethod
    distribution: Optional[DistributionType]
    calculation_time: float
    data_points: int
    portfolio_value: float
    timestamp: datetime
    additional_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class CVaRResult:
    """Conditional VaR (Expected Shortfall) result."""
    cvar_value: float
    var_value: float
    confidence_level: float
    expected_shortfall: float
    tail_mean: float
    tail_variance: float
    time_horizon: int
    method: VaRMethod
    calculation_time: float
    timestamp: datetime

@dataclass
class StressTestResult:
    """Stress test result."""
    scenario: StressScenario
    description: str
    stressed_var: float
    stressed_portfolio_value: float
    percentage_loss: float
    scenario_params: Dict[str, Any]
    calculation_time: datetime

@dataclass
class BacktestResult:
    """VaR backtest result."""
    method: VaRMethod
    confidence_level: float
    test_period: Tuple[datetime, datetime]
    exceptions: int
    total_observations: int
   kupiec_statistic: float
    kupiec_p_value: float
    christoffersen_statistic: float
    christoffersen_p_value: float
    passed_kupiec: bool
    passed_christoffersen: bool
    average_exception_size: float

class EnhancedVaRCalculator:
    """
    Enhanced VaR calculator with institutional-grade features.

    Supports multiple calculation methods, stress testing, and comprehensive backtesting.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Enhanced VaR calculator.

        Args:
            config: Configuration dictionary with VaR parameters
        """
        self.config = config or {}
        self.confidence_levels = self.config.get('confidence_levels', [0.95, 0.99])
        self.time_horizons = self.config.get('time_horizons', [1, 5, 10])  # days
        self.lookback_period = self.config.get('lookback_period', 252)  # Trading days
        self.monte_carlo_simulations = self.config.get('monte_carlo_simulations', 10000)
        self.bootstrap_samples = self.config.get('bootstrap_samples', 1000)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.7)

        # Cache for expensive calculations
        self._var_cache = {}
        self._cvar_cache = {}
        self._stress_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes

        # Stress scenario parameters
        self.stress_scenarios = self._initialize_stress_scenarios()

        # Backtest configuration
        self.backtest_window = self.config.get('backtest_window', 252)  # days
        self.backtest_rolling = self.config.get('backtest_rolling', True)

        logger.info(f"Enhanced VaR calculator initialized with {len(self.confidence_levels)} confidence levels")

    def _initialize_stress_scenarios(self) -> Dict[StressScenario, Dict[str, Any]]:
        """Initialize predefined stress scenarios."""
        return {
            StressScenario.MARKET_CRASH: {
                'market_shock': -0.30,  # 30% market drop
                'volatility_multiplier': 2.5,
                'correlation_increase': 0.9,
                'description': 'Severe market downturn (30% equity drop)'
            },
            StressScenario.VOLATILITY_SPIKE: {
                'volatility_multiplier': 4.0,
                'market_shock': -0.10,
                'description': 'Extreme volatility spike (4x normal)'
            },
            StressScenario.CORRELATION_BREAKDOWN: {
                'correlation_breakdown': True,
                'correlation_target': 0.2,  # Low correlations
                'description': 'Correlation structure breakdown'
            },
            StressScenario.LIQUIDITY_CRISIS: {
                'liquidity_multiplier': 0.3,  # 70% liquidity reduction
                'market_shock': -0.15,
                'description': 'Severe liquidity crisis'
            },
            StressScenario.INTEREST_RATE_SHOCK: {
                'rate_shock': 0.02,  # 200bp rate increase
                'bond_impact': -0.05,
                'description': '200bp interest rate increase'
            }
        }

    async def calculate_enhanced_var(self, portfolio_data: pd.DataFrame,
                                   method: VaRMethod = VaRMethod.HISTORICAL,
                                   confidence_level: float = 0.95,
                                   time_horizon: int = 1,
                                   distribution: Optional[DistributionType] = None) -> VaRResult:
        """
        Calculate enhanced VaR using specified method and parameters.

        Args:
            portfolio_data: Portfolio returns data
            method: VaR calculation method
            confidence_level: Confidence level (e.g., 0.95 for 95% VaR)
            time_horizon: Time horizon in days
            distribution: Distribution for Monte Carlo/parametric methods

        Returns:
            VaRResult: Enhanced VaR calculation result
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache first
            cache_key = f"{method.value}_{confidence_level}_{time_horizon}_{hash(str(portfolio_data.tail(10)))}"
            if cache_key in self._var_cache:
                cached_result = self._var_cache[cache_key]
                if (asyncio.get_event_loop().time() - cached_result.timestamp.timestamp()) < self.cache_ttl:
                    logger.debug(f"Using cached VaR result for {method.value}")
                    return cached_result

            # Calculate VaR based on method
            if method == VaRMethod.HISTORICAL:
                var_value, metrics = await self._calculate_historical_var_enhanced(
                    portfolio_data, confidence_level, time_horizon
                )
            elif method == VaRMethod.PARAMETRIC_NORMAL:
                var_value, metrics = await self._calculate_parametric_var_normal(
                    portfolio_data, confidence_level, time_horizon
                )
            elif method == VaRMethod.PARAMETRIC_T:
                var_value, metrics = await self._calculate_parametric_var_t(
                    portfolio_data, confidence_level, time_horizon
                )
            elif method == VaRMethod.MONTE_CARLO:
                var_value, metrics = await self._calculate_monte_carlo_var_enhanced(
                    portfolio_data, confidence_level, time_horizon, distribution
                )
            elif method == VaRMethod.EXTREME_VALUE:
                var_value, metrics = await self._calculate_extreme_value_var(
                    portfolio_data, confidence_level, time_horizon
                )
            else:
                raise ValueError(f"Unknown VaR method: {method}")

            # Create result
            calculation_time = asyncio.get_event_loop().time() - start_time
            result = VaRResult(
                var_value=var_value,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                method=method,
                distribution=distribution,
                calculation_time=calculation_time,
                data_points=len(portfolio_data),
                portfolio_value=portfolio_data['value'].iloc[-1] if 'value' in portfolio_data.columns else 0,
                timestamp=datetime.utcnow(),
                additional_metrics=metrics
            )

            # Cache result
            self._var_cache[cache_key] = result

            logger.info(f"Calculated enhanced {method.value} VaR: {var_value:.4f} at {confidence_level:.1%} confidence ({time_horizon}-day)")
            return result

        except Exception as e:
            logger.error(f"Enhanced VaR calculation failed: {e}")
            raise

    async def calculate_cvar(self, portfolio_data: pd.DataFrame,
                           method: VaRMethod = VaRMethod.HISTORICAL,
                           confidence_level: float = 0.95,
                           time_horizon: int = 1) -> CVaRResult:
        """
        Calculate Conditional VaR (Expected Shortfall).

        Args:
            portfolio_data: Portfolio returns data
            method: VaR calculation method
            confidence_level: Confidence level
            time_horizon: Time horizon in days

        Returns:
            CVaRResult: Conditional VaR result
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Calculate VaR first
            var_result = await self.calculate_enhanced_var(
                portfolio_data, method, confidence_level, time_horizon
            )

            # Calculate portfolio returns
            returns = self._prepare_returns_data(portfolio_data)

            # Time scaling adjustment
            if time_horizon > 1:
                var_threshold = var_result.var_value / np.sqrt(time_horizon)
            else:
                var_threshold = var_result.var_value

            # Find tail losses
            tail_losses = returns[returns <= -var_threshold]

            if len(tail_losses) == 0:
                raise ValueError("No tail observations found for CVaR calculation")

            # Calculate CVaR metrics
            cvar_value = abs(tail_losses.mean())
            tail_mean = abs(tail_losses.mean())
            tail_variance = tail_losses.var()
            expected_shortfall = cvar_value  # CVaR = Expected Shortfall

            # Create result
            calculation_time = asyncio.get_event_loop().time() - start_time
            result = CVaRResult(
                cvar_value=cvar_value,
                var_value=var_result.var_value,
                confidence_level=confidence_level,
                expected_shortfall=expected_shortfall,
                tail_mean=tail_mean,
                tail_variance=tail_variance,
                time_horizon=time_horizon,
                method=method,
                calculation_time=calculation_time,
                timestamp=datetime.utcnow()
            )

            logger.info(f"Calculated CVaR: {cvar_value:.4f} at {confidence_level:.1%} confidence")
            return result

        except Exception as e:
            logger.error(f"CVaR calculation failed: {e}")
            raise

    async def run_stress_test(self, portfolio_data: pd.DataFrame,
                            scenario: StressScenario = StressScenario.MARKET_CRASH,
                            custom_params: Optional[Dict[str, Any]] = None) -> StressTestResult:
        """
        Run stress test with specified scenario.

        Args:
            portfolio_data: Portfolio data
            scenario: Stress scenario to apply
            custom_params: Custom parameters for CUSTOM scenario

        Returns:
            StressTestResult: Stress test result
        """
        try:
            # Get scenario parameters
            if scenario == StressScenario.CUSTOM:
                if custom_params is None:
                    raise ValueError("Custom parameters required for CUSTOM scenario")
                scenario_params = custom_params
            else:
                scenario_params = self.stress_scenarios[scenario]

            # Apply stress scenario to portfolio data
            stressed_data = self._apply_stress_scenario(portfolio_data, scenario_params)

            # Calculate VaR on stressed data
            stressed_var_result = await self.calculate_enhanced_var(
                stressed_data, VaRMethod.HISTORICAL, 0.99, 1
            )

            # Calculate portfolio impact
            current_value = portfolio_data['value'].iloc[-1] if 'value' in portfolio_data.columns else 1
            stressed_value = stressed_data['value'].iloc[-1] if 'value' in stressed_data.columns else 1
            percentage_loss = (current_value - stressed_value) / current_value

            # Create result
            result = StressTestResult(
                scenario=scenario,
                description=scenario_params['description'],
                stressed_var=stressed_var_result.var_value,
                stressed_portfolio_value=stressed_value,
                percentage_loss=percentage_loss,
                scenario_params=scenario_params,
                calculation_time=datetime.utcnow()
            )

            logger.info(f"Stress test completed for {scenario.value}: {percentage_loss:.2%} portfolio loss")
            return result

        except Exception as e:
            logger.error(f"Stress test failed for {scenario.value}: {e}")
            raise

    async def run_backtest(self, returns_data: pd.Series,
                         method: VaRMethod = VaRMethod.HISTORICAL,
                         confidence_level: float = 0.95) -> BacktestResult:
        """
        Run VaR backtest with Kupiec and Christoffersen tests.

        Args:
            returns_data: Time series of portfolio returns
            method: VaR method to backtest
            confidence_level: Confidence level for VaR

        Returns:
            BacktestResult: Backtest results
        """
        try:
            if len(returns_data) < self.backtest_window:
                raise ValueError(f"Insufficient data for backtest: need {self.backtest_window}, got {len(returns_data)}")

            # Initialize tracking variables
            exceptions = []
            var_predictions = []
            actual_returns = []

            # Rolling window backtest
            window_size = min(self.lookback_period, len(returns_data) // 2)

            for i in range(window_size, len(returns_data)):
                # Get historical data up to point i
                historical_data = returns_data.iloc[i-window_size:i]

                # Calculate VaR
                if method == VaRMethod.HISTORICAL:
                    var = abs(np.percentile(historical_data, (1 - confidence_level) * 100))
                elif method == VaRMethod.PARAMETRIC_NORMAL:
                    mean = historical_data.mean()
                    std = historical_data.std()
                    z_score = stats.norm.ppf(1 - confidence_level)
                    var = abs(mean + z_score * std)
                else:
                    # For other methods, fall back to historical
                    var = abs(np.percentile(historical_data, (1 - confidence_level) * 100))

                # Check if actual return exceeds VaR
                actual_return = returns_data.iloc[i]
                is_exception = actual_return < -var

                exceptions.append(is_exception)
                var_predictions.append(var)
                actual_returns.append(actual_return)

            # Calculate backtest statistics
            total_observations = len(exceptions)
            num_exceptions = sum(exceptions)
            expected_exceptions = total_observations * (1 - confidence_level)

            # Kupiec test
            kupiec_stat, kupiec_p_value = self._kupiec_test(
                num_exceptions, total_observations, confidence_level
            )

            # Christoffersen test (independence test)
            christoffersen_stat, christoffersen_p_value = self._christoffersen_test(exceptions)

            # Calculate average exception size
            exception_sizes = [abs(actual_returns[i]) for i, is_exc in enumerate(exceptions) if is_exc]
            avg_exception_size = np.mean(exception_sizes) if exception_sizes else 0

            # Determine test results
            passed_kupiec = kupiec_p_value > 0.05  # 5% significance level
            passed_christoffersen = christoffersen_p_value > 0.05

            # Create result
            result = BacktestResult(
                method=method,
                confidence_level=confidence_level,
                test_period=(
                    returns_data.index[window_size],
                    returns_data.index[-1]
                ),
                exceptions=num_exceptions,
                total_observations=total_observations,
                kupiec_statistic=kupiec_stat,
                kupiec_p_value=kupiec_p_value,
                christoffersen_statistic=christoffersen_stat,
                christoffersen_p_value=christoffersen_p_value,
                passed_kupiec=passed_kupiec,
                passed_christoffersen=passed_christoffersen,
                average_exception_size=avg_exception_size
            )

            logger.info(f"Backtest completed for {method.value}: {num_exceptions}/{total_observations} exceptions")
            return result

        except Exception as e:
            logger.error(f"Backtest failed for {method.value}: {e}")
            raise

    # Private implementation methods

    def _prepare_returns_data(self, portfolio_data: pd.DataFrame) -> pd.Series:
        """Prepare returns data from portfolio DataFrame."""
        if 'returns' in portfolio_data.columns:
            returns = portfolio_data['returns']
        elif 'value' in portfolio_data.columns:
            returns = portfolio_data['value'].pct_change().dropna()
        else:
            # Assume first column contains portfolio values
            returns = portfolio_data.iloc[:, 0].pct_change().dropna()
        return returns

    async def _calculate_historical_var_enhanced(self, portfolio_data: pd.DataFrame,
                                              confidence_level: float,
                                              time_horizon: int) -> Tuple[float, Dict[str, float]]:
        """Calculate enhanced historical VaR with time scaling."""
        returns = self._prepare_returns_data(portfolio_data)

        if len(returns) < 30:
            raise ValueError("Insufficient data for historical VaR calculation")

        # Calculate basic VaR
        var_percentile = (1 - confidence_level) * 100
        var_value = abs(np.percentile(returns, var_percentile))

        # Time scaling (square-root rule)
        if time_horizon > 1:
            var_value *= np.sqrt(time_horizon)

        # Additional metrics
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)
        jarque_bera_stat, jarque_bera_p = stats.jarque_bera(returns)

        metrics = {
            'skewness': skewness,
            'kurtosis': kurtosis,
            'jarque_bera_statistic': jarque_bera_stat,
            'jarque_bera_p_value': jarque_bera_p,
            'volatility': returns.std() * np.sqrt(252)
        }

        return var_value, metrics

    async def _calculate_parametric_var_normal(self, portfolio_data: pd.DataFrame,
                                             confidence_level: float,
                                             time_horizon: int) -> Tuple[float, Dict[str, float]]:
        """Calculate parametric VaR assuming normal distribution."""
        returns = self._prepare_returns_data(portfolio_data)

        mean_return = returns.mean()
        std_return = returns.std()

        # Calculate VaR using normal distribution
        z_score = stats.norm.ppf(1 - confidence_level)
        var_value = abs(mean_return + z_score * std_return)

        # Time scaling
        if time_horizon > 1:
            var_value *= np.sqrt(time_horizon)

        # Additional metrics
        metrics = {
            'mean_return': mean_return,
            'volatility': std_return,
            'sharpe_ratio': mean_return / std_return if std_return > 0 else 0,
            'var_to_volatility_ratio': var_value / std_return if std_return > 0 else 0
        }

        return var_value, metrics

    async def _calculate_parametric_var_t(self, portfolio_data: pd.DataFrame,
                                        confidence_level: float,
                                        time_horizon: int) -> Tuple[float, Dict[str, float]]:
        """Calculate parametric VaR assuming Student's t-distribution."""
        returns = self._prepare_returns_data(portfolio_data)

        # Fit Student's t-distribution
        df, loc, scale = stats.t.fit(returns)

        # Calculate VaR using t-distribution
        t_quantile = stats.t.ppf(1 - confidence_level, df)
        var_value = abs(loc + t_quantile * scale)

        # Time scaling
        if time_horizon > 1:
            var_value *= np.sqrt(time_horizon)

        # Additional metrics
        metrics = {
            'degrees_of_freedom': df,
            'location_parameter': loc,
            'scale_parameter': scale,
            'volatility': returns.std(),
            'tail_heaviness': df
        }

        return var_value, metrics

    async def _calculate_monte_carlo_var_enhanced(self, portfolio_data: pd.DataFrame,
                                                confidence_level: float,
                                                time_horizon: int,
                                                distribution: Optional[DistributionType] = None) -> Tuple[float, Dict[str, float]]:
        """Calculate enhanced Monte Carlo VaR."""
        returns = self._prepare_returns_data(portfolio_data)

        if distribution is None:
            distribution = DistributionType.NORMAL

        # Fit distribution to returns
        if distribution == DistributionType.NORMAL:
            mean_return = returns.mean()
            std_return = returns.std()

            # Generate Monte Carlo simulations
            simulated_returns = np.random.normal(mean_return, std_return, self.monte_carlo_simulations)

        elif distribution == DistributionType.STUDENT_T:
            df, loc, scale = stats.t.fit(returns)
            simulated_returns = stats.t.rvs(df, loc, scale, size=self.monte_carlo_simulations)

        elif distribution == DistributionType.SKEWED_T:
            # Simplified skewed t distribution
            df, loc, scale = stats.t.fit(returns)
            skewness = stats.skew(returns)
            # Add skewness parameter (simplified approach)
            simulated_returns = stats.t.rvs(df, loc, scale, size=self.monte_carlo_simulations)
            if skewness < 0:
                simulated_returns = np.abs(simulated_returns) * -1
            else:
                simulated_returns = np.abs(simulated_returns)

        else:  # Default to normal
            mean_return = returns.mean()
            std_return = returns.std()
            simulated_returns = np.random.normal(mean_return, std_return, self.monte_carlo_simulations)

        # Calculate VaR from simulated distribution
        var_percentile = (1 - confidence_level) * 100
        var_value = abs(np.percentile(simulated_returns, var_percentile))

        # Time scaling
        if time_horizon > 1:
            var_value *= np.sqrt(time_horizon)

        # Additional metrics
        metrics = {
            'simulation_count': self.monte_carlo_simulations,
            'simulated_volatility': np.std(simulated_returns),
            'simulated_skewness': stats.skew(simulated_returns),
            'simulated_kurtosis': stats.kurtosis(simulated_returns),
            'distribution_type': distribution.value
        }

        return var_value, metrics

    async def _calculate_extreme_value_var(self, portfolio_data: pd.DataFrame,
                                         confidence_level: float,
                                         time_horizon: int) -> Tuple[float, Dict[str, float]]:
        """Calculate VaR using Extreme Value Theory (Generalized Extreme Value distribution)."""
        returns = self._prepare_returns_data(portfolio_data)

        # Focus on negative returns (losses)
        losses = -returns[returns < 0]  # Convert losses to positive numbers

        if len(losses) < 50:
            # Fallback to historical VaR if insufficient extreme data
            return await self._calculate_historical_var_enhanced(portfolio_data, confidence_level, time_horizon)

        # Use block maxima approach (simplified)
        block_size = max(5, len(losses) // 20)  # Aim for ~20 blocks
        block_maxima = []

        for i in range(0, len(losses), block_size):
            block = losses.iloc[i:i+block_size]
            if len(block) > 0:
                block_maxima.append(block.max())

        if len(block_maxima) < 10:
            # Fallback to historical VaR
            return await self._calculate_historical_var_enhanced(portfolio_data, confidence_level, time_horizon)

        # Fit GEV distribution
        shape, loc, scale = stats.genextreme.fit(block_maxima)

        # Calculate VaR using GEV
        gev_quantile = stats.genextreme.ppf(confidence_level, shape, loc, scale)
        var_value = gev_quantile

        # Time scaling
        if time_horizon > 1:
            var_value *= np.sqrt(time_horizon)

        # Additional metrics
        metrics = {
            'gev_shape_parameter': shape,
            'gev_location_parameter': loc,
            'gev_scale_parameter': scale,
            'block_size': block_size,
            'num_blocks': len(block_maxima),
            'tail_index': -shape if shape < 0 else shape
        }

        return var_value, metrics

    def _apply_stress_scenario(self, portfolio_data: pd.DataFrame,
                             scenario_params: Dict[str, Any]) -> pd.DataFrame:
        """Apply stress scenario to portfolio data."""
        stressed_data = portfolio_data.copy()

        if 'value' in stressed_data.columns:
            values = stressed_data['value']

            # Apply market shock
            if 'market_shock' in scenario_params:
                market_shock = scenario_params['market_shock']
                stressed_data['value'] = values * (1 + market_shock)

            # Apply volatility shock
            if 'volatility_multiplier' in scenario_params:
                vol_multiplier = scenario_params['volatility_multiplier']
                returns = values.pct_change().dropna()
                shocked_returns = returns * vol_multiplier
                shocked_values = values.iloc[0] * (1 + shocked_returns).cumprod()
                stressed_data['value'] = shocked_values.reindex(values.index, method='ffill')

            # Apply correlation breakdown (simplified - affects multi-asset portfolios)
            if scenario_params.get('correlation_breakdown', False):
                # In a real implementation, this would decorrelate the assets
                # For single asset, we just increase idiosyncratic risk
                returns = values.pct_change().dropna()
                shocked_returns = returns * 1.5  # Increase idiosyncratic risk
                shocked_values = values.iloc[0] * (1 + shocked_returns).cumprod()
                stressed_data['value'] = shocked_values.reindex(values.index, method='ffill')

        return stressed_data

    def _kupiec_test(self, num_exceptions: int, total_observations: int,
                    confidence_level: float) -> Tuple[float, float]:
        """Perform Kupiec test for VaR backtesting."""
        expected_exceptions = total_observations * (1 - confidence_level)

        if num_exceptions == 0:
            return 0, 1.0  # No exceptions, perfect model

        # Likelihood ratio test statistic
        if expected_exceptions == 0:
            return float('inf'), 0.0

        lr_stat = 2 * (
            num_exceptions * np.log(num_exceptions / expected_exceptions) +
            (total_observations - num_exceptions) *
            np.log((total_observations - num_exceptions) /
                  (total_observations - expected_exceptions))
        )

        # P-value from chi-square distribution
        p_value = 1 - stats.chi2.cdf(lr_stat, df=1)

        return lr_stat, p_value

    def _christoffersen_test(self, exceptions: List[bool]) -> Tuple[float, float]:
        """Perform Christoffersen independence test for VaR backtesting."""
        if len(exceptions) < 2:
            return 0, 1.0

        # Count transition frequencies
        n00 = sum(1 for i in range(len(exceptions)-1)
                 if not exceptions[i] and not exceptions[i+1])
        n01 = sum(1 for i in range(len(exceptions)-1)
                 if not exceptions[i] and exceptions[i+1])
        n10 = sum(1 for i in range(len(exceptions)-1)
                 if exceptions[i] and not exceptions[i+1])
        n11 = sum(1 for i in range(len(exceptions)-1)
                 if exceptions[i] and exceptions[i+1])

        # Calculate transition probabilities
        n0 = n00 + n01
        n1 = n10 + n11
        n = n0 + n1

        if n0 == 0 or n1 == 0:
            return 0, 1.0

        pi0 = n01 / n0 if n0 > 0 else 0
        pi1 = n11 / n1 if n1 > 0 else 0
        pi = (n01 + n11) / n if n > 0 else 0

        # Likelihood ratio test statistic
        if pi0 == 0 or pi1 == 0 or pi == 0 or pi == 1:
            return 0, 1.0

        lr_stat = 2 * (
            n00 * np.log((1 - pi0) / (1 - pi)) +
            n01 * np.log(pi0 / pi) +
            n10 * np.log((1 - pi1) / (1 - pi)) +
            n11 * np.log(pi1 / pi)
        )

        # P-value from chi-square distribution
        p_value = 1 - stats.chi2.cdf(lr_stat, df=1)

        return lr_stat, p_value

    def clear_cache(self):
        """Clear calculation cache."""
        self._var_cache.clear()
        self._cvar_cache.clear()
        self._stress_cache.clear()
        logger.info("Cleared enhanced VaR calculation cache")

# Factory function for easy instantiation
def create_enhanced_var_calculator(config: Optional[Dict[str, Any]] = None) -> EnhancedVaRCalculator:
    """Create enhanced VaR calculator instance."""
    return EnhancedVaRCalculator(config)