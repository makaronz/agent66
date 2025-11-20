"""
Advanced Portfolio Risk Management System

This module provides institutional-grade portfolio risk management with:
- Advanced correlation matrix analysis and dynamic correlation tracking
- Concentration risk monitoring and sector exposure management
- Market exposure limits and beta-adjusted position sizing
- Diversification metrics and portfolio optimization
- Real-time risk monitoring and automated rebalancing
- Risk attribution and factor analysis
"""

import numpy as np
import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from scipy import stats
from scipy.optimize import minimize
import networkx as nx
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings

logger = logging.getLogger(__name__)

class ConcentrationMetric(Enum):
    """Concentration measurement metrics."""
    HERFINDAHL_INDEX = "herfindahl_index"
    CR4 = "cr4"  # Concentration ratio of top 4
    CR10 = "cr10"  # Concentration ratio of top 10
    ENTROPY = "entropy"
    GINI = "gini"

class RiskFactorType(Enum):
    """Risk factor types for factor analysis."""
    MARKET = "market"
    SIZE = "size"
    VALUE = "value"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    CREDIT = "credit"
    CURRENCY = "currency"
    COMMODITY = "commodity"
    INTEREST_RATE = "interest_rate"

class RebalanceSignal(Enum):
    """Portfolio rebalancing signals."""
    OVERWEIGHT = "overweight"
    UNDERWEIGHT = "underweight"
    CONCENTRATION_RISK = "concentration_risk"
    CORRELATION_RISK = "correlation_risk"
    SECTOR_LIMIT = "sector_limit"
    RISK_LIMIT = "risk_limit"

@dataclass
class PositionInfo:
    """Detailed position information."""
    symbol: str
    sector: Optional[str]
    market_cap: Optional[float]
    beta: Optional[float]
    volatility: float
    liquidity_score: float
    currency: str
    market_value: float
    weight: float
    returns: pd.Series

@dataclass
class CorrelationAnalysis:
    """Correlation analysis results."""
    correlation_matrix: pd.DataFrame
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    condition_number: float
    effective_rank: float
    maximum_correlation: float
    average_correlation: float
    correlation_clusters: Dict[str, List[str]]
    network_density: float
    systemic_risk_score: float
    timestamp: datetime

@dataclass
class ConcentrationRisk:
    """Concentration risk analysis."""
    metric: ConcentrationMetric
    value: float
    threshold: float
    top_positions: List[Tuple[str, float]]
    sector_concentration: Dict[str, float]
    currency_concentration: Dict[str, float]
    risk_level: str
    timestamp: datetime

@dataclass
class DiversificationMetrics:
    """Portfolio diversification metrics."""
    diversification_ratio: float
    effective_number_bets: float
    max_drawdown_contribution: Dict[str, float]
    risk_contribution: Dict[str, float]
    factor_exposures: Dict[RiskFactorType, float]
    specific_risk: float
    systematic_risk: float
    timestamp: datetime

@dataclass
class RebalanceRecommendation:
    """Portfolio rebalancing recommendation."""
    signal: RebalanceSignal
    symbol: str
    current_weight: float
    target_weight: float
    reason: str
    priority: int  # 1-10, 1 being highest
    expected_impact: float
    timestamp: datetime

class PortfolioRiskManager:
    """
    Advanced portfolio risk management system.

    Provides comprehensive portfolio analysis, risk monitoring, and rebalancing recommendations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Portfolio Risk Manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.max_concentration = self.config.get('max_concentration', 0.15)  # 15% max position
        self.max_sector_exposure = self.config.get('max_sector_exposure', 0.30)  # 30% max sector
        self.max_currency_exposure = self.config.get('max_currency_exposure', 0.40)  # 40% max currency
        self.min_diversification_ratio = self.config.get('min_diversification_ratio', 1.5)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.7)
        self.rebalance_threshold = self.config.get('rebalance_threshold', 0.05)  # 5% deviation

        # Portfolio state
        self.positions: Dict[str, PositionInfo] = {}
        self.portfolio_value: float = 0.0
        self.base_currency: str = self.config.get('base_currency', 'USD')

        # Risk factor models
        self.risk_factors: Dict[RiskFactorType, pd.Series] = {}
        self.factor_loadings: pd.DataFrame = pd.DataFrame()

        # Historical data cache
        self._correlation_history: List[CorrelationAnalysis] = []
        self._concentration_history: List[ConcentrationRisk] = []
        self._rebalance_history: List[RebalanceRecommendation] = []

        # Monitoring thresholds
        self.risk_limits = {
            'max_portfolio_volatility': self.config.get('max_portfolio_volatility', 0.15),
            'max_beta': self.config.get('max_beta', 1.5),
            'min_liquidity_score': self.config.get('min_liquidity_score', 0.3),
            'max_drawdown': self.config.get('max_drawdown', 0.20)
        }

        logger.info("Portfolio Risk Manager initialized with institutional-grade features")

    async def analyze_correlation_matrix(self, returns_data: pd.DataFrame,
                                       method: str = 'pearson',
                                       lookback_period: int = 252) -> CorrelationAnalysis:
        """
        Perform comprehensive correlation analysis.

        Args:
            returns_data: Asset returns DataFrame
            method: Correlation method ('pearson', 'spearman', 'kendall')
            lookback_period: Lookback period in days

        Returns:
            CorrelationAnalysis: Comprehensive correlation analysis
        """
        try:
            # Filter data to lookback period
            if len(returns_data) > lookback_period:
                returns_data = returns_data.tail(lookback_period)

            # Calculate correlation matrix
            if method == 'pearson':
                correlation_matrix = returns_data.corr(method='pearson')
            elif method == 'spearman':
                correlation_matrix = returns_data.corr(method='spearman')
            elif method == 'kendall':
                correlation_matrix = returns_data.corr(method='kendall')
            else:
                raise ValueError(f"Unknown correlation method: {method}")

            # Eigenvalue analysis
            eigenvalues, eigenvectors = np.linalg.eigh(correlation_matrix.values)
            eigenvalues = np.sort(eigenvalues)[::-1]  # Sort descending
            condition_number = eigenvalues[0] / eigenvalues[-1] if eigenvalues[-1] > 0 else float('inf')

            # Calculate effective rank (number of significant eigenvalues)
            total_variance = np.sum(eigenvalues)
            cumulative_variance = np.cumsum(eigenvalues) / total_variance
            effective_rank = np.sum(cumulative_variance < 0.95) + 1

            # Correlation statistics
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
            upper_triangle = correlation_matrix.where(mask)
            max_correlation = upper_triangle.abs().max().max()
            average_correlation = upper_triangle.abs().mean().mean()

            # Clustering analysis
            correlation_clusters = self._identify_correlation_clusters(correlation_matrix)

            # Network analysis
            network_density = self._calculate_network_density(correlation_matrix)
            systemic_risk_score = self._calculate_systemic_risk_score(correlation_matrix, eigenvalues)

            # Create result
            result = CorrelationAnalysis(
                correlation_matrix=correlation_matrix,
                eigenvalues=eigenvalues,
                eigenvectors=eigenvectors,
                condition_number=condition_number,
                effective_rank=effective_rank,
                maximum_correlation=max_correlation,
                average_correlation=average_correlation,
                correlation_clusters=correlation_clusters,
                network_density=network_density,
                systemic_risk_score=systemic_risk_score,
                timestamp=datetime.utcnow()
            )

            # Store in history
            self._correlation_history.append(result)
            if len(self._correlation_history) > 100:  # Keep last 100 analyses
                self._correlation_history.pop(0)

            logger.info(f"Correlation analysis completed: max_corr={max_correlation:.3f}, "
                       f"eff_rank={effective_rank:.1f}, systemic_risk={systemic_risk_score:.3f}")

            return result

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            raise

    async def analyze_concentration_risk(self, positions: Dict[str, float],
                                       sectors: Optional[Dict[str, str]] = None,
                                       currencies: Optional[Dict[str, str]] = None) -> ConcentrationRisk:
        """
        Analyze portfolio concentration risk.

        Args:
            positions: Dictionary of symbol to position weights
            sectors: Dictionary of symbol to sector classification
            currencies: Dictionary of symbol to currency

        Returns:
            ConcentrationRisk: Concentration risk analysis
        """
        try:
            # Calculate position weights
            total_value = sum(positions.values())
            weights = {symbol: value / total_value for symbol, value in positions.items()}

            # Calculate Herfindahl-Hirschman Index (HHI)
            hhi = sum(w ** 2 for w in weights.values())

            # Calculate concentration ratios
            sorted_weights = sorted(weights.values(), reverse=True)
            cr4 = sum(sorted_weights[:4]) if len(sorted_weights) >= 4 else sum(sorted_weights)
            cr10 = sum(sorted_weights[:10]) if len(sorted_weights) >= 10 else sum(sorted_weights)

            # Calculate entropy
            entropy = -sum(w * np.log(w) for w in weights.values() if w > 0)

            # Calculate Gini coefficient
            gini = self._calculate_gini_coefficient(list(weights.values()))

            # Determine concentration level (use HHI as primary metric)
            concentration_value = hhi
            concentration_metric = ConcentrationMetric.HERFINDAHL_INDEX

            # Top positions
            top_positions = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:10]

            # Sector concentration
            sector_concentration = {}
            if sectors:
                sector_weights = {}
                for symbol, weight in weights.items():
                    sector = sectors.get(symbol, 'Unknown')
                    sector_weights[sector] = sector_weights.get(sector, 0) + weight
                sector_concentration = sector_weights

            # Currency concentration
            currency_concentration = {}
            if currencies:
                currency_weights = {}
                for symbol, weight in weights.items():
                    currency = currencies.get(symbol, 'Unknown')
                    currency_weights[currency] = currency_weights.get(currency, 0) + weight
                currency_concentration = currency_weights

            # Determine risk level
            if hhi > 0.25:  # High concentration
                risk_level = 'HIGH'
            elif hhi > 0.15:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'

            # Create result
            result = ConcentrationRisk(
                metric=concentration_metric,
                value=concentration_value,
                threshold=self.max_concentration,
                top_positions=top_positions,
                sector_concentration=sector_concentration,
                currency_concentration=currency_concentration,
                risk_level=risk_level,
                timestamp=datetime.utcnow()
            )

            # Store in history
            self._concentration_history.append(result)
            if len(self._concentration_history) > 100:
                self._concentration_history.pop(0)

            logger.info(f"Concentration analysis: HHI={hhi:.3f}, risk_level={risk_level}")
            return result

        except Exception as e:
            logger.error(f"Concentration risk analysis failed: {e}")
            raise

    async def calculate_diversification_metrics(self, portfolio_returns: pd.Series,
                                               position_returns: pd.DataFrame,
                                               position_weights: Dict[str, float]) -> DiversificationMetrics:
        """
        Calculate portfolio diversification metrics.

        Args:
            portfolio_returns: Portfolio returns time series
            position_returns: Individual position returns
            position_weights: Position weights

        Returns:
            DiversificationMetrics: Diversification analysis
        """
        try:
            # Calculate diversification ratio
            weighted_volatility = np.sqrt(
                sum(w**2 * position_returns[col].var() for col, w in position_weights.items() if col in position_returns.columns)
            )
            portfolio_volatility = portfolio_returns.std()
            diversification_ratio = weighted_volatility / portfolio_volatility if portfolio_volatility > 0 else 1.0

            # Calculate effective number of bets (using correlation matrix)
            correlation_matrix = position_returns.corr().fillna(0)
            inv_correlation = np.linalg.inv(correlation_matrix + np.eye(len(correlation_matrix)) * 1e-8)
            effective_number_bets = sum(
                w1 * w2 * inv_correlation[i, j]
                for i, (sym1, w1) in enumerate(position_weights.items())
                for j, (sym2, w2) in enumerate(position_weights.items())
                if sym1 in correlation_matrix.columns and sym2 in correlation_matrix.columns
            )

            # Calculate risk contributions
            marginal_contributions = {}
            total_risk = portfolio_returns.var()

            for symbol, weight in position_weights.items():
                if symbol in position_returns.columns:
                    # Simplified marginal VaR contribution
                    cov_with_portfolio = position_returns[symbol].cov(portfolio_returns)
                    marginal_contrib = weight * cov_with_portfolio / total_risk if total_risk > 0 else 0
                    marginal_contributions[symbol] = marginal_contrib

            # Normalize risk contributions
            risk_contribution = {
                symbol: contrib / sum(marginal_contributions.values()) if marginal_contributions else 0
                for symbol, contrib in marginal_contributions.items()
            }

            # Factor analysis using PCA
            factor_exposures = {}
            if len(position_returns.columns) > 1:
                try:
                    pca = PCA(n_components=min(5, len(position_returns.columns)))
                    pca.fit(position_returns.fillna(0))

                    # Map components to risk factors (simplified)
                    if pca.explained_variance_ratio_[0] > 0.3:
                        factor_exposures[RiskFactorType.MARKET] = pca.explained_variance_ratio_[0]
                    if pca.explained_variance_ratio_[1] > 0.1:
                        factor_exposures[RiskFactorType.VOLATILITY] = pca.explained_variance_ratio_[1]
                except Exception as e:
                    logger.warning(f"PCA analysis failed: {e}")

            # Calculate systematic vs specific risk
            systematic_risk = diversification_ratio / 2.0  # Simplified calculation
            specific_risk = 1.0 - systematic_risk

            # Calculate maximum drawdown contribution
            max_drawdown_contribution = {}
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()

            # Simplified drawdown contribution based on weights
            max_drawdown_contribution = {
                symbol: weight * max_drawdown for symbol, weight in position_weights.items()
            }

            # Create result
            result = DiversificationMetrics(
                diversification_ratio=diversification_ratio,
                effective_number_bets=effective_number_bets,
                max_drawdown_contribution=max_drawdown_contribution,
                risk_contribution=risk_contribution,
                factor_exposures=factor_exposures,
                specific_risk=specific_risk,
                systematic_risk=systematic_risk,
                timestamp=datetime.utcnow()
            )

            logger.info(f"Diversification analysis: ratio={diversification_ratio:.2f}, "
                       f"eff_bets={effective_number_bets:.1f}")

            return result

        except Exception as e:
            logger.error(f"Diversification analysis failed: {e}")
            raise

    async def generate_rebalance_recommendations(self,
                                                current_positions: Dict[str, float],
                                                target_weights: Optional[Dict[str, float]] = None,
                                                market_data: Optional[Dict[str, pd.DataFrame]] = None) -> List[RebalanceRecommendation]:
        """
        Generate portfolio rebalancing recommendations.

        Args:
            current_positions: Current positions and weights
            target_weights: Target weights (if None, use equal weight)
            market_data: Market data for additional analysis

        Returns:
            List[RebalanceRecommendation]: List of rebalancing recommendations
        """
        try:
            recommendations = []
            total_value = sum(current_positions.values())
            current_weights = {symbol: value / total_value for symbol, value in current_positions.items()}

            # If no target weights provided, use equal weight
            if target_weights is None:
                num_positions = len(current_positions)
                target_weights = {symbol: 1.0 / num_positions for symbol in current_positions.keys()}

            # Check for weight deviations
            for symbol, current_weight in current_weights.items():
                target_weight = target_weights.get(symbol, 0)
                deviation = abs(current_weight - target_weight)

                if deviation > self.rebalance_threshold:
                    # Determine rebalancing direction
                    if current_weight > target_weight:
                        signal = RebalanceSignal.UNDERWEIGHT
                        reason = f"Position overweight by {deviation:.1%}"
                    else:
                        signal = RebalanceSignal.OVERWEIGHT
                        reason = f"Position underweight by {deviation:.1%}"

                    # Calculate priority based on deviation magnitude
                    priority = min(10, int(deviation * 20))  # Scale deviation to priority

                    recommendation = RebalanceRecommendation(
                        signal=signal,
                        symbol=symbol,
                        current_weight=current_weight,
                        target_weight=target_weight,
                        reason=reason,
                        priority=priority,
                        expected_impact=deviation,
                        timestamp=datetime.utcnow()
                    )
                    recommendations.append(recommendation)

            # Check concentration risk
            concentration_analysis = await self.analyze_concentration_risk(current_positions)
            if concentration_analysis.risk_level in ['HIGH', 'MEDIUM']:
                for symbol, weight in concentration_analysis.top_positions[:3]:
                    if weight > self.max_concentration:
                        recommendation = RebalanceRecommendation(
                            signal=RebalanceSignal.CONCENTRATION_RISK,
                            symbol=symbol,
                            current_weight=weight,
                            target_weight=min(weight * 0.8, self.max_concentration),
                            reason=f"Concentration risk: {weight:.1%} exceeds limit of {self.max_concentration:.1%}",
                            priority=1,  # High priority
                            expected_impact=weight - self.max_concentration,
                            timestamp=datetime.utcnow()
                        )
                        recommendations.append(recommendation)

            # If market data provided, perform additional analysis
            if market_data:
                # Check for correlation risk
                returns_data = pd.DataFrame()
                for symbol, data in market_data.items():
                    if symbol in current_positions and 'close' in data.columns:
                        returns_data[symbol] = data['close'].pct_change().dropna()

                if len(returns_data.columns) > 1:
                    correlation_analysis = await self.analyze_correlation_matrix(returns_data.tail(252))
                    if correlation_analysis.maximum_correlation > self.correlation_threshold:
                        # Find highly correlated pairs
                        high_corr_pairs = []
                        corr_matrix = correlation_analysis.correlation_matrix
                        for i in range(len(corr_matrix.columns)):
                            for j in range(i + 1, len(corr_matrix.columns)):
                                if abs(corr_matrix.iloc[i, j]) > self.correlation_threshold:
                                    high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))

                        for symbol1, symbol2 in high_corr_pairs[:2]:  # Limit to top 2 pairs
                            if symbol1 in current_positions and symbol2 in current_positions:
                                # Reduce position in larger weight
                                if current_weights[symbol1] > current_weights[symbol2]:
                                    larger_symbol = symbol1
                                else:
                                    larger_symbol = symbol2

                                recommendation = RebalanceRecommendation(
                                    signal=RebalanceSignal.CORRELATION_RISK,
                                    symbol=larger_symbol,
                                    current_weight=current_weights[larger_symbol],
                                    target_weight=current_weights[larger_symbol] * 0.9,
                                    reason=f"High correlation with {larger_symbol if larger_symbol == symbol1 else symbol1}",
                                    priority=3,
                                    expected_impact=current_weights[larger_symbol] * 0.1,
                                    timestamp=datetime.utcnow()
                                )
                                recommendations.append(recommendation)

            # Sort recommendations by priority
            recommendations.sort(key=lambda x: x.priority)

            # Store in history
            self._rebalance_history.extend(recommendations)
            if len(self._rebalance_history) > 500:  # Keep last 500 recommendations
                self._rebalance_history = self._rebalance_history[-500:]

            logger.info(f"Generated {len(recommendations)} rebalancing recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Rebalancing analysis failed: {e}")
            raise

    def calculate_beta_adjusted_position_size(self, symbol: str, beta: float,
                                            portfolio_beta: float,
                                            target_portfolio_beta: float,
                                            current_weight: float) -> float:
        """
        Calculate beta-adjusted position size.

        Args:
            symbol: Symbol to adjust
            beta: Symbol's beta
            portfolio_beta: Current portfolio beta
            target_portfolio_beta: Target portfolio beta
            current_weight: Current position weight

        Returns:
            float: Adjusted position weight
        """
        if beta == 0:
            return current_weight

        # Calculate beta adjustment factor
        if portfolio_beta > target_portfolio_beta:
            # Need to reduce high-beta positions
            if beta > 1:
                adjustment_factor = target_portfolio_beta / portfolio_beta
            else:
                adjustment_factor = 1.0  # Keep low-beta positions
        else:
            # Can increase positions, favor high-beta
            if beta > 1:
                adjustment_factor = 1.2  # Slightly increase high-beta
            else:
                adjustment_factor = 1.0

        adjusted_weight = current_weight * adjustment_factor
        return min(adjusted_weight, self.max_concentration)

    # Private helper methods

    def _identify_correlation_clusters(self, correlation_matrix: pd.DataFrame) -> Dict[str, List[str]]:
        """Identify correlation clusters using hierarchical clustering."""
        try:
            # Use K-means clustering on correlation distance
            distance_matrix = 1 - np.abs(correlation_matrix.values)
            np.fill_diagonal(distance_matrix, 0)

            if len(correlation_matrix) < 2:
                return {}

            # Determine optimal number of clusters (simplified)
            n_clusters = min(5, len(correlation_matrix) // 2)

            kmeans = KMeans(n_clusters=max(2, n_clusters), random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(distance_matrix)

            # Create cluster dictionary
            clusters = {}
            for i, label in enumerate(cluster_labels):
                symbol = correlation_matrix.columns[i]
                cluster_key = f"cluster_{label}"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(symbol)

            return clusters

        except Exception as e:
            logger.warning(f"Clustering analysis failed: {e}")
            return {}

    def _calculate_network_density(self, correlation_matrix: pd.DataFrame) -> float:
        """Calculate network density from correlation matrix."""
        try:
            # Create adjacency matrix (threshold at 0.5 correlation)
            threshold = 0.5
            adjacency_matrix = (np.abs(correlation_matrix.values) > threshold).astype(int)
            np.fill_diagonal(adjacency_matrix, 0)

            # Calculate network density
            n = len(adjacency_matrix)
            max_edges = n * (n - 1) / 2
            actual_edges = np.sum(adjacency_matrix) / 2  # Divide by 2 as it's symmetric

            density = actual_edges / max_edges if max_edges > 0 else 0
            return density

        except Exception as e:
            logger.warning(f"Network density calculation failed: {e}")
            return 0.0

    def _calculate_systemic_risk_score(self, correlation_matrix: pd.DataFrame,
                                     eigenvalues: np.ndarray) -> float:
        """Calculate systemic risk score based on eigenvalue distribution."""
        try:
            # Use principal eigenvalue as indicator of systemic risk
            principal_eigenvalue = eigenvalues[0]
            total_eigenvalues = np.sum(eigenvalues)

            # Normalize and combine with other factors
            eigenvalue_concentration = principal_eigenvalue / total_eigenvalues
            max_correlation = correlation_matrix.where(
                np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
            ).abs().max().max()

            # Combine factors (weighted average)
            systemic_risk = 0.6 * eigenvalue_concentration + 0.4 * max_correlation
            return min(systemic_risk, 1.0)

        except Exception as e:
            logger.warning(f"Systemic risk calculation failed: {e}")
            return 0.0

    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """Calculate Gini coefficient for concentration measurement."""
        try:
            sorted_values = sorted(values)
            n = len(values)
            cumulative_sum = np.cumsum(sorted_values)
            gini = (n + 1 - 2 * np.sum(cumulative_sum) / cumulative_sum[-1]) / n
            return gini

        except Exception as e:
            logger.warning(f"Gini coefficient calculation failed: {e}")
            return 0.0

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        try:
            summary = {
                'timestamp': datetime.utcnow(),
                'portfolio_stats': {
                    'num_positions': len(self.positions),
                    'portfolio_value': self.portfolio_value,
                    'base_currency': self.base_currency
                },
                'latest_correlation': {},
                'latest_concentration': {},
                'recent_rebalance_signals': len([r for r in self._rebalance_history
                                               if (datetime.utcnow() - r.timestamp).total_seconds() < 86400]),
                'risk_alerts': []
            }

            # Latest correlation analysis
            if self._correlation_history:
                latest_corr = self._correlation_history[-1]
                summary['latest_correlation'] = {
                    'max_correlation': latest_corr.maximum_correlation,
                    'systemic_risk_score': latest_corr.systemic_risk_score,
                    'effective_rank': latest_corr.effective_rank
                }

                if latest_corr.maximum_correlation > self.correlation_threshold:
                    summary['risk_alerts'].append('High correlation risk detected')

            # Latest concentration analysis
            if self._concentration_history:
                latest_conc = self._concentration_history[-1]
                summary['latest_concentration'] = {
                    'hhi': latest_conc.value,
                    'risk_level': latest_conc.risk_level,
                    'top_position': latest_conc.top_positions[0] if latest_conc.top_positions else None
                }

                if latest_conc.risk_level == 'HIGH':
                    summary['risk_alerts'].append('High concentration risk detected')

            return summary

        except Exception as e:
            logger.error(f"Risk summary generation failed: {e}")
            return {'error': str(e), 'timestamp': datetime.utcnow()}

# Factory function for easy instantiation
def create_portfolio_risk_manager(config: Optional[Dict[str, Any]] = None) -> PortfolioRiskManager:
    """Create portfolio risk manager instance."""
    return PortfolioRiskManager(config)