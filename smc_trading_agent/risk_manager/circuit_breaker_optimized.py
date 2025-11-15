"""
Optimized Async Circuit Breaker with Ultra-Low Latency Risk Checks

Implements high-performance risk management with:
- Async VaR calculations with caching
- Connection pooling for database access
- Pre-computed risk metrics
- <5ms risk check latency target
"""

import asyncio
import time
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import json
from functools import lru_cache

from redis.asyncio import Redis, ConnectionPool
import asyncpg
from scipy import stats

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking trades
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class RiskConfig:
    """Configuration for risk management."""
    max_drawdown: float = 0.05
    max_var: float = 0.02
    max_correlation: float = 0.7
    max_position_size: float = 100000.0
    leverage_limit: float = 3.0
    var_confidence: float = 0.95
    var_time_horizon: int = 1
    
    # Performance settings
    cache_ttl_seconds: int = 30
    parallel_calculation: bool = True
    max_workers: int = 4
    precompute_metrics: bool = True
    
    # Database settings
    db_pool_size: int = 20
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql://user:pass@localhost/smc_db"


class VaRCalculator:
    """Ultra-fast VaR calculator with caching and parallel computation."""
    
    def __init__(self, config: RiskConfig, redis_url: str):
        self.config = config
        self._cache = {}
        self._cache_timestamps = {}
        self._executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # Redis for distributed caching
        self.redis_pool = ConnectionPool.from_url(redis_url, max_connections=10)
        self._redis = None
        
        # Pre-computed lookup tables for common calculations
        self._precomputed_quantiles = self._precompute_quantiles()
        
    async def initialize(self):
        """Initialize async resources."""
        self._redis = Redis(connection_pool=self.redis_pool)
        await self._redis.ping()
        logger.info("VaR Calculator initialized with async support")
    
    def _precompute_quantiles(self) -> Dict[float, float]:
        """Pre-compute common quantile values for faster lookup."""
        quantiles = {}
        for confidence in [0.90, 0.95, 0.99, 0.999]:
            quantiles[confidence] = stats.norm.ppf(1 - confidence)
        return quantiles

    @lru_cache(maxsize=1000)
    def _get_quantile(self, confidence: float) -> float:
        """Get pre-computed quantile value."""
        return self._precomputed_quantiles.get(confidence, stats.norm.ppf(1 - confidence))

    async def calculate_var(
        self,
        returns: np.ndarray,
        method: str = "historical",
        confidence: float = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate Value at Risk with ultra-low latency.
        
        Args:
            returns: Portfolio returns array
            method: VaR calculation method
            confidence: Confidence level
            
        Returns:
            Tuple of (VaR value, metadata)
        """
        confidence = confidence or self.config.var_confidence
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_var_cache_key(returns, method, confidence)
        cached_result = await self._get_cached_result(cache_key)
        
        if cached_result:
            return cached_result['var_value'], cached_result['metadata']
        
        # Calculate VaR based on method
        if method == "historical":
            var_value = self._calculate_historical_var(returns, confidence)
        elif method == "parametric":
            var_value = self._calculate_parametric_var(returns, confidence)
        else:
            # Fallback to historical
            var_value = self._calculate_historical_var(returns, confidence)
        
        calculation_time = (time.time() - start_time) * 1000
        
        result = {
            'var_value': var_value,
            'metadata': {
                'method': method,
                'confidence': confidence,
                'sample_size': len(returns),
                'calculation_time_ms': calculation_time,
                'cached': False
            }
        }
        
        # Cache result
        await self._cache_result(cache_key, result)
        
        return var_value, result['metadata']

    def _calculate_historical_var(self, returns: np.ndarray, confidence: float) -> float:
        """Fast historical VaR calculation using numpy."""
        if len(returns) == 0:
            return 0.0
            
        # Use numpy's fast percentile function
        return -np.percentile(returns, (1 - confidence) * 100)

    def _calculate_parametric_var(self, returns: np.ndarray, confidence: float) -> float:
        """Fast parametric VaR calculation using pre-computed quantiles."""
        if len(returns) < 2:
            return 0.0
            
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        
        if std == 0:
            return 0.0
            
        # Use pre-computed quantile
        quantile = self._get_quantile(confidence)
        return -(mean + std * quantile)

    async def calculate_correlation_matrix(self, returns_matrix: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Calculate correlation matrix with optimization."""
        start_time = time.time()
        
        if returns_matrix.shape[0] < 2:
            return np.eye(1), {'max_correlation': 0.0, 'calculation_time_ms': 0}
        
        # Use numpy's efficient correlation calculation
        correlation_matrix = np.corrcoef(returns_matrix)
        
        # Get maximum off-diagonal correlation
        if correlation_matrix.shape[0] > 1:
            mask = ~np.eye(correlation_matrix.shape[0], dtype=bool)
            max_correlation = np.max(np.abs(correlation_matrix[mask]))
        else:
            max_correlation = 0.0
        
        calculation_time = (time.time() - start_time) * 1000
        
        metadata = {
            'max_correlation': float(max_correlation),
            'matrix_shape': correlation_matrix.shape,
            'calculation_time_ms': calculation_time
        }
        
        return correlation_matrix, metadata

    def _generate_var_cache_key(self, returns: np.ndarray, method: str, confidence: float) -> str:
        """Generate cache key for VaR calculation."""
        # Use hash of returns data for cache key
        returns_str = json.dumps(returns.tolist()[:100])  # Limit size for efficiency
        return f"var:{method}:{confidence}:{hash(returns_str)}"

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached calculation result."""
        try:
            if self._redis:
                data = await self._redis.getex(cache_key, ex=self.config.cache_ttl_seconds)
                if data:
                    return json.loads(data)
        except Exception:
            pass
            
        return self._cache.get(cache_key)

    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache calculation result."""
        try:
            if self._redis:
                await self._redis.setex(
                    cache_key,
                    self.config.cache_ttl_seconds,
                    json.dumps(result, default=str)
                )
        except Exception:
            pass
            
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()


class OptimizedCircuitBreaker:
    """
    Optimized circuit breaker with ultra-low latency risk checks.
    
    Key optimizations:
    - Async database operations with connection pooling
    - Pre-computed risk metrics
    - Cached VaR calculations
    - Parallel risk checks
    - Efficient memory management
    """
    
    def __init__(self, config: RiskConfig):
        self.config = config
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.success_count = 0
        
        # Risk calculator
        self.var_calculator = VaRCalculator(config, config.redis_url)
        
        # Database connection pool
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # Performance tracking
        self.risk_check_times = []
        self.total_checks = 0
        self.blocked_trades = 0
        
        # Thread pool for parallel calculations
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # Risk limits cache
        self._risk_limits_cache = {}
        self._risk_limits_cache_time = 0

    async def initialize(self) -> None:
        """Initialize circuit breaker with async resources."""
        try:
            # Initialize VaR calculator
            await self.var_calculator.initialize()
            
            # Create database connection pool
            self.db_pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=5,
                max_size=self.config.db_pool_size,
                command_timeout=5.0  # 5 second timeout
            )
            
            logger.info("Optimized Circuit Breaker initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker: {e}")
            raise

    async def check_risk_limits(
        self,
        portfolio_data: Dict[str, Any],
        trade_details: Dict[str, Any]
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Check risk limits with ultra-low latency.
        
        Args:
            portfolio_data: Current portfolio data
            trade_details: Proposed trade details
            
        Returns:
            Tuple of (is_safe, violations, metadata)
        """
        start_time = time.time()
        self.total_checks += 1
        
        # Quick state check
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > 60:  # 1 minute recovery
                self.state = CircuitState.HALF_OPEN
            else:
                self.blocked_trades += 1
                return False, ["Circuit breaker is OPEN"], self._create_metadata(start_time)
        
        # Parallel risk checks
        if self.config.parallel_calculation:
            violations, metadata = await self._parallel_risk_checks(portfolio_data, trade_details)
        else:
            violations, metadata = await self._sequential_risk_checks(portfolio_data, trade_details)
        
        # Update circuit state
        is_safe = len(violations) == 0
        await self._update_circuit_state(is_safe)
        
        # Update performance metrics
        check_time = (time.time() - start_time) * 1000
        self.risk_check_times.append(check_time)
        
        if len(self.risk_check_times) > 1000:
            self.risk_check_times.pop(0)
        
        metadata['check_time_ms'] = check_time
        metadata['circuit_state'] = self.state.value
        
        return is_safe, violations, metadata

    async def _parallel_risk_checks(
        self,
        portfolio_data: Dict[str, Any],
        trade_details: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Execute risk checks in parallel."""
        loop = asyncio.get_event_loop()
        
        # Create parallel tasks
        tasks = [
            loop.run_in_executor(self.executor, self._check_position_size, portfolio_data, trade_details),
            loop.run_in_executor(self.executor, self._check_leverage, portfolio_data, trade_details),
            self._check_drawdown(portfolio_data),
            self._check_var_limits(portfolio_data),
            self._check_correlation_limits(portfolio_data)
        ]
        
        # Wait for all checks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        violations = []
        metadata = {'parallel_checks': True, 'check_results': {}}
        
        check_names = ['position_size', 'leverage', 'drawdown', 'var', 'correlation']
        
        for i, result in enumerate(results):
            check_name = check_names[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Risk check {check_name} failed: {result}")
                violations.append(f"Risk check {check_name} error: {str(result)}")
                metadata['check_results'][check_name] = 'error'
            else:
                if result:  # violations returned
                    violations.extend(result if isinstance(result, list) else [result])
                    metadata['check_results'][check_name] = 'violations'
                else:
                    metadata['check_results'][check_name] = 'passed'
        
        return violations, metadata

    async def _sequential_risk_checks(
        self,
        portfolio_data: Dict[str, Any],
        trade_details: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Execute risk checks sequentially (fallback)."""
        violations = []
        metadata = {'parallel_checks': False, 'check_results': {}}
        
        # Position size check
        pos_violations = self._check_position_size(portfolio_data, trade_details)
        if pos_violations:
            violations.extend(pos_violations if isinstance(pos_violations, list) else [pos_violations])
            metadata['check_results']['position_size'] = 'violations'
        else:
            metadata['check_results']['position_size'] = 'passed'
        
        # Leverage check
        lev_violations = self._check_leverage(portfolio_data, trade_details)
        if lev_violations:
            violations.extend(lev_violations if isinstance(lev_violations, list) else [lev_violations])
            metadata['check_results']['leverage'] = 'violations'
        else:
            metadata['check_results']['leverage'] = 'passed'
        
        # Drawdown check
        dd_violations = await self._check_drawdown(portfolio_data)
        if dd_violations:
            violations.extend(dd_violations)
            metadata['check_results']['drawdown'] = 'violations'
        else:
            metadata['check_results']['drawdown'] = 'passed'
        
        # VaR check
        var_violations = await self._check_var_limits(portfolio_data)
        if var_violations:
            violations.extend(var_violations)
            metadata['check_results']['var'] = 'violations'
        else:
            metadata['check_results']['var'] = 'passed'
        
        # Correlation check
        corr_violations = await self._check_correlation_limits(portfolio_data)
        if corr_violations:
            violations.extend(corr_violations)
            metadata['check_results']['correlation'] = 'violations'
        else:
            metadata['check_results']['correlation'] = 'passed'
        
        return violations, metadata

    def _check_position_size(self, portfolio_data: Dict[str, Any], trade_details: Dict[str, Any]) -> List[str]:
        """Check position size limits."""
        violations = []
        
        try:
            trade_size = abs(float(trade_details.get('quantity', 0)) * float(trade_details.get('price', 0)))
            
            if trade_size > self.config.max_position_size:
                violations.append(
                    f"Position size exceeded: ${trade_size:,.2f} > ${self.config.max_position_size:,.2f}"
                )
                
        except (ValueError, TypeError) as e:
            violations.append(f"Invalid position data: {e}")
            
        return violations

    def _check_leverage(self, portfolio_data: Dict[str, Any], trade_details: Dict[str, Any]) -> List[str]:
        """Check leverage limits."""
        violations = []
        
        try:
            current_leverage = float(portfolio_data.get('leverage', 0))
            trade_leverage = float(trade_details.get('leverage_impact', 0))
            total_leverage = current_leverage + trade_leverage
            
            if total_leverage > self.config.leverage_limit:
                violations.append(
                    f"Leverage limit exceeded: {total_leverage:.2f}x > {self.config.leverage_limit:.2f}x"
                )
                
        except (ValueError, TypeError) as e:
            violations.append(f"Invalid leverage data: {e}")
            
        return violations

    async def _check_drawdown(self, portfolio_data: Dict[str, Any]) -> List[str]:
        """Check drawdown limits."""
        violations = []
        
        try:
            current_drawdown = float(portfolio_data.get('drawdown', 0))
            
            if current_drawdown > self.config.max_drawdown:
                violations.append(
                    f"Max drawdown exceeded: {current_drawdown:.2%} > {self.config.max_drawdown:.2%}"
                )
                
        except (ValueError, TypeError):
            violations.append("Invalid drawdown data")
            
        return violations

    async def _check_var_limits(self, portfolio_data: Dict[str, Any]) -> List[str]:
        """Check VaR limits with async calculation."""
        violations = []
        
        try:
            returns_data = portfolio_data.get('returns', [])
            if not returns_data:
                return violations
                
            returns = np.array(returns_data)
            
            # Fast VaR calculation
            var_value, _ = await self.var_calculator.calculate_var(
                returns, "historical", self.config.var_confidence
            )
            
            if var_value > self.config.max_var:
                violations.append(
                    f"VaR threshold exceeded: {var_value:.2%} > {self.config.max_var:.2%}"
                )
                
        except Exception as e:
            logger.warning(f"VaR calculation error: {e}")
            violations.append(f"VaR calculation error: {e}")
            
        return violations

    async def _check_correlation_limits(self, portfolio_data: Dict[str, Any]) -> List[str]:
        """Check correlation limits."""
        violations = []
        
        try:
            returns_matrix = portfolio_data.get('returns_matrix')
            if returns_matrix is None:
                return violations
                
            if not isinstance(returns_matrix, np.ndarray):
                returns_matrix = np.array(returns_matrix)
            
            # Fast correlation calculation
            _, metadata = await self.var_calculator.calculate_correlation_matrix(returns_matrix)
            
            if metadata['max_correlation'] > self.config.max_correlation:
                violations.append(
                    f"Correlation threshold exceeded: {metadata['max_correlation']:.3f} > {self.config.max_correlation:.3f}"
                )
                
        except Exception as e:
            logger.warning(f"Correlation calculation error: {e}")
            violations.append(f"Correlation calculation error: {e}")
            
        return violations

    async def _update_circuit_state(self, is_safe: bool) -> None:
        """Update circuit breaker state based on check results."""
        if is_safe:
            self.success_count += 1
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= 5:  # Threshold for opening circuit
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened due to {self.failure_count} failures")

    def _create_metadata(self, start_time: float) -> Dict[str, Any]:
        """Create metadata for risk check result."""
        return {
            'check_time_ms': (time.time() - start_time) * 1000,
            'circuit_state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_checks': self.total_checks,
            'blocked_trades': self.blocked_trades
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker performance metrics."""
        if self.risk_check_times:
            avg_check_time = np.mean(self.risk_check_times)
            p95_check_time = np.percentile(self.risk_check_times, 95)
            p99_check_time = np.percentile(self.risk_check_times, 99)
        else:
            avg_check_time = p95_check_time = p99_check_time = 0
        
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_checks': self.total_checks,
            'blocked_trades': self.blocked_trades,
            'performance': {
                'avg_check_time_ms': avg_check_time,
                'p95_check_time_ms': p95_check_time,
                'p99_check_time_ms': p99_check_time
            },
            'metrics': {
                'total_violations': self.failure_count,
                'violation_rate': self.failure_count / max(1, self.total_checks)
            }
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.db_pool:
                await self.db_pool.close()
                
            self.executor.shutdown(wait=True)
            
            if hasattr(self.var_calculator, '_redis') and self.var_calculator._redis:
                await self.var_calculator._redis.close()
                
            logger.info("Optimized Circuit Breaker cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Factory function for easy instantiation
async def create_optimized_circuit_breaker(
    max_drawdown: float = 0.05,
    max_var: float = 0.02,
    redis_url: str = "redis://localhost:6379",
    database_url: str = "postgresql://user:pass@localhost/smc_db",
    **kwargs
) -> OptimizedCircuitBreaker:
    """
    Create and initialize optimized circuit breaker.
    
    Args:
        max_drawdown: Maximum allowed drawdown
        max_var: Maximum allowed VaR
        redis_url: Redis connection URL
        database_url: Database connection URL
        **kwargs: Additional configuration options
        
    Returns:
        OptimizedCircuitBreaker: Initialized circuit breaker
    """
    config = RiskConfig(
        max_drawdown=max_drawdown,
        max_var=max_var,
        redis_url=redis_url,
        database_url=database_url,
        **kwargs
    )
    
    circuit_breaker = OptimizedCircuitBreaker(config)
    await circuit_breaker.initialize()
    
    return circuit_breaker