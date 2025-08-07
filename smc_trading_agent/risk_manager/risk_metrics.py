"""
Risk Metrics Monitoring System for SMC Trading Agent.

This module provides comprehensive risk metrics monitoring for 6 risk categories:
- Market Risk: Price volatility, drawdown, VaR
- Credit Risk: Counterparty exposure, default probability
- Liquidity Risk: Bid-ask spreads, market depth, trading volume
- Operational Risk: System failures, execution errors, data quality
- Concentration Risk: Position concentration, sector exposure
- Correlation Risk: Portfolio correlation, diversification metrics

Provides real-time monitoring, threshold checking, and alerting capabilities.
"""

import numpy as np
import pandas as pd
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from .var_calculator import VaRCalculator, VaRMethod

logger = logging.getLogger(__name__)


class RiskCategory(Enum):
    """Risk categories for monitoring."""
    MARKET = "market"
    CREDIT = "credit"
    LIQUIDITY = "liquidity"
    OPERATIONAL = "operational"
    CONCENTRATION = "concentration"
    CORRELATION = "correlation"


class RiskSeverity(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetric:
    """Individual risk metric data."""
    name: str
    value: float
    threshold: float
    category: RiskCategory
    severity: RiskSeverity
    timestamp: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAlert:
    """Risk alert data."""
    category: RiskCategory
    severity: RiskSeverity
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: float
    alert_id: str = ""


@dataclass
class RiskSummary:
    """Comprehensive risk summary."""
    timestamp: float
    overall_risk_score: float
    category_scores: Dict[RiskCategory, float]
    active_alerts: List[RiskAlert]
    metrics: Dict[str, RiskMetric]
    portfolio_value: float
    total_positions: int


class RiskMetricsMonitor:
    """
    Comprehensive risk metrics monitoring system.
    
    Monitors 6 risk categories with real-time calculation,
    threshold checking, and alerting capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk metrics monitor.
        
        Args:
            config: Configuration dictionary with risk parameters
        """
        self.config = config
        self.var_calculator = VaRCalculator(config.get('var_calculator', {}))
        
        # Risk thresholds from configuration
        self.thresholds = config.get('thresholds', {
            RiskCategory.MARKET: {
                'max_drawdown': 0.10,
                'max_var': 0.05,
                'max_volatility': 0.30
            },
            RiskCategory.CREDIT: {
                'max_exposure': 0.20,
                'max_default_probability': 0.01
            },
            RiskCategory.LIQUIDITY: {
                'min_bid_ask_spread': 0.001,
                'min_market_depth': 1000000,
                'min_trading_volume': 500000
            },
            RiskCategory.OPERATIONAL: {
                'max_error_rate': 0.01,
                'max_latency': 1000,
                'min_data_quality': 0.95
            },
            RiskCategory.CONCENTRATION: {
                'max_position_size': 0.20,
                'max_sector_exposure': 0.30
            },
            RiskCategory.CORRELATION: {
                'max_correlation': 0.70,
                'min_diversification': 0.50
            }
        })
        
        # Monitoring state
        self.metrics_history: Dict[str, List[RiskMetric]] = {}
        self.active_alerts: List[RiskAlert] = []
        self.last_calculation_time = 0
        self.calculation_interval = config.get('calculation_interval', 60)  # seconds
        
        # Alert management
        self.alert_cooldown = config.get('alert_cooldown', 300)  # 5 minutes
        self.last_alert_time: Dict[str, float] = {}
        
        logger.info("Initialized risk metrics monitor with 6 risk categories")
    
    async def calculate_market_risk(self, portfolio_data: pd.DataFrame) -> Dict[str, RiskMetric]:
        """Calculate market risk metrics."""
        try:
            metrics = {}
            
            # Calculate drawdown
            if 'value' in portfolio_data.columns:
                values = portfolio_data['value']
                peak = values.expanding().max()
                drawdown = (values - peak) / peak
                current_drawdown = abs(drawdown.iloc[-1])
                
                metrics['drawdown'] = RiskMetric(
                    name='drawdown',
                    value=current_drawdown,
                    threshold=self.thresholds[RiskCategory.MARKET]['max_drawdown'],
                    category=RiskCategory.MARKET,
                    severity=self._calculate_severity(current_drawdown, self.thresholds[RiskCategory.MARKET]['max_drawdown']),
                    timestamp=time.time(),
                    description=f"Current portfolio drawdown: {current_drawdown:.2%}"
                )
            
            # Calculate VaR
            var_result = await self.var_calculator.calculate_var(
                portfolio_data, VaRMethod.HISTORICAL, 0.95
            )
            
            metrics['var'] = RiskMetric(
                name='var',
                value=var_result.var_value,
                threshold=self.thresholds[RiskCategory.MARKET]['max_var'],
                category=RiskCategory.MARKET,
                severity=self._calculate_severity(var_result.var_value, self.thresholds[RiskCategory.MARKET]['max_var']),
                timestamp=time.time(),
                description=f"95% VaR: {var_result.var_value:.2%}",
                metadata={'method': var_result.method.value, 'confidence_level': var_result.confidence_level}
            )
            
            # Calculate volatility
            if 'returns' in portfolio_data.columns:
                returns = portfolio_data['returns']
            else:
                values = portfolio_data['value'] if 'value' in portfolio_data.columns else portfolio_data.iloc[:, 0]
                returns = values.pct_change().dropna()
            
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            metrics['volatility'] = RiskMetric(
                name='volatility',
                value=volatility,
                threshold=self.thresholds[RiskCategory.MARKET]['max_volatility'],
                category=RiskCategory.MARKET,
                severity=self._calculate_severity(volatility, self.thresholds[RiskCategory.MARKET]['max_volatility']),
                timestamp=time.time(),
                description=f"Annualized volatility: {volatility:.2%}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Market risk calculation failed: {e}")
            return {}
    
    async def calculate_credit_risk(self, portfolio_data: pd.DataFrame, 
                                  counterparty_data: Optional[Dict] = None) -> Dict[str, RiskMetric]:
        """Calculate credit risk metrics."""
        try:
            metrics = {}
            
            # Calculate counterparty exposure (simplified)
            if counterparty_data:
                total_exposure = sum(counterparty_data.values())
                max_exposure = max(counterparty_data.values()) if counterparty_data else 0
                exposure_ratio = max_exposure / total_exposure if total_exposure > 0 else 0
                
                metrics['exposure'] = RiskMetric(
                    name='exposure',
                    value=exposure_ratio,
                    threshold=self.thresholds[RiskCategory.CREDIT]['max_exposure'],
                    category=RiskCategory.CREDIT,
                    severity=self._calculate_severity(exposure_ratio, self.thresholds[RiskCategory.CREDIT]['max_exposure']),
                    timestamp=time.time(),
                    description=f"Max counterparty exposure: {exposure_ratio:.2%}"
                )
            
            # Default probability (placeholder - would use external credit data)
            default_prob = 0.005  # 0.5% default probability
            
            metrics['default_probability'] = RiskMetric(
                name='default_probability',
                value=default_prob,
                threshold=self.thresholds[RiskCategory.CREDIT]['max_default_probability'],
                category=RiskCategory.CREDIT,
                severity=self._calculate_severity(default_prob, self.thresholds[RiskCategory.CREDIT]['max_default_probability']),
                timestamp=time.time(),
                description=f"Estimated default probability: {default_prob:.2%}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Credit risk calculation failed: {e}")
            return {}
    
    async def calculate_liquidity_risk(self, market_data: pd.DataFrame) -> Dict[str, RiskMetric]:
        """Calculate liquidity risk metrics."""
        try:
            metrics = {}
            
            # Calculate bid-ask spread (simplified)
            if 'bid' in market_data.columns and 'ask' in market_data.columns:
                spread = (market_data['ask'] - market_data['bid']) / market_data['bid']
                avg_spread = spread.mean()
                
                metrics['bid_ask_spread'] = RiskMetric(
                    name='bid_ask_spread',
                    value=avg_spread,
                    threshold=self.thresholds[RiskCategory.LIQUIDITY]['min_bid_ask_spread'],
                    category=RiskCategory.LIQUIDITY,
                    severity=self._calculate_severity(avg_spread, self.thresholds[RiskCategory.LIQUIDITY]['min_bid_ask_spread'], reverse=True),
                    timestamp=time.time(),
                    description=f"Average bid-ask spread: {avg_spread:.4f}"
                )
            
            # Market depth (placeholder)
            market_depth = 2000000  # $2M market depth
            
            metrics['market_depth'] = RiskMetric(
                name='market_depth',
                value=market_depth,
                threshold=self.thresholds[RiskCategory.LIQUIDITY]['min_market_depth'],
                category=RiskCategory.LIQUIDITY,
                severity=self._calculate_severity(market_depth, self.thresholds[RiskCategory.LIQUIDITY]['min_market_depth'], reverse=True),
                timestamp=time.time(),
                description=f"Market depth: ${market_depth:,.0f}"
            )
            
            # Trading volume (placeholder)
            trading_volume = 1000000  # $1M daily volume
            
            metrics['trading_volume'] = RiskMetric(
                name='trading_volume',
                value=trading_volume,
                threshold=self.thresholds[RiskCategory.LIQUIDITY]['min_trading_volume'],
                category=RiskCategory.LIQUIDITY,
                severity=self._calculate_severity(trading_volume, self.thresholds[RiskCategory.LIQUIDITY]['min_trading_volume'], reverse=True),
                timestamp=time.time(),
                description=f"Daily trading volume: ${trading_volume:,.0f}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Liquidity risk calculation failed: {e}")
            return {}
    
    async def calculate_operational_risk(self, system_metrics: Dict[str, Any]) -> Dict[str, RiskMetric]:
        """Calculate operational risk metrics."""
        try:
            metrics = {}
            
            # Error rate
            error_rate = system_metrics.get('error_rate', 0.005)
            
            metrics['error_rate'] = RiskMetric(
                name='error_rate',
                value=error_rate,
                threshold=self.thresholds[RiskCategory.OPERATIONAL]['max_error_rate'],
                category=RiskCategory.OPERATIONAL,
                severity=self._calculate_severity(error_rate, self.thresholds[RiskCategory.OPERATIONAL]['max_error_rate']),
                timestamp=time.time(),
                description=f"System error rate: {error_rate:.2%}"
            )
            
            # Latency
            latency = system_metrics.get('latency_ms', 500)
            
            metrics['latency'] = RiskMetric(
                name='latency',
                value=latency,
                threshold=self.thresholds[RiskCategory.OPERATIONAL]['max_latency'],
                category=RiskCategory.OPERATIONAL,
                severity=self._calculate_severity(latency, self.thresholds[RiskCategory.OPERATIONAL]['max_latency']),
                timestamp=time.time(),
                description=f"System latency: {latency}ms"
            )
            
            # Data quality
            data_quality = system_metrics.get('data_quality', 0.98)
            
            metrics['data_quality'] = RiskMetric(
                name='data_quality',
                value=data_quality,
                threshold=self.thresholds[RiskCategory.OPERATIONAL]['min_data_quality'],
                category=RiskCategory.OPERATIONAL,
                severity=self._calculate_severity(data_quality, self.thresholds[RiskCategory.OPERATIONAL]['min_data_quality'], reverse=True),
                timestamp=time.time(),
                description=f"Data quality score: {data_quality:.2%}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Operational risk calculation failed: {e}")
            return {}
    
    async def calculate_concentration_risk(self, portfolio_data: pd.DataFrame) -> Dict[str, RiskMetric]:
        """Calculate concentration risk metrics."""
        try:
            metrics = {}
            
            # Position concentration
            if len(portfolio_data.columns) > 1:
                position_values = []
                for col in portfolio_data.columns:
                    if col not in ['timestamp', 'date', 'time', 'value', 'returns']:
                        position_values.append(portfolio_data[col].iloc[-1])
                
                if position_values:
                    total_value = sum(abs(v) for v in position_values)
                    max_position = max(abs(v) for v in position_values)
                    concentration = max_position / total_value if total_value > 0 else 0
                    
                    metrics['position_concentration'] = RiskMetric(
                        name='position_concentration',
                        value=concentration,
                        threshold=self.thresholds[RiskCategory.CONCENTRATION]['max_position_size'],
                        category=RiskCategory.CONCENTRATION,
                        severity=self._calculate_severity(concentration, self.thresholds[RiskCategory.CONCENTRATION]['max_position_size']),
                        timestamp=time.time(),
                        description=f"Max position concentration: {concentration:.2%}"
                    )
            
            # Sector exposure (placeholder)
            sector_exposure = 0.25  # 25% sector exposure
            
            metrics['sector_exposure'] = RiskMetric(
                name='sector_exposure',
                value=sector_exposure,
                threshold=self.thresholds[RiskCategory.CONCENTRATION]['max_sector_exposure'],
                category=RiskCategory.CONCENTRATION,
                severity=self._calculate_severity(sector_exposure, self.thresholds[RiskCategory.CONCENTRATION]['max_sector_exposure']),
                timestamp=time.time(),
                description=f"Sector exposure: {sector_exposure:.2%}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Concentration risk calculation failed: {e}")
            return {}
    
    async def calculate_correlation_risk(self, portfolio_data: pd.DataFrame) -> Dict[str, RiskMetric]:
        """Calculate correlation risk metrics."""
        try:
            metrics = {}
            
            # Calculate correlation matrix
            correlation_result = await self.var_calculator.calculate_correlation_matrix(portfolio_data)
            
            # Max correlation
            metrics['max_correlation'] = RiskMetric(
                name='max_correlation',
                value=abs(correlation_result.max_correlation),
                threshold=self.thresholds[RiskCategory.CORRELATION]['max_correlation'],
                category=RiskCategory.CORRELATION,
                severity=self._calculate_severity(abs(correlation_result.max_correlation), self.thresholds[RiskCategory.CORRELATION]['max_correlation']),
                timestamp=time.time(),
                description=f"Maximum correlation: {correlation_result.max_correlation:.4f}"
            )
            
            # Diversification score (1 - average correlation)
            diversification = 1 - abs(correlation_result.avg_correlation)
            
            metrics['diversification'] = RiskMetric(
                name='diversification',
                value=diversification,
                threshold=self.thresholds[RiskCategory.CORRELATION]['min_diversification'],
                category=RiskCategory.CORRELATION,
                severity=self._calculate_severity(diversification, self.thresholds[RiskCategory.CORRELATION]['min_diversification'], reverse=True),
                timestamp=time.time(),
                description=f"Portfolio diversification: {diversification:.2%}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Correlation risk calculation failed: {e}")
            return {}
    
    async def calculate_all_risk_metrics(self, portfolio_data: pd.DataFrame,
                                       market_data: Optional[pd.DataFrame] = None,
                                       system_metrics: Optional[Dict[str, Any]] = None,
                                       counterparty_data: Optional[Dict] = None) -> Dict[str, RiskMetric]:
        """Calculate all risk metrics across all categories."""
        try:
            all_metrics = {}
            
            # Calculate metrics for each category
            market_metrics = await self.calculate_market_risk(portfolio_data)
            credit_metrics = await self.calculate_credit_risk(portfolio_data, counterparty_data)
            liquidity_metrics = await self.calculate_liquidity_risk(market_data or pd.DataFrame())
            operational_metrics = await self.calculate_operational_risk(system_metrics or {})
            concentration_metrics = await self.calculate_concentration_risk(portfolio_data)
            correlation_metrics = await self.calculate_correlation_risk(portfolio_data)
            
            # Combine all metrics
            all_metrics.update(market_metrics)
            all_metrics.update(credit_metrics)
            all_metrics.update(liquidity_metrics)
            all_metrics.update(operational_metrics)
            all_metrics.update(concentration_metrics)
            all_metrics.update(correlation_metrics)
            
            # Store in history
            for metric_name, metric in all_metrics.items():
                if metric_name not in self.metrics_history:
                    self.metrics_history[metric_name] = []
                self.metrics_history[metric_name].append(metric)
                
                # Keep only last 1000 entries
                if len(self.metrics_history[metric_name]) > 1000:
                    self.metrics_history[metric_name] = self.metrics_history[metric_name][-1000:]
            
            self.last_calculation_time = time.time()
            
            logger.info(f"Calculated {len(all_metrics)} risk metrics across 6 categories")
            return all_metrics
            
        except Exception as e:
            logger.error(f"Risk metrics calculation failed: {e}")
            return {}
    
    async def check_thresholds_and_generate_alerts(self, metrics: Dict[str, RiskMetric]) -> List[RiskAlert]:
        """Check all metrics against thresholds and generate alerts."""
        try:
            new_alerts = []
            
            for metric_name, metric in metrics.items():
                # Check if metric exceeds threshold
                if metric.value > metric.threshold:
                    # Check alert cooldown
                    alert_key = f"{metric.category.value}_{metric_name}"
                    current_time = time.time()
                    
                    if alert_key not in self.last_alert_time or \
                       (current_time - self.last_alert_time[alert_key]) > self.alert_cooldown:
                        
                        # Generate alert
                        alert = RiskAlert(
                            category=metric.category,
                            severity=metric.severity,
                            message=f"{metric.category.value.title()} risk threshold exceeded: {metric.description}",
                            metric_name=metric_name,
                            current_value=metric.value,
                            threshold=metric.threshold,
                            timestamp=current_time,
                            alert_id=f"{alert_key}_{int(current_time)}"
                        )
                        
                        new_alerts.append(alert)
                        self.last_alert_time[alert_key] = current_time
                        
                        logger.warning(f"Risk alert generated: {alert.message}")
            
            # Add new alerts to active alerts
            self.active_alerts.extend(new_alerts)
            
            # Remove old alerts (older than 24 hours)
            cutoff_time = time.time() - 86400  # 24 hours
            self.active_alerts = [alert for alert in self.active_alerts if alert.timestamp > cutoff_time]
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Threshold checking failed: {e}")
            return []
    
    async def get_risk_summary(self, portfolio_data: pd.DataFrame,
                             market_data: Optional[pd.DataFrame] = None,
                             system_metrics: Optional[Dict[str, Any]] = None,
                             counterparty_data: Optional[Dict] = None) -> RiskSummary:
        """Get comprehensive risk summary."""
        try:
            # Calculate all metrics
            metrics = await self.calculate_all_risk_metrics(
                portfolio_data, market_data, system_metrics, counterparty_data
            )
            
            # Generate alerts
            new_alerts = await self.check_thresholds_and_generate_alerts(metrics)
            
            # Calculate category scores
            category_scores = {}
            for category in RiskCategory:
                category_metrics = [m for m in metrics.values() if m.category == category]
                if category_metrics:
                    # Calculate weighted average severity
                    severity_weights = {
                        RiskSeverity.LOW: 1,
                        RiskSeverity.MEDIUM: 2,
                        RiskSeverity.HIGH: 3,
                        RiskSeverity.CRITICAL: 4
                    }
                    total_weight = sum(severity_weights[m.severity] for m in category_metrics)
                    avg_score = total_weight / len(category_metrics)
                    category_scores[category] = min(avg_score / 4, 1.0)  # Normalize to 0-1
                else:
                    category_scores[category] = 0.0
            
            # Calculate overall risk score
            overall_risk_score = sum(category_scores.values()) / len(category_scores)
            
            # Get portfolio info
            portfolio_value = portfolio_data['value'].iloc[-1] if 'value' in portfolio_data.columns else 0
            total_positions = len([col for col in portfolio_data.columns if col not in ['timestamp', 'date', 'time', 'value', 'returns']])
            
            # Create risk summary
            summary = RiskSummary(
                timestamp=time.time(),
                overall_risk_score=overall_risk_score,
                category_scores=category_scores,
                active_alerts=self.active_alerts,
                metrics=metrics,
                portfolio_value=portfolio_value,
                total_positions=total_positions
            )
            
            logger.info(f"Generated risk summary: overall score={overall_risk_score:.2f}, "
                       f"alerts={len(self.active_alerts)}, positions={total_positions}")
            return summary
            
        except Exception as e:
            logger.error(f"Risk summary generation failed: {e}")
            raise
    
    def _calculate_severity(self, value: float, threshold: float, reverse: bool = False) -> RiskSeverity:
        """Calculate risk severity based on value and threshold."""
        try:
            if reverse:
                # For metrics where lower is worse (e.g., liquidity, data quality)
                ratio = threshold / value if value > 0 else float('inf')
            else:
                # For metrics where higher is worse (e.g., VaR, drawdown)
                ratio = value / threshold if threshold > 0 else float('inf')
            
            if ratio >= 2.0:
                return RiskSeverity.CRITICAL
            elif ratio >= 1.5:
                return RiskSeverity.HIGH
            elif ratio >= 1.0:
                return RiskSeverity.MEDIUM
            else:
                return RiskSeverity.LOW
                
        except Exception as e:
            logger.error(f"Severity calculation failed: {e}")
            return RiskSeverity.LOW
    
    async def get_metrics_history(self, metric_name: str, 
                                hours: int = 24) -> List[RiskMetric]:
        """Get historical metrics for specified metric."""
        try:
            if metric_name not in self.metrics_history:
                return []
            
            cutoff_time = time.time() - (hours * 3600)
            return [m for m in self.metrics_history[metric_name] if m.timestamp > cutoff_time]
            
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    async def clear_alerts(self):
        """Clear all active alerts."""
        self.active_alerts.clear()
        self.last_alert_time.clear()
        logger.info("Cleared all active alerts")
    
    async def get_monitor_status(self) -> Dict[str, Any]:
        """Get monitor status and statistics."""
        try:
            return {
                "last_calculation_time": self.last_calculation_time,
                "calculation_interval": self.calculation_interval,
                "active_alerts_count": len(self.active_alerts),
                "metrics_history_size": {name: len(history) for name, history in self.metrics_history.items()},
                "alert_cooldown": self.alert_cooldown,
                "thresholds": {cat.value: thresholds for cat, thresholds in self.thresholds.items()}
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitor status: {e}")
            return {}
