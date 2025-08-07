import sys
import signal
import logging
import logging.config
import time
from typing import Dict, Any, Optional

# Secure configuration loading
from smc_trading_agent.config_loader import load_secure_config, ConfigValidationError, EnvironmentVariableError
from smc_trading_agent.config_validator import validate_config

# Component Imports
from smc_trading_agent.data_pipeline.ingestion import MarketDataProcessor
from smc_trading_agent.smc_detector.indicators import SMCIndicators
from smc_trading_agent.decision_engine.model_ensemble import AdaptiveModelSelector
from smc_trading_agent.risk_manager.smc_risk_manager import SMCRiskManager

# Error handling and validation imports
from smc_trading_agent.error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)
from smc_trading_agent.validators import (
    data_validator, DataQualityLevel, DataValidationError
)

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
            print(f"  Stop Loss: {validated_signal.stop_loss}")
            print(f"  Take Profit: {validated_signal.take_profit}")
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
        sys.exit(1)

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

def load_config(config_path: str = "smc_trading_agent/config.yaml") -> Dict[str, Any]:
    """
    Load configuration using secure configuration loader with environment variable substitution.
    
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
        print("You can create a .env file with the following variables:", file=sys.stderr)
        print("  BINANCE_API_KEY=your_api_key_here", file=sys.stderr)
        print("  BINANCE_API_SECRET=your_api_secret_here", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    config = load_config()
    
    # Validate configuration
    is_valid, errors, warnings = validate_config(config)
    if not is_valid:
        logger.error("Configuration validation failed")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    
    if warnings:
        logger.warning("Configuration validation completed with warnings")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("Initializing SMC Trading Agent services...", extra=config.get('app', {}))

    # Initialize all services with error handling
    try:
        data_processor = MarketDataProcessor()
        smc_detector = SMCIndicators()
        decision_engine = AdaptiveModelSelector()
        risk_manager = SMCRiskManager()
        execution_engine = ExecutionEngine(config)
        
        # Register components for health monitoring
        health_monitor.register_component("data_processor", lambda: True, critical=True)
        health_monitor.register_component("smc_detector", lambda: True, critical=True)
        health_monitor.register_component("decision_engine", lambda: True, critical=True)
        health_monitor.register_component("risk_manager", lambda: True, critical=True)
        health_monitor.register_component("execution_engine", lambda: True, critical=True)
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        return 1

    logger.info("All services initialized. Starting main application loop.")

    # Initialize circuit breakers and retry handlers for components
    data_circuit_breaker = CircuitBreaker("data_processor", 3, 60.0, logger)
    smc_circuit_breaker = CircuitBreaker("smc_detector", 3, 60.0, logger)
    decision_circuit_breaker = CircuitBreaker("decision_engine", 3, 60.0, logger)
    risk_circuit_breaker = CircuitBreaker("risk_manager", 3, 60.0, logger)
    
    data_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    smc_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    decision_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    risk_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)

    # Main application loop with comprehensive error handling
    while not shutdown_flag:
        logger.info("Starting new orchestration cycle.")
        
        try:
            # Check system health before processing
            system_health = health_monitor.get_system_health()
            if not system_health["overall_healthy"]:
                logger.warning("System health check failed, skipping cycle", extra=system_health)
                time.sleep(30)  # Wait before retry
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

        logger.info("Orchestration cycle complete. Waiting for next interval.")
        try:
            # Sleep for 1 minute before the next cycle
            for _ in range(60):
                if shutdown_flag:
                    break
                time.sleep(1)
        except InterruptedError:
            break

    logger.info("SMC Trading Agent has shut down gracefully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
