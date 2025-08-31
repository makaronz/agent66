import asyncio
import argparse
import logging
import logging.config
import sys
import signal
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config_loader import SecureConfigLoader
from service_manager import ServiceManager
from health_monitor import HealthMonitor

# Import the new offline-first components
from database.connection_pool import initialize_pool, close_all_connections
from compliance.mifid_reporting import ComplianceEngine
from interfaces import MarketBatch, Decisions, Orders
from providers.mock import (
    MockDataFeed, MockAnalyzer, MockDecisionEngine, MockExecutorClient, MockRiskManager
)
from providers.real import (
    RealDataFeed, RealAnalyzer, RealDecisionEngine, RealExecutorClient, RealRiskManager
)

# Mock components for offline development
class MockDataIngestion:
    async def get_latest_ohlcv_data(self, *args, **kwargs):
        logging.info("MockDataIngestion: Returning mock data.")
        # In a real scenario, this would load data from a local file
        return {}
    # Compatibility with trading loop
    async def get_latest_data(self, *args, **kwargs):
        return await self.get_latest_ohlcv_data(*args, **kwargs)

class MockSMCIndicators:
    def detect_order_blocks(self, *args, **kwargs):
        logging.info("MockSMCIndicators: Returning mock order blocks.")
        return []
    async def analyze(self, *args, **kwargs):
        logging.info("MockSMCIndicators: analyze() -> []")
        return []

class MockAdaptiveModelSelector:
    def make_decision(self, *args, **kwargs):
        logging.info("MockAdaptiveModelSelector: No decision made.")
        return None
    async def process(self, *args, **kwargs):
        logging.info("MockAdaptiveModelSelector: process() -> []")
        return []

class MockExecutionEngine:
    def execute_trade(self, trade_details):
        logging.info(f"MockExecutionEngine: Executing trade: {trade_details}")
    async def execute(self, decisions):
        logging.info(f"MockExecutionEngine: execute() called with: {decisions}")

class MockRiskManager:
    async def assess(self, decisions):
        logging.info("MockRiskManager: assess() passthrough")
        return decisions

# Global application state
shutdown_flag = False
app_start_time = None
health_status = {
    'status': 'starting',
    'services': {},
    'last_check': None,
    'uptime': 0,
    'errors': [],
    'connection_status': {
        'database': False,
        'exchanges': {},
        'monitoring': False
    }
}

def setup_logging(config):
    try:
        logging.config.dictConfig(config['logging'])
        logging.info("Logging configured successfully.")
    except (ValueError, KeyError) as e:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        logging.warning(f"Failed to configure logging from config: {e}. Using basic config.")

def handle_shutdown_signal(signum, frame):
    global shutdown_flag
    if not shutdown_flag:
        logging.info(f"Received shutdown signal: {signal.Signals(signum).name}. Initiating graceful shutdown...")
        shutdown_flag = True
        health_status['status'] = 'shutting_down'

async def check_service_health(service_manager: ServiceManager) -> Dict[str, Any]:
    """Check health of all registered services."""
    logger = logging.getLogger(__name__)
    service_health = {}
    
    try:
        for service_name in ['data_feed', 'analyzer', 'decision_engine', 'executor', 'risk_manager']:
            try:
                service = service_manager.get_service(service_name)
                if service:
                    # Basic health check - service exists and is callable
                    if hasattr(service, 'health_check'):
                        is_healthy = await service.health_check() if asyncio.iscoroutinefunction(service.health_check) else service.health_check()
                    else:
                        is_healthy = True  # Assume healthy if no explicit health check
                    
                    service_health[service_name] = {
                        'status': 'healthy' if is_healthy else 'unhealthy',
                        'last_check': datetime.now().isoformat()
                    }
                else:
                    service_health[service_name] = {
                        'status': 'not_found',
                        'last_check': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                service_health[service_name] = {
                    'status': 'error',
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
    except Exception as e:
        logger.error(f"Service health check failed: {e}")
        
    return service_health

async def check_database_connection() -> bool:
    """Check database connection health."""
    try:
        # Import here to avoid circular imports
        from database.connection_pool import get_connection
        
        async with get_connection() as conn:
            # Simple query to test connection
            await conn.execute("SELECT 1")
            return True
    except Exception as e:
        logging.getLogger(__name__).warning(f"Database health check failed: {e}")
        return False

async def update_health_status(service_manager: ServiceManager):
    """Update global health status."""
    global health_status, app_start_time
    
    try:
        # Update uptime
        if app_start_time:
            health_status['uptime'] = int((datetime.now() - app_start_time).total_seconds())
        
        # Check services
        health_status['services'] = await check_service_health(service_manager)
        
        # Check database
        health_status['connection_status']['database'] = await check_database_connection()
        
        # Update monitoring status
        health_status['connection_status']['monitoring'] = True  # If we can update, monitoring is working
        
        # Determine overall status
        all_services_healthy = all(
            service.get('status') == 'healthy' 
            for service in health_status['services'].values()
        )
        
        if shutdown_flag:
            health_status['status'] = 'shutting_down'
        elif all_services_healthy and health_status['connection_status']['database']:
            health_status['status'] = 'healthy'
        else:
            health_status['status'] = 'degraded'
            
        health_status['last_check'] = datetime.now().isoformat()
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to update health status: {e}")
        health_status['status'] = 'error'
        health_status['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        })
        
        # Keep only last 10 errors
        health_status['errors'] = health_status['errors'][-10:]

def create_health_app(service_manager: ServiceManager) -> FastAPI:
    """Create FastAPI app with health endpoints."""
    app = FastAPI(title="SMC Trading Agent Health Monitor", version="1.0.0")
    
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return JSONResponse(
            status_code=200 if health_status['status'] in ['healthy', 'degraded'] else 503,
            content={
                'status': health_status['status'],
                'timestamp': datetime.now().isoformat(),
                'uptime': health_status['uptime']
            }
        )
    
    @app.get("/health/detailed")
    async def detailed_health():
        """Detailed health status with all components."""
        return JSONResponse(
            status_code=200 if health_status['status'] != 'error' else 503,
            content=health_status
        )
    
    @app.get("/health/services")
    async def services_health():
        """Service-specific health status."""
        return JSONResponse(content=health_status['services'])
    
    @app.get("/health/connections")
    async def connections_health():
        """Connection status for external dependencies."""
        return JSONResponse(content=health_status['connection_status'])
    
    @app.get("/metrics")
    async def metrics():
        """Basic metrics endpoint."""
        return JSONResponse(content={
            'uptime_seconds': health_status['uptime'],
            'start_time': app_start_time.isoformat() if app_start_time else None,
            'status': health_status['status'],
            'service_count': len(health_status['services']),
            'healthy_services': sum(1 for s in health_status['services'].values() if s.get('status') == 'healthy'),
            'error_count': len(health_status['errors'])
        })
    
    @app.get("/readiness")
    @app.get("/ready")
    async def readiness():
        status = 200 if service_manager.is_ready() else 503
        return JSONResponse(status_code=status, content={
            'ready': service_manager.is_ready(),
            'timestamp': datetime.now().isoformat()
        })

    return app

async def start_health_server(health_app: FastAPI):
    """Start the health monitoring server with the provided FastAPI app."""
    import uvicorn
    
    config = uvicorn.Config(health_app, host="0.0.0.0", port=8001, log_level="info")
    server = uvicorn.Server(config)
    
    # Start server in background
    import asyncio
    asyncio.create_task(server.serve())
    
    logging.info("Health monitoring server started on http://0.0.0.0:8001")
    logging.info("Available endpoints:")
    logging.info("  - GET /health - Basic health check")
    logging.info("  - GET /health/detailed - Detailed health status")
    logging.info("  - GET /health/services - Service health status")
    logging.info("  - GET /health/connections - Connection status")
    logging.info("  - GET /metrics - Basic metrics")
    
    return server

async def trading_loop(service_manager):
    """Main trading loop with proper error handling and shutdown management."""
    logger = logging.getLogger(__name__)
    
    while not shutdown_flag:
        try:
            # Get market data
            market_data = await service_manager.get_service('data_feed').get_latest_data()
            
            if market_data:
                # Detect SMC patterns
                smc_signals = await service_manager.get_service('analyzer').analyze(market_data)
                
                if smc_signals:
                    # Make trading decisions -> orders
                    orders = await service_manager.get_service('decision_engine').process(smc_signals)
                    # Execute trades
                    exec_report = await service_manager.get_service('executor').execute(orders)
                    # Assess risk from execution
                    _ = await service_manager.get_service('risk_manager').assess(exec_report)
            
            # Sleep for a short interval before next iteration
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            await asyncio.sleep(5)  # Wait longer on error
    
    logger.info("Trading loop stopped.")

async def trading_loop_with_health_monitoring(service_manager):
    """Trading loop with integrated health monitoring."""
    logger = logging.getLogger(__name__)
    last_health_check = datetime.now()
    health_check_interval = timedelta(seconds=30)  # Check health every 30 seconds
    
    while not shutdown_flag:
        try:
            # Periodic health check
            current_time = datetime.now()
            if current_time - last_health_check >= health_check_interval:
                await update_health_status(service_manager)
                last_health_check = current_time
            
            # Get market data
            market_data = await service_manager.get_service('data_feed').get_latest_data()
            
            if market_data:
                # Detect SMC patterns
                smc_signals = await service_manager.get_service('analyzer').analyze(market_data)
                
                if smc_signals:
                    # Make trading decisions -> orders
                    orders = await service_manager.get_service('decision_engine').process(smc_signals)
                    # Execute trades
                    exec_report = await service_manager.get_service('executor').execute(orders)
                    # Assess risk
                    _ = await service_manager.get_service('risk_manager').assess(exec_report)
            
            # Sleep for a short interval before next iteration
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            # Update health status on error
            health_status['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': f"Trading loop error: {str(e)}"
            })
            health_status['errors'] = health_status['errors'][-10:]  # Keep only last 10 errors
            await asyncio.sleep(5)  # Wait longer on error
    
    logger.info("Trading loop with health monitoring stopped.")

async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "online"], default="offline")
    parser.add_argument("--exchange", choices=["binance"], default="binance")
    args, _ = parser.parse_known_args()
    
    # Load configuration
    config_loader = SecureConfigLoader(env_file=".env")
    try:
        config = config_loader.load_config("config.yaml")
    except FileNotFoundError as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Configuration error: {e}")
        return 1

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # Initialize database pool for offline use
    db_path = config.get('database', {}).get('name', 'data/smc_agent_offline.db')
    max_connections = config.get('database', {}).get('pool_size', 5)
    import os
    db_dir = os.path.dirname(db_path)
    if not db_dir:
        # Treat provided name as logical name; store under data/ with .db suffix
        fname = db_path if db_path.endswith('.db') else f"{db_path}.db"
        db_path = os.path.join('data', fname)
        db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    initialize_pool(db_path, max_connections)
    logger.info(f"Offline database pool initialized with SQLite: {db_path}")

    # Initialize services
    service_manager = ServiceManager(config, logger)
    health_monitor = HealthMonitor(config.get('monitoring', {}))

    try:
        if args.mode == "online":
            service_manager.register_service("data_feed", RealDataFeed(config), lambda: True)
            real_analyzer = RealAnalyzer(config)
            service_manager.register_service("analyzer", real_analyzer, getattr(real_analyzer, "warm_up", None))
            service_manager.register_service("decision_engine", RealDecisionEngine(config), lambda: True)
            # Choose exchange-specific executor
            if args.exchange == "binance":
                from providers.binance import BinanceExecutorClient
                exec_client = BinanceExecutorClient(config)
                service_manager.register_service("executor", exec_client, getattr(exec_client, "ready", None) or (lambda: True))
            else:
                service_manager.register_service("executor", RealExecutorClient(config), lambda: True)
            service_manager.register_service("risk_manager", RealRiskManager(config), lambda: True)
        else:
            service_manager.register_service("data_feed", MockDataFeed(), lambda: True)
            service_manager.register_service("analyzer", MockAnalyzer(), lambda: True)
            service_manager.register_service("decision_engine", MockDecisionEngine(), lambda: True)
            service_manager.register_service("executor", MockExecutorClient(), lambda: True)
            service_manager.register_service("risk_manager", MockRiskManager(), lambda: True)
        service_manager.register_service("mifid_reporter", ComplianceEngine(), lambda: True)

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        return 1

    # Start health monitoring server
    health_app = create_health_app(service_manager)
    monitoring_port = config.get('monitoring', {}).get('port', 8008)
    server_config = uvicorn.Config(health_app, host="0.0.0.0", port=monitoring_port, log_level="info")
    server = uvicorn.Server(server_config)
    server_task = asyncio.create_task(server.serve())

    # Ensure readiness after service registration
    await service_manager.initialize_services(use_mock=(args.mode == "offline"))
    
    # Start the main trading loop
    trading_task = asyncio.create_task(trading_loop(service_manager))

    logger.info("SMC Trading Agent started in offline mode.")

    # Wait for shutdown signal
    while not shutdown_flag:
        await asyncio.sleep(1)

    # Graceful shutdown
    logger.info("Shutting down services...")
    trading_task.cancel()
    server.should_exit = True
    server_task.cancel()

    try:
        await trading_task
        await server_task
    except asyncio.CancelledError:
        pass # Expected on shutdown

    close_all_connections()
    logger.info("Database connections closed. Shutdown complete.")
    return 0

async def main():
    global shutdown_flag, app_start_time, health_status
    
    # Initialize app start time
    app_start_time = datetime.now()
    health_status['status'] = 'starting'
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    logging.info("Starting SMC Trading Agent...")
    
    try:
        # Initialize configuration
        config_loader = SecureConfigLoader(env_file=".env")
        config = config_loader.load_config("config.yaml")
        health_status['status'] = 'initializing'
        
        # Initialize service manager
        service_manager = ServiceManager(config, logging.getLogger(__name__))
        
        # Initialize services with mock components for offline mode
        await service_manager.initialize_services(use_mock=True)
        health_status['status'] = 'services_initialized'
        
        # Perform initial health check
        await update_health_status(service_manager)
        
        # Start health monitoring server
        health_app = create_health_app(service_manager)
        health_server = await start_health_server(health_app)
        
        # Mark as running
        health_status['status'] = 'running'
        logging.info("SMC Trading Agent is now running and healthy")
        
        # Start main trading loop with periodic health updates
        await trading_loop_with_health_monitoring(service_manager)
        
    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        health_status['status'] = 'error'
        health_status['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': f"Critical startup error: {str(e)}"
        })
        raise
    finally:
        logging.info("Shutting down SMC Trading Agent...")
        health_status['status'] = 'shutting_down'
        
        if 'service_manager' in locals():
            await service_manager.shutdown()
        if 'health_server' in locals():
            health_server.should_exit = True
            
        health_status['status'] = 'stopped'

def main_sync():
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        # Use CLI-enabled async entry
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received.")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main_sync())
