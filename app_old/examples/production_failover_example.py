#!/usr/bin/env python3
"""
Production Failover System Example

This example demonstrates how to set up and use the complete failover system
in a production environment with real exchange connections, monitoring,
and automated recovery.

Usage:
    python examples/production_failover_example.py --environment production
    python examples/production_failover_example.py --environment testnet --demo
"""

import asyncio
import logging
import argparse
import signal
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_pipeline.exchange_connectors.production_config import Environment, ExchangeType
from data_pipeline.exchange_connectors.failover_integration import (
    ProductionFailoverFactory,
    FailoverAwareDataPipeline,
    test_production_failover_system
)
from data_pipeline.exchange_connectors.failover_manager import FailoverEvent, FailoverTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('failover_example.log')
    ]
)
logger = logging.getLogger(__name__)


class ProductionFailoverDemo:
    """
    Comprehensive demonstration of the production failover system.
    
    Shows real-world usage patterns, monitoring, and operational procedures.
    """
    
    def __init__(self, environment: Environment, config_path: Optional[str] = None):
        """
        Initialize the failover demonstration.
        
        Args:
            environment: Target environment
            config_path: Path to configuration file
        """
        self.environment = environment
        self.config_path = config_path or "data_pipeline/exchange_connectors/failover_config.yaml"
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.factory: Optional[ProductionFailoverFactory] = None
        self.pipeline: Optional[FailoverAwareDataPipeline] = None
        
        # State tracking
        self.running = False
        self.stats = {
            "start_time": None,
            "data_messages_received": 0,
            "failover_events": 0,
            "exchanges_used": set(),
            "errors": []
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Initialized failover demo for {environment.value}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def setup(self):
        """Set up the failover system."""
        try:
            logger.info("Setting up production failover system...")
            
            # Create factory
            self.factory = ProductionFailoverFactory(self.environment)
            
            # Create data pipeline
            self.pipeline = FailoverAwareDataPipeline(self.factory)
            
            # Add data callback
            self.pipeline.add_data_callback(self._handle_data_message)
            
            # Add failover callback
            self.factory.failover_manager.add_failover_callback(self._handle_failover_event)
            
            logger.info("Failover system setup completed")
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise
    
    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of failover capabilities."""
        logger.info("Starting comprehensive failover demonstration")
        
        try:
            self.stats["start_time"] = datetime.utcnow()
            self.running = True
            
            # Phase 1: System startup and health checks
            await self._demo_phase_1_startup()
            
            # Phase 2: Normal operation with data flow
            await self._demo_phase_2_normal_operation()
            
            # Phase 3: Failover scenarios
            await self._demo_phase_3_failover_scenarios()
            
            # Phase 4: Recovery and failback
            await self._demo_phase_4_recovery()
            
            # Phase 5: Monitoring and reporting
            await self._demo_phase_5_monitoring()
            
            logger.info("Comprehensive demonstration completed successfully")
            
        except Exception as e:
            logger.error(f"Demonstration failed: {e}")
            self.stats["errors"].append(str(e))
            raise
        
        finally:
            await self._cleanup()
    
    async def _demo_phase_1_startup(self):
        """Phase 1: System startup and health checks."""
        logger.info("=== PHASE 1: System Startup and Health Checks ===")
        
        async with self.factory.managed_failover_connectors() as context:
            connectors = context["connectors"]
            failover_manager = context["failover_manager"]
            
            logger.info(f"Connected to {len(connectors)} exchanges:")
            for exchange_type, connector in connectors.items():
                logger.info(f"  - {exchange_type.value}: {connector.name}")
                self.stats["exchanges_used"].add(exchange_type.value)
            
            # Show initial health status
            status = failover_manager.get_status()
            logger.info(f"Primary exchange: {status['primary_exchange']}")
            logger.info(f"Active exchange: {status['active_exchange']}")
            
            # Display health scores
            logger.info("Exchange health scores:")
            for exchange, health in status["exchange_health"].items():
                logger.info(f"  - {exchange}: {health['health_score']:.1f}% "
                          f"(connected: {health['is_connected']}, "
                          f"latency: {health['average_latency_ms']:.1f}ms)")
            
            # Wait for health monitoring to stabilize
            logger.info("Allowing health monitoring to stabilize...")
            await asyncio.sleep(10)
    
    async def _demo_phase_2_normal_operation(self):
        """Phase 2: Normal operation with data flow."""
        logger.info("=== PHASE 2: Normal Operation with Data Flow ===")
        
        if not self.running:
            return
        
        # Start data ingestion
        streams = ["btcusdt@trade", "ethusdt@trade", "adausdt@trade"]
        await self.pipeline.start_data_ingestion(streams)
        
        logger.info(f"Started data ingestion for streams: {streams}")
        logger.info("Collecting data for 30 seconds...")
        
        # Let data flow for a while
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < 30 and self.running:
            await asyncio.sleep(1)
            
            # Show periodic stats
            if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
                active_exchange = self.factory.get_active_exchange()
                logger.info(f"Data flowing from {active_exchange.value if active_exchange else 'unknown'} "
                          f"({self.stats['data_messages_received']} messages received)")
        
        await self.pipeline.stop_data_ingestion()
        logger.info(f"Phase 2 completed. Total messages: {self.stats['data_messages_received']}")
    
    async def _demo_phase_3_failover_scenarios(self):
        """Phase 3: Failover scenarios."""
        logger.info("=== PHASE 3: Failover Scenarios ===")
        
        if not self.running:
            return
        
        # Test different failover scenarios
        scenarios = [
            "connection_failure",
            "high_latency",
            "manual_failover"
        ]
        
        for scenario in scenarios:
            if not self.running:
                break
            
            logger.info(f"Testing scenario: {scenario}")
            
            try:
                result = await self.factory.failover_manager.test_failover_scenario(scenario)
                
                if result["success"]:
                    logger.info(f"✓ Scenario '{scenario}' completed successfully in {result['duration_ms']:.1f}ms")
                    if result.get("failover_occurred"):
                        logger.info(f"  Failover: {result['original_active']} -> {result['new_active']}")
                else:
                    logger.error(f"✗ Scenario '{scenario}' failed: {result.get('error', 'Unknown error')}")
                
                # Wait between scenarios
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Scenario '{scenario}' raised exception: {e}")
                self.stats["errors"].append(f"Scenario {scenario}: {str(e)}")
    
    async def _demo_phase_4_recovery(self):
        """Phase 4: Recovery and failback."""
        logger.info("=== PHASE 4: Recovery and Failback ===")
        
        if not self.running:
            return
        
        # Show current failover state
        status = self.factory.get_failover_status()
        logger.info(f"Current state: {status['current_state']}")
        logger.info(f"Active exchange: {status['active_exchange']}")
        logger.info(f"Failed exchanges: {status['failed_exchanges']}")
        
        # Simulate recovery check
        logger.info("Checking for exchange recovery...")
        await self.factory.failover_manager._check_failed_exchange_recovery()
        
        # Show updated status
        updated_status = self.factory.get_failover_status()
        if updated_status["failed_exchanges"] != status["failed_exchanges"]:
            logger.info("Exchange recovery detected!")
            logger.info(f"Updated failed exchanges: {updated_status['failed_exchanges']}")
        else:
            logger.info("No exchange recovery detected in this demo")
        
        # Show recovery statistics
        stats = updated_status["statistics"]
        logger.info(f"Failover statistics:")
        logger.info(f"  - Total failovers: {stats['total_failovers']}")
        logger.info(f"  - Successful failovers: {stats['successful_failovers']}")
        logger.info(f"  - Average failover time: {stats['average_failover_time_ms']:.1f}ms")
    
    async def _demo_phase_5_monitoring(self):
        """Phase 5: Monitoring and reporting."""
        logger.info("=== PHASE 5: Monitoring and Reporting ===")
        
        if not self.running:
            return
        
        # Generate comprehensive status report
        status = self.factory.get_failover_status()
        
        logger.info("=== FINAL SYSTEM STATUS ===")
        logger.info(f"Environment: {status['environment']}")
        logger.info(f"Current state: {status['current_state']}")
        logger.info(f"Primary exchange: {status['primary_exchange']}")
        logger.info(f"Active exchange: {status['active_exchange']}")
        
        logger.info("\nExchange Health Summary:")
        for exchange, health in status["exchange_health"].items():
            logger.info(f"  {exchange}:")
            logger.info(f"    Health Score: {health['health_score']:.1f}%")
            logger.info(f"    Connected: {health['is_connected']}")
            logger.info(f"    Latency: {health['average_latency_ms']:.1f}ms")
            logger.info(f"    Success Rate: {health['success_rate_5min']:.1f}%")
            logger.info(f"    Priority: {health['priority']}")
        
        logger.info(f"\nFailover Rules ({len(status['failover_rules'])} configured):")
        for rule in status["failover_rules"]:
            status_icon = "✓" if rule["enabled"] else "✗"
            logger.info(f"  {status_icon} {rule['trigger']} (threshold: {rule['threshold']}, priority: {rule['priority']})")
        
        if status["recent_events"]:
            logger.info(f"\nRecent Events ({len(status['recent_events'])}):")
            for event in status["recent_events"][-5:]:  # Last 5 events
                success_icon = "✓" if event["success"] else "✗"
                logger.info(f"  {success_icon} {event['timestamp']}: {event['from_exchange']} -> {event['to_exchange']} "
                          f"({event['trigger']}, {event['duration_ms']:.1f}ms)")
        
        # Export detailed report
        report_path = f"failover_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        self.factory.failover_manager.export_failover_report(report_path)
        logger.info(f"Detailed report exported to: {report_path}")
        
        # Show demo statistics
        logger.info("\n=== DEMO STATISTICS ===")
        duration = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        logger.info(f"Demo duration: {duration:.1f} seconds")
        logger.info(f"Data messages received: {self.stats['data_messages_received']}")
        logger.info(f"Failover events: {self.stats['failover_events']}")
        logger.info(f"Exchanges used: {', '.join(self.stats['exchanges_used'])}")
        
        if self.stats["errors"]:
            logger.info(f"Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats["errors"]:
                logger.info(f"  - {error}")
        else:
            logger.info("No errors encountered ✓")
    
    async def _handle_data_message(self, data: Dict[str, Any]):
        """Handle incoming data messages."""
        self.stats["data_messages_received"] += 1
        
        # Log every 100th message to avoid spam
        if self.stats["data_messages_received"] % 100 == 0:
            source = data.get("source_exchange", "unknown")
            symbol = data.get("symbol", "unknown")
            logger.debug(f"Data #{self.stats['data_messages_received']}: {symbol} from {source}")
    
    async def _handle_failover_event(self, event: FailoverEvent):
        """Handle failover events."""
        self.stats["failover_events"] += 1
        
        success_icon = "✓" if event.success else "✗"
        logger.info(f"{success_icon} FAILOVER EVENT: {event.from_exchange.value} -> {event.to_exchange.value}")
        logger.info(f"  Trigger: {event.trigger.value}")
        logger.info(f"  Duration: {event.duration_ms:.1f}ms")
        logger.info(f"  Success: {event.success}")
        
        if not event.success and event.error_message:
            logger.error(f"  Error: {event.error_message}")
    
    async def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        
        try:
            if self.pipeline:
                await self.pipeline.stop_data_ingestion()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def run_system_tests(environment: Environment):
    """Run comprehensive system tests."""
    logger.info("Running comprehensive system tests...")
    
    try:
        results = await test_production_failover_system(environment)
        
        logger.info("=== SYSTEM TEST RESULTS ===")
        logger.info(f"Environment: {results['environment']}")
        logger.info(f"Duration: {results['duration_seconds']:.1f} seconds")
        logger.info(f"Overall success: {results['success']}")
        
        if results["success"]:
            tests = results["tests"]
            
            # Connectivity test
            if "connectivity" in tests:
                conn = tests["connectivity"]
                logger.info(f"✓ Connectivity: {conn['connected_exchanges']} exchanges connected")
                logger.info(f"  Active: {conn['active_exchange']}")
            
            # Health monitoring test
            if "health_monitoring" in tests:
                health = tests["health_monitoring"]
                logger.info(f"✓ Health Monitoring: {health['exchanges_monitored']} exchanges monitored")
                logger.info(f"  Monitoring active: {health['monitoring_active']}")
            
            # Failover scenarios test
            if "failover_scenarios" in tests:
                scenarios = tests["failover_scenarios"]
                logger.info(f"✓ Failover Scenarios: {len(scenarios.get('results', {}))} scenarios tested")
                
                for scenario, result in scenarios.get("results", {}).items():
                    success_icon = "✓" if result.get("success", False) else "✗"
                    logger.info(f"  {success_icon} {scenario}")
            
            # Data pipeline test
            if "data_pipeline" in tests:
                pipeline = tests["data_pipeline"]
                logger.info(f"✓ Data Pipeline: {pipeline['data_received']} messages received")
                logger.info(f"  Functional: {pipeline['pipeline_functional']}")
        
        else:
            logger.error(f"✗ System tests failed: {results.get('error', 'Unknown error')}")
        
        return results["success"]
        
    except Exception as e:
        logger.error(f"System tests failed with exception: {e}")
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Production Failover System Example")
    parser.add_argument(
        "--environment",
        choices=["production", "testnet"],
        default="testnet",
        help="Target environment"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run interactive demonstration"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run system tests only"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    # Convert environment string to enum
    environment = Environment.PRODUCTION if args.environment == "production" else Environment.TESTNET
    
    logger.info(f"Starting production failover example in {environment.value} mode")
    
    try:
        if args.test:
            # Run system tests only
            success = await run_system_tests(environment)
            sys.exit(0 if success else 1)
        
        elif args.demo:
            # Run interactive demonstration
            demo = ProductionFailoverDemo(environment, args.config)
            await demo.setup()
            await demo.run_comprehensive_demo()
        
        else:
            # Run both tests and demo
            logger.info("Running system tests first...")
            test_success = await run_system_tests(environment)
            
            if test_success:
                logger.info("System tests passed, running demonstration...")
                demo = ProductionFailoverDemo(environment, args.config)
                await demo.setup()
                await demo.run_comprehensive_demo()
            else:
                logger.error("System tests failed, skipping demonstration")
                sys.exit(1)
        
        logger.info("Production failover example completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())