#!/usr/bin/env python3
"""
Main entry point for SMC Trading Agent Stream Processor

This module initializes and runs the Kafka Streams-based real-time data processing
system for market data with exactly-once processing semantics.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional
import yaml
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_pipeline.stream_processor import StreamProcessorManager, StreamProcessor
from config_loader import ConfigLoader
from health_monitor import HealthMonitor
from service_manager import ServiceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/stream_processor.log')
    ]
)

logger = logging.getLogger(__name__)


class StreamProcessorApp:
    """
    Main application class for the stream processor.
    
    Manages the lifecycle of stream processors, health monitoring,
    and graceful shutdown handling.
    """
    
    def __init__(self):
        """Initialize the stream processor application."""
        self.config = None
        self.processor_manager = None
        self.health_monitor = None
        self.service_manager = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Stream Processor Application initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def load_configuration(self) -> bool:
        """
        Load application configuration.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise
        """
        try:
            config_loader = ConfigLoader()
            
            # Load configuration from file or environment
            config_path = os.getenv('CONFIG_PATH', '/app/config/streams-config.yaml')
            
            if os.path.exists(config_path):
                logger.info(f"Loading configuration from {config_path}")
                self.config = config_loader.load_yaml_config(config_path)
            else:
                logger.info("Loading configuration from environment variables")
                self.config = self._load_config_from_env()
            
            # Validate configuration
            if not self._validate_configuration():
                logger.error("Configuration validation failed")
                return False
            
            logger.info("Configuration loaded and validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
        processor_id = os.getenv('PROCESSOR_ID', 'stream-processor-1')
        
        return {
            'kafka': {
                'bootstrap_servers': bootstrap_servers
            },
            'stream_processors': {
                'market_data_processor': {
                    'consumer_group': f'smc-market-data-processor-{processor_id}',
                    'processing_mode': 'exactly_once',
                    'batch_size': int(os.getenv('BATCH_SIZE', '100')),
                    'commit_interval_ms': int(os.getenv('COMMIT_INTERVAL_MS', '5000')),
                    'max_poll_records': int(os.getenv('MAX_POLL_RECORDS', '500')),
                    'input_topics': [
                        'market_data.binance.btcusdt.trades',
                        'market_data.binance.ethusdt.trades',
                        'market_data.bybit.btcusdt.trades',
                        'market_data.bybit.ethusdt.trades',
                        'market_data.oanda.eurusd.trades',
                        'market_data.binance.btcusdt.orderbook',
                        'market_data.binance.ethusdt.orderbook',
                        'market_data.bybit.btcusdt.orderbook',
                        'market_data.bybit.ethusdt.orderbook'
                    ],
                    'output_topics': {
                        'enriched_trades': 'enriched_trades',
                        'enriched_orderbook': 'enriched_orderbook',
                        'enriched_klines': 'enriched_klines',
                        'smc_signals': 'smc_signals'
                    }
                }
            },
            'logging': {
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'format': 'json'
            },
            'monitoring': {
                'metrics_port': int(os.getenv('METRICS_PORT', '8080')),
                'health_check_port': int(os.getenv('HEALTH_CHECK_PORT', '8081'))
            }
        }
    
    def _validate_configuration(self) -> bool:
        """
        Validate the loaded configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            # Check required sections
            required_sections = ['kafka', 'stream_processors', 'monitoring']
            for section in required_sections:
                if section not in self.config:
                    logger.error(f"Missing required configuration section: {section}")
                    return False
            
            # Validate Kafka configuration
            kafka_config = self.config['kafka']
            if 'bootstrap_servers' not in kafka_config or not kafka_config['bootstrap_servers']:
                logger.error("Missing or empty Kafka bootstrap servers")
                return False
            
            # Validate stream processors configuration
            processors_config = self.config['stream_processors']
            if not processors_config:
                logger.error("No stream processors configured")
                return False
            
            for processor_id, processor_config in processors_config.items():
                if not self._validate_processor_config(processor_id, processor_config):
                    return False
            
            # Validate monitoring configuration
            monitoring_config = self.config['monitoring']
            required_ports = ['metrics_port', 'health_check_port']
            for port_key in required_ports:
                if port_key not in monitoring_config:
                    logger.error(f"Missing monitoring port configuration: {port_key}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def _validate_processor_config(self, processor_id: str, config: Dict[str, Any]) -> bool:
        """
        Validate individual processor configuration.
        
        Args:
            processor_id: Processor identifier
            config: Processor configuration
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ['consumer_group', 'input_topics', 'output_topics']
        
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field '{field}' in processor '{processor_id}'")
                return False
        
        # Validate input topics
        if not config['input_topics'] or not isinstance(config['input_topics'], list):
            logger.error(f"Invalid input_topics configuration for processor '{processor_id}'")
            return False
        
        # Validate output topics
        if not config['output_topics'] or not isinstance(config['output_topics'], dict):
            logger.error(f"Invalid output_topics configuration for processor '{processor_id}'")
            return False
        
        return True
    
    async def initialize_services(self) -> bool:
        """
        Initialize all services.
        
        Returns:
            bool: True if all services initialized successfully, False otherwise
        """
        try:
            # Initialize service manager
            self.service_manager = ServiceManager()
            
            # Initialize health monitor
            health_config = {
                'port': self.config['monitoring']['health_check_port'],
                'metrics_port': self.config['monitoring']['metrics_port']
            }
            self.health_monitor = HealthMonitor(health_config)
            
            # Initialize stream processor manager
            manager_config = {
                'bootstrap_servers': self.config['kafka']['bootstrap_servers']
            }
            self.processor_manager = StreamProcessorManager(manager_config)
            
            # Start health monitor
            await self.health_monitor.start()
            
            logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False
    
    async def start_stream_processors(self) -> bool:
        """
        Start all configured stream processors.
        
        Returns:
            bool: True if all processors started successfully, False otherwise
        """
        try:
            processors_config = self.config['stream_processors']
            
            for processor_id, processor_config in processors_config.items():
                # Add Kafka bootstrap servers to processor config
                processor_config['bootstrap_servers'] = self.config['kafka']['bootstrap_servers']
                
                logger.info(f"Starting stream processor: {processor_id}")
                
                if await self.processor_manager.start_processor(processor_id, processor_config):
                    logger.info(f"Stream processor '{processor_id}' started successfully")
                else:
                    logger.error(f"Failed to start stream processor: {processor_id}")
                    return False
            
            logger.info("All stream processors started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream processors: {e}")
            return False
    
    async def run(self) -> int:
        """
        Main application run method.
        
        Returns:
            int: Exit code (0 for success, 1 for error)
        """
        try:
            logger.info("Starting SMC Trading Agent Stream Processor...")
            
            # Load configuration
            if not await self.load_configuration():
                logger.error("Failed to load configuration")
                return 1
            
            # Initialize services
            if not await self.initialize_services():
                logger.error("Failed to initialize services")
                return 1
            
            # Start stream processors
            if not await self.start_stream_processors():
                logger.error("Failed to start stream processors")
                return 1
            
            # Register health checks
            await self._register_health_checks()
            
            self.running = True
            logger.info("Stream Processor Application started successfully")
            
            # Main application loop
            await self._main_loop()
            
            logger.info("Stream Processor Application stopped")
            return 0
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            return 1
        finally:
            await self.cleanup()
    
    async def _register_health_checks(self):
        """Register health check endpoints."""
        if self.health_monitor and self.processor_manager:
            # Register processor health checks
            for processor_id in self.config['stream_processors'].keys():
                self.health_monitor.register_health_check(
                    f"processor_{processor_id}",
                    lambda pid=processor_id: self._check_processor_health(pid)
                )
            
            # Register overall system health check
            self.health_monitor.register_health_check(
                "system",
                self._check_system_health
            )
    
    async def _check_processor_health(self, processor_id: str) -> Dict[str, Any]:
        """Check health of a specific processor."""
        metrics = self.processor_manager.get_processor_metrics(processor_id)
        if metrics:
            return {
                'healthy': metrics.get('state') == 'running',
                'details': metrics
            }
        return {'healthy': False, 'details': 'Processor not found'}
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        all_metrics = self.processor_manager.get_all_metrics()
        healthy_processors = sum(1 for m in all_metrics.values() if m.get('state') == 'running')
        total_processors = len(all_metrics)
        
        return {
            'healthy': healthy_processors == total_processors and total_processors > 0,
            'details': {
                'healthy_processors': healthy_processors,
                'total_processors': total_processors,
                'processors': all_metrics
            }
        }
    
    async def _main_loop(self):
        """Main application loop."""
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown of the application."""
        logger.info("Initiating graceful shutdown...")
        
        self.running = False
        
        try:
            # Stop stream processors
            if self.processor_manager:
                await self.processor_manager.stop_all_processors()
            
            # Stop health monitor
            if self.health_monitor:
                await self.health_monitor.stop()
            
            # Stop service manager
            if self.service_manager:
                await self.service_manager.stop_all_services()
            
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self.shutdown_event.set()
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            # Ensure all services are stopped
            if self.running:
                await self.shutdown()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point."""
    app = StreamProcessorApp()
    
    try:
        exit_code = await app.run()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await app.shutdown()
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    # Run the application
    asyncio.run(main())