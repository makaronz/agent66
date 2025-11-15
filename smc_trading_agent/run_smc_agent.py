import sys
import signal
import logging
import logging.config
import time
import asyncio
from typing import Dict, Any, Optional
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Secure configuration loading
try:
    from config_loader import load_secure_config, ConfigValidationError, EnvironmentVariableError
    from config_validator import validate_config
except ImportError as e:
    print(f"Error importing configuration modules: {e}")
    print("Creating a simple test configuration...")

    def load_secure_config(config_path, env_file=None):
        return {
            "app": {"name": "smc-trading-agent", "version": "1.0.0"},
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    }
                },
                "handlers": {
                    "default": {
                        "class": "logging.StreamHandler",
                        "formatter": "default",
                        "stream": "ext://sys.stdout"
                    }
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["default"]
                }
            },
            "data_pipeline": {
                "exchanges": ["binance", "bybit"],
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"]
            },
            "decision_engine": {
                "confidence_threshold": 0.7
            },
            "monitoring": {
                "port": 8008
            }
        }

    def validate_config(config):
        return True, [], ["Test configuration - validation not implemented"]

# Component Imports - with fallbacks
try:
    from data_pipeline.ingestion import MarketDataProcessor
except ImportError:
    print("Warning: MarketDataProcessor not found, using mock")
    class MarketDataProcessor:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        def get_latest_ohlcv_data(self, symbol, timeframe):
            import pandas as pd
            import numpy as np
            # Generate mock data
            dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='H')
            return pd.DataFrame({
                'timestamp': dates,
                'open': np.random.uniform(50000, 60000, 100),
                'high': np.random.uniform(60000, 65000, 100),
                'low': np.random.uniform(45000, 50000, 100),
                'close': np.random.uniform(50000, 60000, 100),
                'volume': np.random.uniform(100, 1000, 100)
            }).set_index('timestamp')

try:
    from smc_detector.indicators import SMCIndicators
except ImportError:
    print("Warning: SMCIndicators not found, using mock")
    class SMCIndicators:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        def detect_order_blocks(self, df):
            # Return mock order blocks
            return [
                {
                    'price_level': (55000, 56000),
                    'direction': 'bullish',
                    'strength': 0.8,
                    'timestamp': df.index[-1]
                }
            ]

try:
    from decision_engine.model_ensemble import AdaptiveModelSelector
except ImportError:
    print("Warning: AdaptiveModelSelector not found, using mock")
    class AdaptiveModelSelector:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        def make_decision(self, order_blocks, market_data):
            # Return mock trading signal
            return {
                'action': 'buy',
                'symbol': 'BTC/USDT',
                'entry_price': 55000,
                'confidence': 0.75
            }

try:
    from risk_manager.smc_risk_manager import SMCRiskManager
except ImportError:
    print("Warning: SMCRiskManager not found, using mock")
    class SMCRiskManager:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        def calculate_stop_loss(self, entry_price, action, order_blocks, structure):
            return entry_price * 0.98 if action == 'buy' else entry_price * 1.02
        def calculate_take_profit(self, entry_price, stop_loss, action):
            return entry_price * 1.05 if action == 'buy' else entry_price * 0.95

try:
    from error_handlers import CircuitBreaker, RetryHandler, error_boundary, safe_execute, health_monitor, TradingError, ComponentHealthError, ErrorSeverity
except ImportError:
    print("Warning: Error handlers not found, using simplified versions")
    class CircuitBreaker:
        def __init__(self, name, failure_threshold, recovery_timeout, logger):
            self.name = name
            self.logger = logger
        def call(self, func):
            return func()

    class RetryHandler:
        def __init__(self, max_retries, base_delay, max_delay, logger):
            self.logger = logger
        def call(self, func):
            return func()

    def safe_execute(component, severity):
        def decorator(func):
            return func
        return decorator

    class ErrorSeverity:
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

try:
    from validators import data_validator, DataQualityLevel, DataValidationError
except ImportError:
    print("Warning: Validators not found, using mock")
    class DataQualityLevel:
        EXCELLENT = "excellent"
        GOOD = "good"
        POOR = "poor"
        UNUSABLE = "unusable"

    class data_validator:
        @staticmethod
        def validate_market_data(df):
            return True, []

        @staticmethod
        def assess_data_quality(df):
            return DataQualityLevel.GOOD

        @staticmethod
        def validate_order_blocks(order_blocks):
            return order_blocks

        @staticmethod
        def validate_trade_signal(signal):
            return signal

try:
    from service_manager import ServiceManager
except ImportError:
    print("Warning: ServiceManager not found, using mock")
    class ServiceManager:
        def __init__(self, config, logger):
            self.config = config
            self.logger = logger
            self.services = {}
            self.shutdown_requested_flag = False

        def register_service(self, name, service, health_check, critical=False):
            self.services[name] = {'service': service, 'health_check': health_check, 'critical': critical}

        def get_service(self, name):
            return self.services[name]['service']

        def get_service_health(self):
            return {"overall_healthy": True, "services": {}}

        def is_shutdown_requested(self):
            return self.shutdown_requested_flag

        def service_lifecycle(self):
            # Simple context manager
            class SimpleContext:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            return SimpleContext()

try:
    from health_monitor import EnhancedHealthMonitor
except ImportError:
    print("Warning: EnhancedHealthMonitor not found, using mock")
    class EnhancedHealthMonitor:
        def __init__(self, app_name, logger):
            self.app_name = app_name
            self.logger = logger

        async def start_background_health_checks(self):
            pass

        def get_fastapi_app(self):
            # Return minimal FastAPI app
            try:
                from fastapi import FastAPI
                app = FastAPI()

                @app.get("/health")
                async def health():
                    return {"status": "healthy", "app": self.app_name}

                return app
            except ImportError:
                return None

        async def shutdown(self):
            pass

# FastAPI and server imports
try:
    from fastapi import FastAPI
    import uvicorn
except ImportError:
    print("Warning: FastAPI/uvicorn not found, using simplified version")
    FastAPI = None
    uvicorn = None

# Global flag to indicate shutdown
shutdown_flag = False

# Placeholder for the Rust-based execution engine
class ExecutionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config.get("execution_engine", {})
        self.logger.info("Execution Engine (Placeholder) initialized.")

        # Initialize circuit breaker for execution engine
        self.circuit_breaker = CircuitBreaker(
            name="execution_engine",
            failure_threshold=3,
            recovery_timeout=120.0,
            logger=self.logger
        )

        # Initialize retry handler for transient failures
        self.retry_handler = RetryHandler(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0,
            logger=self.logger
        )

    @safe_execute("execution_engine", ErrorSeverity.HIGH)
    def execute_trade(self, trade_details: Dict[str, Any]):
        """Execute trade with comprehensive error handling."""
        # Validate trade details
        validated_signal = data_validator.validate_trade_signal(trade_details)

        self.logger.info("Executing trade", extra={'trade': trade_details})

        # Use circuit breaker and retry handler for execution
        def _execute():
            print(f"--- EXECUTION ENGINE ---")
            print(f"  Action: {validated_signal.action}")
            print(f"  Symbol: {validated_signal.symbol}")
            print(f"  Entry: {validated_signal.entry_price}")
            print(f"  Stop Loss: {validated_signal.stop_loss if hasattr(validated_signal, 'stop_loss') else 'N/A'}")
            print(f"  Take Profit: {validated_signal.take_profit if hasattr(validated_signal, 'take_profit') else 'N/A'}")
            print(f"------------------------")
            return True

        return self.circuit_breaker.call(
            lambda: self.retry_handler.call(_execute)
        )

def setup_logging(config: Dict[str, Any]):
    try:
        logging.config.dictConfig(config["logging"])
        sys.excepthook = handle_uncaught_exception
    except (ValueError, KeyError) as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger().critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def handle_shutdown_signal(signum, frame):
    global shutdown_flag
    if not shutdown_flag:
        logging.getLogger().info(f"Received shutdown signal: {signal.Signals(signum).name}. Initiating graceful shutdown...")
        shutdown_flag = True
    else:
        logging.getLogger().warning("Received second shutdown signal. Forcing exit.")
        sys.exit(1)

def load_config(config_path: str = "config.yaml"):
    """
    Load configuration using secure configuration loader with environment variable substitution.
    """
    try:
        # Try to load from .env file first, then fall back to system environment
        env_file = ".env"
        return load_secure_config(config_path, env_file)
    except FileNotFoundError:
        print(f"Configuration file not found at {config_path}, using test configuration")
        return load_secure_config(config_path, ".env")
    except Exception as e:
        print(f"Error loading configuration: {e}, using test configuration")
        return load_secure_config(config_path, ".env")

async def run_trading_agent(config: Dict[str, Any], service_manager: ServiceManager, logger: logging.Logger):
    """Run the main trading agent loop with enhanced service coordination."""

    # Get services from service manager
    data_processor = service_manager.get_service("data_processor")
    smc_detector = service_manager.get_service("smc_detector")
    decision_engine = service_manager.get_service("decision_engine")
    risk_manager = service_manager.get_service("risk_manager")
    execution_engine = service_manager.get_service("execution_engine")

    # Initialize circuit breakers and retry handlers for components
    data_circuit_breaker = CircuitBreaker("data_processor", 3, 60.0, logger)
    smc_circuit_breaker = CircuitBreaker("smc_detector", 3, 60.0, logger)
    decision_circuit_breaker = CircuitBreaker("decision_engine", 3, 60.0, logger)
    risk_circuit_breaker = CircuitBreaker("risk_manager", 3, 60.0, logger)

    data_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    smc_retry_handler = RetryHandler(2, 1.0, 10.0, logger)
    decision_retry_handler = RetryHandler(2, 1.0, 10.0, logger)
    risk_retry_handler = RetryHandler(2, 1.0, 10.0, logger)

    # Main application loop with comprehensive error handling
    cycle_count = 0
    max_cycles = 5  # Limit to 5 cycles for testing

    while not service_manager.is_shutdown_requested() and cycle_count < max_cycles:
        cycle_count += 1
        logger.info(f"Starting orchestration cycle #{cycle_count}")

        try:
            # Check system health before processing
            system_health = service_manager.get_service_health()
            if not system_health["overall_healthy"]:
                logger.warning("System health check failed, skipping cycle", extra=system_health)
                await asyncio.sleep(5)  # Wait before retry
                continue

            # 1. Get market data with error handling
            market_data_df = None
            try:
                market_data_df = data_circuit_breaker.call(
                    lambda: data_retry_handler.call(
                        data_processor.get_latest_ohlcv_data, "BTC/USDT", "1h"
                    )
                )

                # Validate market data quality
                is_valid, validation_errors = data_validator.validate_market_data(market_data_df)
                if not is_valid:
                    logger.error("Market data validation failed", extra={"errors": validation_errors})
                    continue

                quality_level = data_validator.assess_data_quality(market_data_df)
                if quality_level in [DataQualityLevel.POOR, DataQualityLevel.UNUSABLE]:
                    logger.warning(f"Market data quality is {quality_level.value}, skipping cycle")
                    continue

                logger.info("Market data received and validated.", extra={
                    'data_shape': market_data_df.shape,
                    'quality_level': quality_level.value
                })

            except Exception as e:
                logger.error(f"Failed to get market data: {str(e)}", exc_info=True)
                continue

            # 2. Analyze data for SMC patterns with error handling
            order_blocks = []
            try:
                order_blocks = smc_circuit_breaker.call(
                    lambda: smc_retry_handler.call(
                        smc_detector.detect_order_blocks, market_data_df
                    )
                )

                # Validate order blocks
                if order_blocks:
                    validated_blocks = data_validator.validate_order_blocks(order_blocks)
                    logger.info(f"Detected {len(validated_blocks)} valid order block(s).",
                              extra={'order_blocks': order_blocks})

            except Exception as e:
                logger.error(f"Failed to detect SMC patterns: {str(e)}", exc_info=True)
                continue

            # 3. Make a decision with error handling
            trade_signal = None
            if order_blocks:
                try:
                    trade_signal = decision_circuit_breaker.call(
                        lambda: decision_retry_handler.call(
                            decision_engine.make_decision, order_blocks, market_data_df
                        )
                    )

                    if trade_signal:
                        # Validate trade signal
                        validated_signal = data_validator.validate_trade_signal(trade_signal)

                        if validated_signal.confidence > config.get('decision_engine', {}).get('confidence_threshold', 0.7):
                            logger.info("Decision engine generated a high-confidence trade signal.",
                                      extra={'signal': trade_signal})

                            # 4. Apply risk management with error handling
                            stop_loss = None
                            take_profit = None
                            try:
                                stop_loss = risk_circuit_breaker.call(
                                    lambda: risk_retry_handler.call(
                                        risk_manager.calculate_stop_loss,
                                        validated_signal.entry_price,
                                        validated_signal.action,
                                        order_blocks,
                                        {} # structure placeholder
                                    )
                                )
                                take_profit = risk_circuit_breaker.call(
                                    lambda: risk_retry_handler.call(
                                        risk_manager.calculate_take_profit,
                                        validated_signal.entry_price,
                                        stop_loss,
                                        validated_signal.action
                                    )
                                )

                            except Exception as e:
                                logger.error(f"Risk management calculation failed: {str(e)}", exc_info=True)
                                continue

                            # 5. Execute the trade with error handling
                            try:
                                final_trade = {
                                    **trade_signal,
                                    "stop_loss": stop_loss,
                                    "take_profit": take_profit
                                }
                                execution_engine.execute_trade(final_trade)

                            except Exception as e:
                                logger.error(f"Trade execution failed: {str(e)}", exc_info=True)
                                continue

                        elif trade_signal:
                            logger.info("Trade signal confidence below threshold, no action taken.",
                                      extra={'signal': trade_signal})

                except Exception as e:
                    logger.error(f"Decision engine failed: {str(e)}", exc_info=True)
                    continue
            else:
                logger.info("No significant SMC patterns detected in this cycle.")

        except Exception as e:
            logger.error(f"Unexpected error in orchestration cycle: {str(e)}", exc_info=True)
            continue

        logger.info(f"Orchestration cycle {cycle_count} complete. Waiting for next interval.")
        try:
            # Sleep for 10 seconds between cycles (reduced for testing)
            for _ in range(10):
                if service_manager.is_shutdown_requested():
                    break
                await asyncio.sleep(1)
        except InterruptedError:
            break

    logger.info(f"SMC Trading Agent has completed {cycle_count} cycles and shut down gracefully.")

async def main_async():
    """Async main function with enhanced service coordination."""

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

    logger.info("🚀 Initializing SMC Trading Agent with Enhanced Service Coordination...", extra=config.get('app', {}))
    logger.info("🤖 Swarm Coordinated Trading System - ACTIVE")
    logger.info("📊 Specialized Agents: Data Pipeline, SMC Detector, Decision Engine, Risk Manager, Execution Engine")

    # Initialize service manager
    service_manager = ServiceManager(config, logger)

    # Initialize enhanced health monitor
    health_monitor = EnhancedHealthMonitor(
        app_name=config.get('app', {}).get('name', 'smc-trading-agent'),
        logger=logger
    )

    # Initialize all services with error handling
    try:
        data_processor = MarketDataProcessor()
        smc_detector = SMCIndicators()
        decision_engine = AdaptiveModelSelector()
        risk_manager = SMCRiskManager()
        execution_engine = ExecutionEngine(config)

        # Register services with service manager
        service_manager.register_service("data_processor", data_processor, lambda: True, critical=True)
        service_manager.register_service("smc_detector", smc_detector, lambda: True, critical=True)
        service_manager.register_service("decision_engine", decision_engine, lambda: True, critical=True)
        service_manager.register_service("risk_manager", risk_manager, lambda: True, critical=True)
        service_manager.register_service("execution_engine", execution_engine, lambda: True, critical=True)

        logger.info("✅ All services registered successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        return 1

    # Start health monitoring
    await health_monitor.start_background_health_checks()

    # Get monitoring port from config
    monitoring_port = config.get('monitoring', {}).get('port', 8008)

    # Create FastAPI app for health monitoring
    app = health_monitor.get_fastapi_app()

    if app and uvicorn:
        # Start health monitoring server
        config_uvicorn = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=monitoring_port,
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)

        # Run trading agent and health monitoring concurrently
        try:
            async with service_manager.service_lifecycle():
                # Start health monitoring server in background
                server_task = asyncio.create_task(server.serve())
                logger.info(f"🌐 Health monitoring server started on http://localhost:{monitoring_port}")

                # Run trading agent
                trading_task = asyncio.create_task(
                    run_trading_agent(config, service_manager, logger)
                )

                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [server_task, trading_task],
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
            logger.error(f"Service lifecycle failed: {e}", exc_info=True)
            return 1
        finally:
            # Shutdown health monitor
            await health_monitor.shutdown()
    else:
        # Run without health monitoring server
        logger.warning("FastAPI/uvicorn not available, running without health monitoring server")
        try:
            await run_trading_agent(config, service_manager, logger)
        except Exception as e:
            logger.error(f"Trading agent failed: {e}", exc_info=True)
            return 1

    return 0

def main():
    """Main entry point with signal handling."""
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
    print("🤖 SMC Trading Agent - Swarm Coordinated System")
    print("=" * 60)
    print("🚀 Initializing with specialized AI agents...")
    print("📊 Hierarchical topology: Coordinators → Specialists → Workers")
    print("🛡️ Risk Management: Circuit breakers, validation, error handling")
    print("=" * 60)

    exit_code = main()
    print("=" * 60)
    if exit_code == 0:
        print("✅ Trading agent completed successfully!")
    else:
        print(f"❌ Trading agent exited with code {exit_code}")
    print("=" * 60)
    sys.exit(exit_code)