#!/usr/bin/env python3
"""
Monitoring setup utility for SMC Trading Agent

This script helps set up and configure the monitoring system with:
- Prometheus metrics server
- Grafana dashboards
- Alert configurations
- Health checks
"""

import os
import sys
import argparse
import logging
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from monitoring.enhanced_monitoring import initialize_monitoring
from monitoring.grafana_dashboards import GrafanaConfig, DashboardSetup
from config import get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MonitoringSetup:
    """Monitoring system setup utility"""

    def __init__(self):
        self.monitoring_system = None
        self.running = False

    def start_monitoring(self, config: Optional[Dict[str, Any]] = None):
        """Start the monitoring system"""
        try:
            if config is None:
                # Load configuration from config module
                app_config = get_config()
                config = app_config.monitoring.dict()

            logger.info("Starting enhanced monitoring system...")

            # Initialize monitoring system
            self.monitoring_system = initialize_monitoring(config)

            # Start monitoring
            self.monitoring_system.start()

            self.running = True
            logger.info("Monitoring system started successfully")

            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            return True

        except Exception as e:
            logger.error(f"Failed to start monitoring system: {e}")
            return False

    def setup_grafana_dashboards(self, grafana_url: str, grafana_api_key: str,
                                grafana_username: Optional[str] = None,
                                grafana_password: Optional[str] = None) -> bool:
        """Setup Grafana dashboards"""
        try:
            logger.info("Setting up Grafana dashboards...")

            grafana_config = GrafanaConfig(
                url=grafana_url,
                api_key=grafana_api_key,
                username=grafana_username,
                password=grafana_password
            )

            dashboard_setup = DashboardSetup(grafana_config)

            if dashboard_setup.setup_all_dashboards():
                logger.info("All Grafana dashboards created successfully")
                return True
            else:
                logger.error("Failed to create some dashboards")
                return False

        except Exception as e:
            logger.error(f"Failed to setup Grafana dashboards: {e}")
            return False

    def stop_monitoring(self):
        """Stop the monitoring system"""
        if self.monitoring_system and self.running:
            logger.info("Stopping monitoring system...")
            self.monitoring_system.stop()
            self.running = False
            logger.info("Monitoring system stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_monitoring()
        sys.exit(0)

    def run_demo(self):
        """Run a demonstration of the monitoring system"""
        if not self.running:
            logger.error("Monitoring system not running")
            return

        logger.info("Starting monitoring demonstration...")

        try:
            # Simulate some trading activity
            for i in range(10):
                if not self.running:
                    break

                # Record a trade
                self.monitoring_system.record_trade(
                    symbol="BTC/USDT",
                    side="buy" if i % 2 == 0 else "sell",
                    quantity=0.1 + (i * 0.01),
                    price=50000.0 + (i * 100),
                    execution_time=0.05 + (i * 0.001),
                    pnl=10.0 * (i % 3 - 1),  # Simulate some P&L
                    slippage=0.0001 * (1 + i * 0.1)
                )

                # Update portfolio value
                portfolio_value = 10000.0 + (i * 50)
                self.monitoring_system.update_portfolio_value(portfolio_value)

                # Update risk score
                risk_score = 0.3 + (i * 0.05)
                self.monitoring_system.update_risk_score(risk_score)

                # Record some latencies
                components = ["smc_detector", "risk_manager", "execution_engine", "api"]
                for component in components:
                    latency = 0.01 + (i * 0.005)
                    self.monitoring_system.record_latency(component, latency)

                # Show current status
                health = self.monitoring_system.get_health_status()
                summary = self.monitoring_system.get_trading_summary()
                alerts = self.monitoring_system.get_active_alerts()

                print(f"\n--- Status Update {i+1} ---")
                print(f"Health Status: {health['overall_status']}")
                print(f"Portfolio Value: ${portfolio_value:.2f}")
                print(f"Risk Score: {risk_score:.2f}")
                print(f"Total Trades: {summary.get('total_trades', 0)}")
                print(f"Active Alerts: {len(alerts)}")

                time.sleep(2)

            logger.info("Monitoring demonstration completed")

        except Exception as e:
            logger.error(f"Error during demonstration: {e}")

    def show_status(self):
        """Show current monitoring system status"""
        if not self.monitoring_system:
            logger.error("Monitoring system not initialized")
            return

        try:
            # Health status
            health = self.monitoring_system.get_health_status()
            print(f"\n=== System Health ===")
            print(f"Overall Status: {health['overall_status']}")
            print(f"Total Checks: {health.get('total_checks', 0)}")
            print(f"Healthy Checks: {health.get('healthy_checks', 0)}")
            if health.get('critical_failures'):
                print(f"Critical Failures: {', '.join(health['critical_failures'])}")

            # Trading summary
            summary = self.monitoring_system.get_trading_summary()
            if summary:
                print(f"\n=== Trading Summary ===")
                print(f"Total Trades: {summary.get('total_trades', 0)}")
                print(f"Win Rate: {summary.get('win_rate', 0):.1%}")
                print(f"Total P&L: ${summary.get('total_pnl', 0):.2f}")
                print(f"Avg Execution Time: {summary.get('avg_execution_time', 0):.3f}s")
                print(f"Avg Slippage: {summary.get('avg_slippage', 0):.4f}")

            # Active alerts
            alerts = self.monitoring_system.get_active_alerts()
            if alerts:
                print(f"\n=== Active Alerts ===")
                for alert in alerts:
                    print(f"- {alert['severity'].upper()}: {alert['message']}")
            else:
                print(f"\n=== Active Alerts ===")
                print("No active alerts")

        except Exception as e:
            logger.error(f"Error getting status: {e}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="SMC Trading Agent Monitoring Setup")
    parser.add_argument("action", choices=[
        "start", "stop", "setup-grafana", "demo", "status"
    ], help="Action to perform")

    parser.add_argument("--config-file", "-c",
                       help="Configuration file path")
    parser.add_argument("--grafana-url", "-g",
                       help="Grafana URL")
    parser.add_argument("--grafana-api-key", "-k",
                       help="Grafana API key")
    parser.add_argument("--grafana-username", "-u",
                       help="Grafana username")
    parser.add_argument("--grafana-password", "-p",
                       help="Grafana password")
    parser.add_argument("--demo", action="store_true",
                       help="Run demonstration after starting")
    parser.add_argument("--no-daemon", action="store_true",
                       help="Run in foreground (don't daemonize)")

    args = parser.parse_args()

    setup = MonitoringSetup()

    if args.action == "start":
        # Load configuration
        config = None
        if args.config_file:
            # Load from file (implement as needed)
            pass

        if setup.start_monitoring(config):
            if args.demo:
                setup.run_demo()
            elif args.no_daemon:
                # Keep running in foreground
                print("Monitoring system running. Press Ctrl+C to stop.")
                try:
                    while setup.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            else:
                print("Monitoring system started in daemon mode")
                setup.show_status()
        else:
            return 1

    elif args.action == "stop":
        setup.stop_monitoring()

    elif args.action == "setup-grafana":
        if not all([args.grafana_url, args.grafana_api_key]):
            logger.error("Grafana URL and API key are required")
            return 1

        if setup.setup_grafana_dashboards(
            args.grafana_url,
            args.grafana_api_key,
            args.grafana_username,
            args.grafana_password
        ):
            print("Grafana dashboards setup completed successfully")
        else:
            print("Failed to setup Grafana dashboards")
            return 1

    elif args.action == "demo":
        if setup.start_monitoring():
            setup.run_demo()
            setup.stop_monitoring()
        else:
            return 1

    elif args.action == "status":
        # Try to connect to existing monitoring system
        if setup.start_monitoring():
            setup.show_status()
            setup.stop_monitoring()
        else:
            print("Monitoring system is not running")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())