import sys
import signal
import logging
import logging.config
import time
import asyncio
from typing import Dict, Any, Optional

# Secure configuration loading
from config_loader import load_secure_config, ConfigValidationError, EnvironmentVariableError
from config_validator import validate_config

# Component Imports
from data_pipeline.live_data_client import LiveDataClient  # CHANGED: Live data instead of mock
from smc_detector.indicators import SMCIndicators
from decision_engine.simple_heuristic import SimpleSMCHeuristic as AdaptiveModelSelector
from risk_manager.smc_risk_manager import SMCRiskManager
from execution_engine.paper_trading import PaperTradingEngine  # ADDED: Paper trading engine

# Error handling and validation imports
from error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)
from validators import (
    data_validator, DataQualityLevel, DataValidationError
)

# New service coordination and health monitoring
from service_manager import ServiceManager
from health_monitor import EnhancedHealthMonitor

# FastAPI and server imports
from fastapi import FastAPI
import uvicorn

# Global flag to indicate shutdown
shutdown_flag = False

# REMOVED: Placeholder ExecutionEngine - replaced with PaperTradingEngine
# See execution_engine/paper_trading.py for full implementation

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

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
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
    smc_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    decision_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)
    risk_retry_handler = RetryHandler(2, 1.0, 10.0, logger=logger)

    # Main application loop with comprehensive error handling
    while not service_manager.is_shutdown_requested():
        logger.info("Starting new orchestration cycle.")
        
        try:
            # Check system health before processing
            system_health = service_manager.get_service_health()
            if not system_health["overall_healthy"]:
                logger.warning("System health check failed, skipping cycle", extra=system_health)
                await asyncio.sleep(30)  # Wait before retry
                continue
            
            # 1. Get market data with error handling (LIVE DATA via REST API)
            market_data_df = None
            try:
                # CHANGED: Async call to LiveDataClient
                market_data_df = await data_processor.get_latest_ohlcv_data("BTC/USDT", "1h")
                
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

            # 3. Make a decision - SIMPLIFIED HEURISTIC (no ML for v1)
            trade_signal = None
            if order_blocks:
                try:
                    # SIMPLE SMC HEURISTIC: Use latest order block direction
                    latest_ob = order_blocks[0]
                    
                    # Determine direction from order block
                    ob_direction = latest_ob.get('direction') or latest_ob.get('type')
                    
                    if ob_direction in ['bullish', 'BULLISH']:
                        trade_signal = {
                            "action": "BUY",
                            "symbol": "BTC/USDT",
                            "entry_price": latest_ob['price_level'][0] if isinstance(latest_ob['price_level'], tuple) else latest_ob['price_level'],
                            "confidence": min(0.75 + latest_ob.get('strength', 0) * 0.2, 0.95)
                        }
                    elif ob_direction in ['bearish', 'BEARISH']:
                        trade_signal = {
                            "action": "SELL",
                            "symbol": "BTC/USDT",
                            "entry_price": latest_ob['price_level'][1] if isinstance(latest_ob['price_level'], tuple) else latest_ob['price_level'],
                            "confidence": min(0.75 + latest_ob.get('strength', 0) * 0.2, 0.95)
                        }
                    
                    if trade_signal:
                        # Validate trade signal
                        validated_signal = data_validator.validate_trade_signal(trade_signal)
                        
                        confidence_threshold = config.get('decision_engine', {}).get('confidence_threshold', 0.7)
                        if validated_signal.confidence > confidence_threshold:
                            logger.info(
                                f"🎯 SIMPLE SMC HEURISTIC: {trade_signal['action']} signal generated "
                                f"(confidence: {validated_signal.confidence:.2%}, direction: {ob_direction})", 
                                extra={'signal': trade_signal}
                            )
                            
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

                            # 5. Execute the paper trade
                            try:
                                # Calculate position size with risk validation
                                account_summary = execution_engine.get_account_summary()
                                initial_position_size = account_summary['balance'] * 0.01 / validated_signal.entry_price
                                
                                # Validate and adjust position size if needed
                                size_validation = risk_manager.validate_position_size(
                                    symbol=validated_signal.symbol,
                                    size=initial_position_size,
                                    price=validated_signal.entry_price,
                                    balance=account_summary['balance'],
                                    max_risk_percent=0.02
                                )
                                
                                if size_validation['adjusted']:
                                    position_size = size_validation['adjusted_size']
                                    logger.warning(
                                        f"Position size adjusted: {size_validation['reason']}"
                                    )
                                else:
                                    position_size = initial_position_size
                                
                                # Check daily loss limit before trading
                                if not risk_manager.check_daily_loss_limit(risk_manager.daily_pnl):
                                    logger.critical("🚨 Trading halted: Daily loss limit reached")
                                    continue
                                
                                # Execute paper order
                                paper_trade = execution_engine.execute_order(
                                    symbol=validated_signal.symbol,
                                    side=validated_signal.action,
                                    size=position_size,
                                    price=validated_signal.entry_price,
                                    stop_loss=stop_loss,
                                    take_profit=take_profit,
                                    reason=f"SMC pattern detected with {validated_signal.confidence:.2%} confidence"
                                )
                                
                                if paper_trade:
                                    logger.info("✅ Paper trade executed successfully", extra={'trade': paper_trade.dict()})
                                else:
                                    logger.warning("⚠️ Paper trade rejected by engine")
                                
                            except Exception as e:
                                logger.error(f"Trade execution failed: {str(e)}", exc_info=True)
                                continue
                                
                        else:
                            logger.info(
                                f"Trade signal confidence below threshold "
                                f"({validated_signal.confidence:.2%} < {confidence_threshold:.2%}), no action taken.", 
                                extra={'signal': trade_signal}
                            )
                            
                except Exception as e:
                    logger.error(f"Decision engine failed: {str(e)}", exc_info=True)
                    continue
            else:
                logger.info("No significant SMC patterns detected in this cycle.")
            
            # 6. Update open positions with live prices (check SL/TP)
            if execution_engine.positions:
                try:
                    # Get live prices for all open positions
                    live_prices = {}
                    for symbol in execution_engine.positions.keys():
                        symbol_data = await data_processor.get_latest_ohlcv_data(symbol, "1h", limit=1)
                        if symbol_data is not None and not symbol_data.empty:
                            live_prices[symbol] = symbol_data['close'].iloc[-1]
                    
                    # Update positions and check stop loss / take profit
                    execution_engine.update_positions(live_prices)
                    
                except Exception as e:
                    logger.error(f"Failed to update positions: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Unexpected error in orchestration cycle: {str(e)}", exc_info=True)
            continue

        logger.info("Orchestration cycle complete. Waiting for next interval.")
        try:
            # Sleep for 1 minute before the next cycle
            for _ in range(60):
                if service_manager.is_shutdown_requested():
                    break
                await asyncio.sleep(1)
        except InterruptedError:
            break

    logger.info("SMC Trading Agent has shut down gracefully.")

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

    logger.info("Initializing SMC Trading Agent with enhanced service coordination...", extra=config.get('app', {}))

    # Initialize service manager
    service_manager = ServiceManager(config, logger)
    
    # Initialize enhanced health monitor
    health_monitor = EnhancedHealthMonitor(
        app_name=config.get('app', {}).get('name', 'smc-trading-agent'),
        logger=logger
    )
    
    # Initialize all services with error handling
    try:
        # CHANGED: Use LiveDataClient instead of mock MarketDataProcessor
        data_processor = LiveDataClient(base_url="http://localhost:3001")
        smc_detector = SMCIndicators()
        decision_engine = AdaptiveModelSelector()
        
        # Initialize risk manager with config
        risk_config = config.get('risk_manager', {})
        risk_manager = SMCRiskManager(config=risk_config)
        
        # CHANGED: Use PaperTradingEngine instead of placeholder
        # Get trading mode from config (default: paper)
        trading_mode = config.get('app', {}).get('mode', 'paper')
        initial_balance = config.get('paper_trading', {}).get('initial_balance', 10000.0)
        execution_engine = PaperTradingEngine(initial_balance=initial_balance)
        logger.info(f"Trading mode: {trading_mode.upper()} with ${initial_balance:.2f} balance")
        
        # Register services with service manager
        service_manager.register_service("data_processor", data_processor, lambda: True, critical=True)
        service_manager.register_service("smc_detector", smc_detector, lambda: True, critical=True)
        service_manager.register_service("decision_engine", decision_engine, lambda: True, critical=True)
        service_manager.register_service("risk_manager", risk_manager, lambda: True, critical=True)
        service_manager.register_service("execution_engine", execution_engine, lambda: True, critical=True)
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        return 1

    # Start health monitoring
    await health_monitor.start_background_health_checks()
    
    # Get monitoring port from config
    monitoring_port = config.get('monitoring', {}).get('port', 8008)
    
    # Create FastAPI app for health monitoring
    app = health_monitor.get_fastapi_app()
    
    # Add paper trading API endpoints
    @app.get("/api/python/paper-trades")
    async def get_paper_trades():
        """Get paper trading history."""
        try:
            trades = execution_engine.get_trade_history(limit=50)
            return {"success": True, "data": trades}
        except Exception as e:
            logger.error(f"Failed to get paper trades: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @app.get("/api/python/positions")
    async def get_positions():
        """Get open positions."""
        try:
            positions = execution_engine.get_open_positions()
            return {"success": True, "data": positions}
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @app.get("/api/python/account")
    async def get_account():
        """Get account summary."""
        try:
            summary = execution_engine.get_account_summary()
            return {"success": True, "data": summary}
        except Exception as e:
            logger.error(f"Failed to get account summary: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
    sys.exit(main())
