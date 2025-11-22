<<<<<<< Current (Your changes)
=======
"""
Data Pipeline Service for SMC Trading Agent.

This module provides the main entry point for the data pipeline service including:
- Data ingestion coordination
- Real-time data processing
- Health monitoring endpoints
- Graceful shutdown handling
- Service lifecycle management
"""

import sys
import signal
import logging
import logging.config
import asyncio
import time
from typing import Dict, Any, Optional

# Configuration and validation imports
from ..config_loader import load_secure_config, ConfigValidationError, EnvironmentVariableError
from ..config_validator import validate_config

# Data pipeline components
from .ingestion import MarketDataProcessor

# Error handling and validation imports
from ..error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)

# Service coordination and health monitoring
from ..service_manager import ServiceManager
from ..health_monitor import EnhancedHealthMonitor

# FastAPI and server imports
from fastapi import FastAPI
import uvicorn

# Global flag to indicate shutdown
shutdown_flag = False


class DataPipelineService:
    """
    Data Pipeline Service for coordinating data ingestion and processing.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.data_processor = MarketDataProcessor()
        self.is_running = False
        
        # Initialize circuit breakers for data pipeline operations
        self.ingestion_circuit_breaker = CircuitBreaker(
            name="data_ingestion",
            failure_threshold=3,
            recovery_timeout=60.0,
            logger=self.logger
        )
        
        self.processing_circuit_breaker = CircuitBreaker(
            name="data_processing",
            failure_threshold=3,
            recovery_timeout=60.0,
            logger=self.logger
        )
        
        # Initialize retry handlers
        self.ingestion_retry_handler = RetryHandler(2, 1.0, 10.0, logger=self.logger)
        self.processing_retry_handler = RetryHandler(2, 1.0, 10.0, logger=self.logger)
    
    async def initialize(self):
        """Initialize the data pipeline service."""
        self.logger.info("Initializing Data Pipeline Service...")
        
        try:
            # Initialize data processor
            if hasattr(self.data_processor, 'initialize_async'):
                await self.data_processor.initialize_async()
            elif hasattr(self.data_processor, 'initialize'):
                self.data_processor.initialize()
            
            self.logger.info("Data Pipeline Service initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Pipeline Service: {e}", exc_info=True)
            return False
    
    async def shutdown(self):
        """Shutdown the data pipeline service."""
        self.logger.info("Shutting down Data Pipeline Service...")
        self.is_running = False
        
        try:
            # Shutdown data processor
            if hasattr(self.data_processor, 'shutdown_async'):
                await self.data_processor.shutdown_async()
            elif hasattr(self.data_processor, 'shutdown'):
                self.data_processor.shutdown()
            
            self.logger.info("Data Pipeline Service shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during Data Pipeline Service shutdown: {e}", exc_info=True)
    
    def health_check(self) -> bool:
        """Health check for the data pipeline service."""
        try:
            # Basic health check - verify data processor is accessible
            if self.data_processor is None:
                return False
            
            # Additional health checks can be added here
            # For example, check database connections, Kafka connectivity, etc.
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data pipeline health check failed: {e}")
            return False
    
    async def run_data_pipeline(self):
        """Run the main data pipeline loop."""
        self.is_running = True
        self.logger.info("Starting Data Pipeline Service...")
        
        # Get configuration
        data_config = self.config.get('data_pipeline', {})
        symbols = data_config.get('ingestion', {}).get('symbols', ['BTC/USDT'])
        timeframe = data_config.get('ingestion', {}).get('timeframe', '1h')
        
        while self.is_running:
            try:
                self.logger.info("Starting data ingestion cycle...")
                
                # Ingest data for each symbol
                for symbol in symbols:
                    try:
                        # Get market data with error handling
                        market_data = self.ingestion_circuit_breaker.call(
                            lambda: self.ingestion_retry_handler.call(
                                self.data_processor.get_latest_ohlcv_data, symbol, timeframe
                            )
                        )
                        
                        if market_data is not None and not market_data.empty:
                            self.logger.info(f"Successfully ingested data for {symbol}", extra={
                                'symbol': symbol,
                                'data_shape': market_data.shape,
                                'timeframe': timeframe
                            })
                            
                            # Process the data (placeholder for real-time processing)
                            await self._process_market_data(market_data, symbol)
                        else:
                            self.logger.warning(f"No data received for {symbol}")
                    
                    except Exception as e:
                        self.logger.error(f"Failed to ingest data for {symbol}: {e}", exc_info=True)
                        continue
                
                self.logger.info("Data ingestion cycle completed. Waiting for next interval...")
                
                # Wait before next cycle
                for _ in range(60):  # 1 minute interval
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Unexpected error in data pipeline cycle: {e}", exc_info=True)
                await asyncio.sleep(30)  # Wait before retry
                continue
        
        self.logger.info("Data Pipeline Service stopped.")
    
    async def _process_market_data(self, market_data, symbol: str):
        """Process market data (placeholder for real-time processing)."""
        try:
            # This is where real-time processing would happen
            # For now, just log the processing
            self.logger.debug(f"Processing market data for {symbol}", extra={
                'symbol': symbol,
                'data_points': len(market_data)
            })
            
            # Placeholder for real-time processing operations:
            # - OHLCV construction
            # - Volume profile analysis
            # - Liquidity zone detection
            # - Data storage
            
        except Exception as e:
            self.logger.error(f"Failed to process market data for {symbol}: {e}", exc_info=True)


def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration."""
    try:
        logging.config.dictConfig(config["logging"])
        sys.excepthook = handle_uncaught_exception
    except (ValueError, KeyError) as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        sys.exit(1)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger().critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals."""
    global shutdown_flag
    if not shutdown_flag:
        logging.getLogger().info(f"Received shutdown signal: {signal.Signals(signum).name}. Initiating graceful shutdown...")
        shutdown_flag = True
    else:
        logging.getLogger().warning("Received second shutdown signal. Forcing exit.")
        sys.exit(1)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration using secure configuration loader.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary with environment variables substituted
        
    Raises:
        SystemExit: If configuration loading fails
    """
    try:
        # Try to load from .env file first, then fall back to system environment
        env_file = ".env"
        return load_secure_config(config_path, env_file)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    except (ConfigValidationError, EnvironmentVariableError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Please ensure all required environment variables are set.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)


async def main_async():
    """Async main function for data pipeline service."""
    
    # Load and validate configuration
    config = load_config()
    
    # Validate configuration
    is_valid, errors, warnings = validate_config(config)
    if not is_valid:
        print("Configuration validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    if warnings:
        print("Configuration validation completed with warnings")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("Initializing Data Pipeline Service with enhanced service coordination...", extra=config.get('app', {}))

    # Initialize service manager
    service_manager = ServiceManager(config, logger)
    
    # Initialize enhanced health monitor
    health_monitor = EnhancedHealthMonitor(
        app_name=f"{config.get('app', {}).get('name', 'smc-trading-agent')}-data-pipeline",
        logger=logger
    )
    
    # Initialize data pipeline service
    try:
        data_pipeline_service = DataPipelineService(config, logger)
        
        # Register service with service manager
        service_manager.register_service(
            "data_pipeline", 
            data_pipeline_service, 
            data_pipeline_service.health_check, 
            critical=True
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize data pipeline service: {str(e)}", exc_info=True)
        return 1

    # Start health monitoring
    await health_monitor.start_background_health_checks()
    
    # Get monitoring port from config (use different port for data pipeline)
    monitoring_port = config.get('monitoring', {}).get('port', 8008) + 1  # Use next port
    
    # Create FastAPI app for health monitoring
    app = health_monitor.get_fastapi_app()
    
    # Start health monitoring server
    config_uvicorn = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=monitoring_port,
        log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    
    # Run data pipeline service and health monitoring concurrently
    try:
        async with service_manager.service_lifecycle():
            # Start health monitoring server in background
            server_task = asyncio.create_task(server.serve())
            
            # Run data pipeline service
            pipeline_task = asyncio.create_task(
                data_pipeline_service.run_data_pipeline()
            )
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [server_task, pipeline_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
    except Exception as e:
        logger.error(f"Data pipeline service lifecycle failed: {e}", exc_info=True)
        return 1
    finally:
        # Shutdown health monitor
        await health_monitor.shutdown()
    
    return 0


def main():
    """Main entry point for data pipeline service."""
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Received keyboard interrupt, shutting down gracefully...")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
>>>>>>> Incoming (Background Agent changes)
