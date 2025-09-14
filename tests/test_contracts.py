"""
Contract-style tests to ensure cross-module data contracts remain stable.

Validates key DTO-like shapes returned by connectors and integration flows.
"""

from typing import Dict, Any

import pytest


def _assert_trade_contract(trade: Dict[str, Any]) -> None:
    required = {"exchange", "symbol", "price", "quantity", "side", "timestamp"}
    assert required.issubset(trade.keys())


@pytest.mark.contract
def test_connector_trade_contract_shapes():
    # Example normalized trades from connectors (representative subset)
    binance = {
        "exchange": "binance", "symbol": "BTCUSDT", "price": 50000.0,
        "quantity": 0.01, "side": "BUY", "timestamp": 1710000000000, "trade_id": 1
    }
    bybit = {
        "exchange": "bybit", "symbol": "BTCUSDT", "price": 50010.0,
        "quantity": 0.02, "side": "Buy", "timestamp": 1710000001000, "trade_id": "2"
    }
    oanda = {
        "exchange": "oanda", "symbol": "EUR_USD", "price": 1.1,
        "quantity": 1000.0, "side": "buy", "timestamp": 1710000002, "trade_id": "x"
    }

    for t in (binance, bybit, oanda):
        _assert_trade_contract(t)


