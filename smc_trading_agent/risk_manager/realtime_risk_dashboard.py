"""
Real-Time Risk Dashboard System

This module provides comprehensive real-time risk monitoring with:
- Live risk metrics and alerts
- Interactive risk visualization
- Real-time VaR and stress testing
- Portfolio heat mapping and correlation visualization
- Risk threshold monitoring and automated alerts
- Performance and risk attribution analytics
- Regulatory compliance monitoring dashboard
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
import threading
import time
from collections import defaultdict, deque
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import websockets
import asyncio
from fastapi import WebSocket
import uuid

# Import our risk management components
from .enhanced_var_calculator import EnhancedVaRCalculator, VaRMethod
from .portfolio_risk_manager import PortfolioRiskManager
from .dynamic_risk_controls import DynamicRiskControls, MarketRegime
from .enhanced_compliance_engine import EnhancedComplianceEngine, ComplianceStatus

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskMetricType(Enum):
    """Risk metric types for dashboard."""
    PORTFOLIO_VAR = "portfolio_var"
    PORTFOLIO_CVAR = "portfolio_cvar"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    CORRELATION_RISK = "correlation_risk"
    CONCENTRATION_RISK = "concentration_risk"
    BETA_EXPOSURE = "beta_exposure"
    LIQUIDITY_RISK = "liquidity_risk"
    COMPLIANCE_STATUS = "compliance_status"

class DashboardTheme(Enum):
    """Dashboard visualization themes."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"

@dataclass
class RiskAlert:
    """Risk alert notification."""
    alert_id: str
    metric_type: RiskMetricType
    severity: AlertSeverity
    title: str
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RiskMetric:
    """Real-time risk metric."""
    metric_type: RiskMetricType
    value: float
    timestamp: datetime
    previous_value: Optional[float]
    change_pct: Optional[float]
    trend: str  # "up", "down", "stable"
    status: str  # "normal", "warning", "critical"
    color: str

@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    update_interval: int = 5  # seconds
    max_data_points: int = 1000
    theme: DashboardTheme = DashboardTheme.LIGHT
    enable_alerts: bool = True
    alert_thresholds: Dict[RiskMetricType, Dict[str, float]] = field(default_factory=dict)
    websocket_enabled: bool = True
    port: int = 8001

class RealTimeRiskDashboard:
    """
    Real-time risk dashboard with comprehensive monitoring and visualization.

    Provides live risk metrics, alerts, and interactive visualizations for
    institutional-grade risk management.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Real-Time Risk Dashboard.

        Args:
            config: Dashboard configuration
        """
        self.config = config or {}
        self.dashboard_config = DashboardConfig(**self.config)

        # Initialize risk management components
        self.var_calculator = EnhancedVaRCalculator(self.config.get('var_config', {}))
        self.portfolio_manager = PortfolioRiskManager(self.config.get('portfolio_config', {}))
        self.dynamic_controls = DynamicRiskControls(self.config.get('dynamic_config', {}))
        self.compliance_engine = EnhancedComplianceEngine(self.config.get('compliance_config', {}))

        # Dashboard state
        self.risk_metrics: Dict[RiskMetricType, deque] = defaultdict(lambda: deque(maxlen=self.dashboard_config.max_data_points))
        self.active_alerts: Dict[str, RiskAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.websocket_connections: Dict[str, WebSocket] = {}

        # Real-time data streams
        self.market_data_stream: Dict[str, pd.DataFrame] = {}
        self.portfolio_stream: deque = deque(maxlen=100)
        self.performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_update = datetime.utcnow()

        # Alert thresholds
        self._initialize_alert_thresholds()

        # Dashboard layouts
        self.dashboard_layouts = self._initialize_dashboard_layouts()

        logger.info("Real-Time Risk Dashboard initialized")

    def _initialize_alert_thresholds(self):
        """Initialize default alert thresholds for risk metrics."""
        self.dashboard_config.alert_thresholds = {
            RiskMetricType.PORTFOLIO_VAR: {
                'warning': 0.02,  # 2% VaR triggers warning
                'critical': 0.04   # 4% VaR triggers critical
            },
            RiskMetricType.MAX_DRAWDOWN: {
                'warning': 0.10,  # 10% drawdown warning
                'critical': 0.15   # 15% drawdown critical
            },
            RiskMetricType.VOLATILITY: {
                'warning': 0.20,  # 20% annualized vol warning
                'critical': 0.30   # 30% annualized vol critical
            },
            RiskMetricType.CORRELATION_RISK: {
                'warning': 0.7,   # 0.7 correlation warning
                'critical': 0.85  # 0.85 correlation critical
            },
            RiskMetricType.CONCENTRATION_RISK: {
                'warning': 0.15,  # 15% concentration warning
                'critical': 0.25   # 25% concentration critical
            },
            RiskMetricType.LIQUIDITY_RISK: {
                'warning': 0.05,  # 5% liquidity risk warning
                'critical': 0.10   # 10% liquidity risk critical
            }
        }

    def _initialize_dashboard_layouts(self) -> Dict[str, Any]:
        """Initialize dashboard layout configurations."""
        return {
            'main_dashboard': {
                'layout': 'grid_2x2',
                'components': [
                    'risk_metrics_overview',
                    'var_analysis',
                    'correlation_heatmap',
                    'alerts_panel'
                ]
            },
            'risk_analysis': {
                'layout': 'grid_3x1',
                'components': [
                    'portfolio_composition',
                    'risk_attribution',
                    'stress_testing'
                ]
            },
            'compliance': {
                'layout': 'grid_2x2',
                'components': [
                    'compliance_status',
                    'best_execution',
                    'transaction_monitoring',
                    'audit_trail'
                ]
            },
            'performance': {
                'layout': 'grid_2x2',
                'components': [
                    'returns_analysis',
                    'risk_adjusted_performance',
                    'attribution_analysis',
                    'benchmark_comparison'
                ]
            }
        }

    async def start_monitoring(self):
        """Start real-time risk monitoring."""
        try:
            if self.is_monitoring:
                logger.warning("Dashboard monitoring already running")
                return

            self.is_monitoring = True

            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()

            # Start WebSocket server if enabled
            if self.dashboard_config.websocket_enabled:
                await self._start_websocket_server()

            logger.info("Real-time risk monitoring started")

        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
            raise

    async def stop_monitoring(self):
        """Stop real-time risk monitoring."""
        try:
            self.is_monitoring = False

            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)

            # Close WebSocket connections
            for websocket in self.websocket_connections.values():
                await websocket.close()

            self.websocket_connections.clear()

            logger.info("Real-time risk monitoring stopped")

        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")

    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread."""
        while self.is_monitoring:
            try:
                # Update risk metrics
                asyncio.run(self._update_risk_metrics())

                # Check for alerts
                asyncio.run(self._check_alerts())

                # Update dashboard data
                asyncio.run(self._update_dashboard_data())

                # Sleep until next update
                time.sleep(self.dashboard_config.update_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(self.dashboard_config.update_interval)

    async def _update_risk_metrics(self):
        """Update all risk metrics with latest data."""
        try:
            # Get latest portfolio data
            if not self.portfolio_stream:
                return

            latest_portfolio = self.portfolio_stream[-1]
            portfolio_data = latest_portfolio.get('data', pd.DataFrame())

            if portfolio_data.empty:
                return

            # Calculate portfolio VaR
            if 'returns' in portfolio_data.columns:
                var_result = await self.var_calculator.calculate_enhanced_var(
                    portfolio_data, VaRMethod.HISTORICAL, 0.95, 1
                )
                await self._update_metric(RiskMetricType.PORTFOLIO_VAR, var_result.var_value)

                # Calculate CVaR
                cvar_result = await self.var_calculator.calculate_cvar(
                    portfolio_data, VaRMethod.HISTORICAL, 0.95, 1
                )
                await self._update_metric(RiskMetricType.PORTFOLIO_CVAR, cvar_result.cvar_value)

            # Calculate volatility
            if 'returns' in portfolio_data.columns:
                volatility = portfolio_data['returns'].std() * np.sqrt(252)
                await self._update_metric(RiskMetricType.VOLATILITY, volatility)

            # Calculate maximum drawdown
            if 'value' in portfolio_data.columns:
                max_drawdown = self._calculate_max_drawdown(portfolio_data['value'])
                await self._update_metric(RiskMetricType.MAX_DRAWDOWN, max_drawdown)

            # Update portfolio-specific metrics
            await self._update_portfolio_risk_metrics()

            self.last_update = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to update risk metrics: {e}")

    async def _update_portfolio_risk_metrics(self):
        """Update portfolio-specific risk metrics."""
        try:
            # Get current positions
            current_positions = self._get_current_positions()

            if not current_positions:
                return

            # Calculate correlation risk
            correlation_analysis = await self.portfolio_manager.analyze_correlation_matrix(
                self._get_returns_matrix(current_positions)
            )
            await self._update_metric(RiskMetricType.CORRELATION_RISK, correlation_analysis.maximum_correlation)

            # Calculate concentration risk
            concentration_analysis = await self.portfolio_manager.analyze_concentration_risk(
                current_positions
            )
            await self._update_metric(RiskMetricType.CONCENTRATION_RISK, concentration_analysis.value)

            # Calculate liquidity risk (simplified)
            liquidity_risk = self._calculate_liquidity_risk(current_positions)
            await self._update_metric(RiskMetricType.LIQUIDITY_RISK, liquidity_risk)

            # Calculate compliance status
            compliance_score = self._calculate_compliance_score()
            await self._update_metric(RiskMetricType.COMPLIANCE_STATUS, compliance_score)

        except Exception as e:
            logger.error(f"Failed to update portfolio risk metrics: {e}")

    async def _update_metric(self, metric_type: RiskMetricType, value: float):
        """Update a specific risk metric."""
        try:
            previous_value = None
            change_pct = None
            trend = "stable"
            status = "normal"
            color = "green"

            # Get previous value for comparison
            if len(self.risk_metrics[metric_type]) > 0:
                previous_metric = self.risk_metrics[metric_type][-1]
                previous_value = previous_metric.value
                change_pct = ((value - previous_value) / previous_value) * 100 if previous_value != 0 else 0

                if abs(change_pct) > 0.01:
                    trend = "up" if change_pct > 0 else "down"

            # Determine status and color based on thresholds
            thresholds = self.dashboard_config.alert_thresholds.get(metric_type, {})
            if 'critical' in thresholds and value >= thresholds['critical']:
                status = "critical"
                color = "red"
            elif 'warning' in thresholds and value >= thresholds['warning']:
                status = "warning"
                color = "orange"
            else:
                color = "green"

            # Create metric
            metric = RiskMetric(
                metric_type=metric_type,
                value=value,
                timestamp=datetime.utcnow(),
                previous_value=previous_value,
                change_pct=change_pct,
                trend=trend,
                status=status,
                color=color
            )

            # Add to history
            self.risk_metrics[metric_type].append(metric)

        except Exception as e:
            logger.error(f"Failed to update metric {metric_type}: {e}")

    async def _check_alerts(self):
        """Check for risk alert conditions."""
        if not self.dashboard_config.enable_alerts:
            return

        try:
            for metric_type, metric_history in self.risk_metrics.items():
                if not metric_history:
                    continue

                latest_metric = metric_history[-1]
                thresholds = self.dashboard_config.alert_thresholds.get(metric_type, {})

                # Check for critical alerts
                if 'critical' in thresholds and latest_metric.value >= thresholds['critical']:
                    await self._create_alert(
                        metric_type,
                        AlertSeverity.CRITICAL,
                        f"Critical {metric_type.value}",
                        f"{metric_type.value} has reached critical level: {latest_metric.value:.4f}",
                        latest_metric.value,
                        thresholds['critical']
                    )

                # Check for warning alerts
                elif 'warning' in thresholds and latest_metric.value >= thresholds['warning']:
                    await self._create_alert(
                        metric_type,
                        AlertSeverity.MEDIUM,
                        f"Warning {metric_type.value}",
                        f"{metric_type.value} exceeds warning threshold: {latest_metric.value:.4f}",
                        latest_metric.value,
                        thresholds['warning']
                    )

        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")

    async def _create_alert(self, metric_type: RiskMetricType, severity: AlertSeverity,
                          title: str, message: str, current_value: float,
                          threshold_value: float):
        """Create and process a risk alert."""
        try:
            alert_id = str(uuid.uuid4())
            alert = RiskAlert(
                alert_id=alert_id,
                metric_type=metric_type,
                severity=severity,
                title=title,
                message=message,
                current_value=current_value,
                threshold_value=threshold_value,
                timestamp=datetime.utcnow()
            )

            # Add to active alerts
            self.active_alerts[alert_id] = alert

            # Add to history
            self.alert_history.append(alert)

            # Send WebSocket notification
            await self._broadcast_alert(alert)

            logger.warning(f"Risk alert created: {title}")

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")

    async def _update_dashboard_data(self):
        """Update dashboard data structures."""
        try:
            # Update performance metrics
            await self._update_performance_metrics()

            # Broadcast updates to WebSocket clients
            if self.websocket_connections:
                dashboard_update = await self._get_dashboard_update()
                await self._broadcast_dashboard_update(dashboard_update)

        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")

    async def update_market_data(self, symbol: str, data: pd.DataFrame):
        """Update market data for a symbol."""
        try:
            self.market_data_stream[symbol] = data.tail(1000)  # Keep last 1000 data points

            # Update portfolio stream if this is a portfolio component
            portfolio_data = self._aggregate_portfolio_data()
            if not portfolio_data.empty:
                self.portfolio_stream.append({
                    'timestamp': datetime.utcnow(),
                    'data': portfolio_data
                })

        except Exception as e:
            logger.error(f"Failed to update market data for {symbol}: {e}")

    async def generate_dashboard_visualizations(self) -> Dict[str, Any]:
        """Generate dashboard visualizations."""
        try:
            visualizations = {}

            # Risk metrics overview
            visualizations['risk_metrics_overview'] = await self._create_risk_metrics_chart()

            # VaR analysis chart
            visualizations['var_analysis'] = await self._create_var_analysis_chart()

            # Correlation heatmap
            visualizations['correlation_heatmap'] = await self._create_correlation_heatmap()

            # Portfolio composition
            visualizations['portfolio_composition'] = await self._create_portfolio_composition_chart()

            # Alerts panel
            visualizations['alerts_panel'] = await self._create_alerts_panel()

            # Performance chart
            visualizations['performance_chart'] = await self._create_performance_chart()

            return visualizations

        except Exception as e:
            logger.error(f"Failed to generate dashboard visualizations: {e}")
            return {}

    # Visualization creation methods

    async def _create_risk_metrics_chart(self) -> Dict[str, Any]:
        """Create risk metrics overview chart."""
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Portfolio VaR', 'Volatility', 'Max Drawdown', 'Correlation Risk'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )

            # Add VaR trace
            var_metrics = list(self.risk_metrics[RiskMetricType.PORTFOLIO_VAR])
            if var_metrics:
                var_times = [m.timestamp for m in var_metrics]
                var_values = [m.value for m in var_metrics]
                fig.add_trace(
                    go.Scatter(x=var_times, y=var_values, name='VaR', line=dict(color='red')),
                    row=1, col=1
                )

            # Add volatility trace
            vol_metrics = list(self.risk_metrics[RiskMetricType.VOLATILITY])
            if vol_metrics:
                vol_times = [m.timestamp for m in vol_metrics]
                vol_values = [m.value for m in vol_metrics]
                fig.add_trace(
                    go.Scatter(x=vol_times, y=vol_values, name='Volatility', line=dict(color='blue')),
                    row=1, col=2
                )

            # Add drawdown trace
            dd_metrics = list(self.risk_metrics[RiskMetricType.MAX_DRAWDOWN])
            if dd_metrics:
                dd_times = [m.timestamp for m in dd_metrics]
                dd_values = [m.value for m in dd_metrics]
                fig.add_trace(
                    go.Scatter(x=dd_times, y=dd_values, name='Max Drawdown', line=dict(color='orange')),
                    row=2, col=1
                )

            # Add correlation trace
            corr_metrics = list(self.risk_metrics[RiskMetricType.CORRELATION_RISK])
            if corr_metrics:
                corr_times = [m.timestamp for m in corr_metrics]
                corr_values = [m.value for m in corr_metrics]
                fig.add_trace(
                    go.Scatter(x=corr_times, y=corr_values, name='Correlation Risk', line=dict(color='purple')),
                    row=2, col=2
                )

            fig.update_layout(
                title='Real-Time Risk Metrics Overview',
                height=600,
                showlegend=False
            )

            return {'chart': fig.to_json(), 'type': 'risk_metrics_overview'}

        except Exception as e:
            logger.error(f"Failed to create risk metrics chart: {e}")
            return {'error': str(e)}

    async def _create_var_analysis_chart(self) -> Dict[str, Any]:
        """Create VaR analysis chart."""
        try:
            var_metrics = list(self.risk_metrics[RiskMetricType.PORTFOLIO_VAR])
            cvar_metrics = list(self.risk_metrics[RiskMetricType.PORTFOLIO_CVAR])

            if not var_metrics:
                return {'error': 'No VaR data available'}

            fig = go.Figure()

            # Add VaR trace
            var_times = [m.timestamp for m in var_metrics]
            var_values = [m.value for m in var_metrics]
            fig.add_trace(
                go.Scatter(x=var_times, y=var_values, name='VaR (95%)', line=dict(color='red', width=2))
            )

            # Add CVaR trace
            if cvar_metrics:
                cvar_times = [m.timestamp for m in cvar_metrics]
                cvar_values = [m.value for m in cvar_metrics]
                fig.add_trace(
                    go.Scatter(x=cvar_times, y=cvar_values, name='CVaR (95%)', line=dict(color='darkred', width=2, dash='dash'))
                )

            fig.update_layout(
                title='Value at Risk Analysis',
                xaxis_title='Time',
                yaxis_title='Risk Measure',
                height=400,
                hovermode='x unified'
            )

            return {'chart': fig.to_json(), 'type': 'var_analysis'}

        except Exception as e:
            logger.error(f"Failed to create VaR analysis chart: {e}")
            return {'error': str(e)}

    async def _create_correlation_heatmap(self) -> Dict[str, Any]:
        """Create correlation heatmap."""
        try:
            current_positions = self._get_current_positions()
            if len(current_positions) < 2:
                return {'error': 'Insufficient positions for correlation analysis'}

            returns_matrix = self._get_returns_matrix(current_positions)
            correlation_analysis = await self.portfolio_manager.analyze_correlation_matrix(returns_matrix)

            fig = go.Figure(data=go.Heatmap(
                z=correlation_analysis.correlation_matrix.values,
                x=correlation_analysis.correlation_matrix.columns,
                y=correlation_analysis.correlation_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=correlation_analysis.correlation_matrix.round(2).values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))

            fig.update_layout(
                title='Portfolio Correlation Matrix',
                height=500
            )

            return {'chart': fig.to_json(), 'type': 'correlation_heatmap'}

        except Exception as e:
            logger.error(f"Failed to create correlation heatmap: {e}")
            return {'error': str(e)}

    async def _create_portfolio_composition_chart(self) -> Dict[str, Any]:
        """Create portfolio composition chart."""
        try:
            current_positions = self._get_current_positions()
            if not current_positions:
                return {'error': 'No positions available'}

            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{"type": "pie"}, {"type": "bar"}]],
                subplot_titles=('Portfolio Allocation', 'Position Sizes')
            )

            # Pie chart for allocation
            symbols = list(current_positions.keys())
            values = list(current_positions.values())

            fig.add_trace(
                go.Pie(labels=symbols, values=values, name="Allocation"),
                row=1, col=1
            )

            # Bar chart for position sizes
            fig.add_trace(
                go.Bar(x=symbols, y=values, name="Position Size", marker_color='lightblue'),
                row=1, col=2
            )

            fig.update_layout(
                title='Portfolio Composition',
                height=400,
                showlegend=False
            )

            return {'chart': fig.to_json(), 'type': 'portfolio_composition'}

        except Exception as e:
            logger.error(f"Failed to create portfolio composition chart: {e}")
            return {'error': str(e)}

    async def _create_alerts_panel(self) -> Dict[str, Any]:
        """Create alerts panel data."""
        try:
            active_alerts = list(self.active_alerts.values())
            recent_alerts = list(self.alert_history)[-10:]  # Last 10 alerts

            alerts_data = {
                'active_alerts': [
                    {
                        'id': alert.alert_id,
                        'title': alert.title,
                        'message': alert.message,
                        'severity': alert.severity.value,
                        'timestamp': alert.timestamp.isoformat(),
                        'metric_type': alert.metric_type.value
                    }
                    for alert in active_alerts
                ],
                'recent_alerts': [
                    {
                        'id': alert.alert_id,
                        'title': alert.title,
                        'severity': alert.severity.value,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in recent_alerts
                ],
                'alert_summary': {
                    'total_active': len(active_alerts),
                    'critical_count': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                    'high_count': len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                    'medium_count': len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]),
                    'low_count': len([a for a in active_alerts if a.severity == AlertSeverity.LOW])
                }
            }

            return {'data': alerts_data, 'type': 'alerts_panel'}

        except Exception as e:
            logger.error(f"Failed to create alerts panel: {e}")
            return {'error': str(e)}

    async def _create_performance_chart(self) -> Dict[str, Any]:
        """Create performance chart."""
        try:
            if not self.portfolio_stream:
                return {'error': 'No portfolio data available'}

            # Get portfolio value series
            portfolio_values = []
            timestamps = []

            for entry in self.portfolio_stream:
                data = entry['data']
                if 'value' in data.columns:
                    portfolio_values.extend(data['value'].tolist())
                    timestamps.extend(data.index.tolist())

            if not portfolio_values:
                return {'error': 'No portfolio values available'}

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(x=timestamps, y=portfolio_values, name='Portfolio Value', line=dict(color='green'))
            )

            # Add drawdown overlay
            portfolio_series = pd.Series(portfolio_values, index=timestamps)
            running_max = portfolio_series.expanding().max()
            drawdown = (portfolio_series - running_max) / running_max * 100

            fig.add_trace(
                go.Scatter(x=timestamps, y=drawdown, name='Drawdown %', line=dict(color='red'), yaxis='y2')
            )

            fig.update_layout(
                title='Portfolio Performance',
                xaxis_title='Time',
                yaxis=dict(title='Portfolio Value'),
                yaxis2=dict(title='Drawdown %', overlaying='y', side='right'),
                height=400,
                hovermode='x unified'
            )

            return {'chart': fig.to_json(), 'type': 'performance_chart'}

        except Exception as e:
            logger.error(f"Failed to create performance chart: {e}")
            return {'error': str(e)}

    # WebSocket methods

    async def _start_websocket_server(self):
        """Start WebSocket server for real-time updates."""
        try:
            # This would be implemented with a proper WebSocket server
            # For now, we'll just log that it would start
            logger.info(f"WebSocket server would start on port {self.dashboard_config.port}")

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")

    async def _broadcast_alert(self, alert: RiskAlert):
        """Broadcast alert to connected clients."""
        try:
            if not self.websocket_connections:
                return

            alert_data = {
                'type': 'alert',
                'alert_id': alert.alert_id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'timestamp': alert.timestamp.isoformat(),
                'metric_type': alert.metric_type.value,
                'current_value': alert.current_value,
                'threshold': alert.threshold_value
            }

            # Send to all connected clients
            for websocket in self.websocket_connections.values():
                try:
                    await websocket.send_json(alert_data)
                except:
                    # Remove dead connections
                    pass

        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")

    async def _broadcast_dashboard_update(self, update_data: Dict[str, Any]):
        """Broadcast dashboard update to connected clients."""
        try:
            if not self.websocket_connections:
                return

            update_data['type'] = 'dashboard_update'
            update_data['timestamp'] = datetime.utcnow().isoformat()

            # Send to all connected clients
            for websocket in self.websocket_connections.values():
                try:
                    await websocket.send_json(update_data)
                except:
                    # Remove dead connections
                    pass

        except Exception as e:
            logger.error(f"Failed to broadcast dashboard update: {e}")

    async def _get_dashboard_update(self) -> Dict[str, Any]:
        """Get current dashboard state for broadcasting."""
        try:
            latest_metrics = {}
            for metric_type, metric_history in self.risk_metrics.items():
                if metric_history:
                    latest_metrics[metric_type.value] = {
                        'value': metric_history[-1].value,
                        'status': metric_history[-1].status,
                        'change_pct': metric_history[-1].change_pct,
                        'timestamp': metric_history[-1].timestamp.isoformat()
                    }

            return {
                'latest_metrics': latest_metrics,
                'active_alerts_count': len(self.active_alerts),
                'last_update': self.last_update.isoformat(),
                'monitoring_status': 'active' if self.is_monitoring else 'inactive'
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard update: {e}")
            return {}

    # Helper methods

    def _get_current_positions(self) -> Dict[str, float]:
        """Get current portfolio positions."""
        # This would typically come from portfolio management system
        # For now, return sample data
        return {
            'BTCUSDT': 0.4,
            'ETHUSDT': 0.3,
            'ADAUSDT': 0.2,
            'DOTUSDT': 0.1
        }

    def _get_returns_matrix(self, positions: Dict[str, float]) -> pd.DataFrame:
        """Get returns matrix for correlation analysis."""
        # This would typically calculate from historical price data
        # For now, return sample data
        symbols = list(positions.keys())
        dates = pd.date_range(end=datetime.utcnow(), periods=100, freq='D')

        returns_data = {}
        for symbol in symbols:
            # Generate sample returns
            returns = np.random.normal(0.001, 0.02, 100)
            returns_data[symbol] = returns

        return pd.DataFrame(returns_data, index=dates)

    def _calculate_max_drawdown(self, values: pd.Series) -> float:
        """Calculate maximum drawdown from value series."""
        try:
            if values.empty:
                return 0.0

            cumulative = (1 + values.pct_change().fillna(0)).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return abs(drawdown.min())

        except Exception as e:
            logger.error(f"Failed to calculate max drawdown: {e}")
            return 0.0

    def _calculate_liquidity_risk(self, positions: Dict[str, float]) -> float:
        """Calculate liquidity risk score."""
        # Simplified liquidity risk calculation
        # In practice, this would consider trading volume, bid-ask spreads, etc.
        return np.random.uniform(0.01, 0.1)  # Sample value

    def _calculate_compliance_score(self) -> float:
        """Calculate compliance status score."""
        # Simplified compliance score (0-1, where 1 is fully compliant)
        return np.random.uniform(0.8, 1.0)  # Sample value

    async def _update_performance_metrics(self):
        """Update performance metrics tracking."""
        try:
            # Calculate various performance metrics
            if self.portfolio_stream:
                latest_portfolio = self.portfolio_stream[-1]
                portfolio_data = latest_portfolio.get('data', pd.DataFrame())

                if not portfolio_data.empty and 'returns' in portfolio_data.columns:
                    returns = portfolio_data['returns']

                    # Sharpe ratio
                    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
                    self.performance_metrics['sharpe_ratio'].append(sharpe_ratio)

                    # Sortino ratio
                    downside_returns = returns[returns < 0]
                    sortino_ratio = returns.mean() / downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
                    self.performance_metrics['sortino_ratio'].append(sortino_ratio)

                    # Maximum drawdown
                    max_dd = self._calculate_max_drawdown(portfolio_data.get('value', pd.Series()))
                    self.performance_metrics['max_drawdown'].append(max_dd)

                    # Volatility
                    volatility = returns.std() * np.sqrt(252)
                    self.performance_metrics['volatility'].append(volatility)

        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")

    def _aggregate_portfolio_data(self) -> pd.DataFrame:
        """Aggregate market data into portfolio data."""
        try:
            if not self.market_data_stream:
                return pd.DataFrame()

            # Simple aggregation - would be more sophisticated in practice
            all_data = []
            for symbol, data in self.market_data_stream.items():
                if 'close' in data.columns:
                    all_data.append(data['close'])

            if not all_data:
                return pd.DataFrame()

            # Combine data
            portfolio_df = pd.concat(all_data, axis=1)
            portfolio_df.columns = [f'asset_{i}' for i in range(len(portfolio_df.columns))]

            # Calculate portfolio value (equally weighted)
            portfolio_df['value'] = portfolio_df.mean(axis=1)
            portfolio_df['returns'] = portfolio_df['value'].pct_change()

            return portfolio_df.dropna()

        except Exception as e:
            logger.error(f"Failed to aggregate portfolio data: {e}")
            return pd.DataFrame()

# Factory function for easy instantiation
def create_realtime_risk_dashboard(config: Optional[Dict[str, Any]] = None) -> RealTimeRiskDashboard:
    """Create real-time risk dashboard instance."""
    return RealTimeRiskDashboard(config)