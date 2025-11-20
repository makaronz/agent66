#!/usr/bin/env python3
"""
Grafana Dashboard Configuration for SMC Trading Agent

Provides automated dashboard creation and management for:
- Trading performance metrics
- System health monitoring
- Risk management dashboards
- Real-time market data visualization
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class GrafanaConfig:
    """Grafana connection configuration"""
    url: str
    api_key: str
    username: Optional[str] = None
    password: Optional[str] = None
    organization: Optional[str] = None


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    uid: str
    title: str
    description: str
    tags: List[str]
    panels: List[Dict[str, Any]]
    variables: List[Dict[str, Any]] = None
    time_from: str = "now-1h"
    time_to: str = "now"
    refresh: str = "30s"


class GrafanaDashboardManager:
    """Manages Grafana dashboards for the trading system"""

    def __init__(self, config: GrafanaConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        })

        if config.username and config.password:
            self.session.auth = (config.username, config.password)

    def test_connection(self) -> bool:
        """Test connection to Grafana"""
        try:
            response = self.session.get(f"{self.config.url}/api/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Grafana: {e}")
            return False

    def create_dashboard(self, dashboard_config: DashboardConfig) -> bool:
        """Create or update a dashboard"""
        try:
            dashboard_payload = {
                "dashboard": {
                    "id": None,
                    "uid": dashboard_config.uid,
                    "title": dashboard_config.title,
                    "description": dashboard_config.description,
                    "tags": dashboard_config.tags,
                    "timezone": "browser",
                    "panels": dashboard_config.panels,
                    "time": {
                        "from": dashboard_config.time_from,
                        "to": dashboard_config.time_to
                    },
                    "refresh": dashboard_config.refresh,
                    "schemaVersion": 27,
                    "version": 1,
                    "templating": {
                        "list": dashboard_config.variables or []
                    }
                },
                "overwrite": True
            }

            response = self.session.post(
                f"{self.config.url}/api/dashboards/db",
                json=dashboard_payload
            )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Dashboard created/updated: {dashboard_config.title} (ID: {result.get('id')})")
                return True
            else:
                logger.error(f"Failed to create dashboard: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return False

    def delete_dashboard(self, uid: str) -> bool:
        """Delete a dashboard by UID"""
        try:
            response = self.session.delete(f"{self.config.url}/api/dashboards/uid/{uid}")
            if response.status_code == 200:
                logger.info(f"Dashboard deleted: {uid}")
                return True
            else:
                logger.error(f"Failed to delete dashboard: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error deleting dashboard: {e}")
            return False

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards"""
        try:
            response = self.session.get(f"{self.config.url}/api/search")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list dashboards: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error listing dashboards: {e}")
            return []

    def create_data_source(self, data_source_config: Dict[str, Any]) -> bool:
        """Create a Prometheus data source"""
        try:
            response = self.session.post(
                f"{self.config.url}/api/datasources",
                json=data_source_config
            )
            if response.status_code in [200, 201]:
                logger.info(f"Data source created: {data_source_config.get('name')}")
                return True
            else:
                logger.error(f"Failed to create data source: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating data source: {e}")
            return False


class DashboardTemplates:
    """Pre-built dashboard templates for the trading system"""

    @staticmethod
    def trading_performance_dashboard() -> DashboardConfig:
        """Trading performance dashboard"""
        panels = [
            {
                "id": 1,
                "title": "Portfolio Value",
                "type": "stat",
                "targets": [
                    {
                        "expr": "portfolio_value",
                        "legendFormat": "Portfolio Value"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "mappings": []
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
            },
            {
                "id": 2,
                "title": "Total P&L",
                "type": "stat",
                "targets": [
                    {
                        "expr": "sum(increase(trade_pnl_bucket[24h]))",
                        "legendFormat": "24h P&L"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": -1000},
                                {"color": "yellow", "value": 0},
                                {"color": "green", "value": 1000}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
            },
            {
                "id": 3,
                "title": "Trade Execution Time",
                "type": "heatmap",
                "targets": [
                    {
                        "expr": "rate(trade_execution_time_bucket[1h])",
                        "legendFormat": "{{le}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
            },
            {
                "id": 4,
                "title": "Trade Volume by Symbol",
                "type": "piechart",
                "targets": [
                    {
                        "expr": "sum by (symbol) (increase(trade_volume[24h]))",
                        "legendFormat": "{{symbol}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
            },
            {
                "id": 5,
                "title": "Win Rate",
                "type": "stat",
                "targets": [
                    {
                        "expr": "(sum(increase(trades_total{side=\"buy\"}[24h])) + sum(increase(trades_total{side=\"sell\"}[24h]))) / (sum(increase(trades_total{side=\"buy\"}[24h])) + sum(increase(trades_total{side=\"sell\"}[24h]))) * 100",
                        "legendFormat": "Win Rate"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": 40},
                                {"color": "yellow", "value": 60},
                                {"color": "green", "value": 80}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 16}
            },
            {
                "id": 6,
                "title": "Risk Score",
                "type": "gauge",
                "targets": [
                    {
                        "expr": "risk_score",
                        "legendFormat": "Risk Score"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent-0.1",
                        "max": 1,
                        "min": 0,
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 0.6},
                                {"color": "red", "value": 0.8}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 16}
            },
            {
                "id": 7,
                "title": "Slippage Distribution",
                "type": "histogram",
                "targets": [
                    {
                        "expr": "rate(slippage_bucket[1h])",
                        "legendFormat": "Slippage"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
            },
            {
                "id": 8,
                "title": "Signal Confidence",
                "type": "heatmap",
                "targets": [
                    {
                        "expr": "rate(signal_confidence_bucket[1h])",
                        "legendFormat": "{{le}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 24}
            }
        ]

        return DashboardConfig(
            uid="trading-performance",
            title="SMC Trading - Performance Dashboard",
            description="Real-time trading performance metrics and analytics",
            tags=["smc", "trading", "performance"],
            panels=panels,
            time_from="now-6h",
            refresh="15s"
        )

    @staticmethod
    def system_health_dashboard() -> DashboardConfig:
        """System health monitoring dashboard"""
        panels = [
            {
                "id": 1,
                "title": "System CPU Usage",
                "type": "graph",
                "targets": [
                    {
                        "expr": "system_cpu_usage",
                        "legendFormat": "CPU %"
                    }
                ],
                "yAxes": [
                    {"max": 100, "min": 0, "unit": "percent"}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
            },
            {
                "id": 2,
                "title": "System Memory Usage",
                "type": "graph",
                "targets": [
                    {
                        "expr": "system_memory_usage",
                        "legendFormat": "Memory %"
                    }
                ],
                "yAxes": [
                    {"max": 100, "min": 0, "unit": "percent"}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
            },
            {
                "id": 3,
                "title": "Health Check Status",
                "type": "stat",
                "targets": [
                    {
                        "expr": "sum(health_check_status)",
                        "legendFormat": "Healthy Checks"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": 1},
                                {"color": "green", "value": 3}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8}
            },
            {
                "id": 4,
                "title": "Active Alerts",
                "type": "stat",
                "targets": [
                    {
                        "expr": "sum(alerts_total)",
                        "legendFormat": "Total Alerts"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 1},
                                {"color": "red", "value": 5}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 8}
            },
            {
                "id": 5,
                "title": "Network I/O",
                "type": "graph",
                "targets": [
                    {
                        "expr": "rate(system_network_bytes_sent[5m])",
                        "legendFormat": "Bytes Sent/s"
                    },
                    {
                        "expr": "rate(system_network_bytes_recv[5m])",
                        "legendFormat": "Bytes Recv/s"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
            },
            {
                "id": 6,
                "title": "System Load Average",
                "type": "graph",
                "targets": [
                    {
                        "expr": "system_load_average",
                        "legendFormat": "Load Average"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
            },
            {
                "id": 7,
                "title": "Process Count",
                "type": "graph",
                "targets": [
                    {
                        "expr": "system_process_count",
                        "legendFormat": "Processes"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
            }
        ]

        return DashboardConfig(
            uid="system-health",
            title="SMC Trading - System Health",
            description="System resource monitoring and health status",
            tags=["smc", "system", "health"],
            panels=panels,
            time_from="now-1h",
            refresh="10s"
        )

    @staticmethod
    def risk_management_dashboard() -> DashboardConfig:
        """Risk management dashboard"""
        panels = [
            {
                "id": 1,
                "title": "Portfolio Risk Score",
                "type": "gauge",
                "targets": [
                    {
                        "expr": "risk_score",
                        "legendFormat": "Risk Score"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent-0.1",
                        "max": 1,
                        "min": 0,
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 0.5},
                                {"color": "red", "value": 0.8}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
            },
            {
                "id": 2,
                "title": "Position Sizes by Symbol",
                "type": "bargauge",
                "targets": [
                    {
                        "expr": "position_size",
                        "legendFormat": "{{symbol}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
            },
            {
                "id": 3,
                "title": "Daily Loss",
                "type": "stat",
                "targets": [
                    {
                        "expr": "sum(increase(trade_pnl_bucket[24h])) < 0",
                        "legendFormat": "Daily Loss"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": -100},
                                {"color": "yellow", "value": -500},
                                {"color": "red", "value": -1000}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 8, "x": 0, "y": 8}
            },
            {
                "id": 4,
                "title": "Max Drawdown",
                "type": "stat",
                "targets": [
                    {
                        "expr": "max_over_time(portfolio_value[24h]) - portfolio_value",
                        "legendFormat": "Current Drawdown"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": -500},
                                {"color": "red", "value": -1000}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 8, "x": 8, "y": 8}
            },
            {
                "id": 5,
                "title": "VaR Limit Usage",
                "type": "gauge",
                "targets": [
                    {
                        "expr": "risk_score * 100",
                        "legendFormat": "VaR Usage %"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "max": 100,
                        "min": 0,
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 70},
                                {"color": "red", "value": 90}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 8, "x": 16, "y": 8}
            },
            {
                "id": 6,
                "title": "Risk Alerts",
                "type": "table",
                "targets": [
                    {
                        "expr": "alerts_total",
                        "legendFormat": "Alerts",
                        "format": "table"
                    }
                ],
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
            }
        ]

        return DashboardConfig(
            uid="risk-management",
            title="SMC Trading - Risk Management",
            description="Risk monitoring and management metrics",
            tags=["smc", "risk", "management"],
            panels=panels,
            time_from="now-3h",
            refresh="30s"
        )

    @staticmethod
    def latency_monitoring_dashboard() -> DashboardConfig:
        """Latency monitoring dashboard"""
        panels = [
            {
                "id": 1,
                "title": "Trade Execution Latency",
                "type": "heatmap",
                "targets": [
                    {
                        "expr": "rate(trade_execution_time_bucket[1h])",
                        "legendFormat": "{{le}}"
                    }
                ],
                "gridPos": {"h": 10, "w": 12, "x": 0, "y": 0}
            },
            {
                "id": 2,
                "title": "System Component Latency",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(latency_bucket[5m]))",
                        "legendFormat": "95th percentile - {{component}}"
                    },
                    {
                        "expr": "histogram_quantile(0.50, rate(latency_bucket[5m]))",
                        "legendFormat": "50th percentile - {{component}}"
                    }
                ],
                "gridPos": {"h": 10, "w": 12, "x": 12, "y": 0}
            },
            {
                "id": 3,
                "title": "SMC Detection Latency",
                "type": "stat",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(latency_bucket{component=\"smc_detector\"}[5m]))",
                        "legendFormat": "95th percentile"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "ms",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 50},
                                {"color": "red", "value": 100}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 10}
            },
            {
                "id": 4,
                "title": "Risk Analysis Latency",
                "type": "stat",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(latency_bucket{component=\"risk_manager\"}[5m]))",
                        "legendFormat": "95th percentile"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "ms",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 25},
                                {"color": "red", "value": 50}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 10}
            },
            {
                "id": 5,
                "title": "Order Execution Latency",
                "type": "stat",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(latency_bucket{component=\"execution_engine\"}[5m]))",
                        "legendFormat": "95th percentile"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "ms",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 25},
                                {"color": "red", "value": 50}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 10}
            },
            {
                "id": 6,
                "title": "API Response Time",
                "type": "stat",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(latency_bucket{component=\"api\"}[5m]))",
                        "legendFormat": "95th percentile"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "ms",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 100},
                                {"color": "red", "value": 500}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 10}
            }
        ]

        return DashboardConfig(
            uid="latency-monitoring",
            title="SMC Trading - Latency Monitoring",
            description="System latency monitoring and performance metrics",
            tags=["smc", "latency", "performance"],
            panels=panels,
            time_from="now-30m",
            refresh="5s"
        )


class DashboardSetup:
    """Automated dashboard setup for the trading system"""

    def __init__(self, grafana_config: GrafanaConfig):
        self.grafana_manager = GrafanaDashboardManager(grafana_config)

    def setup_all_dashboards(self) -> bool:
        """Setup all standard dashboards"""
        try:
            # Test connection first
            if not self.grafana_manager.test_connection():
                logger.error("Cannot connect to Grafana")
                return False

            # Create Prometheus data source if needed
            self._setup_prometheus_datasource()

            # Create dashboards
            dashboards = [
                DashboardTemplates.trading_performance_dashboard(),
                DashboardTemplates.system_health_dashboard(),
                DashboardTemplates.risk_management_dashboard(),
                DashboardTemplates.latency_monitoring_dashboard()
            ]

            success_count = 0
            for dashboard in dashboards:
                if self.grafana_manager.create_dashboard(dashboard):
                    success_count += 1
                else:
                    logger.error(f"Failed to create dashboard: {dashboard.title}")

            logger.info(f"Created {success_count}/{len(dashboards)} dashboards successfully")
            return success_count == len(dashboards)

        except Exception as e:
            logger.error(f"Error setting up dashboards: {e}")
            return False

    def _setup_prometheus_datasource(self):
        """Setup Prometheus data source"""
        datasource_config = {
            "name": "SMC Trading Prometheus",
            "type": "prometheus",
            "url": "http://localhost:8000",  # Default Prometheus port
            "access": "proxy",
            "isDefault": True,
            "editable": True
        }

        # Check if data source already exists
        existing_datasources = self._list_datasources()
        for ds in existing_datasources:
            if ds['name'] == datasource_config['name']:
                logger.info(f"Data source '{datasource_config['name']}' already exists")
                return

        # Create new data source
        if self.grafana_manager.create_data_source(datasource_config):
            logger.info(f"Created Prometheus data source: {datasource_config['name']}")
        else:
            logger.error(f"Failed to create Prometheus data source")

    def _list_datasources(self) -> List[Dict[str, Any]]:
        """List existing data sources"""
        try:
            response = self.grafana_manager.session.get(
                f"{self.grafana_manager.config.url}/api/datasources"
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def create_custom_dashboard(self, dashboard_config: DashboardConfig) -> bool:
        """Create a custom dashboard"""
        return self.grafana_manager.create_dashboard(dashboard_config)

    def export_dashboard(self, uid: str, file_path: str) -> bool:
        """Export dashboard to file"""
        try:
            response = self.grafana_manager.session.get(
                f"{self.grafana_manager.config.url}/api/dashboards/uid/{uid}"
            )
            if response.status_code == 200:
                dashboard_data = response.json()
                with open(file_path, 'w') as f:
                    json.dump(dashboard_data, f, indent=2)
                logger.info(f"Dashboard exported to: {file_path}")
                return True
            else:
                logger.error(f"Failed to export dashboard: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error exporting dashboard: {e}")
            return False


def main():
    """Example usage of dashboard setup"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    grafana_config = GrafanaConfig(
        url=os.getenv('GRAFANA_URL', 'http://localhost:3000'),
        api_key=os.getenv('GRAFANA_API_KEY'),
        username=os.getenv('GRAFANA_USERNAME'),
        password=os.getenv('GRAFANA_PASSWORD')
    )

    setup = DashboardSetup(grafana_config)

    if setup.setup_all_dashboards():
        print("All dashboards created successfully!")
    else:
        print("Failed to create some dashboards")


if __name__ == "__main__":
    main()