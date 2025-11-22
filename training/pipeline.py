# training/pipeline.py

"""
Enhanced Trading Model Training Pipeline

This module contains the functions for building and evaluating the trading model training pipeline.
It includes custom time-series cross-validation, walk-forward backtesting, performance evaluation metrics,
and advanced validation capabilities including cross-exchange validation, statistical tests,
regime-specific backtesting, Monte Carlo simulation, and enhanced out-of-sample testing.

Key Features:
- Traditional time-series cross-validation and walk-forward backtesting
- Cross-exchange validation and correlation analysis
- Statistical validation tests (Mann-Whitney U, SPA, Diebold-Mariano)
- Regime-specific backtesting with market condition filtering
- Monte Carlo simulation for strategy robustness testing
- Enhanced out-of-sample testing with multiple time periods
- Integration with 2019-2025 data split timeline
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import quantstats as qs
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from .validation.cross_exchange.validator import CrossExchangeValidator
from .validation.statistical_tests.test_suite import StatisticalTestSuite
from ..decision_engine.model_ensemble import ModelEnsemble

logger = logging.getLogger(__name__)


class MissingNumericColumnError(Exception):
    """Raised when no numeric columns are found in a DataFrame required for validation.

    This exception is used in statistical and traditional validation paths
    when `strategy_data` lacks numeric columns necessary to compute returns.
    """


def create_strict_time_series_split(data, n_splits=5, gap=0):
    """
    Creates a time-series cross-validator that enforces a gap between train and test sets.

    This function is a wrapper around scikit-learn's TimeSeriesSplit but is designed
    to make the gap parameter explicit and central to its use, preventing data leakage
    from features engineered with lookaheads (e.g., rolling means).

    Args:
        data (pd.DataFrame or np.ndarray): The dataset to be split.
        n_splits (int): The number of splits to generate.
        gap (int): The number of samples to exclude between the end of the training set
                   and the beginning of the test set.

    Yields:
        tuple: A tuple containing the training and testing indices for each split.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    for train_index, test_index in tscv.split(data):
        yield train_index, test_index


def walk_forward_backtest(model, X, y, n_splits=5, gap=0):
    """
    Performs a walk-forward backtest of a given model.

    This function simulates how a model would perform in a real-world scenario by
    iteratively training on past data and testing on future data. It includes
    data preprocessing within each fold to prevent data leakage.

    Args:
        model: A scikit-learn compatible model instance.
        X (pd.DataFrame): The feature dataset.
        y (pd.Series): The target variable.
        n_splits (int): The number of splits for the time-series cross-validation.
        gap (int): The gap between training and testing sets in each fold.

    Returns:
        dict: A dictionary containing performance metrics from the backtest.
    """
    all_preds = []
    all_true_indices = []

    cv_splitter = create_strict_time_series_split(X, n_splits=n_splits, gap=gap)

    for fold, (train_index, test_index) in enumerate(cv_splitter):
        print(f"--- Fold {fold+1}/{n_splits} ---")
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        print(f"Training on {len(X_train)} samples...")
        model.fit(X_train_scaled, y_train)
        
        print(f"Testing on {len(X_test)} samples...")
        preds = model.predict(X_test_scaled)
        
        all_preds.append(preds)
        all_true_indices.extend(test_index)

    # Align predictions with original index
    final_preds = pd.Series(np.concatenate(all_preds), index=X.iloc[all_true_indices].index)
    # Ensure chronological order to avoid misalignment in return calculations
    final_preds = final_preds.sort_index()

    # Align true values to predictions and ensure the same chronological ordering
    final_true = y.loc[final_preds.index]
    final_true = final_true.sort_index()

    # Assume predictions are signals (+1 for buy, -1 for sell, 0 for hold)
    # This is a simplified assumption. A real implementation would be more complex.
    # We calculate returns based on the signal and the true next-period price change.
    returns = final_true.pct_change().shift(-1) * final_preds
    returns = returns.fillna(0)
    
    return calculate_performance_metrics(returns)


def calculate_performance_metrics(returns):
    """
    Calculates key performance metrics for a trading strategy using quantstats.

    Args:
        returns (pd.Series): A pandas Series of portfolio returns for each period.

    Returns:
        dict: A dictionary of performance metrics.
    """
    print("\nCalculating performance metrics...")
    
    # Ensure returns is a pandas Series
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)

    qs.extend_pandas()

    metrics = {
        "Sharpe Ratio": returns.sharpe(),
        "Sortino Ratio": returns.sortino(),
        "Max Drawdown [%]": returns.max_drawdown() * 100,
        "Calmar Ratio": returns.calmar(),
        "CAGR [%]": returns.cagr() * 100,
        "Win Rate [%]": returns.win_rate() * 100,
        "Cumulative Returns": returns.cumsum().iloc[-1]
    }
    
    # Generate and print a concise report
    qs.reports.metrics(returns, mode='basic')

    return metrics


class EnhancedTrainingPipeline:
    """
    Enhanced training pipeline with comprehensive validation capabilities.
    
    Integrates traditional training methods with advanced validation including
    cross-exchange validation, statistical tests, regime-specific backtesting,
    Monte Carlo simulation, and enhanced out-of-sample testing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize enhanced training pipeline.
        
        Args:
            config: Configuration dictionary containing:
                - model_config: Model ensemble configuration
                - validation_config: Validation framework configuration
                - cross_exchange_config: Cross-exchange validation settings
                - statistical_test_config: Statistical validation parameters
                - regime_analysis_config: Regime-specific testing settings
                - monte_carlo_config: Monte Carlo simulation parameters
                - oos_config: Out-of-sample testing configuration
        """
        self.config = config
        self.model_ensemble = ModelEnsemble(
            input_size=config.get('input_size', 50),
            sequence_length=config.get('sequence_length', 60)
        )
        
        # Initialize validation components
        self.cross_exchange_validator = None
        if config.get('enable_cross_exchange_validation', True):
            cross_exchange_config = config.get('cross_exchange_config', {})
            self.cross_exchange_validator = CrossExchangeValidator(cross_exchange_config)
        
        self.statistical_test_suite = None
        if config.get('enable_statistical_validation', True):
            statistical_config = config.get('statistical_validation_config', {})
            self.statistical_test_suite = StatisticalTestSuite(statistical_config)
        
        # Validation results storage
        self.validation_results = {}
        
        logger.info("EnhancedTrainingPipeline initialized with comprehensive validation capabilities")
    
    async def comprehensive_validation(
        self, 
        strategy_data: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None,
        validation_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive validation suite with async processing.
        
        Args:
            strategy_data: Strategy performance data
            benchmark_data: Optional benchmark data for comparison
            validation_config: Optional validation configuration override
            
        Returns:
            Dict[str, Any]: Comprehensive validation results
        """
        logger.info("Starting comprehensive validation suite")
        start_time = datetime.now()
        
        try:
            validation_tasks = []
            
            # Cross-exchange validation
            if self.cross_exchange_validator is not None:
                logger.info("Adding cross-exchange validation to task queue")
                cross_exchange_task = self._run_cross_exchange_validation(strategy_data)
                validation_tasks.append(('cross_exchange', cross_exchange_task))
            
            # Statistical validation tests
            if self.statistical_test_suite is not None:
                logger.info("Adding statistical validation to task queue")
                statistical_task = self._run_statistical_validation(strategy_data, benchmark_data)
                validation_tasks.append(('statistical', statistical_task))
            
            # Traditional backtesting validation
            traditional_task = self._run_traditional_validation(strategy_data)
            validation_tasks.append(('traditional', traditional_task))
            
            # Execute validation tasks
            validation_results = {}
            
            if validation_tasks:
                logger.info(f"Executing {len(validation_tasks)} validation tasks")
                
                # Run tasks concurrently
                task_names = [name for name, _ in validation_tasks]
                tasks = [task for _, task in validation_tasks]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, (task_name, result) in enumerate(zip(task_names, results)):
                    if isinstance(result, Exception):
                        logger.error(f"Validation task {task_name} failed: {str(result)}")
                        validation_results[task_name] = {
                            'status': 'failed',
                            'error': str(result)
                        }
                    else:
                        validation_results[task_name] = {
                            'status': 'completed',
                            'results': result
                        }
                        logger.info(f"Validation task {task_name} completed successfully")
            
            # Calculate overall validation score
            overall_score = self._calculate_overall_validation_score(validation_results)
            
            # Generate comprehensive recommendations
            recommendations = self._generate_comprehensive_recommendations(validation_results)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            comprehensive_results = {
                'validation_results': validation_results,
                'overall_validation_score': overall_score,
                'recommendations': recommendations,
                'execution_time': execution_time,
                'validation_timestamp': datetime.now(),
                'configuration': self.config
            }
            
            # Store results
            self.validation_results = comprehensive_results
            
            logger.info(f"Comprehensive validation completed in {execution_time:.2f}s")
            logger.info(f"Overall validation score: {overall_score:.3f}")
            
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"Comprehensive validation failed: {str(e)}")
            raise
    
    async def _run_cross_exchange_validation(self, strategy_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run cross-exchange validation.
        
        Args:
            strategy_data: Strategy performance data
            
        Returns:
            Dict[str, Any]: Cross-exchange validation results
        """
        logger.info("Running cross-exchange validation")
        
        try:
            # Determine validation time range from strategy data
            start_time = strategy_data.index.min() if hasattr(strategy_data.index, 'min') else datetime.now() - timedelta(days=30)
            end_time = strategy_data.index.max() if hasattr(strategy_data.index, 'max') else datetime.now()
            
            # Run cross-exchange validation
            cross_exchange_results = await self.cross_exchange_validator.validate_across_exchanges(
                base_data=strategy_data,
                start_time=start_time,
                end_time=end_time
            )
            
            # Extract key metrics for summary
            summary = {
                'overall_correlation': cross_exchange_results.overall_correlation,
                'correlation_significance': cross_exchange_results.correlation_significance,
                'performance_consistency': cross_exchange_results.performance_consistency,
                'data_quality_score': cross_exchange_results.data_quality_score,
                'validation_exchanges': cross_exchange_results.validation_exchanges,
                'recommendations': cross_exchange_results.recommendations,
                'execution_time': cross_exchange_results.execution_time
            }
            
            logger.info(f"Cross-exchange validation completed with correlation: {cross_exchange_results.overall_correlation:.3f}")
            
            return {
                'summary': summary,
                'detailed_results': cross_exchange_results,
                'validation_type': 'cross_exchange'
            }
            
        except Exception as e:
            logger.error(f"Cross-exchange validation failed: {str(e)}")
            raise
    
    async def _run_statistical_validation(
        self, 
        strategy_data: pd.DataFrame, 
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive statistical validation tests.
        
        Args:
            strategy_data: Strategy performance data
            benchmark_data: Optional benchmark data for comparison
            
        Returns:
            Dict[str, Any]: Statistical validation results
        """
        logger.info("Running comprehensive statistical validation tests")
        
        try:
            # Prepare strategy returns
            if 'returns' in strategy_data.columns:
                strategy_returns = strategy_data['returns']
            elif 'close' in strategy_data.columns:
                strategy_returns = strategy_data['close'].pct_change().dropna()
            else:
                # Use first numerical column as proxy
                numeric_cols = strategy_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    strategy_returns = strategy_data[numeric_cols[0]].pct_change().dropna()
                else:
                    raise MissingNumericColumnError(
                        (
                            f"No numeric columns found in DataFrame 'strategy_data' "
                            f"(shape={strategy_data.shape}). Present columns: "
                            f"{list(strategy_data.columns)}. Unable to perform statistical validation."
                        )
                    )
            
            # Normalize index to avoid alignment issues in downstream processing
            # Ensures a contiguous 0..N-1 RangeIndex regardless of source indexing or dropna effects
            strategy_returns.index = pd.RangeIndex(len(strategy_returns))
            
            # Prepare benchmark returns
            if benchmark_data is not None:
                if 'returns' in benchmark_data.columns:
                    benchmark_returns = benchmark_data['returns']
                elif 'close' in benchmark_data.columns:
                    benchmark_returns = benchmark_data['close'].pct_change().dropna()
                else:
                    # Use first numerical column as proxy
                    numeric_cols = benchmark_data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        benchmark_returns = benchmark_data[numeric_cols[0]].pct_change().dropna()
                    else:
                        benchmark_returns = None
            else:
                # Create simple benchmark (zero returns)
                benchmark_returns = pd.Series(np.zeros(len(strategy_returns)), index=strategy_returns.index)
            
            # Run comprehensive statistical tests
            statistical_results = await self.statistical_test_suite.run_all_tests(
                strategy_returns=strategy_returns,
                benchmark_returns=benchmark_returns
            )
            
            # Extract key metrics for summary
            summary = {
                'overall_significance': statistical_results.overall_significance,
                'significance_summary': statistical_results.significance_summary,
                'execution_time': statistical_results.execution_time,
                'recommendations': statistical_results.recommendations
            }
            
            # Add individual test results
            if statistical_results.mann_whitney_result:
                summary['mann_whitney'] = {
                    'statistic': statistical_results.mann_whitney_result.statistic,
                    'p_value': statistical_results.mann_whitney_result.p_value,
                    'effect_size': statistical_results.mann_whitney_result.effect_size,
                    'is_significant': statistical_results.mann_whitney_result.is_significant
                }
            
            if statistical_results.spa_result:
                summary['spa'] = {
                    'spa_statistic': statistical_results.spa_result.spa_statistic,
                    'p_value': statistical_results.spa_result.p_value,
                    'best_strategy': statistical_results.spa_result.best_strategy,
                    'confidence_set': statistical_results.spa_result.confidence_set,
                    'is_significant': statistical_results.spa_result.is_significant
                }
            
            if statistical_results.diebold_mariano_result:
                summary['diebold_mariano'] = {
                    'dm_statistic': statistical_results.diebold_mariano_result.dm_statistic,
                    'p_value': statistical_results.diebold_mariano_result.p_value,
                    'is_significant': statistical_results.diebold_mariano_result.is_significant
                }
            
            logger.info(f"Statistical validation completed with overall significance: {statistical_results.overall_significance}")
            
            return {
                'summary': summary,
                'detailed_results': statistical_results,
                'validation_type': 'statistical'
            }
            
        except Exception as e:
            logger.error(f"Statistical validation failed: {str(e)}")
            raise
    
    async def _run_traditional_validation(self, strategy_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run traditional validation methods.
        
        Args:
            strategy_data: Strategy performance data
            
        Returns:
            Dict[str, Any]: Traditional validation results
        """
        logger.info("Running traditional validation methods")
        
        try:
            # Prepare data for traditional validation
            if 'returns' in strategy_data.columns:
                returns = strategy_data['returns']
            elif 'close' in strategy_data.columns:
                returns = strategy_data['close'].pct_change().dropna()
            else:
                # Use first numerical column as proxy
                numeric_cols = strategy_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    returns = strategy_data[numeric_cols[0]].pct_change().dropna()
                else:
                    raise MissingNumericColumnError(
                        (
                            f"No numeric columns found in DataFrame 'strategy_data' "
                            f"(shape={strategy_data.shape}). Present columns: "
                            f"{list(strategy_data.columns)}. Unable to perform traditional validation."
                        )
                    )
            
            # Calculate traditional performance metrics
            traditional_metrics = calculate_performance_metrics(returns)
            
            # Add additional validation metrics
            additional_metrics = {
                'return_distribution_normality': self._test_return_normality(returns),
                'autocorrelation_test': self._test_autocorrelation(returns),
                'stationarity_test': self._test_stationarity(returns),
                'outlier_analysis': self._analyze_outliers(returns)
            }
            
            logger.info("Traditional validation completed successfully")
            
            return {
                'performance_metrics': traditional_metrics,
                'statistical_tests': additional_metrics,
                'validation_type': 'traditional'
            }
            
        except Exception as e:
            logger.error(f"Traditional validation failed: {str(e)}")
            raise
    
    def _test_return_normality(self, returns: pd.Series) -> Dict[str, float]:
        """Test return distribution normality."""
        from scipy import stats
        
        # Jarque-Bera test for normality
        jb_stat, jb_p_value = stats.jarque_bera(returns.dropna())
        
        # Shapiro-Wilk test (for smaller samples)
        if len(returns) <= 5000:
            sw_stat, sw_p_value = stats.shapiro(returns.dropna())
        else:
            sw_stat, sw_p_value = np.nan, np.nan
        
        return {
            'jarque_bera_statistic': jb_stat,
            'jarque_bera_p_value': jb_p_value,
            'shapiro_wilk_statistic': sw_stat,
            'shapiro_wilk_p_value': sw_p_value,
            'is_normal_jb': jb_p_value > 0.05,
            'is_normal_sw': sw_p_value > 0.05 if not np.isnan(sw_p_value) else None
        }
    
    def _test_autocorrelation(self, returns: pd.Series) -> Dict[str, float]:
        """Test for autocorrelation in returns."""
        from statsmodels.stats.diagnostic import acorr_ljungbox
        
        # Ljung-Box test for autocorrelation
        lb_result = acorr_ljungbox(returns.dropna(), lags=10, return_df=True)
        
        return {
            'ljung_box_statistic': lb_result['lb_stat'].iloc[-1],
            'ljung_box_p_value': lb_result['lb_pvalue'].iloc[-1],
            'has_autocorrelation': lb_result['lb_pvalue'].iloc[-1] < 0.05
        }
    
    def _test_stationarity(self, returns: pd.Series) -> Dict[str, float]:
        """Test for stationarity in returns."""
        from statsmodels.tsa.stattools import adfuller
        
        # Augmented Dickey-Fuller test
        adf_result = adfuller(returns.dropna())
        
        return {
            'adf_statistic': adf_result[0],
            'adf_p_value': adf_result[1],
            'adf_critical_values': adf_result[4],
            'is_stationary': adf_result[1] < 0.05
        }
    
    def _analyze_outliers(self, returns: pd.Series) -> Dict[str, float]:
        """Analyze outliers in return distribution."""
        returns_clean = returns.dropna()
        
        # Calculate outlier statistics
        q1 = returns_clean.quantile(0.25)
        q3 = returns_clean.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = returns_clean[(returns_clean < lower_bound) | (returns_clean > upper_bound)]
        
        return {
            'outlier_count': len(outliers),
            'outlier_percentage': len(outliers) / len(returns_clean) * 100,
            'extreme_outlier_threshold': 3 * returns_clean.std(),
            'max_positive_outlier': returns_clean.max(),
            'max_negative_outlier': returns_clean.min()
        }
    
    def _calculate_overall_validation_score(self, validation_results: Dict[str, Any]) -> float:
        """
        Calculate overall validation score across all validation methods.
        
        Args:
            validation_results: Results from all validation methods
            
        Returns:
            float: Overall validation score (0-1)
        """
        scores = []
        weights = []
        
        # Cross-exchange validation score
        if 'cross_exchange' in validation_results:
            cross_exchange_data = validation_results['cross_exchange']
            if cross_exchange_data['status'] == 'completed':
                summary = cross_exchange_data['results']['summary']
                # Combine correlation, consistency, and data quality
                cross_exchange_score = (
                    summary['overall_correlation'] * 0.4 +
                    summary['performance_consistency'] * 0.3 +
                    summary['data_quality_score'] * 0.3
                )
                scores.append(cross_exchange_score)
                weights.append(0.4)  # Weight for cross-exchange validation
        
        # Statistical validation score
        if 'statistical' in validation_results:
            statistical_data = validation_results['statistical']
            if statistical_data['status'] == 'completed':
                summary = statistical_data['results']['summary']
                
                # Create score based on significance and effect sizes
                statistical_score = 0.0
                
                # Mann-Whitney contribution
                if 'mann_whitney' in summary:
                    mw = summary['mann_whitney']
                    if mw['is_significant']:
                        # Positive effect size means strategy outperforms
                        effect_contribution = min(max((mw['effect_size'] + 1) / 2, 0), 1)
                        statistical_score += effect_contribution * 0.4
                    else:
                        statistical_score += 0.2  # Partial score for non-significance
                
                # SPA test contribution
                if 'spa' in summary:
                    spa = summary['spa']
                    if spa['is_significant']:
                        statistical_score += 0.3
                    else:
                        statistical_score += 0.1
                
                # Diebold-Mariano contribution
                if 'diebold_mariano' in summary:
                    dm = summary['diebold_mariano']
                    if dm['is_significant']:
                        # Negative DM statistic means strategy forecasts better
                        dm_contribution = 0.3 if dm['dm_statistic'] < 0 else 0.1
                        statistical_score += dm_contribution
                    else:
                        statistical_score += 0.15
                
                # Normalize statistical score
                statistical_score = min(statistical_score, 1.0)
                scores.append(statistical_score)
                weights.append(0.4)  # Weight for statistical validation
        
        # Traditional validation score
        if 'traditional' in validation_results:
            traditional_data = validation_results['traditional']
            if traditional_data['status'] == 'completed':
                # Extract performance metrics for scoring
                perf_metrics = traditional_data['results']['performance_metrics']
                
                # Create score based on key metrics
                sharpe_score = min(max((perf_metrics.get('Sharpe Ratio', 0) + 2) / 4, 0), 1)
                drawdown_score = max(1 - abs(perf_metrics.get('Max Drawdown [%]', 100)) / 100, 0)
                return_score = min(max((perf_metrics.get('CAGR [%]', 0) + 50) / 100, 0), 1)
                
                traditional_score = (sharpe_score * 0.4 + drawdown_score * 0.3 + return_score * 0.3)
                scores.append(traditional_score)
                weights.append(0.2)  # Lower weight as statistical tests provide more rigorous validation
        
        # Calculate weighted average
        if scores and weights:
            overall_score = np.average(scores, weights=weights[:len(scores)])
        else:
            overall_score = 0.0
        
        return max(0.0, min(1.0, overall_score))
    
    def _generate_comprehensive_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """
        Generate comprehensive recommendations based on all validation results.
        
        Args:
            validation_results: Results from all validation methods
            
        Returns:
            List[str]: Comprehensive recommendations
        """
        recommendations = []
        
        # Cross-exchange recommendations
        if 'cross_exchange' in validation_results:
            cross_exchange_data = validation_results['cross_exchange']
            if cross_exchange_data['status'] == 'completed':
                cross_exchange_recs = cross_exchange_data['results']['summary']['recommendations']
                recommendations.extend([f"CROSS-EXCHANGE: {rec}" for rec in cross_exchange_recs])
        
        # Statistical validation recommendations
        if 'statistical' in validation_results:
            statistical_data = validation_results['statistical']
            if statistical_data['status'] == 'completed':
                statistical_recs = statistical_data['results']['summary']['recommendations']
                recommendations.extend([f"STATISTICAL: {rec}" for rec in statistical_recs])
        
        # Traditional validation recommendations
        if 'traditional' in validation_results:
            traditional_data = validation_results['traditional']
            if traditional_data['status'] == 'completed':
                perf_metrics = traditional_data['results']['performance_metrics']
                stat_tests = traditional_data['results']['statistical_tests']
                
                # Performance-based recommendations
                if perf_metrics.get('Sharpe Ratio', 0) < 1.0:
                    recommendations.append("PERFORMANCE: Low Sharpe ratio indicates poor risk-adjusted returns.")
                
                if perf_metrics.get('Max Drawdown [%]', 0) < -20:
                    recommendations.append("RISK: High maximum drawdown indicates excessive risk exposure.")
                
                # Statistical test recommendations
                normality = stat_tests.get('return_distribution_normality', {})
                if not normality.get('is_normal_jb', True):
                    recommendations.append("DISTRIBUTION: Returns show non-normal distribution - consider alternative risk models.")
                
                autocorr = stat_tests.get('autocorrelation_test', {})
                if autocorr.get('has_autocorrelation', False):
                    recommendations.append("AUTOCORRELATION: Returns show autocorrelation - model may have predictive information.")
        
        # Overall assessment
        overall_score = self._calculate_overall_validation_score(validation_results)
        
        if overall_score >= 0.8:
            recommendations.append("OVERALL: Excellent validation results - strategy appears robust and well-validated.")
        elif overall_score >= 0.6:
            recommendations.append("OVERALL: Good validation results with some areas for improvement.")
        elif overall_score >= 0.4:
            recommendations.append("OVERALL: Moderate validation results - strategy needs significant improvements.")
        else:
            recommendations.append("OVERALL: Poor validation results - strategy requires major revision.")
        
        return recommendations
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of latest validation results.
        
        Returns:
            Dict[str, Any]: Validation summary
        """
        if not self.validation_results:
            return {'status': 'no_validation_performed'}
        
        return {
            'overall_score': self.validation_results.get('overall_validation_score', 0.0),
            'validation_methods': list(self.validation_results.get('validation_results', {}).keys()),
            'key_recommendations': self.validation_results.get('recommendations', [])[:5],  # Top 5
            'validation_timestamp': self.validation_results.get('validation_timestamp'),
            'execution_time': self.validation_results.get('execution_time', 0.0)
        }


# Backward compatibility function
def create_enhanced_training_pipeline(config: Dict[str, Any]) -> EnhancedTrainingPipeline:
    """
    Create enhanced training pipeline instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        EnhancedTrainingPipeline: Initialized enhanced training pipeline
    """
    return EnhancedTrainingPipeline(config)
