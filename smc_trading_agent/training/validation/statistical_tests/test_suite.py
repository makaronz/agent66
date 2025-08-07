"""
Statistical Test Suite for Trading Strategy Validation

This module provides a unified interface for running comprehensive statistical
validation tests including Mann-Whitney U, Superior Predictive Ability (SPA),
and Diebold-Mariano tests.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

from .mann_whitney import MannWhitneyTest, MannWhitneyResult
from .spa_test import SPATest, SPAResult
from .diebold_mariano import DieboldMarianoTest, DieboldMarianoResult

logger = logging.getLogger(__name__)


@dataclass
class StatisticalValidationResults:
    """Comprehensive statistical validation results."""
    test_suite_name: str
    mann_whitney_result: Optional[MannWhitneyResult]
    spa_result: Optional[SPAResult]
    diebold_mariano_result: Optional[DieboldMarianoResult]
    overall_significance: bool
    significance_summary: Dict[str, bool]
    test_configuration: Dict[str, Any]
    execution_time: float
    recommendations: List[str]
    validation_timestamp: datetime


class StatisticalTestSuite:
    """
    Comprehensive statistical test suite for trading strategy validation.
    
    Provides a unified interface for running multiple statistical tests
    to validate trading strategy performance and forecast accuracy.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize statistical test suite.
        
        Args:
            config: Configuration dictionary containing:
                - significance_level: Statistical significance threshold (default: 0.05)
                - mann_whitney_config: Configuration for Mann-Whitney test
                - spa_config: Configuration for SPA test
                - diebold_mariano_config: Configuration for Diebold-Mariano test
                - parallel_execution: Run tests in parallel (default: True)
        """
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.parallel_execution = config.get('parallel_execution', True)
        
        # Initialize individual test instances
        mann_whitney_config = config.get('mann_whitney_config', {})
        mann_whitney_config['significance_level'] = self.significance_level
        self.mann_whitney_test = MannWhitneyTest(mann_whitney_config)
        
        spa_config = config.get('spa_config', {})
        spa_config['significance_level'] = self.significance_level
        self.spa_test = SPATest(spa_config)
        
        diebold_mariano_config = config.get('diebold_mariano_config', {})
        diebold_mariano_config['significance_level'] = self.significance_level
        self.diebold_mariano_test = DieboldMarianoTest(diebold_mariano_config)
        
        logger.info("StatisticalTestSuite initialized with comprehensive validation capabilities")
    
    async def run_all_tests(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series,
        strategy_forecasts: Optional[pd.Series] = None,
        benchmark_forecasts: Optional[pd.Series] = None,
        actual_values: Optional[pd.Series] = None,
        multiple_strategies: Optional[Dict[str, pd.Series]] = None
    ) -> StatisticalValidationResults:
        """
        Run comprehensive statistical validation test suite.
        
        Args:
            strategy_returns: Primary strategy return series
            benchmark_returns: Benchmark return series
            strategy_forecasts: Strategy forecast series (for DM test)
            benchmark_forecasts: Benchmark forecast series (for DM test)
            actual_values: Actual observed values (for DM test)
            multiple_strategies: Multiple strategy returns for SPA test
            
        Returns:
            StatisticalValidationResults: Comprehensive test results
        """
        logger.info("Running comprehensive statistical validation test suite")
        start_time = datetime.now()
        
        try:
            # Prepare test execution plan
            test_tasks = []
            
            # Mann-Whitney U test (always run)
            mann_whitney_task = self._run_mann_whitney_test(strategy_returns, benchmark_returns)
            test_tasks.append(('mann_whitney', mann_whitney_task))
            
            # SPA test (if multiple strategies provided)
            if multiple_strategies is not None and len(multiple_strategies) > 1:
                spa_task = self._run_spa_test(multiple_strategies, benchmark_returns)
                test_tasks.append(('spa', spa_task))
            
            # Diebold-Mariano test (if forecasts provided)
            if (strategy_forecasts is not None and 
                benchmark_forecasts is not None and 
                actual_values is not None):
                dm_task = self._run_diebold_mariano_test(
                    strategy_forecasts, benchmark_forecasts, actual_values
                )
                test_tasks.append(('diebold_mariano', dm_task))
            
            # Execute tests
            test_results = {}
            
            if self.parallel_execution and len(test_tasks) > 1:
                # Run tests in parallel
                logger.info(f"Executing {len(test_tasks)} tests in parallel")
                test_names = [name for name, _ in test_tasks]
                tasks = [task for _, task in test_tasks]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, (test_name, result) in enumerate(zip(test_names, results)):
                    if isinstance(result, Exception):
                        logger.error(f"Test {test_name} failed: {str(result)}")
                        test_results[test_name] = None
                    else:
                        test_results[test_name] = result
                        logger.info(f"Test {test_name} completed successfully")
            else:
                # Run tests sequentially
                logger.info(f"Executing {len(test_tasks)} tests sequentially")
                for test_name, task in test_tasks:
                    try:
                        result = await task
                        test_results[test_name] = result
                        logger.info(f"Test {test_name} completed successfully")
                    except Exception as e:
                        logger.error(f"Test {test_name} failed: {str(e)}")
                        test_results[test_name] = None
            
            # Process results
            mann_whitney_result = test_results.get('mann_whitney')
            spa_result = test_results.get('spa')
            diebold_mariano_result = test_results.get('diebold_mariano')
            
            # Calculate overall significance and summary
            significance_summary = self._calculate_significance_summary(
                mann_whitney_result, spa_result, diebold_mariano_result
            )
            
            overall_significance = any(significance_summary.values())
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                mann_whitney_result, spa_result, diebold_mariano_result, significance_summary
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create comprehensive results
            results = StatisticalValidationResults(
                test_suite_name="Comprehensive Statistical Validation Suite",
                mann_whitney_result=mann_whitney_result,
                spa_result=spa_result,
                diebold_mariano_result=diebold_mariano_result,
                overall_significance=overall_significance,
                significance_summary=significance_summary,
                test_configuration=self.config,
                execution_time=execution_time,
                recommendations=recommendations,
                validation_timestamp=datetime.now()
            )
            
            logger.info(f"Statistical validation completed in {execution_time:.2f}s")
            logger.info(f"Overall significance: {overall_significance}")
            
            return results
            
        except Exception as e:
            logger.error(f"Statistical validation test suite failed: {str(e)}")
            raise
    
    async def _run_mann_whitney_test(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> Optional[MannWhitneyResult]:
        """Run Mann-Whitney U test."""
        try:
            logger.info("Running Mann-Whitney U test")
            result = await self.mann_whitney_test.test(strategy_returns, benchmark_returns)
            return result
        except Exception as e:
            logger.error(f"Mann-Whitney test failed: {str(e)}")
            return None
    
    async def _run_spa_test(
        self, 
        multiple_strategies: Dict[str, pd.Series],
        benchmark_returns: pd.Series
    ) -> Optional[SPAResult]:
        """Run Superior Predictive Ability test."""
        try:
            logger.info("Running Superior Predictive Ability test")
            
            # Determine benchmark strategy name
            benchmark_name = None
            for name, returns in multiple_strategies.items():
                if returns.equals(benchmark_returns):
                    benchmark_name = name
                    break
            
            if benchmark_name is None:
                # Add benchmark to strategies if not found
                benchmark_name = 'benchmark'
                multiple_strategies = multiple_strategies.copy()
                multiple_strategies[benchmark_name] = benchmark_returns
            
            result = await self.spa_test.test(multiple_strategies, benchmark_name)
            return result
        except Exception as e:
            logger.error(f"SPA test failed: {str(e)}")
            return None
    
    async def _run_diebold_mariano_test(
        self, 
        strategy_forecasts: pd.Series,
        benchmark_forecasts: pd.Series,
        actual_values: pd.Series
    ) -> Optional[DieboldMarianoResult]:
        """Run Diebold-Mariano test."""
        try:
            logger.info("Running Diebold-Mariano test")
            result = await self.diebold_mariano_test.test(
                strategy_forecasts, benchmark_forecasts, actual_values
            )
            return result
        except Exception as e:
            logger.error(f"Diebold-Mariano test failed: {str(e)}")
            return None
    
    def _calculate_significance_summary(
        self,
        mann_whitney_result: Optional[MannWhitneyResult],
        spa_result: Optional[SPAResult],
        diebold_mariano_result: Optional[DieboldMarianoResult]
    ) -> Dict[str, bool]:
        """Calculate significance summary across all tests."""
        significance_summary = {}
        
        if mann_whitney_result is not None:
            significance_summary['mann_whitney'] = mann_whitney_result.is_significant
        
        if spa_result is not None:
            significance_summary['spa'] = spa_result.is_significant
        
        if diebold_mariano_result is not None:
            significance_summary['diebold_mariano'] = diebold_mariano_result.is_significant
        
        return significance_summary
    
    def _generate_recommendations(
        self,
        mann_whitney_result: Optional[MannWhitneyResult],
        spa_result: Optional[SPAResult],
        diebold_mariano_result: Optional[DieboldMarianoResult],
        significance_summary: Dict[str, bool]
    ) -> List[str]:
        """Generate comprehensive recommendations based on all test results."""
        recommendations = []
        
        # Mann-Whitney recommendations
        if mann_whitney_result is not None:
            if mann_whitney_result.is_significant:
                if mann_whitney_result.effect_size > 0:
                    recommendations.append(
                        f"MANN-WHITNEY: Strategy significantly outperforms benchmark "
                        f"(p={mann_whitney_result.p_value:.4f}, effect size={mann_whitney_result.effect_size:.3f})"
                    )
                else:
                    recommendations.append(
                        f"MANN-WHITNEY: Strategy significantly underperforms benchmark "
                        f"(p={mann_whitney_result.p_value:.4f}, effect size={mann_whitney_result.effect_size:.3f})"
                    )
            else:
                recommendations.append(
                    f"MANN-WHITNEY: No significant difference from benchmark "
                    f"(p={mann_whitney_result.p_value:.4f})"
                )
        
        # SPA test recommendations
        if spa_result is not None:
            if spa_result.is_significant:
                recommendations.append(
                    f"SPA TEST: {spa_result.best_strategy} shows superior predictive ability "
                    f"(p={spa_result.p_value:.4f}). Confidence set: {', '.join(spa_result.confidence_set)}"
                )
            else:
                recommendations.append(
                    f"SPA TEST: No strategy shows superior predictive ability "
                    f"(p={spa_result.p_value:.4f}). All strategies statistically equivalent."
                )
        
        # Diebold-Mariano recommendations
        if diebold_mariano_result is not None:
            if diebold_mariano_result.is_significant:
                if diebold_mariano_result.dm_statistic < 0:
                    recommendations.append(
                        f"DIEBOLD-MARIANO: Strategy forecasts are significantly more accurate "
                        f"(p={diebold_mariano_result.p_value:.4f})"
                    )
                else:
                    recommendations.append(
                        f"DIEBOLD-MARIANO: Benchmark forecasts are significantly more accurate "
                        f"(p={diebold_mariano_result.p_value:.4f})"
                    )
            else:
                recommendations.append(
                    f"DIEBOLD-MARIANO: No significant difference in forecast accuracy "
                    f"(p={diebold_mariano_result.p_value:.4f})"
                )
        
        # Overall assessment
        significant_tests = sum(significance_summary.values())
        total_tests = len(significance_summary)
        
        if significant_tests == 0:
            recommendations.append(
                "OVERALL: No statistical evidence of superior performance. "
                "Strategy appears equivalent to benchmark across all tests."
            )
        elif significant_tests == total_tests:
            recommendations.append(
                "OVERALL: Strong statistical evidence of performance difference. "
                "Results are consistent across all validation tests."
            )
        else:
            recommendations.append(
                f"OVERALL: Mixed evidence - {significant_tests}/{total_tests} tests show significance. "
                "Consider additional validation or investigation of discrepancies."
            )
        
        # Practical recommendations
        if any(significance_summary.values()):
            recommendations.append(
                "RECOMMENDATION: Conduct out-of-sample validation to confirm findings. "
                "Consider transaction costs and implementation constraints."
            )
        else:
            recommendations.append(
                "RECOMMENDATION: Strategy may not provide meaningful improvement over benchmark. "
                "Consider parameter optimization or alternative approaches."
            )
        
        return recommendations
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of available tests and their configurations."""
        return {
            'available_tests': ['mann_whitney', 'spa', 'diebold_mariano'],
            'significance_level': self.significance_level,
            'parallel_execution': self.parallel_execution,
            'test_configurations': {
                'mann_whitney': self.mann_whitney_test.config,
                'spa': self.spa_test.config,
                'diebold_mariano': self.diebold_mariano_test.config
            }
        }
    
    async def run_mann_whitney_only(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> MannWhitneyResult:
        """Run only Mann-Whitney U test."""
        return await self.mann_whitney_test.test(strategy_returns, benchmark_returns)
    
    async def run_spa_only(
        self, 
        multiple_strategies: Dict[str, pd.Series], 
        benchmark_name: str
    ) -> SPAResult:
        """Run only Superior Predictive Ability test."""
        return await self.spa_test.test(multiple_strategies, benchmark_name)
    
    async def run_diebold_mariano_only(
        self, 
        strategy_forecasts: pd.Series,
        benchmark_forecasts: pd.Series,
        actual_values: pd.Series
    ) -> DieboldMarianoResult:
        """Run only Diebold-Mariano test."""
        return await self.diebold_mariano_test.test(
            strategy_forecasts, benchmark_forecasts, actual_values
        )
