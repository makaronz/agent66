"""
FastAPI application for SMC Trading Agent
Provides comprehensive OpenAPI documentation and trading engine endpoints
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import logging

# This would be your actual ServiceManager instance, passed around
# For now, we'll use a mock placeholder.
class MockServiceManager:
    def get_service(self, name):
        # Return a mock service
        class MockService:
            def __getattr__(self, item):
                def wrapper(*args, **kwargs):
                    logging.info(f"Mock service '{name}' method '{item}' called.")
                    return {}
                return wrapper
        return MockService()

service_manager = MockServiceManager()

def get_sm():
    return service_manager

app = FastAPI(
    title="SMC Trading Agent API - Offline Mode",
    description="API for the SMC Trading Agent, running in a local, offline configuration.",
    version="1.0.0-offline"
)

class TradeSignal(BaseModel):
    symbol: str
    action: str # e.g., 'buy', 'sell'
    size: float

@app.get("/health", tags=["Health"])
async def health_check():
    """Check the health of the API."""
    return {"status": "ok"}

@app.get("/status/services", tags=["Status"])
async def get_services_status(sm: MockServiceManager = Depends(get_sm)):
    """Get the status of all running services."""
    # In a real implementation, this would query the HealthMonitor
    return {"data_ingestion": "healthy", "risk_manager": "healthy"}

@app.post("/trade/execute", tags=["Trading"])
async def execute_trade(signal: TradeSignal, sm: MockServiceManager = Depends(get_sm)):
    """Execute a trade manually."""
    risk_manager = sm.get_service('risk_manager')
    is_safe, message = risk_manager.assess_trade_risk(signal.symbol, signal.size, 0, 0, 0)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Risk check failed: {message}")
    
    execution_engine = sm.get_service('execution_engine')
    result = execution_engine.execute_trade(signal.dict())
    return {"message": "Trade execution initiated", "details": result}

@app.get("/risk/limits", tags=["Risk"])
async def get_risk_limits(sm: MockServiceManager = Depends(get_sm)):
    """Get the current risk limits."""
    risk_manager = sm.get_service('risk_manager')
    return risk_manager.risk_config

# Add other endpoints as needed for offline analysis and control
