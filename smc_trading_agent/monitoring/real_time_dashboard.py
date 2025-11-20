#!/usr/bin/env python3
"""
Real-Time Dashboard API for SMC Trading Agent

Provides WebSocket streaming and REST endpoints for:
- Live trading metrics and performance indicators
- System resource monitoring (CPU, memory, latency)
- Trading signal quality metrics
- P&L tracking and risk metrics
- Real-time alerts and notifications
- Market data streaming
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import threading
import queue
import uuid

# FastAPI for WebSocket support
try:
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI not available. Install with: pip install fastapi uvicorn")

# Plotly for advanced chart generation
try:
    import plotly.graph_objects as go
    import plotly.utils
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("Plotly not available. Install with: pip install plotly")

from .enhanced_monitoring import get_monitoring_system, EnhancedMonitoringSystem

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetric:
    """Dashboard metric definition"""
    id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    change_24h: Optional[float] = None
    change_pct_24h: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    metadata: Dict[str, Any] = None


@dataclass
class AlertNotification:
    """Alert notification structure"""
    id: str
    severity: str
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    component: str = ""
    metrics: Dict[str, Any] = None


@dataclass
class TradingSignal:
    """Trading signal information"""
    id: str
    symbol: str
    strategy: str
    signal_type: str  # buy, sell, hold
    confidence: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = None
    smc_patterns: List[str] = None
    risk_score: float = 0.0


class RealTimeDashboardManager:
    """Real-time dashboard data manager"""

    def __init__(self, monitoring_system: EnhancedMonitoringSystem = None):
        self.monitoring_system = monitoring_system or get_monitoring_system()
        self.connections: Dict[str, WebSocket] = {}
        self.alert_subscribers: List[Callable] = []
        self.data_queue = queue.Queue()
        self.running = False

        # Data caches
        self.metrics_cache: Dict[str, DashboardMetric] = {}
        self.alerts_cache: List[AlertNotification] = []
        self.signals_cache: List[TradingSignal] = []
        self.performance_history: List[Dict[str, Any]] = []

        # Update intervals (seconds)
        self.metrics_update_interval = 2
        self.performance_update_interval = 10
        self.alert_check_interval = 5

    async def register_websocket(self, websocket: WebSocket, client_id: str):
        """Register a WebSocket connection for real-time updates"""
        await websocket.accept()
        self.connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")

        # Send initial data
        await self.send_initial_data(client_id)

    async def unregister_websocket(self, client_id: str):
        """Unregister a WebSocket connection"""
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    async def send_initial_data(self, client_id: str):
        """Send initial dashboard data to a new client"""
        try:
            initial_data = {
                "type": "initial_data",
                "data": {
                    "metrics": await self.get_current_metrics(),
                    "alerts": await self.get_active_alerts(),
                    "signals": await self.get_recent_signals(),
                    "performance": await self.get_performance_summary(),
                    "system_health": await self.get_system_health()
                }
            }
            await self.send_to_client(client_id, initial_data)
        except Exception as e:
            logger.error(f"Error sending initial data to {client_id}: {e}")

    async def send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send data to a specific WebSocket client"""
        if client_id in self.connections:
            try:
                websocket = self.connections[client_id]
                await websocket.send_text(json.dumps(data, default=str))
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                # Remove dead connection
                await self.unregister_websocket(client_id)

    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast data to all connected clients"""
        if not self.connections:
            return

        message = json.dumps(data, default=str)
        dead_clients = []

        for client_id, websocket in self.connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                dead_clients.append(client_id)

        # Remove dead connections
        for client_id in dead_clients:
            await self.unregister_websocket(client_id)

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current dashboard metrics"""
        try:
            metrics = {}

            if self.monitoring_system:
                # Get trading metrics
                trading_summary = self.monitoring_system.get_trading_summary()
                metrics.update({
                    "total_trades": trading_summary.get("total_trades", 0),
                    "win_rate": trading_summary.get("win_rate", 0) * 100,
                    "avg_execution_time": trading_summary.get("avg_execution_time", 0),
                    "total_pnl": trading_summary.get("total_pnl", 0),
                    "avg_slippage": trading_summary.get("avg_slippage", 0) * 10000  # Convert to basis points
                })

                # Get system metrics
                system_health = self.monitoring_system.get_health_status()
                metrics.update({
                    "system_status": system_health.get("overall_status", "unknown"),
                    "healthy_checks": system_health.get("healthy_checks", 0),
                    "total_checks": system_health.get("total_checks", 0)
                })

                # Get metric values from registry
                if hasattr(self.monitoring_system.metric_registry, 'get_metric_value'):
                    portfolio_value = self.monitoring_system.metric_registry.get_metric_value("portfolio_value") or 0
                    risk_score = self.monitoring_system.metric_registry.get_metric_value("risk_score") or 0
                    cpu_usage = self.monitoring_system.metric_registry.get_metric_value("system_cpu_usage") or 0
                    memory_usage = self.monitoring_system.metric_registry.get_metric_value("system_memory_usage") or 0

                    metrics.update({
                        "portfolio_value": portfolio_value,
                        "risk_score": risk_score * 100,  # Convert to percentage
                        "cpu_usage": cpu_usage,
                        "memory_usage": memory_usage
                    })

            # Add calculated metrics
            if metrics.get("total_trades", 0) > 0:
                metrics["daily_trades"] = metrics["total_trades"]  # Simplified
                metrics["profit_factor"] = abs(metrics.get("total_pnl", 0) / max(metrics["total_trades"] * 10, 1))

            return metrics

        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {}

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        try:
            if self.monitoring_system:
                alerts = self.monitoring_system.get_active_alerts()
                return [asdict(alert) if hasattr(alert, '__dict__') else alert for alert in alerts]
            return []
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    async def get_recent_signals(self) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        try:
            # Return cached signals (would be populated by signal generation)
            return [asdict(signal) for signal in self.signals_cache[-20:]]  # Last 20 signals
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            if self.monitoring_system:
                trading_summary = self.monitoring_system.get_trading_summary()
                return {
                    "sharpe_ratio": 1.5,  # Placeholder - would calculate from history
                    "max_drawdown": -5.2,  # Placeholder
                    "calmar_ratio": 2.1,   # Placeholder
                    "total_return": 12.5,  # Placeholder
                    "volatility": 15.3,    # Placeholder
                    "beta": 0.85,          # Placeholder
                    "var_95": -2.1,        # Placeholder
                    "expected_shortfall": -3.2  # Placeholder
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            if self.monitoring_system:
                return self.monitoring_system.get_health_status()
            return {}
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {}

    def add_alert_notification(self, alert: AlertNotification):
        """Add a new alert notification"""
        self.alerts_cache.append(alert)

        # Keep only last 100 alerts
        if len(self.alerts_cache) > 100:
            self.alerts_cache = self.alerts_cache[-100:]

        # Broadcast alert
        asyncio.create_task(self.broadcast({
            "type": "alert",
            "data": asdict(alert)
        }))

    def add_trading_signal(self, signal: TradingSignal):
        """Add a new trading signal"""
        self.signals_cache.append(signal)

        # Keep only last 50 signals
        if len(self.signals_cache) > 50:
            self.signals_cache = self.signals_cache[-50:]

        # Broadcast signal
        asyncio.create_task(self.broadcast({
            "type": "signal",
            "data": asdict(signal)
        }))

    async def update_metrics(self):
        """Update dashboard metrics"""
        while self.running:
            try:
                metrics = await self.get_current_metrics()

                # Broadcast metrics update
                await self.broadcast({
                    "type": "metrics_update",
                    "data": metrics,
                    "timestamp": datetime.now().isoformat()
                })

                await asyncio.sleep(self.metrics_update_interval)

            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)

    async def start_real_time_updates(self):
        """Start real-time dashboard updates"""
        if self.running:
            return

        self.running = True

        # Start metrics update task
        asyncio.create_task(self.update_metrics())

        logger.info("Real-time dashboard updates started")

    async def stop_real_time_updates(self):
        """Stop real-time dashboard updates"""
        self.running = False
        logger.info("Real-time dashboard updates stopped")

    def generate_plotly_chart(self, chart_type: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Plotly chart configuration"""
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available"}

        try:
            if chart_type == "equity_curve":
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[d["timestamp"] for d in data],
                    y=[d["value"] for d in data],
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='green', width=2)
                ))
                fig.update_layout(
                    title="Portfolio Equity Curve",
                    xaxis_title="Time",
                    yaxis_title="Portfolio Value ($)",
                    template="plotly_dark"
                )

            elif chart_type == "performance_metrics":
                fig = go.Figure()
                metrics = ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
                for metric in metrics:
                    fig.add_trace(go.Bar(
                        name=metric.replace('_', ' ').title(),
                        x=[metric],
                        y=[data.get(metric, 0)]
                    ))
                fig.update_layout(
                    title="Performance Metrics",
                    template="plotly_dark"
                )

            else:
                return {"error": f"Unsupported chart type: {chart_type}"}

            return json.loads(fig.to_json())

        except Exception as e:
            logger.error(f"Error generating Plotly chart: {e}")
            return {"error": str(e)}


# Global dashboard manager instance
_dashboard_manager: Optional[RealTimeDashboardManager] = None


def get_dashboard_manager() -> RealTimeDashboardManager:
    """Get global dashboard manager instance"""
    return _dashboard_manager


def initialize_dashboard_manager(monitoring_system: EnhancedMonitoringSystem = None) -> RealTimeDashboardManager:
    """Initialize global dashboard manager"""
    global _dashboard_manager
    _dashboard_manager = RealTimeDashboardManager(monitoring_system)
    return _dashboard_manager


# Alert notification functions
async def send_trading_alert(severity: str, title: str, message: str, component: str = ""):
    """Send a trading alert to all connected dashboard clients"""
    dashboard = get_dashboard_manager()
    if dashboard:
        alert = AlertNotification(
            id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(),
            component=component
        )
        dashboard.add_alert_notification(alert)


async def send_trading_signal(symbol: str, strategy: str, signal_type: str,
                            confidence: float, entry_price: float = None,
                            stop_loss: float = None, take_profit: float = None,
                            smc_patterns: List[str] = None):
    """Send a trading signal to all connected dashboard clients"""
    dashboard = get_dashboard_manager()
    if dashboard:
        signal = TradingSignal(
            id=str(uuid.uuid4()),
            symbol=symbol,
            strategy=strategy,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=datetime.now(),
            smc_patterns=smc_patterns or []
        )
        dashboard.add_trading_signal(signal)