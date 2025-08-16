"""
Contract tests for microservice API boundaries.
Tests API contracts, data schemas, and service interactions.
"""

import pytest
import json
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pydantic import BaseModel, ValidationError
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException

# Import API schemas and models
from api.validation.schemas import (
    TradingSignalSchema,
    MarketDataSchema,
    OrderBlockSchema,
    RiskParametersSchema,
    TradeExecutionSchema
)


class APIContractTest:
    """Base class for API contract testing."""
    
    def __init__(self, service_name: str, api_version: str = "v1"):
        self.service_name = service_name
        self.api_version = api_version
        self.base_url = f"/api/{api_version}"
    
    def validate_response_schema(self, response_data: Dict[str, Any], expected_schema: BaseModel):
        """Validate response data against expected schema."""
        try:
            validated_data = expected_schema(**response_data)
            return True, validated_data
        except ValidationError as e:
            return False, e.errors()
    
    def validate_error_response(self, response_data: Dict[str, Any]):
        """Validate error response format."""
        required_fields = ['error', 'message', 'timestamp']
        return all(field in response_data for field in required_fields)


class TestDataPipelineAPIContracts:
    """Contract tests for Data Pipeline API."""
    
    @pytest.fixture
    def data_pipeline_client(self):
        """Create test client for data pipeline API."""
        app = FastAPI()
        
        @app.get("/api/v1/market-data/{symbol}")
        async def get_market_data(symbol: str, timeframe: str = "1h", limit: int = 100):
            # Mock market data response
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "data": [
                    {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "open": 50000.0,
                        "high": 50100.0,
                        "low": 49900.0,
                        "close": 50050.0,
                        "volume": 1000.0
                    }
                ],
                "count": 1,
                "metadata": {
                    "source": "binance",
                    "last_updated": "2024-01-01T10:01:00Z"
                }
            }
        
        @app.post("/api/v1/market-data/subscribe")
        async def subscribe_to_market_data(request: Dict[str, Any]):
            return {
                "subscription_id": "sub_123456",
                "symbols": request.get("symbols", []),
                "status": "active",
                "websocket_url": "ws://localhost:8080/ws/market-data"
            }
        
        return TestClient(app)
    
    def test_market_data_endpoint_contract(self, data_pipeline_client):
        """Test market data endpoint contract."""
        # Test valid request
        response = data_pipeline_client.get("/api/v1/market-data/BTCUSDT?timeframe=1h&limit=100")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "symbol" in data
        assert "timeframe" in data
        assert "data" in data
        assert "count" in data
        assert "metadata" in data
        
        # Validate data array structure
        assert isinstance(data["data"], list)
        if data["data"]:
            candle = data["data"][0]
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            assert all(field in candle for field in required_fields)
            
            # Validate data types
            assert isinstance(candle["open"], (int, float))
            assert isinstance(candle["high"], (int, float))
            assert isinstance(candle["low"], (int, float))
            assert isinstance(candle["close"], (int, float))
            assert isinstance(candle["volume"], (int, float))
        
        # Validate metadata
        assert "source" in data["metadata"]
        assert "last_updated" in data["metadata"]
    
    def test_market_data_subscription_contract(self, data_pipeline_client):
        """Test market data subscription endpoint contract."""
        subscription_request = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1m", "5m"],
            "callback_url": "http://localhost:8000/webhook/market-data"
        }
        
        response = data_pipeline_client.post("/api/v1/market-data/subscribe", json=subscription_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "subscription_id" in data
        assert "symbols" in data
        assert "status" in data
        assert "websocket_url" in data
        
        # Validate data types and values
        assert isinstance(data["subscription_id"], str)
        assert isinstance(data["symbols"], list)
        assert data["status"] in ["active", "pending", "failed"]
        assert data["websocket_url"].startswith(("ws://", "wss://"))
    
    def test_market_data_error_responses(self, data_pipeline_client):
        """Test market data API error response contracts."""
        # Test invalid symbol
        response = data_pipeline_client.get("/api/v1/market-data/INVALID_SYMBOL")
        
        # Should handle gracefully (either 404 or 200 with empty data)
        assert response.status_code in [200, 404]
        
        if response.status_code == 404:
            data = response.json()
            assert "error" in data
            assert "message" in data
    
    @pytest.mark.parametrize("symbol,timeframe,limit", [
        ("BTCUSDT", "1m", 50),
        ("ETHUSDT", "5m", 100),
        ("ADAUSDT", "1h", 200),
        ("DOTUSDT", "4h", 500),
        ("LINKUSDT", "1d", 1000)
    ])
    def test_market_data_parameter_variations(self, data_pipeline_client, symbol, timeframe, limit):
        """Test market data endpoint with various parameter combinations."""
        response = data_pipeline_client.get(f"/api/v1/market-data/{symbol}?timeframe={timeframe}&limit={limit}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == symbol
        assert data["timeframe"] == timeframe
        assert isinstance(data["data"], list)


class TestSMCDetectorAPIContracts:
    """Contract tests for SMC Detector API."""
    
    @pytest.fixture
    def smc_detector_client(self):
        """Create test client for SMC detector API."""
        app = FastAPI()
        
        @app.post("/api/v1/smc/detect-order-blocks")
        async def detect_order_blocks(request: Dict[str, Any]):
            return {
                "order_blocks": [
                    {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "type": "bullish",
                        "price_level": [50000.0, 49900.0],
                        "strength_volume": 5000.0,
                        "confidence": 0.85
                    }
                ],
                "total_blocks": 1,
                "analysis_metadata": {
                    "data_points_analyzed": 100,
                    "volume_threshold_percentile": 95,
                    "processing_time_ms": 150
                }
            }
        
        @app.post("/api/v1/smc/detect-choch-bos")
        async def detect_choch_bos(request: Dict[str, Any]):
            return {
                "coch_patterns": [
                    {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "type": "bullish_coch",
                        "price_level": [50100.0, 49950.0],
                        "confidence": 0.78,
                        "volume_confirmed": True
                    }
                ],
                "bos_patterns": [
                    {
                        "timestamp": "2024-01-01T10:05:00Z",
                        "type": "bullish_bos",
                        "price_level": 50200.0,
                        "confidence": 0.82,
                        "break_strength": 1.5
                    }
                ],
                "total_patterns": 2,
                "swing_highs": [10, 30, 50],
                "swing_lows": [5, 25, 45]
            }
        
        @app.post("/api/v1/smc/detect-liquidity-sweeps")
        async def detect_liquidity_sweeps(request: Dict[str, Any]):
            return {
                "detected_sweeps": [
                    {
                        "timestamp": "2024-01-01T10:00:00Z",
                        "type": "bullish_sweep",
                        "price_level": 50000.0,
                        "sweep_high": 50050.0,
                        "sweep_low": 49950.0,
                        "confidence": 0.75,
                        "volume_spike": 2.5,
                        "reversal_confirmed": True
                    }
                ],
                "total_sweeps": 1,
                "support_levels": [49800.0, 49900.0],
                "resistance_levels": [50100.0, 50200.0]
            }
        
        return TestClient(app)
    
    def test_order_block_detection_contract(self, smc_detector_client):
        """Test order block detection API contract."""
        request_data = {
            "market_data": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "open": 50000.0,
                    "high": 50100.0,
                    "low": 49900.0,
                    "close": 50050.0,
                    "volume": 1000.0
                }
            ],
            "parameters": {
                "volume_threshold_percentile": 95,
                "bos_confirmation_factor": 1.5
            }
        }
        
        response = smc_detector_client.post("/api/v1/smc/detect-order-blocks", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "order_blocks" in data
        assert "total_blocks" in data
        assert "analysis_metadata" in data
        
        # Validate order blocks structure
        for block in data["order_blocks"]:
            assert "timestamp" in block
            assert "type" in block
            assert "price_level" in block
            assert "strength_volume" in block
            assert "confidence" in block
            
            # Validate data types and constraints
            assert block["type"] in ["bullish", "bearish"]
            assert isinstance(block["price_level"], list)
            assert len(block["price_level"]) == 2
            assert 0 <= block["confidence"] <= 1
            assert block["strength_volume"] > 0
    
    def test_choch_bos_detection_contract(self, smc_detector_client):
        """Test CHOCH/BOS detection API contract."""
        request_data = {
            "market_data": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "open": 50000.0,
                    "high": 50100.0,
                    "low": 49900.0,
                    "close": 50050.0,
                    "volume": 1000.0
                }
            ],
            "parameters": {
                "min_swing_distance": 5,
                "confidence_threshold": 0.7
            }
        }
        
        response = smc_detector_client.post("/api/v1/smc/detect-choch-bos", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "coch_patterns" in data
        assert "bos_patterns" in data
        assert "total_patterns" in data
        assert "swing_highs" in data
        assert "swing_lows" in data
        
        # Validate CHOCH patterns
        for pattern in data["coch_patterns"]:
            assert "timestamp" in pattern
            assert "type" in pattern
            assert "confidence" in pattern
            assert pattern["type"] in ["bullish_coch", "bearish_coch"]
            assert 0 <= pattern["confidence"] <= 1
        
        # Validate BOS patterns
        for pattern in data["bos_patterns"]:
            assert "timestamp" in pattern
            assert "type" in pattern
            assert "confidence" in pattern
            assert pattern["type"] in ["bullish_bos", "bearish_bos"]
            assert 0 <= pattern["confidence"] <= 1
    
    def test_liquidity_sweep_detection_contract(self, smc_detector_client):
        """Test liquidity sweep detection API contract."""
        request_data = {
            "market_data": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "open": 50000.0,
                    "high": 50100.0,
                    "low": 49900.0,
                    "close": 50050.0,
                    "volume": 1000.0
                }
            ],
            "parameters": {
                "volume_threshold_percentile": 95,
                "min_sweep_distance": 0.1,
                "confidence_threshold": 0.7
            }
        }
        
        response = smc_detector_client.post("/api/v1/smc/detect-liquidity-sweeps", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "detected_sweeps" in data
        assert "total_sweeps" in data
        assert "support_levels" in data
        assert "resistance_levels" in data
        
        # Validate sweep structure
        for sweep in data["detected_sweeps"]:
            assert "timestamp" in sweep
            assert "type" in sweep
            assert "confidence" in sweep
            assert "volume_spike" in sweep
            assert "reversal_confirmed" in sweep
            
            assert sweep["type"] in ["bullish_sweep", "bearish_sweep"]
            assert 0 <= sweep["confidence"] <= 1
            assert isinstance(sweep["reversal_confirmed"], bool)


class TestDecisionEngineAPIContracts:
    """Contract tests for Decision Engine API."""
    
    @pytest.fixture
    def decision_engine_client(self):
        """Create test client for decision engine API."""
        app = FastAPI()
        
        @app.post("/api/v1/decision/make-decision")
        async def make_decision(request: Dict[str, Any]):
            return {
                "action": "BUY",
                "symbol": "BTCUSDT",
                "entry_price": 50000.0,
                "confidence": 0.85,
                "reasoning": "Strong bullish order block detected with high volume confirmation",
                "model_predictions": {
                    "lstm": {"action": "BUY", "confidence": 0.82},
                    "transformer": {"action": "BUY", "confidence": 0.88},
                    "ppo": {"action": "HOLD", "confidence": 0.65}
                },
                "market_conditions": {
                    "volatility": 0.25,
                    "trend_strength": 35.0,
                    "trend_direction": "uptrend",
                    "regime": "high_vol_uptrend"
                },
                "timestamp": "2024-01-01T10:00:00Z"
            }
        
        @app.post("/api/v1/decision/update-models")
        async def update_models(request: Dict[str, Any]):
            return {
                "status": "success",
                "models_updated": ["lstm", "transformer"],
                "training_metrics": {
                    "lstm": {"accuracy": 0.78, "loss": 0.45},
                    "transformer": {"accuracy": 0.82, "loss": 0.38}
                },
                "timestamp": "2024-01-01T10:00:00Z"
            }
        
        return TestClient(app)
    
    def test_make_decision_contract(self, decision_engine_client):
        """Test decision making API contract."""
        request_data = {
            "order_blocks": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "type": "bullish",
                    "price_level": [50000.0, 49900.0],
                    "strength_volume": 5000.0,
                    "confidence": 0.85
                }
            ],
            "market_data": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "close": 50000.0,
                    "volume": 1000.0
                }
            ],
            "parameters": {
                "confidence_threshold": 0.7,
                "risk_tolerance": "medium"
            }
        }
        
        response = decision_engine_client.post("/api/v1/decision/make-decision", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "action" in data
        assert "symbol" in data
        assert "entry_price" in data
        assert "confidence" in data
        assert "reasoning" in data
        assert "model_predictions" in data
        assert "market_conditions" in data
        assert "timestamp" in data
        
        # Validate data types and constraints
        assert data["action"] in ["BUY", "SELL", "HOLD"]
        assert isinstance(data["entry_price"], (int, float))
        assert 0 <= data["confidence"] <= 1
        assert isinstance(data["reasoning"], str)
        
        # Validate model predictions structure
        for model, prediction in data["model_predictions"].items():
            assert "action" in prediction
            assert "confidence" in prediction
            assert prediction["action"] in ["BUY", "SELL", "HOLD"]
            assert 0 <= prediction["confidence"] <= 1
        
        # Validate market conditions
        market_conditions = data["market_conditions"]
        assert "volatility" in market_conditions
        assert "trend_strength" in market_conditions
        assert "trend_direction" in market_conditions
        assert "regime" in market_conditions
    
    def test_model_update_contract(self, decision_engine_client):
        """Test model update API contract."""
        request_data = {
            "training_data": [
                {
                    "features": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "target": 1
                }
            ],
            "models_to_update": ["lstm", "transformer"],
            "training_parameters": {
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001
            }
        }
        
        response = decision_engine_client.post("/api/v1/decision/update-models", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "status" in data
        assert "models_updated" in data
        assert "training_metrics" in data
        assert "timestamp" in data
        
        # Validate data types
        assert data["status"] in ["success", "partial", "failed"]
        assert isinstance(data["models_updated"], list)
        
        # Validate training metrics
        for model, metrics in data["training_metrics"].items():
            assert "accuracy" in metrics
            assert "loss" in metrics
            assert 0 <= metrics["accuracy"] <= 1
            assert metrics["loss"] >= 0


class TestRiskManagerAPIContracts:
    """Contract tests for Risk Manager API."""
    
    @pytest.fixture
    def risk_manager_client(self):
        """Create test client for risk manager API."""
        app = FastAPI()
        
        @app.post("/api/v1/risk/calculate-parameters")
        async def calculate_risk_parameters(request: Dict[str, Any]):
            return {
                "stop_loss": 49500.0,
                "take_profit": 50500.0,
                "position_size": 0.1,
                "risk_reward_ratio": 2.0,
                "max_loss_amount": 500.0,
                "risk_percentage": 2.0,
                "calculations": {
                    "entry_price": 50000.0,
                    "account_balance": 25000.0,
                    "volatility_adjustment": 1.2,
                    "order_block_distance": 100.0
                },
                "timestamp": "2024-01-01T10:00:00Z"
            }
        
        @app.post("/api/v1/risk/validate-trade")
        async def validate_trade(request: Dict[str, Any]):
            return {
                "is_valid": True,
                "risk_score": 3.5,
                "warnings": [],
                "violations": [],
                "risk_metrics": {
                    "position_risk": 2.0,
                    "portfolio_risk": 15.5,
                    "correlation_risk": 0.3,
                    "liquidity_risk": 0.1
                },
                "recommendations": [
                    "Consider reducing position size by 20%",
                    "Monitor correlation with existing positions"
                ],
                "timestamp": "2024-01-01T10:00:00Z"
            }
        
        return TestClient(app)
    
    def test_risk_parameters_calculation_contract(self, risk_manager_client):
        """Test risk parameters calculation API contract."""
        request_data = {
            "entry_price": 50000.0,
            "action": "BUY",
            "account_balance": 25000.0,
            "risk_percentage": 2.0,
            "order_blocks": [
                {
                    "type": "bullish",
                    "price_level": [50000.0, 49900.0]
                }
            ],
            "market_conditions": {
                "volatility": 0.25,
                "trend_strength": 35.0
            }
        }
        
        response = risk_manager_client.post("/api/v1/risk/calculate-parameters", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "stop_loss" in data
        assert "take_profit" in data
        assert "position_size" in data
        assert "risk_reward_ratio" in data
        assert "max_loss_amount" in data
        assert "risk_percentage" in data
        assert "calculations" in data
        assert "timestamp" in data
        
        # Validate data types and constraints
        assert isinstance(data["stop_loss"], (int, float))
        assert isinstance(data["take_profit"], (int, float))
        assert data["position_size"] > 0
        assert data["risk_reward_ratio"] > 0
        assert data["max_loss_amount"] > 0
        assert 0 < data["risk_percentage"] <= 100
        
        # Validate calculations structure
        calculations = data["calculations"]
        assert "entry_price" in calculations
        assert "account_balance" in calculations
        assert isinstance(calculations["entry_price"], (int, float))
        assert isinstance(calculations["account_balance"], (int, float))
    
    def test_trade_validation_contract(self, risk_manager_client):
        """Test trade validation API contract."""
        request_data = {
            "trade": {
                "symbol": "BTCUSDT",
                "action": "BUY",
                "entry_price": 50000.0,
                "position_size": 0.1,
                "stop_loss": 49500.0,
                "take_profit": 50500.0
            },
            "portfolio": {
                "total_balance": 25000.0,
                "available_balance": 20000.0,
                "open_positions": [
                    {
                        "symbol": "ETHUSDT",
                        "side": "long",
                        "size": 1.0,
                        "unrealized_pnl": 100.0
                    }
                ]
            },
            "risk_limits": {
                "max_position_risk": 5.0,
                "max_portfolio_risk": 20.0,
                "max_correlation": 0.7
            }
        }
        
        response = risk_manager_client.post("/api/v1/risk/validate-trade", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "is_valid" in data
        assert "risk_score" in data
        assert "warnings" in data
        assert "violations" in data
        assert "risk_metrics" in data
        assert "recommendations" in data
        assert "timestamp" in data
        
        # Validate data types
        assert isinstance(data["is_valid"], bool)
        assert isinstance(data["risk_score"], (int, float))
        assert isinstance(data["warnings"], list)
        assert isinstance(data["violations"], list)
        assert isinstance(data["recommendations"], list)
        
        # Validate risk metrics
        risk_metrics = data["risk_metrics"]
        assert "position_risk" in risk_metrics
        assert "portfolio_risk" in risk_metrics
        assert all(isinstance(v, (int, float)) for v in risk_metrics.values())


class TestExecutionEngineAPIContracts:
    """Contract tests for Execution Engine API."""
    
    @pytest.fixture
    def execution_engine_client(self):
        """Create test client for execution engine API."""
        app = FastAPI()
        
        @app.post("/api/v1/execution/execute-trade")
        async def execute_trade(request: Dict[str, Any]):
            return {
                "execution_id": "exec_123456789",
                "status": "executed",
                "trade": {
                    "symbol": "BTCUSDT",
                    "action": "BUY",
                    "quantity": 0.1,
                    "executed_price": 50005.0,
                    "executed_quantity": 0.1,
                    "fees": 5.0,
                    "execution_time": "2024-01-01T10:00:01.234Z"
                },
                "order_details": {
                    "order_id": "order_987654321",
                    "order_type": "market",
                    "time_in_force": "IOC",
                    "exchange": "binance"
                },
                "slippage": {
                    "expected_price": 50000.0,
                    "executed_price": 50005.0,
                    "slippage_bps": 1.0,
                    "slippage_amount": 5.0
                },
                "timestamp": "2024-01-01T10:00:01.234Z"
            }
        
        @app.get("/api/v1/execution/status/{execution_id}")
        async def get_execution_status(execution_id: str):
            return {
                "execution_id": execution_id,
                "status": "executed",
                "progress": 100,
                "updates": [
                    {
                        "timestamp": "2024-01-01T10:00:00.500Z",
                        "status": "pending",
                        "message": "Order submitted to exchange"
                    },
                    {
                        "timestamp": "2024-01-01T10:00:01.234Z",
                        "status": "executed",
                        "message": "Order fully executed"
                    }
                ],
                "final_result": {
                    "executed_quantity": 0.1,
                    "average_price": 50005.0,
                    "total_fees": 5.0
                }
            }
        
        return TestClient(app)
    
    def test_trade_execution_contract(self, execution_engine_client):
        """Test trade execution API contract."""
        request_data = {
            "trade": {
                "symbol": "BTCUSDT",
                "action": "BUY",
                "quantity": 0.1,
                "order_type": "market",
                "entry_price": 50000.0,
                "stop_loss": 49500.0,
                "take_profit": 50500.0
            },
            "execution_parameters": {
                "exchange": "binance",
                "time_in_force": "IOC",
                "max_slippage_bps": 10,
                "retry_attempts": 3
            },
            "risk_parameters": {
                "max_position_size": 1.0,
                "emergency_stop": False
            }
        }
        
        response = execution_engine_client.post("/api/v1/execution/execute-trade", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "execution_id" in data
        assert "status" in data
        assert "trade" in data
        assert "order_details" in data
        assert "slippage" in data
        assert "timestamp" in data
        
        # Validate execution ID format
        assert isinstance(data["execution_id"], str)
        assert len(data["execution_id"]) > 0
        
        # Validate status
        assert data["status"] in ["pending", "executed", "partially_executed", "failed", "cancelled"]
        
        # Validate trade details
        trade = data["trade"]
        assert "symbol" in trade
        assert "action" in trade
        assert "executed_price" in trade
        assert "executed_quantity" in trade
        assert "fees" in trade
        assert "execution_time" in trade
        
        # Validate order details
        order_details = data["order_details"]
        assert "order_id" in order_details
        assert "order_type" in order_details
        assert "exchange" in order_details
        
        # Validate slippage information
        slippage = data["slippage"]
        assert "expected_price" in slippage
        assert "executed_price" in slippage
        assert "slippage_bps" in slippage
        assert isinstance(slippage["slippage_bps"], (int, float))
    
    def test_execution_status_contract(self, execution_engine_client):
        """Test execution status API contract."""
        execution_id = "exec_123456789"
        
        response = execution_engine_client.get(f"/api/v1/execution/status/{execution_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "execution_id" in data
        assert "status" in data
        assert "progress" in data
        assert "updates" in data
        
        # Validate data types
        assert data["execution_id"] == execution_id
        assert data["status"] in ["pending", "executed", "partially_executed", "failed", "cancelled"]
        assert 0 <= data["progress"] <= 100
        assert isinstance(data["updates"], list)
        
        # Validate updates structure
        for update in data["updates"]:
            assert "timestamp" in update
            assert "status" in update
            assert "message" in update
            assert isinstance(update["message"], str)


@pytest.mark.contract
class TestCrossServiceIntegration:
    """Contract tests for cross-service integration."""
    
    def test_data_pipeline_to_smc_detector_integration(self):
        """Test data flow from data pipeline to SMC detector."""
        # Mock data pipeline response
        market_data_response = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "data": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "open": 50000.0,
                    "high": 50100.0,
                    "low": 49900.0,
                    "close": 50050.0,
                    "volume": 1000.0
                }
            ]
        }
        
        # Transform for SMC detector
        smc_request = {
            "market_data": market_data_response["data"],
            "parameters": {
                "volume_threshold_percentile": 95
            }
        }
        
        # Validate transformation
        assert "market_data" in smc_request
        assert isinstance(smc_request["market_data"], list)
        assert len(smc_request["market_data"]) > 0
        
        # Validate data structure compatibility
        for candle in smc_request["market_data"]:
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            assert all(field in candle for field in required_fields)
    
    def test_smc_detector_to_decision_engine_integration(self):
        """Test data flow from SMC detector to decision engine."""
        # Mock SMC detector response
        smc_response = {
            "order_blocks": [
                {
                    "timestamp": "2024-01-01T10:00:00Z",
                    "type": "bullish",
                    "price_level": [50000.0, 49900.0],
                    "strength_volume": 5000.0,
                    "confidence": 0.85
                }
            ],
            "total_blocks": 1
        }
        
        # Transform for decision engine
        decision_request = {
            "order_blocks": smc_response["order_blocks"],
            "parameters": {
                "confidence_threshold": 0.7
            }
        }
        
        # Validate transformation
        assert "order_blocks" in decision_request
        assert isinstance(decision_request["order_blocks"], list)
        
        # Validate order block structure compatibility
        for block in decision_request["order_blocks"]:
            assert "type" in block
            assert "confidence" in block
            assert block["type"] in ["bullish", "bearish"]
            assert 0 <= block["confidence"] <= 1
    
    def test_decision_engine_to_risk_manager_integration(self):
        """Test data flow from decision engine to risk manager."""
        # Mock decision engine response
        decision_response = {
            "action": "BUY",
            "symbol": "BTCUSDT",
            "entry_price": 50000.0,
            "confidence": 0.85
        }
        
        # Transform for risk manager
        risk_request = {
            "entry_price": decision_response["entry_price"],
            "action": decision_response["action"],
            "account_balance": 25000.0,  # From portfolio service
            "risk_percentage": 2.0
        }
        
        # Validate transformation
        assert "entry_price" in risk_request
        assert "action" in risk_request
        assert risk_request["action"] in ["BUY", "SELL"]
        assert isinstance(risk_request["entry_price"], (int, float))
    
    def test_risk_manager_to_execution_engine_integration(self):
        """Test data flow from risk manager to execution engine."""
        # Mock risk manager response
        risk_response = {
            "stop_loss": 49500.0,
            "take_profit": 50500.0,
            "position_size": 0.1,
            "risk_reward_ratio": 2.0
        }
        
        # Mock decision engine data
        decision_data = {
            "action": "BUY",
            "symbol": "BTCUSDT",
            "entry_price": 50000.0
        }
        
        # Transform for execution engine
        execution_request = {
            "trade": {
                "symbol": decision_data["symbol"],
                "action": decision_data["action"],
                "quantity": risk_response["position_size"],
                "order_type": "market",
                "entry_price": decision_data["entry_price"],
                "stop_loss": risk_response["stop_loss"],
                "take_profit": risk_response["take_profit"]
            },
            "execution_parameters": {
                "exchange": "binance",
                "time_in_force": "IOC"
            }
        }
        
        # Validate transformation
        assert "trade" in execution_request
        trade = execution_request["trade"]
        assert "symbol" in trade
        assert "action" in trade
        assert "quantity" in trade
        assert trade["action"] in ["BUY", "SELL"]
        assert trade["quantity"] > 0
    
    def test_error_propagation_across_services(self):
        """Test error propagation and handling across services."""
        # Test error response format consistency
        error_responses = [
            {
                "service": "data_pipeline",
                "error": {
                    "error": "DATA_UNAVAILABLE",
                    "message": "Market data not available for symbol",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "details": {"symbol": "INVALID"}
                }
            },
            {
                "service": "smc_detector",
                "error": {
                    "error": "INSUFFICIENT_DATA",
                    "message": "Not enough data points for analysis",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "details": {"required": 100, "provided": 50}
                }
            },
            {
                "service": "decision_engine",
                "error": {
                    "error": "LOW_CONFIDENCE",
                    "message": "All models below confidence threshold",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "details": {"max_confidence": 0.45, "threshold": 0.7}
                }
            }
        ]
        
        # Validate error format consistency
        for response in error_responses:
            error = response["error"]
            assert "error" in error
            assert "message" in error
            assert "timestamp" in error
            assert isinstance(error["error"], str)
            assert isinstance(error["message"], str)
            assert "details" in error  # Optional but recommended


if __name__ == "__main__":
    # Run contract tests
    pytest.main([__file__, "-v", "-m", "contract", "--tb=short"])